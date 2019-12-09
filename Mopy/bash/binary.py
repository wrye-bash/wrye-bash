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
# TODO(inf) Refactor some other parts of WB to use this (VMAD, cosaves,
#  save headers)?
# Pros:
#  - *Massively* cuts down on duplicate code
#  - Only one format to learn for newcomers to the code
# Cons:
#  - We lose IDE support vs the current cosaves way of doing it
#  - The way these classes work is fairly unintuitive - it was created for
#    VMAD, which is part of the record code, so that's where the 'inspiration'
#    came from
"""Provides abstract classes for reading and writing binary files that have
arbitrarily complex internal hierarchy, e.g. VMAD subrecords and compiled
Papyrus script files (.pex)."""

from collections import OrderedDict
from struct import calcsize

from bolt import decode, encode, struct_pack, struct_unpack

__author__ = u'Infernio'

# Internal --------------------------------------------------------------------
def _dump_str16(str_val, target_enc, fmt_prefix):
    """Encodes the specified string using the specified encoding and returns
    data for both its length (as a 16-bit integer) and its encoded value."""
    encoded_str = encode(str_val, firstEncoding=target_enc)
    return struct_pack(fmt_prefix + 'H', len(encoded_str)) + encoded_str

def _read_str16(ins, target_enc, fmt_prefix):
    """Reads a 16-bit length integer, then reads a string of that length. Uses
    the specified encoding to decode, unless it is None, in which case chardet
    is queried."""
    return decode(ins.read(struct_unpack(fmt_prefix + 'H', ins.read(2))[0]),
                  encoding=target_enc)

class _AComponentInstance(object):
    """Abstract base class for all dynamically created component instances."""
    __slots__ = ()

    # TODO(inf) Entirely copy-pasted from MelObject
    def __repr__(self):
        to_show = []
        for obj_attr in self.__slots__:
            if hasattr(self, obj_attr):
                to_show.append(u'%s: %r' % (obj_attr, getattr(self, obj_attr)))
        return u'<%s>' % u', '.join(sorted(to_show)) # is sorted() needed here?

# Public ----------------------------------------------------------------------
class ABinaryComponent(object):
    """Abstract base class for binary file components. Specify a 'processors'
    class variable to use. Syntax: OrderedDict, mapping an attribute name
    for the record to a tuple containing a format string (limited to format
    strings that resolve to a single attribute). 'str16' is a special format
    string that instead reads a uint16 and a string of that length.

    By default, chardet is called to determine the most appropriate encoding
    for any read strings. However, you may override this by changing the class
    variable 'override_input_enc'. Written strings use ASCII encoding by
    default. Again, this can be changed by changing the class variable
    'override_output_enc'.

    By default, all struct calls prefix an '=' character to avoid padding. You
    can override this by changing the 'format_prefix' class variable, e.g. if
    you have to write big-endian files or if you want the padding.

    You can override any of the methods specified below to do other things
    after or before 'processors' has been evaluated, just be sure to call
    super(...).{dump,load}_data(...) when appropriate.

    :type processors: OrderedDict[str, str]
    :type override_input_enc: unicode | None"""
    format_prefix = '='
    processors = OrderedDict()
    override_input_enc = None
    override_output_enc = u'ascii'

    def dump_data(self, component):
        """Returns data for the specified component instance and returns the
        result as a string, ready for writing to an output stream."""
        getter = component.__getattribute__
        out_data = ''
        for attr, fmt_str in self.__class__.processors.iteritems():
            attr_val = getter(attr)
            if fmt_str == 'str16':
                out_data += _dump_str16(
                    attr_val, self.__class__.override_output_enc,
                    self.__class__.format_prefix)
            else:
                out_data += struct_pack(self.__class__.format_prefix + fmt_str,
                                        attr_val)
        return out_data

    def load_data(self, component, ins):
        """Loads data from the specified input stream and attaches it to the
        specified component instance."""
        setter = component.__setattr__
        for attr, fmt_str in self.__class__.processors.iteritems():
            if fmt_str == 'str16':
                read_val = _read_str16(ins, self.__class__.override_input_enc,
                                       self.__class__.format_prefix)
            else:
                read_val = struct_unpack(
                    self.__class__.format_prefix + fmt_str,
                    ins.read(calcsize(fmt_str)))[0]
            setter(attr, read_val)

    def make_new(self):
        """Creates a new runtime instance of this component with the
        appropriate __slots__ set."""
        try:
            return self._component_class()
        except AttributeError:
            class _ComponentInstance(_AComponentInstance):
                __slots__ = self.used_slots
            self._component_class = _ComponentInstance # create only once
            return self._component_class()

    @property
    def used_slots(self):
        """Returns a list containing the slots needed by this component. Note
        that this should not change at runtime, since the class created with it
        is cached - see make_new above."""
        return [x for x in self.__class__.processors.iterkeys()]

    def get_size(self, component):
        """Returns the size of this component, in bytes.

        :rtype: int"""
        total_size = 0
        getter = component.__getattribute__
        for attr, fmt_str in self.__class__.processors.iteritems():
            attr_val = getter(attr)
            if fmt_str == 'str16':
                total_size += len(attr_val) + 2
            else:
                total_size += calcsize(fmt_str)
        return total_size

class AFixedContainer(ABinaryComponent):
    """Abstract base class for components that contain a fixed number of other
    components. Which ones are present is determined by a flags field. You
    need to specify a processor that sets an attribute named, by default,
    'fragment_flags' to the right value (you can change the name using the
    class variable 'flags_attr'). Additionally, you have to set 'flags_mapper'
    to a bolt.Flags instance that can be used for decoding the flags and
    'flags_to_children' to an OrderedDict that maps flag names to child
    attribute names. The order of this dict is the order in which the children
    will be read and written. Finally, you need to set 'child_loader' to an
    instance of the correct class for your class type. Note that you have to do
    this last part inside __init__, as it is an instance variable."""
    # Abstract - to be set by subclasses
    flags_attr = 'fragment_flags'
    flags_mapper = None
    flags_to_children = OrderedDict()
    child_loader = None

    def load_data(self, component, ins):
        # Load the regular attributes first
        super(AFixedContainer, self).load_data(component, ins)
        # Then, process the flags and decode them
        child_flags = self.__class__.flags_mapper(
            getattr(component, self.__class__.flags_attr))
        setattr(component, self.__class__.flags_attr, child_flags)
        # Finally, inspect the flags and load the appropriate children. We must
        # always load and dump these in the exact order specified by the
        # subclass!
        is_flag_set = child_flags.__getattr__
        set_child = component.__setattr__
        new_child = self.child_loader.make_new
        load_child = self.child_loader.load_data
        for flag_attr, child_attr in \
                self.__class__.flags_to_children.iteritems():
            if is_flag_set(flag_attr):
                child = new_child()
                load_child(child, ins)
                set_child(child_attr, child)
            else:
                set_child(child_attr, None)

    def dump_data(self, component):
        # Update the flags first, then dump the regular attributes
        # Also use this chance to store the value of each present child
        children = []
        get_child = component.__getattribute__
        child_flags = getattr(component, self.__class__.flags_attr)
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
        out_data = super(AFixedContainer, self).dump_data(component)
        # Then, dump each child for which the flag is now set, in order
        dump_child = self.child_loader.dump_data
        for child in children:
            out_data += dump_child(child)
        return out_data

    @property
    def used_slots(self):
        return self.__class__.flags_to_children.values() + super(
            AFixedContainer, self).used_slots

    def get_size(self, component):
        child_size = self.child_loader.get_size
        total_size = super(AFixedContainer, self).get_size(component)
        get_child = component.__getattribute__
        return total_size + sum(
            child_size(get_child(child_attr))
            for child_attr in self.__class__.flags_to_children.itervalues())

class AVariableContainer(ABinaryComponent):
    """Abstract base class for components that contain a variable number of
    other components, with the count stored in a preceding integer. You need
    to specify a processor that sets an attribute named, by default,
    'fragment_count' to the right value (you can change the name using the
    class variable 'counter_attr'). Additionally, you have to set
    'child_loader' to an instance of the correct class for your child type.
    Note that you have to do this inside __init__, as it is an instance
    variable. The attribute name used for the list of children may also be
    customized via the class variable 'children_attr'."""
    # Abstract - to be set by subclasses
    child_loader = None
    children_attr = 'fragments'
    counter_attr = 'fragment_count'

    def load_data(self, component, ins):
        # Load the regular attributes first
        super(AVariableContainer, self).load_data(component, ins)
        # Then, load each child
        children = []
        new_child = self.child_loader.make_new
        load_child = self.child_loader.load_data
        append_child = children.append
        for x in xrange(getattr(component, self.__class__.counter_attr)):
            child = new_child()
            load_child(child, ins)
            append_child(child)
        setattr(component, self.__class__.children_attr, children)

    def dump_data(self, component):
        # Update the child count, then dump the regular attributes
        children = getattr(component, self.__class__.children_attr)
        setattr(component, self.__class__.counter_attr, len(children))
        out_data = super(AVariableContainer, self).dump_data(component)
        # Then, dump each child
        dump_child = self.child_loader.dump_data
        for child in children:
            out_data += dump_child(child)
        return out_data

    @property
    def used_slots(self):
        return [self.__class__.children_attr] + super(
            AVariableContainer, self).used_slots

    def get_size(self, component):
        child_size = self.child_loader.get_size
        total_size = super(AVariableContainer, self).get_size(component)
        children = getattr(component, self.__class__.children_attr)
        return total_size + sum(child_size(child) for child in children)
