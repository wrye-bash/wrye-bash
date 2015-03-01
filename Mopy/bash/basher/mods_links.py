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

"""Menu items for the _main_ menu of the mods tab - their window attribute
points to BashFrame.modList singleton."""

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
    max_load_orders_saved = 64

    def __init__(self):
        super(Mods_LoadList, self).__init__()
        self.loadListsDict = bosh.settings['bash.loadLists.data']
        self.loadListsDict['Bethesda ESMs'] = [
            GPath(x) for x in bush.game.bethDataFiles
            if x.endswith(u'.esm')
            ] # FIXME: selects both Oblivion.esm AND Oblivion1_1.esm
        #--Links
        _self = self
        class _All(ItemLink):
            text = _(u'All')
            def Execute(self, event): _self.DoAll(event)
        class _None(ItemLink):
            text = _(u'None')
            def Execute(self, event): _self.DoNone(event)
        class _Edit(ItemLink):
            text = _(u'Edit Lists...')
            def Execute(self, event): _self.DoEdit(event)
        class _SaveLink(EnabledLink):
            text = _(u'Save List...')
            def _enable(self): return bool(bosh.modInfos.ordered)
            def Execute(self, event): _self.DoSave(event)
        self.extraItems = [_All(), _None(), _SaveLink(), _Edit(),
                           SeparatorLink()]
        class _LoListLink(ItemLink):
            def Execute(self, event):
                """Select mods in list."""
                selectList = [GPath(modName) for modName in self.window.items if GPath(modName) in _self.loadListsDict[self.text]]
                errorMessage = bosh.modInfos.selectExact(selectList)
                self.window.RefreshUI()
                if errorMessage: self._showError(errorMessage, self.text)
        self.__class__.cls = _LoListLink

    @property
    def _choices(self):
        items = self.loadListsDict.keys()
        items.sort(lambda a,b: cmp(a.lower(),b.lower()))
        return items

    def DoNone(self,event):
        """Unselect all mods."""
        bosh.modInfos.selectExact([])
        self.window.RefreshUI()

    def DoAll(self,event):
        """Select all mods."""
        modInfos = bosh.modInfos
        try:
            # first select the bashed patch(es) and their masters
            for bashedPatch in [GPath(modName) for modName in self.window.items if modInfos[modName].header.author in (u'BASHED PATCH',u'BASHED LISTS')]:
                if not modInfos.isSelected(bashedPatch):
                    modInfos.select(bashedPatch, False)
            # then activate mods that are not tagged NoMerge or Deactivate or Filter
            for mod in [GPath(modName) for modName in self.window.items if modName not in modInfos.mergeable and u'Deactivate' not in modInfos[modName].getBashTags() and u'Filter' not in modInfos[modName].getBashTags()]:
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
            self._showError(_(u"Mod list is full, so some mods were skipped"),
                            _(u'Select All'))
        self.window.RefreshUI()

    def DoSave(self,event):
        #--No slots left?
        if len(self.loadListsDict) >= (self.max_load_orders_saved + 1):
            self._showError(_(u'All load list slots are full. Please delete an'
                              u' existing load list before adding another.'))
            return
        #--Dialog
        newItem = (self._askText(_(u'Save current load list as:'),
                                 u'Wrye Bash') or u'').strip()
        if not newItem: return
        if len(newItem) > 64:
            message = _(u'Load list name must be between 1 and 64 characters long.')
            return self._showError(message)
        self.loadListsDict[newItem] = bosh.modInfos.ordered[:]
        bosh.settings.setChanged('bash.loadLists.data')

    def DoEdit(self,event):
        data = _Mods_LoadListData(self.window)
        balt.ListEditor.Display(self.window, _(u'Load Lists'), data)

# "Sort by" submenu -----------------------------------------------------------
class Mods_EsmsFirst(CheckLink, EnabledLink):
    """Sort esms to the top."""
    help = _(u'Sort masters by type. Always on if current sort is Load Order.')
    text = _(u'Type')

    def _enable(self): return not self.window.forceEsmFirst()
    def _check(self): return self.window.esmsFirst

    def Execute(self,event):
        self.window.esmsFirst = not self.window.esmsFirst
        self.window.SortItems()

class Mods_SelectedFirst(CheckLink):
    """Sort loaded mods to the top."""
    help = _(u'Sort loaded mods to the top')
    text = _(u'Selection')

    def _check(self): return self.window.selectedFirst

    def Execute(self,event):
        self.window.selectedFirst = not self.window.selectedFirst
        self.window.SortItems()

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
        self.window.RefreshUI()
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
        selected = self.window.GetSelected()
        mods = selected if selected else fileInfos.data
        newTime = max(fileInfos[x].mtime for x in mods)
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
        self._showLog(text, title=_(u"Active Mod Files"), fixedFont=False,
                      icons=Resources.bashBlue)

#------------------------------------------------------------------------------
class Mods_ListBashTags(ItemLink):
    """Copies list of bash tags to clipboard."""
    text = _(u"List Bash Tags...")
    help = _(u"Copies list of bash tags to clipboard.")

    def Execute(self,event):
        #--Get masters list
        text = bosh.modInfos.getTagList()
        balt.copyToClipboard(text)
        self._showLog(text, title=_(u"Bash Tags"), fixedFont=False,
                      icons=Resources.bashBlue)

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
        self.window.RefreshUI(files=bosh.modInfos.autoGhost(True))

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
        self.window.RefreshUI()

# CRUFT -----------------------------------------------------------------------
class Mods_ReplacersData: # CRUFT
    """Empty version of a now removed class. Here for compatibility with
    older settings files."""
    pass

class Mod_MergedLists_Data: # CRUFT
    """Empty version of a now removed class. Here for compatibility with
    older settings files."""
    pass
