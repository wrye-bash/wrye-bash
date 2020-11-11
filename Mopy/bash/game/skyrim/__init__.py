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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""GameInfo override for TES V: Skyrim."""

from os.path import join as _j

from .. import GameInfo
from ... import brec
from ...brec import MreFlst, MreGlob

class SkyrimGameInfo(GameInfo):
    displayName = u'Skyrim'
    fsName = u'Skyrim'
    altName = u'Wrye Smash'
    bash_root_prefix = u'Skyrim'
    launch_exe = u'TESV.exe'
    # Set to this because TESV.exe also exists for Enderal
    game_detect_file = u'SkyrimLauncher.exe'
    version_detect_file = u'TESV.exe'
    master_file = u'Skyrim.esm'
    taglist_dir = u'Skyrim'
    regInstallKeys = (u'Bethesda Softworks\\Skyrim', u'Installed Path')
    nexusUrl = u'https://www.nexusmods.com/skyrim/'
    nexusName = u'Skyrim Nexus'
    nexusKey = 'bash.installers.openSkyrimNexus.continue'

    plugin_name_specific_dirs = GameInfo.plugin_name_specific_dirs + [
        _j(u'meshes', u'actors', u'character', u'facegendata', u'facegeom'),
        _j(u'textures', u'actors', u'character', u'facegendata', u'facetint')]

    class Ck(GameInfo.Ck):
        ck_abbrev = u'CK'
        long_name = u'Creation Kit'
        exe = u'CreationKit.exe'
        image_name = u'creationkit%s.png'

    class Se(GameInfo.Se):
        se_abbrev = u'SKSE'
        long_name = u'Skyrim Script Extender'
        exe = u'skse_loader.exe'
        ver_files = [u'skse_loader.exe', u'skse_steam_loader.dll']
        plugin_dir = u'SKSE'
        cosave_tag = u'SKSE'
        cosave_ext = u'.skse'
        url = u'http://skse.silverlock.org/'
        url_tip = u'http://skse.silverlock.org/'

    class Sd(GameInfo.Sd):
        sd_abbrev = u'SD'
        long_name = u'Script Dragon'
        install_dir = u'asi'

    class Sp(GameInfo.Sp):
        sp_abbrev = u'SP'
        long_name = u'SkyProc'
        install_dir = u'SkyProc Patchers'

    class Ini(GameInfo.Ini):
        default_ini_file = u'Skyrim_default.ini'
        dropdown_inis = [u'Skyrim.ini', u'SkyrimPrefs.ini']
        resource_archives_keys = (u'sResourceArchiveList',
                                  u'sResourceArchiveList2')

    class Bsa(GameInfo.Bsa):
        # Skyrim only accepts the base name
        attachment_regex = u''
        has_bsl = True
        valid_versions = {0x68}

    class Psc(GameInfo.Psc):
        source_extensions = {u'.psc'}
        # In SSE Bethesda made the mistake of packaging the CK's script source
        # as 'source/scripts' instead of 'scripts/source'. The CK even still
        # expects the sources to be in 'scripts/source', so you'd have to edit
        # its INI if you wanted to use 'source/scripts'. However, some modders
        # have nonetheless adopted this convention, so to support this we
        # redirect them to the correct path while scanning the package in BAIN.
        # Sits here because the situation then got worse - some modders have
        # started packaging 'source' dirs even in Skyrim LE.
        source_redirects = {
            _j(u'source', u'scripts'): _j(u'scripts', u'source'),
            u'source': _j(u'scripts', u'source'),
        }

    class Xe(GameInfo.Xe):
        full_name = u'TES5Edit'
        xe_key_prefix = u'tes5View'

    class Bain(GameInfo.Bain):
        data_dirs = GameInfo.Bain.data_dirs | {
            u'asi', # script dragon
            u'calientetools', # bodyslide
            u'dialogueviews',
            u'dyndolod',
            u'grass',
            u'interface',
            u'lodsettings',
            u'scripts',
            u'seq',
            u'shadersfx',
            u'skse',
            u'skyproc patchers',
            u'source', # see Psc.source_redirects above
            u'strings',
            u'tools', # FNIS
        }
        keep_data_dirs = {u'LSData'}
        no_skip = (
            # These are all in the Interface folder. Apart from the skyui_
            # files, they are all present in vanilla.
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
        no_skip_dirs = {
            # This rule is to allow mods with string translation enabled.
            _j(u'interface', u'translations'): [u'.txt']
        }
        skip_bain_refresh = {u'tes5edit backups', u'tes5edit cache'}

    class Esp(GameInfo.Esp):
        canBash = True
        canEditHeader = True
        validHeaderVersions = (0.94, 1.70,)
        generate_temp_child_onam = True
        max_lvl_list_size = 255
        biped_flag_names = (
            u'head', u'hair', u'body', u'hands', u'forearms', u'amulet',
            u'ring', u'feet', u'calves', u'shield', u'bodyaddon1_tail',
            u'long_hair', u'circlet', u'bodyaddon2', u'dragon_head',
            u'dragon_lwing', u'dragon_rwing', u'dragon_body', u'bodyaddon7',
            u'bodyaddon8', u'decapate_head', u'decapate', u'bodyaddon9',
            u'bodyaddon10', u'bodyaddon11', u'bodyaddon12', u'bodyaddon13',
            u'bodyaddon14', u'bodyaddon15', u'bodyaddon16', u'bodyaddon17',
            u'fx01')

    allTags = {
        u'Actors.ACBS', u'Actors.AIData', u'Actors.AIPackages',
        u'Actors.AIPackagesForceAdd', u'Actors.CombatStyle',
        u'Actors.DeathItem', u'Actors.RecordFlags', u'Actors.Spells',
        u'Actors.SpellsForceAdd', u'Actors.Stats', u'C.Acoustic', u'C.Climate',
        u'C.Encounter', u'C.ForceHideLand', u'C.ImageSpace', u'C.Light',
        u'C.Location', u'C.LockList', u'C.MiscFlags', u'C.Music', u'C.Name',
        u'C.Owner', u'C.RecordFlags', u'C.Regions', u'C.SkyLighting',
        u'C.Water', u'Deactivate', u'Delev', u'Destructible', u'EffectStats',
        u'EnchantmentStats', u'Factions', u'Filter', u'Graphics',
        u'Invent.Add', u'Invent.Change', u'Invent.Remove', u'Keywords',
        u'MustBeActiveIfImported', u'Names', u'NoMerge',
        u'NPC.AIPackageOverrides', u'NPC.Class', u'NPC.Race', u'ObjectBounds',
        u'Outfits.Add', u'Outfits.Remove', u'Relations.Add',
        u'Relations.Change', u'Relations.Remove', u'Relev', u'Sound',
        u'SpellStats', u'Stats', u'Text',
    }

    patchers = {
        u'AliasModNames', u'ContentsChecker', u'ImportActors',
        u'ImportActorsAIPackages', u'ImportActorsDeathItems',
        u'ImportActorsSpells', u'ImportCells', u'ImportDestructible',
        u'ImportEffectsStats', u'ImportEnchantmentStats', u'ImportFactions',
        u'ImportGraphics', u'ImportInventory', u'ImportKeywords',
        u'ImportNames', u'ImportObjectBounds', u'ImportOutfits',
        u'ImportRelations', u'ImportSounds', u'ImportSpellStats',
        u'ImportStats', u'ImportText', u'LeveledLists', u'MergePatches',
        u'TweakActors', u'TweakAssorted', u'TweakSettings',
    }

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
        cls._dynamic_import_modules(__name__)
        from .records import MreCell, MreWrld, MreFact, MreAchr, MreDial, \
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
            MreAspc, MreRela, MreEfsh, MreSnct, MreOtft, MrePerk
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
        #       MreAchr, MreDial, MreInfo,
        # ---------------------------------------------------------------------
        cls.mergeClasses = (# MreAchr, MreDial, MreInfo,
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
        )

        # MreScpt is Oblivion/FO3/FNV Only
        # MreMgef, has not been verified to be used here for Skyrim

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
        #-> this needs updating for Skyrim
        header_type.valid_header_sigs = set(
            header_type.top_grup_sigs + [b'GRUP', b'TES4', b'REFR', b'ACHR',
                                         b'ACRE', b'LAND', b'INFO', b'NAVM',
                                         b'PHZD', b'PGRE'])
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
            MreWthr, MreCell, MreWrld, MreQust, MreTes4, MrePack,
            # MreNavm, MreNavi
        )}
        brec.MreRecord.simpleTypes = (
                set(brec.MreRecord.type_class) - {b'TES4', b'ACHR', b'CELL',
                                                  b'DIAL', b'INFO', b'WRLD'})
        cls._validate_records()

GAME_TYPE = SkyrimGameInfo
