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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Setting the locale in latest versions of python/wx is super buggy - see
issue #610. Write some tests for common scenarios - note these should
ideally run in all supported OSs - currently windoz."""
import time

import wx as _wx

from .. import bolt
from ..localize import setup_locale

class TestLocalize:
    """Test setup_locale WIP"""

    @classmethod
    def setup_class(cls):
        bolt.deprintOn = True

    @classmethod
    def teardown_class(cls):
        bolt.deprintOn = False

    def _test_locale(self, loc, capsys):
        with capsys.disabled():
            print(f'\n\n******* Testing {loc=} *******')
            setup_locale(loc, _wx)
            # getlocale = locale.getlocale()
            # print(getlocale)
            # assert getlocale
            # call the wx API that blows
            assert _wx.ArtProvider.GetBitmap(_wx.ART_PLUS, size=(16, 16))
            assert time.strptime('2006-01-01', '%Y-%m-%d')
            # assert time.strptime('2006-01-01', '%c')
            print(f'******* Tested {loc=} *******')

    def test_setlocale_pl_PL(self, capsys):
        """Test setting locale to pl_PL."""
        self._test_locale("pl_PL", capsys)

    def test_setlocale_nocli(self, capsys):
        """Test setting locale to default."""
        self._test_locale("", capsys)

    def test_setlocale_pl_dash_PL(self, capsys):
        """Test setting locale to pl-PL - seems it's not recognised by wx."""
        self._test_locale("pl-PL", capsys)
