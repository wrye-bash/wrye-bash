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
"""GameInfo override for Fallout 4 VR. Inherits from Fallout 4 and tweaks where
necessary."""

from ..fallout4 import Fallout4GameInfo
from ... import bolt

class Fallout4VRGameInfo(Fallout4GameInfo):
    displayName = u'Fallout 4 VR'
    fsName = u'Fallout4VR'
    game_icon = u'fallout4vr_%u.png'
    altName = u'Wrye VRash'
    bash_root_prefix = u'Fallout4VR'
    bak_game_name = u'Fallout4VR'
    my_games_name = u'Fallout4VR'
    appdata_name = u'Fallout4VR'
    launch_exe = u'Fallout4VR.exe'
    game_detect_includes = {'Fallout4VR.exe'}
    version_detect_file = u'Fallout4VR.exe'
    master_file = bolt.FName(u'Fallout4.esm')
    taglist_dir = 'Fallout4VR'
    loot_dir = u'Fallout4VR'
    loot_game_name = 'Fallout4VR'
    registry_keys = [(r'Bethesda Softworks\Fallout 4 VR', 'Installed Path')]

    espm_extensions = Fallout4GameInfo.espm_extensions - {u'.esl'}
    check_esl = False

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
        expanded_plugin_range = False
        validHeaderVersions = (0.95,)

    allTags = Fallout4GameInfo.allTags | {u'NoMerge'}
    patchers = Fallout4GameInfo.patchers | {u'MergePatches'}

    bethDataFiles = Fallout4GameInfo.bethDataFiles | {
        'fallout4 - misc - beta.ba2',
        'fallout4 - misc - debug.ba2',
        'fallout4_vr - main.ba2',
        'fallout4_vr - shaders.ba2',
        'fallout4_vr - textures.ba2',
        'fallout4_vr.esm',
    }

    # ---------------------------------------------------------------------
    # --Imported - MreGlob is special import, not in records.py
    # ---------------------------------------------------------------------
    @classmethod
    def init(cls):
        cls._dynamic_import_modules(__name__)
        from ...brec import MreGmst
        from .records import MreTes4
        from ..fallout4.records import MreLvli, MreLvln
        cls.mergeable_sigs = {x.rec_sig: x for x in (
            MreGmst, MreLvli, MreLvln,
        )}
        # Setting RecordHeader class variables --------------------------------
        from ... import brec
        header_type = brec.RecordHeader
        header_type.top_grup_sigs = [
            b'GMST', b'KYWD', b'LCRT', b'AACT', b'TRNS', b'CMPO', b'TXST',
            b'GLOB', b'DMGT', b'CLAS', b'FACT', b'HDPT', b'EYES', b'RACE',
            b'SOUN', b'ASPC', b'MGEF', b'LTEX', b'ENCH', b'SPEL', b'ACTI',
            b'TACT', b'ARMO', b'BOOK', b'CONT', b'DOOR', b'INGR', b'LIGH',
            b'MISC', b'STAT', b'SCOL', b'MSTT', b'GRAS', b'TREE', b'FLOR',
            b'FURN', b'WEAP', b'AMMO', b'NPC_', b'LVLN', b'KEYM', b'ALCH',
            b'IDLM', b'NOTE', b'PROJ', b'HAZD', b'BNDS', b'TERM', b'LVLI',
            b'WTHR', b'CLMT', b'SPGD', b'RFCT', b'REGN', b'NAVI', b'CELL',
            b'WRLD', b'QUST', b'IDLE', b'PACK', b'CSTY', b'LSCR', b'LVSP',
            b'ANIO', b'WATR', b'EFSH', b'EXPL', b'DEBR', b'IMGS', b'IMAD',
            b'FLST', b'PERK', b'BPTD', b'ADDN', b'AVIF', b'CAMS', b'CPTH',
            b'VTYP', b'MATT', b'IPCT', b'IPDS', b'ARMA', b'ECZN', b'LCTN',
            b'MESG', b'DOBJ', b'DFOB', b'LGTM', b'MUSC', b'FSTP', b'FSTS',
            b'SMBN', b'SMQN', b'SMEN', b'DLBR', b'MUST', b'DLVW', b'EQUP',
            b'RELA', b'SCEN', b'ASTP', b'OTFT', b'ARTO', b'MATO', b'MOVT',
            b'SNDR', b'DUAL', b'SNCT', b'SOPM', b'COLL', b'CLFM', b'REVB',
            b'PKIN', b'RFGP', b'AMDL', b'LAYR', b'COBJ', b'OMOD', b'MSWP',
            b'ZOOM', b'INNR', b'KSSM', b'AECH', b'SCCO', b'AORU', b'SCSN',
            b'STAG', b'NOCM', b'LENS', b'GDRY', b'OVIS',
        ]
        from ..fallout4.records import MreCell ## todo just added for ref_types
        header_type.valid_header_sigs = {*header_type.top_grup_sigs,
            *MreCell.ref_types, b'INFO', b'GRUP', b'NAVM', b'LAND', b'DIAL', ## todo DIAL??
                                         b'TES4'}
        header_type.plugin_form_version = 131
        brec.MreRecord.type_class = {x.rec_sig: x for x in ( # Not mergeable
            (MreTes4,))}
        brec.MreRecord.type_class.update(cls.mergeable_sigs)
        brec.MreRecord.simpleTypes = (
            set(brec.MreRecord.type_class) - {b'TES4'})
        cls._validate_records()

GAME_TYPE = Fallout4VRGameInfo
