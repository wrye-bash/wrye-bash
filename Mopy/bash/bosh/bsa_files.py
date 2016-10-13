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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2015 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""Bsa files."""

__author__ = 'Utumno'

import struct

class BSAHeader(object):
    __slots__ = ( # in the order encountered in the header
        'file_id', 'version', 'folder_record_offset', 'archive_flags',
        'folder_count', 'file_count', 'total_folder_name_length',
        'total_file_name_length', 'file_flags', )

    def read_header(self, ins):
        for attr in BSAHeader.__slots__:
            self.__setattr__(attr, struct.unpack('I', ins.read(4))[0])

class BSAFolderRecord(object):
    __slots__ = ('folder_name_hash', 'files_count', 'file_records_offset', )

class BSAFileRecord(object):
    __slots__ = ('file_name_hash', 'file_data_size', 'raw_file_data_offset', )

class BSA(object):
    __slots__ = ('bsa_header', 'folder_records', 'file_record_blocks',
                 'file_name_block', 'data_block', )
