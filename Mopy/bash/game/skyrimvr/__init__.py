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

"""GameInfo override for TES V: Skyrim VR."""

from ..skyrimse import SkyrimSEGameInfo
from ... import brec
from ...brec import MreFlst, MreGlob

class SkyrimVRGameInfo(SkyrimSEGameInfo):
    displayName = u'Skyrim VR'
    fsName = u'Skyrim VR'
    altName = u'Wrye VRash'
    game_icon = u'skyrimvr_%u.png'
    bash_root_prefix = u'Skyrim VR' # backwards compat :(
    bak_game_name = u'Skyrim VR'
    my_games_name = u'Skyrim VR'
    appdata_name = u'Skyrim VR'
    launch_exe = u'SkyrimVR.exe'
    game_detect_includes = [u'SkyrimVR.exe']
    version_detect_file = u'SkyrimVR.exe'
    loot_dir = u'Skyrim VR'
    regInstallKeys = (u'Bethesda Softworks\\Skyrim VR', u'Installed Path')

    espm_extensions = SkyrimSEGameInfo.espm_extensions - {u'.esl'}
    check_esl = False

    class Se(SkyrimSEGameInfo.Se):
        se_abbrev = u'SKSEVR'
        long_name = u'Skyrim VR Script Extender'
        exe = u'sksevr_loader.exe'
        ver_files = [u'sksevr_loader.exe', u'sksevr_steam_loader.dll']

    class Ini(SkyrimSEGameInfo.Ini):
        default_ini_file = u'Skyrim.ini' # yes, that's the default one
        dropdown_inis = [u'SkyrimVR.ini', u'SkyrimPrefs.ini']
        resource_override_key = u'sVrResourceArchiveList'
        resource_override_defaults = [u'Skyrim_VR - Main.bsa']

    class Xe(SkyrimSEGameInfo.Xe):
        full_name = u'TES5VREdit'
        xe_key_prefix = u'tes5vrview'

    class Bain(SkyrimSEGameInfo.Bain):
        skip_bain_refresh = {u'tes5vredit backups', u'tes5vredit cache'}

    allTags = SkyrimSEGameInfo.allTags | {u'NoMerge'}
    patchers = SkyrimSEGameInfo.patchers | {u'MergePatches'}

    bethDataFiles = SkyrimSEGameInfo.bethDataFiles | {
        'skyrimvr.esm',
        'skyrim_vr - main.bsa',
    }

    @classmethod
    def init(cls):
        cls._dynamic_import_modules(__name__)
        # First import from skyrimse.records file
        from ..skyrimse.records import MreVoli, MreLens
        # then import rest of records from skyrim.records
        from ..skyrim.records import MreAact, MreAchr, MreActi, MreAddn, \
            MreAlch, MreAnio, MreAppa, MreArma, MreArmo, MreArto, MreAspc, \
            MreAstp, MreAvif, MreBook, MreBptd, MreCams, MreCell, MreClas, \
            MreClfm, MreClmt, MreCobj, MreColl, MreCont, MreCpth, MreCsty, \
            MreDebr, MreDial, MreDlbr, MreDlvw, MreDobj, MreDoor, MreDual, \
            MreEczn, MreEfsh, MreEnch, MreEqup, MreExpl, MreEyes, MreFact, \
            MreFlor, MreFstp, MreFsts, MreFurn, MreGmst, MreGras, MrePack, \
            MreHazd, MreHdpt, MreTes4, MreIdle, MreIdlm, MreImad, MreImgs, \
            MreInfo, MreIngr, MreIpct, MreIpds, MreKeym, MreKywd, MreLcrt, \
            MreLctn, MreLgtm, MreLigh, MreLscr, MreLvli, MreLvln, MreLvsp, \
            MreMatt, MreMesg, MreMgef, MreMisc, MreMovt, MreMstt, MreMusc, \
            MreMust, MreNpc, MreOtft, MrePerk, MreProj, MreQust, MreRegn, \
            MreRela, MreRevb, MreRfct, MreScrl, MreShou, MreSlgm, MreSmbn, \
            MreSmen, MreSmqn, MreSnct, MreSndr, MreSopm, MreSoun, MreSpel, \
            MreSpgd, MreTact, MreTree, MreTxst, MreVtyp, MreWoop, MreWrld, \
            MreAmmo, MreLtex, MreMato, MreStat, MreWatr, MreWeap, MreWthr, \
            MreRace
        cls.mergeable_sigs = {clazz.rec_sig: clazz for clazz in (
            # MreAchr, MreDial, MreInfo,
            MreAact, MreActi, MreAddn, MreAlch, MreAmmo, MreAnio, MreAppa,
            MreArma, MreArmo, MreArto, MreAspc, MreAstp, MreAvif, MreBook,
            MreBptd, MreCams, MreClas, MreClfm, MreClmt, MreCobj, MreColl,
            MreCont, MreCpth, MreCsty, MreDebr, MreDlbr, MreDlvw, MreDobj,
            MreDoor, MreDual, MreEczn, MreEfsh, MreEnch, MreEqup, MreExpl,
            MreEyes, MreFlor, MreFlst, MreFstp, MreFsts, MreFurn, MreGlob,
            MreGmst, MreGras, MreHazd, MreHdpt, MreIdle, MreIdlm, MreImad,
            MreImgs, MreIngr, MreIpct, MreIpds, MreKeym, MreKywd, MreLcrt,
            MreLctn, MreLgtm, MreLigh, MreLscr, MreLtex, MreLvli, MreLvln,
            MreLvsp, MreMato, MreMatt, MreMesg, MreMgef, MreMisc, MreMovt,
            MreMstt, MreMusc, MreMust, MreNpc, MreOtft, MrePerk, MreProj,
            MreRegn, MreRela, MreRevb, MreRfct, MreScrl, MreShou, MreSlgm,
            MreSmbn, MreSmen, MreSmqn, MreSnct, MreSndr, MreSopm, MreSoun,
            MreSpel, MreSpgd, MreStat, MreTact, MreTree, MreTxst, MreVtyp,
            MreWatr, MreWeap, MreWoop, MreWthr, MreVoli, MreLens, MreQust,
            MrePack, MreFact, MreRace,
        )}
        # Setting RecordHeader class variables --------------------------------
        header_type = brec.RecordHeader
        header_type.top_grup_sigs = [
            b'GMST', b'KYWD', b'LCRT', b'AACT', b'TXST', b'GLOB', b'CLAS',
            b'FACT', b'HDPT', b'HAIR', b'EYES', b'RACE', b'SOUN', b'ASPC',
            b'MGEF', b'SCPT', b'LTEX', b'ENCH', b'SPEL', b'SCRL', b'ACTI',
            b'TACT', b'ARMO', b'BOOK', b'CONT', b'DOOR', b'INGR', b'LIGH',
            b'MISC', b'APPA', b'STAT', b'SCOL', b'MSTT', b'PWAT', b'GRAS',
            b'TREE', b'CLDC', b'FLOR', b'FURN', b'WEAP', b'AMMO', b'NPC_',
            b'LVLN', b'KEYM', b'ALCH', b'IDLM', b'COBJ', b'PROJ', b'HAZD',
            b'SLGM', b'LVLI', b'WTHR', b'CLMT', b'SPGD', b'RFCT', b'REGN',
            b'NAVI', b'CELL', b'WRLD', b'DIAL', b'QUST', b'IDLE', b'PACK',
            b'CSTY', b'LSCR', b'LVSP', b'ANIO', b'WATR', b'EFSH', b'EXPL',
            b'DEBR', b'IMGS', b'IMAD', b'FLST', b'PERK', b'BPTD', b'ADDN',
            b'AVIF', b'CAMS', b'CPTH', b'VTYP', b'MATT', b'IPCT', b'IPDS',
            b'ARMA', b'ECZN', b'LCTN', b'MESG', b'RGDL', b'DOBJ', b'LGTM',
            b'MUSC', b'FSTP', b'FSTS', b'SMBN', b'SMQN', b'SMEN', b'DLBR',
            b'MUST', b'DLVW', b'WOOP', b'SHOU', b'EQUP', b'RELA', b'SCEN',
            b'ASTP', b'OTFT', b'ARTO', b'MATO', b'MOVT', b'SNDR', b'DUAL',
            b'SNCT', b'SOPM', b'COLL', b'CLFM', b'REVB', b'LENS', b'VOLI',
        ]
        header_type.valid_header_sigs = set(
            header_type.top_grup_sigs + [b'GRUP', b'TES4', b'REFR', b'ACHR',
                                         b'ACRE', b'LAND', b'INFO', b'NAVM',
                                         b'PARW', b'PBAR', b'PBEA', b'PCON',
                                         b'PFLA', b'PGRE', b'PHZD', b'PMIS'])
        header_type.plugin_form_version = 44
        brec.MreRecord.type_class = {x.rec_sig: x for x in (
            MreAchr, MreDial, MreInfo, MreAact, MreActi, MreAddn, MreAlch,
            MreAmmo, MreAnio, MreAppa, MreArma, MreArmo, MreArto, MreAspc,
            MreAstp, MreAvif, MreBook, MreBptd, MreCams, MreClas, MreClfm,
            MreClmt, MreCobj, MreColl, MreCont, MreCpth, MreCsty, MreDebr,
            MreDlbr, MreDlvw, MreDobj, MreDoor, MreDual, MreEczn, MreEfsh,
            MreEnch, MreEqup, MreExpl, MreEyes, MreFact, MreFlor, MreFlst,
            MreFstp, MreFsts, MreFurn, MreGlob, MreGmst, MreGras, MreHazd,
            MreHdpt, MreIdle, MreIdlm, MreImad, MreImgs, MreIngr, MreIpct,
            MreIpds, MreKeym, MreKywd, MreLcrt, MreLctn, MreLgtm, MreLigh,
            MreLscr, MreLtex, MreLvli, MreLvln, MreLvsp, MreMato, MreMatt,
            MreMesg, MreMgef, MreMisc, MreMovt, MreMstt, MreMusc, MreMust,
            MreNpc, MreOtft, MrePerk, MreProj, MreRegn, MreRela, MreRevb,
            MreRfct, MreScrl, MreShou, MreSlgm, MreSmbn, MreSmen, MreSmqn,
            MreSnct, MreSndr, MreSopm, MreSoun, MreSpel, MreSpgd, MreStat,
            MreTact, MreTree, MreTxst, MreVtyp, MreWatr, MreWeap, MreWoop,
            MreWthr, MreCell, MreWrld, MreVoli, MreLens, MreQust, MreTes4,
            MrePack, MreRace,
            # MreNavm, MreNavi
        )}
        brec.MreRecord.simpleTypes = (
                set(brec.MreRecord.type_class) - {b'TES4', b'ACHR', b'CELL',
                                                  b'DIAL', b'INFO', b'WRLD'})
        cls._validate_records()

GAME_TYPE = SkyrimVRGameInfo
