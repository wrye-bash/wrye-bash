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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Menu items for the _main_ menu of the mods tab - their window attribute
points to BashFrame.modList singleton."""

import re
from .. import bosh, balt, load_order
from .. import bush # for Mods_LoadListData, Mods_LoadList
from .. import exception
from ..balt import ItemLink, CheckLink, BoolLink, EnabledLink, ChoiceLink, \
    SeparatorLink, Link
from ..bolt import GPath

__all__ = ['Mods_EsmsFirst', 'Mods_LoadList', 'Mods_SelectedFirst',
           'Mods_OblivionVersion', 'Mods_CreateBlankBashedPatch',
           'Mods_CreateBlank', 'Mods_ListMods', 'Mods_ListBashTags',
           'Mods_CleanDummyMasters', 'Mods_AutoGhost', 'Mods_LockLoadOrder',
           'Mods_ScanDirty', 'Mods_CrcRefresh', 'Mods_AutoESLFlagBP']

# "Load" submenu --------------------------------------------------------------
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
        self.loadListDict[newName] = self.loadListDict[oldName]
        del self.loadListDict[oldName]
        return newName

    def remove(self,item):
        """Removes load list."""
        del self.loadListDict[item]
        return True

class Mods_LoadList(ChoiceLink):
    """Add active mods list links."""
    __uninitialized = {}
    loadListsDict = __uninitialized

    def __init__(self):
        super(Mods_LoadList, self).__init__()
        _self = self
        #--Links
        class __Activate(ItemLink):
            """Common methods used by Links de/activating mods."""
            def _refresh(self): self.window.RefreshUI(refreshSaves=True)
            def _selectExact(self, mods):
                errorMessage = bosh.modInfos.lo_activate_exact(mods)
                self._refresh()
                if errorMessage: self._showError(errorMessage, self._text)
        class _All(__Activate):
            _text = _(u'Activate All')
            _help = _(u'Activate all mods')
            def Execute(self):
                """Select all mods."""
                try:
                    bosh.modInfos.lo_activate_all()
                except exception.PluginsFullError:
                    self._showError(
                        _(u"Mod list is full, so some mods were skipped"),
                        _(u'Select All'))
                except exception.BoltError as e:
                    self._showError(u'%s' % e, _(u'Select All'))
                self._refresh()
        class _None(__Activate):
            _text = _(u'De-activate All')
            _help = _(u'De-activate all mods')
            def Execute(self): self._selectExact([])
        class _Selected(__Activate):
            _text = _(u'Activate Selected')
            _help = _(u'Activate only the mods selected in the UI')
            def Execute(self):
                self._selectExact(self.window.GetSelected())
        class _Edit(ItemLink):
            _text = _(u'Edit Active Mods Lists...')
            _help = _(u'Display a dialog to rename/remove active mods lists')
            def Execute(self):
                editorData = _Mods_LoadListData(self.window, _self.load_lists)
                balt.ListEditor.display_dialog(
                    self.window, _(u'Active Mods Lists'), editorData)
        class _SaveLink(EnabledLink):
            _text = _(u'Save Active Mods List')
            _help = _(u'Save the currently active mods to a new active mods list')
            def _enable(self): return bool(load_order.cached_active_tuple())
            def Execute(self):
                newItem = self._askText(
                    _(u'Save currently active mods list as:'))
                if not newItem: return
                if len(newItem) > 64:
                    message = _(u'Active Mods list name must be between '
                                u'1 and 64 characters long.')
                    return self._showError(message)
                _self.load_lists[newItem] = list(
                    load_order.cached_active_tuple())
        self.extraItems = [_All(), _None(), _Selected(), _SaveLink(), _Edit(),
                           SeparatorLink()]
        class _LoListLink(__Activate):
            def Execute(self):
                """Activate mods in list."""
                mods = set(_self.load_lists[self._text])
                mods = [m for m in self.window.data_store.keys() if m in mods]
                self._selectExact(mods)
            @property
            def menu_help(self):
                return _(u'Activate mods in the %(list_name)s list' % {
                    'list_name': self._text})
        self.__class__.choiceLinkType = _LoListLink

    @property
    def load_lists(self):
        """Get the load lists, since those come from BashLoadOrders.dat we must
        wait for this being initialized in ModInfos.__init__"""
        if self.__class__.loadListsDict is self.__class__.__uninitialized:
            loadListData = load_order.get_active_mods_lists()
            loadListData['Bethesda ESMs'] = [
                GPath(x) for x in bush.game.bethDataFiles if x.endswith(
                    u'.esm') # but avoid activating modding esms for oblivion
                and (not re.match(bosh.reOblivion.pattern, x, re.I)
                     or x == u'oblivion.esm')]
            self.__class__.loadListsDict = loadListData
        return self.__class__.loadListsDict

    @property
    def _choices(self):
        return sorted(self.load_lists.keys(), key=lambda a: a.lower())

# "Sort by" submenu -----------------------------------------------------------
class Mods_EsmsFirst(CheckLink, EnabledLink):
    """Sort esms to the top."""
    _help = _(u'Sort masters by type. Always on if current sort is Load Order.')
    _text = _(u'Type')

    def _enable(self): return not self.window.forceEsmFirst()
    def _check(self): return self.window.esmsFirst

    def Execute(self):
        self.window.esmsFirst = not self.window.esmsFirst
        self.window.SortItems()

class Mods_SelectedFirst(CheckLink):
    """Sort loaded mods to the top."""
    _help = _(u'Sort loaded mods to the top')
    _text = _(u'Selection')

    def _check(self): return self.window.selectedFirst

    def Execute(self):
        self.window.selectedFirst = not self.window.selectedFirst
        self.window.SortItems()

# "Oblivion.esm" submenu ------------------------------------------------------
class Mods_OblivionVersion(CheckLink, EnabledLink):
    """Specify/set Oblivion version."""
    _help = _(u'Specify/set Oblivion version')

    def __init__(self, key, setProfile=False):
        super(Mods_OblivionVersion, self).__init__()
        self.key = self._text = key
        self.setProfile = setProfile

    def _check(self): return bosh.modInfos.voCurrent == self.key

    def _enable(self):
        return bosh.modInfos.voCurrent is not None \
                          and self.key in bosh.modInfos.voAvailable

    def Execute(self):
        """Handle selection."""
        if bosh.modInfos.voCurrent == self.key: return
        bosh.modInfos.setOblivionVersion(self.key)
        self.window.RefreshUI(refreshSaves=True) # True: refresh save's masters
        if self.setProfile:
            bosh.saveInfos.profiles.setItem(bosh.saveInfos.localSave,'vOblivion',self.key)
        Link.Frame.set_bash_frame_title()

# "File" submenu --------------------------------------------------------------
class Mods_CreateBlankBashedPatch(ItemLink):
    """Create a new bashed patch."""
    _text, _help = _(u'New Bashed Patch...'), _(u'Create a new bashed patch')

    def Execute(self):
        newPatchName = bosh.modInfos.generateNextBashedPatch(
            self.window.GetSelected())
        if newPatchName is not None:
            self.window.ClearSelected(clear_details=True)
            self.window.RefreshUI(redraw=[newPatchName], refreshSaves=False)
        else:
            self._showWarning(u"Unable to create new bashed patch: "
                              u"10 bashed patches already exist!")

class Mods_CreateBlank(ItemLink):
    """Create a new blank mod."""
    _text, _help = _(u'New Mod...'), _(u'Create a new blank mod')

    def __init__(self, masterless=False):
        super(Mods_CreateBlank, self).__init__()
        self.masterless = masterless
        if masterless:
            self._text = _(u'New Mod (masterless)...')
            self._help = _(u'Create a new blank mod with no masters')

    def Execute(self):
        newName = self.window.new_name(GPath(u'New Mod.esp'))
        windowSelected = self.window.GetSelected()
        self.window.data_store.create_new_mod(newName, windowSelected,
                                              masterless=self.masterless)
        if windowSelected: # assign it the group of the first selected mod
            mod_group = self.window.data_store.table.getColumn('group')
            mod_group[newName] = mod_group.get(windowSelected[0], u'')
        self.window.ClearSelected(clear_details=True)
        self.window.RefreshUI(redraw=[newName], refreshSaves=False)

#------------------------------------------------------------------------------
class Mods_ListMods(ItemLink):
    """Copies list of mod files to clipboard."""
    _text = _(u"List Mods...")
    _help = _(u"Copies list of active mod files to clipboard.")

    def Execute(self):
        #--Get masters list
        list_txt = bosh.modInfos.getModList(showCRC=balt.getKeyState(67))
        balt.copyToClipboard(list_txt)
        self._showLog(list_txt, title=_(u"Active Mod Files"), fixedFont=False)

#------------------------------------------------------------------------------
class Mods_ListBashTags(ItemLink): # duplicate of mod_links.Mod_ListBashTags
    """Copies list of bash tags to clipboard."""
    _text = _(u"List Bash Tags...")
    _help = _(u"Copies list of bash tags to clipboard.")

    def Execute(self):
        tags_text = bosh.modInfos.getTagList()
        balt.copyToClipboard(tags_text)
        self._showLog(tags_text, title=_(u"Bash Tags"), fixedFont=False)

#------------------------------------------------------------------------------
class Mods_CleanDummyMasters(EnabledLink):
    """Clean up after using a 'Create Dummy Masters...' command."""
    _text = _(u'Remove Dummy Masters...')
    _help = _(u"Clean up after using a 'Create Dummy Masters...' command")

    def _enable(self):
        for fileInfo in bosh.modInfos.values():
            if fileInfo.header.author == u'BASHED DUMMY':
                return True
        return False

    def Execute(self):
        remove = []
        for fileName, fileInfo in bosh.modInfos.iteritems():
            if fileInfo.header.author == u'BASHED DUMMY':
                remove.append(fileName)
        remove = load_order.get_ordered(remove)
        self.window.DeleteItems(items=remove, order=False,
                                dialogTitle=_(u'Delete Dummy Masters'))

#------------------------------------------------------------------------------
class Mods_AutoGhost(BoolLink):
    """Toggle Auto-ghosting."""
    _text, key = _(u'Auto-Ghost'), 'bash.mods.autoGhost'
    _help = _(u'Toggles whether or not to automatically ghost all disabled '
              u'mods.')

    def Execute(self):
        super(Mods_AutoGhost, self).Execute()
        self.window.RefreshUI(redraw=bosh.modInfos.autoGhost(force=True),
                              refreshSaves=False)

class Mods_AutoESLFlagBP(BoolLink):
    """Automatically flags built Bashed Patches as ESLs. This is safe, since
    BPs can never contain new records, only overrides."""
    _text = _(u'ESL-Flag Bashed Patches')
    _help = _(u'Automatically flags any built Bashed Patches as ESLs, freeing '
              u'up a load order slot.')
    key = 'bash.mods.auto_flag_esl'

class Mods_ScanDirty(BoolLink):
    """Read mod CRC's to check for dirty mods."""
    _text = _(u"Check mods against LOOT's dirty mod list")
    _help = _(u'Display a tooltip if mod is dirty and underline dirty mods.')
    key = 'bash.mods.scanDirty'

    def Execute(self):
        super(Mods_ScanDirty, self).Execute()
        self.window.RefreshUI(refreshSaves=False) # update all mouse tips

class Mods_LockLoadOrder(CheckLink):
    """Turn on Lock Load Order feature."""
    _text = _(u'Lock Load Order')
    _help = _(u"Will reset mod Load Order to whatever Wrye Bash has saved for"
             u" them whenever Wrye Bash refreshes data/starts up.")

    def _check(self): return load_order.locked

    def Execute(self):
        def _show_lo_lock_warning():
            message = _(u'Lock Load Order is a feature which resets load '
                        u'order to a previously memorized state. While this '
                        u'feature is good for maintaining your load order, it '
                        u'will also undo any load order changes that you have '
                        u'made outside Bash.')
            return self._askContinue(message, 'bash.load_order.lock_continue',
                                     title=_(u'Lock Load Order'))
        load_order.toggle_lock_load_order(_show_lo_lock_warning)

#------------------------------------------------------------------------------
class Mods_CrcRefresh(ItemLink):
    """Recalculate crcs for all mods"""
    _text = _(u'Recalculate CRCs')
    _help = _(u'Clean stale CRCs from cache')

    @balt.conversation
    def Execute(self):
        message = u'== %s' % _(u'Mismatched CRCs') + u'\n\n'
        with balt.BusyCursor(): pairs = bosh.modInfos.refresh_crcs()
        mismatched = dict((k, v) for k, v in pairs.iteritems() if v[0] != v[1])
        if mismatched:
            message += u'  * ' + u'\n  * '.join(
                [u'%s: cached %08X real %08X' % (k.s, v[1], v[0]) for k, v in
                 mismatched.iteritems()])
            self.window.RefreshUI(redraw=mismatched.keys(), refreshSaves=False)
        else: message += _(u'No stale cached CRC values detected')
        self._showWryeLog(message)
