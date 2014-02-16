# -*- coding: utf-8 -*-
#
#===============================================================================
#
# Taglist Generator
#
# This script generates taglist.yaml files in Mopy\Bashed Patches\Oblivion and
# Mopy\Bashed Patches\Skyrim using the BOSS API and source masterlists. The 
# masterlists must be named "masterlist.txt" or "masterlist.yaml" and put in the 
# folders mentioned above, or be present in a BOSS install that was installed 
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
    
# Masterlist paths
oblivionMlist = None
skyrimMlist = None
fallout3Mlist = None
falloutNVMlist = None
    
# Detect a BOSSv3 install.
localAppData = os.path.join(os.environ["LOCALAPPDATA"], 'BOSS')
if os.path.exists(localAppData):
    if oblivionDir and os.path.exists(os.path.join(localAppData, 'Oblivion')):
        oblivionMlist = os.path.join(localAppData, 'Oblivion', 'masterlist.yaml')
    if skyrimDir and os.path.exists(os.path.join(localAppData, 'Skyrim')):
        skyrimMlist = os.path.join(localAppData, 'Skyrim', 'masterlist.yaml')
    if fallout3Dir and os.path.exists(os.path.join(localAppData, 'Fallout3')):
        fallout3Mlist = os.path.join(localAppData, 'Fallout3', 'masterlist.yaml')
    if falloutNVDir and os.path.exists(os.path.join(localAppData, 'FalloutNV')):
        falloutNVMlist = os.path.join(localAppData, 'FalloutNV', 'masterlist.yaml')
else:
    # No BOSSv3 install, try v2.
    mlistDir = None
    try:
        key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, u'Software\\Boss', 0, _winreg.KEY_READ|_winreg.KEY_WOW64_32KEY)
        value = _winreg.QueryValueEx(key,u'Installed Path')
        if value[1] == _winreg.REG_SZ and os.path.exists(value[0]):
            print u'Found BOSS.'
            mlistDir = value[0]
    except:
        pass
        
    if not mlistDir:
        # No BOSSv2 either, look in local folders.
        mlistDir = os.path.join('..', 'Mopy', 'Bash Patches')
    
    if oblivionDir and os.path.exists(os.path.join(mlistDir, 'Oblivion')):
        oblivionMlist = os.path.join(mlistDir, 'Oblivion', 'masterlist.txt')
    if skyrimDir and os.path.exists(os.path.join(mlistDir, 'Skyrim')):
        skyrimMlist = os.path.join(mlistDir, 'Skyrim', 'masterlist.txt')
    if fallout3Dir and os.path.exists(os.path.join(mlistDir, 'Fallout 3')):
        fallout3Mlist = os.path.join(mlistDir, 'Fallout 3', 'masterlist.txt')
    if falloutNVDir and os.path.exists(os.path.join(mlistDir, 'Fallout New Vegas')):
        falloutNVMlist = os.path.join(mlistDir, 'Fallout New Vegas', 'masterlist.txt')
        

# Load BAPI.
bapi.Init(bapiDir)
if bapi.BAPI:
    print u'Loaded the BOSS API from "%s", version %s.' % (bapiDir, bapi.version)
else:
    raise Exception("Couldn't load BOSS API.")

if oblivionMlist:
    # Convert Oblivion masterlist.
    print u'Getting masterlist from %s' % oblivionMlist
    taglistDir = u'../Mopy/Bash Patches/Oblivion/taglist.yaml'
    if os.path.exists(oblivionMlist):
        boss = bapi.BossDb(oblivionDir,bapi.boss_game_tes4)
        boss.PlainLoad(oblivionMlist)
        boss.DumpMinimal(taglistDir,True)
        print u'Oblivion masterlist converted.'
    else:
        print u'Error: Oblivion masterlist not found.'
    
if skyrimMlist:
    # Convert Skyrim masterlist.
    print u'Getting masterlist from %s' % skyrimMlist
    taglistDir = u'../Mopy/Bash Patches/Skyrim/taglist.yaml'
    if os.path.exists(skyrimMlist):
        boss = bapi.BossDb(skyrimDir,bapi.boss_game_tes5)
        boss.PlainLoad(skyrimMlist)
        boss.DumpMinimal(taglistDir,True)
        print u'Skyrim masterlist converted.'
    else:
        print u'Error: Skyrim masterlist not found.'
    
if fallout3Mlist:
    # Convert Fallout 3 masterlist.
    print u'Getting masterlist from %s' % fallout3Mlist
    taglistDir = u'../Mopy/Bash Patches/Fallout 3/taglist.yaml'
    if os.path.exists(fallout3Mlist):
        boss = bapi.BossDb(fallout3Dir,bapi.boss_game_fo3)
        boss.PlainLoad(fallout3Mlist)
        boss.DumpMinimal(taglistDir,True)
        print u'Fallout 3 masterlist converted.'
    else:
        print u'Error: Fallout 3 masterlist not found.'
    
if falloutNVMlist:
    # Convert Fallout New Vegas masterlist.
    print u'Getting masterlist from %s' % falloutNVMlist
    taglistDir = u'../Mopy/Bash Patches/Fallout New Vegas/taglist.yaml'
    if os.path.exists(falloutNVMlist):
        boss = bapi.BossDb(falloutNVDir,bapi.boss_game_fonv)
        boss.PlainLoad(falloutNVMlist)
        boss.DumpMinimal(taglistDir,True)
        print u'Fallout New Vegas masterlist converted.'
    else:
        print u'Error: Fallout New Vegas masterlist not found.'
    
print u'Taglist generator finished.'
