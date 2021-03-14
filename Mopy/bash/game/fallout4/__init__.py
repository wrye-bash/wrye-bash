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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""GameInfo override for Fallout 4."""

from os.path import join as _j

from ..patch_game import GameInfo, PatchGame
from ... import brec

class Fallout4GameInfo(PatchGame):
    displayName = u'Fallout 4'
    fsName = u'Fallout4'
    altName = u'Wrye Flash'
    bash_root_prefix = u'Fallout4'
    launch_exe = u'Fallout4.exe'
    game_detect_files = [u'Fallout4.exe']
    version_detect_file = u'Fallout4.exe'
    master_file = u'Fallout4.esm'
    taglist_dir = u'Fallout4'
    regInstallKeys = (u'Bethesda Softworks\\Fallout4', u'Installed Path')
    nexusUrl = u'https://www.nexusmods.com/fallout4/'
    nexusName = u'Fallout 4 Nexus'
    nexusKey = u'bash.installers.openFallout4Nexus.continue'

    espm_extensions = GameInfo.espm_extensions | {u'.esl'}
    has_achlist = True
    check_esl = True
    plugin_name_specific_dirs = GameInfo.plugin_name_specific_dirs + [
        _j(u'meshes', u'actors', u'character', u'facegendata', u'facegeom'),
        _j(u'meshes', u'actors', u'character', u'facecustomization')]

    class Ws(GameInfo.Ws):
        publisher_name = u'Bethesda'
        win_store_name = u'BethesdaSoftworks.Fallout4-PC'

    class Ck(GameInfo.Ck):
        ck_abbrev = u'CK'
        long_name = u'Creation Kit'
        exe = u'CreationKit.exe'
        image_name = u'creationkit%s.png'

    class Se(GameInfo.Se):
        se_abbrev = u'F4SE'
        long_name = u'Fallout 4 Script Extender'
        exe = u'f4se_loader.exe'
        ver_files = [u'f4se_loader.exe', u'f4se_steam_loader.dll']
        plugin_dir = u'F4SE'
        cosave_tag = u'F4SE'
        cosave_ext = u'.f4se'
        url = u'http://f4se.silverlock.org/'
        url_tip = u'http://f4se.silverlock.org/'

    class Ini(GameInfo.Ini):
        default_ini_file = u'Fallout4_default.ini'
        dropdown_inis = [u'Fallout4.ini', u'Fallout4Prefs.ini']
        resource_archives_keys = (
            u'sResourceIndexFileList', u'sResourceStartUpArchiveList',
            u'sResourceArchiveList', u'sResourceArchiveList2',
            u'sResourceArchiveListBeta'
        )

    class Ess(GameInfo.Ess):
        ext = u'.fos'

    class Bsa(GameInfo.Bsa):
        bsa_extension = u'.ba2'
        valid_versions = {0x01}

    class Psc(GameInfo.Psc):
        source_extensions = {u'.psc'}

    class Xe(GameInfo.Xe):
        full_name = u'FO4Edit'
        xe_key_prefix = u'fo4View'

    class Bain(GameInfo.Bain):
        data_dirs = GameInfo.Bain.data_dirs | {
            u'f4se',
            u'interface',
            u'lodsettings',
            u'materials',
            u'mcm', # FO4 MCM
            u'misc',
            u'programs',
            u'scripts',
            u'seq',
            u'shadersfx',
            u'strings',
            u'tools', # bodyslide
            u'vis',
        }
        no_skip_dirs = {
            # This rule is to allow mods with string translation enabled.
            _j(u'interface', u'translations'): [u'.txt']
        }
        skip_bain_refresh = {u'fo4edit backups', u'fo4edit cache'}

    class Esp(GameInfo.Esp):
        canBash = True
        canEditHeader = True
        validHeaderVersions = (0.95, 1.0)
        expanded_plugin_range = True
        max_lvl_list_size = 255

    allTags = {
        u'Deactivate', u'Delev', u'Filter', u'ObjectBounds', u'Relev',
    }

    patchers = {
        u'ImportObjectBounds', u'LeveledLists',
    }

    bethDataFiles = {
        #--Vanilla
        u'fallout4.esm',
        u'fallout4.cdx',
        u'fallout4 - animations.ba2',
        u'fallout4 - geometry.csg',
        u'fallout4 - interface.ba2',
        u'fallout4 - materials.ba2',
        u'fallout4 - meshes.ba2',
        u'fallout4 - meshesextra.ba2',
        u'fallout4 - misc.ba2',
        u'fallout4 - nvflex.ba2',
        u'fallout4 - shaders.ba2',
        u'fallout4 - sounds.ba2',
        u'fallout4 - startup.ba2',
        u'fallout4 - textures1.ba2',
        u'fallout4 - textures2.ba2',
        u'fallout4 - textures3.ba2',
        u'fallout4 - textures4.ba2',
        u'fallout4 - textures5.ba2',
        u'fallout4 - textures6.ba2',
        u'fallout4 - textures7.ba2',
        u'fallout4 - textures8.ba2',
        u'fallout4 - textures9.ba2',
        u'fallout4 - voices.ba2',
        u'dlcrobot.esm',
        u'dlcrobot.cdx',
        u'dlcrobot - geometry.csg',
        u'dlcrobot - main.ba2',
        u'dlcrobot - textures.ba2',
        u'dlcrobot - voices_en.ba2',
        u'dlcworkshop01.esm',
        u'dlcworkshop01.cdx',
        u'dlcworkshop01 - geometry.csg',
        u'dlcworkshop01 - main.ba2',
        u'dlcworkshop01 - textures.ba2',
        u'dlccoast.esm',
        u'dlccoast.cdx',
        u'dlccoast - geometry.csg',
        u'dlccoast - main.ba2',
        u'dlccoast - textures.ba2',
        u'dlccoast - voices_en.ba2',
        u'dlcworkshop02.esm',
        u'dlcworkshop02 - main.ba2',
        u'dlcworkshop02 - textures.ba2',
        u'dlcworkshop03.esm',
        u'dlcworkshop03.cdx',
        u'dlcworkshop03 - geometry.csg',
        u'dlcworkshop03 - main.ba2',
        u'dlcworkshop03 - textures.ba2',
        u'dlcworkshop03 - voices_en.ba2',
        u'dlcnukaworld.esm',
        u'dlcnukaworld.cdx',
        u'dlcnukaworld - geometry.csg',
        u'dlcnukaworld - main.ba2',
        u'dlcnukaworld - textures.ba2',
        u'dlcnukaworld - voices_en.ba2',
    }

    @classmethod
    def init(cls):
        cls._dynamic_import_modules(__name__)
        from .records import MreGmst, MreTes4, MreLvli, MreLvln
        cls.mergeable_sigs = {clazz.rec_sig: clazz for clazz in (
            MreGmst, MreLvli, MreLvln
        )}
        # Setting RecordHeader class variables --------------------------------
        header_type = brec.RecordHeader
        header_type.top_grup_sigs = [
            b'GMST', b'KYWD', b'LCRT', b'AACT', b'TRNS', b'CMPO', b'TXST',
            b'GLOB', b'DMGT', b'CLAS', b'FACT', b'HDPT', b'RACE', b'SOUN',
            b'ASPC', b'MGEF', b'LTEX', b'ENCH', b'SPEL', b'ACTI', b'TACT',
            b'ARMO', b'BOOK', b'CONT', b'DOOR', b'INGR', b'LIGH', b'MISC',
            b'STAT', b'SCOL', b'MSTT', b'GRAS', b'TREE', b'FLOR', b'FURN',
            b'WEAP', b'AMMO', b'NPC_', b'PLYR', b'LVLN', b'KEYM', b'ALCH',
            b'IDLM', b'NOTE', b'PROJ', b'HAZD', b'BNDS', b'TERM', b'LVLI',
            b'WTHR', b'CLMT', b'SPGD', b'RFCT', b'REGN', b'NAVI', b'CELL',
            b'WRLD', b'QUST', b'IDLE', b'PACK', b'CSTY', b'LSCR', b'LVSP',
            b'ANIO', b'WATR', b'EFSH', b'EXPL', b'DEBR', b'IMGS', b'IMAD',
            b'FLST', b'PERK', b'BPTD', b'ADDN', b'AVIF', b'CAMS', b'CPTH',
            b'VTYP', b'MATT', b'IPCT', b'IPDS', b'ARMA', b'ECZN', b'LCTN',
            b'MESG', b'DOBJ', b'DFOB', b'LGTM', b'MUSC', b'FSTP', b'FSTS',
            b'SMBN', b'SMQN', b'SMEN', b'DLBR', b'MUST', b'DLVW', b'EQUP',
            b'RELA', b'SCEN', b'ASTP', b'OTFT', b'ARTO', b'MATO', b'MOVT',
            b'SNDR', b'SNCT', b'SOPM', b'COLL', b'CLFM', b'REVB', b'PKIN',
            b'RFGP', b'AMDL', b'LAYR', b'COBJ', b'OMOD', b'MSWP', b'ZOOM',
            b'INNR', b'KSSM', b'AECH', b'SCCO', b'AORU', b'SCSN', b'STAG',
            b'NOCM', b'LENS', b'GDRY', b'OVIS',
        ]
        header_type.valid_header_sigs = (set(header_type.top_grup_sigs) |
            {b'GRUP', b'TES4', b'REFR', b'ACHR', b'PMIS', b'PARW', b'PGRE',
             b'PBEA', b'PFLA', b'PCON', b'PBAR', b'PHZD', b'LAND', b'NAVM',
             b'DIAL', b'INFO'})
        header_type.plugin_form_version = 131
        brec.MreRecord.type_class = {x.rec_sig: x for x in (
            MreTes4, MreGmst, MreLvli, MreLvln,
        )}
        brec.MreRecord.simpleTypes = (
            set(brec.MreRecord.type_class) - {b'TES4'})
        cls._validate_records()

GAME_TYPE = Fallout4GameInfo
