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
from . import Mod_BaloGroups_Edit, bashBlue, bashFrameSetTitle, ListBoxes
from .. import bosh, balt
from .. import bush # for Mods_LoadListData, Mods_LoadList
from ..balt import _Link, CheckLink, BoolLink, EnabledLink, ChoiceLink, SeparatorLink
from ..bolt import GPath

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
        self.extraItems = [_Link(self.idList.ALL, _(u'All')),
                           _Link(self.idList.NONE, _(u'None')), _SaveLink(),
                           _Link(self.idList.EDIT, _(u'Edit Lists...')),
                           SeparatorLink()]
        self.extraActions = {self.idList.ALL: self.DoAll,
                             self.idList.NONE: self.DoNone,
                             self.idList.SAVE: self.DoSave,
                             self.idList.EDIT: self.DoEdit, }

    def GetItems(self):
        items = self.loadListsDict.keys()
        items.sort(lambda a,b: cmp(a.lower(),b.lower()))
        return items

    def SortWindow(self):
        self.window.PopulateItems()

    def _range(self):
        for id,item in zip(self.idList,self.GetItems()):
            yield _Link(id,item)

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
        item = self.GetItems()[event.GetId()-self.idList.BASE]
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
        balt.ListEditor.Display(self.window,_(u'Load Lists'), data)

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
        bashFrameSetTitle()

#------------------------------------------------------------------------------
class Mods_ListMods(_Link):
    """Copies list of mod files to clipboard."""
    text = _(u"List Mods...")
    help = _(u"Copies list of active mod files to clipboard.")

    def Execute(self,event):
        #--Get masters list
        text = bosh.modInfos.getModList(showCRC=balt.getKeyState(67))
        balt.copyToClipboard(text)
        balt.showLog(self.window,text,_(u"Active Mod Files"),asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class Mods_ListBashTags(_Link):
    """Copies list of bash tags to clipboard."""
    text = _(u"List Bash Tags...")
    help = _(u"Copies list of bash tags to clipboard.")

    def Execute(self,event):
        #--Get masters list
        text = bosh.modInfos.getTagList()
        balt.copyToClipboard(text)
        balt.showLog(self.window,text,_(u"Bash Tags"),asDialog=False,fixedFont=False,icons=bashBlue)

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
        from . import bashFrame # FIXME
        dialog = ListBoxes(bashFrame,_(u'Delete Dummy Masters'),
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
        bashFrame.RefreshData()
        self.window.RefreshUI()

# "Balo" links ----------------------------------------------------------------
class Mods_AutoGroup(BoolLink):
    """Turn on autogrouping."""
    text = _(u'Auto Group (Deprecated -- Please use BOSS instead)')
    key = 'bash.balo.autoGroup'

    def Execute(self,event):
        BoolLink.Execute(self,event)
        bosh.modInfos.updateAutoGroups()

#------------------------------------------------------------------------------
class Mods_FullBalo(BoolLink):
    """Turn Full Balo off/on."""
    text = _(u'Full Balo (Deprecated -- Please use BOSS instead)')
    key = 'bash.balo.full'

    def Execute(self,event):
        if not bosh.settings[self.key]:
            message = (_(u'Activate Full Balo?')
                       + u'\n\n' +
                       _(u'Full Balo segregates mods by groups, and then autosorts mods within those groups by alphabetical order.  Full Balo is still in development and may have some rough edges.')
                       )
            if balt.askContinue(self.window,message,'bash.balo.full.continue',_(u'Balo Groups')):
                dialog = Mod_BaloGroups_Edit(self.window)
                dialog.ShowModal()
                dialog.Destroy()
            return
        else:
            bosh.settings[self.key] = False
            bosh.modInfos.fullBalo = False
            bosh.modInfos.refresh(doInfos=False)

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

# TODO(ut): classes below used by AppButton subclasses ------------------------
class Mods_Tes4ViewExpert(BoolLink):
    """Toggle Tes4Edit expert mode (when launched via Bash)."""
    text, key = _(u'Tes4Edit Expert'), 'tes4View.iKnowWhatImDoing'

#------------------------------------------------------------------------------
class Mods_Tes5ViewExpert(BoolLink):
    """Toggle Tes5Edit expert mode (when launched via Bash)."""
    text, key = _(u'Tes5Edit Expert'), 'tes5View.iKnowWhatImDoing'

#------------------------------------------------------------------------------
class Mods_BOSSDisableLockTimes(BoolLink):
    """Toggle Lock Load Order disabling when launching BOSS through Bash."""
    text = _(u'BOSS Disable Lock Load Order')
    key = 'BOSS.ClearLockTimes'
    help = _(u"If selected, will temporarily disable Bash's Lock Load Order"
             u" when running BOSS through Bash.")

#------------------------------------------------------------------------------
class Mods_BOSSLaunchGUI(BoolLink):
    """If BOSS.exe is available then BOSS GUI.exe should be too."""
    text, key, help = _(u'Launch using GUI'), 'BOSS.UseGUI', \
                      _(u"If selected, Bash will run BOSS's GUI.")

# CRUFT -----------------------------------------------------------------------
class Mods_ReplacersData: # TODO: CRUFT
    """Empty version of a now removed class. Here for compatibility with
    older settings files."""
    pass

class Mod_MergedLists_Data: # TODO: CRUFT
    """Empty version of a now removed class. Here for compatibility with
    older settings files."""
    pass
