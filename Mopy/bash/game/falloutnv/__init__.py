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
"""GameInfo override for Fallout NV."""

from collections import defaultdict

from ..fallout3 import Fallout3GameInfo
from ... import brec
from ...brec import MreFlst, MreGlob

class FalloutNVGameInfo(Fallout3GameInfo):
    displayName = u'Fallout New Vegas'
    fsName = u'FalloutNV'
    altName = u'Wrye Flash NV'
    game_icon = u'falloutnv_%u.png'
    bash_root_prefix = u'FalloutNV'
    bak_game_name = u'FalloutNV'
    my_games_name = u'FalloutNV'
    appdata_name = u'FalloutNV'
    launch_exe = u'FalloutNV.exe'
    game_detect_includes = [u'FalloutNV.exe']
    version_detect_file = u'FalloutNV.exe'
    master_file = u'FalloutNV.esm'
    taglist_dir = u'FalloutNV'
    loot_dir = u'FalloutNV'
    boss_game_name = u'FalloutNV'
    regInstallKeys = (u'Bethesda Softworks\\FalloutNV',u'Installed Path')
    nexusUrl = u'https://www.nexusmods.com/newvegas/'
    nexusName = u'New Vegas Nexus'
    nexusKey = u'bash.installers.openNewVegasNexus.continue'

    class Se(Fallout3GameInfo.Se):
        se_abbrev = u'NVSE'
        long_name = u'New Vegas Script Extender'
        exe = u'nvse_loader.exe'
        ver_files = [u'nvse_loader.exe', u'nvse_steam_loader.dll']
        plugin_dir = u'NVSE'
        cosave_tag = u'NVSE'
        cosave_ext = u'.nvse'
        url = u'http://nvse.silverlock.org/'
        url_tip = u'http://nvse.silverlock.org/'

    class Bsa(Fallout3GameInfo.Bsa):
        redate_dict = defaultdict(lambda: 1136066400, { # '2006-01-01'
            u'Fallout - Meshes.bsa': 1104530400,    # '2005-01-01'
            u'Fallout - Meshes2.bsa': 1104616800,   # '2005-01-02'
            u'Fallout - Misc.bsa': 1104703200,      # '2005-01-03'
            u'Fallout - Sound.bsa': 1104789600,     # '2005-01-04'
            u'Fallout - Textures.bsa': 1104876000,  # '2005-01-05'
            u'Fallout - Textures2.bsa': 1104962400, # '2005-01-06'
            u'Fallout - Voices1.bsa': 1105048800,   # '2005-01-07'
        })

    class Xe(Fallout3GameInfo.Xe):
        full_name = u'FNVEdit'
        xe_key_prefix = u'fnvView'

    class Bain(Fallout3GameInfo.Bain):
        data_dirs = (Fallout3GameInfo.Bain.data_dirs - {u'fose'}) | {u'nvse'}
        skip_bain_refresh = {u'fnvedit backups', u'fnvedit cache'}

    class Esp(Fallout3GameInfo.Esp):
        validHeaderVersions = (0.94, 1.32, 1.33, 1.34)

    allTags = Fallout3GameInfo.allTags | {u'WeaponMods'}
    patchers = Fallout3GameInfo.patchers | {u'ImportWeaponModifications'}

    bethDataFiles = {
        #--Vanilla
        u'falloutnv.esm',
        u'fallout - invalidation.bsa',
        u'fallout - meshes.bsa',
        u'fallout - meshes2.bsa',
        u'fallout - misc.bsa',
        u'fallout - sound.bsa',
        u'fallout - textures.bsa',
        u'fallout - textures2.bsa',
        u'fallout - voices1.bsa',
        #--Preorder Packs
        u'caravanpack.esm',
        u'caravanpack - main.bsa',
        u'classicpack.esm',
        u'classicpack - main.bsa',
        u'mercenarypack.esm',
        u'mercenarypack - main.bsa',
        u'tribalpack.esm',
        u'tribalpack - main.bsa',
        #--DLCs
        u'deadmoney.esm',
        u'deadmoney - main.bsa',
        u'deadmoney - sounds.bsa',
        u'gunrunnersarsenal.esm',
        u'gunrunnersarsenal - main.bsa',
        u'gunrunnersarsenal - sounds.bsa',
        u'honesthearts.esm',
        u'honesthearts - main.bsa',
        u'honesthearts - sounds.bsa',
        u'oldworldblues.esm',
        u'oldworldblues - main.bsa',
        u'oldworldblues - sounds.bsa',
        u'lonesomeroad.esm',
        u'lonesomeroad - main.bsa',
        u'lonesomeroad - sounds.bsa',
    }

    @classmethod
    def _dynamic_import_modules(cls, package_name):
        super(FalloutNVGameInfo, cls)._dynamic_import_modules(package_name)
        from .patcher import preservers
        cls.game_specific_import_patchers = {
            u'ImportWeaponModifications':
                preservers.ImportWeaponModificationsPatcher,
        }

    @classmethod
    def init(cls):
        cls._dynamic_import_modules(__name__)
        # First import from our records file
        from .records import MreTes4, MreAloc, MreAmef, MreCcrd, MreCdck, \
            MreChal, MreChip, MreCmny, MreCsno, MreDehy, MreDial, MreHung, \
            MreImod, MreLsct, MreMset, MreRcct, MreRcpe, MreRepu, MreSlpd, \
            MreWthr
        # Then from fallout3.records
        from ..fallout3.records import MreCpth, MreIdle, MreMesg, MrePack, \
            MrePerk, MreQust, MreSpel, MreTerm, MreNpc, MreAddn, MreAnio, \
            MreAvif, MreBook, MreBptd, MreCams, MreClas, MreClmt, MreCobj, \
            MreCrea, MreDebr, MreDoor, MreEczn, MreEfsh, MreExpl, MreEyes, \
            MreFurn, MreGras, MreHair, MreIdlm, MreImgs, MreIngr, MreRace, \
            MreIpds, MreLgtm, MreLtex, MreLvlc, MreLvli, MreLvln, MreMgef, \
            MreMicn, MreMstt, MreNavi, MreNavm, MreNote, MrePwat, MreRads, \
            MreRgdl, MreScol, MreScpt, MreTree, MreTxst, MreVtyp, MreWatr, \
            MreWrld, MreAlch, MreActi, MreAmmo, MreArma, MreArmo, MreAspc, \
            MreCont, MreAchr, MreAcre, MreCell, MreCsty, MreDobj, MreEnch, \
            MreFact, MreGmst, MreHdpt, MreImad, MreInfo, MreIpct, MreKeym, \
            MreLigh, MreLscr, MreMisc, MreMusc, MrePgre, MrePmis, MreProj, \
            MreRefr, MreRegn, MreSoun, MreStat, MreTact, MreWeap
        cls.mergeable_sigs = {clazz.rec_sig: clazz for clazz in (
            MreActi, MreAddn, MreAlch, MreAloc, MreAmef, MreAmmo, MreAnio,
            MreArma, MreArmo, MreAspc, MreAvif, MreBook, MreBptd, MreCams,
            MreCcrd, MreCdck, MreChal, MreChip, MreClas, MreClmt, MreCmny,
            MreCobj, MreCont, MreCpth, MreCrea, MreCsno, MreCsty, MreDebr,
            MreDehy, MreDobj, MreDoor, MreEczn, MreEfsh, MreEnch, MreExpl,
            MreEyes, MreFact, MreFlst, MreFurn, MreGlob, MreGras, MreHair,
            MreHdpt, MreHung, MreIdle, MreIdlm, MreImad, MreImgs, MreImod,
            MreIngr, MreIpct, MreIpds, MreKeym, MreLgtm, MreLigh, MreLscr,
            MreLsct, MreLtex, MreLvlc, MreLvli, MreLvln, MreMesg, MreMgef,
            MreMicn, MreMisc, MreMset, MreMstt, MreMusc, MreNote, MreNpc,
            MrePack, MrePerk, MreProj, MrePwat, MreQust, MreRace, MreRads,
            MreRcct, MreRcpe, MreRegn, MreRepu, MreRgdl, MreScol, MreScpt,
            MreSlpd, MreSoun, MreSpel, MreStat, MreTact, MreTerm, MreTree,
            MreTxst, MreVtyp, MreWatr, MreWeap, MreWthr, MreGmst,
        )}
        # Setting RecordHeader class variables --------------------------------
        header_type = brec.RecordHeader
        header_type.top_grup_sigs = [
            b'GMST', b'TXST', b'MICN', b'GLOB', b'CLAS', b'FACT', b'HDPT',
            b'HAIR', b'EYES', b'RACE', b'SOUN', b'ASPC', b'MGEF', b'SCPT',
            b'LTEX', b'ENCH', b'SPEL', b'ACTI', b'TACT', b'TERM', b'ARMO',
            b'BOOK', b'CONT', b'DOOR', b'INGR', b'LIGH', b'MISC', b'STAT',
            b'SCOL', b'MSTT', b'PWAT', b'GRAS', b'TREE', b'FURN', b'WEAP',
            b'AMMO', b'NPC_', b'CREA', b'LVLC', b'LVLN', b'KEYM', b'ALCH',
            b'IDLM', b'NOTE', b'COBJ', b'PROJ', b'LVLI', b'WTHR', b'CLMT',
            b'REGN', b'NAVI', b'DIAL', b'QUST', b'IDLE', b'PACK', b'CSTY',
            b'LSCR', b'ANIO', b'WATR', b'EFSH', b'EXPL', b'DEBR', b'IMGS',
            b'IMAD', b'FLST', b'PERK', b'BPTD', b'ADDN', b'AVIF', b'RADS',
            b'CAMS', b'CPTH', b'VTYP', b'IPCT', b'IPDS', b'ARMA', b'ECZN',
            b'MESG', b'RGDL', b'DOBJ', b'LGTM', b'MUSC', b'IMOD', b'REPU',
            b'RCPE', b'RCCT', b'CHIP', b'CSNO', b'LSCT', b'MSET', b'ALOC',
            b'CHAL', b'AMEF', b'CCRD', b'CMNY', b'CDCK', b'DEHY', b'HUNG',
            b'SLPD', b'CELL', b'WRLD',
        ]
        header_type.valid_header_sigs = set(
            header_type.top_grup_sigs + [b'GRUP', b'TES4', b'ACHR', b'ACRE',
                                         b'INFO', b'LAND', b'NAVM', b'PGRE',
                                         b'PMIS', b'REFR'])
        header_type.plugin_form_version = 15
        brec.MreRecord.type_class = {x.rec_sig: x for x in ( # Not Mergeable
            (MreAchr, MreAcre, MreCell, MreDial, MreInfo, MreNavi, MreNavm,
             MrePgre, MrePmis, MreRefr, MreWrld, MreTes4,))}
        brec.MreRecord.type_class.update(cls.mergeable_sigs)
        brec.MreRecord.simpleTypes = (
            set(brec.MreRecord.type_class) - {
            b'TES4', b'ACHR', b'ACRE', b'CELL', b'DIAL', b'INFO', b'LAND',
            b'NAVI', b'NAVM', b'PGRE', b'PMIS', b'REFR', b'WRLD'})
        cls._validate_records()

GAME_TYPE = FalloutNVGameInfo
