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
"""GameInfo override for TES V: Skyrim Special Edition."""

from ..skyrim import SkyrimGameInfo
from ... import brec
from ...brec import MreFlst, MreGlob

class SkyrimSEGameInfo(SkyrimGameInfo):
    displayName = u'Skyrim Special Edition'
    fsName = u'Skyrim Special Edition'
    bash_root_prefix = u'Skyrim Special Edition' # backwards compat :(
    launch_exe = u'SkyrimSE.exe'
    # Set to this because SkyrimSE.exe also exists for Enderal SE
    game_detect_files = [u'SkyrimSELauncher.exe']
    version_detect_file = u'SkyrimSE.exe'
    taglist_dir = u'SkyrimSE'
    regInstallKeys = (u'Bethesda Softworks\\Skyrim Special Edition',
                      u'Installed Path')

    nexusUrl = u'https://www.nexusmods.com/skyrimspecialedition/'
    nexusName = u'Skyrim SE Nexus'
    nexusKey = u'bash.installers.openSkyrimSeNexus.continue'

    espm_extensions = SkyrimGameInfo.espm_extensions | {u'.esl'}
    has_achlist = True
    check_esl = True

    class Ws(SkyrimGameInfo.Ws):
        publisher_name = u'Bethesda'
        win_store_name = u'BethesdaSoftworks.SkyrimSE-PC'

    class Se(SkyrimGameInfo.Se):
        se_abbrev = u'SKSE64'
        long_name = u'Skyrim SE Script Extender'
        exe = u'skse64_loader.exe'
        ver_files = [u'skse64_loader.exe', u'skse64_steam_loader.dll']

    # ScriptDragon doesn't exist for SSE
    class Sd(SkyrimGameInfo.Sd):
        sd_abbrev = u''
        long_name = u''
        install_dir = u''

    class Bsa(SkyrimGameInfo.Bsa):
        # Skyrim SE accepts the base name and ' - Textures'
        attachment_regex = r'(?: \- Textures)?'
        valid_versions = {0x69}

    class Xe(SkyrimGameInfo.Xe):
        full_name = u'SSEEdit'
        xe_key_prefix = u'sseView'

    class Bain(SkyrimGameInfo.Bain):
        skip_bain_refresh = {u'sseedit backups', u'sseedit cache'}

    allTags = SkyrimGameInfo.allTags - {u'NoMerge'}
    patchers = SkyrimGameInfo.patchers - {u'MergePatches'}

    bethDataFiles = {
        u'skyrim.esm',
        u'update.esm',
        u'dawnguard.esm',
        u'dragonborn.esm',
        u'hearthfires.esm',
        u'skyrim - animations.bsa',
        u'skyrim - interface.bsa',
        u'skyrim - meshes0.bsa',
        u'skyrim - meshes1.bsa',
        u'skyrim - misc.bsa',
        u'skyrim - patch.bsa',
        u'skyrim - shaders.bsa',
        u'skyrim - sounds.bsa',
        u'skyrim - textures0.bsa',
        u'skyrim - textures1.bsa',
        u'skyrim - textures2.bsa',
        u'skyrim - textures3.bsa',
        u'skyrim - textures4.bsa',
        u'skyrim - textures5.bsa',
        u'skyrim - textures6.bsa',
        u'skyrim - textures7.bsa',
        u'skyrim - textures8.bsa',
        u'skyrim - voices_en0.bsa',
    }

    @classmethod
    def init(cls):
        cls._dynamic_import_modules(__name__)
        # First import from skyrimse.records file
        from .records import MreVoli, MreLens
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
            b'SNCT', b'SOPM', b'COLL', b'CLFM', b'REVB', b'LENS', b'VOLI']
        #-> this needs updating for Skyrim
        header_type.valid_header_sigs = set(
            header_type.top_grup_sigs + [b'GRUP', b'TES4', b'REFR', b'ACHR',
                                         b'ACRE', b'LAND', b'INFO', b'NAVM',
                                         b'PHZD', b'PGRE'])
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

GAME_TYPE = SkyrimSEGameInfo
