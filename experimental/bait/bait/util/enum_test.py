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

    heavyAir = Air.Oxygen | Air.Nitrogen
    assert 3 == heavyAir
    assert Air.parse_value(5) != heavyAir
    assert Air.parse_value(3) == heavyAir
    assert Air.parse_value(10102) is None
    assert Air.Hydrogen == ~heavyAir
    assert Air.Oxygen in heavyAir
    assert Air.Hydrogen not in heavyAir
    assert Air.Oxygen == heavyAir & Air.Oxygen
    assert allAir == heavyAir | Air.Hydrogen
    assert allAir == heavyAir ^ Air.Hydrogen
    assert allAir ^ heavyAir == Air.Hydrogen

    assert allAir & None is None
    assert allAir | None is None
    assert allAir ^ None is None


def enum_test():
    class Mammals(enum.Enum):
        __enumerables__ = ('Bat', 'Whale', ('Dog','Puppy',1), 'Cat')
    assert Mammals.Bat == Mammals.parse_name("Bat")
    assert Mammals.Dog == Mammals.Puppy
    assert Mammals.Dog != Mammals.Whale


def enum_enum_test():
    enumClass = enum.enum("eclass", ('e1', 'e2', 'e3'))
    assert "e2" == enumClass.e2.name
    assert enumClass.e2 == enumClass.parse_name("e2")