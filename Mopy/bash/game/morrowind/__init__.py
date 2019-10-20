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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""GameInfo override for TES III: Morrowind."""
from .. import GameInfo
from ... import brec

class MorrowindGameInfo(GameInfo):
    displayName = u'Morrowind'
    fsName = u'Morrowind'
    altName = u'Wrye Mash'
    defaultIniFile = u'Morrowind.ini'
    uses_personal_folders = False
    launch_exe = u'Morrowind.exe'
    game_detect_file = [u'Morrowind.exe']
    version_detect_file  = [u'Morrowind.exe']
    masterFiles = [u'Morrowind.esm']
    mods_dir = u'Data Files'
    iniFiles = [u'Morrowind.ini']
    pklfile = u'bash\\db\\Morrowind_ids.pkl'
    masterlist_dir = u'Morrowind'
    # This is according to xEdit's sources, but it doesn't make that key for me
    regInstallKeys = (u'Bethesda Softworks\\Morrowind', u'Installed Path')
    nexusUrl = u'https://www.nexusmods.com/morrowind/'
    nexusName = u'Morrowind Nexus'
    nexusKey = u'bash.installers.openMorrowindNexus.continue'

    allow_reset_bsa_timestamps = True
    supports_mod_inis = False

    using_txt_file = False

    class ck(GameInfo.ck):
        ck_abbrev = u'TESCS'
        long_name = u'Construction Set'
        exe = u'TES Construction Set.exe'
        se_args = None
        image_name = u'tescs%s.png'

    # TODO(inf) MWSE and MGE are vastly different from the later game versions

    class ini(GameInfo.ini): # No BSA Redirection, TODO need BSA Invalidation
        bsaRedirection = (u'', u'')

    class pnd(GameInfo.pnd): # Morrowind seems to have no such directories
        voice_dir = []

    class xe(GameInfo.xe):
        full_name = u'TES3Edit'
        expert_key = u'tes3View.iKnowWhatImDoing'

    screenshot_enabled_key = (u'General', u'Screen Shot Enable', u'1')
    screenshot_base_key = (u'General', u'Screen Shot Base Name', u'ScreenShot')
    screenshot_index_key = (u'General', u'Screen Shot Index', u'0')

    # BAIN:
    dataDirs = GameInfo.dataDirs | {
        u'bookart',
        u'icons',
        u'mwse',
        u'shaders',
    }
    SkipBAINRefresh = {
        u'tes3edit backups',
        u'tes3edit cache',
    }

    class esp(GameInfo.esp):
        validHeaderVersions = (1.2, 1.3)
        stringsFiles = []
        plugin_header_sig = b'TES3'

    @classmethod
    def init(cls):
        cls._dynamic_import_modules(__name__)
        from .records import MreTes3
        # Setting RecordHeader class variables - Morrowind is special
        rec_header = brec.RecordHeader
        rec_header.rec_header_size = 16
        rec_header.rec_pack_format = [u'=4s', u'I', u'I', u'I']
        rec_header.rec_pack_format_str = u''.join(rec_header.rec_pack_format)
        rec_header.sub_header_fmt = u'=4sI'
        rec_header.sub_header_size = 8
        rec_header.topTypes = [
            b'GMST', b'GLOB', b'CLAS', b'FACT', b'RACE', b'SOUN', b'SKIL',
            b'MGEF', b'SCPT', b'REGN', b'SSCR', b'BSGN', b'LTEX', b'STAT',
            b'DOOR', b'MISC', b'WEAP', b'CONT', b'SPEL', b'CREA', b'BODY',
            b'LIGH', b'ENCH', b'NPC_', b'ARMO', b'CLOT', b'REPA', b'ACTI',
            b'APPA', b'LOCK', b'PROB', b'INGR', b'BOOK', b'ALCH', b'LEVI',
            b'LEVC', b'CELL', b'LAND', b'PGRD', b'SNDG', b'DIAL', b'INFO']
            # +SSCR? in xEdit: to be confirmed
        # TODO(inf) Everything up to this TODO correct, the rest may not be yet
        rec_header.pack_formats = {0: u'=4sI4s2I'}
        rec_header.pack_formats.update(
            {x: u'=4s4I' for x in {1, 6, 7, 8, 9, 10}})
        rec_header.pack_formats.update({x: u'=4sIi2I' for x in {2, 3}})
        rec_header.pack_formats.update({x: u'=4sIhh2I' for x in {4, 5}})
        rec_header.recordTypes = set(rec_header.topTypes + [b'TES3'])
        brec.MreRecord.type_class = dict((x.classType, x) for x in (MreTes3,))
        brec.MreRecord.simpleTypes = (
            set(brec.MreRecord.type_class) - {b'TES3'})

GAME_TYPE = MorrowindGameInfo
