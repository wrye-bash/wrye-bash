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
"""GameInfo override for Fallout 4 VR. Inherits from Fallout 4 and tweaks where
necessary."""

from ..fallout4 import Fallout4GameInfo
from ... import brec

class Fallout4VRGameInfo(Fallout4GameInfo):
    displayName = u'Fallout 4 VR'
    fsName = u'Fallout4VR'
    altName = u'Wrye VRash'
    defaultIniFile = u'Fallout4.ini'
    launch_exe = u'Fallout4VR.exe'
    game_detect_file = [u'Fallout4VR.exe']
    version_detect_file = [u'Fallout4VR.exe']
    masterFiles = [u'Fallout4.esm', u'Fallout4_VR.esm',]
    iniFiles = [
        u'Fallout4.ini',
        u'Fallout4Prefs.ini',
        u'Fallout4Custom.ini',
        u'Fallout4VrCustom.ini',
    ]
    regInstallKeys = (u'Bethesda Softworks\\Fallout 4 VR', u'Installed Path')

    espm_extensions = Fallout4GameInfo.espm_extensions - {u'.esl'}
    check_esl = False

    class Se(Fallout4GameInfo.Se):
        se_abbrev = u'F4SEVR'
        long_name = u'Fallout 4 VR Script Extender'
        exe = u'f4sevr_loader.exe'
        ver_files = [u'f4sevr_loader.exe', u'f4sevr_steam_loader.dll']

    class Bsa(Fallout4GameInfo.Bsa):
        vanilla_string_bsas = Fallout4GameInfo.Bsa.vanilla_string_bsas.copy()
        vanilla_string_bsas.update({
            u'fallout4_vr.esm': [u'Fallout4_VR - Main.ba2'],
        })

    class Xe(Fallout4GameInfo.Xe):
        full_name = u'FO4VREdit'
        expert_key = 'fo4vrView.iKnowWhatImDoing'

    SkipBAINRefresh = {u'fo4vredit backups', u'fo4vredit cache'}

    class Esp(Fallout4GameInfo.Esp):
        expanded_plugin_range = False

    # ---------------------------------------------------------------------
    # --Imported - MreGlob is special import, not in records.py
    # ---------------------------------------------------------------------
    @classmethod
    def init(cls):
        cls._dynamic_import_modules(__name__)
        # First import from fallout4.records file, so MelModel is set correctly
        from .records import MreTes4, MreLvli, MreLvln
        # ---------------------------------------------------------------------
        # These Are normally not mergable but added to brec.MreRecord.type_class
        #
        #       MreCell,
        # ---------------------------------------------------------------------
        # These have undefined FormIDs Do not merge them
        #
        #       MreNavi, MreNavm,
        # ---------------------------------------------------------------------
        # These need syntax revision but can be merged once that is corrected
        #
        #       MreAchr, MreDial, MreLctn, MreInfo, MreFact, MrePerk,
        # ---------------------------------------------------------------------
        cls.mergeClasses = (
            # -- Imported from Skyrim/SkyrimSE
            # Added to records.py
            MreLvli, MreLvln
        )
        # Setting RecordHeader class variables --------------------------------
        brec.RecordHeader.topTypes = [
            'GMST', 'KYWD', 'LCRT', 'AACT', 'TRNS', 'CMPO', 'TXST', 'GLOB',
            'DMGT', 'CLAS', 'FACT', 'HDPT', 'RACE', 'SOUN', 'ASPC', 'MGEF',
            'LTEX', 'ENCH', 'SPEL', 'ACTI', 'TACT', 'ARMO', 'BOOK', 'CONT',
            'DOOR', 'INGR', 'LIGH', 'MISC', 'STAT', 'SCOL', 'MSTT', 'GRAS',
            'TREE', 'FLOR', 'FURN', 'WEAP', 'AMMO', 'NPC_', 'PLYR', 'LVLN',
            'KEYM', 'ALCH', 'IDLM', 'NOTE', 'PROJ', 'HAZD', 'BNDS', 'TERM',
            'LVLI', 'WTHR', 'CLMT', 'SPGD', 'RFCT', 'REGN', 'NAVI', 'CELL',
            'WRLD', 'QUST', 'IDLE', 'PACK', 'CSTY', 'LSCR', 'LVSP', 'ANIO',
            'WATR', 'EFSH', 'EXPL', 'DEBR', 'IMGS', 'IMAD', 'FLST', 'PERK',
            'BPTD', 'ADDN', 'AVIF', 'CAMS', 'CPTH', 'VTYP', 'MATT', 'IPCT',
            'IPDS', 'ARMA', 'ECZN', 'LCTN', 'MESG', 'DOBJ', 'DFOB', 'LGTM',
            'MUSC', 'FSTP', 'FSTS', 'SMBN', 'SMQN', 'SMEN', 'DLBR', 'MUST',
            'DLVW', 'EQUP', 'RELA', 'SCEN', 'ASTP', 'OTFT', 'ARTO', 'MATO',
            'MOVT', 'SNDR', 'SNCT', 'SOPM', 'COLL', 'CLFM', 'REVB', 'PKIN',
            'RFGP', 'AMDL', 'LAYR', 'COBJ', 'OMOD', 'MSWP', 'ZOOM', 'INNR',
            'KSSM', 'AECH', 'SCCO', 'AORU', 'SCSN', 'STAG', 'NOCM', 'LENS',
            'GDRY', 'OVIS']
        brec.RecordHeader.recordTypes = (set(brec.RecordHeader.topTypes) |
            {'GRUP', 'TES4', 'REFR', 'ACHR', 'PMIS', 'PARW', 'PGRE', 'PBEA',
             'PFLA', 'PCON', 'PBAR', 'PHZD', 'LAND', 'NAVM', 'DIAL', 'INFO'})
        brec.RecordHeader.plugin_form_version = 131
        brec.MreRecord.type_class = dict((x.classType,x) for x in (
            #--Always present
            MreTes4, MreLvli, MreLvln,
            # Imported from Skyrim or SkyrimSE
            # Added to records.py
            ))
        brec.MreRecord.simpleTypes = (
            set(brec.MreRecord.type_class) - {'TES4',})

GAME_TYPE = Fallout4VRGameInfo
