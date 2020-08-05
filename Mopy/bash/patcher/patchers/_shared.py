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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Temp module housing shared classes between CBash and PBash until CBash is
dropped entirely."""
from collections import defaultdict
from ..base import AImportPatcher, AListPatcher

#------------------------------------------------------------------------------
class _AImportInventory(AListPatcher):  # next class that has ___init__
    iiMode = True

    def __init__(self, p_name, p_file, p_sources):
        super(_AImportInventory, self).__init__(p_name, p_file, p_sources)
        self.id_deltas = defaultdict(list)
        #should be redundant since this patcher doesn't allow unloaded
        #self.srcs = [x for x in self.srcs if (x in modInfos and x in
        # patchFile.allMods)]

#------------------------------------------------------------------------------
class _ANamesPatcher(AImportPatcher):
    """Import names from source mods/files."""
    logMsg =  u'\n=== ' + _(u'Renamed Items')
    srcsHeader = u'=== ' + _(u'Source Mods/Files')

#------------------------------------------------------------------------------
class _ANpcFacePatcher(AImportPatcher):
    """NPC Faces patcher, for use with TNR or similar mods."""
    _read_write_records = (b'NPC_',)

    def _ignore_record(self, faceMod):
        # Ignore the record. Another option would be to just ignore the
        # attr_fidvalue result
        self.patchFile.patcher_mod_skipcount[self._patcher_name][faceMod] += 1

#------------------------------------------------------------------------------
class _AStatsPatcher(AImportPatcher):
    """Import stats from mod file."""
    scanOrder = 28
    editOrder = 28 #--Run ahead of bow patcher
    logMsg = u'\n=== ' + _(u'Imported Stats')
    srcsHeader = u'=== ' + _(u'Source Mods/Files')

#------------------------------------------------------------------------------
class _ASpellsPatcher(AImportPatcher):
    """Import spell changes from mod files."""
    scanOrder = 29
    editOrder = 29 #--Run ahead of bow patcher
    _read_write_records = (b'SPEL',)
