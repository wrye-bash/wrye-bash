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
from ... import archives
from ...bosh import ListInfo, ModInfo
from ...bosh.bain import InstallerProject, InstallerArchive, InstallerMarker

class TestListInfo(object):
    def test_validate_filename_str(self):
        li_val = ListInfo.validate_filename_str
        str_, rt = li_val(u'?', allowed_exts={})
        assert rt is None
        str_, rt = li_val(u'78.exe', allowed_exts={u'exe'})
        assert rt is None
        str_, rt = li_val(u'78.exe', allowed_exts={u'.exe'})
        assert rt == u'78'
        mi_val = ModInfo.validate_filename_str
        for fname_ in (u'78.%s' % s for s in (u'esp', u'esm')):
            str_, rt = mi_val(fname_)
            assert rt == u'78'
        str_, rt = mi_val(u'78.exe')
        assert rt is None
        inst_arch_val = InstallerArchive.validate_filename_str
        for fname_ in (u'78%s' % s for s in archives.writeExts):
            str_, rt = inst_arch_val(fname_)
            assert str_ == fname_
            assert rt == u'78'
        for fname_, e in ((u'78%s' % s, s) for s in [u'.rar', u'.exe']):
            str_, rt = inst_arch_val(fname_)
            assert rt is None
            str_, rt = inst_arch_val(fname_, use_default_ext=True)
            assert str_ == u'78.7z'
            assert rt == (u'78',
                u'The %s extension is unsupported. Using .7z instead.' % e)
        inst_mark_val = InstallerMarker.validate_filename_str
        for fname_ in (u'?.invalid' , u'.valid-note-dot'):
            str_, rt = inst_mark_val(fname_)
            assert str_ == fname_
        inst_proj_val = InstallerProject.validate_filename_str
        str_, rt = inst_proj_val(u'?.invalid')
        assert rt is None
        str_, rt = inst_proj_val(u'.valid-note-dot')
        assert str_ == fname_
