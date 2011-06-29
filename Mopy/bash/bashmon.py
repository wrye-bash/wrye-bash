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
#  Wrye Bash copyright (C) 2005, 2006, 2007, 2008, 2009 Wrye
#
# =============================================================================

"""bashmon is a monitor program which handles requests from Breeze582000's OBSE
extension. Current monitor commands are focused exclusively on shapeshifting the
player, however other commands might be useful to include.

Note: bashmon is based on Breeze582000's brzMonitor (which it replaces).
"""
# Imports ----------------------------------------------------------------------
#--Standard
import cStringIO
import StringIO
import string
import struct
import sys
import time
import traceback

#--Local
import bosh
import bolt
from bosh import PCFaces
from bolt import _, GPath, intArg

#--Debugging/Info
bosh.deprintOn = True
if bolt.bUseUnicode:
    stringBuffer = StringIO.StringIO
else:
    stringBuffer = cStringIO.StringIO

# Utils -----------------------------------------------------------------------
class Data:
    """Some setup and data. Mostly various paths."""
    def __init__(self):
        #--Init bosh stuff
        bosh.initBosh()
        bosh.initSettings(readOnly=True)
        bosh.oblivionIni = bosh.OblivionIni()
        bosh.oblivionIni.mtime = 0
        bosh.modInfos = bosh.ModInfos()
        bosh.saveInfos = bosh.SaveInfos() #--Create, but don't fill
        self.savesDir = None
        self.saves = {}
        self.update()

    def update(self):
        """Check to see if saves directory has changed. If so, update paths."""
        ini = bosh.oblivionIni
        if not self.savesDir or ini.mtime != ini.path.mtime:
            ini.mtime = ini.path.mtime
            savesDir = bosh.dirs['saveBase'].join(ini.getSetting('General','SLocalSavePath','Saves\\'))
            if savesDir != self.savesDir:
                print '\nMonitoring:',savesDir.stail
                self.setSavesDir(savesDir)
                self.setSignals()
                self.clearSignals()

    def setSavesDir(self,savesDir):
        """Set paths for signal files."""
        self.savesDir = savesDir
        #--Breeze
        signalDir = savesDir
        self.brz_ping        = signalDir.join('.ping')
        self.brz_pong        = signalDir.join('.pong')
        self.brz_request     = signalDir.join('.request')
        self.brz_completed   = signalDir.join('.completed')
        self.brz_failed      = signalDir.join('.failed')
        self.brz_shapeIsMale = signalDir.join('.shapeIsMale')
        self.removeRequest   = True
        #--Pluggy text
        signalDir = bosh.dirs['saveBase'].join('Pluggy','User Files','BashMon')
        self.plt_ping        = signalDir.join('ping.txt')
        self.plt_pong        = signalDir.join('pong.txt')
        self.plt_request     = signalDir.join('request.txt')
        self.plt_completed   = signalDir.join('completed.txt')
        self.plt_failed      = signalDir.join('failed.txt')
        self.plt_shapeIsMale = signalDir.join('shapeIsMale.txt')
        self.removeRequest   = False

    def clearSignals(self):
        """Clears all signal files."""
        for source in ('brz','plt'):
            for attr in 'ping,pong,request,completed,failed,shapeIsMale'.split(','):
                path = getattr(self,source+'_'+attr)
                path.remove()

    def setSignals(self,source='brz'):
        """Set signal source to brz or plt as appropriate."""
        for attr in 'ping,pong,request,completed,failed,shapeIsMale'.split(','):
            setattr(self,attr,getattr(self,source+'_'+attr))

    def hasPing(self):
        """Checks for request in either directory, then updates signals accordingly."""
        if self.brz_ping.exists():
            self.setSignals('brz')
            return True
        elif self.plt_ping.exists():
            self.setSignals('plt')
            return True
        else:
            return False

    def hasRequest(self):
        """Checks for request in either directory, then updates signals accordingly."""
        if self.brz_request.exists():
            self.setSignals('brz')
            return True
        elif self.plt_request.exists():
            self.setSignals('plt')
            return True
        else:
            return False

    def hasSaveFile(self,saveKey):
        """True if savekey is in self.saves."""
        return saveKey in self.saves

    def getSaveFile(self,saveName,saveKey=None):
        """Gets save file from self. Else creates a new savefile and loads it."""
        if not saveKey and saveName in self.saves:
            return self.saves[saveName]
        #--New Save file
        saveDir, saveName = self.savesDir.join(saveName).headTail
        saveInfo = bosh.SaveInfo(saveDir,saveName)
        saveFile = bosh.SaveFile(saveInfo)
        saveFile.load()
        if saveKey: self.saves[saveKey] = saveFile
        return saveFile

#--Data singleton
data = None

def printFace(face):
    """Print data on face for debugging."""
    print face.pcName
    for attr in ('iclass','baseSpell','fatigue'):
        print ' ',attr,getattr(face,attr)
    for entry in face.factions:
        print ' %08X %2i' % entry
    print

# Monitor Commands ------------------------------------------------------------
monitorCommands = {}
def monitorCommand(func):
    """Add a function to monitor commands."""
    monitorCommands[func.__name__] = func
    return func

@monitorCommand
def loadSaveGame(saveKey,saveName):
    """Opens save for later operations."""
    data.getSaveFile(saveName,saveKey)

@monitorCommand
def saveSaveGame(saveKey):
    """Saves changes to savegame."""
    saveFile = data.saves.pop(saveKey)
    saveFile.safeSave()

@monitorCommand
def deleteForm(saveKey,formid):
    """Saves changes to savegame. WARNING: NOT TESTED! [3/16/2008]"""
    formid = intArg(formid)
    saveFile = data.getSaveFile(saveName)
    removedRecord = saveFile.removeRecord(formid)
    removedCreated = saveFile.removeCreated(formid)
    print ("  No such record.","  Removed")[removedRecord or removedCreated]

@monitorCommand
def ripAppearance(srcName,destName,srcForm='player',destForm='player',flags=`0x2|0x4|0x8|0x10`):
    """Rips a face from one save game and pastes it into another."""
    flags = intArg(flags)
    srcName = GPath(srcName)
    destName = GPath(destName)
    #--Get source face
    srcFile = data.getSaveFile(srcName)
    if srcForm == 'player':
        face = PCFaces.save_getPlayerFace(srcFile)
    else:
        srcForm = intArg(srcForm)
        face = PCFaces.save_getCreatedFace(srcFile,srcForm)
    #printFace(face)
    #--Set destination face
    if srcName == destName:
        destFile = srcFile
    else:
        destFile = data.getSaveFile(destName)
    if destForm == 'player':
        PCFaces.save_setPlayerFace(destFile,face,flags) #--Race, gender, hair, eyes
    else:
        destForm = intArg(destForm)
        PCFaces.save_setCreatedFace(destFile,destForm,face)
        if not face.gender: data.shapeIsMale.touch()
    if destName not in data.saves:
        destFile.safeSave()
    #--Done
    print face.pcName,'...',

@monitorCommand
def swapPlayer(saveName,oldForm,newForm,flags=0x1|0x2|0x4|0x8|0x10|0x20|0x40):
    """Swaps the player between old and new forms.
    Archives player's current form/stats to oldForm, then changes player into new form."""
    oldForm = intArg(oldForm)
    newForm = intArg(newForm)
    flags = intArg(flags)
    #--Open Save file
    saveName = GPath(saveName)
    saveFile = data.getSaveFile(saveName)
    #--player >> oldForm
    oldFace = PCFaces.save_getPlayerFace(saveFile)
    PCFaces.save_setCreatedFace(saveFile,oldForm,oldFace)
    if not oldFace.gender: data.shapeIsMale.touch()
    #--newForm >> player
    newFace = PCFaces.save_getCreatedFace(saveFile,newForm)
    PCFaces.save_setPlayerFace(saveFile,newFace,flags)
    #--Checking
    #printFace(oldFace)
    #printFace(PCFaces.save_getCreatedFace(saveFile,oldForm))
    #printFace(newFace)
    #printFace(PCFaces.save_getPlayerFace(saveFile))
    #--Save and done
    if saveName not in data.saves:
        saveFile.safeSave()
    print '  %s >> %s...' % (oldFace.pcName,newFace.pcName)

@monitorCommand
def moveSave(oldSave,newSave):
    """Temporarilty moves quicksave.ess to quicktemp.ess."""
    #--Use path.tail to prevent access outside of saves directory
    oldPath = data.savesDir.join(GPath(oldSave).tail)
    newPath = data.savesDir.join(GPath(newSave).tail)
    if newPath.exists() and not newPath.isfile():
        raise bolt.BoltError(newPath+_(' exists and is not a save file.'))
    if oldPath.exists():
        if not oldPath.isfile(): raise bolt.BoltError(oldPath+_(' is not a save file.'))
        oldPath.moveTo(newPath)
        bosh.CoSaves(oldPath).move(newPath)

# Monitor ---------------------------------------------------------------------
header = """== STARTING BASHMON ==
  bashmon is a monitor program which handles requests from Breeze582000's OBSE
  extension. Currently (Dec. 2007), the monitor is focused exclusively on
  shapeshifting the  player, hence it is only useful in combination with
  Breeze's Seducers/Succubi mod and Wrye's Morph mod.

  To stop the monitor, press Ctrl-c or close the command shell window."""

def monitor(sleepSeconds=0.25):
    """Monitor for requests to rip appearance, etc."""
    global data
    print header
    data = Data()
    running = True
    while running:
        try:
            time.sleep(sleepSeconds)
            data.update()
            if data.hasPing():
                print time.strftime('%H:%M:%S',time.localtime()), 'ping'
                data.ping.moveTo(data.pong)
                data.setSignals()
            if not data.hasRequest():
                continue
        except KeyboardInterrupt:
            print time.strftime('\n%H:%M:%S',time.localtime()),_("Bashmon stopped.")
            running = False
            continue
        except IOError:
            print time.strftime('\n%H:%M:%S',time.localtime()),_("Oblivion.ini is busy.")
            continue
        except:
            data.failed.touch()
            traceback.print_exc()
            running = False
            break
        #--Handle lines in request
        print time.strftime('%H:%M:%S request',time.localtime()) #, '='*60
        ins = data.request.open('r')
        try:
            for line in ins:
                line =line.strip()
                if not line: continue
                args = string.split(line)
                #--Handle request
                command,args = args[0],args[1:]
                print ' ', line
                command = monitorCommands[command]
                command(*args)
            ins.close()
            print '  Completed\n'
            data.completed.touch()
            if data.removeRequest:
                data.request.remove()
            while data.completed.exists():
                time.sleep(0.1)
            data.setSignals()
        except:
            print '  Failed\n'
            data.failed.touch()
            traceback.print_exc()
            running = False
            break
    raw_input('\nSTOPPED: Press any key to exit.')

# Main -------------------------------------------------------------------------
if __name__ == '__main__':
    monitor(0.25) #--Call monitor with specified sleep interval
