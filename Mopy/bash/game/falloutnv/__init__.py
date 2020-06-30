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
"""GameInfo override for Fallout NV."""
from ..fallout3 import Fallout3GameInfo
from ... import brec
from ...brec import MreFlst, MreGlob

class FalloutNVGameInfo(Fallout3GameInfo):
    displayName = u'Fallout New Vegas'
    fsName = u'FalloutNV'
    altName = u'Wrye Flash NV'
    bash_root_prefix = u'FalloutNV'
    defaultIniFile = u'Fallout_default.ini'
    launch_exe = u'FalloutNV.exe'
    game_detect_file = [u'FalloutNV.exe']
    version_detect_file = [u'FalloutNV.exe']
    master_file = u'FalloutNV.esm'
    iniFiles = [u'Fallout.ini', u'FalloutPrefs.ini']
    pklfile = u'bash\\db\\FalloutNV_ids.pkl'
    masterlist_dir = u'FalloutNV'
    regInstallKeys = (u'Bethesda Softworks\\FalloutNV',u'Installed Path')
    nexusUrl = u'https://www.nexusmods.com/newvegas/'
    nexusName = u'New Vegas Nexus'
    nexusKey = u'bash.installers.openNewVegasNexus'

    class Se(Fallout3GameInfo.Se):
        se_abbrev = u'NVSE'
        long_name = u'Fallout Script Extender'
        exe = u'nvse_loader.exe'
        ver_files = [u'nvse_loader.exe', u'nvse_steam_loader.dll']
        plugin_dir = u'NVSE'
        cosave_tag = u'NVSE'
        cosave_ext = u'.nvse'
        url = u'http://nvse.silverlock.org/'
        url_tip = u'http://nvse.silverlock.org/'

    class Xe(Fallout3GameInfo.Xe):
        full_name = u'FNVEdit'
        xe_key_prefix = u'fnvView'

    # BAIN:
    dataDirs = (Fallout3GameInfo.dataDirs - {u'fose'}) | {u'nvse'}
    SkipBAINRefresh = {u'fnvedit backups', u'fnvedit cache'}
    ignoreDataFiles = {
        #    u'NVSE\\Plugins\\Construction Set Extender.dll',
        #    u'NVSE\\Plugins\\Construction Set Extender.ini'
    }
    ignoreDataDirs = {u'LSData'} #    u'NVSE\\Plugins\\ComponentDLLs\\CSE',

    class Esp(Fallout3GameInfo.Esp):
        canCBash = False # True?
        validHeaderVersions = (0.94, 1.32, 1.33, 1.34)

    #--Bash Tags supported by this game
    # 'Body-F', 'Body-M', 'Body-Size-M', 'Body-Size-F', 'C.Climate', 'C.Light',
    # 'C.Music', 'C.Name', 'C.RecordFlags', 'C.Owner', 'C.Water','Deactivate',
    # 'Delev', 'Eyes', 'Factions', 'Relations', 'Filter', 'Graphics', 'Hair',
    # 'IIM', 'Invent', 'Names', 'NoMerge', 'NpcFaces', 'R.Relations', 'Relev',
    # 'Scripts', 'ScriptContents', 'Sound', 'Stats', 'Voice-F', 'Voice-M',
    # 'R.Teeth', 'R.Mouth', 'R.Ears', 'R.Head', 'R.Attributes-F',
    # 'R.Attributes-M', 'R.Skills', 'R.Description', 'Roads', 'Actors.Anims',
    # 'Actors.AIData', 'Actors.DeathItem', 'Actors.AIPackages',
    # 'Actors.AIPackagesForceAdd', 'Actors.Stats', 'Actors.ACBS', 'NPC.Class',
    # 'Actors.CombatStyle', 'Creatures.Blood', 'NPC.Race','Actors.Skeleton',
    # 'NpcFacesForceFullImport', 'MustBeActiveIfImported', 'Deflst',
    # 'Destructible', 'WeaponMods'
    allTags = Fallout3GameInfo.allTags | {u'WeaponMods'}

    # ActorImporter, AliasesPatcher, AssortedTweaker, CellImporter, ContentsChecker,
    # DeathItemPatcher, DestructiblePatcher, FidListsMerger, GlobalsTweaker,
    # GmstTweaker, GraphicsPatcher, ImportFactions, ImportInventory, ImportRelations,
    # ImportScriptContents, ImportScripts, KFFZPatcher, ListsMerger, NamesPatcher,
    # NamesTweaker, NPCAIPackagePatcher, NpcFacePatcher, PatchMerger, RacePatcher,
    # RoadImporter, SoundPatcher, StatsPatcher, UpdateReferences, WeaponModsPatcher,
    #--Patcher available when building a Bashed Patch (referenced by class name)
    patchers = Fallout3GameInfo.patchers + (u'WeaponModsPatcher',)

    @classmethod
    def init(cls):
        cls._dynamic_import_modules(__name__)
        # From Valda's version
        # MreAchr, MreAcre, MreActi, MreAlch, MreAloc, MreAmef, MreAmmo,
        # MreAnio, MreAppa, MreArma, MreArmo, MreAspc, MreAvif, MreBook,
        # MreBptd, MreBsgn, MreCcrd, MreCdck, MreChal, MreChip, MreClas,
        # MreClmt, MreClot, MreCmny, MreCont, MreCrea, MreCsno, MreCsty,
        # MreDebr, MreDehy, MreDial, MreDobj, MreDoor, MreEczn, MreEfsh,
        # MreEnch, MreExpl, MreEyes, MreFact, MreFlor, MreFlst, MreFurn,
        # MreGlob, MreGmst, MreGras, MreHair, MreHdpt, MreHung, MreIdle,
        # MreIdlm, MreImad, MreImod, MreInfo, MreIngr, MreIpct, MreIpds,
        # MreKeym, MreLigh, MreLscr, MreLsct, MreLtex, MreLvlc, MreLvli,
        # MreLvln, MreLvsp, MreMgef, MreMicn, MreMisc, MreMset, MreMstt,
        # MreMusc, MreNote, MreNpc, MrePack, MrePerk, MreProj, MrePwat,
        # MreQust, MreRace, MreRcct, MreRcpe, MreRefr, MreRegn, MreRepu,
        # MreRoad, MreSbsp, MreScpt, MreSgst, MreSkil, MreSlgm, MreSlpd,
        # MreSoun, MreSpel, MreStat, MreTact, MreTerm, MreTes4, MreTree,
        # MreTxst, MreVtyp, MreWatr, MreWeap, MreWthr, MreCell, MreWrld,
        # MreNavm,
        # First import from our record file
        from .records import MreActi, MreAloc, MreAmef, MreAmmo, MreArma, \
            MreArmo, MreAspc, MreCcrd, MreCdck, MreChal, MreChip, MreCmny, \
            MreCont, MreCsno, MreCsty, MreDehy, MreDobj, MreEnch, MreFact, \
            MreHdpt, MreHung, MreImad, MreImod, MreIpct, MreKeym, MreLigh, \
            MreLscr, MreLsct, MreMisc, MreMset, MreMusc, MreProj, MreRcct, \
            MreRcpe, MreRegn, MreRepu, MreSlpd, MreSoun, MreStat, MreTact, \
            MreWeap, MreWthr, MreAchr, MreAcre, MreCell, MreDial, MreGmst, \
            MreInfo, MrePgre, MrePmis, MreRefr, MreTes4
        # then from fallout3.records
        from ..fallout3.records import MreCpth, MreIdle, MreMesg, MrePack, \
            MrePerk, MreQust, MreSpel, MreTerm, MreNpc, MreAddn, MreAnio, \
            MreAvif, MreBook, MreBptd, MreCams, MreClas, MreClmt, MreCobj, \
            MreCrea, MreDebr, MreDoor, MreEczn, MreEfsh, MreExpl, MreEyes, \
            MreFurn, MreGras, MreHair, MreIdlm, MreImgs, MreIngr, MreRace, \
            MreIpds, MreLgtm, MreLtex, MreLvlc, MreLvli, MreLvln, MreMgef, \
            MreMicn, MreMstt, MreNavi, MreNavm, MreNote, MrePwat, MreRads, \
            MreRgdl, MreScol, MreScpt, MreTree, MreTxst, MreVtyp, MreWatr, \
            MreWrld, MreAlch
        # Old Mergeable from Valda's version
        # MreActi, MreAlch, MreAloc, MreAmef, MreAmmo, MreAnio, MreAppa,
        # MreArma, MreArmo, MreAspc, MreAvif, MreBook, MreBptd, MreBsgn,
        # MreCcrd, MreCdck, MreChal, MreChip, MreClas, MreClmt, MreClot,
        # MreCmny, MreCont, MreCrea, MreCsno, MreCsty, MreDebr, MreDehy,
        # MreDobj, MreDoor, MreEczn, MreEfsh, MreEnch, MreExpl, MreEyes,
        # MreFact, MreFlor, MreFlst, MreFurn, MreGlob, MreGras, MreHair,
        # MreHdpt, MreHung, MreIdle, MreIdlm, MreImad, MreImod, MreIngr,
        # MreIpct, MreIpds, MreKeym, MreLigh, MreLscr, MreLsct, MreLtex,
        # MreLvlc, MreLvli, MreLvln, MreLvsp, MreMgef, MreMicn, MreMisc,
        # MreMset, MreMstt, MreMusc, MreNote, MreNpc, MrePack, MrePerk,
        # MreProj, MrePwat, MreQust, MreRace, MreRcct, MreRcpe, MreRegn,
        # MreRepu, MreSbsp, MreScpt, MreSgst, MreSkil, MreSlgm, MreSlpd,
        # MreSoun, MreSpel, MreStat, MreTact, MreTerm, MreTree, MreTxst,
        # MreVtyp, MreWatr, MreWeap, MreWthr,
        cls.mergeClasses = (
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
            )
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
        brec.MreRecord.type_class = {
            x.rec_sig: x for x in (cls.mergeClasses +  # Not Mergeable
                (MreAchr, MreAcre, MreCell, MreDial, MreInfo, MreNavi,
                 MreNavm, MrePgre, MrePmis, MreRefr, MreWrld, MreTes4,))}
        brec.MreRecord.simpleTypes = (
            set(brec.MreRecord.type_class) - {
            # b'TES4',b'ACHR',b'ACRE',b'REFR',b'CELL',b'PGRD',b'PGRE',b'LAND',
            # b'WRLD',b'INFO',b'DIAL',b'NAVM'
            b'TES4', b'ACHR', b'ACRE', b'CELL', b'DIAL', b'INFO', b'LAND', b'NAVI',
            b'NAVM', b'PGRE', b'PMIS', b'REFR', b'WRLD', })

GAME_TYPE = FalloutNVGameInfo
