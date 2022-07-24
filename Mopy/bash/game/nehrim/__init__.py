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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""GameInfo override for TES IV: Oblivion."""
import struct as _struct

from ..oblivion import OblivionGameInfo
from ... import brec, bolt
from ...brec import MreGlob, MreLand

class NehrimGameInfo(OblivionGameInfo):
    displayName = u'Nehrim'
    game_icon = u'nehrim_%u.png'
    bash_root_prefix = u'Nehrim'
    bak_game_name = u'Nehrim'
    game_detect_includes = [u'NehrimLauncher.exe']
    master_file = bolt.FName(u'Nehrim.esm')
    loot_dir = u'Nehrim'
    boss_game_name = u'Nehrim'
    nexusUrl = u'https://www.nexusmods.com/nehrim/'
    nexusName = u'Nehrim Nexus'
    nexusKey = u'bash.installers.openNehrimNexus.continue'

    class Bsa(OblivionGameInfo.Bsa):
        redate_dict = bolt.DefaultFNDict(lambda: 1136066400, { # '2006-01-01'
            u'N - Textures1.bsa': 1104530400, # '2005-01-01'
            u'N - Textures2.bsa': 1104616800, # '2005-01-02'
            u'L - Voices.bsa': 1104703200,    # '2005-01-03'
            u'N - Meshes.bsa': 1104789600,    # '2005-01-04'
            u'N - Sounds.bsa': 1104876000,    # '2005-01-05'
            u'L - Misc.bsa': 1104962400,      # '2005-01-06'
            u'N - Misc.bsa': 1105048800,      # '2005-01-07'
        })

    # Oblivion minus Oblivion-specific patchers (Cobl Catalogs, Cobl
    # Exhaustion, Morph Factions and SEWorld Tests)
    patchers = {p for p in OblivionGameInfo.patchers if p not in
                (u'CoblCatalogs', u'CoblExhaustion', u'MorphFactions',
                 u'SEWorldTests')}

    raceNames = {
        0x224fc:  _(u'Alemanne'),
        0x18d9e5: _(u'Half-Aeterna'),
        0x224fd:  _(u'Normanne'),
    }
    raceShortNames = {
        0x224fc:  u'Ale',
        0x18d9e5: u'Aet',
        0x224fd:  u'Nor',
    }
    raceHairMale = {
        0x224fc:  0x90475, #--Ale
        0x18d9e5: 0x5c6b,  #--Aet
        0x224fd:  0x1da82, #--Nor
    }
    raceHairFemale = {
        0x224fc:  0x1da83, #--Ale
        0x18d9e5: 0x3e1e,  #--Aet
        0x224fd:  0x1da83, #--Nor
    }

    bethDataFiles = {
        'l - misc.bsa',
        'l - voices.bsa',
        'n - meshes.bsa',
        'n - misc.bsa',
        'n - sounds.bsa',
        'n - textures1.bsa',
        'n - textures2.bsa',
        'nehrim.esm',
        'translation.esp',
    }

    nirnroots = _(u'Vynroots')

    @classmethod
    def _dynamic_import_modules(cls, package_name):
        # bypass setting the patchers in super class
        super(OblivionGameInfo, cls)._dynamic_import_modules(package_name)
        # Only Import Roads is of any interest
        from ..oblivion.patcher import preservers
        cls.game_specific_import_patchers = {
            u'ImportRoads': preservers.ImportRoadsPatcher, }

    @classmethod
    def init(cls):
        cls._dynamic_import_modules(__name__)
        from ..oblivion.records import MreActi, MreAlch, MreAmmo, MreAnio, \
            MreArmo, MreBook, MreBsgn, MreClas, MreClot, MreCont, MreCrea, \
            MreDoor, MreEfsh, MreEnch, MreEyes, MreFact, MreFlor, MreFurn, \
            MreGras, MreHair, MreIngr, MreKeym, MreLigh, MreLscr, MreLvlc, \
            MreLvli, MreLvsp, MreMgef, MreMisc, MreNpc, MrePack, MreQust, \
            MreRace, MreScpt, MreSgst, MreSlgm, MreSoun, MreSpel, MreStat, \
            MreTree, MreWatr, MreWeap, MreWthr, MreClmt, MreCsty, MreIdle, \
            MreLtex, MreRegn, MreSbsp, MreSkil, MreAchr, MreAcre, MreCell, \
            MreGmst, MreRefr, MreRoad, MreTes4, MreWrld, MreDial, MreInfo, \
            MrePgrd, MreAppa
        cls.mergeable_sigs = {clazz.rec_sig: clazz for clazz in (
            MreActi, MreAlch, MreAmmo, MreAnio, MreAppa, MreArmo, MreBook,
            MreBsgn, MreClas, MreClot, MreCont, MreCrea, MreDoor, MreEfsh,
            MreEnch, MreEyes, MreFact, MreFlor, MreFurn, MreGlob, MreGras,
            MreHair, MreIngr, MreKeym, MreLigh, MreLscr, MreLvlc, MreLvli,
            MreLvsp, MreMgef, MreMisc, MreNpc, MrePack, MreQust, MreRace,
            MreScpt, MreSgst, MreSlgm, MreSoun, MreSpel, MreStat, MreTree,
            MreWatr, MreWeap, MreWthr, MreClmt, MreCsty, MreIdle, MreLtex,
            MreRegn, MreSbsp, MreSkil, MreAchr, MreAcre, MreCell, MreGmst,
            MreRefr, MreRoad, MreWrld, MreDial, MreInfo, MreLand, MrePgrd,
        )}
        cls.readClasses = (b'MGEF', b'SCPT')
        cls.writeClasses = (b'MGEF',)
        # Setting RecordHeader class variables - Oblivion is special
        header_type = brec.RecordHeader
        header_type.rec_header_size = 20
        header_type.rec_pack_format = [u'=4s', u'I', u'I', u'I', u'I']
        header_type.rec_pack_format_str = u''.join(header_type.rec_pack_format)
        header_type.header_unpack = _struct.Struct(
            header_type.rec_pack_format_str).unpack
        header_type.pack_formats = {0: u'=4sI4s2I'}
        header_type.pack_formats.update(
            {x: u'=4s4I' for x in {1, 6, 7, 8, 9, 10}})
        header_type.pack_formats.update({x: u'=4sIi2I' for x in {2, 3}})
        header_type.pack_formats.update({x: u'=4sIhh2I' for x in {4, 5}})
        # Similar to other games
        header_type.top_grup_sigs = [
            b'GMST', b'GLOB', b'CLAS', b'FACT', b'HAIR', b'EYES', b'RACE',
            b'SOUN', b'SKIL', b'MGEF', b'SCPT', b'LTEX', b'ENCH', b'SPEL',
            b'BSGN', b'ACTI', b'APPA', b'ARMO', b'BOOK', b'CLOT', b'CONT',
            b'DOOR', b'INGR', b'LIGH', b'MISC', b'STAT', b'GRAS', b'TREE',
            b'FLOR', b'FURN', b'WEAP', b'AMMO', b'NPC_', b'CREA', b'LVLC',
            b'SLGM', b'KEYM', b'ALCH', b'SBSP', b'SGST', b'LVLI', b'WTHR',
            b'CLMT', b'REGN', b'CELL', b'WRLD', b'DIAL', b'QUST', b'IDLE',
            b'PACK', b'CSTY', b'LSCR', b'LVSP', b'ANIO', b'WATR', b'EFSH',
        ]
        header_type.valid_header_sigs = set(
            header_type.top_grup_sigs + [b'GRUP', b'TES4', b'ROAD', b'REFR',
                                         b'ACHR', b'ACRE', b'PGRD', b'LAND',
                                         b'INFO'])
        brec.MreRecord.type_class = {x.rec_sig: x for x in (
            MreAchr, MreAcre, MreActi, MreAlch, MreAmmo, MreAnio, MreAppa,
            MreArmo, MreBook, MreBsgn, MreCell, MreClas, MreClot, MreCont,
            MreCrea, MreDoor, MreEfsh, MreEnch, MreEyes, MreFact, MreFlor,
            MreFurn, MreGlob, MreGmst, MreGras, MreHair, MreIngr, MreKeym,
            MreLigh, MreLscr, MreLvlc, MreLvli, MreLvsp, MreMgef, MreMisc,
            MreNpc, MrePack, MreQust, MreRace, MreRefr, MreRoad, MreScpt,
            MreSgst, MreSkil, MreSlgm, MreSoun, MreSpel, MreStat, MreTree,
            MreTes4, MreWatr, MreWeap, MreWrld, MreWthr, MreClmt, MreCsty,
            MreIdle, MreLtex, MreRegn, MreSbsp, MreDial, MreInfo, MreLand,
            MrePgrd)}
        brec.MreRecord.simpleTypes = (set(brec.MreRecord.type_class) - {
            b'TES4', b'ACHR', b'ACRE', b'REFR', b'CELL', b'PGRD', b'ROAD',
            b'LAND', b'WRLD', b'INFO', b'DIAL'})
        cls._validate_records()

GAME_TYPE = NehrimGameInfo
