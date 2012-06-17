# -*- coding: utf-8 -*-
#
#===============================================================================
#
# Taglist Generator
#
# This script generates taglist.txt files in Mopy\Bashed Patches\Oblivion and
# Mopy\Bashed Patches\Skyrim using the BOSS API and source masterlists. The 
# masterlists must be named "masterlist.txt" and put in the folders mentioned
# above. Upon generation of the taglists, the masterlists will be deleted (so
# it is effectively a conversion). To generate the taglist for a game, you must
# have the game installed. This script will generate taglists for all detected
# games.
#
# Usage:
#   mktaglist.py
#
# THIS SCRIPT MUST BE PLACED IN MOPY TO EXECUTE, BUT DO NOT PACKAGE FOR RELEASE
#
#===============================================================================

import os
import _winreg
import bash.bapi as bapi

bapiDir = u'bash' + os.sep + u'compiled'

# Detect games.
oblivionDir = None
skyrimDir = None
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

# Load BAPI.
bapi.Init(bapiDir)
if bapi.BAPI:
    print u'Loaded the BOSS API from "%s", version %s.' % (bapiDir, bapi.version)
else:
    raise Exception("Couldn't load BOSS API.")

if oblivionDir:
    # Convert Oblivion masterlist.
    masterlistDir = u'Bash Patches' + os.sep + u'Oblivion' + os.sep + u'masterlist.txt'
    taglistDir = u'Bash Patches' + os.sep + u'Oblivion' + os.sep + u'taglist.txt'
    if os.path.exists(masterlistDir):
        boss = bapi.BossDb(oblivionDir,bapi.BOSS_API_GAME_OBLIVION)
        boss.Load(masterlistDir)
        boss.DumpMinimal(taglistDir,True)
        # Delete converted masterlist.
        os.remove(masterlistDir)
        print u'Oblivion masterlist converted.'
    else:
        print u'Error: Oblivion masterlist not found.'
    
if skyrimDir:
    # Convert Skyrim masterlist.
    masterlistDir = u'Bash Patches' + os.sep + u'Skyrim' + os.sep + u'masterlist.txt'
    taglistDir = u'Bash Patches' + os.sep + u'Skyrim' + os.sep + u'taglist.txt'
    if os.path.exists(masterlistDir):
        boss = bapi.BossDb(skyrimDir,bapi.BOSS_API_GAME_SKYRIM)
        boss.Load(masterlistDir)
        boss.DumpMinimal(taglistDir,True)
        # Delete converted masterlist.
        os.remove(masterlistDir)
        print u'Skyrim masterlist converted.'
    else:
        print u'Error: Skyrim masterlist not found.'
    
print u'Taglist generator finished.'
