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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""GameInfo override for TES V: Skyrim VR."""

from ..skyrimse import SkyrimSEGameInfo
from ... import brec
from ...brec import MreGlob

class SkyrimVRGameInfo(SkyrimSEGameInfo):
    displayName = u'Skyrim VR'
    fsName = u'Skyrim VR'
    altName = u'Wrye VRash'
    launch_exe = u'SkyrimVR.exe'
    game_detect_file = [u'SkyrimVR.exe']
    version_detect_file = [u'SkyrimVR.exe']
    regInstallKeys = (
        u'Bethesda Softworks\\Skyrim VR',
        u'Installed Path'
    )

    espm_extensions = SkyrimSEGameInfo.espm_extensions - {u'.esl'}
    check_esl = False

    allTags = SkyrimSEGameInfo.allTags | {u'NoMerge'}
    patchers = (u'PatchMerger', # PatchMerger must come first !
        u'ActorImporter', u'CellImporter', u'ContentsChecker',
        u'DeathItemPatcher', u'DestructiblePatcher', u'GmstTweaker',
        u'GraphicsPatcher', u'ImportActorsSpells', u'ImportInventory',
        u'KeywordsImporter', u'ListsMerger', u'NamesPatcher',
        u'NPCAIPackagePatcher', u'ObjectBoundsImporter', u'SoundPatcher',
        u'SpellsPatcher', u'StatsPatcher', u'TextImporter', u'TweakActors',
    )

    class Se(SkyrimSEGameInfo.Se):
        se_abbrev = u'SKSEVR'
        long_name = u'Skyrim VR Script Extender'
        exe = u'sksevr_loader.exe'
        ver_files = [u'sksevr_loader.exe', u'sksevr_steam_loader.dll']

    class Bsa(SkyrimSEGameInfo.Bsa):
        vanilla_string_bsas = SkyrimSEGameInfo.Bsa.vanilla_string_bsas.copy()
        vanilla_string_bsas.update({
            u'skyrimvr.esm': [u'Skyrim - Patch.bsa', u'Skyrim - Interface.bsa',
                              u'Skyrim_VR - Main.bsa'],
        })

    class Xe(SkyrimSEGameInfo.Xe):
        full_name = u'TES5VREdit'
        expert_key = 'tes5vrview.iKnowWhatImDoing'

    SkipBAINRefresh = {u'tes5vredit backups', u'tes5vredit cache'}

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

GAME_TYPE = SkyrimVRGameInfo
