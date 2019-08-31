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
"""GameInfo override for TES V: Skyrim."""

from .default_tweaks import default_tweaks
from .. import GameInfo
from ... import brec
from ...brec import MreGlob

class SkyrimGameInfo(GameInfo):
    displayName = u'Skyrim'
    fsName = u'Skyrim'
    altName = u'Wrye Smash'
    defaultIniFile = u'Skyrim_default.ini'
    launch_exe = u'TESV.exe'
    # Set to this because TESV.exe also exists for Enderal
    game_detect_file = [u'SkyrimLauncher.exe']
    version_detect_file = [u'TESV.exe']
    masterFiles = [u'Skyrim.esm', u'Update.esm']
    iniFiles = [u'Skyrim.ini', u'SkyrimPrefs.ini']
    pklfile = ur'bash\db\Skyrim_ids.pkl'
    masterlist_dir = u'Skyrim'
    regInstallKeys = (u'Bethesda Softworks\\Skyrim', u'Installed Path')
    nexusUrl = u'https://www.nexusmods.com/skyrim/'
    nexusName = u'Skyrim Nexus'
    nexusKey = 'bash.installers.openSkyrimNexus.continue'

    has_bsl = True
    vanilla_string_bsas = {
        u'skyrim.esm': [u'Skyrim - Interface.bsa'],
        u'update.esm': [u'Skyrim - Interface.bsa'],
        u'dawnguard.esm': [u'Dawnguard.bsa'],
        u'hearthfires.esm': [u'Hearthfires.bsa'],
        u'dragonborn.esm': [u'Dragonborn.bsa'],
    }
    resource_archives_keys = (u'sResourceArchiveList', u'sResourceArchiveList2')
    script_extensions = {u'.psc'}

    class cs(GameInfo.cs):
        cs_abbrev = u'CK'
        long_name = u'Creation Kit'
        exe = u'CreationKit.exe'
        se_args = None  # u'-editor'
        image_name = u'creationkit%s.png'

    class se(GameInfo.se):
        se_abbrev = u'SKSE'
        long_name = u'Skyrim Script Extender'
        exe = u'skse_loader.exe'
        steam_exe = u'skse_loader.exe'
        plugin_dir = u'SKSE'
        cosave_ext = u'.skse'
        url = u'http://skse.silverlock.org/'
        url_tip = u'http://skse.silverlock.org/'

    class sd(GameInfo.sd):
        sd_abbrev = u'SD'
        long_name = u'Script Dragon'
        install_dir = u'asi'

    class sp(GameInfo.sp):
        sp_abbrev = u'SP'
        long_name = u'SkyProc'
        install_dir = u'SkyProc Patchers'

    class ini(GameInfo.ini):
        allowNewLines = True
        bsaRedirection = (u'', u'')

    class pnd(GameInfo.pnd):
        facegen_dir_1 = [u'meshes', u'actors', u'character', u'facegendata',
                         u'facegeom']
        facegen_dir_2 = [u'textures', u'actors', u'character', u'facegendata',
                         u'facetint']

    # BAIN:
    dataDirs = GameInfo.dataDirs | {
        u'dialogueviews',
        u'grass',
        u'interface',
        u'lodsettings',
        u'scripts',
        u'seq',
        u'shadersfx',
        u'strings',
    }
    dataDirsPlus = {
        u'asi',
        u'calientetools', # bodyslide
        u'dyndolod',
        u'ini',
        u'skse',
        u'skyproc patchers',
        u'tools', # Bodyslide, FNIS
    }
    dontSkip = (
           # These are all in the Interface folder. Apart from the skyui_ files,
           # they are all present in vanilla.
           u'skyui_cfg.txt',
           u'skyui_translate.txt',
           u'credits.txt',
           u'credits_french.txt',
           u'fontconfig.txt',
           u'controlmap.txt',
           u'gamepad.txt',
           u'mouse.txt',
           u'keyboard_english.txt',
           u'keyboard_french.txt',
           u'keyboard_german.txt',
           u'keyboard_spanish.txt',
           u'keyboard_italian.txt',
    )
    dontSkipDirs = {
        # This rule is to allow mods with string translation enabled.
        'interface\\translations':['.txt']
    }
    SkipBAINRefresh = {u'tes5edit backups', u'tes5edit cache'}
    ignoreDataDirs = {u'LSData'}

    class esp(GameInfo.esp):
        canBash = True
        canEditHeader = True
        validHeaderVersions = (0.94, 1.70,)

    allTags = {u'C.Acoustic', u'C.Climate', u'C.Encounter', u'C.ForceHideLand',
               u'C.ImageSpace', u'C.Light', u'C.Location', u'C.LockList',
               u'C.Music', u'C.Name', u'C.Owner', u'C.RecordFlags',
               u'C.Regions', u'C.SkyLighting', u'C.Water', u'Deactivate',
               u'Delev', u'Filter', u'Graphics', u'Invent', u'Names',
               u'NoMerge', u'Relev', u'Sound', u'Stats'}

    patchers = (
        u'CellImporter', u'GmstTweaker', u'GraphicsPatcher',
        u'ImportInventory', u'ListsMerger', u'PatchMerger', u'SoundPatcher',
        u'StatsPatcher', u'NamesPatcher',
        )

    weaponTypes = (
        _(u'Blade (1 Handed)'),
        _(u'Blade (2 Handed)'),
        _(u'Blunt (1 Handed)'),
        _(u'Blunt (2 Handed)'),
        _(u'Staff'),
        _(u'Bow'),
        )

    raceNames = {
        0x13740 : _(u'Argonian'),
        0x13741 : _(u'Breton'),
        0x13742 : _(u'Dark Elf'),
        0x13743 : _(u'High Elf'),
        0x13744 : _(u'Imperial'),
        0x13745 : _(u'Khajiit'),
        0x13746 : _(u'Nord'),
        0x13747 : _(u'Orc'),
        0x13748 : _(u'Redguard'),
        0x13749 : _(u'Wood Elf'),
        }
    raceShortNames = {
        0x13740 : u'Arg',
        0x13741 : u'Bre',
        0x13742 : u'Dun',
        0x13743 : u'Alt',
        0x13744 : u'Imp',
        0x13745 : u'Kha',
        0x13746 : u'Nor',
        0x13747 : u'Orc',
        0x13748 : u'Red',
        0x13749 : u'Bos',
        }
    raceHairMale = {
        0x13740 : 0x64f32, #--Arg
        0x13741 : 0x90475, #--Bre
        0x13742 : 0x64214, #--Dun
        0x13743 : 0x7b792, #--Alt
        0x13744 : 0x90475, #--Imp
        0x13745 : 0x653d4, #--Kha
        0x13746 : 0x1da82, #--Nor
        0x13747 : 0x66a27, #--Orc
        0x13748 : 0x64215, #--Red
        0x13749 : 0x690bc, #--Bos
        }
    raceHairFemale = {
        0x13740 : 0x64f33, #--Arg
        0x13741 : 0x1da83, #--Bre
        0x13742 : 0x1da83, #--Dun
        0x13743 : 0x690c2, #--Alt
        0x13744 : 0x1da83, #--Imp
        0x13745 : 0x653d0, #--Kha
        0x13746 : 0x1da83, #--Nor
        0x13747 : 0x64218, #--Orc
        0x13748 : 0x64210, #--Red
        0x13749 : 0x69473, #--Bos
        }

    @classmethod
    def init(cls):
        cls._dynamic_import_constants(__name__)
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

GAME_TYPE = SkyrimGameInfo
