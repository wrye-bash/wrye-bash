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
"""Compiled Papyrus script files. File extension is .pex (probably stands for
Papyrus EXecutable). They are also big-endian, contrasting with almost every
other Bethesda-related file format."""
# Note: the classes in here are carefully ordered to avoid dependency issues

import sys
from collections import OrderedDict
from struct import calcsize

from . import AFile
from ..binary import ABinaryComponent, AVariableContainer
from ..bolt import Flags, struct_pack, struct_unpack
from ..exception import FileError

__author__ = u'Infernio'

# TODO(inf) If we want to be able to create new ones (e.g. to implement our own
#  compiler), binary.py will need edits to accept defaults for each processor
# Utilities -------------------------------------------------------------------
class _APEXComponent(ABinaryComponent):
    """Abstract base class for PEX components. Sets Windows-1252 as
    encoding and enforces big-endian byte ordering."""
    format_prefix = '>'
    override_input_enc = override_output_enc = u'cp1252'

class _APEXVariableContainer(_APEXComponent, AVariableContainer):
    """Variant of AVariableContainer, but with the right encodings set."""

def _read_pex_byte(ins):
    """Version of unpack_byte that uses big-endian."""
    return struct_unpack('>B', ins.read(1))[0]

def _read_pex_short(ins):
    """Version of unpack_short that uses big-endian."""
    return struct_unpack('>H', ins.read(2))[0]

# Header ----------------------------------------------------------------------
class _PEXHeader(_APEXComponent):
    """Implements the PEX header. Ensures that the magic number is correct and
    raises an error if it's not."""
    processors = OrderedDict([
        ('pex_magic',         'I'),
        ('pex_major_version', 'B'),
        ('pex_minor_version', 'B'),
        ('game_id',           'H'),
        ('compilation_time',  'Q'),
        ('source_file_name',  'str16'),
        ('user_name',         'str16'),
        ('machine_name',      'str16'),
    ])

    def load_data(self, component, ins):
        super(_PEXHeader, self).load_data(component, ins)
        if component.pex_magic != 0xFA57C0DE:
            raise RuntimeError(u'Invalid PEX file: Wrong magic (expected '
                               u'0xFA57C0DE, got 0x%08X)' %
                               component.pex_magic)

# String Table ----------------------------------------------------------------
class _PEXStringTableEntry(_APEXComponent):
    """Implements a single entry in the PEX string table."""
    processors = OrderedDict([
        ('str_val', 'str16'),
    ])

class _PEXStringTable(_APEXVariableContainer):
    """Implements the PEX string table."""
    processors = OrderedDict([
        ('string_count', 'H'),
    ])
    child_loader = _PEXStringTableEntry()
    children_attr = 'stored_strings'
    counter_attr = 'string_count'

# Debug Info ------------------------------------------------------------------
class _PEXLineNumber(_APEXComponent):
    """Implements a single entry in the line number array."""
    processors = OrderedDict([
        ('line_num', 'H'),
    ])

class _PEXDebugFunction(_APEXVariableContainer):
    """Implements a single debug function. Any number of these may be stored in
    a debug info component. They also contain children themselves, in the form
    of an array of line numbers, which maps instructions back to their source
    code lines."""
    processors = OrderedDict([
        ('object_name_index',   'H'),
        ('state_name_index',    'H'),
        ('function_name_index', 'H'),
        ('function_type',       'B'),
        ('line_num_count',      'H'),
    ])
    child_loader = _PEXLineNumber()
    children_attr = 'line_numbers'
    counter_attr = 'line_num_count'

class _PEXDebugInfo(_APEXVariableContainer):
    """Implements the debug info section. The difficult part here is that it is
    preceded by a boolean which, if False, means that this component is not
    actually present in the PEX file."""
    processors = OrderedDict([
        ('modification_time',    'Q'),
        ('debug_function_count', 'H'),
    ])
    child_loader = _PEXDebugFunction()
    children_attr = 'debug_functions'
    counter_attr = 'debug_function_count'

    def dump_data(self, component):
        # If has_debug_info is False, don't dump out this component
        out_data = struct_pack('>B', component.has_debug_info)
        if component.has_debug_info:
            out_data += super(_PEXDebugInfo, self).dump_data(component)
        return out_data

    def load_data(self, component, ins):
        # Begins with a bool - if that is False, skip the entire component
        do_load = component.has_debug_info = _read_pex_byte(ins)
        if do_load: super(_PEXDebugInfo, self).load_data(component, ins)

    @property
    def used_slots(self):
        return ['has_debug_info'] + super(_PEXDebugInfo, self).used_slots

    def get_size(self, component):
        return super(_PEXDebugInfo, self).get_size(component) + 1

# User Flags ------------------------------------------------------------------
class _PEXUserFlag(_APEXComponent):
    """Implements a single user flag."""
    processors = OrderedDict([
        ('name_index', 'H'),
        ('flag_index', 'B'),
    ])

class _PEXUserFlags(_APEXVariableContainer):
    """Implements an array of user flags with a preceding 16-bit count."""
    processors = OrderedDict([
        ('user_flag_count', 'H'),
    ])
    child_loader = _PEXUserFlag()
    children_attr = 'active_user_flags'
    counter_attr = 'user_flag_count'

# Values ----------------------------------------------------------------------
class _PEXValue(_APEXComponent):
    """Implements a single value component. The difficult part here is that the
    type of value that is stored varies depending on the value of the uint8
    that comes before it."""
    processors = OrderedDict([
        ('value_type', 'B'),
    ])
    var_type_to_format = {
        0: '',  # null
        1: 'H', # identifier
        2: 'H', # string
        3: 'i', # integer
        4: 'f', # float
        5: 'B', # bool
    }

    def dump_data(self, component):
        out_data = super(_PEXValue, self).dump_data(component)
        var_fmt = self.var_type_to_format[component.value_type]
        if var_fmt: # skip null
            out_data += struct_pack('>' + var_fmt, component.value_data)
        return out_data

    def load_data(self, component, ins):
        super(_PEXValue, self).load_data(component, ins)
        var_fmt = self.var_type_to_format[component.value_type]
        if var_fmt: # skip null
            component.value_data = struct_unpack(
                '>' + var_fmt, ins.read(calcsize(var_fmt)))[0]

    @property
    def used_slots(self):
        return ['value_data'] + super(_PEXValue, self).used_slots

    def get_size(self, component):
        total_size = super(_PEXValue, self).get_size(component)
        val_type = component.value_type
        if val_type in (1, 2): # string or identifier
            total_size += len(component.value_data)
        elif val_type in (3, 4): # integer or float
            total_size += 4
        else: # val_type == 5
            total_size += 1
        return total_size

# Variable --------------------------------------------------------------------
class _PEXVariableType(_APEXComponent):
    """Implements a single variable type component."""
    processors = OrderedDict([
        ('variable_name', 'H'),
        ('variable_type', 'H'),
    ])

class _PEXVariable(_APEXComponent):
    """Implements a single variable. Contains both a variable type and value
    component, with a uint32 between them."""
    processors = OrderedDict([
        ('var_user_flags', 'I'),
    ])
    _var_type_loader = _PEXVariableType()
    _var_default_val_loader = _PEXValue()

    def dump_data(self, component):
        return (self._var_type_loader.dump_data(component)
                + super(_PEXVariable, self).dump_data(component)
                + self._var_default_val_loader.dump_data(component))

    def load_data(self, component, ins):
        self._var_type_loader.load_data(component, ins)
        super(_PEXVariable, self).load_data(component, ins)
        self._var_default_val_loader.load_data(component, ins)

    @property
    def used_slots(self):
        return (self._var_type_loader.used_slots
                + self._var_default_val_loader.used_slots
                + super(_PEXVariable, self).used_slots)

    def get_size(self, component):
        return (self._var_type_loader.get_size(component)
                + self._var_default_val_loader.get_size(component)
                + super(_PEXVariable, self).get_size(component))

# Instructions ----------------------------------------------------------------
_opcodes = {
    # Syntax: byte -> (opcode, # of args, has varargs)
    0x00: (u'nop',                0, False),
    0x01: (u'iadd',               3, False),
    0x02: (u'fadd',               3, False),
    0x03: (u'isub',               3, False),
    0x04: (u'fsub',               3, False),
    0x05: (u'imul',               3, False),
    0x06: (u'fmul',               3, False),
    0x07: (u'idiv',               3, False),
    0x08: (u'fdiv',               3, False),
    0x09: (u'imod',               3, False),
    0x0A: (u'not',                2, False),
    0x0B: (u'ineg',               2, False),
    0x0C: (u'fneg',               2, False),
    0x0D: (u'assign',             2, False),
    0x0E: (u'cast',               2, False),
    0x0F: (u'cmp_eq',             3, False),
    0x10: (u'cmp_lt',             3, False),
    0x11: (u'cmp_lte',            3, False),
    0x12: (u'cmp_gt',             3, False),
    0x13: (u'cmp_gte',            3, False),
    0x14: (u'jmp',                1, False),
    0x15: (u'jmpt',               2, False),
    0x16: (u'jmpf',               2, False),
    0x17: (u'callmethod',         3, True),
    0x18: (u'callparent',         2, True),
    0x19: (u'callstatic',         3, True),
    0x1A: (u'return',             1, False),
    0x1B: (u'strcat',             3, False),
    0x1C: (u'propget',            3, False),
    0x1D: (u'propset',            3, False),
    0x1E: (u'array_create',       2, False),
    0x1F: (u'array_length',       2, False),
    0x20: (u'array_getelement',   3, False),
    0x21: (u'array_setelement',   3, False),
    0x22: (u'array_findelement',  4, False),
    0x23: (u'array_rfindelement', 4, False),
}

class _PEXInstruction(_APEXComponent):
    """Implements a single instruction. The difficult part here is that the
    arguments change heavily depending on the opcode of the instruction: the
    number of arguments can change, and some opcodes support varargs as
    well."""
    processors = OrderedDict([
        ('opcode', 'B'),
    ])
    _value_loader = _PEXValue()

    def dump_data(self, component):
        # Verify some stuff up front
        _mnemonic, num_args, has_varargs = _opcodes[component.opcode]
        if len(component.arguments) != num_args:
            raise RuntimeError(u'Wrong number of arguments when writing')
        if bool(component.varargs) != has_varargs:
            raise RuntimeError(u'Incorrect varargs state when writing')
        dump_arg = self._value_loader.dump_data
        out_data = super(_PEXInstruction, self).dump_data(component)
        out_data += ''.join(dump_arg(a) for a in component.arguments)
        out_data += dump_arg(component.vararg_count)
        return out_data + ''.join(dump_arg(a) for a in component.varargs)

    def load_data(self, component, ins):
        new_arg = self._value_loader.make_new
        load_arg = self._value_loader.load_data
        def load_arguments(arg_count):
            """Helper method to share code for regular args and varargs."""
            temp_arguments = []
            append_arg = temp_arguments.append
            for x in xrange(arg_count):
                next_arg = new_arg()
                load_arg(next_arg, ins)
                append_arg(next_arg)
            return temp_arguments
        super(_PEXInstruction, self).load_data(component, ins)
        _mnemonic, num_args, has_varargs = _opcodes[component.opcode]
        component.arguments = load_arguments(num_args)
        if has_varargs:
            # Yes, the counter is a value. It can only be an integer
            # (duh, loading 0.5 or 'foo' varargs makes no sense), but why not
            # just use a uint32 right away??
            vararg_c = component.vararg_count = new_arg()
            load_arg(vararg_c, ins)
            if vararg_c.value_type != 3:
                raise RuntimeError(u'Invalid PEX file: Invalid value type for '
                                   u'varargs (expected 3, got %u)' %
                                   vararg_c.value_type)
            component.varargs = load_arguments(vararg_c.value_data)

    @property
    def used_slots(self):
        return ['arguments', 'vararg_count', 'varargs'] + super(
            _PEXInstruction, self).used_slots

    def get_size(self, component):
        _mnemonic, _num_args, has_varargs = _opcodes[component.opcode]
        value_size = self._value_loader.get_size
        total_size = super(_PEXInstruction, self).get_size(component)
        total_size += sum(value_size(a) for a in component.arguments)
        if has_varargs:
            total_size += value_size(component.vararg_count)
            total_size += sum(value_size(v) for v in component.varargs)
        return total_size

# Functions -------------------------------------------------------------------
class _PEXFunction(_APEXVariableContainer):
    """Implements a single function. Contains three child lists (parameters,
    local variables and instructions)."""
    processors = OrderedDict([
        ('return_type',         'H'),
        ('docstring',           'H'),
        ('function_user_flags', 'I'),
        ('function_flags',      'B'),
        ('param_count',         'H'),
    ])
    child_loader = _PEXVariableType()
    children_attr = 'parameters'
    counter_attr = 'param_count'
    _instruction_loader = _PEXInstruction()
    _function_flags = Flags(names=Flags.getNames(
        'global_function',
        'native_function',
    ))

    def dump_data(self, component):
        dump_local = self.child_loader.dump_data
        dump_instruction = self._instruction_loader.dump_data
        out_data = super(_PEXFunction, self).dump_data(component)
        out_data += struct_pack('>H', len(component.local_vars))
        out_data += ''.join(dump_local(l) for l in component.local_vars)
        out_data += struct_pack('>H', len(component.instructions))
        return out_data + ''.join(dump_instruction(i)
                                  for i in component.instructions)

    def load_data(self, component, ins):
        new_instruction = self._instruction_loader.make_new
        new_local = self.child_loader.make_new
        load_instruction = self._instruction_loader.load_data
        load_local = self.child_loader.load_data
        super(_PEXFunction, self).load_data(component, ins)
        component.function_flags = self._function_flags(
            component.function_flags)
        component.local_vars = []
        append_local = component.local_vars.append
        for x in xrange(_read_pex_short(ins)):
            curr_local = new_local()
            load_local(curr_local, ins)
            append_local(curr_local)
        component.instructions = []
        append_instruction = component.instructions.append
        for x in xrange(_read_pex_short(ins)):
            curr_instruction = new_instruction()
            load_instruction(curr_instruction, ins)
            append_instruction(curr_instruction)

    @property
    def used_slots(self):
        return ['local_vars', 'instructions'] + super(
            _PEXFunction, self).used_slots

    def get_size(self, component):
        local_var_size = self.child_loader.get_size
        instruction_size = self._instruction_loader.get_size
        total_size = super(_PEXFunction, self).get_size(component)
        total_size += sum(local_var_size(l) for l in component.local_vars)
        total_size += sum(instruction_size(i) for i in component.instructions)
        return total_size + 4 # 2 16bit counters

class _PEXNamedFunction(_APEXComponent):
    """Implements a single named function. A named function simply consists of
    a name and a function."""
    processors = OrderedDict([
        ('function_name', 'H'),
    ])
    _function_loader = _PEXFunction()

    def dump_data(self, component):
        return (super(_PEXNamedFunction, self).dump_data(component)
                + self._function_loader.dump_data(component))

    def load_data(self, component, ins):
        super(_PEXNamedFunction, self).load_data(component, ins)
        self._function_loader.load_data(component, ins)

    @property
    def used_slots(self):
        return self._function_loader.used_slots + super(
            _PEXNamedFunction, self).used_slots

    def get_size(self, component):
        return self._function_loader.get_size(component) + super(
            _PEXNamedFunction, self).get_size(component)

# States ----------------------------------------------------------------------
class _PEXState(_APEXVariableContainer):
    processors = OrderedDict([
        ('state_name',           'H'),
        ('state_function_count', 'H'),
    ])
    child_loader = _PEXNamedFunction()
    children_attr = 'state_functions'
    counter_attr = 'state_function_count'

# Properties ------------------------------------------------------------------
class _PEXProperty(_APEXComponent):
    """Implements a single property. The difficult part here is that the
    property flags determine what comes after them."""
    processors = OrderedDict([
        ('property_name',       'H'),
        ('property_type',       'H'),
        ('docstring',           'H'),
        ('property_user_flags', 'I'),
        ('property_flags',      'B'),
    ])
    _function_loader = _PEXFunction()
    _property_flags = Flags(names=Flags.getNames(
        'is_readable',
        'is_writable',
        'has_autovar',
    ))

    def dump_data(self, component):
        out_data = super(_PEXProperty, self).dump_data(component)
        prop_flags = component.property_flags
        if prop_flags.has_autovar:
            # Wins out over the other flags
            out_data += struct_pack('>H', component.auto_var_name)
        else:
            dump_handler = self._function_loader.dump_data
            if prop_flags.is_readable:
                out_data += dump_handler(component.read_handler)
            if prop_flags.is_writable:
                out_data += dump_handler(component.write_handler)
        return out_data

    def load_data(self, component, ins):
        super(_PEXProperty, self).load_data(component, ins)
        prop_flags = component.property_flags = self._property_flags(
            component.property_flags)
        if prop_flags.has_autovar:
            # Wins out over the other flags
            component.auto_var_name = _read_pex_short(ins)
        else:
            new_handler = self._function_loader.make_new
            load_handler = self._function_loader.load_data
            if prop_flags.is_readable:
                curr_handler = component.read_handler = new_handler()
                load_handler(curr_handler, ins)
            if prop_flags.is_writable:
                curr_handler = component.write_handler = new_handler()
                load_handler(curr_handler, ins)

    @property
    def used_slots(self):
        return ['auto_var_name', 'read_handler', 'write_handler'] + super(
            _PEXProperty, self).used_slots

    def get_size(self, component):
        total_size = super(_PEXProperty, self).get_size(component)
        prop_flags = component.property_flags
        if prop_flags.has_autovar:
            # Wins out over the other flags
            total_size += 2
        else:
            handler_size = self._function_loader.get_size
            if prop_flags.is_readable:
                total_size += handler_size(component.read_handler)
            if prop_flags.is_writable:
                total_size += handler_size(component.write_handler)
        return total_size

# Objects ---------------------------------------------------------------------
class _PEXObjectData(_APEXVariableContainer):
    """Implements a single object data component. Contains three child lists
    (variables, properties and states)."""
    processors = OrderedDict([
        ('parent_class_name', 'H'),
        ('docstring',         'H'),
        ('object_user_flags', 'I'),
        ('auto_state_name',   'H'),
        ('variable_count',    'H'),
    ])
    child_loader = _PEXVariable()
    children_attr = 'variables'
    counter_attr = 'variable_count'
    _property_loader = _PEXProperty()
    _state_loader = _PEXState()

    def dump_data(self, component):
        dump_property = self._property_loader.dump_data
        dump_state = self._state_loader.dump_data
        out_data = super(_PEXObjectData, self).dump_data(component)
        out_data += struct_pack('>H', len(component.properties))
        out_data += ''.join(dump_property(p) for p in component.properties)
        out_data += struct_pack('>H', len(component.states))
        return out_data + ''.join(dump_state(s) for s in component.states)

    def load_data(self, component, ins):
        new_property = self._property_loader.make_new
        new_state = self._state_loader.make_new
        load_property = self._property_loader.load_data
        load_state = self._state_loader.load_data
        super(_PEXObjectData, self).load_data(component, ins)
        component.properties = []
        append_property = component.properties.append
        for x in xrange(_read_pex_short(ins)):
            next_prop = new_property()
            load_property(next_prop, ins)
            append_property(next_prop)
        component.states = []
        append_state = component.states.append
        for x in xrange(_read_pex_short(ins)):
            next_state = new_state()
            load_state(next_state, ins)
            append_state(next_state)

    @property
    def used_slots(self):
        return ['properties', 'states'] + super(
            _PEXObjectData, self).used_slots

    def get_size(self, component):
        prop_size = self._property_loader.get_size
        state_size = self._state_loader.get_size
        total_size = super(_PEXObjectData, self).get_size(component)
        total_size += sum(prop_size(p) for p in component.properties)
        total_size += sum(state_size(s) for s in component.states)
        return total_size + 4 # 2 16bit counters

class _PEXObject(_APEXComponent):
    """Implements a single object."""
    processors = OrderedDict([
        ('name_index',  'H'),
        ('object_size', 'I'),
    ])
    _object_data_loader = _PEXObjectData()

    def dump_data(self, component):
        component.object_size = self._object_data_loader.get_size(
            component) + 4 # for some reason, the size field itself is counted
        out_data = super(_PEXObject, self).dump_data(component)
        return out_data + self._object_data_loader.dump_data(component)

    def load_data(self, component, ins):
        super(_PEXObject, self).load_data(component, ins)
        self._object_data_loader.load_data(component, ins)

    @property
    def used_slots(self):
        return self._object_data_loader.used_slots + super(
            _PEXObject, self).used_slots

    def get_size(self, component):
        return self._object_data_loader.get_size(component) + super(
            _PEXObject, self).get_size(component)

class _PEXObjects(_APEXVariableContainer):
    processors = OrderedDict([
        ('object_count', 'H'),
    ])
    child_loader = _PEXObject()
    children_attr = 'object_list'
    counter_attr = 'object_count'

# PEX Files -------------------------------------------------------------------
class PEXFile(AFile):
    """A compiled Papyrus script file (.pex, Papyrus EXecutable)."""
    # TODO(inf) loading_state - second time we're doing this. Might be time for
    #  some sort of API in AFile to remember how far a file has been loaded?
    # Would also allow the ugly '[:1]' down there to be dropped
    __slots__ = ('loading_state', 'pex_header', 'string_table', 'debug_info',
                 'user_flags', 'pex_objects',)
    # Start at 1, 0 means unloaded
    target_states = {v: k for k, v in enumerate(__slots__[1:], start=1)}

    def __init__(self, pex_path, load_cache=False):
        self.loading_state = 0
        super(PEXFile, self).__init__(pex_path, load_cache,
                                      raise_on_error=True)

    # API ---------------------------------------------------------------------
    def get_opcode_info(self, component):
        """Returns opcode info as a tuple - mnemonic, #args, has varags."""
        return _opcodes[component.opcode]

    def get_user_flag_mapper(self):
        """Returns a bolt.Flags instance that handles this script's user
        flags."""
        return Flags(names={
            self.look_up_string(f.name_index): f.flag_index
            for f in self.user_flags.active_user_flags
        })

    def look_up_string(self, string_index):
        """Looks up the specified string index in this PEX file's string
        table."""
        self.read_pex_file(up_to='string_table')
        return self.string_table.stored_strings[string_index].str_val

    def read_pex_file(self, up_to=None):
        """Reads this PEX file and assigns all read components to the matching
        instance attributes - see __slots__ for an overview. Will simply return
        if the file has already been loaded.

        :param up_to: If set to one of this class's attributes, will only read
            that much of the file. If set to None (the default), will read
            everything.
        :type up_to: str | None"""
        def should_read_part(part_attr):
            """Helper method to check if we should load this part of the
            file.

            :type part_attr: str"""
            return target_state >= self.target_states[part_attr]
        def read_part(part_loader, part_attr):
            """Helper method for reading part of a PEX file.

            :type part_loader: _APEXComponent
            :type part_attr: str"""
            read_target = part_loader.make_new()
            part_loader.load_data(read_target, ins)
            setattr(self, part_attr, read_target)
        # If 'up_to' is unknown or None, load everything
        target_state = self.target_states.get(up_to, len(self.target_states))
        if self.loading_state < target_state:
            try:
                with self.abs_path.open('rb') as ins:
                    if not should_read_part('pex_header'): return
                    read_part(_PEXHeader(), 'pex_header')
                    if not should_read_part('string_table'): return
                    read_part(_PEXStringTable(), 'string_table')
                    if not should_read_part('debug_info'): return
                    read_part(_PEXDebugInfo(), 'debug_info')
                    if not should_read_part('user_flags'): return
                    read_part(_PEXUserFlags(), 'user_flags')
                    if not should_read_part('pex_objects'): return
                    read_part(_PEXObjects(), 'pex_objects')
                    if ins.tell() < self.abs_path.size:
                        raise FileError(self.abs_path, u'Invalid PEX file: '
                                                       u'Leftover data at end '
                                                       u'of file')
            except RuntimeError as e:
                raise FileError, (self.abs_path, e.__class__.__name__ + u' ' +
                                  e.message), sys.exc_info()[2]

    def write_pex_file(self, out_path):
        self.read_pex_file() # We need the entire PEX file to write
        out_data = self.pex_header.dump_data()
        out_data += self.string_table.dump_data()
        out_data += self.user_flags.dump_data()
        out_data += self.debug_info.dump_data()
        out_data += self.pex_objects.dump_data()
        with out_path.open('wb') as out:
            out.write(out_data)

    def write_pex_file_safe(self, out_path=u''):
        """Writes out any in-memory changes that have been made to this PEX
        file to the specified path, first moving it to a temporary location to
        avoid overwriting the original file if something goes wrong.

        :param out_path: The path to write to. If empty or None, this PEX
            file's own path is used instead."""
        out_path = out_path or self.abs_path
        self.write_pex_file(out_path.temp)
        out_path.untemp()

    # Overrides ---------------------------------------------------------------
    def _reset_cache(self, stat_tuple, load_cache):
        # Reset our loading state to 'unloaded', which will discard everything
        # when the next request is made to the PEX file (see read_pex_file)
        self.loading_state = 0
        super(PEXFile, self)._reset_cache(stat_tuple, load_cache)

def get_pex_type(game_fsName):
    """:rtype: type[PEXFile]"""
    # TODO(inf) FO4 needs adjustments here
    return PEXFile
