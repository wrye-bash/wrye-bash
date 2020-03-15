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
"""GameInfo override for TES V: Skyrim Special Edition."""

from ..skyrim import SkyrimGameInfo
from ... import brec
from ...brec import MreGlob

class SkyrimSEGameInfo(SkyrimGameInfo):
    displayName = u'Skyrim Special Edition'
    fsName = u'Skyrim Special Edition'
    altName = u'Wrye Smash'
    defaultIniFile = u'Skyrim_Default.ini'
    launch_exe = u'SkyrimSE.exe'
    game_detect_file = [u'SkyrimSE.exe']
    version_detect_file = [u'SkyrimSE.exe']
    masterlist_dir = u'SkyrimSE'
    regInstallKeys = (
        u'Bethesda Softworks\\Skyrim Special Edition',
        u'Installed Path'
    )

    nexusUrl = u'https://www.nexusmods.com/skyrimspecialedition/'
    nexusName = u'Skyrim SE Nexus'
    nexusKey = 'bash.installers.openSkyrimSeNexus.continue'

    espm_extensions = SkyrimGameInfo.espm_extensions | {u'.esl'}
    has_achlist = True
    check_esl = True

    allTags = SkyrimGameInfo.allTags - {u'MustBeActiveIfImported', u'NoMerge',}

    patchers = ( # PatchMerger must come first if enabled!
        u'ActorImporter', u'CellImporter', u'ContentsChecker',
        u'DeathItemPatcher', u'DestructiblePatcher', u'GmstTweaker',
        u'GraphicsPatcher', u'ImportActorsSpells', u'ImportInventory',
        u'KeywordsImporter', u'ListsMerger', u'NamesPatcher',
        u'NPCAIPackagePatcher', u'ObjectBoundsImporter', u'SoundPatcher',
        u'SpellsPatcher', u'StatsPatcher', u'TextImporter', u'TweakActors',
    )

    # MreScpt is Oblivion/FO3/FNV Only
    # MreMgef, has not been verified to be used here for Skyrim

    class se(SkyrimGameInfo.se):
        se_abbrev = u'SKSE64'
        long_name = u'Skyrim SE Script Extender'
        exe = u'skse64_loader.exe'
        ver_files = [u'skse64_loader.exe', u'skse64_steam_loader.dll']

    # ScriptDragon doesn't exist for SSE
    class sd(SkyrimGameInfo.sd):
        sd_abbrev = u''
        long_name = u''
        install_dir = u''

    class Bsa(SkyrimGameInfo.Bsa):
        valid_versions = {0x69}
        vanilla_string_bsas = {
            u'skyrim.esm': [u'Skyrim - Patch.bsa', u'Skyrim - Interface.bsa'],
            u'update.esm': [u'Skyrim - Patch.bsa', u'Skyrim - Interface.bsa'],
            u'dawnguard.esm': [u'Skyrim - Patch.bsa',
                               u'Skyrim - Interface.bsa'],
            u'hearthfires.esm': [u'Skyrim - Patch.bsa',
                                 u'Skyrim - Interface.bsa'],
            u'dragonborn.esm': [u'Skyrim - Patch.bsa',
                                u'Skyrim - Interface.bsa'],
        }

    class xe(SkyrimGameInfo.xe):
        full_name = u'SSEEdit'
        expert_key = 'sseView.iKnowWhatImDoing'

    SkipBAINRefresh = {u'sseedit backups', u'sseedit cache'}

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
            MreFlor, MreFlst, MreFstp, MreFsts, MreFurn, MreGmst, MreGras, \
            MreHazd, MreHdpt, MreTes4, MreIdle, MreIdlm, MreImad, MreImgs, \
            MreInfo, MreIngr, MreIpct, MreIpds, MreKeym, MreKywd, MreLcrt, \
            MreLctn, MreLgtm, MreLigh, MreLscr, MreLvli, MreLvln, MreLvsp, \
            MreMatt, MreMesg, MreMgef, MreMisc, MreMovt, MreMstt, MreMusc, \
            MreMust, MreNpc, MreOtft, MrePerk, MreProj, MreQust, MreRegn, \
            MreRela, MreRevb, MreRfct, MreScrl, MreShou, MreSlgm, MreSmbn, \
            MreSmen, MreSmqn, MreSnct, MreSndr, MreSopm, MreSoun, MreSpel, \
            MreSpgd, MreTact, MreTree, MreTxst, MreVtyp, MreWoop, MreWrld, \
            MreAmmo, MreLtex, MreMato, MreStat, MreWatr, MreWeap, MreWthr, \
            MrePack
        cls.mergeClasses = (
            # MreAchr, MreDial, MreInfo, MreFact,
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
            MrePack,
        )
        # Setting RecordHeader class variables --------------------------------
        brec.RecordHeader.topTypes = [
            'GMST', 'KYWD', 'LCRT', 'AACT', 'TXST', 'GLOB', 'CLAS', 'FACT',
            'HDPT', 'HAIR', 'EYES', 'RACE', 'SOUN', 'ASPC', 'MGEF', 'SCPT',
            'LTEX', 'ENCH', 'SPEL', 'SCRL', 'ACTI', 'TACT', 'ARMO', 'BOOK',
            'CONT', 'DOOR', 'INGR', 'LIGH', 'MISC', 'APPA', 'STAT', 'SCOL',
            'MSTT', 'PWAT', 'GRAS', 'TREE', 'CLDC', 'FLOR', 'FURN', 'WEAP',
            'AMMO', 'NPC_', 'LVLN', 'KEYM', 'ALCH', 'IDLM', 'COBJ', 'PROJ',
            'HAZD', 'SLGM', 'LVLI', 'WTHR', 'CLMT', 'SPGD', 'RFCT', 'REGN',
            'NAVI', 'CELL', 'WRLD', 'DIAL', 'QUST', 'IDLE', 'PACK', 'CSTY',
            'LSCR', 'LVSP', 'ANIO', 'WATR', 'EFSH', 'EXPL', 'DEBR', 'IMGS',
            'IMAD', 'FLST', 'PERK', 'BPTD', 'ADDN', 'AVIF', 'CAMS', 'CPTH',
            'VTYP', 'MATT', 'IPCT', 'IPDS', 'ARMA', 'ECZN', 'LCTN', 'MESG',
            'RGDL', 'DOBJ', 'LGTM', 'MUSC', 'FSTP', 'FSTS', 'SMBN', 'SMQN',
            'SMEN', 'DLBR', 'MUST', 'DLVW', 'WOOP', 'SHOU', 'EQUP', 'RELA',
            'SCEN', 'ASTP', 'OTFT', 'ARTO', 'MATO', 'MOVT', 'SNDR', 'DUAL',
            'SNCT', 'SOPM', 'COLL', 'CLFM', 'REVB', 'LENS', 'VOLI']
        #-> this needs updating for Skyrim
        brec.RecordHeader.recordTypes = set(
            brec.RecordHeader.topTypes + ['GRUP', 'TES4', 'REFR', 'ACHR',
                                          'ACRE', 'LAND', 'INFO', 'NAVM',
                                          'PHZD', 'PGRE'])
        brec.RecordHeader.plugin_form_version = 44
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
            MreNpc, MreOtft, MrePerk, MreProj, MreRegn, MreRela, MreRevb,
            MreRfct, MreScrl, MreShou, MreSlgm, MreSmbn, MreSmen, MreSmqn,
            MreSnct, MreSndr, MreSopm, MreSoun, MreSpel, MreSpgd, MreStat,
            MreTact, MreTree, MreTxst, MreVtyp, MreWatr, MreWeap, MreWoop,
            MreWthr, MreCell, MreWrld, MreVoli, MreLens, MreQust, MreTes4,
            MrePack,
            # MreNavm, MreNavi
        ))
        brec.MreRecord.simpleTypes = (
            set(brec.MreRecord.type_class) - {'TES4', 'ACHR', 'CELL', 'DIAL',
                                              'INFO', 'WRLD', })

GAME_TYPE = SkyrimSEGameInfo
