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
import pytest

from ..bolt import LowerDict, DefaultLowerDict, OrderedLowerDict, decoder, \
    encode, getbestencoding, GPath, Path, Rounder, SigToStr, StrToSig, \
    LooseVersion

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
    # Wrong - this is Windows-1251, not MacCyrillic!
    assert getbestencoding(b'\xc2\xed\xe8\xec\xe0\xed\xe8'
                           b'\xe5')[0] == u'MacCyrillic'

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
                      b'\xb8\xd0\xb5') == u'Внимание'
        # Russian (Windows-1251), but gets autodetected as MacCyrillic
        assert decoder(b'\xc2\xed\xe8\xec\xe0\xed\xe8\xe5') != u'Внимание'

    def test_decoder_encoding(self):
        """Tests the 'encoding' parameter of decoder."""
        # UTF-8-encoded 'Warning' in Chinese, fed to various encodings
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                      encoding=u'ascii') == u'警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                      encoding=u'gbk') == u'璀﹀憡'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                      encoding=u'cp932') == u'警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                      encoding=u'cp949') == u'警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                      encoding=u'cp1252') == u'è\xad¦å‘Š'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                      encoding=u'utf8') == u'警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                      encoding=u'cp500') == u'YÝwVj«'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                      encoding=u'UTF-16LE') == u'귨誑'
        # Bad detections from above, with the correct encoding
        assert decoder(b'\xbe\xaf\xb8\xe6', encoding=u'gbk') == u'警告'
        assert decoder(b'\x8cx\x8d\x90', encoding=u'cp932') == u'警告'
        assert decoder(b'\xc2\xed\xe8\xec\xe0\xed\xe8\xe5',
                      encoding=u'cp1251') == u'Внимание'

    def test_decoder_avoidEncodings(self):
        """Tests the 'avoidEncodings' parameter of avoidEncodings."""
        # UTF-8-encoded 'Warning' in Chinese, fed to various encodings
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                      avoidEncodings=(u'ascii',)) == u'警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                      avoidEncodings=(u'gbk',)) == u'警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                      avoidEncodings=(u'cp932',)) == u'警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                      avoidEncodings=(u'cp949',)) == u'警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                      avoidEncodings=(u'cp1252',)) == u'警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                      avoidEncodings=(u'utf8',)) == u'璀﹀憡'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                      avoidEncodings=(u'cp500',)) == u'警告'
        assert decoder(b'\xe8\xad\xa6\xe5\x91\x8a',
                      avoidEncodings=(u'UTF-16LE',)) == u'警告'
        # Bad detections from above - this one works now...
        assert decoder(b'\xbe\xaf\xb8\xe6',
                      avoidEncodings=(u'ISO-8859-1',)) == u'警告'
        # But this one still fails because GBK is next in line and happens to
        # not error when given those bytes. Even avoiding GBK does not help
        # because the only thing the 'avoidEncodings' parameter does is avoid
        # bad chardet detections.
        assert decoder(b'\xc2\xed\xe8\xec\xe0\xed\xe8\xe5',
                      avoidEncodings=(u'MacCyrillic',)) != u'Внимание'
        assert decoder(b'\xc2\xed\xe8\xec\xe0\xed\xe8\xe5',
                      avoidEncodings=(u'MacCyrillic', u'gbk')) != u'Внимание'

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

    def test___delitem__(self):
        a = self.dict_type()
        a.update(dict(sape=4139, guido=4127, jack=4098))
        del a['sAPe']
        assert 'sape' not in a
        del a['GUIDO']
        assert 'guido' not in a

    def test___getitem__(self):
        a = self.dict_type(dict(sape=4139, guido=4127, jack=4098))
        assert a['sape'] == 4139
        assert a['SAPE'] == 4139
        assert a['SAPe'] == 4139

    dict_arg = dict(sape=4139, guido=4127, jack=4098)
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

    def test_get(self):
        a = self.dict_type(dict(sape=4139, guido=4127, jack=4098))
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
        # https://bugs.python.org/issue23372 (rejected)
        a = self.dict_type(int, dict(sape=4139, guido=4139, jack=4139))
        c = self.dict_type.fromkeys(['sape', 'guido', 'jack'], 4139)
        assert a == c # !!!
        c = self.dict_type.fromkeys(['sApe', 'guIdo', 'jaCK'], 4139)
        assert a == c # !!!

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
        assert r'c:\random\path.txt' == p
        assert GPath('c:/random/path.txt') == p
        assert GPath(r'c:\random\path.txt') == p
        # paths and bytes
        assert b'c:/random/path.txt' == p
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
        assert empty == b''
        assert not (None == empty)
        with pytest.raises(TypeError): assert empty == []
        with pytest.raises(TypeError): assert empty == False
        with pytest.raises(TypeError): assert not (empty == [1])

    def test__le__(self):
        # paths and unicode
        p = GPath('c:/random/path.txt')
        assert 'c:/random/path.txt' <= p
        assert r'c:\random\path.txt' <= p
        assert GPath('c:/random/path.txt') <= p
        assert GPath(r'c:\random\path.txt') <= p
        # paths and bytes
        assert b'c:/random/path.txt' <= p
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
        assert empty <= b''
        with pytest.raises(TypeError): assert (None <= p)
        with pytest.raises(TypeError): assert not (p <= None)
        with pytest.raises(TypeError): assert empty <= []
        with pytest.raises(TypeError): assert empty <= False
        with pytest.raises(TypeError): assert not (empty <= [1])

    def test_dict_keys(self):
        d = {GPath('c:/random/path.txt'): 1}
        assert not ('c:/random/path.txt' in d) ## oops
        assert r'c:\random\path.txt' in d
        assert GPath('c:/random/path.txt') in d
        assert GPath(r'c:\random\path.txt') in d
        dd = {'c:/random/path.txt': 1}
        assert not GPath('c:/random/path.txt') in dd
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
