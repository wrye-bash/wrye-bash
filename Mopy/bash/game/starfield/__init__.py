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
from os.path import join as _j

from .. import GameInfo, ObjectIndexRange
from ..patch_game import PatchGame
from ... import bolt

class StarfieldGameInfo(PatchGame):
    """GameInfo override for Starfield."""
    displayName = 'Starfield'
    fsName = 'Starfield'
    altName = 'Wrye Stash'
    game_icon = 'starfield_%u.png'
    bash_root_prefix = 'Starfield'
    bak_game_name = 'Starfield'
    my_games_name = 'Starfield'
    appdata_name = 'Starfield'
    launch_exe = 'Starfield.exe'
    game_detect_includes = {'Starfield.exe'}
    version_detect_file = 'Starfield.exe'
    master_file = bolt.FName('Starfield.esm')
    taglist_dir = 'Starfield'
    loot_dir = 'Starfield'
    loot_game_name = 'Starfield'
    # TODO(SF) doesn't seem to have one, we need to accelerate our new Steam
    #  detection method (plus that one will work on Linux too)
    registry_keys = []
    nexusUrl = 'https://www.nexusmods.com/starfield/'
    nexusName = 'Starfield Nexus'
    nexusKey = 'bash.installers.openStarfieldNexus.continue'

    espm_extensions = GameInfo.espm_extensions | {'.esl'}
    has_achlist = False # TODO(SF) check once CK is out
    check_esl = True
    plugin_name_specific_dirs = GameInfo.plugin_name_specific_dirs + [
        _j('textures', 'actors', 'character', 'facecustomization'),
        _j('meshes', 'actors', 'character', 'facegendata', 'facegeom'),
    ]

    class Ck(GameInfo.Ck): # TODO(SF) add once it exists
        pass

    class Se(GameInfo.Se):
        se_abbrev = 'SFSE'
        long_name = 'Starfield Script Extender'
        exe = 'sfse_loader.exe'
        ver_files = ['sfse_loader.exe', 'sfse_steam_loader.dll']
        plugin_dir = 'SFSE'
        cosave_tag = 'SFSE'
        cosave_ext = '.sfse'
        url = 'https://sfse.silverlock.org/'
        url_tip = 'https://sfse.silverlock.org/'

    class Ini(GameInfo.Ini):
        default_ini_file = 'Starfield.ini' # TODO(SF) verify
        default_game_lang = 'en'
        # TODO(SF) there is no Starfield.ini in My Games, should we somehow
        #  generate a StarfieldCustom.ini instead? Or will our copying of
        #  Starfield.ini work?
        dropdown_inis = ['StarfieldPrefs.ini']
        resource_archives_keys = (
            'sResourceIndexFileList', 'sResourceStartUpArchiveList',
            'sResourceArchiveList',
        )

    class Ess(GameInfo.Ess):
        ext = '.sfs'
        # TODO(SF) Did the screenshot get moved or does it just not exist
        #  anymore? ssWidth and ssHeight do seem to exist, but they are now
        #  always 0
        has_screenshots = False

    class Bsa(GameInfo.Bsa):
        bsa_extension = '.ba2'
        valid_versions = {0x02, 0x03}

    class Psc(GameInfo.Psc):
        source_extensions = {'.psc'}

    class Xe(GameInfo.Xe):
        full_name = 'SF1Edit'
        xe_key_prefix = 'sf1View' # TODO(SF) verify

    class Bain(GameInfo.Bain):
        data_dirs = GameInfo.Bain.data_dirs | {
            # TODO(SF) verify vanilla dirs
            'interface',
            'lodsettings',
            'materials',
            'misc',
            'programs',
            'scripts',
            'seq',
            'sfse', # 3P: SFSE
            'shadersfx',
            'strings',
            'vis',
        }
        no_skip_dirs = GameInfo.Bain.no_skip_dirs | {
            # This rule is to allow mods with string translation enabled.
            _j('interface', 'translations'): {'.txt'},
        }
        skip_bain_refresh = {'sf1edit backups', 'sf1edit cache'}

    class Esp(GameInfo.Esp):
        extension_forces_flags = True
        max_lvl_list_size = 255
        object_index_range = ObjectIndexRange.EXPANDED_ALWAYS
        validHeaderVersions = (0.96,)

    allTags = set()

    bethDataFiles = {
        'blueprintships-starfield - localization.ba2',
        'blueprintships-starfield.esm',
        'constellation - localization.ba2',
        'constellation - textures.ba2',
        'constellation.esm',
        'oldmars - localization.ba2',
        'oldmars - textures.ba2',
        'oldmars.esm',
        'starfield - animations.ba2',
        'starfield - densitymaps.ba2',
        'starfield - faceanimation01.ba2',
        'starfield - faceanimation02.ba2',
        'starfield - faceanimation03.ba2',
        'starfield - faceanimation04.ba2',
        'starfield - faceanimationpatch.ba2',
        'starfield - facemeshes.ba2',
        'starfield - generatedtextures.ba2',
        'starfield - interface.ba2',
        'starfield - lodmeshes.ba2',
        'starfield - lodmeshespatch.ba2',
        'starfield - lodtextures.ba2',
        'starfield - localization.ba2',
        'starfield - materials.ba2',
        'starfield - meshes01.ba2',
        'starfield - meshes02.ba2',
        'starfield - meshespatch.ba2',
        'starfield - misc.ba2',
        'starfield - particles.ba2',
        'starfield - particlestestdata.ba2',
        'starfield - planetdata.ba2',
        'starfield - shaders.ba2',
        'starfield - shadersbeta.ba2',
        'starfield - terrain01.ba2',
        'starfield - terrain02.ba2',
        'starfield - terrain03.ba2',
        'starfield - terrain04.ba2',
        'starfield - terrainpatch.ba2',
        'starfield - textures01.ba2',
        'starfield - textures02.ba2',
        'starfield - textures03.ba2',
        'starfield - textures04.ba2',
        'starfield - textures05.ba2',
        'starfield - textures06.ba2',
        'starfield - textures07.ba2',
        'starfield - textures08.ba2',
        'starfield - textures09.ba2',
        'starfield - textures10.ba2',
        'starfield - textures11.ba2',
        'starfield - texturespatch.ba2',
        'starfield - voices01.ba2',
        'starfield - voices02.ba2',
        'starfield - voicespatch.ba2',
        'starfield - wwisesounds01.ba2',
        'starfield - wwisesounds02.ba2',
        'starfield - wwisesounds03.ba2',
        'starfield - wwisesounds04.ba2',
        'starfield - wwisesounds05.ba2',
        'starfield - wwisesoundspatch.ba2',
        'starfield.esm',
    }

    # Function Info -----------------------------------------------------------
    # 0: no param; 1: int param; 2: FormID param; 3: float param
    # Third parameter is always sint32, so no need to specify here
    condition_function_data = {
        # TODO(SF) fill out once dumped
        0:  ('ADD_FUNCTIONS_HERE', 0, 0),
    }
    getvatsvalue_index = 0 # TODO(SF) fill out once dumped

    top_groups = [
        b'GMST', b'KYWD', b'FFKW', b'LCRT', b'AACT', b'TRNS', b'TXST', b'GLOB',
        b'DMGT', b'CLAS', b'FACT', b'AFFE', b'HDPT', b'RACE', b'SOUN', b'SECH',
        b'ASPC', b'AOPF', b'MGEF', b'LTEX', b'PDCL', b'ENCH', b'SPEL', b'ACTI',
        b'CURV', b'CUR3', b'ARMO', b'BOOK', b'CONT', b'DOOR', b'LIGH', b'MISC',
        b'STAT', b'SCOL', b'PKIN', b'MSTT', b'GRAS', b'FLOR', b'FURN', b'WEAP',
        b'AMMO', b'NPC_', b'LVLN', b'LVLP', b'KEYM', b'ALCH', b'IDLM', b'BMMO',
        b'PROJ', b'HAZD', b'BNDS', b'TERM', b'LVLI', b'GBFT', b'GBFM', b'LVLB',
        b'WTHR', b'WTHS', b'CLMT', b'SPGD', b'REGN', b'NAVI', b'CELL', b'WRLD',
        b'NAVM', b'DIAL', b'INFO', b'QUST', b'IDLE', b'PACK', b'CSTY', b'LSCR',
        b'ANIO', b'WATR', b'EFSH', b'EXPL', b'DEBR', b'IMGS', b'IMAD', b'FLST',
        b'PERK', b'BPTD', b'ADDN', b'AVIF', b'CAMS', b'CPTH', b'VTYP', b'MATT',
        b'IPCT', b'IPDS', b'ARMA', b'LCTN', b'MESG', b'DOBJ', b'DFOB', b'LGTM',
        b'MUSC', b'FSTP', b'FSTS', b'SMBN', b'SMQN', b'SMEN', b'DLBR', b'MUST',
        b'EQUP', b'SCEN', b'OTFT', b'ARTO', b'MOVT', b'COLL', b'CLFM', b'REVB',
        b'RFGP', b'PERS', b'AMDL', b'AAMD', b'MAAM', b'LAYR', b'COBJ', b'OMOD',
        b'ZOOM', b'INNR', b'KSSM', b'AORU', b'STAG', b'IRES', b'BIOM', b'NOCM',
        b'LENS', b'OVIS', b'STND', b'STMP', b'GCVR', b'MRPH', b'TRAV', b'RSGD',
        b'OSWP', b'ATMO', b'LVSC', b'SPCH', b'AAPD', b'VOLI', b'SFBK', b'SFPC',
        b'SFPT', b'SFTR', b'PCMT', b'BMOD', b'STBH', b'PNDT', b'CNDF', b'PCBN',
        b'PCCN', b'STDT', b'WWED', b'RSPJ', b'AOPS', b'AMBS', b'WBAR', b'PTST',
        b'LMSW', b'FORC', b'TMLM', b'EFSQ', b'SDLT', b'MTPT', b'CLDF', b'FOGV',
        b'WKMF', b'LGDI', b'PSDC', b'SUNP', b'PMFT', b'TODD', b'AVMD', b'CHAL',
    ]
    complex_groups = {b'CELL', b'WRLD', b'DIAL', b'QUST'} # TODO(SF) verify

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)
        cls._import_records(__name__)

GAME_TYPE = StarfieldGameInfo
