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
"""GameInfo override for TES IV: Oblivion."""

from .. import GameInfo
from ... import brec
from ...brec import MreGlob

class OblivionGameInfo(GameInfo):
    displayName = u'Oblivion'
    fsName = u'Oblivion'
    altName = u'Wrye Bash'
    defaultIniFile = u'Oblivion_default.ini'
    launch_exe = u'Oblivion.exe'
    game_detect_file = [u'Oblivion.exe']
    version_detect_file  = [u'Oblivion.exe']
    masterFiles = [u'Oblivion.esm', u'Nehrim.esm']
    iniFiles = [u'Oblivion.ini']
    pklfile = u'bash\\db\\Oblivion_ids.pkl'
    masterlist_dir = u'Oblivion'
    regInstallKeys = (u'Bethesda Softworks\\Oblivion', u'Installed Path')
    nexusUrl = u'https://www.nexusmods.com/oblivion/'
    nexusName = u'TES Nexus'
    nexusKey = 'bash.installers.openTesNexus.continue'

    patchURL = u'http://www.elderscrolls.com/downloads/updates_patches.htm'
    patchTip = u'http://www.elderscrolls.com/'

    allow_reset_bsa_timestamps = True
    supports_mod_inis = False

    using_txt_file = False
    has_standalone_pluggy = True

    class cs(GameInfo.cs):
        cs_abbrev = u'TESCS'
        long_name = u'Construction Set'
        exe = u'TESConstructionSet.exe'
        se_args = u'-editor'
        image_name = u'tescs%s.png'

    class se(GameInfo.se):
        se_abbrev = u'OBSE'
        long_name = u'Oblivion Script Extender'
        exe = u'obse_loader.exe'
        steam_exe = u'obse_1_2_416.dll'
        plugin_dir = u'OBSE'
        cosave_ext = u'.obse'
        url = u'http://obse.silverlock.org/'
        url_tip = u'http://obse.silverlock.org/'

    class ge(GameInfo.ge):
        ge_abbrev = u'OBGE'
        long_name = u'Oblivion Graphics Extender'
        exe = [(u'obse', u'plugins', u'obge.dll'),
               (u'obse', u'plugins', u'obgev2.dll'),
               (u'obse', u'plugins', u'oblivionreloaded.dll'),
               ]
        url = u'https://www.nexusmods.com/oblivion/mods/30054'
        url_tip = u'https://www.nexusmods.com/oblivion'

    class ess(GameInfo.ess):
        canEditMore = True

    # BAIN:
    dataDirs = GameInfo.dataDirs | {
        u'distantlod',
        u'facegen',
        u'fonts',
        u'menus',
        u'shaders',
        u'trees',
    }
    dataDirsPlus = {
        u'_tejon',
        u'ini',
        u'obse',
        u'pluggy',
        u'scripts',
        u'streamline',
    }
    SkipBAINRefresh = {
        u'tes4edit backups',
        u'tes4edit cache',
        u'bgsee',
        u'conscribe logs',
    }
    wryeBashDataFiles = GameInfo.wryeBashDataFiles | {
        u'ArchiveInvalidationInvalidated!.bsa'}
    ignoreDataFiles = {
        u'OBSE\\Plugins\\Construction Set Extender.dll',
        u'OBSE\\Plugins\\Construction Set Extender.ini'
    }
    ignoreDataFilePrefixes = {
        u'Meshes\\Characters\\_Male\\specialanims\\0FemaleVariableWalk_'
    }
    ignoreDataDirs = {
        u'OBSE\\Plugins\\ComponentDLLs\\CSE',
        u'LSData'
    }

    class esp(GameInfo.esp):
        canBash = True
        canCBash = True
        canEditHeader = True
        validHeaderVersions = (0.8,1.0)
        stringsFiles = []

    allTags = {u'Body-F', u'Body-M', u'Body-Size-M', u'Body-Size-F',
               u'C.Climate', u'C.Light', u'C.Music', u'C.Name',
               u'C.Owner', u'C.RecordFlags', u'C.Regions', u'C.Water',
               u'Deactivate', u'Delev', u'Eyes', u'Factions', u'Relations',
               u'Filter', u'Graphics', u'Hair', u'IIM', u'Invent', u'Names',
               u'NoMerge', u'NpcFaces', u'R.Relations', u'Relev', u'Scripts',
               u'ScriptContents', u'Sound', u'SpellStats', u'Stats',
               u'Voice-F', u'Voice-M', u'R.Teeth', u'R.Mouth', u'R.Ears',
               u'R.Head', u'R.Attributes-F', u'R.Attributes-M', u'R.Skills',
               u'R.Description', u'R.AddSpells', u'R.ChangeSpells', u'Roads',
               u'Actors.Anims', u'Actors.AIData', u'Actors.DeathItem',
               u'Actors.AIPackages', u'Actors.AIPackagesForceAdd',
               u'Actors.Stats', u'Actors.ACBS', u'NPC.Class',
               u'Actors.CombatStyle', u'Creatures.Blood', u'Actors.Spells',
               u'Actors.SpellsForceAdd', u'NPC.Race', u'Actors.Skeleton',
               u'NpcFacesForceFullImport', u'MustBeActiveIfImported',
               u'Npc.HairOnly', u'Npc.EyesOnly'}  # , 'ForceMerge'

    patchers = (
        'AliasesPatcher', 'AssortedTweaker', 'PatchMerger', 'AlchemicalCatalogs',
        'KFFZPatcher', 'ActorImporter', 'DeathItemPatcher', 'NPCAIPackagePatcher',
        'CoblExhaustion', 'UpdateReferences', 'CellImporter', 'ClothesTweaker',
        'GmstTweaker', 'GraphicsPatcher', 'ImportFactions', 'ImportInventory',
        'SpellsPatcher', 'TweakActors', 'ImportRelations', 'ImportScripts',
        'ImportActorsSpells', 'ListsMerger', 'MFactMarker', 'NamesPatcher',
        'NamesTweaker', 'NpcFacePatcher', 'RacePatcher', 'RoadImporter',
        'SoundPatcher', 'StatsPatcher', 'SEWorldEnforcer', 'ContentsChecker',
        )

    CBash_patchers = (
        'CBash_AliasesPatcher', 'CBash_AssortedTweaker', 'CBash_PatchMerger',
        'CBash_AlchemicalCatalogs', 'CBash_KFFZPatcher', 'CBash_ActorImporter',
        'CBash_DeathItemPatcher', 'CBash_NPCAIPackagePatcher',
        'CBash_CoblExhaustion', 'CBash_UpdateReferences', 'CBash_CellImporter',
        'CBash_ClothesTweaker', 'CBash_GmstTweaker', 'CBash_GraphicsPatcher',
        'CBash_ImportFactions', 'CBash_ImportInventory', 'CBash_SpellsPatcher',
        'CBash_TweakActors', 'CBash_ImportRelations', 'CBash_ImportScripts',
        'CBash_ImportActorsSpells', 'CBash_ListsMerger', 'CBash_MFactMarker',
        'CBash_NamesPatcher', 'CBash_NamesTweaker', 'CBash_NpcFacePatcher',
        'CBash_RacePatcher', 'CBash_RoadImporter', 'CBash_SoundPatcher',
        'CBash_StatsPatcher', 'CBash_SEWorldEnforcer', 'CBash_ContentsChecker',
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
        0x23fe9 : _(u'Argonian'),
        0x224fc : _(u'Breton'),
        0x191c1 : _(u'Dark Elf'),
        0x19204 : _(u'High Elf'),
        0x00907 : _(u'Imperial'),
        0x22c37 : _(u'Khajiit'),
        0x224fd : _(u'Nord'),
        0x191c0 : _(u'Orc'),
        0x00d43 : _(u'Redguard'),
        0x00019 : _(u'Vampire'),
        0x223c8 : _(u'Wood Elf'),
        }
    raceShortNames = {
        0x23fe9 : u'Arg',
        0x224fc : u'Bre',
        0x191c1 : u'Dun',
        0x19204 : u'Alt',
        0x00907 : u'Imp',
        0x22c37 : u'Kha',
        0x224fd : u'Nor',
        0x191c0 : u'Orc',
        0x00d43 : u'Red',
        0x223c8 : u'Bos',
        }
    raceHairMale = {
        0x23fe9 : 0x64f32, #--Arg
        0x224fc : 0x90475, #--Bre
        0x191c1 : 0x64214, #--Dun
        0x19204 : 0x7b792, #--Alt
        0x00907 : 0x90475, #--Imp
        0x22c37 : 0x653d4, #--Kha
        0x224fd : 0x1da82, #--Nor
        0x191c0 : 0x66a27, #--Orc
        0x00d43 : 0x64215, #--Red
        0x223c8 : 0x690bc, #--Bos
        }
    raceHairFemale = {
        0x23fe9 : 0x64f33, #--Arg
        0x224fc : 0x1da83, #--Bre
        0x191c1 : 0x1da83, #--Dun
        0x19204 : 0x690c2, #--Alt
        0x00907 : 0x1da83, #--Imp
        0x22c37 : 0x653d0, #--Kha
        0x224fd : 0x1da83, #--Nor
        0x191c0 : 0x64218, #--Orc
        0x00d43 : 0x64210, #--Red
        0x223c8 : 0x69473, #--Bos
        }

    @classmethod
    def init(cls):
        cls._dynamic_import_modules(__name__)
        from .records import MreActi, MreAlch, MreAmmo, MreAnio, MreAppa, \
            MreArmo, MreBook, MreBsgn, MreClas, MreClot, MreCont, MreCrea, \
            MreDoor, MreEfsh, MreEnch, MreEyes, MreFact, MreFlor, MreFurn, \
            MreGras, MreHair, MreIngr, MreKeym, MreLigh, MreLscr, MreLvlc, \
            MreLvli, MreLvsp, MreMgef, MreMisc, MreNpc, MrePack, MreQust, \
            MreRace, MreScpt, MreSgst, MreSlgm, MreSoun, MreSpel, MreStat, \
            MreTree, MreWatr, MreWeap, MreWthr, MreClmt, MreCsty, MreIdle, \
            MreLtex, MreRegn, MreSbsp, MreSkil, MreAchr, MreAcre, MreCell, \
            MreGmst, MreRefr, MreRoad, MreHeader, MreWrld, MreDial, MreInfo
        cls.mergeClasses = (
            MreActi, MreAlch, MreAmmo, MreAnio, MreAppa, MreArmo, MreBook,
            MreBsgn, MreClas, MreClot, MreCont, MreCrea, MreDoor, MreEfsh,
            MreEnch, MreEyes, MreFact, MreFlor, MreFurn, MreGlob, MreGras,
            MreHair, MreIngr, MreKeym, MreLigh, MreLscr, MreLvlc, MreLvli,
            MreLvsp, MreMgef, MreMisc, MreNpc, MrePack, MreQust, MreRace,
            MreScpt, MreSgst, MreSlgm, MreSoun, MreSpel, MreStat, MreTree,
            MreWatr, MreWeap, MreWthr, MreClmt, MreCsty, MreIdle, MreLtex,
            MreRegn, MreSbsp, MreSkil,
        )
        cls.readClasses = (MreMgef, MreScpt,)
        cls.writeClasses = (MreMgef,)
        # Setting RecordHeader class variables - Oblivion is special
        __rec_type = brec.RecordHeader
        __rec_type.rec_header_size = 20
        __rec_type.rec_pack_format = ['=4s', 'I', 'I', 'I', 'I']
        __rec_type.rec_pack_format_str = ''.join(__rec_type.rec_pack_format)
        __rec_type.pack_formats = {0: '=4sI4s2I'}
        __rec_type.pack_formats.update(
            {x: '=4s4I' for x in {1, 6, 7, 8, 9, 10}})
        __rec_type.pack_formats.update({x: '=4sIi2I' for x in {2, 3}})
        __rec_type.pack_formats.update({x: '=4sIhh2I' for x in {4, 5}})
        # Similar to other games
        __rec_type.topTypes = [
            'GMST', 'GLOB', 'CLAS', 'FACT', 'HAIR', 'EYES', 'RACE', 'SOUN',
            'SKIL', 'MGEF', 'SCPT', 'LTEX', 'ENCH', 'SPEL', 'BSGN', 'ACTI',
            'APPA', 'ARMO', 'BOOK', 'CLOT', 'CONT', 'DOOR', 'INGR', 'LIGH',
            'MISC', 'STAT', 'GRAS', 'TREE', 'FLOR', 'FURN', 'WEAP', 'AMMO',
            'NPC_', 'CREA', 'LVLC', 'SLGM', 'KEYM', 'ALCH', 'SBSP', 'SGST',
            'LVLI', 'WTHR', 'CLMT', 'REGN', 'CELL', 'WRLD', 'DIAL', 'QUST',
            'IDLE', 'PACK', 'CSTY', 'LSCR', 'LVSP', 'ANIO', 'WATR', 'EFSH']
        __rec_type.recordTypes = set(
            __rec_type.topTypes + ['GRUP', 'TES4', 'ROAD', 'REFR', 'ACHR',
                                   'ACRE', 'PGRD', 'LAND', 'INFO'])
        brec.MreRecord.type_class = dict((x.classType,x) for x in (
            MreAchr, MreAcre, MreActi, MreAlch, MreAmmo, MreAnio, MreAppa,
            MreArmo, MreBook, MreBsgn, MreCell, MreClas, MreClot, MreCont,
            MreCrea, MreDoor, MreEfsh, MreEnch, MreEyes, MreFact, MreFlor,
            MreFurn, MreGlob, MreGmst, MreGras, MreHair, MreIngr, MreKeym,
            MreLigh, MreLscr, MreLvlc, MreLvli, MreLvsp, MreMgef, MreMisc,
            MreNpc, MrePack, MreQust, MreRace, MreRefr, MreRoad, MreScpt,
            MreSgst, MreSkil, MreSlgm, MreSoun, MreSpel, MreStat, MreTree,
            MreHeader, MreWatr, MreWeap, MreWrld, MreWthr, MreClmt, MreCsty,
            MreIdle, MreLtex, MreRegn, MreSbsp, MreDial, MreInfo,))
        brec.MreRecord.simpleTypes = (
            set(brec.MreRecord.type_class) - {'TES4', 'ACHR', 'ACRE', 'REFR',
                                              'CELL', 'PGRD', 'ROAD', 'LAND',
                                              'WRLD', 'INFO', 'DIAL'})

GAME_TYPE = OblivionGameInfo
