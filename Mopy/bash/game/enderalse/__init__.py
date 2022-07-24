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
"""This modules defines static data for use by bush, when Enderal SE is set as
the active game."""

from ..enderal import EnderalGameInfo
from ..skyrimse import SkyrimSEGameInfo
from ... import brec
from ...brec import MreFlst, MreGlob

# We want the final chain of attribute lookups to be Enderal SE -> Enderal LE
# -> Skyrim SE -> Skyrim LE -> Defaults, i.e. the narrower overrides first
class EnderalSEGameInfo(EnderalGameInfo, SkyrimSEGameInfo):
    displayName = u'Enderal Special Edition'
    fsName = u'Enderal Special Edition'
    game_icon = u'enderalse_%u.png'
    bash_root_prefix = u'EnderalSE'
    bak_game_name = u'Enderal Special Edition'
    my_games_name = u'Enderal Special Edition'
    appdata_name = u'Enderal Special Edition'
    # Enderal LE also has an Enderal Launcher.exe, but no SkyrimSE.exe. Skyrim
    # SE has SkyrimSE.exe, but no Enderal Launcher.exe
    game_detect_includes = [u'Enderal Launcher.exe', u'SkyrimSE.exe']
    loot_dir = u'Enderal Special Edition'
    # This is in HKCU. There's also one in HKLM that uses 'SureAI\Enderal SE'
    # for some reason
    regInstallKeys = (u'SureAI\\EnderalSE', u'Install_Path')
    nexusUrl = u'https://www.nexusmods.com/enderalspecialedition/'
    nexusName = u'Enderal Special Edition Nexus'
    nexusKey = u'bash.installers.openEnderalSENexus.continue'

    class Ini(EnderalGameInfo.Ini):
        save_prefix = u'..\\Enderal Special Edition\\Saves'

    class Xe(EnderalGameInfo.Xe):
        full_name = u'EnderalSEEdit'
        xe_key_prefix = u'enderalSEView'

    class Bain(EnderalGameInfo.Bain):
        skip_bain_refresh = {u'enderalseedit backups', u'enderalseedit cache'}

    bethDataFiles = {
        'dawnguard.esm',
        'dragonborn.esm',
        'e - meshes.bsa',
        'e - scripts.bsa',
        'e - se.bsa',
        'e - sounds.bsa',
        'e - textures1.bsa',
        'e - textures2.bsa',
        'e - textures3.bsa',
        'enderal - forgotten stories.esm',
        'hearthfires.esm',
        'l - textures.bsa',
        'l - voices.bsa',
        'skyrim - animations.bsa',
        'skyrim - interface.bsa',
        'skyrim - meshes0.bsa',
        'skyrim - meshes1.bsa',
        'skyrim - misc.bsa',
        'skyrim - patch.bsa',
        'skyrim - shaders.bsa',
        'skyrim - sounds.bsa',
        'skyrim - textures0.bsa',
        'skyrim - textures1.bsa',
        'skyrim - textures2.bsa',
        'skyrim - textures3.bsa',
        'skyrim - textures4.bsa',
        'skyrim - textures5.bsa',
        'skyrim - textures6.bsa',
        'skyrim - textures7.bsa',
        'skyrim - textures8.bsa',
        'skyrim.esm',
        'skyui_se.bsa',
        'skyui_se.esp',
        'update.esm',
    }

    _patcher_package = 'bash.game.enderalse' # We need to override tweaks
    @classmethod
    def init(cls):
        # Copy-pasted from Skyrim
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
            b'SNCT', b'SOPM', b'COLL', b'CLFM', b'REVB', b'LENS', b'VOLI']
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

GAME_TYPE = EnderalSEGameInfo
