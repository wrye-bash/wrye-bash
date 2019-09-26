# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This modules defines static data for use by bush, when Enderal is set as the
   active game."""

from ..skyrim import SkyrimGameInfo
from ... import brec
from ...brec import MreGlob

class EnderalGameInfo(SkyrimGameInfo):
    displayName = u'Enderal'
    fsName = u'Enderal'
    altName = u'Wrye Smash'
    defaultIniFile = u'enderal_default.ini'
    # Set to this because TESV.exe also exists for Enderal
    game_detect_file = [u'Enderal Launcher.exe']
    # This isn't exact (currently 1.5.0 when it should be 1.5.7), but it's the
    # closest we're going to get
    version_detect_file = [u'Enderal Launcher.exe']
    iniFiles = [u'Enderal.ini', u'EnderalPrefs.ini']
    pklfile = u'bash\\db\\Enderal_ids.pkl'
    regInstallKeys = (
        u'SureAI\\Enderal',
        u'Install_Path'
    )
    save_prefix = u'..\\Enderal\\Saves'

    nexusUrl = u'https://www.nexusmods.com/enderal/'
    nexusName = u'Enderal Nexus'
    nexusKey = u'bash.installers.openEnderalNexus.continue'

    vanilla_string_bsas = {
        u'skyrim.esm': [u'Skyrim - Interface.bsa'],
        u'update.esm': [u'Skyrim - Interface.bsa'],
        u'enderal - forgotten stories.esm': [u'Skyrim - Interface.bsa'],
    }
    SkipBAINRefresh = {u'enderaledit backups', u'enderaledit cache'}

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

    @classmethod
    def init(cls):
        # Copy-pasted from Skyrim
        cls._dynamic_import_modules(__name__)
        from .records import MreCell, MreWrld, MreFact, MreAchr, MreDial, \
            MreInfo, MreCams, MreWthr, MreDual, MreMato, MreVtyp, MreMatt, \
            MreLvsp, MreEnch, MreProj, MreDlbr, MreRfct, MreMisc, MreActi, \
            MreEqup, MreCpth, MreDoor, MreAnio, MreHazd, MreIdlm, MreEczn, \
            MreIdle, MreLtex, MreQust, MreMstt, MreNpc, MreFlst, MreIpds, \
            MreGmst, MreRevb, MreClmt, MreDebr, MreSmbn, MreLvli, MreSpel, \
            MreKywd, MreLvln, MreAact, MreSlgm, MreRegn, MreFurn, MreGras, \
            MreAstp, MreWoop, MreMovt, MreCobj, MreShou, MreSmen, MreColl, \
            MreArto, MreAddn, MreSopm, MreCsty, MreAppa, MreArma, MreArmo, \
            MreKeym, MreTxst, MreHdpt, MreHeader, MreAlch, MreBook, MreSpgd, \
            MreSndr, MreImgs, MreScrl, MreMust, MreFstp, MreFsts, MreMgef, \
            MreLgtm, MreMusc, MreClas, MreLctn, MreTact, MreBptd, MreDobj, \
            MreLscr, MreDlvw, MreTree, MreWatr, MreFlor, MreEyes, MreWeap, \
            MreIngr, MreClfm, MreMesg, MreLigh, MreExpl, MreLcrt, MreStat, \
            MreAmmo, MreSmqn, MreImad, MreSoun, MreAvif, MreCont, MreIpct, \
            MreAspc, MreRela, MreEfsh, MreSnct, MreOtft
        # ---------------------------------------------------------------------
        # Unused records, they have empty GRUP in skyrim.esm-------------------
        # CLDC HAIR PWAT RGDL SCOL SCPT
        # ---------------------------------------------------------------------
        # These Are normally not mergeable but added to brec.MreRecord.type_class
        #
        #       MreCell,
        # ---------------------------------------------------------------------
        # These have undefined FormIDs Do not merge them
        #
        #       MreNavi, MreNavm,
        # ---------------------------------------------------------------------
        # These need syntax revision but can be merged once that is corrected
        #
        #       MreAchr, MreDial, MreLctn, MreInfo, MreFact, MrePerk,
        # ---------------------------------------------------------------------
        cls.mergeClasses = (# MreAchr, MreDial, MreInfo, MreFact,
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
            MreMstt, MreMusc, MreMust, MreNpc, MreOtft, MreProj, MreRegn,
            MreRela, MreRevb, MreRfct, MreScrl, MreShou, MreSlgm, MreSmbn,
            MreSmen, MreSmqn, MreSnct, MreSndr, MreSopm, MreSoun, MreSpel,
            MreSpgd, MreStat, MreTact, MreTree, MreTxst, MreVtyp, MreWatr,
            MreWeap, MreWoop, MreWthr,
            ####### for debug
            MreQust,)

        # MreScpt is Oblivion/FO3/FNV Only
        # MreMgef, has not been verified to be used here for Skyrim

        # Setting RecordHeader class variables --------------------------------
        brec.RecordHeader.topTypes = ['GMST', 'KYWD', 'LCRT', 'AACT', 'TXST',
            'GLOB', 'CLAS', 'FACT', 'HDPT', 'HAIR', 'EYES', 'RACE', 'SOUN',
            'ASPC', 'MGEF', 'SCPT', 'LTEX', 'ENCH', 'SPEL', 'SCRL', 'ACTI',
            'TACT', 'ARMO', 'BOOK', 'CONT', 'DOOR', 'INGR', 'LIGH', 'MISC',
            'APPA', 'STAT', 'SCOL', 'MSTT', 'PWAT', 'GRAS', 'TREE', 'CLDC',
            'FLOR', 'FURN', 'WEAP', 'AMMO', 'NPC_', 'LVLN', 'KEYM', 'ALCH',
            'IDLM', 'COBJ', 'PROJ', 'HAZD', 'SLGM', 'LVLI', 'WTHR', 'CLMT',
            'SPGD', 'RFCT', 'REGN', 'NAVI', 'CELL', 'WRLD', 'DIAL', 'QUST',
            'IDLE', 'PACK', 'CSTY', 'LSCR', 'LVSP', 'ANIO', 'WATR', 'EFSH',
            'EXPL', 'DEBR', 'IMGS', 'IMAD', 'FLST', 'PERK', 'BPTD', 'ADDN',
            'AVIF', 'CAMS', 'CPTH', 'VTYP', 'MATT', 'IPCT', 'IPDS', 'ARMA',
            'ECZN', 'LCTN', 'MESG', 'RGDL', 'DOBJ', 'LGTM', 'MUSC', 'FSTP',
            'FSTS', 'SMBN', 'SMQN', 'SMEN', 'DLBR', 'MUST', 'DLVW', 'WOOP',
            'SHOU', 'EQUP', 'RELA', 'SCEN', 'ASTP', 'OTFT', 'ARTO', 'MATO',
            'MOVT', 'SNDR', 'DUAL', 'SNCT', 'SOPM', 'COLL', 'CLFM', 'REVB']
        #-> this needs updating for Skyrim
        brec.RecordHeader.recordTypes = set(
            brec.RecordHeader.topTypes + ['GRUP', 'TES4', 'REFR', 'ACHR',
                                          'ACRE', 'LAND', 'INFO', 'NAVM',
                                          'PHZD', 'PGRE'])
        brec.RecordHeader.plugin_form_version = 43
        brec.MreRecord.type_class = dict((x.classType,x) for x in (
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
            MreNpc, MreOtft, MreProj, MreRegn, MreRela, MreRevb, MreRfct,
            MreScrl, MreShou, MreSlgm, MreSmbn, MreSmen, MreSmqn, MreSnct,
            MreSndr, MreSopm, MreSoun, MreSpel, MreSpgd, MreStat, MreTact,
            MreTree, MreTxst, MreVtyp, MreWatr, MreWeap, MreWoop, MreWthr,
            MreCell, MreWrld,  # MreNavm, MreNavi
            ####### for debug
            MreQust, MreHeader,
        ))
        brec.MreRecord.simpleTypes = (
            set(brec.MreRecord.type_class) - {'TES4', 'ACHR', 'CELL', 'DIAL',
                                              'INFO', 'WRLD', })

GAME_TYPE = EnderalGameInfo
