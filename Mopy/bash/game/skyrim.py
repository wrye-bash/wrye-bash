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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2011 Wrye Bash Team
#
# =============================================================================

"""This modules defines static data for use by bush, when
   TES V: Skyrim is set at the active game."""

#--Name of the game
name = 'Skyrim'

#--exe to look for to see if this is the right game
exe = 'TESV.exe'

#--Registry keys to read to find the install location
regInstallKeys = [
    ('Bethesda Softworks\Skyrim','Installed Path'),
    ]

#--patch information
patchURL = '' # Update via steam
patchTip = 'Update via Steam'

#--Script Extender information
class se:
    shortName = 'SKSE'                      # Abbreviated name
    longName = 'Skyrim Script Extender'     # Full name
    exe = 'skse_loader.exe'                 # Exe to run
    steamExe = 'skse_loader.exe'            # Exe to run if a steam install
    url = 'http://skse.silverlock.org/'     # URL to download from
    urlTip = 'http://skse.silverlock.org/'  # Tooltip for mouse over the URL

#--Graphics Extender information
class ge:
    shortName = ''
    longName = ''
    exe = ''
    url = ''
    urlTip = ''

#--Wrye Bash capabilities with this game
canBash = False      # No Bashed Patch creation or messing with mods
canEditSaves = False # Only basic understanding of save games

#--INI files that should show up in the INI Edits tab
iniFiles = [
    r'Skyrim.ini',
    r'SkyrimPrefs.ini',
    ]

#--The main plugin file Wrye Bash should look for
masterFiles = [
    r'Skyrim.esm',
    ]

#--Game ESM/ESP/BSA files
bethDataFiles = set((
    #--Vanilla
    r'skyrim.esm',
    r'update.esm',
    r'skyrim - animations.bsa',
    r'skyrim - interface.bsa',
    r'skyrim - meshes.bsa',
    r'skyrim - misc.bsa',
    r'skyrim - shaders.bsa',
    r'skyrim - sounds.bsa',
    r'skyrim - textures.bsa',
    r'skyrim - voices.bsa',
    r'skyrim - voicesextra.bsa',
    ))

#--Every file in the Data directory from Bethsoft
allBethFiles = set((
    #--Vanilla
    r'skyrim.esm',
    r'update.esm',
    r'skyrim - animations.bsa',
    r'skyrim - interface.bsa',
    r'skyrim - meshes.bsa',
    r'skyrim - misc.bsa',
    r'skyrim - shaders.bsa',
    r'skyrim - sounds.bsa',
    r'skyrim - textures.bsa',
    r'skyrim - voices.bsa',
    r'skyrim - voicesextra.bsa',
    r'interface\translate_english.txt', #--probably need one for each language
    r'strings\skyrim_english.dlstrings', #--same here
    r'strings\skyrim_english.ilstrings',
    r'strings\skryim_english.strings',
    r'strings\update_english.dlstrings',
    r'strings\update_english.ilstrings',
    r'strings\update_english.strings',
    r'video\bgs_logo.bik',
    ))

#--BAIN: Directories that are OK to install to
dataDirs = set(('bash patches','interface','meshes','strings','textures',
    'video','lodsettings','grass','scripts','shadersfx','music','sound',))
dataDirsPlus = set(('ini tweaks','skse','ini'))

#--Valid ESM/ESP header versions
validHeaderVersions = (0.94,)

#--Class to use to read the TES4 record
tes4ClassName = 'MreTes5'
#--How to unpack the record header
unpackRecordHeader = ('4s5I',24,'REC_HEAD')
