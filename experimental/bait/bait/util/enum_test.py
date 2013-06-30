# -*- coding: utf-8 -*-
#
# bait/util/enum_test.py
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

from . import enum


def flag_enum_test():
    class Air(enum.FlagEnum):
        __enumerables__ = ('NoAir', 'Oxygen', 'Nitrogen', 'Hydrogen')
        # not required; just here so autocomplete works
        Oxygen = None
        Nitrogen = None
        Hydrogen = None

    assert "Oxygen" != Air.Oxygen
    assert "Oxygen" == Air.Oxygen.name
    assert "Oxygen" == str(Air.Oxygen)
    assert "Oxygen" == "%s" % Air.Oxygen
    assert 0 != Air.Oxygen
    assert Air.Oxygen
    assert bool(Air.Oxygen)
    assert 0 == Air.NoAir
    assert not bool(Air.NoAir)
    assert not Air.NoAir

    allAir = Air.Oxygen | Air.Nitrogen | Air.Hydrogen
    allValue = allAir.value
    assert allAir == Air.parse_value(allValue)

    assert Air.Oxygen ^ Air.Oxygen == Air.NoAir
    assert Air.Oxygen ^ Air.Oxygen == 0
    assert 0 == Air.Oxygen ^ Air.Oxygen
    assert Air.Oxygen ^ Air.NoAir == Air.Oxygen
    assert Air.NoAir ^ Air.Oxygen == Air.Oxygen

    assert Air.Oxygen & Air.Oxygen == Air.Oxygen
    assert Air.Oxygen in allAir
    assert Air.Oxygen in Air.Oxygen

    heavyAir = Air.Oxygen | Air.Nitrogen
    assert 3 == heavyAir
    assert Air.parse_value(5) != heavyAir
    assert Air.parse_value(3) == heavyAir
    try:
        dummy = Air.parse_value(10102)
        assert False
    except ValueError: pass
    assert Air.Hydrogen == ~heavyAir
    assert Air.Oxygen in heavyAir
    assert Air.Hydrogen not in heavyAir
    assert Air.Oxygen == heavyAir & Air.Oxygen
    assert allAir == heavyAir | Air.Hydrogen
    assert allAir == heavyAir ^ Air.Hydrogen
    assert allAir ^ heavyAir == Air.Hydrogen

    try:
        dummy = allAir & None
        assert False
    except ValueError: pass
    try:
        dummy = allAir | None
        assert False
    except ValueError: pass
    try:
        dummy = allAir ^ None
        assert False
    except ValueError: pass
    try:
        dummy = None & allAir
        assert False
    except ValueError: pass
    try:
        dummy = None | allAir
        assert False
    except ValueError: pass
    try:
        dummy = None ^ allAir
        assert False
    except ValueError: pass
    assert ~allAir == Air.NoAir

    # test iterations
    assert [elem for elem in allAir] == [Air.Oxygen, Air.Nitrogen, Air.Hydrogen]
    assert [elem for elem in Air.NoAir] == []
    assert [elem for elem in Air.Hydrogen] == [Air.Hydrogen]

    heavyAir |= Air.Hydrogen
    assert heavyAir == allAir
    heavyAir ^= Air.Hydrogen
    assert heavyAir != allAir
    assert heavyAir == Air.Oxygen | Air.Nitrogen
    heavyAir &= Air.Hydrogen
    assert heavyAir == 0

    assert Air.NoAir not in allAir

    for airType in Air:
        if airType is not Air.NoAir:
            assert airType in allAir

    # test identities
    heavyAir = Air.Oxygen | Air.Nitrogen
    assert heavyAir | Air.NoAir == heavyAir
    assert Air.NoAir | heavyAir == heavyAir
    assert heavyAir | heavyAir == heavyAir
    assert allAir | heavyAir == allAir

    # test overlapping values
    lightAir = Air.Hydrogen | Air.Nitrogen
    assert heavyAir.value | lightAir.value == allAir.value
    assert heavyAir | lightAir == allAir
    assert lightAir | heavyAir == allAir
    assert str(heavyAir|lightAir) == str(lightAir|heavyAir)


def enum_test():
    class Mammals(enum.Enum):
        __enumerables__ = ('Bat', 'Whale', ('Dog','Puppy',1), 'Cat')
    assert Mammals.Bat == Mammals.parse_name("Bat")
    assert Mammals.Dog == Mammals.Puppy
    assert Mammals.Dog != Mammals.Whale
    assert 0 <= repr(Mammals.Dog).index("Dog")
    assert 0 <= repr(Mammals.Dog).index("Mammals")

    mdict = {Mammals.Bat:Mammals.Cat}
    assert mdict[Mammals.Bat] == Mammals.Cat

    try:
        assert Mammals.Bat != Mammals.Bat | Mammals.Bat
        assert False
    except TypeError: pass
    try:
        assert Mammals.Bat != Mammals.Bat & Mammals.Bat
        assert False
    except TypeError: pass
    try:
        assert Mammals.Bat != Mammals.Bat ^ Mammals.Bat
        assert False
    except TypeError: pass

    try:
        dummy = ~Mammals.Bat
        assert False
    except TypeError: pass
    try:
        dummy = Mammals.Bat | 3
        assert False
    except TypeError: pass

    try:
        for elem in Mammals.Bat: pass
        assert False
    except TypeError: pass


def make_enum_test():
    enumClass = enum.make_enum("eclass", 'e1', 'e2', 'e3')
    assert "e2" == enumClass.e2.name
    assert enumClass.e2 == enumClass.parse_name("e2")

    flagEnumClass = enum.make_flag_enum("StubAir", 'NoAir', 'SomeAir', 'LotsaAir')

    try:
        dummy = flagEnumClass.SomeAir & enumClass.e2
        assert False
    except TypeError: pass
    assert enumClass.e3

    enumClass = enum.make_enum("eclass", ('e1',5), 'e2', ('e3',5))
    assert enumClass.e1 == enumClass.e3

    enumClass = enum.make_enum("eclass", ('e1',1), 'e2', 'e3')
    assert enumClass.e1 != enumClass.e2
    assert enumClass.e1 != enumClass.e3

    assert enum.make_enum("enum1", ('e1', 5)).e1 is not \
           enum.make_enum("enum1", ('e1', 5)).e1
    try:
        dummy = enum.make_enum("enum1", ('e1', 5)).e1 == \
                enum.make_enum("enum1", ('e1', 5)).e1
        assert False
    except TypeError: pass
