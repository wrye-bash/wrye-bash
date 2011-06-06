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
    e = Air.Oxygen | Air.Nitrogen | Air.Hydrogen
    eValue = e.Value
    assert e == Air.get_enum_by_value(eValue)

def enum_test():
    class Mammals(enum.Enum):
        __enumerables__ = ('Bat', 'Whale', ('Dog','Puppy',1), 'Cat')
    assert Mammals.Bat == Mammals.get_enum_by_name("Bat")
