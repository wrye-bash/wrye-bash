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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2014 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This modules defines static data for use by bush, when
   Fallout NV is set at the active game."""
from .constants import *
from .default_tweaks import default_tweaks
from .. import GameInfo
from ... import brec
from ...brec import MreGlob

class FalloutNVGameInfo(GameInfo):
    displayName = u'Fallout New Vegas'
    fsName = u'FalloutNV'
    altName = u'Wrye Flash NV'
    defaultIniFile = u'Fallout_default.ini'
    exe = u'FalloutNV.exe'
    masterFiles = [u'FalloutNV.esm']
    iniFiles = [u'Fallout.ini', u'FalloutPrefs.ini']
    pklfile = ur'bash\db\FalloutNV_ids.pkl'
    regInstallKeys = (u'Bethesda Softworks\\FalloutNV',u'Installed Path')
    nexusUrl = u'http://www.nexusmods.com/newvegas/'
    nexusName = u'New Vegas Nexus'
    nexusKey = u'bash.installers.openNewVegasNexus'

    allow_reset_bsa_timestamps = True
    supports_mod_inis = False

    using_txt_file = False

    class cs(GameInfo.cs):
        shortName = u'GECK'
        longName = u'Garden of Eden Creation Kit'
        exe = u'GECK.exe'
        seArgs = u'-editor'
        imageName = u'geck%s.png'

    class se(GameInfo.se):
        shortName = u'NVSE'
        longName = u'Fallout Script Extender'
        exe = u'nvse_loader.exe'
        steamExe = u'nvse_loader.dll'
        url = u'http://nvse.silverlock.org/'
        urlTip = u'http://nvse.silverlock.org/'

    SkipBAINRefresh = {u'fnvedit backups'}

    class ess(GameInfo.ess):
        ext = u'.fos'

    dataDirs = {
        u'bash patches',
        u'distantlod',
        u'docs',
        u'facegen',
        u'fonts',
        u'menus',
        u'meshes',
        u'music',
        u'shaders',
        u'sound',
        u'textures',
        u'trees',
        u'video',
        }
    dataDirsPlus = {
        u'scripts',
        u'ini',
        u'nvse'
        }

    wryeBashDataFiles = {
        ur'ArchiveInvalidationInvalidated!.bsa'
        ur'Fallout - AI!.bsa'
    }
    ignoreDataFiles = {
        #    ur'NVSE\Plugins\Construction Set Extender.dll',
        #    ur'NVSE\Plugins\Construction Set Extender.ini'
    }
    ignoreDataDirs = {ur'LSData'} #    ur'NVSE\Plugins\ComponentDLLs\CSE',

    class esp(GameInfo.esp):
        canBash = True
        canCBash = False
        canEditHeader = True
        validHeaderVersions = (0.94, 1.32, 1.33, 1.34)
        stringsFiles = []

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
    allTags = {u'C.Acoustic', u'C.Climate', u'C.Encounter', u'C.ImageSpace',
               u'C.Light', u'C.Music', u'C.Name', u'C.Owner', u'C.RecordFlags',
               u'C.Water', u'Deactivate', u'Deflst', u'Delev', u'Destructible',
               u'Factions', u'Filter', u'Graphics', u'Invent', u'Names',
               u'NoMerge', u'Relations', u'Relev', u'Sound', u'Stats',
               u'WeaponMods'}

    # ActorImporter, AliasesPatcher, AssortedTweaker, CellImporter, ContentsChecker,
    # DeathItemPatcher, DestructiblePatcher, FidListsMerger, GlobalsTweaker,
    # GmstTweaker, GraphicsPatcher, ImportFactions, ImportInventory, ImportRelations,
    # ImportScriptContents, ImportScripts, KFFZPatcher, ListsMerger, NamesPatcher,
    # NamesTweaker, NPCAIPackagePatcher, NpcFacePatcher, PatchMerger, RacePatcher,
    # RoadImporter, SoundPatcher, StatsPatcher, UpdateReferences, WeaponModsPatcher,
    #--Patcher available when building a Bashed Patch (referenced by class name)
    patchers = (
        u'AliasesPatcher', u'CellImporter', u'DestructiblePatcher',
        u'FidListsMerger', u'GmstTweaker', u'GraphicsPatcher',
        u'ImportFactions', u'ImportInventory', u'ImportRelations',
        u'ListsMerger', u'NamesPatcher', u'PatchMerger', u'SoundPatcher',
        u'StatsPatcher', u'WeaponModsPatcher',)

    weaponTypes = (
        _(u'Big gun'),
        _(u'Energy'),
        _(u'Small gun'),
        _(u'Melee'),
        _(u'Unarmed'),
        _(u'Thrown'),
        _(u'Mine'),
        )

    raceNames = {
        0x000019 : _(u'Caucasian'),
        0x0038e5 : _(u'Hispanic'),
        0x0038e6 : _(u'Asian'),
        0x003b3e : _(u'Ghoul'),
        0x00424a : _(u'AfricanAmerican'),
        0x0042be : _(u'AfricanAmerican Child'),
        0x0042bf : _(u'AfricanAmerican Old'),
        0x0042c0 : _(u'Asian Child'),
        0x0042c1 : _(u'Asian Old'),
        0x0042c2 : _(u'Caucasian Child'),
        0x0042c3 : _(u'Caucasian Old'),
        0x0042c4 : _(u'Hispanic Child'),
        0x0042c5 : _(u'Hispanic Old'),
        0x04bb8d : _(u'Caucasian Raider'),
        0x04bf70 : _(u'Hispanic Raider'),
        0x04bf71 : _(u'Asian Raider'),
        0x04bf72 : _(u'AfricanAmerican Raider'),
        0x0987dc : _(u'Hispanic Old Aged'),
        0x0987dd : _(u'Asian Old Aged'),
        0x0987de : _(u'AfricanAmerican Old Aged'),
        0x0987df : _(u'Caucasian Old Aged'),
        }

    raceShortNames = {
        0x000019 : u'Cau',
        0x0038e5 : u'His',
        0x0038e6 : u'Asi',
        0x003b3e : u'Gho',
        0x00424a : u'Afr',
        0x0042be : u'AfC',
        0x0042bf : u'AfO',
        0x0042c0 : u'AsC',
        0x0042c1 : u'AsO',
        0x0042c2 : u'CaC',
        0x0042c3 : u'CaO',
        0x0042c4 : u'HiC',
        0x0042c5 : u'HiO',
        0x04bb8d : u'CaR',
        0x04bf70 : u'HiR',
        0x04bf71 : u'AsR',
        0x04bf72 : u'AfR',
        0x0987dc : u'HOA',
        0x0987dd : u'AOA',
        0x0987de : u'FOA',
        0x0987df : u'COA',
        }

    raceHairMale = {
        0x000019 : 0x014b90, #--Cau
        0x0038e5 : 0x0a9d6f, #--His
        0x0038e6 : 0x014b90, #--Asi
        0x003b3e : None, #--Gho
        0x00424a : 0x0306be, #--Afr
        0x0042be : 0x060232, #--AfC
        0x0042bf : 0x0306be, #--AfO
        0x0042c0 : 0x060232, #--AsC
        0x0042c1 : 0x014b90, #--AsO
        0x0042c2 : 0x060232, #--CaC
        0x0042c3 : 0x02bfdb, #--CaO
        0x0042c4 : 0x060232, #--HiC
        0x0042c5 : 0x02ddee, #--HiO
        0x04bb8d : 0x02bfdb, #--CaR
        0x04bf70 : 0x02bfdb, #--HiR
        0x04bf71 : 0x02bfdb, #--AsR
        0x04bf72 : 0x0306be, #--AfR
        0x0987dc : 0x0987da, #--HOA
        0x0987dd : 0x0987da, #--AOA
        0x0987de : 0x0987d9, #--FOA
        0x0987df : 0x0987da, #--COA
        }

    raceHairFemale = {
        0x000019 : 0x05dc6b, #--Cau
        0x0038e5 : 0x05dc76, #--His
        0x0038e6 : 0x022e50, #--Asi
        0x003b3e : None, #--Gho
        0x00424a : 0x05dc78, #--Afr
        0x0042be : 0x05a59e, #--AfC
        0x0042bf : 0x072e39, #--AfO
        0x0042c0 : 0x05a5a3, #--AsC
        0x0042c1 : 0x072e39, #--AsO
        0x0042c2 : 0x05a59e, #--CaC
        0x0042c3 : 0x072e39, #--CaO
        0x0042c4 : 0x05a59e, #--HiC
        0x0042c5 : 0x072e39, #--HiO
        0x04bb8d : 0x072e39, #--CaR
        0x04bf70 : 0x072e39, #--HiR
        0x04bf71 : 0x072e39, #--AsR
        0x04bf72 : 0x072e39, #--AfR
        0x0987dc : 0x044529, #--HOA
        0x0987dd : 0x044529, #--AOA
        0x0987de : 0x044529, #--FOA
        0x0987df : 0x044529, #--COA
        }

    @classmethod
    def init(cls):
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
        from .records import MreActi, MreAloc, MreAmef, MreAmmo, MreArma, \
            MreArmo, MreAspc, MreCcrd, MreCdck, MreChal, MreChip, MreCmny, \
            MreCont, MreCpth, MreCsno, MreCsty, MreDehy, MreDobj, MreEnch, \
            MreFact, MreHdpt, MreHung, MreIdle, MreImad, MreImod, MreIpct, \
            MreKeym, MreLigh, MreLscr, MreLsct, MreMesg, MreMisc, MreMset, \
            MreMusc, MrePack, MrePerk, MreProj, MreQust, MreRace, MreRcct, \
            MreRcpe, MreRegn, MreRepu, MreSlpd, MreSoun, MreSpel, MreStat, \
            MreTact, MreTerm, MreWeap, MreWthr, MreAchr, MreAcre, MreCell, \
            MreDial, MreGmst, MreInfo, MrePgre, MrePmis, MreRefr, MreHeader, \
            MreNpc
        from ..fallout3.records import MreAddn, MreAnio, MreAvif, MreBook, \
            MreBptd, MreCams, MreClas, MreClmt, MreCobj, MreCrea, MreDebr, \
            MreDoor, MreEczn, MreEfsh, MreExpl, MreEyes, MreFlst, MreFurn, \
            MreGras, MreHair, MreIdlm, MreImgs, MreIngr, MreIpds, MreLgtm, \
            MreLtex, MreLvlc, MreLvli, MreLvln, MreMgef, MreMicn, MreMstt, \
            MreNavi, MreNavm, MreNote, MrePwat, MreRads, MreRgdl, MreScol, \
            MreScpt, MreTree, MreTxst, MreVtyp, MreWatr, MreWrld, MreAlch
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
                MreTxst, MreVtyp, MreWatr, MreWeap, MreWthr,
            )
        # Setting RecordHeader class variables --------------------------------
        brec.RecordHeader.topTypes = [
            'GMST', 'TXST', 'MICN', 'GLOB', 'CLAS', 'FACT', 'HDPT', 'HAIR',
            'EYES', 'RACE', 'SOUN', 'ASPC', 'MGEF', 'SCPT', 'LTEX', 'ENCH',
            'SPEL', 'ACTI', 'TACT', 'TERM', 'ARMO', 'BOOK', 'CONT', 'DOOR',
            'INGR', 'LIGH', 'MISC', 'STAT', 'SCOL', 'MSTT', 'PWAT', 'GRAS',
            'TREE', 'FURN', 'WEAP', 'AMMO', 'NPC_', 'CREA', 'LVLC', 'LVLN',
            'KEYM', 'ALCH', 'IDLM', 'NOTE', 'COBJ', 'PROJ', 'LVLI', 'WTHR',
            'CLMT', 'REGN', 'NAVI', 'DIAL', 'QUST', 'IDLE', 'PACK', 'CSTY',
            'LSCR', 'ANIO', 'WATR', 'EFSH', 'EXPL', 'DEBR', 'IMGS', 'IMAD',
            'FLST', 'PERK', 'BPTD', 'ADDN', 'AVIF', 'RADS', 'CAMS', 'CPTH',
            'VTYP', 'IPCT', 'IPDS', 'ARMA', 'ECZN', 'MESG', 'RGDL', 'DOBJ',
            'LGTM', 'MUSC', 'IMOD', 'REPU', 'RCPE', 'RCCT', 'CHIP', 'CSNO',
            'LSCT', 'MSET', 'ALOC', 'CHAL', 'AMEF', 'CCRD', 'CMNY', 'CDCK',
            'DEHY', 'HUNG', 'SLPD', 'CELL', 'WRLD', ]
        brec.RecordHeader.recordTypes = set(
            brec.RecordHeader.topTypes + ['GRUP', 'TES4', 'ACHR', 'ACRE',
                                          'INFO', 'LAND', 'NAVM', 'PGRE',
                                          'PMIS', 'REFR'])
        brec.RecordHeader.plugin_form_version = 15
        brec.MreRecord.type_class = dict(
            (x.classType, x) for x in (cls.mergeClasses +  # Not Mergeable
            (MreAchr, MreAcre, MreCell, MreDial, MreGmst, MreInfo, MreNavi,
             MreNavm, MrePgre, MrePmis, MreRefr, MreWrld, MreHeader,)))
        brec.MreRecord.simpleTypes = (
            set(brec.MreRecord.type_class) - {
            # 'TES4','ACHR','ACRE','REFR','CELL','PGRD','PGRE','LAND',
            # 'WRLD','INFO','DIAL','NAVM'
            'TES4', 'ACHR', 'ACRE', 'CELL', 'DIAL', 'INFO', 'LAND', 'NAVI',
            'NAVM', 'PGRE', 'PMIS', 'REFR', 'WRLD', })

GAME_TYPE = FalloutNVGameInfo
