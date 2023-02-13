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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Tests for complex regexes used in bosh."""
import re

from ...bosh import reTesNexus, reVersion

class _ATestRe:
    """Base class for regex tests."""
    _test_regex: re.Pattern
    # The plugin header description to test. Specified as a list of strings
    # which will be joined with '\n'
    _test_str: list[str]
    # The number of expected matches - matches re.findall return type
    _expected_matches: list[tuple[str, str]]

    def test_regex(self):
        """Runs the actual findall-based test."""
        rev_matches = self._test_regex.findall('\n'.join(self._test_str))
        assert rev_matches == self._expected_matches

# reVersion -------------------------------------------------------------------
class _ATestReVersion(_ATestRe):
    """Base class for reVersion tests."""
    _test_regex = reVersion

class TestReVersion_Simple(_ATestReVersion):
    """Tests straightforward matches."""
    _test_str = [
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
    _test_str = ['V. v: very normal string. no version here.']
    _expected_matches = []

class TestReVersion_NeedsNumber(_ATestReVersion):
    """Tests that purely alphabetic 'version numbers' do not match."""
    _test_str = [
        'very unfortunate match',
        'vanity',
        'released on 02/10/2021',
    ]
    _expected_matches = []

class TestReVersion_AnySpaces(_ATestReVersion):
    """Tests that any number of spaces (including tabs) are allowed between the
    version marker and the actual version."""
    _test_str = [
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
    _test_str = [
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
    _test_str = [
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
    _test_str = [
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
    _test_str = [
        'v1.0',
        'This is v1.0',
        ' v1.0',
        '\tv1.0',
        'This is a very important plugin.',
    ]
    _expected_matches = [('v', '1.0')] * 4

# reTesNexus ------------------------------------------------------------------
class _ATestReTesNexus(_ATestRe):
    """Base class for reTesNexus tests."""
    _test_regex = reTesNexus

class TestReTesNexus_ASLAL(_ATestReTesNexus):
    """Tests that the regex works correctly with a basic package name (taken
    from ASLAL)."""
    _test_str = ['Alternate Start - Live Another Life-272-4-1-4-1608766947.7z']
    _expected_matches = [('Alternate Start - Live Another Life', '272', '.7z',
                          '.7z', '7z')]

class TestReTesNexus_MoreHud(_ATestReTesNexus):
    """Tests that the regex works correctly with the package name that
    necessitated the rewrite in the first place (moreHUD). The problem was that
    this one has four parts to its versions, the old regex could only handle
    1-3."""
    _test_str = ['moreHUD SE Light Master - AE-12688-5-1-1-0-1653588018.7z']
    _expected_matches = [('moreHUD SE Light Master - AE', '12688', '.7z',
                          '.7z', '7z')]

class TestReTesNexus_RaceMenu(_ATestReTesNexus):
    """Tests a broken case. The problem here is the usage of dashes after the
    'v0', which makes it ambigous as to whether that's a version number or the
    mod page ID."""
    _test_str = ['RaceMenu Anniversary Edition v0-4-19-11-19080-0-4-19-11-'
                 '1657140512.7z']
    _expected_matches = [('RaceMenu Anniversary Edition v0', '4', '.7z', '.7z',
                          '7z')]

class TestReTesNexus_RaceMenuFixed(_ATestReTesNexus):
    """Tests that the problem described above is indeed due to dashes.
    Replacing them with dots gives the right result."""
    _test_str = ['RaceMenu Anniversary Edition v0.4.19.11-19080-0-4-19-11-'
                 '1657140512.7z']
    _expected_matches = [('RaceMenu Anniversary Edition v0.4.19.11', '19080',
                          '.7z', '.7z', '7z')]

class TestReTesNexus_NoMatch(_ATestReTesNexus):
    """Tests the package name of the Improved Camera preview release 2, a mod
    that isn't from the Nexus and hence shouldn't match."""
    _test_str = ['ImprovedCameraAE-PR2.7z']
    _expected_matches = []

class TestReTesNexus_FutureMod(_ATestReTesNexus):
    """Tests a hypothetical future mod release that has a mod ID with 8 digits
    and a download ID with 17 digits. The old regex could only handle up to 7
    digits for the mod ID and only up to 16 digits for the download ID."""
    _test_str = ['Cool Future Mod-25013821-2-0-1-0-380147987496669221.7z']
    _expected_matches = [('Cool Future Mod', '25013821', '.7z', '.7z', '7z')]
