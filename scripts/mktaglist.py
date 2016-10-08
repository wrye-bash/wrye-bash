# -*- coding: utf-8 -*-
#
#===============================================================================
#
# Taglist Generator
#
# This script generates taglist.yaml files in Mopy\Bashed Patches\Oblivion and
# Mopy\Bashed Patches\Skyrim using the LOOT API and source masterlists. The
# masterlists must be named "masterlist.txt" or "masterlist.yaml" and put in the
# folders mentioned above, or be present in a LOOT install that was installed
# using its installer.
# To generate the taglist for a game, you must have the game installed. This
# script will generate taglists for all detected games.
#
# Usage:
#   mktaglist.py
#
#===============================================================================

import sys
import os
import _winreg
from collections import OrderedDict

sys.path.append(u'Mopy')

import loot_api

def GetGameInstallPath(fsName):
    try:
        reg_key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
            u'Software\\Bethesda Softworks\\{}'.format(fsName),
            0,
            _winreg.KEY_READ | _winreg.KEY_WOW64_32KEY)
    except OSError as e:
        if e.errno == 2: return None # The system cannot find the file specified

    value = _winreg.QueryValueEx(reg_key, u'Installed Path')
    if value[1] == _winreg.REG_SZ and os.path.exists(value[0]):
        return value[0]
    else:
        return None

def GetMasterlistPath(lootDataDir, gameFolderName):
    masterlistPath = os.path.join(lootDataDir, gameFolderName, u'masterlist.yaml')
    if os.path.exists(masterlistPath):
        return masterlistPath
    else:
        return None

print u'Loaded the LOOT API v{0} using wrapper version {1}'.format(loot_api.Version.string(), loot_api.WrapperVersion.string())

localAppData = os.path.join(os.environ["LOCALAPPDATA"], 'LOOT')
if not os.path.exists(localAppData):
    raise Exception(u'No LOOT masterlists install found in {}'.format(localAppData))

gamesData = [
    (u'Oblivion', loot_api.GameType.tes4),
    (u'Skyrim', loot_api.GameType.tes5),
    (u'Skyrim Special Edition', loot_api.GameType.tes5se),
    (u'Fallout3', loot_api.GameType.fo3),
    (u'FalloutNV', loot_api.GameType.fonv),
    (u'Fallout4', loot_api.GameType.fo4),
    ]

for fsName, gameType in gamesData:
    gameInstallPath = GetGameInstallPath(fsName)

    if gameInstallPath:
        print u'Found {}'.format(gameInstallPath)
    else:
        continue

    masterlistPath = GetMasterlistPath(localAppData, fsName)
    taglistDir = u'Mopy/Bash Patches/{}/taglist.yaml'.format(fsName)

    if masterlistPath is None:
        print u'Error: {} masterlist not found.'.format(fsName)
        continue

    lootDb = loot_api.create_database(gameType, gameInstallPath)
    lootDb.load_lists(masterlistPath)
    lootDb.write_minimal_list(taglistDir, True)

    print u'{} masterlist converted.'.format(fsName)

print u'Taglist generator finished.'

raw_input(u'Done')
