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

"""bashmon is a monitor program which handles requests from Breeze582000's OBSE
extension. Current monitor commands are focused exclusively on shapeshifting the
player, however other commands might be useful to include.

Note: bashmon is based on Breeze582000's brzMonitor (which it replaces).
"""
# Imports ----------------------------------------------------------------------
#--Standard
import string
import time
import traceback

#--Local
import bass
import bosh._saves
import bush
import bosh
import bolt
from bosh.faces import PCFaces
from bolt import GPath, intArg

#--Debugging/Info
bolt.deprintOn = True

# Utils -----------------------------------------------------------------------
class Data:
    """Some setup and data. Mostly various paths."""
    def __init__(self):
        #--Init bosh stuff
        bosh.initBosh()
        bosh.initSettings(readOnly=True)
        bosh.oblivionIni = bosh.ini_files.OblivionIni(bush.game.iniFiles[0])
        bosh.oblivionIni.mtime = 0
        bosh.modInfos = bosh.ModInfos()
        bosh.saveInfos = bosh.SaveInfos() #--Create, but don't fill
        self.savesDir = None
        self.saves = {}
        self.update()

    def update(self):
        """Check to see if saves directory has changed. If so, update paths."""
        ini = bosh.oblivionIni
        if not self.savesDir or ini.mtime != ini.abs_path.mtime:
            ini.mtime = ini.abs_path.mtime
            savesDir = bass.dirs['saveBase'].join(ini.getSetting(u'General', u'SLocalSavePath', u'Saves\\'))
            if savesDir != self.savesDir:
                print u'\n'+_(u'Monitoring:'),savesDir.stail
                self.setSavesDir(savesDir)
                self.setSignals()
                self.clearSignals()

    def setSavesDir(self,savesDir):
        """Set paths for signal files."""
        self.savesDir = savesDir
        #--Breeze
        signalDir = savesDir
        self.brz_ping        = signalDir.join(u'.ping')
        self.brz_pong        = signalDir.join(u'.pong')
        self.brz_request     = signalDir.join(u'.request')
        self.brz_completed   = signalDir.join(u'.completed')
        self.brz_failed      = signalDir.join(u'.failed')
        self.brz_shapeIsMale = signalDir.join(u'.shapeIsMale')
        self.removeRequest   = True
        #--Pluggy text
        signalDir = bass.dirs['saveBase'].join(u'Pluggy', u'User Files', u'BashMon')
        self.plt_ping        = signalDir.join(u'ping.txt')
        self.plt_pong        = signalDir.join(u'pong.txt')
        self.plt_request     = signalDir.join(u'request.txt')
        self.plt_completed   = signalDir.join(u'completed.txt')
        self.plt_failed      = signalDir.join(u'failed.txt')
        self.plt_shapeIsMale = signalDir.join(u'shapeIsMale.txt')
        self.removeRequest   = False

    def clearSignals(self):
        """Clears all signal files."""
        for source in ('brz','plt'):
            for attr in 'ping,pong,request,completed,failed,shapeIsMale'.split(','):
                source_path = getattr(self,source+'_'+attr)
                source_path.remove()

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
        saveFile = bosh._saves.SaveFile(saveInfo)
        saveFile.load()
        if saveKey: self.saves[saveKey] = saveFile
        return saveFile

#--Data singleton
data = None

def printFace(face):
    """Print data on face for debugging."""
    print face.pcName
    for attr in ('iclass','baseSpell','fatigue'):
        print u' ',attr,getattr(face,attr)
    for entry in face.factions:
        print u' %08X %2i' % entry
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
    saveFile = data.getSaveFile(saveKey)
    removedRecord = saveFile.removeRecord(formid)
    removedCreated = saveFile.removeCreated(formid)
    print (u"  No such record.",u"  Removed")[removedRecord or removedCreated]

@monitorCommand
def ripAppearance(srcName,destName,srcForm='player',destForm='player',flags=unicode(0x2|0x4|0x8|0x10)):
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
    print face.pcName,u'...',

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
    print u'  %s >> %s...' % (oldFace.pcName,newFace.pcName)

@monitorCommand
def moveSave(oldSave,newSave):
    """Temporarilty moves quicksave.ess to quicktemp.ess."""
    #--Use path.tail to prevent access outside of saves directory
    oldPath = data.savesDir.join(GPath(oldSave).tail)
    newPath = data.savesDir.join(GPath(newSave).tail)
    if newPath.exists() and not newPath.isfile():
        raise bolt.BoltError(newPath+_(u' exists and is not a save file.'))
    if oldPath.exists():
        if not oldPath.isfile(): raise bolt.BoltError(oldPath+_(u' is not a save file.'))
        oldPath.moveTo(newPath)
        bosh.CoSaves(oldPath).move(newPath)

# Monitor ---------------------------------------------------------------------
header = u"""== STARTING BASHMON ==
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
                print time.strftime('%H:%M:%S',time.localtime()), u'ping'
                data.ping.moveTo(data.pong)
                data.setSignals()
            if not data.hasRequest():
                continue
        except KeyboardInterrupt:
            print time.strftime('\n%H:%M:%S',time.localtime()),_(u"Bashmon stopped.")
            running = False
            continue
        except IOError:
            print time.strftime('\n%H:%M:%S',time.localtime()),_(u"Oblivion.ini is busy.")
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
            print u' ',_(u'Completed')+u'\n'
            data.completed.touch()
            if data.removeRequest:
                data.request.remove()
            while data.completed.exists():
                time.sleep(0.1)
            data.setSignals()
        except:
            print u' ',_(u'Failed')+u'\n'
            data.failed.touch()
            traceback.print_exc()
            running = False
            break
    raw_input(u'\nSTOPPED: Press any key to exit.')
