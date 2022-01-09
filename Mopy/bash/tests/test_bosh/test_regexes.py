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
"""Tests for complex regexes used in bosh."""
from ...bosh import reVersion

class _ATestReVersion:
    """Base class for reVersion tests."""
    # The plugin header description to test. Specified as a list of strings
    # which will be joined with '\n'
    _header_desc: list[str]
    # The number of expected matches - matches re.findall return type
    _expected_matches: list[tuple[str, str]]

    def test_reVersion(self):
        """Runs the actual findall-based test."""
        rev_matches = reVersion.findall('\n'.join(self._header_desc))
        assert rev_matches == self._expected_matches

class TestReVersion_Simple(_ATestReVersion):
    """Tests straightforward matches."""
    _header_desc = [
        'version: 1.0',
        'version1.0',
        'version 1.0',
        'version.1.0',
        'ver: 1.0',
        'ver1.0',
        'ver 1.0',
        'ver.1.0',
        'rev: 1.0',
        'rev1.0',
        'rev 1.0',
        'rev.1.0',
        'r: 1.0',
        'r1.0',
        'r 1.0',
        'r.1.0',
        'v1.0',
        'v: 1.0',
        'v 1.0',
        'v.1.0',
    ]
    _expected_matches = [
        ('version:', '1.0'),
        ('version', '1.0'),
        ('version', '1.0'),
        ('version.', '1.0'),
        ('ver:', '1.0'),
        ('ver', '1.0'),
        ('ver', '1.0'),
        ('ver.', '1.0'),
        ('rev:', '1.0'),
        ('rev', '1.0'),
        ('rev', '1.0'),
        ('rev.', '1.0'),
        ('r:', '1.0'),
        ('r', '1.0'),
        ('r', '1.0'),
        ('r.', '1.0'),
        ('v', '1.0'),
        ('v:', '1.0'),
        ('v', '1.0'),
        ('v.', '1.0'),
    ]

class TestReVersion_NoVersion(_ATestReVersion):
    """Tests a string with no versions, but two 'v's that could start a
    version."""
    _header_desc = ['V. v: very normal string. no version here.']
    _expected_matches = []

class TestReVersion_NeedsNumber(_ATestReVersion):
    """Tests that purely alphabetic 'version numbers' do not match."""
    _header_desc = [
        'very unfortunate match',
        'vanity',
        'released on 02/10/2021',
    ]
    _expected_matches = []

class TestReVersion_AnySpaces(_ATestReVersion):
    """Tests that any number of spaces (including tabs) are allowed between the
    version marker and the actual version."""
    _header_desc = [
        'v1.0',
        'v 1.0',
        'v  1.0',
        'v\t1.0',
        'v\t\t1.0',
        'v\n1.0', # newlines are not accepted
        'v\r\n1.0',
    ]
    _expected_matches = [('v', '1.0')] * 5

class TestReVersion_Alphanumeric(_ATestReVersion):
    """Tests that letters are allowed inside versions."""
    _header_desc = [
        'v1a',
        'v1a.2b',
        'v1a.2b.3c',
        'v1a.2b.3c.4d',
        'va1', # not a valid version number - see NeedsNumber above
        'v1a.b2.1c',
        'v1.2.1.alpha1', # more realistic version number
    ]
    _expected_matches = [
        ('v', '1a'),
        ('v', '1a.2b'),
        ('v', '1a.2b.3c'),
        ('v', '1a.2b.3c.4d'),
        ('v', '1a.b2.1c'),
        ('v', '1.2.1.alpha1'),
    ]

class TestReVersion_TrailingPlus(_ATestReVersion):
    """Tests that a trailing plus is accepted."""
    _header_desc = [
        'v1.0+',
        'v1+.0',
        'v+1.0', # improper syntax
    ]
    _expected_matches = [
        ('v', '1.0+'),
        ('v', '1+'),
    ]

class TestReVersion_Dashes(_ATestReVersion):
    """Tests that dashes can be used instead of and mixed with dots."""
    _header_desc = [
        'v1.0.0',
        'v1.0-0',
        'v1-0.0',
        'v1-0-0',
    ]
    _expected_matches = [
        ('v', '1.0.0'),
        ('v', '1.0-0'),
        ('v', '1-0.0'),
        ('v', '1-0-0'),
    ]

class TestReVersion_Anywhere(_ATestReVersion):
    """Tests that versions are accepted anywhere within a line."""
    _header_desc = [
        'v1.0',
        'This is v1.0',
        ' v1.0',
        '\tv1.0',
        'This is a very important plugin.',
    ]
    _expected_matches = [('v', '1.0')] * 4
