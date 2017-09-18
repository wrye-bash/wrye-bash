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
   Skyrim is set at the active game."""

import struct
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
    MreIpct, MreAspc, MreRela, MreEfsh, MreSnct, MreOtft
from ...brec import MreGlob, BaseRecordHeader
from ...exception import ModError

#--Name of the game to use in UI.
displayName = u'Skyrim'
#--Name of the game's filesystem folder.
fsName = u'Skyrim'
#--Alternate display name to use instead of "Wrye Bash for ***"
altName = u'Wrye Smash'
#--Name of game's default ini file.
defaultIniFile = u'Skyrim_default.ini'

#--Exe to look for to see if this is the right game
exe = u'TESV.exe'

#--Registry keys to read to find the install location
regInstallKeys = (u'Bethesda Softworks\\Skyrim', u'Installed Path')

#--patch information
patchURL = u'' # Update via steam
patchTip = u'Update via Steam'

#--URL to the Nexus site for this game
nexusUrl = u'http://www.nexusmods.com/skyrim/'
nexusName = u'Skyrim Nexus'
nexusKey = 'bash.installers.openSkyrimNexus.continue'

# Bsa info
allow_reset_bsa_timestamps = False
bsa_extension = ur'bsa'
supports_mod_inis = True
vanilla_string_bsas = {
    u'skyrim.esm': [u'Skyrim - Interface.bsa'],
    u'update.esm': [u'Skyrim - Interface.bsa'],
    u'dawnguard.esm': [u'Dawnguard.bsa'],
    u'hearthfires.esm': [u'Hearthfires.bsa'],
    u'dragonborn.esm': [u'Dragonborn.bsa'],
}
resource_archives_keys = (u'sResourceArchiveList', u'sResourceArchiveList2')

# Load order info
using_txt_file = True

#--Creation Kit Set information
class cs:
    shortName = u'CK'                # Abbreviated name
    longName = u'Creation Kit'       # Full name
    exe = u'CreationKit.exe'         # Executable to run
    seArgs = None # u'-editor'       # Argument to pass to the SE to load the CS # Not yet needed
    imageName = u'creationkit%s.png' # Image name template for the status bar

#--Script Extender information
class se:
    shortName = u'SKSE'                      # Abbreviated name
    longName = u'Skyrim Script Extender'     # Full name
    exe = u'skse_loader.exe'                 # Exe to run
    steamExe = u'skse_loader.exe'            # Exe to run if a steam install
    url = u'http://skse.silverlock.org/'     # URL to download from
    urlTip = u'http://skse.silverlock.org/'  # Tooltip for mouse over the URL

#--Script Dragon
class sd:
    shortName = u'SD'
    longName = u'Script Dragon'
    installDir = u'asi'

#--SkyProc Patchers
class sp:
    shortName = u'SP'
    longName = u'SkyProc'
    installDir = u'SkyProc Patchers'

#--Quick shortcut for combining the SE and SD names
se_sd = se.shortName+u'/'+sd.longName

#--Graphics Extender information
class ge:
    shortName = u''
    longName = u''
    exe = u'**DNE**'
    url = u''
    urlTip = u''

#--4gb Launcher
class laa:
    # Skyrim has a 4gb Launcher, but as of patch 1.3.10, it is
    # no longer required (Bethsoft updated TESV.exe to already
    # be LAA)
    name = u''
    exe = u'**DNE**'
    launchesSE = False

# Files BAIN shouldn't skip
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

# Directories where specific file extensions should not be skipped by BAIN
dontSkipDirs = {
                # This rule is to allow mods with string translation enabled.
                'interface\\translations':['.txt']
}

#Folders BAIN should never check
SkipBAINRefresh = {
    #Use lowercase names
    u'tes5edit backups',
}

#--Some stuff dealing with INI files
class ini:
    #--True means new lines are allowed to be added via INI Tweaks
    #  (by default)
    allowNewLines = True

    #--INI Entry to enable BSA Redirection
    bsaRedirection = (u'',u'')

#--Save Game format stuff
class ess:
    # Save file capabilities
    canReadBasic = True         # All the basic stuff needed for the Saves Tab
    canEditMasters = True       # Adjusting save file masters
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

#The pickle file for this game. Holds encoded GMST IDs from the big list below.
pklfile = r'bash\db\Skyrim_ids.pkl'

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
}

# Installer -------------------------------------------------------------------
# ensure all path strings are prefixed with 'r' to avoid interpretation of
#   accidental escape sequences
wryeBashDataFiles = {
    u'Bashed Patch.esp',
    u'Bashed Patch, 0.esp',
    u'Bashed Patch, 1.esp',
    u'Bashed Patch, 2.esp',
    u'Bashed Patch, 3.esp',
    u'Bashed Patch, 4.esp',
    u'Bashed Patch, 5.esp',
    u'Bashed Patch, 6.esp',
    u'Bashed Patch, 7.esp',
    u'Bashed Patch, 8.esp',
    u'Bashed Patch, 9.esp',
    u'Bashed Patch, CBash.esp',
    u'Bashed Patch, Python.esp',
    u'Bashed Patch, Warrior.esp',
    u'Bashed Patch, Thief.esp',
    u'Bashed Patch, Mage.esp',
    u'Bashed Patch, Test.esp',
    u'Docs\\Bash Readme Template.html',
    u'Docs\\wtxt_sand_small.css',
    u'Docs\\wtxt_teal.css',
    u'Docs\\Bash Readme Template.txt',
    u'Docs\\Bashed Patch, 0.html',
    u'Docs\\Bashed Patch, 0.txt',
}
wryeBashDataDirs = {
    u'Bash Patches',
    u'INI Tweaks'
}
ignoreDataFiles = {
}
ignoreDataFilePrefixes = {
}
ignoreDataDirs = {
    u'LSData'
}

#--Tags supported by this game
allTags = sorted((
    u'C.Acoustic', u'C.Climate', u'C.Encounter', u'C.ImageSpace', u'C.Light',
    u'C.Location', u'C.SkyLighting', u'C.Music', u'C.Name', u'C.Owner',
    u'C.RecordFlags', u'C.Regions', u'C.Water', u'Deactivate', u'Delev',
    u'Filter', u'Graphics', u'Invent', u'NoMerge', u'Relev', u'Sound',
    u'Stats', u'Names',
    ))

#--Gui patcher classes available when building a Bashed Patch
patchers = (
    u'AliasesPatcher', u'CellImporter', u'GmstTweaker', u'GraphicsPatcher',
    u'ImportInventory', u'ListsMerger', u'PatchMerger', u'SoundPatcher',
    u'StatsPatcher', u'NamesPatcher',
    )

#--CBash Gui patcher classes available when building a Bashed Patch
CBash_patchers = tuple()

# Magic Info ------------------------------------------------------------------
weaponTypes = (
    _(u'Blade (1 Handed)'),
    _(u'Blade (2 Handed)'),
    _(u'Blunt (1 Handed)'),
    _(u'Blunt (2 Handed)'),
    _(u'Staff'),
    _(u'Bow'),
    )

# Race Info -------------------------------------------------------------------
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

    #--Top types in Skyrim order.
    topTypes = ['GMST', 'KYWD', 'LCRT', 'AACT', 'TXST', 'GLOB', 'CLAS', 'FACT',
                'HDPT', 'HAIR', 'EYES', 'RACE', 'SOUN', 'ASPC', 'MGEF', 'SCPT',
                'LTEX', 'ENCH', 'SPEL', 'SCRL', 'ACTI', 'TACT', 'ARMO', 'BOOK',
                'CONT', 'DOOR', 'INGR', 'LIGH', 'MISC', 'APPA', 'STAT', 'SCOL',
                'MSTT', 'PWAT', 'GRAS', 'TREE', 'CLDC', 'FLOR', 'FURN', 'WEAP',
                'AMMO', 'NPC_', 'LVLN', 'KEYM', 'ALCH', 'IDLM', 'COBJ', 'PROJ',
                'HAZD', 'SLGM', 'LVLI', 'WTHR', 'CLMT', 'SPGD', 'RFCT', 'REGN',
                'NAVI', 'CELL', 'WRLD', 'DIAL', 'QUST', 'IDLE', 'PACK', 'CSTY',
                'LSCR', 'LVSP', 'ANIO', 'WATR', 'EFSH', 'EXPL', 'DEBR', 'IMGS',
                'IMAD', 'FLST', 'PERK', 'BPTD', 'ADDN', 'AVIF', 'CAMS', 'CPTH',
                'VTYP', 'MATT', 'IPCT', 'IPDS', 'ARMA', 'ECZN', 'LCTN', 'MESG',
                'RGDL', 'DOBJ', 'LGTM', 'MUSC', 'FSTP', 'FSTS', 'SMBN', 'SMQN',
                'SMEN', 'DLBR', 'MUST', 'DLVW', 'WOOP', 'SHOU', 'EQUP', 'RELA',
                'SCEN', 'ASTP', 'OTFT', 'ARTO', 'MATO', 'MOVT', 'SNDR', 'DUAL',
                'SNCT', 'SOPM', 'COLL', 'CLFM', 'REVB', ]

    #--Dict mapping 'ignored' top types to un-ignored top types.
    topIgTypes = dict(
        [(struct.pack('I', (struct.unpack('I', type)[0]) | 0x1000), type) for
         type in topTypes])

    #-> this needs updating for Skyrim
    recordTypes = set(
        topTypes + 'GRUP,TES4,REFR,ACHR,ACRE,LAND,INFO,NAVM,PHZD,PGRE'.split(
            ','))

#--Mod I/O
#------------------------------------------------------------------------------
# Unused records, they have empty GRUP in skyrim.esm---------------------------
# CLDC ------------------------------------------------------------------------
#------------------------------------------------------------------------------
# Unused records, they have empty GRUP in skyrim.esm---------------------------
# HAIR ------------------------------------------------------------------------
#------------------------------------------------------------------------------
# Unused records, they have empty GRUP in skyrim.esm---------------------------
# PWAT ------------------------------------------------------------------------
#------------------------------------------------------------------------------
# Unused records, they have empty GRUP in skyrim.esm---------------------------
# RGDL ------------------------------------------------------------------------
#------------------------------------------------------------------------------
# Unused records, they have empty GRUP in skyrim.esm---------------------------
# SCOL ------------------------------------------------------------------------
#------------------------------------------------------------------------------
# Unused records, they have empty GRUP in skyrim.esm---------------------------
# SCPT ------------------------------------------------------------------------
#------------------------------------------------------------------------------
# These Are normally not mergable but added to brec.MreRecord.type_class
#
#       MreCell,
#------------------------------------------------------------------------------
# These have undefined FormIDs Do not merge them
#
#       MreNavi, MreNavm,
#------------------------------------------------------------------------------
# These need syntax revision but can be merged once that is corrected
#
#       MreAchr, MreDial, MreLctn, MreInfo, MreFact, MrePerk,
#------------------------------------------------------------------------------
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
    MreVtyp, MreWatr, MreWeap, MreWoop, MreWthr,
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
        MreWthr, MreCell, MreWrld,  # MreNavm, MreNavi
        ####### for debug
        MreQust, MreHeader,
    ))

    #--Simple records
    brec.MreRecord.simpleTypes = (
        set(brec.MreRecord.type_class) - {'TES4', 'ACHR', 'CELL', 'DIAL',
                                          'INFO', 'WRLD', })
