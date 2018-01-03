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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2015 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This modules defines static data for use by bush, when TES V:
   Skyrim Special Edition is set at the active game."""

from .constants import *
from .default_tweaks import default_tweaks
from ... import brec
from .records import MreCell, MreWrld, MreFact, MreAchr, MreDial, MreInfo, \
    MreCams, MreWthr, MreDual, MreMato, MreVtyp, MreMatt, MreLvsp, MreEnch, \
    MreProj, MreDlbr, MreRfct, MreMisc, MreActi, MreEqup, MreCpth, MreDoor, \
    MreAnio, MreHazd, MreIdlm, MreEczn, MreIdle, MreLtex, MreQust, MreMstt, \
    MreNpc, MreFlst, MreIpds, MreGmst, MreRevb, MreClmt, MreDebr, MreSmbn, \
    MreLvli, MreSpel, MreKywd, MreLvln, MreAact, MreSlgm, MreRegn, MreFurn, \
    MreGras, MreAstp, MreWoop, MreMovt, MreCobj, MreShou, MreSmen, MreColl, \
    MreArto, MreAddn, MreSopm, MreCsty, MreAppa, MreArma, MreArmo, MreKeym, \
    MreTxst, MreHdpt, MreHeader, MreAlch, MreBook, MreSpgd, MreSndr, MreImgs, \
    MreScrl, MreMust, MreFstp, MreFsts, MreMgef, MreLgtm, MreMusc, MreClas, \
    MreLctn, MreTact, MreBptd, MreDobj, MreLscr, MreDlvw, MreTree, MreWatr, \
    MreFlor, MreEyes, MreWeap, MreIngr, MreClfm, MreMesg, MreLigh, MreExpl, \
    MreLcrt, MreStat, MreAmmo, MreSmqn, MreImad, MreSoun, MreAvif, MreCont, \
    MreIpct, MreAspc, MreRela, MreEfsh, MreSnct, MreOtft, MreVoli, MreLens
from .. import GameInfo
from ...bolt import struct_pack, struct_unpack
from ...brec import MreGlob
from ..skyrim import SkyrimGameInfo


class SkyrimSEGameInfo(SkyrimGameInfo):
    displayName = u'Skyrim Special Edition'
    fsName = u'Skyrim Special Edition'
    altName = u'Wrye Smash'
    defaultIniFile = u'Skyrim_Default.ini'

    exe = u'SkyrimSE.exe'

    regInstallKeys = (
        u'Bethesda Softworks\\Skyrim Special Edition',
        u'Installed Path'
    )

    nexusUrl = u'http://www.nexusmods.com/skyrimspecialedition/'
    nexusName = u'Skyrim SE Nexus'
    nexusKey = 'bash.installers.openSkyrimSeNexus.continue'

    vanilla_string_bsas = {
        u'skyrim.esm': [u'Skyrim - Patch.bsa', u'Skyrim - Interface.bsa'],
        u'update.esm': [u'Skyrim - Patch.bsa', u'Skyrim - Interface.bsa'],
        u'dawnguard.esm': [u'Skyrim - Patch.bsa', u'Skyrim - Interface.bsa'],
        u'hearthfires.esm': [u'Skyrim - Patch.bsa', u'Skyrim - Interface.bsa'],
        u'dragonborn.esm': [u'Skyrim - Patch.bsa', u'Skyrim - Interface.bsa'],
    }

    espm_extensions = {u'.esp', u'.esm', u'.esl'}

    allTags = sorted((
        u'Deactivate', u'Delev', u'Invent', u'NoMerge', u'Relev',
        ))

    patchers = (
        u'GmstTweaker', u'ImportInventory', u'ListsMerger', u'PatchMerger',
    )

    mergeClasses = (
        # MreAchr, MreDial, MreInfo,
        # MreFact,
        MreAact, MreActi, MreAddn, MreAlch, MreAmmo, MreAnio, MreAppa, MreArma,
        MreArmo, MreArto, MreAspc, MreAstp, MreAvif, MreBook, MreBptd, MreCams,
        MreClas, MreClfm, MreClmt, MreCobj, MreColl, MreCont, MreCpth, MreCsty,
        MreDebr, MreDlbr, MreDlvw, MreDobj, MreDoor, MreDual, MreEczn, MreEfsh,
        MreEnch, MreEqup, MreExpl, MreEyes, MreFlor, MreFlst, MreFstp, MreFsts,
        MreFurn, MreGlob, MreGmst, MreGras, MreHazd, MreHdpt, MreIdle, MreIdlm,
        MreImad, MreImgs, MreIngr, MreIpct, MreIpds, MreKeym, MreKywd, MreLcrt,
        MreLctn, MreLgtm, MreLigh, MreLscr, MreLtex, MreLvli, MreLvln, MreLvsp,
        MreMato, MreMatt, MreMesg, MreMgef, MreMisc, MreMovt, MreMstt, MreMusc,
        MreMust, MreNpc, MreOtft, MreProj, MreRegn, MreRela, MreRevb, MreRfct,
        MreScrl, MreShou, MreSlgm, MreSmbn, MreSmen, MreSmqn, MreSnct, MreSndr,
        MreSopm, MreSoun, MreSpel, MreSpgd, MreStat, MreTact, MreTree, MreTxst,
        MreVtyp, MreWatr, MreWeap, MreWoop, MreWthr, MreVoli,
        ####### for debug
        MreQust,
    )

    # MreScpt is Oblivion/FO3/FNV Only
    # MreMgef, has not been verified to be used here for Skyrim

    @classmethod
    def init(cls):
        brec.RecordHeader.topTypes = [
            'GMST', 'KYWD', 'LCRT', 'AACT', 'TXST', 'GLOB', 'CLAS', 'FACT', 'HDPT',
            'HAIR', 'EYES', 'RACE', 'SOUN', 'ASPC', 'MGEF', 'SCPT', 'LTEX', 'ENCH',
            'SPEL', 'SCRL', 'ACTI', 'TACT', 'ARMO', 'BOOK', 'CONT', 'DOOR', 'INGR',
            'LIGH', 'MISC', 'APPA', 'STAT', 'SCOL', 'MSTT', 'PWAT', 'GRAS', 'TREE',
            'CLDC', 'FLOR', 'FURN', 'WEAP', 'AMMO', 'NPC_', 'LVLN', 'KEYM', 'ALCH',
            'IDLM', 'COBJ', 'PROJ', 'HAZD', 'SLGM', 'LVLI', 'WTHR', 'CLMT', 'SPGD',
            'RFCT', 'REGN', 'NAVI', 'CELL', 'WRLD', 'DIAL', 'QUST', 'IDLE', 'PACK',
            'CSTY', 'LSCR', 'LVSP', 'ANIO', 'WATR', 'EFSH', 'EXPL', 'DEBR', 'IMGS',
            'IMAD', 'FLST', 'PERK', 'BPTD', 'ADDN', 'AVIF', 'CAMS', 'CPTH', 'VTYP',
            'MATT', 'IPCT', 'IPDS', 'ARMA', 'ECZN', 'LCTN', 'MESG', 'RGDL', 'DOBJ',
            'LGTM', 'MUSC', 'FSTP', 'FSTS', 'SMBN', 'SMQN', 'SMEN', 'DLBR', 'MUST',
            'DLVW', 'WOOP', 'SHOU', 'EQUP', 'RELA', 'SCEN', 'ASTP', 'OTFT', 'ARTO',
            'MATO', 'MOVT', 'SNDR', 'DUAL', 'SNCT', 'SOPM', 'COLL', 'CLFM', 'REVB',
            'LENS', 'VOLI']

        #-> this needs updating for Skyrim
        brec.RecordHeader.recordTypes = set(
            brec.RecordHeader.topTypes + ['GRUP', 'TES4', 'REFR', 'ACHR', 'ACRE',
                                          'LAND', 'INFO', 'NAVM', 'PHZD', 'PGRE'])
        brec.RecordHeader.plugin_form_version = 44

        brec.MreRecord.type_class = dict((x.classType,x) for x in (
            MreAchr, MreDial, MreInfo, MreAact, MreActi, MreAddn, MreAlch, MreAmmo,
            MreAnio, MreAppa, MreArma, MreArmo, MreArto, MreAspc, MreAstp, MreAvif,
            MreBook, MreBptd, MreCams, MreClas, MreClfm, MreClmt, MreCobj, MreColl,
            MreCont, MreCpth, MreCsty, MreDebr, MreDlbr, MreDlvw, MreDobj, MreDoor,
            MreDual, MreEczn, MreEfsh, MreEnch, MreEqup, MreExpl, MreEyes, MreFact,
            MreFlor, MreFlst, MreFstp, MreFsts, MreFurn, MreGlob, MreGmst, MreGras,
            MreHazd, MreHdpt, MreIdle, MreIdlm, MreImad, MreImgs, MreIngr, MreIpct,
            MreIpds, MreKeym, MreKywd, MreLcrt, MreLctn, MreLgtm, MreLigh, MreLscr,
            MreLtex, MreLvli, MreLvln, MreLvsp, MreMato, MreMatt, MreMesg, MreMgef,
            MreMisc, MreMovt, MreMstt, MreMusc, MreMust, MreNpc, MreOtft, MreProj,
            MreRegn, MreRela, MreRevb, MreRfct, MreScrl, MreShou, MreSlgm, MreSmbn,
            MreSmen, MreSmqn, MreSnct, MreSndr, MreSopm, MreSoun, MreSpel, MreSpgd,
            MreStat, MreTact, MreTree, MreTxst, MreVtyp, MreWatr, MreWeap, MreWoop,
            MreWthr, MreCell, MreWrld, MreVoli, MreLens, # MreNavm, MreNavi
            ####### for debug
            MreQust, MreHeader,
        ))

        brec.MreRecord.simpleTypes = (
            set(brec.MreRecord.type_class) - {'TES4', 'ACHR', 'CELL', 'DIAL',
                                              'INFO', 'WRLD', })

GAME_TYPE = SkyrimSEGameInfo
