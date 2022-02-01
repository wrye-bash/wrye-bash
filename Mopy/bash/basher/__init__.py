# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <https://www.gnu.org/licenses/>.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This package provides the GUI interface for Wrye Bash. (However, the Wrye
Bash application is actually launched by the bash module.)

This module is used to help split basher.py to a package without breaking
the program. basher.py was organized starting with lower level elements,
working up to higher level elements (up the BashApp). This was followed by
definition of menus and buttons classes, dialogs, and finally by several
initialization functions. Currently the package structure is:

__init.py__       : this file, basher.py core, must be further split
constants.py      : constants, will grow
*_links.py        : menus and buttons (app_buttons.py)
links_init.py     : the initialization functions for menus, defines menu order
dialogs.py        : subclasses of DialogWindow (except patcher dialog)
frames.py         : subclasses of wx.Frame (except BashFrame)
gui_patchers.py   : the gui patcher classes used by the patcher dialog
patcher_dialog.py : the patcher dialog

The layout is still fluid - there may be a links package, or a package per tab.
A central global variable is balt.Link.Frame, the BashFrame singleton.

Non-GUI objects and functions are provided by the bosh module. Of those, the
primary objects used are the plugins, modInfos and saveInfos singletons -- each
representing external data structures (the plugins.txt file and the Data and
Saves directories respectively). Persistent storage for the app is primarily
provided through the settings singleton (however the modInfos singleton also
has its own data store)."""

# Imports ---------------------------------------------------------------------
#--Python
import collections
import os
import sys
import time
from collections import OrderedDict, namedtuple, defaultdict
from functools import partial, reduce
from typing import Optional, List

#--wxPython
import wx

#--Local
from .. import bush, bosh, bolt, bass, env, load_order, archives
from ..bolt import GPath, SubProgress, deprint, round_size, dict_sort, \
    top_level_items, GPath_no_norm, os_name
from ..bosh import omods, ModInfo
from ..exception import AbstractError, BoltError, CancelError, FileError, \
    SkipError, UnknownListener
from ..localize import format_date, unformat_date

startupinfo = bolt.startupinfo

#--Balt
from .. import balt
from ..balt import CheckLink, EnabledLink, SeparatorLink, Link, Resources, \
    AppendableLink, ListBoxes, INIListCtrl, DnDStatusBar, NotebookPanel, \
    images, colors, Links, ItemLink

from ..gui import Button, CancelButton, HLayout, Label, LayoutOptions, \
    SaveButton, Stretch, TextArea, TextField, VLayout, EventResult, DropDown, \
    WindowFrame, Splitter, TabbedPanel, PanelWin, CheckListBox, Color, \
    Picture, ImageWrapper, CenteredSplash, BusyCursor, RadioButton, \
    GlobalMenu, CopyOrMovePopup, ListBox, ClickableImage, CENTER, \
    MultiChoicePopup, WithMouseEvents, read_files_from_clipboard_cb, \
    get_shift_down, FileOpen

# Constants -------------------------------------------------------------------
from .constants import colorInfo, settingDefaults, installercons

# BAIN wizard support, requires PyWin32, so import will fail if it's not installed
try:
    from .. import belt
    bEnableWizard = True
except ImportError:
    bEnableWizard = False
    deprint(u'Error initializing installer wizards:', traceback=True)

#  - Make sure that python root directory is in PATH, so can access dll's.
_env_path = os.environ[u'PATH']
if sys.prefix not in set(_env_path.split(u';')):
    os.environ[u'PATH'] = _env_path + u';' + sys.prefix

# Settings --------------------------------------------------------------------
settings = None # type: Optional[bolt.Settings]

# Links -----------------------------------------------------------------------
#------------------------------------------------------------------------------
class Installers_Link(ItemLink):
    """InstallersData mixin"""
    _dialog_title: str

    @property
    def idata(self):
        """:rtype: bosh.InstallersData"""
        return self.window.data_store
    @property
    def iPanel(self):
        """:rtype: InstallersPanel"""
        return self.window.panel

    def _askFilename(self, message, filename, inst_type=bosh.InstallerArchive,
                     disallow_overwrite=False, no_dir=True, base_dir=None,
                     allowed_exts=archives.writeExts, use_default_ext=True,
                     check_exists=True, no_file=False):
        """:rtype: bolt.Path"""
        result = self._askText(message, title=self._dialog_title,
                               default=f'{filename}') # accept Path and str
        if not result: return
        #--Error checking
        archive_path, msg = inst_type.validate_filename_str(result,
            allowed_exts=allowed_exts, use_default_ext=use_default_ext)
        if msg is None:
            self._showError(archive_path) # it's an error message in this case
            return
        if isinstance(msg, tuple):
            _root, msg = msg
            self._showWarning(msg) # warn on extension change
        base_dir = base_dir or self.idata.store_dir
        if no_dir and base_dir.join(archive_path).is_dir():
            self._showError(_(u'%s is a directory.') % archive_path)
            return
        if no_file and base_dir.join(archive_path).is_file():
            self._showError(_(u'%s is a file.') % archive_path)
            return
        if check_exists and base_dir.join(archive_path).exists():
            if disallow_overwrite:
                self._showError(_(u'%s already exists.') % archive_path)
                return
            if not self._askYes(
                    _(u'%s already exists. Overwrite it?') % archive_path,
                    title=self._dialog_title, default=False): return
        return archive_path

#--Information about the various Tabs
tabInfo = {
    # InternalName: [className, title, instance]
    u'Installers': [u'InstallersPanel', _(u'Installers'), None],
    u'Mods': [u'ModPanel', _(u'Mods'), None],
    u'Saves': [u'SavePanel', _(u'Saves'), None],
    u'INI Edits': [u'INIPanel', _(u'INI Edits'), None],
    u'Screenshots': [u'ScreensPanel', _(u'Screenshots'), None],
    # u'BSAs':[u'BSAPanel', _(u'BSAs'), None],
}

#------------------------------------------------------------------------------
# Panels ----------------------------------------------------------------------
#------------------------------------------------------------------------------
class _DetailsViewMixin(NotebookPanel):
    """Mixin to add detailsPanel attribute to a Panel with a details view.

    Mix it in to SashUIListPanel so UILists can call SetDetails and
    ClearDetails on their panels."""
    detailsPanel = None
    def _setDetails(self, fileName):
        self.detailsPanel.SetFile(fileName=fileName)
    def ClearDetails(self): self._setDetails(None)
    def SetDetails(self, fileName=u'SAME'): self._setDetails(fileName)

    def RefreshUIColors(self):
        super(_DetailsViewMixin, self).RefreshUIColors()
        self.detailsPanel.RefreshUIColors()

    def ClosePanel(self, destroy=False):
        self.detailsPanel.ClosePanel(destroy)
        super(_DetailsViewMixin, self).ClosePanel(destroy)

    def ShowPanel(self, **kwargs):
        super(_DetailsViewMixin, self).ShowPanel()
        self.detailsPanel.ShowPanel(**kwargs)

_UIsetting = namedtuple(u'UIsetting', u'default_ get_ set_')
class SashPanel(NotebookPanel):
    """Subclass of Notebook Panel, designed for two pane panel. Overrides
    ShowPanel to do some first show initialization."""
    defaultSashPos = minimumSize = 256
    _ui_settings = {u'.sashPos' : _UIsetting(lambda self: self.defaultSashPos,
        lambda self: self.splitter.get_sash_pos(),
        lambda self, sashPos: self.splitter.set_sash_pos(sashPos))}

    def __init__(self, parent, isVertical=True):
        super(SashPanel, self).__init__(parent)
        self.splitter = Splitter(self, allow_split=False,
                                 min_pane_size=self.__class__.minimumSize)
        self.left, self.right = self.splitter.make_panes(vertically=isVertical)
        self.isVertical = isVertical
        VLayout(item_weight=1, item_expand=True,
                items=[self.splitter]).apply_to(self)

    def ShowPanel(self, **kwargs):
        """Unfortunately can't use EVT_SHOW, as the panel needs to be
        populated for position to be set correctly."""
        if self._firstShow:
            for key, ui_set in self._ui_settings.items():
                sashPos = settings.get(self.__class__.keyPrefix + key,
                                       ui_set.default_(self))
                ui_set.set_(self, sashPos)
            self._firstShow = False

    def ClosePanel(self, destroy=False):
        if not self._firstShow and destroy: # if the panel was shown
            for key, ui_set in self._ui_settings.items():
                settings[self.__class__.keyPrefix + key] = ui_set.get_(self)

class SashUIListPanel(SashPanel):
    """SashPanel featuring a UIList and a corresponding listData datasource."""
    listData = None
    _status_str = u'OVERRIDE:' + u' %d'
    _ui_list_type = None # type: type

    def __init__(self, parent, isVertical=True):
        super(SashUIListPanel, self).__init__(parent, isVertical)
        self.uiList = self._ui_list_type(self.left, listData=self.listData,
                                         keyPrefix=self.keyPrefix, panel=self)

    def SelectUIListItem(self, item, deselectOthers=False):
        self.uiList.SelectAndShowItem(item, deselectOthers=deselectOthers,
                                      focus=True)

    def _sbCount(self): return self.__class__._status_str % len(self.listData)

    def SetStatusCount(self):
        """Sets status bar count field."""
        Link.Frame.set_status_count(self, self._sbCount())

    def RefreshUIColors(self):
        self.uiList.RefreshUI(focus_list=False)

    def ShowPanel(self, **kwargs):
        """Resize the columns if auto is on and set Status bar text. Also
        sets the scroll bar and sash positions on first show. Must be _after_
        RefreshUI for scroll bar to be set correctly."""
        if self._firstShow:
            super(SashUIListPanel, self).ShowPanel()
            self.uiList.SetScrollPosition()
        self.uiList.autosizeColumns()
        self.uiList.Focus()
        self.SetStatusCount()
        self.uiList.setup_global_menu()

    def ClosePanel(self, destroy=False):
        if not self._firstShow and destroy: # if the panel was shown
            super(SashUIListPanel, self).ClosePanel(destroy)
            self.uiList.SaveScrollPosition(isVertical=self.isVertical)
        self.listData.save()

class BashTab(_DetailsViewMixin, SashUIListPanel):
    """Wrye Bash Tab, composed of a UIList and a Details panel."""
    _details_panel_type = None # type: type
    defaultSashPos = 512
    minimumSize = 256

    def __init__(self, parent, isVertical=True):
        super(BashTab, self).__init__(parent, isVertical)
        self.detailsPanel = self._details_panel_type(self.right, self)
        #--Layout
        HLayout(item_expand=True, item_weight=1,
                items=[self.detailsPanel]).apply_to(self.right)
        HLayout(item_expand=True, item_weight=2,
                items=[self.uiList]).apply_to(self.left)

#------------------------------------------------------------------------------
class _ModsUIList(balt.UIList):

    _esmsFirstCols = balt.UIList.nonReversibleCols
    @property
    def esmsFirst(self): return settings.get(self.keyPrefix + u'.esmsFirst',
                            True) or self.sort_column in self._esmsFirstCols
    @esmsFirst.setter
    def esmsFirst(self, val): settings[self.keyPrefix + u'.esmsFirst'] = val

    @property
    def selectedFirst(self):
        return settings.get(self.keyPrefix + u'.selectedFirst', False)
    @selectedFirst.setter
    def selectedFirst(self, val):
        settings[self.keyPrefix + u'.selectedFirst'] = val

    def _sortEsmsFirst(self, items):
        if self.esmsFirst:
            items.sort(key=lambda a: not load_order.in_master_block(
                self.data_store[a]))

    def _activeModsFirst(self, items):
        if self.selectedFirst: items.sort(key=lambda x: x not in
            bosh.modInfos.imported | bosh.modInfos.merged | set(
                load_order.cached_active_tuple()))

    def forceEsmFirst(self):
        return self.sort_column in _ModsUIList._esmsFirstCols

#------------------------------------------------------------------------------
class MasterList(_ModsUIList):
    column_links = Links()
    context_links = Links()
    keyPrefix = u'bash.masters' # use for settings shared among the lists (cols)
    _editLabels = True
    #--Sorting
    _default_sort_col = u'Num'
    _sort_keys = {
        u'Num'          : None, # sort by master index, the key itself
        u'File'         : lambda self, a:
            self.data_store[a].curr_name.s.lower(),
        # Missing mods sort last alphabetically
        u'Current Order': lambda self, a: self._curr_lo_index[
            self.data_store[a].curr_name],
        'Indices': lambda self, a: self._save_real_master_index(
            self.data_store[a].curr_name),
    }
    def _activeModsFirst(self, items):
        if self.selectedFirst:
            items.sort(key=lambda x: self.data_store[x].curr_name not in set(
                load_order.cached_active_tuple()) | bosh.modInfos.imported
                                           | bosh.modInfos.merged)
    _extra_sortings = [_ModsUIList._sortEsmsFirst, _activeModsFirst]
    _sunkenBorder, _singleCell = False, True
    #--Labels
    labels = OrderedDict([
        (u'File',          lambda self, mi: bosh.modInfos.masterWithVersion(
            self.data_store[mi].curr_name.s)),
        (u'Num',           lambda self, mi: u'%02X' % mi),
        (u'Current Order', lambda self, mi: bosh.modInfos.hexIndexString(
            self.data_store[mi].curr_name)),
        ('Indices', lambda self, mi: self._save_real_master_hex(
            self.data_store[mi].curr_name)),
    ])
    # True if we should highlight masters whose stored size does not match the
    # size of the plugin on disk
    _do_size_checks = False

    @property
    def esmsFirst(self):
        # Flip the default for masters, we want to show the order in the save
        # so as to not make renamed/disabled masters 'jump around'
        return (settings.get(self.keyPrefix + u'.esmsFirst', False) or
                self.sort_column in self._esmsFirstCols)

    @property
    def cols(self):
        # using self.__class__.keyPrefix for common saves/mods masters settings
        return settings[self.__class__.keyPrefix + u'.cols']

    message = _(u'Edit/update the masters list? Note that the update process '
                u'may automatically rename some files. Be sure to review the '
                u'changes before saving.')

    def __init__(self, parent, listData=None, keyPrefix=keyPrefix, panel=None,
                 detailsPanel=None):
        #--Data/Items
        self.edited = False
        self.detailsPanel = detailsPanel
        self.fileInfo = None
        self._curr_lo_index = {} # cache, orders missing last alphabetically
        # Caches based on SaveHeader.masters_regular and masters_esl - map
        self._save_lo_regular = {}
        self._save_lo_esl = []
        self._allowEditKey = keyPrefix + u'.allowEdit'
        self.is_inaccurate = False # Mirrors SaveInfo.has_inaccurate_masters
        #--Parent init
        super(MasterList, self).__init__(parent,
                      listData=listData if listData is not None else {},
                      keyPrefix=keyPrefix, panel=panel)

    @property
    def allowEdit(self): return bass.settings.get(self._allowEditKey, False)
    @allowEdit.setter
    def allowEdit(self, val):
        if val and (not self.detailsPanel.allowDetailsEdit or not
               balt.askContinue(
                   self, self.message, self.keyPrefix + u'.update.continue',
                   _(u'Update Masters') + u' ' + _(u'BETA'))):
            return
        bass.settings[self._allowEditKey] = val
        if val:
            self.InitEdit()
        else:
            self.SetFileInfo(self.fileInfo)
            self.detailsPanel.testChanges() # disable buttons if no other edits

    def _handle_select(self, item_key): pass
    def _handle_key_up(self, wrapped_evt): pass

    def OnDClick(self, lb_dex_and_flags):
        if self.mouse_index is None or self.mouse_index < 0:
            return # Nothing was clicked
        sel_curr_name = self.data_store[self.mouse_index].curr_name
        if sel_curr_name not in bosh.modInfos:
            return # Master that is not installed was clicked
        balt.Link.Frame.notebook.SelectPage(u'Mods', sel_curr_name)

    #--Indices column - 'real', runtime indices
    def _save_real_master_index(self, master_name):
        """Returns a sort key for the 'real' index of the specified master
        within this save."""
        if master_name in self._save_lo_regular:
            # For regular masters, just return the index
            return self._save_lo_regular[master_name]
        elif master_name in self._save_lo_esl:
            # For ESL masters, sort them after the last regular master
            return len(self._save_lo_regular) + self._save_lo_esl[master_name]
        else:
            # This could potentially happen if we rename a save master
            return sys.maxsize

    def _save_real_master_hex(self, master_name):
        """Returns the 'real' index of the specified master within this save,
        i.e. the FormID prefix it had at the time the save was created. Compare
        ModInfo.real_index[_string]."""
        if master_name in self._save_lo_regular:
            return '%02X' % self._save_lo_regular[master_name]
        elif master_name in self._save_lo_esl:
            return 'FE %03X' % self._save_lo_esl[master_name]
        else:
            return ''

    #--Set ModInfo
    def SetFileInfo(self,fileInfo):
        self.ClearSelected()
        self.edited = False
        self.fileInfo = fileInfo
        self.data_store.clear()
        self.DeleteAll()
        #--Null fileInfo?
        if not fileInfo:
            return
        #--Fill data and populate
        self.is_inaccurate = fileInfo.has_inaccurate_masters
        has_sizes = bush.game.Esp.check_master_sizes and isinstance(
            fileInfo, bosh.ModInfo) # only mods have master sizes
        for mi, masters_name in enumerate(fileInfo.masterNames):
            masters_size = fileInfo.header.master_sizes[mi] if has_sizes else 0
            self.data_store[mi] = bosh.MasterInfo(masters_name, masters_size)
        self._reList()
        self._update_real_indices(fileInfo)
        self.PopulateItems()

    #--Get Master Status
    def GetMasterStatus(self, mi):
        masterInfo = self.data_store[mi]
        masters_name = masterInfo.curr_name
        status = masterInfo.getStatus()
        if status == 30: return status # does not exist
        # current load order of master relative to other masters
        loadOrderIndex = self._curr_lo_index[masters_name]
        ordered = load_order.cached_active_tuple()
        if mi != loadOrderIndex: # there are active masters out of order
            return 20  # orange
        elif status > 0:
            return status  # never happens
        elif (mi < len(ordered)) and (ordered[mi] == masters_name):
            return -10  # Blue
        else:
            return status  # 0, Green

    def set_item_format(self, mi, item_format, target_ini_setts):
        masterInfo = self.data_store[mi]
        masters_name = masterInfo.curr_name
        #--Font color
        fileBashTags = masterInfo.getBashTags()
        mouseText = u''
        # Text foreground
        if masters_name in bosh.modInfos.bashed_patches:
            item_format.text_key = u'mods.text.bashedPatch'
            mouseText += _(u'Bashed Patch. ')
            if masterInfo.is_esl(): # ugh, copy-paste from below
                mouseText += _(u'Light plugin. ')
        elif masters_name in bosh.modInfos.mergeable:
            if u'NoMerge' in fileBashTags and not bush.game.check_esl:
                item_format.text_key = u'mods.text.noMerge'
                mouseText += _(u'Technically mergeable, but has NoMerge tag. ')
            else:
                item_format.text_key = u'mods.text.mergeable'
                if bush.game.check_esl:
                    mouseText += _(u'Can be ESL-flagged. ')
                else:
                    # Merged plugins won't be in master lists
                    mouseText += _(u'Can be merged into Bashed Patch. ')
        else:
            # NoMerge / Mergeable should take priority over ESL/ESM color
            final_text_key = u'mods.text.es'
            if masterInfo.is_esl():
                final_text_key += u'l'
                mouseText += _(u'Light plugin. ')
            if load_order.in_master_block(masterInfo):
                final_text_key += u'm'
                mouseText += _(u'Master plugin. ')
            # Check if it's special, leave ESPs alone
            if final_text_key != u'mods.text.es':
                item_format.text_key = final_text_key
        # Text background
        if masters_name.s in bosh.modInfos.activeBad: # if active, it's in LO
            item_format.back_key = u'mods.bkgd.doubleTime.load'
            mouseText += _(u'Plugin name incompatible, will not load. ')
        elif bosh.modInfos.isBadFileName(masters_name.s): # might not be in LO
            item_format.back_key = u'mods.bkgd.doubleTime.exists'
            mouseText += _(u'Plugin name incompatible, cannot be activated. ')
        elif masterInfo.hasActiveTimeConflict():
            item_format.back_key = u'mods.bkgd.doubleTime.load'
            mouseText += _(u'Another plugin has the same timestamp. ')
        elif masterInfo.hasTimeConflict():
            item_format.back_key = u'mods.bkgd.doubleTime.exists'
            mouseText += _(u'Another plugin has the same timestamp. ')
        elif masterInfo.is_ghost:
            item_format.back_key = u'mods.bkgd.ghosted'
            mouseText += _(u'Plugin is ghosted. ')
        elif self._do_size_checks and bosh.modInfos.size_mismatch(
                masters_name, masterInfo.stored_size):
            item_format.back_key = u'mods.bkgd.size_mismatch'
            mouseText += _(u'Stored size does not match the one on disk. ')
        if self.allowEdit:
            if masterInfo.old_name in settings[u'bash.mods.renames']:
                item_format.strong = True
        #--Image
        status = self.GetMasterStatus(mi)
        oninc = load_order.cached_is_active(masters_name) or (
            masters_name in bosh.modInfos.merged and 2)
        on_display = self.detailsPanel.displayed_item
        if status == 30: # master is missing
            mouseText += _(u'Missing master of %s.  ') % on_display
        #--HACK - load order status
        elif on_display in bosh.modInfos:
            if status == 20:
                mouseText += _(u'Reordered relative to other masters.  ')
            lo_index = load_order.cached_lo_index
            if lo_index(on_display) < lo_index(masters_name):
                mouseText += _(u'Loads after %s.  ') % on_display
                status = 20 # paint orange
        item_format.icon_key = status, oninc
        self.mouseTexts[mi] = mouseText

    #--Relist
    def _reList(self):
        fileOrderNames = [v.curr_name for v in self.data_store.values()]
        self._curr_lo_index = {p: i for i, p in enumerate(
            load_order.get_ordered(fileOrderNames))}

    def _update_real_indices(self, new_file_info):
        """Updates the 'real' indices cache. Does nothing outside of saves."""

    #--InitEdit
    def InitEdit(self):
        #--Pre-clean
        edited = False
        for mi, masterInfo in self.data_store.items():
            newName = settings[u'bash.mods.renames'].get(
                masterInfo.curr_name, None)
            #--Rename?
            if newName and newName in bosh.modInfos:
                masterInfo.set_name(newName)
                edited = True
        #--Done
        if edited: self.SetMasterlistEdited(repopulate=True)

    def SetMasterlistEdited(self, repopulate=False):
        self._reList()
        if repopulate: self.PopulateItems()
        self.edited = True
        self.detailsPanel.SetEdited() # inform the details panel

    #--Column Menu
    def DoColumnMenu(self, evt_col):
        if self.fileInfo: super(MasterList, self).DoColumnMenu(evt_col)
        return EventResult.FINISH

    def _handle_left_down(self, wrapped_evt, lb_dex_and_flags):
        if self.allowEdit: self.InitEdit()

    #--Events: Label Editing
    def OnBeginEditLabel(self, evt_label, uilist_ctrl):
        if not self.allowEdit: return EventResult.CANCEL
        # pass event on (for label editing)
        return super(MasterList, self).OnBeginEditLabel(evt_label, uilist_ctrl)

    def _rename_type(self):
        """Check if the operation is allowed and return ModInfo as the item
        type of the selected label to be renamed."""
        to_rename = self.GetSelected()
        return (to_rename and ModInfo) or None

    def OnLabelEdited(self, is_edit_cancelled, evt_label, evt_index, evt_item):
        newName = GPath(evt_label)
        #--No change?
        if newName in bosh.modInfos:
            masterInfo = self.data_store[evt_item]
            masterInfo.set_name(newName)
            self.SetMasterlistEdited()
            settings[u'bash.mods.renames'][masterInfo.old_name] = newName
            # populate, refresh must be called last
            self.PopulateItem(itemDex=evt_index)
            return EventResult.FINISH ##: needed?
        elif newName == u'':
            return EventResult.CANCEL
        else:
            balt.showError(self, _(u'File %s does not exist.') % newName)
            return EventResult.CANCEL

    #--GetMasters
    def GetNewMasters(self):
        """Returns new master list."""
        return [v.curr_name for k, v in dict_sort(self.data_store)]

#------------------------------------------------------------------------------
class INIList(balt.UIList):
    column_links = Links()  #--Column menu
    context_links = Links()  #--Single item menu
    global_links = defaultdict(lambda: Links()) # Global menu
    _shellUI = True
    _sort_keys = {
        u'File'     : None,
        u'Installer': lambda self, a: self.data_store[a].get_table_prop(
            u'installer', u''),
    }
    def _sortValidFirst(self, items):
        if settings[u'bash.ini.sortValid']:
            items.sort(key=lambda a: self.data_store[a].tweak_status() < 0)
    _extra_sortings = [_sortValidFirst]
    #--Labels
    labels = OrderedDict([
        (u'File',      lambda self, p: p.s),
        (u'Installer', lambda self, p: self.data_store[p].get_table_prop(
            u'installer', u'')),
    ])
    _target_ini = True # pass the target_ini settings on PopulateItem

    @property
    def current_ini_name(self): return self.panel.detailsPanel.ini_name

    def CountTweakStatus(self):
        """Returns number of each type of tweak, in the
        following format:
        (applied,mismatched,not_applied,invalid)"""
        applied = 0
        mismatch = 0
        not_applied = 0
        invalid = 0
        for ini_info in self.data_store.values():
            status = ini_info.tweak_status()
            if status == -10: invalid += 1
            elif status == 0: not_applied += 1
            elif status == 10: mismatch += 1
            elif status == 20: applied += 1
        return applied,mismatch,not_applied,invalid

    def ListTweaks(self):
        """Returns text list of tweaks"""
        tweaklist = _(u'Active Ini Tweaks:') + u'\n'
        tweaklist += u'[spoiler]\n'
        for tweak, info in dict_sort(self.data_store):
            if not info.tweak_status() == 20: continue
            tweaklist+= u'%s\n' % tweak
        tweaklist += u'[/spoiler]\n'
        return tweaklist

    @staticmethod
    def filterOutDefaultTweaks(ini_tweaks):
        """Filter out default tweaks from tweaks iterable."""
        return [x for x in ini_tweaks if not bosh.iniInfos[x].is_default_tweak]

    def _toDelete(self, items):
        items = super(INIList, self)._toDelete(items)
        return self.filterOutDefaultTweaks(items)

    def set_item_format(self, ini_name, item_format, target_ini_setts):
        iniInfo = self.data_store[ini_name]
        status = iniInfo.tweak_status(target_ini_setts)
        #--Image
        checkMark = 0
        icon = 0    # Ok tweak, not applied
        mousetext = u''
        if status == 20:
            # Valid tweak, applied
            checkMark = 1
            mousetext = _(u'Tweak is currently applied.')
        elif status == 15:
            # Valid tweak, some settings applied, others are
            # overwritten by values in another tweak from same installer
            checkMark = 3
            mousetext = _(u'Some settings are applied.  Some are overwritten by another tweak from the same installer.')
        elif status == 10:
            # Ok tweak, some parts are applied, others not
            icon = 10
            checkMark = 3
            mousetext = _(u'Some settings are changed.')
        elif status < 0:
            # Bad tweak
            if not iniInfo.is_applicable(status):
                icon = 20
                mousetext = _(u'Tweak is invalid')
            else:
                icon = 0
                mousetext = _(u'Tweak adds new settings')
        if iniInfo.is_default_tweak:
            mousetext = _(u'Default Bash Tweak') + (
                (u'.  ' + mousetext) if mousetext else u'')
            item_format.italics = True
        self.mouseTexts[ini_name] = mousetext
        item_format.icon_key = icon, checkMark
        #--Font/BG Color
        if status < 0:
            item_format.back_key = u'ini.bkgd.invalid'

    def _handle_left_down(self, wrapped_evt, lb_dex_and_flags):
        """Handle click on icon events
        :param wrapped_evt:
        """
        ini_inf = self._get_info_clicked(lb_dex_and_flags, on_icon=True)
        if ini_inf and self.apply_tweaks([ini_inf]):
            self.panel.ShowPanel()

    @classmethod
    def apply_tweaks(cls, tweak_infos, target_ini=None):
        target_ini_file = target_ini or bosh.iniInfos.ini
        if not cls.ask_create_target_ini(target_ini_file) or not \
                cls._warn_tweak_game_ini(target_ini_file.abs_path.stail):
            return False
        needsRefresh = False
        for ini_info in tweak_infos:
            #--No point applying a tweak that's already applied
            if target_ini: # if target was given calculate the status for it
                stat = ini_info.getStatus(target_ini_file)
                ini_info.reset_status() # iniInfos.ini may differ from target
            else: stat = ini_info.tweak_status()
            if stat == 20 or not ini_info.is_applicable(stat): continue
            needsRefresh |= target_ini_file.applyTweakFile(
                ini_info.read_ini_content())
        return needsRefresh

    @staticmethod
    @balt.conversation
    def ask_create_target_ini(target_ini_file, msg=None):
        """Check if target ini for operation exists - if not and the target is
        the game ini ask if the user wants to create it by copying the default
        ini"""
        msg = target_ini_file.target_ini_exists(msg)
        if msg in (True, False): return msg
        # Game ini does not exist - try copying the default game ini
        default_ini = bass.dirs[u'app'].join(bush.game.Ini.default_ini_file)
        if default_ini.exists():
            msg += _(u'Do you want Bash to create it by copying '
                     u'%(default_ini)s ?') % {u'default_ini': default_ini}
            if not balt.askYes(None, msg, _(u'Missing game Ini')):
                return False
        else:
            msg += _(u'Please create it manually to continue.')
            balt.showError(None, msg, _(u'Missing game Ini'))
            return False
        try:
            default_ini.copyTo(target_ini_file.abs_path)
            if balt.Link.Frame.iniList:
                balt.Link.Frame.iniList.panel.ShowPanel()
            else:
                bosh.iniInfos.refresh(refresh_infos=False)
            return True
        except OSError:
            error_msg = u'Failed to copy %s to %s' % (
                default_ini, target_ini_file.abs_path)
            deprint(error_msg, traceback=True)
            balt.showError(None, error_msg, _(u'Missing game Ini'))
        return False

    @staticmethod
    @balt.conversation
    def _warn_tweak_game_ini(chosen):
        ask = True
        if chosen in bush.game.Ini.dropdown_inis:
            message = (_(u'Apply an ini tweak to %s?') % chosen + u'\n\n' + _(
                u'WARNING: Incorrect tweaks can result in CTDs and even '
                u'damage to your computer!'))
            ask = balt.askContinue(balt.Link.Frame, message,
                                   u'bash.iniTweaks.continue', _(u'INI Tweaks'))
        return ask

#------------------------------------------------------------------------------
class INITweakLineCtrl(INIListCtrl):

    def __init__(self, parent, iniContents):
        super(INITweakLineCtrl, self).__init__(parent)
        self.tweakLines = []
        self.iniContents = self._contents = iniContents

    def _get_selected_line(self, index): return self.tweakLines[index][5]

    def refresh_tweak_contents(self, tweakPath):
        # Make sure to freeze/thaw, all the InsertItem calls make the GUI lag
        self.Freeze()
        self._RefreshTweakLineCtrl(tweakPath)
        self.Thaw()

    def _RefreshTweakLineCtrl(self, tweakPath):
        # Clear the list, then populate it with the new lines
        self.DeleteAllItems()
        if tweakPath is None:
            return
        # TODO(ut) avoid if ini tweak did not change
        self.tweakLines = bosh.iniInfos.get_tweak_lines_infos(tweakPath)
        updated_line_nums = set()
        for i,line in enumerate(self.tweakLines):
            #--Line
            self.InsertItem(i, line[0])
            #--Line color
            status, deleted = line[4], line[6]
            if status == -10: color = colors[u'tweak.bkgd.invalid']
            elif status == 10: color = colors[u'tweak.bkgd.mismatched']
            elif status == 20: color = colors[u'tweak.bkgd.matched']
            elif deleted: color = colors[u'tweak.bkgd.mismatched']
            else: color = Color.from_wx(self.GetBackgroundColour())
            color = color.to_rgba_tuple()
            self.SetItemBackgroundColour(i, color)
            #--Set iniContents color
            lineNo = line[5]
            if lineNo != -1:
                self.iniContents.SetItemBackgroundColour(lineNo,color)
                updated_line_nums.add(lineNo)
        #--Reset line color for other iniContents lines
        background_color = self.iniContents.GetBackgroundColour()
        for i in range(self.iniContents.GetItemCount()):
            if i in updated_line_nums: continue
            if self.iniContents.GetItemBackgroundColour(i) != background_color:
                self.iniContents.SetItemBackgroundColour(i, background_color)
        #--Refresh column width
        self.fit_column_to_header(0)

#------------------------------------------------------------------------------
class TargetINILineCtrl(INIListCtrl):

    def SetTweakLinesCtrl(self, control):
        self._contents = control

    def _get_selected_line(self, index):
        for i, line in enumerate(self._contents.tweakLines):
            if index == line[5]: return i
        return -1

    def refresh_ini_contents(self):
        # Make sure to freeze/thaw, all the InsertItem calls make the GUI lag
        self.Freeze()
        self._RefreshIniContents()
        self.Thaw()

    def _RefreshIniContents(self):
        if bosh.iniInfos.ini.isCorrupted: return
        # Clear the list, then populate it with the new lines
        self.DeleteAllItems()
        main_ini_selected = (bush.game.Ini.dropdown_inis[0] ==
                             bosh.iniInfos.ini.abs_path.stail)
        try:
            sel_ini_lines = bosh.iniInfos.ini.read_ini_content()
            if main_ini_selected: # If we got here, reading the INI worked
                Link.Frame.oblivionIniMissing = False
            for i, line in enumerate(sel_ini_lines):
                self.InsertItem(i, line.rstrip())
        except OSError:
            if main_ini_selected:
                Link.Frame.oblivionIniMissing = True
        self.fit_column_to_header(0)

#------------------------------------------------------------------------------
class ModList(_ModsUIList):
    #--Class Data
    column_links = Links() #--Column menu
    context_links = Links() #--Single item menu
    global_links = defaultdict(lambda: Links()) # Global menu
    _sort_keys = {
        u'File'      : None,
        u'Author'    : lambda self, a:self.data_store[a].header.author.lower(),
        u'Rating'    : lambda self, a: self.data_store[a].get_table_prop(
                            u'rating', u''),
        u'Group'     : lambda self, a: self.data_store[a].get_table_prop(
                            u'group', u''),
        u'Installer' : lambda self, a: self.data_store[a].get_table_prop(
                            u'installer', u''),
        u'Load Order': lambda self, a: load_order.cached_lo_index_or_max(a),
        u'Indices'   : lambda self, a: self.data_store[a].real_index(),
        u'Modified'  : lambda self, a: self.data_store[a].mtime,
        u'Size'      : lambda self, a: self.data_store[a].fsize,
        u'Status'    : lambda self, a: self.data_store[a].getStatus(),
        u'Mod Status': lambda self, a: self.data_store[a].txt_status(),
        u'CRC'       : lambda self, a: self.data_store[a].cached_mod_crc(),
    }
    _extra_sortings = [_ModsUIList._sortEsmsFirst,
                       _ModsUIList._activeModsFirst]
    _dndList, _dndColumns = True, [u'Load Order']
    _sunkenBorder = False
    #--Labels
    labels = OrderedDict([
        (u'File',       lambda self, p:self.data_store.masterWithVersion(p.s)),
        (u'Load Order', lambda self, p: self.data_store.hexIndexString(p)),
        (u'Indices',    lambda self, p:self.data_store[p].real_index_string()),
        (u'Rating',     lambda self, p: self.data_store[p].get_table_prop(
                            u'rating', u'')),
        (u'Group',      lambda self, p: self.data_store[p].get_table_prop(
                            u'group', u'')),
        (u'Installer',  lambda self, p: self.data_store[p].get_table_prop(
                            u'installer', u'')),
        (u'Modified',   lambda self, p: format_date(self.data_store[p].mtime)),
        (u'Size',       lambda self, p: round_size(self.data_store[p].fsize)),
        (u'Author',     lambda self, p: self.data_store[p].header.author if
                                       self.data_store[p].header else u'-'),
        (u'CRC',        lambda self, p: self.data_store[p].crc_string()),
        (u'Mod Status', lambda self, p: self.data_store[p].txt_status()),
    ])
    _copy_paths = True

    #-- Drag and Drop-----------------------------------------------------
    def _dropIndexes(self, indexes, newIndex): # will mess with plugins cache !
        """Drop contiguous indexes on newIndex and return True if LO changed"""
        if newIndex < 0:
            return False # from _handle_key_down() & moving master esm up
        count = self.item_count
        dropItem = self.GetItem(newIndex if (count > newIndex) else count - 1)
        firstItem = self.GetItem(indexes[0])
        lastItem = self.GetItem(indexes[-1])
        return bosh.modInfos.dropItems(dropItem, firstItem, lastItem)

    def OnDropIndexes(self, indexes, newIndex):
        if self._dropIndexes(indexes, newIndex):
            # Take all indices into account - we may be moving plugins up, in
            # which case the smallest index is in indexes, or we may be moving
            # plugins down, in which case the smallest index is newIndex
            lowest_index = min(newIndex, min(indexes))
            self._refreshOnDrop(lowest_index)

    def dndAllow(self, event):
        msg = u''
        continue_key = u'bash.mods.dnd.column.continue'
        if not self.sort_column in self._dndColumns:
            msg = _(u'Reordering mods is only allowed when they are sorted '
                    u'by Load Order.')
        else:
            pinned = load_order.filter_pinned(self.GetSelected())
            if pinned:
                msg = (_(u"You can't reorder the following mods:") + u'\n' +
                       u', '.join(str(s) for s in pinned))
                continue_key = u'bash.mods.dnd.pinned.continue'
        if msg:
            balt.askContinue(self, msg, continue_key)
            return super(ModList, self).dndAllow(event) # disallow
        return True

    @balt.conversation
    def _refreshOnDrop(self, first_index):
        #--Save and Refresh
        try:
            bosh.modInfos.cached_lo_save_all()
        except BoltError as e:
            balt.showError(self, u'%s' % e)
        first_impacted = load_order.cached_lo_tuple()[first_index]
        self.RefreshUI(redraw=self._lo_redraw_targets({first_impacted}),
                       refreshSaves=True)

    #--Populate Item
    def set_item_format(self, mod_name, item_format, target_ini_setts):
        mod_info = self.data_store[mod_name]
        #--Image
        status = mod_info.getStatus()
        checkMark = (load_order.cached_is_active(mod_name) # 1
            or (mod_name in bosh.modInfos.merged and 2)
            or (mod_name in bosh.modInfos.imported and 3)) # or 0
        status_image_key = 20 if 20 <= status < 30 else status
        item_format.icon_key = status_image_key, checkMark
        #--Default message
        mouseText = u''
        fileBashTags = mod_info.getBashTags()
        # Text foreground
        if mod_name in bosh.modInfos.activeBad:
            mouseText += _(u'Plugin name incompatible, will not load. ')
        if mod_name in bosh.modInfos.bad_names:
            mouseText += _(u'Plugin name incompatible, cannot be activated. ')
        if mod_name in bosh.modInfos.missing_strings:
            mouseText += _(u'Plugin is missing string localization files. ')
        if mod_name in bosh.modInfos.bashed_patches:
            item_format.text_key = u'mods.text.bashedPatch'
            mouseText += _(u'Bashed Patch. ')
            if mod_info.is_esl(): # ugh, copy-paste from below
                mouseText += _(u'Light plugin. ')
        elif mod_name in bosh.modInfos.mergeable:
            if u'NoMerge' in fileBashTags and not bush.game.check_esl:
                item_format.text_key = u'mods.text.noMerge'
                mouseText += _(u'Technically mergeable, but has NoMerge tag. ')
            else:
                item_format.text_key = u'mods.text.mergeable'
                if bush.game.check_esl:
                    mouseText += _(u'Can be ESL-flagged. ')
                else:
                    if checkMark == 2:
                        mouseText += _(u'Merged into Bashed Patch. ')
                    else:
                        mouseText += _(u'Can be merged into Bashed Patch. ')
        else:
            # NoMerge / Mergeable should take priority over ESL/ESM color
            final_text_key = u'mods.text.es'
            if mod_info.is_esl():
                final_text_key += u'l'
                mouseText += _(u'Light plugin. ')
            if load_order.in_master_block(mod_info):
                final_text_key += u'm'
                mouseText += _(u'Master plugin. ')
            # Check if it's special, leave ESPs alone
            if final_text_key != u'mods.text.es':
                item_format.text_key = final_text_key
        # Mirror the checkbox color info in the status bar
        if status == 30:
            mouseText += _(u'One or more masters are missing. ')
        else:
            if status in {20, 21}:
                mouseText += _(u'Loads before its master(s). ')
            if status in {10, 21}:
                mouseText += _(u'Masters have been re-ordered. ')
        if checkMark == 1:   mouseText += _(u'Active in load order. ')
        elif checkMark == 3: mouseText += _(u'Imported into Bashed Patch. ')
        if u'Deactivate' in fileBashTags:
            item_format.italics = True
        # Text background
        if mod_name in bosh.modInfos.activeBad:
            item_format.back_key = u'mods.bkgd.doubleTime.load'
        elif mod_name in bosh.modInfos.bad_names:
            item_format.back_key = u'mods.bkgd.doubleTime.exists'
        elif mod_name in bosh.modInfos.missing_strings:
            if load_order.cached_is_active(mod_name):
                item_format.back_key = u'mods.bkgd.doubleTime.load'
            else:
                item_format.back_key = u'mods.bkgd.doubleTime.exists'
        elif mod_info.hasBadMasterNames():
            if load_order.cached_is_active(mod_name):
                item_format.back_key = u'mods.bkgd.doubleTime.load'
            else:
                item_format.back_key = u'mods.bkgd.doubleTime.exists'
            mouseText += _(u'Has master names that will not load. ')
        elif mod_info.hasActiveTimeConflict():
            item_format.back_key = u'mods.bkgd.doubleTime.load'
            mouseText += _(u'Another plugin has the same timestamp. ')
        elif u'Deactivate' in fileBashTags and checkMark == 1:
            item_format.back_key = u'mods.bkgd.deactivate'
            mouseText += _(u'Mod should be imported and deactivated. ')
        elif mod_info.hasTimeConflict():
            item_format.back_key = u'mods.bkgd.doubleTime.exists'
            mouseText += _(u'Another plugin has the same timestamp. ')
        elif mod_info.isGhost:
            item_format.back_key = u'mods.bkgd.ghosted'
            mouseText += _(u'Plugin is ghosted. ')
        elif (bush.game.Esp.check_master_sizes
              and mod_info.has_master_size_mismatch()):
            item_format.back_key = u'mods.bkgd.size_mismatch'
            mouseText += _(u'Has size-mismatched master(s). ')
        if settings[u'bash.mods.scanDirty']:
            message = mod_info.getDirtyMessage()
            mouseText += message[1]
            if message[0]: item_format.underline = True
        self.mouseTexts[mod_name] = mouseText

    def RefreshUI(self, **kwargs):
        """Refresh UI for modList - always specify refreshSaves explicitly."""
        super(ModList, self).RefreshUI(**kwargs)
        if kwargs.pop(u'refreshSaves', False):
            Link.Frame.saveListRefresh(focus_list=False)

    #--Events ---------------------------------------------
    def OnDClick(self, lb_dex_and_flags):
        """Handle doubleclicking a mod in the Mods List."""
        modInfo = self._get_info_clicked(lb_dex_and_flags)
        if not modInfo: return
        if not Link.Frame.docBrowser:
            from .frames import DocBrowser
            DocBrowser().show_frame()
            settings[u'bash.modDocs.show'] = True
        Link.Frame.docBrowser.SetMod(modInfo.ci_key)
        Link.Frame.docBrowser.raise_frame()

    def _handle_key_down(self, wrapped_evt):
        """Char event: Reorder (Ctrl+Up and Ctrl+Down)."""
        def undo_redo_op(lo_op):
            # Grab copies of the old LO/actives for find_first_difference
            prev_lo = load_order.cached_lo_tuple()
            prev_acti = load_order.cached_active_tuple()
            if not lo_op(): return # nothing to do
            curr_lo = load_order.cached_lo_tuple()
            curr_acti = load_order.cached_active_tuple()
            low_diff = load_order.find_first_difference(
                prev_lo, prev_acti, curr_lo, curr_acti)
            if low_diff is None: return # load orders were identical
            # Finally, we pass to _lo_redraw_targets to take all other relevant
            # details into account
            self.RefreshUI(redraw=self._lo_redraw_targets({curr_lo[low_diff]}),
                           refreshSaves=True)
        kcode = wrapped_evt.key_code
        if wrapped_evt.is_cmd_down and kcode in balt.wxArrows:
            if not self.dndAllow(event=None): return
            # Calculate continuous chunks of indexes
            chunk, chunks, indexes = 0, [[]], self.GetSelectedIndexes()
            previous = -1
            for dex in indexes:
                if previous != -1 and previous + 1 != dex:
                    chunk += 1
                    chunks.append([])
                previous = dex
                chunks[chunk].append(dex)
            moveMod = 1 if kcode in balt.wxArrowDown else -1
            moved = False
            # Initialize the lowest index to the smallest existing one (we
            # won't ever beat this one if we are moving indices up)
            lowest_index = min(indexes)
            for chunk in chunks:
                if not chunk: continue # nothing to move, skip
                newIndex = chunk[0] + moveMod
                if chunk[-1] + moveMod == self.item_count:
                    continue # trying to move last plugin past the list
                # Check if moving hits a new lowest index (this is the case if
                # we are moving indices down)
                lowest_index = min(lowest_index, newIndex)
                moved |= self._dropIndexes(chunk, newIndex)
            if moved: self._refreshOnDrop(lowest_index)
        # Ctrl+Z: Undo last load order or active plugins change
        elif wrapped_evt.is_cmd_down and kcode == ord(u'Z'):
            undo_redo_op(self.data_store.redo_load_order
                         if wrapped_evt.is_shift_down
                         else self.data_store.undo_load_order)
        # Ctrl+Y: Redo last load order or active plugins change
        elif wrapped_evt.is_cmd_down and kcode == ord(u'Y'):
            undo_redo_op(self.data_store.redo_load_order)
        else: # correctly update the highlight around selected mod
            return EventResult.CONTINUE
        # Otherwise we'd jump to a random plugin that starts with the key code
        return EventResult.FINISH

    def _handle_key_up(self, wrapped_evt):
        """Char event: Activate selected items, select all items"""
        ##Space
        if wrapped_evt.is_space:
            selected = self.GetSelected()
            toActivate = [item for item in selected if
                          not load_order.cached_is_active(item)]
            # If none are checked or all are checked, then toggle the selection
            # Otherwise, check all that aren't
            toggle_target = (selected if len(toActivate) == 0 or
                                         len(toActivate) == len(selected)
                             else toActivate)
            self._toggle_active_state(*toggle_target)
        super(ModList, self)._handle_key_up(wrapped_evt)

    def _handle_left_down(self, wrapped_evt, lb_dex_and_flags):
        """Left Down: Check/uncheck mods.
        :param wrapped_evt:
        """
        mod_clicked_on_icon = self._getItemClicked(lb_dex_and_flags,
                                                   on_icon=True)
        if mod_clicked_on_icon:
            self._toggle_active_state(mod_clicked_on_icon)
            # _handle_select no longer seems to fire for the wrong index, but
            # deselecting the others is still the better behavior here
            self.SelectAndShowItem(mod_clicked_on_icon, deselectOthers=True,
                                   focus=True)
            return EventResult.FINISH
        else:
            mod_clicked = self._getItemClicked(lb_dex_and_flags)
            if wrapped_evt.is_alt_down and mod_clicked:
                if self.jump_to_mods_installer(mod_clicked): return
            # Pass Event onward to _handle_select

    def _select(self, modName):
        super(ModList, self)._select(modName)
        if Link.Frame.docBrowser:
            Link.Frame.docBrowser.SetMod(modName)

    @staticmethod
    def _unhide_wildcard():
        return bosh.modInfos.plugin_wildcard()

    #--Helpers ---------------------------------------------
    @staticmethod
    def _lo_redraw_targets(impacted_plugins):
        """Given a set of plugins (as paths) that were impacted by a load order
        operation, returns a set UIList keys (as paths) for elements that need
        to be redrawn."""
        ui_impacted = impacted_plugins.copy()
        ##: We have to refresh every active plugin that loads higher than
        # the lowest-loading one that was (un)checked as well since their
        # load order/index columns will change. A full refresh is complete
        # overkill for this, but alas... -> #353
        if len(ui_impacted) == 1:
            lowest_impacted = next(iter(ui_impacted)) # fast path
        else:
            lowest_impacted = min(ui_impacted,
                                  key=load_order.cached_lo_index_or_max)
        ui_impacted.update(load_order.cached_higher_loading(lowest_impacted))
        # If the touched plugins include BPs, we need to refresh their
        # imported/merged plugins too (checkbox icons). Note that we can do
        # this after the lowest-loading check above, because the
        # imported/merged plugins will not affect any other plugins if they
        # aren't active, and won't need an update if they are active.
        ui_imported, ui_merged = bosh.modInfos.getSemiActive(
            ui_impacted, skip_active=True)
        return ui_impacted | ui_imported | ui_merged

    @balt.conversation
    def _toggle_active_state(self, *mods):
        """Toggle active state of mods given - all mods must be either
        active or inactive."""
        active = [mod for mod in mods if load_order.cached_is_active(mod)]
        assert not active or len(active) == len(mods) # empty or all
        inactive = (not active and mods) or []
        changes = collections.defaultdict(dict)
        # Track which plugins we activated or deactivated
        touched = set()
        # Deactivate ?
        # Track illegal deactivations for the return value
        illegal_deactivations = []
        for act in active:
            if act in touched: continue # already deactivated
            try:
                changed = self.data_store.lo_deactivate(act, doSave=False)
                if not changed:
                    # Can't deactivate that mod, track this
                    illegal_deactivations.append(act.s)
                    continue
                touched |= changed
                if len(changed) > (act in changed): # deactivated dependents
                    changed = [x for x in changed if x != act]
                    changes[self.__deactivated_key][act] = \
                        load_order.get_ordered(changed)
            except BoltError as e:
                balt.showError(self, u'%s' % e)
        # Activate ?
        # Track illegal activations for the return value
        illegal_activations = []
        for inact in inactive:
            if inact in touched: continue # already activated
            ## For now, allow selecting unicode named files, for testing
            ## I'll leave the warning in place, but maybe we can get the
            ## game to load these files.s
            #if fileName in self.data_store.bad_names: return
            try:
                activated = self.data_store.lo_activate(inact, doSave=False)
                if not activated:
                    # Can't activate that mod, track this
                    illegal_activations.append(inact.s)
                    continue
                touched |= set(activated)
                if len(activated) > (inact in activated): # activated masters
                    activated = [x for x in activated if x != inact]
                    changes[self.__activated_key][inact] = activated
            except BoltError as e:
                balt.showError(self, u'%s' % e)
                break
        # Show warnings to the user if they attempted to deactivate mods that
        # can't be deactivated (e.g. vanilla masters on newer games) and/or
        # attempted to activate mods that can't be activated (e.g. .esu
        # plugins).
        if illegal_deactivations:
            balt.askContinue(self,
                _(u"You can't deactivate the following mods:")
                + u'\n%s' % u', '.join(illegal_deactivations),
                u'bash.mods.dnd.illegal_deactivation.continue')
        if illegal_activations:
            balt.askContinue(self,
                _(u"You can't activate the following mods:")
                + u'\n%s' % u', '.join(illegal_activations),
                u'bash.mods.dnd.illegal_activation.continue')
        if touched:
            bosh.modInfos.cached_lo_save_active()
            self.__toggle_active_msg(changes)
            self.RefreshUI(redraw=self._lo_redraw_targets(touched),
                           refreshSaves=True)

    __activated_key = _(u'Masters activated:')
    __deactivated_key = _(u'Children deactivated:')
    def __toggle_active_msg(self, changes_dict):
        masters_activated = changes_dict[self.__activated_key]
        children_deactivated = changes_dict[self.__deactivated_key]
        checklists = []
        # It's one or the other !
        if masters_activated:
            checklists = [self.__activated_key, _(
            u'Wrye Bash automatically activates the masters of activated '
            u'plugins.'), masters_activated]
            msg = _(u'Activating the following plugins caused their masters '
                    u'to be activated')
        elif children_deactivated:
            checklists += [self.__deactivated_key, _(
                u'Wrye Bash automatically deactivates the children of '
                u'deactivated plugins.'), children_deactivated]
            msg = _(u'Deactivating the following plugins caused their '
                    u'children to be deactivated')
        else: return
        ListBoxes.display_dialog(self, _(u'Masters/Children affected'), msg,
                                 [checklists], liststyle=u'tree',
                                 canCancel=False)

    def jump_to_mods_installer(self, modName):
        fn_inst = self.get_installer(modName)
        if fn_inst is None:
            return False
        balt.Link.Frame.notebook.SelectPage(u'Installers', fn_inst)
        return True

    def get_installer(self, modName):
        if not balt.Link.Frame.iPanel or not bass.settings[
            u'bash.installers.enabled']: return None
        installer = self.data_store.table.getColumn(u'installer').get(modName)
        return GPath(installer)

#------------------------------------------------------------------------------
class _DetailsMixin(object):
    """Mixin for panels that display detailed info on mods, saves etc."""

    @property
    def file_info(self): return self.file_infos.get(self.displayed_item, None)
    @property
    def displayed_item(self): raise AbstractError
    @property
    def file_infos(self): raise AbstractError

    def _resetDetails(self): raise AbstractError

    # Details panel API
    def SetFile(self, fileName=u'SAME'):
        """Set file to be viewed. Leave fileName empty to reset.
        :type fileName: str | bolt.Path | None"""
        #--Reset?
        if fileName == u'SAME':
            if self.displayed_item not in self.file_infos:
                fileName = None
            else:
                fileName = self.displayed_item
        elif not fileName or (fileName not in self.file_infos):
            fileName = None
        if not fileName: self._resetDetails()
        return fileName

class _EditableMixin(_DetailsMixin):
    """Mixin for detail panels that allow editing the info they display."""

    def __init__(self, buttonsParent, ui_list_panel):
        self.edited = False
        #--Save/Cancel
        self._save_btn = SaveButton(buttonsParent)
        self._save_btn.on_clicked.subscribe(self.DoSave)
        self._cancel_btn = CancelButton(buttonsParent)
        self._cancel_btn.on_clicked.subscribe(self.DoCancel)
        self._save_btn.enabled = False
        self._cancel_btn.enabled = False

    # Details panel API
    def SetFile(self, fileName=u'SAME'):
        #--Edit State
        self.edited = False
        self._save_btn.enabled = False
        self._cancel_btn.enabled = False
        return super(_EditableMixin, self).SetFile(fileName)

    # Abstract edit methods
    @property
    def allowDetailsEdit(self): raise AbstractError

    def SetEdited(self):
        if not self.displayed_item: return
        self.edited = True
        if self.allowDetailsEdit:
            self._save_btn.enabled = True
        self._cancel_btn.enabled = True

    def DoSave(self): raise AbstractError

    def DoCancel(self): self.SetFile()

class _EditableMixinOnFileInfos(_EditableMixin):
    """Bsa/Mods/Saves details, DEPRECATED: we need common data infos API!"""
    _max_filename_chars = 256
    _min_controls_width = 128
    @property
    def file_info(self): raise AbstractError
    @property
    def displayed_item(self):
        return self.file_info.ci_key if self.file_info else None

    def __init__(self, masterPanel, ui_list_panel):
        # super(_EditableMixinOnFileInfos, self).__init__(masterPanel)
        _EditableMixin.__init__(self, masterPanel, ui_list_panel)
        #--File Name
        self._fname_ctrl = TextField(self.left,
                                     max_length=self._max_filename_chars)
        self._fname_ctrl.on_focus_lost.subscribe(self.OnFileEdited)
        self._fname_ctrl.on_text_changed.subscribe(self.OnFileEdit)
        # TODO(nycz): GUI set_size
        #                       size=(self._min_controls_width, -1))
        self.panel_uilist = ui_list_panel.uiList

    def OnFileEdited(self):
        """Event: Finished editing file name."""
        if not self.file_info: return
        #--Changed?
        fileStr = self._fname_ctrl.text_content
        if fileStr == self.fileStr: return
        #--Validate the filename
        name_path, root = self.file_info.validate_name(fileStr)
        if root is None:
            balt.showError(self, name_path) # it's an error message in this case
            self._fname_ctrl.text_content = self.fileStr
        #--Okay?
        else:
            self.fileStr = fileStr
            self.SetEdited()

    def OnFileEdit(self, new_text):
        """Event: Editing filename."""
        if not self.file_info: return
        if not self.edited and self.fileStr != new_text:
            self.SetEdited()

    @balt.conversation
    def _refresh_detail_info(self):
        try: # use self.file_info.ci_key, as name may have been updated
            # Although we could avoid rereading the header I leave it here as
            # an extra error check - error handling is WIP
            self.panel_uilist.data_store.new_info(self.file_info.ci_key,
                                                  notify_bain=True)
            return self.file_info.ci_key
        except FileError as e:
            deprint(u'Failed to edit details for %s' % self.displayed_item,
                    traceback=True)
            balt.showError(self,
                           _(u'File corrupted on save!') + u'\n' + e.message)
            return None

class _SashDetailsPanel(_DetailsMixin, SashPanel):
    """Details panel with two splitters"""
    _ui_settings = {**SashPanel._ui_settings, **{
        u'.subSplitterSashPos': _UIsetting(lambda self: 0,
        lambda self: self.subSplitter.get_sash_pos(),
        lambda self, sashPos: self.subSplitter.set_sash_pos(sashPos))}
    }

    def __init__(self, parent):
        # call the init of SashPanel - _DetailsMixin hasn't any init
        super(_DetailsMixin, self).__init__(parent, isVertical=False)
        # needed so subpanels do not collapse
        self.subSplitter = self._get_sub_splitter()

    def _get_sub_splitter(self):
        return Splitter(self.right, min_pane_size=64)

class _ModsSavesDetails(_EditableMixinOnFileInfos, _SashDetailsPanel):
    """Mod and Saves details panel, feature a master's list.

    I named the master list attribute 'uilist' to stand apart from the
    uiList of SashUIListPanel. ui_list_panel is mods or saves panel
    :type uilist: MasterList"""
    _master_list_type = MasterList

    def __init__(self, parent, ui_list_panel, split_vertically=False):
        _SashDetailsPanel.__init__(self, parent)
        # min_pane_size split the bottom panel into the master uilist and mod tags/save notes
        self.masterPanel, self._bottom_low_panel = \
            self.subSplitter.make_panes(vertically=split_vertically)
        _EditableMixinOnFileInfos.__init__(self, self.masterPanel,
                                           ui_list_panel)
        #--Masters
        self.uilist = self._master_list_type(
            self.masterPanel, keyPrefix=self.keyPrefix, panel=ui_list_panel,
            detailsPanel=self)
        self._masters_label = Label(self.masterPanel, _(u'Masters:'))
        VLayout(spacing=4, items=[
            self._masters_label,
            (self.uilist, LayoutOptions(weight=1, expand=True)),
            HLayout(spacing=4, items=[self._save_btn, self._cancel_btn])
        ]).apply_to(self.masterPanel)
        VLayout(item_expand=True, item_weight=1,
                items=[self.subSplitter]).apply_to(self.right)

    def ShowPanel(self, **kwargs):
        super(_ModsSavesDetails, self).ShowPanel(**kwargs)
        self.uilist.autosizeColumns()

    def testChanges(self): raise AbstractError

class _ModMasterList(MasterList):
    """Override to avoid doing size checks on save master lists."""
    _do_size_checks = bush.game.Esp.check_master_sizes
    banned_columns = {'Indices'} # The Indices column is Saves-specific

class ModDetails(_ModsSavesDetails):
    """Details panel for mod tab."""
    keyPrefix = u'bash.mods.details' # used in sash/scroll position, sorting
    _master_list_type = _ModMasterList

    @property
    def file_info(self): return self.modInfo
    @property
    def file_infos(self): return bosh.modInfos
    @property
    def allowDetailsEdit(self): return bush.game.Esp.canEditHeader

    def __init__(self, parent, ui_list_panel):
        super(ModDetails, self).__init__(parent, ui_list_panel,
                                         split_vertically=True)
        top, bottom = self.left, self.right
        #--Data
        self.modInfo = None
        textWidth = 200
        #--Version
        self.version = Label(top, u'v0.00')
        #--Author
        # TODO(inf) de-wx! all the size usages below
        self.gAuthor = TextField(top, max_length=511) # size=(textWidth,-1))
        self.gAuthor.on_focus_lost.subscribe(self.OnEditAuthor)
        self.gAuthor.on_text_changed.subscribe(self.OnAuthorEdit)
        #--Modified
        self.modified_txt = TextField(top, max_length=32)
        self.modified_txt.on_focus_lost.subscribe(self.OnEditModified)
        self.modified_txt.on_text_changed.subscribe(self.OnModifiedEdit)
        # size=(textWidth, -1),
        #--Description
        self._desc_area = TextArea(top, auto_tooltip=False, max_length=511)
            # size=(textWidth, 128),
        self._desc_area.on_focus_lost.subscribe(self.OnEditDescription)
        self._desc_area.on_text_changed.subscribe(self.OnDescrEdit)
        #--Bash tags
        ##: Come up with a better solution for this
        class _ExClickableImage(WithMouseEvents, ClickableImage):
            bind_lclick_down = True
        self._add_tag_btn = _ExClickableImage(self._bottom_low_panel,
            'ART_PLUS', no_border=False,
            btn_tooltip=_(u'Add bash tags to this plugin.'))
        self._add_tag_btn.on_mouse_left_down.subscribe(self._popup_add_tags)
        self._rem_tag_btn = ClickableImage(self._bottom_low_panel,
            'ART_MINUS', no_border=False,
            btn_tooltip=_(u'Remove the selected tag(s) from this plugin.'))
        self._rem_tag_btn.on_clicked.subscribe(self._remove_selected_tags)
        self.gTags = ListBox(self._bottom_low_panel, isSort=True,
                             isSingle=False, isExtended=True)
        self.gTags.on_mouse_right_up.subscribe(self._popup_misc_tags)
        #--Layout
        VLayout(spacing=4, item_expand=True, items=[
            HLayout(items=[Label(top, _(u'File:')), Stretch(), self.version]),
            self._fname_ctrl,
            Label(top, _(u'Author:')), self.gAuthor,
            Label(top, _(u'Modified:')), self.modified_txt,
            Label(top, _(u'Description:')),
            (self._desc_area, LayoutOptions(expand=True, weight=1))
        ]).apply_to(top)
        VLayout(spacing=4, item_expand=True, items=[
            HLayout(item_expand=True, items=[
                (Label(self._bottom_low_panel, _(u'Bash Tags:')),
                 LayoutOptions(expand=False, v_align=CENTER)),
                Stretch(), self._add_tag_btn, self._rem_tag_btn,
            ]),
            (self.gTags, LayoutOptions(expand=True, weight=1))
        ]).apply_to(self._bottom_low_panel)

    def _get_sub_splitter(self):
        return Splitter(self.right, min_pane_size=128)

    def _resetDetails(self):
        self.modInfo = None
        self.fileStr = u''
        self.authorStr = u''
        self.modifiedStr = u''
        self.descriptionStr = u''
        self.versionStr = u'v0.00'

    def SetFile(self, fileName=u'SAME'):
        fileName = super(ModDetails, self).SetFile(fileName)
        if fileName:
            modInfo = self.modInfo = bosh.modInfos[fileName]
            #--Remember values for edit checks
            self.fileStr = modInfo.ci_key.s
            self.authorStr = modInfo.header.author
            self.modifiedStr = format_date(modInfo.mtime)
            self.descriptionStr = modInfo.header.description
            self.versionStr = u'v%0.2f' % modInfo.header.version
            minf_tags = list(modInfo.getBashTags())
        else:
            minf_tags = []
        #--Set fields
        self._fname_ctrl.text_content = self.fileStr
        self.gAuthor.text_content = self.authorStr
        self.modified_txt.text_content = self.modifiedStr
        self._desc_area.text_content = self.descriptionStr
        self.version.label_text = self.versionStr
        self.uilist.SetFileInfo(self.modInfo)
        self.gTags.lb_set_items(minf_tags)
        if self.modInfo and not self.modInfo.is_auto_tagged():
            self.gTags.set_background_color(
                self.gAuthor.get_background_color())
        else:
            self.gTags.set_background_color(self.get_background_color())

    def _OnTextEdit(self, old_text, new_text):
        if not self.modInfo: return
        if not self.edited and old_text != new_text: self.SetEdited()

    def OnAuthorEdit(self, new_text):
        self._OnTextEdit(self.authorStr, new_text)
    def OnModifiedEdit(self, new_text):
        self._OnTextEdit(self.modifiedStr, new_text)
    def OnDescrEdit(self, new_text):
        self._OnTextEdit(self.descriptionStr.replace(
            u'\r\n', u'\n').replace(u'\r', u'\n'), new_text)

    def OnEditAuthor(self):
        if not self.modInfo: return
        authorStr = self.gAuthor.text_content
        if authorStr != self.authorStr:
            self.authorStr = authorStr
            self.SetEdited()

    def OnEditModified(self):
        if not self.modInfo: return
        modifiedStr = self.modified_txt.text_content
        if modifiedStr == self.modifiedStr: return
        try:
            newTimeTup = unformat_date(modifiedStr)
            time.mktime(newTimeTup)
        except ValueError:
            balt.showError(self,_(u'Unrecognized date: ')+modifiedStr)
            self.modified_txt.text_content = self.modifiedStr
            return
        #--Normalize format
        modifiedStr = time.strftime(u'%c', newTimeTup)
        self.modifiedStr = modifiedStr
        self.modified_txt.text_content = modifiedStr #--Normalize format
        self.SetEdited()

    def OnEditDescription(self):
        if not self.modInfo: return
        if self._desc_area.text_content != self.descriptionStr.replace(u'\r\n',
                u'\n').replace(u'\r', u'\n'):
            self.descriptionStr = self._desc_area.text_content ##: .replace(u'\n', u'r\n')
            self.SetEdited()

    bsaAndBlocking = _(
        u'This mod has an associated archive (%s) and an associated '
        u'plugin-name-specific directory (e.g. Sound\\Voice\\%s), which will '
        u'become detached when the mod is renamed.') + u'\n\n' + _(
        u'Note that the BSA archive may also contain a plugin-name-specific '
        u'directory, which would remain detached even if the archive name is '
        u'adjusted.')
    bsa = _(
        u'This mod has an associated archive (%s), which will become detached '
        u'when the mod is renamed.') + u'\n\n' + _(
        u'Note that this BSA archive may contain a plugin-name-specific '
        u'directory (e.g. Sound\\Voice\\%s), which would remain detached even '
        u'if the archive file name is adjusted.')
    blocking = _(
        u'This mod has an associated plugin-name-specific directory, (e.g. '
        u'Sound\\Voice\\%s) which will become detached when the mod is '
        u'renamed.')

    def testChanges(self): # used by the master list when editing is disabled
        modInfo = self.modInfo
        if not modInfo or (self.fileStr == modInfo.ci_key and
                           self.modifiedStr == format_date(modInfo.mtime) and
                           self.authorStr == modInfo.header.author and
                           self.descriptionStr == modInfo.header.description):
            self.DoCancel()

    @balt.conversation
    def DoSave(self):
        modInfo = self.modInfo
        #--Change Tests
        changeName = (self.fileStr != modInfo.ci_key)
        changeDate = (self.modifiedStr != format_date(modInfo.mtime))
        changeHedr = (self.authorStr != modInfo.header.author or
                      self.descriptionStr != modInfo.header.description)
        changeMasters = self.uilist.edited
        #--Warn on rename if file has BSA and/or dialog
        if changeName:
            msg = modInfo.askResourcesOk(bsaAndBlocking=self.bsaAndBlocking,
                                         bsa=self.bsa, blocking=self.blocking)
            if msg and not balt.askWarning(self, msg, _(
                u'Rename ') + u'%s' % modInfo): return
        #--Only change date?
        if changeDate and not (changeName or changeHedr or changeMasters):
            self._set_date(modInfo)
            with load_order.Unlock():
                bosh.modInfos.refresh(refresh_infos=False, _modTimesChange=True)
            BashFrame.modList.RefreshUI( # refresh saves if lo changed
                refreshSaves=not load_order.using_txt_file())
            return
        #--Backup
        modInfo.makeBackup()
        #--Change Name?
        if changeName:
            oldName,newName = modInfo.ci_key,GPath(self.fileStr.strip())
            #--Bad name?
            if (bosh.modInfos.isBadFileName(newName.s) and
                not balt.askContinue(self,_(
                    u'File name %s cannot be encoded to ASCII. %s may not be '
                    u'able to activate this plugin because of this. Do you '
                    u'want to rename the plugin anyway?')
                                     % (newName,bush.game.displayName),
                                     u'bash.rename.isBadFileName.continue')
                ):
                return ##: cancels all other changes - move to validate_filename (without the balt part)
            settings[u'bash.mods.renames'][oldName] = newName
            changeName = self.panel_uilist.try_rename(modInfo, newName)
        #--Change hedr/masters?
        if changeHedr or changeMasters:
            modInfo.header.author = self.authorStr.strip()
            modInfo.header.description = bolt.winNewLines(self.descriptionStr.strip())
            modInfo.header.masters = self.uilist.GetNewMasters()
            modInfo.header.changed = True
            modInfo.writeHeader()
        #--Change date?
        if changeDate:
            self._set_date(modInfo) # crc recalculated in writeHeader if needed
        if changeDate or changeHedr or changeMasters:
            # we reread header to make sure was written correctly
            detail_item = self._refresh_detail_info()
        else: detail_item = self.file_info.ci_key
        #--Done
        with load_order.Unlock():
            bosh.modInfos.refresh(refresh_infos=False, _modTimesChange=changeDate)
        refreshSaves = detail_item is None or changeName or (
            changeDate and not load_order.using_txt_file())
        self.panel_uilist.RefreshUI(refreshSaves=refreshSaves,
                                    detail_item=detail_item)

    def _set_date(self, modInfo):
        newTimeTup = unformat_date(self.modifiedStr)
        modInfo.setmtime(time.mktime(newTimeTup))

    #--Bash Tags
    ##: Once we're on wx4.1.1, we can use OnDimiss to fully refreshUI the
    # plugin in question (and do the same when removing a tag), so that
    # adding/removing a NoMerge tag properly updates the text color
    def _popup_add_tags(self, wrapped_evt, _lb_dex_and_flags):
        """Show bash tag selection menu."""
        if not self.modInfo: return
        def _refresh_only_details():
            self.SetFile()
        mod_info = self.modInfo # type: bosh.ModInfo
        app_tags = mod_info.getBashTags()
        class BashTagsPopup(MultiChoicePopup):
            def _update_tags(self, changed_tags, tags_were_added):
                """Adds or removes the specified set of tags."""
                if mod_info.is_auto_tagged():
                    mod_info.set_auto_tagged(False)
                curr_app_tags = mod_info.getBashTags()
                if tags_were_added:
                    curr_app_tags |= changed_tags
                else:
                    curr_app_tags -= changed_tags
                mod_info.setBashTags(curr_app_tags)
                _refresh_only_details()
            def on_item_checked(self, choice_name, choice_checked):
                self._update_tags({choice_name}, choice_checked)
            def on_mass_select(self, curr_choices, choices_checked):
                self._update_tags(set(curr_choices), choices_checked)
        bt_popup = BashTagsPopup(
            self, all_choices={t: t in app_tags for t in bush.game.allTags},
            help_text=_(u'Tick a tag to add it to the plugin.'),
            aa_btn_tooltip=_(u'Add all shown tags to the plugin.'),
            ra_btn_tooltip=_(u'Remove all shown tags from the plugin.'))
        mouse_pos = self._add_tag_btn.to_absolute_position(wrapped_evt.evt_pos)
        bt_popup.show_popup(mouse_pos)
        # Returning FINISH is important here because the OS handler will
        # otherwise take focus away from the popup, which causes it to close
        # immediately (since it's transient)
        return EventResult.FINISH

    def _remove_selected_tags(self):
        """Callback to remove the selected bash tags from the current
        plugin."""
        if not self.modInfo: return
        sel_tags = set(self.gTags.lb_get_selected_strings())
        if not sel_tags: return
        # Remember where the first selected tag was so we can reselect
        first_tag_index = next(iter(self.gTags.lb_get_selections()))
        if self.modInfo.is_auto_tagged():
            self.modInfo.set_auto_tagged(False)
        self.modInfo.setBashTags(self.modInfo.getBashTags() - sel_tags)
        self.SetFile() # refresh only details
        new_tag_count = self.gTags.lb_get_items_count()
        if new_tag_count:
            if first_tag_index >= new_tag_count:
                # We removed the end of the tags list, select the new last tag
                self.gTags.lb_select_index(new_tag_count - 1)
            else:
                # Otherwise we removed in the middle, so starting from our
                # selection, everything will have shifted down by one, meaning
                # we can reselect at the same index to get the next item
                self.gTags.lb_select_index(first_tag_index)

    def _popup_misc_tags(self, _lb_selection_dex):
        """Show a menu for miscellaneous tags menu functionality."""
        if not self.modInfo: return
        #--Links closure
        mod_info = self.modInfo # type: bosh.ModInfo
        mod_tags = mod_info.getBashTags()
        def _refresh_only_details():
            self.SetFile()
        # Toggle auto Bash tags
        class Tags_Automatic(CheckLink):
            _text = _(u'Automatic')
            _help = _(u'Use the tags from the description and '
                      u'masterlist/userlist.')
            def _check(self): return mod_info.is_auto_tagged()
            def Execute(self):
                """Toggle automatic bash tags on/off."""
                new_auto = not mod_info.is_auto_tagged()
                mod_info.set_auto_tagged(new_auto)
                if new_auto: mod_info.reloadBashTags()
                _refresh_only_details()
        # Copy tags to various places
        bashTagsDesc = mod_info.getBashTagsDesc()
        tag_plugin_name = mod_info.ci_key
        # We need to grab both the ones from the description and from LOOT,
        # since we need to save a diff in case of Copy to BashTags
        added_tags, deleted_tags = bosh.read_loot_tags(tag_plugin_name)
        # Emulate the effects of applying the LOOT tags
        old_tags = bashTagsDesc.copy()
        old_tags |= added_tags
        old_tags -= deleted_tags
        dir_diff = bosh.mods_metadata.diff_tags(mod_tags, old_tags)
        class Tags_CopyToBashTags(EnabledLink):
            _text = _(u'Copy to BashTags')
            _help = _(u'Copies a diff between currently applied tags and '
                      u'description/LOOT tags to %s.') % (
                bass.dirs[u'tag_files'].join(mod_info.ci_key.body + u'.txt'))
            def _enable(self):
                return (not mod_info.is_auto_tagged() and
                        bosh.read_dir_tags(tag_plugin_name) != dir_diff)
            def Execute(self):
                """Copy manually assigned bash tags into the Data/BashTags
                folder."""
                bosh.mods_metadata.save_tags_to_dir(tag_plugin_name, dir_diff)
                _refresh_only_details()
        class Tags_CopyToDescription(EnabledLink):
            _text = _(u'Copy to Description')
            _help = _(u'Copies currently applied tags to the plugin '
                      u'description.')
            def _enable(self):
                return (not mod_info.is_auto_tagged()
                        and mod_tags != bashTagsDesc)
            def Execute(self):
                """Copy manually assigned bash tags into the mod description"""
                if mod_info.setBashTagsDesc(mod_tags):
                    _refresh_only_details()
                else:
                    balt.showError(
                        Link.Frame, _(u'Description field including the Bash '
                                      u'Tags must be at most 511 characters. '
                                      u'Edit the description to leave enough '
                                      u'room.'))
        class Tags_SelectAll(ItemLink):
            _text = _(u'Select All')
            _help = _(u'Selects all currently applied tags.')
            def Execute(self):
                self.window.lb_select_all()
        class Tags_DeselectAll(ItemLink):
            _text = _(u'Deselect All')
            _help = _(u'Deselects all currently applied tags.')
            def Execute(self):
                self.window.lb_select_none()
        tag_links = Links()
        tag_links.append(Tags_Automatic())
        tag_links.append(SeparatorLink())
        tag_links.append(Tags_CopyToBashTags())
        tag_links.append(Tags_CopyToDescription())
        tag_links.append(SeparatorLink())
        tag_links.append(Tags_SelectAll())
        tag_links.append(Tags_DeselectAll())
        tag_links.popup_menu(self.gTags, None)

#------------------------------------------------------------------------------
class INIDetailsPanel(_DetailsMixin, SashPanel):
    keyPrefix = u'bash.ini.details'

    @property
    def displayed_item(self): return self._ini_detail
    @property
    def file_infos(self): return bosh.iniInfos

    def __init__(self, parent, ui_list_panel):
        super(INIDetailsPanel, self).__init__(parent, isVertical=True)
        self._ini_panel = ui_list_panel
        self._ini_detail = None
        left,right = self.left, self.right
        #--Remove from list button
        self.removeButton = Button(right, _(u'Remove'))
        self.removeButton.on_clicked.subscribe(self._OnRemove)
        #--Edit button
        self.editButton = Button(right, _(u'Edit...'))
        self.editButton.on_clicked.subscribe(lambda:
                                             self.current_ini_path.start())
        #--Ini file
        self.iniContents = TargetINILineCtrl(right._native_widget)
        self.lastDir = settings.get(u'bash.ini.lastDir', bass.dirs[u'mods'].s)
        #--Tweak file
        self.tweakContents = INITweakLineCtrl(left._native_widget, self.iniContents)
        self.iniContents.SetTweakLinesCtrl(self.tweakContents)
        self.tweakName = TextField(left, editable=False, no_border=True)
        self._enable_buttons()
        self._inis_combo_box = DropDown(right, value=self.ini_name,
                                        choices=self._ini_keys)
        #--Events
        self._inis_combo_box.on_combo_select.subscribe(self._on_select_drop_down)
        #--Layout
        VLayout(item_expand=True, spacing=4, items=[
            HLayout(spacing=4, items=[
                (self._inis_combo_box, LayoutOptions(expand=True, weight=1)),
                self.removeButton, self.editButton]),
            (self.iniContents, LayoutOptions(weight=1))
        ]).apply_to(right)
        VLayout(item_expand=True, items=[
            self.tweakName,
            (self.tweakContents, LayoutOptions(weight=1))
        ]).apply_to(left)

    # Read only wrappers around bass.settings[u'bash.ini.choices']
    @property
    def current_ini_path(self):
        """Return path of currently chosen ini."""
        return list(self.target_inis.values())[
            settings[u'bash.ini.choice']]

    @property
    def target_inis(self):
        """Return settings[u'bash.ini.choices'], set in IniInfos#__init__.
        :rtype: OrderedDict[str, bolt.Path]"""
        return settings[u'bash.ini.choices']

    @property
    def _ini_keys(self): return list(settings[u'bash.ini.choices'])

    @property
    def ini_name(self): return self._ini_keys[settings[u'bash.ini.choice']]

    def _resetDetails(self): pass

    def SetFile(self, fileName=u'SAME'):
        fileName = super(INIDetailsPanel, self).SetFile(fileName)
        self._ini_detail = fileName
        self.tweakContents.refresh_tweak_contents(fileName)
        self.tweakName.text_content = fileName.sbody if fileName else u''

    def _enable_buttons(self):
        isGameIni = bosh.iniInfos.ini in bosh.gameInis
        self.removeButton.enabled = not isGameIni
        self.editButton.enabled = not isGameIni or self.current_ini_path.is_file()

    def _OnRemove(self):
        """Called when the 'Remove' button is pressed."""
        self.__remove(self.ini_name)
        self._combo_reset()
        self.ShowPanel(target_changed=True)
        self._ini_panel.uiList.RefreshUI()

    def _combo_reset(self): self._inis_combo_box.set_choices(self._ini_keys)

    def _clean_targets(self):
        for ini_fname, ini_path in self.target_inis.items():
            if ini_path is not None and not ini_path.is_file():
                if not bosh.get_game_ini(ini_path):
                    self.__remove(ini_fname)
        self._combo_reset()

    def __remove(self, ini_str_name): # does NOT change sorting
        del self.target_inis[ini_str_name]
        settings[u'bash.ini.choice'] -= 1

    def set_choice(self, ini_str_name, reset_choices=True):
        if reset_choices: self._combo_reset()
        settings[u'bash.ini.choice'] = self._ini_keys.index(ini_str_name)

    def _on_select_drop_down(self, selection):
        """Called when the user selects a new target INI from the drop down."""
        full_path = self.target_inis[selection]
        if full_path is None:
            # 'Browse...'
            wildcard =  u'|'.join(
                [_(u'Supported files') + u' (*.ini,*.cfg)|*.ini;*.cfg',
                 _(u'INI files') + u' (*.ini)|*.ini',
                 _(u'Config files') + u' (*.cfg)|*.cfg', ])
            full_path = FileOpen.display_dialog(self, defaultDir=self.lastDir,
                                                wildcard=wildcard)
            if full_path: self.lastDir = full_path.shead
            ini_choice_ = settings[u'bash.ini.choice']
            if not full_path or ( # reselected the current target ini
                    full_path.stail in self.target_inis and ini_choice_ ==
                    self._ini_keys.index(full_path.stail)):
                self._inis_combo_box.set_selection(ini_choice_)
                return
        # new file or selected an existing one different from current choice
        self.set_choice(full_path.stail, bool(bosh.INIInfos.update_targets(
            {full_path.stail: full_path}))) # reset choices if ini was added
        self.ShowPanel(target_changed=True)
        self._ini_panel.uiList.RefreshUI()

    def check_new_target(self):
        """Checks if the target INI has been changed and, if so, updates
        bosh.iniInfos.ini to match. Returns whether or not the target INI has
        changed."""
        new_target = bosh.iniInfos.ini.abs_path != self.current_ini_path
        if new_target:
            bosh.iniInfos.ini = self.current_ini_path
        return new_target

    def ShowPanel(self, target_changed=False, clean_targets=False, **kwargs):
        if self._firstShow:
            super(INIDetailsPanel, self).ShowPanel(**kwargs)
            target_changed = True # to display the target ini
        target_changed |= self.check_new_target()
        self._enable_buttons() # if a game ini was deleted will disable edit
        if clean_targets: self._clean_targets()
        # first refresh_ini_contents as refresh_tweak_contents needs its lines
        if target_changed:
            self.iniContents.refresh_ini_contents()
            Link.Frame.warn_game_ini()
        self._inis_combo_box.set_selection(settings[u'bash.ini.choice'])

    def ClosePanel(self, destroy=False):
        super(INIDetailsPanel, self).ClosePanel(destroy)
        settings[u'bash.ini.lastDir'] = self.lastDir

class INIPanel(BashTab):
    keyPrefix = u'bash.ini'
    _ui_list_type = INIList
    _details_panel_type = INIDetailsPanel

    def __init__(self, parent):
        self.listData = bosh.iniInfos
        super(INIPanel, self).__init__(parent)
        BashFrame.iniList = self.uiList

    def RefreshUIColors(self):
        self.uiList.RefreshUI(focus_list=False)
        self.detailsPanel.ShowPanel(target_changed=True)

    def ShowPanel(self, refresh_infos=False, refresh_target=True,
                  clean_targets=False, focus_list=True, detail_item=u'SAME',
                  **kwargs):
        # Have to do this first, since IniInfos.refresh will otherwise use the
        # old INI and report no change, so we won't refresh the INI in the
        # details panel
        target_ch = self.detailsPanel.check_new_target()
        changes = bosh.iniInfos.refresh(refresh_infos=refresh_infos,
                                        refresh_target=refresh_target)
        target_ch |= changes and changes[3]
        super(INIPanel, self).ShowPanel(target_changed=target_ch,
                                        clean_targets=clean_targets)
        if changes or target_ch: # we need this to be more granular
            self.uiList.RefreshUI(focus_list=focus_list,
                                  detail_item=detail_item)

    def _sbCount(self):
        stati = self.uiList.CountTweakStatus()
        return _(u'Tweaks:') + u' %d/%d' % (stati[0], sum(stati[:-1]))

#------------------------------------------------------------------------------
class ModPanel(BashTab):
    keyPrefix = u'bash.mods'
    _ui_list_type = ModList
    _details_panel_type = ModDetails

    def __init__(self,parent):
        self.listData = bosh.modInfos
        super(ModPanel, self).__init__(parent)
        BashFrame.modList = self.uiList

    def _sbCount(self):
        all_mods = load_order.cached_active_tuple()
        total_str = _(u'Mods:') + u' %u/%u' % (len(all_mods),
                                               len(bosh.modInfos))
        if not bush.game.has_esl:
            return total_str
        else:
            regular_mods_count = reduce(lambda accum, mod_path: accum + 1 if
            not bosh.modInfos[mod_path].is_esl() else accum, all_mods, 0)
            return total_str + _(u' (ESP/M: %u, ESL: %u)') % (
                regular_mods_count, len(all_mods) - regular_mods_count)

    def ClosePanel(self, destroy=False):
        load_order.persist_orders()
        super(ModPanel, self).ClosePanel(destroy)

#------------------------------------------------------------------------------
class SaveList(balt.UIList):
    #--Class Data
    column_links = Links() #--Column menu
    context_links = Links() #--Single item menu
    global_links = defaultdict(lambda: Links()) # Global menu
    _editLabels = _copy_paths = True
    _sort_keys = {
        u'File'    : None, # just sort by name
        u'Modified': lambda self, a: self.data_store[a].mtime,
        u'Size'    : lambda self, a: self.data_store[a].fsize,
        u'PlayTime': lambda self, a: self.data_store[a].header.gameTicks,
        u'Player'  : lambda self, a: self.data_store[a].header.pcName,
        u'Cell'    : lambda self, a: self.data_store[a].header.pcLocation,
        u'Status'  : lambda self, a: self.data_store[a].getStatus(),
    }
    #--Labels, why checking for header here - is this called on corrupt saves ?
    @staticmethod
    def _headInfo(saveInfo, attr):
        if not saveInfo.header: return u'-'
        return getattr(saveInfo.header, attr)
    @staticmethod
    def _playTime(saveInfo):
        if not saveInfo.header: return u'-'
        playMinutes = saveInfo.header.gameTicks // 60000
        return u'%d:%02d' % (playMinutes//60, (playMinutes % 60))
    labels = OrderedDict([
        (u'File',     lambda self, p: p.s),
        (u'Modified', lambda self, p: format_date(self.data_store[p].mtime)),
        (u'Size',     lambda self, p: round_size(self.data_store[p].fsize)),
        (u'PlayTime', lambda self, p: self._playTime(self.data_store[p])),
        (u'Player',   lambda self, p: self._headInfo(self.data_store[p],
                                                     u'pcName')),
        (u'Cell',     lambda self, p: self._headInfo(self.data_store[p],
                                                     u'pcLocation')),
    ])

    @balt.conversation
    def OnLabelEdited(self, is_edit_cancelled, evt_label, evt_index, evt_item):
        """Savegame renamed."""
        if is_edit_cancelled: return EventResult.FINISH # todo CANCEL?
        newName, root = \
            self.panel.detailsPanel.file_info.validate_filename_str(evt_label)
        if not root:
            balt.showError(self, newName)
            return EventResult.CANCEL # validate_filename would Veto
        item_edited = [self.panel.detailsPanel.displayed_item]
        to_select = set()
        to_del = set()
        for saveInfo in self.GetSelectedInfos():
            rename_res = self.try_rename(saveInfo, root, to_select, to_del,
                                         item_edited)
            if not rename_res: break
        if to_select:
            self.RefreshUI(redraw=to_select, to_del=to_del, # to_add
                           detail_item=item_edited[0])
            #--Reselect the renamed items
            self.SelectItemsNoCallback(to_select)
        return EventResult.CANCEL # needed ! clears new name from label on exception

    def try_rename(self, saveinf, new_root, to_select=None, to_del=None,
                   item_edited=None, ext=u''):
        newFileName = saveinf.unique_key(new_root, ext)
        oldName = self._try_rename(saveinf, newFileName)
        if oldName:
            if to_select is not None: to_select.add(newFileName)
            if to_del is not None: to_del.add(oldName)
            if item_edited and oldName == item_edited[0]:
                item_edited[0] = newFileName
            return oldName, newFileName # continue

    @staticmethod
    def _unhide_wildcard():
        starred = u'*' + bush.game.Ess.ext
        return bush.game.displayName + u' ' + _(
            u'Save files') + u' (' + starred + u')|' + starred

    #--Populate Item
    def set_item_format(self, fileName, item_format, target_ini_setts):
        save_info = self.data_store[fileName]
        #--Image
        status = save_info.getStatus()
        item_format.icon_key = status, save_info.is_save_enabled()

    #--Events ---------------------------------------------
    @balt.conversation
    def _handle_left_down(self, wrapped_evt, lb_dex_and_flags):
        """Disable save by changing its extension so it's not loaded by the
        game."""
        #--Pass Event onward
        sinf = self._get_info_clicked(lb_dex_and_flags, on_icon=True)
        if not sinf: return
        # Don't allow enabling backups, the game won't read them either way
        if (fn_item := sinf.ci_key).cext == u'.bak':
            balt.showError(self, _(u'You cannot enable save backups.'))
            return
        enabled_ext = bush.game.Ess.ext
        disabled_ext = enabled_ext[:-1] + u'r'
        msg = _(u'Clicking on a save icon will disable/enable the save '
                u'by changing its extension to %(save_ext_on)s (enabled) or '
                u'%(save_ext_off)s (disabled).') % {
            u'save_ext_on': enabled_ext, u'save_ext_off': disabled_ext}
        if not balt.askContinue(self, msg, u'bash.saves.askDisable.continue'):
            return
        do_enable = not sinf.is_save_enabled()
        extension = enabled_ext if do_enable else disabled_ext
        rename_res = self.try_rename(sinf, fn_item.root, ext=extension)
        if rename_res:
            self.RefreshUI(redraw=[rename_res[1]], to_del=[fn_item])

    # Save profiles
    def set_local_save(self, new_saves, refreshSaveInfos):
        if not INIList.ask_create_target_ini(bosh.oblivionIni, msg=_(
            u'Setting the save profile is done by editing the game ini.')):
            return
        self.data_store.setLocalSave(new_saves, refreshSaveInfos)
        balt.Link.Frame.set_bash_frame_title()

#------------------------------------------------------------------------------
class _SaveMasterList(MasterList):
    """Override to handle updating ESL masters."""
    def _update_real_indices(self, new_file_info):
        # Check if we have to worry about ESL masters
        if bush.game.has_esl and new_file_info.header.has_esl_masters:
            self._save_lo_regular = {m: i for i, m in enumerate(
                new_file_info.header.masters_regular)}
            self._save_lo_esl = {m: i for i, m in enumerate(
                new_file_info.header.masters_esl)}
        else:
            self._save_lo_regular = {m: i for i, m in enumerate(
                new_file_info.masterNames)}
            self._save_lo_esl = {}

class SaveDetails(_ModsSavesDetails):
    """Savefile details panel."""
    keyPrefix = u'bash.saves.details' # used in sash/scroll position, sorting
    _master_list_type = _SaveMasterList

    @property
    def file_info(self): return self.saveInfo
    @property
    def file_infos(self): return bosh.saveInfos
    @property
    def allowDetailsEdit(self): return self.saveInfo.header.can_edit_header

    def __init__(self, parent, ui_list_panel):
        super(SaveDetails, self).__init__(parent, ui_list_panel)
        top, bottom = self.left, self.right
        #--Data
        self.saveInfo = None
        textWidth = 200
        #--Player Info
        self._resetDetails()
        self.playerInfo = Label(top, u' \n \n ')
        self._set_player_info_label()
        self.gCoSaves = Label(top, u'--\n--')
        #--Picture
        self.picture = Picture(top, textWidth, 192 * textWidth // 256,
            background=colors[u'screens.bkgd.image']) #--Native: 256x192
        #--Save Info
        self.gInfo = TextArea(self._bottom_low_panel, max_length=2048)
        self.gInfo.on_text_changed.subscribe(self.OnInfoEdit)
        # TODO(nycz): GUI set_size size=(textWidth, 64)
        #--Layouts
        VLayout(item_expand=True, items=[
            self._fname_ctrl,
            HLayout(item_expand=True, items=[
                (self.playerInfo, LayoutOptions(weight=1)), self.gCoSaves
            ]),
            (self.picture, LayoutOptions(weight=1)),
        ]).apply_to(top)
        VLayout(items=[
            Label(self._bottom_low_panel, _(u'Save Notes:')),
            (self.gInfo, LayoutOptions(expand=True, weight=1))
        ]).apply_to(self._bottom_low_panel)

    def _resetDetails(self):
        self.saveInfo = None
        self.fileStr = u''
        self.playerNameStr = u''
        self.curCellStr = u''
        self.playerLevel = 0
        self.gameDays = 0
        self.playMinutes = 0
        self.coSaves = u'--\n--'

    def SetFile(self, fileName=u'SAME'):
        fileName = super(SaveDetails, self).SetFile(fileName)
        if fileName:
            saveInfo = self.saveInfo = bosh.saveInfos[fileName]
            #--Remember values for edit checks
            self.fileStr = saveInfo.ci_key.s
            self.playerNameStr = saveInfo.header.pcName
            self.curCellStr = saveInfo.header.pcLocation
            self.gameDays = saveInfo.header.gameDays
            self.playMinutes = saveInfo.header.gameTicks//60000
            self.playerLevel = saveInfo.header.pcLevel
            self.coSaves = saveInfo.get_cosave_tags()
            note_text = saveInfo.get_table_prop(u'info', u'')
        else:
            note_text = u''
        #--Set Fields
        self._fname_ctrl.text_content = self.fileStr
        self._set_player_info_label()
        self.gCoSaves.label_text = self.coSaves
        self.uilist.SetFileInfo(self.saveInfo)
        # Picture - lazily loaded since it takes up so much memory
        if self.saveInfo:
            if not self.saveInfo.header.image_loaded:
                self.saveInfo.header.read_save_header(load_image=True)
            new_save_screen = ImageWrapper.bmp_from_bitstream(
                *self.saveInfo.header.image_parameters)
        else:
            new_save_screen = None # reset to default
        self.picture.set_bitmap(new_save_screen)
        #--Info Box
        self.gInfo.modified = False
        self.gInfo.text_content = note_text
        self._update_masters_warning()

    def _set_player_info_label(self):
        self.playerInfo.label_text = (self.playerNameStr + u'\n' +
            _(u'Level') + u' %d, ' + _(u'Day') + u' %d, ' +
            _(u'Play') + u' %d:%02d\n%s') % (
            self.playerLevel, int(self.gameDays), self.playMinutes // 60,
            (self.playMinutes % 60), self.curCellStr)

    def _update_masters_warning(self):
        """Show or hide the 'inaccurate masters' warning."""
        show_warning = self.uilist.is_inaccurate
        self._masters_label.label_text = (
            _(u'Masters (likely inaccurate, hover for more info):')
            if show_warning else _(u'Masters:'))
        self._masters_label.tooltip = (
            _(u'This save has ESL masters and cannot be displayed accurately '
              u'without an up-to-date cosave. Please install the latest '
              u'version of %s and create a new save to see the true master '
              u'order.') % bush.game.Se.se_abbrev if show_warning else u'')
        if show_warning:
            self._masters_label.set_foreground_color(colors[u'default.warn'])
        else:
            self._masters_label.reset_foreground_color()

    def OnInfoEdit(self, new_text):
        """Info field was edited."""
        if self.saveInfo and self.gInfo.modified:
            self.saveInfo.set_table_prop(u'info', new_text)

    def testChanges(self): # used by the master list when editing is disabled
        saveInfo = self.saveInfo
        if not saveInfo or self.fileStr == saveInfo.ci_key:
            self.DoCancel()

    @balt.conversation
    def DoSave(self):
        """Event: Clicked Save button."""
        saveInfo = self.saveInfo
        #--Change Tests
        changeName = (self.fileStr != saveInfo.ci_key)
        changeMasters = self.uilist.edited
        #--Backup
        saveInfo.makeBackup() ##: why backup when just renaming - #292
        prevMTime = saveInfo.mtime
        #--Change Name?
        to_del = set()
        if changeName:
            newName = GPath(self.fileStr.strip()).root
            # if you were wondering: OnFileEdited checked if file existed,
            # and yes we recheck below, in Mod/BsaDetails we don't - filesystem
            # APIs might warn user (with a dialog hopefully) for an overwrite,
            # otherwise we can have a race whatever we try here - an extra
            # check can't harm nor makes a (any) difference
            self.panel_uilist.try_rename(saveInfo, newName, to_del=to_del)
        #--Change masters?
        if changeMasters:
            saveInfo.header.masters = self.uilist.GetNewMasters()
            saveInfo.write_masters()
            saveInfo.setmtime(prevMTime)
            detail_item = self._refresh_detail_info()
        else: detail_item = self.file_info.ci_key
        kwargs = {u'to_del': to_del, u'detail_item': detail_item}
        if detail_item is None:
            kwargs[u'to_del'] = to_del | {self.file_info.ci_key}
        else:
            kwargs[u'redraw'] = [detail_item]
        self.panel_uilist.RefreshUI(**kwargs)

    def RefreshUIColors(self):
        self._update_masters_warning()
        self.picture.SetBackground(colors[u'screens.bkgd.image'])

#------------------------------------------------------------------------------
class SavePanel(BashTab):
    """Savegames tab."""
    keyPrefix = u'bash.saves'
    _status_str = _(u'Saves:') + u' %d'
    _ui_list_type = SaveList
    _details_panel_type = SaveDetails

    def __init__(self,parent):
        if not bush.game.Ess.canReadBasic:
            raise BoltError(u'Wrye Bash cannot read save games for %s.' %
                bush.game.displayName)
        self.listData = bosh.saveInfos
        super(SavePanel, self).__init__(parent)
        BashFrame.saveList = self.uiList

    def ClosePanel(self, destroy=False):
        bosh.saveInfos.profiles.save()
        super(SavePanel, self).ClosePanel(destroy)

#------------------------------------------------------------------------------
class InstallersList(balt.UIList):
    column_links = Links()
    context_links = Links()
    global_links = defaultdict(lambda: Links()) # Global menu
    _icons = installercons
    _sunkenBorder = False
    _shellUI = True
    _editLabels = _copy_paths = True
    _default_sort_col = u'Package'
    _sort_keys = {
        u'Package' : None,
        u'Order'   : lambda self, x: self.data_store[x].order,
        u'Modified': lambda self, x: self.data_store[x].modified,
        u'Size'    : lambda self, x: self.data_store[x].fsize,
        u'Files'   : lambda self, x: self.data_store[x].num_of_files,
    }
    #--Special sorters
    def _sortStructure(self, items):
        if settings[u'bash.installers.sortStructure']:
            items.sort(key=lambda self, x: self.data_store[x].type)
    def _sortActive(self, items):
        if settings[u'bash.installers.sortActive']:
            items.sort(key=lambda x: not self.data_store[x].is_active)
    def _sortProjects(self, items):
        if settings[u'bash.installers.sortProjects']:
            items.sort(key=lambda x: not self.data_store[x].is_project())
    _extra_sortings = [_sortStructure, _sortActive, _sortProjects]
    #--Labels
    labels = OrderedDict([
        (u'Package',  lambda self, p: p.s),
        (u'Order',    lambda self, p: u'%d' % self.data_store[p].order),
        (u'Modified', lambda self, p: format_date(self.data_store[p].modified)),
        (u'Size',     lambda self, p: self.data_store[p].size_string()),
        (u'Files',    lambda self, p: self.data_store[p].number_string(
            self.data_store[p].num_of_files)),
    ])
    #--DnD
    _dndList, _dndFiles, _dndColumns = True, True, [u'Order']
    #--GUI
    _status_color = {-20: u'grey', -10: u'red', 0: u'white', 10: u'orange',
                     20: u'yellow', 30: u'green'}
    _type_textKey = {1: u'default.text', 2: u'installers.text.complex'}

    #--Item Info
    def set_item_format(self, item, item_format, target_ini_setts):
        inst = self.data_store[item] # type: bosh.bain.Installer
        #--Text
        if inst.type == 2 and len(inst.subNames) == 2:
            item_format.text_key = self._type_textKey[1]
        elif inst.is_marker():
            item_format.text_key = u'installers.text.marker'
        else: item_format.text_key = self._type_textKey.get(inst.type,
                                             u'installers.text.invalid')
        #--Background
        if inst.skipDirFiles:
            item_format.back_key = u'installers.bkgd.skipped'
        mouse_text = u''
        if inst.dirty_sizeCrc:
            item_format.back_key = u'installers.bkgd.dirty'
            mouse_text += _(u'Needs Annealing due to a change in configuration.')
        elif inst.underrides:
            item_format.back_key = u'installers.bkgd.outOfOrder'
            mouse_text += _(u'Needs Annealing due to a change in Install Order.')
        #--Icon
        item_format.icon_key = u'on' if inst.is_active else u'off'
        item_format.icon_key += u'.' + self._status_color[inst.status]
        if inst.type < 0: item_format.icon_key = u'corrupt'
        else:
            if inst.is_project(): item_format.icon_key += u'.dir'
            if settings[u'bash.installers.wizardOverlay'] and inst.hasWizard:
                item_format.icon_key += u'.wiz'
        #if textKey == 'installers.text.invalid': # I need a 'text.markers'
        #    text += _(u'Marker Package. Use for grouping installers together')
        #--TODO: add mouse  mouse tips
        self.mouseTexts[item] = mouse_text

    def _rename_type(self):
        #--Only rename multiple items of the same type
        renaming_type = super(InstallersList, self)._rename_type()
        if renaming_type is None: return None
        for item in self.GetSelectedInfos():
            if not type(item) is renaming_type:
                balt.showError(self, _(
                    u"Bash can't rename mixed installers types"))
                return None
            #--Also, don't allow renaming the 'Last' marker
            elif item is self.data_store[self.data_store.lastKey]:
                balt.showError(self, _(u'Renaming %s is not '
                                       u'allowed') % self.data_store.lastKey)
                return None
        return renaming_type

    @balt.conversation
    def OnLabelEdited(self, is_edit_cancelled, evt_label, evt_index, evt_item):
        """Renamed some installers"""
        if is_edit_cancelled: return EventResult.FINISH ##: previous behavior todo TTT
        selected = self.GetSelectedInfos()
        # all selected have common type! enforced in OnBeginEditLabel
        newName, root = selected[0].validate_filename_str(evt_label,
            allowed_exts=archives.readExts)
        if root is None:
            balt.showError(self, newName)
            return EventResult.CANCEL
        #--Rename each installer, keeping the old extension (for archives)
        if isinstance(root, tuple):
            root = root[0]
        with BusyCursor():
            refreshes, ex = [(False, False, False)], None
            newselected = []
            try:
                for package in selected:
                    if not self.try_rename(package, root, refreshes,
                                           newselected):
                        ex = True
                        break
            finally:
                refreshNeeded = modsRefresh = iniRefresh = False
                if len(refreshes) > 1:
                    refreshNeeded, modsRefresh, iniRefresh = [
                        any(grouped) for grouped in zip(*refreshes)]
            #--Refresh UI
            if refreshNeeded or ex: # refresh the UI in case of an exception
                if modsRefresh: BashFrame.modList.RefreshUI(refreshSaves=False,
                                                            focus_list=False)
                if iniRefresh and BashFrame.iniList is not None:
                    # It will be None if the INI Edits Tab was hidden at
                    # startup, and never initialized
                    BashFrame.iniList.RefreshUI()
                self.RefreshUI()
                #--Reselected the renamed items
                self.SelectItemsNoCallback(newselected)
            return EventResult.CANCEL

    def try_rename(self, inst_info, new_root, refreshes, newselected):
        newFileName = inst_info.unique_key(new_root) # preserve extension for installers
        if newFileName is None: # just changed extension - continue
            return False, False, False
        result = self._try_rename(inst_info, newFileName)
        if result:
            refreshes.append(result)
            if result[0]: newselected.append(newFileName)
            return newFileName # continue

    @staticmethod
    def _unhide_wildcard():
        starred = u';'.join(u'*' + ext for ext in archives.readExts)
        return bush.game.displayName + u' ' + _(
            u'Mod Archives') + u' (' + starred + u')|' + starred

    #--Drag and Drop-----------------------------------------------------------
    def OnDropIndexes(self, indexes, newPos):
        # See if the column is reverse sorted first
        column = self.sort_column
        reverse = self.colReverse.get(column,False)
        if reverse:
            newPos = self.item_count - newPos - 1 - (indexes[-1] - indexes[0])
            if newPos < 0: newPos = 0
        # Move the given indexes to the new position
        self.data_store.moveArchives(self.GetSelected(), newPos)
        self.data_store.irefresh(what=u'N')
        self.RefreshUI()

    def _extractOmods(self, omodnames, progress):
        """Called from onDropFiles duplicating __extractOmods with a bunch of
        subtle differences. FIXME(ut) this must go - we should let caller's ShowPanel do it"""
        failed = []
        completed = []
        progress.setFull(len(omodnames))
        try:
            for i, omod in enumerate(omodnames):
                om_name = omod.stail
                progress(i, om_name)
                outDir = bass.dirs[u'installers'].join(omod.body)
                if outDir.exists():
                    if balt.askYes(progress.dialog, _(
                        u"The project '%s' already exists.  Overwrite "
                        u"with '%s'?") % (omod.sbody, om_name)):
                        env.shellDelete(outDir, parent=self,
                                        recycle=True)  # recycle
                    else: continue
                try:
                    bosh.omods.OmodFile(omod).extractToProject(
                        outDir, SubProgress(progress, i))
                    completed.append(omod)
                except (CancelError, SkipError):
                    # Omod extraction was cancelled, or user denied admin
                    # rights if needed
                    raise
                except:
                    deprint(f"Failed to extract '{om_name}'.\n\n",
                            traceback=True)
                    failed.append(om_name)
        except CancelError:
            skipped = set(omodnames) - set(completed)
            msg = u''
            for filepaths, m in (
                    [completed, _(u'The following OMODs were unpacked:')],
                    [skipped, _(u'The following OMODs were skipped:')]):
                if filepaths:
                    filepaths = [f' * {x.stail}' for x in filepaths]
                    msg += m + u'\n%s\n\n' % u'\n'.join(filepaths)
            if failed:
                msg += _(u'The following OMODs failed to extract:') + \
                       u'\n%s' % u'\n'.join(failed)
            balt.showOk(self, msg, _(u'OMOD Extraction Canceled'))
        else:
            if failed: balt.showWarning(self, _(
                u'The following OMODs failed to extract.  This could be '
                u'a file IO error, or an unsupported OMOD format:') + u'\n\n'
                + u'\n'.join(failed), _(u'OMOD Extraction Complete'))
        finally:
            progress(len(omodnames), _(u'Refreshing...'))

    def _askCopyOrMove(self, filenames):
        action = settings[u'bash.installers.onDropFiles.action']
        if action not in (u'COPY', u'MOVE'):
            if filenames:
                message = _(u'You have dragged the following files into Wrye '
                            u'Bash:') + u'\n\n * '
                message += u'\n * '.join(f.s for f in filenames) + u'\n'
            else: message = _(u'You have dragged some converters into Wrye '
                            u'Bash.')
            message += u'\n' + _(u'What would you like to do with them?')
            action, remember = CopyOrMovePopup.display_dialog(self, message,
                sizes_dict=balt.sizes)
            if action and remember:
                settings[u'bash.installers.onDropFiles.action'] = action
        return action

    @balt.conversation
    def OnDropFiles(self, x, y, filenames):
        filenames = [GPath(x) for x in filenames]
        dirs = {x for x in filenames if x.is_dir()}
        omodnames = [x for x in filenames if
                     not x in dirs and x.cext in archives.omod_exts]
        converters = {x for x in filenames if
                      bosh.converters.ConvertersData.validConverterName(x)}
        filenames = [x for x in filenames if x in dirs
                     or x.cext in archives.readExts and x not in converters]
        if not (omodnames or converters or filenames): return
        if omodnames:
            with balt.Progress(_(u'Extracting OMODs...'), u'\n' + u' ' * 60,
                                 abort=True) as prog:
                self._extractOmods(omodnames, prog)
        if filenames or converters:
            action = self._askCopyOrMove(filenames)
            if action in [u'COPY',u'MOVE']:
                with BusyCursor():
                    installersJoin = bass.dirs[u'installers'].join
                    convertersJoin = bass.dirs[u'converters'].join
                    filesTo = [installersJoin(x.tail) for x in filenames]
                    filesTo.extend(convertersJoin(x.tail) for x in converters)
                    filenames.extend(converters)
                    try:
                        (env.shellMove if action == 'MOVE' else env.shellCopy)(
                            filenames, filesTo, parent=self)
                    except (CancelError,SkipError):
                        pass
        self.panel.frameActivated = True
        self.panel.ShowPanel(focus_list=True)

    def dndAllow(self, event):
        if not self.sort_column in self._dndColumns:
            msg = _(u"Drag and drop in the Installer's list is only allowed "
                    u'when the list is sorted by install order')
            balt.askContinue(self, msg, u'bash.installers.dnd.column.continue')
            return super(InstallersList, self).dndAllow(event) # disallow
        return True

    def _handle_key_down(self, wrapped_evt):
        """Char event: Reorder."""
        kcode = wrapped_evt.key_code
        # Ctrl+Up/Ctrl+Down - Move installer up/down install order
        if wrapped_evt.is_cmd_down and kcode in balt.wxArrows:
            selected = self.GetSelected()
            if len(selected) < 1: return
            orderKey = partial(self._sort_keys[u'Order'], self)
            moveMod = 1 if kcode in balt.wxArrowDown else -1 # move down or up
            sorted_ = sorted(selected, key=orderKey, reverse=(moveMod == 1))
            # get the index two positions after the last or before the first
            visibleIndex = self.GetIndex(sorted_[0]) + moveMod * 2
            maxPos = max(x.order for x in self.data_store.values())
            for thisFile in sorted_:
                newPos = self.data_store[thisFile].order + moveMod
                if newPos < 0 or maxPos < newPos: break
                self.data_store.moveArchives([thisFile], newPos)
            self.data_store.irefresh(what=u'N')
            self.RefreshUI()
            visibleIndex = sorted((visibleIndex, 0, maxPos))[1]
            self.EnsureVisibleIndex(visibleIndex)
        elif wrapped_evt.is_cmd_down and kcode == ord(u'V'):
            # Ctrl+V - drop files onto the Installers tab via clipboard
            read_files_from_clipboard_cb(
                lambda clip_file_paths: self.OnDropFiles(
                    0, 0, clip_file_paths))
        # Enter: Open selected installers
        elif kcode in balt.wxReturn: self.OpenSelected()
        else:
            return EventResult.CONTINUE
        # Otherwise we'd jump to a random plugin that starts with the key code
        return EventResult.FINISH

    def OnDClick(self, lb_dex_and_flags):
        """Double click, open the installer."""
        inst = self._get_info_clicked(lb_dex_and_flags)
        if not inst: return
        if inst.is_marker():
            # Double click on a Marker, select all items below
            # it in install order, up to the next Marker
            sorted_ = self._SortItems(col=u'Order', sortSpecial=False)
            new = []
            for nextItem in sorted_[inst.order + 1:]:
                if self.data_store[nextItem].is_marker():
                    break
                new.append(nextItem)
            if new:
                self.SelectItemsNoCallback(new)
                self.SelectItem((new[-1])) # show details for the last one
        else:
            self.OpenSelected(selected=[inst.ci_key])

    def _handle_key_up(self, wrapped_evt):
        """Char events: Action depends on keys pressed"""
        # Ctrl+Shift+N - Add a marker
        if (wrapped_evt.is_cmd_down and wrapped_evt.is_shift_down and
                wrapped_evt.key_code == ord(u'N')):
            self.addMarker()
        super(InstallersList, self)._handle_key_up(wrapped_evt)

    # Installer specific ------------------------------------------------------
    def addMarker(self):
        selected_installers = self.GetSelected()
        if selected_installers:
            sorted_inst = self.data_store.sorted_values(selected_installers)
            max_order = sorted_inst[-1].order + 1 #place it after last selected
        else:
            max_order = None
        new_marker = GPath(u'====')
        try:
            index = self.GetIndex(new_marker)
        except KeyError: # u'====' not found in the internal dictionary
            self.data_store.add_marker(new_marker, max_order)
            self.RefreshUI() # need to redraw all items cause order changed
            index = self.GetIndex(new_marker)
        if index != -1:
            self.SelectAndShowItem(new_marker, deselectOthers=True,
                                   focus=True)
            self.Rename([new_marker])

    def rescanInstallers(self, toRefresh, abort, update_from_data=True,
                         calculate_projects_crc=False, shallow=False):
        """Refresh installers, ignoring skip refresh flag.

        Will also update InstallersData for the paths this installer would
        install, in case a refresh is requested because those files were
        modified/deleted (BAIN only scans Data/ once or boot). If 'shallow' is
        True (only the configurations of the installers changed) it will run
        refreshDataSizeCrc of the installers, otherwise a full refreshBasic."""
        toRefresh = list(self.data_store.ipackages(toRefresh))
        if not toRefresh: return
        try:
            with balt.Progress(_(u'Refreshing Packages...'), u'\n' + u' ' * 60,
                               abort=abort) as progress:
                progress.setFull(len(toRefresh))
                dest = set() # installer's destination paths rel to Data/
                for index, installer in enumerate(
                        self.data_store.sorted_values(toRefresh)):
                    progress(index, _(u'Refreshing Packages...') + u'\n%s' %
                             installer)
                    if shallow:
                        op = installer.refreshDataSizeCrc
                    else:
                        op = partial(installer.refreshBasic,
                                     SubProgress(progress, index, index + 1),
                                     calculate_projects_crc)
                    dest.update(op())
                self.data_store.hasChanged = True  # is it really needed ?
                if update_from_data:
                    progress(0, _(u'Refreshing From %s...')
                             % bush.game.mods_dir + u'\n' + u' ' * 60)
                    self.data_store.update_data_SizeCrcDate(dest, progress)
        except CancelError:  # User canceled the refresh
            if not abort: raise # I guess CancelError is raised on aborting
        self.data_store.irefresh(what=u'NS')
        self.RefreshUI()

#------------------------------------------------------------------------------
class InstallersDetails(_SashDetailsPanel):
    keyPrefix = u'bash.installers.details'
    defaultSashPos = - 32 # negative so it sets bottom panel's (comments) size
    minimumSize = 32 # so comments dont take too much space
    _ui_settings = {**_SashDetailsPanel._ui_settings, **{
        u'.checkListSplitterSashPos' : _UIsetting(lambda self: 0,
        lambda self: self.checkListSplitter.get_sash_pos(),
        lambda self, sashPos: self.checkListSplitter.set_sash_pos(sashPos))}
    }

    @property
    def displayed_item(self): return self._displayed_installer
    @property
    def file_infos(self): return self._idata

    def __init__(self, parent, ui_list_panel):
        """Initialize."""
        super(InstallersDetails, self).__init__(parent)
        self.installersPanel = ui_list_panel
        self._idata = self.installersPanel.listData
        self._displayed_installer = None
        top, bottom = self.left, self.right
        commentsSplitter = self.splitter
        self.subSplitter, commentsPanel = commentsSplitter.make_panes(
            first_pane=self.subSplitter, second_pane=PanelWin(bottom))
        #--Package
        self.gPackage = TextArea(top, editable=False, no_border=True)
        #--Info Tabs
        self.gNotebook, self.checkListSplitter = self.subSplitter.make_panes(
            first_pane=TabbedPanel(self.subSplitter, multiline=True),
            second_pane=Splitter(self.subSplitter, min_pane_size=50,
                                 sash_gravity=0.5))
        self.gNotebook.set_min_size(100, 100)
        self.infoPages = []
        infoTitles = (
            (u'gGeneral', _(u'General')),
            (u'gMatched', _(u'Matched')),
            (u'gMissing', _(u'Missing')),
            (u'gMismatched', _(u'Mismatched')),
            (u'gConflicts', _(u'Conflicts')),
            (u'gUnderrides', _(u'Underridden')),
            (u'gDirty', _(u'Dirty')),
            (u'gSkipped', _(u'Skipped')),
            )
        for cmp_name, page_title in infoTitles:
            gPage = TextArea(self.gNotebook, editable=False,
                             auto_tooltip=False, do_wrap=False)
            gPage.set_component_name(cmp_name)
            self.gNotebook.add_page(gPage, page_title)
            self.infoPages.append([gPage,False])
        self.gNotebook.set_selected_page_index(
            settings[u'bash.installers.page'])
        self.gNotebook.on_nb_page_change.subscribe(self.OnShowInfoPage)
        self.sp_panel, espmsPanel = self.checkListSplitter.make_panes(
            vertically=True)
        #--Sub-Installers
        self.gSubList = CheckListBox(self.sp_panel, isExtended=True)
        self.gSubList.on_box_checked.subscribe(self._check_subitem)
        self.gSubList.on_mouse_right_up.subscribe(self._sub_selection_menu)
        # FOMOD/Sub-Packages radio buttons
        self.fomod_btn = RadioButton(self.sp_panel, _(u'FOMOD'))
        self.fomod_btn.tooltip = _(u'Disable the regular BAIN sub-packages '
                                   u'and use the results of the last FOMOD '
                                   u'installer run instead.')
        self.sp_btn = RadioButton(self.sp_panel, _(u'Sub-Packages'))
        self.sp_btn.tooltip = _(u'Use the regular BAIN sub-packages.')
        for rb in (self.fomod_btn, self.sp_btn):
            rb.on_checked.subscribe(self._on_fomod_checked)
        self.sp_label = Label(self.sp_panel, _(u'Sub-Packages'))
        self._update_fomod_state()
        #--Espms
        # sorted list of the displayed installer espm names - esms sorted first
        self.espm_checklist_fns = [] # type: List[bolt.Path]
        self.gEspmList = CheckListBox(espmsPanel, isExtended=True)
        self.gEspmList.on_box_checked.subscribe(self._on_check_plugin)
        self.gEspmList.on_mouse_left_dclick.subscribe(
            self._on_plugin_filter_dclick)
        self.gEspmList.on_mouse_right_up.subscribe(self._selection_menu)
        #--Comments
        self.gComments = TextArea(commentsPanel, auto_tooltip=False)
        #--Splitter settings
        commentsSplitter.set_min_pane_size(-self.__class__.defaultSashPos)
        commentsSplitter.set_sash_gravity(1.0)
        #--Layout
        VLayout(items=[
            self.fomod_btn, self.sp_btn, self.sp_label,
            (self.gSubList, LayoutOptions(expand=True, weight=1)),
        ]).apply_to(self.sp_panel)
        VLayout(items=[
            Label(espmsPanel, _(u'Plugin Filter')),
            (self.gEspmList, LayoutOptions(expand=True, weight=1)),
        ]).apply_to(espmsPanel)
        VLayout(item_expand=True, items=[
            self.gPackage, (self.subSplitter, LayoutOptions(weight=1)),
        ]).apply_to(top)
        VLayout(items=[
            Label(commentsPanel, _(u'Comments')),
            (self.gComments, LayoutOptions(expand=True, weight=1)),
        ]).apply_to(commentsPanel)
        VLayout(item_expand=True, item_weight=1, items=[
            commentsPanel,
        ]).apply_to(bottom)

    def _get_sub_splitter(self):
        return Splitter(self.left, min_pane_size=50, sash_gravity=0.5)

    def OnShowInfoPage(self, wx_id, selected_index):
        """A specific info page has been selected."""
        if wx_id == self.gNotebook.wx_id_(): # todo because of BashNotebook event??
            # todo use the pages directly not the index
            gPage,initialized = self.infoPages[selected_index]
            if self._displayed_installer and not initialized:
                self.RefreshInfoPage(selected_index, self.file_info)

    def ClosePanel(self, destroy=False):
        """Saves details if they need saving."""
        if not self._firstShow and destroy: # save subsplitters
            super(InstallersDetails, self).ClosePanel(destroy)
            settings[u'bash.installers.page'] = \
                self.gNotebook.get_selected_page_index()
        self._save_comments()

    def _save_comments(self):
        inst = self.file_info
        if inst and self.gComments.modified:
            inst.comments = self.gComments.text_content
            self._idata.setChanged()

    def SetFile(self, fileName=u'SAME'):
        """Refreshes detail view associated with data from item."""
        if self._displayed_installer is not None:
            self._save_comments()
        fileName = super(InstallersDetails, self).SetFile(fileName)
        self._displayed_installer = fileName
        del self.espm_checklist_fns[:]
        if fileName:
            installer = self._idata[fileName]
            #--Name
            self.gPackage.text_content = fileName.s
            #--Info Pages
            currentIndex = self.gNotebook.get_selected_page_index()
            for index,(gPage,state) in enumerate(self.infoPages):
                self.infoPages[index][1] = False
                if index == currentIndex: self.RefreshInfoPage(index,installer)
                else: gPage.text_content = u''
            #--Sub-Packages
            self.gSubList.lb_clear()
            if len(installer.subNames) <= 2:
                self.gSubList.lb_clear()
            else:
                ##: TODO(ut) subNames/subActives should be a dict really no?
                sub_isactive = zip(installer.subNames, installer.subActives)
                next(sub_isactive) # pop empty subpackage, duh
                sub_isactive = {k: v for k, v in sub_isactive}
                self.gSubList.set_all_items_keep_pos(sub_isactive)
            self._update_fomod_state()
            #--Espms
            if not installer.espms:
                self.gEspmList.lb_clear()
            else:
                fns = self.espm_checklist_fns = sorted(installer.espms, key=lambda x: (
                    x.cext != u'.esm', x)) # esms first then alphabetically
                espm_acti = {['', '*'][installer.isEspmRenamed(
                    x)] + x.s: x not in installer.espmNots for x in fns}
                self.gEspmList.set_all_items_keep_pos(espm_acti)
            #--Comments
            self.gComments.text_content = installer.comments

    def _resetDetails(self):
        self.gPackage.text_content = u''
        for index, (gPage, state) in enumerate(self.infoPages):
            self.infoPages[index][1] = True
            gPage.text_content = u''
        self.gSubList.lb_clear()
        self.gEspmList.lb_clear()
        self.gComments.text_content = u''

    def RefreshInfoPage(self,index,installer):
        """Refreshes notebook page."""
        gPage,initialized = self.infoPages[index]
        if initialized: return
        else: self.infoPages[index][1] = True
        pageName = gPage.get_component_name()
        def _dumpFiles(files, header=u''):
            if files:
                buff = []
                files = bolt.sortFiles(files)
                if header: buff.append(header)
                for file in files:
                    oldName = installer.getEspmName(file)
                    if oldName != file:
                        oldName = f'{oldName} -> {file}'
                    buff.append(oldName)
                return buff.append('') or '\n'.join(buff) # add a newline
            elif header:
                return header+u'\n'
            else:
                return u''
        if pageName == u'gGeneral':
            inf_ = ['== ' + _('Overview'), _('Type: ') + installer.type_string,
                    installer.structure_string(), installer.size_info_str()]
            nConfigured = len(installer.ci_dest_sizeCrc)
            nMissing = len(installer.missingFiles)
            nMismatched = len(installer.mismatchedFiles)
            is_mark = installer.is_marker()
            numstr = partial(installer.number_string, marker_string='N/A')
            inf_.extend([
                _('Modified:') + (' N/A' if is_mark else
                    f' {format_date(installer.modified)}'),
                _('Data CRC:') + (' N/A' if is_mark else
                    f' {installer.crc:08X}'),
                _('Files:') + f' {numstr(installer.num_of_files)}',
                _('Configured:') + (' N/A' if is_mark else
                    f' {nConfigured:d} ({round_size(installer.unSize)})'),
                _('  Matched:') + ' %s' % numstr(
                    nConfigured - nMissing - nMismatched),
                 _('  Missing:') + f' {numstr(nMissing)}',
                 _('  Conflicts:') + f' {numstr(nMismatched)}',
                '', # One newline in between the main info and the file list
                _dumpFiles(installer.ci_dest_sizeCrc,
                           '== ' + _('Configured Files'))])
            gPage.text_content = u'\n'.join(inf_)
        elif pageName == u'gMatched':
            gPage.text_content = _dumpFiles(set(
                installer.ci_dest_sizeCrc) - installer.missingFiles -
                                           installer.mismatchedFiles)
        elif pageName == u'gMissing':
            gPage.text_content = _dumpFiles(installer.missingFiles)
        elif pageName == u'gMismatched':
            gPage.text_content = _dumpFiles(installer.mismatchedFiles)
        elif pageName == u'gConflicts':
            gPage.text_content = self._idata.getConflictReport(
                installer, u'OVER', bosh.modInfos)
        elif pageName == u'gUnderrides':
            gPage.text_content = self._idata.getConflictReport(
                installer, u'UNDER', bosh.modInfos)
        elif pageName == u'gDirty':
            gPage.text_content = _dumpFiles(installer.dirty_sizeCrc)
        elif pageName == u'gSkipped':
            gPage.text_content = u'\n'.join((_dumpFiles(
                installer.skipExtFiles, u'== ' + _(u'Skipped (Extension)')),
                                             _dumpFiles(
                installer.skipDirFiles, u'== ' + _(u'Skipped (Dir)'))))

    #--Config
    def refreshCurrent(self,installer):
        """Refreshes current item while retaining scroll positions."""
        installer.refreshDataSizeCrc()
        installer.refreshStatus(self._idata)
        # Save scroll bar positions, because gList.RefreshUI will
        subScrollPos  = self.gSubList.lb_get_vertical_scroll_pos()
        espmScrollPos = self.gEspmList.lb_get_vertical_scroll_pos()
        subIndices = self.gSubList.lb_get_selections()
        self.installersPanel.uiList.RefreshUI(redraw=[self.displayed_item])
        for subIndex in subIndices:
            self.gSubList.lb_select_index(subIndex)
        # Reset the scroll bars back to their original position
        subScroll = subScrollPos - self.gSubList.lb_get_vertical_scroll_pos()
        self.gSubList.lb_scroll_lines(subScroll)
        espmScroll = espmScrollPos - self.gEspmList.lb_get_vertical_scroll_pos()
        self.gEspmList.lb_scroll_lines(espmScroll)

    def _check_subitem(self, lb_selection_dex):
        """Handle check/uncheck of item."""
        installer = self.file_info
        self.gSubList.lb_select_index(lb_selection_dex)
        for lb_selection_dex in range(self.gSubList.lb_get_items_count()):
            installer.subActives[lb_selection_dex+1] = self.gSubList.lb_is_checked_at_index(lb_selection_dex)
        if not get_shift_down():
            self.refreshCurrent(installer)

    def _selection_menu(self, lb_selection_dex):
        """Handle right click in espm list."""
        # Clear if we right click something entirely outside the selection
        if lb_selection_dex not in self.gEspmList.lb_get_selections():
            self.gEspmList.lb_select_none()
        self.gEspmList.lb_select_index(lb_selection_dex)
        #--Show/Destroy Menu
        InstallersPanel.espmMenu.popup_menu(self, lb_selection_dex)

    def _sub_selection_menu(self, lb_selection_dex):
        """Handle right click in sub-packages list."""
        # Clear if we right click something entirely outside the selection
        if lb_selection_dex not in self.gSubList.lb_get_selections():
            self.gSubList.lb_select_none()
        self.gSubList.lb_select_index(lb_selection_dex)
        #--Show/Destroy Menu
        InstallersPanel.subsMenu.popup_menu(self, lb_selection_dex)

    def _on_check_plugin(self, lb_selection_dex):
        """Handle check/uncheck of item."""
        espmNots = self.file_info.espmNots
        plugin_name = self.get_espm(lb_selection_dex)
        if self.gEspmList.lb_is_checked_at_index(lb_selection_dex):
            espmNots.discard(plugin_name)
        else:
            espmNots.add(plugin_name)
        self.gEspmList.lb_select_index(lb_selection_dex)    # so that (un)checking also selects (moves the highlight)
        if not get_shift_down():
            self.refreshCurrent(self.file_info)

    def get_espm(self, lb_selection_dex):
        plugin_name = self.gEspmList.lb_get_str_item_at_index(
            lb_selection_dex).replace(u'&&', u'&')
        if plugin_name[0] == u'*':
            plugin_name = plugin_name[1:]
        return GPath_no_norm(plugin_name)

    def _on_plugin_filter_dclick(self, selected_index):
        """Handles double-clicking on a plugin in the plugin filter."""
        if selected_index < 0: return
        selected_name = self.get_espm(selected_index)
        if selected_name not in bosh.modInfos: return
        balt.Link.Frame.notebook.SelectPage(u'Mods', selected_name)

    def set_subpackage_checkmarks(self, checked):
        """Checks or unchecks all subpackage checkmarks and propagates that
        information to BAIN."""
        self.gSubList.set_all_checkmarks(checked=checked)
        for index in range(self.gSubList.lb_get_items_count()):
            # + 1 due to empty string included in subActives by BAIN
            self.file_info.subActives[index + 1] = checked

    # FOMOD Handling Implementation & API -------------------------------------
    def _update_fomod_state(self):
        """Shows or hides and enables or disables the FOMOD/Sub-Packages radio
        buttons as well as the Sub-Packages list based on whether or not the
        current installer has an active FOMOD config."""
        inst_info = self.file_info
        # Needs to be a bool for wx, otherwise it will assert
        has_fomod = bool(inst_info and inst_info.has_fomod_conf)
        self.fomod_btn.visible = has_fomod
        self.sp_btn.visible = has_fomod
        self.sp_label.visible = not has_fomod
        # Same deal as above. Note that we need to do these always, otherwise
        # the Sub-Packages list would stay disabled when switching installers
        fomod_checked = bool(has_fomod and inst_info.extras_dict.get(
            u'fomod_active', False))
        self.fomod_btn.is_checked = fomod_checked
        self.sp_btn.is_checked = not fomod_checked
        self.gSubList.enabled = not fomod_checked
        self.sp_panel.update_layout()

    def set_fomod_mode(self, fomod_enabled):
        """Programatically enables or disables FOMOD mode and updates the GUI
        as needed. Does not refresh, callers are responsible for that."""
        self.file_info.extras_dict[u'fomod_active'] = fomod_enabled
        # Uncheck all subpackages, otherwise the FOMOD files will get combined
        # with the ones from the checked subpackages. Store the active
        # sub-packages and restore them if we go back to regular sub-packages
        # mode again. This is a big fat HACK: it shouldn't be necessary to do
        # this - fix BAIN so it isn't.
        if fomod_enabled:
            self.file_info.extras_dict[
                u'fomod_prev_sub_actives'] = self.file_info.subActives[:]
            self.set_subpackage_checkmarks(checked=False)
        else:
            prev_sub_actives = self.file_info.extras_dict.get(
                u'fomod_prev_sub_actives', [])
            # Make sure we can actually apply the stored subActives - package
            # could have changed since we saved these
            if prev_sub_actives and len(prev_sub_actives) == len(
                    self.file_info.subActives):
                self.file_info.subActives = prev_sub_actives[:]
                # See set_subpackage_checkmarks for the off-by-one explanation
                for i, sa_checked in enumerate(prev_sub_actives[1:]):
                    if i >= self.gSubList.lb_get_items_count():
                        break # Otherwise breaks for 'simple' packages w/ FOMOD
                    self.gSubList.lb_check_at_index(i, sa_checked)
        self._update_fomod_state()

    def _on_fomod_checked(self, _checked): # Ignore, could be either one
        """Internal callback, called when one of the FOMOD/Sub-Packages radio
        buttons has been checked."""
        self.set_fomod_mode(self.fomod_btn.is_checked)
        self.refreshCurrent(self.file_info)

class InstallersPanel(BashTab):
    """Panel for InstallersTank."""
    espmMenu = Links()
    subsMenu = Links()
    keyPrefix = u'bash.installers'
    _ui_list_type = InstallersList
    _details_panel_type = InstallersDetails

    def __init__(self,parent):
        """Initialize."""
        BashFrame.iPanel = self
        self.listData = bosh.bain.Installer.instData = bosh.bain.InstallersData()
        super(InstallersPanel, self).__init__(parent)
        #--Refreshing
        self._data_dir_scanned = False
        self.refreshing = False
        self.frameActivated = False
        # if user cancels the refresh in wx 3 because progress is an OS
        # window Bash effectively regains focus and keeps trying to refresh
        # FIXME(ut) hack we must rewrite Progress for wx 3
        self._user_cancelled = False

    @balt.conversation
    def _first_run_set_enabled(self):
        if settings[u'bash.installers.isFirstRun']:
            settings[u'bash.installers.isFirstRun'] = False
            message = _(u'Do you want to enable Installers?') + u'\n\n\t' + _(
                u'If you do, Bash will first need to initialize some data. '
                u'This can take on the order of five minutes if there are '
                u'many mods installed.') + u'\n\n\t' + _(
                u'If not, you can enable it at any time by right-clicking '
                u"the column header menu and selecting 'Enabled'.")
            settings[u'bash.installers.enabled'] = balt.askYes(self, message,
                                                              _(u'Installers'))

    @balt.conversation
    def ShowPanel(self, canCancel=True, fullRefresh=False, scan_data_dir=False,
                  focus_list=False, **kwargs):
        """Panel is shown. Update self.data."""
        self._first_run_set_enabled() # must run _before_ if below
        if (not settings[u'bash.installers.enabled'] or self.refreshing
                or self._user_cancelled):
            self._user_cancelled = False
            return
        try:
            self.refreshing = True
            self._refresh_installers_if_needed(canCancel, fullRefresh,
                                               scan_data_dir, focus_list)
            super(InstallersPanel, self).ShowPanel()
        finally:
            self.refreshing = False

    @balt.conversation
    @bosh.bain.projects_walk_cache
    def _refresh_installers_if_needed(self, canCancel, fullRefresh,
                                      scan_data_dir, focus_list):
        if settings.get(u'bash.installers.updatedCRCs',True): #only checked here
            settings[u'bash.installers.updatedCRCs'] = False
            self._data_dir_scanned = False
        do_refresh = scan_data_dir = scan_data_dir or not self._data_dir_scanned
        refresh_info = None
        if self.frameActivated:
            folders, files = top_level_items(bass.dirs[u'installers'])
            omds = [GPath_no_norm(inst_path) for inst_path in files
                    if os.path.splitext(inst_path)[1].lower() in archives.omod_exts]
            if any(inst_path not in omods.failedOmods for inst_path in omds):
                omod_projects = self.__extractOmods(omds) ##: change above to filter?
                folders.extend(omod_projects)
            if not do_refresh:
                refresh_info = self.listData.scan_installers_dir(folders,
                    files, fullRefresh)
                do_refresh = refresh_info.refresh_needed()
        refreshui = False
        if do_refresh:
            with balt.Progress(_(u'Refreshing Installers...'),
                               u'\n' + u' ' * 60, abort=canCancel) as progress:
                try:
                    what = u'DISC' if scan_data_dir else u'IC'
                    refreshui |= self.listData.irefresh(progress, what,
                                                        fullRefresh,
                                                        refresh_info)
                    self.frameActivated = False
                except CancelError:
                    self._user_cancelled = True # User canceled the refresh
                finally:
                    self._data_dir_scanned = True
        elif self.frameActivated and self.listData.refreshConvertersNeeded():
            with balt.Progress(_(u'Refreshing Converters...'),
                               u'\n' + u' ' * 60) as progress:
                try:
                    refreshui |= self.listData.irefresh(progress, u'C',
                                                        fullRefresh)
                    self.frameActivated = False
                except CancelError:
                    pass # User canceled the refresh
        do_refresh = self.listData.refreshTracked()
        refreshui |= do_refresh and self.listData.refreshInstallersStatus()
        if refreshui: self.uiList.RefreshUI(focus_list=focus_list)

    def __extractOmods(self, omds):
        omod_projects = []
        with balt.Progress(_(u'Extracting OMODs...'),
                           u'\n' + u' ' * 60) as progress:
            dirInstallersJoin = bass.dirs[u'installers'].join
            progress.setFull(max(len(omds), 1))
            omodMoves, omodRemoves = set(), set()
            for i, omod in enumerate(omds):
                progress(i, omod.s)
                pr_name = bosh.InstallerProject.unique_name(omod.body,
                                                            check_exists=True)
                outDir = dirInstallersJoin(pr_name)
                try:
                    omod_path = dirInstallersJoin(omod)
                    bosh.omods.OmodFile(omod_path).extractToProject(
                        outDir, SubProgress(progress, i))
                    omodRemoves.add(omod_path)
                    omod_projects.append(pr_name.s)
                except (CancelError, SkipError):
                    omodMoves.add(omod_path)
                except:
                    deprint(f"Error extracting OMOD '{omod}':", traceback=True)
                    # Ensure we don't infinitely refresh if moving the omod
                    # fails
                    bosh.omods.failedOmods.add(omod)
                    omodMoves.add(omod_path)
            # Cleanup
            dialog_title = _(u'OMOD Extraction - Cleanup Error')
            # Delete extracted omods
            def _del(files): env.shellDelete(files, parent=self._native_widget)
            try:
                _del(omodRemoves)
            except (CancelError, SkipError):
                while balt.askYes(self, _(
                        u'Bash needs Administrator Privileges to delete '
                        u'OMODs that have already been extracted.') +
                        u'\n\n' + _(u'Try again?'), dialog_title):
                    try:
                        omodRemoves = [x for x in omodRemoves if x.exists()]
                        _del(omodRemoves)
                    except (CancelError, SkipError):
                        continue
                    break
                else:
                    # User decided not to give permission.  Add omod to
                    # 'failedOmods' so we know not to try to extract them again
                    for omod in omodRemoves:
                        if omod.exists():
                            bosh.omods.failedOmods.add(omod.tail)
            # Move bad omods
            def _move_omods(failed):
                dests = [dirInstallersJoin(u'Bash', u'Failed OMODs', omod.tail)
                         for omod in failed]
                env.shellMove(failed, dests, parent=self._native_widget)
            try:
                omodMoves = list(omodMoves)
                env.shellMakeDirs([dirInstallersJoin('Bash', 'Failed OMODs')])
                _move_omods(omodMoves)
            except (CancelError, SkipError):
                while balt.askYes(self, _(
                        u'Bash needs Administrator Privileges to move failed '
                        u'OMODs out of the Bash Installers directory.') +
                        u'\n\n' + _(u'Try again?'), dialog_title):
                    try:
                        omodMoves = [x for x in omodMoves if x.exists()]
                        _move_omods(omodMoves)
                    except (CancelError, SkipError):
                        continue
        return omod_projects

    def _sbCount(self):
        active = sum(x.is_active for x in self.listData.values())
        return _(u'Packages:') + u' %d/%d' % (active, len(self.listData))

    def RefreshUIMods(self, mods_changed, inis_changed):
        """Refresh UI plus refresh mods state."""
        self.uiList.RefreshUI()
        if mods_changed:
            BashFrame.modList.RefreshUI(refreshSaves=True, focus_list=False)
            Link.Frame.warn_corrupted(warn_mods=True, warn_strings=True)
            Link.Frame.warn_load_order()
        if inis_changed:
            if BashFrame.iniList is not None:
                BashFrame.iniList.RefreshUI(focus_list=False)
        # TODO(ut) : add bsas_changed param! (or rather move this inside BAIN)
        bosh.bsaInfos.refresh()
        Link.Frame.warn_corrupted(warn_bsas=True)

#------------------------------------------------------------------------------
class ScreensList(balt.UIList):
    column_links = Links() #--Column menu
    context_links = Links() #--Single item menu
    global_links = defaultdict(lambda: Links()) # Global menu
    _shellUI = True
    _editLabels = _copy_paths = True

    _sort_keys = {u'File'    : None,
                  u'Modified': lambda self, a: self.data_store[a].mtime,
                  u'Size'    : lambda self, a: self.data_store[a].fsize,
                 }
    #--Labels
    labels = OrderedDict([
        (u'File',     lambda self, p: p.s),
        (u'Modified', lambda self, p: format_date(self.data_store[p].mtime)),
        (u'Size',     lambda self, p: round_size(self.data_store[p].fsize)),
    ])

    #--Events ---------------------------------------------
    def OnDClick(self, lb_dex_and_flags):
        """Double click a screenshot"""
        hitItem = self._getItemClicked(lb_dex_and_flags)
        if hitItem:
            self.OpenSelected(selected=[hitItem])
        return EventResult.FINISH

    @balt.conversation
    def OnLabelEdited(self, is_edit_cancelled, evt_label, evt_index, evt_item):
        """Rename selected screenshots."""
        if is_edit_cancelled: return EventResult.CANCEL
        root, numStr = self.panel.detailsPanel.file_info.validate_filename_str(
            evt_label)
        if numStr is None: # allow for number only names
            balt.showError(self, root)
            return EventResult.CANCEL
        selected = self.GetSelectedInfos()
        #--Rename each screenshot, keeping the old extension
        num = int(numStr or  0)
        digits = len(u'%s' % (num + len(selected) - 1))
        numStr = numStr.zfill(digits) if numStr else u''
        with BusyCursor():
            to_select = set()
            to_del = set()
            item_edited = [self.panel.detailsPanel.displayed_item]
            for scrinf in selected:
                if not self.try_rename(scrinf, root, numStr, to_select, to_del,
                                       item_edited): break
                num += 1
                numStr = str(num).zfill(digits)
            if to_select:
                self.RefreshUI(redraw=to_select, to_del=to_del,
                               detail_item=item_edited[0])
                #--Reselected the renamed items
                self.SelectItemsNoCallback(to_select)
            return EventResult.CANCEL

    def try_rename(self, scrinf, root, numStr, to_select=None, to_del=None,
                   item_edited=None):
        newName = GPath(root + numStr + scrinf.abs_path.ext) # TODO: refactor ScreenInfo.unique_key()
        if scrinf.get_store().store_dir.join(newName).exists():
            return None # break
        oldName = self._try_rename(scrinf, newName)
        if oldName:
            if to_select is not None: to_select.add(newName)
            if to_del is not None: to_del.add(oldName)
            if item_edited and oldName == item_edited[0]:
                item_edited[0] = newName
            return oldName, newName # continue

    def _handle_key_up(self, wrapped_evt):
        # Enter: Open selected screens
        if wrapped_evt.key_code in balt.wxReturn: self.OpenSelected()
        else: super(ScreensList, self)._handle_key_up(wrapped_evt)

#------------------------------------------------------------------------------
class ScreensDetails(_DetailsMixin, NotebookPanel):

    def __init__(self, parent, ui_list_panel):
        super(ScreensDetails, self).__init__(parent)
        self.screenshot_control = Picture(parent, 256, 192,
            background=colors[u'screens.bkgd.image'])
        self.displayed_screen = None # type: bolt.Path
        HLayout(item_expand=True, item_weight=1,
                items=[self.screenshot_control]).apply_to(self)

    @property
    def displayed_item(self): return self.displayed_screen

    @property
    def file_infos(self): return bosh.screen_infos

    def _resetDetails(self):
        self.screenshot_control.set_bitmap(None)

    def SetFile(self, fileName=u'SAME'):
        """Set file to be viewed."""
        #--Reset?
        self.displayed_screen = super(ScreensDetails, self).SetFile(fileName)
        if not self.displayed_screen: return
        if self.file_info.cached_bitmap is None:
            self.file_info.cached_bitmap = self.screenshot_control.set_bitmap(
                self.file_info.abs_path)
        else:
            self.screenshot_control.set_bitmap(self.file_info.cached_bitmap)

    def RefreshUIColors(self):
        self.screenshot_control.SetBackground(colors[u'screens.bkgd.image'])

#------------------------------------------------------------------------------
class ScreensPanel(BashTab):
    """Screenshots tab."""
    keyPrefix = u'bash.screens'
    _status_str = _(u'Screens:') + u' %d'
    _ui_list_type = ScreensList
    _details_panel_type = ScreensDetails

    def __init__(self,parent):
        """Initialize."""
        self.listData = bosh.screen_infos = bosh.ScreenInfos()
        super(ScreensPanel, self).__init__(parent)

    def ShowPanel(self, **kwargs):
        """Panel is shown. Update self.data."""
        if bosh.screen_infos.refresh():
            self.uiList.RefreshUI(focus_list=False)
        super(ScreensPanel, self).ShowPanel()

#------------------------------------------------------------------------------
class BSAList(balt.UIList):
    column_links = Links() #--Column menu
    context_links = Links() #--Single item menu
    global_links = defaultdict(lambda: Links()) # Global menu
    _sort_keys = {u'File'    : None,
                  u'Modified': lambda self, a: self.data_store[a].mtime,
                  u'Size'    : lambda self, a: self.data_store[a].fsize,
                 }
    #--Labels
    labels = OrderedDict([
        (u'File',     lambda self, p: p.s),
        (u'Modified', lambda self, p: format_date(self.data_store[p].mtime)),
        (u'Size',     lambda self, p: round_size(self.data_store[p].fsize)),
    ])

#------------------------------------------------------------------------------
class BSADetails(_EditableMixinOnFileInfos, SashPanel):
    """BSAfile details panel."""

    @property
    def file_info(self): return self._bsa_info
    @property
    def file_infos(self): return bosh.bsaInfos
    @property
    def allowDetailsEdit(self): return True

    def __init__(self, parent, ui_list_panel):
        SashPanel.__init__(self, parent, isVertical=False)
        top, bottom = self.left, self.right
        _EditableMixinOnFileInfos.__init__(self, bottom, ui_list_panel)
        #--Data
        self._bsa_info = None
        #--BSA Info
        self.gInfo = TextArea(bottom)
        self.gInfo.on_text_changed.subscribe(self.OnInfoEdit)
        #--Layout
        VLayout(item_expand=True, items=[
            Label(top, _(u'File:')), self._fname_ctrl]).apply_to(top)
        VLayout(spacing=4, items=[
            (self.gInfo, LayoutOptions(expand=True)),
            HLayout(spacing=4, items=[self._save_btn, self._cancel_btn])
        ]).apply_to(bottom)

    def _resetDetails(self):
        self._bsa_info = None
        self.fileStr = u''

    def SetFile(self, fileName=u'SAME'):
        """Set file to be viewed."""
        fileName = super(BSADetails, self).SetFile(fileName)
        if fileName:
            self._bsa_info = bosh.bsaInfos[fileName]
            #--Remember values for edit checks
            self.fileStr = self._bsa_info.ci_key.s
            self.gInfo.text_content = self._bsa_info.get_table_prop(u'info',
                _(u'Notes: '))
        else:
            self.gInfo.text_content = _(u'Notes: ')
        #--Set Fields
        self._fname_ctrl.text_content = self.fileStr
        #--Info Box
        self.gInfo.modified = False

    def OnInfoEdit(self, new_text):
        """Info field was edited."""
        if self._bsa_info and self.gInfo.modified:
            self._bsa_info.set_table_prop(u'info', new_text)

    @balt.conversation
    def DoSave(self):
        """Event: Clicked Save button."""
        #--Change Tests
        changeName = (self.fileStr != self._bsa_info.ci_key)
        #--Change Name?
        if changeName:
            newName = GPath(self.fileStr.strip())
            if self.panel_uilist.try_rename(self._bsa_info, newName):
                self.panel_uilist.RefreshUI(detail_item=self.file_info.ci_key)

#------------------------------------------------------------------------------
class BSAPanel(BashTab):
    """BSA info tab."""
    keyPrefix = u'bash.BSAs'
    _status_str = _(u'BSAs:') + u' %d'
    _ui_list_type = BSAList
    _details_panel_type = BSADetails

    def __init__(self,parent):
        self.listData = bosh.bsaInfos
        bosh.bsaInfos.refresh()
        super(BSAPanel, self).__init__(parent)
        BashFrame.bsaList = self.uiList

#--Tabs menu ------------------------------------------------------------------
_widget_to_panel = {}
class _Tab_Link(AppendableLink, CheckLink, EnabledLink):
    """Handle hiding/unhiding tabs."""
    def __init__(self,tabKey,canDisable=True):
        super(_Tab_Link, self).__init__()
        self.tabKey = tabKey
        self.enabled = canDisable
        className, self._text, item = tabInfo.get(self.tabKey,[None,None,None])
        self._help = _(u'Show/Hide the %(tabtitle)s Tab.') % (
            {u'tabtitle': self._text})

    def _append(self, window): return self._text is not None

    def _enable(self): return self.enabled

    def _check(self): return bass.settings[u'bash.tabs.order'][self.tabKey]

    def Execute(self):
        if bass.settings[u'bash.tabs.order'][self.tabKey]:
            # It was enabled, disable it.
            iMods = None
            iInstallers = None
            iDelete = None
            for i in range(Link.Frame.notebook.GetPageCount()):
                pageTitle = Link.Frame.notebook.GetPageText(i)
                if pageTitle == tabInfo[u'Mods'][1]:
                    iMods = i
                elif pageTitle == tabInfo[u'Installers'][1]:
                    iInstallers = i
                if pageTitle == tabInfo[self.tabKey][1]:
                    iDelete = i
            if iDelete == Link.Frame.notebook.GetSelection():
                # We're deleting the current page...
                if ((iDelete == 0 and iInstallers == 1) or
                        (iDelete - 1 == iInstallers)):
                    # The auto-page change will change to
                    # the 'Installers' tab.  Change to the
                    # 'Mods' tab instead.
                    Link.Frame.notebook.SetSelection(iMods)
            tabInfo[self.tabKey][2].ClosePanel() ##: note the panel remains in memory
            page = Link.Frame.notebook.GetPage(iDelete)
            Link.Frame.notebook.RemovePage(iDelete)
            page.Show(False)
        else:
            # It was disabled, enable it
            insertAt = 0
            for k, k_enabled in bass.settings[u'bash.tabs.order'].items():
                if k == self.tabKey: break
                insertAt += k_enabled
            className,title,panel = tabInfo[self.tabKey]
            if not panel:
                panel = globals()[className](Link.Frame.notebook)
                tabInfo[self.tabKey][2] = panel
                _widget_to_panel[panel.wx_id_()] = panel
            if insertAt > Link.Frame.notebook.GetPageCount():
                Link.Frame.notebook.AddPage(panel._native_widget,title)
            else:
                Link.Frame.notebook.InsertPage(insertAt,panel._native_widget,title)
        bass.settings[u'bash.tabs.order'][self.tabKey] ^= True

class BashNotebook(wx.Notebook, balt.TabDragMixin):

    # default tabs order and default enabled state, keys as in tabInfo
    _tabs_enabled_ordered = OrderedDict(((u'Installers', True),
                                        (u'Mods', True),
                                        (u'Saves', True),
                                        (u'INI Edits', True),
                                        (u'Screenshots', True),
                                        # (u'BSAs', False),
                                       ))

    @staticmethod
    def _tabOrder():
        """Return dict containing saved tab order and enabled state of tabs."""
        newOrder = settings.get(u'bash.tabs.order',
                                BashNotebook._tabs_enabled_ordered)
        # append any new tabs - appends last
        newTabs = set(tabInfo) - set(newOrder)
        for n in newTabs: newOrder[n] = BashNotebook._tabs_enabled_ordered[n]
        # delete any removed tabs
        deleted = set(newOrder) - set(tabInfo)
        for d in deleted: del newOrder[d]
        # Ensure the 'Mods' tab is always shown
        if u'Mods' not in newOrder: newOrder[u'Mods'] = True # inserts last
        settings[u'bash.tabs.order'] = newOrder
        return newOrder

    def __init__(self, parent):
        wx.Notebook.__init__(self, parent)
        balt.TabDragMixin.__init__(self)
        #--Pages
        iInstallers = iMods = -1
        for page, enabled in self._tabOrder().items():
            if not enabled: continue
            className, title, item = tabInfo[page]
            panel = globals().get(className,None)
            if panel is None: continue
            deprint(u"Constructing panel '%s'" % title)
            # Some page specific stuff
            if page == u'Installers': iInstallers = self.GetPageCount()
            elif page == u'Mods': iMods = self.GetPageCount()
            # Add the page
            try:
                item = panel(self)
                self.AddPage(item._native_widget, title)
                tabInfo[page][2] = item
                _widget_to_panel[item.wx_id_()] = item
                deprint(u"Panel '%s' constructed successfully" % title)
            except:
                if page == u'Mods':
                    deprint(u"Fatal error constructing panel '%s'." % title)
                    raise
                deprint(u"Error constructing '%s' panel." % title,
                        traceback=True)
                settings[u'bash.tabs.order'][page] = False
        #--Selection
        pageIndex = max(min(
            settings[u'bash.page'], self.GetPageCount() - 1), 0)
        if settings[u'bash.installers.fastStart'] and pageIndex == iInstallers:
            pageIndex = iMods
        self.SetSelection(pageIndex)
        self.currentPage = _widget_to_panel[
            self.GetPage(self.GetSelection()).GetId()]
        #--Setup Popup menu for Right Click on a Tab
        self.Bind(wx.EVT_CONTEXT_MENU, self.DoTabMenu)

    @staticmethod
    def tabLinks(menu):
        for key in BashNotebook._tabOrder(): # use tabOrder here - it is used in
            # InitLinks which runs _before_ settings[u'bash.tabs.order'] is set!
            canDisable = bool(key != u'Mods')
            menu.append(_Tab_Link(key, canDisable))
        return menu

    def SelectPage(self, page_title, item):
        ind = 0
        for title, enabled in settings[u'bash.tabs.order'].items():
            if title == page_title:
                if not enabled: return
                break
            ind += enabled
        else: raise BoltError(u'Invalid page: %s' % page_title)
        self.SetSelection(ind)
        tabInfo[page_title][2].SelectUIListItem(item, deselectOthers=True)

    def DoTabMenu(self,event):
        pos = event.GetPosition()
        pos = self.ScreenToClient(pos)
        tabId = self.HitTest(pos)
        if tabId != wx.NOT_FOUND and tabId[0] != wx.NOT_FOUND:
            menu = self.tabLinks(Links())
            menu.popup_menu(self, None)
        else:
            event.Skip()

    def drag_tab(self, newPos):
        # Find the key
        removeTitle = self.GetPageText(newPos)
        oldOrder = list(settings[u'bash.tabs.order'])
        for removeKey in oldOrder:
            if tabInfo[removeKey][1] == removeTitle:
                break
        oldOrder.remove(removeKey)
        if newPos == 0: # Moved to the front
            newOrder = [removeKey] + oldOrder
        elif newPos == self.GetPageCount() - 1: # Moved to the end
            newOrder = oldOrder + [removeKey]
        else: # Moved somewhere in the middle
            nextTabTitle = self.GetPageText(newPos+1)
            for nextTabKey in oldOrder:
                if tabInfo[nextTabKey][1] == nextTabTitle:
                    break
            nextTabIndex = oldOrder.index(nextTabKey)
            newOrder = oldOrder[:nextTabIndex]+[removeKey]+oldOrder[nextTabIndex:]
        settings[u'bash.tabs.order'] = OrderedDict(
            (k, settings[u'bash.tabs.order'][k]) for k in newOrder)

    def OnShowPage(self,event):
        """Call panel's ShowPanel() and set the current panel."""
        if event.GetId() == self.GetId(): ##: why ?
            bolt.GPathPurge()
            self.currentPage = _widget_to_panel[
                self.GetPage(event.GetSelection()).GetId()]
            self.currentPage.ShowPanel(
                refresh_target=load_order.using_ini_file())
            event.Skip() ##: shouldn't this always be called ?

#------------------------------------------------------------------------------
class BashStatusBar(DnDStatusBar):
    #--Class Data
    obseButton = None
    laaButton = None

    def UpdateIconSizes(self, skip_refresh=False):
        self.buttons = [] # will be populated with _displayed_ gButtons - g ?
        order = settings[u'bash.statusbar.order']
        hide = settings[u'bash.statusbar.hide']
        # Add buttons in order that is saved - on first run order = [] !
        for uid in order[:]:
            link = self.GetLink(uid=uid)
            # Doesn't exist?
            if link is None:
                order.remove(uid)
                continue
            # Hidden?
            if uid in hide: continue
            # Not present ?
            if not link.IsPresent(): continue
            # Add it
            try:
                self._addButton(link)
            except AttributeError: # '_App_Button' object has no attribute 'imageKey'
                deprint(u'Failed to load button %r' % (uid,), traceback=True)
        # Add any new buttons
        for link in BashStatusBar.buttons:
            # Already tested?
            uid = link.uid
            if uid in order: continue
            # Remove any hide settings, if they exist
            if uid in hide:
                hide.discard(uid)
            order.append(uid)
            try:
                self._addButton(link)
            except AttributeError:
                deprint(u'Failed to load button %r' % (uid,), traceback=True)
        if not skip_refresh:
            self.refresh_status_bar(refresh_icon_size=True)

    def HideButton(self, button, skip_refresh=False):
        if button in self.buttons:
            # Find the BashStatusBar_Button instance that made it
            link = self.GetLink(button=button)
            if link:
                button.visible = False
                self.buttons.remove(button)
                settings[u'bash.statusbar.hide'].add(link.uid)
                if not skip_refresh:
                    self.refresh_status_bar()

    def UnhideButton(self, link, skip_refresh=False):
        uid = link.uid
        settings[u'bash.statusbar.hide'].discard(uid)
        # Find the position to insert it at
        order = settings[u'bash.statusbar.order']
        if uid not in order:
            # Not specified, put it at the end
            order.append(uid)
            self._addButton(link)
        else:
            # Specified, but now factor in hidden buttons, etc
            self._addButton(link)
            button = self.buttons.pop()
            thisIndex, insertBefore = order.index(link.uid), 0
            for i in range(len(self.buttons)):
                otherlink = self.GetLink(index=i)
                indexOther = order.index(otherlink.uid)
                if indexOther > thisIndex:
                    insertBefore = i
                    break
            self.buttons.insert(insertBefore,button)
        if not skip_refresh:
            self.refresh_status_bar()

    def GetLink(self,uid=None,index=None,button=None):
        """Get the Link object with a specific uid,
           or that made a specific button."""
        if uid is not None:
            for link in BashStatusBar.buttons:
                if link.uid == uid:
                    return link
        elif index is not None:
            button = self.buttons[index]
        if button is not None:
            for link in BashStatusBar.buttons:
                if link.gButton is button:
                    return link
        return None

    def refresh_status_bar(self, refresh_icon_size=False):
        """Updates status widths and the icon sizes, if refresh_icon_size is
        True. Also propagates resizing events.

        :param refresh_icon_size: Whether or not to update icon sizes too."""
        txt_len = 280 if bush.game.has_esl else 130
        self.SetStatusWidths([self.iconsSize * len(self.buttons), -1, txt_len])
        if refresh_icon_size: self.SetSize((-1, self.iconsSize))
        # Causes the status bar to fill half the screen on wxGTK
        ##: See if removing this call entirely causes problems on Windows
        if wx.Platform != u'__WXGTK__': self.SendSizeEventToParent()
        self.OnSize()

#------------------------------------------------------------------------------
class BashFrame(WindowFrame):
    """Main application frame."""
    ##:ex basher globals - hunt their use down - replace with methods - see #63
    docBrowser = None
    plugin_checker = None
    # UILists - use sparingly for inter Panel communication
    # modList is always set but for example iniList may be None (tab not
    # enabled).
    saveList = None
    iniList = None
    modList = None
    bsaList = None
    # Panels - use sparingly
    iPanel = None # BAIN panel
    # initial size/position
    _frame_settings_key = u'bash.frame'
    _def_size = (1024, 512)
    _size_hints = (512, 512)

    @property
    def statusBar(self): return self._native_widget.GetStatusBar()

    def __init__(self, parent=None):
        #--Singleton
        balt.Link.Frame = self
        #--Window
        super(BashFrame, self).__init__(parent, title=u'Wrye Bash',
                                        icon_bundle=Resources.bashRed,
                                        sizes_dict=bass.settings)
        self.set_bash_frame_title()
        # Status Bar & Global Menu
        self._native_widget.SetStatusBar(BashStatusBar(self._native_widget))
        self.global_menu = None
        self.set_global_menu(GlobalMenu())
        #--Notebook panel
        # attributes used when ini panel is created (warn for missing game ini)
        self.oblivionIniCorrupted = u''
        self.oblivionIniMissing = self._oblivionIniMissing = False
        self.notebook = BashNotebook(self._native_widget)
        #--Data
        self.inRefreshData = False #--Prevent recursion while refreshing.
        self.knownCorrupted = set()
        self.known_invalid_versions = set()
        self.known_older_form_versions = set()
        self.known_mismatched_version_bsas = set()
        self.known_ba2_collisions = set()
        self.incompleteInstallError = False

    @balt.conversation
    def warnTooManyModsBsas(self):
        limit_fixers = bush.game.Se.limit_fixer_plugins
        if not limit_fixers: return # Problem does not apply to this game
        if not bass.inisettings[u'WarnTooManyFiles']: return
        for lf in limit_fixers:
            lf_path = bass.dirs[u'mods'].join(bush.game.Se.plugin_dir,
                                              u'plugins', lf)
            if lf_path.is_file():
                return # Limit-fixing xSE plugin installed
        if not len(bosh.bsaInfos): bosh.bsaInfos.refresh()
        if len(bosh.bsaInfos) + len(bosh.modInfos) >= 325 and not \
                settings[u'bash.mods.autoGhost']:
            message = _(u'It appears that you have more than 325 mods and bsas'
                u' in your %s directory and auto-ghosting is disabled. This '
                u'may cause problems in %s; see the readme under auto-ghost '
                u'for more details and please enable auto-ghost.') % \
                      (bush.game.mods_dir, bush.game.displayName)
            if len(bosh.bsaInfos) + len(bosh.modInfos) >= 400:
                message = _(u'It appears that you have more than 400 mods and '
                    u'bsas in your %s directory and auto-ghosting is '
                    u'disabled. This will cause problems in %s; see the readme'
                    u' under auto-ghost for more details. ') % \
                          (bush.game.mods_dir, bush.game.displayName)
            balt.showWarning(self, message, _(u'Too many mod files.'))

    def bind_refresh(self, bind=True):
        if self._native_widget:
            try:
                self.on_activate.subscribe(self.RefreshData) if bind else \
                    self.on_activate.unsubscribe(self.RefreshData)
                return True
            except UnknownListener:
                # when first called via RefreshData in balt.conversation
                return False # we were not bound

    def Restart(self, *args):
        """Restart Bash - edit bass.sys_argv with specified args then let
        bash.exit_cleanup() handle restart.

        :param args: tuple of lists of command line args - use the *long*
                     options, for instance --Language and not -L
        """
        for arg in args:
            bass.update_sys_argv(arg)
        #--Restarting, assume users don't want to be prompted again about UAC
        bass.update_sys_argv([u'--no-uac'])
        # restart
        bass.is_restarting = True
        self.close_win(True)

    def set_bash_frame_title(self):
        """Set title. Set to default if no title supplied."""
        if bush.game.altName and settings[u'bash.useAltName']:
            title = bush.game.altName + u' %s%s'
        else:
            title = u'Wrye Bash %s%s '+_(u'for')+u' '+bush.game.displayName
        title %= (bass.AppVersion, (u' ' + _(u'(Standalone)'))
                                    if bass.is_standalone else u'')
        title += u': '
        # chop off save prefix - +1 for the path separator
        maProfile = bosh.saveInfos.localSave[len(
            bush.game.Ini.save_prefix) + 1:]
        if maProfile:
            title += maProfile
        else:
            title += _(u'Default')
        if bosh.modInfos.voCurrent:
            title += f' [{bosh.modInfos.voCurrent}]'
        self._native_widget.SetTitle(title)

    def set_status_count(self, requestingPanel, countTxt):
        """Sets status bar count field."""
        if self.notebook.currentPage is requestingPanel: # we need to check if
        # requesting Panel is currently shown because Refresh UI path may call
        # Refresh UI of other tabs too - this results for instance in mods
        # count flickering when deleting a save in saves tab - ##: hunt down
            self.statusBar.SetStatusText(countTxt, 2)

    def set_status_info(self, infoTxt):
        """Sets status bar info field."""
        self.statusBar.SetStatusText(infoTxt, 1)

    #--Events ---------------------------------------------
    @balt.conversation
    def RefreshData(self, evt_active=True, booting=False):
        """Refresh all data - window activation event callback, called also
        on boot."""
        #--Ignore deactivation events.
        if not evt_active or self.inRefreshData: return
        #--UPDATES-----------------------------------------
        self.inRefreshData = True
        popMods = popSaves = popBsas = None
        #--Config helpers
        bosh.lootDb.refreshBashTags()
        #--Check bsas, needed to detect string files in modInfos refresh...
        bosh.oblivionIni.get_ini_language(cached=False) # reread ini language
        if not booting and bosh.bsaInfos.refresh():
            popBsas = u'ALL'
        #--Check plugins.txt and mods directory...
        if not booting and bosh.modInfos.refresh():
            popMods = u'ALL'
        #--Check savegames directory...
        if not booting and bosh.saveInfos.refresh():
            popSaves = u'ALL'
        #--Repopulate, focus will be set in ShowPanel
        if popMods:
            BashFrame.modList.RefreshUI(refreshSaves=True, # True just in case
                                        focus_list=False)
        elif popSaves:
            BashFrame.saveListRefresh(focus_list=False)
        if popBsas:
            BashFrame.bsaListRefresh(focus_list=False)
        #--Show current notebook panel
        if self.iPanel: self.iPanel.frameActivated = True
        self.notebook.currentPage.ShowPanel(refresh_infos=not booting,
                                            clean_targets=not booting)
        #--WARNINGS----------------------------------------
        if booting: self.warnTooManyModsBsas()
        self.warn_load_order()
        self._warn_reset_load_order()
        self.warn_corrupted(warn_mods=True, warn_saves=True, warn_strings=True,
                            warn_bsas=True)
        self.warn_game_ini()
        self._missingDocsDir()
        #--Done (end recursion blocker)
        self.inRefreshData = False
        return EventResult.FINISH

    def _warn_reset_load_order(self):
        if load_order.warn_locked and not bass.inisettings[
            u'SkipResetTimeNotifications']:
            balt.showWarning(self, _(u'Load order has changed outside of Bash '
                u'and has been reverted to the one saved in Bash. You can hit '
                u'Ctrl + Z while the mods list has focus to undo this.'),
                             _(u'Lock Load Order'))
            load_order.warn_locked = False

    def warn_load_order(self):
        """Warn if plugins.txt has bad or missing files, or is overloaded."""
        def warn(message, lists, title=_(u'Warning: Load List Sanitized')):
            ListBoxes.display_dialog(self, title, message, [lists],
                                     liststyle=u'list', canCancel=False)
        if bosh.modInfos.selectedBad:
           msg = [u'',_(u'Missing files have been removed from load list:')]
           msg.extend(sorted(bosh.modInfos.selectedBad))
           warn(_(u'Missing files have been removed from load list:'), msg)
           bosh.modInfos.selectedBad = set()
        #--Was load list too long? or bad filenames?
        if bosh.modInfos.selectedExtra:## or bosh.modInfos.activeBad:
           ## Disable this message for now, until we're done testing if
           ## we can get the game to load these files
           #if bosh.modInfos.activeBad:
           #    msg = [u'Incompatible names:',
           #           u'Incompatible file names deactivated:']
           #    msg.extend(bosh.modInfos.bad_names)
           #    bosh.modInfos.activeBad = set()
           #    message.append(msg)
           msg = [u'Too many files:', _(
               u'Load list is overloaded.  Some files have been deactivated:')]
           msg.extend(sorted(bosh.modInfos.selectedExtra))
           warn(_(u'Files have been removed from load list:'), msg)
           bosh.modInfos.selectedExtra = set()

    def warn_corrupted(self, warn_mods=False, warn_saves=False,
                       warn_strings=False, warn_bsas=False):
        #--Any new corrupted files?
        message = []
        corruptMods = set(bosh.modInfos.corrupted)
        if warn_mods and not corruptMods <= self.knownCorrupted:
            m = [_(u'Plugin warnings'),
                 _(u'The following mod files have unrecognized headers: ')]
            m.extend(sorted(corruptMods))
            message.append(m)
            self.knownCorrupted |= corruptMods
        corruptSaves = set(bosh.saveInfos.corrupted)
        if warn_saves and not corruptSaves <= self.knownCorrupted:
            m = [_(u'Save game warnings'),
                 _(u'The following save files have errors: ')]
            m.extend(sorted(corruptSaves))
            message.append(m)
            self.knownCorrupted |= corruptSaves
        valid_vers = bush.game.Esp.validHeaderVersions
        invalidVersions = {ck for ck, x in bosh.modInfos.items() if
                           all(x.header.version != v for v in valid_vers)}
        if warn_mods and not invalidVersions <= self.known_invalid_versions:
            m = [_(u'Unrecognized Versions'),
                 _(u'The following mods have unrecognized header versions: ')]
            m.extend(sorted(invalidVersions - self.known_invalid_versions))
            message.append(m)
            self.known_invalid_versions |= invalidVersions
        old_fvers = bosh.modInfos.older_form_versions
        if warn_mods and not old_fvers <= self.known_older_form_versions:
            m = [_(u'Old Header Form Versions'),
                 _(u"The following mods don't use the current plugin Form Version: ")]
            m.extend(sorted(old_fvers - self.known_older_form_versions))
            message.append(m)
            self.known_older_form_versions |= old_fvers
        if warn_strings and bosh.modInfos.new_missing_strings:
            m = [_(u'Missing String Localization files:'),
                 _(u'This will cause CTDs if activated.')]
            m.extend(sorted(bosh.modInfos.missing_strings))
            message.append(m)
            bosh.modInfos.new_missing_strings.clear()
        bsa_mvers = bosh.bsaInfos.mismatched_versions
        if warn_bsas and not bsa_mvers <= self.known_mismatched_version_bsas:
            m = [_(u'Mismatched BSA Versions'),
                 _(u'The following BSAs have a version other than the one '
                   u'this game expects. This can lead to CTDs, please extract '
                   u'and repack them using the %s-provided tool: ') %
                 bush.game.Ck.long_name]
            m.extend(sorted(bsa_mvers - self.known_mismatched_version_bsas))
            message.append(m)
            self.known_mismatched_version_bsas |= bsa_mvers
        ba2_colls = bosh.bsaInfos.ba2_collisions
        if warn_bsas and not ba2_colls <= self.known_ba2_collisions:
            m = [_(u'BA2 Hash Collisions'),
                 _(u'The following BA2s have filenames whose hashes collide, '
                   u'which will cause one or more of them to fail to work '
                   u'correctly. This should be corrected by the mod author(s) '
                   u'by renaming the files to avoid the collision: ')]
            m.extend(sorted(ba2_colls - self.known_ba2_collisions))
            message.append(m)
            self.known_ba2_collisions |= ba2_colls
        if message:
            ListBoxes.display_dialog(
              self, _(u'Warnings'), _(u'The following warnings were found:'),
            message, liststyle=u'list', canCancel=False)

    _ini_missing = _(u'%(ini)s does not exist yet.  %(game)s will create this '
        u'file on first run.  INI tweaks will not be usable until then.')
    @balt.conversation
    def warn_game_ini(self):
        #--Corrupt Oblivion.ini
        if self.oblivionIniCorrupted != bosh.oblivionIni.isCorrupted:
            self.oblivionIniCorrupted = bosh.oblivionIni.isCorrupted
            if self.oblivionIniCorrupted:
                msg = u'\n'.join([self.oblivionIniCorrupted, u'', _(u'Please '
                    u'replace the ini with a default copy and restart Bash.')])
                balt.showWarning(self, msg, _(u'Corrupted game Ini'))
        elif self.oblivionIniMissing != self._oblivionIniMissing:
            self._oblivionIniMissing = self.oblivionIniMissing
            if self._oblivionIniMissing:
                balt.showWarning(self, self._ini_missing % {
                    u'ini': bosh.oblivionIni.abs_path,
                    u'game': bush.game.displayName}, _(u'Missing game Ini'))

    def _missingDocsDir(self):
        #--Missing docs directory?
        testFile = bass.dirs[u'mopy'].join(u'Docs', u'wtxt_teal.css')
        if self.incompleteInstallError or testFile.exists(): return
        self.incompleteInstallError = True
        msg = _(u'Installation appears incomplete. Please re-unzip bash to '
                u'game directory so that ALL files are installed.') + u'\n\n'\
              + _(u'Correct installation will create a Mopy and %s\\Docs '
                  u'directories.') % bush.game.mods_dir
        balt.showWarning(self, msg, _(u'Incomplete Installation'))

    def on_closing(self, destroy=True):
        """Handle Close event. Save application data."""
        try:
            # Save sizes here, in the finally clause position is not saved - todo PY3: test if needed
            super(BashFrame, self).on_closing(destroy=False)
            self.bind_refresh(bind=False)
            self.SaveSettings(destroy=True)
        except:
                deprint(u'An error occurred while trying to save settings:',
                        traceback=True)
        finally:
            self.destroy_component()

    def SaveSettings(self, destroy=False):
        """Save application data."""
        # Purge some memory
        bolt.GPathPurge()
        # Clean out unneeded settings
        self.CleanSettings()
        if Link.Frame.docBrowser: Link.Frame.docBrowser.DoSave()
        settings[u'bash.frameMax'] = self.is_maximized
        settings[u'bash.page'] = self.notebook.GetSelection()
        # use tabInfo below so we save settings of panels that the user closed
        for _k, (_cname, tab_name, panel) in tabInfo.items():
            if panel is None: continue
            try:
                panel.ClosePanel(destroy)
            except:
                deprint(u'An error occurred while saving settings of '
                        u'the %s panel:' % tab_name, traceback=True)
        settings.save()

    @staticmethod
    def CleanSettings():
        """Cleans junk from settings before closing."""
        #--Clean rename dictionary.
        modNames = set(bosh.modInfos)
        modNames.update(bosh.modInfos.table)
        renames = bass.settings[u'bash.mods.renames']
        # Make a copy, we may alter it in the loop
        for old_mname, new_mname in list(renames.items()):
            if new_mname not in modNames:
                del renames[old_mname]
        #--Clean backup
        for fileInfos in (bosh.modInfos,bosh.saveInfos):
            goodRoots = {p.root for p in fileInfos}
            backupDir = fileInfos.bash_dir.join(u'Backups')
            if not backupDir.is_dir(): continue
            for back_fname in backupDir.list():
                back_path = backupDir.join(back_fname)
                if back_fname.root not in goodRoots and back_path.is_file():
                    back_path.remove()

    @staticmethod
    def saveListRefresh(focus_list):
        if BashFrame.saveList:
            BashFrame.saveList.RefreshUI(focus_list=focus_list)

    @staticmethod
    def bsaListRefresh(focus_list):
        if BashFrame.bsaList:
            BashFrame.bsaList.RefreshUI(focus_list=focus_list)

    # Global Menu API
    def set_global_menu(self, new_global_menu):
        """Changes the global menu to the specified one."""
        self.global_menu = new_global_menu
        self.refresh_global_menu_visibility()

    def refresh_global_menu_visibility(self):
        """Hides or shows the global menu, depending on the setting the user
        chose."""
        # Forcibly hide it on Linux because of the possibility that someone is
        # using a system-wide menubar (e.g. Ubuntu). wxWidgets (and hence also
        # wxPython) do not generate open/close events for that style of
        # menubar, which means we can't implement our JIT global menu - it will
        # simply display empty global menus that do nothing when clicked.
        show_gm = bass.settings[u'bash.show_global_menu'] and os_name == u'nt'
        self._native_widget.SetMenuBar(self.global_menu._native_widget
                                       if show_gm else None)

#------------------------------------------------------------------------------
class BashApp(object):
    """Wrapper around a wx Application."""
    __slots__ = ('bash_app',)

    def __init__(self, bash_app):
        self.bash_app = bash_app

    def Init(self): # not OnInit(), we need to initialize _after_ the app has been instantiated
        """Initialize the application data and create the BashFrame."""
        #--OnStartup SplashScreen and/or Progress
        #   Progress gets hidden behind splash by default, since it's not very informative anyway
        splash_screen = None
        with balt.Progress(u'Wrye Bash', _(u'Initializing') + u' ' * 10,
                           elapsed=False) as progress:
            # Is splash enabled in ini ?
            if bass.inisettings[u'EnableSplashScreen']:
                if (splash := bass.dirs['images'].join(
                    'wryesplash.png')).is_file():
                    splash_screen = CenteredSplash(splash.s)
            #--Init Data
            progress(0.2, _(u'Initializing Data'))
            self.InitData(progress)
            progress(0.7, _(u'Initializing Version'))
            self.InitVersion()
            #--MWFrame
            progress(0.8, _(u'Initializing Windows'))
            frame = BashFrame() # Link.Frame global set here
            progress(1.0, _(u'Done'))
        if splash_screen:
            splash_screen.stop_splash()
        self.bash_app.SetTopWindow(frame._native_widget)
        frame.show_frame()
        frame.RefreshData(booting=True)
        frame.is_maximized = settings[u'bash.frameMax']
        # Moved notebook.Bind() callback here as OnShowPage() is explicitly
        # called in RefreshData
        frame.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED,
                            frame.notebook.OnShowPage)
        return frame

    @staticmethod
    def InitData(progress):
        """Initialize all data. Called by Init()."""
        progress(0.2, _(u'Initializing BSAs'))
        #bsaInfos: used in warnTooManyModsBsas() and modInfos strings detection
        bosh.bsaInfos = bosh.BSAInfos()
        bosh.bsaInfos.refresh(booting=True)
        progress(0.3, _(u'Initializing plugins'))
        bosh.modInfos = bosh.ModInfos()
        bosh.modInfos.refresh(booting=True)
        progress(0.5, _(u'Initializing saves'))
        bosh.saveInfos = bosh.SaveInfos()
        bosh.saveInfos.refresh(booting=True)
        progress(0.6, _(u'Initializing INIs'))
        bosh.iniInfos = bosh.INIInfos()
        bosh.iniInfos.refresh(refresh_target=False)
        # screens/installers data are refreshed upon showing the panel
        #--Patch check
        if bush.game.Esp.canBash:
            if not bosh.modInfos.bashed_patches and bass.inisettings[u'EnsurePatchExists']:
                progress(0.68, _(u'Generating Blank Bashed Patch'))
                try:
                    bosh.modInfos.generateNextBashedPatch(selected_mods=())
                except: # YAK but this may blow and has blown on whatever coding error, crashing Bash on boot
                    deprint(u'Failed to create new bashed patch', traceback=True)

    @staticmethod
    def InitVersion():
        """Perform any version to version conversion. Called by Init()."""
        #--Current Version
        if settings[u'bash.version'] != bass.AppVersion:
            settings[u'bash.version'] = bass.AppVersion
            # rescan mergeability on version upgrade to detect new mergeable
            deprint(u'Version changed, rescanning mergeability')
            bosh.modInfos.rescanMergeable(bosh.modInfos, bolt.Progress())
            deprint(u'Done rescanning mergeability')

# Initialization --------------------------------------------------------------
from .gui_patchers import initPatchers
def InitSettings(): # this must run first !
    """Initializes settings dictionary for bosh and basher."""
    bosh.initSettings()
    global settings
    balt._settings = bass.settings
    balt.sizes = bass.settings.get(u'bash.window.sizes', {})
    settings = bass.settings
    settings.loadDefaults(settingDefaults)
    # The colors dictionary only gets copied into settings if it is missing
    # entirely, copy new entries if needed
    for color_key, color_val in settingDefaults[u'bash.colors'].items():
        if color_key not in settings[u'bash.colors']:
            settings[u'bash.colors'][color_key] = color_val
    # Import/Export DLL permissions was broken and stored DLLs with a ':'
    # appended, simply drop those here (worst case some people will have to
    # re-confirm that they want to install a DLL). Note we have to do this here
    # because init_global_skips below bakes them into Installer._{bad,good}Dlls
    for key_suffix in (u'goodDlls', u'badDlls'):
        dict_key = u'bash.installers.' + key_suffix
        bass.settings[dict_key] = {k: v for k, v
                                   in bass.settings[dict_key].items()
                                   if not k.endswith(u':')}
    bosh.bain.Installer.init_global_skips() # must be after loadDefaults - grr #178
    bosh.bain.Installer.init_attributes_process()
    # Plugin encoding used to decode mod string fields
    bolt.pluginEncoding = bass.settings[u'bash.pluginEncoding']
    initPatchers()

def InitImages():
    """Initialize color and image collections."""
    # TODO(inf) backwards compat - remove on settings update
    _conv_dict = {
        b'BLACK': (0,   0,   0),
        b'BLUE':  (0,   0,   255),
        b'NAVY':  (35,  35,  142),
        b'GREY':  (128, 128, 128),
        b'WHITE': (255, 255, 255),
    }
    # Setup the colors dictionary
    for color_key, color_val in settings[u'bash.colors'].items():
        # Convert any colors that were stored as bytestrings into tuples
        if isinstance(color_val, bytes):
            color_val = _conv_dict[color_val]
            settings[u'bash.colors'][color_key] = color_val
        colors[color_key] = color_val
    #--Images
    imgDirJn = bass.dirs[u'images'].join
    def _png(fname): return ImageWrapper(imgDirJn(fname))
    #--Standard
    images[u'save.on'] = _png(u'save_on.png')
    images[u'save.off'] = _png(u'save_off.png')
    # Up/Down arrows for UIList columns
    images[u'arrow.up'] = _png(u'arrow_up.png')
    images[u'arrow.down'] = _png(u'arrow_down.png')
    #--Misc
    images[u'help.16'] = _png(u'help16.png')
    images[u'help.24'] = _png(u'help24.png')
    images[u'help.32'] = _png(u'help32.png')
    #--ColorChecks
    images[u'checkbox.red.x'] = _png(u'checkbox_red_x.png')
    images[u'checkbox.red.x.16'] = _png(u'checkbox_red_x.png')
    images[u'checkbox.red.x.24'] = _png(u'checkbox_red_x_24.png')
    images[u'checkbox.red.x.32'] = _png(u'checkbox_red_x_32.png')
    images[u'checkbox.red.off.16'] = _png(u'checkbox_red_off.png')
    images[u'checkbox.red.off.24'] = _png(u'checkbox_red_off_24.png')
    images[u'checkbox.red.off.32'] = _png(u'checkbox_red_off_32.png')
    images[u'checkbox.green.on.16'] = _png(u'checkbox_green_on.png')
    images[u'checkbox.green.off.16'] = _png(u'checkbox_green_off.png')
    images[u'checkbox.green.on.24'] = _png(u'checkbox_green_on_24.png')
    images[u'checkbox.green.off.24'] = _png(u'checkbox_green_off_24.png')
    images[u'checkbox.green.on.32'] = _png(u'checkbox_green_on_32.png')
    images[u'checkbox.green.off.32'] = _png(u'checkbox_green_off_32.png')
    images[u'checkbox.blue.on.16'] = _png(u'checkbox_blue_on.png')
    images[u'checkbox.blue.on.24'] = _png(u'checkbox_blue_on_24.png')
    images[u'checkbox.blue.on.32'] = _png(u'checkbox_blue_on_32.png')
    images[u'checkbox.blue.off.16'] = _png(u'checkbox_blue_off.png')
    images[u'checkbox.blue.off.24'] = _png(u'checkbox_blue_off_24.png')
    images[u'checkbox.blue.off.32'] = _png(u'checkbox_blue_off_32.png')
    #--DocBrowser
    images[u'doc.16'] = _png(u'docbrowser16.png')
    images[u'doc.24'] = _png(u'docbrowser24.png')
    images[u'doc.32'] = _png(u'docbrowser32.png')
    images[u'settingsbutton.16'] = _png(u'settingsbutton16.png')
    images[u'settingsbutton.24'] = _png(u'settingsbutton24.png')
    images[u'settingsbutton.32'] = _png(u'settingsbutton32.png')
    images[u'modchecker.16'] = _png(u'modchecker16.png')
    images[u'modchecker.24'] = _png(u'modchecker24.png')
    images[u'modchecker.32'] = _png(u'modchecker32.png')
    images[u'pickle.16'] = _png(u'pickle16.png')
    images[u'pickle.24'] = _png(u'pickle24.png')
    images[u'pickle.32'] = _png(u'pickle32.png')

from .links_init import InitLinks
