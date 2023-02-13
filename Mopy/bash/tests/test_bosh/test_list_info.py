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
"""This seems to belong in test_bolt, but it imports from bosh and really tests
bosh functionality."""
from ... import archives
from ...bolt import ListInfo
from ...bosh import ModInfo
from ...bosh.bain import InstallerArchive, InstallerMarker, InstallerProject

class TestListInfo(object):
    def test_validate_filename_str(self):
        li_val = ListInfo.validate_filename_str
        str_, rt = li_val('?', allowed_exts={})
        assert rt is None
        str_, rt = li_val('78.exe', allowed_exts={'exe'})
        assert rt is None
        str_, rt = li_val('78.exe', allowed_exts={'.exe'})
        assert rt == '78'
        mi_val = ModInfo.validate_filename_str
        for fname_ in (f'78.{s}' for s in ('esp', 'esm')):
            str_, rt = mi_val(fname_)
            assert rt == '78'
        str_, rt = mi_val('78.exe')
        assert rt is None
        inst_arch_val = InstallerArchive.validate_filename_str
        for fname_ in (f'78{s}' for s in archives.writeExts):
            str_, rt = inst_arch_val(fname_)
            assert str_ == fname_
            assert rt == '78'
        for fname_, e in ((f'78{s}', s) for s in ['.rar', '.exe']):
            str_, rt = inst_arch_val(fname_)
            assert rt is None
            str_, rt = inst_arch_val(fname_, use_default_ext=True)
            assert str_ == '78.7z'
            assert rt == (
                '78', f'The {e} extension is unsupported. Using .7z instead.')
        inst_mark_val = InstallerMarker.validate_filename_str
        for fname_ in ('?.invalid', '.valid-note-dot'):
            str_, rt = inst_mark_val(fname_)
            assert str_ == fname_
        inst_proj_val = InstallerProject.validate_filename_str
        str_, rt = inst_proj_val('?.invalid')
        assert rt is None
        str_, rt = inst_proj_val('.valid-note-dot')
        assert str_ == fname_
