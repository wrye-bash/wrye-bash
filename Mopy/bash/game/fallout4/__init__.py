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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""GameInfo override for Fallout 4."""

from os.path import join as _j

from ..patch_game import GameInfo, PatchGame
from .. import WS_COMMON
from ... import brec, bolt

class Fallout4GameInfo(PatchGame):
    displayName = u'Fallout 4'
    fsName = u'Fallout4'
    altName = u'Wrye Flash'
    game_icon = u'fallout4_%u.png'
    bash_root_prefix = u'Fallout4'
    bak_game_name = u'Fallout4'
    my_games_name = u'Fallout4'
    appdata_name = u'Fallout4'
    launch_exe = u'Fallout4.exe'
    game_detect_includes = [u'Fallout4.exe']
    game_detect_excludes = WS_COMMON
    version_detect_file = u'Fallout4.exe'
    master_file = bolt.FName(u'Fallout4.esm')
    taglist_dir = u'Fallout4'
    loot_dir = u'Fallout4'
    loot_game_name = 'Fallout4'
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
            'f4se', # 3P: F4SE
            'interface',
            'lodsettings',
            'materials',
            'mcm', # 3P: FO4 MCM
            'misc',
            'programs',
            'scripts',
            'seq',
            'shadersfx',
            'strings',
            'tools', # 3P: BodySlide
            'vis',
        }
        no_skip_dirs = GameInfo.Bain.no_skip_dirs | {
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
        reference_types = {b'ACHR', b'PARW', b'PBAR', b'PBEA', b'PCON',
                           b'PFLA', b'PGRE', b'PHZD', b'PMIS', b'REFR'}

    patchers = {
        u'ImportObjectBounds', u'LeveledLists',
    }

    bethDataFiles = {
        'dlccoast - geometry.csg',
        'dlccoast - main.ba2',
        'dlccoast - textures.ba2',
        'dlccoast - voices_de.ba2',
        'dlccoast - voices_en.ba2',
        'dlccoast - voices_es.ba2',
        'dlccoast - voices_fr.ba2',
        'dlccoast - voices_it.ba2',
        'dlccoast - voices_ja.ba2',
        'dlccoast.cdx',
        'dlccoast.esm',
        'dlcnukaworld - geometry.csg',
        'dlcnukaworld - main.ba2',
        'dlcnukaworld - textures.ba2',
        'dlcnukaworld - voices_de.ba2',
        'dlcnukaworld - voices_en.ba2',
        'dlcnukaworld - voices_es.ba2',
        'dlcnukaworld - voices_fr.ba2',
        'dlcnukaworld - voices_it.ba2',
        'dlcnukaworld - voices_ja.ba2',
        'dlcnukaworld.cdx',
        'dlcnukaworld.esm',
        'dlcrobot - geometry.csg',
        'dlcrobot - main.ba2',
        'dlcrobot - textures.ba2',
        'dlcrobot - voices_de.ba2',
        'dlcrobot - voices_en.ba2',
        'dlcrobot - voices_es.ba2',
        'dlcrobot - voices_fr.ba2',
        'dlcrobot - voices_it.ba2',
        'dlcrobot - voices_ja.ba2',
        'dlcrobot.cdx',
        'dlcrobot.esm',
        'dlcworkshop01 - geometry.csg',
        'dlcworkshop01 - main.ba2',
        'dlcworkshop01 - textures.ba2',
        'dlcworkshop02 - main.ba2',
        'dlcworkshop02 - textures.ba2',
        'dlcworkshop03 - geometry.csg',
        'dlcworkshop03 - main.ba2',
        'dlcworkshop03 - textures.ba2',
        'dlcworkshop03 - voices_de.ba2',
        'dlcworkshop03 - voices_en.ba2',
        'dlcworkshop03 - voices_es.ba2',
        'dlcworkshop03 - voices_fr.ba2',
        'dlcworkshop03 - voices_it.ba2',
        'dlcworkshop03 - voices_ja.ba2',
        'dlcworkshop01.cdx',
        'dlcworkshop01.esm',
        'dlcworkshop02.esm',
        'dlcworkshop03.cdx',
        'dlcworkshop03.esm',
        'fallout4 - animations.ba2',
        'fallout4 - geometry.csg',
        'fallout4 - interface.ba2',
        'fallout4 - materials.ba2',
        'fallout4 - meshes.ba2',
        'fallout4 - meshesextra.ba2',
        'fallout4 - misc.ba2',
        'fallout4 - nvflex.ba2',
        'fallout4 - shaders.ba2',
        'fallout4 - sounds.ba2',
        'fallout4 - startup.ba2',
        'fallout4 - textures1.ba2',
        'fallout4 - textures2.ba2',
        'fallout4 - textures3.ba2',
        'fallout4 - textures4.ba2',
        'fallout4 - textures5.ba2',
        'fallout4 - textures6.ba2',
        'fallout4 - textures7.ba2',
        'fallout4 - textures8.ba2',
        'fallout4 - textures9.ba2',
        'fallout4 - voices.ba2',
        'fallout4 - voices_de.ba2',
        'fallout4 - voices_es.ba2',
        'fallout4 - voices_fr.ba2',
        'fallout4 - voices_it.ba2',
        'fallout4 - voices_rep.ba2',
        'fallout4.cdx',
        'fallout4.esm',
    }

    @classmethod
    def init(cls):
        cls._dynamic_import_modules(__name__)
        from .records import MreAact, MreActi, MreAddn, MreAech, MreAmdl, \
            MreAnio, MreAoru, MreArma, MreArmo, \
            MreGmst, MreLvli, MreLvln, MrePerk, MreTes4
        cls.mergeable_sigs = {clazz.rec_sig: clazz for clazz in (
            MreAact, MreActi, MreAddn, MreAech, MreAmdl, MreAnio, MreAoru,
            MreArma, MreArmo,
            MreGmst, MreLvli, MreLvln, MrePerk,
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
            MreAact, MreActi, MreAddn, MreAech, MreAmdl, MreAnio, MreAoru,
            MreArma, MreArmo,
            MreGmst, MreLvli, MreLvln, MrePerk, MreTes4,
        )}
        brec.MreRecord.simpleTypes = (
            set(brec.MreRecord.type_class) - {b'TES4'})
        cls._validate_records()

GAME_TYPE = Fallout4GameInfo
