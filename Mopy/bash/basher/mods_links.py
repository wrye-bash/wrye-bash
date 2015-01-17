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
from . import Resources
from .dialogs import ListBoxes
from .. import bosh, balt
from .. import bush # for Mods_LoadListData, Mods_LoadList
from ..balt import ItemLink, CheckLink, BoolLink, EnabledLink, ChoiceLink, \
    SeparatorLink, Link
from ..bolt import GPath
from ..patcher.patch_files import PatchFile

__all__ = ['Mods_EsmsFirst', 'Mods_LoadList', 'Mods_SelectedFirst',
           'Mods_OblivionVersion', 'Mods_CreateBlankBashedPatch',
           'Mods_CreateBlank', 'Mods_ListMods', 'Mods_ListBashTags',
           'Mods_CleanDummyMasters', 'Mods_AutoGhost', 'Mods_LockTimes',
           'Mods_ScanDirty']

modList = None

# "Load" submenu --------------------------------------------------------------
class _Mods_LoadListData(balt.ListEditorData):
    """Data capsule for load list editing dialog."""
    def __init__(self,parent):
        """Initialize."""
        self.data = bosh.settings['bash.loadLists.data']
        self.data['Bethesda ESMs'] = [
            GPath(x) for x in bush.game.bethDataFiles
            if x.endswith(u'.esm')
            ]
        #--GUI
        balt.ListEditorData.__init__(self,parent)
        self.showRename = True
        self.showRemove = True

    def getItemList(self):
        """Returns load list keys in alpha order."""
        return sorted(self.data.keys(),key=lambda a: a.lower())

    def rename(self,oldName,newName):
        """Renames oldName to newName."""
        #--Right length?
        if len(newName) == 0 or len(newName) > 64:
            balt.showError(self.parent,
                _(u'Name must be between 1 and 64 characters long.'))
            return False
        #--Rename
        bosh.settings.setChanged('bash.loadLists.data')
        self.data[newName] = self.data[oldName]
        del self.data[oldName]
        return newName

    def remove(self,item):
        """Removes load list."""
        bosh.settings.setChanged('bash.loadLists.data')
        del self.data[item]
        return True

class Mods_LoadList(ChoiceLink):
    """Add load list links."""
    idList = balt.IdList(10000, 90,'SAVE','EDIT','NONE','ALL') # was ID_LOADERS

    def __init__(self):
        super(Mods_LoadList, self).__init__()
        self.loadListsDict = bosh.settings['bash.loadLists.data']
        self.loadListsDict['Bethesda ESMs'] = [
            GPath(x) for x in bush.game.bethDataFiles
            if x.endswith(u'.esm')
            ]
        class _SaveLink(EnabledLink):
            id, text = self.idList.SAVE, _(u'Save List...') # notice self
            def _enable(self): return bool(bosh.modInfos.ordered)
        self.extraItems = [ItemLink(self.idList.ALL, _(u'All')),
                           ItemLink(self.idList.NONE, _(u'None')), _SaveLink(),
                           ItemLink(self.idList.EDIT, _(u'Edit Lists...')),
                           SeparatorLink()]
        self.extraActions = {self.idList.ALL: self.DoAll,
                             self.idList.NONE: self.DoNone,
                             self.idList.SAVE: self.DoSave,
                             self.idList.EDIT: self.DoEdit, }

    @property
    def items(self):
        items = self.loadListsDict.keys()
        items.sort(lambda a,b: cmp(a.lower(),b.lower()))
        return items

    def SortWindow(self):
        self.window.PopulateItems()

    def DoNone(self,event):
        """Unselect all mods."""
        bosh.modInfos.selectExact([])
        modList.RefreshUI()

    def DoAll(self,event):
        """Select all mods."""
        modInfos = bosh.modInfos
        try:
            # first select the bashed patch(es) and their masters
            for bashedPatch in [GPath(modName) for modName in modList.items if modInfos[modName].header.author in (u'BASHED PATCH',u'BASHED LISTS')]:
                if not modInfos.isSelected(bashedPatch):
                    modInfos.select(bashedPatch, False)
            # then activate mods that are not tagged NoMerge or Deactivate or Filter
            for mod in [GPath(modName) for modName in modList.items if modName not in modInfos.mergeable and u'Deactivate' not in modInfos[modName].getBashTags() and u'Filter' not in modInfos[modName].getBashTags()]:
                if not modInfos.isSelected(mod):
                    modInfos.select(mod, False)
            # then activate as many of the remaining mods as we can
            for mod in modInfos.mergeable:
                if u'Deactivate' in modInfos[mod].getBashTags(): continue
                if u'Filter' in modInfos[mod].getBashTags(): continue
                if not modInfos.isSelected(mod):
                    modInfos.select(mod, False)
            modInfos.plugins.save()
            modInfos.refreshInfoLists()
            modInfos.autoGhost()
        except bosh.PluginsFullError:
            balt.showError(self.window, _(u"Mod list is full, so some mods were skipped"), _(u'Select All'))
        modList.RefreshUI()

    def DoList(self,event):
        """Select mods in list."""
        item = self.items[event.GetId() - self.idList.BASE]
        selectList = [GPath(modName) for modName in modList.items if GPath(modName) in self.loadListsDict[item]]
        errorMessage = bosh.modInfos.selectExact(selectList)
        modList.RefreshUI()
        if errorMessage:
            balt.showError(self.window,errorMessage,item)

    def DoSave(self,event):
        #--No slots left?
        if len(self.loadListsDict) >= (self.idList.MAX - self.idList.BASE + 1):
            balt.showError(self,_(u'All load list slots are full. Please delete an existing load list before adding another.'))
            return
        #--Dialog
        newItem = (balt.askText(self.window,_(u'Save current load list as:'),u'Wrye Bash') or u'').strip()
        if not newItem: return
        if len(newItem) > 64:
            message = _(u'Load list name must be between 1 and 64 characters long.')
            return balt.showError(self.window,message)
        self.loadListsDict[newItem] = bosh.modInfos.ordered[:]
        bosh.settings.setChanged('bash.loadLists.data')

    def DoEdit(self,event):
        data = _Mods_LoadListData(self.window)
        balt.ListEditor.Display(self.window, _(u'Load Lists'), data)

# "Sort by" submenu -----------------------------------------------------------
class Mods_EsmsFirst(CheckLink):
    """Sort esms to the top."""
    help = _(u'Sort masters by type')

    def __init__(self, prefix=u''):
        super(Mods_EsmsFirst, self).__init__()
        self.prefix = prefix
        self.text = self.prefix + _(u'Type')

    def _check(self): return self.window.esmsFirst

    def Execute(self,event):
        self.window.esmsFirst = not self.window.esmsFirst
        self.window.PopulateItems()

class Mods_SelectedFirst(CheckLink):
    """Sort loaded mods to the top."""
    help = _(u'Sort loaded mods to the top')

    def __init__(self, prefix=u''):
        super(Mods_SelectedFirst, self).__init__()
        self.prefix = prefix
        self.text = self.prefix + _(u'Selection')

    def _check(self): return self.window.selectedFirst

    def Execute(self,event):
        self.window.selectedFirst = not self.window.selectedFirst
        self.window.PopulateItems()

# "Oblivion.esm" submenu ------------------------------------------------------
class Mods_OblivionVersion(CheckLink, EnabledLink):
    """Specify/set Oblivion version."""
    help = _(u'Specify/set Oblivion version')

    def __init__(self, key, setProfile=False):
        super(Mods_OblivionVersion, self).__init__()
        self.key = self.text = key
        self.setProfile = setProfile

    def _check(self): return bosh.modInfos.voCurrent == self.key

    def _enable(self):
        return bosh.modInfos.voCurrent is not None \
                          and self.key in bosh.modInfos.voAvailable

    def Execute(self,event):
        """Handle selection."""
        if bosh.modInfos.voCurrent == self.key: return
        bosh.modInfos.setOblivionVersion(self.key)
        bosh.modInfos.refresh()
        modList.RefreshUI()
        if self.setProfile:
            bosh.saveInfos.profiles.setItem(bosh.saveInfos.localSave,'vOblivion',self.key)
        Link.Frame.SetTitle()

# "File" submenu --------------------------------------------------------------
class Mods_CreateBlankBashedPatch(ItemLink):
    """Create a new bashed patch."""
    text, help = _(u'New Bashed Patch...'), _(u'Create a new bashed patch')

    def Execute(self,event):
        newPatchName = PatchFile.generateNextBashedPatch(self.window)
        if newPatchName is not None:
            self.window.RefreshUI(detail=newPatchName)

class Mods_CreateBlank(ItemLink):
    """Create a new blank mod."""
    text, help = _(u'New Mod...'), _(u'Create a new blank mod')

    def Execute(self,event):
        fileInfos = self.window.data
        count = 0
        newName = GPath(u'New Mod.esp')
        while newName in fileInfos:
            count += 1
            newName = GPath(u'New Mod %d.esp' % count)
        newInfo = fileInfos.factory(fileInfos.dir,newName)
        if self.selected:
            newTime = max(fileInfos[x].mtime for x in self.selected)
        else:
            newTime = max(fileInfos[x].mtime for x in fileInfos.data)
        newInfo.mtime = fileInfos.getFreeTime(newTime,newTime)
        newFile = bosh.ModFile(newInfo,bosh.LoadFactory(True))
        newFile.tes4.masters = [GPath(bush.game.masterFiles[0])]
        newFile.safeSave()
        mod_group = fileInfos.table.getColumn('group')
        mod_group[newName] = mod_group.get(newName,u'')
        bosh.modInfos.refresh()
        self.window.RefreshUI(detail=newName)

#------------------------------------------------------------------------------
class Mods_ListMods(ItemLink):
    """Copies list of mod files to clipboard."""
    text = _(u"List Mods...")
    help = _(u"Copies list of active mod files to clipboard.")

    def Execute(self,event):
        #--Get masters list
        text = bosh.modInfos.getModList(showCRC=balt.getKeyState(67))
        balt.copyToClipboard(text)
        balt.showLog(self.window,text,_(u"Active Mod Files"),asDialog=False,fixedFont=False,icons=Resources.bashBlue)

#------------------------------------------------------------------------------
class Mods_ListBashTags(ItemLink):
    """Copies list of bash tags to clipboard."""
    text = _(u"List Bash Tags...")
    help = _(u"Copies list of bash tags to clipboard.")

    def Execute(self,event):
        #--Get masters list
        text = bosh.modInfos.getTagList()
        balt.copyToClipboard(text)
        balt.showLog(self.window,text,_(u"Bash Tags"),asDialog=False,fixedFont=False,icons=Resources.bashBlue)

#------------------------------------------------------------------------------
class Mods_CleanDummyMasters(EnabledLink):
    """Clean up after using a 'Create Dummy Masters...' command."""
    text = _(u'Remove Dummy Masters...')
    help = _(u"Clean up after using a 'Create Dummy Masters...' command")

    def _enable(self):
        for fileName in bosh.modInfos.data:
            fileInfo = bosh.modInfos[fileName]
            if fileInfo.header.author == u'BASHED DUMMY':
                return True
        return False

    def Execute(self,event):
        """Handle execution."""
        remove = []
        for fileName in bosh.modInfos.data:
            fileInfo = bosh.modInfos[fileName]
            if fileInfo.header.author == u'BASHED DUMMY':
                remove.append(fileName)
        remove = bosh.modInfos.getOrdered(remove)
        message = [u'',_(u'Uncheck items to skip deleting them if desired.')]
        message.extend(remove)
        dialog = ListBoxes(Link.Frame,_(u'Delete Dummy Masters'),
                     _(u'Delete these items? This operation cannot be undone.'),
                     [message])
        if dialog.ShowModal() == ListBoxes.ID_CANCEL:
            dialog.Destroy()
            return
        id = dialog.ids[u'']
        checks = dialog.FindWindowById(id)
        if checks:
            for i,mod in enumerate(remove):
                if checks.IsChecked(i):
                    self.window.data.delete(mod)
        dialog.Destroy()
        Link.Frame.RefreshData()
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class Mods_AutoGhost(BoolLink):
    """Toggle Auto-ghosting."""
    text, key = _(u'Auto-Ghost'), 'bash.mods.autoGhost'

    def Execute(self,event):
        BoolLink.Execute(self,event)
        files = bosh.modInfos.autoGhost(True)
        self.window.RefreshUI(files)

#------------------------------------------------------------------------------
class Mods_ScanDirty(BoolLink):
    """Read mod CRC's to check for dirty mods."""
    text = _(u"Check mods against BOSS's dirty mod list")
    key = 'bash.mods.scanDirty'

    def Execute(self,event):
        BoolLink.Execute(self,event)
        self.window.PopulateItems()

class Mods_LockTimes(CheckLink):
    """Turn on resetMTimes feature."""
    text = _(u'Lock Load Order')
    help = _(u"Will reset mod Load Order to whatever Wrye Bash has saved for"
             u" them whenever Wrye Bash refreshes data/starts up.")

    def _check(self): return bosh.modInfos.lockLO

    def Execute(self,event):
        lockLO = not bosh.modInfos.lockLO
        if not lockLO: bosh.modInfos.mtimes.clear()
        bosh.settings['bosh.modInfos.resetMTimes'] = bosh.modInfos.lockLO = lockLO
        bosh.modInfos.refresh(doInfos=False)
        modList.RefreshUI()

# CRUFT -----------------------------------------------------------------------
class Mods_ReplacersData: # CRUFT
    """Empty version of a now removed class. Here for compatibility with
    older settings files."""
    pass

class Mod_MergedLists_Data: # CRUFT
    """Empty version of a now removed class. Here for compatibility with
    older settings files."""
    pass
