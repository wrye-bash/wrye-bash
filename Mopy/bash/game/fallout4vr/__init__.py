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
"""GameInfo override for Fallout 4 VR. Inherits from Fallout 4 and tweaks where
necessary."""

from ..fallout4 import Fallout4GameInfo
from ... import brec

class Fallout4VRGameInfo(Fallout4GameInfo):
    displayName = u'Fallout 4 VR'
    fsName = u'Fallout4VR'
    altName = u'Wrye VRash'
    bash_root_prefix = u'Fallout4VR'
    launch_exe = u'Fallout4VR.exe'
    game_detect_files = [u'Fallout4VR.exe']
    version_detect_file = u'Fallout4VR.exe'
    master_file = u'Fallout4.esm'
    regInstallKeys = (u'Bethesda Softworks\\Fallout 4 VR', u'Installed Path')

    espm_extensions = Fallout4GameInfo.espm_extensions - {u'.esl'}
    check_esl = False

    class Ws(Fallout4GameInfo.Ws):
        # Fallout 4 VR has no Windows Store version, don't
        # implicitely use Fallout 4's information
        publisher_name = u''
        win_store_name = u''

    class Se(Fallout4GameInfo.Se):
        se_abbrev = u'F4SEVR'
        long_name = u'Fallout 4 VR Script Extender'
        exe = u'f4sevr_loader.exe'
        ver_files = [u'f4sevr_loader.exe', u'f4sevr_steam_loader.dll']

    class Ini(Fallout4GameInfo.Ini):
        default_ini_file = u'Fallout4.ini' ##: why not Fallout4_default.ini?
        dropdown_inis = Fallout4GameInfo.Ini.dropdown_inis + [
            u'Fallout4VrCustom.ini'] ##: why is this here?

    class Xe(Fallout4GameInfo.Xe):
        full_name = u'FO4VREdit'
        xe_key_prefix = u'fo4vrView'

    class Bain(Fallout4GameInfo.Bain):
        skip_bain_refresh = {u'fo4vredit backups', u'fo4vredit cache'}

    class Esp(Fallout4GameInfo.Esp):
        validHeaderVersions = (0.95,)
        expanded_plugin_range = False

    allTags = Fallout4GameInfo.allTags | {u'NoMerge'}
    patchers = Fallout4GameInfo.patchers | {u'MergePatches'}

    bethDataFiles = {
        u'fallout4.esm',
        u'fallout4.cdx',
        u'fallout4 - animations.ba2',
        u'fallout4 - geometry.csg',
        u'fallout4 - interface.ba2',
        u'fallout4 - materials.ba2',
        u'fallout4 - meshes.ba2',
        u'fallout4 - meshesextra.ba2',
        u'fallout4 - misc.ba2',
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
        u'fallout4_vr.esm',
        u'fallout4_vr - main.ba2',
        u'fallout4_vr - shaders.ba2',
        u'fallout4_vr - textures.ba2',
    }

    # ---------------------------------------------------------------------
    # --Imported - MreGlob is special import, not in records.py
    # ---------------------------------------------------------------------
    _patcher_package = u'bash.game.fallout4'
    @classmethod
    def init(cls):
        cls._dynamic_import_modules(__name__)
        # First import FO4VR-specific record classes
        from .records import MreTes4
        # Then import from fallout4.records file
        from ..fallout4.records import MreGmst, MreLvli, MreLvln
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

GAME_TYPE = Fallout4VRGameInfo
