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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from os.path import join as _j

from .. import GameInfo, ObjectIndexRange, _SFPluginFlag
from ..patch_game import PatchGame
from ..store_mixins import SteamMixin, WindowsStoreMixin
from ... import bolt
from ...games_lo import AsteriskGame
from ...bolt import FName, fast_cached_property
from ...plugin_types import AMasterFlag

class _SFMasterFlag(AMasterFlag):
    # order matters for the ui keys
    BLUEPRINT = ('blueprint_flag', '_is_blueprint', 'b')
    ESM = ('esm_flag', '_is_master', 'm')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.name == 'BLUEPRINT':
            self.help_flip = _('Flip the BLUEPRINT flag on the selected '
                               'plugins.')

    @classmethod
    def sort_masters_key(cls, mod_inf) -> tuple[bool, ...]:
        """Return a key so that ESMs come first and blueprint masters last."""
        is_master = cls.ESM.cached_type(mod_inf)
        return is_master and cls.BLUEPRINT.cached_type(mod_inf), not is_master

class _AStarfieldGameInfo(PatchGame):
    """GameInfo override for Starfield."""
    display_name = 'Starfield'
    fsName = 'Starfield'
    altName = 'Wrye Stash'
    game_icon = 'starfield.svg'
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
    nexusUrl = 'https://www.nexusmods.com/starfield/'
    nexusName = 'Starfield Nexus'
    nexusKey = 'bash.installers.openStarfieldNexus.continue'

    espm_extensions = {*GameInfo.espm_extensions, '.esl'}
    has_achlist = True
    plugin_name_specific_dirs = GameInfo.plugin_name_specific_dirs + [
        _j('textures', 'actors', 'character', 'facecustomization'),
        _j('meshes', 'actors', 'character', 'facegendata', 'facegeom'),
    ]

    @staticmethod
    def get_fid_class(augmented_masters, in_overlay_plugin):
        # Overlay plugins (whose TES4 record header flags feature an
        # overlay_flag) can only contain overrides (any non-override records
        # in them will become injected into either the first plugin in the
        # master list or the first plugin in the whole LO - probably the
        # former) TODO(SF) check which of those two is true
        if not in_overlay_plugin:
            return super(_AStarfieldGameInfo, _AStarfieldGameInfo
                         ).get_fid_class(augmented_masters, in_overlay_plugin)
        overlay_threshold = len(augmented_masters) - 1
        from ...brec import FormId
        class _FormID(FormId):
            @fast_cached_property
            def long_fid(self, *, __masters=augmented_masters):
                try:
                    if self.mod_dex >= overlay_threshold:
                        # Overlay plugins can't have new records (or
                        # HITMEs), those get injected into the first
                        # master instead
                        return __masters[0], self.short_fid & 0xFFFFFF
                    return __masters[self.mod_dex], self.short_fid & 0xFFFFFF
                except IndexError:
                    # Clamp HITMEs to the plugin's own address space
                    return __masters[-1], self.short_fid & 0xFFFFFF
        return _FormID

    class Ck(GameInfo.Ck):
        ck_abbrev = 'CK'
        long_name = 'Creation Kit'
        exe = 'CreationKit.exe'
        image_name = 'creationkit%s.png' # TODO(SF) update icon

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
        start_dex_keys = {GameInfo.Ini.BSA_MIN: (
            'sResourceIndexFileList', 'sResourceStartUpArchiveList',
            'sResourceArchiveList',
        )}

    class Ess(GameInfo.Ess):
        ext = '.sfs'
        has_screenshots = False # TODO(SF) verify

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
            'dataviews', # Creation Kit
            'distantlod',
            'editorfiles', # Creation Kit
            'geometries',
            'interface',
            'lodsettings',
            'materials',
            'misc',
            'particles',
            'planetdata',
            'programs',
            'scripts',
            'seq',
            'sfse', # 3P: SFSE
            'shadersfx',
            'source', # Creation Kit
            'space',
            'strings',
            'terrain',
            'vis',
        }
        no_skip_dirs = GameInfo.Bain.no_skip_dirs | {
            # This rule is to allow mods with string translation enabled.
            _j('interface', 'translations'): {'.txt'},
        }
        skip_bain_refresh = {'sf1edit backups', 'sf1edit cache'}

    class Esp(GameInfo.Esp):
        extension_forces_flags = True
        # Because the FE slot is reserved for ESLs - yes, including in master
        # lists. Thanks, Bethesda
        master_limit = 253
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
        'creationkit - shaders.ba2',
        'oldmars - localization.ba2',
        'oldmars - textures.ba2',
        'oldmars.esm',
        'sfbgs003 - main.ba2',
        'sfbgs003 - textures.ba2',
        'sfbgs003 - voices_de.ba2',
        'sfbgs003 - voices_en.ba2',
        'sfbgs003 - voices_es.ba2',
        'sfbgs003 - voices_fr.ba2',
        'sfbgs003 - voices_ja.ba2',
        'sfbgs003.esm',
        'sfbgs004 - main.ba2',
        'sfbgs004 - textures.ba2',
        'sfbgs004 - voices_de.ba2',
        'sfbgs004 - voices_en.ba2',
        'sfbgs004 - voices_es.ba2',
        'sfbgs004 - voices_fr.ba2',
        'sfbgs004 - voices_ja.ba2',
        'sfbgs004.esm',
        'sfbgs006 - main.ba2',
        'sfbgs006 - textures.ba2',
        'sfbgs006.esm',
        'sfbgs007 - main.ba2',
        'sfbgs007.esm',
        'sfbgs008 - main.ba2',
        'sfbgs008.esm',
        'shatteredspace - main01.ba2',
        'shatteredspace - main02.ba2',
        'shatteredspace - textures.ba2',
        'shatteredspace - voices_en.ba2',
        'shatteredspace.esm',
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
        'starfield - lodtextures01.ba2',
        'starfield - lodtextures02.ba2',
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

    class _LoStarfield(AsteriskGame):
        force_load_first = tuple(map(FName, (
            'ShatteredSpace.esm', 'Constellation.esm', 'OldMars.esm',
            'SFBGS003.esm', 'SFBGS004.esm', 'SFBGS006.esm', 'SFBGS007.esm',
            'SFBGS008.esm', # 'BlueprintShips-Starfield.esm',
        )))
        # The game tries to read a Starfield.ccc already, but it's not present
        # yet. Also, official Creations are written to plugins.txt & can be
        # disabled & reordered in the LO.
        _ccc_filename = 'Starfield.ccc'

        def _rem_from_plugins_txt(self):
            # don't remove blueprint masters, let the game do that rather
            # than overwritte user edits (the ones we do remove are harcoded
            # and whatever the user has done with lo files does not seem to
            # matter, but Blueprint load order seems to be affected)
            act = self._active_if_present - {FName(
                'BlueprintShips-Starfield.esm')}
            # we won't remove Blueprint masters from plugins.txt but we need
            # to append them in lo if present so we don't warn
            blue = {k: v for k, v in self.mod_infos.items() if all(
                pf.cached_type(v) for pf in self._game_handle.master_flags)}
            blue = [t[0] for t in # sort blueprint masters ftime/mod ascending
                    sorted(blue.items(), key=lambda x: (x[1].ftime, x[0]))]
            return act, blue

        def _set_pinned_mods(self):
            """Override for making BlueprintShips.esm always active while not
            having a fixed position in the load order."""
            mbaip, fo_mods = super()._set_pinned_mods()
            mbaip.add(FName('BlueprintShips-Starfield.esm')) #active if present
            return mbaip, fo_mods

        def _get_ccc_path(self):
            from ... import bass
            if (mg_ccc := bass.dirs['saveBase'].join(self._ccc_filename
                                                     )).exists():
                return mg_ccc
            return super()._get_ccc_path()

    lo_handler = _LoStarfield

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)
        cls._import_records(__name__)

    def _init_plugin_types(self, pflags=None):
        self.master_flags = _SFMasterFlag
        super()._init_plugin_types(_SFPluginFlag)

class SteamStarfieldGameInfo(SteamMixin, _AStarfieldGameInfo):
    """GameInfo override for the Steam version of Starfield."""
    class St(_AStarfieldGameInfo.St):
        steam_ids = [1716740]

class WSStarfieldGameInfo(WindowsStoreMixin, _AStarfieldGameInfo):
    """GameInfo override for the Windows Store version of Starfield."""
    class Ws(_AStarfieldGameInfo.Ws):
        win_store_name = 'BethesdaSoftworks.ProjectGold'

GAME_TYPE = {g.unique_display_name: g for g in (
    SteamStarfieldGameInfo, WSStarfieldGameInfo)}
