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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from collections import OrderedDict
from ..bolt import LowerDict, DefaultLowerDict, OrderedLowerDict

class TestLowerDict(object):
    dict_type = LowerDict

    def test___delitem__(self):
        a = self.dict_type()
        a.update(dict(sape=4139, guido=4127, jack=4098))
        del a[u'sAPe']
        assert u'sape' not in a
        del a[u'GUIDO']
        assert u'guido' not in a

    def test___getitem__(self):
        a = self.dict_type(dict(sape=4139, guido=4127, jack=4098))
        assert a[u'sape'] == 4139
        assert a[u'SAPE'] == 4139
        assert a[u'SAPe'] == 4139

    def test___init__(self):
        a = self.dict_type(dict(sape=4139, guido=4127, jack=4098))
        b = self.dict_type(sape=4139, guido=4127, jack=4098)
        c = self.dict_type([(u'sape', 4139), (u'guido', 4127),
                            (u'jack', 4098)])
        d = self.dict_type(c)
        e = self.dict_type(c, sape=4139, guido=4127, jack=4098)
        f = e.copy()
        del f[u'JACK']
        f = self.dict_type(f, jack=4098)
        assert a == b
        assert a == c
        assert a == d
        assert a == e
        assert a == f

    def test___setitem__(self):
        a = self.dict_type()
        a[u'sape'] = 4139
        assert a[u'sape'] == 4139
        assert a[u'SAPE'] == 4139
        assert a[u'SAPe'] == 4139
        a[u'sape'] = u'None'
        assert a[u'sape'] == u'None'
        assert a[u'SAPE'] == u'None'
        assert a[u'SAPe'] == u'None'

    def test_fromkeys(self):
        a = self.dict_type(dict(sape=4139, guido=4139, jack=4139))
        c = self.dict_type.fromkeys([u'sape', u'guido', u'jack'], 4139)
        assert a == c
        c = self.dict_type.fromkeys([u'sApe', u'guIdo', u'jaCK'], 4139)
        assert a == c

    def test_get(self):
        a = self.dict_type(dict(sape=4139, guido=4127, jack=4098))
        assert a.get(u'sape') == 4139
        assert a.get(u'SAPE') == 4139
        assert a.get(u'SAPe') == 4139

    def test_setdefault(self):
        a = self.dict_type()
        a[u'sape'] = 4139
        assert a.setdefault(u'sape') == 4139
        assert a.setdefault(u'SAPE') == 4139
        assert a.setdefault(u'SAPe') == 4139
        assert a.setdefault(u'GUIDO', 4127) == 4127
        assert a.setdefault(u'guido') == 4127
        assert a.setdefault(u'GUido') == 4127

    def test_pop(self):
        a = self.dict_type()
        a[u'sape'] = 4139
        assert a[u'sape'] == 4139
        assert a[u'SAPE'] == 4139
        assert a[u'SAPe'] == 4139

    def test_update(self):
        a = self.dict_type()
        a.update(dict(sape=4139, guido=4127, jack=4098))
        assert a[u'sape'] == 4139
        assert a[u'SAPE'] == 4139
        assert a[u'guido'] == 4127
        assert a[u'GUido'] == 4127

    def test___repr__(self):
        a = self.dict_type()
        a.update(dict(sape=4139, guido=4127, jack=4098))
        # Needed for the eval below, not unused!
        from ..bolt import CIstr
        assert eval(repr(a)) == a

class TestDefaultLowerDict(TestLowerDict):
    dict_type = DefaultLowerDict

    def test___init__(self):
        a = self.dict_type(LowerDict, dict(sape=4139, guido=4127, jack=4098))
        b = self.dict_type(LowerDict, sape=4139, guido=4127, jack=4098)
        c = self.dict_type(LowerDict, [(u'sape', 4139), (u'guido', 4127),
                                       (u'jack', 4098)])
        d = self.dict_type(LowerDict, c)
        e = self.dict_type(LowerDict, c, sape=4139, guido=4127, jack=4098)
        f = e.copy()
        assert a == b
        assert a == c
        assert a == d
        assert a == e
        assert a == f

    def test___getitem__(self):
        a = self.dict_type(LowerDict, dict(sape=4139, guido=4127, jack=4098))
        assert a[u'sape'] == 4139
        assert a[u'SAPE'] == 4139
        assert a[u'SAPe'] == 4139
        assert a[u'NEW_KEY'] == LowerDict()

    def test_get(self):
        a = self.dict_type(int, dict(sape=4139, guido=4127, jack=4098))
        assert a.get(u'sape') == 4139
        assert a.get(u'SAPE') == 4139
        assert a.get(u'SAPe') == 4139
        assert a.get(u'NEW_KEY') == None

    def test_fromkeys(self):
        # see: defaultdict.fromkeys should accept a callable factory:
        # https://bugs.python.org/issue23372 (rejected)
        a = self.dict_type(int, dict(sape=4139, guido=4139, jack=4139))
        c = self.dict_type.fromkeys([u'sape', u'guido', u'jack'], 4139)
        assert a == c # !!!
        c = self.dict_type.fromkeys([u'sApe', u'guIdo', u'jaCK'], 4139)
        assert a == c # !!!

class TestOrderedLowerDict(TestLowerDict):
    dict_type = OrderedLowerDict

    def test___init__(self):
        # Using dict here would discard order!
        ao = OrderedDict()
        ao[u'sape'] = 4193
        ao[u'guido'] = 4127
        ao[u'jack'] = 4098
        a = self.dict_type(ao)
        b = OrderedLowerDict()
        b[u'sape'] = 4193
        b[u'guido'] = 4127
        b[u'jack'] = 4098
        assert a == b
        # Order differs, so these are unequal
        c = OrderedLowerDict()
        b[u'sape'] = 4193
        b[u'jack'] = 4098
        b[u'guido'] = 4127
        assert a != c
        assert b != c

    def test_fromkeys(self):
        # Using dict here would discard order!
        a = self.dict_type()
        a[u'sape'] = a[u'guido'] = a[u'jack'] = 4139
        c = self.dict_type.fromkeys([u'sape', u'guido', u'jack'], 4139)
        assert a == c
        c = self.dict_type.fromkeys([u'sApe', u'guIdo', u'jaCK'], 4139)
        assert a == c

    def test_keys(self):
        a = self.dict_type([(u'sape', 4139), (u'guido', 4127),
                            (u'jack', 4098)])
        assert a.keys() == [u'sape', u'guido', u'jack']
