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
import copy

import pytest

from ..bolt import LowerDict, DefaultLowerDict, OrderedLowerDict, decoder, \
    encode, getbestencoding, GPath, Path, Rounder, SigToStr, StrToSig, \
    LooseVersion, FName, FNDict, os_name, CIstr, GPath_no_norm, DefaultFNDict

def test_getbestencoding():
    """Tests getbestencoding. Keep this one small, we don't want to test
    chardet here."""
    # These two are correct, but...
    assert getbestencoding(b'\xe8\xad\xa6\xe5\x91\x8a')[0] == u'utf8'
    assert getbestencoding(b'\xd0\x92\xd0\xbd\xd0\xb8\xd0\xbc\xd0\xb0\xd0\xbd'
                           b'\xd0\xb8\xd0\xb5')[0] == u'utf8'
    # chardet not confident enough to say - this is Windows-932
    assert getbestencoding(b'\x8cx\x8d\x90')[0] == None
    # Wrong - this is GBK, not ISO-8859-1!
    assert getbestencoding(b'\xbe\xaf\xb8\xe6')[0] == u'ISO-8859-1'
    # Since chardet 5.0, detected correctly as Windows-1251 - before 5.0 it got
    # wrongly detected as MacCyrillic
    assert getbestencoding(b'\xc2\xed\xe8\xec\xe0\xed\xe8'
                           b'\xe5')[0] == 'cp1251'

class TestDecoder(object):
    def test_decoder_basics(self):
        """Tests basic decoding in various languages and encodings."""
        # Chinese & Japanese (UTF-8)
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a') == u'警告'
        # Chinese (GBK), but gets autodetected as ISO-8859-1
        assert decoder(b'\xbe\xaf\xb8\xe6') != u'警告'
        # Japanese (Windows-932), but chardet isn't confident enough to tell,
        # so we run through our encodingOrder and GBK happens to not error
        assert decoder(b'\x8cx\x8d\x90') == u'寈崘'
        # English (ASCII)
        assert decoder(b'Warning') == u'Warning'
        # German (ASCII)
        assert decoder(b'Warnung') == u'Warnung'
        # German (Windows-1252)
        assert decoder(b'\xc4pfel') == u'Äpfel'
        # Portuguese (UTF-8)
        assert decoder(b'Aten\xc3\xa7\xc3\xa3o') == u'Atenção'
        # Russian (UTF-8)
        assert decoder(b'\xd0\x92\xd0\xbd\xd0\xb8\xd0\xbc\xd0\xb0\xd0\xbd\xd0'
                       b'\xb8\xd0\xb5') == 'Внимание'
        # Russian (Windows-1251), before chardet 5.0 this got wrongly detected
        # as MacCyrillic
        assert decoder(b'\xc2\xed\xe8\xec\xe0\xed\xe8\xe5') == 'Внимание'

    def test_decoder_encoding(self):
        """Tests the 'encoding' parameter of decoder."""
        # UTF-8-encoded 'Warning' in Chinese, fed to various encodings
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                       encoding='ascii') == '警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                       encoding='gbk') == '璀﹀憡'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                       encoding='cp932') == '警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                       encoding='cp949') == '警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                       encoding='cp1252') == 'è\xad¦å‘Š'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                       encoding='utf8') == '警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                       encoding='cp500') == 'YÝwVj«'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                       encoding='UTF-16LE') == '귨誑'
        # Bad detections from above, with the correct encoding
        assert decoder(b'\x8cx\x8d\x90', encoding='cp932') == '警告'
        assert decoder(b'\xbe\xaf\xb8\xe6', encoding='gbk') == '警告'
        # This one works since chardet 5.0, still keeping it here just in case
        assert decoder(b'\xc2\xed\xe8\xec\xe0\xed\xe8\xe5',
                       encoding='cp1251') == 'Внимание'

    def test_decoder_avoidEncodings(self):
        """Tests the 'avoidEncodings' parameter of decoder."""
        # UTF-8-encoded 'Warning' in Chinese, fed to various encodings
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                       avoidEncodings=('ascii',)) == '警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                       avoidEncodings=('gbk',)) == '警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                       avoidEncodings=('cp932',)) == '警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                       avoidEncodings=('cp949',)) == '警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                       avoidEncodings=('cp1252',)) == '警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                       avoidEncodings=('utf8',)) == '璀﹀憡'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                       avoidEncodings=('cp500',)) == '警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                       avoidEncodings=('UTF-16LE',)) == '警告'
        # Bad detections from above - this one works now...
        assert decoder(b'\xbe\xaf\xb8\xe6',
                       avoidEncodings=('ISO-8859-1',)) == '警告'

    def decode_already_decoded(self):
        """Tests if passing in a unicode string doesn't try any decoding."""
        assert decoder(u'警告') == u'警告' # Chinese & Japanese
        assert decoder(u'Warning') == u'Warning' # English
        assert decoder(u'Warnung') == u'Warnung' # German
        assert decoder(u'Attenzione') == u'Attenzione' # Italian
        assert decoder(u'Atenção') == u'Atenção' # Portuguese
        assert decoder(u'Внимание') == u'Внимание' # Russian
        assert decoder(None) is None

class TestEncode(object):
    def test_encode_basics(self):
        """Tries encoding a bunch of words and checks the chosen encoding to
        see if it's sensible."""
        # Chinese & Japanese -> UTF-8
        assert encode(u'警告', returnEncoding=True) == (
            b'\xe8\xad\xa6\xe5\x91\x8a', u'utf8')
        # English -> ASCII
        assert encode(u'Warning', returnEncoding=True) == (
            b'Warning', u'ascii')
        # German -> ASCII or Windows-1252, depending on umlauts etc.
        assert encode(u'Warnung', returnEncoding=True) == (
            b'Warnung', u'ascii')
        assert encode(u'Äpfel', returnEncoding=True) == (
            b'\xc4pfel', u'cp1252')
        # Portuguese -> UTF-8
        assert encode(u'Atenção', returnEncoding=True) == (
            b'Aten\xc3\xa7\xc3\xa3o', u'utf8')
        # Russian -> UTF-8
        assert encode(u'Внимание', returnEncoding=True) == (
            b'\xd0\x92\xd0\xbd\xd0\xb8\xd0\xbc\xd0\xb0\xd0\xbd\xd0\xb8\xd0'
            b'\xb5', u'utf8')

    def test_encode_firstEncoding(self):
        """Tests the 'firstEncoding' parameter of encode."""
        # Chinese & Japanese ->  UTF-8, Windows-932 & GBK
        assert encode(u'警告',
                      firstEncoding=u'utf8') == b'\xe8\xad\xa6\xe5\x91\x8a'
        assert encode(u'警告', firstEncoding=u'gbk') == b'\xbe\xaf\xb8\xe6'
        assert encode(u'警告', firstEncoding=u'cp932') == b'\x8cx\x8d\x90'
        # Russian -> UTF-8 & Windows-1251
        assert encode(u'Внимание', firstEncoding=u'utf8') == (
            b'\xd0\x92\xd0\xbd\xd0\xb8\xd0\xbc\xd0\xb0\xd0\xbd\xd0\xb8\xd0'
            b'\xb5')
        assert encode(u'Внимание', firstEncoding=u'cp1251') == (
            b'\xc2\xed\xe8\xec\xe0\xed\xe8\xe5')

def test_decoder_encode_roundtrip():
    """Tests that de/encode preserves roundtrip de/encoding."""
    for s in (u'警告', u'Warning', u'Warnung', u'Äpfel', u'Attenzione',
              u'Atenção', u'Внимание'):
        assert decoder(encode(s)) == s

# encode/decode dicts
class TestSigToStr:

    def test___missing__(self):
        sigtostr = SigToStr()
        assert sigtostr[b'TES4'] == 'TES4'
        assert sigtostr[b'\x00IAD'] == '\0IAD' # game/falloutnv/records.py:473
        # other values just pass through - use in f'{val}'but not in join(vals)
        assert sigtostr[42] == 42
        assert sigtostr['42'] == '42'

class TestStrToSig:

    def test___missing__(self):
        strtosig = StrToSig()
        assert strtosig['TES4'] == b'TES4'
        assert strtosig['\x00IAD'] == b'\x00IAD'
        with pytest.raises(AttributeError): strtosig[42]
        with pytest.raises(AttributeError): strtosig[b'42']

class TestLowerDict(object):
    dict_type = LowerDict
    key_type = CIstr
    dict_arg = dict(sape=4139, guido=4127, jack=4098)

    def test___delitem__(self):
        a = self.dict_type()
        a.update(dict(sape=4139, guido=4127, jack=4098))
        del a['sAPe']
        assert 'sape' not in a
        del a['GUIDO']
        assert 'guido' not in a

    def test___getitem__(self):
        a = self.dict_type(self.dict_arg)
        assert a['sape'] == 4139
        assert a['SAPE'] == 4139
        assert a['SAPe'] == 4139
    def test___init__(self):
        assert list(self.dict_arg) == ['sape', 'guido', 'jack'] # assert py >= 3.7
        a = self.dict_type(self.dict_arg)
        b = self.dict_type(sape=4139, guido=4127, jack=4098)
        c = self.dict_type([('sape', 4139), ('guido', 4127),
                            ('jack', 4098)])
        d = self.dict_type(c)
        e = self.dict_type(c, sape=4139, guido=4127, jack=4098)
        f = e.copy()
        del f['JACK']
        f = self.dict_type(f, jack=4098)
        assert a == b
        assert a == c
        assert a == d
        assert a == e
        assert a == f

    def test___setitem__(self):
        a = self.dict_type()
        a['sape'] = 4139
        assert a['sape'] == 4139
        assert a['SAPE'] == 4139
        assert a['SAPe'] == 4139
        a['sape'] = 'None'
        assert a['sape'] == 'None'
        assert a['SAPE'] == 'None'
        assert a['SAPe'] == 'None'

    def test_fromkeys(self):
        a = self.dict_type(dict.fromkeys(self.dict_arg, 4139))
        c = self.dict_type.fromkeys(self.dict_arg, 4139)
        assert a == c
        c = self.dict_type.fromkeys(['sApe', 'guIdo', 'jaCK'], 4139)
        assert a == c
        assert type(c) is self.dict_type

    def test_get(self):
        a = self.dict_type(self.dict_arg)
        assert a.get('sape') == 4139
        assert a.get('SAPE') == 4139
        assert a.get('SAPe') == 4139

    def test_setdefault(self):
        a = self.dict_type()
        a['sape'] = 4139
        assert a.setdefault('sape') == 4139
        assert a.setdefault('SAPE') == 4139
        assert a.setdefault('SAPe') == 4139
        assert a.setdefault('GUIDO', 4127) == 4127
        assert a.setdefault('guido') == 4127
        assert a.setdefault('GUido') == 4127

    def test_pop(self):
        a = self.dict_type()
        a['sape'] = 4139
        assert a['sape'] == 4139
        assert a['SAPE'] == 4139
        assert a['SAPe'] == 4139

    def test_update(self):
        a = self.dict_type()
        a.update(dict(sape=4139, guido=4127, jack=4098))
        assert a['sape'] == 4139
        assert a['SAPE'] == 4139
        assert a['guido'] == 4127
        assert a['GUido'] == 4127

    def test___repr__(self):
        a = self.dict_type()
        a.update(dict(sape=4139, guido=4127, jack=4098))
        # Needed for the eval below, not unused!
        from ..bolt import CIstr
        assert eval(repr(a)) == a

    def test_key_type(self):
        d = self.dict_type({'key': 'val'})
        assert type(list(d)[0]) is self.key_type

class TestDefaultLowerDict(TestLowerDict):
    dict_type = DefaultLowerDict

    def test___init__(self):
        a = self.dict_type(LowerDict, dict(sape=4139, guido=4127, jack=4098))
        b = self.dict_type(LowerDict, sape=4139, guido=4127, jack=4098)
        c = self.dict_type(LowerDict, [('sape', 4139), ('guido', 4127),
                                       ('jack', 4098)])
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
        assert a['sape'] == 4139
        assert a['SAPE'] == 4139
        assert a['SAPe'] == 4139
        assert a['NEW_KEY'] == LowerDict()

    def test_get(self):
        a = self.dict_type(int, dict(sape=4139, guido=4127, jack=4098))
        assert a.get('sape') == 4139
        assert a.get('SAPE') == 4139
        assert a.get('SAPe') == 4139
        assert a.get('NEW_KEY') == None

    def test_fromkeys(self):
        # see: defaultdict.fromkeys should accept a callable factory:
        # https://github.com/python/cpython/issues/67561 (rejected)
        a = self.dict_type(int, dict(sape=4139, guido=4139, jack=4139))
        c = self.dict_type.fromkeys(['sape', 'guido', 'jack'], 4139)
        assert a == c # !!!
        c = self.dict_type.fromkeys(['sApe', 'guIdo', 'jaCK'], 4139)
        assert a == c # !!!

    def test_key_type(self):
        d = self.dict_type(None, {'key': 'val'})
        assert type(list(d)[0]) is self.key_type

class TestOrderedLowerDict(TestLowerDict):
    dict_type = OrderedLowerDict

    def test___init__(self):
        super(TestOrderedLowerDict, self).test___init__()
        a = self.dict_type(self.dict_arg)
        b = OrderedLowerDict()
        b['sape'] = 4139
        b['guido'] = 4127
        b['jack'] = 4098
        assert a == b
        # Order differs, so these are unequal
        c = OrderedLowerDict()
        c['sape'] = 4139
        c['jack'] = 4098
        c['guido'] = 4127
        assert a != c
        assert b != c

    def test_keys(self):
        a = self.dict_type([('sape', 4139), ('guido', 4127),
                            ('jack', 4098)])
        assert list(a) == ['sape', 'guido', 'jack']

class TestStringLike:

    def test_std_strings(self):
        # reminder
        assert 'abc' != b'abc'
        for other in (b'', [], [1], None, True, False, 55):
            assert '' != other

    def test__le__(self):
        # reminder
        with pytest.raises(TypeError): assert ('' <= b'')
        with pytest.raises(TypeError): assert ('123' <= b'123')
        with pytest.raises(TypeError): assert (None <= '')
        with pytest.raises(TypeError): assert not ('' <= [])
        with pytest.raises(TypeError): assert not ('' <= [1])
        with pytest.raises(TypeError): assert not ('' <= None)
        with pytest.raises(TypeError): assert not ('' <= True)
        with pytest.raises(TypeError): assert not ('' <= 55)

class TestPath(object):
    """Path's odds and ends."""

    def test__eq__(self):
        # paths and unicode
        p = GPath('c:/random/path.txt')
        assert 'c:/random/path.txt' == p
        if os_name == 'nt':
            assert r'c:\random\path.txt' == p
            assert GPath(r'c:\random\path.txt') == p
        assert GPath('c:/random/path.txt') == p
        # paths and bytes
        with pytest.raises(TypeError): assert b'c:/random/path.txt' == p
        with pytest.raises(TypeError): assert p == b'c:/random/path.txt'
        with pytest.raises(SyntaxError):
            eval(r"assert b'' r'c:\random\path.txt' == p")
        assert GPath(b'c:/random/path.txt') != p
        with pytest.raises(SyntaxError):
            eval(r"assert GPath(b'' r'c:\random\path.txt') == p")
        # paths and None
        assert not (None == p)
        # test comp with Falsy - previously assertions passed
        with pytest.raises(TypeError): assert not (p == [])
        with pytest.raises(TypeError): assert not (p == False)
        with pytest.raises(TypeError): assert not (p == [1])
        # Falsy and "empty" Path
        empty = GPath('')
        assert empty == Path('')
        assert empty == ''
        with pytest.raises(TypeError): assert empty == b''
        with pytest.raises(TypeError): assert b'' == empty
        assert not (None == empty)
        with pytest.raises(TypeError): assert empty == []
        with pytest.raises(TypeError): assert empty == False
        with pytest.raises(TypeError): assert not (empty == [1])

    def test__le__(self):
        # paths and unicode
        p = GPath('c:/random/path.txt')
        assert 'c:/random/path.txt' <= p
        if os_name == 'nt':
            assert r'c:\random\path.txt' <= p
            assert GPath(r'c:\random\path.txt') <= p
        assert GPath('c:/random/path.txt') <= p
        # paths and bytes
        with pytest.raises(TypeError): assert b'c:/random/path.txt' <= p
        with pytest.raises(SyntaxError):
            eval(r"assert b'' r'c:\random\path.txt' <= p")
        with pytest.raises(TypeError): assert GPath(b'c:/random/path.txt') <= p
        with pytest.raises(SyntaxError):
            eval(r"assert GPath(b'' r'c:\random\path.txt') <= p")
        # test comp with None
        with pytest.raises(TypeError): assert (None <= p)
        # unrelated types - previously assertions passed
        with pytest.raises(TypeError): assert not (p <= [])
        with pytest.raises(TypeError): assert not (p <= False)
        with pytest.raises(TypeError): assert not (p <= [1])
        # Falsy and "empty" Path
        empty = GPath('')
        assert empty <= Path('')
        assert empty <= ''
        with pytest.raises(TypeError): assert empty <= b''
        with pytest.raises(TypeError): assert (None <= p)
        with pytest.raises(TypeError): assert not (p <= None)
        with pytest.raises(TypeError): assert empty <= []
        with pytest.raises(TypeError): assert empty <= False
        with pytest.raises(TypeError): assert not (empty <= [1])

    def test_dict_keys(self):
        d = {GPath('c:/random/path.txt'): 1}
        if os_name == 'nt':
            assert not ('c:/random/path.txt' in d) ## oops
            assert r'c:\random\path.txt' in d
            assert GPath(r'c:\random\path.txt') in d
        assert GPath('c:/random/path.txt') in d
        dd = {'c:/random/path.txt': 1}
        if os_name == 'nt': assert not GPath('c:/random/path.txt') in dd
        assert not GPath(r'c:\random\path.txt') in dd

class TestRounder(object):

    def test__eq__(self):
        # would be different if we actually rounded
        assert Rounder(1.0000017) == Rounder(1.0000014)
        # system mtimes check
        assert Rounder(1618840002.5121067) == Rounder(1618840002.512106)
        rounder_5th = Rounder(1.00001)
        assert rounder_5th == 1.00001
        assert rounder_5th != 1.000
        assert rounder_5th != Rounder(1.000)
        assert rounder_5th == Rounder(1.00001)
        rounder_6th = Rounder(1.000001)
        assert rounder_6th == 1.000
        assert rounder_6th == Rounder(1)
        assert rounder_6th == 1
        # cross type comparisons - TODO: py3 may raise?
        assert rounder_5th != b'123'
        assert not (rounder_5th == [])
        assert not (rounder_5th == [1])
        assert not (rounder_5th == None)
        assert not (rounder_5th == True)
        assert not (rounder_5th == 55)

class TestLooseVersion:
    def test_repr(self):
        """Tests that parsing and __repr__ work correctly."""
        assert repr(LooseVersion('1.0')) == '1.0'
        assert repr(LooseVersion('1-0')) == '1.0'
        assert repr(LooseVersion('a.b.c')) == 'a.b.c'
        # Watch out - we treat this as a separate component, hence it looks
        # like this (that's correct, though it may be surprising at first)
        assert repr(LooseVersion('1.2.2.alpha1')) == '1.2.2.alpha.1'
        assert repr(LooseVersion('1.0-rc1+')) == '1.0.rc.1.+'
        # Unicode should work fine too
        assert repr(LooseVersion('0.9-ä-⻨-❓')) == '0.9.ä.⻨.❓'
        assert repr(LooseVersion('0.9-ä⻨❓')) == '0.9.ä⻨❓'

    def test_eq(self):
        """Tests that __eq__ (and __ne__, by extension) work correctly."""
        assert LooseVersion('1.0') != LooseVersion('1.1')
        assert LooseVersion('1.0') == LooseVersion('1.0')
        assert LooseVersion('1.1') != LooseVersion('1.0')
        # Test with alphabetic characters and a length mismatch too
        assert LooseVersion('1.1') != LooseVersion('1.1a')
        assert LooseVersion('1.1a') == LooseVersion('1.1a')
        assert LooseVersion('1.1a') != LooseVersion('1.1')

    def test_lt(self):
        """Tests that __lt__ works correctly."""
        assert LooseVersion('1.0') < LooseVersion('1.1')
        assert not (LooseVersion('1.0') < LooseVersion('1.0'))
        assert not (LooseVersion('1.1') < LooseVersion('1.0'))
        # Test with alphabetic characters and a length mismatch too
        assert LooseVersion('1.1') < LooseVersion('1.1a')
        assert not (LooseVersion('1.1a') < LooseVersion('1.1a'))
        assert not (LooseVersion('1.1a') < LooseVersion('1.1'))

    def test_le(self):
        """Tests that __le__ works correctly."""
        assert LooseVersion('1.0') <= LooseVersion('1.1')
        assert LooseVersion('1.0') <= LooseVersion('1.0')
        assert not (LooseVersion('1.1') <= LooseVersion('1.0'))
        # Test with alphabetic characters and a length mismatch too
        assert LooseVersion('1.1') <= LooseVersion('1.1a')
        assert LooseVersion('1.1a') <= LooseVersion('1.1a')
        assert not (LooseVersion('1.1a') <= LooseVersion('1.1'))

    def test_gt(self):
        """Tests that __gt__ works correctly."""
        assert not (LooseVersion('1.0') > LooseVersion('1.1'))
        assert not (LooseVersion('1.0') > LooseVersion('1.0'))
        assert LooseVersion('1.1') > LooseVersion('1.0')
        # Test with alphabetic characters and a length mismatch too
        assert not (LooseVersion('1.1') > LooseVersion('1.1a'))
        assert not (LooseVersion('1.1a') > LooseVersion('1.1a'))
        assert LooseVersion('1.1a') > LooseVersion('1.1')

    def test_ge(self):
        """Tests that __ge__ works correctly."""
        assert not (LooseVersion('1.0') >= LooseVersion('1.1'))
        assert LooseVersion('1.0') >= LooseVersion('1.0')
        assert LooseVersion('1.1') >= LooseVersion('1.0')
        # Test with alphabetic characters and a length mismatch too
        assert not (LooseVersion('1.1') >= LooseVersion('1.1a'))
        assert LooseVersion('1.1a') >= LooseVersion('1.1a')
        assert LooseVersion('1.1a') >= LooseVersion('1.1')

    def test_not_implemented(self):
        """Tests that comparing LooseVersion with incompatible types raises
        errors (or returns False for __eq__/__ne__)."""
        assert not (LooseVersion('1.0') == 'foo')
        assert LooseVersion('1.0') != 'foo'
        with pytest.raises(TypeError): assert LooseVersion('1.0') < 'foo'
        with pytest.raises(TypeError): assert LooseVersion('1.0') <= 'foo'
        with pytest.raises(TypeError): assert LooseVersion('1.0') > 'foo'
        with pytest.raises(TypeError): assert LooseVersion('1.0') >= 'foo'

class TestFname(object):
    """Fname vs Paths, strings and bytes."""

    def test__eq__(self):
        assert (fn := FName('path.txt')) == FName('Path.txt')
        assert FName('path.txt') is fn # note they are identical
        # fname and unicode strings
        assert 'path.txt' == fn
        assert 'Path.txt' == fn
        # fname and bytes
        with pytest.raises(TypeError): assert b'path.txt' != fn
        # fname and paths
        with pytest.raises(TypeError): assert fn == GPath('path.txt')
        with pytest.raises(TypeError): assert GPath('Path.txt') == fn
        # fname and CIstr
        assert fn == CIstr('Path.txt')
        assert CIstr('Path.txt') == fn
        assert fn == CIstr('pAth.txt')
        # fname and None
        assert not (None == fn)
        # test comp with Falsy/other types
        for other in (b'', [], [1], True, False, 55):
            with pytest.raises(TypeError): assert fn != other
        # Falsy and "empty" FName
        empty = FName('')
        assert FName('') is empty
        assert not empty
        assert empty == ''
        with pytest.raises(TypeError): assert empty != GPath('')
        for other in (b'', [], [1], True, False, 55):
            with pytest.raises(TypeError): assert empty != other
        assert not (None == empty)
        assert not (empty == None)
        assert not (empty is None)

    def test__le__(self):
        # fnames and unicode
        fn = FName('path.txt')
        assert 'path.txt' <= fn
        with pytest.raises(TypeError): assert GPath('path.txt') <= fn
        # fnames and bytes
        with pytest.raises(TypeError): assert b'path.txt' <= fn
        # unrelated types - previously assertions passed
        with pytest.raises(TypeError): assert not (fn <= [])
        with pytest.raises(TypeError): assert not (fn <= [1])
        with pytest.raises(TypeError): assert not (fn <= False)
        with pytest.raises(TypeError): assert (None <= fn)
        with pytest.raises(TypeError): assert not (fn <= None)
        # Falsy and "empty" FName
        empty = FName('')
        with pytest.raises(TypeError): assert empty <= Path('')
        with pytest.raises(TypeError): assert Path('') <= empty
        assert empty <= ''
        with pytest.raises(TypeError): assert empty <= b''
        with pytest.raises(TypeError): assert empty <= []
        with pytest.raises(TypeError): assert not (empty <= [1])
        with pytest.raises(TypeError): assert empty <= False
        with pytest.raises(TypeError): assert (None <= empty)

    def test_fn_ext(self):
        file_str = 'path.txt'
        FILE_STR = file_str.upper()
        assert (FN := FName(FILE_STR)) == (fn := FName(file_str))
        assert FN.fn_ext == fn.fn_ext
        assert FName('PATH.txt').fn_ext is fn.fn_ext
        assert fn.fn_ext == '.txt'
        assert fn.fn_ext == '.TXT'
        assert not FName('').fn_ext
        assert not FName('path').fn_ext

    def test_fn_body(self):
        file_str = 'path.txt'
        FILE_STR = file_str.upper()
        assert (FN := FName(FILE_STR)) == (fn := FName(file_str))
        assert FN.fn_body == fn.fn_body
        assert FName('path.TXT').fn_body is fn.fn_body
        assert fn.fn_body == 'path'
        assert fn.fn_body == 'PATH'
        assert not FName('').fn_body
        assert not FName('.txt').fn_body

    def test_immutable__new__(self):
        a = FName('abc')
        b = FName('abc')
        assert a is b

    def test_lower(self):
        file_str = 'path.txt'
        FILE_STR = file_str.upper()
        assert (lo := ((FN := FName(FILE_STR)).lower())) == file_str
        assert lo is FN.lower() # immutable

    def test_copy(self):
        file_str = 'path.txt'
        fn = FName(file_str)
        assert copy.copy(fn) is copy.deepcopy(fn) is fn # immutable

    # Non unit tests ----------------------------------------------------------
    def test_gpath_on_fname(self):
        assert type(GPath(FName('Passes through os.path.normpath')).s) is str

    def test_gpath_no_norm_on_fname(self):
        assert type(GPath_no_norm(FName('Passes through!')).s) is FName ##: oopsie

    def test_path_join_fname(self):
        assert type(GPath('c:\\users\\mrd').join(FName('wrye')).s) is str

    def test_containers(self):
        """Test membership of FN's vs paths and strings in various container
        types - beware of hashed containers."""
        file_str = 'path.txt'
        FILE_STR = file_str.upper()
        assert (FN := FName(FILE_STR)) == (fn := FName(file_str))
        path = GPath(file_str)
        PATH = GPath(FILE_STR)
        containers = zip((set, list, dict), ({fn}, [fn], {fn: 1}),
                         ({file_str}, [file_str], {file_str: 1}))
        for cont_type, fn_cont, string_cont in containers:
            assert file_str in fn_cont
            if cont_type is set or cont_type is dict: ##: oopsie we need an FNDict!
                assert FILE_STR not in fn_cont
            else:
                assert FILE_STR in fn_cont
            assert FN in fn_cont # yey
            with pytest.raises(TypeError): assert path in fn_cont
            with pytest.raises(TypeError): assert PATH in fn_cont
            assert path in string_cont
            assert PATH in string_cont
            assert fn in string_cont
            assert FN in string_cont

class TestFNDict(TestLowerDict):
    dict_type = FNDict
    key_type = FName

class TestDefaultFNDict(TestDefaultLowerDict):
    dict_type = DefaultFNDict
    key_type = FName
