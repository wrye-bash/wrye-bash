# -*- coding: utf-8 -*-
#
#===============================================================================
#
# Taglist Generator
#
# This script generates taglist.yaml files in Mopy/Bashed Patches game
# subdirectories using the LOOT API and masterlists. The LOOT API Python module
# must be installed in the Mopy folder (use the install_loot_api.py script), and
# this script must be run from the repository root. The script will skip
# generating taglists for any games that do not have a folder in
# Mopy/Bashed Patches that matches the first tuple value of an element in the
# gamesData list below, so if adding a taglist for a new game, create the folder
# first.
#
# Usage:
#   mktaglist.py
#
#===============================================================================

import os
import shutil
import sys
import tempfile
import urllib
from collections import OrderedDict

sys.path.append(u'Mopy')

import loot_api

def MockGameInstall(masterFileName):
    gamePath = tempfile.mkdtemp()
    os.mkdir(os.path.join(gamePath, u'Data'))
    open(os.path.join(gamePath, u'Data', masterFileName), 'a').close()

    return gamePath

def CleanUpMockedGameInstall(gamePath):
    shutil.rmtree(gamePath)

def DownloadMasterlist(repository, destinationPath):
    url = u'https://raw.githubusercontent.com/loot/{}/v0.10/masterlist.yaml'.format(repository)
    urllib.urlretrieve(url, destinationPath)

print u'Loaded the LOOT API v{0} using wrapper version {1}'.format(loot_api.Version.string(), loot_api.WrapperVersion.string())

gamesData = [
    (u'Oblivion', 'Oblivion.esm', 'oblivion', loot_api.GameType.tes4),
    (u'Skyrim', 'Skyrim.esm', 'skyrim', loot_api.GameType.tes5),
    (u'Skyrim Special Edition', 'Skyrim.esm', 'skyrimse', loot_api.GameType.tes5se),
    (u'Fallout3', 'Fallout3.esm', 'fallout3', loot_api.GameType.fo3),
    (u'FalloutNV', 'FalloutNV.esm', 'falloutnv', loot_api.GameType.fonv),
    (u'Fallout4', 'Fallout4.esm', 'fallout4', loot_api.GameType.fo4),
    ]

for fsName, masterFileName, repository, gameType in gamesData:
    gameInstallPath = MockGameInstall(masterFileName)

    masterlistPath = os.path.join(gameInstallPath, u'masterlist.yaml')
    taglistDir = u'Mopy/Bash Patches/{}/taglist.yaml'.format(fsName)

    if not os.path.exists(taglistDir):
        print u'Skipping taglist for {} as its output directory does not exist'.format(fsName)
        continue

    DownloadMasterlist(repository, masterlistPath)
    lootDb = loot_api.create_database(gameType, gameInstallPath)
    lootDb.load_lists(masterlistPath)
    lootDb.write_minimal_list(taglistDir, True)

    print u'{} masterlist converted.'.format(fsName)

    CleanUpMockedGameInstall(gameInstallPath)

print u'Taglist generator finished.'

raw_input(u'Done')
