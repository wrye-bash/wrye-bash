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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2014 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import StringIO
import re
import shutil
import struct
from . import ImportFaceDialog, JPEG, Resources
from .. import bosh, bolt, balt, bush
from ..balt import EnabledLink, AppendableLink, Link, CheckLink, ChoiceLink, \
    ItemLink, SeparatorLink, OneItemLink, Image
from ..bolt import GPath, ArgumentError, SubProgress, deprint, BoltError
from ..bosh import formatInteger

modList = None
saveList = None

ID_PROFILES  = balt.IdList(10500, 90,'EDIT','DEFAULT')
ID_PROFILES2 = balt.IdList(10700, 90,'EDIT','DEFAULT') #Needed for Save_Move()

#------------------------------------------------------------------------------
# Saves Links -----------------------------------------------------------------
#------------------------------------------------------------------------------
class Saves_ProfilesData(balt.ListEditorData):
    """Data capsule for save profiles editing dialog."""
    def __init__(self,parent):
        """Initialize."""
        self.baseSaves = bosh.dirs['saveBase'].join(u'Saves')
        #--GUI
        balt.ListEditorData.__init__(self,parent)
        self.showAdd    = True
        self.showRename = True
        self.showRemove = True
        self.showInfo   = True
        self.infoWeight = 2
        self.infoReadOnly = False

    def getItemList(self):
        """Returns load list keys in alpha order."""
        #--Get list of directories in Hidden, but do not include default.
        items = [x.s for x in bosh.saveInfos.getLocalSaveDirs()]
        items.sort(key=lambda a: a.lower())
        return items

    #--Info box
    def getInfo(self,item):
        """Returns string info on specified item."""
        profileSaves = u'Saves\\'+item+u'\\'
        return bosh.saveInfos.profiles.getItem(profileSaves,'info',_(u'About %s:') % item)
    def setInfo(self,item,text):
        """Sets string info on specified item."""
        profileSaves = u'Saves\\'+item+u'\\'
        bosh.saveInfos.profiles.setItem(profileSaves,'info',text)

    def add(self):
        """Adds a new profile."""
        newName = balt.askText(self.parent,_(u"Enter profile name:"))
        if not newName:
            return False
        if newName in self.getItemList():
            balt.showError(self.parent,_(u'Name must be unique.'))
            return False
        if len(newName) == 0 or len(newName) > 64:
            balt.showError(self.parent,
                _(u'Name must be between 1 and 64 characters long.'))
            return False
        try:
            newName.encode('cp1252')
        except UnicodeEncodeError:
            balt.showError(self.parent,
                _(u'Name must be encodable in Windows Codepage 1252 (Western European), due to limitations of %(gameIni)s.') % {'gameIni':bush.game.iniFiles[0]})
            return False
        self.baseSaves.join(newName).makedirs()
        newSaves = u'Saves\\'+newName+u'\\'
        bosh.saveInfos.profiles.setItem(newSaves,'vOblivion',bosh.modInfos.voCurrent)
        return newName

    def rename(self,oldName,newName):
        """Renames profile oldName to newName."""
        newName = newName.strip()
        lowerNames = [name.lower() for name in self.getItemList()]
        #--Error checks
        if newName.lower() in lowerNames:
            balt.showError(self,_(u'Name must be unique.'))
            return False
        if len(newName) == 0 or len(newName) > 64:
            balt.showError(self.parent,
                _(u'Name must be between 1 and 64 characters long.'))
            return False
        #--Rename
        oldDir,newDir = (self.baseSaves.join(dir) for dir in (oldName,newName))
        oldDir.moveTo(newDir)
        oldSaves,newSaves = ((u'Saves\\'+name+u'\\') for name in (oldName,newName))
        if bosh.saveInfos.localSave == oldSaves:
            bosh.saveInfos.setLocalSave(newSaves)
            Link.Frame.SetTitle()
        bosh.saveInfos.profiles.moveRow(oldSaves,newSaves)
        return newName

    def remove(self,profile):
        """Removes load list."""
        profileSaves = u'Saves\\'+profile+u'\\'
        #--Can't remove active or Default directory.
        if bosh.saveInfos.localSave == profileSaves:
            balt.showError(self.parent,_(u'Active profile cannot be removed.'))
            return False
        #--Get file count. If > zero, verify with user.
        profileDir = bosh.dirs['saveBase'].join(profileSaves)
        files = [file for file in profileDir.list() if bosh.reSaveExt.search(file.s)]
        if files:
            message = _(u'Delete profile %s and the %d save files it contains?') % (profile,len(files))
            if not balt.askYes(self.parent,message,_(u'Delete Profile')):
                return False
        #--Remove directory
        if GPath(bush.game.fsName).join(u'Saves').s not in profileDir.s:
            raise BoltError(u'Sanity check failed: No "%s\\Saves" in %s.' % (bush.game.fsName,profileDir.s))
        shutil.rmtree(profileDir.s) #--DO NOT SCREW THIS UP!!!
        bosh.saveInfos.profiles.delRow(profileSaves)
        return True

#------------------------------------------------------------------------------
class Saves_Profiles(ChoiceLink):
    """Select a save set profile -- i.e., the saves directory."""
    local = None

    def __init__(self):
        super(Saves_Profiles, self).__init__()
        self.idList = ID_PROFILES
        self.extraActions = {self.idList.EDIT: self.DoEdit,
                            self.idList.DEFAULT: self.DoDefault,}

    @property
    def items(self): return [x.s for x in bosh.saveInfos.getLocalSaveDirs()]

    class _CheckLink(CheckLink):
        def _check(self):
            return Saves_Profiles.local == (u'Saves\\' + self.text + u'\\')
    cls = _CheckLink

    def _initData(self, window, data):
        super(Saves_Profiles, self)._initData(window, data)
        Saves_Profiles.local = bosh.saveInfos.localSave
        self.extraItems =[ItemLink(self.idList.EDIT, _(u"Edit Profiles...")),
                          SeparatorLink()
        ]
        class _Default(CheckLink):
            text = _(u'Default')
            def _check(self): return Saves_Profiles.local == u'Saves\\'
        self.extraItems += [_Default(_id=self.idList.DEFAULT)]

    def DoEdit(self,event):
        """Show profiles editing dialog."""
        data = Saves_ProfilesData(self.window)
        balt.ListEditor.Display(self.window, _(u'Save Profiles'), data)

    def DoDefault(self,event):
        """Handle selection of Default."""
        arcSaves,newSaves = bosh.saveInfos.localSave,u'Saves\\'
        bosh.saveInfos.setLocalSave(newSaves)
        self.swapPlugins(arcSaves,newSaves)
        self.swapOblivionVersion(newSaves)
        Link.Frame.SetTitle()
        self.window.details.SetFile(None)
        modList.RefreshUI()
        Link.Frame.RefreshData()

    def DoList(self,event):
        """Handle selection of label."""
        profile = self.items[event.GetId()-self.idList.BASE]
        arcSaves = bosh.saveInfos.localSave
        newSaves = u'Saves\\%s\\' % (profile,)
        bosh.saveInfos.setLocalSave(newSaves)
        self.swapPlugins(arcSaves,newSaves)
        self.swapOblivionVersion(newSaves)
        Link.Frame.SetTitle()
        self.window.details.SetFile(None)
        Link.Frame.RefreshData()
        bosh.modInfos.autoGhost()
        modList.RefreshUI()

    @staticmethod
    def swapPlugins(arcSaves,newSaves):
        """Saves current plugins into arcSaves directory and loads plugins
        from newSaves directory (if present)."""
        arcPath,newPath = (bosh.dirs['saveBase'].join(saves)
            for saves in (arcSaves,newSaves))
        #--Archive old Saves
        bosh.modInfos.plugins.copyTo(arcPath)
        bosh.modInfos.plugins.copyFrom(newPath)

    @staticmethod
    def swapOblivionVersion(newSaves):
        """Swaps Oblivion version to memorized version."""
        voNew = bosh.saveInfos.profiles.setItemDefault(newSaves,'vOblivion',bosh.modInfos.voCurrent)
        if voNew in bosh.modInfos.voAvailable:
            bosh.modInfos.setOblivionVersion(voNew)

#------------------------------------------------------------------------------
class Save_LoadMasters(OneItemLink):
    """Sets the load list to the save game's masters.""" # TODO(ut): test
    text = _(u'Load Masters')
    help = _(u"Set the load list to the save game's masters")

    def Execute(self,event):
        fileName = GPath(self.selected[0])
        fileInfo = self.window.data[fileName]
        errorMessage = bosh.modInfos.selectExact(fileInfo.masterNames)
        modList.PopulateItems()
        saveList.PopulateItems()
        self.window.details.SetFile(fileName)
        if errorMessage:
            balt.showError(self.window,errorMessage,fileName.s)

#------------------------------------------------------------------------------
class Save_ImportFace(OneItemLink):
    """Imports a face from another save."""
    text = _(u'Import Face...')
    help = _(u'Import a face from another save')

    def Execute(self,event):
        #--File Info
        fileName = GPath(self.selected[0])
        fileInfo = self.window.data[fileName]
        #--Select source face file
        srcDir = fileInfo.dir
        wildcard = _(u'%s Files')%bush.game.displayName+u' (*.esp;*.esm;*.ess;*.esr)|*.esp;*.esm;*.ess;*.esr'
        #--File dialog
        srcPath = balt.askOpen(self.window,_(u'Face Source:'),srcDir, u'', wildcard,mustExist=True)
        if not srcPath: return
        if bosh.reSaveExt.search(srcPath.s):
            self.FromSave(fileInfo,srcPath)
        elif bosh.reModExt.search(srcPath.s):
            self.FromMod(fileInfo,srcPath)

    def FromSave(self,fileInfo,srcPath):
        """Import from a save."""
        #--Get face
        srcDir,srcName = GPath(srcPath).headTail
        srcInfo = bosh.SaveInfo(srcDir,srcName)
        with balt.Progress(srcName.s) as progress:
            saveFile = bosh.SaveFile(srcInfo)
            saveFile.load(progress)
            progress.Destroy()
            srcFaces = bosh.PCFaces.save_getFaces(saveFile)
            #--Dialog
            ImportFaceDialog.Display(self.window,srcName.s,fileInfo,srcFaces)

    def FromMod(self,fileInfo,srcPath):
        """Import from a mod."""
        #--Get faces
        srcDir,srcName = GPath(srcPath).headTail
        srcInfo = bosh.ModInfo(srcDir,srcName)
        srcFaces = bosh.PCFaces.mod_getFaces(srcInfo)
        #--No faces to import?
        if not srcFaces:
            balt.showOk(self.window,_(u'No player (PC) faces found in %s.') % srcName.s,srcName.s)
            return
        #--Dialog
        ImportFaceDialog.Display(self.window, srcName.s, fileInfo, srcFaces)

#------------------------------------------------------------------------------
class Save_RenamePlayer(EnabledLink):
    """Renames the Player character in a save game."""
    text = _(u'Rename Player...')
    help = _(u'Rename the Player character in a save game')

    def _enable(self): return len(self.selected) != 0

    def Execute(self,event):
        saveInfo = bosh.saveInfos[self.selected[0]]
        newName = balt.askText(self.window,_(u"Enter new player name. E.g. Conan the Bold"),
            _(u"Rename player"),saveInfo.header.pcName)
        if not newName: return
        for save in self.selected:
            savedPlayer = bosh.Save_NPCEdits(self.window.data[GPath(save)])
            savedPlayer.renamePlayer(newName)
        bosh.saveInfos.refresh()
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class Save_ExportScreenshot(OneItemLink):
    """Exports the saved screenshot from a save game."""
    text = _(u'Export Screenshot...')
    help = _(u'Export the saved screenshot from a save game')

    def Execute(self,event):
        saveInfo = bosh.saveInfos[self.selected[0]]
        imagePath = balt.askSave(Link.Frame,_(u'Save Screenshot as:'), bosh.dirs['patches'].s,_(u'Screenshot %s.jpg') % self.selected[0].s,u'*.jpg')
        if not imagePath: return
        width,height,data = saveInfo.header.image
        image = Image.GetImage(data, height, width)
        image.SaveFile(imagePath.s,JPEG)

#------------------------------------------------------------------------------
class Save_DiffMasters(EnabledLink):
    """Shows how saves masters differ from active mod list."""
    text = _(u'Diff Masters...')
    help = _(u"Show how the masters of a save differ from active mod list or"
             u" another save")

    def _enable(self): return len(self.selected) in (1,2)

    def Execute(self,event):
        oldNew = map(GPath,self.selected)
        oldNew.sort(key = lambda x: bosh.saveInfos.dir.join(x).mtime)
        oldName = oldNew[0]
        oldInfo = self.window.data[GPath(oldName)]
        oldMasters = set(oldInfo.masterNames)
        if len(self.selected) == 1:
            newName = GPath(_(u'Active Masters'))
            newMasters = set(bosh.modInfos.ordered)
        else:
            newName = oldNew[1]
            newInfo = self.window.data[GPath(newName)]
            newMasters = set(newInfo.masterNames)
        missing = oldMasters - newMasters
        extra = newMasters - oldMasters
        if not missing and not extra:
            message = _(u'Masters are the same.')
            balt.showInfo(self.window,message,_(u'Diff Masters'))
        else:
            message = u''
            if missing:
                message += u'=== '+_(u'Removed Masters')+u' (%s):\n* ' % oldName.s
                message += u'\n* '.join(x.s for x in bosh.modInfos.getOrdered(missing))
                if extra: message += u'\n\n'
            if extra:
                message += u'=== '+_(u'Added Masters')+u' (%s):\n* ' % newName.s
                message += u'\n* '.join(x.s for x in bosh.modInfos.getOrdered(extra))
            balt.showWryeLog(self.window,message,_(u'Diff Masters'))

#------------------------------------------------------------------------------
class Save_Rename(EnabledLink):
    """Renames Save File."""
    text = _(u'Rename...')
    help = _(u'Rename Save File')
    def _enable(self): return len(self.selected) != 0

    def Execute(self,event):
        if len(self.selected) > 0:
            index = self.window.list.FindItem(0,self.selected[0].s)
            if index != -1:
                self.window.list.EditLabel(index)

#------------------------------------------------------------------------------
class Save_Renumber(EnabledLink):
    """Renumbers a whole lot of save files."""
    text = _(u'Re-number Save(s)...')
    help = _(u'Renumber a whole lot of save files')
    def _enable(self): return len(self.selected) != 0

    def Execute(self,event):
        #--File Info
        newNumber = balt.askNumber(self.window,_(u"Enter new number to start numbering the selected saves at."),
            prompt=_(u'Save Number'),title=_(u'Re-number Saves'),value=1,min=1,max=10000)
        if not newNumber: return
        rePattern = re.compile(ur'^(save )(\d*)(.*)',re.I|re.U)
        for index, name in enumerate(self.selected):
            maPattern = rePattern.match(name.s)
            if not maPattern: continue
            maPattern = maPattern.groups()
            if not maPattern[1]: continue
            newFileName = u"%s%d%s" % (maPattern[0],newNumber,maPattern[2])
            if newFileName != name.s:
                oldPath = bosh.saveInfos.dir.join(name.s)
                newPath = bosh.saveInfos.dir.join(newFileName)
                if not newPath.exists():
                    oldPath.moveTo(newPath)
                    if GPath(oldPath.s[:-3]+bush.game.se.shortName.lower()).exists():
                        GPath(oldPath.s[:-3]+bush.game.se.shortName.lower()).moveTo(GPath(newPath.s[:-3]+bush.game.se.shortName.lower()))
                    if GPath(oldPath.s[:-3]+u'pluggy').exists():
                        GPath(oldPath.s[:-3]+u'pluggy').moveTo(GPath(newPath.s[:-3]+u'pluggy'))
                newNumber += 1
        bosh.saveInfos.refresh()
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class Save_EditCreatedData(balt.ListEditorData):
    """Data capsule for custom item editing dialog."""
    def __init__(self,parent,saveFile,recordTypes):
        """Initialize."""
        self.changed = False
        self.saveFile = saveFile
        data = self.data = {}
        self.enchantments = {}
        #--Parse records and get into data
        for index,record in enumerate(saveFile.created):
            if record.recType == 'ENCH':
                self.enchantments[record.fid] = record.getTypeCopy()
            elif record.recType in recordTypes:
                record = record.getTypeCopy()
                if not record.full: continue
                record.getSize() #--Since type copy makes it changed.
                saveFile.created[index] = record
                record_full = record.full
                if record_full not in data: data[record_full] = (record_full,[])
                data[record_full][1].append(record)
        #--GUI
        balt.ListEditorData.__init__(self,parent)
        self.showRename = True
        self.showInfo = True
        self.showSave = True
        self.showCancel = True

    def getItemList(self):
        """Returns load list keys in alpha order."""
        items = sorted(self.data.keys())
        items.sort(key=lambda x: self.data[x][1][0].recType)
        return items

    def getInfo(self,item):
        """Returns string info on specified item."""
        buff = StringIO.StringIO()
        name,records = self.data[item]
        record = records[0]
        #--Armor, clothing, weapons
        if record.recType == 'ARMO':
            buff.write(_(u'Armor')+u'\n'+_(u'Flags: '))
            buff.write(u', '.join(record.flags.getTrueAttrs())+u'\n')
            for attr in ('strength','value','weight'):
                buff.write(u'%s: %s\n' % (attr,getattr(record,attr)))
        elif record.recType == 'CLOT':
            buff.write(_(u'Clothing')+u'\n'+_(u'Flags: '))
            buff.write(u', '.join(record.flags.getTrueAttrs())+u'\n')
        elif record.recType == 'WEAP':
            buff.write(bush.game.weaponTypes[record.weaponType]+u'\n')
            for attr in ('damage','value','speed','reach','weight'):
                buff.write(u'%s: %s\n' % (attr,getattr(record,attr)))
        #--Enchanted? Switch record to enchantment.
        if hasattr(record,'enchantment') and record.enchantment in self.enchantments:
            buff.write(u'\n'+_(u'Enchantment:')+u'\n')
            record = self.enchantments[record.enchantment].getTypeCopy()
        #--Magic effects
        if record.recType in ('ALCH','SPEL','ENCH'):
            buff.write(record.getEffectsSummary())
        #--Done
        ret = buff.getvalue()
        buff.close()
        return ret

    def rename(self,oldName,newName):
        """Renames oldName to newName."""
        #--Right length?
        if len(newName) == 0:
            return False
        elif len(newName) > 128:
            balt.showError(self.parent,_(u'Name is too long.'))
            return False
        elif newName in self.data:
            balt.showError(self.parent,_(u'Name is already used.'))
            return False
        #--Rename
        self.data[newName] = self.data.pop(oldName)
        self.changed = True
        return newName

    def save(self):
        """Handles save button."""
        if not self.changed:
            balt.showOk(self.parent,_(u'No changes made.'))
        else:
            self.changed = False #--Allows graceful effort if close fails.
            count = 0
            for newName,(oldName,records) in self.data.items():
                if newName == oldName: continue
                for record in records:
                    record.full = newName
                    record.setChanged()
                    record.getSize()
                count += 1
            self.saveFile.safeSave()
            balt.showOk(self.parent, _(u'Names modified: %d.') % count,self.saveFile.fileInfo.name.s)

#------------------------------------------------------------------------------
class Save_EditCreated(OneItemLink):
    """Allows user to rename custom items (spells, enchantments, etc)."""
    menuNames = {'ENCH':_(u'Rename Enchanted...'),
                 'SPEL':_(u'Rename Spells...'),
                 'ALCH':_(u'Rename Potions...')
                 }
    recordTypes = {'ENCH':('ARMO','CLOT','WEAP')}
    help = _(u'Allow user to rename custom items (spells, enchantments, etc)')

    def __init__(self,type):
        if type not in Save_EditCreated.menuNames:
            raise ArgumentError
        super(Save_EditCreated, self).__init__()
        self.type = type
        self.menuName = self.text = Save_EditCreated.menuNames[self.type]

    def Execute(self,event):
        """Handle menu selection."""
        #--Get save info for file
        fileName = GPath(self.selected[0])
        fileInfo = self.window.data[fileName]
        #--Get SaveFile
        with balt.Progress(_(u"Loading...")) as progress:
            saveFile = bosh.SaveFile(fileInfo)
            saveFile.load(progress)
        #--No custom items?
        recordTypes = Save_EditCreated.recordTypes.get(self.type,(self.type,))
        records = [record for record in saveFile.created if record.recType in recordTypes]
        if not records:
            balt.showOk(self.window,_(u'No items to edit.'))
            return
        #--Open editor dialog
        data = Save_EditCreatedData(self.window,saveFile,recordTypes)
        balt.ListEditor.Display(self.window, self.menuName, data)

#------------------------------------------------------------------------------
class Save_EditPCSpellsData(balt.ListEditorData):
    """Data capsule for pc spell editing dialog."""
    def __init__(self,parent,saveInfo):
        """Initialize."""
        self.saveSpells = bosh.SaveSpells(saveInfo)
        with balt.Progress(_(u'Loading Masters')) as progress:
            self.saveSpells.load(progress)
        self.data = self.saveSpells.getPlayerSpells()
        self.removed = set()
        #--GUI
        balt.ListEditorData.__init__(self,parent)
        self.showRemove = True
        self.showInfo = True
        self.showSave = True
        self.showCancel = True

    def getItemList(self):
        """Returns load list keys in alpha order."""
        return sorted(self.data.keys(),key=lambda a: a.lower())

    def getInfo(self,item):
        """Returns string info on specified item."""
        iref,record = self.data[item]
        return record.getEffectsSummary()

    def remove(self,item):
        """Removes item. Return true on success."""
        if not item in self.data: return False
        iref,record = self.data[item]
        self.removed.add(iref)
        del self.data[item]
        return True

    def save(self):
        """Handles save button click."""
        self.saveSpells.removePlayerSpells(self.removed)

#------------------------------------------------------------------------------
class Save_EditPCSpells(OneItemLink):
    """Save spell list editing dialog."""
    text = _(u'Delete Spells...')
    # TODO(ut): help + AppendtoMenu had : """Append ref replacer items to menu."""

    def Execute(self,event):
        fileName = GPath(self.selected[0])
        fileInfo = self.window.data[fileName]
        data = Save_EditPCSpellsData(self.window,fileInfo)
        balt.ListEditor.Display(self.window, _(u'Player Spells'), data)

#------------------------------------------------------------------------------
class Save_EditCreatedEnchantmentCosts(OneItemLink):
    """Dialogue and Menu for setting number of uses for Cast When Used Enchantments."""
    text = _(u'Set Number of Uses for Weapon Enchantments...')
    help = _(u'Set number of uses for Cast When Used Enchantments')

    def Execute(self,event):
        fileName = GPath(self.selected[0])
        fileInfo = self.window.data[fileName]
        dialog = balt.askNumber(self.window,
            (_(u'Enter the number of uses you desire per recharge for all custom made enchantments.')
             + u'\n' +
             _(u'(Enter 0 for unlimited uses)')),
            prompt=_(u'Uses'),title=_(u'Number of Uses'),value=50,min=0,max=10000)
        if not dialog: return
        Enchantments = bosh.SaveEnchantments(fileInfo)
        Enchantments.load()
        Enchantments.setCastWhenUsedEnchantmentNumberOfUses(dialog)

#------------------------------------------------------------------------------
class Save_Move(ChoiceLink):
    """Moves or copies selected files to alternate profile."""
    local = None

    def __init__(self, copyMode=False):
        super(Save_Move, self).__init__()
        self.idList = ID_PROFILES if copyMode else ID_PROFILES2
        self.copyMode = copyMode
        self.extraActions = {self.idList.DEFAULT: self.DoDefault}

    @property
    def items(self): return [x.s for x in bosh.saveInfos.getLocalSaveDirs()]

    class _WasCheckLink(EnabledLink): # never checked at that
        def _enable(self):
            return Save_Move.local != (u'Saves\\'+ self.text +u'\\')
    cls = _WasCheckLink

    def _initData(self, window, data):
        super(Save_Move, self)._initData(window, data)
        Save_Move.local = bosh.saveInfos.localSave
        class _Default(EnabledLink):
            text = _(u'Default')
            def _enable(self): return Save_Move.local != u'Saves\\'
        self.extraItems = [_Default(_id=self.idList.DEFAULT)]

    def DoDefault(self,event):
        """Handle selection of Default."""
        self.MoveFiles(_(u'Default'))

    def DoList(self,event):
        """Handle selection of label."""
        profile = self.items[event.GetId()-self.idList.BASE]
        self.MoveFiles(profile)

    def MoveFiles(self,profile):
        fileInfos = self.window.data
        destDir = bosh.dirs['saveBase'].join(u'Saves')
        if profile != _(u'Default'):
            destDir = destDir.join(profile)
        if destDir == fileInfos.dir:
            balt.showError(self.window,_(u"You can't move saves to the current profile!"))
            return
        savesTable = bosh.saveInfos.table
        #--bashDir
        destTable = bolt.Table(bosh.PickleDict(destDir.join('Bash','Table.dat')))
        count = 0
        ask = True
        for fileName in self.selected:
            if ask and not self.window.data.moveIsSafe(fileName,destDir):
                message = (_(u'A file named %s already exists in %s. Overwrite it?')
                    % (fileName.s,profile))
                result = balt.askContinueShortTerm(self.window,message,_(u'Move File'))
                #if result is true just do the job but ask next time if applicable as well
                if not result: continue
                elif result == 2: ask = False #so don't warn for rest of operation
            if self.copyMode:
                bosh.saveInfos.copy(fileName,destDir)
            else:
                bosh.saveInfos.move(fileName,destDir,False)
            if fileName in savesTable:
                destTable[fileName] = savesTable.pop(fileName)
            count += 1
        destTable.save()
        Link.Frame.RefreshData()
        if self.copyMode:
            balt.showInfo(self.window,_(u'%d files copied to %s.') % (count,profile),_(u'Copy File'))

#------------------------------------------------------------------------------
class Save_RepairAbomb(OneItemLink):
    """Repairs animation slowing by resetting counter(?) at end of TesClass
    data."""
    text = _(u'Repair Abomb')
    help = _(u'Repair animation slowing')

    def Execute(self,event):
        #--File Info
        fileName = GPath(self.selected[0])
        fileInfo = self.window.data[fileName]
        #--Check current value
        saveFile = bosh.SaveFile(fileInfo)
        saveFile.load()
        (tcSize,abombCounter,abombFloat) = saveFile.getAbomb()
        #--Continue?
        progress = 100*abombFloat/struct.unpack('f',struct.pack('I',0x49000000))[0]
        newCounter = 0x41000000
        if abombCounter <= newCounter:
            balt.showOk(self.window,_(u'Abomb counter is too low to reset.'),_(u'Repair Abomb'))
            return
        message = (_(u"Reset Abomb counter? (Current progress: %.0f%%.)")
                   + u'\n\n' +
                   _(u"Note: Abomb animation slowing won't occur until progress is near 100%%.")
                   ) % progress
        if balt.askYes(self.window,message,_(u'Repair Abomb'),default=False):
            saveFile.setAbomb(newCounter)
            saveFile.safeSave()
            balt.showOk(self.window,_(u'Abomb counter reset.'),_(u'Repair Abomb'))

#------------------------------------------------------------------------------
## TODO: This is probably unneccessary now.  v105 was a long time ago
class Save_RepairFactions(EnabledLink): # CRUFT
    """Repair factions from v 105 Bash error, plus mod faction changes."""
    text = _(u'Repair Factions')
    help =_(u'Repair factions from v 105 Bash error, plus mod faction changes')

    def _enable(self):
        return bool(bosh.modInfos.ordered) and len(self.selected) == 1

    def Execute(self,event):
        debug = False
        message = (_(u'This will (mostly) repair faction membership errors due to Wrye Bash v 105 bug and/or faction changes in underlying mods.')
                   + u'\n\n' +
                   _(u'WARNING!  This repair is NOT perfect!  Do not use it unless you have to!')
                   )
        if not balt.askContinue(self.window,message,
                'bash.repairFactions.continue',_(u'Repair Factions')):
            return
        question = _(u"Restore dropped factions too?  WARNING:  This may involve clicking through a LOT of yes/no dialogs.")
        restoreDropped = balt.askYes(self.window, question, _(u'Repair Factions'),default=False)
        legitNullSpells = bush.repairFactions_legitNullSpells
        legitNullFactions = bush.repairFactions_legitNullFactions
        legitDroppedFactions = bush.repairFactions_legitDroppedFactions
        with balt.Progress(_(u'Repair Factions')) as progress:
            #--Loop over active mods
            log = bolt.LogFile(StringIO.StringIO())
            offsetFlag = 0x80
            npc_info = {}
            fact_eid = {}
            loadFactory = bosh.LoadFactory(False,bosh.MreRecord.type_class['NPC_'],
                                                 bosh.MreRecord.type_class['FACT'])
            ordered = list(bosh.modInfos.ordered)
            subProgress = SubProgress(progress,0,0.4,len(ordered))
            for index,modName in enumerate(ordered):
                subProgress(index,_(u'Scanning ') + modName.s)
                modInfo = bosh.modInfos[modName]
                modFile = bosh.ModFile(modInfo,loadFactory)
                modFile.load(True)
                #--Loop over mod NPCs
                mapToOrdered = bosh.MasterMap(modFile.tes4.masters+[modName], ordered)
                for npc in modFile.NPC_.getActiveRecords():
                    fid = mapToOrdered(npc.fid,None)
                    if not fid: continue
                    factions = []
                    for entry in npc.factions:
                        faction = mapToOrdered(entry.faction,None)
                        if not faction: continue
                        factions.append((faction,entry.rank))
                    npc_info[fid] = (npc.eid,factions)
                #--Loop over mod factions
                for fact in modFile.FACT.getActiveRecords():
                    fid = mapToOrdered(fact.fid,None)
                    if not fid: continue
                    fact_eid[fid] = fact.eid
            #--Loop over savefiles
            subProgress = SubProgress(progress,0.4,1.0,len(self.selected))
            message = _(u'NPC Factions Restored/UnNulled:')
            for index,saveName in enumerate(self.selected):
                log.setHeader(u'== '+saveName.s,True)
                subProgress(index,_(u'Updating ') + saveName.s)
                saveInfo = self.window.data[saveName]
                saveFile = bosh.SaveFile(saveInfo)
                saveFile.load()
                records = saveFile.records
                mapToOrdered = bosh.MasterMap(saveFile.masters, ordered)
                mapToSave = bosh.MasterMap(ordered,saveFile.masters)
                refactionedCount = unNulledCount = 0
                for recNum in xrange(len(records)):
                    unFactioned = unSpelled = unModified = refactioned = False
                    (recId,recType,recFlags,version,data) = records[recNum]
                    if recType != 35: continue
                    orderedRecId = mapToOrdered(recId,None)
                    eid = npc_info.get(orderedRecId,('',))[0]
                    npc = bosh.SreNPC(recFlags,data)
                    recFlags = bosh.SreNPC.flags(recFlags)
                    #--Fix Bash v 105 null array bugs
                    if recFlags.factions and not npc.factions and recId not in legitNullFactions:
                        log(u'. %08X %s -- ' % (recId,eid) + _(u'Factions'))
                        npc.factions = None
                        unFactioned = True
                    if recFlags.modifiers and not npc.modifiers:
                        log(u'. %08X %s -- ' % (recId,eid) + _(u'Modifiers'))
                        npc.modifiers = None
                        unModified = True
                    if recFlags.spells and not npc.spells and recId not in legitNullSpells:
                        log(u'. %08X %s -- ' % (recId,eid) + _(u'Spells'))
                        npc.spells = None
                        unSpelled = True
                    unNulled = (unFactioned or unSpelled or unModified)
                    unNulledCount += (0,1)[unNulled]
                    #--Player, player faction
                    if recId == 7:
                        playerStartSpell = saveFile.getIref(0x00000136)
                        if npc.spells is not None and playerStartSpell not in npc.spells:
                            log(u'. %08X %s -- **%s**' % (recId,eid._(u'DefaultPlayerSpell')))
                            npc.spells.append(playerStartSpell)
                            refactioned = True #--I'm lying, but... close enough.
                        playerFactionIref = saveFile.getIref(0x0001dbcd)
                        if (npc.factions is not None and
                            playerFactionIref not in [iref for iref,level in npc.factions]
                            ):
                                log(u'. %08X %s -- **%s**' % (recId,eid,_(u'PlayerFaction, 0')))
                                npc.factions.append((playerFactionIref,0))
                                refactioned = True
                    #--Compare to mod data
                    elif orderedRecId in npc_info and restoreDropped:
                        (npcEid,factions) = npc_info[orderedRecId]
                        #--Refaction?
                        if npc.factions and factions:
                            curFactions = set([iref for iref,level in npc.factions])
                            for orderedId,level in factions:
                                fid = mapToSave(orderedId,None)
                                if not fid: continue
                                iref = saveFile.getIref(fid)
                                if iref not in curFactions and (recId,fid) not in legitDroppedFactions:
                                    factEid = fact_eid.get(orderedId,'------')
                                    question = _(u'Restore %s to %s faction?') % (npcEid,factEid)
                                    deprint(_(u'refactioned') +u' %08X %08X %s %s' % (recId,fid,npcEid,factEid))
                                    if not balt.askYes(self.window, question, saveName.s,default=False):
                                        continue
                                    log(u'. %08X %s -- **%s, %d**' % (recId,eid,factEid,level))
                                    npc.factions.append((iref,level))
                                    refactioned = True
                    refactionedCount += (0,1)[refactioned]
                    #--Save record changes?
                    if unNulled or refactioned:
                        saveFile.records[recNum] = (recId,recType,npc.getFlags(),version,npc.getData())
                #--Save changes?
                subProgress(index+0.5,_(u'Updating ') + saveName.s)
                if unNulledCount or refactionedCount:
                    saveFile.safeSave()
                message += u'\n%d %d %s' % (refactionedCount,unNulledCount,saveName.s,)
        balt.showWryeLog(self.window,log.out.getvalue(),_(u'Repair Factions'),icons=Resources.bashBlue)
        log.out.close()

#------------------------------------------------------------------------------
class Save_RepairHair(OneItemLink):
    """Repairs hair that has been zeroed due to removal of a hair mod."""
    text = _(u'Repair Hair')
    help = _(u'Repair hair that has been zeroed due to removal of a hair mod.')

    def Execute(self,event):
        #--File Info
        fileName = GPath(self.selected[0])
        fileInfo = self.window.data[fileName]
        if bosh.PCFaces.save_repairHair(fileInfo):
            balt.showOk(self.window,_(u'Hair repaired.'))
        else:
            balt.showOk(self.window,_(u'No repair necessary.'),fileName.s)

#------------------------------------------------------------------------------
class Save_ReweighPotions(OneItemLink):
    """Changes weight of all player potions to specified value."""
    text = _(u'Reweigh Potions...')
    help = _(u'Change weight of all player potions to specified value')

    def Execute(self,event):
        #--Query value
        result = balt.askText(self.window,
            _(u"Set weight of all player potions to..."),
            _(u"Reweigh Potions"),
            u'%0.2f' % (bosh.settings.get('bash.reweighPotions.newWeight',0.2),))
        if not result: return
        try:
            newWeight = float(result.strip())
            if newWeight < 0 or newWeight > 100:
                raise Exception('')
        except:
            balt.showOk(self.window,_(u'Invalid weight: %s') % newWeight)
            return
        bosh.settings['bash.reweighPotions.newWeight'] = newWeight
        #--Do it
        fileName = GPath(self.selected[0])
        fileInfo = self.window.data[fileName]
        with balt.Progress(_(u"Reweigh Potions")) as progress:
            saveFile = bosh.SaveFile(fileInfo)
            saveFile.load(SubProgress(progress,0,0.5))
            count = 0
            progress(0.5,_(u"Processing."))
            for index,record in enumerate(saveFile.created):
                if record.recType == 'ALCH':
                    record = record.getTypeCopy()
                    record.weight = newWeight
                    record.getSize()
                    saveFile.created[index] = record
                    count += 1
            if count:
                saveFile.safeSave(SubProgress(progress,0.6,1.0))
                progress.Destroy()
                balt.showOk(self.window,_(u'Potions reweighed: %d.') % count,fileName.s)
            else:
                progress.Destroy()
                balt.showOk(self.window,_(u'No potions to reweigh!'),fileName.s)

#------------------------------------------------------------------------------
class Save_Stats(OneItemLink):
    """Show savefile statistics."""
    text = _(u'Statistics')
    help = _(u'Show savefile statistics')

    def Execute(self,event):
        fileName = GPath(self.selected[0])
        fileInfo = self.window.data[fileName]
        saveFile = bosh.SaveFile(fileInfo)
        with balt.Progress(_(u"Statistics")) as progress:
            saveFile.load(SubProgress(progress,0,0.9))
            log = bolt.LogFile(StringIO.StringIO())
            progress(0.9,_(u"Calculating statistics."))
            saveFile.logStats(log)
            progress.Destroy()
            text = log.out.getvalue()
            balt.showLog(self.window,text,fileName.s,asDialog=False,fixedFont=False,icons=Resources.bashBlue)

#------------------------------------------------------------------------------
class Save_StatObse(AppendableLink, EnabledLink):
    """Dump .obse records."""
    text = _(u'.%s Statistics') % bush.game.se.shortName.lower()
    help = _(u'Dump .%s records') % bush.game.se.shortName.lower()

    def _append(self, window): return bool(bush.game.se.shortName)

    def _enable(self):
        if len(self.selected) != 1: return False
        self.fileName = GPath(self.selected[0])
        self.fileInfo = self.window.data[self.fileName]
        fileName = self.fileInfo.getPath().root + u'.' + bush.game.se.shortName
        return fileName.exists()

    def Execute(self,event):
        saveFile = bosh.SaveFile(self.fileInfo)
        with balt.Progress(u'.'+bush.game.se.shortName) as progress:
            saveFile.load(SubProgress(progress,0,0.9))
            log = bolt.LogFile(StringIO.StringIO())
            progress(0.9,_(u"Calculating statistics."))
            saveFile.logStatObse(log)
        text = log.out.getvalue()
        log.out.close()
        balt.showLog(self.window, text, self.fileName.s, asDialog=False,
                     fixedFont=False, icons=Resources.bashBlue)

#------------------------------------------------------------------------------
class Save_Unbloat(OneItemLink):
    """Unbloats savegame."""
    text = _(u'Remove Bloat...')
    help = _(u'Unbloat savegame. Experimental ! Back up your saves before'
             u' using it on them')

    def Execute(self,event):
        #--File Info
        saveName = GPath(self.selected[0])
        saveInfo = self.window.data[saveName]
        delObjRefs = 0
        with balt.Progress(_(u'Scanning for Bloat')) as progress:
            #--Scan and report
            saveFile = bosh.SaveFile(saveInfo)
            saveFile.load(SubProgress(progress,0,0.8))
            createdCounts,nullRefCount = saveFile.findBloating(SubProgress(progress,0.8,1.0))
        #--Dialog
        if not createdCounts and not nullRefCount:
            balt.showOk(self.window,_(u'No bloating found.'),saveName.s)
            return
        message = u''
        if createdCounts:
            for type,name in sorted(createdCounts):
                message += u'  %s %s: %s\n' % (type,name,formatInteger(createdCounts[(type,name)]))
        if nullRefCount:
            message += u'  '+_(u'Null Ref Objects:')+ u' %s\n' % formatInteger(nullRefCount)
        message = (_(u'Remove savegame bloating?')
                   + u'\n'+message+u'\n' +
                   _(u'WARNING: This is a risky procedure that may corrupt your savegame!  Use only if necessary!')
                   )
        if not balt.askYes(self.window,message,_(u'Remove bloating?')):
            return
        #--Remove bloating
        with balt.Progress(_(u'Removing Bloat')) as progress:
            nums = saveFile.removeBloating(createdCounts.keys(),True,SubProgress(progress,0,0.9))
            progress(0.9,_(u'Saving...'))
            saveFile.safeSave()
        balt.showOk(self.window,
            (_(u'Uncreated Objects: %d')
             + u'\n' +
             _(u'Uncreated Refs: %d')
             + u'\n' +
             _(u'UnNulled Refs: %d')
             ) % nums,
            saveName.s)
        self.window.RefreshUI(saveName)

#------------------------------------------------------------------------------
class Save_UpdateNPCLevels(EnabledLink):
    """Update NPC levels from active mods."""
    text = _(u'Update NPC Levels...')
    help = _(u'Update NPC levels from active mods')

    def _enable(self): return bool(self.selected and bosh.modInfos.ordered)

    def Execute(self,event):
        debug = True
        message = _(u'This will relevel the NPCs in the selected save game(s) according to the npc levels in the currently active mods.  This supersedes the older "Import NPC Levels" command.')
        if not balt.askContinue(self.window,message,'bash.updateNpcLevels.continue',_(u'Update NPC Levels')):
            return
        with balt.Progress(_(u'Update NPC Levels')) as progress:
            #--Loop over active mods
            offsetFlag = 0x80
            npc_info = {}
            loadFactory = bosh.LoadFactory(False,bosh.MreRecord.type_class['NPC_'])
            ordered = list(bosh.modInfos.ordered)
            subProgress = SubProgress(progress,0,0.4,len(ordered))
            modErrors = []
            for index,modName in enumerate(ordered):
                subProgress(index,_(u'Scanning ') + modName.s)
                modInfo = bosh.modInfos[modName]
                modFile = bosh.ModFile(modInfo,loadFactory)
                try:
                    modFile.load(True)
                except bosh.ModError, x:
                    modErrors.append(u'%s'%x)
                    continue
                if 'NPC_' not in modFile.tops: continue
                #--Loop over mod NPCs
                mapToOrdered = bosh.MasterMap(modFile.tes4.masters+[modName], ordered)
                for npc in modFile.NPC_.getActiveRecords():
                    fid = mapToOrdered(npc.fid,None)
                    if not fid: continue
                    npc_info[fid] = (npc.eid, npc.level, npc.calcMin, npc.calcMax, npc.flags.pcLevelOffset)
            #--Loop over savefiles
            subProgress = SubProgress(progress,0.4,1.0,len(self.selected))
            message = _(u'NPCs Releveled:')
            for index,saveName in enumerate(self.selected):
                subProgress(index,_(u'Updating ') + saveName.s)
                saveInfo = self.window.data[saveName]
                saveFile = bosh.SaveFile(saveInfo)
                saveFile.load()
                records = saveFile.records
                mapToOrdered = bosh.MasterMap(saveFile.masters, ordered)
                releveledCount = 0
                #--Loop over change records
                for recNum in xrange(len(records)):
                    releveled = False
                    (recId,recType,recFlags,version,data) = records[recNum]
                    orderedRecId = mapToOrdered(recId,None)
                    if recType != 35 or recId == 7 or orderedRecId not in npc_info: continue
                    (eid,level,calcMin,calcMax,pcLevelOffset) = npc_info[orderedRecId]
                    npc = bosh.SreNPC(recFlags,data)
                    acbs = npc.acbs
                    if acbs and (
                        (acbs.level != level) or
                        (acbs.calcMin != calcMin) or
                        (acbs.calcMax != calcMax) or
                        (acbs.flags.pcLevelOffset != pcLevelOffset)
                        ):
                        acbs.flags.pcLevelOffset = pcLevelOffset
                        acbs.level = level
                        acbs.calcMin = calcMin
                        acbs.calcMax = calcMax
                        (recId,recType,recFlags,version,data) = saveFile.records[recNum]
                        records[recNum] = (recId,recType,npc.getFlags(),version,npc.getData())
                        releveledCount += 1
                        saveFile.records[recNum] = npc.getTuple(recId,version)
                #--Save changes?
                subProgress(index+0.5,_(u'Updating ') + saveName.s)
                if releveledCount:
                    saveFile.safeSave()
                message += u'\n%d %s' % (releveledCount,saveName.s)
        if modErrors:
            message += u'\n\n'+_(u'Some mods had load errors and were skipped:')+u'\n* '
            message += u'\n* '.join(modErrors)
        balt.showOk(self.window,message,_(u'Update NPC Levels'))
