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

sys.path.append('../Mopy/bash')

import loot

lootDir = u'../Mopy/bash/compiled'

# Detect games.
oblivionDir = None
skyrimDir = None
fallout3Dir = None
falloutNVDir = None
fallout4Dir = None

# Detect Oblivion.
try:
    key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, u'Software\\Bethesda Softworks\\Oblivion', 0, _winreg.KEY_READ|_winreg.KEY_WOW64_32KEY)
    value = _winreg.QueryValueEx(key,u'Installed Path')
    if value[1] == _winreg.REG_SZ and os.path.exists(value[0]):
        oblivionDir = value[0]
        print u'Found Oblivion.'
except:
    pass
#Detect Skyrim.
try:
    key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, u'Software\\Bethesda Softworks\\Skyrim', 0, _winreg.KEY_READ|_winreg.KEY_WOW64_32KEY)
    value = _winreg.QueryValueEx(key,u'Installed Path')
    if value[1] == _winreg.REG_SZ and os.path.exists(value[0]):
        skyrimDir = value[0]
        print u'Found Skyrim.'
except:
    pass

#Detect Fallout3.
try:
    key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, u'Software\\Bethesda Softworks\\Fallout3', 0, _winreg.KEY_READ|_winreg.KEY_WOW64_32KEY)
    value = _winreg.QueryValueEx(key,u'Installed Path')
    if value[1] == _winreg.REG_SZ and os.path.exists(value[0]):
        fallout3Dir = value[0]
        print u'Found Fallout3.'
except:
    pass

#Detect FalloutNV.
try:
    key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, u'Software\\Bethesda Softworks\\FalloutNV', 0, _winreg.KEY_READ|_winreg.KEY_WOW64_32KEY)
    value = _winreg.QueryValueEx(key,u'Installed Path')
    if value[1] == _winreg.REG_SZ and os.path.exists(value[0]):
        falloutNVDir = value[0]
        print u'Found FalloutNV.'
except:
    pass

#Detect Fallout4.
try:
    key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, u'Software\\Bethesda Softworks\\Fallout4', 0, _winreg.KEY_READ|_winreg.KEY_WOW64_32KEY)
    value = _winreg.QueryValueEx(key,u'Installed Path')
    if value[1] == _winreg.REG_SZ and os.path.exists(value[0]):
        fallout4Dir = value[0]
        print u'Found Fallout4.'
except:
    pass

# Masterlist paths
oblivionMlist = None
skyrimMlist = None
fallout3Mlist = None
falloutNVMlist = None
fallout4Mlist = None

# Detect a LOOT install.
localAppData = os.path.join(os.environ["LOCALAPPDATA"], 'LOOT')
if os.path.exists(localAppData):
    if oblivionDir and os.path.exists(os.path.join(localAppData, 'Oblivion')):
        oblivionMlist = os.path.join(localAppData, 'Oblivion', 'masterlist.yaml')
    if skyrimDir and os.path.exists(os.path.join(localAppData, 'Skyrim')):
        skyrimMlist = os.path.join(localAppData, 'Skyrim', 'masterlist.yaml')
    if fallout3Dir and os.path.exists(os.path.join(localAppData, 'Fallout3')):
        fallout3Mlist = os.path.join(localAppData, 'Fallout3', 'masterlist.yaml')
    if falloutNVDir and os.path.exists(os.path.join(localAppData, 'FalloutNV')):
        falloutNVMlist = os.path.join(localAppData, 'FalloutNV', 'masterlist.yaml')
    if fallout4Dir and os.path.exists(os.path.join(localAppData, 'Fallout4')):
        fallout4Mlist = os.path.join(localAppData, 'Fallout4', 'masterlist.yaml')
else:
    raise Exception("No LOOT install found.")


# Load the LOOT API.
loot.Init(lootDir)
if loot.LootApi:
    print u'Loaded the LOOT API from "%s", version %s.' % (lootDir, loot.version)
else:
    raise Exception("Couldn't load LOOT API.")

if oblivionMlist:
    # Convert Oblivion masterlist.
    print u'Getting masterlist from %s' % oblivionMlist
    taglistDir = u'../Mopy/Bash Patches/Oblivion/taglist.yaml'
    if os.path.exists(oblivionMlist):
        lootDb = loot.LootDb(oblivionDir,loot.LOOT_GAME_TES4)
        lootDb.PlainLoad(oblivionMlist)
        lootDb.DumpMinimal(taglistDir,True)
        print u'Oblivion masterlist converted.'
    else:
        print u'Error: Oblivion masterlist not found.'

if skyrimMlist:
    # Convert Skyrim masterlist.
    print u'Getting masterlist from %s' % skyrimMlist
    taglistDir = u'../Mopy/Bash Patches/Skyrim/taglist.yaml'
    if os.path.exists(skyrimMlist):
        lootDb = loot.LootDb(skyrimDir,loot.LOOT_GAME_TES5)
        lootDb.PlainLoad(skyrimMlist)
        lootDb.DumpMinimal(taglistDir,True)
        print u'Skyrim masterlist converted.'
    else:
        print u'Error: Skyrim masterlist not found.'

if fallout3Mlist:
    # Convert Fallout 3 masterlist.
    print u'Getting masterlist from %s' % fallout3Mlist
    taglistDir = u'../Mopy/Bash Patches/Fallout3/taglist.yaml'
    if os.path.exists(fallout3Mlist):
        lootDb = loot.LootDb(fallout3Dir,loot.LOOT_GAME_FO3)
        lootDb.PlainLoad(fallout3Mlist)
        lootDb.DumpMinimal(taglistDir,True)
        print u'Fallout 3 masterlist converted.'
    else:
        print u'Error: Fallout 3 masterlist not found.'

if falloutNVMlist:
    # Convert Fallout New Vegas masterlist.
    print u'Getting masterlist from %s' % falloutNVMlist
    taglistDir = u'../Mopy/Bash Patches/FalloutNV/taglist.yaml'
    if os.path.exists(falloutNVMlist):
        lootDb = loot.LootDb(falloutNVDir,loot.LOOT_GAME_FONV)
        lootDb.PlainLoad(falloutNVMlist)
        lootDb.DumpMinimal(taglistDir,True)
        print u'Fallout New Vegas masterlist converted.'
    else:
        print u'Error: Fallout New Vegas masterlist not found.'

if fallout4Mlist:
    # Convert Fallout New Vegas masterlist.
    print u'Getting masterlist from %s' % fallout4Mlist
    taglistDir = u'../Mopy/Bash Patches/Fallout4/taglist.yaml'
    if os.path.exists(fallout4Mlist):
        lootDb = loot.LootDb(fallout4Dir,loot.LOOT_GAME_FO4)
        lootDb.PlainLoad(fallout4Mlist)
        lootDb.DumpMinimal(taglistDir,True)
        print u'Fallout 4 masterlist converted.'
    else:
        print u'Error: Fallout 4 masterlist not found.'

print u'Taglist generator finished.'
