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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from pytest import fail

from ...loot_parser import _process_condition_string
from ...exception import LexerError, ParserError

# Conditions: Canonical representation tests ----------------------------------
class _ATestCanonical(object):
    """Tests if parsing the specified condition produces the specified
    canonical parsing result."""
    _condition = u''
    _canonical_parse = u''

    def test_parse_condition(self):
        """Tests that parsing the condition produces the canonical
        representation."""
        assert repr(_process_condition_string(
            self._condition)) == self._canonical_parse

    def test_parse_canonical(self):
        """Tests that parsing the canonical representation also produces the
        canonical representation (e.g. doesn't add more and more
        parentheses)."""
        assert repr(_process_condition_string(
            self._canonical_parse)) == self._canonical_parse

class TestCanonicalSAFunction(_ATestCanonical):
    """Tests if a single-argument function parses correctly."""
    _condition = _canonical_parse = u'foo("bar")'

class TestCanonicalMAFunction(_ATestCanonical):
    """Tests if a multi-argument function parses correctly. Also checks all
    types of arguments."""
    _condition = _canonical_parse = (u'foo("bar", 955CCA77, >, <, >=, <=, ==, '
                                     u'!=)')

class TestCanonicalNot(_ATestCanonical):
    """Tests if a simple combination of 'not' and a function works."""
    _condition = u'not foo("bar")'
    _canonical_parse = u'(not foo("bar"))'

class TestCanonicalAnd(_ATestCanonical):
    """Tests if a simple combination of two functions using 'and' works."""
    _condition = u'foo("bar") and bar("foo")'
    _canonical_parse = u'(foo("bar") and bar("foo"))'

class TestCanonicalOr(_ATestCanonical):
    """Tests if a simple combination of two functions using 'or' works."""
    _condition = u'foo("bar") or bar("foo")'
    _canonical_parse = u'(foo("bar") or bar("foo"))'

class TestCanonicalParens(_ATestCanonical):
    """Tests if using parentheses works (will be discarded in the canonical
    representation since they're not necessary for a bare function)."""
    _condition = u'(foo("bar"))'
    _canonical_parse = u'foo("bar")'

class TestCanonicalPrecedenceOrAnd(_ATestCanonical):
    """Tests if the precedence between 'or' and 'and' is parsed correctly
    ('and' should have higher precedence)."""
    _condition = u'foo("bar") and bar("qux") or qux("foo")'
    _canonical_parse = u'((foo("bar") and bar("qux")) or qux("foo"))'

class TestCanonicalWhitespace(_ATestCanonical):
    """Tests if the parser ignores whitespace outside of strings, but respects
    it inside strings."""
    _condition = u'  foo ( " b a r " )  '
    _canonical_parse = u'foo(" b a r ")'

class TestCanonicalNotExpr(_ATestCanonical):
    """Tests if the parser supports not-expressions (metadata syntax
    v0.17+)."""
    _condition = u'not (foo("bar") and bar("foo"))'
    _canonical_parse = u'(not (foo("bar") and bar("foo")))'

class TestCanonicalNotExprComplex(_ATestCanonical):
    """Tests if a complex combination of not-expressions that was bugged in the
    initial implementation of this feature in WB."""
    _condition = u'not (not foo("bar") and not bar("foo"))'
    _canonical_parse = u'(not ((not foo("bar")) and (not bar("foo"))))'

class TestCanonicalExample1(_ATestCanonical):
    """Tests parsing of a condition based off of an example given in the
    libloot docs."""
    _condition = u'foo("bar") and bar("qux") or not qux("foo")'
    _canonical_parse = u'((foo("bar") and bar("qux")) or (not qux("foo")))'

class TestCanonicalExample2(_ATestCanonical):
    """Tests parsing of a condition based off of an example given in the
    libloot docs."""
    _condition = u'foo("bar") and (bar("qux") or not qux("foo"))'
    _canonical_parse = u'(foo("bar") and (bar("qux") or (not qux("foo"))))'

# Conditions: Rejected-by-lexer tests -----------------------------------------
class _ATestLexerRejects(object):
    """Tests if lexing the specified condition fails."""
    _condition = u''

    def test_lexer_rejects(self):
        try:
            _process_condition_string(self._condition)
            fail('Processing should fail at the parser, but succeeded '
                 'instead.')
        except LexerError:
            pass # Correct behavior, pass the test
        except ParserError:
            fail('Processing should fail at the parser, but failed at the '
                 'lexer instead.')

class TestLexerRejectsUnclosedString(_ATestLexerRejects):
    """Tests if the lexer rejects a string that lacks closing quotation
    marks."""
    _condition = u'"foo'

class TestLexerRejectsNewline(_ATestLexerRejects):
    """Tests if the lexer rejects a string with a newline."""
    _condition = u'foo\n'

class TestLexerRejectsInvalidHex(_ATestLexerRejects):
    """Tests if the lexer rejects a checksum with non-hexadecimal digits."""
    _condition = u'0123456789ABCDEFG'

class TestLexerRejectsEmptyString(_ATestLexerRejects):
    """Tests if the lexer rejects an empty string."""
    _condition = u'""'

class TestLexerRejectsSQString(_ATestLexerRejects):
    """Tests if the lexer rejects a single-quoted string."""
    _condition = u"'foo'"

# Conditions: Rejected-by-parser tests ----------------------------------------
class _ATestParserRejects(object):
    """Tests if parsing the specified condition fails, but lexing works."""
    _condition = u''

    def test_parser_rejects(self):
        try:
            _process_condition_string(self._condition)
            fail('Processing should fail at the parser, but succeeded '
                 'instead.')
        except LexerError:
            fail('Processing should fail at the parser, but failed at the '
                 'lexer instead.')
        except ParserError:
            pass # Correct behavior, pass the test

class TestParserRejectsEmptyCondition(_ATestParserRejects):
    """Tests if the parser rejects an empty condition string."""

class TestParserRejectsBareString(_ATestParserRejects):
    """Tests if the parser rejects a bare string."""
    _condition = u'"foo"'

class TestParserRejectsBareChecksum(_ATestParserRejects):
    """Tests if the parser rejects a bare checksum."""
    _condition = u'1A98F5B'

class TestParserRejectsBareComparison(_ATestParserRejects):
    """Tests if the parser rejects a bare comparison operator."""
    _condition = u'!='

class TestParserRejectsBareComma(_ATestParserRejects):
    """Tests if the parser rejects a bare comma."""
    _condition = u','

class TestParserRejectsBareFunction(_ATestParserRejects):
    """Tests if the parser rejects a bare function."""
    _condition = u'foo'

class TestParserRejectsBareNot(_ATestParserRejects):
    """Tests if the parser rejects a bare 'not'."""
    _condition = u'not'

class TestParserRejectsBareAnd(_ATestParserRejects):
    """Tests if the parser rejects a bare 'and'."""
    _condition = u'and'

class TestParserRejectsBareOr(_ATestParserRejects):
    """Tests if the parser rejects a bare 'or'."""
    _condition = u'or'

class TestParserRejectsNAFunction(_ATestParserRejects):
    """Tests if the parser rejects a function with no arguments."""
    _condition = u'foo()'

class TestParserRejectsMissingArgL(_ATestParserRejects):
    """Tests if the parser rejects a binary operator with a missing argument on
    the LHS."""
    _condition = u' and foo("bar")'

class TestParserRejectsMissingArgR(_ATestParserRejects):
    """Tests if the parser rejects a binary operator with a missing argument on
    the RHS."""
    _condition = u'foo("bar") or '

class TestParserRejectsDoubleBinary(_ATestParserRejects):
    """Tests if the parser rejects a double binary operator."""
    _condition = u'foo("bar") and and bar("foo")'

class TestParserRejectsDoubleNot(_ATestParserRejects):
    """Tests if the parser rejects a double 'not' expression."""
    _condition = u'not not foo("bar")'
