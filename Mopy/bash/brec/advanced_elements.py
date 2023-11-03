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
"""Houses more complex building blocks for creating record definitions. The
split from basic_elements.py is somewhat arbitrary, but generally elements in
this file involve conditional loading and are much less commonly used. Relies
on some of the elements defined in basic_elements, e.g. MelBase, MelObject and
MelStruct."""

__author__ = 'Infernio'

import copy
from collections.abc import Callable
from itertools import chain
from typing import Any, BinaryIO

from .basic_elements import MelBase, MelNull, MelNum, MelObject, \
    MelSequential, MelStruct, MelGroups
from .. import bush
from ..bolt import attrgetter_cache, deprint, structs_cache, \
    flatten_multikey_dict
from ..exception import ArgumentError, ModSizeError

#------------------------------------------------------------------------------
class _MelDistributor(MelNull):
    """Implements a distributor that can handle duplicate record signatures.
    See the wiki page '[dev] Plugin Format: Distributors' for a detailed
    overview of this class and the semi-DSL it implements."""
    def __init__(self, distributor_config: dict):
        # Maps attribute name to loader
        self._attr_to_loader: dict[str, MelBase] = {}
        # Maps subrecord signature to loader
        self._sig_to_loader: dict[bytes, MelBase] = {}
        # All signatures that this distributor targets
        self._target_sigs: set[bytes] = set()
        self._distributor_config = distributor_config
        # Validate that the distributor config we were given has valid syntax
        # and resolve any shortcuts (e.g. the A|B syntax)
        self._pre_process()

    def _raise_syntax_error(self, error_msg):
        """Small helper for raising distributor config syntax errors."""
        raise SyntaxError(f'Invalid distributor syntax: {error_msg}')

    def _pre_process(self):
        """Ensures that the distributor config defined above has correct syntax
        and resolves shortcuts (e.g. A|B syntax)."""
        if not isinstance(self._distributor_config, dict):
            self._raise_syntax_error(
                f'distributor_config must be a dict (actual type: '
                f'{type(self._distributor_config)})')
        scopes_to_iterate = [self._distributor_config]
        while scopes_to_iterate:
            scope = scopes_to_iterate.pop()
            for signature_str in list(scope):
                if not isinstance(signature_str, bytes):
                    self._raise_syntax_error(
                        f'All keys must be signature bytestrings (offending '
                        f'key: {signature_str!r})')
                # Resolve 'A|B' syntax
                split_sigs = signature_str.split(b'|')
                resolved_entry = scope[signature_str]
                if not resolved_entry:
                    self._raise_syntax_error(f'Mapped values may not be empty '
                        f'(offending value: {resolved_entry!r})')
                # Delete the 'A|B' entry, not needed anymore
                del scope[signature_str]
                for signature in split_sigs:
                    if len(signature) != 4:
                        self._raise_syntax_error(
                            f'Signature strings must have length 4 (offending '
                            f'string: {signature})')
                    if signature in scope:
                        self._raise_syntax_error(
                            f'Duplicate signature string (offending string: '
                            f'{signature})')
                    # For each option in A|B|..|Z, make a new entry
                    scope[signature] = resolved_entry
                re_type = type(resolved_entry)
                if re_type == dict:
                    # If this is a simple scope, recurse into it
                    scopes_to_iterate.append(resolved_entry)
                elif re_type == tuple:
                    # If this is a mixed scope, validate its syntax and recurse
                    # into it
                    if (len(resolved_entry) != 2
                            or not isinstance(resolved_entry[0], str)
                            or not isinstance(resolved_entry[1], dict)):
                        self._raise_syntax_error(
                            f'Mixed scopes must always have two elements - an '
                            f'attribute string and a dict (offending mixed '
                            f'scope: {resolved_entry!r})')
                    scopes_to_iterate.append(resolved_entry[1])
                elif re_type == list:
                    # If this is a sequence, ensure that each entry has valid
                    # syntax
                    for seq_entry in resolved_entry:
                        if isinstance(seq_entry, tuple):
                            if (len(seq_entry) != 2
                                    or not isinstance(seq_entry[0], bytes)
                                    or not isinstance(seq_entry[1], str)):
                                self._raise_syntax_error(
                                    f'Sequence tuples must always have two '
                                    f'elements, a bytestring and a string '
                                    f'(offending sequential entry: '
                                    f'{seq_entry!r})')
                        elif not isinstance(seq_entry, bytes):
                            self._raise_syntax_error(
                                f'Sequence entries must either be tuples or '
                                f'bytestrings (actual type: '
                                f'{type(seq_entry)})')
                elif re_type != str:
                    # This isn't a simple scope, mixed scope, sequence or
                    # target, so it's something invalid
                    self._raise_syntax_error(
                        f'Only simple scopes, mixed scopes, sequences and '
                        f'targets may occur as values (offending type: '
                        f'{re_type})')

    def getLoaders(self, loaders):
        # We need a copy of the unmodified signature-to-loader dictionary for
        # looking up signatures at runtime
        self._sig_to_loader = loaders.copy()
        # Recursively descend into the distributor config to find all relevant
        # subrecord signatures, then register ourselves
        self._target_sigs = set()
        scopes_to_iterate = [self._distributor_config]
        while scopes_to_iterate:
            scope = scopes_to_iterate.pop()
            # The keys are always subrecord signatures
            for signature_str in list(scope):
                # We will definitely need this signature
                self._target_sigs.add(signature_str)
                resolved_entry = scope[signature_str]
                re_type = type(resolved_entry)
                if re_type == dict:
                    # If this is a simple scope, recurse into it
                    scopes_to_iterate.append(resolved_entry)
                elif re_type == tuple:
                    # If this is a mixed scope, recurse into it
                    scopes_to_iterate.append(resolved_entry[1])
                elif re_type == list:
                    # If this is a sequence, record the signatures of each
                    # entry (bytes or tuple[bytes, str])
                    self._target_sigs.update([t[0] if isinstance(t, tuple)
                                              else t for t in resolved_entry])
        for subrecord_type in self._target_sigs:
            loaders[subrecord_type] = self

    def getSlotsUsed(self):
        # _loader_state is the current state of our descent into the
        # distributor config, this is a list of strings marking the
        # subrecords we've visited.
        # _seq_index is only used when processing a sequential and marks
        # the index where we left off in the last load_mel
        return '_loader_state', '_seq_index'

    def setDefault(self, record):
        record._loader_state = []
        record._seq_index = None

    def set_mel_set(self, mel_set):
        """Sets parent MelSet. We use this to collect the attribute names
        from each loader."""
        self.mel_set = mel_set
        for element in mel_set.elements:
            # Underscore means internal usage only - e.g. distributor state
            el_attrs = [s for s in element.getSlotsUsed()
                        if not s.startswith('_')]
            for el_attr in el_attrs:
                self._attr_to_loader[el_attr] = element

    def _accepts_signature(self, dist_specifier, signature):
        """Internal helper method that checks if the specified signature is
        handled by the specified distribution specifier."""
        to_check = (dist_specifier[0] if isinstance(dist_specifier, tuple)
                    else dist_specifier)
        return to_check == signature

    def _distribute_load(self, dist_specifier, record, ins, size_,
                         *debug_strs):
        """Internal helper method that distributes a load_mel call to the
        element loader pointed at by the specified distribution specifier."""
        if isinstance(dist_specifier, tuple):
            signature = dist_specifier[0]
            target_loader = self._attr_to_loader[dist_specifier[1]]
        else:
            signature = dist_specifier
            target_loader = self._sig_to_loader[dist_specifier]
        target_loader.load_mel(record, ins, signature, size_, *debug_strs)

    def _apply_mapping(self, mapped_el, record, ins, signature, size_,
                       *debug_strs):
        """Internal helper method that applies a single mapping element
        (mapped_el). This implements the correct loader state manipulations for
        that element and also distributes the load_mel call to the correct
        loader, as specified by the mapping element and the current
        signature."""
        el_type = type(mapped_el)
        if el_type == dict:
            # Simple Scopes ---------------------------------------------------
            # A simple scope - add the signature to the load state and
            # distribute the load by signature. That way we will descend
            # into this scope on the next load_mel call.
            record._loader_state.append(signature)
            self._distribute_load(signature, record, ins, size_, *debug_strs)
        elif el_type == tuple:
            # Mixed Scopes ----------------------------------------------------
            # A mixed scope - implement it like a simple scope, but
            # distribute the load by attribute name.
            record._loader_state.append(signature)
            self._distribute_load((signature, mapped_el[0]), record, ins,
                                  size_, *debug_strs)
        elif el_type == list:
            # Sequences -------------------------------------------------------
            # A sequence - add the signature to the load state, set the
            # sequence index to 1, and distribute the load to the element
            # specified by the first sequence entry.
            record._loader_state.append(signature)
            record._seq_index = 1 # we'll load the first element right now
            self._distribute_load(mapped_el[0], record, ins, size_,
                                  *debug_strs)
        else: # el_type == str, verified in _pre_process
            # Targets ---------------------------------------------------------
            # A target - don't add the signature to the load state and
            # distribute the load by attribute name.
            self._distribute_load((signature, mapped_el), record, ins,
                                  size_, *debug_strs)

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        loader_state = record._loader_state
        seq_index = record._seq_index
        # First, descend as far as possible into the scopes. However, also
        # build up a tracker we can use to backtrack later on.
        descent_tracker = []
        current_scope = self._distributor_config
        # Scopes --------------------------------------------------------------
        for signature in loader_state:
            current_scope = current_scope[signature]
            if isinstance(current_scope, tuple): # handle mixed scopes
                current_scope = current_scope[1]
            descent_tracker.append((signature, current_scope))
        # Sequences -----------------------------------------------------------
        # Then, check if we're in the middle of a sequence. If so,
        # current_scope will actually be a list, namely the sequence we're
        # iterating over.
        if seq_index is not None:
            if seq_index < len(current_scope):
                dist_specifier = current_scope[seq_index]
                if self._accepts_signature(dist_specifier, sub_type):
                    # We're good to go, call the next loader in the sequence
                    # and increment the sequence index
                    self._distribute_load(dist_specifier, record, ins, size_,
                                          *debug_strs)
                    record._seq_index += 1
                    return
            # The sequence is either over or we prematurely hit a non-matching
            # type - either way, stop distributing loads to it.
            record._seq_index = None
        # Next, check if the current scope depth contains a specifier that
        # accepts our signature. If so, use that one to track and distribute.
        # If not, we have to backtrack.
        while descent_tracker:
            prev_sig, prev_scope = descent_tracker.pop()
            # For each previous scope, check if it contains a specifier that
            # accepts our signature and use it if so.
            if sub_type in prev_scope:
                # Calculate the new loader state - contains signatures for all
                # remaining scopes we haven't backtracked through yet plus the
                # one we just backtrackd into
                record._loader_state = [*(x[0] for x in descent_tracker),
                                        prev_sig]
                self._apply_mapping(prev_scope[sub_type], record, ins,
                                    sub_type, size_, *debug_strs)
                return
        # We didn't find anything during backtracking, so it must be in the top
        # scope. Wipe the loader state first and then apply the mapping.
        record._loader_state = []
        self._apply_mapping(self._distributor_config[sub_type], record, ins,
                            sub_type, size_, *debug_strs)

    @property
    def signatures(self):
        return self._target_sigs

#------------------------------------------------------------------------------
class MelArray(MelBase):
    """Represents a single subrecord that consists of multiple fixed-size
    components. Note that only elements that properly implement static_size
    and fulfill len(self.signatures) == 1, i.e. ones that have a static size
    and resolve to only a single signature, can be used."""
    def __init__(self, array_attr: str, element: MelBase,
            prelude: MelBase | None = None):
        """Creates a new MelArray with the specified attribute and element.

        :param array_attr: The attribute name to give the entire array.
        :param element: The element that each entry in this array will be
            loaded and dumped by.
        :param prelude: An optional element that will be loaded and dumped once
            before the repeating element."""
        try:
            self._element_size = element.static_size
        except NotImplementedError:
            raise SyntaxError(u'MelArray may only be used with elements that '
                              u'have a static size')
        if len(element.signatures) != 1:
            raise SyntaxError(u'MelArray may only be used with elements that '
                              u'resolve to exactly one signature')
        # Use this instead of element.mel_sig to support e.g. unions
        element_sig = next(iter(element.signatures))
        super(MelArray, self).__init__(element_sig, array_attr)
        self._element = element
        self._element_has_fids = False
        # Underscore means internal usage only - e.g. distributor state
        self.array_element_attrs = [s for s in element.getSlotsUsed() if
                                    not s.startswith(u'_')]
        # Validate that the prelude is valid if it's present (i.e. it must have
        # only one signature and it must match the element's signature)
        if prelude:
            prelude_sigs = prelude.signatures
            if len(prelude_sigs) != 1:
                raise SyntaxError(u'MelArray preludes must have exactly one '
                                  u'signature')
            if next(iter(prelude_sigs)) != element_sig:
                raise SyntaxError(u'MelArray preludes must have the same '
                                  u'signature as the main element')
        self._prelude = prelude
        self._prelude_has_fids = False
        try:
            self._prelude_size = prelude.static_size if prelude else 0
        except NotImplementedError:
            raise SyntaxError(u'MelArray preludes must have a static size')

    def getSlotsUsed(self):
        slots_ret = self._prelude.getSlotsUsed() if self._prelude else ()
        return super(MelArray, self).getSlotsUsed() + slots_ret

    def hasFids(self, formElements):
        temp_elements_prelude = set()
        temp_elements_element = set()
        if self._prelude:
            self._prelude.hasFids(temp_elements_prelude)
            self._prelude_has_fids = bool(temp_elements_prelude)
        self._element.hasFids(temp_elements_element)
        self._element_has_fids = bool(temp_elements_element)
        if temp_elements_prelude or temp_elements_element:
            formElements.add(self)

    def setDefault(self, record):
        if self._prelude:
            self._prelude.setDefault(record)
        setattr(record, self.attr, [])

    def mapFids(self, record, function, save_fids=False):
        if self._prelude_has_fids:
            self._prelude.mapFids(record, function, save_fids)
        self._map_array_fids(record, function, save_fids)

    def _map_array_fids(self, record, function, save_fids):
        if self._element_has_fids:
            array_val = getattr(record, self.attr)
            if array_val:
                map_entry = self._element.mapFids
                for arr_entry in array_val:
                    map_entry(arr_entry, function, save_fids)

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        if self._prelude:
            self._prelude.load_mel(record, ins, sub_type, self._prelude_size,
                                   *debug_strs)
            size_ -= self._prelude_size
        self._load_array(record, ins, sub_type, size_, *debug_strs)

    def _load_array(self, record, ins, sub_type, size_, *debug_strs):
        append_entry = getattr(record, self.attr).append
        entry_slots = self.array_element_attrs
        entry_size = self._element_size
        load_entry = self._element.load_mel
        for x in range(size_ // entry_size):
            arr_entry = MelObject()
            append_entry(arr_entry)
            arr_entry.__slots__ = entry_slots
            load_entry(arr_entry, ins, sub_type, entry_size, *debug_strs)

    def pack_subrecord_data(self, record):
        """Collects the actual data that will be dumped out."""
        array_val = getattr(record, self.attr)
        if not array_val: return None # don't dump out empty arrays
        if self._prelude:
            sub_data = self._prelude.pack_subrecord_data(record)
            if sub_data is None:
                deprint(f'{record}: prelude={self._prelude} '
                        f'for attr={self.attr} returned None packed data')
                sub_data = b''
        else:
            sub_data = b''
        sub_data += self._pack_array_data(array_val)
        return sub_data

    def _pack_array_data(self, array_val):
        return b''.join(
            [self._element.pack_subrecord_data(arr_entry) for arr_entry in
             array_val])

#------------------------------------------------------------------------------
class MelSimpleArray(MelArray):
    """A MelArray of simple elements (currently MelNum) - override loading and
    dumping of the array to avoid creating MelObjects."""
    _element: MelNum

    def __init__(self, array_attr, element: MelNum, prelude=None):
        if not isinstance(element, MelNum):
            raise SyntaxError(f'MelSimpleArray only accepts MelNum, passed: '
                              f'{element!r}')
        super().__init__(array_attr, element, prelude)

    def _load_array(self, record, ins, sub_type, size_, *debug_strs):
        entry_size = self._element_size
        load_element = self._element.load_bytes
        getattr(record, self.attr).extend([
            load_element(ins, entry_size, *debug_strs) for _x in
            range(size_ // entry_size)])

    def _map_array_fids(self, record, function, save_fids):
        if self._element_has_fids:
            array_val = getattr(record, self.attr)
            mapped = [function(arr_entry) for arr_entry in array_val]
            if save_fids:
                setattr(record, self.attr, mapped)

    def _pack_array_data(self, array_val):
        return b''.join(map(self._element.packer, array_val))

#------------------------------------------------------------------------------
class MelTruncatedStruct(MelStruct):
    """Works like a MelStruct, but automatically upgrades certain older,
    truncated struct formats."""
    def __init__(self, sub_sig, sub_fmt, *elements, old_versions,
                 is_required=None):
        """Creates a new MelTruncatedStruct with the specified parameters.

        :param sub_sig: The subrecord signature of this struct.
        :param sub_fmt: The format of this struct.
        :param elements: The element syntax of this struct.
        :param old_versions: The older formats that are supported by this
            struct.
        :param is_required: Whether this struct should be dumped even if not
            loaded."""
        if not isinstance(old_versions, set):
            raise SyntaxError('MelTruncatedStruct: old_versions must be a set')
        super().__init__(sub_sig, sub_fmt, *elements, is_required=is_required)
        self._all_unpackers = {
            structs_cache[alt_fmt].size: structs_cache[alt_fmt].unpack for
            alt_fmt in old_versions}
        self._all_unpackers[self._static_size] = self._unpacker

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        # Try retrieving the format - if not possible, wrap the error to make
        # it more informative
        try:
            target_unpacker = self._all_unpackers[size_]
        except KeyError:
            raise ModSizeError(ins.inName, debug_strs,
                               tuple(self._all_unpackers), size_)
        # Actually unpack the struct and pad it with defaults if it's an older,
        # truncated version
        unpacked_val = ins.unpack(target_unpacker, size_, *debug_strs)
        unpacked_val = self._pre_process_unpacked(unpacked_val)
        # Set the attributes according to the values we just unpacked
        for att, val in zip(self.attrs, unpacked_val):
            setattr(record, att, val)

    def _pre_process_unpacked(self, unpacked_val):
        """You may override this if you need to change the unpacked value in
        any way before it is used to assign attributes, however make sure to
        call the parent method which applies actions to the unpacked values.
        Don't apply the actions in overrides."""
        return (*(val if act is None else act(val) for val, act in
                  zip(unpacked_val, self.actions)),
        # append default values (actions are already applied to self.defaults!)
                *self.defaults[len(unpacked_val):])

    @property
    def static_size(self):
        # We behave just like a regular struct if we don't have any old formats
        if len(self._all_unpackers) != 1:
            raise NotImplementedError
        return super(MelTruncatedStruct, self).static_size

#------------------------------------------------------------------------------
class MelLists(MelStruct):
    """Convenience subclass to collect unpacked attributes to lists.
    'actions' is discarded"""
    # map attribute names to slices/indexes of the tuple of unpacked elements
    _attr_indexes: dict[str, slice | int] = {}

    def __init__(self, mel_sig, struct_formats, *elements):
        if len(struct_formats) != len(elements):
            raise SyntaxError(f'MelLists: struct_formats ({struct_formats}) '
                              f'do not match elements ({elements})')
        super(MelLists, self).__init__(mel_sig, struct_formats, *elements)

    @staticmethod
    def _expand_formats(elements, expanded_fmts):
        # This is fine because we enforce the precondition
        # len(struct_formats) == len(elements) in MelLists.__init__
        return [int(f[:-1] or 1) if f[-1] == 's' else 0 for f in expanded_fmts]

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        unpacked = list(ins.unpack(self._unpacker, size_, *debug_strs))
        for attr, _slice in self.__class__._attr_indexes.items():
            setattr(record, attr, unpacked[_slice])

    def pack_subrecord_data(self, record):
        attr_vals = [getattr(record, a) for a in self.__class__._attr_indexes]
        if all(x is None for x in attr_vals):
            # This is entirely None, skip the dump completely
            return None
        ##: What about when this is *partially* None? Skip? Use defaults?
        return self._packer(*chain(
            *(j if isinstance(j, list) else [j] for j in attr_vals)))

#------------------------------------------------------------------------------
# Unions and Deciders
class ADecider(object):
    """A decider returns one of several possible values when called, based on
    parameters such as the record instance, sub type, or record size. See
    MelUnion's docstring for more information."""
    # Set this to True if your decider can handle a decide_dump call -
    # otherwise, the result of decide_load will be stored and reused during
    # dumpData, if that is possible. If not (e.g. for a newly created record),
    # then the union will pick some element in its dict - no guarantees made.
    can_decide_at_dump = False

    def decide_load(self, record, ins, sub_type, rec_size):
        """Called during load_mel.

        :param record: The record instance we're assigning attributes to.
        :param ins: The ModReader instance used to read the record.
        :type ins: ModReader
        :param sub_type: The four-character subrecord signature.
        :type sub_type: bytes
        :param rec_size: The total size of the subrecord.
        :type rec_size: int
        :return: Any value this decider deems fitting for the parameters it is
            given."""
        raise NotImplementedError

    def decide_dump(self, record):
        """Called during dumpData.

        :param record: The record instance we're reading attributes from.
        :return: Any value this decider deems fitting for the parameters it is
            given."""
        if self.can_decide_at_dump:
            raise NotImplementedError

class ACommonDecider(ADecider):
    """Abstract class for deciders that can decide at both load and dump-time,
    based only on the record. Provides a single method, _decide_common, that
    the subclass has to implement."""
    can_decide_at_dump = True

    def decide_load(self, record, ins, sub_type, rec_size):
        return self._decide_common(record)

    def decide_dump(self, record):
        return self._decide_common(record)

    def _decide_common(self, record):
        """Performs the actual decisions for both loading and dumping."""
        raise NotImplementedError

class AttrValDecider(ACommonDecider):
    """Decider that returns an attribute value (may optionally apply a function
    to it first)."""
    # Internal sentinel value used for the assign_missing argument
    _assign_missing_sentinel = object()

    def __init__(self, target_attr, transformer=None,
                 assign_missing=_assign_missing_sentinel):
        """Creates a new AttrValDecider with the specified attribute and
        optional arguments.

        :param target_attr: The name of the attribute to return the value
            for.
        :type target_attr: str
        :param transformer: A function that takes a single argument, the value
            read from target_attr, and returns some other value. Can be used to
            e.g. return only the first character of an eid.
        :param assign_missing: Normally, an AttributeError is raised if the
            record does not have target_attr. If this is anything other than
            the sentinel value, an error will not be raised and this will be
            returned instead."""
        self.target_attr = target_attr
        self.transformer = transformer
        self.assign_missing = assign_missing

    def _decide_common(self, record):
        if self.assign_missing is not self._assign_missing_sentinel:
            # We have a valid assign_missing, default to it
            ret_val = getattr(record, self.target_attr, self.assign_missing)
        else:
            # Raises an AttributeError if target_attr is missing
            ret_val = getattr(record, self.target_attr)
        if self.transformer is not None:
            ret_val = self.transformer(ret_val)
        return ret_val

class FidNotNullDecider(ACommonDecider):
    """Decider that returns True if the FormID attribute with the specified
    name is not NULL."""
    def __init__(self, target_attr):
        """Creates a new FidNotNullDecider with the specified attribute.

        :param target_attr: The name of the attribute to check.
        :type target_attr: str"""
        self._target_attr = target_attr

    def _decide_common(self, record):
        try:
            return not getattr(record, self._target_attr).is_null()
        except AttributeError: # 'NoneType' object has no attribute 'is_null'
            return False # a MelUnion attribute that was set to None default

class FlagDecider(ACommonDecider):
    """Decider that checks if certain flags are set."""
    def __init__(self, flags_attr, required_flags):
        """Creates a new FlagDecider with the specified flag attribute and
        required flag names.

        :param flags_attr: The attribute that stores the flag value.
        :param required_flags: The names of all flags that have to be set."""
        self._flags_attr = flags_attr
        self._required_flags = required_flags

    def _decide_common(self, record):
        flags_val = getattr(record, self._flags_attr)
        return all(getattr(flags_val, flag_name)
                   for flag_name in self._required_flags)

class FormVersionDecider(ACommonDecider):
    """Decider that checks a record's form version."""
    def __init__(self, fv_callable: Callable[[int], Any]):
        """Creates a new FormVersionDecider with the specified callable.

        :param fv_callable: A callable taking an int, which will be the
            record's form version. The return value of this callable will be
            returned by the decider."""
        self._fv_callable = fv_callable

    def _decide_common(self, record):
        return self._fv_callable(record.header.form_version)

class SinceFormVersionDecider(FormVersionDecider):
    """Decider that compares the record's form version against a target form
    version."""
    def __init__(self, comp_op: Callable[[int, int], Any],
            target_form_ver: int):
        """Creates a new SinceFormVersionDecider with the specified parameters.

        :param comp_op: A callable that takes two integers, which will be the
            record's form version and target_form_ver. The return value of this
            callable will be returned by the decider.
        :param target_form_ver: The form version in which the change was
            introduced."""
        def _callable(rec_form_ver: int):
            return comp_op(rec_form_ver, target_form_ver)
        super().__init__(_callable)

class PartialLoadDecider(ADecider):
    """Partially loads a subrecord using a given loader, then rewinds the
    input stream and delegates to a given decider. Can decide at dump-time
    iff the given decider can as well."""
    def __init__(self, loader: MelBase, decider: ADecider):
        """Constructs a new PartialLoadDecider with the specified loader and
        decider.

        :param loader: The MelBase instance to use for loading. Must have a
            static size.
        :param decider: The decider to use after loading."""
        self._loader = loader
        self._load_size = loader.static_size
        self._decider = decider
        # This works because MelUnion._get_element_from_record does not use
        # self.__class__ to access can_decide_at_dump
        self.can_decide_at_dump = decider.can_decide_at_dump

    def decide_load(self, record, ins, sub_type, rec_size):
        starting_pos = ins.tell()
        # Make a deep copy so that no modifications from this decision will
        # make it to the actual record
        target = copy.deepcopy(record)
        self._loader.load_mel(target, ins, sub_type, self._load_size,
                              u'DECIDER', sub_type)
        ins.seek(starting_pos)
        # Use the modified record here to make the temporary changes visible to
        # the delegate decider
        return self._decider.decide_load(target, ins, sub_type, rec_size)

    def decide_dump(self, record):
        if not self.can_decide_at_dump:
            raise NotImplementedError
        # We can simply delegate here without doing anything else, since the
        # record has to have been loaded since then
        return self._decider.decide_dump(record)

class PerkEpdfDecider(ACommonDecider):
    """Decider for PERK's EPFD subrecord. Mostly just an AttrValDecider, except
    if the pp_param_type is 2 and the pe_function is one of several possible
    values, the result changes."""
    def __init__(self, int_functions: set[int]):
        self._int_functions = int_functions

    def _decide_common(self, record):
        pp_type = record.pp_param_type
        if pp_type == 2 and record.pe_function in self._int_functions:
            return 8
        return pp_type

class SaveDecider(ADecider):
    """Decider that returns True if the input file is a save."""
    def __init__(self):
        self._save_ext = bush.game.Ess.ext

    def decide_load(self, record, ins, sub_type, rec_size):
        return ins.inName.fn_ext == self._save_ext

class SignatureDecider(ADecider):
    """Very simple decider that just returns the subrecord type (aka
    signature). This is the default decider used by MelUnion."""
    def decide_load(self, record, ins, sub_type, rec_size):
        return sub_type

class SizeDecider(ADecider):
    """Decider that returns the size of the target subrecord."""
    def decide_load(self, record, ins, sub_type, rec_size):
        return rec_size

class MelUnion(MelBase):
    """Resolves to one of several record elements based on an ADecider.
    Defaults to a SignatureDecider.

    The decider is queried for a value, which is then used to perform a lookup
    in the element_mapping dict passed in. For example, consider this MelUnion,
    which showcases most features:
        MelUnion({
            'b': MelUInt32(b'DATA', 'value'), # actually a bool
            'f': MelFloat(b'DATA', 'value'),
            's': MelLString(b'DATA', 'value'),
        }, decider=AttrValDecider(
            'eid', transformer=lambda e: e[0] if e else 'i'),
            fallback=MelSInt32(b'DATA', 'value')
        ),
    When a DATA subrecord is encountered, the union is asked to load it. It
    queries its decider, which in this case reads the 'eid' attribute (i.e. the
    EDID subrecord) and returns the first character of that attribute's value,
    defaulting to 'i' if it's empty. The union then looks up the returned value
    in its mapping. If it finds it (e.g. if it's 'b'), then it will delegate
    loading to the MelBase-derived object mapped to that value. Otherwise, it
    will check if a fallback element is available. If it is, then that one is
    used. Otherwise, an ArgumentError is raised.

    When dumping and mapping fids, a similar process occurs. The decider is
    asked if it is capable of deciding with the (more limited) information
    available at this time. If it can, it is queried and the result is once
    again used to look up in the mapping. If, however, the decider can't decide
    at this time, the union looks if this is a newly created record or one that
    has been read. In the former case, it just picks an arbitrary element to
    dump out. In the latter case, it reuses the previous decider result to look
    up the mapping.

    Note: This class does not (and likely won't ever be able to) support
    getDefaulters / getDefault."""
    # Incremented every time we construct a MelUnion - ensures we always make
    # unique attributes on the records
    _union_index = 0

    def __init__(self, element_mapping: dict[Any, MelBase],
                 decider: ADecider = SignatureDecider(),
                 fallback: MelBase | None = None):
        """Creates a new MelUnion with the specified element mapping and
        optional parameters. See the class docstring for extensive information
        on MelUnion usage.

        :param element_mapping: The element mapping.
        :param decider: An ADecider instance to use. Defaults to
            SignatureDecider.
        :param fallback: The fallback element to use. Defaults to None, which
            will raise an error if the decider returns an unknown value."""
        # Decide on the decider
        if not isinstance(decider, ADecider):
            raise ArgumentError('decider must be an ADecider')
        self.decider = decider
        self.element_mapping = flatten_multikey_dict(element_mapping)
        self.fid_elements = set()
        self._sort_elements = set()
        # Create a unique attribute name to dynamically cache decider result
        self.decider_result_attr = f'_union_type_{MelUnion._union_index}'
        MelUnion._union_index += 1
        self.fallback = fallback
        self._possible_sigs = {*chain.from_iterable(element.signatures for
                               element in self.element_mapping.values())}
        if self.fallback:
            self._possible_sigs.update(self.fallback.signatures)

    def _get_element(self, decider_ret):
        """Retrieves the fitting element from element_mapping for the
        specified decider result.

        :param decider_ret: The result of the decide_* method that was
            invoked.
        :return: The matching record element to use."""
        element = self.element_mapping.get(decider_ret, self.fallback)
        if not element:
            raise ArgumentError(
                f'Specified element mapping did not handle a decider return '
                f'value ({decider_ret!r}) and there is no fallback')
        return element

    def _get_element_from_record(self, record):
        """Retrieves the fitting element based on the specified record instance
        only. Small wrapper around _get_element to share code between dumpData
        and mapFids.

        :param record: The record instance we're dealing with.
        :return: The matching record element to use."""
        if self.decider.can_decide_at_dump:
            # If the decider can decide at dump-time, let it
            return self._get_element(self.decider.decide_dump(record))
        elif not hasattr(record, self.decider_result_attr):
            # We're dealing with a record that was just created, but the
            # decider can't be used - default to some element
            return next(iter(self.element_mapping.values()))
        else:
            # We can use the result we decided earlier
            return self._get_element(
                getattr(record, self.decider_result_attr))

    def getSlotsUsed(self):
        # We need to reserve every possible slot, since we can't know what
        # we'll resolve to yet. Use a set to avoid duplicates.
        slots_ret = {self.decider_result_attr}
        for element in self.element_mapping.values():
            slots_ret.update(element.getSlotsUsed())
        if self.fallback: slots_ret.update(self.fallback.getSlotsUsed())
        return tuple(slots_ret)

    def getLoaders(self, loaders):
        # We need to collect all signatures and assign ourselves for them all
        # to handle unions with different signatures
        temp_loaders = {}
        for element in self.element_mapping.values():
            element.getLoaders(temp_loaders)
        if self.fallback: self.fallback.getLoaders(temp_loaders)
        for signature in temp_loaders:
            loaders[signature] = self

    def hasFids(self, formElements):
        # Ask each of our elements, and remember the ones where we'd have to
        # actually forward the mapFids call. We can't just blindly call
        # mapFids, since MelBase.mapFids is abstract.
        elements = self.element_mapping.values()
        if self.fallback: elements = self.fallback, *elements
        for element in elements:
            temp_elements = set()
            element.hasFids(temp_elements)
            if temp_elements:
                self.fid_elements.add(element)
        if self.fid_elements: formElements.add(self)

    def setDefault(self, record):
        # Ask each element - but we *don't* want to set our _union_type
        # attributes here! If we did, then we'd have no way to distinguish
        # between a loaded and a freshly constructed record.
        for element in self.element_mapping.values():
            element.setDefault(record)
        if self.fallback: self.fallback.setDefault(record)
        # This is somewhat hacky. We let all FormID elements set their
        # defaults  afterwards so that records have integers if possible,
        # otherwise mapFids will blow up on unions that haven't been loaded,
        # but contain FormIDs and other types in other union alternatives
        for element in self.fid_elements:
            element.setDefault(record)

    def mapFids(self, record, function, save_fids=False):
        element = self._get_element_from_record(record)
        if element in self.fid_elements:
            element.mapFids(record, function, save_fids)

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        # Ask the decider, and save the result for later - even if the decider
        # can decide at dump-time! Some deciders may want to have this as a
        # backup if they can't deliver a high-quality result.
        decider_ret = self.decider.decide_load(record, ins, sub_type, size_)
        setattr(record, self.decider_result_attr, decider_ret)
        self._get_element(decider_ret).load_mel(record, ins, sub_type, size_,
                                                *debug_strs)

    def dumpData(self, record, out):
        self._get_element_from_record(record).dumpData(record, out)

    def needs_sorting(self):
        # Ask each of our elements, and remember the ones we need to sort
        for element in self.element_mapping.values():
            if element.needs_sorting():
                self._sort_elements.add(element)
        return bool(self._sort_elements)

    def sort_subrecord(self, record):
        element = self._get_element_from_record(record)
        if element in self._sort_elements:
            element.sort_subrecord(record)

    @property
    def signatures(self):
        return self._possible_sigs

    @property
    def static_size(self):
        all_elements = list(self.element_mapping.values())
        if self.fallback:
            all_elements.append(self.fallback)
        first_size = all_elements[0].static_size # pick arbitrary element size
        if any(element.static_size != first_size for element in all_elements):
            raise NotImplementedError # The sizes are not all identical
        return first_size

#------------------------------------------------------------------------------
# Counters and Sorting
class _MelWrapper(MelBase):
    """Base class for classes like MelCounter and MelSorted that wrap another
    element."""
    def __init__(self, wrapped_mel: MelBase):
        self._wrapped_mel = wrapped_mel

    def getSlotsUsed(self):
        return self._wrapped_mel.getSlotsUsed()

    def getDefaulters(self, defaulters, base):
        self._wrapped_mel.getDefaulters(defaulters, base)

    def getDefault(self):
        return self._wrapped_mel.getDefault()

    def getLoaders(self, loaders):
        temp_loaders = {}
        self._wrapped_mel.getLoaders(temp_loaders)
        for l in temp_loaders:
            loaders[l] = self

    def hasFids(self, formElements):
        self._wrapped_mel.hasFids(formElements)

    def setDefault(self, record):
        self._wrapped_mel.setDefault(record)

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        self._wrapped_mel.load_mel(record, ins, sub_type, size_, *debug_strs)

    def dumpData(self, record, out):
        self._wrapped_mel.dumpData(record, out)

    def mapFids(self, record, function, save_fids=False):
        self._wrapped_mel.mapFids(record, function, save_fids)

    def needs_sorting(self):
        return self._wrapped_mel.needs_sorting()

    def sort_subrecord(self, record):
        self._wrapped_mel.sort_subrecord(record)

    @property
    def signatures(self):
        return self._wrapped_mel.signatures

    @property
    def static_size(self):
        return self._wrapped_mel.static_size

##: This ugliness just exposes how terrible _MelWrapper really is. A better
# tool is deperately wanted!
class _MelWrapperNoDD(_MelWrapper):
    """Variant of _MelWrapper that does not direct dumpData to the wrapped
    element. Necessary if you want to use pack_subrecord_data or packSub in
    your wrapper."""
    def dumpData(self, record, out):
        super(_MelWrapper, self).dumpData(record, out) # bypass _MelWrapper

    def pack_subrecord_data(self, record):
        return self._wrapped_mel.pack_subrecord_data(record)

    def packSub(self, out: BinaryIO, binary_data: bytes):
        self._wrapped_mel.packSub(out, binary_data)

#------------------------------------------------------------------------------
class MelCounter(_MelWrapper):
    """Wraps a _MelField-derived object (meaning that it is compatible with
    e.g. MelUInt32). Just before writing, the wrapped element's value is
    updated to the len() of another element's value, e.g. a MelGroups instance.
    Additionally, dumping is skipped if the counter is falsy after updating.

    See also MelPartialCounter, which targets mixed structs."""
    def __init__(self, counter_mel: MelBase, /, *, counts: str,
            is_required=False):
        """Creates a new MelCounter.

        :param counter_mel: The element that stores the counter's value.
        :param counts: The attribute name that this counter counts."""
        super(MelCounter, self).__init__(counter_mel)
        self._counted_attr = counts
        self._is_required = is_required

    def dumpData(self, record, out):
        # Count the counted type first, then check if we should even dump
        val_len = len(getattr(record, self._counted_attr, []))
        setattr(record, self._wrapped_mel.attr, val_len)
        if val_len or self._is_required:
            super().dumpData(record, out)

# NoDD for _MelObts and MelOmodData
class MelPartialCounter(_MelWrapperNoDD):
    """Similar to MelCounter, but works for MelStructs that contain more than
    just a counter (including multiple counters). This means adding behavior
    for mapping fids, but dropping the conditional dumping behavior."""
    def __init__(self, counter_mel: MelStruct, /, *, counters: dict[str, str]):
        """Creates a new MelPartialCounter.

        :param counter_mel: The element that stores the counter's value.
        :param counters: A dict mapping counter attribute names to the
            names of the attributes those counters count."""
        super().__init__(counter_mel)
        self._counters = counters

    def dumpData(self, record, out):
        for counter_attr, counted_attr in self._counters.items():
            setattr(record, counter_attr,
                len(getattr(record, counted_attr, [])))
        super().dumpData(record, out)

#------------------------------------------------------------------------------
class MelExtra(_MelWrapperNoDD):
    """Used to wrap another element that has additional unknown/junk data of
    varying length after it."""
    def __init__(self, wrapped_mel: MelBase, *, extra_attr: str):
        super().__init__(wrapped_mel)
        # Check if the wrapped element is static-sized and store the size if so
        try:
            self._wrapped_size = wrapped_mel.static_size
        except NotImplementedError:
            self._wrapped_size = None
        self._extra_attr = extra_attr

    def getSlotsUsed(self):
        return self._extra_attr, *super().getSlotsUsed()

    def load_mel(self, record, ins, sub_type, size_, *debug_strs):
        # Load everything but the unknown/junk data - pass the static size if
        # the component is static-sized (and hence will probably be verifying
        # the subrecord size) or the full subrecord size if it's not
        start_pos = ins.tell()
        super().load_mel(record, ins, sub_type, self._wrapped_size or size_,
            *debug_strs)
        # Now, read the remainder of the subrecord and store it
        read_size = ins.tell() - start_pos
        setattr(record, self._extra_attr, ins.read(size_ - read_size))

    def pack_subrecord_data(self, record):
        final_packed = self._wrapped_mel.pack_subrecord_data(record)
        extra_data = getattr(record, self._extra_attr)
        if extra_data is not None:
            final_packed += extra_data
        return final_packed

#------------------------------------------------------------------------------
class MelSorted(_MelWrapper):
    """Wraps a MelBase-derived element with a list as its single attribute and
    sorts that list right after loading and right before dumping."""

    def __init__(self, sorted_mel: MelBase, sort_by_attrs=(),
                 sort_special: callable = None):
        """Creates a new MelSorted instance with the specified parameters.

        :param sorted_mel: The element that needs sorting.
        :param sort_by_attrs: May either be a tuple or a string. Specifies the
            attribute(s) of the list entries that should be used as the sort
            key(s). If left empty, the entire list entry will be used as the
            sort key (same as specifying key=None for a sort).
        :param sort_special: Allows specifying a completely custom key function
            for sorting."""
        super().__init__(sorted_mel)
        if sort_special:
            # Special key function given, use that
            self._attr_key_func = sort_special
        elif sort_by_attrs:
            # One or more attributes given, verify they exist and make an
            # attrgetter out of them to use as the key function
            ##: This is pretty hacky - a MelBase method a la all_leaf_attrs
            # would be very useful here
            if isinstance(sorted_mel, MelSequential):
                all_child_attrs = set()
                for e in sorted_mel.elements:
                    all_child_attrs.update(e.getSlotsUsed())
            elif isinstance(sorted_mel, MelArray):
                all_child_attrs = set(sorted_mel.array_element_attrs)
            else:
                raise SyntaxError(f'sort_by_attrs is not supported for '
                                  f'{type(sorted_mel)} instances')
            # Note that sort_by_attrs could be either a single attr or a tuple
            # of attrs
            wanted_attrs = set(sort_by_attrs) if isinstance(
                sort_by_attrs, tuple) else {sort_by_attrs}
            missing_attrs = wanted_attrs - all_child_attrs
            if missing_attrs:
                raise SyntaxError(f'The following attributes passed to '
                    f'sort_by_attrs do not exist: {sorted(missing_attrs)}')
            self._attr_key_func = attrgetter_cache[sort_by_attrs]
        else:
            # Simply use the default key function (whole list entries)
            self._attr_key_func = None

    def needs_sorting(self):
        return True

    def sort_subrecord(self, record):
        # Sort child subrecords first, since the sort for this subrecord may
        # depend on their order
        super().sort_subrecord(record)
        to_sort_val = getattr(record, self._wrapped_mel.attr)
        if to_sort_val:
            to_sort_val.sort(key=self._attr_key_func)

#------------------------------------------------------------------------------
class MelDependentSequential(MelSequential):
    """A MelSequential where some elements will only be dumped if other
    elements are present. Especially useful for elements that are required iff
    another element is present. See also MelDependentGroups."""
    def __init__(self, *elements,
            dependencies: dict[int | tuple[int, ...], list[str]]):
        """Create a new MelDependentSequential with the specified parameters.

        :param dependencies: A dict (or multikey dict) mapping element indices
            to a list of attributes that must be truthy, most notably not None,
            in order for the element at that index to be dumped out."""
        super().__init__(*elements)
        self._group_dependencies = flatten_multikey_dict(dependencies)

    def dumpData(self, record, out):
        for i, element in enumerate(self.elements):
            dependent_attrs = self._group_dependencies.get(i)
            if (dependent_attrs is None or
                    all(getattr(record, a) for a in dependent_attrs)):
                element.dumpData(record, out)

#------------------------------------------------------------------------------
class MelDependentGroups(MelDependentSequential, MelGroups):
    """A MelGroups version of MelDependentSequential, see there for docs."""
    def __init__(self, attr: str, *elements,
            dependencies: dict[int, list[str]]):
        # Skip MelDependentSequential's initializer, we need MelGroups' for the
        # attribute name
        super(MelDependentSequential, self).__init__(attr, *elements)
        self._group_dependencies = dependencies
