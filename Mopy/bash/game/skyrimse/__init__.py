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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2015 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This modules defines static data for use by bush, when TES V:
   Skyrim Special Edition is set at the active game."""

from .constants import *
from .default_tweaks import default_tweaks
from ... import brec
from .records import MreCell, MreWrld, MreFact, MreAchr, MreDial, MreInfo, \
    MreCams, MreWthr, MreDual, MreMato, MreVtyp, MreMatt, MreLvsp, MreEnch, \
    MreProj, MreDlbr, MreRfct, MreMisc, MreActi, MreEqup, MreCpth, MreDoor, \
    MreAnio, MreHazd, MreIdlm, MreEczn, MreIdle, MreLtex, MreQust, MreMstt, \
    MreNpc, MreFlst, MreIpds, MreGmst, MreRevb, MreClmt, MreDebr, MreSmbn, \
    MreLvli, MreSpel, MreKywd, MreLvln, MreAact, MreSlgm, MreRegn, MreFurn, \
    MreGras, MreAstp, MreWoop, MreMovt, MreCobj, MreShou, MreSmen, MreColl, \
    MreArto, MreAddn, MreSopm, MreCsty, MreAppa, MreArma, MreArmo, MreKeym, \
    MreTxst, MreHdpt, MreHeader, MreAlch, MreBook, MreSpgd, MreSndr, MreImgs, \
    MreScrl, MreMust, MreFstp, MreFsts, MreMgef, MreLgtm, MreMusc, MreClas, \
    MreLctn, MreTact, MreBptd, MreDobj, MreLscr, MreDlvw, MreTree, MreWatr, \
    MreFlor, MreEyes, MreWeap, MreIngr, MreClfm, MreMesg, MreLigh, MreExpl, \
    MreLcrt, MreStat, MreAmmo, MreSmqn, MreImad, MreSoun, MreAvif, MreCont, \
    MreIpct, MreAspc, MreRela, MreEfsh, MreSnct, MreOtft, MreVoli, MreLens
from ...bolt import struct_pack, struct_unpack
from ...brec import MreGlob
# Common with Skyrim
from ..skyrim import patchURL, patchTip, allow_reset_bsa_timestamps, \
    bsa_extension, using_txt_file, cs, se, sd, sp, se_sd, ge, laa, dontSkip, \
    dontSkipDirs, ini, pklfile, wryeBashDataFiles, wryeBashDataDirs, \
    ignoreDataFiles, ignoreDataFilePrefixes, ignoreDataDirs, CBash_patchers, \
    weaponTypes, raceNames, raceShortNames, raceHairMale, raceHairFemale, \
    SkipBAINRefresh, supports_mod_inis, resource_archives_keys

#--Name of the game to use in UI.
displayName = u'Skyrim Special Edition'
#--Name of the game's filesystem folder.
fsName = u'Skyrim Special Edition'
#--Alternate display name to use instead of "Wrye Bash for ***"
altName = u'Wrye Smash'
#--Name of game's default ini file.
defaultIniFile = u'Skyrim_Default.ini'

#--Exe to look for to see if this is the right game
exe = u'SkyrimSE.exe'

#--Registry keys to read to find the install location
regInstallKeys = (u'Bethesda Softworks\\Skyrim Special Edition', u'Installed Path')

#--URL to the Nexus site for this game
nexusUrl = u'http://www.nexusmods.com/skyrimspecialedition/'
nexusName = u'Skyrim SE Nexus'
nexusKey = 'bash.installers.openSkyrimSeNexus.continue'

# Bsa info
vanilla_string_bsas = {
    u'skyrim.esm': [u'Skyrim - Patch.bsa', u'Skyrim - Interface.bsa'],
    u'update.esm': [u'Skyrim - Patch.bsa', u'Skyrim - Interface.bsa'],
    u'dawnguard.esm': [u'Skyrim - Patch.bsa', u'Skyrim - Interface.bsa'],
    u'hearthfires.esm': [u'Skyrim - Patch.bsa', u'Skyrim - Interface.bsa'],
    u'dragonborn.esm': [u'Skyrim - Patch.bsa', u'Skyrim - Interface.bsa'],
}

# plugin extensions
espm_extensions = {u'.esp', u'.esm', u'.esl'}

#--Save Game format stuff
class ess:
    # Save file capabilities
    canReadBasic = True         # All the basic stuff needed for the Saves Tab
    canEditMore = False         # No advanced editing
    ext = u'.ess'               # Save file extension

#--INI files that should show up in the INI Edits tab
iniFiles = [
    u'Skyrim.ini',
    u'SkyrimPrefs.ini',
    ]

#--INI setting to setup Save Profiles
saveProfilesKey = (u'General',u'SLocalSavePath')

#--The main plugin Wrye Bash should look for
masterFiles = [
    u'Skyrim.esm',
    u'Update.esm',
    ]

#--BAIN: Directories that are OK to install to
dataDirs = {
    u'dialogueviews',
    u'interface',
    u'meshes',
    u'strings',
    u'textures',
    u'video',
    u'lodsettings',
    u'grass',
    u'scripts',
    u'shadersfx',
    u'music',
    u'sound',
    u'seq',
}
dataDirsPlus = {
    u'skse',
    u'ini',
    u'asi',
    u'skyproc patchers',
    u'calientetools', # bodyslide
    u'dyndolod',
    u'tools',
}

#--Tags supported by this game
allTags = sorted((
    u'Deactivate', u'Delev', u'Invent', u'NoMerge', u'Relev',
    ))

#--Gui patcher classes available when building a Bashed Patch
patchers = (
    u'GmstTweaker', u'ImportInventory', u'ListsMerger', u'PatchMerger',
)

#--Plugin format stuff
class esp:
    #--Wrye Bash capabilities
    canBash = True          # Can create Bashed Patches
    canCBash = False        # CBash can handle this game's records
    canEditHeader = True    # Can edit anything in the TES4 record

    #--Valid ESM/ESP header versions
    validHeaderVersions = (0.94, 1.70,)

    #--Strings Files
    stringsFiles = [
        ((u'Strings',), u'%(body)s_%(language)s.STRINGS'),
        ((u'Strings',), u'%(body)s_%(language)s.DLSTRINGS'),
        ((u'Strings',), u'%(body)s_%(language)s.ILSTRINGS'),
    ]

#--Mergeable record types
mergeClasses = (
    # MreAchr, MreDial, MreInfo,
    # MreFact,
    MreAact, MreActi, MreAddn, MreAlch, MreAmmo, MreAnio, MreAppa, MreArma,
    MreArmo, MreArto, MreAspc, MreAstp, MreAvif, MreBook, MreBptd, MreCams,
    MreClas, MreClfm, MreClmt, MreCobj, MreColl, MreCont, MreCpth, MreCsty,
    MreDebr, MreDlbr, MreDlvw, MreDobj, MreDoor, MreDual, MreEczn, MreEfsh,
    MreEnch, MreEqup, MreExpl, MreEyes, MreFlor, MreFlst, MreFstp, MreFsts,
    MreFurn, MreGlob, MreGmst, MreGras, MreHazd, MreHdpt, MreIdle, MreIdlm,
    MreImad, MreImgs, MreIngr, MreIpct, MreIpds, MreKeym, MreKywd, MreLcrt,
    MreLctn, MreLgtm, MreLigh, MreLscr, MreLtex, MreLvli, MreLvln, MreLvsp,
    MreMato, MreMatt, MreMesg, MreMgef, MreMisc, MreMovt, MreMstt, MreMusc,
    MreMust, MreNpc, MreOtft, MreProj, MreRegn, MreRela, MreRevb, MreRfct,
    MreScrl, MreShou, MreSlgm, MreSmbn, MreSmen, MreSmqn, MreSnct, MreSndr,
    MreSopm, MreSoun, MreSpel, MreSpgd, MreStat, MreTact, MreTree, MreTxst,
    MreVtyp, MreWatr, MreWeap, MreWoop, MreWthr, MreVoli,
    ####### for debug
    MreQust,
)

#--Extra read classes: these record types will always be loaded, even if
# patchers don't need them directly (for example, MGEF for magic effects info)
# MreScpt is Oblivion/FO3/FNV Only
# MreMgef, has not been verified to be used here for Skyrim
readClasses = ()
writeClasses = ()

def init():
    # Due to a bug with py2exe, 'reload' doesn't function properly.  Instead of
    # re-executing all lines within the module, it acts like another 'import'
    # statement - in otherwords, nothing happens.  This means any lines that
    # affect outside modules must do so within this function, which will be
    # called instead of 'reload'

    #--Top types in Skyrim order.
    brec.RecordHeader.topTypes = [
        'GMST', 'KYWD', 'LCRT', 'AACT', 'TXST', 'GLOB', 'CLAS', 'FACT', 'HDPT',
        'HAIR', 'EYES', 'RACE', 'SOUN', 'ASPC', 'MGEF', 'SCPT', 'LTEX', 'ENCH',
        'SPEL', 'SCRL', 'ACTI', 'TACT', 'ARMO', 'BOOK', 'CONT', 'DOOR', 'INGR',
        'LIGH', 'MISC', 'APPA', 'STAT', 'SCOL', 'MSTT', 'PWAT', 'GRAS', 'TREE',
        'CLDC', 'FLOR', 'FURN', 'WEAP', 'AMMO', 'NPC_', 'LVLN', 'KEYM', 'ALCH',
        'IDLM', 'COBJ', 'PROJ', 'HAZD', 'SLGM', 'LVLI', 'WTHR', 'CLMT', 'SPGD',
        'RFCT', 'REGN', 'NAVI', 'CELL', 'WRLD', 'DIAL', 'QUST', 'IDLE', 'PACK',
        'CSTY', 'LSCR', 'LVSP', 'ANIO', 'WATR', 'EFSH', 'EXPL', 'DEBR', 'IMGS',
        'IMAD', 'FLST', 'PERK', 'BPTD', 'ADDN', 'AVIF', 'CAMS', 'CPTH', 'VTYP',
        'MATT', 'IPCT', 'IPDS', 'ARMA', 'ECZN', 'LCTN', 'MESG', 'RGDL', 'DOBJ',
        'LGTM', 'MUSC', 'FSTP', 'FSTS', 'SMBN', 'SMQN', 'SMEN', 'DLBR', 'MUST',
        'DLVW', 'WOOP', 'SHOU', 'EQUP', 'RELA', 'SCEN', 'ASTP', 'OTFT', 'ARTO',
        'MATO', 'MOVT', 'SNDR', 'DUAL', 'SNCT', 'SOPM', 'COLL', 'CLFM', 'REVB',
        'LENS', 'VOLI']

    #-> this needs updating for Skyrim
    brec.RecordHeader.recordTypes = set(
        brec.RecordHeader.topTypes + ['GRUP', 'TES4', 'REFR', 'ACHR', 'ACRE',
                                      'LAND', 'INFO', 'NAVM', 'PHZD', 'PGRE'])
    brec.RecordHeader.plugin_form_version = 44

    #--Record Types
    brec.MreRecord.type_class = dict((x.classType,x) for x in (
        MreAchr, MreDial, MreInfo, MreAact, MreActi, MreAddn, MreAlch, MreAmmo,
        MreAnio, MreAppa, MreArma, MreArmo, MreArto, MreAspc, MreAstp, MreAvif,
        MreBook, MreBptd, MreCams, MreClas, MreClfm, MreClmt, MreCobj, MreColl,
        MreCont, MreCpth, MreCsty, MreDebr, MreDlbr, MreDlvw, MreDobj, MreDoor,
        MreDual, MreEczn, MreEfsh, MreEnch, MreEqup, MreExpl, MreEyes, MreFact,
        MreFlor, MreFlst, MreFstp, MreFsts, MreFurn, MreGlob, MreGmst, MreGras,
        MreHazd, MreHdpt, MreIdle, MreIdlm, MreImad, MreImgs, MreIngr, MreIpct,
        MreIpds, MreKeym, MreKywd, MreLcrt, MreLctn, MreLgtm, MreLigh, MreLscr,
        MreLtex, MreLvli, MreLvln, MreLvsp, MreMato, MreMatt, MreMesg, MreMgef,
        MreMisc, MreMovt, MreMstt, MreMusc, MreMust, MreNpc, MreOtft, MreProj,
        MreRegn, MreRela, MreRevb, MreRfct, MreScrl, MreShou, MreSlgm, MreSmbn,
        MreSmen, MreSmqn, MreSnct, MreSndr, MreSopm, MreSoun, MreSpel, MreSpgd,
        MreStat, MreTact, MreTree, MreTxst, MreVtyp, MreWatr, MreWeap, MreWoop,
        MreWthr, MreCell, MreWrld, MreVoli, MreLens, # MreNavm, MreNavi
        ####### for debug
        MreQust, MreHeader,
    ))

    #--Simple records
    brec.MreRecord.simpleTypes = (
        set(brec.MreRecord.type_class) - {'TES4', 'ACHR', 'CELL', 'DIAL',
                                          'INFO', 'WRLD', })
