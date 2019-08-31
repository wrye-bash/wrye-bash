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
"""GameInfo override for Fallout 4."""

from .default_tweaks import default_tweaks
from .. import GameInfo
from ... import brec

class Fallout4GameInfo(GameInfo):
    displayName = u'Fallout 4'
    fsName = u'Fallout4'
    altName = u'Wrye Flash'
    defaultIniFile = u'Fallout4_default.ini'
    launch_exe = u'Fallout4.exe'
    game_detect_file = [u'Fallout4.exe']
    version_detect_file = [u'Fallout4.exe']
    masterFiles = [u'Fallout4.esm']
    iniFiles = [u'Fallout4.ini', u'Fallout4Prefs.ini', u'Fallout4Custom.ini', ]
    pklfile = ur'bash\db\Fallout4_ids.pkl'
    masterlist_dir = u'Fallout4'
    regInstallKeys = (u'Bethesda Softworks\\Fallout4', u'Installed Path')
    nexusUrl = u'https://www.nexusmods.com/fallout4/'
    nexusName = u'Fallout 4 Nexus'
    nexusKey = 'bash.installers.openFallout4Nexus.continue'

    bsa_extension = ur'ba2'
    vanilla_string_bsas = {
        u'fallout4.esm': [u'Fallout4 - Interface.ba2'],
        u'dlcrobot.esm': [u'DLCRobot - Main.ba2'],
        u'dlcworkshop01.esm': [u'DLCworkshop01 - Main.ba2'],
        u'dlcworkshop02.esm': [u'DLCworkshop02 - Main.ba2'],
        u'dlcworkshop03.esm': [u'DLCworkshop03 - Main.ba2'],
        u'dlccoast.esm': [u'DLCCoast - Main.ba2'],
        u'dlcnukaworld.esm':  [u'DLCNukaWorld - Main.ba2'],
    }
    resource_archives_keys = (
        u'sResourceIndexFileList', u'sResourceStartUpArchiveList',
        u'sResourceArchiveList', u'sResourceArchiveList2',
        u'sResourceArchiveListBeta'
    )

    espm_extensions = {u'.esp', u'.esm', u'.esl'}
    script_extensions = {u'.psc'}
    has_achlist = True
    check_esl = True

    class cs(GameInfo.cs):
        # TODO:  When the Fallout 4 Creation Kit is actually released,
        # double check that the filename is correct, and create an actual icon
        cs_abbrev = u'FO4CK'
        long_name = u'Creation Kit'
        exe = u'CreationKit.exe'
        se_args = None
        image_name = u'creationkit%s.png'

    class se(GameInfo.se):
        se_abbrev = u'F4SE'
        long_name = u'Fallout 4 Script Extender'
        exe = u'f4se_loader.exe'
        steam_exe = u'f4se_steam_loader.dll'
        plugin_dir = u'F4SE'
        cosave_ext = u'.f4se'
        url = u'http://f4se.silverlock.org/'
        url_tip = u'http://f4se.silverlock.org/'

    class ini(GameInfo.ini):
        allowNewLines = True
        bsaRedirection = (u'',u'')

    class ess(GameInfo.ess):
        ext = u'.fos'

    class pnd(GameInfo.pnd):
        facegen_dir_1 = [u'meshes', u'actors', u'character', u'facegendata',
                         u'facegeom']
        facegen_dir_2 = [u'meshes', u'actors', u'character',
                         u'facecustomization']

    # BAIN:
    dataDirs = GameInfo.dataDirs | {
        u'interface',
        u'lodsettings',
        u'materials',
        u'misc',
        u'programs',
        u'scripts',
        u'seq',
        u'shadersfx',
        u'strings',
        u'vis',
    }
    dataDirsPlus = {
        u'f4se',
        u'ini',
        u'mcm',   # FO4 MCM
        u'tools', # bodyslide
    }
    dontSkipDirs = {
        # This rule is to allow mods with string translation enabled.
        'interface\\translations':['.txt']
    }
    SkipBAINRefresh = {u'fo4edit backups', u'fo4edit cache'}

    class esp(GameInfo.esp):
        canBash = True
        canEditHeader = True
        validHeaderVersions = (0.95,)

    allTags = {u'Delev', u'Relev'}

    patchers = (u'ListsMerger',)

    # ---------------------------------------------------------------------
    # --Imported - MreGlob is special import, not in records.py
    # ---------------------------------------------------------------------
    @classmethod
    def init(cls):
        cls._dynamic_import_constants(__name__)
        # First import from fallout4.records file, so MelModel is set correctly
        from .records import MreHeader, MreLvli, MreLvln
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
            MreHeader, MreLvli, MreLvln,
            # Imported from Skyrim or SkyrimSE
            # Added to records.py
            ))
        brec.MreRecord.simpleTypes = (
            set(brec.MreRecord.type_class) - {'TES4',})

GAME_TYPE = Fallout4GameInfo
