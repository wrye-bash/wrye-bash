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

sys.path.append('../Mopy/bash')

import loot

lootDir = u'../Mopy/bash/compiled'

games_info = OrderedDict([(u'Oblivion', None), (u'Skyrim', None),
                          (u'Fallout3', None), (u'FalloutNV', None),
                          # (u'Fallout4', None),
                          ])

# Detect games.
for g in games_info:
    try:
        reg_key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
            u'Software\\Bethesda Softworks\\%s' % g, 0,
            _winreg.KEY_READ | _winreg.KEY_WOW64_32KEY)
    except OSError as e:
        if e.errno == 2: continue # The system cannot find the file specified
    value = _winreg.QueryValueEx(reg_key, u'Installed Path')
    if value[1] == _winreg.REG_SZ and os.path.exists(value[0]):
        games_info[g] = value[0]
        print u'Found %s.' % g


# Detect LOOT masterlists' installation path in AppData/Local
localAppData = os.path.join(os.environ["LOCALAPPDATA"], 'LOOT')
if not os.path.exists(localAppData):
    raise Exception("No LOOT masterlists install found in %s" % localAppData)

# Detect masterlists
for g, app_dir in games_info.iteritems():
    if app_dir is not None and os.path.exists(os.path.join(localAppData, g)):
        games_info[g] = (
            app_dir, os.path.join(localAppData, g, 'masterlist.yaml'))


# Load the LOOT API.
loot.Init(lootDir)
if loot.LootApi:
    print u'Loaded the LOOT API from "%s", version %s.' % (lootDir, loot.version)
else:
    raise Exception("Couldn't load LOOT API.")


loot_codes = dict(zip(games_info.keys(), (
    loot.LOOT_GAME_TES4, loot.LOOT_GAME_TES5, loot.LOOT_GAME_FO3,
    loot.LOOT_GAME_FONV,
    # loot.LOOT_GAME_FO4,
)))

for game, info in games_info.iteritems():
    if info is None: continue
    print u'Getting masterlist from %s' % info[1]
    taglistDir = u'../Mopy/Bash Patches/%s/taglist.yaml' % game
    # taglistDir = u'../%s - taglist.yaml' % game
    if os.path.exists(info[1]):
        lootDb = loot.LootDb(info[0], loot_codes[game])
        lootDb.PlainLoad(info[1])
        lootDb.DumpMinimal(taglistDir, True)
        print u'%s masterlist converted.' % game
    else:
        print u'Error: %s masterlist not found.' % game

print u'Taglist generator finished.'

raw_input(u'Done')
