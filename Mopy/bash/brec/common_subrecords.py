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
"""Builds on the basic elements defined in base_elements.py to provide
definitions for some commonly needed subrecords."""
from collections import defaultdict
from itertools import chain

from .advanced_elements import AttrValDecider, MelArray, MelTruncatedStruct, \
    MelUnion, PartialLoadDecider, FlagDecider, MelSorted
from .basic_elements import MelBase, MelFid, MelGroup, MelGroups, MelLString, \
    MelNull, MelSequential, MelString, MelStruct, MelUInt32, MelOptStruct, \
    MelFloat, MelReadOnly, MelFids, MelUInt32Flags, MelUInt8Flags, MelSInt32, \
    MelStrings, MelUInt8, MelFidList
from .utils_constants import _int_unpacker, FID, null1
from ..bolt import Flags, encode, struct_pack, struct_unpack, unpack_byte, \
    dict_sort
from ..exception import ModError, ModSizeError

#------------------------------------------------------------------------------
class MelActionFlags(MelUInt32Flags):
    """XACT (Action Flags) subrecord for REFR records."""
    _act_flags = Flags(0, Flags.getNames(u'act_use_default', u'act_activate',
        u'act_open', u'act_open_by_default'))

    def __init__(self):
        super(MelActionFlags, self).__init__(b'XACT', u'action_flags',
                                             self._act_flags)

    ##: HACK - right solution is having None as the default for flags combined
    # with the ability to mark subrecords as required (e.g. for QSDT)
    def pack_subrecord_data(self, record):
        flag_val = getattr(record, self.attr)
        return (self._packer(flag_val.dump())
                if flag_val != self._flag_default else None)

#------------------------------------------------------------------------------
class MelActivateParents(MelGroup):
    """XAPD/XAPR (Activate Parents) subrecords for REFR records."""
    _ap_flags = Flags(0, Flags.getNames(u'parent_activate_only'),
        unknown_is_unused=True)

    def __init__(self):
        super(MelActivateParents, self).__init__(u'activate_parents',
            MelUInt8Flags(b'XAPD', u'activate_parent_flags', self._ap_flags),
            MelSorted(MelGroups(u'activate_parent_refs',
                MelStruct(b'XAPR', [u'I', u'f'], (FID, u'ap_reference'), u'ap_delay'),
            ), sort_by_attrs=u'ap_reference'),
        )

#------------------------------------------------------------------------------
class MelBounds(MelGroup):
    """Wrapper around MelGroup for the common task of defining OBND - Object
    Bounds. Uses MelGroup to avoid merging them when importing."""
    def __init__(self):
        super(MelBounds, self).__init__(u'bounds',
            MelStruct(b'OBND', [u'6h'], u'boundX1', u'boundY1', u'boundZ1',
                      u'boundX2', u'boundY2', u'boundZ2')
        )

#------------------------------------------------------------------------------
class MelCtda(MelUnion):
    """Handles a condition. The difficulty here is that the type of its
    parameters depends on its function index. We handle it by building what
    amounts to a decision tree using MelUnions."""
    # 0 = Unknown/Ignored, 1 = Int, 2 = FormID, 3 = Float
    _param_types = {0: u'4s', 1: u'i', 2: u'I', 3: u'f'}
    # This is technically a lot more complex (the highest three bits also
    # encode the comparison operator), but we only care about use_global, so we
    # can treat the rest as unknown flags and just carry them forward
    _ctda_type_flags = Flags(0, Flags.getNames(
        u'do_or', u'use_aliases', u'use_global', u'use_packa_data',
        u'swap_subject_and_target'))

    def __init__(self, ctda_sub_sig=b'CTDA', suffix_fmt=[],
                 suffix_elements=None, old_suffix_fmts=None):
        """Creates a new MelCtda instance with the specified properties.

        :param ctda_sub_sig: The signature of this subrecord. Probably
            b'CTDA'.
        :param suffix_fmt: The struct format string to use, starting after the
            first two parameters.
        :param suffix_elements: The struct elements to use, starting after the
            first two parameters.
        :param old_suffix_fmts: A set of old versions to pass to
            MelTruncatedStruct. Must conform to the same syntax as suffix_fmt.
            May be empty.
        :type old_suffix_fmts: set[str]"""
        if old_suffix_fmts is None: old_suffix_fmts = set()
        if suffix_elements is None: suffix_elements = []
        from .. import bush
        super(MelCtda, self).__init__({
            # Build a (potentially truncated) struct for each function index
            func_index: self._build_struct(func_data, ctda_sub_sig, suffix_fmt,
                                           suffix_elements, old_suffix_fmts)
            for func_index, func_data
            in bush.game.condition_function_data.items()
        }, decider=PartialLoadDecider(
            # Skip everything up to the function index in one go, we'll be
            # discarding this once we rewind anyways.
            loader=MelStruct(ctda_sub_sig, [u'8s', u'H'], u'ctda_ignored', u'ifunc'),
            decider=AttrValDecider(u'ifunc'),
        ))
        self._ctda_mel = next(iter(self.element_mapping.values())) # type: MelStruct

    # Helper methods - Note that we skip func_data[0]; the first element is
    # the function name, which is only needed for puny human brains
    def _build_struct(self, func_data, ctda_sub_sig, suffix_fmt,
                      suffix_elements, old_suffix_fmts):
        """Builds up a struct from the specified jungle of parameters. Mostly
        inherited from __init__, see there for docs."""
        # The '4s' here can actually be a float or a FormID. We do *not* want
        # to handle this via MelUnion, because the deep nesting is going to
        # cause exponential growth and bring PBash down to a crawl.
        prefix_fmt = [u'B', u'3s', u'4s', u'H', u'2s']
        prefix_elements = [(self._ctda_type_flags, u'operFlag'),
                           u'unused1', u'compValue',
                           u'ifunc', u'unused2']
        # Builds an argument tuple to use for formatting the struct format
        # string from above plus the suffix we got passed in
        fmt_list = [self._param_types[func_param] for func_param in
                    func_data[1:]]
        shared_params = ([ctda_sub_sig, (prefix_fmt + fmt_list + suffix_fmt)] +
                         self._build_params(func_data, prefix_elements,
                                            suffix_elements))
        # Only use MelTruncatedStruct if we have old versions, save the
        # overhead otherwise
        if old_suffix_fmts:
            full_old_versions = {
                u''.join(prefix_fmt + fmt_list + ([f] if f else [])) for f in
                old_suffix_fmts}
            return MelTruncatedStruct(*shared_params,
                                      old_versions=full_old_versions)
        return MelStruct(*shared_params)

    @staticmethod
    def _build_params(func_data, prefix_elements, suffix_elements):
        """Builds a list of struct elements to pass to MelTruncatedStruct."""
        # First, build up a list of the parameter elemnts to use
        func_elements = [
            (FID, u'param%u' % i) if func_param == 2 else u'param%u' % i
            for i, func_param in enumerate(func_data[1:], start=1)]
        # Then, combine the suffix, parameter and suffix elements
        return prefix_elements + func_elements + suffix_elements

    # Nesting workarounds -----------------------------------------------------
    # To avoid having to nest MelUnions too deeply - hurts performance even
    # further (see below) plus grows exponentially
    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        super(MelCtda, self).load_mel(record, ins, sub_type, size_, *debug_strs)
        # See _build_struct comments above for an explanation of this
        record.compValue = struct_unpack(u'fI'[record.operFlag.use_global],
                                         record.compValue)[0]

    def mapFids(self, record, function, save=False):
        super(MelCtda, self).mapFids(record, function, save)
        if record.operFlag.use_global:
            new_comp_val = function(record.compValue)
            if save: record.compValue = new_comp_val

    def dumpData(self, record, out):
        # See _build_struct comments above for an explanation of this
        record.compValue = struct_pack(u'fI'[record.operFlag.use_global],
                                       record.compValue)
        super(MelCtda, self).dumpData(record, out)

    # Some small speed hacks --------------------------------------------------
    # To avoid having to ask 100s of unions to each set their defaults,
    # declare they have fids, etc. Wastes a *lot* of time.
    def hasFids(self, formElements):
        self.fid_elements = list(self.element_mapping.values())
        formElements.add(self)

    def getLoaders(self, loaders):
        loaders[self._ctda_mel.mel_sig] = self

    def getSlotsUsed(self):
        return self.decider_result_attr, *self._ctda_mel.getSlotsUsed()

    def setDefault(self, record):
        next(iter(self.element_mapping.values())).setDefault(record)

class MelCtdaFo3(MelCtda):
    """Version of MelCtda that handles the additional complexities that were
    introduced in FO3 (and present in all games after that):

    1. The 'reference' element is a FormID if runOn is 2, otherwise it is an
    unused uint32. Except for the FNV functions IsFacingUp and IsLeftUp, where
    it is never a FormID. Yup.
    2. The 'GetVATSValue' function is horrible. The type of its second
    parameter depends on the value of the first one. And of course it can be a
    FormID."""
    # Maps param #1 value to the struct format string to use for GetVATSValue's
    # param #2 - missing means unknown/unused, aka 4s
    # Note 18, 19 and 20 were introduced in Skyrim, but since they are not used
    # in FO3 it's no problem to just keep them here
    _vats_param2_fmt = defaultdict(lambda: u'4s', {
        0: u'I', 1: u'I', 2: u'I', 3: u'I', 5: u'i', 6: u'I', 9: u'I',
        10: u'I', 15: u'I', 18: u'I', 19: u'I', 20: u'I'})
    # The param #1 values that indicate param #2 is a FormID
    _vats_param2_fid = {0, 1, 2, 3, 9, 10}

    def __init__(self, suffix_fmt=u'', suffix_elements=[],
                 old_suffix_fmts=set()):
        super(MelCtdaFo3, self).__init__(suffix_fmt=suffix_fmt,
                                         suffix_elements=suffix_elements,
                                         old_suffix_fmts=old_suffix_fmts)
        from .. import bush
        self._getvatsvalue_ifunc = bush.game.getvatsvalue_index
        self._ignore_ifuncs = ({106, 285} if bush.game.fsName == u'FalloutNV'
                               else set()) # 106 == IsFacingUp, 285 == IsLeftUp

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        super(MelCtdaFo3, self).load_mel(record, ins, sub_type, size_, *debug_strs)
        if record.ifunc == self._getvatsvalue_ifunc:
            record.param2 = struct_unpack(self._vats_param2_fmt[record.param1],
                                          record.param2)[0]

    def mapFids(self, record, function, save=False):
        super(MelCtdaFo3, self).mapFids(record, function, save)
        if record.runOn == 2 and record.ifunc not in self._ignore_ifuncs:
            new_reference = function(record.reference)
            if save: record.reference = new_reference
        if (record.ifunc == self._getvatsvalue_ifunc and
                record.param1 in self._vats_param2_fid):
            new_param2 = function(record.param2)
            if save: record.param2 = new_param2

    def dumpData(self, record, out):
        if record.ifunc == self._getvatsvalue_ifunc:
            record.param2 = struct_pack(self._vats_param2_fmt[record.param1],
                                        record.param2)
        super(MelCtdaFo3, self).dumpData(record, out)

#------------------------------------------------------------------------------
class MelDecalData(MelOptStruct):
    _decal_data_flags = Flags(0, Flags.getNames(
        u'parallax',
        u'alphaBlending',
        u'alphaTesting',
        u'noSubtextures', # Skyrim+, will just be ignored for earlier games
    ), unknown_is_unused=True)

    def __init__(self):
        super(MelDecalData, self).__init__(b'DODT',
            [u'7f', u'B', u'B', u'2s', u'3B', u's'], u'minWidth',
            u'maxWidth', u'minHeight', u'maxHeight', u'depth', u'shininess',
            u'parallaxScale', u'parallaxPasses',
            (self._decal_data_flags, u'decalFlags'), u'unusedDecal1',
            u'redDecal', u'greenDecal', u'blueDecal', u'unusedDecal2')

#------------------------------------------------------------------------------
class MelReferences(MelGroups):
    """Handles mixed sets of SCRO and SCRV for scripts, quests, etc."""
    def __init__(self):
        super(MelReferences, self).__init__(u'references', MelUnion({
            b'SCRO': MelFid(b'SCRO', u'reference'),
            b'SCRV': MelUInt32(b'SCRV', u'reference'),
        }))

#------------------------------------------------------------------------------
class MelSkipInterior(MelUnion):
    """Union that skips dumping if we're in an interior."""
    def __init__(self, element):
        super(MelSkipInterior, self).__init__({
            True: MelReadOnly(element),
            False: element,
        }, decider=FlagDecider(u'flags', [u'isInterior']))

#------------------------------------------------------------------------------
class MelColorInterpolator(MelArray):
    """Wrapper around MelArray that defines a time interpolator - an array
    of five floats, where each entry in the array describes a point on a curve,
    with 'time' as the X axis and 'red', 'green', 'blue' and 'alpha' as the Y
    axis."""
    def __init__(self, sub_type, attr):
        super(MelColorInterpolator, self).__init__(attr,
            MelStruct(sub_type, [u'5f'], u'time', u'red', u'green', u'blue',
                u'alpha'),
        )

#------------------------------------------------------------------------------
# xEdit calls this 'time interpolator', but that name doesn't really make sense
# Both this class and the color interpolator above interpolate over time
class MelValueInterpolator(MelArray):
    """Wrapper around MelArray that defines a value interpolator - an array
    of two floats, where each entry in the array describes a point on a curve,
    with 'time' as the X axis and 'value' as the Y axis."""
    def __init__(self, sub_type, attr):
        super(MelValueInterpolator, self).__init__(attr,
            MelStruct(sub_type, [u'2f'], u'time', u'value'),
        )

#------------------------------------------------------------------------------
class MelColor(MelStruct):
    """Required Color."""
    def __init__(self, color_sig=b'CNAM'):
        super(MelColor, self).__init__(color_sig, [u'4B'], u'red', u'green',
            u'blue', u'unused_alpha')

class MelColorO(MelOptStruct):
    """Optional Color."""
    def __init__(self, color_sig=b'CNAM'):
        super(MelColorO, self).__init__(color_sig, [u'4B'], u'red', u'green',
            u'blue', u'unused_alpha')

#------------------------------------------------------------------------------
class MelDescription(MelLString):
    """Handles a description (DESC) subrecord."""
    def __init__(self, desc_attr=u'description'):
        super(MelDescription, self).__init__(b'DESC', desc_attr)

#------------------------------------------------------------------------------
class MelEdid(MelString):
    """Handles an Editor ID (EDID) subrecord."""
    def __init__(self):
        super(MelEdid, self).__init__(b'EDID', u'eid')

#------------------------------------------------------------------------------
class MelFull(MelLString):
    """Handles a name (FULL) subrecord."""
    def __init__(self):
        super(MelFull, self).__init__(b'FULL', u'full')

#------------------------------------------------------------------------------
class MelIcons(MelSequential):
    """Handles icon subrecords. Defaults to ICON and MICO, with attribute names
    'iconPath' and 'smallIconPath', since that's most common."""
    def __init__(self, icon_attr=u'iconPath', mico_attr=u'smallIconPath',
                 icon_sig=b'ICON', mico_sig=b'MICO'):
        """Creates a new MelIcons with the specified attributes.

        :param icon_attr: The attribute to use for the ICON subrecord. If
            falsy, this means 'do not include an ICON subrecord'.
        :param mico_attr: The attribute to use for the MICO subrecord. If
            falsy, this means 'do not include a MICO subrecord'."""
        final_elements = []
        if icon_attr: final_elements.append(MelString(icon_sig, icon_attr))
        if mico_attr: final_elements.append(MelString(mico_sig, mico_attr))
        super(MelIcons, self).__init__(*final_elements)

class MelIcons2(MelIcons):
    """Handles ICO2 and MIC2 subrecords. Defaults to attribute names
    'femaleIconPath' and 'femaleSmallIconPath', since that's most common."""
    def __init__(self, ico2_attr=u'femaleIconPath',
                 mic2_attr=u'femaleSmallIconPath'):
        super(MelIcons2, self).__init__(icon_attr=ico2_attr,
            mico_attr=mic2_attr, icon_sig=b'ICO2', mico_sig=b'MIC2')

class MelIcon(MelIcons):
    """Handles a standalone ICON subrecord, i.e. without any MICO subrecord."""
    def __init__(self, icon_attr=u'iconPath'):
        super(MelIcon, self).__init__(icon_attr=icon_attr, mico_attr=u'')

class MelIco2(MelIcons2):
    """Handles a standalone ICO2 subrecord, i.e. without any MIC2 subrecord."""
    def __init__(self, ico2_attr):
        super(MelIco2, self).__init__(ico2_attr=ico2_attr, mic2_attr=u'')

#------------------------------------------------------------------------------
class MelMdob(MelFid):
    """Represents the common Menu Display Object subrecord."""
    def __init__(self):
        super(MelMdob, self).__init__(b'MDOB', u'menu_display_object')

#------------------------------------------------------------------------------
class MelWthrColors(MelStruct):
    """Used in WTHR for PNAM and NAM0 for all games but FNV."""
    def __init__(self, wthr_sub_sig):
        MelStruct.__init__(
            self, wthr_sub_sig,
            [u'3B', u's', u'3B', u's', u'3B', u's', u'3B', u's'], u'riseRed',
            u'riseGreen',
            u'riseBlue', u'unused1', u'dayRed', u'dayGreen',
            u'dayBlue',u'unused2', u'setRed', u'setGreen', u'setBlue',
            u'unused3', u'nightRed', u'nightGreen', u'nightBlue',
            u'unused4')

#------------------------------------------------------------------------------
class MelDropSound(MelFid):
    """Handles the common ZNAM - Drop Sound subrecord."""
    def __init__(self):
        super(MelDropSound, self).__init__(b'ZNAM', u'dropSound')

#------------------------------------------------------------------------------
class MelEnchantment(MelFid):
    """Represents the common enchantment/object effect subrecord."""
    ##: Would be better renamed to object_effect, but used in tons of places
    # that need renaming/reworking first
    def __init__(self):
        super(MelEnchantment, self).__init__(b'EITM', u'enchantment')

#------------------------------------------------------------------------------
class MelPickupSound(MelFid):
    """Handles the common YNAM - Pickup Sound subrecord."""
    def __init__(self):
        super(MelPickupSound, self).__init__(b'YNAM', u'pickupSound')

#------------------------------------------------------------------------------
##: This is a strange fusion of MelLists, MelStruct and MelTruncatedStruct
# because one of the attrs is a flags field and in Skyrim it's truncated too
class MelRaceData(MelTruncatedStruct):
    """Pack RACE skills and skill boosts as a single attribute."""

    def __init__(self, sub_sig, sub_fmt, *elements, **kwargs):
        if 'old_versions' not in kwargs:
            kwargs['old_versions'] = set() # set default to avoid errors
        super(MelRaceData, self).__init__(sub_sig, sub_fmt, *elements,
                                          **kwargs)

    @staticmethod
    def _expand_formats(elements, struct_formats):
        expanded_fmts = []
        for f in struct_formats:
            if f == u'14b':
                expanded_fmts.append(0)
            elif f[-1] != u's':
                expanded_fmts.extend([f[-1]] * int(f[:-1] or 1))
            else:
                expanded_fmts.append(int(f[:-1] or 1))
        return expanded_fmts

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        try:
            target_unpacker = self._all_unpackers[size_]
        except KeyError:
            raise ModSizeError(ins.inName, debug_strs,
                               tuple(self._all_unpackers), size_)
        unpacked = ins.unpack(target_unpacker, size_, *debug_strs)
        unpacked = self._pre_process_unpacked(unpacked)
        record.skills = unpacked[:14]
        for attr, value, action in zip(self.attrs[1:], unpacked[14:],
                                        self.actions[1:]):
            setattr(record, attr, action(value) if callable(action) else value)

    def pack_subrecord_data(self, record):
        values = list(record.skills)
        values.extend(
            action(value).dump() if callable(action) else value
            for value, action in zip(
                (getattr(record, a) for a in self.attrs[1:]),
                self.actions[1:]))
        return self._packer(*values)

#------------------------------------------------------------------------------
class MelRaceParts(MelNull):
    """Handles a subrecord array, where each subrecord is introduced by an
    INDX subrecord, which determines the meaning of the subrecord. The
    resulting attributes are set directly on the record.
    :type _indx_to_loader: dict[int, MelBase]"""
    def __init__(self, indx_to_attr, group_loaders):
        """Creates a new MelRaceParts element with the specified INDX mapping
        and group loaders.

        :param indx_to_attr: A mapping from the INDX values to the final
            record attributes that will be used for the subsequent
            subrecords.
        :type indx_to_attr: dict[int, str]
        :param group_loaders: A callable that takes the INDX value and
            returns an iterable with one or more MelBase-derived subrecord
            loaders. These will be loaded and dumped directly after each
            INDX."""
        self._last_indx = None # used during loading
        self._indx_to_attr = indx_to_attr
        # Create loaders for use at runtime
        self._indx_to_loader = {
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

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        __unpacker=_int_unpacker # PY3: keyword only search for __unpacker
        if sub_type == b'INDX':
            self._last_indx = ins.unpack(__unpacker, size_, *debug_strs)[0]
        else:
            self._indx_to_loader[self._last_indx].load_mel(
                record, ins, sub_type, size_, *debug_strs)

    def dumpData(self, record, out):
        # Note that we have to dump out the attributes sorted by the INDX value
        for part_indx, part_attr in dict_sort(self._indx_to_attr):
            if hasattr(record, part_attr): # only dump present parts
                MelUInt32(b'INDX', u'UNUSED').packSub(
                    out, struct_pack(u'=I', part_indx))
                self._indx_to_loader[part_indx].dumpData(record, out)

    @property
    def signatures(self):
        return self._possible_sigs

#------------------------------------------------------------------------------
class MelRaceVoices(MelStruct):
    """Set voices to zero, if equal race fid. If both are zero, then skip
    dumping."""
    def pack_subrecord_data(self, record):
        if record.maleVoice == record.fid: record.maleVoice = 0
        if record.femaleVoice == record.fid: record.femaleVoice = 0
        if (record.maleVoice, record.femaleVoice) != (0, 0):
            return super(MelRaceVoices, self).pack_subrecord_data(record)
        return None

#------------------------------------------------------------------------------
class MelScript(MelFid):
    """Represents the common script subrecord in TES4/FO3/FNV."""
    def __init__(self):
        super(MelScript, self).__init__(b'SCRI', u'script_fid')

#------------------------------------------------------------------------------
class MelScriptVars(MelSorted):
    """Handles SLSD and SCVR combos defining script variables."""
    _var_flags = Flags(0, Flags.getNames(u'is_long_or_short'))

    def __init__(self):
        super(MelScriptVars, self).__init__(MelGroups(u'script_vars',
            MelStruct(b'SLSD', [u'I', u'12s', u'B', u'7s'], u'var_index',
                      u'unused1', (self._var_flags, u'var_flags'),
                      u'unused2'),
            MelString(b'SCVR', u'var_name'),
        ), sort_by_attrs=u'var_index')

#------------------------------------------------------------------------------
class MelEnableParent(MelOptStruct):
    """Enable Parent struct for a reference record (REFR, ACHR, etc.)."""
    # The pop_in flag doesn't technically exist for all XESP subrecords, but it
    # will just be ignored for those where it doesn't exist, so no problem.
    _parent_flags = Flags(0, Flags.getNames(u'opposite_parent', u'pop_in'))

    def __init__(self):
        super(MelEnableParent, self).__init__(
            b'XESP', [u'I', u'B', u'3s'], (FID, u'ep_reference'),
            (self._parent_flags, u'parent_flags'), u'xesp_unused'),

#------------------------------------------------------------------------------
class MelMapMarker(MelGroup):
    """Map marker struct for a reference record (REFR, ACHR, etc.). Also
    supports the WMI1 subrecord from FNV."""
    # Same idea as above - show_all_hidden is FO3+, but that's no problem.
    _marker_flags = Flags(0, Flags.getNames(
        u'visible', u'can_travel_to', u'show_all_hidden'))

    def __init__(self, with_reputation=False):
        group_elems = [
            MelBase(b'XMRK', u'marker_data'),
            MelUInt8Flags(b'FNAM', u'marker_flags', self._marker_flags),
            MelFull(),
            MelOptStruct(b'TNAM', [u'B', u's'], u'marker_type', u'unused1'),
        ]
        if with_reputation:
            group_elems.append(MelFid(b'WMI1', u'marker_reputation'))
        super(MelMapMarker, self).__init__(u'map_marker', *group_elems)

#------------------------------------------------------------------------------
class MelMODS(MelBase):
    """MODS/MO2S/etc/DMDS subrecord"""
    def hasFids(self,formElements):
        formElements.add(self)

    def setDefault(self,record):
        setattr(record, self.attr, None)

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        __unpacker=_int_unpacker
        insUnpack = ins.unpack
        insRead32 = ins.readString32
        count, = insUnpack(__unpacker, 4, *debug_strs)
        mods_data = []
        dataAppend = mods_data.append
        for x in range(count):
            string = insRead32(*debug_strs)
            fid = ins.unpackRef()
            index, = insUnpack(__unpacker, 4, *debug_strs)
            dataAppend((string,fid,index))
        setattr(record, self.attr, mods_data)

    def pack_subrecord_data(self,record):
        mods_data = getattr(record, self.attr)
        if mods_data is not None:
            # Sort by 3D Name and 3D Index
            mods_data.sort(key=lambda e: (e[0], e[2]))
            return b''.join(chain([struct_pack(u'I', len(mods_data))],
                *([struct_pack(u'I', len(string)), encode(string),
                   struct_pack(u'=2I', fid, index)]
                  for (string, fid, index) in mods_data)))

    def mapFids(self,record,function,save=False):
        attr = self.attr
        mods_data = getattr(record, attr)
        if mods_data is not None:
            mods_data = [(string,function(fid),index) for (string,fid,index)
                         in getattr(record, attr)]
            if save: setattr(record, attr, mods_data)

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
    def __init__(self, entry_type_val, element):
        """:type entry_type_val: int"""
        super(MelRegnEntrySubrecord, self).__init__({
            entry_type_val: element,
        }, decider=AttrValDecider(u'entryType'),
            fallback=MelNull(b'NULL')) # ignore

#------------------------------------------------------------------------------
class MelRef3D(MelOptStruct):
    """3D position and rotation for a reference record (REFR, ACHR, etc.)."""
    def __init__(self):
        super(MelRef3D, self).__init__(
            b'DATA', [u'6f'], u'ref_pos_x', u'ref_pos_y', u'ref_pos_z',
            u'ref_rot_x', u'ref_rot_y', u'ref_rot_z'),

#------------------------------------------------------------------------------
class MelRefScale(MelFloat):
    """Scale for a reference record (REFR, ACHR, etc.)."""
    def __init__(self): # default was 1.0
        super(MelRefScale, self).__init__(b'XSCL', u'ref_scale')

#------------------------------------------------------------------------------
class MelSpells(MelSorted):
    """Handles the common SPLO subrecord."""
    def __init__(self):
        super(MelSpells, self).__init__(MelFids(b'SPLO', u'spells'))

#------------------------------------------------------------------------------
class MelWorldBounds(MelSequential):
    """Worlspace (WRLD) bounds."""
    def __init__(self):
        super(MelWorldBounds, self).__init__(
            MelStruct(b'NAM0', [u'2f'], u'object_bounds_min_x',
                u'object_bounds_min_y'),
            MelStruct(b'NAM9', [u'2f'], u'object_bounds_max_x',
                u'object_bounds_max_y'),
        )

#------------------------------------------------------------------------------
class MelXlod(MelOptStruct):
    """Distant LOD Data."""
    def __init__(self):
        super(MelXlod, self).__init__(b'XLOD', [u'3f'], u'lod1', u'lod2',
                                      u'lod3')

#------------------------------------------------------------------------------
class MelOwnership(MelGroup):
    """Handles XOWN, XRNK for cells and cell children."""

    def __init__(self, attr=u'ownership'):
        MelGroup.__init__(self, attr,
            MelFid(b'XOWN', u'owner'),
            MelSInt32(b'XRNK', u'rank'),
        )

    def dumpData(self,record,out):
        if record.ownership and record.ownership.owner: ##: use pack_subrecord_data ?
            MelGroup.dumpData(self,record,out)

#------------------------------------------------------------------------------
class MelDebrData(MelStruct):
    def __init__(self):
        # Format doesn't matter, struct.Struct(u'') works! ##: MelStructured
        super(MelDebrData, self).__init__(b'DATA', [], u'percentage',
            (u'modPath', null1), u'flags')

    @staticmethod
    def _expand_formats(elements, struct_formats):
        return [0] * len(elements)

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        byte_data = ins.read(size_, *debug_strs)
        record.percentage = unpack_byte(ins, byte_data[0:1])[0]
        record.modPath = byte_data[1:-2]
        if byte_data[-2] != null1:
            raise ModError(ins.inName, f'Unexpected subrecord: {debug_strs}')
        record.flags = struct_unpack(u'B', byte_data[-1])[0]

    def pack_subrecord_data(self, record):
        return b''.join(
            [struct_pack(u'B', record.percentage), record.modPath, null1,
             struct_pack(u'B', record.flags)])

#------------------------------------------------------------------------------
class MelBodyParts(MelSorted):
    """Handles the common NIFZ (Body Parts) subrecord."""
    def __init__(self): ##: case insensitive
        super(MelBodyParts, self).__init__(MelStrings(b'NIFZ', u'bodyParts'))

#------------------------------------------------------------------------------
class MelFactions(MelSorted):
    """Handles the common SNAM (Factions) subrecord."""
    def __init__(self):
        super(MelFactions, self).__init__(MelGroups(u'factions',
            MelStruct(b'SNAM', [u'I', u'B', u'3s'], (FID, u'faction'), u'rank',
                      (u'unused1', b'ODB')),
        ), sort_by_attrs=u'faction'),

#------------------------------------------------------------------------------
class MelAnimations(MelSorted):
    """Handles the common KFFZ (Animations) subrecord."""
    def __init__(self):
        super(MelAnimations, self).__init__(
            MelStrings(b'KFFZ', u'animations')), ##: case insensitive

#------------------------------------------------------------------------------
class MelRelations(MelSorted):
    """Handles the common XNAM (Relations) subrecord. Group combat reaction
    (GCR) can be excluded (i.e. in Oblivion)."""
    def __init__(self, with_gcr=True):
        if with_gcr:
            rel_struct = MelStruct(b'XNAM', [u'I', u'i', u'I'],
                                   (FID, u'faction'), u'mod',
                                   u'group_combat_reaction')
        else:
            rel_struct = MelStruct(b'XNAM', [u'I', u'i'],
                                   (FID, u'faction'), u'mod')
        super(MelRelations, self).__init__(MelGroups(u'relations', rel_struct),
                                           sort_by_attrs=u'faction')

#------------------------------------------------------------------------------
class MelActorSounds(MelSorted):
    """Handles the CSDT/CSDI/CSDC subrecord complex used by CREA records in
    TES4/FO3/FNV and NPC_ records in TES5."""
    def __init__(self):
        super(MelActorSounds, self).__init__(MelGroups(u'sounds',
            MelUInt32(b'CSDT', u'type'),
            MelSorted(MelGroups(u'sound_types',
                MelFid(b'CSDI', u'sound'),
                MelUInt8(b'CSDC', u'chance'),
            ), sort_by_attrs=u'sound'),
        ), sort_by_attrs=u'type')

#------------------------------------------------------------------------------
class MelRegions(MelSorted):
    """Handles the CELL subrecord XCLR (Regions)."""
    def __init__(self):
        super(MelRegions, self).__init__(MelFidList(b'XCLR', u'regions'))

#------------------------------------------------------------------------------
class MelWeatherTypes(MelSorted):
    """Handles the CLMT subrecord WLST (Weather Types)."""
    def __init__(self, with_global=True):
        if with_global:
            wlst_struct = MelStruct(b'WLST', [u'I', u'i', u'I'],
                                    (FID, u'weather'), u'chance',
                                    (FID, u'global'))
        else:
            wlst_struct = MelStruct(b'WLST', [u'I', u'i'], (FID, u'weather'),
                                    u'chance')
        super(MelWeatherTypes, self).__init__(MelArray(
            u'weather_types', wlst_struct), sort_by_attrs=u'weather')

#------------------------------------------------------------------------------
class MelFactionRanks(MelSorted):
    """Handles the FACT RNAM/MNAM/FNAM/INAM subrecords."""
    def __init__(self):
        super(MelFactionRanks, self).__init__(MelGroups(u'ranks',
            MelSInt32(b'RNAM', u'rank_level'),
            MelLString(b'MNAM', u'male_title'),
            MelLString(b'FNAM', u'female_title'),
            MelString(b'INAM', u'insignia_path'),
        ), sort_by_attrs=u'rank_level')

#------------------------------------------------------------------------------
class MelLscrLocations(MelSorted):
    """Handles the LSCR subrecord LNAM (Locations)."""
    def __init__(self):
        super(MelLscrLocations, self).__init__(MelGroups(u'locations',
            MelStruct(b'LNAM', [u'2I', u'2h'], (FID, u'direct'),
                      (FID, u'indirect'), u'gridy', u'gridx'),
        ), sort_by_attrs=(u'direct', u'indirect', u'gridy', u'gridx'))

#------------------------------------------------------------------------------
class MelReflectedRefractedBy(MelSorted):
    """Reflected/Refracted By for a reference record (REFR, ACHR, etc.)."""
    _watertypeFlags = Flags(0, Flags.getNames(u'reflection', u'refraction'))

    def __init__(self):
        super(MelReflectedRefractedBy, self).__init__(
            MelGroups(u'reflectedRefractedBy',
                MelStruct(b'XPWR', [u'2I'], (FID, u'waterReference'),
                          (self._watertypeFlags, u'waterFlags')),
        ), sort_by_attrs=u'waterReference')
