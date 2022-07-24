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
"""Test archives.py"""
import os
import tempfile

from ..archives import compress7z, extract7z
from ..bolt import GPath, FName

_utils_dir = GPath(os.path.join(os.path.dirname(__file__), 'utils'))

def test_compress_extract_with_spaces(capsys):
    """Test compress7z/extract7z roundtrip, with spaces in folder names."""
    with capsys.disabled():
        with tempfile.TemporaryDirectory(prefix='dir with spaces') as dirname:
            print('created temporary directory', dirname)
            # Compress
            out_fname = FName('output archive.7z')
            full_out = GPath(os.path.join(dirname, out_fname))
            # check "temp_list" arg, for excluding files from compression
            templist = os.path.join(dirname, 'temp list.txt')
            with open(templist, 'w', encoding=u'utf-8-sig') as out:
                out.write(u'*thumbs.db\n')
            try:
                with open(thumbs := os.path.join(_utils_dir, 'thumbs.db'),
                          'w'):
                    print(f'creating {thumbs}')
                compress7z(full_out, out_fname, _utils_dir, temp_list=templist)
            finally:
                try:
                    os.remove(thumbs) ##: needed?
                except FileNotFoundError:
                    pass
            # Extract - test filelist_to_extract for extracting only some files
            with open(templist, 'w', encoding='utf8') as out:
                out.write('__init__.py\n')
            extract7z(full_out, dirname, filelist_to_extract=templist)
            assert '__init__.py' in os.listdir(dirname)
