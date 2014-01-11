# -*- coding: utf-8 -*-
#
#===============================================================================
#
# Taglist Generator
#
# This script generates taglist.txt files in Mopy\Bashed Patches\Oblivion and
# Mopy\Bashed Patches\Skyrim using the BOSS API and source masterlists. The 
# masterlists must be named "masterlist.txt" and put in the folders mentioned
# above, or be present in a BOSS install that was installed using its installer. 
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

import bapi

bapiDir = u'../Mopy/bash/compiled'

# Detect games.
oblivionDir = None
skyrimDir = None
fallout3Dir = None
falloutNVDir = None

# Detect Oblivion.
try:
    key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, u'Software\\Bethesda Softworks\\Oblivion', 0, _winreg.KEY_READ|_winreg.KEY_WOW64_32KEY)
    value = _winreg.QueryValueEx(key,u'Installed Path')
    if value[1] == _winreg.REG_SZ and os.path.exists(value[0]):
        oblivionDir = value[0]
        print u'Found Oblivion.'
except:
    raise
#Detect Skyrim.
try:
    key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, u'Software\\Bethesda Softworks\\Skyrim', 0, _winreg.KEY_READ|_winreg.KEY_WOW64_32KEY)
    value = _winreg.QueryValueEx(key,u'Installed Path')
    if value[1] == _winreg.REG_SZ and os.path.exists(value[0]):
        skyrimDir = value[0]
        print u'Found Skyrim.'
except:
    raise
    
#Detect Fallout3.
try:
    key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, u'Software\\Bethesda Softworks\\Fallout3', 0, _winreg.KEY_READ|_winreg.KEY_WOW64_32KEY)
    value = _winreg.QueryValueEx(key,u'Installed Path')
    if value[1] == _winreg.REG_SZ and os.path.exists(value[0]):
        fallout3Dir = value[0]
        print u'Found Fallout3.'
except:
    raise

#Detect FalloutNV.
try:
    key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, u'Software\\Bethesda Softworks\\FalloutNV', 0, _winreg.KEY_READ|_winreg.KEY_WOW64_32KEY)
    value = _winreg.QueryValueEx(key,u'Installed Path')
    if value[1] == _winreg.REG_SZ and os.path.exists(value[0]):
        falloutNVDir = value[0]
        print u'Found FalloutNV.'
except:
    raise

# Detect a BOSS install if present. Doesn't detect manual installs because there is no way to obtain a path without guesswork.
bossDir = None
try:
    key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, u'Software\\Boss', 0, _winreg.KEY_READ|_winreg.KEY_WOW64_32KEY)
    value = _winreg.QueryValueEx(key,u'Installed Path')
    if value[1] == _winreg.REG_SZ and os.path.exists(value[0]):
        bossDir = value[0]
        print u'Found BOSS.'
except:
    pass

# Load BAPI.
bapi.Init(bapiDir)
if bapi.BAPI:
    print u'Loaded the BOSS API from "%s", version %s.' % (bapiDir, bapi.version)
else:
    raise Exception("Couldn't load BOSS API.")

if oblivionDir:
    # Convert Oblivion masterlist.
    if bossDir and os.path.exists(bossDir + u'/Oblivion/masterlist.txt'):
       masterlistDir = bossDir + u'/Oblivion/masterlist.txt'
    else:
       masterlistDir = u'../Mopy/Bash Patches/Oblivion/masterlist.txt'
    print u'Getting masterlist from %s' % masterlistDir
    taglistDir = u'../Mopy/Bash Patches/Oblivion/taglist.txt'
    if os.path.exists(masterlistDir):
        boss = bapi.BossDb(oblivionDir,bapi.BOSS_API_GAME_OBLIVION)
        boss.Load(masterlistDir)
        boss.DumpMinimal(taglistDir,True)
        print u'Oblivion masterlist converted.'
    else:
        print u'Error: Oblivion masterlist not found.'
    
if skyrimDir:
    # Convert Skyrim masterlist.
    if bossDir and os.path.exists(bossDir + u'/Skyrim/masterlist.txt'):
       masterlistDir = bossDir + u'/Skyrim/masterlist.txt'
    else:
       masterlistDir = u'../Mopy/Bash Patches/Skyrim/masterlist.txt'
    print u'Getting masterlist from %s' % masterlistDir
    taglistDir = u'../Mopy/Bash Patches/Skyrim/taglist.txt'
    if os.path.exists(masterlistDir):
        boss = bapi.BossDb(skyrimDir,bapi.BOSS_API_GAME_SKYRIM)
        boss.Load(masterlistDir)
        boss.DumpMinimal(taglistDir,True)
        print u'Skyrim masterlist converted.'
    else:
        print u'Error: Skyrim masterlist not found.'
    
if fallout3Dir:
    # Convert Fallout 3 masterlist.
    if bossDir and os.path.exists(bossDir + u'/Fallout 3/masterlist.txt'):
       masterlistDir = bossDir + u'/Fallout 3/masterlist.txt'
    else:
       masterlistDir = u'../Mopy/Bash Patches/Fallout 3/masterlist.txt'
    print u'Getting masterlist from %s' % masterlistDir
    taglistDir = u'../Mopy/Bash Patches/Fallout 3/taglist.txt'
    if os.path.exists(masterlistDir):
        boss = bapi.BossDb(fallout3Dir,bapi.BOSS_API_GAME_FALLOUT3)
        boss.Load(masterlistDir)
        boss.DumpMinimal(taglistDir,True)
        print u'Fallout 3 masterlist converted.'
    else:
        print u'Error: Fallout 3 masterlist not found.'
    
if falloutNVDir:
    # Convert Fallout New Vegas masterlist.
    if bossDir and os.path.exists(bossDir + u'/Fallout New Vegas/masterlist.txt'):
       masterlistDir = bossDir + u'/Fallout New Vegas/masterlist.txt'
    else:
       masterlistDir = u'../Mopy/Bash Patches/Fallout New Vegas/masterlist.txt'
    print u'Getting masterlist from %s' % masterlistDir
    taglistDir = u'../Mopy/Bash Patches/Fallout New Vegas/taglist.txt'
    if os.path.exists(masterlistDir):
        boss = bapi.BossDb(falloutNVDir,bapi.BOSS_API_GAME_FALLOUTNV)
        boss.Load(masterlistDir)
        boss.DumpMinimal(taglistDir,True)
        print u'Fallout New Vegas masterlist converted.'
    else:
        print u'Error: Fallout New Vegas masterlist not found.'
    
print u'Taglist generator finished.'
