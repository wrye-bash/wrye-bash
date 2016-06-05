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

"""Menu items for the _main_ menu of the mods tab - their window attribute
points to BashFrame.modList singleton."""

import re as _re
from .. import bosh, balt, load_order
from .. import bush # for Mods_LoadListData, Mods_LoadList
from ..bass import Resources
from ..balt import ItemLink, CheckLink, BoolLink, EnabledLink, ChoiceLink, \
    SeparatorLink, Link
from ..bolt import GPath, BoltError

__all__ = ['Mods_EsmsFirst', 'Mods_LoadList', 'Mods_SelectedFirst',
           'Mods_OblivionVersion', 'Mods_CreateBlankBashedPatch',
           'Mods_CreateBlank', 'Mods_ListMods', 'Mods_ListBashTags',
           'Mods_CleanDummyMasters', 'Mods_AutoGhost', 'Mods_LockTimes',
           'Mods_ScanDirty']

# "Load" submenu --------------------------------------------------------------
def _getLoadListsDict():
    loadListData = bosh.settings['bash.loadLists.data']
    loadListData['Bethesda ESMs'] = [GPath(x) for x in bush.game.bethDataFiles
        if x.endswith(u'.esm') # but avoid activating modding esms for oblivion
    and (not _re.match(bosh.reOblivion.pattern, x, _re.IGNORECASE)
         or x == u'oblivion.esm')]
    return loadListData

class _Mods_LoadListData(balt.ListEditorData):
    """Data capsule for load list editing dialog."""
    def __init__(self, parent, loadListsDict):
        self.loadListDict = loadListsDict
        #--GUI
        balt.ListEditorData.__init__(self,parent)
        self.showRename = True
        self.showRemove = True

    def getItemList(self):
        """Returns load list keys in alpha order."""
        return sorted(self.loadListDict.keys(), key=lambda a: a.lower())

    def rename(self,oldName,newName):
        """Renames oldName to newName."""
        #--Right length?
        if len(newName) == 0 or len(newName) > 64:
            balt.showError(self.parent,
                _(u'Name must be between 1 and 64 characters long.'))
            return False
        #--Rename
        bosh.settings.setChanged('bash.loadLists.data')
        self.loadListDict[newName] = self.loadListDict[oldName]
        del self.loadListDict[oldName]
        return newName

    def remove(self,item):
        """Removes load list."""
        bosh.settings.setChanged('bash.loadLists.data')
        del self.loadListDict[item]
        return True

class Mods_LoadList(ChoiceLink):
    """Add load list links."""
    loadListsDict = {}

    def __init__(self):
        super(Mods_LoadList, self).__init__()
        Mods_LoadList.loadListsDict = self.loadListsDict or _getLoadListsDict()
        #--Links
        class __Activate(ItemLink):
            """Common methods used by Links de/activating mods."""
            def _refresh(self): self.window.RefreshUI(refreshSaves=True)
            def _selectExact(self, mods):
                errorMessage = bosh.modInfos.lo_activate_exact(mods)
                self._refresh()
                if errorMessage: self._showError(errorMessage, self.text)
        class _All(__Activate):
            text = _(u'All')
            help = _(u'Activate all mods')
            def Execute(self):
                """Select all mods."""
                try:
                    bosh.modInfos.lo_activate_all()
                except bosh.PluginsFullError:
                    self._showError(
                        _(u"Mod list is full, so some mods were skipped"),
                        _(u'Select All'))
                except BoltError as e:
                    self._showError(u'%s' % e, _(u'Select All'))
                self._refresh()
        class _None(__Activate):
            text = _(u'None')
            def Execute(self): self._selectExact([])
        class _Selected(__Activate):
            text = _(u'Selected')
            help = _(u'Activate only the mods selected in the list')
            def Execute(self):
                self._selectExact(self.window.GetSelected())
        class _Edit(ItemLink):
            text = _(u'Edit Lists...')
            def Execute(self):
                editorData = _Mods_LoadListData(self.window,
                                                Mods_LoadList.loadListsDict)
                balt.ListEditor.Display(self.window, _(u'Load Lists'),
                                        editorData)
        class _SaveLink(EnabledLink):
            text = _(u'Save List...')
            def _enable(self): return bool(load_order.activeCached())
            def Execute(self):
                newItem = self._askText(_(u'Save current load list as:'))
                if not newItem: return
                if len(newItem) > 64:
                    message = _(u'Load list name must be between 1 and 64 '
                                u'characters long.')
                    return self._showError(message)
                Mods_LoadList.loadListsDict[newItem] = list(
                    load_order.activeCached())
                bosh.settings.setChanged('bash.loadLists.data')
        self.extraItems = [_All(), _None(), _Selected(), _SaveLink(), _Edit(),
                           SeparatorLink()]
        class _LoListLink(__Activate):
            def Execute(self):
                """Select mods in list."""
                listed = Mods_LoadList.loadListsDict[self.text]
                mods = filter(lambda m: m in listed,
                              map(GPath, self.window.GetItems()))
                self._selectExact(mods)
        self.__class__.choiceLinkType = _LoListLink

    @property
    def _choices(self):
        return sorted(self.loadListsDict.keys(), key=lambda a: a.lower())

# "Sort by" submenu -----------------------------------------------------------
class Mods_EsmsFirst(CheckLink, EnabledLink):
    """Sort esms to the top."""
    help = _(u'Sort masters by type. Always on if current sort is Load Order.')
    text = _(u'Type')

    def _enable(self): return not self.window.forceEsmFirst()
    def _check(self): return self.window.esmsFirst

    def Execute(self):
        self.window.esmsFirst = not self.window.esmsFirst
        self.window.SortItems()

class Mods_SelectedFirst(CheckLink):
    """Sort loaded mods to the top."""
    help = _(u'Sort loaded mods to the top')
    text = _(u'Selection')

    def _check(self): return self.window.selectedFirst

    def Execute(self):
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

    def Execute(self):
        """Handle selection."""
        if bosh.modInfos.voCurrent == self.key: return
        bosh.modInfos.setOblivionVersion(self.key)
        bosh.modInfos.refresh()
        self.window.RefreshUI(refreshSaves=True) # True: refresh save's masters
        if self.setProfile:
            bosh.saveInfos.profiles.setItem(bosh.saveInfos.localSave,'vOblivion',self.key)
        Link.Frame.SetTitle()

# "File" submenu --------------------------------------------------------------
class Mods_CreateBlankBashedPatch(ItemLink):
    """Create a new bashed patch."""
    text, help = _(u'New Bashed Patch...'), _(u'Create a new bashed patch')

    def Execute(self):
        newPatchName = bosh.modInfos.generateNextBashedPatch()
        if newPatchName is not None:
            self.window.RefreshUI(files=[newPatchName], refreshSaves=False)
            self.window.SelectAndShowItem(newPatchName, deselectOthers=True)
        else:
            self._showWarning(u"Unable to create new bashed patch: "
                              u"10 bashed patches already exist!")


class Mods_CreateBlank(ItemLink):
    """Create a new blank mod."""
    text, help = _(u'New Mod...'), _(u'Create a new blank mod')

    def __init__(self, masterless=False):
        super(Mods_CreateBlank, self).__init__()
        self.masterless = masterless
        if masterless:
            self.text = _(u'New Mod (masterless)...')
            self.help = _(u'Create a new blank mod with no masters')

    def Execute(self):
        newName = self.window.new_name(GPath(u'New Mod.esp'))
        windowSelected = self.window.GetSelected()
        self.window.data_store.create_new_mod(newName, windowSelected,
                                              masterless=self.masterless)
        if windowSelected: # assign it the group of the first selected mod
            mod_group = self.window.data_store.table.getColumn('group')
            mod_group[newName] = mod_group.get(windowSelected[0], u'')
        self.window.RefreshUI(files=[newName], refreshSaves=False)
        self.window.SelectAndShowItem(newName, deselectOthers=True)

#------------------------------------------------------------------------------
class Mods_ListMods(ItemLink):
    """Copies list of mod files to clipboard."""
    text = _(u"List Mods...")
    help = _(u"Copies list of active mod files to clipboard.")

    def Execute(self):
        #--Get masters list
        text = bosh.modInfos.getModList(showCRC=balt.getKeyState(67))
        balt.copyToClipboard(text)
        self._showLog(text, title=_(u"Active Mod Files"), fixedFont=False,
                      icons=Resources.bashBlue)

#------------------------------------------------------------------------------
class Mods_ListBashTags(ItemLink): # duplicate of mod_links.Mod_ListBashTags
    """Copies list of bash tags to clipboard."""
    text = _(u"List Bash Tags...")
    help = _(u"Copies list of bash tags to clipboard.")

    def Execute(self):
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
        for fileInfo in bosh.modInfos.values():
            if fileInfo.header.author == u'BASHED DUMMY':
                return True
        return False

    def Execute(self):
        """Handle execution."""
        remove = []
        for fileName, fileInfo in bosh.modInfos.items():
            if fileInfo.header.author == u'BASHED DUMMY':
                remove.append(fileName)
        remove = load_order.get_ordered(remove)
        self.window.DeleteItems(items=remove, order=False,
                                dialogTitle=_(u'Delete Dummy Masters'))
        # Link.Frame.RefreshData() ##: why ?

#------------------------------------------------------------------------------
class Mods_AutoGhost(BoolLink):
    """Toggle Auto-ghosting."""
    text, key = _(u'Auto-Ghost'), 'bash.mods.autoGhost'

    def Execute(self):
        super(Mods_AutoGhost, self).Execute()
        self.window.RefreshUI(files=bosh.modInfos.autoGhost(force=True),
                              refreshSaves=False)

#------------------------------------------------------------------------------
class Mods_ScanDirty(BoolLink):
    """Read mod CRC's to check for dirty mods."""
    text = _(u"Check mods against BOSS's dirty mod list")
    key = 'bash.mods.scanDirty'

    def Execute(self):
        super(Mods_ScanDirty, self).Execute()
        self.window.RefreshUI(refreshSaves=False)

class Mods_LockTimes(CheckLink):
    """Turn on Lock Load Order feature."""
    text = _(u'Lock Load Order')
    help = _(u"Will reset mod Load Order to whatever Wrye Bash has saved for"
             u" them whenever Wrye Bash refreshes data/starts up.")

    def _check(self): return bosh.modInfos.lockLO

    def Execute(self): bosh.modInfos.lockLOSet(not bosh.modInfos.lockLO)
