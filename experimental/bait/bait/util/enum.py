# -*- coding: utf-8 -*-
#
# bait/util/enum.py
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <http://www.gnu.org/licenses/>.
#
#  Wrye Bash Copyright (C) 2011 Myk Taylor
#
# =============================================================================

# This file is based on example code in one of the responses at:
#   http://stackoverflow.com/questions/36932/whats-the-best-way-to-implement-an-enum-in-python
# I fleshed out the implementation, especially around FlagEnums and bitwise operators


import functools
import itertools
import logging


_logger = logging.getLogger(__name__)


class _EnumValue(object):
    def __init__(self, name, value, type_):
        self.__value = value
        self.__name = name
        self._type = type_
    def __str__(self):
        return self.__name
    def __repr__(self):
        return '{cls}({0!r},{1!r},{2})'.format(
            self.__name, self.__value, self._type.__name__, cls=type(self).__name__)
    def __hash__(self):
        return hash(self.__value)
    def __nonzero__(self):
        return bool(self.__value)
    def __cmp__(self, other):
        if isinstance(other, _EnumValue):
            if self._type is not other._type:
                raise TypeError("cannot compare enums of different types: %s, %s" % \
                             (self._type, other._type))
            return cmp(self.__value, other.__value)
        else:
            # hopefully they're the same type, but this still makes sense if they're not
            return cmp(self.__value, other)
    def __or__(self, other):
        if other is None:
            raise ValueError("cannot evaluate bitwise operator with None argument")
        self._validate_bitwise_operator_context(other)
        value = self.__value|other.__value
        if value == self.__value:
            return self
        if value == other.__value:
            return other
        if self.__value & other.__value == 0:
            return _EnumValue(
                '{0.name} | {1.name}'.format(self, other),
                self.__value|other.__value,
                self._type)
        return self._type.parse_value(value)
    def __ror__(self, other):
        return self.__or__(other)
    def __ior__(self, other):
        # do not change internal state of singleton enums!
        return self.__or__(other)
    def __and__(self, other):
        if other is None:
            raise ValueError("cannot evaluate bitwise operator with None argument")
        self._validate_bitwise_operator_context(other)
        value = self.__value & other.__value
        if value is self.__value:
            return self
        elif value is other.__value:
            return other
        return self._type.parse_value(value)
    def __rand__(self, other):
        return self.__and__(other)
    def __iand__(self, other):
        # do not change internal state of singleton enums!
        return self.__and__(other)
    def __xor__(self, other):
        if other is None:
            raise ValueError("cannot evaluate bitwise operator with None argument")
        self._validate_bitwise_operator_context(other)
        value = self.__value ^ other.__value
        if value is self.__value:
            return self
        elif value is other.__value:
            return other
        return self._type.parse_value(value)
    def __rxor__(self, other):
        return self.__xor__(other)
    def __ixor__(self, other):
        # do not change internal state of singleton enums!
        return self.__xor__(other)
    def __contains__(self, other):
        # note that the first enumerable (value == 0) is not "in" anything
        return bool(self&other)
    def __invert__(self):
        # this operation only makes sense for flag enums
        if not issubclass(self._type, FlagEnum):
            raise TypeError("incompatible type for FlagEnum bitwise operator: %s" % \
                            self._type.__name__)
        enumerables = self._type.__enumerables__
        return functools.reduce(
            _EnumValue.__or__,
            (enum for enum in enumerables.itervalues() if enum not in self))
    def __iter__(self):
        # this operation only makes sense for flag enums
        if not issubclass(self._type, FlagEnum):
            raise TypeError("incompatible type for FlagEnum iteration: %s" % \
                            self._type.__name__)
        value = self.__value
        if value != 0:
            for pos in itertools.count():
                if 0 == value: break
                lowBit = 0x1 & value
                value = value >> 1
                if 0x0 == lowBit:
                    continue
                yield self._type._parse_value(1 << pos)
    def _validate_bitwise_operator_context(self, other):
        if type(self) is not type(other):
            raise TypeError("cannot apply bitwise operator to non-enum: %s" % type(other))
        if not issubclass(self._type, FlagEnum):
            raise TypeError("incompatible type for FlagEnum bitwise operator: %s" % \
                            self._type.__name__)
        if not issubclass(other._type, FlagEnum):
            raise TypeError("incompatible type for FlagEnum bitwise operator: %s" % \
                            other._type.__name__)
    @property
    def name(self):
        return self.__name
    @property
    def value(self):
        return self.__value

class _EnumMeta(type):
    @staticmethod
    def __addToReverseLookup(rev, value, newKeys, nextIter, force=True):
        if value in rev:
            forced, items = rev.get(value, (force, ()))
            if forced and force: # value was forced, so just append
                combinedKeys = items + newKeys
                _logger.debug("adding reverse lookup: %s=%s",
                              str(value), str(combinedKeys))
                rev[value] = (True, combinedKeys)
            elif not forced: # move it to a new spot
                next = nextIter.next()
                _EnumMeta.__addToReverseLookup(rev, next, items, nextIter, False)
                _logger.debug("adding reverse lookup: %s=%s", str(value), str(newKeys))
                rev[value] = (force, newKeys)
            else: # not forcing this value
                next = nextIter.next()
                _EnumMeta.__addToReverseLookup(rev, next, newKeys, nextIter, False)
        else: # set it and forget it
            _logger.debug("adding reverse lookup: %s=%s", str(value), str(newKeys))
            rev[value] = (force, newKeys)
        return value

    def __init__(cls, name, bases, atts):
        classVars = vars(cls)
        enums = classVars.get('__enumerables__', None)
        nextIter = getattr(cls, '__nextitr__', itertools.count)()
        reverseLookup = {}
        values = {}

        if enums is not None:
            # build reverse lookup
            for item in enums:
                if isinstance(item, (tuple, list)):
                    items = list(item)
                    value = items.pop()
                    _logger.debug("adding forced value: %s=%s", str(value), str(items))
                    _EnumMeta.__addToReverseLookup(
                        reverseLookup, value, tuple(map(str,items)), nextIter)
                else:
                    value = nextIter.next()
                    # add it to the reverse lookup, but don't force it to that value
                    _logger.debug("adding non-forced value: %s=%s", str(value), str(item))
                    value = _EnumMeta.__addToReverseLookup(
                        reverseLookup, value, (str(item), ), nextIter, False)

            # build values and clean up reverse lookup
            for value, fkeys in reverseLookup.iteritems():
                f, keys = fkeys
                for key in keys:
                    enum = _EnumValue(key, value, cls)
                    _logger.debug("creating enum value: %s=%s", key, str(value))
                    setattr(cls, key, enum)
                    values[key] = enum
                reverseLookup[value] = \
                        tuple(val for val in values.itervalues() if val.value == value)
        setattr(cls, '__reverseLookup__', reverseLookup)
        setattr(cls, '__enumerables__', values)
        setattr(cls, '_Max', max([key for key in reverseLookup] or [0]))
        return super(_EnumMeta, cls).__init__(name, bases, atts)

    def __iter__(cls):
        for enum in cls.__enumerables__.itervalues():
            yield enum
    def parse_name(cls, name):
        return cls.__enumerables__.get(name, None)
    def parse_value(cls, value):
        if 0 == value or not issubclass(cls, FlagEnum):
            return cls._parse_value(value)
        retVal = None
        for pos in itertools.count():
            if 0 == value: break
            lowBit = 0x1 & value
            value = value >> 1
            if 0x0 == lowBit:
                continue
            flagVal = 1 << pos
            flagEnum = cls._parse_value(flagVal)
            if flagEnum is None:
                # don't allow invalid bits in our enums
                raise ValueError(
                    "invalid flag set for %s enum: 0x%x" % (cls.__name__, flagVal))
            if retVal is None: retVal = flagEnum
            else: retVal = retVal|flagEnum
        return retVal
    def _parse_value(cls, value):
        return cls.__reverseLookup__.get(value, (None, ))[0]

class Enum(object):
    __metaclass__ = _EnumMeta
    __enumerables__ = None

class FlagEnum(Enum):
    @staticmethod
    def __nextitr__():
        yield 0
        for val in itertools.count():
            yield 1 << val


def make_enum(name, *args):
    return _EnumMeta(name, (Enum, ), dict(__enumerables__=args))

def make_flag_enum(name, *args):
    return _EnumMeta(name, (FlagEnum, ), dict(__enumerables__=args))
