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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import importlib

from .. import WS_COMMON_FILES, ObjectIndexRange
from ..skyrim import ASkyrimGameInfo
from ..store_mixins import EGSMixin, GOGMixin, SteamMixin, WindowsStoreMixin
from ..._games_lo import AsteriskGame
from ...bolt import classproperty, FName

_GOG_IDS = [
    1801825368, # Game
    1162721350, # Anniversary Upgrade DLC/patch
    1711230643, # Package
]

class ASkyrimSEGameInfo(ASkyrimGameInfo):
    """GameInfo override for TES V: Skyrim Special Edition."""
    display_name = 'Skyrim Special Edition'
    fsName = u'Skyrim Special Edition'
    game_icon = u'skyrimse_%u.png'
    bash_root_prefix = u'Skyrim Special Edition' # backwards compat :(
    bak_game_name = u'Skyrim Special Edition'
    my_games_name = u'Skyrim Special Edition'
    appdata_name = u'Skyrim Special Edition'
    launch_exe = u'SkyrimSE.exe'
    # Set to this because SkyrimSE.exe also exists for Enderal SE
    game_detect_includes = {'SkyrimSELauncher.exe'}
    # Files carefully chosen such that no platform has any of them in common
    # with another platform. SkyrimVR.exe is here because some older guides
    # recommend creating a copy of SkyrimVR.exe called SkyrimSE.exe to "trick"
    # WB into launching. That's from back when WB had no VR support, but those
    # guides haven't been updated since...
    game_detect_excludes = (set(GOGMixin.get_unique_filenames(_GOG_IDS)) |
                            WS_COMMON_FILES |
                            {'EOSSDK-Win64-Shipping.dll'} | # Epic Store
                            {'SkyrimVR.exe'})
    version_detect_file = u'SkyrimSE.exe'
    taglist_dir = u'SkyrimSE'
    loot_dir = u'Skyrim Special Edition'
    loot_game_name = 'Skyrim Special Edition'
    boss_game_name = u'' # BOSS does not support SSE
    nexusUrl = u'https://www.nexusmods.com/skyrimspecialedition/'
    nexusName = u'Skyrim SE Nexus'
    nexusKey = u'bash.installers.openSkyrimSeNexus.continue'

    espm_extensions = {*ASkyrimGameInfo.espm_extensions, '.esl'}
    has_achlist = True

    class Se(ASkyrimGameInfo.Se):
        se_abbrev = u'SKSE64'
        long_name = u'Skyrim SE Script Extender'
        exe = u'skse64_loader.exe'
        ver_files = [u'skse64_loader.exe', u'skse64_steam_loader.dll']

    # ScriptDragon doesn't exist for SSE
    class Sd(ASkyrimGameInfo.Sd):
        sd_abbrev = u''
        long_name = u''
        install_dir = u''

    class Bsa(ASkyrimGameInfo.Bsa):
        # Skyrim SE accepts the base name and ' - Textures'
        attachment_regex = r'(?: \- Textures)?'
        valid_versions = {0x69}
        # patch BSA (which only exists in SSE) will always load after the
        # interface BSA and hence should win all conflicts when fetching
        # strings
        _str_heuristics = tuple(enumerate(('main', 'patch', 'interface')))

    class Xe(ASkyrimGameInfo.Xe):
        full_name = u'SSEEdit'
        xe_key_prefix = u'sseView'

    class Bain(ASkyrimGameInfo.Bain):
        skip_bain_refresh = {u'sseedit backups', u'sseedit cache'}

    class Esp(ASkyrimGameInfo.Esp):
        extension_forces_flags = True
        # Because the FE slot is reserved for ESLs - yes, including in master
        # lists. Thanks, Bethesda
        master_limit = 253
        object_index_range = ObjectIndexRange.EXPANDED_CONDITIONAL
        object_index_range_expansion_ver = 1.71
        validHeaderVersions = (0.94, 1.70, 1.71)
        warn_older_form_versions = True

    bethDataFiles = {
        'skyrim.esm',
        'update.esm',
        'dawnguard.esm',
        'dragonborn.esm',
        'hearthfires.esm',
        'skyrim - animations.bsa',
        'skyrim - interface.bsa',
        'skyrim - meshes0.bsa',
        'skyrim - meshes1.bsa',
        'skyrim - misc.bsa',
        'skyrim - patch.bsa',
        'skyrim - shaders.bsa',
        'skyrim - sounds.bsa',
        'skyrim - textures0.bsa',
        'skyrim - textures1.bsa',
        'skyrim - textures2.bsa',
        'skyrim - textures3.bsa',
        'skyrim - textures4.bsa',
        'skyrim - textures5.bsa',
        'skyrim - textures6.bsa',
        'skyrim - textures7.bsa',
        'skyrim - textures8.bsa',
        'skyrim - voices_de0.bsa',
        'skyrim - voices_en0.bsa',
        'skyrim - voices_es0.bsa',
        'skyrim - voices_fr0.bsa',
        'skyrim - voices_it0.bsa',
        'skyrim - voices_ja0.bsa',
        'skyrim - voices_pl0.bsa',
        'skyrim - voices_ru0.bsa',
        '_resourcepack.bsa',
        '_resourcepack.esl',
        'marketplacetextures.bsa',
        'ccafdsse001-dwesanctuary.bsa',
        'ccafdsse001-dwesanctuary.esm',
        'ccasvsse001-almsivi.bsa',
        'ccasvsse001-almsivi.esm',
        'ccbgssse001-fish.bsa',
        'ccbgssse001-fish.esm',
        'ccbgssse002-exoticarrows.bsa',
        'ccbgssse002-exoticarrows.esl',
        'ccbgssse003-zombies.bsa',
        'ccbgssse003-zombies.esl',
        'ccbgssse004-ruinsedge.bsa',
        'ccbgssse004-ruinsedge.esl',
        'ccbgssse005-goldbrand.bsa',
        'ccbgssse005-goldbrand.esl',
        'ccbgssse006-stendarshammer.bsa',
        'ccbgssse006-stendarshammer.esl',
        'ccbgssse007-chrysamere.bsa',
        'ccbgssse007-chrysamere.esl',
        'ccbgssse008-wraithguard.bsa',
        'ccbgssse008-wraithguard.esl',
        'ccbgssse010-petdwarvenarmoredmudcrab.bsa',
        'ccbgssse010-petdwarvenarmoredmudcrab.esl',
        'ccbgssse011-hrsarmrelvn.bsa',
        'ccbgssse011-hrsarmrelvn.esl',
        'ccbgssse012-hrsarmrstl.bsa',
        'ccbgssse012-hrsarmrstl.esl',
        'ccbgssse013-dawnfang.bsa',
        'ccbgssse013-dawnfang.esl',
        'ccbgssse014-spellpack01.bsa',
        'ccbgssse014-spellpack01.esl',
        'ccbgssse016-umbra.bsa',
        'ccbgssse016-umbra.esm',
        'ccbgssse018-shadowrend.bsa',
        'ccbgssse018-shadowrend.esl',
        'ccbgssse019-staffofsheogorath.bsa',
        'ccbgssse019-staffofsheogorath.esl',
        'ccbgssse020-graycowl.bsa',
        'ccbgssse020-graycowl.esl',
        'ccbgssse021-lordsmail.bsa',
        'ccbgssse021-lordsmail.esl',
        'ccbgssse025-advdsgs.bsa',
        'ccbgssse025-advdsgs.esm',
        'ccbgssse031-advcyrus.bsa',
        'ccbgssse031-advcyrus.esm',
        'ccbgssse034-mntuni.bsa',
        'ccbgssse034-mntuni.esl',
        'ccbgssse035-petnhound.bsa',
        'ccbgssse035-petnhound.esl',
        'ccbgssse036-petbwolf.bsa',
        'ccbgssse036-petbwolf.esl',
        'ccbgssse037-curios.bsa',
        'ccbgssse037-curios.esl',
        'ccbgssse038-bowofshadows.bsa',
        'ccbgssse038-bowofshadows.esl',
        'ccbgssse040-advobgobs.bsa',
        'ccbgssse040-advobgobs.esl',
        'ccbgssse041-netchleather.bsa',
        'ccbgssse041-netchleather.esl',
        'ccbgssse043-crosselv.bsa',
        'ccbgssse043-crosselv.esl',
        'ccbgssse045-hasedoki.bsa',
        'ccbgssse045-hasedoki.esl',
        'ccbgssse050-ba_daedric.bsa',
        'ccbgssse050-ba_daedric.esl',
        'ccbgssse051-ba_daedricmail.bsa',
        'ccbgssse051-ba_daedricmail.esl',
        'ccbgssse052-ba_iron.bsa',
        'ccbgssse052-ba_iron.esl',
        'ccbgssse053-ba_leather.bsa',
        'ccbgssse053-ba_leather.esl',
        'ccbgssse054-ba_orcish.bsa',
        'ccbgssse054-ba_orcish.esl',
        'ccbgssse055-ba_orcishscaled.bsa',
        'ccbgssse055-ba_orcishscaled.esl',
        'ccbgssse056-ba_silver.bsa',
        'ccbgssse056-ba_silver.esl',
        'ccbgssse057-ba_stalhrim.bsa',
        'ccbgssse057-ba_stalhrim.esl',
        'ccbgssse058-ba_steel.bsa',
        'ccbgssse058-ba_steel.esl',
        'ccbgssse059-ba_dragonplate.bsa',
        'ccbgssse059-ba_dragonplate.esl',
        'ccbgssse060-ba_dragonscale.bsa',
        'ccbgssse060-ba_dragonscale.esl',
        'ccbgssse061-ba_dwarven.bsa',
        'ccbgssse061-ba_dwarven.esl',
        'ccbgssse062-ba_dwarvenmail.bsa',
        'ccbgssse062-ba_dwarvenmail.esl',
        'ccbgssse063-ba_ebony.bsa',
        'ccbgssse063-ba_ebony.esl',
        'ccbgssse064-ba_elven.bsa',
        'ccbgssse064-ba_elven.esl',
        'ccbgssse066-staves.bsa',
        'ccbgssse066-staves.esl',
        'ccbgssse067-daedinv.bsa',
        'ccbgssse067-daedinv.esm',
        'ccbgssse068-bloodfall.bsa',
        'ccbgssse068-bloodfall.esl',
        'ccbgssse069-contest.bsa',
        'ccbgssse069-contest.esl',
        'cccbhsse001-gaunt.bsa',
        'cccbhsse001-gaunt.esl',
        'ccedhsse001-norjewel.bsa',
        'ccedhsse001-norjewel.esl',
        'ccedhsse002-splkntset.bsa',
        'ccedhsse002-splkntset.esl',
        'ccedhsse003-redguard.bsa',
        'ccedhsse003-redguard.esl',
        'cceejsse001-hstead.bsa',
        'cceejsse001-hstead.esm',
        'cceejsse002-tower.bsa',
        'cceejsse002-tower.esl',
        'cceejsse003-hollow.bsa',
        'cceejsse003-hollow.esl',
        'cceejsse004-hall.bsa',
        'cceejsse004-hall.esl',
        'cceejsse005-cave.bsa',
        'cceejsse005-cave.esm',
        'ccffbsse001-imperialdragon.bsa',
        'ccffbsse001-imperialdragon.esl',
        'ccffbsse002-crossbowpack.bsa',
        'ccffbsse002-crossbowpack.esl',
        'ccfsvsse001-backpacks.bsa',
        'ccfsvsse001-backpacks.esl',
        'cckrtsse001_altar.bsa',
        'cckrtsse001_altar.esl',
        'ccmtysse001-knightsofthenine.bsa',
        'ccmtysse001-knightsofthenine.esl',
        'ccmtysse002-ve.bsa',
        'ccmtysse002-ve.esl',
        'ccpewsse002-armsofchaos.bsa',
        'ccpewsse002-armsofchaos.esl',
        'ccqdrsse001-survivalmode.bsa',
        'ccqdrsse001-survivalmode.esl',
        'ccqdrsse002-firewood.bsa',
        'ccqdrsse002-firewood.esl',
        'ccrmssse001-necrohouse.bsa',
        'ccrmssse001-necrohouse.esl',
        'cctwbsse001-puzzledungeon.bsa',
        'cctwbsse001-puzzledungeon.esm',
        'cctwbsse001-puzzledungeon.modgroups',
        'ccvsvsse001-winter.bsa',
        'ccvsvsse001-winter.esl',
        'ccvsvsse002-pets.bsa',
        'ccvsvsse002-pets.esl',
        'ccvsvsse003-necroarts.bsa',
        'ccvsvsse003-necroarts.esl',
        'ccvsvsse004-beafarmer.bsa',
        'ccvsvsse004-beafarmer.esl',
    }

    assorted_tweaks = ASkyrimGameInfo.assorted_tweaks | {
        'AssortedTweak_ArrowWeight'}

    #--------------------------------------------------------------------------
    # Import Stats
    #--------------------------------------------------------------------------
    # The contents of these tuples have to stay fixed because of CSV parsers
    stats_csv_attrs = ASkyrimGameInfo.stats_csv_attrs | {
        b'AMMO': ('eid', 'value', 'damage', 'weight'),
    }
    stats_attrs = ASkyrimGameInfo.stats_attrs | {
        b'AMMO': ('value', 'damage', 'weight'),
    }

    #--------------------------------------------------------------------------
    # Tweak Names
    #--------------------------------------------------------------------------
    names_tweaks = ASkyrimGameInfo.names_tweaks | {'NamesTweak_AmmoWeight'}

    # Record information ------------------------------------------------------
    top_groups = [
        b'GMST', b'KYWD', b'LCRT', b'AACT', b'TXST', b'GLOB', b'CLAS', b'FACT',
        b'HDPT', b'HAIR', b'EYES', b'RACE', b'SOUN', b'ASPC', b'MGEF', b'SCPT',
        b'LTEX', b'ENCH', b'SPEL', b'SCRL', b'ACTI', b'TACT', b'ARMO', b'BOOK',
        b'CONT', b'DOOR', b'INGR', b'LIGH', b'MISC', b'APPA', b'STAT', b'SCOL',
        b'MSTT', b'PWAT', b'GRAS', b'TREE', b'CLDC', b'FLOR', b'FURN', b'WEAP',
        b'AMMO', b'NPC_', b'LVLN', b'KEYM', b'ALCH', b'IDLM', b'COBJ', b'PROJ',
        b'HAZD', b'SLGM', b'LVLI', b'WTHR', b'CLMT', b'SPGD', b'RFCT', b'REGN',
        b'NAVI', b'CELL', b'WRLD', b'DIAL', b'QUST', b'IDLE', b'PACK', b'CSTY',
        b'LSCR', b'LVSP', b'ANIO', b'WATR', b'EFSH', b'EXPL', b'DEBR', b'IMGS',
        b'IMAD', b'FLST', b'PERK', b'BPTD', b'ADDN', b'AVIF', b'CAMS', b'CPTH',
        b'VTYP', b'MATT', b'IPCT', b'IPDS', b'ARMA', b'ECZN', b'LCTN', b'MESG',
        b'RGDL', b'DOBJ', b'LGTM', b'MUSC', b'FSTP', b'FSTS', b'SMBN', b'SMQN',
        b'SMEN', b'DLBR', b'MUST', b'DLVW', b'WOOP', b'SHOU', b'EQUP', b'RELA',
        b'SCEN', b'ASTP', b'OTFT', b'ARTO', b'MATO', b'VOLI', b'MOVT', b'SNDR',
        b'DUAL', b'SNCT', b'SOPM', b'COLL', b'CLFM', b'REVB', b'LENS',
    ]

    class LoSkyrimSE(AsteriskGame):
        force_load_first = ASkyrimGameInfo.LoSkyrim.force_load_first
        _ccc_filename = 'Skyrim.ccc'
        _ccc_fallback = tuple(map(FName, ( # Up to date as of 2024/04/30
            'ccASVSSE001-ALMSIVI.esm',
            'ccBGSSSE001-Fish.esm',
            'ccBGSSSE002-ExoticArrows.esl',
            'ccBGSSSE003-Zombies.esl',
            'ccBGSSSE004-RuinsEdge.esl',
            'ccBGSSSE005-Goldbrand.esl',
            'ccBGSSSE006-StendarsHammer.esl',
            'ccBGSSSE007-Chrysamere.esl',
            'ccBGSSSE010-PetDwarvenArmoredMudcrab.esl',
            'ccBGSSSE011-HrsArmrElvn.esl',
            'ccBGSSSE012-HrsArmrStl.esl',
            'ccBGSSSE014-SpellPack01.esl',
            'ccBGSSSE019-StaffofSheogorath.esl',
            'ccBGSSSE020-GrayCowl.esl',
            'ccBGSSSE021-LordsMail.esl',
            'ccMTYSSE001-KnightsoftheNine.esl',
            'ccQDRSSE001-SurvivalMode.esl',
            'ccTWBSSE001-PuzzleDungeon.esm',
            'ccEEJSSE001-Hstead.esm',
            'ccQDRSSE002-Firewood.esl',
            'ccBGSSSE018-Shadowrend.esl',
            'ccBGSSSE035-PetNHound.esl',
            'ccFSVSSE001-Backpacks.esl',
            'ccEEJSSE002-Tower.esl',
            'ccEDHSSE001-NorJewel.esl',
            'ccVSVSSE002-Pets.esl',
            'ccBGSSSE037-Curios.esl',
            'ccBGSSSE034-MntUni.esl',
            'ccBGSSSE045-Hasedoki.esl',
            'ccBGSSSE008-Wraithguard.esl',
            'ccBGSSSE036-PetBWolf.esl',
            'ccFFBSSE001-ImperialDragon.esl',
            'ccMTYSSE002-VE.esl',
            'ccBGSSSE043-CrossElv.esl',
            'ccVSVSSE001-Winter.esl',
            'ccEEJSSE003-Hollow.esl',
            'ccBGSSSE016-Umbra.esm',
            'ccBGSSSE031-AdvCyrus.esm',
            'ccBGSSSE038-BowofShadows.esl',
            'ccBGSSSE040-AdvObGobs.esl',
            'ccBGSSSE050-BA_Daedric.esl',
            'ccBGSSSE052-BA_Iron.esl',
            'ccBGSSSE054-BA_Orcish.esl',
            'ccBGSSSE058-BA_Steel.esl',
            'ccBGSSSE059-BA_Dragonplate.esl',
            'ccBGSSSE061-BA_Dwarven.esl',
            'ccPEWSSE002-ArmsOfChaos.esl',
            'ccBGSSSE041-NetchLeather.esl',
            'ccEDHSSE002-SplKntSet.esl',
            'ccBGSSSE064-BA_Elven.esl',
            'ccBGSSSE063-BA_Ebony.esl',
            'ccBGSSSE062-BA_DwarvenMail.esl',
            'ccBGSSSE060-BA_Dragonscale.esl',
            'ccBGSSSE056-BA_Silver.esl',
            'ccBGSSSE055-BA_OrcishScaled.esl',
            'ccBGSSSE053-BA_Leather.esl',
            'ccBGSSSE051-BA_DaedricMail.esl',
            'ccBGSSSE057-BA_Stalhrim.esl',
            'ccBGSSSE066-Staves.esl',
            'ccBGSSSE067-DaedInv.esm',
            'ccBGSSSE068-Bloodfall.esl',
            'ccBGSSSE069-Contest.esl',
            'ccVSVSSE003-NecroArts.esl',
            'ccVSVSSE004-BeAFarmer.esl',
            'ccBGSSSE025-AdvDSGS.esm',
            'ccFFBSSE002-CrossbowPack.esl',
            'ccBGSSSE013-Dawnfang.esl',
            'ccRMSSSE001-NecroHouse.esl',
            'ccEDHSSE003-Redguard.esl',
            'ccEEJSSE004-Hall.esl',
            'ccEEJSSE005-Cave.esm',
            'ccKRTSSE001_Altar.esl',
            'ccCBHSSE001-Gaunt.esl',
            'ccAFDSSE001-DweSanctuary.esm',
            '_ResourcePack.esl',
        )))
    lo_handler = LoSkyrimSE

    @classmethod
    def init(cls, _package_name=None):
        super().init(_package_name or __name__)

    @classmethod
    def _import_records(cls, package_name, plugin_form_vers=44):
        # first import our records from skyrimse.records
        importlib.import_module('.records', package=__name__)
        # package name is skyrim here
        super()._import_records(package_name, plugin_form_vers)

class EGSSkyrimSEGameInfo(EGSMixin, ASkyrimSEGameInfo):
    """GameInfo override for the Epic Games Store version of Skyrim SE."""
    my_games_name = 'Skyrim Special Edition EPIC'
    appdata_name = 'Skyrim Special Edition EPIC'

    @classproperty
    def game_detect_includes(cls):
        return super().game_detect_includes | {'EOSSDK-Win64-Shipping.dll'}

    @classproperty
    def game_detect_excludes(cls):
        return super().game_detect_excludes - {'EOSSDK-Win64-Shipping.dll'}

    class Eg(ASkyrimSEGameInfo.Eg):
        egs_app_names = ['5d600e4f59974aeba0259c7734134e27', # AE
                         'ac82db5035584c7f8a2c548d98c86b2c'] # SE

class GOGSkyrimSEGameInfo(GOGMixin, ASkyrimSEGameInfo):
    """GameInfo override for the GOG version of Skyrim SE."""
    my_games_name = 'Skyrim Special Edition GOG'
    appdata_name = 'Skyrim Special Edition GOG'
    _gog_game_ids = _GOG_IDS

class SteamSkyrimSEGameInfo(SteamMixin, ASkyrimSEGameInfo):
    """GameInfo override for the Steam version of Skyrim SE."""
    class St(ASkyrimSEGameInfo.St):
        steam_ids = [489830]

class WSSkyrimSEGameInfo(WindowsStoreMixin, ASkyrimSEGameInfo):
    """GameInfo override for the Windows Store version of Skyrim SE."""
    my_games_name = 'Skyrim Special Edition MS'
    appdata_name = 'Skyrim Special Edition MS'

    class Ws(ASkyrimSEGameInfo.Ws):
        legacy_publisher_name = 'Bethesda'
        win_store_name = 'BethesdaSoftworks.SkyrimSE-PC'

GAME_TYPE = {g.unique_display_name: g for g in (
    EGSSkyrimSEGameInfo, GOGSkyrimSEGameInfo, SteamSkyrimSEGameInfo,
    WSSkyrimSEGameInfo)}
