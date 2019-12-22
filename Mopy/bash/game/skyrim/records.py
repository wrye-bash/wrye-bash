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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""This module contains the skyrim record classes."""
from collections import OrderedDict

from .constants import condition_function_data
from ... import brec
from ...bolt import Flags, encode, struct_pack, struct_unpack
from ...brec import MelRecord, MelObject, MelGroups, MelStruct, FID, \
    MelGroup, MelString, MreLeveledListBase, MelSet, MelFid, MelNull, \
    MelOptStruct, MelFids, MreHeaderBase, MelBase, MelUnicode, MelFidList, \
    MreGmstBase, MelLString, MelSortedFidList, MelMODS, MreHasEffects, \
    MelColorInterpolator, MelValueInterpolator, MelUnion, AttrValDecider, \
    MelRegnEntrySubrecord, PartialLoadDecider, FlagDecider, MelFloat, \
    MelSInt8, MelSInt32, MelUInt8, MelUInt16, MelUInt32, MelOptFloat, \
    MelOptSInt16, MelOptSInt32, MelOptUInt8, MelOptUInt16, MelOptUInt32, \
    MelOptFid, MelCounter, MelPartialCounter, MelBounds, null1, null2, null3, \
    null4, MelSequential, MelTruncatedStruct, MelIcons, MelIcons2, MelIcon, \
    MelIco2, MelEdid, MelFull, MelArray, MelWthrColors
from ...exception import BoltError, ModError, ModSizeError, StateError
# Set MelModel in brec but only if unset, otherwise we are being imported from
# fallout4.records
if brec.MelModel is None:

    class _MelModel(MelGroup):
        """Represents a model record."""
        # MODB and MODD are no longer used by TES5Edit
        typeSets = {
            'MODL': ('MODL', 'MODT', 'MODS'),
            'MOD2': ('MOD2', 'MO2T', 'MO2S'),
            'MOD3': ('MOD3', 'MO3T', 'MO3S'),
            'MOD4': ('MOD4', 'MO4T', 'MO4S'),
            'MOD5': ('MOD5', 'MO5T', 'MO5S'),
            'DMDL': ('DMDL', 'DMDT', 'DMDS'),
        }

        def __init__(self, attr='model', subType='MODL'):
            types = self.__class__.typeSets[subType]
            MelGroup.__init__(
                self, attr,
                MelString(types[0], 'modPath'),
                # Ignore texture hashes - they're only an
                # optimization, plenty of records in Skyrim.esm
                # are missing them
                MelNull(types[1]),
                MelMODS(types[2], 'alternateTextures')
            )

    brec.MelModel = _MelModel
from ...brec import MelModel

#------------------------------------------------------------------------------
# Record Elements    ----------------------------------------------------------
#------------------------------------------------------------------------------
# TODO(inf) Unused - use or bin (not sure if this actually works though)
class MreActor(MelRecord):
    """Creatures and NPCs."""

    def mergeFilter(self,modSet):
        """Filter out items that don't come from specified modSet.
        Filters spells, factions and items."""
        if not self.longFids: raise StateError(_("Fids not in long format"))
        self.spells = [x for x in self.spells if x[0] in modSet]
        self.factions = [x for x in self.factions if x.faction[0] in modSet]
        self.items = [x for x in self.items if x.item[0] in modSet]

#------------------------------------------------------------------------------
class MelBipedObjectData(MelStruct):
    """Handler for BODT/BOD2 subrecords.  Reads both types, writes only BOD2"""
    BipedFlags = Flags(0L,Flags.getNames(
            (0, 'head'),
            (1, 'hair'),
            (2, 'body'),
            (3, 'hands'),
            (4, 'forearms'),
            (5, 'amulet'),
            (6, 'ring'),
            (7, 'feet'),
            (8, 'calves'),
            (9, 'shield'),
            (10, 'bodyaddon1_tail'),
            (11, 'long_hair'),
            (12, 'circlet'),
            (13, 'bodyaddon2'),
            (14, 'dragon_head'),
            (15, 'dragon_lwing'),
            (16, 'dragon_rwing'),
            (17, 'dragon_body'),
            (18, 'bodyaddon7'),
            (19, 'bodyaddon8'),
            (20, 'decapate_head'),
            (21, 'decapate'),
            (22, 'bodyaddon9'),
            (23, 'bodyaddon10'),
            (24, 'bodyaddon11'),
            (25, 'bodyaddon12'),
            (26, 'bodyaddon13'),
            (27, 'bodyaddon14'),
            (28, 'bodyaddon15'),
            (29, 'bodyaddon16'),
            (30, 'bodyaddon17'),
            (31, 'fx01'),
        ))

    ## Legacy Flags, (For BODT subrecords) - #4 is the only one not discarded.
    LegacyFlags = Flags(0L,Flags.getNames(
            (0, 'modulates_voice'), #{>>> From ARMA <<<}
            (1, 'unknown_2'),
            (2, 'unknown_3'),
            (3, 'unknown_4'),
            (4, 'non_playable'), #{>>> From ARMO <<<}
        ))

    ArmorTypeFlags = Flags(0L,Flags.getNames(
        (0, 'light_armor'),
        (1, 'heavy_armor'),
        (2, 'clothing'),
        ))

    def __init__(self):
        MelStruct.__init__(self,'BOD2','=2I',(MelBipedObjectData.BipedFlags,'bipedFlags',0L),(MelBipedObjectData.ArmorTypeFlags,'armorFlags',0L))

    def getLoaders(self,loaders):
        # Loads either old style BODT or new style BOD2 records
        loaders['BOD2'] = self
        loaders['BODT'] = self

    def loadData(self, record, ins, sub_type, size_, readId):
        if sub_type == 'BODT':
            # Old record type, use alternate loading routine
            if size_ == 8:
                # Version 20 of this subrecord is only 8 bytes (armorType omitted)
                bipedFlags,legacyData = ins.unpack('=2I', size_, readId)
                armorFlags = 0
            elif size_ != 12:
                raise ModSizeError(ins.inName, readId, (12, 8), size_)
            else:
                bipedFlags,legacyData,armorFlags = ins.unpack('=3I', size_, readId)
            # legacyData is discarded except for non-playable status
            setter = record.__setattr__
            setter('bipedFlags',MelBipedObjectData.BipedFlags(bipedFlags))
            legacyFlags = MelBipedObjectData.LegacyFlags(legacyData)
            record.flags1[2] = legacyFlags[4]
            setter('armorFlags',MelBipedObjectData.ArmorTypeFlags(armorFlags))
        else:
            # BOD2 - new style, MelStruct can handle it
            MelStruct.loadData(self, record, ins, sub_type, size_, readId)

class MelAttackData(MelStruct):
    """Wrapper around MelStruct to share some code between the NPC_ and RACE
    definitions."""
    DataFlags = Flags(0L, Flags.getNames('ignoreWeapon', 'bashAttack',
                                         'powerAttack', 'leftAttack',
                                         'rotatingAttack', 'unknown6',
                                         'unknown7', 'unknown8', 'unknown9',
                                         'unknown10', 'unknown11', 'unknown12',
                                         'unknown13', 'unknown14', 'unknown15',
                                         'unknown16',))

    def __init__(self):
        MelStruct.__init__(self, 'ATKD', '2f2I3fI3f', 'damageMult',
                           'attackChance', (FID, 'attackSpell'),
                           (MelAttackData.DataFlags, 'attackDataFlags', 0L),
                           'attackAngle', 'strikeAngle', 'stagger',
                           (FID, 'attackType'), 'knockdown', 'recoveryTime',
                           'staminaMult')

#------------------------------------------------------------------------------
class MelCoed(MelOptStruct):
    """Needs custom unpacker to look at FormID type of owner.  If owner is an
    NPC then it is followed by a FormID.  If owner is a faction then it is
    followed by an signed integer or '=Iif' instead of '=IIf' """ # see #282
    def __init__(self):
        MelOptStruct.__init__(self,'COED','=IIf',(FID,'owner'),(FID,'glob'),
                              'itemCondition')
#------------------------------------------------------------------------------
class MelColor(MelStruct):
    """Required Color."""
    def __init__(self, signature='CNAM'):
        MelStruct.__init__(self, signature, '=4B', 'red', 'green', 'blue',
                           'unk_c')

class MelColorO(MelOptStruct):
    """Optional Color."""
    def __init__(self, signature='CNAM'):
        MelOptStruct.__init__(self, signature, '=4B', 'red', 'green', 'blue',
                           'unk_c')

#------------------------------------------------------------------------------
class MelConditions(MelGroups):
    """Wraps MelGroups for the common task of defining an array of conditions.
    See also MelConditionCounter, which is commonly combined with this class.
    Difficulty is that FID state of parameters depends on function index."""
    class MelCtda(MelStruct):
        def setDefault(self, record):
            MelStruct.setDefault(self, record)
            record.form12345 = 'iiIIi'

        def hasFids(self, formElements):
            formElements.add(self)

        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ not in (32, 28, 24, 20):
                raise ModSizeError(ins.inName, readId, (32, 28, 24, 20), size_)
            unpacked1 = ins.unpack('=B3sfH2s', 12, readId)
            (record.operFlag, record.unused1, record.compValue, ifunc,
             record.unused2) = unpacked1
            #--Get parameters
            if ifunc not in condition_function_data:
                raise BoltError(u'Unknown condition function: %d\nparam1: '
                                u'%08X\nparam2: %08X' % (
                    ifunc, ins.unpackRef(), ins.unpackRef()))
            # Form1 is Param1 - 2 means fid
            form1 = 'I' if condition_function_data[ifunc][1] == 2 else 'i'
            # Form2 is Param2
            form2 = 'I' if condition_function_data[ifunc][2] == 2 else 'i'
            # Form3 is runOn
            form3 = 'I'
            # Form4 is reference, this is a formID when runOn = 2
            form4 = 'I'
            # Form5 is Param3
            form5 = 'I' if condition_function_data[ifunc][3] == 2 else 'i'
            if size_ == 32:
                form12345 = form1 + form2 + form3 + form4 + form5
                unpacked2 = ins.unpack(form12345, 20, readId)
                (record.param1, record.param2, record.runOn, record.reference,
                 record.param3) = unpacked2
            elif size_ == 28:
                form12345 = form1 + form2 + form3 + form4
                unpacked2 = ins.unpack(form12345, 16, readId)
                (record.param1, record.param2, record.runOn,
                 record.reference) = unpacked2
                record.param3 = null4
            elif size_ == 24:
                form12345 = form1 + form2 + form3
                unpacked2 = ins.unpack(form12345, 12, readId)
                (record.param1, record.param2, record.runOn) = unpacked2
                record.reference, record.param3 = null4, null4
            else: # size_ == 20, verified at the start
                form12345 = form1 + form2
                unpacked2 = ins.unpack(form12345, 8, readId)
                record.param1, record.param2 = unpacked2
                (record.runOn, record.reference,
                 record.param3) = null4, null4, null4
            record.ifunc, record.form12345 = ifunc, form12345

        def dumpData(self,record,out):
            out.packSub('CTDA', '=B3sfH2s' + record.form12345,
                record.operFlag, record.unused1, record.compValue,
                record.ifunc, record.unused2, record.param1, record.param2,
                record.runOn, record.reference, record.param3)

        def mapFids(self, record, function, save=False):
                form12345 = record.form12345
                if form12345[0] == 'I':
                    result = function(record.param1)
                    if save: record.param1 = result
                if form12345[1] == 'I':
                    result = function(record.param2)
                    if save: record.param2 = result
                # runOn is uint32, never FID
                if (len(form12345) > 3 and form12345[3] == 'I'
                        and record.runOn == 2):
                    result = function(record.reference)
                    if save: record.reference = result
                if len(form12345) > 4 and form12345[4] == 'I':
                    result = function(record.param3)
                    if save: record.param3 = result

    def __init__(self, attr='conditions'):
        MelGroups.__init__(self, attr,
            MelGroups('condition_list',
                MelConditions.MelCtda(
                    'CTDA', 'B3sfH2siiIIi', 'operFlag', ('unused1', null3),
                    'compValue', 'ifunc', ('unused2', null2), 'param1',
                    'param2', 'runOn', 'reference', 'param3'),
            ),
            MelString('CIS1','param_cis1'),
            MelString('CIS2','param_cis2'),
        )

class MelConditionCounter(MelCounter):
    """Wraps MelCounter for the common task of defining a counter that counts
    MelConditions."""
    def __init__(self):
        MelCounter.__init__(
            self, MelUInt32('CITC', 'conditionCount'), counts='conditions')

#------------------------------------------------------------------------------
class MelDecalData(MelOptStruct):
    """Represents Decal Data."""

    DecalDataFlags = Flags(0L,Flags.getNames(
            (0, 'parallax'),
            (1, 'alphaBlending'),
            (2, 'alphaTesting'),
            (3, 'noSubtextures'),
        ))

    def __init__(self):
        """Initialize elements."""
        MelOptStruct.__init__(
            self, 'DODT', '7f2B2s3Bs', 'minWidth', 'maxWidth',
            'minHeight', 'maxHeight', 'depth', 'shininess', 'parallaxScale',
            'parallaxPasses', (MelDecalData.DecalDataFlags, 'flags', 0L),
            ('unknownDecal1', null2), 'redDecal', 'greenDecal', 'blueDecal',
            ('unknownDecal2', null1)
        )

#------------------------------------------------------------------------------
class MelDestructible(MelGroup):
    """Represents a set of destruct record."""

    MelDestStageFlags = Flags(0L,Flags.getNames(
        (0, 'capDamage'),
        (1, 'disable'),
        (2, 'destroy'),
        (3, 'ignoreExternalDmg'),
        ))

    def __init__(self,attr='destructible'):
        MelGroup.__init__(self,attr,
            MelStruct('DEST','i2B2s','health','count','vatsTargetable','dest_unused'),
            MelGroups('stages',
                MelStruct('DSTD','=4Bi2Ii','health','index','damageStage',
                         (MelDestructible.MelDestStageFlags,'flags',0L),'selfDamagePerSecond',
                         (FID,'explosion',None),(FID,'debris',None),'debrisCount'),
                MelModel('model','DMDL'),
                MelBase('DSTF','footer'),
            ),
        )

#------------------------------------------------------------------------------
class MelEffects(MelGroups):
    """Represents ingredient/potion/enchantment/spell effects."""

    def __init__(self,attr='effects'):
        MelGroups.__init__(self,attr,
            MelFid('EFID','name'), # baseEffect, name
            MelStruct('EFIT','f2I','magnitude','area','duration',),
            MelConditions(),
        )

#------------------------------------------------------------------------------
class MelItems(MelGroups):
    """Wraps MelGroups for the common task of defining a list of items."""
    def __init__(self):
        MelGroups.__init__(self, 'items',
            MelStruct('CNTO', 'Ii', (FID, 'item', None), 'count'),
            MelCoed(),
        )

class MelItemsCounter(MelCounter):
    """Wraps MelCounter for the common task of defining an items counter."""
    def __init__(self):
        MelCounter.__init__(
            self, MelUInt32('COCT', 'item_count'), counts='items')

#------------------------------------------------------------------------------
class MelKeywords(MelSequential):
    """Wraps MelSequential for the common task of defining a list of keywords
    and a corresponding counter."""
    def __init__(self):
        MelSequential.__init__(self,
            # TODO(inf) Kept it as such, why little-endian?
            MelCounter(MelStruct('KSIZ', '<I', 'keyword_count'),
                       counts='keywords'),
            MelFidList('KWDA', 'keywords'),
        )

#------------------------------------------------------------------------------
class MelOwnership(MelGroup):
    """Handles XOWN, XRNK for cells and cell children."""

    def __init__(self,attr='ownership'):
        MelGroup.__init__(self,attr,
            MelFid('XOWN','owner'),
            MelOptSInt32('XRNK', ('rank', None)),
        )

    def dumpData(self,record,out):
        if record.ownership and record.ownership.owner:
            MelGroup.dumpData(self,record,out)

#------------------------------------------------------------------------------
# VMAD - Virtual Machine Adapters
# Some helper classes and functions
def _dump_vmad_str16(str_val):
    """Encodes the specified string using cp1252 and returns data for both its
    length (as a 16-bit integer) and its encoded value."""
    encoded_str = encode(str_val, firstEncoding='cp1252')
    return struct_pack('=H', len(encoded_str)) + encoded_str

def _read_vmad_str16(ins, read_id):
    """Reads a 16-bit length integer, then reads a string in that length.
    Always uses cp1252 to decode."""
    return ins.read(ins.unpack('H', 2, read_id)[0], read_id).decode('cp1252')

class _AVmadComponent(object):
    """Abstract base class for VMAD components. Specify a 'processors'
    class variable to use. Syntax: OrderedDict, mapping an attribute name
    for the record to a tuple containing a format string (limited to format
    strings that resolve to a single attribute) and the format size for that
    format string. 'str16' is a special format string that instead calls
    _read_vmad_str16/_dump_vmad_str16 to handle the matching attribute. If
    using str16, you may omit the format size.

    You can override any of the methods specified below to do other things
    after or before 'processors' has been evaluated, just be sure to call
    super(...).{dump,load}_data(...) when appropriate.

    :type processors: OrderedDict[str, tuple[str, str] | tuple[str]]"""
    processors = OrderedDict()

    def dump_data(self, record):
        """Dumps data for this fragment using the specified record and
        returns the result as a string, ready for writing to an output
        stream."""
        getter = record.__getattribute__
        out_data = ''
        for attr, fmt in self.__class__.processors.iteritems():
            attr_val = getter(attr)
            if fmt[0] == 'str16':
                out_data += _dump_vmad_str16(attr_val)
            else:
                # Make sure to dump with '=' to avoid padding
                out_data += struct_pack('=' + fmt[0], attr_val)
        return out_data

    def load_data(self, record, ins, vmad_version, obj_format, read_id):
        """Loads data for this fragment from the specified input stream and
        attaches it to the specified record. The version of VMAD and the object
        format are also given."""
        setter = record.__setattr__
        for attr, fmt in self.__class__.processors.iteritems():
            fmt_str = fmt[0] # != 'str16' is more common, so optimize for that
            if fmt_str == 'str16':
                setter(attr, _read_vmad_str16(ins, read_id))
            else:
                setter(attr, ins.unpack(fmt_str, fmt[1], read_id)[0])

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
        return [x for x in self.__class__.processors.iterkeys()]

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
    flags_attr = 'fragment_flags'
    flags_mapper = None
    flags_to_children = OrderedDict()
    child_loader = None

    def load_data(self, record, ins, vmad_version, obj_format, read_id):
        # Load the regular attributes first
        super(_AFixedContainer, self).load_data(
            record, ins, vmad_version, obj_format, read_id)
        # Then, process the flags and decode them
        child_flags = self.__class__.flags_mapper(
            getattr(record, self.__class__.flags_attr))
        setattr(record, self.__class__.flags_attr, child_flags)
        # Finally, inspect the flags and load the appropriate children. We must
        # always load and dump these in the exact order specified by the
        # subclass!
        is_flag_set = child_flags.__getattr__
        set_child = record.__setattr__
        new_child = self.child_loader.make_new
        load_child = self.child_loader.load_data
        for flag_attr, child_attr in \
                self.__class__.flags_to_children.iteritems():
            if is_flag_set(flag_attr):
                child = new_child()
                load_child(child, ins, vmad_version, obj_format, read_id)
                set_child(child_attr, child)
            else:
                set_child(child_attr, None)

    def dump_data(self, record):
        # Update the flags first, then dump the regular attributes
        # Also use this chance to store the value of each present child
        children = []
        get_child = record.__getattribute__
        child_flags = getattr(record, self.__class__.flags_attr)
        set_flag = child_flags.__setattr__
        store_child = children.append
        for flag_attr, child_attr in \
                self.__class__.flags_to_children.iteritems():
            child = get_child(child_attr)
            if child is not None:
                store_child(child)
                set_flag(True)
            else:
                # No need to store children we won't be writing out
                set_flag(False)
        out_data = super(_AFixedContainer, self).dump_data(record)
        # Then, dump each child for which the flag is now set, in order
        dump_child = self.child_loader.dump_data
        for child in children:
            out_data += dump_child(child)
        return out_data

    @property
    def used_slots(self):
        return self.__class__.flags_to_children.values() + super(
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
    children_attr = 'fragments'
    counter_attr = 'fragment_count'

    def load_data(self, record, ins, vmad_version, obj_format, read_id):
        # Load the regular attributes first
        super(_AVariableContainer, self).load_data(
            record, ins, vmad_version, obj_format, read_id)
        # Then, load each child
        children = []
        new_child = self.child_loader.make_new
        load_child = self.child_loader.load_data
        append_child = children.append
        for x in xrange(getattr(record, self.__class__.counter_attr)):
            child = new_child()
            load_child(child, ins, vmad_version, obj_format, read_id)
            append_child(child)
        setattr(record, self.__class__.children_attr, children)

    def dump_data(self, record):
        # Update the child count, then dump the
        children = getattr(record, self.__class__.children_attr)
        setattr(record, self.__class__.counter_attr, len(children))
        out_data = super(_AVariableContainer, self).dump_data(record)
        # Then, dump each child
        dump_child = self.child_loader.dump_data
        for child in children:
            out_data += dump_child(child)
        return out_data

    def map_fids(self, record, map_function, save=False):
        map_child = self.child_loader.map_fids
        for child in getattr(record, self.__class__.children_attr):
            map_child(child, map_function, save)

    @property
    def used_slots(self):
        return [self.__class__.children_attr] + super(
            _AVariableContainer, self).used_slots

class ObjectRef(object):
    """An object ref is a FormID and an AliasID. Using a class instead of
    namedtuple for two reasons: lower memory usage (due to __slots__) and
    easier usage/access in the patchers."""
    __slots__ = ('aid', 'fid')

    def __init__(self, aid, fid):
        self.aid = aid # The AliasID
        self.fid = fid # The FormID

    def dump_out(self):
        """Returns the dumped version of this ObjectRef, ready for writing onto
        an output stream."""
        # Write only object format v2
        return struct_pack('=HhI', 0, self.aid, self.fid)

    def map_fids(self, map_function, save=False):
        """Maps the specified function onto this ObjectRef's fid. If save is
        True, the result is stored, otherwise it is discarded."""
        result = map_function(self.fid)
        if save: self.fid = result

    def __repr__(self):
        return u'ObjectRef<%s, %s>' % (self.aid, self.fid)

    # Static helper methods
    @classmethod
    def array_from_file(cls, ins, obj_format, read_id):
        """Reads an array of ObjectRefs directly from the specified input
        stream. Needs the current object format and a read ID as well."""
        make_ref = cls.from_file
        return [make_ref(ins, obj_format, read_id) for _x in
                xrange(ins.unpack('I', 4, read_id)[0])]

    @staticmethod
    def dump_array(target_list):
        """Returns the dumped version of the specified list of ObjectRefs,
        ready for writing onto an output stream. This includes a leading 32-bit
        integer denoting the size."""
        out_data = struct_pack('=I', len(target_list))
        for obj_ref in target_list: # type: ObjectRef
            out_data += obj_ref.dump_out()
        return out_data

    @classmethod
    def from_file(cls, ins, obj_format, read_id):
        """Reads an ObjectRef directly from the specified input stream. Needs
        the current object format and a read ID as well."""
        if obj_format == 1: # object format v1 - fid, aid, unused
            fid, aid, _unused = ins.unpack('IhH', 8, read_id)
        else: # object format v2 - unused, aid, fid
            _unused, aid, fid = ins.unpack('HhI', 8, read_id)
        return cls(aid, fid)

# Implementation --------------------------------------------------------------
class MelVmad(MelBase):
    """Virtual Machine Adapter. Forms the bridge between the Papyrus scripting
    system and the record definitions. A very complex subrecord that requires
    careful loading and dumping. The following is split into several sections,
    detailing fragments, fragment headers, properties, scripts and aliases.

    Note that this code is somewhat heavily optimized for performance, so
    expect lots of inlines and other non-standard or ugly code.

    :type _handler_map: dict[str, type|_AVmadComponent]"""
    # Fragments ---------------------------------------------------------------
    class FragmentBasic(_AVmadComponent):
        """Implements the following fragments:

            - SCEN OnBegin/OnEnd fragments
            - PACK fragments
            - INFO fragments"""
        processors = OrderedDict([
            ('unknown1',      ('b', 1)),
            ('script_name',   ('str16',)),
            ('fragment_name', ('str16',)),
        ])

    class FragmentPERK(_AVmadComponent):
        """Implements PERK fragments."""
        processors = OrderedDict([
            ('fragment_index', ('H', 2)),
            ('unknown1',       ('h', 2)),
            ('unknown2',       ('b', 1)),
            ('script_name',    ('str16',)),
            ('fragment_name',  ('str16',)),
        ])

    class FragmentQUST(_AVmadComponent):
        """Implements QUST fragments."""
        processors = OrderedDict([
            ('quest_stage',       ('H', 2)),
            ('unknown1',          ('h', 2)),
            ('quest_stage_index', ('I', 4)),
            ('unknown2',          ('b', 1)),
            ('script_name',       ('str16',)),
            ('fragment_name',     ('str16',)),
        ])

    class FragmentSCENPhase(_AVmadComponent):
        """Implements SCEN phase fragments."""
        processors = OrderedDict([
            ('fragment_flags', ('B', 1)),
            ('phase_index',    ('B', 1)),
            ('unknown1',       ('h', 2)),
            ('unknown2',       ('b', 1)),
            ('unknown3',       ('b', 1)),
            ('script_name',    ('str16',)),
            ('fragment_name',  ('str16',)),
        ])
        _scen_fragment_phase_flags = Flags(0L, Flags.getNames(
            (0, 'on_start'),
            (1, 'on_completion'),
        ))

        def load_data(self, record, ins, vmad_version, obj_format, read_id):
            super(MelVmad.FragmentSCENPhase, self).load_data(
                record, ins, vmad_version, obj_format, read_id)
            # Turn the read byte into flags for easier runtime usage
            record.fragment_phase_flags = self._scen_fragment_phase_flags(
                record.fragment_phase_flags)

    # Fragment Headers --------------------------------------------------------
    class VmadHandlerINFO(_AFixedContainer):
        """Implements special VMAD handling for INFO records."""
        processors = OrderedDict([
            ('unkown1',        ('b', 1)),
            ('fragment_flags', ('B', 1)), # Updated before writing
            ('file_name',      ('str16',)),
        ])
        flags_mapper = Flags(0L, Flags.getNames(
            (0, 'on_begin'),
            (1, 'on_end'),
        ))
        flags_to_children = OrderedDict([
            ('on_begin', 'begin_frag'),
            ('on_end',   'end_frag'),
        ])

        def __init__(self):
            super(MelVmad.VmadHandlerINFO, self).__init__()
            self.child_loader = MelVmad.FragmentBasic()

    class VmadHandlerPACK(_AFixedContainer):
        """Implements special VMAD handling for PACK records."""
        processors = OrderedDict([
            ('unkown1',        ('b', 1)),
            ('fragment_flags', ('B', 1)), # Updated before writing
            ('file_name',      ('str16',)),
        ])
        flags_mapper = Flags(0L, Flags.getNames(
            (0, 'on_begin'),
            (1, 'on_end'),
            (2, 'on_change'),
        ))
        flags_to_children = OrderedDict([
            ('on_begin',  'begin_frag'),
            ('on_end',    'end_frag'),
            ('on_change', 'change_frag'),
        ])

        def __init__(self):
            super(MelVmad.VmadHandlerPACK, self).__init__()
            self.child_loader = MelVmad.FragmentBasic()

    class VmadHandlerPERK(_AVariableContainer):
        """Implements special VMAD handling for PERK records."""
        processors = OrderedDict([
            ('unknown1', ('b', 1)),
            ('file_name', ('str16',)),
            ('fragment_count', ('H', 2)), # Updated before writing
        ])

        def __init__(self):
            super(MelVmad.VmadHandlerPERK, self).__init__()
            self.child_loader = MelVmad.FragmentPERK()

    class VmadHandlerQUST(_AVariableContainer):
        """Implements special VMAD handling for QUST records."""
        processors = OrderedDict([
            ('unknown1', ('b', 1)),
            ('fragment_count', ('H', 2)),
            ('file_name', ('str16',)),
        ])

        def __init__(self):
            super(MelVmad.VmadHandlerQUST, self).__init__()
            self.child_loader = MelVmad.FragmentQUST()
            self._alias_loader = MelVmad.Alias()

        def load_data(self, record, ins, vmad_version, obj_format, read_id):
            # Load the regular fragments first
            super(MelVmad.VmadHandlerQUST, self).load_data(
                record, ins, vmad_version, obj_format, read_id)
            # Then, load each alias
            record.aliases = []
            new_alias = self._alias_loader.make_new
            load_alias = self._alias_loader.load_data
            append_alias = record.aliases.append
            for x in xrange(ins.unpack('H', 2, read_id)[0]):
                alias = new_alias()
                load_alias(alias, ins, vmad_version, obj_format, read_id)
                append_alias(alias)

        def dump_data(self, record):
            # Dump the regular fragments first
            out_data = super(MelVmad.VmadHandlerQUST, self).dump_data(record)
            # Then, dump each alias
            out_data += struct_pack('=H', len(record.aliases))
            dump_alias = self._alias_loader.dump_data
            for alias in record.aliases:
                out_data += dump_alias(alias)
            return out_data

        def map_fids(self, record, map_function, save=False):
            # No need to call parent, QUST fragments can't contain fids
            map_alias = self._alias_loader.map_fids
            for alias in record.aliases:
                map_alias(alias, map_function, save)

        @property
        def used_slots(self):
            return ['aliases'] + super(
                MelVmad.VmadHandlerQUST, self).used_slots

    ##: Identical to VmadHandlerINFO + some overrides
    class VmadHandlerSCEN(_AFixedContainer):
        """Implements special VMAD handling for SCEN records."""
        processors = OrderedDict([
            ('unkown1',        ('b', 1)),
            ('fragment_flags', ('B', 1)), # Updated before writing
            ('file_name',      ('str16',)),
        ])
        flags_mapper = Flags(0L, Flags.getNames(
            (0, 'on_begin'),
            (1, 'on_end'),
        ))
        flags_to_children = OrderedDict([
            ('on_begin', 'begin_frag'),
            ('on_end',   'end_frag'),
        ])

        def __init__(self):
            super(MelVmad.VmadHandlerSCEN, self).__init__()
            self.child_loader = MelVmad.FragmentBasic()
            self._phase_loader = MelVmad.FragmentSCENPhase()

        def load_data(self, record, ins, vmad_version, obj_format, read_id):
            # First, load the regular attributes and fragments
            super(MelVmad.VmadHandlerSCEN, self).load_data(
                record, ins, vmad_version, obj_format, read_id)
            # Then, load each phase fragment
            record.phase_fragments = []
            frag_count, = ins.unpack('H', 2, read_id)
            new_fragment = self._phase_loader.make_new
            load_fragment = self._phase_loader.load_data
            append_fragment = record.phase_fragments.append
            for x in xrange(frag_count):
                phase_fragment = new_fragment()
                load_fragment(phase_fragment, ins, vmad_version, obj_format,
                              read_id)
                append_fragment(phase_fragment)

        def dump_data(self, record):
            # First, dump the regular attributes and fragments
            out_data = super(MelVmad.VmadHandlerSCEN, self).dump_data(record)
            # Then, dump each phase fragment
            phase_frags = record.phase_fragments
            out_data += struct_pack('=H', len(phase_frags))
            dump_fragment = self._phase_loader.dump_data
            for phase_fragment in phase_frags:
                out_data += dump_fragment(phase_fragment)
            return out_data

        @property
        def used_slots(self):
            return ['phase_fragments'] + super(
                MelVmad.VmadHandlerSCEN, self).used_slots

    # Scripts -----------------------------------------------------------------
    class Script(_AVariableContainer):
        """Represents a single script."""
        children_attr = 'properties'
        counter_attr = 'property_count'
        processors = OrderedDict([
            ('script_name',    ('str16',)),
            ('script_flags',   ('B', 1)),
            ('property_count', ('H', 2)),
        ])
        _script_status_flags = Flags(0L, Flags.getNames(
            # actually an enum, 0x0 means 'local'
            (0, 'inherited'),
            (1, 'removed'),
        ))

        def __init__(self):
            super(MelVmad.Script, self).__init__()
            self.child_loader = MelVmad.Property()

        def load_data(self, record, ins, vmad_version, obj_format, read_id):
            # Load the data, then process the flags
            super(MelVmad.Script, self).load_data(
                record, ins, vmad_version, obj_format, read_id)
            record.script_flags = self._script_status_flags(
                record.script_flags)

    # Properties --------------------------------------------------------------
    class Property(_AVmadComponent):
        """Represents a single script property."""
        # Processors for VMAD >= v4
        _new_processors = OrderedDict([
            ('prop_name', ('str16',)),
            ('prop_type', ('B', 1)),
            ('prop_flags', ('B', 1)),
        ])
        # Processors for VMAD <= v3
        _old_processors = OrderedDict([
            ('prop_name', ('str16',)),
            ('prop_type', ('B', 1)),
        ])
        _property_status_flags = Flags(0L, Flags.getNames(
            (0, 'edited'),
            (1, 'removed'),
        ))

        def load_data(self, record, ins, vmad_version, obj_format, read_id):
            # Load the three regular attributes first - need to check version
            if vmad_version >= 4:
                MelVmad.Property.processors = MelVmad.Property._new_processors
            else:
                MelVmad.Property.processors = MelVmad.Property._old_processors
                record.prop_flags = 1
            super(MelVmad.Property, self).load_data(
                record, ins, vmad_version, obj_format, read_id)
            record.prop_flags = self._property_status_flags(
                record.prop_flags)
            # Then, read the data in the format corresponding to the
            # property_type we just read - warning, some of these look *very*
            # unusual; these are the fastest implementations, at least on py2.
            # In particular, '!= 0' is faster than 'bool()', '[x for x in a]'
            # is slightly faster than 'list(a)' and "repr(c) + 'f'" is faster
            # than "'%uf' % c" or "str(c) + 'f'".
            property_type = record.prop_type
            if property_type == 0: # null
                record.prop_data = None
            elif property_type == 1: # object
                record.prop_data = ObjectRef.from_file(ins, obj_format, read_id)
            elif property_type == 2: # string
                record.prop_data = _read_vmad_str16(ins, read_id)
            elif property_type == 3: # sint32
                record.prop_data, = ins.unpack('i', 4, read_id)
            elif property_type == 4: # float
                record.prop_data, = ins.unpack('f', 4, read_id)
            elif property_type == 5: # bool (stored as uint8)
                # Faster than bool() and other, similar checks
                record.prop_data = ins.unpack('B', 1, read_id) != (0,)
            elif property_type == 11: # object array
                record.prop_data = ObjectRef.array_from_file(ins, obj_format,
                                                             read_id)
            elif property_type == 12: # string array
                record.prop_data = [_read_vmad_str16(ins, read_id) for _x in
                                    xrange(ins.unpack('I', 4, read_id)[0])]
            elif property_type == 13: # sint32 array
                array_len, = ins.unpack('I', 4, read_id)
                # Do *not* change without extensive benchmarking! This is
                # faster than all alternatives, at least on py2.
                record.prop_data = [x for x in ins.unpack(
                    repr(array_len) + 'i', array_len * 4, read_id)]
            elif property_type == 14: # float array
                array_len, = ins.unpack('I', 4, read_id)
                # Do *not* change without extensive benchmarking! This is
                # faster than all alternatives, at least on py2.
                record.prop_data = [x for x in ins.unpack(
                    repr(array_len) + 'f', array_len * 4, read_id)]
            elif property_type == 15: # bool array (stored as uint8 array)
                array_len, = ins.unpack('I', 4, read_id)
                # Do *not* change without extensive benchmarking! This is
                # faster than all alternatives, at least on py2.
                record.prop_data = [x != 0 for x in ins.unpack(
                    repr(array_len) + 'B', array_len, read_id)]
            else:
                raise ModError(ins.inName, u'Unrecognized VMAD property type: '
                                           u'%u' % property_type)

        def dump_data(self, record):
            # Dump the three regular attributes first - note that we only write
            # out VMAD with version of 5 and object format 2, so make sure we
            # use new_processors here
            MelVmad.Property.processors = MelVmad.Property._new_processors
            out_data = super(MelVmad.Property, self).dump_data(record)
            # Then, dump out the data corresponding to the property type
            # See load_data for warnings and explanations about the code style
            property_data = record.prop_data
            property_type = record.prop_type
            if property_type == 0: # null
                return out_data
            elif property_type == 1: # object
                return out_data + property_data.dump_out()
            elif property_type == 2: # string
                return out_data + _dump_vmad_str16(property_data)
            elif property_type == 3: # sint32
                return out_data + struct_pack('=i', property_data)
            elif property_type == 4: # float
                return out_data + struct_pack('=f', property_data)
            elif property_type == 5: # bool (stored as uint8)
                # Faster than int(record.prop_data)
                return out_data + struct_pack('=b', 1 if property_data else 0)
            elif property_type == 11: # object array
                return out_data + ObjectRef.dump_array(property_data)
            elif property_type == 12: # string array
                out_data += struct_pack('=H', len(property_data))
                return out_data + ''.join(_dump_vmad_str16(x) for x in
                                          property_data)
            elif property_type == 13: # sint32 array
                array_len = len(property_data)
                out_data += struct_pack('=H', array_len)
                return out_data + struct_pack(
                    '=' + repr(array_len) + 'i', *property_data)
            elif property_type == 14: # float array
                array_len = len(property_data)
                out_data += struct_pack('=H', array_len)
                return out_data + struct_pack(
                    '=' + repr(array_len) + 'f', *property_data)
            elif property_type == 15: # bool array (stored as uint8 array)
                array_len = len(property_data)
                out_data += struct_pack('=H', array_len)
                # Faster than [int(x) for x in property_data]
                return out_data + struct_pack(
                    '=' + repr(array_len) + 'B', *[x != 0 for x
                                                   in property_data])
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
            return ['prop_data'] + super(MelVmad.Property, self).used_slots

    # Aliases -----------------------------------------------------------------
    class Alias(_AVariableContainer):
        """Represents a single alias."""
        # Can't use any processors when loading - see below
        _load_processors = OrderedDict()
        _dump_processors = OrderedDict([
            ('alias_vmad_version', ('h', 2)),
            ('alias_obj_format', ('h', 2)),
            ('script_count', ('H', 2)),
        ])
        children_attr = 'scripts'
        counter_attr = 'script_count'

        def __init__(self):
            super(MelVmad.Alias, self).__init__()
            self.child_loader = MelVmad.Script()

        def load_data(self, record, ins, vmad_version, obj_format, read_id):
            MelVmad.Alias.processors = MelVmad.Alias._load_processors
            # Aliases start with an ObjectRef, skip that for now and unpack
            # the three regular attributes. We need to do this, since one of
            # the attributes is alias_obj_format, which tells us how to unpack
            # the ObjectRef at the start.
            ins.seek(8, 1, read_id)
            record.alias_vmad_version, = ins.unpack('h', 2, read_id)
            record.alias_obj_format, = ins.unpack('h', 2, read_id)
            record.script_count, = ins.unpack('H', 2, read_id)
            # Change our active VMAD version and object format to the ones we
            # read from this alias
            vmad_version = record.alias_vmad_version
            obj_format = record.alias_obj_format
            # Now we can go back and unpack the ObjectRef - note us passing the
            # (potentially) modified object format
            ins.seek(-14, 1, read_id)
            record.alias_ref_obj = ObjectRef.from_file(ins, obj_format,
                                                       read_id)
            # Skip back over the three attributes we read at the start
            ins.seek(6, 1, read_id)
            # Finally, load the scripts attached to this alias - again, note
            # the (potentially) changed VMAD version and object format
            super(MelVmad.Alias, self).load_data(
                record, ins, vmad_version, obj_format, read_id)

        def dump_data(self, record):
            MelVmad.Alias.processors = MelVmad.Alias._dump_processors
            # Dump out the ObjectRef first and make sure we dump out VMAD v5
            # and object format v2, then we can fall back on our parent's
            # dump_data implementation
            out_data = record.alias_ref_obj.dump_out()
            record.alias_vmad_version, record.alias_obj_format = 5, 2
            return out_data + super(MelVmad.Alias, self).dump_data(record)

        def map_fids(self, record, map_function, save=False):
            record.alias_ref_obj.map_fids(map_function, save)
            super(MelVmad.Alias, self).map_fids(record, map_function, save)

        @property
        def used_slots(self):
            # Manually implemented to avoid depending on self.processors, which
            # may be either _load_processors or _dump_processors right now
            return ['alias_ref_obj', 'alias_vmad_version', 'alias_obj_format',
                    'script_count', 'scripts']

    # Subrecord Implementation ------------------------------------------------
    _handler_map = {
        'INFO': VmadHandlerINFO,
        'PACK': VmadHandlerPACK,
        'PERK': VmadHandlerPERK,
        'QUST': VmadHandlerQUST,
        'SCEN': VmadHandlerSCEN,
    }

    def __init__(self):
        MelBase.__init__(self, 'VMAD', 'vmdata')
        self._script_loader = self.Script()
        self._vmad_class = None

    def _get_special_handler(self, rec_sig):
        """Internal helper method for instantiating / retrieving a VMAD handler
        instance.

        :param rec_sig: The signature of the record type in question.
        :type rec_sig: str
        :rtype: _AVmadComponent"""
        special_handler = self._handler_map[rec_sig]
        if type(special_handler) == type:
            # These initializations need to be delayed, since they require
            # MelVmad to be fully initialized first, so do this JIT
            self._handler_map[rec_sig] = special_handler = special_handler()
        return special_handler

    def loadData(self, record, ins, sub_type, size_, readId):
        # Remember where this VMAD subrecord ends
        end_of_vmad = ins.tell() + size_
        if self._vmad_class is None:
            class _MelVmadImpl(MelObject):
                __slots__ = ('scripts', 'special_data')
            self._vmad_class = _MelVmadImpl # create only once
        record.vmdata = vmad = self._vmad_class()
        # Begin by unpacking the VMAD header and doing some error checking
        vmad_version, obj_format, script_count = ins.unpack('=hhH', 6, readId)
        if vmad_version < 1 or vmad_version > 5:
            raise ModError(ins.inName, u'Unrecognized VMAD version: %u' %
                           vmad_version)
        if obj_format not in (1, 2):
            raise ModError(ins.inName, u'Unrecognized VMAD object format: %u' %
                           obj_format)
        # Next, load any scripts that may be present
        vmad.scripts = []
        new_script = self._script_loader.make_new
        load_script = self._script_loader.load_data
        append_script = vmad.scripts.append
        for i in xrange(script_count):
            script = new_script()
            load_script(script, ins, vmad_version, obj_format, readId)
            append_script(script)
        # If the record type is one of the ones that need special handling and
        # we still have something to read, call the appropriate handler
        if record.recType in self._handler_map and ins.tell() < end_of_vmad:
            special_handler = self._get_special_handler(record.recType)
            vmad.special_data = special_handler.make_new()
            special_handler.load_data(vmad.special_data, ins, vmad_version,
                                      obj_format, readId)
        else:
            vmad.special_data = None

    def dumpData(self, record, out):
        vmad = record.__getattribute__(self.attr)
        if vmad is None: return
        # Start by dumping out the VMAD header - we read all VMAD versions and
        # object formats, but only dump out VMAD v5 and object format v2
        out_data = struct_pack('=hh', 5, 2)
        # Next, dump out all attached scripts
        out_data += struct_pack('=H', len(vmad.scripts))
        dump_script = self._script_loader.dump_data
        for script in vmad.scripts:
            out_data += dump_script(script)
        # If the subrecord has special data attached, ask the appropriate
        # handler to dump that out
        if vmad.special_data and record.recType in self._handler_map:
            out_data += self._get_special_handler(record.recType).dump_data(
                vmad.special_data)
        # Finally, write out the subrecord header, followed by the dumped data
        out.packSub(self.subType, out_data)

    def hasFids(self, formElements):
        # Unconditionally add ourselves - see comment above
        # _AVmadComponent.map_fids for more information
        formElements.add(self)

    def mapFids(self, record, function, save=False):
        vmad = record.__getattribute__(self.attr)
        if vmad is None: return
        map_script = self._script_loader.map_fids
        for script in vmad.scripts:
            map_script(script, function, save)
        if vmad.special_data and record.recType in self._handler_map:
            self._get_special_handler(record.recType).map_fids(
                vmad.special_data, function, save)

#------------------------------------------------------------------------------
# Skyrim Records --------------------------------------------------------------
#------------------------------------------------------------------------------
class MreHeader(MreHeaderBase):
    """TES4 Record.  File header."""
    classType = 'TES4'

    melSet = MelSet(
        MelStruct('HEDR', 'f2I', ('version', 1.7), 'numRecords',
                  ('nextObject', 0x800)),
        MelUnicode('CNAM','author',u'',512),
        MelUnicode('SNAM','description',u'',512),
        MreHeaderBase.MelMasterName('MAST','masters'),
        MelNull('DATA'), # 8 Bytes in Length
        MelFidList('ONAM','overrides',),
        MelBase('SCRN', 'screenshot'),
        MelBase('INTV', 'unknownINTV'),
        MelBase('INCC', 'unknownINCC'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAact(MelRecord):
    """Action."""
    classType = 'AACT'
    melSet = MelSet(
        MelEdid(),
        MelColorO('CNAM'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAchr(MelRecord):
    """Placed NPC."""
    classType = 'ACHR'
    _flags = Flags(0L,Flags.getNames('oppositeParent','popIn'))

    ActivateParentsFlags = Flags(0L,Flags.getNames(
            (0, 'parentActivateOnly'),
        ))

    # TODO class MelAchrPdto: if 'type' in PDTO is equal to 1 then 'data' is
    #  '4s', not FID

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelFid('NAME','base'),
        MelFid('XEZN','encounterZone'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelGroup('patrolData',
            MelFloat('XPRD', 'idleTime',),
            MelNull('XPPA'),
            MelFid('INAM','idle'),
            MelGroup('patrolData',
                MelBase('SCHR','schr_p'),
                MelBase('SCDA','scda_p'),
                MelBase('SCTX','sctx_p'),
                MelBase('QNAM','qnam_p'),
                MelBase('SCRO','scro_p'),
            ),
            MelGroups('topicData',
                MelStruct('PDTO', '2I', 'type', (FID, 'data')),
            ),
            MelFid('TNAM','topic'),
        ),
        MelSInt32('XLCM', 'levelModifier'),
        MelFid('XMRC','merchantContainer',),
        MelSInt32('XCNT', 'count'),
        MelFloat('XRDS', 'radius',),
        MelFloat('XHLP', 'health',),
        MelGroup('linkedReferences',
            MelSortedFidList('XLKR', 'fids'),
        ),
        MelGroup('activateParents',
            MelUInt32('XAPD', (ActivateParentsFlags, 'flags', 0L)),
            MelGroups('activateParentRefs',
                MelStruct('XAPR','If',(FID,'reference'),'delay',),
            ),
        ),
        MelStruct('XCLP','3Bs3Bs','startColorRed','startColorGreen','startColorBlue',
                  'startColorUnknown','endColorRed','endColorGreen','endColorBlue',
                  'endColorUnknown',),
        MelFid('XLCN','persistentLocation',),
        MelFid('XLRL','locationReference',),
        MelNull('XIS2'),
        MelFidList('XLRT','locationRefType',),
        MelFid('XHOR','horse',),
        MelFloat('XHTW', 'headTrackingWeight',),
        MelFloat('XFVC', 'favorCost',),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_flags,'parentFlags'),'unused',),
        MelOwnership(),
        MelOptFid('XEMI', 'emittance'),
        MelFid('XMBR','multiBoundReference',),
        MelNull('XIBS'),
        MelOptFloat('XSCL', ('scale', 1.0)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreActi(MelRecord):
    """Activator."""
    classType = 'ACTI'

    ActivatorFlags = Flags(0L,Flags.getNames(
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
        MelColor('PNAM'),
        MelOptFid('SNAM', 'dropSound'),
        MelOptFid('VNAM', 'pickupSound'),
        MelOptFid('WNAM', 'water'),
        MelLString('RNAM', 'activate_text_override'),
        MelOptUInt16('FNAM', (ActivatorFlags, 'flags', 0L)),
        MelOptFid('KNAM', 'keyword'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAddn(MelRecord):
    """Addon Node."""
    classType = 'ADDN'

    _AddnFlags = Flags(0L, Flags.getNames(
        (1, 'alwaysLoaded'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelSInt32('DATA', 'node_index'),
        MelOptFid('SNAM', 'ambientSound'),
        MelStruct('DNAM', '2H', 'master_particle_system_cap',
                  (_AddnFlags, 'addon_flags')),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAlch(MelRecord,MreHasEffects):
    """Ingestible."""
    classType = 'ALCH'

    IngestibleFlags = Flags(0L,Flags.getNames(
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
        MelLString('DESC','description'),
        MelModel(),
        MelDestructible(),
        MelIcons(),
        MelOptFid('YNAM', 'pickupSound'),
        MelOptFid('ZNAM', 'dropSound'),
        MelOptFid('ETYP', 'equipType'),
        MelFloat('DATA', 'weight'),
        MelStruct('ENIT','i2IfI','value',(IngestibleFlags,'flags',0L),
                  'addiction','addictionChance','soundConsume',),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAmmo(MelRecord):
    """Ammunition."""
    classType = 'AMMO'

    AmmoTypeFlags = Flags(0L,Flags.getNames(
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
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelLString('DESC','description'),
        MelKeywords(),
        MelStruct('DATA','IIfI',(FID,'projectile'),(AmmoTypeFlags,'flags',0L),'damage','value'),
        MelString('ONAM', 'short_name'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAnio(MelRecord):
    """Animated Object."""
    classType = 'ANIO'
    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelString('BNAM', 'unload_event'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAppa(MelRecord):
    """Alchemical Apparatus."""
    classType = 'APPA'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelUInt32('QUAL', 'quality'),
        MelLString('DESC','description'),
        MelStruct('DATA','If','value','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArma(MelRecord):
    """Armor Addon."""
    classType = 'ARMA'

    WeightSliderFlags = Flags(0L,Flags.getNames(
            (0, 'unknown0'),
            (1, 'enabled'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelBipedObjectData(),
        MelFid('RNAM','race'),
        MelStruct('DNAM','4B2sBsf','malePriority','femalePriority',
                  (WeightSliderFlags,'maleFlags',0L),
                  (WeightSliderFlags,'femaleFlags',0L),
                  'unknown','detectionSoundValue','unknown1','weaponAdjust',),
        MelModel('male_model','MOD2'),
        MelModel('female_model','MOD3'),
        MelModel('male_model_1st','MOD4'),
        MelModel('female_model_1st','MOD5'),
        MelOptFid('NAM0', 'skin0'),
        MelOptFid('NAM1', 'skin1'),
        MelOptFid('NAM2', 'skin2'),
        MelOptFid('NAM3', 'skin3'),
        MelFids('MODL','races'),
        MelOptFid('SNDD', 'footstepSound'),
        MelOptFid('ONAM', 'art_object'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArmo(MelRecord):
    """Armor."""
    classType = 'ARMO'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelOptFid('EITM', 'enchantment'),
        MelOptSInt16('EAMT', 'enchantmentAmount'),
        MelModel('model2','MOD2'),
        MelIcons('maleIconPath', 'maleSmallIconPath'),
        MelModel('model4','MOD4'),
        MelIcons2(),
        MelBipedObjectData(),
        MelDestructible(),
        MelOptFid('YNAM', 'pickupSound'),
        MelOptFid('ZNAM', 'dropSound'),
        MelString('BMCT', 'ragdollTemplatePath'), #Ragdoll Constraint Template
        MelOptFid('ETYP', 'equipType'),
        MelOptFid('BIDS', 'bashImpact'),
        MelOptFid('BAMT', 'material'),
        MelOptFid('RNAM', 'race'),
        MelKeywords(),
        MelLString('DESC','description'),
        MelFids('MODL','addons'),
        MelStruct('DATA','=if','value','weight'),
        MelSInt32('DNAM', 'armorRating'),
        MelFid('TNAM','templateArmor'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreArto(MelRecord):
    """Art Effect Object."""
    classType = 'ARTO'

    ArtoTypeFlags = Flags(0L,Flags.getNames(
            (0, 'magic_casting'),
            (1, 'magic_hit_effect'),
            (2, 'enchantment_effect'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelUInt32('DNAM', (ArtoTypeFlags, 'flags', 0L)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAspc(MelRecord):
    """Acoustic Space."""
    classType = 'ASPC'
    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelOptFid('SNAM', 'ambientSound'),
        MelOptFid('RDAT', 'regionData'),
        MelOptFid('BNAM', 'reverb'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAstp(MelRecord):
    """Association Type."""
    classType = 'ASTP'

    AstpTypeFlags = Flags(0L,Flags.getNames('related'))

    melSet = MelSet(
        MelEdid(),
        MelString('MPRT','maleParent'),
        MelString('FPRT','femaleParent'),
        MelString('MCHT','maleChild'),
        MelString('FCHT','femaleChild'),
        MelUInt32('DATA', (AstpTypeFlags, 'flags', 0L)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreAvif(MelRecord):
    """Actor Value Information."""
    classType = 'AVIF'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelLString('DESC','description'),
        MelString('ANAM','abbreviation'),
        MelBase('CNAM','cnam_p'),
        MelOptStruct('AVSK','4f','skillUseMult','skillOffsetMult','skillImproveMult',
                     'skillImproveOffset',),
        MelGroups('perkTree',
            MelFid('PNAM', 'perk',),
            MelBase('FNAM','fnam_p'),
            MelUInt32('XNAM', 'perkGridX'),
            MelUInt32('YNAM', 'perkGridY'),
            MelFloat('HNAM', 'horizontalPosition'),
            MelFloat('VNAM', 'verticalPosition'),
            MelFid('SNAM','associatedSkill',),
            MelGroups('connections',
                MelUInt32('CNAM', 'lineToIndex'),
            ),
            MelUInt32('INAM', 'index',),
        ),
    ).with_distributor({
        'CNAM': 'cnam_p',
        'PNAM': {
            'CNAM': 'perkTree',
        }
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreBook(MelRecord):
    """Book."""
    classType = 'BOOK'

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
        MelLString('DESC','description'),
        MelDestructible(),
        MelOptFid('YNAM', 'pickupSound'),
        MelOptFid('ZNAM', 'dropSound'),
        MelKeywords(),
        MelUnion({
            False: MelStruct('DATA', '2B2siIf',
                             (_book_type_flags, 'book_flags'), 'book_type',
                             ('unused1', null2), 'book_skill', 'value',
                             'weight'),
            True: MelStruct('DATA', '2B2s2If',
                             (_book_type_flags, 'book_flags'), 'book_type',
                             ('unused1', null2), (FID, 'book_spell'), 'value',
                             'weight'),
        }, decider=PartialLoadDecider(
            loader=MelUInt8('DATA', (_book_type_flags, 'book_flags')),
            decider=FlagDecider('book_flags', 'teaches_spell'),
        )),
        MelFid('INAM','inventoryArt'),
        MelLString('CNAM','text'),
    )
    __slots__ = melSet.getSlotsUsed() + ['modb']

#------------------------------------------------------------------------------
class MreBptd(MelRecord):
    """Body Part Data."""
    classType = 'BPTD'

    _flags = Flags(0L,Flags.getNames('severable','ikData','ikBipedData',
        'explodable','ikIsHead','ikHeadtracking','toHitChanceAbsolute'))

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelGroups('bodyParts',
            MelString('BPTN', 'partName'),
            MelString('PNAM','poseMatching'),
            MelString('BPNN', 'nodeName'),
            MelString('BPNT','vatsTarget'),
            MelString('BPNI','ikDataStartNode'),
            MelStruct('BPND','f3Bb2BH2I2fi2I7f2I2B2sf','damageMult',
                      (_flags,'flags'),'partType','healthPercent','actorValue',
                      'toHitChance','explodableChancePercent',
                      'explodableDebrisCount',(FID,'explodableDebris',0L),
                      (FID,'explodableExplosion',0L),'trackingMaxAngle',
                      'explodableDebrisScale','severableDebrisCount',
                      (FID,'severableDebris',0L),(FID,'severableExplosion',0L),
                      'severableDebrisScale','goreEffectPosTransX',
                      'goreEffectPosTransY','goreEffectPosTransZ',
                      'goreEffectPosRotX','goreEffectPosRotY','goreEffectPosRotZ',
                      (FID,'severableImpactDataSet',0L),
                      (FID,'explodableImpactDataSet',0L),'severableDecalCount',
                      'explodableDecalCount',('unused',null2),
                      'limbReplacementScale'),
            MelString('NAM1','limbReplacementModel'),
            MelString('NAM4','goreEffectsTargetBone'),
            # Ignore texture hashes - they're only an optimization, plenty of
            # records in Skyrim.esm are missing them
            MelNull('NAM5'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCams(MelRecord):
    """Camera Shot."""
    classType = 'CAMS'

    CamsFlagsFlags = Flags(0L,Flags.getNames(
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
        MelTruncatedStruct('DATA', '4I7f', 'action', 'location', 'target',
                           (CamsFlagsFlags, 'flags', 0L), 'timeMultPlayer',
                           'timeMultTarget', 'timeMultGlobal', 'maxTime',
                           'minTime', 'targetPctBetweenActors',
                           'nearTargetDistance', old_versions={'4I6f'}),
        MelFid('MNAM','imageSpaceModifier',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCell(MelRecord):
    """Cell."""
    classType = 'CELL'

    CellDataFlags1 = Flags(0L,Flags.getNames(
        (0,'isInterior'),
        (1,'hasWater'),
        (2,'cantFastTravel'),
        (3,'noLODWater'),
        (5,'publicPlace'),
        (6,'handChanged'),
        (7,'showSky'),
        ))

    CellDataFlags2 = Flags(0L,Flags.getNames(
        (0,'useSkyLighting'),
        ))

    CellInheritedFlags = Flags(0L,Flags.getNames(
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

    # 'Force Hide Land' flags
    CellFHLFlags = Flags(0L,Flags.getNames(
            (0, 'quad1'),
            (1, 'quad2'),
            (2, 'quad3'),
            (3, 'quad4'),
        ))

    class MelWaterHeight(MelOptFloat):
        """XCLW sometimes has $FF7FFFFF and causes invalid floating point."""
        default_heights = {4294953216.0, -2147483648.0,
            -3.4028234663852886e+38, 3.4028234663852886e+38} # unused, see #302

        def __init__(self):
            MelOptFloat.__init__(self, 'XCLW', ('waterHeight', -2147483649))

        def loadData(self, record, ins, sub_type, size_, readId):
            # from brec.MelStruct#loadData - formatLen is 0 for MelWaterHeight
            waterHeight = ins.unpack(self.format, size_, readId)
            if not record.flags.isInterior: # drop interior cells for Skyrim
                attr,value = self.attrs[0],waterHeight[0]
                # if value in __default_heights:
                #     value = 3.4028234663852886e+38 # normalize values
                record.__setattr__(attr, value)

        def dumpData(self,record,out):
            if not record.flags.isInterior:
                MelOptFloat.dumpData(self, record, out)

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelTruncatedStruct('DATA', '2B', (CellDataFlags1, 'flags', 0L),
                           (CellDataFlags2, 'skyFlags', 0L),
                           old_versions={'B'}),
        MelOptStruct('XCLC','2iI',('posX', 0),('posY', 0),(CellFHLFlags,'fhlFlags',0L),),
        MelTruncatedStruct(
            'XCLL', '3Bs3Bs3Bs2f2i3f3Bs3Bs3Bs3Bs3Bs3Bs3Bsf3Bs3fI',
            'ambientRed', 'ambientGreen', 'ambientBlue', ('unused1', null1),
            'directionalRed', 'directionalGreen', 'directionalBlue',
            ('unused2', null1), 'fogRed', 'fogGreen', 'fogBlue',
            ('unused3', null1), 'fogNear', 'fogFar', 'directionalXY',
            'directionalZ', 'directionalFade', 'fogClip', 'fogPower',
            'redXplus', 'greenXplus', 'blueXplus', ('unknownXplus', null1),
            'redXminus', 'greenXminus', 'blueXminus', ('unknownXminus', null1),
            'redYplus', 'greenYplus', 'blueYplus', ('unknownYplus', null1),
            'redYminus', 'greenYminus', 'blueYminus', ('unknownYminus', null1),
            'redZplus', 'greenZplus', 'blueZplus', ('unknownZplus', null1),
            'redZminus', 'greenZminus', 'blueZminus', ('unknownZminus', null1),
            'redSpec', 'greenSpec', 'blueSpec', ('unknownSpec', null1),
            'fresnelPower', 'fogColorFarRed', 'fogColorFarGreen',
            'fogColorFarBlue', ('unused4', null1), 'fogMax', 'lightFadeBegin',
            'lightFadeEnd', (CellInheritedFlags, 'inherits', 0L),
            is_optional=True, old_versions={
                '3Bs3Bs3Bs2f2i3f3Bs3Bs3Bs3Bs3Bs3Bs', '3Bs3Bs3Bs2fi'}),
        MelBase('TVDT','occlusionData'),
        # Decoded in xEdit, but properly reading it is relatively slow - see
        # 'Simple Records' option in xEdit - so we skip that for now
        MelBase('MHDT','maxHeightData'),
        MelFid('LTMP','lightTemplate',),
        # leftover flags, they are now in XCLC
        MelBase('LNAM','unknown_LNAM'),
        MelWaterHeight(),
        MelString('XNAM','waterNoiseTexture'),
        MelFidList('XCLR','regions'),
        MelFid('XLCN','location',),
        MelBase('XWCN','unknown_XWCN'), # leftover
        MelBase('XWCS','unknown_XWCS'), # leftover
        MelOptStruct('XWCU', '3f4s3f', ('xOffset', 0.0), ('yOffset', 0.0),
                     ('zOffset', 0.0), ('unk1XWCU', null4), ('xAngle', 0.0),
                     ('yAngle', 0.0), ('zAngle', 0.0), dumpExtra='unk2XWCU',),
        MelFid('XCWT','water'),
        MelOwnership(),
        MelFid('XILL','lockList',),
        MelString('XWEM','waterEnvironmentMap'),
        MelFid('XCCM','climate',), # xEdit calls this 'Sky/Weather From Region'
        MelFid('XCAS','acousticSpace',),
        MelFid('XEZN','encounterZone',),
        MelFid('XCMO','music',),
        MelFid('XCIM','imageSpace',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClas(MelRecord):
    """Class."""
    classType = 'CLAS'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelLString('DESC','description'),
        MelIcons(),
        MelStruct('DATA','4sb19BfI4B','unknown','teaches','maximumtraininglevel',
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
    classType = 'CLFM'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelColorO(),
        MelUInt32('FNAM', 'playable'), # actually a bool, stored as uint32
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreClmt(MelRecord):
    """Climate."""
    classType = 'CLMT'

    melSet = MelSet(
        MelEdid(),
        MelArray('weatherTypes',
            MelStruct('WLST', 'IiI', (FID, 'weather', None), 'chance',
                      (FID, 'global', None)),
        ),
        MelString('FNAM','sunPath',),
        MelString('GNAM','glarePath',),
        MelModel(),
        MelStruct('TNAM','6B','riseBegin','riseEnd','setBegin','setEnd','volatility','phaseLength',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCobj(MelRecord):
    """Constructible Object (Recipes)."""
    classType = 'COBJ'
    isKeyedByEid = True # NULL fids are acceptable

    melSet = MelSet(
        MelEdid(),
        MelItemsCounter(),
        MelItems(),
        MelConditions(),
        MelFid('CNAM','resultingItem'),
        MelFid('BNAM','craftingStation'),
        MelUInt16('NAM1', 'resultingQuantity'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreColl(MelRecord):
    """Collision Layer."""
    classType = 'COLL'

    CollisionLayerFlags = Flags(0L,Flags.getNames(
        (0,'triggerVolume'),
        (1,'sensor'),
        (2,'navmeshObstacle'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelLString('DESC','description'),
        MelUInt32('BNAM', 'layerID'),
        MelColor('FNAM'),
        MelUInt32('GNAM', (CollisionLayerFlags,'flags',0L),),
        MelString('MNAM','name',),
        MelUInt32('INTV', 'interactablesCount'),
        MelFidList('CNAM','collidesWith',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCont(MelRecord):
    """Container."""
    classType = 'CONT'

    ContTypeFlags = Flags(0L,Flags.getNames(
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
        MelStruct('DATA','=Bf',(ContTypeFlags,'flags',0L),'weight'),
        MelFid('SNAM','soundOpen'),
        MelFid('QNAM','soundClose'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCpth(MelRecord):
    """Camera Path"""
    classType = 'CPTH'

    melSet = MelSet(
        MelEdid(),
        MelConditions(),
        MelFidList('ANAM','relatedCameraPaths',),
        MelUInt8('DATA', 'cameraZoom'),
        MelFids('SNAM','cameraShots',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreCsty(MelRecord):
    """Combat Style."""
    classType = 'CSTY'

    CstyTypeFlags = Flags(0L,Flags.getNames(
        (0, 'dueling'),
        (1, 'flanking'),
        (2, 'allowDualWielding'),
    ))

    melSet = MelSet(
        MelEdid(),
        # esm = Equipment Score Mult
        MelStruct('CSGD','10f','offensiveMult','defensiveMult','groupOffensiveMult',
        'esmMelee','esmMagic','esmRanged','esmShout','esmUnarmed','esmStaff',
        'avoidThreatChance',),
        MelBase('CSMD','unknownValue'),
        MelStruct('CSME','8f','atkStaggeredMult','powerAtkStaggeredMult','powerAtkBlockingMult',
        'bashMult','bashRecoilMult','bashAttackMult','bashPowerAtkMult','specialAtkMult',),
        MelStruct('CSCR','4f','circleMult','fallbackMult','flankDistance','stalkTime',),
        MelFloat('CSLR', 'strafeMult'),
        MelStruct('CSFL','8f','hoverChance','diveBombChance','groundAttackChance','hoverTime',
        'groundAttackTime','perchAttackChance','perchAttackTime','flyingAttackChance',),
        MelUInt32('DATA', (CstyTypeFlags, 'flags', 0L)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDebr(MelRecord):
    """Debris."""
    classType = 'DEBR'

    dataFlags = Flags(0L,Flags.getNames('hasCollissionData'))

    class MelDebrData(MelStruct):
        def __init__(self):
            # Format doesn't matter, see {load,dump}Data below
            MelStruct.__init__(self, 'DATA', '', ('percentage', 0),
                               ('modPath', null1), ('flags', 0))

        def loadData(self, record, ins, sub_type, size_, readId):
            """Reads data from ins into record attribute."""
            data = ins.read(size_, readId)
            (record.percentage,) = struct_unpack('B',data[0:1])
            record.modPath = data[1:-2]
            if data[-2] != null1:
                raise ModError(ins.inName,u'Unexpected subrecord: %s' % readId)
            (record.flags,) = struct_unpack('B',data[-1])

        def dumpData(self,record,out):
            """Dumps data from record to outstream."""
            data = ''
            data += struct_pack('B',record.percentage)
            data += record.modPath
            data += null1
            data += struct_pack('B',record.flags)
            out.packSub('DATA',data)

    melSet = MelSet(
        MelEdid(),
        MelGroups('models',
            MelDebrData(),
            MelBase('MODT','modt_p'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDial(brec.MreDial):
    """Dialogue."""

    DialTopicFlags = Flags(0L,Flags.getNames(
        (0, 'doAllBeforeRepeating'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelFloat('PNAM', 'priority',),
        MelFid('BNAM','branch',),
        MelFid('QNAM','quest',),
        MelStruct('DATA','2BH',(DialTopicFlags,'flags_dt',0L),'category',
                  'subtype',),
        # SNAM is a 4 byte string no length byte - TODO(inf) MelFixedString?
        MelStruct('SNAM', '4s', 'subtypeName',),
        ##: Check if this works - if not, move back to method
        MelCounter(MelUInt32('TIFC', 'infoCount'), counts='infos'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDlbr(MelRecord):
    """Dialog Branch."""
    classType = 'DLBR'

    DialogBranchFlags = Flags(0L,Flags.getNames(
        (0,'topLevel'),
        (1,'blocking'),
        (2,'exclusive'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelFid('QNAM','quest',),
        MelUInt32('TNAM', 'unknown'),
        MelUInt32('DNAM', (DialogBranchFlags, 'flags', 0L)),
        MelFid('SNAM','startingTopic',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDlvw(MelRecord):
    """Dialog View"""
    classType = 'DLVW'

    melSet = MelSet(
        MelEdid(),
        MelFid('QNAM','quest',),
        MelFids('BNAM','branches',),
        MelGroups('unknownTNAM',
            MelBase('TNAM','unknown',),
        ),
        MelBase('ENAM','unknownENAM'),
        MelBase('DNAM','unknownDNAM'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDobj(MelRecord):
    """Default Object Manager."""
    classType = 'DOBJ'

    class MelDobjDnam(MelArray):
        """This DNAM can have < 8 bytes of noise at the end, so store those
        in a variable and dump them out again when writing."""
        def __init__(self):
            MelArray.__init__(self, 'objects',
                MelStruct('DNAM', '2I', 'objectUse', (FID, 'objectID')),
            )

        def loadData(self, record, ins, sub_type, size_, readId):
            # Load everything but the noise
            start_pos = ins.tell()
            MelArray.loadData(self, record, ins, sub_type, size_, readId)
            # Now, read the remainder of the subrecord and store it
            read_size = ins.tell() - start_pos
            record.unknownDNAM = ins.read(size_ - read_size)

        def dumpData(self, record, out):
            # We need to fully override this to attach unknownDNAM to the data
            # we'll be writing out
            array_val = getattr(record, self.attr)
            if not array_val: return # don't dump out empty arrays
            array_data = ''
            element_fmt = self._element.format
            # not _element_attrs, that one has all underscores removed
            element_attrs = self._element.attrs
            for arr_entry in array_val:
                array_data += struct_pack(
                    element_fmt, *[getattr(arr_entry, item) for item
                                   in element_attrs])
            out.packSub(self.subType, array_data + record.unknownDNAM)

        def getSlotsUsed(self):
            return MelArray.getSlotsUsed(self) + ('unknownDNAM',)

    melSet = MelSet(
        MelEdid(),
        MelDobjDnam(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDoor(MelRecord):
    """Door."""
    classType = 'DOOR'

    DoorTypeFlags = Flags(0L,Flags.getNames(
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
        MelFid('SNAM','soundOpen'),
        MelFid('ANAM','soundClose'),
        MelFid('BNAM','soundLoop'),
        MelUInt8('FNAM', (DoorTypeFlags, 'flags', 0L)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreDual(MelRecord):
    """Dual Cast Data."""
    classType = 'DUAL'

    DualCastDataFlags = Flags(0L,Flags.getNames(
        (0,'hitEffectArt'),
        (1,'projectile'),
        (2,'explosion'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelStruct('DATA','6I',(FID,'projectile'),(FID,'explosion'),(FID,'effectShader'),
                  (FID,'hitEffectArt'),(FID,'impactDataSet'),(DualCastDataFlags,'flags',0L),),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEczn(MelRecord):
    """Encounter Zone."""
    classType = 'ECZN'

    EcznTypeFlags = Flags(0L,Flags.getNames(
            (0, 'neverResets'),
            (1, 'matchPCBelowMinimumLevel'),
            (2, 'disableCombatBoundary'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct('DATA', '2I2bBb', (FID, 'owner', None),
                           (FID, 'location', None), ('rank', 0),
                           ('minimumLevel', 0), (EcznTypeFlags, 'flags', 0L),
                           ('maxLevel', 0), old_versions={'2I'}),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEfsh(MelRecord):
    """Effect Shader."""
    classType = 'EFSH'

    EfshGeneralFlags = Flags(0L,Flags.getNames(
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
        MelIcon('fillTexture'),
        MelIco2('particleTexture'),
        MelString('NAM7','holesTexture'),
        MelString('NAM8','membranePaletteTexture'),
        MelString('NAM9','particlePaletteTexture'),
        MelTruncatedStruct(
            'DATA', '4s3I3Bs9f3Bs8f5I19f3Bs3Bs3Bs11fI5f3Bsf2I6fI3Bs3Bs9f8I2fI',
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
            'frameCountVariation', (EfshGeneralFlags, 'flags', 0L),
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
class MreEnch(MelRecord,MreHasEffects):
    """Object Effect."""
    classType = 'ENCH'

    EnchGeneralFlags = Flags(0L,Flags.getNames(
        (0, 'noAutoCalc'),
        (1, 'unknownTwo'),
        (2, 'extendDurationOnRecast'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelTruncatedStruct('ENIT', 'i2Ii2If2I', 'enchantmentCost',
                           (EnchGeneralFlags, 'generalFlags', 0L), 'castType',
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
    classType = 'EQUP'
    melSet = MelSet(
        MelEdid(),
        MelFidList('PNAM','canBeEquipped'),
        MelUInt32('DATA', 'useAllParents'), # actually a bool
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreExpl(MelRecord):
    """Explosion."""
    classType = 'EXPL'

    ExplTypeFlags = Flags(0L,Flags.getNames(
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
        MelFid('EITM','objectEffect'),
        MelFid('MNAM','imageSpaceModifier'),
        MelTruncatedStruct(
            'DATA', '6I5f2I', (FID, 'light', None), (FID, 'sound1', None),
            (FID, 'sound2', None), (FID, 'impactDataset', None),
            (FID, 'placedObject', None), (FID, 'spawnProjectile', None),
            'force', 'damage', 'radius', 'isRadius', 'verticalOffsetMult',
            (ExplTypeFlags, 'flags', 0L), 'soundLevel',
            old_versions={'6I5fI', '6I5f', '6I4f'}),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreEyes(MelRecord):
    """Eyes."""
    classType = 'EYES'

    EyesTypeFlags = Flags(0L,Flags.getNames(
            (0, 'playable'),
            (1, 'notMale'),
            (2, 'notFemale'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelIcons(),
        MelUInt8('DATA', (EyesTypeFlags, 'flags', 0L)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFact(MelRecord):
    """Faction."""
    classType = 'FACT'

    FactGeneralTypeFlags = Flags(0L,Flags.getNames(
        (0, 'hiddenFromPC'),
        (1, 'specialCombat'),
        (2, 'unknown3'),
        (3, 'unknown4'),
        (4, 'unknown5'),
        (5, 'unknown6'),
        (6, 'trackCrime'),
        (7, 'ignoreCrimesMurder'),
        (8, 'ignoreCrimesAssult'),
        (9, 'ignoreCrimesStealing'),
        (10, 'ignoreCrimesTrespass'),
        (11, 'doNotReportCrimesAgainstMembers'),
        (12, 'crimeGold-UseDefaults'),
        (13, 'ignoreCrimesPickpocket'),
        (14, 'allowSell'), # vendor
        (15, 'canBeOwner'),
        (16, 'ignoreCrimesWerewolf'),
    ))

#   wbPLVD := wbStruct(PLVD, 'Location', [
#     wbInteger('Type', itS32, wbLocationEnum),
#     wbUnion('Location Value', wbTypeDecider, [
#       {0} wbFormIDCkNoReach('Reference', [NULL, DOOR, PLYR, ACHR, REFR, PGRE, PHZD, PARW, PBAR, PBEA, PCON, PFLA]),
#       {1} wbFormIDCkNoReach('Cell', [NULL, CELL]),
#       {2} wbByteArray('Near Package Start Location', 4, cpIgnore),
#       {3} wbByteArray('Near Editor Location', 4, cpIgnore),
#       {4} wbFormIDCkNoReach('Object ID', [NULL, ACTI, DOOR, STAT, FURN, SPEL, SCRL, NPC_, CONT, ARMO, AMMO, MISC, WEAP, BOOK, KEYM, ALCH, INGR, LIGH, FACT, FLST, IDLM, SHOU]),
#       {5} wbInteger('Object Type', itU32, wbObjectTypeEnum),
#       {6} wbFormIDCk('Keyword', [NULL, KYWD]),
#       {7} wbByteArray('Unknown', 4, cpIgnore),
#       {8} wbInteger('Alias ID', itU32),
#       {9} wbFormIDCkNoReach('Reference', [NULL, DOOR, PLYR, ACHR, REFR, PGRE, PHZD, PARW, PBAR, PBEA, PCON, PFLA]),
#      {10} wbByteArray('Unknown', 4, cpIgnore),
#      {11} wbByteArray('Unknown', 4, cpIgnore),
#      {12} wbByteArray('Unknown', 4, cpIgnore)
#     ]),
#     wbInteger('Radius', itS32)
#   ]);

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelGroups('relations',
            MelStruct('XNAM', 'IiI', (FID, 'faction'), 'mod',
                      'groupCombatReaction'),
        ),
        MelUInt32('DATA', (FactGeneralTypeFlags, 'flags', 0L)),
        MelFid('JAIL','exteriorJailMarker'),
        MelFid('WAIT','followerWaitMarker'),
        MelFid('STOL','stolenGoodsContainer'),
        MelFid('PLCN','playerInventoryContainer'),
        MelFid('CRGR','sharedCrimeFactionList'),
        MelFid('JOUT','jailOutfit'),
        # 'arrest' and 'attackOnSight' are actually bools
        MelTruncatedStruct('CRVA', '2B5Hf2H', 'arrest', 'attackOnSight',
                           'murder', 'assult', 'trespass', 'pickpocket',
                           'unknown', 'stealMultiplier', 'escape', 'werewolf',
                           old_versions={'2B5Hf', '2B5H'}),
        MelGroups('ranks',
            MelUInt32('RNAM', 'rank'),
            MelLString('MNAM','maleTitle'),
            MelLString('FNAM','femaleTitle'),
            MelString('INAM','insigniaPath'),
        ),
        MelFid('VEND','vendorBuySellList'),
        MelFid('VENC','merchantContainer'),
        MelStruct('VENV','3H2s2B2s','startHour','endHour','radius','unknownOne',
                  'onlyBuysStolenItems','notSellBuy','UnknownTwo'),
        MelOptStruct('PLVD','iIi','type',(FID,'locationValue'),'radius',),
        MelConditionCounter(),
        MelConditions(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFlor(MelRecord):
    """Flora."""
    classType = 'FLOR'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelBase('PNAM','unknown01'),
        MelLString('RNAM','activateTextOverride'),
        MelBase('FNAM','unknown02'),
        MelFid('PFIG','ingredient'),
        MelFid('SNAM','harvestSound'),
        MelStruct('PFPC','4B','spring','summer','fall','winter',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFlst(MelRecord):
    """FormID List."""
    classType = 'FLST'

    melSet = MelSet(
        MelEdid(),
        MelFids('LNAM','formIDInList'),
    )
    __slots__ = melSet.getSlotsUsed() + ['mergeOverLast', 'mergeSources',
                                         'items', 'deflsts', 'canListMerge']

    """ Skyrim's FLST can't always be merged if a mod depends on the order of
    the LNAM records for the Papyrus scripts.

    Solution: Create a Bash tag that indicates when a list cannot be merged.
    If even one mod has this tag then the list is not merged into the
    Bash Patch."""

    # The same with Relev, Delev the 'NoFlstMerge' tag applies to the entire mod
    # even if only one FLST requires it.  When parsing the FLSTs from other mods
    # Wrye Bash should skip any FLST from a mod with the 'NoFlstMerge' tag.
    # Example, ModA has 10 FLST, MODB has 11 FLST.  Ten of the lists are the same
    # Between the two mods.  Since only one list is different, only one FLST is
    # different then only one FLST would be mergable.

    # New Bash Tag 'NoFlstMerge'
    def __init__(self, header, ins=None, do_unpack=False):
        MelRecord.__init__(self, header, ins, do_unpack)
        self.mergeOverLast = False #--Merge overrides last mod merged
        self.mergeSources = None #--Set to list by other functions
        self.items  = None #--Set of items included in list
        #--Set of items deleted by list (Deflst mods) unused for Skyrim
        self.deflsts = None

    def mergeFilter(self,modSet):
        """Filter out items that don't come from specified modSet."""
        if not self.longFids: raise StateError(_("Fids not in long format"))
        self.formIDInList = [fid for fid in self.formIDInList if fid[0] in modSet]

    def mergeWith(self,other,otherMod):
        """Merges newLevl settings and entries with self.
        Requires that: self.items, other.deflsts be defined."""
        if not self.longFids: raise StateError(_("Fids not in long format"))
        if not other.longFids: raise StateError(_("Fids not in long format"))
        #--Remove items based on other.removes
        if other.deflsts:
            removeItems = self.items & other.deflsts
            self.formIDInList = [fid for fid in self.formIDInList if fid not in removeItems]
            self.items = (self.items | other.deflsts)
        #--Add new items from other
        newItems = set()
        formIDInListAppend = self.formIDInList.append
        newItemsAdd = newItems.add
        for fid in other.formIDInList:
            if fid not in self.items:
                formIDInListAppend(fid)
                newItemsAdd(fid)
        if newItems:
            self.items |= newItems
        #--Is merged list different from other? (And thus written to patch.)
        if len(self.formIDInList) != len(other.formIDInList):
            self.mergeOverLast = True
        else:
            for selfEntry,otherEntry in zip(self.formIDInList,other.formIDInList):
                if selfEntry != otherEntry:
                    self.mergeOverLast = True
                    break
            else:
                self.mergeOverLast = False
        if self.mergeOverLast:
            self.mergeSources.append(otherMod)
        else:
            self.mergeSources = [otherMod]
        self.setChanged()

#------------------------------------------------------------------------------
class MreFstp(MelRecord):
    """Footstep."""
    classType = 'FSTP'

    melSet = MelSet(
        MelEdid(),
        MelFid('DATA','impactSet'),
        MelString('ANAM','tag'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFsts(MelRecord):
    """Footstep Set."""
    classType = 'FSTS'

    melSet = MelSet(
        MelEdid(),
        MelStruct('XCNT','5I','walkForward','runForward','walkForwardAlt',
                  'runForwardAlt','walkForwardAlternate2',),
        MelFidList('DATA','footstepSets'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreFurn(MelRecord):
    """Furniture."""
    classType = 'FURN'

    FurnGeneralFlags = Flags(0L,Flags.getNames(
        (1, 'ignoredBySandbox'),
    ))

    FurnActiveMarkerFlags = Flags(0L,Flags.getNames(
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

    MarkerEntryPointFlags = Flags(0L,Flags.getNames(
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
        MelBase('PNAM','pnam_p'),
        MelUInt16('FNAM', (FurnGeneralFlags, 'general_f', None)),
        MelFid('KNAM','interactionKeyword'),
        MelUInt32('MNAM', (FurnActiveMarkerFlags, 'activeMarkers', None)),
        MelStruct('WBDT','Bb','benchType','usesSkill',),
        MelFid('NAM1','associatedSpell'),
        MelGroups('markers',
            MelUInt32('ENAM', 'markerIndex',),
            MelStruct('NAM0','2sH','unknown',(MarkerEntryPointFlags,'disabledPoints_f',None),),
            MelFid('FNMK','markerKeyword',),
        ),
        MelGroups('entryPoints',
            MelStruct('FNPR', '2H', 'markerType',
                      (MarkerEntryPointFlags, 'entryPointsFlags', None)),
        ),
        MelString('XMRK','modelFilename'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Marker for organization please don't remove ---------------------------------
# GLOB ------------------------------------------------------------------------
# Defined in brec.py as class MreGlob(MelRecord) ------------------------------
#------------------------------------------------------------------------------
class MreGmst(MreGmstBase):
    """Game Setting."""
    isKeyedByEid = True # NULL fids are acceptable.

#------------------------------------------------------------------------------
class MreGras(MelRecord):
    """Grass."""
    classType = 'GRAS'

    GrasTypeFlags = Flags(0L,Flags.getNames(
            (0, 'vertexLighting'),
            (1, 'uniformScaling'),
            (2, 'fitToSlope'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelStruct('DATA','3BsH2sI4fB3s','density','minSlope','maxSlope',
                  ('unkGras1', null1),'unitsFromWater',('unkGras2', null2),
                  'unitsFromWaterType','positionRange','heightRange',
                  'colorRange','wavePeriod',(GrasTypeFlags,'flags',0L),
                  ('unkGras3', null3),),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreHazd(MelRecord):
    """Hazard."""
    classType = 'HAZD'

    HazdTypeFlags = Flags(0L,Flags.getNames(
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
        MelFid('MNAM','imageSpaceModifier'),
        MelStruct('DATA','I4f5I','limit','radius','lifetime',
                  'imageSpaceRadius','targetInterval',(HazdTypeFlags,'flags',0L),
                  (FID,'spell'),(FID,'light'),(FID,'impactDataSet'),(FID,'sound'),),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreHdpt(MelRecord):
    """Head Part."""
    classType = 'HDPT'

    HdptTypeFlags = Flags(0L,Flags.getNames(
        (0, 'playable'),
        (1, 'male'),
        (2, 'female'),
        (3, 'isExtraPart'),
        (4, 'useSolidTint'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelModel(),
        MelUInt8('DATA', (HdptTypeFlags, 'flags', 0L)),
        MelUInt32('PNAM', 'hdptTypes'),
        MelFids('HNAM','extraParts'),
        MelGroups('partsData',
            MelUInt32('NAM0', 'headPartType',),
            MelString('NAM1','filename'),
        ),
        MelFid('TNAM','textureSet'),
        MelFid('CNAM','color'),
        MelFid('RNAM','validRaces'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIdle(MelRecord):
    """Idle Animation."""
    classType = 'IDLE'

    IdleTypeFlags = Flags(0L,Flags.getNames(
            (0, 'parent'),
            (1, 'sequence'),
            (2, 'noAttacking'),
            (3, 'blocking'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelConditions(),
        MelString('DNAM','filename'),
        MelString('ENAM','animationEvent'),
        MelGroups('idleAnimations',
            MelStruct('ANAM','II',(FID,'parent'),(FID,'prevId'),),
        ),
        MelStruct('DATA','4BH','loopMin','loopMax',(IdleTypeFlags,'flags',0L),
                  'animationGroupSection','replayDelay',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIdlm(MelRecord):
    """Idle Marker."""
    classType = 'IDLM'

    IdlmTypeFlags = Flags(0L,Flags.getNames(
        (0, 'runInSequence'),
        (1, 'unknown1'),
        (2, 'doOnce'),
        (3, 'unknown3'),
        (4, 'ignoredBySandbox'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8('IDLF', (IdlmTypeFlags, 'flags', 0L)),
        MelCounter(MelUInt8('IDLC', 'animation_count'), counts='animations'),
        MelFloat('IDLT', 'idleTimerSetting'),
        MelFidList('IDLA','animations'),
        MelModel(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreInfo(MelRecord):
    """Dialog Response."""
    classType = 'INFO'

    _InfoResponsesFlags = Flags(0L, Flags.getNames(
            (0, 'useEmotionAnimation'),
        ))

    _EnamResponseFlags = Flags(0L, Flags.getNames(
            (0, 'goodbye'),
            (1, 'random'),
            (2, 'sayonce'),
            (3, 'unknown4'),
            (4, 'unknown5'),
            (5, 'randomend'),
            (6, 'invisiblecontinue'),
            (7, 'walkAway'),
            (8, 'walkAwayInvisibleinMenu'),
            (9, 'forcesubtitle'),
            (10, 'canmovewhilegreeting'),
            (11, 'noLIPFile'),
            (12, 'requirespostprocessing'),
            (13, 'audioOutputOverride'),
            (14, 'spendsfavorpoints'),
            (15, 'unknown16'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBase('DATA','unknownDATA'),
        MelStruct('ENAM','2H', (_EnamResponseFlags, 'flags', 0L),
                  'resetHours',),
        MelFid('TPIC','topic',),
        MelFid('PNAM','prevInfo',),
        MelUInt8('CNAM', 'favorLevel'),
        MelFids('TCLT','linkTo',),
        MelFid('DNAM','responseData',),
        MelGroups('responses',
            MelStruct('TRDT', '2I4sB3sIB3s', 'emotionType', 'emotionValue',
                      ('unused1', null4), 'responseNumber', ('unused2', null3),
                      (FID, 'sound', None),
                      (_InfoResponsesFlags, 'responseFlags', 0L),
                      ('unused3', null3),),
            MelLString('NAM1','responseText'),
            MelString('NAM2','scriptNotes'),
            MelString('NAM3','edits'),
            MelFid('SNAM','idleAnimationsSpeaker',),
            MelFid('LNAM','idleAnimationsListener',),
        ),
        MelConditions(),
        MelGroups('leftOver',
            MelBase('SCHR','unknown1'),
            MelFid('QNAM','unknown2'),
            MelNull('NEXT'),
        ),
        MelLString('RNAM','prompt'),
        MelFid('ANAM','speaker',),
        MelFid('TWAT','walkAwayTopic',),
        MelFid('ONAM','audioOutputOverride',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImad(MelRecord):
    """Image Space Adapter."""
    classType = 'IMAD'

    _ImadDofFlags = Flags(0L, Flags.getNames(
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
    _ImadAnimatableFlags = Flags(0L, Flags.getNames(
        (0, 'animatable'),
    ))
    _ImadRadialBlurFlags = Flags(0L, Flags.getNames(
        (0, 'useTarget')
    ))

    melSet = MelSet(
        MelEdid(),
        MelStruct('DNAM', 'If49I2f8I', (_ImadAnimatableFlags, 'aniFlags', 0L),
                  'duration', 'eyeAdaptSpeedMult', 'eyeAdaptSpeedAdd',
                  'bloomBlurRadiusMult', 'bloomBlurRadiusAdd',
                  'bloomThresholdMult', 'bloomThresholdAdd', 'bloomScaleMult',
                  'bloomScaleAdd', 'targetLumMinMult', 'targetLumMinAdd',
                  'targetLumMaxMult', 'targetLumMaxAdd', 'sunlightScaleMult',
                  'sunlightScaleAdd', 'skyScaleMult', 'skyScaleAdd',
                  'unknown08Mult', 'unknown48Add', 'unknown09Mult',
                  'unknown49Add', 'unknown0AMult', 'unknown4AAdd',
                  'unknown0BMult', 'unknown4BAdd', 'unknown0CMult',
                  'unknown4CAdd', 'unknown0DMult', 'unknown4DAdd',
                  'unknown0EMult', 'unknown4EAdd', 'unknown0FMult',
                  'unknown4FAdd', 'unknown10Mult', 'unknown50Add',
                  'saturationMult', 'saturationAdd', 'brightnessMult',
                  'brightnessAdd', 'contrastMult', 'contrastAdd',
                  'unknown14Mult', 'unknown54Add',
                  'tintColor', 'blurRadius', 'doubleVisionStrength',
                  'radialBlurStrength', 'radialBlurRampUp', 'radialBlurStart',
                  (_ImadRadialBlurFlags, 'radialBlurFlags', 0L),
                  'radialBlurCenterX', 'radialBlurCenterY', 'dofStrength',
                  'dofDistance', 'dofRange', (_ImadDofFlags, 'dofFlags', 0L),
                  'radialBlurRampDown', 'radialBlurDownStart', 'fadeColor',
                  'motionBlurStrength'),
        MelValueInterpolator('BNAM', 'blurRadiusInterp'),
        MelValueInterpolator('VNAM', 'doubleVisionStrengthInterp'),
        MelColorInterpolator('TNAM', 'tintColorInterp'),
        MelColorInterpolator('NAM3', 'fadeColorInterp'),
        MelValueInterpolator('RNAM', 'radialBlurStrengthInterp'),
        MelValueInterpolator('SNAM', 'radialBlurRampUpInterp'),
        MelValueInterpolator('UNAM', 'radialBlurStartInterp'),
        MelValueInterpolator('NAM1', 'radialBlurRampDownInterp'),
        MelValueInterpolator('NAM2', 'radialBlurDownStartInterp'),
        MelValueInterpolator('WNAM', 'dofStrengthInterp'),
        MelValueInterpolator('XNAM', 'dofDistanceInterp'),
        MelValueInterpolator('YNAM', 'dofRangeInterp'),
        MelValueInterpolator('NAM4', 'motionBlurStrengthInterp'),
        MelValueInterpolator('\x00IAD', 'eyeAdaptSpeedMultInterp'),
        MelValueInterpolator('\x40IAD', 'eyeAdaptSpeedAddInterp'),
        MelValueInterpolator('\x01IAD', 'bloomBlurRadiusMultInterp'),
        MelValueInterpolator('\x41IAD', 'bloomBlurRadiusAddInterp'),
        MelValueInterpolator('\x02IAD', 'bloomThresholdMultInterp'),
        MelValueInterpolator('\x42IAD', 'bloomThresholdAddInterp'),
        MelValueInterpolator('\x03IAD', 'bloomScaleMultInterp'),
        MelValueInterpolator('\x43IAD', 'bloomScaleAddInterp'),
        MelValueInterpolator('\x04IAD', 'targetLumMinMultInterp'),
        MelValueInterpolator('\x44IAD', 'targetLumMinAddInterp'),
        MelValueInterpolator('\x05IAD', 'targetLumMaxMultInterp'),
        MelValueInterpolator('\x45IAD', 'targetLumMaxAddInterp'),
        MelValueInterpolator('\x06IAD', 'sunlightScaleMultInterp'),
        MelValueInterpolator('\x46IAD', 'sunlightScaleAddInterp'),
        MelValueInterpolator('\x07IAD', 'skyScaleMultInterp'),
        MelValueInterpolator('\x47IAD', 'skyScaleAddInterp'),
        MelBase('\x08IAD', 'unknown08IAD'),
        MelBase('\x48IAD', 'unknown48IAD'),
        MelBase('\x09IAD', 'unknown09IAD'),
        MelBase('\x49IAD', 'unknown49IAD'),
        MelBase('\x0AIAD', 'unknown0aIAD'),
        MelBase('\x4AIAD', 'unknown4aIAD'),
        MelBase('\x0BIAD', 'unknown0bIAD'),
        MelBase('\x4BIAD', 'unknown4bIAD'),
        MelBase('\x0CIAD', 'unknown0cIAD'),
        MelBase('\x4CIAD', 'unknown4cIAD'),
        MelBase('\x0DIAD', 'unknown0dIAD'),
        MelBase('\x4DIAD', 'unknown4dIAD'),
        MelBase('\x0EIAD', 'unknown0eIAD'),
        MelBase('\x4EIAD', 'unknown4eIAD'),
        MelBase('\x0FIAD', 'unknown0fIAD'),
        MelBase('\x4FIAD', 'unknown4fIAD'),
        MelBase('\x10IAD', 'unknown10IAD'),
        MelBase('\x50IAD', 'unknown50IAD'),
        MelValueInterpolator('\x11IAD', 'saturationMultInterp'),
        MelValueInterpolator('\x51IAD', 'saturationAddInterp'),
        MelValueInterpolator('\x12IAD', 'brightnessMultInterp'),
        MelValueInterpolator('\x52IAD', 'brightnessAddInterp'),
        MelValueInterpolator('\x13IAD', 'contrastMultInterp'),
        MelValueInterpolator('\x53IAD', 'contrastAddInterp'),
        MelBase('\x14IAD', 'unknown14IAD'),
        MelBase('\x54IAD', 'unknown54IAD'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreImgs(MelRecord):
    """Image Space."""
    classType = 'IMGS'

    melSet = MelSet(
        MelEdid(),
        MelBase('ENAM','eman_p'),
        MelStruct('HNAM','9f','eyeAdaptSpeed','bloomBlurRadius','bloomThreshold','bloomScale',
                  'receiveBloomThreshold','white','sunlightScale','skyScale',
                  'eyeAdaptStrength',),
        MelStruct('CNAM','3f','Saturation','Brightness','Contrast',),
        MelStruct('TNAM','4f','tintAmount','tintRed','tintGreen','tintBlue',),
        MelStruct('DNAM','3f2sH','dofStrength','dofDistance','dofRange','unknown',
                  'skyBlurRadius',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIngr(MelRecord,MreHasEffects):
    """Ingredient."""
    classType = 'INGR'

    IngrTypeFlags = Flags(0L, Flags.getNames(
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
        MelFid('ETYP','equipmentType',),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelStruct('DATA','if','value','weight'),
        MelStruct('ENIT','iI','ingrValue',(IngrTypeFlags,'flags',0L),),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIpct(MelRecord):
    """Impact."""
    classType = 'IPCT'

    _IpctTypeFlags = Flags(0L, Flags.getNames('noDecalData'))

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelTruncatedStruct('DATA', 'fI2fI2B2s', 'effectDuration',
                           'effectOrientation', 'angleThreshold',
                           'placementRadius', 'soundLevel',
                           (_IpctTypeFlags, 'ipctFlags', 0L), 'impactResult',
                           ('unkIpct1', null1), old_versions={'fI2f'}),
        MelDecalData(),
        MelFid('DNAM','textureSet'),
        MelFid('ENAM','secondarytextureSet'),
        MelFid('SNAM','sound1'),
        MelFid('NAM1','sound2'),
        MelFid('NAM2','hazard'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreIpds(MelRecord):
    """Impact Dataset."""
    classType = 'IPDS'

    melSet = MelSet(
        MelEdid(),
        MelGroups('impactData',
            MelStruct('PNAM', '2I', (FID, 'material'), (FID, 'impact')),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreKeym(MelRecord):
    """Key."""
    classType = 'KEYM'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelKeywords(),
        MelStruct('DATA','if','value','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreKywd(MelRecord):
    """Keyword record."""
    classType = 'KYWD'

    melSet = MelSet(
        MelEdid(),
        MelColorO(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLcrt(MelRecord):
    """Location Reference Type."""
    classType = 'LCRT'

    melSet = MelSet(
        MelEdid(),
        MelColorO(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLctn(MelRecord):
    """Location"""
    classType = 'LCTN'

    melSet = MelSet(
        MelEdid(),
        MelArray('actorCellPersistentReference',
            MelStruct('ACPR', '2I2h', (FID, 'actor'), (FID, 'location'),
                      'gridX', 'gridY'),
        ),
        MelArray('locationCellPersistentReference',
            MelStruct('LCPR', '2I2h', (FID, 'actor'), (FID, 'location'),
                      'gridX', 'gridY'),
        ),
        MelFidList('RCPR','referenceCellPersistentReference',),
        MelArray('actorCellUnique',
            MelStruct('ACUN', '3I', (FID, 'actor'), (FID, 'eef'),
                      (FID, 'location')),
        ),
        MelArray('locationCellUnique',
            MelStruct('LCUN', '3I', (FID, 'actor'), (FID, 'eef'),
                      (FID, 'location')),
        ),
        MelFidList('RCUN','referenceCellUnique',),
        MelArray('actorCellStaticReference',
            MelStruct('ACSR', '3I2h', (FID, 'locRefType'), (FID, 'marker'),
                      (FID, 'location'), 'gridX', 'gridY'),
        ),
        MelArray('locationCellStaticReference',
            MelStruct('LCSR', '3I2h', (FID, 'locRefType'), (FID, 'marker'),
                      (FID, 'location'), 'gridX', 'gridY'),
        ),
        MelFidList('RCSR','referenceCellStaticReference',),
        MelGroups('actorCellEncounterCell',
            MelStruct('ACEC', 'I', (FID,'actor'), dumpExtra='gridsXY'),
        ),
        MelGroups('locationCellEncounterCell',
            MelStruct('LCEC', 'I', (FID,'actor'), dumpExtra='gridsXY'),
        ),
        MelGroups('referenceCellEncounterCell',
            MelStruct('RCEC', 'I', (FID,'actor'), dumpExtra='gridsXY'),
        ),
        MelFidList('ACID','actorCellMarkerReference',),
        MelFidList('LCID','locationCellMarkerReference',),
        MelArray('actorCellEnablePoint',
            MelStruct('ACEP', '2I2h', (FID, 'actor'), (FID,'ref'), 'gridX',
                      'gridY'),
        ),
        MelArray('locationCellEnablePoint',
            MelStruct('LCEP', '2I2h', (FID, 'actor'), (FID,'ref'), 'gridX',
                      'gridY'),
        ),
        MelFull(),
        MelKeywords(),
        MelFid('PNAM','parentLocation',),
        MelFid('NAM1','music',),
        MelFid('FNAM','unreportedCrimeFaction',),
        MelFid('MNAM','worldLocationMarkerRef',),
        MelFloat('RNAM', 'worldLocationRadius'),
        MelFid('NAM0','horseMarkerRef',),
        MelColorO(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLgtm(MelRecord):
    """Lighting Template."""
    classType = 'LGTM'

    class MelLgtmData(MelStruct):
        """Older format skips 8 bytes in the middle and has the same unpacked
        length, so we can't use MelTruncatedStruct."""
        def loadData(self, record, ins, sub_type, size_, readId):
            if size_ == 92:
                MelStruct.loadData(self, record, ins, sub_type, size_, readId)
                return
            elif size_ == 84:
                unpacked_val = ins.unpack('3Bs3Bs3Bs2f2i3f24s3Bs3f4s', size_,
                                          readId)
                # Pad it with 8 null bytes in the middle
                unpacked_val = (unpacked_val[:19]
                                + (unpacked_val[19] + null4 * 2,)
                                + unpacked_val[20:])
                for attr, value, action in zip(self.attrs, unpacked_val,
                                               self.actions):
                    if action: value = action(value)
                    setattr(record, attr, value)
            else:
                raise ModSizeError(ins.inName, readId, (92, 84), size_)

    melSet = MelSet(
        MelEdid(),
        MelLgtmData(
            'DATA', '3Bs3Bs3Bs2f2i3f32s3Bs3f4s', 'redLigh', 'greenLigh',
            'blueLigh','unknownLigh', 'redDirect', 'greenDirect', 'blueDirect',
            'unknownDirect', 'redFog', 'greenFog', 'blueFog', 'unknownFog',
            'fogNear', 'fogFar', 'dirRotXY', 'dirRotZ', 'directionalFade',
            'fogClipDist', 'fogPower', ('ambientColors', null4 * 8),
            'redFogFar', 'greenFogFar', 'blueFogFar', 'unknownFogFar',
            'fogMax', 'lightFaceStart', 'lightFadeEnd',
            ('unknownData2', null4)),
        MelTruncatedStruct(
            'DALC', '4B4B4B4B4B4B4Bf', 'redXplus', 'greenXplus', 'blueXplus',
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
    classType = 'LIGH'

    LighTypeFlags = Flags(0L,Flags.getNames(
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
        MelStruct('DATA','iI4BI6fIf','duration','radius','red','green','blue',
                  'unknown',(LighTypeFlags,'flags',0L),'falloffExponent','fov',
                  'nearClip','fePeriod','feIntensityAmplitude',
                  'feMovementAmplitude','value','weight',),
        MelFloat('FNAM', 'fade'),
        MelFid('SNAM','sound'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLscr(MelRecord):
    """Load Screen."""
    classType = 'LSCR'

    melSet = MelSet(
        MelEdid(),
        MelIcons(),
        MelLString('DESC','description'),
        MelConditions(),
        MelFid('NNAM','loadingScreenNIF'),
        MelFloat('SNAM', 'initialScale'),
        MelStruct('RNAM','3h','rotGridY','rotGridX','rotGridZ',),
        MelStruct('ONAM','2h','rotOffsetMin','rotOffsetMax',),
        MelStruct('XNAM','3f','transGridY','transGridX','transGridZ',),
        MelString('MOD2','cameraPath'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLtex(MelRecord):
    """Landscape Texture."""
    classType = 'LTEX'

    melSet = MelSet(
        MelEdid(),
        MelFid('TNAM','textureSet',),
        MelFid('MNAM','materialType',),
        MelStruct('HNAM','BB','friction','restitution',),
        MelUInt8('SNAM', 'textureSpecularExponent'),
        MelFids('GNAM','grasses'),
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
                self, MelUInt8('LLCT', 'entry_count'), counts='entries')

    class MelLvlo(MelGroups):
        def __init__(self):
            MelGroups.__init__(self,'entries',
                MelStruct('LVLO','=HHIHH','level',('unknown1',null2),
                          (FID,'listId',None),('count',1),('unknown2',null2)),
                MelCoed(),
            )

#------------------------------------------------------------------------------
class MreLvli(MreLeveledList):
    """Leveled Item."""
    classType = 'LVLI'
    top_copy_attrs = ('chanceNone','glob',)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8('LVLD', 'chanceNone'),
        MelUInt8('LVLF', (MreLeveledListBase._flags, 'flags', 0L)),
        MelOptFid('LVLG', 'glob'),
        MreLeveledList.MelLlct(),
        MreLeveledList.MelLvlo(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLvln(MreLeveledList):
    """Leveled NPC."""
    classType = 'LVLN'
    top_copy_attrs = ('chanceNone','model','modt_p',)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8('LVLD', 'chanceNone'),
        MelUInt8('LVLF', (MreLeveledListBase._flags, 'flags', 0L)),
        MelOptFid('LVLG', 'glob'),
        MreLeveledList.MelLlct(),
        MreLeveledList.MelLvlo(),
        MelString('MODL','model'),
        MelBase('MODT','modt_p'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreLvsp(MreLeveledList):
    """Leveled Spell."""
    classType = 'LVSP'

    top_copy_attrs = ('chanceNone',)

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelUInt8('LVLD', 'chanceNone'),
        MelUInt8('LVLF', (MreLeveledListBase._flags, 'flags', 0L)),
        MreLeveledList.MelLlct(),
        MreLeveledList.MelLvlo(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMato(MelRecord):
    """Material Object."""
    classType = 'MATO'

    MatoTypeFlags = Flags(0L,Flags.getNames(
            (0, 'singlePass'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelModel(),
        MelGroups('property_data',
            MelBase('DNAM', 'data_entry'),
        ),
        MelTruncatedStruct(
            'DATA', '11fI', 'falloffScale', 'falloffBias', 'noiseUVScale',
            'materialUVScale', 'projectionVectorX', 'projectionVectorY',
            'projectionVectorZ', 'normalDampener', 'singlePassColor',
            'singlePassColor', 'singlePassColor', (MatoTypeFlags,'flags',0L),
            old_versions={'7f'}),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMatt(MelRecord):
    """Material Type."""
    classType = 'MATT'

    MattTypeFlags = Flags(0L,Flags.getNames(
            (0, 'stairMaterial'),
            (1, 'arrowsStick'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelFid('PNAM', 'materialParent',),
        MelString('MNAM','materialName'),
        MelStruct('CNAM', '3f', 'red', 'green', 'blue'),
        MelFloat('BNAM', 'buoyancy'),
        MelUInt32('FNAM', (MattTypeFlags, 'flags', 0L)),
        MelFid('HNAM', 'havokImpactDataSet',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMesg(MelRecord):
    """Message."""
    classType = 'MESG'

    MesgTypeFlags = Flags(0L,Flags.getNames(
            (0, 'messageBox'),
            (1, 'autoDisplay'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelLString('DESC','description'),
        MelFull(),
        MelFid('INAM','iconUnused'), # leftover
        MelFid('QNAM','materialParent'),
        MelUInt32('DNAM', (MesgTypeFlags, 'flags', 0L)),
        MelUInt32('TNAM', 'displayTime'),
        MelGroups('menuButtons',
            MelLString('ITXT','buttonText'),
            MelConditions(),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMgef(MelRecord):
    """Magic Effect."""
    classType = 'MGEF'

    MgefGeneralFlags = Flags(0L,Flags.getNames(
            (0, 'hostile'),
            (1, 'recover'),
            (2, 'detrimental'),
            (3, 'snaptoNavmesh'),
            (4, 'noHitEvent'),
            (5, 'unknown6'),
            (6, 'unknown7'),
            (7, 'unknown8'),
            (8, 'dispellwithKeywords'),
            (9, 'noDuration'),
            (10, 'noMagnitude'),
            (11, 'noArea'),
            (12, 'fXPersist'),
            (13, 'unknown14'),
            (14, 'goryVisuals'),
            (15, 'hideinUI'),
            (16, 'unknown17'),
            (17, 'noRecast'),
            (18, 'unknown19'),
            (19, 'unknown20'),
            (20, 'unknown21'),
            (21, 'powerAffectsMagnitude'),
            (22, 'powerAffectsDuration'),
            (23, 'unknown24'),
            (24, 'unknown25'),
            (25, 'unknown26'),
            (26, 'painless'),
            (27, 'noHitEffect'),
            (28, 'noDeathDispel'),
            (29, 'unknown30'),
            (30, 'unknown31'),
            (31, 'unknown32'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelFull(),
        MelFid('MDOB','harvestIngredient'),
        MelKeywords(),
        MelPartialCounter(MelStruct(
            'DATA', 'IfI2iH2sIf4I4fIi4Ii3IfIfI4s4s4I2f',
            (MgefGeneralFlags, 'flags', 0L), 'baseCost', (FID, 'assocItem'),
            'magicSkill', 'resistValue', 'counterEffectCount',
            ('unknown1', null2), (FID, 'castingLight'), 'taperWeight',
            (FID, 'hitShader'), (FID, 'enchantShader'), 'minimumSkillLevel',
            'spellmakingArea', 'spellmakingCastingTime', 'taperCurve',
            'taperDuration', 'secondAvWeight', 'mgefArchtype', 'actorValue',
            (FID, 'projectile'), (FID, 'explosion'), 'castingType', 'delivery',
            'secondActorValue', (FID, 'castingArt'), (FID, 'hitEffectArt'),
            (FID, 'impactData'), 'skillUsageMultiplier',
            (FID, 'dualCastingArt'), 'dualCastingScale', (FID,'enchantArt'),
            ('unknown2', null4), ('unknown3', null4), (FID, 'equipAbility'),
            (FID, 'imageSpaceModifier'), (FID, 'perkToApply'),
            'castingSoundLevel', 'scriptEffectAiScore',
            'scriptEffectAiDelayTime'),
            counter='counterEffectCount', counts='counterEffects'),
        MelFids('ESCE','counterEffects'),
        MelArray('sounds',
            MelStruct('SNDD', '2I', 'soundType', (FID, 'sound')),
        ),
        MelLString('DNAM','magicItemDescription'),
        MelConditions(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMisc(MelRecord):
    """Misc. Item."""
    classType = 'MISC'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelOptFid('YNAM', 'pickupSound'),
        MelOptFid('ZNAM', 'dropSound'),
        MelKeywords(),
        MelStruct('DATA','=If','value','weight'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMovt(MelRecord):
    """Movement Type."""
    classType = 'MOVT'

    melSet = MelSet(
        MelEdid(),
        MelString('MNAM','mnam_n'),
        MelTruncatedStruct('SPED', '11f', 'leftWalk', 'leftRun', 'rightWalk',
                           'rightRun', 'forwardWalk', 'forwardRun', 'backWalk',
                           'backRun', 'rotateInPlaceWalk', 'rotateInPlaceRun',
                           'rotateWhileMovingRun', old_versions={'10f'}),
        MelOptStruct('INAM','3f','directional','movementSpeed','rotationSpeed'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMstt(MelRecord):
    """Moveable Static."""
    classType = 'MSTT'

    MsttTypeFlags = Flags(0L,Flags.getNames(
        (0, 'onLocalMap'),
        (1, 'unknown2'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelUInt8('DATA', (MsttTypeFlags, 'flags', 0L)),
        MelFid('SNAM','sound'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMusc(MelRecord):
    """Music Type."""
    classType = 'MUSC'

    MuscTypeFlags = Flags(0L,Flags.getNames(
            (0,'playsOneSelection'),
            (1,'abruptTransition'),
            (2,'cycleTracks'),
            (3,'maintainTrackOrder'),
            (4,'unknown5'),
            (5,'ducksCurrentTrack'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelUInt32('FNAM', (MuscTypeFlags, 'flags', 0L)),
        # Divided by 100 in TES5Edit, probably for editing only
        MelStruct('PNAM','2H','priority','duckingDB'),
        MelFloat('WNAM', 'fadeDuration'),
        MelFidList('TNAM','musicTracks'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreMust(MelRecord):
    """Music Track."""
    classType = 'MUST'

    melSet = MelSet(
        MelEdid(),
        MelUInt32('CNAM', 'trackType'),
        MelOptFloat('FLTV', 'duration'),
        MelOptUInt32('DNAM', 'fadeOut'),
        MelString('ANAM','trackFilename'),
        MelString('BNAM','finaleFilename'),
        MelArray('points',
            MelFloat('FNAM', ('cuePoints', 0.0)),
        ),
        MelOptStruct('LNAM','2fI','loopBegins','loopEnds','loopCount',),
        MelConditionCounter(),
        MelConditions(),
        MelFidList('SNAM','tracks',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Not Mergable - FormIDs unaccounted for
class MreNavi(MelRecord):
    """Navigation Mesh Info Map."""
    classType = 'NAVI'

    melSet = MelSet(
        MelEdid(),
        MelUInt32('NVER', 'version'),
        # NVMI and NVPP would need special routines to handle them
        # If no mitigation is needed, then leave it as MelBase
        MelBase('NVMI','navigationMapInfos',),
        MelBase('NVPP','preferredPathing',),
        MelFidList('NVSI','navigationMesh'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Not Mergable - FormIDs unaccounted for
class MreNavm(MelRecord):
    """Navigation Mesh."""
    classType = 'NAVM'

    NavmTrianglesFlags = Flags(0L,Flags.getNames(
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

    NavmCoverFlags = Flags(0L,Flags.getNames(
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
        MelBase('NVNM','navMeshGeometry'),
        MelBase('ONAM','onam_p'),
        MelBase('PNAM','pnam_p'),
        MelBase('NNAM','nnam_p'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreNpc(MelRecord):
    """Non-Player Character."""
    classType = 'NPC_'

    NpcFlags2 = Flags(0L,Flags.getNames(
            (0, 'useTraits'),
            (1, 'useStats'),
            (2, 'useFactions'),
            (3, 'useSpellList'),
            (4, 'useAIData'),
            (5, 'useAIPackages'),
            (6, 'useModelAnimation?'),
            (7, 'useBaseData'),
            (8, 'useInventory'),
            (9, 'useScript'),
            (10, 'useDefPackList'),
            (11, 'useAttackData'),
            (12, 'useKeywords'),
        ))

    NpcFlags1 = Flags(0L,Flags.getNames(
            (0, 'female'),
            (1, 'essential'),
            (2, 'isCharGenFacePreset'),
            (3, 'respawn'),
            (4, 'autoCalc'),
            (5, 'unique'),
            (6, 'doesNotAffectStealth'),
            (7, 'pcLevelMult'),
            (8, 'useTemplate?'),
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
            (21, 'loopedscript?'),
            (22, 'unknown22'),
            (23, 'unknown23'),
            (24, 'unknown24'),
            (25, 'unknown25'),
            (26, 'unknown26'),
            (27, 'unknown27'),
            (28, 'loopedaudio?'),
            (29, 'isGhost'),
            (30, 'unknown30'),
            (31, 'invulnerable'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelStruct('ACBS','I2Hh3Hh3H',
                  (NpcFlags1,'flags',0L),'magickaOffset',
                  'staminaOffset','level','calcMin',
                  'calcMax','speedMultiplier','dispotionBase',
                  (NpcFlags2,'npcFlags2',0L),'healthOffset','bleedoutOverride',
                  ),
        MelGroups('factions',
            MelStruct('SNAM', 'IB3s', (FID, 'faction'), 'rank', 'snamUnused'),
        ),
        MelOptFid('INAM', 'deathItem'),
        MelOptFid('VTCK', 'voice'),
        MelOptFid('TPLT', 'template'),
        MelFid('RNAM','race'),
        # TODO(inf) Kept it as such, why little-endian?
        MelCounter(MelStruct('SPCT', '<I', 'spell_count'), counts='spells'),
        MelFids('SPLO', 'spells'),
        MelDestructible(),
        MelOptFid('WNAM', 'wormArmor'),
        MelOptFid('ANAM', 'farawaymodel'),
        MelOptFid('ATKR', 'attackRace'),
        MelGroups('attacks',
            MelAttackData(),
            MelString('ATKE', 'attackEvents')
        ),
        MelOptFid('SPOR', 'spectator'),
        MelOptFid('OCOR', 'observe'),
        MelOptFid('GWOR', 'guardWarn'),
        MelOptFid('ECOR', 'combat'),
        MelCounter(MelUInt32('PRKZ', 'perk_count'), counts='perks'),
        MelGroups('perks',
            MelOptStruct('PRKR','IB3s',(FID, 'perk'),'rank','prkrUnused'),
        ),
        MelItemsCounter(),
        MelItems(),
        MelStruct('AIDT', 'BBBBBBBBIII', 'aggression', 'confidence',
                  'engergy', 'responsibility', 'mood', 'assistance',
                  'aggroRadiusBehavior',
                  'aidtUnknown', 'warn', 'warnAttack', 'attack'),
        MelFids('PKID', 'packages',),
        MelKeywords(),
        MelFid('CNAM', 'class'),
        MelFull(),
        MelLString('SHRT', 'shortName'),
        MelBase('DATA', 'marker'),
        MelStruct('DNAM','36BHHH2sfB3s',
            'oneHandedSV','twoHandedSV','marksmanSV','blockSV','smithingSV',
            'heavyArmorSV','lightArmorSV','pickpocketSV','lockpickingSV',
            'sneakSV','alchemySV','speechcraftSV','alterationSV','conjurationSV',
            'destructionSV','illusionSV','restorationSV','enchantingSV',
            'oneHandedSO','twoHandedSO','marksmanSO','blockSO','smithingSO',
            'heavyArmorSO','lightArmorSO','pickpocketSO','lockpickingSO',
            'sneakSO','alchemySO','speechcraftSO','alterationSO','conjurationSO',
            'destructionSO','illusionSO','restorationSO','enchantingSO',
            'health','magicka','stamina',('dnamUnused1',null2),
            'farawaymodeldistance','gearedupweapons',('dnamUnused2',null3)),
        MelFids('PNAM', 'head_part_addons',),
        # TODO(inf) Left everything starting from here alone because it uses
        #  little-endian - why?
        MelOptStruct('HCLF', '<I', (FID, 'hair_color')),
        MelOptStruct('ZNAM', '<I', (FID, 'combat_style')),
        MelOptStruct('GNAM', '<I', (FID, 'gifts')),
        MelBase('NAM5', 'nam5_p'),
        MelStruct('NAM6', '<f', 'height'),
        MelStruct('NAM7', '<f', 'weight'),
        MelStruct('NAM8', '<I', 'sound_level'),
        MelGroups('event_sound',
            MelStruct('CSDT', '<I', 'sound_type'),
            MelGroups('sound',
                MelStruct('CSDI', '<I', (FID, 'sound')),
                MelStruct('CSDC', '<B', 'chance')
            )
        ),
        MelOptStruct('CSCR', '<I', (FID, 'audio_template')),
        MelOptStruct('DOFT', '<I', (FID, 'default_outfit')),
        MelOptStruct('SOFT', '<I', (FID, 'sleep_outfit')),
        MelOptStruct('DPLT', '<I', (FID, 'default_package')),
        MelOptStruct('CRIF', '<I', (FID, 'crime_faction')),
        MelOptStruct('FTST', '<I', (FID, 'face_texture')),
        MelOptStruct('QNAM', '<fff', 'skin_tone_r' ,'skin_tone_g', 'skin_tone_b'),
        MelOptStruct('NAM9', '<fffffffffffffffffff', 'nose_long', 'nose_up',
                     'jaw_up', 'jaw_wide', 'jaw_forward', 'cheeks_up', 'cheeks_back',
                     'eyes_up', 'eyes_out', 'brows_up', 'brows_out', 'brows_forward',
                     'lips_up', 'lips_out', 'chin_wide', 'chin_down', 'chin_underbite',
                     'eyes_back', 'nam9_unused'),
        MelOptStruct('NAMA', '<IiII', 'nose', 'unknown', 'eyes', 'mouth'),
        MelGroups('face_tint_layer',
            MelStruct('TINI', '<H', 'tint_item'),
            MelStruct('TINC', '<4B', 'tintRed', 'tintGreen', 'tintBlue' ,'tintAlpha'),
            MelStruct('TINV', '<i', 'tint_value'),
            MelStruct('TIAS', '<h', 'preset'),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreOtft(MelRecord):
    """Outfit."""
    classType = 'OTFT'

    melSet = MelSet(
        MelEdid(),
        MelFidList('INAM','items'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Marker for organization please don't remove ---------------------------------
# PACK ------------------------------------------------------------------------
class MrePack(MelRecord):
    """Package."""
    classType = 'PACK'

    PackFlags10 = Flags(0L,Flags.getNames(
            (0, 'successCompletesPackage'),
        ))

    PackFlags9 = Flags(0L,Flags.getNames(
            (0, 'repeatwhenComplete'),
            (1, 'unknown1'),
        ))

    PackFlags1 = Flags(0L,Flags.getNames(
            (0, 'offersServices'),
            (1, 'unknown2'),
            (2, 'mustcomplete'),
            (3, 'maintainSpeedatGoal'),
            (4, 'unknown5'),
            (5, 'unknown6'),
            (6, 'unlockdoorsatpackagestart'),
            (7, 'unlockdoorsatpackageend'),
            (8, 'unknown9'),
            (9, 'continueifPCNear'),
            (10, 'onceperday'),
            (11, 'unknown12'),
            (12, 'unknown13'),
            (13, 'preferredSpeed'),
            (14, 'unknown15'),
            (15, 'unknown16'),
            (16, 'unknown17'),
            (17, 'alwaysSneak'),
            (18, 'allowSwimming'),
            (19, 'unknown20'),
            (20, 'ignoreCombat'),
            (21, 'weaponsUnequipped'),
            (22, 'unknown23'),
            (23, 'weaponDrawn'),
            (24, 'unknown25'),
            (25, 'unknown26'),
            (26, 'unknown27'),
            (27, 'noCombatAlert'),
            (28, 'unknown29'),
            (29, 'wearSleepOutfitunused'),
            (30, 'unknown31'),
            (31, 'unknown32'),
        ))

    PackFlags2 = Flags(0L,Flags.getNames(
            (0, 'hellostoplayer'),
            (1, 'randomconversations'),
            (2, 'observecombatbehavior'),
            (3, 'greetcorpsebehavior'),
            (4, 'reactiontoplayeractions'),
            (5, 'friendlyfirecomments'),
            (6, 'aggroRadiusBehavior'),
            (7, 'allowIdleChatter'),
            (8, 'unknown9'),
            (9, 'worldInteractions'),
            (10, 'unknown11'),
            (11, 'unknown12'),
            (12, 'unknown13'),
            (13, 'unknown14'),
            (14, 'unknown15'),
            (15, 'unknown16'),
        ))

    # Data Inputs Flags
    PackFlags3 = Flags(0L,Flags.getNames(
            (0, 'public'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelStruct('PKDT','I3BsH2s',(PackFlags1,'generalFlags',0L),'type','interruptOverride',
                  'preferredSpeed','unknown',(PackFlags2,'interruptFlags',0L),'unknown',),
        MelStruct('PSDT','2bB2b3si','month','dayofweek','date','hour','minute',
                  'unused','durationminutes',),
        MelConditions(),
        MelGroup('idleAnimations',
            MelUInt32('IDLF', 'type'),
            MelPartialCounter(MelStruct('IDLC', 'B3s', 'animation_count',
                                        'unknown'),
                              counter='animation_count', counts='animations'),
            MelFloat('IDLT', 'timerSetting',),
            MelFidList('IDLA', 'animations'),
            MelBase('IDLB','unknown'),
        ),
        MelFid('CNAM','combatStyle',),
        MelFid('QNAM','ownerQuest',),
        MelStruct('PKCU','3I','dataInputCount',(FID,'packageTemplate'),
                  'versionCount',),
        MelGroup('packageData',
            MelGroups('inputValues',
                MelString('ANAM','type'),
                # CNAM Needs Union Decider, No FormID
                MelBase('CNAM','unknown',),
                MelBase('BNAM','unknown',),
                # PDTO Needs Union Decider
                MelGroups('topicData',
                    MelStruct('PDTO', '2I', 'type', (FID, 'data')),
                ),
                # PLDT Needs Union Decider, No FormID
                MelStruct('PLDT','iIi','locationType','locationValue','radius',),
                # PTDA Needs Union Decider
                MelStruct('PTDA','iIi','targetDataType',(FID,'targetDataTarget'),
                          'targetDataCountDist',),
                MelBase('TPIC','unknown',),
            ),
            MelGroups('dataInputs',
                MelSInt8('UNAM', 'index'),
                MelString('BNAM','name',),
                MelUInt32('PNAM', (PackFlags1, 'flags', 0L)),
            ),
        ),
        MelBase('XNAM','marker',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MrePerk(MelRecord):
    """Perk."""
    classType = 'PERK'

    _PerkScriptFlags = Flags(0L,Flags.getNames(
        (0, 'runImmediately'),
        (1, 'replaceDefault'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelFull(),
        MelLString('DESC','description'),
        MelIcons(),
        MelConditions(),
        MelTruncatedStruct('DATA', '5B', ('trait', 0), ('minLevel', 0),
                           ('ranks', 0), ('playable', 0), ('hidden', 0),
                           old_versions={'4B'}),
        MelFid('NNAM', 'next_perk'),
        MelGroups('effects',
            MelStruct('PRKE', '3B', 'type', 'rank', 'priority'),
            MelUnion({
                0: MelStruct('DATA', 'IB3s', (FID, 'quest'), 'quest_stage',
                             'unusedDATA'),
                1: MelFid('DATA', 'ability'),
                2: MelStruct('DATA', '3B', 'entry_point', 'function',
                             'perk_conditions_tab_count'),
            }, decider=AttrValDecider('type')),
            MelGroups('effectConditions',
                MelSInt8('PRKC', 'runOn'),
                MelConditions(),
            ),
            MelGroups('effectParams',
                MelUInt8('EPFT', 'function_parameter_type'),
                MelLString('EPF2','buttonLabel'),
                MelStruct('EPF3','2H',(_PerkScriptFlags, 'script_flags', 0L),
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
                    0: MelBase('EPFD', 'param1'),
                    1: MelFloat('EPFD', 'param1'),
                    2: MelStruct('EPFD', 'If', 'param1', 'param2'),
#                    2: MelUnion({
#                        5:  MelStruct('EPFD', 'If', 'param1', 'param2'),
#                        12: MelStruct('EPFD', 'If', 'param1', 'param2'),
#                        13: MelStruct('EPFD', 'If', 'param1', 'param2'),
#                        14: MelStruct('EPFD', 'If', 'param1', 'param2'),
#                    }, decider=AttrValDecider('../function',
#                                                 assign_missing=-1),
#                        fallback=MelStruct('EPFD', '2f', 'param1', 'param2')),
                    3: MelFid('EPFD', 'param1'),
                    4: MelFid('EPFD', 'param1'),
                    5: MelFid('EPFD', 'param1'),
                    6: MelString('EPFD', 'param1'),
                    7: MelLString('EPFD', 'param1'),
                }, decider=AttrValDecider('function_parameter_type')),
            ),
            MelBase('PRKF','footer'),
        ),
    ).with_distributor({
        'DESC': {
            'CTDA|CIS1|CIS2': 'conditions',
            'DATA': 'trait',
        },
        'PRKE': {
            'CTDA|CIS1|CIS2|DATA': 'effects',
        },
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreProj(MelRecord):
    """Projectile."""
    classType = 'PROJ'

    ProjTypeFlags = Flags(0L,Flags.getNames(
        (0, 'hitscan'),
        (1, 'explosive'),
        (2, 'altTriger'),
        (3, 'muzzleFlash'),
        (4, 'unknown4'),
        (5, 'canbeDisable'),
        (6, 'canbePickedUp'),
        (7, 'superSonic'),
        (8, 'pinsLimbs'),
        (9, 'passThroughSmallTransparent'),
        (10, 'disableCombatAimCorrection'),
        (11, 'rotation'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelTruncatedStruct(
            'DATA', '2H3f2I3f2I3f3I4f2I', (ProjTypeFlags, 'flags', 0L),
            'projectileTypes', ('gravity', 0.0), ('speed', 10000.0),
            ('range', 10000.0), (FID, 'light', 0), (FID, 'muzzleFlash', 0),
            ('tracerChance', 0.0), ('explosionAltTrigerProximity', 0.0),
            ('explosionAltTrigerTimer', 0.0), (FID, 'explosion', 0),
            (FID, 'sound', 0), ('muzzleFlashDuration', 0.0),
            ('fadeDuration', 0.0), ('impactForce', 0.0),
            (FID, 'soundCountDown', 0), (FID, 'soundDisable', 0),
            (FID, 'defaultWeaponSource', 0), ('coneSpread', 0.0),
            ('collisionRadius', 0.0), ('lifetime', 0.0),
            ('relaunchInterval', 0.0), (FID, 'decalData', 0),
            (FID, 'collisionLayer', 0), old_versions={'2H3f2I3f2I3f3I4fI',
                                                      '2H3f2I3f2I3f3I4f'}),
        MelGroup('models',
            MelString('NAM1','muzzleFlashPath'),
            # Ignore texture hashes - they're only an optimization, plenty of
            # records in Skyrim.esm are missing them
            MelNull('NAM2'),
        ),
        MelUInt32('VNAM', 'soundLevel',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Needs testing should be mergable
class MreQust(MelRecord):
    """Quest."""
    classType = 'QUST'

    _questFlags = Flags(0,Flags.getNames(
        (0,'startGameEnabled'),
        (2,'wildernessEncounter'),
        (3,'allowRepeatedStages'),
        (8,'runOnce'),
        (9,'excludeFromDialogueExport'),
        (10,'warnOnAliasFillFailure'),
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
        MelStruct('DNAM', '=H2B4sI', (_questFlags, 'questFlags', 0L),
                  'priority', 'formVersion', 'unknown', 'questType'),
        MelOptStruct('ENAM','4s',('event',None)),
        MelFids('QTGL','textDisplayGlobals'),
        MelString('FLTR','objectWindowFilter'),
        MelConditions('dialogueConditions'),
        MelBase('NEXT','marker'),
        MelConditions('eventConditions'),
        MelGroups('stages',
            MelStruct('INDX','H2B','index',(_stageFlags,'flags',0L),'unknown'),
            MelGroups('logEntries',
                MelUInt8('QSDT', (stageEntryFlags, 'stageFlags', 0L)),
                MelConditions(),
                MelLString('CNAM','log_text'),
                MelFid('NAM0', 'nextQuest'),
                MelBase('SCHR', 'unusedSCHR'),
                MelBase('SCTX', 'unusedSCTX'),
                MelBase('QNAM', 'unusedQNAM'),
            ),
        ),
        MelGroups('objectives',
            MelUInt16('QOBJ', 'index'),
            MelUInt32('FNAM', (objectiveFlags, 'flags', 0L)),
            MelLString('NNAM','description'),
            MelGroups('targets',
                MelStruct('QSTA','iB3s','alias',(targetFlags,'flags'),('unused1',null3)),
                MelConditions(),
            ),
        ),
        MelBase('ANAM','aliasMarker'),
        MelGroups('aliases',
            MelUnion({
                'ALST': MelOptUInt32('ALST', ('aliasId', None)),
                'ALLS': MelOptUInt32('ALLS', ('aliasId', None)),
            }),
            MelString('ALID', 'aliasName'),
            MelUInt32('FNAM', (aliasFlags, 'flags', 0L)),
            MelOptSInt32('ALFI', ('forcedIntoAlias', None)),
            MelFid('ALFL','specificLocation'),
            MelFid('ALFR','forcedReference'),
            MelFid('ALUA','uniqueActor'),
            MelGroup('locationAliasReference',
                MelSInt32('ALFA', 'alias'),
                MelFid('KNAM','keyword'),
                MelFid('ALRT','referenceType'),
            ),
            MelGroup('externalAliasReference',
                MelFid('ALEQ','quest'),
                MelSInt32('ALEA', 'alias'),
            ),
            MelGroup('createReferenceToObject',
                MelFid('ALCO','object'),
                MelStruct('ALCA', 'hH', 'alias', 'create_target'),
                MelUInt32('ALCL', 'createLevel'),
            ),
            MelGroup('findMatchingReferenceNearAlias',
                MelSInt32('ALNA', 'alias'),
                MelUInt32('ALNT', 'type'),
            ),
            MelGroup('findMatchingReferenceFromEvent',
                MelStruct('ALFE','4s',('fromEvent',null4)),
                MelStruct('ALFD','4s',('eventData',null4)),
            ),
            MelConditions(),
            MelKeywords(),
            MelItemsCounter(),
            MelItems(),
            MelFid('SPOR','spectatorOverridePackageList'),
            MelFid('OCOR','observeDeadBodyOverridePackageList'),
            MelFid('GWOR','guardWarnOverridePackageList'),
            MelFid('ECOR','combatOverridePackageList'),
            MelFid('ALDN','displayName'),
            MelFids('ALSP','aliasSpells'),
            MelFids('ALFC','aliasFactions'),
            MelFids('ALPC','aliasPackageData'),
            MelFid('VTCK','voiceType'),
            MelBase('ALED','aliasEnd'),
        ),
        MelLString('NNAM','description'),
        MelGroups('targets',
            MelStruct('QSTA', 'IB3s', (FID, 'target'), (targetFlags, 'flags'),
                      ('unknown1', null3)),
            MelConditions(),
        ),
    ).with_distributor({
        'DNAM': {
            'CTDA|CIS1|CIS2': 'dialogueConditions',
        },
        'NEXT': {
            'CTDA|CIS1|CIS2': 'eventConditions',
        },
        'INDX': {
            'CTDA|CIS1|CIS2': 'stages',
        },
        'QOBJ': {
            'CTDA|CIS1|CIS2|FNAM|QSTA': 'objectives',
            # NNAM followed by NNAM means we've exited the objectives section
            'NNAM': ('objectives', {
                'NNAM': 'description',
            }),
        },
        'ANAM': {
            'CTDA|CIS1|CIS2|FNAM': 'aliases',
            # ANAM is required, so piggyback off of it here to resolve QSTA
            'QSTA': ('targets', {
                'CTDA|CIS1|CIS2': 'targets',
            }),
        },
        # Have to duplicate this here in case a quest has no objectives but
        # does have a description
        'NNAM': 'description',
    })
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Marker for organization please don't remove ---------------------------------
# RACE ------------------------------------------------------------------------
# Needs Updating
class MreRace(MelRecord):
    """Race."""
    classType = 'RACE'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Needs Updating
class MreRefr(MelRecord):
    """Placed Object."""
    classType = 'REFR'
    _marker_flags = Flags(0, Flags.getNames(
        'visible',
        'can_travel_to',
        'show_all_hidden',
    ))
    _parentFlags = Flags(0L,Flags.getNames('oppositeParent','popIn',))
    _actFlags = Flags(0L,Flags.getNames('useDefault', 'activate','open','openByDefault'))
    _lockFlags = Flags(0L,Flags.getNames(None, None, 'leveledLock'))
    _destinationFlags = Flags(0L,Flags.getNames('noAlarm'))
    _parentActivate = Flags(0L,Flags.getNames('parentActivateOnly'))
    reflectFlags = Flags(0L,Flags.getNames('reflection', 'refraction'))
    roomDataFlags = Flags(0L,Flags.getNames(
        (6,'hasImageSpace'),
        (7,'hasLightingTemplate'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelFid('NAME','base'),
        MelOptStruct('XMBO','3f','boundHalfExtentsX','boundHalfExtentsY','boundHalfExtentsZ'),
        MelOptStruct('XPRM','fffffffI','primitiveBoundX','primitiveBoundY','primitiveBoundZ',
                     'primitiveColorRed','primitiveColorGreen','primitiveColorBlue',
                     'primitiveUnknown','primitiveType'),
        MelBase('XORD','xord_p'),
        MelOptStruct('XOCP','9f','occlusionPlaneWidth','occlusionPlaneHeight',
                     'occlusionPlanePosX','occlusionPlanePosY','occlusionPlanePosZ',
                     'occlusionPlaneRot1','occlusionPlaneRot2','occlusionPlaneRot3',
                     'occlusionPlaneRot4'),
        MelArray('portalData',
            MelStruct('XPOD', '2I', (FID, 'portalOrigin'),
                      (FID, 'portalDestination')),
        ),
        MelOptStruct('XPTL','9f','portalWidth','portalHeight','portalPosX','portalPosY','portalPosZ',
                     'portalRot1','portalRot2','portalRot3','portalRot4'),
        MelGroup('roomData',
            MelStruct('XRMR','BB2s','linkedRoomsCount',(roomDataFlags,'roomFlags'),'unknown'),
            MelFid('LNAM', 'lightingTemplate'),
            MelFid('INAM', 'imageSpace'),
            MelFids('XLRM','linkedRoom'),
            ),
        MelBase('XMBP','multiboundPrimitiveMarker'),
        MelBase('XRGD','ragdollData'),
        MelBase('XRGB','ragdollBipedData'),
        MelOptFloat('XRDS', 'radius'),
        MelGroups('reflectedByWaters',
            MelStruct('XPWR', '2I', (FID, 'reference'),
                      (reflectFlags, 'reflection_type')),
        ),
        MelFids('XLTW','litWaters'),
        MelOptFid('XEMI', 'emittance'),
        MelOptStruct('XLIG', '4f4s', 'fov90Delta', 'fadeDelta',
                     'end_distance_cap', 'shadowDepthBias', 'unknown'),
        MelOptStruct('XALP','BB','cutoffAlpha','baseAlpha',),
        MelOptStruct('XTEL','I6fI',(FID,'destinationFid'),'destinationPosX',
                     'destinationPosY','destinationPosZ','destinationRotX',
                     'destinationRotY','destinationRotZ',
                     (_destinationFlags,'destinationFlags')),
        MelFids('XTNM','teleportMessageBox'),
        MelFid('XMBR','multiboundReference'),
        MelBase('XWCN', 'xwcn_p',),
        MelBase('XWCS', 'xwcs_p',),
        MelOptStruct('XWCU','3f4s3f4s','offsetX','offsetY','offsetZ','unknown',
                     'angleX','angleY','angleZ','unknown'),
        MelOptStruct('XCVL','4sf4s','unknown','angleX','unknown',),
        MelFid('XCZR','unknownRef'),
        MelBase('XCZA', 'xcza_p',),
        MelFid('XCZC','unknownRef2'),
        MelOptFloat('XSCL', ('scale',1.0)),
        MelFid('XSPC','spawnContainer'),
        MelGroup('activateParents',
            MelUInt8('XAPD', (_parentActivate, 'flags', None)),
            MelGroups('activateParentRefs',
                MelStruct('XAPR', 'If', (FID, 'reference'), 'delay'),
            ),
        ),
        MelFid('XLIB','leveledItemBaseObject'),
        MelSInt32('XLCM', 'levelModifier'),
        MelFid('XLCN','persistentLocation',),
        MelOptUInt32('XTRI', 'collisionLayer'),
        # {>>Lock Tab for REFR when 'Locked' is Unchecked this record is not present <<<}
        MelTruncatedStruct('XLOC', 'B3sIB3s8s', 'lockLevel', ('unused1',null3),
                           (FID, 'lockKey'), (_lockFlags, 'lockFlags'),
                           ('unused3', null3), ('unused4', null4 * 2),
                           old_versions={'B3sIB3s4s', 'B3sIB3s'}),
        MelFid('XEZN','encounterZone'),
        MelOptStruct('XNDP','IH2s',(FID,'navMesh'),'teleportMarkerTriangle','unknown'),
        MelFidList('XLRT','locationRefType',),
        MelNull('XIS2',),
        MelOwnership(),
        MelOptSInt32('XCNT', 'count'),
        MelOptFloat('XCHG', ('charge', None)),
        MelFid('XLRL','locationReference'),
        MelOptStruct('XESP','IB3s',(FID,'parent'),(_parentFlags,'parentFlags'),('unused6',null3)),
        MelGroups('linkedReference',
            MelStruct('XLKR', '2I', (FID, 'keywordRef'), (FID, 'linkedRef')),
        ),
        MelGroup('patrolData',
            MelFloat('XPRD', 'idleTime'),
            MelBase('XPPA','patrolScriptMarker'),
            MelFid('INAM', 'idle'),
            MelBase('SCHR','schr_p',),
            MelBase('SCTX','sctx_p',),
            MelGroups('topicData',
                MelStruct('PDTO', '2I', 'type', (FID,'data')),
            ),
        ),
        MelOptUInt32('XACT', (_actFlags, 'actFlags', 0L)),
        MelOptFloat('XHTW', 'headTrackingWeight'),
        MelOptFloat('XFVC', 'favorCost'),
        MelBase('ONAM','onam_p'),
        MelGroup('map_marker',
            MelBase('XMRK', 'marker_data'),
            MelOptUInt8('FNAM', (_marker_flags, 'marker_flags')),
            MelFull(),
            MelOptStruct('TNAM', 'Bs', 'marker_type', 'unused1'),
        ),
        MelFid('XATR', 'attachRef'),
        MelOptStruct('XLOD','3f',('lod1',None),('lod2',None),('lod3',None)),
        MelOptStruct('DATA','=6f',('posX',None),('posY',None),('posZ',None),
                     ('rotX',None),('rotY',None),('rotZ',None)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRegn(MelRecord):
    """Region."""
    classType = 'REGN'

    obflags = Flags(0L,Flags.getNames(
        ( 0,'conform'),
        ( 1,'paintVertices'),
        ( 2,'sizeVariance'),
        ( 3,'deltaX'),
        ( 4,'deltaY'),
        ( 5,'deltaZ'),
        ( 6,'Tree'),
        ( 7,'hugeRock'),))
    sdflags = Flags(0L,Flags.getNames(
        ( 0,'pleasant'),
        ( 1,'cloudy'),
        ( 2,'rainy'),
        ( 3,'snowy'),))
    rdatFlags = Flags(0L,Flags.getNames(
        ( 0,'Override'),))

    melSet = MelSet(
        MelEdid(),
        MelStruct('RCLR','3Bs','mapRed','mapBlue','mapGreen',('unused1',null1)),
        MelFid('WNAM','worldspace'),
        MelGroups('areas',
            MelUInt32('RPLI', 'edgeFalloff'),
            MelArray('points',
                MelStruct('RPLD', '2f', 'posX', 'posY'),
            ),
        ),
        MelGroups('entries',
            MelStruct('RDAT', 'I2B2s', 'entryType', (rdatFlags, 'flags'),
                      'priority', ('unused1', null2)),
            MelIcon(),
            MelRegnEntrySubrecord(7, MelFid('RDMO', 'music')),
            MelRegnEntrySubrecord(7, MelArray('sounds',
                MelStruct('RDSA', '2If', (FID, 'sound'), (sdflags, 'flags'),
                          'chance'),
            )),
            MelRegnEntrySubrecord(4, MelString('RDMP', 'mapName')),
            MelRegnEntrySubrecord(2, MelArray('objects',
                MelStruct(
                    'RDOT', 'IH2sf4B2H5f3H2s4s', (FID, 'objectId'),
                    'parentIndex', ('unk1', null2), 'density', 'clustering',
                    'minSlope', 'maxSlope', (obflags, 'flags'),
                    'radiusWRTParent', 'radius', 'minHeight', 'maxHeight',
                    'sink', 'sinkVar', 'sizeVar', 'angleVarX', 'angleVarY',
                    'angleVarZ', ('unk2', null2), ('unk3', null4)),
            )),
            MelRegnEntrySubrecord(6, MelArray('grasses',
                MelStruct('RDGS', 'I4s', (FID, 'grass'), ('unknown', null4)),
            )),
            MelRegnEntrySubrecord(3, MelArray('weatherTypes',
                MelStruct('RDWT', '3I', (FID, 'weather', None), 'chance',
                          (FID, 'global', None)),
            )),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRela(MelRecord):
    """Relationship."""
    classType = 'RELA'

    RelationshipFlags = Flags(0L,Flags.getNames(
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
        MelStruct('DATA','2IHsBI',(FID,'parent'),(FID,'child'),'rankType',
                  'unknown',(RelationshipFlags,'relaFlags',0L),(FID,'associationType'),),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRevb(MelRecord):
    """Reverb Parameters"""
    classType = 'REVB'

    melSet = MelSet(
        MelEdid(),
        MelStruct('DATA','2H4b6B','decayTimeMS','hfReferenceHZ','roomFilter',
                  'hfRoomFilter','reflections','reverbAmp','decayHFRatio',
                  'reflectDelayMS','reverbDelayMS','diffusion','density',
                  'unknown',),
        )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreRfct(MelRecord):
    """Visual Effect."""
    classType = 'RFCT'

    RfctTypeFlags = Flags(0L,Flags.getNames(
        (0, 'rotateToFaceTarget'),
        (1, 'attachToCamera'),
        (2, 'inheritRotation'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelStruct('DATA','3I',(FID,'impactSet'),(FID,'impactSet'),(RfctTypeFlags,'flags',0L),),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreScen(MelRecord):
    """Scene."""
    classType = 'SCEN'

    ScenFlags5 = Flags(0L,Flags.getNames(
            (0, 'unknown1'),
            (1, 'unknown2'),
            (2, 'unknown3'),
            (3, 'unknown4'),
            (4, 'unknown5'),
            (5, 'unknown6'),
            (6, 'unknown7'),
            (7, 'unknown8'),
            (8, 'unknown9'),
            (9, 'unknown10'),
            (10, 'unknown11'),
            (11, 'unknown12'),
            (12, 'unknown13'),
            (13, 'unknown14'),
            (14, 'unknown15'),
            (15, 'faceTarget'),
            (16, 'looping'),
            (17, 'headtrackPlayer'),
        ))

    ScenFlags3 = Flags(0L,Flags.getNames(
            (0, 'deathPauseunsused'),
            (1, 'deathEnd'),
            (2, 'combatPause'),
            (3, 'combatEnd'),
            (4, 'dialoguePause'),
            (5, 'dialogueEnd'),
            (6, 'oBS_COMPause'),
            (7, 'oBS_COMEnd'),
        ))

    ScenFlags2 = Flags(0L,Flags.getNames(
            (0, 'noPlayerActivation'),
            (1, 'optional'),
        ))

    ScenFlags1 = Flags(0L,Flags.getNames(
            (0, 'beginonQuestStart'),
            (1, 'stoponQuestEnd'),
            (2, 'unknown3'),
            (3, 'repeatConditionsWhileTrue'),
            (4, 'interruptible'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelUInt32('FNAM', (ScenFlags1, 'flags', 0L)),
        MelGroups('phases',
            MelNull('HNAM'),
            MelString('NAM0','name',),
            MelGroup('startConditions',
                MelConditions(),
            ),
            MelNull('NEXT'),
            MelGroup('completionConditions',
                MelConditions(),
            ),
            # The next three are all leftovers
            MelGroup('unused',
                MelBase('SCHR','schr_p'),
                MelBase('SCDA','scda_p'),
                MelBase('SCTX','sctx_p'),
                MelBase('QNAM','qnam_p'),
                MelBase('SCRO','scro_p'),
            ),
            MelNull('NEXT'),
            MelGroup('unused',
                MelBase('SCHR','schr_p'),
                MelBase('SCDA','scda_p'),
                MelBase('SCTX','sctx_p'),
                MelBase('QNAM','qnam_p'),
                MelBase('SCRO','scro_p'),
            ),
            MelUInt32('WNAM', 'editorWidth'),
            MelNull('HNAM'),
        ),
        MelGroups('actors',
            MelUInt32('ALID', 'actorID'),
            MelUInt32('LNAM', (ScenFlags2, 'scenFlags2' ,0L)),
            MelUInt32('DNAM', (ScenFlags3, 'flags3' ,0L)),
        ),
        MelGroups('actions',
            MelUInt16('ANAM', 'actionType'),
            MelString('NAM0','name',),
            MelUInt32('ALID', 'actorID',),
            MelBase('LNAM','lnam_p',),
            MelUInt32('INAM', 'index'),
            MelUInt32('FNAM', (ScenFlags5,'flags',0L)),
            MelUInt32('SNAM', 'startPhase'),
            MelUInt32('ENAM', 'endPhase'),
            MelFloat('SNAM', 'timerSeconds'),
            MelFids('PNAM','packages'),
            MelFid('DATA','topic'),
            MelUInt32('HTID', 'headtrackActorID'),
            MelFloat('DMAX', 'loopingMax'),
            MelFloat('DMIN', 'loopingMin'),
            MelUInt32('DEMO', 'emotionType'),
            MelUInt32('DEVA', 'emotionValue'),
            MelGroup('unused', # leftover
                MelBase('SCHR','schr_p'),
                MelBase('SCDA','scda_p'),
                MelBase('SCTX','sctx_p'),
                MelBase('QNAM','qnam_p'),
                MelBase('SCRO','scro_p'),
            ),
            MelNull('ANAM'),
        ),
        # The next three are all leftovers
        MelGroup('unused',
            MelBase('SCHR','schr_p'),
            MelBase('SCDA','scda_p'),
            MelBase('SCTX','sctx_p'),
            MelBase('QNAM','qnam_p'),
            MelBase('SCRO','scro_p'),
        ),
        MelNull('NEXT'),
        MelGroup('unused',
            MelBase('SCHR','schr_p'),
            MelBase('SCDA','scda_p'),
            MelBase('SCTX','sctx_p'),
            MelBase('QNAM','qnam_p'),
            MelBase('SCRO','scro_p'),
        ),
        MelFid('PNAM','quest',),
        MelUInt32('INAM', 'lastActionIndex'),
        MelBase('VNAM','vnam_p'),
        MelConditions(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreScrl(MelRecord,MreHasEffects):
    """Scroll."""
    classType = 'SCRL'

    ScrollDataFlags = Flags(0L,Flags.getNames(
        (0, 'manualCostCalc'),
        (17, 'pcStartSpell'),
        (19, 'areaEffectIgnoresLOS'),
        (20, 'ignoreResistance'),
        (21, 'noAbsorbReflect'),
        (23, 'noDualCastModification'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelKeywords(),
        MelFids('MDOB','menuDisplayObject'),
        MelFid('ETYP','equipmentType',),
        MelLString('DESC','description'),
        MelModel(),
        MelDestructible(),
        MelFid('YNAM','pickupSound',),
        MelFid('ZNAM','dropSound',),
        MelStruct('DATA','If','itemValue','itemWeight',),
        MelStruct('SPIT','IIIfIIffI','baseCost',(ScrollDataFlags,'dataFlags',0L),
                  'scrollType','chargeTime','castType','targetType',
                  'castDuration','range',(FID,'halfCostPerk'),),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreShou(MelRecord):
    """Shout."""
    classType = 'SHOU'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelFid('MDOB','menuDisplayObject'),
        MelLString('DESC','description'),
        MelGroups('wordsOfPower',
            MelStruct('SNAM','2If',(FID,'word',None),(FID,'spell',None),'recoveryTime',),
        ),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSlgm(MelRecord):
    """Soul Gem."""
    classType = 'SLGM'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelIcons(),
        MelDestructible(),
        MelFid('YNAM','pickupSound'),
        MelFid('ZNAM','dropSound'),
        MelKeywords(),
        MelStruct('DATA','If','value','weight'),
        MelUInt8('SOUL', ('soul',0)),
        MelUInt8('SLCP', ('capacity',1)),
        MelFid('NAM0','linkedTo'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSmbn(MelRecord):
    """Story Manager Branch Node."""
    classType = 'SMBN'

    SmbnNodeFlags = Flags(0L,Flags.getNames(
        (0,'Random'),
        (1,'noChildWarn'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelFid('PNAM','parent',),
        MelFid('SNAM','child',),
        MelConditionCounter(),
        MelConditions(),
        MelUInt32('DNAM', (SmbnNodeFlags, 'nodeFlags', 0L)),
        MelBase('XNAM','xnam_p'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSmen(MelRecord):
    """Story Manager Event Node."""
    classType = 'SMEN'

    SmenNodeFlags = Flags(0L,Flags.getNames(
        (0,'Random'),
        (1,'noChildWarn'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelFid('PNAM','parent',),
        MelFid('SNAM','child',),
        MelConditionCounter(),
        MelConditions(),
        MelUInt32('DNAM', (SmenNodeFlags, 'nodeFlags', 0L)),
        MelBase('XNAM','xnam_p'),
        MelString('ENAM','type'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSmqn(MelRecord):
    """Story Manager Quest Node."""
    classType = 'SMQN'

    # "Do all" = "Do all before repeating"
    SmqnQuestFlags = Flags(0L,Flags.getNames(
        (0,'doAll'),
        (1,'sharesEvent'),
        (2,'numQuestsToRun'),
    ))

    SmqnNodeFlags = Flags(0L,Flags.getNames(
        (0,'Random'),
        (1,'noChildWarn'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelFid('PNAM','parent',),
        MelFid('SNAM','child',),
        MelConditionCounter(),
        MelConditions(),
        MelStruct('DNAM','2H',(SmqnNodeFlags,'nodeFlags',0L),(SmqnQuestFlags,'questFlags',0L),),
        MelUInt32('XNAM', 'maxConcurrentQuests'),
        MelOptUInt32('MNAM', ('numQuestsToRun', None)),
        MelCounter(MelUInt32('QNAM', 'quest_count'), counts='quests'),
        MelGroups('quests',
            MelFid('NNAM','quest',),
            MelBase('FNAM','fnam_p'),
            MelOptFloat('RNAM', ('hoursUntilReset', None)),
        )
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSnct(MelRecord):
    """Sound Category."""
    classType = 'SNCT'

    SoundCategoryFlags = Flags(0L,Flags.getNames(
        (0,'muteWhenSubmerged'),
        (1,'shouldAppearOnMenu'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelUInt32('FNAM', (SoundCategoryFlags, 'flags', 0L)),
        MelFid('PNAM','parent',),
        MelUInt16('VNAM', 'staticVolumeMultiplier'),
        MelUInt16('UNAM', 'defaultMenuValue'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSndr(MelRecord):
    """Sound Descriptor."""
    classType = 'SNDR'

    melSet = MelSet(
        MelEdid(),
        MelBase('CNAM','cnam_p'),
        MelFid('GNAM','category',),
        MelFid('SNAM','altSoundFor',),
        MelGroups('sounds',
            MelString('ANAM', 'sound_file_name',),
        ),
        MelFid('ONAM','outputModel',),
        MelLString('FNAM','string'),
        MelConditions(),
        MelStruct('LNAM','sBsB',('unkSndr1',null1),'looping',
                  ('unkSndr2',null1),'rumbleSendValue',),
        MelStruct('BNAM','2b2BH','pctFrequencyShift','pctFrequencyVariance','priority',
                  'dbVariance','staticAttenuation',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSopm(MelRecord):
    """Sound Output Model."""
    classType = 'SOPM'

    SopmFlags = Flags(0L,Flags.getNames(
            (0, 'attenuatesWithDistance'),
            (1, 'allowsRumble'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelStruct('NAM1','B2sB',(SopmFlags,'flags',0L),'unknown1','reverbSendpct',),
        MelBase('FNAM','fnam_p'),
        MelUInt32('MNAM', 'outputType'),
        MelBase('CNAM','cnam_p'),
        MelBase('SNAM','snam_p'),
        MelStruct('ONAM', '=24B', 'ch0_l', 'ch0_r', 'ch0_c', 'ch0_lFE',
                  'ch0_rL', 'ch0_rR', 'ch0_bL', 'ch0_bR', 'ch1_l', 'ch1_r',
                  'ch1_c', 'ch1_lFE', 'ch1_rL', 'ch1_rR', 'ch1_bL', 'ch1_bR',
                  'ch2_l', 'ch2_r', 'ch2_c', 'ch2_lFE', 'ch2_rL', 'ch2_rR',
                  'ch2_bL', 'ch2_bR'),
        MelStruct('ANAM','4s2f5B','unknown2','minDistance','maxDistance',
                  'curve1','curve2','curve3','curve4','curve5',
                   dumpExtra='extraData',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSoun(MelRecord):
    """Sound Marker."""
    classType = 'SOUN'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelString('FNAM','soundFileUnused'), # leftover
        MelBase('SNDD','soundDataUnused'), # leftover
        MelFid('SDSC','soundDescriptor'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSpel(MelRecord,MreHasEffects):
    """Spell."""
    classType = 'SPEL'

    # currently not used for Skyrim needs investigated to see if TES5Edit does this
    # class SpellFlags(Flags):
    #     """For SpellFlags, immuneSilence activates bits 1 AND 3."""
    #     def __setitem__(self,index,value):
    #         setter = Flags.__setitem__
    #         setter(self,index,value)
    #         if index == 1:
    #             setter(self,3,value)

    SpelTypeFlags = Flags(0L,Flags.getNames(
        (0, 'manualCostCalc'),
        (17, 'pcStartSpell'),
        (19, 'areaEffectIgnoresLOS'),
        (20, 'ignoreResistance'),
        (21, 'noAbsorbReflect'),
        (23, 'noDualCastModification'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelFull(),
        MelKeywords(),
        MelFid('MDOB', 'menuDisplayObject'),
        MelFid('ETYP', 'equipmentType'),
        MelLString('DESC','description'),
        MelStruct('SPIT','IIIfIIffI','cost',(SpelTypeFlags,'dataFlags',0L),
                  'scrollType','chargeTime','castType','targetType',
                  'castDuration','range',(FID,'halfCostPerk'),),
        MelEffects(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreSpgd(MelRecord):
    """Shader Particle Geometry."""
    classType = 'SPGD'

    _SpgdDataFlags = Flags(0L, Flags.getNames('rain', 'snow'))

    melSet = MelSet(
        MelEdid(),
        MelTruncatedStruct(
            'DATA', '7f4If', 'gravityVelocity', 'rotationVelocity',
            'particleSizeX', 'particleSizeY', 'centerOffsetMin',
            'centerOffsetMax', 'initialRotationRange', 'numSubtexturesX',
            'numSubtexturesY', (_SpgdDataFlags, 'typeFlags', 0L),
            ('boxSize', 0), ('particleDensity', 0), old_versions={'7f3I'}),
        MelIcon(),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreStat(MelRecord):
    """Static."""
    classType = 'STAT'

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelModel(),
        MelStruct('DNAM', 'fI', 'maxAngle30to120', (FID, 'material'),),
        # Contains null-terminated mesh filename followed by random data
        # up to 260 bytes and repeats 4 times
        MelBase('MNAM', 'distantLOD'),
        MelBase('ENAM', 'unknownENAM'),
    )
    __slots__ = melSet.getSlotsUsed()

# MNAM Should use a custom unpacker if needed for the patcher otherwise MelBase
#------------------------------------------------------------------------------
class MreTact(MelRecord):
    """Talking Activator."""
    classType = 'TACT'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel(),
        MelDestructible(),
        MelKeywords(),
        MelBase('PNAM','pnam_p'),
        MelOptFid('SNAM', 'soundLoop'),
        MelBase('FNAM','fnam_p'),
        MelOptFid('VNAM', 'voiceType'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTree(MelRecord):
    """Tree."""
    classType = 'TREE'

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelModel(),
        MelFid('PFIG','harvestIngredient'),
        MelFid('SNAM','harvestSound'),
        MelStruct('PFPC','4B','spring','summer','fall','wsinter',),
        MelFull(),
        MelStruct('CNAM','ff32sff','trunkFlexibility','branchFlexibility',
                  'unknown','leafAmplitude','leafFrequency',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreTxst(MelRecord):
    """Texture Set."""
    classType = 'TXST'

    TxstTypeFlags = Flags(0L,Flags.getNames(
        (0, 'noSpecularMap'),
        (1, 'facegenTextures'),
        (2, 'hasModelSpaceNormalMap'),
    ))

    melSet = MelSet(
        MelEdid(),
        MelBounds(),
        MelGroups('destructionData',
            MelString('TX00','difuse'),
            MelString('TX01','normalGloss'),
            MelString('TX02','enviroMaskSubSurfaceTint'),
            MelString('TX03','glowDetailMap'),
            MelString('TX04','height'),
            MelString('TX05','environment'),
            MelString('TX06','multilayer'),
            MelString('TX07','backlightMaskSpecular'),
        ),
        MelDecalData(),
        MelUInt16('DNAM', (TxstTypeFlags, 'flags', 0L)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreVtyp(MelRecord):
    """Voice Type."""
    classType = 'VTYP'

    VtypTypeFlags = Flags(0L,Flags.getNames(
            (0, 'allowDefaultDialog'),
            (1, 'female'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelUInt8('DNAM', (VtypTypeFlags, 'flags', 0L)),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWatr(MelRecord):
    """Water."""
    classType = 'WATR'

    WatrTypeFlags = Flags(0L,Flags.getNames(
            (0, 'causesDamage'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelGroups('unused',
            MelString('NNAM','noiseMap',),
        ),
        MelUInt8('ANAM', 'opacity'),
        MelUInt8('FNAM', (WatrTypeFlags, 'flags', 0L)),
        MelBase('MNAM','unused1'),
        MelFid('TNAM','material',),
        MelFid('SNAM','openSound',),
        MelFid('XNAM','spell',),
        MelFid('INAM','imageSpace',),
        MelUInt16('DATA', 'damagePerSecond'),
        MelStruct('DNAM','7f4s2f3Bs3Bs3Bs4s43f','unknown1','unknown2','unknown3',
                  'unknown4','specularPropertiesSunSpecularPower',
                  'waterPropertiesReflectivityAmount',
                  'waterPropertiesFresnelAmount',('unknown5',null4),
                  'fogPropertiesAboveWaterFogDistanceNearPlane',
                  'fogPropertiesAboveWaterFogDistanceFarPlane',
                  # Shallow Color
                  'red_sc','green_sc','blue_sc','unknown_sc',
                  # Deep Color
                  'red_dc','green_dc','blue_dc','unknown_dc',
                  # Reflection Color
                  'red_rc','green_rc','blue_rc','unknown_rc',
                  ('unknown6',null4),'unknown7','unknown8','unknown9','unknown10',
                  'displacementSimulatorStartingSize',
                  'displacementSimulatorForce','displacementSimulatorVelocity',
                  'displacementSimulatorFalloff','displacementSimulatorDampner',
                  'unknown11','noisePropertiesNoiseFalloff',
                  'noisePropertiesLayerOneWindDirection',
                  'noisePropertiesLayerTwoWindDirection',
                  'noisePropertiesLayerThreeWindDirection',
                  'noisePropertiesLayerOneWindSpeed',
                  'noisePropertiesLayerTwoWindSpeed',
                  'noisePropertiesLayerThreeWindSpeed',
                  'unknown12','unknown13','fogPropertiesAboveWaterFogAmount',
                  'unknown14','fogPropertiesUnderWaterFogAmount',
                  'fogPropertiesUnderWaterFogDistanceNearPlane',
                  'fogPropertiesUnderWaterFogDistanceFarPlane',
                  'waterPropertiesRefractionMagnitude',
                  'specularPropertiesSpecularPower',
                  'unknown15','specularPropertiesSpecularRadius',
                  'specularPropertiesSpecularBrightness',
                  'noisePropertiesLayerOneUVScale',
                  'noisePropertiesLayerTwoUVScale',
                  'noisePropertiesLayerThreeUVScale',
                  'noisePropertiesLayerOneAmplitudeScale',
                  'noisePropertiesLayerTwoAmplitudeScale',
                  'noisePropertiesLayerThreeAmplitudeScale',
                  'waterPropertiesReflectionMagnitude',
                  'specularPropertiesSunSparkleMagnitude',
                  'specularPropertiesSunSpecularMagnitude',
                  'depthPropertiesReflections','depthPropertiesRefraction',
                  'depthPropertiesNormals','depthPropertiesSpecularLighting',
                  'specularPropertiesSunSparklePower',),
        MelBase('GNAM','unused2'),
        # Linear Velocity
        MelStruct('NAM0','3f','linv_x','linv_y','linv_z',),
        # Angular Velocity
        MelStruct('NAM1','3f','andv_x','andv_y','andv_z',),
        MelString('NAM2','noiseTexture'),
        MelString('NAM3','unused3'),
        MelString('NAM4','unused4'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWeap(MelRecord):
    """Weapon"""
    classType = 'WEAP'

    WeapFlags3 = Flags(0L,Flags.getNames(
        (0, 'onDeath'),
    ))

    WeapFlags2 = Flags(0L,Flags.getNames(
            (0, 'playerOnly'),
            (1, 'nPCsUseAmmo'),
            (2, 'noJamAfterReloadunused'),
            (3, 'unknown4'),
            (4, 'minorCrime'),
            (5, 'rangeFixed'),
            (6, 'notUsedinNormalCombat'),
            (7, 'unknown8'),
            (8, 'don'),
            (9, 'unknown10'),
            (10, 'rumbleAlternate'),
            (11, 'unknown12'),
            (12, 'nonhostile'),
            (13, 'boundWeapon'),
        ))

    WeapFlags1 = Flags(0L,Flags.getNames(
            (0, 'ignoresNormalWeaponResistance'),
            (1, 'automaticunused'),
            (2, 'hasScopeunused'),
            (3, 'can'),
            (4, 'hideBackpackunused'),
            (5, 'embeddedWeaponunused'),
            (6, 'don'),
            (7, 'nonplayable'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelVmad(),
        MelBounds(),
        MelFull(),
        MelModel('model1','MODL'),
        MelIcons(),
        MelFid('EITM','enchantment',),
        MelOptUInt16('EAMT', 'enchantPoints'),
        MelDestructible(),
        MelFid('ETYP','equipmentType',),
        MelFid('BIDS','blockBashImpactDataSet',),
        MelFid('BAMT','alternateBlockMaterial',),
        MelFid('YNAM','pickupSound',),
        MelFid('ZNAM','dropSound',),
        MelKeywords(),
        MelLString('DESC','description'),
        MelModel('model2','MOD3'),
        MelBase('NNAM','unused1'),
        MelFid('INAM','impactDataSet',),
        MelFid('WNAM','firstPersonModelObject',),
        MelFid('SNAM','attackSound',),
        MelFid('XNAM','attackSound2D',),
        MelFid('NAM7','attackLoopSound',),
        MelFid('TNAM','attackFailSound',),
        MelFid('UNAM','idleSound',),
        MelFid('NAM9','equipSound',),
        MelFid('NAM8','unequipSound',),
        MelStruct('DATA','IfH','value','weight','damage',),
        MelStruct('DNAM','B3s2fH2sf4s4B2f2I5f12si8si4sf','animationType',
                  ('dnamUnk1',null3),'speed','reach',
                  (WeapFlags1,'dnamFlags1',None),('dnamUnk2',null2),'sightFOV',
                  ('dnamUnk3',null4),'baseVATSToHitChance','attackAnimation',
                  'numProjectiles','embeddedWeaponAVunused','minRange',
                  'maxRange','onHit',(WeapFlags2,'dnamFlags2',None),
                  'animationAttackMultiplier',('dnamUnk4',0.0),
                  'rumbleLeftMotorStrength','rumbleRightMotorStrength',
                  'rumbleDuration',('dnamUnk5',null4+null4+null4),'skill',
                  ('dnamUnk6',null4+null4),'resist',('dnamUnk7',null4),'stagger',),
        MelStruct('CRDT','H2sfB3sI','critDamage',('crdtUnk1',null2),'criticalMultiplier',
                  (WeapFlags3,'criticalFlags',0L),('crdtUnk2',null3),(FID,'criticalEffect',None),),
        MelUInt32('VNAM', 'detectionSoundLevel'),
        MelFid('CNAM','template',),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWoop(MelRecord):
    """Word of Power."""
    classType = 'WOOP'

    melSet = MelSet(
        MelEdid(),
        MelFull(),
        MelLString('TNAM','translation'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
class MreWrld(MelRecord):
    """Worldspace."""
    classType = 'WRLD'

    WrldFlags2 = Flags(0L,Flags.getNames(
            (0, 'smallWorld'),
            (1, 'noFastTravel'),
            (2, 'unknown3'),
            (3, 'noLODWater'),
            (4, 'noLandscape'),
            (5, 'unknown6'),
            (6, 'fixedDimensions'),
            (7, 'noGrass'),
        ))

    WrldFlags1 = Flags(0L,Flags.getNames(
            (0, 'useLandData'),
            (1, 'useLODData'),
            (2, 'don'),
            (3, 'useWaterData'),
            (4, 'useClimateData'),
            (5, 'useImageSpaceDataunused'),
            (6, 'useSkyCell'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelGroups('unusedRNAM', # leftover
            MelBase('RNAM','unknown',),
        ),
        MelBase('MHDT','maxHeightData'),
        MelFull(),
        # Fixed Dimensions Center Cell
        MelOptStruct('WCTR','2h',('fixedX', 0),('fixedY', 0),),
        MelFid('LTMP','interiorLighting',),
        MelFid('XEZN','encounterZone',),
        MelFid('XLCN','location',),
        MelGroup('parent',
            MelFid('WNAM','worldspace',),
            MelStruct('PNAM','Bs',(WrldFlags1,'parentFlags',0L),'unknown',),
        ),
        MelFid('CNAM','climate',),
        MelFid('NAM2','water',),
        MelFid('NAM3','lODWaterType',),
        MelOptFloat('NAM4', ('lODWaterHeight', 0.0)),
        MelOptStruct('DNAM','2f',('defaultLandHeight', 0.0),
                     ('defaultWaterHeight', 0.0),),
        MelIcon('mapImage'),
        MelModel('cloudModel','MODL',),
        MelTruncatedStruct('MNAM', '2i4h3f', 'usableDimensionsX',
                           'usableDimensionsY', 'cellCoordinatesX',
                           'cellCoordinatesY', 'seCellX', 'seCellY',
                           'cameraDataMinHeight', 'cameraDataMaxHeight',
                           'cameraDataInitialPitch', is_optional=True,
                           old_versions={'2i4h2f', '2i4h'}),
        MelStruct('ONAM','4f','worldMapScale','cellXOffset','cellYOffset',
                  'cellZOffset',),
        MelFloat('NAMA', 'distantLODMultiplier'),
        MelUInt8('DATA', (WrldFlags2, 'dataFlags', 0L)),
        # {>>> Object Bounds doesn't show up in CK <<<}
        MelStruct('NAM0','2f','minObjX','minObjY',),
        MelStruct('NAM9','2f','maxObjX','maxObjY',),
        MelFid('ZNAM','music',),
        MelString('NNAM','canopyShadowunused'),
        MelString('XNAM','waterNoiseTexture'),
        MelString('TNAM','hDLODDiffuseTexture'),
        MelString('UNAM','hDLODNormalTexture'),
        MelString('XWEM','waterEnvironmentMapunused'),
        MelBase('OFST','unknown'),
    )
    __slots__ = melSet.getSlotsUsed()

#------------------------------------------------------------------------------
# Many Things Marked MelBase that need updated
class MreWthr(MelRecord):
    """Weather"""
    classType = 'WTHR'

    WthrFlags2 = Flags(0L,Flags.getNames(
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

    WthrFlags1 = Flags(0L,Flags.getNames(
            (0, 'weatherPleasant'),
            (1, 'weatherCloudy'),
            (2, 'weatherRainy'),
            (3, 'weatherSnow'),
            (4, 'skyStaticsAlwaysVisible'),
            (5, 'skyStaticsFollowsSunPosition'),
        ))

    melSet = MelSet(
        MelEdid(),
        MelString('\x300TX','cloudTextureLayer_0'),
        MelString('\x310TX','cloudTextureLayer_1'),
        MelString('\x320TX','cloudTextureLayer_2'),
        MelString('\x330TX','cloudTextureLayer_3'),
        MelString('\x340TX','cloudTextureLayer_4'),
        MelString('\x350TX','cloudTextureLayer_5'),
        MelString('\x360TX','cloudTextureLayer_6'),
        MelString('\x370TX','cloudTextureLayer_7'),
        MelString('\x380TX','cloudTextureLayer_8'),
        MelString('\x390TX','cloudTextureLayer_9'),
        MelString('\x3A0TX','cloudTextureLayer_10'),
        MelString('\x3B0TX','cloudTextureLayer_11'),
        MelString('\x3C0TX','cloudTextureLayer_12'),
        MelString('\x3D0TX','cloudTextureLayer_13'),
        MelString('\x3E0TX','cloudTextureLayer_14'),
        MelString('\x3F0TX','cloudTextureLayer_15'),
        MelString('\x400TX','cloudTextureLayer_16'),
        MelString('A0TX','cloudTextureLayer_17'),
        MelString('B0TX','cloudTextureLayer_18'),
        MelString('C0TX','cloudTextureLayer_19'),
        MelString('D0TX','cloudTextureLayer_20'),
        MelString('E0TX','cloudTextureLayer_21'),
        MelString('F0TX','cloudTextureLayer_22'),
        MelString('G0TX','cloudTextureLayer_23'),
        MelString('H0TX','cloudTextureLayer_24'),
        MelString('I0TX','cloudTextureLayer_25'),
        MelString('J0TX','cloudTextureLayer_26'),
        MelString('K0TX','cloudTextureLayer_27'),
        MelString('L0TX','cloudTextureLayer_28'),
        MelBase('DNAM','dnam_p'),
        MelBase('CNAM','cnam_p'),
        MelBase('ANAM','anam_p'),
        MelBase('BNAM','bnam_p'),
        MelBase('LNAM','lnam_p'),
        MelFid('MNAM','precipitationType',),
        MelFid('NNAM','visualEffect',),
        MelBase('ONAM','onam_p'),
        MelBase('RNAM','cloudSpeedY'),
        MelBase('QNAM','cloudSpeedX'),
        MelArray('cloudColors',
            MelWthrColors('PNAM'),
        ),
        MelArray('cloudAlphas',
            MelStruct('JNAM', '4f', 'sunAlpha', 'dayAlpha', 'setAlpha',
                      'nightAlpha'),
        ),
        MelArray('daytimeColors',
            MelWthrColors('NAM0'),
        ),
        MelStruct('FNAM','8f','dayNear','dayFar','nightNear','nightFar',
                  'dayPower','nightPower','dayMax','nightMax',),
        MelStruct('DATA','B2s16B','windSpeed',('unknown',null2),'transDelta',
                  'sunGlare','sunDamage','precipitationBeginFadeIn',
                  'precipitationEndFadeOut','thunderLightningBeginFadeIn',
                  'thunderLightningEndFadeOut','thunderLightningFrequency',
                  (WthrFlags1,'wthrFlags1',0L),'red','green','blue',
                  'visualEffectBegin','visualEffectEnd',
                  'windDirection','windDirectionRange',),
        MelUInt32('NAM1', (WthrFlags2, 'wthrFlags2', 0L)),
        MelGroups('sounds',
            MelStruct('SNAM', '2I', (FID, 'sound'), 'type'),
        ),
        MelFids('TNAM','skyStatics',),
        MelStruct('IMSP','4I',(FID,'imageSpacesSunrise'),(FID,'imageSpacesDay'),
                  (FID,'imageSpacesSunset'),(FID,'imageSpacesNight'),),
        MelGroups('wthrAmbientColors',
            MelTruncatedStruct(
                'DALC', '4B4B4B4B4B4B4Bf', 'redXplus', 'greenXplus',
                'blueXplus', 'unknownXplus', 'redXminus', 'greenXminus',
                'blueXminus', 'unknownXminus', 'redYplus', 'greenYplus',
                'blueYplus', 'unknownYplus', 'redYminus', 'greenYminus',
                'blueYminus', 'unknownYminus', 'redZplus', 'greenZplus',
                'blueZplus', 'unknownZplus', 'redZminus', 'greenZminus',
                'blueZminus', 'unknownZminus', 'redSpec', 'greenSpec',
                'blueSpec', 'unknownSpec', 'fresnelPower',
                old_versions={'4B4B4B4B4B4B'}),
        ),
        MelBase('NAM2','nam2_p'),
        MelBase('NAM3','nam3_p'),
        MelModel('aurora','MODL'),
    )
    __slots__ = melSet.getSlotsUsed()
