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
"""GameInfo override for TES IV: Oblivion."""
from ..oblivion import OblivionGameInfo
from ... import brec
from ...brec import MreGlob

class NehrimGameInfo(OblivionGameInfo):
    displayName = u'Nehrim'
    bash_root_prefix = u'Nehrim'
    game_detect_file = [u'Data', u'Nehrim.esm']
    master_file = u'Nehrim.esm'
#    pklfile = u'Oblivion_ids.pkl' # TODO new pickle
#    nexusUrl = u'https://www.nexusmods.com/nehrim/' # TODO wait for Nexus?
#    nexusName = u'Nehrim Nexus'
#    nexusKey = u'bash.installers.openNehrimNexus.continue'

    # Oblivion minus Oblivion-specific patchers (Cobl Catalogs, Cobl
    # Exhaustion, Morph Factions and SEWorld Tests)
    patchers = tuple(p for p in OblivionGameInfo.patchers if p not in
                     (u'AlchemicalCatalogs', u'CoblExhaustion', u'MFactMarker',
                      u'SEWorldEnforcer'))
    CBash_patchers = tuple(
        p for p in OblivionGameInfo.CBash_patchers if p not in
         (u'CBash_AlchemicalCatalogs', u'CBash_CoblExhaustion',
          u'CBash_MFactMarker', u'CBash_SEWorldEnforcer'))

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
            MreGmst, MreRefr, MreRoad, MreTes4, MreWrld, MreDial, MreInfo
        cls.mergeClasses = (
            MreActi, MreAlch, MreAmmo, MreAnio, MreAppa, MreArmo, MreBook,
            MreBsgn, MreClas, MreClot, MreCont, MreCrea, MreDoor, MreEfsh,
            MreEnch, MreEyes, MreFact, MreFlor, MreFurn, MreGlob, MreGras,
            MreHair, MreIngr, MreKeym, MreLigh, MreLscr, MreLvlc, MreLvli,
            MreLvsp, MreMgef, MreMisc, MreNpc, MrePack, MreQust, MreRace,
            MreScpt, MreSgst, MreSlgm, MreSoun, MreSpel, MreStat, MreTree,
            MreWatr, MreWeap, MreWthr, MreClmt, MreCsty, MreIdle, MreLtex,
            MreRegn, MreSbsp, MreSkil, MreGmst,
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
        brec.MreRecord.type_class = {x.rec_sig: x for x in (
            MreAchr, MreAcre, MreActi, MreAlch, MreAmmo, MreAnio, MreAppa,
            MreArmo, MreBook, MreBsgn, MreCell, MreClas, MreClot, MreCont,
            MreCrea, MreDoor, MreEfsh, MreEnch, MreEyes, MreFact, MreFlor,
            MreFurn, MreGlob, MreGmst, MreGras, MreHair, MreIngr, MreKeym,
            MreLigh, MreLscr, MreLvlc, MreLvli, MreLvsp, MreMgef, MreMisc,
            MreNpc, MrePack, MreQust, MreRace, MreRefr, MreRoad, MreScpt,
            MreSgst, MreSkil, MreSlgm, MreSoun, MreSpel, MreStat, MreTree,
            MreTes4, MreWatr, MreWeap, MreWrld, MreWthr, MreClmt, MreCsty,
            MreIdle, MreLtex, MreRegn, MreSbsp, MreDial, MreInfo,)}
        brec.MreRecord.simpleTypes = (
            set(brec.MreRecord.type_class) - {'TES4', 'ACHR', 'ACRE', 'REFR',
                                              'CELL', 'PGRD', 'ROAD', 'LAND',
                                              'WRLD', 'INFO', 'DIAL'})

GAME_TYPE = NehrimGameInfo
