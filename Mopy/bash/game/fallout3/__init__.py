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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""GameInfo override for Fallout 3."""

from collections import defaultdict
from os.path import join as _j

from ..patch_game import GameInfo, PatchGame
from ... import brec
from ...brec import MreFlst, MreGlob

class Fallout3GameInfo(PatchGame):
    displayName = u'Fallout 3'
    fsName = u'Fallout3'
    altName = u'Wrye Flash'
    game_icon = u'fallout3_%u.png'
    bash_root_prefix = u'Fallout3'
    bak_game_name = u'Fallout3'
    template_dir = u'Fallout3'
    my_games_name = u'Fallout3'
    appdata_name = u'Fallout3'
    launch_exe = u'Fallout3.exe'
    game_detect_includes = [u'Fallout3.exe']
    version_detect_file = u'Fallout3.exe'
    master_file = u'Fallout3.esm'
    taglist_dir = u'Fallout3'
    loot_dir = u'Fallout3'
    boss_game_name = u'Fallout3'
    regInstallKeys = (u'Bethesda Softworks\\Fallout3',u'Installed Path')
    nexusUrl = u'https://www.nexusmods.com/fallout3/'
    nexusName = u'Fallout 3 Nexus'
    nexusKey = u'bash.installers.openFallout3Nexus.continue'

    using_txt_file = False
    plugin_name_specific_dirs = GameInfo.plugin_name_specific_dirs + [
        _j(u'textures', u'characters', u'BodyMods'),
        _j(u'textures', u'characters', u'FaceMods')]

    class Ck(GameInfo.Ck):
        ck_abbrev = u'GECK'
        long_name = u'Garden of Eden Creation Kit'
        exe = u'GECK.exe'
        se_args = u'-editor'
        image_name = u'geck%s.png'

    class Se(GameInfo.Se):
        se_abbrev = u'FOSE'
        long_name = u'Fallout 3 Script Extender'
        exe = u'fose_loader.exe'
        # There is no fose_steam_loader.dll, so we have to list all included
        # DLLs, since people could delete any DLL not matching the game version
        # they're using
        ver_files = [u'fose_loader.exe', u'fose_1_7ng.dll', u'fose_1_7.dll',
                     u'fose_1_6.dll', u'fose_1_5.dll', u'fose_1_4b.dll',
                     u'fose_1_4.dll', u'fose_1_1.dll', u'fose_1_0.dll']
        plugin_dir = u'FOSE'
        cosave_tag = u'FOSE'
        cosave_ext = u'.fose'
        url = u'http://fose.silverlock.org/'
        url_tip = u'http://fose.silverlock.org/'
        limit_fixer_plugins = [u'mod_limit_fix.dll']

    class Ini(GameInfo.Ini):
        allow_new_lines = False
        bsa_redirection_key = (u'Archive', u'sArchiveList')
        default_ini_file = u'Fallout_default.ini'
        dropdown_inis = [u'Fallout.ini', u'FalloutPrefs.ini']
        supports_mod_inis = False

    class Ess(GameInfo.Ess):
        ext = u'.fos'
        can_safely_remove_masters = True

    class Bsa(GameInfo.Bsa):
        allow_reset_timestamps = True
        redate_dict = defaultdict(lambda: 1136066400, { # '2006-01-01'
            'Fallout - MenuVoices.bsa': 1104530400,  # '2005-01-01',
            'Fallout - Meshes.bsa': 1104616800,      # '2005-01-02',
            'Fallout - Misc.bsa': 1104703200,        # '2005-01-03',
            'Fallout - Sound.bsa': 1104789600,       # '2005-01-04',
            'Fallout - Textures.bsa': 1104876000,    # '2005-01-05',
            'Fallout - Voices.bsa': 1104962400,      # '2005-01-06',
        })
        # ArchiveInvalidation Invalidated, which we shipped unmodified for a
        # long time, uses an Oblivion BSA with version 0x67, so we have to
        # accept those here as well
        valid_versions = {0x67, 0x68}

    class Xe(GameInfo.Xe):
        full_name = u'FO3Edit'
        xe_key_prefix = u'fo3View'

    class Bain(GameInfo.Bain):
        data_dirs = GameInfo.Bain.data_dirs | {
            u'config', # mod config files (INIs)
            u'distantlod',
            u'docs',
            u'facegen',
            u'fonts',
            u'fose',
            u'menus',
            u'uio', # User Interface Organizer
            u'scripts',
            u'shaders',
            u'trees',
        }
        keep_data_dirs = {u'LSData'}
        keep_data_files = {u'Fallout - AI!.bsa'}
        skip_bain_refresh = {u'fo3edit backups', u'fo3edit cache'}
        wrye_bash_data_files = {u'ArchiveInvalidationInvalidated!.bsa'}

    class Esp(GameInfo.Esp):
        canBash = True
        canEditHeader = True
        validHeaderVersions = (0.85, 0.94)
        stringsFiles = []
        generate_temp_child_onam = True
        biped_flag_names = (u'head', u'hair', u'upperBody', u'leftHand',
                            u'rightHand', u'weapon', u'pipboy', u'backpack',
                            u'necklace', u'headband', u'hat', u'eyeGlasses',
                            u'noseRing', u'earrings', u'mask', u'choker',
                            u'mouthObject', u'bodyAddOn1', u'bodyAddOn2',
                            u'bodyAddOn3')
        reference_types = {b'ACHR', b'ACRE', b'PBEA', b'PGRE', b'PMIS',
                           b'REFR'}

    allTags = PatchGame.allTags | {u'NoMerge'}

    patchers = {
        u'AliasModNames', u'ContentsChecker', u'FormIDLists', u'ImportActors',
        u'ImportActorsAIPackages', u'ImportActorsAnimations', u'NpcChecker',
        u'ImportActorsDeathItems', u'ImportActorsFaces', u'RaceChecker',
        u'ImportActorsFactions', u'ImportActorsSpells', u'ImportCells',
        u'ImportDestructible', u'ImportEffectsStats', u'ImportRaces',
        u'ImportEnchantmentStats', u'ImportGraphics', u'ImportInventory',
        u'ImportNames', u'ImportObjectBounds', u'ImportRelations',
        u'ImportScripts', u'ImportSounds', u'ImportSpellStats', u'ImportStats',
        u'ImportText', u'LeveledLists', u'MergePatches', u'TweakActors',
        u'TweakAssorted', u'TweakSettings', u'ImportRacesRelations',
        u'TweakRaces', u'TimescaleChecker', u'TweakNames',
    }

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

    bethDataFiles = {
        #--Vanilla
        u'fallout3.esm',
        u'fallout - menuvoices.bsa',
        u'fallout - meshes.bsa',
        u'fallout - misc.bsa',
        u'fallout - sound.bsa',
        u'fallout - textures.bsa',
        u'fallout - voices.bsa',
        #-- DLC
        u'anchorage.esm',
        u'anchorage - main.bsa',
        u'anchorage - sounds.bsa',
        u'thepitt.esm',
        u'thepitt - main.bsa',
        u'thepitt - sounds.bsa',
        u'brokensteel.esm',
        u'brokensteel - main.bsa',
        u'brokensteel - sounds.bsa',
        u'pointlookout.esm',
        u'pointlookout - main.bsa',
        u'pointlookout - sounds.bsa',
        u'zeta.esm',
        u'zeta - main.bsa',
        u'zeta - sounds.bsa',
    }

    @classmethod
    def init(cls):
        cls._dynamic_import_modules(__name__)
        from .records import MreActi, MreAddn, MreAlch, MreAmmo, MreAnio, \
            MreArma, MreArmo, MreAspc, MreAvif, MreBook, MreBptd, MreCams, \
            MreClas, MreClmt, MreCobj, MreCont, MreCpth, MreCrea, MreCsty, \
            MreDebr, MreDobj, MreDoor, MreEczn, MreEfsh, MreEnch, MreExpl, \
            MreEyes, MreFact, MreFurn, MreGras, MreHair, MreHdpt, MreTes4, \
            MreIdle, MreIdlm, MreImad, MreImgs, MreIngr, MreIpct, MreIpds, \
            MreKeym, MreLgtm, MreLigh, MreLscr, MreLtex, MreLvlc, MreLvli, \
            MreLvln, MreMesg, MreMgef, MreMicn, MreMisc, MreMstt, MreMusc, \
            MreNote, MreNpc, MrePack, MrePerk, MreProj, MrePwat, MreQust, \
            MreRace, MreRads, MreRegn, MreRgdl, MreScol, MreScpt, MreSoun, \
            MreSpel, MreStat, MreTact, MreTerm, MreTree, MreTxst, MreVtyp, \
            MreWatr, MreWeap, MreWthr, MreAchr, MreAcre, MreCell, MreDial, \
            MreGmst, MreInfo, MreNavi, MreNavm, MrePgre, MrePmis, MreRefr, \
            MreWrld
        cls.mergeable_sigs = {clazz.rec_sig: clazz for clazz in (
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
            MreWeap, MreWthr, MreGmst,
        )}
        # Setting RecordHeader class variables --------------------------------
        header_type = brec.RecordHeader
        header_type.top_grup_sigs = [
            b'GMST', b'TXST', b'MICN', b'GLOB', b'CLAS', b'FACT', b'HDPT',
            b'HAIR', b'EYES', b'RACE', b'SOUN', b'ASPC', b'MGEF', b'SCPT',
            b'LTEX', b'ENCH', b'SPEL', b'ACTI', b'TACT', b'TERM', b'ARMO',
            b'BOOK', b'CONT', b'DOOR', b'INGR', b'LIGH', b'MISC', b'STAT',
            b'SCOL', b'MSTT', b'PWAT', b'GRAS', b'TREE', b'FURN', b'WEAP',
            b'AMMO', b'NPC_', b'CREA', b'LVLC', b'LVLN', b'KEYM', b'ALCH',
            b'IDLM', b'NOTE', b'PROJ', b'LVLI', b'WTHR', b'CLMT', b'COBJ',
            b'REGN', b'NAVI', b'CELL', b'WRLD', b'DIAL', b'QUST', b'IDLE',
            b'PACK', b'CSTY', b'LSCR', b'ANIO', b'WATR', b'EFSH', b'EXPL',
            b'DEBR', b'IMGS', b'IMAD', b'FLST', b'PERK', b'BPTD', b'ADDN',
            b'AVIF', b'RADS', b'CAMS', b'CPTH', b'VTYP', b'IPCT', b'IPDS',
            b'ARMA', b'ECZN', b'MESG', b'RGDL', b'DOBJ', b'LGTM', b'MUSC',
        ]
        header_type.valid_header_sigs = set(
            header_type.top_grup_sigs + [b'GRUP', b'TES4', b'ACHR', b'ACRE',
                                         b'INFO', b'LAND', b'NAVM', b'PGRE',
                                         b'PMIS', b'REFR'])
        header_type.plugin_form_version = 15
        brec.MreRecord.type_class = {x.rec_sig: x for x in ( # Not Mergeable
             (MreAchr, MreAcre, MreCell, MreDial, MreInfo, MreNavi, MreNavm,
              MrePgre, MrePmis, MreRefr, MreWrld, MreTes4))}
        brec.MreRecord.type_class.update(cls.mergeable_sigs)
        brec.MreRecord.simpleTypes = (set(brec.MreRecord.type_class) - {
            b'TES4', b'ACHR', b'ACRE', b'CELL', b'DIAL', b'INFO', b'LAND',
            b'NAVI', b'NAVM', b'PGRE', b'PMIS', b'REFR', b'WRLD'})
        cls._validate_records()

GAME_TYPE = Fallout3GameInfo
