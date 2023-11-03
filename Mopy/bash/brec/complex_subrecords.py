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
"""Houses highly complex subrecords like NVNM and VMAD that require completely
custom code to handle."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from io import BytesIO
from itertools import chain
from typing import BinaryIO

from . import utils_constants
from .advanced_elements import AttrValDecider, MelCounter, MelPartialCounter, \
    MelTruncatedStruct, MelUnion, PartialLoadDecider, SignatureDecider, \
    MelSorted
from .basic_elements import MelBase, MelBaseR, MelFid, MelGroup, MelGroups, \
    MelObject, MelReadOnly, MelSequential, MelString, MelStruct, MelUInt32, \
    MelUnorderedGroups, MelUInt8
from .common_subrecords import MelFull
from .utils_constants import FID, ZERO_FID, get_structs, int_unpacker
from .. import bolt, bush
from ..bolt import Flags, attrgetter_cache, pack_byte, pack_float, pack_int, \
    pack_int_signed, pack_short, struct_pack, struct_unpack, unpack_str16, \
    unpack_byte, unpack_float, unpack_int, unpack_short, unpack_int_signed
from ..exception import ArgumentError, ModError

# Shared helpers --------------------------------------------------------------
##: These should probably go somewhere else
def _mk_unpacker(struct_fmt):
    """Helper method that creates a method for unpacking values from an input
    stream. Accepts debug strings as well."""
    s_unpack, _s_pack, s_size = get_structs(f'={struct_fmt}')
    def _unpacker(ins, *debug_strs):
        return ins.unpack(s_unpack, s_size, *debug_strs)
    return _unpacker

_unpack_2shorts_signed = _mk_unpacker('2h')

def _mk_packer(struct_fmt):
    """Helper method that creates a method for packing values to an output
    stream."""
    _s_unpack, s_pack, _s_size = get_structs(f'={struct_fmt}')
    def _packer(out, *vals_to_pack):
        return out.write(s_pack(*vals_to_pack))
    return _packer

_pack_2shorts_signed = _mk_packer('2h')

#------------------------------------------------------------------------------
# CS* - Actor Sounds
#------------------------------------------------------------------------------
class MelActorSounds(MelSorted):
    """Handles the CSDT/CSDI/CSDC subrecord complex used by CREA records in
    TES4/FO3/FNV and NPC_ records in TES5."""
    def __init__(self):
        super().__init__(MelGroups('actor_sounds',
            MelUInt32(b'CSDT', 'actor_sound_type'),
            MelSorted(MelGroups('actor_sound_list',
                MelFid(b'CSDI', 'actor_sound_fid'),
                MelUInt8(b'CSDC', 'actor_sound_chance'),
            ), sort_by_attrs='actor_sound_fid'),
        ), sort_by_attrs='actor_sound_type')

class _MelCs2kCs2d(MelGroups):
    """Handles CS2K and CS2D. The complication here is that CS2K begins a new
    actor sound, while CS2D can either finish off an actor sound started by
    CS2K or begin and immediately finish an actor sound if it occurred on its
    own or after another CS2D. Furthermore, actor sounds without keywords must
    be sorted before actor sounds with keywords."""
    def __init__(self):
        super().__init__('actor_sounds',
            MelFid(b'CS2K', 'actor_sound_keyword'),
            MelFid(b'CS2D', 'actor_sound_fid'),
        )

    def getSlotsUsed(self):
        return '_had_cs2k', *super().getSlotsUsed()

    def setDefault(self, record):
        super().setDefault(record)
        record._had_cs2k = False

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        if sub_type == b'CS2D':
            if record._had_cs2k:
                # This actor sound was started via CS2K, finish it off
                target = record.actor_sounds[-1]
                record._had_cs2k = False
            else:
                # We got a CS2D without a previous CS2K, start and finish a new
                # actor sound
                target = self._new_object(record)
        else:
            # We hit a CS2K, start a new actor sound
            target = self._new_object(record)
            record._had_cs2k = True
        self.loaders[sub_type].load_mel(target, ins, sub_type, size_,
            *debug_strs)

    def needs_sorting(self):
        return True

    def sort_subrecord(self, record):
        super().sort_subrecord(record)
        sounds_none = []
        sounds_kw = []
        # Sort the actor sounds that have no keyword associated with them
        # first. We do it like this to avoid comparing FormId instances with
        # None
        for s in record.actor_sounds:
            if s.actor_sound_keyword is None:
                sounds_none.append(s)
            else:
                sounds_kw.append(s)
        ##: Does the game/CK sort by actor_sound_fid too?
        record.actor_sounds = sounds_none + sorted(sounds_kw,
            key=attrgetter_cache['actor_sound_keyword'])

class MelActorSounds2(MelSequential):
    """Bethesda redesigned actor sounds for FO4. This handles the new
    CS2H/CS2K/CS2D/CS2E/CS2F subrecord complex used by NPC_ records."""
    def __init__(self):
        self._cond_required = [
            MelBaseR(b'CS2E', 'actor_sound_end_marker'), # empty marker
            MelBaseR(b'CS2F', 'actor_sound_finalize', set_default=b'\x00'),
        ]
        super().__init__(
            MelCounter(MelUInt32(b'CS2H', 'actor_sounds_count'),
                counts='actor_sounds'),
            _MelCs2kCs2d(),
            *self._cond_required,
        )

    def dumpData(self, record, out):
        for element in self.elements:
            # CS2E and CS2F are required iff there are any actor sounds present
            if record.actor_sounds or element not in self._cond_required:
                element.dumpData(record, out)

#------------------------------------------------------------------------------
# CTDA - Conditions
#------------------------------------------------------------------------------
# Implementation --------------------------------------------------------------
class _MelCtda(MelUnion):
    """Handles a condition. The difficulty here is that the type of its
    parameters depends on its function index. We handle it by building what
    amounts to a decision tree using MelUnions."""
    # 0 = Unknown/Ignored, 1 = Int, 2 = FormID, 3 = Float
    _param_types = {0: '4s', 1: 'i', 2: 'I', 3: 'f'}

    class _CtdaTypeFlags(Flags):
        # This is technically a lot more complex (the highest three bits also
        # encode the comparison operator), but we only care about use_global,
        # so we can treat the rest as unknown flags and just carry them forward
        do_or: bool
        use_aliases: bool
        use_global: bool
        use_packa_data: bool
        swap_subject_and_target: bool

    def __init__(self, ctda_sub_sig=b'CTDA',
            suffix_fmt: list[str] | None = None,
            suffix_elements: list | None = None,
            old_suffix_fmts: set[str] | None = None):
        """Creates a new _MelCtda instance with the specified properties.

        :param ctda_sub_sig: The signature of this subrecord. Probably
            b'CTDA'.
        :param suffix_fmt: The struct format string to use, starting after the
            first two parameters.
        :param suffix_elements: The struct elements to use, starting after the
            first two parameters.
        :param old_suffix_fmts: A set of old versions to pass to
            MelTruncatedStruct. Must conform to the same syntax as suffix_fmt.
            May be empty."""
        if suffix_fmt is None: suffix_fmt = []
        if suffix_elements is None: suffix_elements = []
        if old_suffix_fmts is None: old_suffix_fmts = set()
        super().__init__({
            # Build a (potentially truncated) struct for each function index
            func_index: self._build_struct(func_data, ctda_sub_sig, suffix_fmt,
                                           suffix_elements, old_suffix_fmts)
            for func_index, func_data
            in bush.game.condition_function_data.items()
        }, decider=PartialLoadDecider(
            # Skip everything up to the function index in one go, we'll be
            # discarding this once we rewind anyways.
            loader=MelStruct(ctda_sub_sig, ['8s', 'H'], 'ctda_skip', 'ifunc'),
            decider=AttrValDecider('ifunc'),
        ))
        self._ctda_mel: MelStruct = next(iter(self.element_mapping.values()))

    def _get_element(self, decider_ret):
        try:
            return super()._get_element(decider_ret)
        except ArgumentError as e:
            raise RuntimeError('A condition function could not be retrieved, '
                               'this almost certainly means the '
                               'condition_function_data for this game needs '
                               'to be updated') from e

    # Helper methods - Note that we skip func_data[0]; the first element is
    # the function name, which is only needed for puny human brains
    def _build_struct(self, func_data, ctda_sub_sig, suffix_fmt,
                      suffix_elements, old_suffix_fmts):
        """Builds up a struct from the specified jungle of parameters. Mostly
        inherited from __init__, see there for docs."""
        # The '4s' here can actually be a float or a FormID. We do *not* want
        # to handle this via MelUnion, because the deep nesting is going to
        # cause exponential growth and bring PBash down to a crawl.
        prefix_fmt = ['B', '3s', '4s', 'H', '2s']
        prefix_elements = [(self._CtdaTypeFlags, 'operFlag'), 'unused1',
                           'compValue', 'ifunc', 'unused2']
        # Builds an argument tuple to use for formatting the struct format
        # string from above plus the suffix we got passed in
        fmt_list = [self._param_types[func_param] for func_param in
                    func_data[1:]]
        fmts = [*prefix_fmt, *fmt_list]
        shared_params = ([ctda_sub_sig, fmts + suffix_fmt] +
                         self._build_params(func_data, prefix_elements,
                                            suffix_elements))
        # Only use MelTruncatedStruct if we have old versions, save the
        # overhead otherwise
        if old_suffix_fmts:
            full_old_versions = {''.join([*fmts, f] if f else fmts) for f in
                                 old_suffix_fmts}
            return MelTruncatedStruct(*shared_params,
                                      old_versions=full_old_versions)
        return MelStruct(*shared_params)

    @staticmethod
    def _build_params(func_data, prefix_elements, suffix_elements):
        """Builds a list of struct elements to pass to MelTruncatedStruct."""
        # First, build up a list of the parameter elements to use
        func_elements = [ # param1, param2, param3 are set here
            # 2 == FormID, see PatchGame.condition_function_data
            (FID, f'param{i}') if func_param == 2 else f'param{i}'
            for i, func_param in enumerate(func_data[1:], start=1)]
        # Then, combine the suffix, parameter and suffix elements
        return prefix_elements + func_elements + suffix_elements

    # Nesting workarounds -----------------------------------------------------
    # To avoid having to nest MelUnions too deeply - hurts performance even
    # further (see below) plus grows exponentially
    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        super().load_mel(record, ins, sub_type, size_, *debug_strs)
        # See _build_struct comments above for an explanation of this
        record.compValue = struct_unpack('fI'[record.operFlag.use_global],
                                         record.compValue)[0]
        if record.operFlag.use_global:
            record.compValue = FID(record.compValue)

    def mapFids(self, record, function, save_fids=False):
        super().mapFids(record, function, save_fids)
        if isinstance(record.operFlag, int):
            record.operFlag = self._CtdaTypeFlags(record.operFlag)
        if record.operFlag.use_global:
            new_comp_val = function(record.compValue)
            if save_fids: record.compValue = new_comp_val

    def dumpData(self, record, out):
        # See _build_struct comments above for an explanation of this
        if isinstance(record.operFlag, int):
            record.operFlag = self._CtdaTypeFlags(record.operFlag)
        if record.operFlag.use_global:
            record.compValue = record.compValue.dump()
        record.compValue = struct_pack('fI'[record.operFlag.use_global],
            record.compValue)
        super().dumpData(record, out)

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

class _MelCtdaFo3(_MelCtda):
    """Version of _MelCtda that handles the additional complexities that were
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
    _vats_param2_fmt = defaultdict(lambda: '4s', {
        0: 'I', 1: 'I', 2: 'I', 3: 'I', 5: 'i', 6: 'I', 9: 'I',
        10: 'I', 15: 'I', 18: 'I', 19: 'I', 20: 'I'})
    # The param #1 values that indicate param #2 is a FormID
    _vats_param2_fid = {0, 1, 2, 3, 9, 10}

    def __init__(self, suffix_fmt: list[str] | None = None,
            suffix_elements: list | None = None,
            old_suffix_fmts: set[str] | None = None):
        super().__init__(suffix_fmt=suffix_fmt,
            suffix_elements=suffix_elements, old_suffix_fmts=old_suffix_fmts)
        self._getvatsvalue_ifunc = bush.game.getvatsvalue_index
        self._ignore_ifuncs = ({106, 285} if bush.game.fsName == 'FalloutNV'
                               else set()) # 106 == IsFacingUp, 285 == IsLeftUp

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        super().load_mel(record, ins, sub_type, size_, *debug_strs)
        if record.runOn == 2 and record.ifunc not in self._ignore_ifuncs:
            record.reference = FID(record.reference)
        if record.ifunc == self._getvatsvalue_ifunc:
            p2_unpacked = struct_unpack(
                self._vats_param2_fmt[record.param1], record.param2)[0]
            if record.param1 in self._vats_param2_fid:
                p2_unpacked = FID(p2_unpacked)
            record.param2 = p2_unpacked

    def mapFids(self, record, function, save_fids=False):
        super().mapFids(record, function, save_fids)
        if record.runOn == 2 and record.ifunc not in self._ignore_ifuncs:
            new_reference = function(record.reference)
            if save_fids: record.reference = new_reference
        if (record.ifunc == self._getvatsvalue_ifunc and
                record.param1 in self._vats_param2_fid):
            new_param2 = function(record.param2)
            if save_fids: record.param2 = new_param2

    def dumpData(self, record, out):
        if record.runOn == 2 and record.ifunc not in self._ignore_ifuncs:
            record.reference = record.reference.dump()
        if record.ifunc == self._getvatsvalue_ifunc:
            if record.param1 in self._vats_param2_fid:
                record.param2 = record.param2.dump()
            record.param2 = struct_pack(
                self._vats_param2_fmt[record.param1], record.param2)
        super().dumpData(record, out)

# API - TES4 ------------------------------------------------------------------
class _CtdaDecider(SignatureDecider):
    """Loads based on signature, but always dumps out the newer CTDA format."""
    can_decide_at_dump = True

    def decide_dump(self, record):
        return b'CTDA'

class MelConditionsTes4(MelGroups):
    """A list of conditions. Can contain the old CTDT format as well, which
    will be upgraded on dump."""
    def __init__(self):
        super().__init__('conditions', MelUnion({
            b'CTDA': _MelCtda(suffix_fmt=['4s'],
                suffix_elements=['unused3']),
            # The old (CTDT) format is length 20 and has no suffix
            b'CTDT': MelReadOnly(_MelCtda(b'CTDT', suffix_fmt=['4s'],
                suffix_elements=['unused3'], old_suffix_fmts={''})),
            }, decider=_CtdaDecider()),
        )

# API - FO3 and FNV -----------------------------------------------------------
class MelConditionsFo3(MelGroups):
    """A list of conditions."""
    def __init__(self):
        # Note that reference can be a fid - handled in _MelCtdaFo3.mapFids
        super().__init__('conditions', _MelCtdaFo3(suffix_fmt=['2I'],
            suffix_elements=['runOn', 'reference'], old_suffix_fmts={'I', ''}))

# API - TES5 and onwards ------------------------------------------------------
class MelConditionList(MelGroups):
    """A list of conditions without a counter. Applies to Skyrim and newer
    games. See also MelConditions, which includes a counter for this class."""
    def __init__(self, conditions_attr='conditions'):
        super().__init__(conditions_attr,
            MelGroups('condition_list',
                _MelCtdaFo3(suffix_fmt=['2I', 'i'],
                    suffix_elements=['runOn', 'reference', 'param3'],
                    old_suffix_fmts={'2I', 'I', ''}),
            ),
            MelString(b'CIS1', 'param_cis1'),
            MelString(b'CIS2', 'param_cis2'),
        )

class MelConditions(MelSequential):
    """Wraps MelSequential to define a condition list with an associated
    counter."""
    def __init__(self):
        super().__init__(
            MelCounter(MelUInt32(b'CITC', 'conditionCount'),
                counts='conditions'),
            MelConditionList(),
        )

#------------------------------------------------------------------------------
# OMOD's DATA
#------------------------------------------------------------------------------
# Helpers ---------------------------------------------------------------------
_omod_unpack_include = _mk_unpacker('I3B')
_omod_pack_include = _mk_packer('I3B')
_omod_unpack_property_header = _mk_unpacker('B3sB3sH2s')
_omod_pack_property_header = _mk_packer('B3sB3sH2s')

class _MelOmodInclude(MelObject):
    """Helper class for OMOD-related includes."""
    __slots__ = ('oi_mod', 'oi_attach_point_index', 'oi_optional',
                 'oi_dont_use_all')

    def load_include(self, ins, *debug_strs):
        """Load this include from the specified input stream."""
        self.oi_mod, self.oi_attach_point_index, self.oi_optional, \
        self.oi_dont_use_all = _omod_unpack_include(ins, *debug_strs)
        self.oi_mod = FID(self.oi_mod)

    def dump_include(self, out):
        """Dump this include to the specified output stream."""
        _omod_pack_include(out, self.oi_mod.dump(), self.oi_attach_point_index,
            self.oi_optional, self.oi_dont_use_all)

    def map_include_fids(self, map_function, save_fids=False):
        """Map the OMOD FormID inside this include."""
        result_oi_mod = map_function(self.oi_mod)
        if save_fids: self.oi_mod = result_oi_mod

class _MelOmodProperty(MelObject):
    """Helper class for OMOD-related properties."""
    __slots__ = ('op_value_type', 'op_unused1', 'op_function_type',
                 'op_unused2', 'op_property', 'op_unused3', 'op_value_1',
                 'op_value_2', 'op_step')

    def load_property(self, ins, *debug_strs):
        """Load this property from the specified input stream."""
        # First unpack the part that can't change its data types
        self.op_value_type, self.op_unused1, self.op_function_type, \
        self.op_unused2, self.op_property, \
        self.op_unused3 = _omod_unpack_property_header(ins, *debug_strs)
        # We're now ready to load the first value...
        op_val_ty = self.op_value_type
        if op_val_ty == 0: # uint32
            self.op_value_1 = unpack_int(ins)
        elif op_val_ty == 1: # float
            self.op_value_1 = unpack_float(ins)
        elif op_val_ty == 2: # bool (stored as uint32)
            self.op_value_1 = unpack_int(ins) != 0
        elif op_val_ty in (4, 6): # fid
            self.op_value_1 = FID(unpack_int(ins))
        elif op_val_ty == 5: # enum (stored as uint32)
            self.op_value_1 = unpack_int(ins)
        else: # unknown
            self.op_value_1 = ins.read(4, *debug_strs)
        # ...and the second value
        if op_val_ty in (0, 4): # uint32
            self.op_value_2 = unpack_int(ins)
        elif op_val_ty in (1, 6): # float
            self.op_value_2 = unpack_float(ins)
        elif op_val_ty == 2: # bool (stored as uint32)
            self.op_value_2 = unpack_int(ins) != 0
        else: # unused
            self.op_value_2 = ins.read(4, *debug_strs)
        # Can't forget the final float
        self.op_step = unpack_float(ins)

    def dump_property(self, out):
        """Dump this property to the specified output stream."""
        _omod_pack_property_header(out, self.op_value_type, self.op_unused1,
            self.op_function_type, self.op_unused2, self.op_property,
            self.op_unused3)
        op_val_ty = self.op_value_type
        op_val_dt1 = self.op_value_1
        if op_val_ty == 0: # uint32
            pack_int(out, op_val_dt1)
        elif op_val_ty == 1: # float
            pack_float(out, op_val_dt1)
        elif op_val_ty == 2: # bool (stored as uint32)
            pack_int(out, 1 if op_val_dt1 else 0)
        elif op_val_ty in (4, 6): # fid
            pack_int(out, op_val_dt1.dump())
        elif op_val_ty == 5: # enum (stored as uint32)
            pack_int(out, op_val_dt1)
        else: # unknown
            out.write(op_val_dt1)
        op_val_dt2 = self.op_value_2
        if op_val_ty in (0, 4): # uint32
            pack_int(out, op_val_dt2)
        elif op_val_ty in (1, 6): # float
            pack_float(out, op_val_dt2)
        elif op_val_ty == 2: # bool (stored as uint32)
            pack_int(out, 1 if op_val_dt2 else 0)
        else: # unused
            out.write(op_val_dt2)
        pack_float(out, self.op_step)

    def map_property_fids(self, map_function, save_fids=False):
        """Map the potential FormID inside this property."""
        if self.op_value_type in (4, 6):
            result_val1 = map_function(self.op_value_1)
            if save_fids: self.op_value_1 = result_val1

##: The helper classes are already shared, but we could probably carve out a
# base class for this and _MelObts
class MelOmodData(MelPartialCounter):
    """Handles the OMOD subrecord DATA. Very similar to OBTS (see below)."""
    def __init__(self):
        super().__init__(
            # od = 'OMOD DATA'
            MelStruct(b'DATA', ['2I', '2B', 'I', '2B', '2I'],
                'od_include_count', 'od_property_count', 'od_unknown_bool1',
                'od_unknown_bool2', 'od_form_type', 'od_max_rank',
                'od_level_tier_scaled_offset', (FID, 'od_attach_point'),
                'od_attach_parent_slot_count'),
            counters={
                'od_include_count': 'od_includes',
                'od_property_count': 'od_properties',
                'od_attach_parent_slot_count': 'od_attach_parent_slots',
            })

    def getSlotsUsed(self):
        return ('od_attach_parent_slots', 'od_items', 'od_includes',
                'od_properties', *super().getSlotsUsed())

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        # Unpack the static portion using MelStruct
        super().load_mel(record, ins, sub_type, self.static_size, *debug_strs)
        # Load the attach parent slots - The count was read just now by super
        record.od_attach_parent_slots = [
            FID(unpack_int(ins))
            for _x in range(record.od_attach_parent_slot_count)]
        # Load the items. These are probably unused leftovers since there does
        # not seem to be a way to change them in the CK
        record.od_items = ins.read(8 * unpack_int(ins))
        # Load the includes - The include count was loaded way back at the
        # start of the struct
        record.od_includes = []
        append_include = record.od_includes.append
        for _x in range(record.od_include_count):
            od_include = _MelOmodInclude()
            od_include.load_include(ins, *debug_strs)
            append_include(od_include)
        # Load the properties - this count was right after the include count
        record.od_properties = []
        append_property = record.od_properties.append
        for _x in range(record.od_property_count):
            od_property = _MelOmodProperty()
            od_property.load_property(ins, *debug_strs)
            append_property(od_property)

    def pack_subrecord_data(self, record):
        out = BytesIO()
        out.write(super().pack_subrecord_data(record))
        for od_aps in record.od_attach_parent_slots:
            pack_int(out, od_aps.dump())
        pack_int(out, len(record.od_items) // 8)
        out.write(record.od_items)
        for od_include in record.od_includes:
            od_include.dump_include(out)
        for od_property in record.od_properties:
            od_property.dump_property(out)
        return out.getvalue()

    def mapFids(self, record, function, save_fids=False):
        super().mapFids(record, function, save_fids)
        result_ap_slots = [function(od_aps)
                           for od_aps in record.od_attach_parent_slots]
        if save_fids:
            record.od_attach_parent_slots = result_ap_slots
        for od_include in record.od_includes:
            od_include.map_include_fids(function, save_fids)
        for od_property in record.od_properties:
            od_property.map_property_fids(function, save_fids)

#------------------------------------------------------------------------------
# OBME - Oblivion Magic Extender
#------------------------------------------------------------------------------
# Sits up here because the effects stuff down below needs it
# Helpers ---------------------------------------------------------------------
class _MelObmeScitGroup(MelGroup):
    """Fun HACK for the whole family. We need to carry efix_param_info into
    this group, since '../' syntax is not yet supported (see MelPerkParamsGroups
    for another part of the code that's suffering from this). And we can't
    simply not put this in a group, because a bunch of code relies on a group
    called 'scriptEffect' existing..."""
    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        target = getattr(record, self.attr)
        if target is None:
            class _MelHackyObject(MelObject):
                @property
                def efix_param_info(self):
                    return record.efix_param_info
                @efix_param_info.setter
                def efix_param_info(self, new_efix_info):
                    record.efix_param_info = new_efix_info
            target = _MelHackyObject()
            for element in self.elements:
                element.setDefault(target)
            target.__slots__ = [s for element in self.elements for s in
                                element.getSlotsUsed()]
            setattr(record, self.attr, target)
        self.loaders[sub_type].load_mel(target, ins, sub_type, size_,
            *debug_strs)

# API -------------------------------------------------------------------------
class MelObme(MelStruct):
    """Oblivion Magic Extender subrecord. Prefixed every attribute with obme_
    both for easy grouping in debugger views and to differentiate them from
    vanilla attrs."""
    def __init__(self, struct_sig=b'OBME', extra_format=None,
                 extra_contents=None, reserved_byte_count=28):
        """Initializes a MelObme instance. Supports customization for the
        variations that exist for effects subrecords and MGEF records."""
        # Always begins with record version and OBME version
        # obme_record_version is almost always 0 in plugins using OBME
        struct_contents = ['obme_record_version', 'obme_version_beta',
                           'obme_version_minor', 'obme_version_major']
        # Then comes any extra info placed in the middle
        if extra_contents is not None:
            struct_contents += extra_contents
        # Always ends with a statically sized reserved byte array
        struct_contents += ['obme_unused']
        str_fmts = ['4B', *(extra_format or []), f'{reserved_byte_count}s']
        super().__init__(struct_sig, str_fmts, *struct_contents)

#------------------------------------------------------------------------------
# EFID/EFIT/etc. - Effects
#------------------------------------------------------------------------------
# Helpers ---------------------------------------------------------------------
# TODO(inf) Do we really need to do this? It's an unused test spell
class _MelEffectsScit(MelTruncatedStruct):
    """The script fid for MS40TestSpell doesn't point to a valid script,
    so this class drops it."""
    def _pre_process_unpacked(self, unpacked_val):
        if len(unpacked_val) == 1:
            if unpacked_val[0] & 0xFF000000:
                unpacked_val = (0,) # Discard bogus MS40TestSpell fid
        return super()._pre_process_unpacked(unpacked_val)

class _MelMgefCode(MelStruct):
    """Handles the nonsense that is MGEF codes in Oblivion. This is necessary
    because we use the code, which is actually a FourCC and so really should be
    treated as 4 bytes, as a string all over the codebase. On top of that, OBME
    means that this stupid thing can be a FormID too, depending on its value as
    an integer."""
    def __init__(self, mel_sig: bytes, struct_formats: list[str], *elements,
            mgef_code_attr: str, emulated_attr: str | None = None):
        """"""
        super().__init__(mel_sig, struct_formats, *elements)
        self._mgef_code_attr = mgef_code_attr
        self._mgef_int_attr = f'_{mgef_code_attr}_as_int'
        self._emulated_attr = emulated_attr

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        super().load_mel(record, ins, sub_type, size_, *debug_strs)
        mgef_code = getattr(record, self._mgef_code_attr)
        # Emulate the regular API the rest of WB expects if needed
        if self._emulated_attr:
            setattr(record, self._emulated_attr, bolt.decoder(mgef_code[:4],
                encoding=bolt.pluginEncoding,
                avoidEncodings=('utf8', 'utf-8')))
        setattr(record, self._mgef_int_attr,
                mgef_int := int_unpacker(mgef_code)[0])
        if mgef_int >= 0x80000000:
            # This is actually an OBME FormID, not a normal MGEF code. Note
            # that OBME stores them as big endian for some godforsaken reason
            setattr(record, self._mgef_code_attr,
                FID(bolt.struct_unpack('>I', mgef_code)[0]))

    def pack_subrecord_data(self, record):
        if getattr(record, self._mgef_int_attr) >= 0x80000000:
            mgef_code = getattr(record, self._mgef_code_attr)
            # Skip the harcoded/engine object index check for these FormIDs,
            # they don't appear to obey this check
            ##: Figure out some way to actually verify that
            setattr(record, self._mgef_code_attr, bolt.struct_pack('>I',
                utils_constants.short_mapper_no_engine(mgef_code)))
        return super().pack_subrecord_data(record)

    def hasFids(self, formElements):
        formElements.add(self)

    def mapFids(self, record, function, save_fids=False):
        if getattr(record, self._mgef_int_attr) >= 0x80000000:
            mc_result = function(getattr(record, self._mgef_code_attr))
            if save_fids:
                setattr(record, self._mgef_code_attr, mc_result)

    def getSlotsUsed(self):
        ret_slots = super().getSlotsUsed()
        if self._emulated_attr is not None:
            ret_slots += (self._emulated_attr,)
        return ret_slots + (self._mgef_int_attr,)

# API - TES3 ------------------------------------------------------------------
class MelEffectsTes3(MelGroups):
    """Handles the list of ENAM structs present on several records."""
    def __init__(self):
        super().__init__('effects',
            MelStruct(b'ENAM', ['H', '2b', '5I'], 'effect_index',
                'skill_affected', 'attribute_affected', 'ench_range',
                'ench_area', 'ench_duration', 'ench_magnitude_min',
                'ench_magnitude_max'),
        )

# API - TES4 ------------------------------------------------------------------
##: Should we allow mixing regular effects and OBME ones? This implementation
# assumes no, but xEdit's is broken right now, so...
class MelEffectsTes4(MelSequential):
    """Represents ingredient/potion/enchantment/spell effects. Supports OBME,
    which is why it's so complex. The challenge is that we basically have to
    redirect every procedure to one of two lists of elements, depending on
    whether an 'OBME' subrecord exists or not."""
    class se_flags(Flags):
        hostile: bool

    def __init__(self):
        # Vanilla Elements ----------------------------------------------------
        self._vanilla_elements = [
            # Structs put to required as we create effects/scriptEffect -
            # maybe rework to assign attributes on the spot
            MelGroups('effects',
                # REHE is Restore target's Health - EFID.effect_sig
                # must be the same as EFIT.effect_sig. No need for _MelMgefCode
                # here because we know we don't have OBME on this record
                MelStruct(b'EFID', ['4s'], ('effect_sig', b'REHE')),
                MelStruct(b'EFIT', ['4s', '4I', 'i'], ('effect_sig', b'REHE'),
                    'magnitude', 'area', 'duration', 'recipient',
                    'actorValue', is_required=True),
                MelGroup('scriptEffect',
                    _MelEffectsScit(b'SCIT', ['2I', '4s', 'B', '3s'],
                        (FID, 'script_fid'), 'school', 'visual',
                        (self.se_flags, 'flags'), 'unused1',
                        old_versions={'2I4s', 'I'}, is_required=True),
                    MelFull(),
                ),
            ),
        ]
        # OBME Elements -------------------------------------------------------
        self._obme_elements = [
            MelGroups('effects',
                MelObme(b'EFME', extra_format=['2B'],
                    extra_contents=['efit_param_info', 'efix_param_info'],
                    reserved_byte_count=10),
                _MelMgefCode(b'EFID', ['4s'], ('effect_sig', b'REHE'),
                    mgef_code_attr='effect_sig'),
                MelUnion({
                    0: MelStruct(b'EFIT', ['4s', '4I', '4s'], 'unused_name',
                        'magnitude', 'area', 'duration', 'recipient',
                        'efit_param'),
                    ##: Test this! Does this actually work?
                    (1, 3): MelStruct(b'EFIT', ['4s', '5I'], 'unused_name',
                        'magnitude', 'area', 'duration', 'recipient',
                        (FID, 'efit_param')),
                    2: _MelMgefCode(b'EFIT', ['4s', '4I', '4s'], 'unused_name',
                        'magnitude', 'area', 'duration', 'recipient',
                        ('efit_param', b'REHE'), mgef_code_attr='efit_param'),
                }, decider=AttrValDecider('efit_param_info')),
                _MelObmeScitGroup('scriptEffect',
                    ##: Test! xEdit has all this in EFIX, but it also
                    #  hard-crashes when I try to add EFIX subrecords... this
                    #  is adapted from OBME's official docs, but those could be
                    #  wrong. Also, same note as above for case 3.
                    MelUnion({
                        0: MelStruct(b'SCIT', ['4s', 'I', '4s', 'B', '3s'],
                            'efix_param', 'school', 'visual',
                            se_fl := (self.se_flags, 'flags'), 'unused1'),
                        (1, 3): MelStruct(b'SCIT', ['2I', '4s', 'B', '3s'],
                            (FID, 'efix_param'), 'school', 'visual', se_fl,
                            'unused1'),
                        2: _MelMgefCode(b'SCIT', ['4s', 'I', '4s', 'B', '3s'],
                            ('efix_param', b'REHE'), 'school', 'visual', se_fl,
                            'unused1', mgef_code_attr='efix_param'),
                    }, decider=AttrValDecider('efix_param_info')),
                    MelFull(),
                ),
                MelString(b'EFII', 'obme_icon'),
                ##: Again, FID here needs testing
                MelStruct(b'EFIX', ['2I', 'f', 'i', '16s'],
                    'efix_override_mask', 'efix_flags', 'efix_base_cost',
                    (FID, 'resist_av'), 'efix_reserved'),
            ),
            MelBaseR(b'EFXX', 'effects_end_marker'),
        ]
        # Split everything by Vanilla/OBME
        self._vanilla_loaders = {}
        self._vanilla_form_elements = set()
        self._obme_loaders = {}
        self._obme_form_elements = set()
        # Only for setting the possible signatures, redirected in load_mel etc.
        super().__init__(*self._vanilla_elements, *self._obme_elements)

    # Note that we only support creating vanilla effects, as our records system
    # isn't expressive enough to pass more info along here
    def getDefaulters(self, defaulters, base):
        for element in self._vanilla_elements:
            element.getDefaulters(defaulters, base)

    def getLoaders(self, loaders):
        # We need to collect all signatures and assign ourselves for them all
        # to always gain control of load_mel so we can redirect it properly
        for element in self._vanilla_elements:
            element.getLoaders(self._vanilla_loaders)
        for element in self._obme_elements:
            element.getLoaders(self._obme_loaders)
        for signature in chain(self._vanilla_loaders, self._obme_loaders):
            loaders[signature] = self

    def hasFids(self, formElements):
        for element in self._vanilla_elements:
            element.hasFids(self._vanilla_form_elements)
        for element in self._obme_elements:
            element.hasFids(self._obme_form_elements)
        if self._vanilla_form_elements or self._obme_form_elements:
            formElements.add(self)

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        target_loaders = (self._obme_loaders
                          if record.obme_record_version is not None
                          else self._vanilla_loaders)
        target_loaders[sub_type].load_mel(record, ins, sub_type, size_, *debug_strs)

    def dumpData(self, record, out):
        target_elements = (self._obme_elements
                           if record.obme_record_version is not None
                           else self._vanilla_elements)
        for element in target_elements:
            element.dumpData(record, out)

    def mapFids(self, record, function, save_fids=False):
        target_form_elements = (self._obme_form_elements
                                if record.obme_record_version is not None
                                else self._vanilla_form_elements)
        for form_element in target_form_elements:
            form_element.mapFids(record, function, save_fids)

class MelEffectsTes4ObmeFull(MelString):
    """Hacky class for handling the extra FULL that OBME includes after the
    effects for some reason. We can't just pack this one into MelEffects above
    since otherwise we'd have duplicate signatures in the same load, and
    MelDistributor would just distribute the load to the same MelGroups
    backend, which would blindly use the last FULL. Did I ever mention that
    OBME is an awfully hacky mess?"""
    def __init__(self):
        super().__init__(b'FULL', 'obme_full')

class MelMgefEdidTes4(_MelMgefCode):
    """Handles EDID for Oblivion's MGEF - we can't just use MelEdid because
    this can, of course, be a FormID thanks to OBME."""
    def __init__(self):
        # Always 4 bytes for the magic effect code plus a null terminator
        super().__init__(b'EDID', ['4s', 's'], 'mgef_edid', '_mgef_edid_null',
            mgef_code_attr='mgef_edid', emulated_attr='eid')

# API - FO3 and FNV -----------------------------------------------------------
class MelEffectsFo3(MelGroups):
    """Represents effects in FO3 and FNV - combination of EFID, EFIT and
    CTDA."""
    def __init__(self):
        super().__init__('effects',
            MelFid(b'EFID', 'effect_formid'), # Base Effect
            MelStruct(b'EFIT', ['4I', 'i'], 'magnitude', 'area', 'duration',
                'recipient', 'actorValue'),
            MelConditionsFo3(),
        )

# API - TES5 and onwards ------------------------------------------------------
class MelEffects(MelGroups):
    """Represents effects in Skyrim and newer games - combination of EFID, EFIT
    and CTDA."""
    def __init__(self):
        super().__init__('effects',
            MelFid(b'EFID', 'effect_formid'), # Base Effect
            MelStruct(b'EFIT', ['f', '2I'], 'magnitude', 'area', 'duration'),
            MelConditionList(),
        )

#------------------------------------------------------------------------------
# NVNM - Navmesh Geometry
#------------------------------------------------------------------------------
# Helpers ---------------------------------------------------------------------
_nvnm_unpack_triangle = _mk_unpacker('6h')
_nvnm_unpack_tri_extra = _mk_unpacker('fB')
_nvnm_unpack_edge_link = _mk_unpacker('2Ih')
_nvnm_unpack_door_triangle = _mk_unpacker('H2I')

_nvnm_pack_triangle = _mk_packer('6h')
_nvnm_pack_tri_extra = _mk_packer('fB')
_nvnm_pack_edge_link = _mk_packer('2Ih')
_nvnm_pack_door_triangle = _mk_packer('H2I')

# API, pt1 --------------------------------------------------------------------
class ANvnmContext:
    """Provides context info to the loading/dumping procedures below, so that
    they know what parts of the NVNM format the game and current record
    support. You have to inherit from this and set various game-specific
    fields, then use the resulting class as your MelNvnm's
    _nvnm_context_class."""
    __slots__ = ('nvnm_ver', 'form_ver')

    # Override these and set them based on whether or not they are supported by
    # the current game --------------------------------------------------------
    # The maximum version supported by the game. Also the one we should use
    # when writing records
    max_nvnm_ver: int
    # True if the "Cover Triangle Mappings" have two 16-bit integers ("Cover" &
    # "Triangle"), False if they only have one ("Triangle")
    cover_tri_mapping_has_covers: bool
    # True if the "Waypoints" structure exists
    nvnm_has_waypoints: bool

    def __init__(self, nvnm_ver: int, form_ver: int):
        self.nvnm_ver = nvnm_ver
        self.form_ver = form_ver

# NVNM Components -------------------------------------------------------------
class _AMelNvnmComponent:
    """Base class for NVNM components."""
    __slots__ = ()

    def load_comp(self, ins, nvnm_ctx: ANvnmContext, *debug_strs):
        """Loads this component from the specified input stream.."""
        raise NotImplementedError

    def dump_comp(self, out, nvnm_ctx: ANvnmContext):
        """Dumps this component to the specified output stream."""
        raise NotImplementedError

    def map_fids(self, map_function, save_fids=False):
        """Maps fids for this component. Does nothing by default, you *must*
        override this if your component or some of its children can contain
        fids."""

class _AMelNvnmListComponent(_AMelNvnmComponent):
    """Base class for NVNM components that contain a list of child components
    counted by a 32-bit integer. The first attribute in your slots must be the
    attribute you use to store your children."""
    __slots__ = ()
    # Override this and set it to the class you use to load your children
    _child_class: type

    def load_comp(self, ins, nvnm_ctx: ANvnmContext, *debug_strs):
        child_list = []
        setattr(self, self.__slots__[0], child_list)
        for _x in range(unpack_int(ins)):
            new_child = self._child_class()
            new_child.load_comp(ins, nvnm_ctx, *debug_strs)
            child_list.append(new_child)

    def dump_comp(self, out, nvnm_ctx: ANvnmContext):
        child_list = getattr(self, self.__slots__[0])
        pack_int(out, len(child_list))
        for nvnm_child in child_list:
            nvnm_child.dump_comp(out, nvnm_ctx)

class _AMelNvnmListComponentFids(_AMelNvnmListComponent):
    """Base class for NVNM list components that contain FormIDs."""
    __slots__ = ()

    def map_fids(self, map_function, save_fids=False):
        for nvnm_child in getattr(self, self.__slots__[0]):
            nvnm_child.map_fids(map_function, save_fids)

class _NvnmMain(_AMelNvnmComponent):
    """The main container for NVNM data. Passed along to all the component's
    methods (see below) to provide context and a target for reading/writing."""
    __slots__ = ('nvnm_crc', 'nvnm_pathing_cell', 'nvnm_vertices',
                 'nvnm_triangles', 'nvnm_edge_links', 'nvnm_door_triangles',
                 'nvnm_cover_array', 'nvnm_cover_triangle_map',
                 'nvnm_waypoints', 'nvnm_navmesh_grid')

    def load_comp(self, ins, nvnm_ctx: ANvnmContext, *debug_strs):
        self.nvnm_crc = _NvnmCrc()
        self.nvnm_pathing_cell = _NvnmPathingCell()
        self.nvnm_vertices = _NvnmVertices()
        self.nvnm_triangles = _NvnmTriangles()
        self.nvnm_edge_links = _NvnmEdgeLinks()
        self.nvnm_door_triangles = _NvnmDoorTriangles()
        self.nvnm_cover_array = _NvnmCoverArray()
        self.nvnm_cover_triangle_map = _NvnmCoverTriangleMap()
        self.nvnm_waypoints = _NvnmWaypoints()
        self.nvnm_navmesh_grid = b'' # Handled in AMelNvnm.load_mel
        for nvnm_attr in self.__slots__[:-1]:
            getattr(self, nvnm_attr).load_comp(ins, nvnm_ctx, *debug_strs)

    def dump_comp(self, out, nvnm_ctx: ANvnmContext):
        for nvnm_attr in self.__slots__[:-1]:
            getattr(self, nvnm_attr).dump_comp(out, nvnm_ctx)
        out.write(self.nvnm_navmesh_grid)

    def map_fids(self, map_function, save_fids=False):
        for nvnm_attr in self.__slots__[:-1]:
            getattr(self, nvnm_attr).map_fids(map_function, save_fids)

class _NvnmCrc(_AMelNvnmComponent):
    """CRC corresponding to several types of navmesh usage (see wbCRCValuesEnum
    in xEdit), just read and write it unaltered."""
    __slots__ = ('crc_val',)

    def load_comp(self, ins, nvnm_ctx: ANvnmContext, *debug_strs):
        self.crc_val = unpack_int(ins)

    def dump_comp(self, out, nvnm_ctx: ANvnmContext):
        pack_int(out, self.crc_val)

class _NvnmPathingCell(_AMelNvnmComponent):
    """The navmesh geometry's pathing cell. Holds basic context information
    about where this navmesh geometry is located."""
    __slots__ = ('parent_worldspace', 'parent_cell', 'cell_coord_x',
                 'cell_coord_y')

    def load_comp(self, ins, nvnm_ctx: ANvnmContext, *debug_strs):
        self.parent_worldspace = FID(unpack_int(ins))
        if self.parent_worldspace != ZERO_FID:
            self.parent_cell = None
            # The Y coordinate comes first!
            self.cell_coord_y, self.cell_coord_x = _unpack_2shorts_signed(
                ins, *debug_strs)
        else:
            self.parent_cell = FID(unpack_int(ins))
            self.cell_coord_y = None
            self.cell_coord_x = None

    def dump_comp(self, out, nvnm_ctx: ANvnmContext):
        pack_int(out, self.parent_worldspace.dump())
        if self.parent_worldspace != ZERO_FID:
            _pack_2shorts_signed(out, self.cell_coord_y, self.cell_coord_x)
        else:
            pack_int(out, self.parent_cell.dump())

    def map_fids(self, map_function, save_fids=False):
        result_pw = map_function(self.parent_worldspace)
        if save_fids:
            self.parent_worldspace = result_pw
        if self.parent_cell is not None:
            result_pc = map_function(self.parent_cell)
            if save_fids:
                self.parent_cell = result_pc

class _NvnmVertices(_AMelNvnmComponent):
    """The navmesh geometry's vertices. No FormIDs in here and no form
    version-based differences, so just handle this as big bytestring."""
    __slots__ = ('vertices_data',)

    def load_comp(self, ins, nvnm_ctx: ANvnmContext, *debug_strs):
        num_vertices = unpack_int(ins)
        # 3 floats per vertex
        self.vertices_data = ins.read(num_vertices * 12, *debug_strs)

    def dump_comp(self, out, nvnm_ctx: ANvnmContext):
        pack_int(out, len(self.vertices_data) // 12) # see above
        out.write(self.vertices_data)

class _NvnmTriangles(_AMelNvnmListComponent):
    """The navmesh geometry's triangles. Does not include FormIDs, but there
    are form version-dependent differences so we have to load and upgrade the
    format if neccessary."""
    __slots__ = ('triangles',)

    class _NvnmTriangle(_AMelNvnmComponent):
        """Helper class representing a single triangle."""
        __slots__ = ('vertex_0', 'vertex_1', 'vertex_2', 'edge_0_1',
                     'edge_1_2', 'edge_2_0', 'tri_height', 'tri_unknown',
                     'tri_flags', 'tri_cover_flags')

        def load_comp(self, ins, nvnm_ctx: ANvnmContext, *debug_strs):
            self.vertex_0, self.vertex_1, self.vertex_2, self.edge_0_1, \
            self.edge_1_2, self.edge_2_0 = _nvnm_unpack_triangle(
                ins, *debug_strs)
            # Since form version 57 (introduced in FO4), extra data is included
            # in triangles
            if nvnm_ctx.form_ver > 57:
                self.tri_height, self.tri_unknown = _nvnm_unpack_tri_extra(
                    ins, *debug_strs)
            else:
                self.tri_height = 0.0
                self.tri_unknown = 0
            # Could decode these, but there's little point
            self.tri_flags, self.tri_cover_flags = _unpack_2shorts_signed(
                ins, *debug_strs)

        def dump_comp(self, out, nvnm_ctx: ANvnmContext):
            _nvnm_pack_triangle(out, self.vertex_0, self.vertex_1,
                self.vertex_2, self.edge_0_1, self.edge_1_2, self.edge_2_0)
            if nvnm_ctx.form_ver > 57:
                _nvnm_pack_tri_extra(out, self.tri_height, self.tri_unknown)
            _pack_2shorts_signed(self.tri_flags, self.tri_cover_flags)

    _child_class = _NvnmTriangle

class _NvnmEdgeLinks(_AMelNvnmListComponentFids):
    """The navmesh geometry's edge links. Contains FormIDs and form
    version-dependent differences, so needs decoding."""
    __slots__ = ('edge_links',)

    class _NvnmEdgeLink(_AMelNvnmComponent):
        """Helper class representing a single edge link."""
        __slots__ = ('edge_link_type', 'edge_link_mesh', 'triangle_index',
                     'edge_index')

        def load_comp(self, ins, nvnm_ctx: ANvnmContext, *debug_strs):
            self.edge_link_type, self.edge_link_mesh, \
            self.triangle_index = _nvnm_unpack_edge_link(ins, *debug_strs)
            self.edge_link_mesh = FID(self.edge_link_mesh)
            # Form version 127 (introduced in FO4) added another byte
            if nvnm_ctx.form_ver > 127:
                self.edge_index = unpack_byte(ins)
            else:
                self.edge_index = 0

        def dump_comp(self, out, nvnm_ctx: ANvnmContext):
            _nvnm_pack_edge_link(out, self.edge_link_type,
                self.edge_link_mesh.dump(), self.triangle_index)
            if nvnm_ctx.form_ver > 127:
                pack_byte(out, self.edge_index)

        def map_fids(self, map_function, save_fids=False):
            result_mesh = map_function(self.edge_link_mesh)
            if save_fids:
                self.edge_link_mesh = result_mesh

    _child_class = _NvnmEdgeLink

class _NvnmDoorTriangles(_AMelNvnmListComponentFids):
    """The navmesh geometry's door triangles. Contains FormIDs and also has to
    be sorted."""
    __slots__ = ('door_triangles',)

    class _NvnmDoorTriangle(_AMelNvnmComponent):
        __slots__ = ('triangle_before_door', 'door_type', 'door_fid')

        def load_comp(self, ins, nvnm_ctx: ANvnmContext, *debug_strs):
            self.triangle_before_door, self.door_type, \
            self.door_fid = _nvnm_unpack_door_triangle(ins, *debug_strs)
            # door_fid is only a FormID if door_type != 0
            if self.door_type:
                self.door_fid = FID(self.door_fid)

        def dump_comp(self, out, nvnm_ctx: ANvnmContext):
            door_fid_short = (self.door_fid.dump() if self.door_type else
                              self.door_fid)
            _nvnm_pack_door_triangle(out, self.triangle_before_door,
                self.door_type, door_fid_short)

        def map_fids(self, map_function, save_fids=False):
            if self.door_type:
                result_door = map_function(self.door_fid)
                if save_fids:
                    self.door_fid = result_door

    _child_class = _NvnmDoorTriangle

    def dump_comp(self, out, nvnm_ctx: ANvnmContext):
        self.door_triangles.sort(
            key=attrgetter_cache[('triangle_before_door', 'door_fid')])
        super().dump_comp(out, nvnm_ctx)

class _NvnmCoverArray(_AMelNvnmComponent):
    """The navmesh geometry's cover array. No FormIDs in here and no form
    version-based differences, so just handle this as big bytestring."""
    __slots__ = ('cover_array_data',)

    def load_comp(self, ins, nvnm_ctx: ANvnmContext, *debug_strs):
        # Doesn't exist on NVNM version 12 and lower
        if nvnm_ctx.nvnm_ver > 12:
            num_covers = unpack_int(ins)
            # 2 shorts & 4 bytes per cover
            self.cover_array_data = ins.read(num_covers * 8, *debug_strs)
        else:
            # If we upgrade, we'll have to write out at least a counter with a
            # zero, so set this to an empty bytestring
            self.cover_array_data = b''

    def dump_comp(self, out, nvnm_ctx: ANvnmContext):
        if nvnm_ctx.nvnm_ver > 12:
            pack_int(out, len(self.cover_array_data) // 8) # see above
            out.write(self.cover_array_data)

class _NvnmCoverTriangleMap(_AMelNvnmComponent):
    """The navmesh geometry's cover triangles/cover triangle mappings. No
    FormIDs in here and while the size of the array elements does differ, it
    only differs per game, so we can handle this as a bytestring."""
    __slots__ = ('cover_triangle_map_data',)

    def load_comp(self, ins, nvnm_ctx: ANvnmContext, *debug_strs):
        # Before FO4, this was just a list of cover triangles. Since FO4, it
        # maps covers to triangles
        cover_tris_size = 4 if nvnm_ctx.cover_tri_mapping_has_covers else 2
        num_cover_tris = unpack_int(ins)
        self.cover_triangle_map_data = ins.read(
            num_cover_tris * cover_tris_size, *debug_strs)

    def dump_comp(self, out, nvnm_ctx: ANvnmContext):
        ct_size = 4 if nvnm_ctx.cover_tri_mapping_has_covers else 2
        pack_int(out, len(self.cover_triangle_map_data) // ct_size)
        out.write(self.cover_triangle_map_data)

class _NvnmWaypoints(_AMelNvnmComponent):
    """The navmesh geometry's waypoints. No FormIDs in here and the only form
    version-dependent difference is whether it even exists, so load as a
    bytestring."""
    __slots__ = ('waypoints_data',)

    def load_comp(self, ins, nvnm_ctx: ANvnmContext, *debug_strs):
        # Only since FO4 and not available on NVNM version 11 and lower
        if nvnm_ctx.nvnm_has_waypoints and nvnm_ctx.nvnm_ver > 11:
            num_waypoints = unpack_int(ins)
            # 3 floats + 1 short + 1 int per waypoint
            self.waypoints_data = ins.read(num_waypoints * 18, *debug_strs)
        else:
            # Same reasoning as in _NvnmCoverArray
            self.waypoints_data = b''

    def dump_comp(self, out, nvnm_ctx: ANvnmContext):
        if nvnm_ctx.nvnm_has_waypoints and nvnm_ctx.nvnm_ver > 11:
            pack_int(out, len(self.waypoints_data) // 18) # see above
            out.write(self.waypoints_data)

# API, pt2 --------------------------------------------------------------------
class AMelNvnm(MelBase):
    """Navmesh Geometry. A complex subrecord that requires careful loading via
    custom code. Needs to be subclassed per game to set things like the game's
    maxinum NVNM version - see also ANvnmContext."""
    # A class holding necessary context when reading/writing records
    _nvnm_context_class: type[ANvnmContext]

    def __init__(self):
        super().__init__(b'NVNM', 'navmesh_geometry')

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        # We'll need to know the position at which the NVNM subrecord ends
        # later, so figure it out now
        ins.seek(size_, 1, *debug_strs)
        end_of_nvnm = ins.tell()
        ins.seek(-size_, 1, *debug_strs)
        # Load the header, verify version
        record.navmesh_geometry = nvnm = _NvnmMain()
        nvnm_ver = unpack_int(ins)
        nvnm_max_ver = self._nvnm_context_class.max_nvnm_ver
        if nvnm_ver > nvnm_max_ver:
            raise ModError(ins.inName, f'NVNM version {nvnm_ver} is too new '
                                       f'for this game (at most version '
                                       f'{nvnm_max_ver} supported)')
        # Now we can create the context and load the various components
        nvnm_ctx = self._nvnm_context_class(
            nvnm_ver, record.header.form_version)
        nvnm.load_comp(ins, nvnm_ctx, *debug_strs)
        # This last part is identical between all games and does not contain
        # any FormIDs, but its size is complex to determine. Much easier to
        # just read all leftover bytes in the subrecord and store them as a
        # bytestring
        nvnm.nvnm_navmesh_grid = ins.read(
            end_of_nvnm - ins.tell(), *debug_strs)

    def pack_subrecord_data(self, record):
        out = BytesIO()
        nvnm_ctx = self._nvnm_context_class(
            self._nvnm_context_class.max_nvnm_ver, record.header.form_version)
        record.navmesh_geometry.dump_comp(out, nvnm_ctx)
        return out.getvalue()

    def hasFids(self, formElements):
        formElements.add(self)

    def mapFids(self, record, function, save_fids=False):
        if record.navmesh_geometry is not None:
            record.navmesh_geometry.map_fids(function, save_fids)

#------------------------------------------------------------------------------
# OBTS etc. - Object Templates
#------------------------------------------------------------------------------
# Implementation --------------------------------------------------------------
class _MelObts(MelPartialCounter):
    """Handles the OBTS subrecord. Very complex, contains three arrays (two
    with substructure) and data-sensitive loading that can contain FormIDs."""
    def __init__(self):
        super().__init__(MelStruct(b'OBTS',
            ['2I', 'B', 's', 'B', 's', 'h', '2B'], 'obts_include_count',
            'obts_property_count', 'obts_level_min', 'obts_unused1',
            'obts_level_max', 'obts_unused2', 'obts_addon_index',
            'obts_default', 'obts_keyword_count'),
            counters={'obts_include_count': 'obts_includes',
                      'obts_property_count': 'obts_properties',
                      'obts_keyword_count': 'obts_keywords'})

    def getSlotsUsed(self):
        return ('obts_keywords', 'obts_min_level_for_ranks',
                'obts_alt_levels_per_tier', 'obts_includes',
                'obts_properties', *super().getSlotsUsed())

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        # Unpack the static portion using MelStruct
        super().load_mel(record, ins, sub_type, self.static_size, *debug_strs)
        # Load the keywords - the counter was loaded just now by the struct
        record.obts_keywords = [FID(unpack_int(ins))
                                for _x in range(record.obts_keyword_count)]
        record.obts_min_level_for_ranks = unpack_byte(ins)
        record.obts_alt_levels_per_tier = unpack_byte(ins)
        # Load the includes - The include count was loaded way back at the
        # start of the struct
        record.obts_includes = []
        append_include = record.obts_includes.append
        for _x in range(record.obts_include_count):
            obts_include = _MelOmodInclude()
            obts_include.load_include(ins, *debug_strs)
            append_include(obts_include)
        # Load the properties - this count was right after the include count
        record.obts_properties = []
        append_property = record.obts_properties.append
        for _x in range(record.obts_property_count):
            obts_property = _MelOmodProperty()
            obts_property.load_property(ins, *debug_strs)
            append_property(obts_property)

    def pack_subrecord_data(self, record):
        out = BytesIO()
        out.write(super().pack_subrecord_data(record))
        for obts_kwd in record.obts_keywords:
            pack_int(out, obts_kwd.dump())
        pack_byte(out, record.obts_min_level_for_ranks)
        pack_byte(out, record.obts_alt_levels_per_tier)
        for obts_include in record.obts_includes:
            obts_include.dump_include(out)
        for obts_property in record.obts_properties:
            obts_property.dump_property(out)
        return out.getvalue()

    def mapFids(self, record, function, save_fids=False):
        super().mapFids(record, function, save_fids)
        result_kwds = [function(obts_kwd) for obts_kwd in record.obts_keywords]
        if save_fids: record.obts_keywords = result_kwds
        for obts_include in record.obts_includes:
            obts_include.map_include_fids(function, save_fids)
        for obts_property in record.obts_properties:
            obts_property.map_property_fids(function, save_fids)

# API -------------------------------------------------------------------------
class MelObjectTemplate(MelSequential):
    """Handles an object template, which is a complex subrecord structure
    containing the OBTS subrecord. Note that this also contains a FULL
    subrecord, so you will probably have to use a distributor."""
    def __init__(self):
        self._ot_end_marker = MelBaseR(b'STOP', 'ot_combinations_end_marker')
        super().__init__(
            MelCounter(MelUInt32(b'OBTE', 'ot_combination_count'),
                counts='ot_combinations'),
            MelUnorderedGroups('ot_combinations',
                MelBase(b'OBTF', 'editor_only'),
                MelFull(),
                _MelObts(),
            ),
            self._ot_end_marker,
        )

    ##: I already wrote code like this for CS2E and CS2F up above, this is
    # screaming for a new building block
    def dumpData(self, record, out):
        for element in self.elements:
            # STOP is required iff there are any combinations present
            if record.ot_combinations or element is not self._ot_end_marker:
                element.dumpData(record, out)

#------------------------------------------------------------------------------
# STAG's TNAM
#------------------------------------------------------------------------------
class MelStagTnam(MelString):
    """Handles the STAG subrecord TNAM (Sound). The complication here is that
    it has a FormID before a variable-length string. If this becomes more
    common, we should come up with a similar solution to MelArray that lets us
    place an arbitrary prelude element before a string."""
    def __init__(self):
        super().__init__(b'TNAM', 'stag_sound_action')

    def getSlotsUsed(self):
        return 'stag_sound_fid', *super().getSlotsUsed()

    def hasFids(self,formElements):
        formElements.add(self)

    def mapFids(self, record, function, save_fids=False):
        result = function(record.stag_sound_fid)
        if save_fids:
            record.stag_sound_fid = result

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        record.stag_sound_fid = FID(unpack_int(ins))
        super().load_mel(record, ins, sub_type, size_ - 4, *debug_strs)

    def pack_subrecord_data(self, record):
        return (record.stag_sound_fid.dump(),
                super().pack_subrecord_data(record))

    def packSub(self, out: BinaryIO, stag_sr_data: tuple[int, str]):
        byte_string = struct_pack('I', stag_sr_data[0])
        byte_string += bolt.encode_complex_string(stag_sr_data[1],
            self.maxSize, self.minSize, self.encoding)
        # Skip MelString's packSub, we already encoded the string
        super(MelString, self).packSub(out, byte_string)

#------------------------------------------------------------------------------
# VMAD - Virtual Machine Adapter
#------------------------------------------------------------------------------
# Helpers ---------------------------------------------------------------------
_vmad_key_fragments = attrgetter_cache['fragment_index']
_vmad_key_properties = attrgetter_cache['prop_name']
_vmad_key_qust_aliases = attrgetter_cache['alias_ref_obj']
_vmad_key_qust_fragments = attrgetter_cache[('quest_stage',
                                            'quest_stage_index')]
_vmad_key_script = attrgetter_cache['script_name']

_vmad_unpack_objref_v1 = _mk_unpacker('IhH')
_vmad_unpack_objref_v2 = _mk_unpacker('HhI')

_vmad_pack_objref_v2 = _mk_packer('HhI')

def _dump_str16(out, str_val: str):
    """Encodes the specified string using the plugin encoding and writes data
    for both its length (as a uint16) and its encoded value to the specified
    output stream."""
    encoded_str = bolt.encode(str_val, firstEncoding=bolt.pluginEncoding)
    pack_short(out, len(encoded_str))
    out.write(encoded_str)

def _dump_vmad_str16(out, str_val: str):
    """Encodes the specified string using UTF-8 and writes data for both its
    length (as a uint16) and its encoded value to the specified output
    stream."""
    encoded_str = str_val.encode('utf8')
    pack_short(out, len(encoded_str))
    out.write(encoded_str)

def _read_str16(ins) -> str:
    """Reads a 16-bit length integer, then reads a string in that length."""
    return bolt.decoder(unpack_str16(ins))

def _read_vmad_str16(ins) -> str:
    """Reads a 16-bit length integer, then reads a string in that length.
    Always uses UTF-8 to decode."""
    return unpack_str16(ins).decode('utf8')

class _AVmadComponent(object):
    """Abstract base class for VMAD components. Specify a '_processors'
    class variable to use. Syntax: dict, mapping an attribute name for the
    record to a tuple containing an unpacker, a packer and a size. 'str16' is a
    special value that instead calls _read_str16/_dump_str16 to handle the
    matching attribute.

    You can override any of the methods specified below to do other things
    after or before '_processors' has been evaluated, just be sure to call
    super().{dump,load}_data(...) when appropriate."""
    _processors: dict[str, tuple[callable, callable, int] | str] = {}

    def load_frag(self, record, ins, vmad_ctx: AVmadContext, *debug_strs):
        """Loads data for this fragment from the specified input stream and
        attaches it to the specified record. The VMAD context is also given."""
        self._load_processors(self._processors, record, ins, *debug_strs)

    @staticmethod
    def _load_processors(processors, record, ins, *debug_strs):
        """Runs the specified processors for loading. Broken out of load_frag
        to let the v6 handlers take advantage of it."""
        ins_unpack = ins.unpack
        for attr, fmt in processors.items():
            if fmt != 'str16':
                setattr(record, attr, ins_unpack(fmt[0], fmt[2],
                    *debug_strs)[0])
            else:
                setattr(record, attr, _read_str16(ins))

    def dump_frag(self, record, out, vmad_ctx: AVmadContext):
        """Dumps data for this fragment using the specified record and writes
        it to the specified output stream. The VMAD context is also given."""
        self._dump_processors(self._processors, record, out)

    @staticmethod
    def _dump_processors(processors, record, out):
        """Runs the specified processors for dumping. Broken out of dump_frag
        to let the v6 handlers take advantage of it."""
        out_write = out.write
        for attr, fmt in processors.items():
            attr_val = getattr(record, attr)
            if fmt != 'str16':
                out_write(fmt[1](attr_val))
            else:
                _dump_str16(out, attr_val)

    @bolt.fast_cached_property
    def _component_class(self):
        # TODO(inf) This seems to work - what we're currently doing in
        #  records code, namely reassigning __slots__, does *nothing*:
        #  https://stackoverflow.com/questions/27907373/dynamically-change-slots-in-python-3
        #  Fix that by refactoring class creation like this for
        #  MelBase/MelSet etc.!
        class _MelComponentInstance(MelObject):
            __slots__ = self.used_slots
        return _MelComponentInstance

    def make_new(self):
        """Creates a new runtime instance of this component with the
        appropriate __slots__ set."""
        return self._component_class()

    # Note that there is no has_fids - components (e.g. properties) with fids
    # could dynamically get added at runtime, so we must always call map_fids
    # to make sure.
    def map_fids(self, record, map_function, save_fids=False):
        """Maps fids for this component. Does nothing by default, you *must*
        override this if your component or some of its children can contain
        fids!"""

    @property
    def used_slots(self):
        """Returns a list containing the slots needed by this component. Note
        that this should not change at runtime, since the class created with it
        is cached - see make_new above."""
        return list(self._processors)

class _AFixedContainer(_AVmadComponent):
    """Abstract base class for components that contain a fixed number of other
    components. Which ones are present is determined by a flags field. You
    need to specify a processor that sets an attribute named, by default,
    fragment_flags to the right value (you can change the name using the class
    variable _flags_attr). Additionally, you have to set _flags_mapper to a
    bolt.Flags instance that can be used for decoding the flags and
    _flags_to_children to a dict that maps flag names to child attribute names.
    The order of this dict is the order in which the children will be read and
    written. Finally, you need to set _child_loader to an instance of the
    correct class for your class type. Note that you have to do this inside
    __init__, as it is an instance variable."""
    # Abstract - to be set by subclasses
    _flags_attr = 'fragment_flags' # FIXME after refactoring, check if this is still never overriden - if so, get rid of it and use fragment_flags directly
    _flags_mapper: Flags
    _flags_to_children: dict[str, str]
    _child_loader: _AVmadComponent

    def load_frag(self, record, ins, vmad_ctx: AVmadContext, *debug_strs):
        # Load the regular attributes first
        super().load_frag(record, ins, vmad_ctx, *debug_strs)
        # Then, process the flags and decode them
        child_flags = self._flags_mapper(
            getattr(record, self._flags_attr))
        setattr(record, self._flags_attr, child_flags)
        # Finally, inspect the flags and load the appropriate children. We must
        # always load and dump these in the exact order specified by the
        # subclass!
        new_child = self._child_loader.make_new
        load_child = self._child_loader.load_frag
        for flag_attr, child_attr in self._flags_to_children.items():
            cont_child = None
            if getattr(child_flags, flag_attr):
                cont_child = new_child()
                load_child(cont_child, ins, vmad_ctx, *debug_strs)
            setattr(record, child_attr, cont_child)

    def dump_frag(self, record, out, vmad_ctx: AVmadContext):
        # Update the flags first, then dump the regular attributes
        # Also use this chance to store the value of each present child
        children = []
        child_flags = getattr(record, self._flags_attr)
        store_child = children.append
        for flag_attr, child_attr in self._flags_to_children.items():
            cont_child = getattr(record, child_attr)
            write_child = cont_child is not None
            # No need to store children we won't be writing out
            if write_child:
                store_child(cont_child)
            setattr(child_flags, flag_attr, write_child)
        super().dump_frag(record, out, vmad_ctx)
        # Then, dump each child for which the flag is now set, in order
        dump_child = self._child_loader.dump_frag
        for cont_child in children:
            dump_child(cont_child, out, vmad_ctx)

    @property
    def used_slots(self):
        return super().used_slots + list(self._flags_to_children.values())

class _AVariableContainer(_AVmadComponent):
    """Abstract base class for components that contain a variable number of
    iother components, with the count stored in a preceding integer. You need
    to specify a processor that sets an attribute named, by default,
    fragment_count to the right value (you can change the name using the class
    variable _counter_attr). Additionally, you have to set _child_loader to an
    instance of the correct class for your child type. Note that you have
    to do this inside __init__, as it is an instance variable. The attribute
    name used for the list of children may also be customized via the class
    variable _children_attr."""
    # Abstract - to be set by subclasses
    _children_attr = 'fragments'
    _counter_attr = 'fragment_count'
    _child_loader: _AVmadComponent

    def load_frag(self, record, ins, vmad_ctx: AVmadContext, *debug_strs):
        # Load the regular attributes first
        super().load_frag(record, ins, vmad_ctx, *debug_strs)
        # Then, load each child
        children = []
        new_child = self._child_loader.make_new
        load_child = self._child_loader.load_frag
        append_child = children.append
        for _x in range(getattr(record, self._counter_attr)):
            cont_child = new_child()
            load_child(cont_child, ins, vmad_ctx, *debug_strs)
            append_child(cont_child)
        setattr(record, self._children_attr, children)

    def dump_frag(self, record, out, vmad_ctx: AVmadContext):
        # Update the child count, then dump the processors' data
        children = getattr(record, self._children_attr)
        setattr(record, self._counter_attr, len(children))
        super().dump_frag(record, out, vmad_ctx)
        # Finally, dump each child
        dump_child = self._child_loader.dump_frag
        for cont_child in children:
            dump_child(cont_child, out, vmad_ctx)

    def map_fids(self, record, map_function, save_fids=False):
        map_child = self._child_loader.map_fids
        for cont_child in getattr(record, self._children_attr):
            map_child(cont_child, map_function, save_fids)

    @property
    def used_slots(self):
        return super().used_slots + [self._children_attr]

class _ObjectRef(object):
    """An object ref is a FormID and an AliasID."""
    __slots__ = ('_aid', '_fid')

    def __init__(self, aid, fid):
        self._aid = aid # The AliasID
        self._fid = FID(fid) # The FormID

    def dump_ref(self, out):
        """Dumps this object ref to the specified output stream."""
        # Write only object format v2
        _vmad_pack_objref_v2(out, 0, self._aid, self._fid.dump())

    def map_ref_fids(self, map_function, save_fids=False):
        """Maps the specified function onto this object ref's fid. If save_fids
        is True, the result is stored, otherwise it is discarded."""
        result = map_function(self._fid)
        if save_fids: self._fid = result

    def __lt__(self, other):
        if not isinstance(other, _ObjectRef):
            return NotImplemented
        # Sort key is *only* the FormID, see wbScriptPropertyObject in xEdit
        return self._fid < other._fid

    def __repr__(self):
        return f'_ObjectRef({self._aid}, {self._fid})'

    @classmethod
    def array_from_file(cls, ins, vmad_ctx: AVmadContext, *debug_strs):
        """Reads an array of object refs directly from the specified input
        stream. Needs the current VMAD context as well."""
        make_ref = cls.from_file
        return [make_ref(ins, vmad_ctx, *debug_strs)
                for _x in range(unpack_int(ins))]

    @staticmethod
    def dump_array(out, target_list: list[_ObjectRef]):
        """Dumps the specified list of object refs to the specified output
        stream. This includes a leading uint32 denoting the size."""
        pack_int(out, len(target_list))
        for obj_ref in target_list:
            obj_ref.dump_ref(out)

    @classmethod
    def from_file(cls, ins, vmad_ctx: AVmadContext, *debug_strs):
        """Reads an object ref directly from the specified input stream. Needs
        the current VMAD context as well."""
        if vmad_ctx.obj_format == 1: # object format v1 - fid, aid, unused
            ref_fid, aid, _unused = _vmad_unpack_objref_v1(ins, *debug_strs)
        else: # object format v2 - unused, aid, fid
            _unused, aid, ref_fid = _vmad_unpack_objref_v2(ins, *debug_strs)
        return cls(aid, ref_fid)

# Fragments -------------------------------------------------------------------
class _FragmentBasic(_AVmadComponent):
    """Implements the following fragments:

        - SCEN OnBegin/OnEnd fragments
        - PACK fragments
        - INFO fragments"""
    _processors = {
        'unknown1':      get_structs('b'),
        'script_name':   'str16',
        'fragment_name': 'str16',
    }

class _FragmentPERK(_AVmadComponent):
    """Implements PERK fragments."""
    _processors = {
        'fragment_index': get_structs('H'),
        'unknown1':       get_structs('h'),
        'unknown2':       get_structs('b'),
        'script_name':    'str16',
        'fragment_name':  'str16',
    }

class _FragmentQUST(_AVmadComponent):
    """Implements QUST fragments."""
    _processors = {
        'quest_stage':       get_structs('H'),
        'unknown1':          get_structs('h'),
        'quest_stage_index': get_structs('I'),
        'unknown2':          get_structs('b'),
        'script_name':       'str16',
        'fragment_name':     'str16',
    }

class _FragmentSCENPhase(_AVmadComponent):
    """Implements SCEN phase fragments."""
    _processors = {
        'fragment_flags': get_structs('B'), # on_start, on_completion
        'phase_index':    get_structs('B'),
        'unknown1':       get_structs('h'),
        'unknown2':       get_structs('b'),
        'unknown3':       get_structs('b'),
        'script_name':    'str16',
        'fragment_name':  'str16',
    }

# Fragment Headers ------------------------------------------------------------
class _AVmadHandlerV6Mixin(_AVmadComponent):
    """Mixin for VMAD handlers that had their filename field replaced with a
    script in VMAD v6."""
    # The processors used when loading/dumping the v6 version of this handler.
    # The pre_processors are used right before the script is handled, the
    # post_processors right after - see below
    _v6_pre_processors: dict[str, tuple[callable, callable, int] | str]
    _v6_post_processors: dict[str, tuple[callable, callable, int] | str]
    # The processors used when loading/dumping the v5 version of this handler
    _v5_processors: dict[str, tuple[callable, callable, int] | str]

    def __init__(self):
        self._script_loader = _Script()

    def load_frag(self, record, ins, vmad_ctx: AVmadContext, *debug_strs):
        if vmad_ctx.vmad_ver >= 6:
            # Run the pre-processors, load the script, run the post-processors,
            # then call super to handle fragments
            self._load_processors(self._v6_pre_processors, record, ins,
                *debug_strs)
            record.frag_script = frag_sc = self._script_loader.make_new()
            self._script_loader.load_frag(frag_sc, ins, vmad_ctx, *debug_strs)
            record.file_name = None
            self._load_processors(self._v6_post_processors, record, ins,
                *debug_strs)
            self._processors = {} # handled by pre/post above
            super().load_frag(record, ins, vmad_ctx, *debug_strs)
        else:
            # For v5, we can use the regular loading, then upgrade the script
            # (but only if we will actually end up dumping out >= v6, otherwise
            # save the overhead)
            self._processors = self._v5_processors
            super().load_frag(record, ins, vmad_ctx, *debug_strs)
            if vmad_ctx.max_vmad_ver >= 6:
                record.frag_script = frag_sc = self._script_loader.make_new()
                frag_sc.script_name = record.file_name
                frag_sc.script_status = 0 # Defaults to 0 (local script)
                frag_sc.property_count = 0
                frag_sc.properties = []
            else:
                record.frag_script = None

    def dump_frag(self, record, out, vmad_ctx: AVmadContext):
        if vmad_ctx.vmad_ver >= 6:
            # Run the pre-processors, dump the script, run the post-processors,
            # then call super to handle fragments
            self._dump_processors(self._v6_pre_processors, record, out)
            self._script_loader.dump_frag(record.frag_script, out, vmad_ctx)
            self._dump_processors(self._v6_post_processors, record, out)
            self._processors = {} # handled by pre/post above
            super().dump_frag(record, out, vmad_ctx)
        else:
            # For v5, we can use the regular dumping
            self._processors = self._v5_processors
            super().dump_frag(record, out, vmad_ctx)

    def map_fids(self, record, map_function, save_fids=False):
        if (frag_sc := record.frag_script) is not None:
            self._script_loader.map_fids(frag_sc, map_function, save_fids)
        super().map_fids(record, map_function, save_fids)

    @property
    def used_slots(self):
        return super().used_slots + ['frag_script'] + list(
            set(self._v5_processors) | set(self._v6_pre_processors) |
            set(self._v6_post_processors))

class _VmadHandlerINFO(_AVmadHandlerV6Mixin, _AFixedContainer):
    """Implements special VMAD handling for INFO records."""
    _v6_pre_processors = {
        'extra_bind_data_version': get_structs('b'),
        'fragment_flags':          get_structs('B'),
    }
    _v6_post_processors = {}
    _v5_processors = {
        'extra_bind_data_version': get_structs('b'),
        'fragment_flags':          get_structs('B'),
        'file_name':               'str16',
    }
    class _flags_mapper(Flags):
        on_begin: bool
        on_end: bool
    _flags_to_children = {
        'on_begin': 'begin_frag',
        'on_end':   'end_frag',
    }

    def __init__(self):
        super().__init__()
        self._child_loader = _FragmentBasic()

class _VmadHandlerPACK(_AVmadHandlerV6Mixin, _AFixedContainer):
    """Implements special VMAD handling for PACK records."""
    _v6_pre_processors = {
        'extra_bind_data_version': get_structs('b'),
        'fragment_flags':          get_structs('B'),
    }
    _v6_post_processors = {}
    _v5_processors = {
        'extra_bind_data_version': get_structs('b'),
        'fragment_flags':          get_structs('B'),
        'file_name':               'str16',
    }
    class _flags_mapper(Flags):
        on_begin: bool
        on_end: bool
        on_change: bool
    _flags_to_children = {
        'on_begin':  'begin_frag',
        'on_end':    'end_frag',
        'on_change': 'change_frag',
    }

    def __init__(self):
        super().__init__()
        self._child_loader = _FragmentBasic()

class _VmadHandlerPERK(_AVmadHandlerV6Mixin, _AVariableContainer):
    """Implements special VMAD handling for PERK records."""
    _v6_pre_processors = {
        'extra_bind_data_version': get_structs('b'),
    }
    _v6_post_processors = {
        'fragment_count':          get_structs('H'),
    }
    _v5_processors = {
        'extra_bind_data_version': get_structs('b'),
        'file_name':               'str16',
        'fragment_count':          get_structs('H'),
    }

    def __init__(self):
        super().__init__()
        self._child_loader = _FragmentPERK()

    def dump_frag(self, record, out, vmad_ctx: AVmadContext):
        record.fragments.sort(key=_vmad_key_fragments)
        super().dump_frag(record, out, vmad_ctx)

class _VmadHandlerQUST(_AVariableContainer):
    """Implements special VMAD handling for QUST records."""
    _processors = {
        'extra_bind_data_version': get_structs('b'),
        'fragment_count':          get_structs('H'),
        'file_name':               'str16',
    }

    def __init__(self):
        self._child_loader = _FragmentQUST()
        self._script_loader = _AnonScript()
        self._alias_loader = _Alias()

    def load_frag(self, record, ins, vmad_ctx: AVmadContext, *debug_strs):
        # Load the regular fragments first
        super().load_frag(record, ins, vmad_ctx, *debug_strs)
        # Delegate to the script's handler - this will do nothing on VMAD < v6
        record.frag_script = frag_sc = self._script_loader.make_new()
        frag_sc.script_name = record.file_name
        self._script_loader.load_frag(frag_sc, ins, vmad_ctx, *debug_strs)
        # Then, load each alias
        record.qust_aliases = []
        new_alias = self._alias_loader.make_new
        load_alias = self._alias_loader.load_frag
        append_alias = record.qust_aliases.append
        for _x in range(unpack_short(ins)):
            q_alias = new_alias()
            load_alias(q_alias, ins, vmad_ctx, *debug_strs)
            append_alias(q_alias)

    def dump_frag(self, record, out, vmad_ctx: AVmadContext):
        # Dump the regular fragments first
        record.fragments.sort(key=_vmad_key_qust_fragments)
        super().dump_frag(record, out, vmad_ctx)
        # Delegate to the script's handler - this will do nothing on VMAD < v6
        self._script_loader.dump_frag(record.frag_script, out, vmad_ctx)
        # Then, dump each alias
        q_aliases = record.qust_aliases
        q_aliases.sort(key=_vmad_key_qust_aliases)
        pack_short(out, len(q_aliases))
        dump_alias = self._alias_loader.dump_frag
        for q_alias in q_aliases:
            dump_alias(q_alias, out, vmad_ctx)

    def map_fids(self, record, map_function, save_fids=False):
        # No need to call parent, QUST fragments can't contain fids
        self._script_loader.map_fids(record.frag_script, map_function,
            save_fids)
        map_alias = self._alias_loader.map_fids
        for q_alias in record.qust_aliases:
            map_alias(q_alias, map_function, save_fids)

    @property
    def used_slots(self):
        return super().used_slots + ['qust_aliases', 'frag_script']

class _VmadHandlerSCEN(_AVmadHandlerV6Mixin, _AFixedContainer):
    """Implements special VMAD handling for SCEN records."""
    _v6_pre_processors = {
        'extra_bind_data_version': get_structs('b'),
        'fragment_flags':          get_structs('B'),
    }
    _v6_post_processors = {}
    _v5_processors = {
        'extra_bind_data_version': get_structs('b'),
        'fragment_flags':          get_structs('B'),
        'file_name':               'str16',
    }
    class _flags_mapper(Flags):
        on_begin: bool
        on_end: bool
    _flags_to_children = {
        'on_begin': 'begin_frag',
        'on_end':   'end_frag',
    }

    def __init__(self):
        super().__init__()
        self._child_loader = _FragmentBasic()
        self._phase_loader = _FragmentSCENPhase()

    def load_frag(self, record, ins, vmad_ctx: AVmadContext, *debug_strs):
        # First, load the regular attributes and fragments
        super().load_frag(record, ins, vmad_ctx, *debug_strs)
        # Then, load each phase fragment
        record.phase_fragments = []
        new_fragment = self._phase_loader.make_new
        load_fragment = self._phase_loader.load_frag
        append_fragment = record.phase_fragments.append
        for _x in range(unpack_short(ins)):
            phase_fragment = new_fragment()
            load_fragment(phase_fragment, ins, vmad_ctx, *debug_strs)
            append_fragment(phase_fragment)

    def dump_frag(self, record, out, vmad_ctx: AVmadContext):
        # First, dump the regular attributes and fragments
        super().dump_frag(record, out, vmad_ctx)
        # Then, dump each phase fragment
        phase_frags = record.phase_fragments
        pack_short(out, len(phase_frags))
        dump_fragment = self._phase_loader.dump_frag
        for phase_fragment in phase_frags:
            dump_fragment(phase_fragment, out, vmad_ctx)

    @property
    def used_slots(self):
        return super().used_slots + ['phase_fragments']

# Scripts -----------------------------------------------------------------
class _Script(_AVariableContainer):
    """Represents a single script."""
    _v4_processors = {
        'script_name':    'str16',
        'script_status':  get_structs('B'),
        'property_count': get_structs('H'),
    }
    _v3_processors = {
        'script_name':    'str16',
        'property_count': get_structs('H'),
    }
    _children_attr = 'properties'
    _counter_attr = 'property_count'

    def __init__(self):
        self._child_loader = _Property()

    def load_frag(self, record, ins, vmad_ctx: AVmadContext, *debug_strs):
        # Need to check version, script_status got added in v4
        if vmad_ctx.vmad_ver >= 4:
            self._processors = self._v4_processors
        else:
            self._processors = self._v3_processors
            record.script_status = 0 # Defaults to 0 (local script)
        super().load_frag(record, ins, vmad_ctx, *debug_strs)

    def dump_frag(self, record, out, vmad_ctx: AVmadContext):
        record.properties.sort(key=_vmad_key_properties)
        # We only write VMAD with version >=4
        self._processors = self._v4_processors
        super().dump_frag(record, out, vmad_ctx)

    @property
    def used_slots(self):
        return super().used_slots + list(self._v4_processors)

class _AnonScript(_Script):
    """Special handler for the script inside v6 QUST fragments. The later parts
    (status and properties) are only present if the file_name inherited from
    its parent is not empty. The script itself does not load a name."""
    _v4_processors = {
        'script_status':  get_structs('B'),
        'property_count': get_structs('H'),
    }
    _v3_processors = {
        'property_count': get_structs('H'),
    }

    def load_frag(self, record, ins, vmad_ctx: AVmadContext, *debug_strs):
        if vmad_ctx.vmad_ver >= 6 and record.script_name:
            super().load_frag(record, ins, vmad_ctx, *debug_strs)
        else:
            record.script_status = 0 # Defaults to 0 (local script)
            record.property_count = 0
            record.properties = []

    def dump_frag(self, record, out, vmad_ctx: AVmadContext):
        if vmad_ctx.vmad_ver >= 6 and record.script_name:
            super().dump_frag(record, out, vmad_ctx)

    @property
    def used_slots(self):
        return super().used_slots + ['script_name']

# Properties & Structs --------------------------------------------------------
# All value types that exist - not all are available for all games, see below
_recognized_types = {0, 1, 2, 3, 4, 5, 6, 7, 11, 12, 13, 14, 15, 17}
class _AValueComponent(_AVmadComponent):
    """Base class for VMAD components that need to load a value (object ref,
    sint32, float, etc.). Currently used by properties and structs. Uses two
    slots, val_data and val_type. val_data will be loaded when you call
    _load_val and dumped when you call _dump_val, but val_type has to be loaded
    by your subclass."""
    # Only the MelObject-derived classes have slots, so fast_cached_property is
    # fine
    @bolt.fast_cached_property
    def _struct_loader(self):
        """Structs can be infinitely recursive, so we have to lazily construct
        child loaders as we go."""
        return _Struct()

    @staticmethod
    def _check_errors(val_ty, vmad_ctx: AVmadContext, err_file: str):
        """Checks the specified value type within the specified VMAD context
        for various errors, e.g. using struct types before VMAD v6."""
        if val_ty not in _recognized_types:
            raise ModError(err_file, f'Unrecognized VMAD value type {val_ty}')
        # Array types were added in v5
        if val_ty >= 11 and vmad_ctx.vmad_ver < 5:
            raise ModError(err_file,
                f'Array value type {val_ty} is only supported on VMAD '
                f'version >=5 (record has version {vmad_ctx.vmad_ver})')
        # Struct types were added in v6 (FO4)
        if val_ty in (6, 7, 17) and vmad_ctx.vmad_ver < 6:
            raise ModError(err_file,
                f'Struct value type {val_ty} is only supported on VMAD '
                f'version >=6 (record has version {vmad_ctx.vmad_ver})')

    def load_frag(self, record, ins, vmad_ctx: AVmadContext, *debug_strs):
        super().load_frag(record, ins, vmad_ctx, *debug_strs)
        val_ty = record.val_type
        self._check_errors(val_ty, vmad_ctx, ins.inName)
        # Then, read the data in the format corresponding to the val_ty
        # we just read - see below for notes on performance
        if val_ty == 0: # null
            record.val_data = None
        elif val_ty == 1: # object ref
            record.val_data = _ObjectRef.from_file(ins, vmad_ctx, *debug_strs)
        elif val_ty == 2: # string
            record.val_data = _read_vmad_str16(ins)
        elif val_ty == 3: # sint32
            record.val_data = unpack_int_signed(ins)
        elif val_ty == 4: # float
            record.val_data = unpack_float(ins)
        elif val_ty == 5: # bool (stored as uint8)
            # Faster than bool() and other, similar checks
            record.val_data = unpack_byte(ins) != 0
        elif val_ty in (6, 7): # 6 = variable, 7 = struct
            # xEdit uses the same definition for these two
            struct_ld = self._struct_loader
            record.val_data = val_struct = struct_ld.make_new()
            struct_ld.load_frag(val_struct, ins, vmad_ctx, *debug_strs)
        elif val_ty == 11: # object ref array
            record.val_data = _ObjectRef.array_from_file(ins, vmad_ctx,
                *debug_strs)
        elif val_ty == 12: # string array
            array_len = unpack_int(ins)
            record.val_data = [_read_vmad_str16(ins)
                                for _x in range(array_len)]
        elif val_ty == 13: # sint32 array
            array_len = unpack_int(ins)
            # list() is faster than [x for x in ...] on py3 and the f-string
            # is faster in this situation than old-style formatting
            record.val_data = list(struct_unpack(f'{array_len}i',
                ins.read(array_len * 4, *debug_strs)))
        elif val_ty == 14: # float array
            array_len = unpack_int(ins)
            # See comment for sint32 case above
            record.val_data = list(struct_unpack(f'{array_len}f',
                ins.read(array_len * 4, *debug_strs)))
        elif val_ty == 15: # bool array (stored as uint8 array)
            array_len = unpack_int(ins)
            # Can't use list(), but see comments for sint32 and bool cases
            # regardless for f-string and '!= 0'
            record.val_data = [x != 0 for x in struct_unpack(f'{array_len}B',
                ins.read(array_len, *debug_strs))]
        else: # val_ty == 17 - struct array
            record.val_data = struct_list = []
            new_struct = self._struct_loader.make_new
            load_struct = self._struct_loader.load_frag
            append_struct = struct_list.append
            array_len = unpack_int(ins)
            for _x in range(array_len):
                val_struct = new_struct()
                load_struct(val_struct, ins, vmad_ctx, *debug_strs)
                append_struct(val_struct)

    def dump_frag(self, record, out, vmad_ctx: AVmadContext):
        super().dump_frag(record, out, vmad_ctx)
        val_ty = record.val_type
        ##: Would love to have the dumped file name here...
        self._check_errors(val_ty, vmad_ctx, '')
        val_dt = record.val_data
        if val_ty == 0: # null
            pass
        elif val_ty == 1: # object ref
            val_dt.dump_ref(out)
        elif val_ty == 2: # string
            _dump_vmad_str16(out, val_dt)
        elif val_ty == 3: # sint32
            pack_int_signed(out, val_dt)
        elif val_ty == 4: # float
            pack_float(out, val_dt)
        elif val_ty == 5: # bool (stored as uint8)
            # 2x as fast as int(val_dt)
            pack_byte(out, 1 if val_dt else 0)
        elif val_ty in (6, 7): # 6 = variable, 7 = struct
            self._struct_loader.dump_frag(record.val_data, out, vmad_ctx)
        elif val_ty == 11: # object ref array
            _ObjectRef.dump_array(out, val_dt)
        elif val_ty == 12: # string array
            pack_int(out, len(val_dt))
            for val_str in val_dt:
                _dump_vmad_str16(out, val_str)
        elif val_ty == 13: # sint32 array
            array_len = len(val_dt)
            pack_int(out, array_len)
            out.write(struct_pack(f'={array_len}i', *val_dt))
        elif val_ty == 14: # float array
            array_len = len(val_dt)
            pack_int(out, array_len)
            out.write(struct_pack(f'={array_len}f', *val_dt))
        elif val_ty == 15: # bool array (stored as uint8 array)
            array_len = len(val_dt)
            pack_int(out, array_len)
            # Faster than [int(x) for x in val_dt]
            out.write(struct_pack(f'={array_len}B',
                *[1 if x else 0 for x in val_dt]))
        else: # val_ty == 17 - struct array
            pack_int(out, len(val_dt))
            dump_struct = self._struct_loader.dump_frag
            for val_struct in val_dt:
                dump_struct(val_struct, out, vmad_ctx)

    def map_fids(self, record, map_function, save_fids=False):
        val_ty = record.val_type
        if val_ty == 1: # object ref
            record.val_data.map_ref_fids(map_function, save_fids)
        elif val_ty in (6, 7): # 6 = variable, 7 = struct
            self._struct_loader.map_fids(record.val_data, map_function,
                save_fids)
        elif val_ty == 11: # object ref array
            for obj_ref in record.val_data:
                obj_ref.map_ref_fids(map_function, save_fids)
        elif val_ty == 17: # struct array
            map_struct = self._struct_loader.map_fids
            for val_struct in record.val_data:
                map_struct(val_struct, map_struct, save_fids)

    @property
    def used_slots(self):
        return super().used_slots + ['val_data']

# Properties ------------------------------------------------------------------
class _Property(_AValueComponent):
    """Represents a single script property."""
    _v4_processors = {
        'prop_name':   'str16',
        'val_type':    get_structs('B'),
        'prop_status': get_structs('B'),
    }
    _v3_processors = {
        'prop_name': 'str16',
        'val_type':  get_structs('B'),
    }

    def load_frag(self, record, ins, vmad_ctx: AVmadContext, *debug_strs):
        # Load the three regular attributes first - need to check version,
        # prop_status got added in v4
        if vmad_ctx.vmad_ver >= 4:
            self._processors = self._v4_processors
        else:
            self._processors = self._v3_processors
            record.prop_status = 1 # Defaults to 1 (edited)
        super().load_frag(record, ins, vmad_ctx, *debug_strs)

    def dump_frag(self, record, out, vmad_ctx: AVmadContext):
        # We only write out VMAD with version >=4
        self._processors = self._v4_processors
        super().dump_frag(record, out, vmad_ctx)

    @property
    def used_slots(self):
        # _processors may be empty, _v4_processors or _v3_processors right now
        return list(set(super().used_slots) | set(self._v4_processors))

# Structs ---------------------------------------------------------------------
class _Member(_AValueComponent):
    """Represents a single member of a struct."""
    _processors = {
        'member_name':   'str16',
        'val_type':      get_structs('B'),
        'member_status': get_structs('B'),
    }

class _Struct(_AVariableContainer):
    """Represents a single struct, a type of value used in properties and
    structs (yes, this definition is recursive). Every struct contains a number
    of members (see _Member above)."""
    _processors = {
        'member_count': get_structs('I'),
    }
    _children_attr = 'members'
    _counter_attr = 'member_count'

    def __init__(self):
        self._child_loader = _Member()

# Aliases ---------------------------------------------------------------------
class _Alias(_AVariableContainer):
    """Represents a single alias."""
    # Can't use any _processors when loading - see below
    _out_processors = {
        'alias_vmad_ver':   get_structs('h'),
        'alias_obj_format': get_structs('h'),
        'script_count':     get_structs('H'),
    }
    _children_attr = 'scripts'
    _counter_attr = 'script_count'

    def __init__(self):
        self._child_loader = _Script()

    def load_frag(self, record, ins, vmad_ctx: AVmadContext, *debug_strs):
        # Aliases start with an object ref, skip that for now and unpack the
        # three regular attributes. We need to do this, since one of the
        # attributes is alias_obj_format, which tells us how to unpack the
        # object ref at the start.
        ins_seek = ins.seek
        ins_seek(8, 1, *debug_strs)
        alias_ver, alias_obj = _unpack_2shorts_signed(ins, *debug_strs)
        record.alias_vmad_ver = alias_ver
        record.alias_obj_format = alias_obj
        record.script_count = unpack_short(ins)
        # Change our active VMAD version and object format to the ones we
        # read from this alias
        vmad_ctx = vmad_ctx.from_alias(alias_ver, alias_obj)
        # Now we can go back and unpack the object ref - note us passing the
        # (potentially) modified VMAD context
        ins_seek(-14, 1, *debug_strs)
        record.alias_ref_obj = _ObjectRef.from_file(ins, vmad_ctx, *debug_strs)
        # Skip back over the three attributes we read at the start
        ins_seek(6, 1, *debug_strs)
        # Finally, load the scripts attached to this alias - again, note the
        # (potentially) changed VMAD context
        self._processors = {}
        super().load_frag(record, ins, vmad_ctx, *debug_strs)

    def dump_frag(self, record, out, vmad_ctx: AVmadContext):
        # Dump out the object ref first and make sure we dump out VMAD versions
        # and object formats matching the main record, then we can fall back on
        # our parent's dump_frag implementation
        record.alias_ref_obj.dump_ref(out)
        record.alias_vmad_ver = vmad_ctx.vmad_ver
        record.alias_obj_format = vmad_ctx.obj_format
        record.scripts.sort(key=_vmad_key_script)
        self._processors = self._out_processors
        super().dump_frag(record, out, vmad_ctx)

    def map_fids(self, record, map_function, save_fids=False):
        record.alias_ref_obj.map_ref_fids(map_function, save_fids)
        super().map_fids(record, map_function, save_fids)

    @property
    def used_slots(self):
        return super().used_slots + ['alias_ref_obj'] + list(
            self._out_processors)

# API -------------------------------------------------------------------------
class AVmadContext:
    """Provides context info to the loading/dumping procedures below, so that
    they know what parts of the VMAd format the game and current record
    support. You have to inherit from this and set various game-specific
    fields, then use the resulting class as your MelVmad's
    _vmad_context_class."""
    __slots__ = ('vmad_ver', 'obj_format')

    # Override these and set them based on whether or not they are supported by
    # the current game --------------------------------------------------------
    # The maximum version supported by the game. Also the one we should use
    # when writing records
    max_vmad_ver: int

    def __init__(self, vmad_ver: int, obj_format: int):
        self.vmad_ver = vmad_ver
        self.obj_format = obj_format

    def from_alias(self, alias_vmad_ver: int, alias_obj_format: int):
        """Makes a copy of this VMAD context with the specified alias VMAD
        version and object format instead of the original record's version and
        object format."""
        self_copy = deepcopy(self)
        self_copy.vmad_ver = alias_vmad_ver
        self_copy.obj_format = alias_obj_format
        return self_copy

class AMelVmad(MelBase):
    """Virtual Machine Adapter. Forms the bridge between the Papyrus scripting
    system and the record definitions. A very complex subrecord that requires
    careful loading and dumping. Needs to be subclassed per game to set things
    like the game's maxinum VMAD version - see also AVmadContext.

    Note that this code is somewhat heavily optimized for performance, so
    expect lots of inlines and other non-standard or ugly code."""
    # A class holding necessary context when reading/writing records
    _vmad_context_class: type[AVmadContext]
    # The special handlers used by various record types
    _handler_map: dict[bytes, type | _AVmadComponent] = {
        b'INFO': _VmadHandlerINFO,
        b'PACK': _VmadHandlerPACK,
        b'PERK': _VmadHandlerPERK,
        b'QUST': _VmadHandlerQUST,
        b'SCEN': _VmadHandlerSCEN,
    }

    def __init__(self):
        super().__init__(b'VMAD', 'vmdata')
        self._script_loader = _Script()
        self._vmad_class = None

    def _get_special_handler(self, record_sig: bytes) -> _AVmadComponent:
        """Internal helper method for instantiating / retrieving a VMAD handler
        instance.

        :param record_sig: The signature of the record type in question."""
        special_handler = self._handler_map[record_sig]
        if isinstance(special_handler, type):
            # These initializations need to be delayed, since they require
            # MelVmad to be fully initialized first, so do this JIT
            self._handler_map[record_sig] = special_handler = special_handler()
        return special_handler

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        # Remember where this VMAD subrecord ends
        end_of_vmad = ins.tell() + size_
        if self._vmad_class is None:
            class _MelVmadImpl(MelObject):
                __slots__ = ('scripts', 'special_data')
            self._vmad_class = _MelVmadImpl # create only once
        record.vmdata = vmad = self._vmad_class()
        # Begin by unpacking the VMAD header and doing some error checking
        vmad_ver, obj_format = _unpack_2shorts_signed(ins, *debug_strs)
        vmad_max_ver = self._vmad_context_class.max_vmad_ver
        if vmad_ver > vmad_max_ver:
            raise ModError(ins.inName, f'VMAD version {vmad_ver} is too new '
                                       f'for this game (at most version '
                                       f'{vmad_max_ver} supported)')
        if obj_format not in (1, 2):
            raise ModError(ins.inName, f'Unrecognized VMAD object format '
                                       f'{obj_format}')
        vmad_ctx = self._vmad_context_class(vmad_ver, obj_format)
        # Next, load any scripts that may be present
        vmad.scripts = []
        new_script = self._script_loader.make_new
        load_script = self._script_loader.load_frag
        append_script = vmad.scripts.append
        for i in range(unpack_short(ins)):
            vm_script = new_script()
            load_script(vm_script, ins, vmad_ctx, *debug_strs)
            append_script(vm_script)
        # If the record type is one of the ones that need special handling and
        # we still have something to read, call the appropriate handler
        if record._rec_sig in self._handler_map and ins.tell() < end_of_vmad:
            special_handler = self._get_special_handler(record._rec_sig)
            vmad.special_data = special_handler.make_new()
            special_handler.load_frag(vmad.special_data, ins, vmad_ctx,
                *debug_strs)
        else:
            vmad.special_data = None

    def pack_subrecord_data(self, record):
        vmad = getattr(record, self.attr)
        if vmad is None: return None
        out = BytesIO()
        # Start by dumping out the VMAD header - we read all VMAD versions and
        # object formats, but only dump out VMAD v5 and object format v2
        vmad_ctx = self._vmad_context_class(
            self._vmad_context_class.max_vmad_ver, 2)
        _pack_2shorts_signed(out, vmad_ctx.vmad_ver, vmad_ctx.obj_format)
        # Next, dump out all attached scripts
        vm_scripts = vmad.scripts
        vm_scripts.sort(key=_vmad_key_script)
        pack_short(out, len(vm_scripts))
        dump_script = self._script_loader.dump_frag
        for vmad_script in vm_scripts:
            dump_script(vmad_script, out, vmad_ctx)
        # If the subrecord has special data attached, ask the appropriate
        # handler to dump that out
        if vmad.special_data and record._rec_sig in self._handler_map:
            special_handler = self._get_special_handler(record._rec_sig)
            special_handler.dump_frag(vmad.special_data, out, vmad_ctx)
        return out.getvalue()

    def hasFids(self, formElements):
        # Unconditionally add ourselves - see comment above
        # _AVmadComponent.map_fids for more information
        formElements.add(self)

    def mapFids(self, record, function, save_fids=False):
        vmad = getattr(record, self.attr)
        if vmad is None: return
        map_script = self._script_loader.map_fids
        for vmad_script in vmad.scripts:
            map_script(vmad_script, function, save_fids)
        if vmad.special_data and record._rec_sig in self._handler_map:
            self._get_special_handler(record._rec_sig).map_fids(
                vmad.special_data, function, save_fids)
