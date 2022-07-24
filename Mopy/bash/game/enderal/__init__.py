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
"""This modules defines static data for use by bush, when Enderal is set as the
active game."""

from ..skyrim import SkyrimGameInfo
from ... import brec
from ...brec import MreFlst, MreGlob

class EnderalGameInfo(SkyrimGameInfo):
    displayName = u'Enderal'
    fsName = u'Enderal'
    game_icon = u'enderal_%u.png'
    bash_root_prefix = u'Enderal'
    bak_game_name = u'Enderal'
    my_games_name = u'Enderal'
    appdata_name = u'Enderal'
    # Enderal SE also has an Enderal Launcher.exe, but no TESV.exe. Skyrim LE
    # has TESV.exe, but no Enderal Launcher.exe
    game_detect_includes = [u'Enderal Launcher.exe', u'TESV.exe']
    # This isn't exact (currently 1.5.0 when it should be 1.5.7), but it's the
    # closest we're going to get
    version_detect_file = u'Enderal Launcher.exe'
    taglist_dir = u'Enderal'
    loot_dir = u'Enderal'
    boss_game_name = u'' # BOSS does not support Enderal
    regInstallKeys = (u'SureAI\\Enderal', u'Install_Path')
    nexusUrl = u'https://www.nexusmods.com/enderal/'
    nexusName = u'Enderal Nexus'
    nexusKey = u'bash.installers.openEnderalNexus.continue'

    class Ini(SkyrimGameInfo.Ini):
        default_ini_file = u'enderal_default.ini'
        dropdown_inis = [u'Enderal.ini', u'EnderalPrefs.ini']
        save_prefix = u'..\\Enderal\\Saves'

    class Xe(SkyrimGameInfo.Xe):
        full_name = u'EnderalEdit'
        xe_key_prefix = u'enderalView'

    class Bain(SkyrimGameInfo.Bain):
        skip_bain_refresh = {u'enderaledit backups', u'enderaledit cache'}

    raceNames = {
        0x13741 : _(u'Half Kilénian'),
        0x13742 : _(u'Half Aeterna'),
        0x13743 : _(u'Half Aeterna'),
        0x13746 : _(u'Half Arazealean'),
        0x13748 : _(u'Half Qyranian'),
    }
    raceShortNames = {
        0x13741 : u'Kil',
        0x13742 : u'Aet',
        0x13743 : u'Aet',
        0x13746 : u'Ara',
        0x13748 : u'Qyr',
    }
    # TODO(inf) Not updated yet - seem to only be needed for Oblivion-specific
    #  save code
    raceHairMale = {
        0x13741 : 0x90475, #--Kil
        0x13742 : 0x64214, #--Aet
        0x13743 : 0x7b792, #--Aet
        0x13746 : 0x1da82, #--Ara
        0x13748 : 0x64215, #--Qyr
    }
    raceHairFemale = {
        0x13741 : 0x1da83, #--Kil
        0x13742 : 0x1da83, #--Aet
        0x13743 : 0x690c2, #--Aet
        0x13746 : 0x1da83, #--Ara
        0x13748 : 0x64210, #--Qyr
    }

    bethDataFiles = {
        'e - meshes.bsa',
        'e - music.bsa',
        'e - scripts.bsa',
        'e - sounds.bsa',
        'e - textures1.bsa',
        'e - textures2.bsa',
        'e - textures3.bsa',
        'enderal - forgotten stories.esm',
        'l - textures.bsa',
        'l - voices.bsa',
        'skyrim - animations.bsa',
        'skyrim - interface.bsa',
        'skyrim - meshes.bsa',
        'skyrim - misc.bsa',
        'skyrim - shaders.bsa',
        'skyrim - sounds.bsa',
        'skyrim - textures.bsa',
        'skyrim.esm',
        'update.bsa',
        'update.esm',
    }

    nirnroots = _(u'Vynroots')

    _patcher_package = 'bash.game.enderal' # We need to override tweaks
    @classmethod
    def init(cls):
        # Copy-pasted from Skyrim
        cls._dynamic_import_modules(__name__)
        from ..skyrim.records import MreCell, MreWrld, MreFact, MreAchr, \
            MreInfo, MreCams, MreWthr, MreDual, MreMato, MreVtyp, MreMatt, \
            MreLvsp, MreEnch, MreProj, MreDlbr, MreRfct, MreMisc, MreActi, \
            MreEqup, MreCpth, MreDoor, MreAnio, MreHazd, MreIdlm, MreEczn, \
            MreIdle, MreLtex, MreQust, MreMstt, MreNpc, MreIpds, MrePack, \
            MreGmst, MreRevb, MreClmt, MreDebr, MreSmbn, MreLvli, MreSpel, \
            MreKywd, MreLvln, MreAact, MreSlgm, MreRegn, MreFurn, MreGras, \
            MreAstp, MreWoop, MreMovt, MreCobj, MreShou, MreSmen, MreColl, \
            MreArto, MreAddn, MreSopm, MreCsty, MreAppa, MreArma, MreArmo, \
            MreKeym, MreTxst, MreHdpt, MreTes4, MreAlch, MreBook, MreSpgd, \
            MreSndr, MreImgs, MreScrl, MreMust, MreFstp, MreFsts, MreMgef, \
            MreLgtm, MreMusc, MreClas, MreLctn, MreTact, MreBptd, MreDobj, \
            MreLscr, MreDlvw, MreTree, MreWatr, MreFlor, MreEyes, MreWeap, \
            MreIngr, MreClfm, MreMesg, MreLigh, MreExpl, MreLcrt, MreStat, \
            MreAmmo, MreSmqn, MreImad, MreSoun, MreAvif, MreCont, MreIpct, \
            MreAspc, MreRela, MreEfsh, MreSnct, MreOtft, MrePerk, MreRace, \
            MreDial
        cls.mergeable_sigs = {clazz.rec_sig: clazz for clazz in (# MreAchr, MreDial, MreInfo,
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
            MreWatr, MreWeap, MreWoop, MreWthr, MreQust, MrePack, MreFact,
            MreRace,
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
            b'SNCT', b'SOPM', b'COLL', b'CLFM', b'REVB',
        ]
        header_type.valid_header_sigs = set(
            header_type.top_grup_sigs + [b'GRUP', b'TES4', b'REFR', b'ACHR',
                                         b'ACRE', b'LAND', b'INFO', b'NAVM',
                                         b'PARW', b'PBAR', b'PBEA', b'PCON',
                                         b'PFLA', b'PGRE', b'PHZD', b'PMIS'])
        header_type.plugin_form_version = 43
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
            MreWthr, MreCell, MreWrld, MreQust, MreTes4, MrePack, MreRace,
            # MreNavm, MreNavi
        )}
        brec.MreRecord.simpleTypes = (
                set(brec.MreRecord.type_class) - {b'TES4', b'ACHR', b'CELL',
                                                  b'DIAL', b'INFO', b'WRLD'})
        cls._validate_records()

GAME_TYPE = EnderalGameInfo
