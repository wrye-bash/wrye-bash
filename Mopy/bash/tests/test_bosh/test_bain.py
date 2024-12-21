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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import os

from ...bosh.bain import _remove_empty_dirs
from ...wbtemp import TempDir

def test__remove_empty_dirs():
    with TempDir() as tempdir:
        os.mkdir(tex := os.path.join(tempdir, 'textures'))
        os.mkdir(cl := os.path.join(tex, 'clothes'))
        os.mkdir(os.path.join(cl, 'farmclothes02'))
        _remove_empty_dirs(tex)
        assert not os.path.exists(cl)
