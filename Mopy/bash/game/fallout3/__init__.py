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
"""GameInfo override for Fallout 3."""
from .default_tweaks import default_tweaks
from .. import GameInfo
from ... import brec
from ...brec import MreGlob

class Fallout3GameInfo(GameInfo):
    displayName = u'Fallout 3'
    fsName = u'Fallout3'
    altName = u'Wrye Flash'
    defaultIniFile = u'Fallout_default.ini'
    launch_exe = u'Fallout3.exe'
    game_detect_file = [u'Fallout3.exe']
    version_detect_file = [u'Fallout3.exe']
    masterFiles = [u'Fallout3.esm']
    iniFiles = [u'Fallout.ini', u'FalloutPrefs.ini']
    pklfile = ur'bash\db\Fallout3_ids.pkl'
    masterlist_dir = u'Fallout3'
    regInstallKeys = (u'Bethesda Softworks\\Fallout3',u'Installed Path')
    nexusUrl = u'https://www.nexusmods.com/fallout3/'
    nexusName = u'Fallout 3 Nexus'
    nexusKey = u'bash.installers.openFallout3Nexus'

    allow_reset_bsa_timestamps = True
    supports_mod_inis = False

    using_txt_file = False

    class cs(GameInfo.cs):
        cs_abbrev = u'GECK'
        long_name = u'Garden of Eden Creation Kit'
        exe = u'GECK.exe'
        se_args = u'-editor'
        image_name = u'geck%s.png'

    class se(GameInfo.se):
        se_abbrev = u'FOSE'
        long_name = u'Fallout 3 Script Extender'
        exe = u'fose_loader.exe'
        steam_exe = u'fose_loader.dll'
        plugin_dir = u'FOSE'
        cosave_ext = u'.fose'
        url = u'http://fose.silverlock.org/'
        url_tip = u'http://fose.silverlock.org/'

    class ess(GameInfo.ess):
        ext = u'.fos'

    class pnd(GameInfo.pnd):
        facegen_dir_1 = [u'textures', u'characters', u'BodyMods']
        facegen_dir_2 = [u'textures', u'characters', u'FaceMods']

    # BAIN:
    dataDirs = GameInfo.dataDirs | {
        u'distantlod',
        u'docs',
        u'facegen',
        u'fonts',
        u'menus',
        u'shaders',
        u'trees',
        }
    dataDirsPlus = {
        u'scripts',
        u'ini',
        u'fose',
        }
    SkipBAINRefresh = {u'fo3edit backups', u'fo3edit cache'}
    wryeBashDataFiles = GameInfo.wryeBashDataFiles | {
        ur'ArchiveInvalidationInvalidated!.bsa'
        ur'Fallout - AI!.bsa'
    }
    ignoreDataFiles = {
        #    ur'FOSE\Plugins\Construction Set Extender.dll',
        #    ur'FOSE\Plugins\Construction Set Extender.ini'
    }
    ignoreDataDirs = {ur'LSData'} # r'FOSE\Plugins\ComponentDLLs\CSE',

    class esp(GameInfo.esp):
        canBash = True
        canEditHeader = True
        validHeaderVersions = (0.85, 0.94)
        stringsFiles = []

    #--Tags supported by this game
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
    # 'Destructible'
    allTags = {u'C.Acoustic', u'C.Climate', u'C.Encounter', u'C.ImageSpace',
               u'C.Light', u'C.Music', u'C.Name', u'C.Owner', u'C.RecordFlags',
               u'C.Water', u'Deactivate', u'Deflst', u'Delev', u'Destructible',
               u'Factions', u'Filter', u'Graphics', u'Invent', u'Names',
               u'NoMerge', u'Relations', u'Relev', u'Sound', u'Stats'}

    # ActorImporter, AliasesPatcher, AssortedTweaker, CellImporter, ContentsChecker,
    # DeathItemPatcher, DestructiblePatcher, FidListsMerger, GlobalsTweaker,
    # GmstTweaker, GraphicsPatcher, ImportFactions, ImportInventory, ImportRelations,
    # ImportScriptContents, ImportScripts, KFFZPatcher, ListsMerger, NamesPatcher,
    # NamesTweaker, NPCAIPackagePatcher, NpcFacePatcher, PatchMerger, RacePatcher,
    # RoadImporter, SoundPatcher, StatsPatcher, UpdateReferences,
    #--Patcher available when building a Bashed Patch (referenced by class name)
    patchers = (
        u'AliasesPatcher', u'CellImporter', u'DestructiblePatcher',
        u'FidListsMerger', u'GmstTweaker', u'GraphicsPatcher',
        u'ImportFactions', u'ImportInventory', u'ImportRelations',
        u'ListsMerger', u'NamesPatcher', u'PatchMerger', u'SoundPatcher',
        u'StatsPatcher',)

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
        cls._dynamic_import_constants(__name__)
        # From Valda's version
        # MreAchr, MreAcre, MreActi, MreAlch, MreAmmo, MreAnio, MreAppa,
        # MreArmo, MreBook, MreBsgn, MreCell, MreClas, MreClot, MreCont,
        # MreCrea, MreDoor, MreEfsh, MreEnch, MreEyes, MreFact, MreFlor,
        # MreFurn, MreGlob, MreGmst, MreGras, MreHair, MreIngr, MreKeym,
        # MreLigh, MreLscr, MreLvlc, MreLvli, MreLvsp, MreMgef, MreMisc,
        # MreNpc,  MrePack, MreQust, MreRace, MreRefr, MreRoad, MreScpt,
        # MreSgst, MreSkil, MreSlgm, MreSoun, MreSpel, MreStat, MreTree,
        # MreTes4, MreWatr, MreWeap, MreWrld, MreWthr, MreClmt, MreCsty,
        # MreIdle, MreLtex, MreRegn, MreSbsp, MreDial, MreInfo, MreTxst,
        # MreMicn, MreFlst, MrePerk, MreExpl, MreIpct, MreIpds, MreProj,
        # MreLvln, MreDebr, MreImad, MreMstt, MreNote, MreTerm, MreAvif,
        # MreEczn, MreBptd, MreVtyp, MreMusc, MrePwat, MreAspc, MreHdpt,
        # MreDobj, MreIdlm, MreArma, MreTact, MreNavm
        from .records import MreActi, MreAddn, MreAlch, MreAmmo, MreAnio, \
            MreArma, MreArmo, MreAspc, MreAvif, MreBook, MreBptd, MreCams, \
            MreClas, MreClmt, MreCobj, MreCont, MreCpth, MreCrea, MreCsty, \
            MreDebr, MreDobj, MreDoor, MreEczn, MreEfsh, MreEnch, MreExpl, \
            MreEyes, MreFact, MreFlst, MreFurn, MreGras, MreHair, MreHdpt, \
            MreIdle, MreIdlm, MreImad, MreImgs, MreIngr, MreIpct, MreIpds, \
            MreKeym, MreLgtm, MreLigh, MreLscr, MreLtex, MreLvlc, MreLvli, \
            MreLvln, MreMesg, MreMgef, MreMicn, MreMisc, MreMstt, MreMusc, \
            MreNote, MreNpc, MrePack, MrePerk, MreProj, MrePwat, MreQust, \
            MreRace, MreRads, MreRegn, MreRgdl, MreScol, MreScpt, MreSoun, \
            MreSpel, MreStat, MreTact, MreTerm, MreTree, MreTxst, MreVtyp, \
            MreWatr, MreWeap, MreWthr, MreAchr, MreAcre, MreCell, MreDial, \
            MreGmst, MreInfo, MreNavi, MreNavm, MrePgre, MrePmis, MreRefr, \
            MreWrld, MreHeader
        cls.mergeClasses = (
            MreActi, MreAddn, MreAlch, MreAmmo, MreAnio, MreArma, MreArmo,
            MreAspc, MreAvif, MreBook, MreBptd, MreCams, MreClas, MreClmt,
            MreCobj, MreCont, MreCpth, MreCrea, MreCsty, MreDebr, MreDobj,
            MreDoor, MreEczn, MreEfsh, MreEnch, MreExpl, MreEyes, MreFact,
            MreFlst, MreFurn, MreGlob, MreGras, MreHair, MreHdpt, MreIdle,
            MreIdlm, MreImad, MreImgs, MreIngr, MreIpct, MreIpds, MreKeym,
            MreLgtm, MreLigh, MreLscr, MreLtex, MreLvlc, MreLvli, MreLvln,
            MreMesg, MreMgef, MreMicn, MreMisc, MreMstt, MreMusc, MreNote,
            MreNpc, MrePack, MrePerk, MreProj, MrePwat, MreQust, MreRace,
            MreRads, MreRegn, MreRgdl, MreScol, MreScpt, MreSoun, MreSpel,
            MreStat, MreTact,MreTerm, MreTree, MreTxst, MreVtyp, MreWatr,
            MreWeap, MreWthr,
            )
        # Setting RecordHeader class variables --------------------------------
        brec.RecordHeader.topTypes = [
            'GMST', 'TXST', 'MICN', 'GLOB', 'CLAS', 'FACT', 'HDPT', 'HAIR',
            'EYES', 'RACE', 'SOUN', 'ASPC', 'MGEF', 'SCPT', 'LTEX', 'ENCH',
            'SPEL', 'ACTI', 'TACT', 'TERM', 'ARMO', 'BOOK', 'CONT', 'DOOR',
            'INGR', 'LIGH', 'MISC', 'STAT', 'SCOL', 'MSTT', 'PWAT', 'GRAS',
            'TREE', 'FURN', 'WEAP', 'AMMO', 'NPC_', 'CREA', 'LVLC', 'LVLN',
            'KEYM', 'ALCH', 'IDLM', 'NOTE', 'PROJ', 'LVLI', 'WTHR', 'CLMT',
            'COBJ', 'REGN', 'NAVI', 'CELL', 'WRLD', 'DIAL', 'QUST', 'IDLE',
            'PACK', 'CSTY', 'LSCR', 'ANIO', 'WATR', 'EFSH', 'EXPL', 'DEBR',
            'IMGS', 'IMAD', 'FLST', 'PERK', 'BPTD', 'ADDN', 'AVIF', 'RADS',
            'CAMS', 'CPTH', 'VTYP', 'IPCT', 'IPDS', 'ARMA', 'ECZN', 'MESG',
            'RGDL', 'DOBJ', 'LGTM', 'MUSC', ]
        brec.RecordHeader.recordTypes = set(
            brec.RecordHeader.topTypes + ['GRUP', 'TES4', 'ACHR', 'ACRE',
                                          'INFO', 'LAND', 'NAVM', 'PGRE',
                                          'PMIS', 'REFR'])
        brec.RecordHeader.plugin_form_version = 15
        brec.MreRecord.type_class = dict(
            (x.classType, x) for x in (cls.mergeClasses + # Not Mergeable
            (MreAchr, MreAcre, MreCell, MreDial, MreGmst, MreInfo, MreNavi,
             MreNavm, MrePgre, MrePmis, MreRefr, MreWrld, MreHeader)))
        brec.MreRecord.simpleTypes = (set(brec.MreRecord.type_class) - {
            # 'TES4','ACHR','ACRE','REFR','CELL','PGRD','ROAD','LAND',
            # 'WRLD','INFO','DIAL','PGRE','NAVM'
            'TES4', 'ACHR', 'ACRE', 'CELL', 'DIAL', 'INFO', 'LAND', 'NAVI',
            'NAVM', 'PGRE', 'PMIS', 'REFR', 'WRLD', })

GAME_TYPE = Fallout3GameInfo
