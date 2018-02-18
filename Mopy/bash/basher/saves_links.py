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

"""Menu items for the main and item menus of the saves tab - their window
attribute points to BashFrame.saveList singleton."""

import StringIO
import re
import shutil
from . import BashFrame
from .dialogs import ImportFaceDialog
from .. import bass, bosh, bolt, balt, bush, parsers, load_order
from ..balt import EnabledLink, AppendableLink, Link, CheckLink, ChoiceLink, \
    ItemLink, SeparatorLink, OneItemLink, Image, UIList_Rename
from ..bolt import GPath, SubProgress, formatInteger, struct_pack, struct_unpack
from ..bosh import faces
from ..exception import ArgumentError, BoltError, CancelError, ModError

__all__ = ['Saves_Profiles', 'Save_Rename', 'Save_Renumber', 'Save_Move',
           'Save_LoadMasters', 'Save_DiffMasters', 'Save_Stats',
           'Save_StatObse', 'Save_EditPCSpells', 'Save_RenamePlayer',
           'Save_EditCreatedEnchantmentCosts', 'Save_ImportFace',
           'Save_EditCreated', 'Save_ReweighPotions', 'Save_UpdateNPCLevels',
           'Save_ExportScreenshot', 'Save_Unbloat', 'Save_RepairAbomb',
           'Save_RepairHair']

#------------------------------------------------------------------------------
# Saves Links -----------------------------------------------------------------
#------------------------------------------------------------------------------
class Saves_ProfilesData(balt.ListEditorData):
    """Data capsule for save profiles editing dialog."""
    def __init__(self,parent):
        """Initialize."""
        self.baseSaves = bass.dirs['saveBase'].join(u'Saves')
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
        newName = balt.askText(self.parent, _(u"Enter profile name:"))
        if not newName: return False
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
        oldDir, newDir = (self.baseSaves.join(subdir) for subdir in
                          (oldName, newName))
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
        profileDir = bass.dirs['saveBase'].join(profileSaves)
        files = [save for save in profileDir.list() if
                 bosh.SaveInfos.rightFileType(save)]
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

    @property
    def _choices(self): return [x.s for x in bosh.saveInfos.getLocalSaveDirs()]

    class _ProfileLink(CheckLink, EnabledLink):
        @property
        def help(self):
            return _(u'Set profile to %(prof)s (My Games/Saves/%(prof)s)') % {
                               'prof': self._text}
        @property
        def relativePath(self): return u'Saves\\' + self._text + u'\\'
        def _check(self): return Saves_Profiles.local == self.relativePath
        def _enable(self): return not self._check()
        def Execute(self):
            arcSaves = bosh.saveInfos.localSave
            newSaves = self.relativePath
            with balt.BusyCursor():
                bosh.saveInfos.setLocalSave(newSaves, refreshSaveInfos=False)
                bosh.modInfos.swapPluginsAndMasterVersion(arcSaves, newSaves)
                Link.Frame.SetTitle()
                bosh.saveInfos.refresh()
                self.window.DeleteAll() # let call below repopulate
                self.window.RefreshUI(detail_item=None)
                self.window.panel.ShowPanel()
                Link.Frame.warn_corrupted(warn_mods=False, warn_strings=False)

    choiceLinkType = _ProfileLink

    class _Default(_ProfileLink):
        _text = _(u'Default')
        @property
        def help(self):
            return _(u'Set profile to the default (My Games/Saves)')
        @property
        def relativePath(self): return u'Saves\\'

    class _Edit(ItemLink):
        _text = _(u"Edit Profiles...")
        help = _(u'Show save profiles editing dialog')

        def Execute(self):
            """Show save profiles editing dialog."""
            data = Saves_ProfilesData(self.window)
            balt.ListEditor.Display(self.window, _(u'Save Profiles'), data)

    extraItems = [_Edit(), SeparatorLink(), _Default()]

    def _initData(self, window, selection):
        super(Saves_Profiles, self)._initData(window, selection)
        Saves_Profiles.local = bosh.saveInfos.localSave

#------------------------------------------------------------------------------
class Save_LoadMasters(OneItemLink):
    """Sets the active mods to the save game's masters."""
    _text = _(u'Load Masters')
    help = _(u"Set the active mods to the save game's masters")

    def Execute(self):
        errorMessage = bosh.modInfos.lo_activate_exact(
            self._selected_info.masterNames)
        BashFrame.modList.RefreshUI(refreshSaves=True, focus_list=False)
        self.window.Focus()
        if errorMessage: self._showError(errorMessage, self._selected_item.s)

#------------------------------------------------------------------------------
class Save_ImportFace(OneItemLink):
    """Imports a face from another save."""
    _text = _(u'Import Face...')
    help = _(u'Import a face from another save')

    @balt.conversation
    def Execute(self):
        #--Select source face file
        srcDir = self._selected_info.dir
        exts = u';*'.join(bush.game.espm_extensions | {
            bush.game.ess.ext, bush.game.ess.ext[-1] + u'r'})
        wildcard = _(u'%s Files') % bush.game.displayName + \
                   u' (*' + exts + u')|*' + exts
        #--File dialog
        srcPath = self._askOpen(title=_(u'Face Source:'), defaultDir=srcDir,
                                wildcard=wildcard, mustExist=True)
        if not srcPath: return
        if bosh.SaveInfos.rightFileType(srcPath):
            self.FromSave(self._selected_info, srcPath)
        elif bosh.ModInfos.rightFileType(srcPath):
            self.FromMod(self._selected_info, srcPath)

    def FromSave(self,fileInfo,srcPath):
        """Import from a save."""
        #--Get face
        srcInfo = bosh.SaveInfo(srcPath)
        with balt.Progress(srcPath.tail.s) as progress:
            saveFile = bosh._saves.SaveFile(srcInfo)
            saveFile.load(progress)
        srcFaces = bosh.faces.PCFaces.save_getFaces(saveFile)
        #--Dialog
        ImportFaceDialog.Display(self.window,srcPath.tail.s,fileInfo,srcFaces)

    def FromMod(self,fileInfo,srcPath):
        """Import from a mod."""
        #--Get faces
        srcInfo = bosh.ModInfo(srcPath)
        srcFaces = bosh.faces.PCFaces.mod_getFaces(srcInfo)
        #--No faces to import?
        mod = srcPath.tail.s
        if not srcFaces:
            self._showOk(_(u'No player (PC) faces found in %s.') % mod, mod)
            return
        #--Dialog
        ImportFaceDialog.Display(self.window, mod, fileInfo, srcFaces)

#------------------------------------------------------------------------------
class Save_RenamePlayer(ItemLink):
    """Renames the Player character in a save game."""
    _text = _(u'Rename Player...')
    help = _(u'Rename the Player character in a save game')

    def Execute(self):
        # get new player name - must not be empty
        saveInfo = bosh.saveInfos[self.selected[0]]
        newName = self._askText(
            _(u"Enter new player name. E.g. Conan the Bold"),
            title=_(u"Rename player"), default=saveInfo.header.pcName)
        if not newName: return
        for save in self.iselected_infos():
            savedPlayer = bosh._saves.Save_NPCEdits(save)
            savedPlayer.renamePlayer(newName)
        bosh.saveInfos.refresh()
        self.window.RefreshUI(redraw=self.selected)

#------------------------------------------------------------------------------
class Save_ExportScreenshot(OneItemLink):
    """Exports the saved screenshot from a save game."""
    _text = _(u'Export Screenshot...')
    help = _(u'Export the saved screenshot from a save game')

    def Execute(self):
        imagePath = balt.askSave(Link.Frame, _(u'Save Screenshot as:'),
            bass.dirs['patches'].s,
            _(u'Screenshot %s.jpg') % self._selected_item.s, u'*.jpg')
        if not imagePath: return
        width, height, image_data = self._selected_info.header.image
        image = Image.GetImage(image_data, height, width)
        image.SaveFile(imagePath.s, Image.typesDict['jpg'])

#------------------------------------------------------------------------------
class Save_DiffMasters(EnabledLink):
    """Shows how saves masters differ from active mod list."""
    _text = _(u'Diff Masters...')
    help = _(u"Show how the masters of a save differ from active mod list or"
             u" another save")

    def _enable(self): return len(self.selected) in (1,2)

    def Execute(self):
        oldNew = self.selected
        oldNew.sort(key = lambda x: bosh.saveInfos[x].mtime)
        oldName = oldNew[0]
        oldInfo = self.window.data_store[oldName]
        oldMasters = set(oldInfo.masterNames)
        if len(self.selected) == 1:
            newName = GPath(_(u'Active Masters'))
            newMasters = set(load_order.cached_active_tuple())
        else:
            newName = oldNew[1]
            newInfo = self.window.data_store[newName]
            newMasters = set(newInfo.masterNames)
        missing = oldMasters - newMasters
        added = newMasters - oldMasters
        if not missing and not added:
            message = _(u'Masters are the same.')
            self._showInfo(message, title=_(u'Diff Masters'))
        else:
            message = u''
            if missing:
                message += u'=== '+_(u'Removed Masters')+u' (%s):\n* ' % oldName.s
                message += u'\n* '.join(x.s for x in load_order.get_ordered(missing))
                if added: message += u'\n\n'
            if added:
                message += u'=== '+_(u'Added Masters')+u' (%s):\n* ' % newName.s
                message += u'\n* '.join(x.s for x in load_order.get_ordered(added))
            self._showWryeLog(message, title=_(u'Diff Masters'))

#------------------------------------------------------------------------------
class Save_Rename(UIList_Rename):
    """Renames Save File."""
    help = _(u'Rename Save File')

#------------------------------------------------------------------------------
class Save_Renumber(EnabledLink):
    """Renumbers a whole lot of save files."""
    _text = _(u'Re-number Save(s)...')
    help = _(u'Renumber a whole lot of save files') + u'.  ' + _(
        u'Savename must be "Save <some number><optional text>"')
    _re_numbered_save = re.compile(ur'^(save )(\d*)(.*)', re.I | re.U)

    def _enable(self):
        self._matches = []
        for save_path in self.selected:
            save_match = self._re_numbered_save.match(save_path.s)
            if save_match: self._matches.append((save_path, save_match))
        return bool(self._matches)

    def Execute(self):
        newNumber = self._askNumber(
            _(u"Enter new number to start numbering the selected saves at."),
            prompt=_(u'Save Number'), title=_(u'Re-number Saves'), value=1,
            min=1, max=10000)
        if not newNumber: return
        to_select = []
        for name, maPattern in self._matches:
            maPattern = maPattern.groups()
            if not maPattern[1]: continue
            newFileName = u"%s%d%s" % (maPattern[0],newNumber,maPattern[2])
            if newFileName != name.s:
                new_file_path = GPath(newFileName)
                try:
                    bosh.saveInfos.rename_info(name, new_file_path)
                except (CancelError, OSError, IOError):
                    break
                newNumber += 1
                to_select.append(new_file_path)
        if to_select:
            self.window.RefreshUI()
            self.window.SelectItemsNoCallback(to_select)

#------------------------------------------------------------------------------
class Save_EditCreatedData(balt.ListEditorData):
    """Data capsule for custom item editing dialog."""
    def __init__(self, parent, saveFile, types_set):
        self.changed = False
        self.saveFile = saveFile
        name_nameRecords = self.name_nameRecords = {}
        self.enchantments = {}
        #--Parse records and get into name_nameRecords
        for index,record in enumerate(saveFile.created):
            if record.recType == 'ENCH':
                self.enchantments[record.fid] = record.getTypeCopy()
            elif record.recType in types_set:
                record = record.getTypeCopy()
                if not record.full: continue
                record.getSize() #--Since type copy makes it changed.
                saveFile.created[index] = record
                record_full = record.full
                if record_full not in name_nameRecords:
                    name_nameRecords[record_full] = (record_full, [])
                name_nameRecords[record_full][1].append(record)
        #--GUI
        balt.ListEditorData.__init__(self,parent)
        self.showRename = True
        self.showInfo = True
        self.showSave = True
        self.showCancel = True

    def getItemList(self):
        """Returns load list keys in alpha order."""
        items = sorted(self.name_nameRecords.keys())
        items.sort(key=lambda x: self.name_nameRecords[x][1][0].recType)
        return items

    def getInfo(self,item):
        """Returns string info on specified item."""
        buff = StringIO.StringIO()
        name,records = self.name_nameRecords[item]
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
        elif newName in self.name_nameRecords:
            balt.showError(self.parent,_(u'Name is already used.'))
            return False
        #--Rename
        self.name_nameRecords[newName] = self.name_nameRecords.pop(oldName)
        self.changed = True
        return newName

    def save(self):
        """Handles save button."""
        if not self.changed:
            balt.showOk(self.parent,_(u'No changes made.'))
        else:
            self.changed = False #--Allows graceful effort if close fails.
            count = 0
            for newName,(oldName,records) in self.name_nameRecords.items():
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
    rec_types = {'ENCH': {'ARMO', 'CLOT', 'WEAP'}, 'SPEL': {'SPEL'},
                 'ALCH': {'ALCH'}}
    help = _(u'Allow user to rename custom items (spells, enchantments, etc)')

    def __init__(self, save_rec_type):
        if save_rec_type not in Save_EditCreated.menuNames:
            raise ArgumentError
        super(Save_EditCreated, self).__init__()
        self.save_rec_type = save_rec_type
        self._text = Save_EditCreated.menuNames[self.save_rec_type]

    def Execute(self):
        #--Get SaveFile
        with balt.Progress(_(u"Loading...")) as progress:
            saveFile = bosh._saves.SaveFile(self._selected_info)
            saveFile.load(progress)
        #--No custom items?
        types_set = Save_EditCreated.rec_types[self.save_rec_type]
        records = [rec for rec in saveFile.created if rec.recType in types_set]
        if not records:
            self._showOk(_(u'No items to edit.'))
            return
        #--Open editor dialog
        data = Save_EditCreatedData(self.window,saveFile,types_set)
        balt.ListEditor.Display(self.window, self._text, data)

#------------------------------------------------------------------------------
class Save_EditPCSpellsData(balt.ListEditorData):
    """Data capsule for pc spell editing dialog."""
    def __init__(self,parent,saveInfo):
        """Initialize."""
        self.saveSpells = bosh._saves.SaveSpells(saveInfo)
        with balt.Progress(_(u'Loading Masters')) as progress:
            self.saveSpells.load(bosh.modInfos, progress)
        self.player_spells = self.saveSpells.getPlayerSpells()
        self.removed = set()
        #--GUI
        balt.ListEditorData.__init__(self,parent)
        self.showRemove = True
        self.showInfo = True
        self.showSave = True
        self.showCancel = True

    def getItemList(self):
        """Returns load list keys in alpha order."""
        return sorted(self.player_spells.keys(), key=lambda a: a.lower())

    def getInfo(self,item):
        """Returns string info on specified item."""
        iref,record = self.player_spells[item]
        return record.getEffectsSummary()

    def remove(self,item):
        """Removes item. Return true on success."""
        if not item in self.player_spells: return False
        iref,record = self.player_spells[item]
        self.removed.add(iref)
        del self.player_spells[item]
        return True

    def save(self):
        """Handles save button click."""
        self.saveSpells.removePlayerSpells(self.removed)

#------------------------------------------------------------------------------
class Save_EditPCSpells(OneItemLink):
    """Save spell list editing dialog."""
    _text = _(u'Delete Spells...')
    help = _(u'Delete unused spells from your spell list in the selected save.'
             u' Warning: This cannot be undone')

    def Execute(self):
        pc_spell_data = Save_EditPCSpellsData(self.window, self._selected_info)
        balt.ListEditor.Display(self.window, _(u'Player Spells'),pc_spell_data)

#------------------------------------------------------------------------------
class Save_EditCreatedEnchantmentCosts(OneItemLink):
    """Dialogue and Menu for setting number of uses for Cast When Used Enchantments."""
    _text = _(u'Set Number of Uses for Weapon Enchantments...')
    help = _(u'Set number of uses for Cast When Used Enchantments')

    def Execute(self):
        dialog = self._askNumber(
            _(u'Enter the number of uses you desire per recharge for all '
              u'custom made enchantments.') + u'\n' + _(
                u'(Enter 0 for unlimited uses)'), prompt=_(u'Uses'),
            title=_(u'Number of Uses'), value=50, min=0, max=10000)
        if not dialog: return
        Enchantments = bosh._saves.SaveEnchantments(self._selected_info)
        Enchantments.load()
        Enchantments.setCastWhenUsedEnchantmentNumberOfUses(dialog)

#------------------------------------------------------------------------------
class Save_Move(ChoiceLink):
    """Moves or copies selected files to alternate profile."""
    local = None

    def __init__(self, copyMode=False):
        super(Save_Move, self).__init__()
        self.copyMode = copyMode

    @property
    def _choices(self): return [x.s for x in bosh.saveInfos.getLocalSaveDirs()]

    def _initData(self, window, selection):
        super(Save_Move, self)._initData(window, selection)
        Save_Move.local = bosh.saveInfos.localSave
        _self = self
        class _Default(EnabledLink):
            _text = _(u'Default')
            def _enable(self): return Save_Move.local != u'Saves\\'
            def Execute(self): _self.MoveFiles(_(u'Default'))
        class _SaveProfileLink(EnabledLink):
            def _enable(self):
                return Save_Move.local != (u'Saves\\' + self._text + u'\\')
            def Execute(self): _self.MoveFiles(self._text)
        self.__class__.choiceLinkType = _SaveProfileLink
        self.extraItems = [_Default()]

    def MoveFiles(self,profile):
        destDir = bass.dirs['saveBase'].join(u'Saves')
        if profile != _(u'Default'):
            destDir = destDir.join(profile)
        if destDir == bosh.saveInfos.store_dir:
            self._showError(_(u"You can't move saves to the current profile!"))
            return
        try:
            count = self._move_saves(destDir, profile)
        finally:
            if not self.copyMode: # files moved to other profile, refresh
                moved = bosh.saveInfos.delete_refresh(self.selected, None,
                                                      check_existence=True)
                self.window.RefreshUI(to_del=moved)
        msg = (_(u'%d files copied to %s.') if self.copyMode else _(
            u'%d files moved to %s.')) % (count, profile)
        self._showInfo(msg, title=_(u'Copy File'))

    def _move_saves(self, destDir, profile):
        savesTable = bosh.saveInfos.table
        #--bashDir
        destTable = bolt.Table(bolt.PickleDict(destDir.join('Bash','Table.dat')))
        count = 0
        ask = True
        for fileName in self.selected:
            if ask and destDir.join(fileName).exists():
                message = (_(u'A file named %s already exists in %s. Overwrite it?')
                    % (fileName.s,profile))
                result = self._askContinueShortTerm(message,
                                                    title=_(u'Move File'))
                #if result is true just do the job but ask next time if applicable as well
                if not result: continue
                elif result == 2: ask = False #so don't warn for rest of operation
            if self.copyMode:
                bosh.saveInfos.copy_info(fileName, destDir)
                if fileName in savesTable:
                    destTable[fileName] = savesTable[fileName]
            else:
                bosh.saveInfos.move_info(fileName, destDir)
                if fileName in savesTable:
                    destTable[fileName] = savesTable.pop(fileName)
            count += 1
        destTable.save()
        return count

#------------------------------------------------------------------------------
class Save_RepairAbomb(OneItemLink):
    """Repairs animation slowing by resetting counter(?) at end of TesClass
    data."""
    _text = _(u'Repair Abomb')
    help = _(u'Repair animation slowing')

    def Execute(self):
        #--File Info
        fileInfo = self._selected_info
        #--Check current value
        saveFile = bosh._saves.SaveFile(fileInfo)
        saveFile.load()
        (tcSize,abombCounter,abombFloat) = saveFile.getAbomb()
        #--Continue?
        progress = 100*abombFloat/struct_unpack('f', struct_pack('I',0x49000000))[0]
        newCounter = 0x41000000
        if abombCounter <= newCounter:
            self._showOk(_(u'Abomb counter is too low to reset.'))
            return
        message = (_(u"Reset Abomb counter? (Current progress: %.0f%%.)")
                   + u'\n\n' +
                   _(u"Note: Abomb animation slowing won't occur until progress is near 100%%.")
                   ) % progress
        if self._askYes(message, _(u'Repair Abomb'), default=False):
            saveFile.setAbomb(newCounter)
            saveFile.safeSave()
            self._showOk(_(u'Abomb counter reset.'))

#------------------------------------------------------------------------------
class Save_RepairHair(OneItemLink):
    """Repairs hair that has been zeroed due to removal of a hair mod."""
    _text = _(u'Repair Hair')
    help = _(u'Repair hair that has been zeroed due to removal of a hair mod.')

    def Execute(self):
        #--File Info
        if bosh.faces.PCFaces.save_repairHair(self._selected_info):
            self._showOk(_(u'Hair repaired.'))
        else:
            self._showOk(_(u'No repair necessary.'), self._selected_item.s)

#------------------------------------------------------------------------------
class Save_ReweighPotions(OneItemLink):
    """Changes weight of all player potions to specified value."""
    _text = _(u'Reweigh Potions...')
    help = _(u'Change weight of all player potions to specified value')

    def Execute(self):
        #--Query value
        default = u'%0.2f' % (bass.settings.get(
            'bash.reweighPotions.newWeight', 0.2),)
        newWeight = self._askText(_(u"Set weight of all player potions to..."),
                                  title=_(u"Reweigh Potions"), default=default)
        if not newWeight: return
        try:
            newWeight = float(newWeight)
            if newWeight < 0 or newWeight > 100: raise ValueError
        except ValueError:
            self._showOk(_(u'Invalid weight: %s') % newWeight)
            return
        bass.settings['bash.reweighPotions.newWeight'] = newWeight
        #--Do it
        with balt.Progress(_(u"Reweigh Potions")) as progress:
            saveFile = bosh._saves.SaveFile(self._selected_info)
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
                self._showOk(_(u'Potions reweighed: %d.') % count,
                             self._selected_item.s)
            else:
                progress.Destroy()
                self._showOk(_(u'No potions to reweigh!'),
                             self._selected_item.s)

#------------------------------------------------------------------------------
class Save_Stats(OneItemLink):
    """Show savefile statistics."""
    _text = _(u'Statistics')
    help = _(u'Show savefile statistics')

    def Execute(self):
        saveFile = bosh._saves.SaveFile(self._selected_info)
        with balt.Progress(_(u"Statistics")) as progress:
            saveFile.load(SubProgress(progress,0,0.9))
            log = bolt.LogFile(StringIO.StringIO())
            progress(0.9,_(u"Calculating statistics."))
            saveFile.logStats(log)
            progress.Destroy()
            text = log.out.getvalue()
            self._showLog(text, title=self._selected_item.s, fixedFont=False)

#------------------------------------------------------------------------------
class Save_StatObse(AppendableLink, OneItemLink):
    """Dump .obse records."""
    _text = _(u'.%s Statistics') % bush.game.se.shortName.lower()
    help = _(u'Dump .%s records') % bush.game.se.shortName.lower()

    def _append(self, window): return bool(bush.game.se.shortName)

    def _enable(self):
        if not super(Save_StatObse, self)._enable(): return False
        cosave = self._selected_info.get_se_cosave_path()
        return cosave.exists()

    def Execute(self):
        with balt.BusyCursor():
            log = bolt.LogFile(StringIO.StringIO())
            cosave = self._selected_info.get_cosave()
            if cosave is not None:
                cosave.logStatObse(log, self._selected_info.header.masters)
        text = log.out.getvalue()
        log.out.close()
        self._showLog(text, title=self._selected_item.s, fixedFont=False)

#------------------------------------------------------------------------------
class Save_Unbloat(OneItemLink):
    """Unbloats savegame."""
    _text = _(u'Remove Bloat...')
    help = _(u'Unbloat savegame. Experimental ! Back up your saves before'
             u' using it on them')

    def Execute(self):
        #--File Info
        with balt.Progress(_(u'Scanning for Bloat')) as progress:
            #--Scan and report
            saveFile = bosh._saves.SaveFile(self._selected_info)
            saveFile.load(SubProgress(progress,0,0.8))
            createdCounts,nullRefCount = saveFile.findBloating(SubProgress(progress,0.8,1.0))
        #--Dialog
        if not createdCounts and not nullRefCount:
            self._showOk(_(u'No bloating found.'), self._selected_item.s)
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
        if not self._askYes(message, _(u'Remove bloating?')): return
        #--Remove bloating
        with balt.Progress(_(u'Removing Bloat')) as progress:
            nums = saveFile.removeBloating(createdCounts.keys(),True,SubProgress(progress,0,0.9))
            progress(0.9,_(u'Saving...'))
            saveFile.safeSave()
        self._showOk((_(u'Uncreated Objects: %d') + u'\n' +
                      _(u'Uncreated Refs: %d') + u'\n' +
                      _(u'UnNulled Refs: %d')) % nums, self._selected_item.s)
        self.window.RefreshUI(redraw=[self._selected_item])

#------------------------------------------------------------------------------
class Save_UpdateNPCLevels(EnabledLink):
    """Update NPC levels from active mods."""
    _text = _(u'Update NPC Levels...')
    help = _(u'Update NPC levels from active mods')

    def _enable(self): return bool(load_order.cached_active_tuple())

    def Execute(self):
        message = _(u'This will relevel the NPCs in the selected save game(s) according to the npc levels in the currently active mods.  This supersedes the older "Import NPC Levels" command.')
        if not self._askContinue(message, 'bash.updateNpcLevels.continue',
                                 _(u'Update NPC Levels')): return
        with balt.Progress(_(u'Update NPC Levels')) as progress:
            #--Loop over active mods
            npc_info = {}
            loadFactory = parsers.LoadFactory(
                    False, bosh.MreRecord.type_class['NPC_'])
            ordered = list(load_order.cached_active_tuple())
            subProgress = SubProgress(progress,0,0.4,len(ordered))
            modErrors = []
            for index,modName in enumerate(ordered):
                subProgress(index,_(u'Scanning ') + modName.s)
                modInfo = bosh.modInfos[modName]
                modFile = parsers.ModFile(modInfo, loadFactory)
                try:
                    modFile.load(True)
                except ModError as x:
                    modErrors.append(u'%s'%x)
                    continue
                if 'NPC_' not in modFile.tops: continue
                #--Loop over mod NPCs
                mapToOrdered = parsers.MasterMap(modFile.tes4.masters + [modName], ordered)
                for npc in modFile.NPC_.getActiveRecords():
                    fid = mapToOrdered(npc.fid,None)
                    if not fid: continue
                    npc_info[fid] = (npc.eid, npc.level, npc.calcMin, npc.calcMax, npc.flags.pcLevelOffset)
            #--Loop over savefiles
            subProgress = SubProgress(progress,0.4,1.0,len(self.selected))
            message = _(u'NPCs Releveled:')
            for index,(saveName,saveInfo) in enumerate(self.iselected_pairs()):
                subProgress(index,_(u'Updating ') + saveName.s)
                saveFile = bosh._saves.SaveFile(saveInfo)
                saveFile.load()
                records = saveFile.records
                mapToOrdered = parsers.MasterMap(saveFile.masters, ordered)
                releveledCount = 0
                #--Loop over change records
                for recNum in xrange(len(records)):
                    (recId,recType,recFlags,version,data) = records[recNum]
                    orderedRecId = mapToOrdered(recId,None)
                    if recType != 35 or recId == 7 or orderedRecId not in npc_info: continue
                    (eid,level,calcMin,calcMax,pcLevelOffset) = npc_info[orderedRecId]
                    npc = bosh._saves.SreNPC(recFlags, data)
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
        self._showOk(message, _(u'Update NPC Levels'))
