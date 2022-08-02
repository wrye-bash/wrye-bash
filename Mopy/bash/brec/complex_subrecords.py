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
"""Houses highly complex subrecords like NVNM and VMAD that require completely
custom code to handle."""
from __future__ import annotations

from collections import defaultdict
from io import BytesIO
from itertools import chain
from typing import Type

from .advanced_elements import MelUnion, PartialLoadDecider, AttrValDecider, \
    MelTruncatedStruct, SignatureDecider, MelCounter
from .basic_elements import MelBase, MelStruct, MelGroups, MelReadOnly, \
    MelString, MelSequential, MelUInt32, MelFid, MelGroup, MelObject, \
    MelOptStruct, MelBaseR
from .common_subrecords import MelFull
from .utils_constants import get_structs, FID, null1, ZERO_FID
from ..bolt import pack_int, pack_byte, attrgetter_cache, Flags, struct_pack, \
    struct_unpack
from ..exception import AbstractError, ModError

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
    # This is technically a lot more complex (the highest three bits also
    # encode the comparison operator), but we only care about use_global, so we
    # can treat the rest as unknown flags and just carry them forward
    _ctda_type_flags = Flags.from_names('do_or', 'use_aliases', 'use_global',
        'use_packa_data', 'swap_subject_and_target')

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
        from .. import bush
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
        prefix_elements = [(self._ctda_type_flags, 'operFlag'), 'unused1',
                           'compValue', 'ifunc', 'unused2']
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
                ''.join(prefix_fmt + fmt_list + ([f] if f else [])) for f in
                old_suffix_fmts}
            return MelTruncatedStruct(*shared_params,
                                      old_versions=full_old_versions)
        return MelStruct(*shared_params)

    @staticmethod
    def _build_params(func_data, prefix_elements, suffix_elements):
        """Builds a list of struct elements to pass to MelTruncatedStruct."""
        # First, build up a list of the parameter elemnts to use
        func_elements = [
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
        if record.operFlag.use_global:
            new_comp_val = function(record.compValue)
            if save_fids: record.compValue = new_comp_val

    def dumpData(self, record, out):
        # See _build_struct comments above for an explanation of this
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
        from .. import bush
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
# OBME - Oblivion Magic Extender
#------------------------------------------------------------------------------
# Helpers ---------------------------------------------------------------------
class _MelObmeScitGroup(MelGroup):
    """Fun HACK for the whole family. We need to carry efix_param_info into
    this group, since '../' syntax is not yet supported (see MrePerk in Skyrim
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
class MelObme(MelOptStruct):
    """Oblivion Magic Extender subrecord. Prefixed every attribute with obme_
    both for easy grouping in debugger views and to differentiate them from
    vanilla attrs."""
    def __init__(self, struct_sig=b'OBME', extra_format=None,
                 extra_contents=None, reserved_byte_count=28):
        """Initializes a MelObme instance. Supports customization for the
        variations that exist for effects subrecords and MGEF records."""
        if extra_format is None:
            extra_format = []
        if extra_contents is None:
            extra_contents = []
        # Always begins with record version and OBME version - None here is on
        # purpose, to differentiate from 0 which is almost always the record
        # version in plugins using OBME
        struct_contents = [('obme_record_version', None),
                           'obme_version_beta', 'obme_version_minor',
                           'obme_version_major']
        # Then comes any extra info placed in the middle
        struct_contents += extra_contents
        # Always ends with a statically sized reserved byte array
        struct_contents += [('obme_unused', null1 * reserved_byte_count)]
        str_fmts = ['4B', *extra_format, f'{reserved_byte_count}s']
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
    se_flags = Flags.from_names('hostile')

    def __init__(self):
        # Vanilla Elements ----------------------------------------------------
        self._vanilla_elements = [
            MelGroups('effects',
                # REHE is Restore target's Health - EFID.effect_sig
                # must be the same as EFIT.effect_sig
                MelStruct(b'EFID', ['4s'], ('effect_sig', b'REHE')),
                MelStruct(b'EFIT', ['4s', '4I', 'i'], ('effect_sig', b'REHE'),
                    'magnitude', 'area', 'duration', 'recipient',
                    'actorValue'),
                MelGroup('scriptEffect',
                    _MelEffectsScit(b'SCIT', ['2I', '4s', 'B', '3s'],
                        (FID, 'script_fid'), 'school', 'visual',
                        (self.se_flags, 'flags'), 'unused1',
                        old_versions={'2I4s', 'I'}),
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
                MelStruct(b'EFID', ['4s'], ('effect_sig', b'REHE')),
                MelUnion({
                    0: MelStruct(b'EFIT', ['4s', '4I', '4s'], 'unused_name',
                        'magnitude', 'area', 'duration', 'recipient',
                        'efit_param'),
                    ##: Test this! Does this actually work?
                    (1, 3): MelStruct(b'EFIT', ['4s', '5I'], 'unused_name',
                        'magnitude', 'area', 'duration', 'recipient',
                        (FID, 'efit_param')),
                    ##: This case needs looking at, OBME docs say this about
                    # efit_param in case 2: 'If >= 0x80000000 lowest byte is
                    # Mod Index, otherwise no resolution'
                    2: MelStruct(b'EFIT', ['4s', '4I', '4s'], 'unused_name',
                        'magnitude', 'area', 'duration', 'recipient',
                        ('efit_param', b'REHE')),
                }, decider=AttrValDecider('efit_param_info')),
                _MelObmeScitGroup('scriptEffect',
                    ##: Test! xEdit has all this in EFIX, but it also
                    #  hard-crashes when I try to add EFIX subrecords... this
                    #  is adapted from OBME's official docs, but those could be
                    #  wrong. Also, same notes as above for case 2 and 3.
                    MelUnion({
                        0: MelStruct(b'SCIT', ['4s', 'I', '4s', 'B', '3s'],
                            'efix_param', 'school', 'visual',
                            se_fl := (self.se_flags, 'flags'), 'unused1'),
                        1: MelStruct(b'SCIT', ['2I', '4s', 'B', '3s'],
                            (FID, 'efix_param'), 'school', 'visual', se_fl,
                            'unused1'),
                        2: MelStruct(b'SCIT', ['4s', 'I', '4s', 'B', '3s'],
                            ('efix_param', b'REHE'), 'school', 'visual', se_fl,
                            'unused1'),
                        3: MelStruct(b'SCIT', ['2I', '4s', 'B', '3s'],
                            (FID, 'efit_param'), 'school', 'visual', se_fl,
                            'unused1'),
                    }, decider=AttrValDecider('efix_param_info')),
                    MelFull(),
                ),
                MelString(b'EFII', 'obme_icon'),
                ##: Again, FID here needs testing
                MelOptStruct(b'EFIX', ['2I', 'f', 'i', '16s'],
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
def _mk_unpacker(struct_fmt, only_one=False):
    """Helper method that creates a method for unpacking values from an input
    stream. Accepts debug strings as well.

    :param only_one: If set, return only the first element of the unpacked
        tuple."""
    s_unpack, _s_pack, s_size = get_structs(f'={struct_fmt}')
    if only_one:
        def _unpacker(ins, *debug_strs):
            return ins.unpack(s_unpack, s_size, *debug_strs)[0]
    else:
        def _unpacker(ins, *debug_strs):
            return ins.unpack(s_unpack, s_size, *debug_strs)
    return _unpacker

_nvnm_unpack_byte = _mk_unpacker('B', only_one=True)
_nvnm_unpack_short = _mk_unpacker('H', only_one=True)
_nvnm_unpack_int = _mk_unpacker('I', only_one=True)
_nvnm_unpack_float = _mk_unpacker('f', only_one=True)
_nvnm_unpack_2shorts = _mk_unpacker('2h')
_nvnm_unpack_triangle = _mk_unpacker('6h')
_nvnm_unpack_tri_extra = _mk_unpacker('fB')
_nvnm_unpack_edge_link = _mk_unpacker('2Ih')
_nvnm_unpack_door_triangle = _mk_unpacker('H2I')

def _mk_packer(struct_fmt):
    """Helper method that creates a method for packing values to an output
    stream."""
    _s_unpack, s_pack, _s_size = get_structs(f'={struct_fmt}')
    def _packer(out, *vals_to_pack):
        return out.write(s_pack(*vals_to_pack))
    return _packer

_nvnm_pack_2shorts = _mk_packer('2h')
_nvnm_pack_triangle = _mk_packer('6h')
_nvnm_pack_tri_extra = _mk_packer('fB')
_nvnm_pack_edge_link = _mk_packer('2Ih')
_nvnm_pack_door_triangle = _mk_packer('H2I')

# API, pt1 --------------------------------------------------------------------
class ANvnmContext:
    """Provides context info to the loading/dumping procedures below, so that
    they know what parts of the NVNM format the game and current record
    support. You have to override this and set """
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
        raise AbstractError('load_comp not implemented')

    def dump_comp(self, out, nvnm_ctx: ANvnmContext):
        """Dumps this component to the specified output stream."""
        raise AbstractError('dump_comp not implemented')

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
        for _x in range(_nvnm_unpack_int(ins, *debug_strs)):
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
        self.crc_val = _nvnm_unpack_int(ins, *debug_strs)

    def dump_comp(self, out, nvnm_ctx: ANvnmContext):
        pack_int(out, self.crc_val)

class _NvnmPathingCell(_AMelNvnmComponent):
    """The navmesh geometry's pathing cell. Holds basic context information
    about where this navmesh geometry is located."""
    __slots__ = ('parent_worldspace', 'parent_cell', 'cell_coord_x',
                 'cell_coord_y')

    def load_comp(self, ins, nvnm_ctx: ANvnmContext, *debug_strs):
        self.parent_worldspace = FID(_nvnm_unpack_int(ins, *debug_strs))
        if self.parent_worldspace != ZERO_FID:
            self.parent_cell = None
            # The Y coordinate comes first!
            self.cell_coord_y, self.cell_coord_x = _nvnm_unpack_2shorts(
                ins, *debug_strs)
        else:
            self.parent_cell = FID(_nvnm_unpack_int(ins, *debug_strs))
            self.cell_coord_y = None
            self.cell_coord_x = None

    def dump_comp(self, out, nvnm_ctx: ANvnmContext):
        pack_int(out, self.parent_worldspace.dump())
        if self.parent_worldspace != ZERO_FID:
            _nvnm_pack_2shorts(out, self.cell_coord_y, self.cell_coord_x)
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
        num_vertices = _nvnm_unpack_int(ins, *debug_strs)
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
            self.tri_flags, self.tri_cover_flags = _nvnm_unpack_2shorts(
                ins, *debug_strs)

        def dump_comp(self, out, nvnm_ctx: ANvnmContext):
            _nvnm_pack_triangle(out, self.vertex_0, self.vertex_1,
                self.vertex_2, self.edge_0_1, self.edge_1_2, self.edge_2_0)
            if nvnm_ctx.form_ver > 57:
                _nvnm_pack_tri_extra(out, self.tri_height, self.tri_unknown)
            _nvnm_pack_2shorts(self.tri_flags, self.tri_cover_flags)

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
                self.edge_index = _nvnm_unpack_byte(ins, *debug_strs)
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
            num_covers = _nvnm_unpack_int(ins, *debug_strs)
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
        num_cover_tris = _nvnm_unpack_int(ins, *debug_strs)
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
            num_waypoints = _nvnm_unpack_int(ins, *debug_strs)
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
    custom code. Needs to be overriden per game to set things like the game's
    maxinum NVNM version - see also ANvnmContext."""
    # A class holding necessary context when reading/writing records
    _nvnm_context_class: Type[ANvnmContext]

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
        nvnm_ver = _nvnm_unpack_int(ins, *debug_strs)
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
