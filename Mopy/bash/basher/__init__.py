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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
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
from __future__ import annotations

import collections
import os
import sys
import time
from collections import OrderedDict, defaultdict, namedtuple
from collections.abc import Iterable
from functools import partial, reduce
from itertools import chain

import wx

# basher-local imports - maybe work towards dropping (some of) these?
from .constants import colorInfo, settingDefaults
from .dialogs import CreateNewPlugin, CreateNewProject, UpdateNotification, \
    DependentsAffectedDialog, MastersAffectedDialog, MultiWarningDialog, \
    LoadOrderSanitizedDialog
from .frames import DocBrowser
from .gui_patchers import initPatchers
from .. import archives, balt, bass, bolt, bosh, bush, env, initialization, \
    load_order
from ..balt import AppendableLink, CheckLink, DnDStatusBar, EnabledLink, \
    INIListCtrl, InstallerColorChecks, ItemLink, Link, Links, NotebookPanel, \
    Resources, SeparatorLink, colors, images, UIList
from ..bolt import FName, GPath, SubProgress, deprint, dict_sort, \
    forward_compat_path_to_fn, os_name, round_size, str_to_sig, \
    to_unix_newlines, to_win_newlines, top_level_items, LooseVersion
from ..bosh import ModInfo, omods
from ..exception import BoltError, CancelError, FileError, SkipError, \
    UnknownListener
from ..gui import CENTER, BusyCursor, Button, CancelButton, CenteredSplash, \
    CheckListBox, Color, CopyOrMovePopup, DateAndTimeDialog, DropDown, \
    EventResult, FileOpen, GlobalMenu, HLayout, ImageWrapper, Label, \
    LayoutOptions, ListBox, MultiChoicePopup, PanelWin, Picture, \
    PureImageButton, RadioButton, SaveButton, Splitter, Stretch, TabbedPanel, \
    TextArea, TextField, VLayout, WindowFrame, WithMouseEvents, \
    get_shift_down, read_files_from_clipboard_cb, showError, askYes, \
    showWarning, askWarning, showOk
from ..localize import format_date
from ..update_checker import LatestVersion, UCThread

#  - Make sure that python root directory is in PATH, so can access dll's.
_env_path = os.environ['PATH']
if sys.prefix not in _env_path.split(';'):
    os.environ['PATH'] = f'{_env_path};{sys.prefix}'

# Settings --------------------------------------------------------------------
settings: bolt.Settings | None = None

# Links -----------------------------------------------------------------------
#------------------------------------------------------------------------------
class Installers_Link(ItemLink):
    """InstallersData mixin"""
    _dialog_title: str
    window: 'InstallersList'

    @property
    def idata(self):
        """:rtype: bosh.InstallersData"""
        return self._data_store
    @property
    def iPanel(self):
        """:rtype: InstallersPanel"""
        return self.window.panel

    def _askFilename(self, message, filename, inst_type=bosh.InstallerArchive,
                     disallow_overwrite=False, no_dir=True, base_dir=None,
                     allowed_exts=archives.writeExts, use_default_ext=True,
                     check_exists=True, no_file=False):
        """:rtype: bolt.FName"""
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
        fmt_pf = {'package_filename': archive_path}
        if no_dir and base_dir.join(archive_path).is_dir():
            self._showError(_('%(package_filename)s is a directory.') % fmt_pf)
            return
        if no_file and base_dir.join(archive_path).is_file():
            self._showError(_('%(package_filename)s is a file.') % fmt_pf)
            return
        if check_exists and base_dir.join(archive_path).exists():
            if disallow_overwrite:
                self._showError(_('%(package_filename)s already '
                                  'exists.') % fmt_pf)
                return
            msg = _('%(package_filename)s already exists. Overwrite it?'
                    ) % fmt_pf
            if not self._askYes(msg, self._dialog_title, default_is_yes=False):
                return
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
_same_file = object() # None already has special meaning, so use this default
class _DetailsViewMixin(NotebookPanel):
    """Mixin to add detailsPanel attribute to a Panel with a details view.

    Mix it in to SashUIListPanel so UILists can call SetDetails and
    ClearDetails on their panels."""
    detailsPanel = None
    def _setDetails(self, fileName):
        self.detailsPanel.SetFile(fileName=fileName)
    def ClearDetails(self): self._setDetails(None)
    def SetDetails(self, fileName=_same_file): self._setDetails(fileName)

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
    _ui_settings = {'.sashPos': _UIsetting(lambda self: self.defaultSashPos,
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
    _status_str = 'OVERRIDE: %(status_num)d'
    _ui_list_type: type[UIList] = None

    def __init__(self, parent, isVertical=True):
        super(SashUIListPanel, self).__init__(parent, isVertical)
        self.uiList = self._ui_list_type(self.left, listData=self.listData,
                                         keyPrefix=self.keyPrefix, panel=self)

    def SelectUIListItem(self, item, deselectOthers=False):
        self.uiList.SelectAndShowItem(item, deselectOthers=deselectOthers,
                                      focus=True)

    def _sbCount(self): return self.__class__._status_str % {
        'status_num': len(self.listData)}

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
class _ModsUIList(UIList):
    _masters_first_cols = UIList.nonReversibleCols

    @property
    def masters_first(self):
        """Whether or not masters should be sorted before non-masters for the
        current sort column."""
        return (settings.get(f'{self.keyPrefix}.esmsFirst', True) or
                self.masters_first_required)

    @masters_first.setter
    def masters_first(self, val):
        settings[f'{self.keyPrefix}.esmsFirst'] = val

    @property
    def selectedFirst(self):
        return settings.get(f'{self.keyPrefix}.selectedFirst', False)

    @selectedFirst.setter
    def selectedFirst(self, val):
        settings[f'{self.keyPrefix}.selectedFirst'] = val

    def _sort_masters_first(self, items):
        """Conditional sort, performs the actual 'masters-first' sorting if
        needed."""
        if self.masters_first:
            items.sort(key=lambda a: not self.data_store[a].in_master_block())

    def _activeModsFirst(self, items):
        if self.selectedFirst:
            set_active = set(load_order.cached_active_tuple())
            set_merged = set(bosh.modInfos.merged)
            set_imported = set(bosh.modInfos.imported)
            def _sel_sort_key(x):
                # First active, then merged, then imported, then inactive
                if x in set_active: return 0
                elif x in set_merged: return 1
                elif x in set_imported: return 2
                else: return 3
            items.sort(key=_sel_sort_key)

    @property
    def masters_first_required(self):
        """Return True if sorting by master status is required for the current
        sort column."""
        return self.sort_column in self._masters_first_cols

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
            self.data_store[a].curr_name.lower(),
        # Missing mods sort last alphabetically
        u'Current Order': lambda self, a: self._curr_lo_index[
            self.data_store[a].curr_name],
        'Indices': lambda self, a: self._save_lo_real_index[
            self.data_store[a].curr_name],
        'Current Index': lambda self, a: self._curr_real_index[
            self.data_store[a].curr_name],
    }
    def _activeModsFirst(self, items):
        if self.selectedFirst:
            set_active = set(load_order.cached_active_tuple())
            set_merged = set(bosh.modInfos.merged)
            set_imported = set(bosh.modInfos.imported)
            def _sel_sort_key(x):
                # First active, then merged, then imported, then inactive
                x_curr_name = self.data_store[x].curr_name
                if x_curr_name in set_active: return 0
                elif x_curr_name in set_merged: return 1
                elif x_curr_name in set_imported: return 2
                else: return 3
            items.sort(key=_sel_sort_key)
    _extra_sortings = [_ModsUIList._sort_masters_first, _activeModsFirst]
    _sunkenBorder, _singleCell = False, True
    #--Labels
    labels = {
        'File': lambda self, mi: bosh.modInfos.masterWithVersion(
            self.data_store[mi].curr_name),
        'Num': lambda self, mi: f'{mi:02X}',
        'Current Order': lambda self, mi: bosh.modInfos.hexIndexString(
            self.data_store[mi].curr_name),
        'Indices': lambda self, mi: self._save_lo_hex_string[
            self.data_store[mi].curr_name],
        'Current Index': lambda self, mi: bosh.modInfos.real_index_strings[
            self.data_store[mi].curr_name],
    }
    # True if we should highlight masters whose stored size does not match the
    # size of the plugin on disk
    _do_size_checks = False

    @property
    def masters_first(self):
        # Flip the default for masters, we want to show the order in the save
        # so as to not make renamed/disabled masters 'jump around'
        return (settings.get(f'{self.keyPrefix}.esmsFirst', False) or
                self.masters_first_required)

    # We have to override this, otherwise Mods_MastersFirst breaks
    @masters_first.setter
    def masters_first(self, val):
        settings[f'{self.keyPrefix}.esmsFirst'] = val

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
        self._curr_real_index = {}
        # Cache based on SaveHeader.masters_regular and masters_esl
        self._save_lo_real_index = defaultdict(lambda: sys.maxsize)
        self._save_lo_hex_string = defaultdict(lambda: '')
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
                   _('Update Masters') + ' - ' + _('BETA'))):
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
        """Double click - jump to selected plugin on Mods tab."""
        if self.mouse_index is None or self.mouse_index < 0:
            return # Nothing was clicked
        sel_curr_name = self.data_store[self.mouse_index].curr_name
        if sel_curr_name not in bosh.modInfos:
            return # Master that is not installed was clicked
        balt.Link.Frame.notebook.SelectPage(u'Mods', sel_curr_name)
        return EventResult.FINISH

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
        self._update_real_indices(fileInfo)
        self.is_inaccurate = fileInfo.has_inaccurate_masters
        if isinstance(fileInfo, bosh.ModInfo):
            can_have_sizes = bush.game.Esp.check_master_sizes
            can_have_esl = False
        else:
            can_have_sizes = False
            can_have_esl = bush.game.has_esl
        all_esl_masters = (set(fileInfo.header.masters_esl) if can_have_esl
                           else None)
        all_master_sizes = (fileInfo.header.master_sizes if can_have_sizes
                            else None)
        for mi, ma_name in enumerate(fileInfo.masterNames):
            ma_size = all_master_sizes[mi] if can_have_sizes else 0
            ma_esl = can_have_esl and ma_name in all_esl_masters
            self.data_store[mi] = bosh.MasterInfo(ma_name, ma_size, ma_esl)
        self._reList()
        self.populate_items()

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
            mouseText += _('Bashed Patch.') + ' '
            if masterInfo.is_esl(): # ugh, copy-paste from below
                mouseText += _('Light plugin.') + ' '
        elif masters_name in bosh.modInfos.mergeable:
            if u'NoMerge' in fileBashTags and not bush.game.check_esl:
                item_format.text_key = u'mods.text.noMerge'
                mouseText += _('Technically mergeable, but has NoMerge '
                               'tag.') + ' '
            else:
                item_format.text_key = u'mods.text.mergeable'
                if bush.game.check_esl:
                    mouseText += _('Can be ESL-flagged.') + ' '
                else:
                    # Merged plugins won't be in master lists
                    mouseText += _('Can be merged into Bashed Patch.') + ' '
        else:
            # NoMerge / Mergeable should take priority over ESL/ESM color
            final_text_key = u'mods.text.es'
            if masterInfo.is_esl():
                final_text_key += u'l'
                mouseText += _('Light plugin.') + ' '
            if masterInfo.in_master_block():
                final_text_key += u'm'
                mouseText += _('Master plugin.') + ' '
            # Check if it's special, leave ESPs alone
            if final_text_key != u'mods.text.es':
                item_format.text_key = final_text_key
        # Text background
        if masters_name in bosh.modInfos.activeBad: # if active, it's in LO
            item_format.back_key = u'mods.bkgd.doubleTime.load'
            mouseText += _('Plugin name incompatible, will not load.') + ' '
        elif bosh.modInfos.isBadFileName(masters_name): # might not be in LO
            item_format.back_key = u'mods.bkgd.doubleTime.exists'
            mouseText += _('Plugin name incompatible, cannot be '
                           'activated.') + ' '
        elif masterInfo.hasActiveTimeConflict():
            item_format.back_key = u'mods.bkgd.doubleTime.load'
            mouseText += _('Another plugin has the same timestamp.') + ' '
        elif masterInfo.hasTimeConflict():
            item_format.back_key = u'mods.bkgd.doubleTime.exists'
            mouseText += _('Another plugin has the same timestamp.') + ' '
        elif masterInfo.is_ghost:
            item_format.back_key = u'mods.bkgd.ghosted'
            mouseText += _('Plugin is ghosted.') + ' '
        elif self._do_size_checks and bosh.modInfos.size_mismatch(
                masters_name, masterInfo.stored_size):
            item_format.back_key = u'mods.bkgd.size_mismatch'
            mouseText += _('Stored size does not match the one on disk.') + ' '
        if self.allowEdit:
            if masterInfo.old_name in settings[u'bash.mods.renames']:
                item_format.bold = True
        #--Image
        status = self.GetMasterStatus(mi)
        oninc = load_order.cached_is_active(masters_name) or (
            masters_name in bosh.modInfos.merged and 2)
        on_display = self.detailsPanel.displayed_item
        if status == 30: # master is missing
            mouseText += _('Missing master of %(child_plugin_name)s.') % {
                'child_plugin_name': on_display} + ' '
        #--HACK - load order status
        elif on_display in bosh.modInfos:
            if status == 20:
                mouseText += _('Reordered relative to other masters.') + ' '
            lo_index = load_order.cached_lo_index
            if lo_index(on_display) < lo_index(masters_name):
                mouseText += _('Loads after %(child_plugin_name)s.') % {
                    'child_plugin_name': on_display} + ' '
                status = 20 # paint orange
        item_format.icon_key = status, oninc
        self.mouseTexts[mi] = mouseText

    #--Relist
    def _reList(self):
        file_order_names = load_order.get_ordered(
            [v.curr_name for v in self.data_store.values()])
        self._curr_lo_index = {p: i for i, p in enumerate(file_order_names)}
        r_indices = bosh.modInfos.real_indices
        self._curr_real_index = {p: r_indices[p] for p in file_order_names}

    def _update_real_indices(self, new_file_info):
        """Updates the 'real' indices cache. Does nothing outside of saves."""

    #--InitEdit
    def InitEdit(self):
        #--Pre-clean
        edited = False
        for mi, masterInfo in self.data_store.items():
            newName = settings[u'bash.mods.renames'].get(
                masterInfo.curr_name, None)
            #--Rename only if corresponding modInfo is present
            edited |= bool(masterInfo.rename_if_present(newName))
        #--Done
        if edited: self.SetMasterlistEdited(repopulate=True)

    def SetMasterlistEdited(self, repopulate=False):
        self._reList()
        if repopulate: self.populate_items()
        self.edited = True
        self.detailsPanel.SetEdited() # inform the details panel

    #--Column Menu
    def DoColumnMenu(self, evt_col: int, bypass_gm_setting=False):
        if self.fileInfo:
            # Since there is no global menu for master lists, bypass the global
            # menu setting (otherwise the user would never be able to access
            # these links)
            super().DoColumnMenu(evt_col, bypass_gm_setting=True)
        return EventResult.FINISH

    def _handle_left_down(self, wrapped_evt, lb_dex_and_flags):
        if self.allowEdit: self.InitEdit()

    #--Events: Label Editing
    def OnBeginEditLabel(self, evt_label, uilist_ctrl):
        if not self.allowEdit: return EventResult.CANCEL
        # pass event on (for label editing)
        return super(MasterList, self).OnBeginEditLabel(evt_label, uilist_ctrl)

    def _check_rename_requirements(self):
        """Check if the operation is allowed and return ModInfo as the item
        type of the selected label to be renamed."""
        to_rename = self.GetSelected()
        if to_rename:
            return ModInfo, ''
        else:
            # I don't see how this would be possible, but just in case...
            return None, _('No items selected for renaming.')

    def OnLabelEdited(self, is_edit_cancelled, evt_label, evt_index, evt_item):
        #--No change?
        masterInfo = self.data_store[evt_item]
        if masterInfo.rename_if_present(evt_label): # evt_label is the new name
            self.SetMasterlistEdited()
            bass.settings[u'bash.mods.renames'][
                masterInfo.old_name] = masterInfo.curr_name
            # populate, refresh must be called last
            self.PopulateItem(itemDex=evt_index)
            return EventResult.FINISH ##: needed?
        elif evt_label == u'':
            return EventResult.CANCEL
        else:
            showError(self, _('File %(selected_file)s does not exist.') % {
                'selected_file': evt_label})
            return EventResult.CANCEL

    #--GetMasters
    def GetNewMasters(self):
        """Returns new master list."""
        return [v.curr_name for k, v in dict_sort(self.data_store)]

#------------------------------------------------------------------------------
class INIList(UIList):
    column_links = Links()  #--Column menu
    context_links = Links()  #--Single item menu
    global_links = defaultdict(lambda: Links()) # Global menu
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
    labels = {
        'File': lambda self, p: p,
        'Installer': lambda self, p: self.data_store[p].get_table_prop(
            'installer', ''),
    }
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
        tweaklist = _('Active INI Tweaks:') + '\n'
        tweaklist += u'[spoiler]\n'
        for tweak, info in dict_sort(self.data_store):
            if not info.tweak_status() == 20: continue
            tweaklist+= f'{tweak}\n'
        tweaklist += u'[/spoiler]\n'
        return tweaklist

    def set_item_format(self, ini_name, item_format, target_ini_setts):
        iniInfo = self.data_store[ini_name]
        status = iniInfo.tweak_status(target_ini_setts)
        #--Image
        checkMark = 0
        icon = 0    # Ok tweak, not applied
        mousetext = ''
        if status == 20:
            # Valid tweak, applied
            checkMark = 1
            mousetext = _('Tweak is currently applied.')
        elif status == 15:
            # Valid tweak, some settings applied, others are
            # overwritten by values in another tweak from same installer
            checkMark = 3
            mousetext = _('Some settings are applied. Some are overwritten '
                          'by another tweak from the same installer.')
        elif status == 10:
            # Ok tweak, some parts are applied, others not
            icon = 10
            checkMark = 3
            mousetext = _('Some settings are changed.')
        elif status < 0:
            # Bad tweak
            if not iniInfo.is_applicable(status):
                icon = 20
                mousetext = _('Tweak is invalid.')
            else:
                icon = 0
                mousetext = _('Tweak adds new settings.')
        if iniInfo.is_default_tweak:
            def_tweak_text = _('Default Wrye Bash tweak.')
            mousetext = (def_tweak_text + f' {mousetext}'
                         if mousetext else def_tweak_text)
            item_format.italics = True
        self.mouseTexts[ini_name] = mousetext
        item_format.icon_key = icon, checkMark
        #--Font/BG Color
        if status < 0:
            item_format.back_key = u'ini.bkgd.invalid'

    # Events ------------------------------------------------------------------
    def _handle_left_down(self, wrapped_evt, lb_dex_and_flags):
        tweak_clicked_on_icon = self._get_info_clicked(lb_dex_and_flags,
                                                       on_icon=True)
        if tweak_clicked_on_icon:
            # Left click on icon - Activate tweak
            if self.apply_tweaks([tweak_clicked_on_icon]):
                self.panel.ShowPanel()
            return EventResult.FINISH
        else:
            tweak_clicked = self._getItemClicked(lb_dex_and_flags)
            if wrapped_evt.is_alt_down and tweak_clicked:
                # Alt+Left click - jump to source
                if self.jump_to_source(tweak_clicked):
                    return EventResult.FINISH

    def OnDClick(self, lb_dex_and_flags):
        """Double click - open selected tweak."""
        tweak_clicked = self._get_info_clicked(lb_dex_and_flags)
        if tweak_clicked and not tweak_clicked.is_default_tweak:
            self.OpenSelected(selected=[tweak_clicked.fn_key])
        return EventResult.FINISH

    def _handle_key_down(self, wrapped_evt):
        kcode = wrapped_evt.key_code
        if kcode in balt.wxReturn:
            # Enter - open selected tweaks
            self.OpenSelected(
                self.data_store.filter_essential(self.GetSelected()))
        else:
            return super()._handle_key_down(wrapped_evt)
        # Otherwise we'd jump to a random tweak that starts with the key code
        return EventResult.FINISH

    # INI-specific methods ----------------------------------------------------
    @classmethod
    def apply_tweaks(cls, tweak_infos, target_ini=None):
        tweak_infos_list = list(tweak_infos) # may be a generator
        target_ini_file = target_ini or bosh.iniInfos.ini
        if not cls.ask_create_target_ini(target_ini_file):
            return False
        # Default tweaks are tested, so no need to warn about trust and
        # crashes, etc.
        tweaks_are_trusted = all(t.is_default_tweak for t in tweak_infos_list)
        if (not tweaks_are_trusted and
                not cls._warn_tweak_game_ini(target_ini_file.abs_path.stail)):
            return False
        needsRefresh = False
        for ini_info in tweak_infos_list:
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
            if not askYes(None, msg, _('Missing game Ini')):
                return False
        else:
            msg += _(u'Please create it manually to continue.')
            showError(None, msg, _('Missing game Ini'))
            return False
        try:
            default_ini.copyTo(target_ini_file.abs_path)
            if balt.Link.Frame.iniList:
                balt.Link.Frame.iniList.panel.ShowPanel()
            else:
                bosh.iniInfos.refresh(refresh_infos=False)
            return True
        except OSError:
            target_ini_pth = target_ini_file.abs_path
            deprint(f'Failed to copy {default_ini} to {target_ini_pth}',
                traceback=True)
            msg = _('Failed to copy %(def_ini_path)s to %(target_ini_pth)s.'
                    ) % {'def_ini_path': default_ini,
                         'target_ini_pth': target_ini_pth}
            showError(None, msg, title=_('Missing Game INI'))
        return False

    @staticmethod
    @balt.conversation
    def _warn_tweak_game_ini(chosen):
        ask = True
        if chosen in bush.game.Ini.dropdown_inis:
            ask = balt.askContinue(balt.Link.Frame,
                _('Apply an INI tweak to %(curr_target_ini)s? Make sure you '
                  'trust the tweak, as incorrect tweaks can cause '
                  'crashes.') % {'curr_target_ini': chosen},
                'bash.iniTweaks.continue', title=_('INI Tweaks'))
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
        try:
            self._RefreshTweakLineCtrl(tweakPath)
        finally:
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
        try:
            self._RefreshIniContents()
        finally:
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
    _extra_sortings = [_ModsUIList._sort_masters_first,
                       _ModsUIList._activeModsFirst]
    _dndList, _dndColumns = True, [u'Load Order']
    _sunkenBorder = False
    #--Labels
    labels = {
        'File': lambda self, p: self.data_store.masterWithVersion(p),
        'Load Order': lambda self, p: self.data_store.hexIndexString(p),
        'Indices': lambda self, p: self.data_store[p].real_index_string(),
        'Rating': lambda self, p: self.data_store[p].get_table_prop('rating',
                                                                    ''),
        'Group': lambda self, p: self.data_store[p].get_table_prop('group',
                                                                   ''),
        'Installer': lambda self, p: self.data_store[p].get_table_prop(
            'installer', ''),
        'Modified': lambda self, p: format_date(self.data_store[p].mtime),
        'Size': lambda self, p: round_size(self.data_store[p].fsize),
        'Author': lambda self, p: self.data_store[p].header.author if
        self.data_store[p].header else '-',
        'CRC': lambda self, p: self.data_store[p].crc_string(),
        'Mod Status': lambda self, p: self.data_store[p].txt_status(),
    }
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
            balt.askContinue(self, msg, continue_key, show_cancel=False)
            return super(ModList, self).dndAllow(event) # disallow
        return True

    @balt.conversation
    def _refreshOnDrop(self, first_index):
        #--Save and Refresh
        try:
            bosh.modInfos.cached_lo_save_all()
        except (BoltError, NotImplementedError) as e:
            showError(self, f'{e}')
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
            mouseText += _('Plugin name incompatible, will not load.') + ' '
        if mod_name in bosh.modInfos.bad_names:
            mouseText += _('Plugin name incompatible, cannot be '
                           'activated.') + ' '
        if mod_name in bosh.modInfos.missing_strings:
            mouseText += _('Plugin is missing string localization '
                           'files.') + ' '
        if mod_name in bosh.modInfos.bashed_patches:
            item_format.text_key = u'mods.text.bashedPatch'
            mouseText += _('Bashed Patch.') + ' '
            if mod_info.is_esl(): # ugh, copy-paste from below
                mouseText += _('Light plugin.') + ' '
        elif mod_name in bosh.modInfos.mergeable:
            if u'NoMerge' in fileBashTags and not bush.game.check_esl:
                item_format.text_key = u'mods.text.noMerge'
                mouseText += _('Technically mergeable, but has NoMerge '
                               'tag.') + ' '
            else:
                item_format.text_key = u'mods.text.mergeable'
                if bush.game.check_esl:
                    mouseText += _('Can be ESL-flagged.') + ' '
                else:
                    if checkMark == 2:
                        mouseText += _('Merged into Bashed Patch.') + ' '
                    else:
                        mouseText += _('Can be merged into Bashed '
                                       'Patch.') + ' '
        else:
            # NoMerge / Mergeable should take priority over ESL/ESM color
            final_text_key = u'mods.text.es'
            if mod_info.is_esl():
                final_text_key += u'l'
                mouseText += _('Light plugin.') + ' '
            if mod_info.in_master_block():
                final_text_key += u'm'
                mouseText += _('Master plugin.') + ' '
            # Check if it's special, leave ESPs alone
            if final_text_key != u'mods.text.es':
                item_format.text_key = final_text_key
        # Mirror the checkbox color info in the status bar
        if status == 30:
            mouseText += _('One or more masters are missing.') + ' '
        else:
            if status in {20, 21}:
                mouseText += _('Loads before its masters.') + ' '
            if status in {10, 21}:
                mouseText += _('Masters have been re-ordered.') + ' '
        if checkMark == 1:
            mouseText += _('Active in load order.') + ' '
        elif checkMark == 3:
            mouseText += _('Imported into Bashed Patch.') + ' '
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
            mouseText += _('Has master names that will not load.') + ' '
        elif mod_info.hasActiveTimeConflict():
            item_format.back_key = u'mods.bkgd.doubleTime.load'
            mouseText += _('Another plugin has the same timestamp.') + ' '
        elif mod_info.hasTimeConflict():
            item_format.back_key = u'mods.bkgd.doubleTime.exists'
            mouseText += _('Another plugin has the same timestamp.') + ' '
        elif mod_info.isGhost:
            item_format.back_key = u'mods.bkgd.ghosted'
            mouseText += _('Plugin is ghosted.') + ' '
        elif (bush.game.Esp.check_master_sizes
              and mod_info.has_master_size_mismatch()):
            item_format.back_key = u'mods.bkgd.size_mismatch'
            mouseText += _('Has size-mismatched masters.') + ' '
        if settings[u'bash.mods.scanDirty']:
            # Don't mark vanilla files as dirty if the ignore setting is active
            if (not settings['bash.mods.ignore_dirty_vanilla_files'] or
                    mod_name not in bush.game.bethDataFiles):
                message = mod_info.getDirtyMessage()
                mouseText += message[1]
                if message[0]: item_format.underline = True
        self.mouseTexts[mod_name] = mouseText

    def RefreshUI(self, **kwargs):
        """Refresh UI for modList - always specify refreshSaves explicitly."""
        super(ModList, self).RefreshUI(**kwargs)
        if kwargs.pop(u'refreshSaves', False):
            Link.Frame.saveListRefresh(focus_list=False)

    # Events ------------------------------------------------------------------
    def OnDClick(self, lb_dex_and_flags):
        """Double click - open selected plugin in Doc Browser."""
        modInfo = self._get_info_clicked(lb_dex_and_flags)
        if not modInfo: return
        if not Link.Frame.docBrowser:
            DocBrowser().show_frame()
        Link.Frame.docBrowser.SetMod(modInfo.fn_key) ##: will GPath it
        Link.Frame.docBrowser.raise_frame()

    def _handle_key_down(self, wrapped_evt):
        kcode = wrapped_evt.key_code
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
        elif wrapped_evt.is_cmd_down and kcode in balt.wxArrows:
            # Ctrl+Up/Ctrl+Down - move plugin up/down load order
            if not self.dndAllow(event=None): return
            # Calculate continuous chunks of indexes
            chunk, chunks, indexes = 0, [[]], self._get_selected()
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
        elif wrapped_evt.is_cmd_down and kcode == ord('Z'):
            if wrapped_evt.is_shift_down:
                # Ctrl+Shift+Z - redo last load order or active plugins change
                self.lo_redo()
            else:
                # Ctrl+Z - undo last load order or active plugins change
                self.lo_undo()
        elif wrapped_evt.is_cmd_down and kcode == ord('Y'):
            # Ctrl+Y - redo last load order or active plugins change
            self.lo_redo()
        else:
            return super()._handle_key_down(wrapped_evt)
        # Otherwise we'd jump to a random plugin that starts with the key code
        return EventResult.FINISH

    def _handle_key_up(self, wrapped_evt):
        """Char event: Activate selected items, select all items"""
        # Space - enable/disable selected plugins
        if wrapped_evt.is_cmd_down and wrapped_evt.key_code == ord('N'):
            if not bush.game.Esp.canBash: return # We can't write plugins
            if wrapped_evt.is_shift_down:
                # Ctrl+Shift+N - Create a new Bashed Patch
                self.new_bashed_patch()
            else:
                # Ctrl+N - Create a new plugin
                CreateNewPlugin.display_dialog(self)
        else:
            return super()._handle_key_up(wrapped_evt)
        return EventResult.FINISH

    def _handle_left_down(self, wrapped_evt, lb_dex_and_flags):
        mod_clicked_on_icon = self._getItemClicked(lb_dex_and_flags,
                                                   on_icon=True)
        if mod_clicked_on_icon:
            # Left click on icon - (de)activate plugin
            self._toggle_active_state(mod_clicked_on_icon)
            # _handle_select no longer seems to fire for the wrong index, but
            # deselecting the others is still the better behavior here
            self.SelectAndShowItem(mod_clicked_on_icon, deselectOthers=True,
                                   focus=True)
            return EventResult.FINISH
        else:
            mod_clicked = self._getItemClicked(lb_dex_and_flags)
            if wrapped_evt.is_alt_down and mod_clicked:
                # Alt+Left click - jump to source
                if self.jump_to_source(mod_clicked):
                    return EventResult.FINISH
            # Pass Event onward to _handle_select

    def _select(self, modName):
        super(ModList, self)._select(modName)
        if Link.Frame.docBrowser:
            Link.Frame.docBrowser.SetMod(modName)

    @staticmethod
    def _unhide_wildcard():
        return bosh.modInfos.plugin_wildcard()

    # Helpers -----------------------------------------------------------------
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
                deactivated = self.data_store.lo_deactivate(act, doSave=False)
                if not deactivated:
                    # Can't deactivate that mod, track this
                    illegal_deactivations.append(act)
                    continue
                touched |= deactivated
                if len(deactivated) > (act in deactivated):
                    # deactivated dependents
                    deactivated = [x for x in deactivated if x != act]
                    changes[self._deactivated_key][act] = \
                        load_order.get_ordered(deactivated)
            except (BoltError, NotImplementedError) as e:
                showError(self, f'{e}')
        # Activate ?
        # Track illegal activations for the return value
        illegal_activations = []
        for inact in inactive:
            if inact in touched: continue # already activated
            ## For now, allow selecting unicode named files, for testing
            ## I'll leave the warning in place, but maybe we can get the
            ## game to load these files
            #if fileName in self.data_store.bad_names: return
            try:
                activated = self.data_store.lo_activate(inact, doSave=False)
                if not activated:
                    # Can't activate that mod, track this
                    illegal_activations.append(inact)
                    continue
                touched |= set(activated)
                if len(activated) > (inact in activated): # activated masters
                    activated = [x for x in activated if x != inact]
                    changes[self._activated_key][inact] = activated
            except (BoltError, NotImplementedError) as e:
                showError(self, f'{e}')
                break
        # Show warnings to the user if they attempted to deactivate mods that
        # can't be deactivated (e.g. vanilla masters on newer games) and/or
        # attempted to activate mods that can't be activated (e.g. .esu
        # plugins).
        warn_msg = warn_cont_key = ''
        if illegal_deactivations:
            warn_msg = (_("You can't deactivate the following mods:") +
                        f"\n{', '.join(illegal_deactivations)}")
            warn_cont_key = 'bash.mods.dnd.illegal_deactivation.continue'
        if illegal_activations:
            warn_msg = (_("You can't activate the following mods:") +
                        f"\n{', '.join(illegal_activations)}")
            warn_cont_key = 'bash.mods.dnd.illegal_activation.continue'
        if warn_msg:
            balt.askContinue(self, warn_msg, warn_cont_key, show_cancel=False)
        if touched:
            bosh.modInfos.cached_lo_save_active()
            self.__toggle_active_msg(changes)
            self.RefreshUI(redraw=self._lo_redraw_targets(touched),
                           refreshSaves=True)

    _activated_key = 0
    _deactivated_key = 1
    def __toggle_active_msg(self, changes_dict):
        masters_activated = self.decorate_tree_dict(
            changes_dict[self._activated_key])
        dependents_deactivated = self.decorate_tree_dict(
            changes_dict[self._deactivated_key])
        # If we have no changes, abort - if we do have changes, only one of
        # these can be truthy at a time
        if not masters_activated and not dependents_deactivated:
            return
        if masters_activated:
            target_dlg = MastersAffectedDialog
            target_tree_dict = masters_activated
        else:
            target_dlg = DependentsAffectedDialog
            target_tree_dict = dependents_deactivated
        target_dlg(self, mods_list_images=self._icons,
            decorated_plugins=target_tree_dict).show_modeless()

    # Undo/Redo ---------------------------------------------------------------
    def _undo_redo_op(self, undo_or_redo):
        """Helper for load order undo/redo operations. Handles UI refreshes."""
        # Grab copies of the old LO/actives for find_first_difference
        prev_lo = load_order.cached_lo_tuple()
        prev_acti = load_order.cached_active_tuple()
        if not undo_or_redo():
            return # Nothing to do
        curr_lo = load_order.cached_lo_tuple()
        curr_acti = load_order.cached_active_tuple()
        low_diff = load_order.find_first_difference(
            prev_lo, prev_acti, curr_lo, curr_acti)
        if low_diff is None:
            return # Load orders were identical
        # Finally, we pass to _lo_redraw_targets to take all other relevant
        # details into account
        self.RefreshUI(redraw=self._lo_redraw_targets({curr_lo[low_diff]}),
                       refreshSaves=True)

    def lo_undo(self):
        """Undoes a load order change."""
        self._undo_redo_op(self.data_store.undo_load_order)

    def lo_redo(self):
        """Redoes a load order change."""
        self._undo_redo_op(self.data_store.redo_load_order)

    # Other -------------------------------------------------------------------
    def new_bashed_patch(self):
        """Create a new Bashed Patch and refresh the GUI for it."""
        new_patch_name = bosh.modInfos.generateNextBashedPatch(
            self.GetSelected())
        if new_patch_name is not None:
            self.ClearSelected(clear_details=True)
            self.RefreshUI(redraw=[new_patch_name], refreshSaves=False)
        else:
            showWarning(self, _('Unable to create new Bashed Patch: 10 Bashed '
                                'Patches already exist!'))

#------------------------------------------------------------------------------
class _DetailsMixin(object):
    """Mixin for panels that display detailed info on mods, saves etc."""

    @property
    def file_info(self): return self.file_infos.get(self.displayed_item, None)
    @property
    def displayed_item(self): raise NotImplementedError
    @property
    def file_infos(self): raise NotImplementedError

    def _resetDetails(self): raise NotImplementedError

    # Details panel API
    def SetFile(self, fileName=_same_file):
        """Set file to be viewed. Leave fileName empty to reset.
        :type fileName: str | FName | None"""
        #--Reset?
        if fileName is _same_file:
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
    def SetFile(self, fileName=_same_file):
        #--Edit State
        self.edited = False
        self._save_btn.enabled = False
        self._cancel_btn.enabled = False
        return super(_EditableMixin, self).SetFile(fileName)

    # Abstract edit methods
    @property
    def allowDetailsEdit(self): raise NotImplementedError

    def SetEdited(self):
        if not self.displayed_item: return
        self.edited = True
        if self.allowDetailsEdit:
            self._save_btn.enabled = True
        self._cancel_btn.enabled = True

    def DoSave(self): raise NotImplementedError

    def DoCancel(self): self.SetFile()

class _EditableMixinOnFileInfos(_EditableMixin):
    """Bsa/Mods/Saves details, DEPRECATED: we need common data infos API!"""
    _max_filename_chars = 256
    _min_controls_width = 128
    @property
    def file_info(self): raise NotImplementedError
    @property
    def displayed_item(self):
        return self.file_info.fn_key if self.file_info else None

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
            showError(self, name_path) # it's an error message in this case
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
        try: # use self.file_info.fn_key, as name may have been updated
            # Although we could avoid rereading the header I leave it here as
            # an extra error check - error handling is WIP
            self.panel_uilist.data_store.new_info(self.file_info.fn_key,
                                                  notify_bain=True)
            return self.file_info.fn_key
        except FileError as e:
            deprint(f'Failed to edit details for {self.displayed_item}',
                    traceback=True)
            showError(self, _('File corrupted on save!') + f'\n{e.message}')
            return None

class _SashDetailsPanel(_DetailsMixin, SashPanel):
    """Details panel with two splitters"""
    _ui_settings = {**SashPanel._ui_settings,
        '.subSplitterSashPos': _UIsetting(lambda self: 0,
        lambda self: self.subSplitter.get_sash_pos(),
        lambda self, sashPos: self.subSplitter.set_sash_pos(sashPos))
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

    def testChanges(self): raise NotImplementedError

class _ModMasterList(MasterList):
    """Override to avoid doing size checks on save master lists."""
    _do_size_checks = bush.game.Esp.check_master_sizes
    banned_columns = {'Indices', 'Current Index'} # These are Saves-specific

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
        #--Version
        self.version = Label(top, u'v0.00')
        #--Author
        self._max_author_len = bush.game.Esp.max_author_length
        # Note: max_length here is not enough - unicode characters may take up
        # >1 byte, so we show a warning via label and truncate when writing
        self.gAuthor = TextField(top, max_length=self._max_author_len)
        self.gAuthor.on_text_changed.subscribe(self._on_author_typed)
        self.gAuthor.on_focus_lost.subscribe(self._on_author_finished)
        self._author_label = Label(top, '')
        self._set_author_label('')
        #--Modified
        self.modified_txt = TextField(top, max_length=32)
        self.modified_txt.on_text_changed.subscribe(self._on_modified_typed)
        self.modified_txt.on_focus_lost.subscribe(self._on_modified_finished)
        calendar_button = PureImageButton(top,
            balt.images['calendar.16'].get_bitmap(),
            btn_tooltip=_('Change this value using an interactive dialog.'))
        calendar_button.on_clicked.subscribe(self._on_calendar_clicked)
        #--Description
        self._max_desc_len = bush.game.Esp.max_desc_length
        # Same note about max_length applies here too
        self._desc_area = TextArea(top, max_length=self._max_desc_len,
            auto_tooltip=False)
        self._desc_area.on_text_changed.subscribe(self._on_desc_typed)
        self._desc_area.on_focus_lost.subscribe(self._on_desc_finished)
        self._desc_label = Label(top, '')
        self._set_desc_label('')
        #--Bash tags
        ##: Come up with a better solution for this
        class _ExPureImageButton(WithMouseEvents, PureImageButton):
            bind_lclick_down = True
        self._add_tag_btn = _ExPureImageButton(self._bottom_low_panel,
            balt.images['plus.16'].get_bitmap(),
            btn_tooltip=_('Add bash tags to this plugin.'))
        self._add_tag_btn.on_mouse_left_down.subscribe(self._popup_add_tags)
        self._rem_tag_btn = PureImageButton(self._bottom_low_panel,
            balt.images['minus.16'].get_bitmap(),
            btn_tooltip=_('Remove the selected tags from this plugin.'))
        self._rem_tag_btn.on_clicked.subscribe(self._remove_selected_tags)
        self.gTags = ListBox(self._bottom_low_panel, isSort=True,
                             isSingle=False, isExtended=True)
        self.gTags.on_mouse_right_up.subscribe(self._popup_misc_tags)
        #--Layout
        VLayout(spacing=4, item_expand=True, items=[
            HLayout(items=[Label(top, _(u'File:')), Stretch(), self.version]),
            self._fname_ctrl,
            self._author_label,
            self.gAuthor,
            Label(top, _(u'Modified:')),
            HLayout(item_expand=True, items=[
                (self.modified_txt, LayoutOptions(weight=1)),
                calendar_button,
            ]),
            self._desc_label,
            (self._desc_area, LayoutOptions(weight=1))
        ]).apply_to(top)
        VLayout(spacing=4, item_expand=True, items=[
            HLayout(item_expand=True, items=[
                (Label(self._bottom_low_panel, _(u'Bash Tags:')),
                 LayoutOptions(expand=False, v_align=CENTER)),
                Stretch(), self._add_tag_btn, self._rem_tag_btn,
            ]),
            (self.gTags, LayoutOptions(expand=True, weight=1))
        ]).apply_to(self._bottom_low_panel)
        # If the game has no tags, then there is no point in enabling the Bash
        # Tags field
        self._bottom_low_panel.enabled = bool(bush.game.allTags)

    def _get_sub_splitter(self):
        return Splitter(self.right, min_pane_size=128)

    def _resetDetails(self):
        self.modInfo = None
        self.fileStr = u''
        self.authorStr = u''
        self.modifiedStr = u''
        self.descriptionStr = u''
        self.versionStr = u'v0.00'

    def SetFile(self, fileName=_same_file):
        fileName = super(ModDetails, self).SetFile(fileName)
        if fileName:
            modInfo = self.modInfo = bosh.modInfos[fileName]
            #--Remember values for edit checks
            self.fileStr = modInfo.fn_key
            self.authorStr = modInfo.header.author
            self.modifiedStr = format_date(modInfo.mtime)
            self.descriptionStr = modInfo.header.description
            self.versionStr = f'v{modInfo.header.version:0.2f}'
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

    def _set_author_label(self, new_author_str):
        """Helper method for setting the right count etc. in the Author
        label."""
        curr_author_len = len(bolt.encode(new_author_str)) # auto-encoding
        self._author_label.label_text = _(
            'Author - [%(curr_bytes)d/%(max_bytes)d bytes]:') % {
            'curr_bytes': curr_author_len, 'max_bytes': self._max_author_len}
        if curr_author_len > self._max_author_len:
            self._author_label.set_foreground_color(colors['default.warn'])
        else:
            self._author_label.reset_foreground_color()

    def _set_desc_label(self, new_desc_str):
        """Helper method for setting the right count etc. in the Description
        label."""
        curr_desc_len = len(bolt.encode(new_desc_str)) # auto-encoding
        self._desc_label.label_text = _(
            'Description - [%(curr_bytes)d/%(max_bytes)d bytes]:') % {
            'curr_bytes': curr_desc_len, 'max_bytes': self._max_desc_len}
        if curr_desc_len > self._max_desc_len:
            self._desc_label.set_foreground_color(colors['default.warn'])
        else:
            self._desc_label.reset_foreground_color()

    def _on_text_typed(self, old_text, new_text):
        if not self.modInfo: return
        if not self.edited and old_text != new_text: self.SetEdited()

    def _on_author_typed(self, new_text):
        self._on_text_typed(self.authorStr, new_text)
        self._set_author_label(new_text)

    def _on_modified_typed(self, new_text):
        self._on_text_typed(self.modifiedStr, new_text)

    def _on_desc_typed(self, new_text):
        self._on_text_typed(self.descriptionStr, to_unix_newlines(new_text))
        # Use Windows newlines here since those are what we'll actually be
        # writing out
        self._set_desc_label(to_win_newlines(new_text))

    def _on_author_finished(self):
        if not self.modInfo: return
        authorStr = self.gAuthor.text_content
        if authorStr != self.authorStr:
            self.authorStr = authorStr
            self.SetEdited()

    def _apply_modified_timestamp(self, fmt_timestamp):
        """Shared code for _on_modified_finished and _on_calendar_clicked."""
        self.modifiedStr = fmt_timestamp
        self.modified_txt.text_content = fmt_timestamp
        self.SetEdited()

    def _on_modified_finished(self):
        if not self.modInfo: return
        modifiedStr = self.modified_txt.text_content
        if modifiedStr == self.modifiedStr: return
        try:
            newTimeTup = time.strptime(modifiedStr)
            time.mktime(newTimeTup)
        except ValueError:
            showError(self, _(
                'Invalid date "%(unrecognized_date)s", formatting is likely '
                'incorrect.') % {'unrecognized_date': modifiedStr})
            self.modified_txt.text_content = self.modifiedStr
            return
        self._apply_modified_timestamp(time.strftime('%c', newTimeTup))

    def _on_desc_finished(self):
        if not self.modInfo: return
        new_desc = to_unix_newlines(self._desc_area.text_content)
        if new_desc != self.descriptionStr:
            self.descriptionStr = new_desc
            self.SetEdited()

    def _on_calendar_clicked(self):
        """Internal callback that handles showing the date and time dialog and
        processing its result."""
        user_ok, user_datetime = DateAndTimeDialog.display_dialog(
            self, warning_color=balt.colors['default.warn'],
            icon_bundle=balt.Resources.bashBlue)
        if user_ok and user_datetime:
            self._apply_modified_timestamp(user_datetime.strftime('%c'))

    _bsa_and_blocking_msg = _(
        'This plugin has an associated BSA (%(assoc_bsa_name)s) and an '
        'associated plugin-name-specific directory (e.g. %(pnd_example)s), '
        'which will become detached when the plugin is renamed.') + '\n\n' + _(
        'Note that the BSA may also contain a plugin-name-specific directory, '
        'which would remain detached even if the archive name were adjusted.')
    _bsa_msg = _(
        'This plugin has an associated BSA (%(assoc_bsa_name)s), which will '
        'become detached when the plugin is renamed.') + '\n\n' + _(
        'Note that the BSA may contain a plugin-name-specific directory '
        '(e.g. %(pnd_example)s), which would remain detached even '
        'if the archive file name were adjusted.')
    _blocking_msg = _(
        'This plugin has an associated plugin-name-specific directory (e.g. '
        '%(pnd_example)s), which will become detached when the plugin is '
        'renamed.')

    def testChanges(self): # used by the master list when editing is disabled
        modInfo = self.modInfo
        if not modInfo or (self.fileStr == modInfo.fn_key and
                           self.modifiedStr == format_date(modInfo.mtime) and
                           self.authorStr == modInfo.header.author and
                           self.descriptionStr == modInfo.header.description):
            self.DoCancel()

    __bad_name_msg = _('File name %(bad_file_name)s cannot be encoded to '
        'Windows-1252. %(game_name)s may not be able to activate this '
        'plugin because of this. Do you want to rename the plugin anyway?')
    @balt.conversation
    def DoSave(self):
        modInfo = self.modInfo
        #--Change Tests
        file_str = FName(self.fileStr.strip())
        changeName = file_str != modInfo.fn_key
        changeDate = (self.modifiedStr != format_date(modInfo.mtime))
        changeHedr = (self.authorStr != modInfo.header.author or
                      self.descriptionStr != modInfo.header.description)
        changeMasters = self.uilist.edited
        #--Warn on rename if file has BSA and/or dialog
        if changeName:
            msg = modInfo.ask_resources_ok(
                bsa_and_blocking_msg=self._bsa_and_blocking_msg,
                bsa_msg=self._bsa_msg, blocking_msg=self._blocking_msg)
            if msg and not askWarning(
                    self, msg, title=_('Rename %(target_file_name)s') % {
                        'target_file_name': modInfo}): return
        #--Only change date?
        if changeDate and not (changeName or changeHedr or changeMasters):
            self._set_date(modInfo)
            with load_order.Unlock():
                bosh.modInfos.refresh(refresh_infos=False, _modTimesChange=True)
            BashFrame.modList.RefreshUI( # refresh saves if lo changed
                refreshSaves=not bush.game.using_txt_file)
            return
        #--Backup
        modInfo.makeBackup()
        #--Change Name?
        if changeName:
            oldName,newName = modInfo.fn_key, file_str
            #--Bad name?
            if bosh.modInfos.isBadFileName(str(newName)):
                msg = self.__bad_name_msg % {'bad_file_name': newName,
                    'game_name': bush.game.displayName}
                if not balt.askContinue(self, msg,
                                        'bash.rename.isBadFileName.continue'):
                    return ##: cancels all other changes - move to validate_filename (without the balt part)
            settings[u'bash.mods.renames'][oldName] = newName
            changeName = self.panel_uilist.try_rename(modInfo, newName)
        #--Change hedr/masters?
        if changeHedr or changeMasters:
            modInfo.header.author = self.authorStr.strip()
            modInfo.header.description = self.descriptionStr.strip()
            old_mi_masters = modInfo.header.masters
            modInfo.header.masters = self.uilist.GetNewMasters()
            modInfo.header.setChanged()
            modInfo.writeHeader(old_mi_masters)
        #--Change date?
        if changeDate:
            self._set_date(modInfo) # crc recalculated in writeHeader if needed
        if changeDate or changeHedr or changeMasters:
            # we reread header to make sure was written correctly
            detail_item = self._refresh_detail_info()
        else: detail_item = self.file_info.fn_key
        #--Done
        with load_order.Unlock():
            bosh.modInfos.refresh(refresh_infos=False, _modTimesChange=changeDate)
        refreshSaves = detail_item is None or changeName or (
            changeDate and not bush.game.using_txt_file)
        self.panel_uilist.RefreshUI(refreshSaves=refreshSaves,
                                    detail_item=detail_item)

    def _set_date(self, modInfo):
        modInfo.setmtime(time.mktime(time.strptime(self.modifiedStr)))

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
            help_text=_('Check a tag to add it to the plugin.'),
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
        tag_plugin_name = mod_info.fn_key
        # We need to grab both the ones from the description and from LOOT,
        # since we need to save a diff in case of Copy to BashTags
        added_tags, deleted_tags = bosh.read_loot_tags(tag_plugin_name)
        # Emulate the effects of applying the LOOT tags
        old_tags = bashTagsDesc.copy()
        old_tags |= added_tags
        old_tags -= deleted_tags
        dir_diff = bosh.mods_metadata.diff_tags(mod_tags, old_tags)
        class Tags_CopyToBashTags(EnabledLink):
            _text = _('Copy to BashTags')
            _help = _('Copies a diff between currently applied tags and '
                      'description/LOOT tags to %(bashtags_path)s.') % {
                'bashtags_path': bass.dirs['tag_files'].join(
                    f'{mod_info.fn_key.fn_body}.txt')}
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
                    showError(Link.Frame, _(
                        'Description field including the Bash Tags must be at '
                        'most 511 characters. Edit the description to leave '
                        'enough room.'))
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
        return list(self.target_inis.values())[settings['bash.ini.choice']]

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

    def SetFile(self, fileName=_same_file):
        fileName = super(INIDetailsPanel, self).SetFile(fileName)
        self._ini_detail = fileName
        self.tweakContents.refresh_tweak_contents(fileName)
        self.tweakName.text_content = fileName.fn_body if fileName else u''

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
        for ini_fname, ini_path in list(self.target_inis.items()):
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
            wildcard =  '|'.join([
                _('Supported files') + ' (*.ini,*.cfg,*.toml)'
                                       '|*.ini;*.cfg;*.toml',
                _('INI files') + ' (*.ini)|*.ini',
                _('Config files') + ' (*.cfg)|*.cfg',
                _('TOML files') + ' (*.toml)|*.toml',
            ])
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

    _ini_same_item = object()
    def ShowPanel(self, refresh_infos=False, refresh_target=True,
            clean_targets=False, focus_list=True, detail_item=_ini_same_item,
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
            if detail_item is not self._ini_same_item:
                self.uiList.RefreshUI(focus_list=focus_list,
                                      detail_item=detail_item)
            else:
                self.uiList.RefreshUI(focus_list=focus_list)

    def _sbCount(self):
        stati = self.uiList.CountTweakStatus()
        return _('Tweaks: %(status_num)d/%(total_status_num)d') % {
            'status_num': stati[0], 'total_status_num': sum(stati[:-1])}

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
        if not bush.game.has_esl:
            return _('Mods: %(status_num)d/%(total_status_num)d') % {
                'status_num': len(all_mods),
                'total_status_num': len(bosh.modInfos)}
        else:
            regular_mods_count = reduce(lambda accum, mod_path: accum + 1 if
            not bosh.modInfos[mod_path].is_esl() else accum, all_mods, 0)
            return _('Mods: %(status_num)d/%(total_status_num)d (ESP/M: '
                     '%(status_num_espm)d, ESL: %(status_num_esl)d)') % {
                'status_num': len(all_mods),
                'total_status_num': len(bosh.modInfos),
                'status_num_espm': regular_mods_count,
                'status_num_esl': len(all_mods) - regular_mods_count}

    def ClosePanel(self, destroy=False):
        load_order.persist_orders()
        super(ModPanel, self).ClosePanel(destroy)

#------------------------------------------------------------------------------
class SaveList(UIList):
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
        return f'{playMinutes // 60}:{playMinutes % 60:02d}'
    labels = {
        'File':     lambda self, p: p,
        'Modified': lambda self, p: format_date(self.data_store[p].mtime),
        'Size':     lambda self, p: round_size(self.data_store[p].fsize),
        'PlayTime': lambda self, p: self._playTime(self.data_store[p]),
        'Player': lambda self, p: self._headInfo(self.data_store[p], 'pcName'),
        'Cell':     lambda self, p: self._headInfo(self.data_store[p],
                                                   'pcLocation'),
    }

    @balt.conversation
    def OnLabelEdited(self, is_edit_cancelled, evt_label, evt_index, evt_item):
        """Savegame renamed."""
        if is_edit_cancelled: return EventResult.FINISH # todo CANCEL?
        newName, root = \
            self.panel.detailsPanel.file_info.validate_filename_str(evt_label)
        if not root:
            showError(self, newName)
            return EventResult.CANCEL # validate_filename would Veto
        item_edited = [self.panel.detailsPanel.displayed_item]
        to_select = set()
        to_del = set()
        for saveInfo in self.get_selected_infos_filtered():
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
                   item_edited=None, force_ext=''):
        newFileName = saveinf.unique_key(new_root, force_ext)
        oldName = self._try_rename(saveinf, newFileName)
        if oldName:
            if to_select is not None: to_select.add(newFileName)
            if to_del is not None: to_del.add(oldName)
            if item_edited and oldName == item_edited[0]:
                item_edited[0] = newFileName
            return oldName, newFileName # continue

    @staticmethod
    def _unhide_wildcard():
        starred = f'*{bush.game.Ess.ext};*.bak'
        return f'{bush.game.displayName} ' + _(
            'Save files') + f' ({starred})|{starred}'

    #--Populate Item
    def set_item_format(self, fileName, item_format, target_ini_setts):
        save_info = self.data_store[fileName]
        #--Image
        status = save_info.getStatus()
        item_format.icon_key = status, save_info.is_save_enabled()

    # Events ------------------------------------------------------------------
    @balt.conversation
    def _handle_left_down(self, wrapped_evt, lb_dex_and_flags):
        """Disable save by changing its extension so it's not loaded by the
        game."""
        #--Pass Event onward
        sinf = self._get_info_clicked(lb_dex_and_flags, on_icon=True)
        if not sinf: return
        # Don't allow enabling backups, the game won't read them either way
        if (fn_item := sinf.fn_key).fn_ext == u'.bak':
            showError(self, _('You cannot enable save backups.'))
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
        rename_res = self.try_rename(sinf, fn_item.fn_body,force_ext=extension)
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
        self._save_lo_real_index.clear()
        self._save_lo_hex_string.clear()
        # Check if we have to worry about ESL masters
        if bush.game.has_esl and new_file_info.header.has_esl_masters:
            save_lo_regular = {m: i for i, m in enumerate(
                new_file_info.header.masters_regular)}
            num_regular = len(save_lo_regular)
            # For ESL masters, we have to add an offset to the real index
            for i, m in enumerate(new_file_info.header.masters_esl):
                self._save_lo_real_index[m] = num_regular + i
                self._save_lo_hex_string[m] = f'FE {i:03X}'
        else:
            save_lo_regular = {m: i for i, m in enumerate(
                new_file_info.masterNames)}
        # For regular masters, simply store the LO index
        self._save_lo_real_index.update(save_lo_regular)
        self._save_lo_hex_string.update({m: f'{i:02X}' for m, i
                                         in save_lo_regular.items()})

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

    def SetFile(self, fileName=_same_file):
        fileName = super(SaveDetails, self).SetFile(fileName)
        if fileName:
            saveInfo = self.saveInfo = bosh.saveInfos[fileName]
            #--Remember values for edit checks
            self.fileStr = saveInfo.fn_key
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
        localized_info = _('Level %(player_level)d, Day %(save_day)d, '
                           'Play %(play_time)s') % {
            'player_level': self.playerLevel, 'save_day': int(self.gameDays),
            'play_time': f'{self.playMinutes // 60}:'
                         f'{self.playMinutes % 60:02d}'}
        self.playerInfo.label_text = (f'{self.playerNameStr}\n{localized_info}'
                                      f'\n{self.curCellStr}')

    def _update_masters_warning(self):
        """Show or hide the 'inaccurate masters' warning."""
        show_warning = self.uilist.is_inaccurate
        self._masters_label.label_text = (
            _(u'Masters (likely inaccurate, hover for more info):')
            if show_warning else _(u'Masters:'))
        self._masters_label.tooltip = (
            _('This save has ESL masters and cannot be displayed accurately '
              'without an up-to-date cosave. Please install the latest '
              'version of %(se_name)s and create a new save to see the true '
              'master order.') % {'se_name': bush.game.Se.se_abbrev}
            if show_warning else '')
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
        if not saveInfo or self.fileStr == saveInfo.fn_key:
            self.DoCancel()

    @balt.conversation
    def DoSave(self):
        """Event: Clicked Save button."""
        saveInfo = self.saveInfo
        #--Change Tests
        changeName = (self.fileStr != saveInfo.fn_key)
        changeMasters = self.uilist.edited
        #--Backup
        saveInfo.makeBackup() ##: why backup when just renaming - #292
        prevMTime = saveInfo.mtime
        #--Change Name?
        to_del = set()
        if changeName:
            newName = FName(self.fileStr.strip()).fn_body
            # if you were wondering: OnFileEdited checked if file existed,
            # and yes we recheck below, in Mod/BsaDetails we don't - filesystem
            # APIs might warn user (with a dialog hopefully) for an overwrite,
            # otherwise we can have a race whatever we try here - an extra
            # check can't harm nor makes a (any) difference
            self.panel_uilist.try_rename(saveInfo, newName, to_del=to_del)
        #--Change masters?
        if changeMasters:
            prev_masters = saveInfo.masterNames
            curr_masters = self.uilist.GetNewMasters()
            master_remaps = {m1: m2 for m1, m2
                             in zip(prev_masters, curr_masters) if m1 != m2}
            saveInfo.write_masters(master_remaps)
            saveInfo.setmtime(prevMTime)
            detail_item = self._refresh_detail_info()
        else: detail_item = self.file_info.fn_key
        kwargs = {u'to_del': to_del, u'detail_item': detail_item}
        if detail_item is None:
            kwargs[u'to_del'] = to_del | {self.file_info.fn_key}
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
    _status_str = _('Saves: %(status_num)d')
    _ui_list_type = SaveList
    _details_panel_type = SaveDetails

    def __init__(self,parent):
        if not bush.game.Ess.canReadBasic:
            raise BoltError(f'Wrye Bash cannot read save games for '
                            f'{bush.game.displayName}.')
        self.listData = bosh.saveInfos
        super(SavePanel, self).__init__(parent)
        BashFrame.saveList = self.uiList

    def ClosePanel(self, destroy=False):
        bosh.saveInfos.profiles.save()
        super(SavePanel, self).ClosePanel(destroy)

#------------------------------------------------------------------------------
class InstallersList(UIList):
    column_links = Links()
    context_links = Links()
    global_links = defaultdict(lambda: Links()) # Global menu
    _icons = InstallerColorChecks()
    _sunkenBorder = False
    _editLabels = _copy_paths = True
    _default_sort_col = u'Package'
    _sort_keys = {
        u'Package' : None,
        u'Order'   : lambda self, x: self.data_store[x].order,
        u'Modified': lambda self, x: self.data_store[x].file_mod_time,
        u'Size'    : lambda self, x: self.data_store[x].fsize,
        u'Files'   : lambda self, x: self.data_store[x].num_of_files,
    }
    #--Special sorters
    def _sortStructure(self, items):
        if settings[u'bash.installers.sortStructure']:
            items.sort(key=lambda x: self.data_store[x].type)
    def _sortActive(self, items):
        if settings[u'bash.installers.sortActive']:
            items.sort(key=lambda x: not self.data_store[x].is_active)
    def _sortProjects(self, items):
        if settings[u'bash.installers.sortProjects']:
            items.sort(key=lambda x: not self.data_store[x].is_project)
    _extra_sortings = [_sortStructure, _sortActive, _sortProjects]
    #--Labels
    labels = {
        'Package':  lambda self, p: p,
        'Order':    lambda self, p: f'{self.data_store[p].order}',
        'Modified': lambda self, p: format_date(self.data_store[p].file_mod_time),
        'Size':     lambda self, p: self.data_store[p].size_string(),
        'Files':    lambda self, p: self.data_store[p].number_string(
            self.data_store[p].num_of_files),
    }
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
        elif inst.is_marker:
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
            if inst.is_project: item_format.icon_key += u'.dir'
            if settings[u'bash.installers.wizardOverlay'] and inst.hasWizard:
                item_format.icon_key += u'.wiz'
        #if textKey == 'installers.text.invalid': # I need a 'text.markers'
        #    text += _(u'Marker Package. Use for grouping installers together')
        #--TODO: add mouse  mouse tips
        self.mouseTexts[item] = mouse_text

    def _check_rename_requirements(self):
        rename_type, rename_err = super()._check_rename_requirements()
        if rename_type is None:
            return rename_type, rename_err
        # Only allow renaming multiple packages if they have the same type
        for item in self.GetSelectedInfos():
            if type(item) != rename_type:
                return None, _("Wrye Bash can't rename mixed package types.")
        return rename_type, rename_err

    @balt.conversation
    def OnLabelEdited(self, is_edit_cancelled, evt_label, evt_index, evt_item):
        """Renamed some installers"""
        if is_edit_cancelled: return EventResult.FINISH ##: previous behavior todo TTT
        selected = self.get_selected_infos_filtered()
        # all selected have common type! enforced in OnBeginEditLabel
        newName, root = selected[0].validate_filename_str(evt_label,
            allowed_exts=archives.readExts)
        if root is None:
            showError(self, newName)
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
        starred = ';'.join(f'*{e}' for e in archives.readExts)
        return f'{bush.game.displayName} {_("Mod Archives")} ' \
               f'({starred})|{starred}'

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
        self.data_store.refresh_n()
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
                    if askYes(progress.dialog, _(
                        "The project '%(omod_project)s' already exists. Do "
                        "you want to overwrite it with '%(omod_name)s'?") % {
                            'omod_project': omod.sbody, 'omod_name': om_name}):
                        env.shellDelete([outDir], parent=self,
                                        recycle=True)  # recycle
                    else: continue
                try:
                    bosh.omods.OmodFile(omod).extractToProject(
                        outDir, SubProgress(progress, i), askYes)
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
            showOk(self, msg, _('OMOD Extraction Canceled'))
        else:
            if failed: showWarning(self, _(
                'The following OMODs failed to extract.  This could be '
                'a file IO error, or an unsupported OMOD format:') + '\n\n'
                    + '\n'.join(failed), _('OMOD Extraction Complete'))
        finally:
            progress(len(omodnames), _(u'Refreshing...'))

    def _askCopyOrMove(self, packages, converters):
        action = settings[u'bash.installers.onDropFiles.action']
        if action not in (u'COPY', u'MOVE'):
            msg = _('You have dragged the following files into Wrye '
                    'Bash:') + '\n\n * ' + '\n * '.join(
                f.stail for f in sorted(chain(packages, converters))) + '\n'
            msg += '\n' + _('What would you like to do with them?')
            action, remember = CopyOrMovePopup.display_dialog(self, msg,
                sizes_dict=settings, icon_bundle=balt.Resources.bashBlue)
            if action and remember:
                settings[u'bash.installers.onDropFiles.action'] = action
        return action

    def _overwrite_disallowed(self, target_file, is_package):
        """Checks if a package or converter is being overwritten by a 'drop
        files' action. If so, asks the user for confirmation. Returns True if
        there is no overwrite or the user has allowed the overwrite, False
        otherwise."""
        if target_file.exists():
            if is_package:
                overwrite_msg = _(
                    "A package with the name '%(target_fname)s' already "
                    "exists. Do you want to overwrite it?")
                overwrite_key = 'bash.installers.onDropFiles.overwrite_pkg'
                overwrite_title = _('Overwrite Package?')
            else:
                overwrite_msg = _(
                    "A BCF with the name '%(target_fname)s' already exists. "
                    "Do you want to overwrite it?")
                overwrite_key = 'bash.installers.onDropFiles.overwrite_conv'
                overwrite_title = _('Overwrite BCF?')
            return not balt.askContinue(self, overwrite_msg % {
                'target_fname': target_file.stail},
                f'{overwrite_key}.continue', title=overwrite_title)
        return False

    @balt.conversation
    def OnDropFiles(self, x: int, y: int, filenames: Iterable[str]):
        file_paths = [GPath(f) for f in filenames]
        dirs = {f for f in file_paths if f.is_dir()}
        omod_paths = [f for f in file_paths if
                      f not in dirs and f.cext in archives.omod_exts]
        converters = {c for c in file_paths if
                      bosh.converters.ConvertersData.validConverterName(
                          FName(f'{c}'))}
        packages = {p for p in file_paths if p not in converters and
                    (p in dirs or p.cext in archives.readExts)}
        if not (omod_paths or converters or packages): return
        if omod_paths:
            with balt.Progress(_(u'Extracting OMODs...'), abort=True) as prog:
                self._extractOmods(omod_paths, prog)
        if packages or converters:
            action = self._askCopyOrMove(packages, converters)
            if action in ('COPY', 'MOVE'):
                sources_dests: dict[bolt.Path, bolt.Path] = {}
                pkgs_dir = bass.dirs['installers']
                # Ask the user to confirm any overwrites for projects, for
                # archives (converters, archive installers) we can let
                # shellMove/Copy prompt for us
                for candidate_pkg in packages:
                    candidate_to = pkgs_dir.join(candidate_pkg.tail)
                    if candidate_pkg.is_dir() and self._overwrite_disallowed(
                        candidate_to, is_package=True):
                        continue
                    sources_dests[candidate_pkg] = candidate_to
                convs_dir = bass.dirs['converters']
                sources_dests |= {
                    candidate_conv: convs_dir.join(candidate_conv.tail)
                    for candidate_conv in converters
                }
                if not sources_dests:
                    return # All overwrites disallowed by user, abort
                with BusyCursor():
                    try:
                        shell_action = (env.shellMove if action == 'MOVE' else
                                        env.shellCopy)
                        shell_action(sources_dests, parent=self,
                            ask_confirm=askYes, allow_undo=True)
                    except (CancelError, SkipError):
                        pass
        self.panel.frameActivated = True
        self.panel.ShowPanel(focus_list=True)

    def dndAllow(self, event):
        if not self.sort_column in self._dndColumns:
            msg = _(u"Drag and drop in the Installer's list is only allowed "
                    u'when the list is sorted by install order')
            balt.askContinue(self, msg, 'bash.installers.dnd.column.continue',
                show_cancel=False)
            return super(InstallersList, self).dndAllow(event) # disallow
        return True

    def _handle_key_down(self, wrapped_evt):
        """Char event: Reorder."""
        kcode = wrapped_evt.key_code
        if wrapped_evt.is_cmd_down and kcode in balt.wxArrows:
            # Ctrl+Up/Ctrl+Down - move installer up/down install order
            selected = self.GetSelected()
            if len(selected) < 1: return
            orderKey = partial(self._sort_keys[u'Order'], self)
            moveMod = 1 if kcode in balt.wxArrowDown else -1 # move down or up
            sorted_ = sorted(selected, key=orderKey, reverse=(moveMod == 1))
            # get the index two positions after the last or before the first
            visibleIndex = self._get_uil_index(sorted_[0]) + moveMod * 2
            maxPos = max(x.order for x in self.data_store.values())
            for thisFile in sorted_:
                newPos = self.data_store[thisFile].order + moveMod
                if newPos < 0 or maxPos < newPos: break
                self.data_store.moveArchives([thisFile], newPos)
            self.data_store.refresh_n()
            self.RefreshUI()
            visibleIndex = sorted((visibleIndex, 0, maxPos))[1]
            self.EnsureVisibleIndex(visibleIndex)
        elif wrapped_evt.is_cmd_down and kcode == ord(u'V'):
            # Ctrl+V - drop files onto the Installers tab via clipboard
            read_files_from_clipboard_cb(
                lambda clip_file_paths: self.OnDropFiles(
                    0, 0, clip_file_paths))
        elif kcode in balt.wxReturn:
            # Enter - open selected installers
            self.OpenSelected()
        else:
            return super()._handle_key_down(wrapped_evt)
        # Otherwise we'd jump to a random plugin that starts with the key code
        return EventResult.FINISH

    def OnDClick(self, lb_dex_and_flags):
        """Handle double clicks on the Installers tab."""
        inst = self._get_info_clicked(lb_dex_and_flags)
        if not inst: return
        if inst.is_marker:
            # Double click on a marker - select all items below it in install
            # order, up to the next marker
            sorted_ = self._SortItems(col=u'Order', sortSpecial=False)
            new = []
            for nextItem in sorted_[inst.order + 1:]:
                if self.data_store[nextItem].is_marker:
                    break
                new.append(nextItem)
            if new:
                self.SelectItemsNoCallback(new)
                self.SelectItem((new[-1])) # show details for the last one
        else:
            # Double click on a package - open the package
            self.OpenSelected(selected=[inst.fn_key])

    def _handle_key_up(self, wrapped_evt):
        """Char events: Action depends on keys pressed"""
        if wrapped_evt.is_cmd_down and wrapped_evt.key_code == ord('N'):
            if wrapped_evt.is_shift_down:
                # Ctrl+Shift+N - Add a marker
                self.addMarker()
            else:
                # Ctrl+N - Create a new project
                CreateNewProject.display_dialog(self)
            return EventResult.FINISH
        else:
            super()._handle_key_up(wrapped_evt)

    # Installer specific ------------------------------------------------------
    def addMarker(self):
        selected_installers = self.GetSelected()
        if selected_installers:
            sorted_inst = self.data_store.sorted_values(selected_installers)
            max_order = sorted_inst[-1].order + 1 #place it after last selected
        else:
            max_order = None
        new_marker = FName('====')
        try:
            index = self._get_uil_index(new_marker)
        except KeyError: # '====' not found in the internal dictionary
            self.data_store.new_info(new_marker, install_order=max_order,
                                     is_mark=True)
            self.RefreshUI() # need to redraw all items cause order changed
            index = self._get_uil_index(new_marker)
        if index != -1:
            self.SelectAndShowItem(new_marker, deselectOthers=True,
                                   focus=True)
            self.Rename([new_marker])

    def rescanInstallers(self, toRefresh, abort, update_from_data=True,
                         calculate_projects_crc=False, shallow=False):
        """Refresh installers, ignoring skipRefresh flag.

        Will also update InstallersData for the paths this installer would
        install, in case a refresh is requested because those files were
        modified/deleted (BAIN only scans Data/ once or boot). If 'shallow' is
        True (only the configurations of the installers changed) it will run
        refreshDataSizeCrc of the installers, otherwise a full _reset_cache."""
        toRefresh = self.data_store.sorted_values(
            self.data_store.ipackages(toRefresh))
        if not toRefresh: return
        try:
            with balt.Progress(_('Refreshing Packages...'),
                               abort=abort) as progress:
                progress.setFull(len(toRefresh))
                dest = set() # installer's destination paths rel to Data/
                for index, installer in enumerate(toRefresh):
                    progress(index,
                             _('Refreshing Packages...') + f'\n{installer}')
                    if shallow:
                        op = installer.refreshDataSizeCrc
                    else:
                        op = partial(installer._reset_cache,
                            progress=SubProgress(progress, index, index + 1),
                            recalculate_project_crc=calculate_projects_crc)
                    dest.update(op())
                self.data_store.hasChanged = True  # is it really needed ?
                if update_from_data:
                    progress(0, _('Refreshing from %(data_folder)s...') % {
                        'data_folder': bush.game.mods_dir} + f'\n{" " * 60}')
                    self.data_store.update_data_SizeCrcDate(dest, progress)
        except CancelError:  # User canceled the refresh
            if not abort: raise # I guess CancelError is raised on aborting
        self.data_store.refresh_ns()
        self.RefreshUI()

#------------------------------------------------------------------------------
class InstallersDetails(_SashDetailsPanel):
    keyPrefix = u'bash.installers.details'
    defaultSashPos = - 32 # negative so it sets bottom panel's (comments) size
    minimumSize = 32 # so comments don't take too much space
    _ui_settings = {**_SashDetailsPanel._ui_settings,
        '.checkListSplitterSashPos' : _UIsetting(lambda self: 0,
        lambda self: self.checkListSplitter.get_sash_pos(),
        lambda self, sashPos: self.checkListSplitter.set_sash_pos(sashPos))
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
        self.espm_checklist_fns: list[FName] = []
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
            self._idata.hasChanged = True

    def SetFile(self, fileName=_same_file):
        """Refreshes detail view associated with data from item."""
        if self._displayed_installer is not None:
            self._save_comments()
        fileName = super(InstallersDetails, self).SetFile(fileName)
        self._displayed_installer = fileName
        del self.espm_checklist_fns[:]
        if fileName:
            installer = self._idata[fileName]
            #--Name
            self.gPackage.text_content = fileName
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
                next(sub_isactive) # pop empty sub-package, duh
                sub_isactive = {k: v for k, v in sub_isactive}
                self.gSubList.set_all_items_keep_pos(sub_isactive)
            self._update_fomod_state()
            #--Espms
            if not installer.espms:
                self.gEspmList.lb_clear()
            else:
                fns = self.espm_checklist_fns = sorted(installer.espms, key=lambda x: (
                    x.fn_ext != u'.esm', x)) # esms first then alphabetically
                espm_acti = {['', '*'][installer.isEspmRenamed(
                    x)] + x: x not in installer.espmNots for x in fns}
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
                    fn_file_dump = FName(str(file))
                    # Avoid running through _remaps over and over for
                    # non-plugins (can't use 'in modInfos' since the plugins
                    # may not be installed)
                    if bosh.modInfos.rightFileType(fn_file_dump):
                        oldName = installer.getEspmName(fn_file_dump)
                        if oldName != fn_file_dump:
                            buff.append(f'{oldName} -> {fn_file_dump}')
                            continue
                    buff.append(fn_file_dump)
                return buff.append('') or '\n'.join(buff) # add a newline
            elif header:
                return header+u'\n'
            else:
                return u''
        if pageName == u'gGeneral':
            inf_ = ['== ' + _('Overview'), _('Type: %(package_type)s') % {
                'package_type': installer.type_string},
                    installer.structure_string(), installer.size_info_str()]
            nConfigured = len(installer.ci_dest_sizeCrc)
            nMissing = len(installer.missingFiles)
            nMismatched = len(installer.mismatchedFiles)
            is_mark = installer.is_marker
            numstr = partial(installer.number_string, marker_string='N/A')
            inf_.extend([
                _('Modified: %(modified_date)s') % {
                    'modified_date': 'N/A' if is_mark else
                    format_date(installer.file_mod_time)},
                _('Data CRC: %(data_crc)s') % {
                    'data_crc': 'N/A' if is_mark else f'{installer.crc:08X}'},
                _('Files: %(num_files)s') % {
                    'num_files': f'{numstr(installer.num_of_files)}'},
                _('Configured: %(files_and_size)s') % {
                    'files_and_size': 'N/A' if is_mark else
                    f'{nConfigured:d} ({round_size(installer.unSize)})'},
                '  ' + _('Matched: %(num_files)s') % {
                    'num_files': numstr(nConfigured - nMissing - nMismatched)},
                '  ' + _('Missing: %(num_files)s') % {
                    'num_files': numstr(nMissing)},
                '  ' + _('Conflicts: %(num_files)s') % {
                    'num_files': numstr(nMismatched)},
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
        plugin_name = self.gEspmList.lb_get_str_item_at_index(lb_selection_dex)
        if plugin_name[0] == u'*':
            plugin_name = plugin_name[1:]
        return FName(plugin_name)

    def _on_plugin_filter_dclick(self, selected_index):
        """Handles double-clicking on a plugin in the plugin filter."""
        if selected_index < 0: return
        selected_name = self.get_espm(selected_index)
        if selected_name not in bosh.modInfos: return
        balt.Link.Frame.notebook.SelectPage(u'Mods', selected_name)
        return EventResult.FINISH

    def set_subpackage_checkmarks(self, checked):
        """Checks or unchecks all sub-package checkmarks and propagates that
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
        # Uncheck all sub-packages, otherwise the FOMOD files will get combined
        # with the ones from the checked sub-packages. Store the active
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
            settings['bash.installers.enabled'] = askYes(self, message,
                                                         _('Installers'))

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
            if settings.get('bash.installers.updatedCRCs', True): # only checked here
                settings['bash.installers.updatedCRCs'] = False
                self._data_dir_scanned = False
            do_refresh = scan_data_dir = scan_data_dir or not self._data_dir_scanned
            refresh_info = None
            if self.frameActivated: # otherwise we are called directly
                folders, files = map(list,
                                     top_level_items(bass.dirs['installers']))
                omds = [fninst for fninst in files if
                        fninst.fn_ext in archives.omod_exts]
                if any(inst_path not in omods.failedOmods for inst_path in
                       omds):
                    omod_projects = self.__extractOmods(omds) ##: change above to filter?
                    if omod_projects:
                        deprint(f'Extending projects: {omod_projects}')
                        folders.extend(omod_projects)
                if not do_refresh:
                    #with balt.Progress(_('Scanning Packages...')) as progress:
                    refresh_info = self.listData.update_installers(folders,
                        files, fullRefresh, progress=bolt.Progress())
                    do_refresh = refresh_info.refresh_needed()
            refreshui = False
            if do_refresh:
                with balt.Progress(_('Refreshing Installers...'),
                                   abort=canCancel) as progress:
                    try:
                        what = 'DISC' if scan_data_dir else 'IC'
                        refreshui |= self.listData.irefresh(progress, what,
                                                            fullRefresh,
                                                            refresh_info)
                        self.frameActivated = False
                    except CancelError:
                        self._user_cancelled = True # User canceled the refresh
                    finally:
                        self._data_dir_scanned = True
            elif self.frameActivated:
                try:
                    refreshui |= self.listData.irefresh(what='C',
                        fullRefresh=fullRefresh)
                    self.frameActivated = False
                except CancelError:
                    pass # User canceled the refresh
            do_refresh = self.listData.refreshTracked()
            refreshui |= do_refresh and self.listData.refreshInstallersStatus()
            if refreshui: self.uiList.RefreshUI(focus_list=focus_list)
            super(InstallersPanel, self).ShowPanel()
        finally:
            self.refreshing = False

    def __extractOmods(self, omds):
        omod_projects = []
        with balt.Progress(_('Extracting OMODs...')) as progress:
            dirInstallersJoin = bass.dirs[u'installers'].join
            progress.setFull(max(len(omds), 1))
            omodMoves, omodRemoves = set(), set()
            for i, fn_omod in enumerate(omds):
                progress(i, fn_omod)
                pr_name = bosh.InstallerProject.unique_name(fn_omod.fn_body,
                                                            check_exists=True)
                outDir = dirInstallersJoin(pr_name)
                try:
                    omod_path = dirInstallersJoin(fn_omod)
                    bosh.omods.OmodFile(omod_path).extractToProject(
                        outDir, SubProgress(progress, i), askYes)
                    omodRemoves.add(omod_path)
                    omod_projects.append(pr_name)
                except (CancelError, SkipError):
                    omodMoves.add(omod_path)
                except:
                    deprint(f"Error extracting OMOD '{fn_omod}':", traceback=True)
                    # Ensure we don't infinitely refresh if moving the omod
                    # fails
                    bosh.omods.failedOmods.add(fn_omod)
                    omodMoves.add(omod_path)
            # Cleanup
            dialog_title = _(u'OMOD Extraction - Cleanup Error')
            # Delete extracted omods
            def _del(files): env.shellDelete(files, parent=self)
            try:
                _del(omodRemoves)
            except (CancelError, SkipError):
                while askYes(self, _(
                        'Bash needs Administrator Privileges to delete '
                        'OMODs that have already been extracted.') +
                        '\n\n' + _('Try again?'), dialog_title):
                    try:
                        omodRemoves = [x for x in omodRemoves if x.exists()]
                        _del(omodRemoves)
                    except (CancelError, SkipError):
                        continue
                    break
                else:
                    # User decided not to give permission.  Add omod to
                    # 'failedOmods' so we know not to try to extract them again
                    for omod_path in omodRemoves:
                        if omod_path.exists():
                            bosh.omods.failedOmods.add(FName(omod_path.stail))
            # Move bad omods
            def _move_omods(failed: Iterable[bolt.Path]):
                env.shellMove({
                    omod: dirInstallersJoin('Bash', 'Failed OMODs', omod.tail)
                    for omod in failed
                }, parent=self)
            try:
                env.shellMakeDirs([dirInstallersJoin('Bash', 'Failed OMODs')])
                _move_omods(omodMoves)
            except (CancelError, SkipError):
                while askYes(self, _(
                        'Bash needs Administrator Privileges to move failed '
                        'OMODs out of the Bash Installers directory.') +
                        '\n\n' + _('Try again?'), dialog_title):
                    try:
                        omodMoves = [x for x in omodMoves if x.exists()]
                        _move_omods(omodMoves)
                    except (CancelError, SkipError):
                        continue
        return omod_projects

    def _sbCount(self):
        active = sum(x.is_active for x in self.listData.values())
        return _('Packages: %(status_num)d/%(total_status_num)d') % {
            'status_num': active, 'total_status_num': len(self.listData)}

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
class ScreensList(UIList):
    column_links = Links() #--Column menu
    context_links = Links() #--Single item menu
    global_links = defaultdict(lambda: Links()) # Global menu
    _editLabels = _copy_paths = True

    _sort_keys = {u'File'    : None,
                  u'Modified': lambda self, a: self.data_store[a].mtime,
                  u'Size'    : lambda self, a: self.data_store[a].fsize,
    }
    #--Labels
    labels ={
        'File':     lambda self, p: p,
        'Modified': lambda self, p: format_date(self.data_store[p].mtime),
        'Size':     lambda self, p: round_size(self.data_store[p].fsize),
    }

    # Events ------------------------------------------------------------------
    def OnDClick(self, lb_dex_and_flags):
        """Double click - open selected screenshot."""
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
            showError(self, root)
            return EventResult.CANCEL
        selected = self.get_selected_infos_filtered()
        #--Rename each screenshot, keeping the old extension
        num = int(numStr or 0)
        digits = len(f'{(num + len(selected) - 1)}')
        numStr = numStr.zfill(digits) if numStr else ''
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
        newName = FName(root + numStr + scrinf.fn_key.fn_ext) # TODO: add ScreenInfo.unique_key()
        if scrinf.get_store().store_dir.join(newName).exists():
            return None # break
        oldName = self._try_rename(scrinf, newName)
        if oldName:
            if to_select is not None: to_select.add(newName)
            if to_del is not None: to_del.add(oldName)
            if item_edited and oldName == item_edited[0]:
                item_edited[0] = newName
            return oldName, newName # continue

    def _handle_key_down(self, wrapped_evt):
        # Enter: Open selected screens
        if wrapped_evt.key_code in balt.wxReturn:
            self.OpenSelected()
        else:
            return super()._handle_key_down(wrapped_evt)
        # Otherwise we'd jump to a random screenshot that starts with the key
        # code
        return EventResult.FINISH

#------------------------------------------------------------------------------
class ScreensDetails(_DetailsMixin, NotebookPanel):

    def __init__(self, parent, ui_list_panel):
        super(ScreensDetails, self).__init__(parent)
        self.screenshot_control = Picture(self, 256, 192,
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

    def SetFile(self, fileName=_same_file):
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
    _status_str = _('Screens: %(status_num)d')
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
class BSAList(UIList):
    column_links = Links() #--Column menu
    context_links = Links() #--Single item menu
    global_links = defaultdict(lambda: Links()) # Global menu
    _sort_keys = {'File'    : None,
                  'Modified': lambda self, a: self.data_store[a].mtime,
                  'Size'    : lambda self, a: self.data_store[a].fsize,
    }
    #--Labels
    labels = {
        'File':     lambda self, p: p,
        'Modified': lambda self, p: format_date(self.data_store[p].mtime),
        'Size':     lambda self, p: round_size(self.data_store[p].fsize),
    }

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

    def SetFile(self, fileName=_same_file):
        """Set file to be viewed."""
        fileName = super(BSADetails, self).SetFile(fileName)
        if fileName:
            self._bsa_info = bosh.bsaInfos[fileName]
            #--Remember values for edit checks
            self.fileStr = self._bsa_info.fn_key
            self.gInfo.text_content = self._bsa_info.get_table_prop('info',
                _('Notes:') + ' ')
        else:
            self.gInfo.text_content = _('Notes:') + ' '
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
        if (newName := FName(self.fileStr.strip())) != self._bsa_info.fn_key:
            if self.panel_uilist.try_rename(self._bsa_info, newName):
                self.panel_uilist.RefreshUI(detail_item=self.file_info.fn_key)

#------------------------------------------------------------------------------
class BSAPanel(BashTab):
    """BSA info tab."""
    keyPrefix = u'bash.BSAs'
    _status_str = _('BSAs: %(status_num)d')
    _ui_list_type = BSAList
    _details_panel_type = BSADetails

    def __init__(self,parent):
        self.listData = bosh.bsaInfos
        super(BSAPanel, self).__init__(parent)
        BashFrame.bsaList = self.uiList

#--Tabs menu ------------------------------------------------------------------
_widget_to_panel = {}
class _Tab_Link(AppendableLink, CheckLink, EnabledLink):
    """Handle hiding/unhiding tabs."""

    def __init__(self, _text, tabKey, *, canDisable=True):
        super().__init__(_text)
        self.tabKey = tabKey
        self.enabled = canDisable
        self._help = _('Show/Hide the %(tabtitle)s Tab.') % {
            'tabtitle': self._text}

    def _append(self, window): return self._text is not None

    def _enable(self): return self.enabled

    def _check(self): return bass.settings[u'bash.tabs.order'][self.tabKey]

    def Execute(self):
        tab_info = tabInfo
        if bass.settings[u'bash.tabs.order'][self.tabKey]:
            # It was enabled, disable it.
            iMods = None
            iInstallers = None
            iDelete = None
            for i in range(Link.Frame.notebook.GetPageCount()):
                pageTitle = Link.Frame.notebook.GetPageText(i)
                if pageTitle == tab_info[u'Mods'][1]:
                    iMods = i
                elif pageTitle == tab_info[u'Installers'][1]:
                    iInstallers = i
                if pageTitle == tab_info[self.tabKey][1]:
                    iDelete = i
            if iDelete == Link.Frame.notebook.GetSelection():
                # We're deleting the current page...
                if ((iDelete == 0 and iInstallers == 1) or
                        (iDelete - 1 == iInstallers)):
                    # The auto-page change will change to
                    # the 'Installers' tab.  Change to the
                    # 'Mods' tab instead.
                    Link.Frame.notebook.SetSelection(iMods)
            tab_info[self.tabKey][2].ClosePanel() ##: note the panel remains in memory
            page = Link.Frame.notebook.GetPage(iDelete)
            Link.Frame.notebook.RemovePage(iDelete)
            page.Show(False)
        else:
            # It was disabled, enable it
            insertAt = 0
            for k, k_enabled in bass.settings[u'bash.tabs.order'].items():
                if k == self.tabKey: break
                insertAt += k_enabled
            className,title,panel = tab_info[self.tabKey]
            if not panel:
                panel = globals()[className](Link.Frame.notebook)
                tab_info[self.tabKey][2] = panel
                _widget_to_panel[panel.wx_id_()] = panel
            if insertAt > Link.Frame.notebook.GetPageCount():
                Link.Frame.notebook.AddPage(panel._native_widget,title)
            else:
                Link.Frame.notebook.InsertPage(insertAt,panel._native_widget,title)
        bass.settings[u'bash.tabs.order'][self.tabKey] ^= True

class BashNotebook(wx.Notebook, balt.TabDragMixin):

    # default tabs order and default enabled state, keys as in tabInfo
    _tabs_enabled_ordered = {'Installers': True, 'Mods': True, 'Saves': True,
                             'INI Edits': True, 'Screenshots': True,
                            # ('BSAs', False),
    }

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
        tab_info = tabInfo
        for page, enabled in self._tabOrder().items():
            if not enabled: continue
            className, title, _item = tab_info[page]
            panel = globals().get(className,None)
            if panel is None: continue
            deprint(f"Constructing panel '{title}'")
            # Some page specific stuff
            if page == u'Installers': iInstallers = self.GetPageCount()
            elif page == u'Mods': iMods = self.GetPageCount()
            # Add the page
            try:
                item = panel(self)
                self.AddPage(item._native_widget, title)
                tab_info[page][2] = item
                _widget_to_panel[item.wx_id_()] = item
                deprint(f"Panel '{title}' constructed successfully")
            except:
                if page == 'Mods':
                    deprint(f"Fatal error constructing panel '{title}'.")
                    raise
                deprint(f"Error constructing '{title}' panel.",
                        traceback=True)
                settings['bash.tabs.order'][page] = False
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
        # use tabOrder here - it is used in InitLinks which runs *before*
        # settings['bash.tabs.order'] is set!
        for key, (__cls, tab_title, __panel) in BashNotebook._tabOrder():
            menu.append(
                _Tab_Link(tab_title, key, canDisable=bool(key != 'Mods')))
        return menu

    def SelectPage(self, page_title, item):
        """Jumps to the specified item on the specified tab.

        Note: If you call this from inside an event handler, be sure to return
        EventResult.FINISH, otherwise a later OS handler may steal focus onto
        the now-invisible tab."""
        ind = 0
        for tab_key, is_enabled in settings['bash.tabs.order'].items():
            if tab_key == page_title:
                if not is_enabled: return
                break
            ind += is_enabled
        else: raise BoltError(f'Invalid tab key: {page_title}')
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
            newOrder = [removeKey, *oldOrder]
        elif newPos == self.GetPageCount() - 1: # Moved to the end
            newOrder = [*oldOrder, removeKey]
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

    def UpdateIconSizes(self, skip_refresh=False):
        self.buttons = {} # populated with SBLinks whose gButtons is not None
        # when bash is run for the first time those are empty - set here
        order = settings[u'bash.statusbar.order']
        hide = settings[u'bash.statusbar.hide']
        # filter for non-existent ids and reorder the dict according to order
        hidden = {lid for lid in hide if lid in BashStatusBar.all_sb_links}
        hide.clear()
        hide.update(hidden)
        saved_order = {lid: li for lid in order if
                       (li := BashStatusBar.all_sb_links.get(lid))}
        # append new buttons and reorder BashStatusBar.all_sb_links
        BashStatusBar.all_sb_links = saved_order | BashStatusBar.all_sb_links
        order[:] = list(BashStatusBar.all_sb_links) # set bash.statusbar.order
        # Add buttons in order that is saved
        for link_uid, link in BashStatusBar.all_sb_links.items():
            # Hidden?
            if link_uid in hide: continue
            # Not present ?
            if not link.IsPresent(): continue
            # Add it
            try:
                self._addButton(link)
            except AttributeError: # '_App_Button' object has no attribute 'imageKey'
                deprint(f'Failed to load button {link_uid!r}', traceback=True)
        if not skip_refresh:
            self.refresh_status_bar(refresh_icon_size=True)

    def HideButton(self, button, skip_refresh=False):
        for link_uid, link in self.buttons.items():
            if link.gButton is button:
                button.visible = False
                del self.buttons[link_uid]
                settings['bash.statusbar.hide'].add(link_uid)
                if not skip_refresh:
                    self.refresh_status_bar()
                return

    def UnhideButton(self, link, skip_refresh=False):
        uid = link.uid
        settings[u'bash.statusbar.hide'].discard(uid)
        # Find the position to insert it at
        order = settings[u'bash.statusbar.order']
        self._addButton(link)
        if uid not in order:
            # Not specified, put it at the end
            order.append(uid)
        else:
            self._sort_buttons(order)
        if not skip_refresh:
            self.refresh_status_bar()

    def refresh_status_bar(self, refresh_icon_size=False):
        """Updates status widths and the icon sizes, if refresh_icon_size is
        True. Also propagates resizing events.

        :param refresh_icon_size: Whether or not to update icon sizes too."""
        txt_len = 280 if bush.game.has_esl else 130
        self.SetStatusWidths([self.iconsSize * len(self.buttons), -1, txt_len])
        if refresh_icon_size:
            ##: Why - 12? I just tried values until it looked good, why does
            # this one work best?
            self.SetMinHeight(self.iconsSize - 12)
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
    _key_prefix = 'bash.frame'
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
            message = _(
                'It appears that you have more than 325 plugins and BSAs '
                'in your %(data_folder)s folder and auto-ghosting is '
                'disabled. This may cause problems in %(game_name)s; see the '
                'auto-ghost section of the readme for more details and '
                'consider enabling auto-ghosting.') % {
                'data_folder': bush.game.mods_dir,
                'game_name': bush.game.displayName}
            if len(bosh.bsaInfos) + len(bosh.modInfos) >= 400:
                message = _(
                    'It appears that you have more than 400 plugins and BSAs '
                    'in your %(data_folder)s folder and auto-ghosting is '
                    'disabled. This will cause problems in %(game_name)s; see '
                    'the auto-ghost section of the readme for more '
                    'details.') % {'data_folder': bush.game.mods_dir,
                                   'game_name': bush.game.displayName}
            showWarning(self, message, title=_('Too Many Plugins.'))

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
        self.exit_wb()

    def exit_wb(self):
        """Closes Wrye Bash as if the X in the upper right corner had been
        pressed. That means it includes saving settings etc."""
        ##: This breaks on py3 + wx4.2, use sys.exit + manual save for now
        #self.close_win(True)
        self.SaveSettings()
        sys.exit(0)

    def set_bash_frame_title(self):
        """Set title. Set to default if no title supplied."""
        if bush.game.altName and settings[u'bash.useAltName']:
            if bass.is_standalone:
                title = _('%(wb_alt_name)s %(wb_version)s (Standalone)')
            else:
                title = '%(wb_alt_name)s %(wb_version)s'
        else:
            if bass.is_standalone:
                title = _('Wrye Bash %(wb_version)s (Standalone) for '
                          '%(game_name)s')
            else:
                title = _('Wrye Bash %(wb_version)s for %(game_name)s')
        title %= {'wb_alt_name': bush.game.altName,
                  'wb_version': bass.AppVersion,
                  'game_name': bush.game.displayName}
        title += ': '
        # chop off save prefix - +1 for the path separator
        maProfile = bosh.saveInfos.localSave[len(
            bush.game.Ini.save_prefix) + 1:]
        if maProfile:
            title += maProfile
        else:
            title += _('Default')
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

    # Events ------------------------------------------------------------------
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
        initialization.lootDb.refreshBashTags()
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
        #--Done (end recursion blocker)
        self.inRefreshData = False
        return EventResult.FINISH

    def _warn_reset_load_order(self):
        if load_order.warn_locked and not bass.inisettings[
            u'SkipResetTimeNotifications']:
            showWarning(self, _('Load order has changed outside of Bash and '
                'has been reverted to the one saved in Bash. You can hit '
                'Ctrl + Z while the mods list has focus to undo this.'),
                _('Lock Load Order'))
            load_order.warn_locked = False

    def warn_load_order(self):
        """Warn if plugins.txt has bad or missing files, or is overloaded."""
        def mk_warning(lo_warn_msg: str, warning_plugins: Iterable[FName]):
            """Helper for creating a single warning change entry from the
            specified warning message and to-be-highlighted plugins."""
            warning_dec_plugins = self.modList.decorate_tree_dict(
                {p: [] for p in sorted(warning_plugins)})
            return LoadOrderSanitizedDialog.make_change_entry(
                mods_list_images=self.modList._icons,
                mods_change_desc=lo_warn_msg,
                decorated_plugins=warning_dec_plugins)
        lo_warnings = []
        if bosh.modInfos.selectedBad:
            lo_warnings.append(mk_warning(
                _('The following plugins could not be found in the '
                  '%(data_folder)s folder or are corrupt and have thus been '
                  'removed from the load order.') % {
                    'data_folder': bush.game.mods_dir,
                }, bosh.modInfos.selectedBad))
            bosh.modInfos.selectedBad = set()
        if bosh.modInfos.selectedExtra:
            if bush.game.has_esl:
                warn_msg = _('The following plugins have been deactivated '
                             'because only %(max_regular_plugins)d regular '
                             'plugins and %(max_esl_plugins)d ESL-flagged '
                             'plugins may be active at the same time.')
            else:
                warn_msg = _('The following plugins have been deactivated '
                             'because only %(max_regular_plugins)d plugins '
                             'may be active at the same time.')
            lo_warnings.append(mk_warning(warn_msg % {
                'max_regular_plugins': load_order.max_espms(),
                'max_esl_plugins': load_order.max_esls(),
            }, bosh.modInfos.selectedExtra))
            bosh.modInfos.selectedExtra = set()
        ##: Disable this message for now, until we're done testing if we can
        # get the game to load these files
        # if bosh.modInfos.activeBad:
        #     lo_warnings.append(mk_warning(
        #         _('The following plugins have been deactivated because they '
        #           'have filenames that cannot be encoded in Windows-1252 and '
        #           'thus cannot be loaded by %(game_name)s.') % {
        #             'game_name': bush.game.displayName,
        #         }, bosh.modInfos.activeBad))
        #     bosh.modInfos.activeBad = set()
        if lo_warnings:
            LoadOrderSanitizedDialog(self,
                highlight_changes=lo_warnings).show_modeless()

    def warn_corrupted(self, warn_mods=False, warn_saves=False,
                       warn_strings=False, warn_bsas=False):
        def mk_warning(warn_msg: str, warning_items: Iterable[FName], *,
                target_uil: UIList, target_tab_key: str):
            """Helper for creating a single warning change entry from the
            specified warning message and to-be-highlighted items, relative to
            the specified UIList/Tab."""
            if target_uil is not None:
                warning_dec_items = target_uil.decorate_tree_dict(
                    {i: [] for i in sorted(warning_items)})
            else:
                # Tab is not enabled, no way to decorate with it
                warning_dec_items = {
                    i: (None, []) for i in sorted(warning_items)}
            return MultiWarningDialog.make_change_entry(
                uil_images=target_uil._icons if target_uil else None,
                origin_tab_key=target_tab_key, warn_change_desc=warn_msg,
                decorated_items=warning_dec_items)
        def mk_mods_warning(warn_msg: str, warning_items: Iterable[FName]):
            """Version of mk_warning for the Mods tab."""
            return mk_warning(warn_msg, warning_items,
                target_uil=self.modList, target_tab_key='Mods')
        def mk_saves_warning(warn_msg: str, warning_items: Iterable[FName]):
            """Version of mk_warning for the Saves tab."""
            return mk_warning(warn_msg, warning_items,
                target_uil=self.saveList, target_tab_key='Saves')
        def mk_bsa_warning(warn_msg: str, warning_items: Iterable[FName]):
            """Version of mk_warning for the BSAs tab."""
            return mk_warning(warn_msg, warning_items,
                target_uil=self.bsaList, target_tab_key='BSAs')
        multi_warnings = []
        corruptMods = set(bosh.modInfos.corrupted)
        if warn_mods and not corruptMods <= self.knownCorrupted:
            multi_warnings.append(mk_mods_warning(
                _('The following plugins could not be read. This most likely '
                  'means that they are corrupt.'),
                corruptMods - self.knownCorrupted))
            self.knownCorrupted |= corruptMods
        corruptSaves = set(bosh.saveInfos.corrupted)
        if warn_saves and not corruptSaves <= self.knownCorrupted:
            multi_warnings.append(mk_saves_warning(
                _('The following save files could not be read. This most '
                  'likely means that they are corrupt.'),
                corruptSaves - self.knownCorrupted))
            self.knownCorrupted |= corruptSaves
        valid_vers = bush.game.Esp.validHeaderVersions
        invalidVersions = {ck for ck, x in bosh.modInfos.items() if
                           all(x.header.version != v for v in valid_vers)}
        if warn_mods and not invalidVersions <= self.known_invalid_versions:
            multi_warnings.append(mk_mods_warning(
                _('The following plugins have header versions that are not '
                  'valid for this game. This may mean that they are '
                  'actually intended to be used for a different game.'),
                invalidVersions - self.known_invalid_versions))
            self.known_invalid_versions |= invalidVersions
        old_fvers = bosh.modInfos.older_form_versions
        if warn_mods and not old_fvers <= self.known_older_form_versions:
            multi_warnings.append(mk_mods_warning(
                _('The following plugins use an older Form Version for their '
                  'main header. This most likely means that they were not '
                  'ported properly (if at all).'),
                old_fvers - self.known_older_form_versions))
            self.known_older_form_versions |= old_fvers
        if warn_strings and bosh.modInfos.new_missing_strings:
            multi_warnings.append(mk_mods_warning(
                _('The following plugins are marked as localized, but are '
                  'missing strings localization files in the language your '
                  'game is set to. This will cause CTDs if they are '
                  'activated.'), bosh.modInfos.new_missing_strings))
            bosh.modInfos.new_missing_strings.clear()
        bsa_mvers = bosh.bsaInfos.mismatched_versions
        if warn_bsas and not bsa_mvers <= self.known_mismatched_version_bsas:
            multi_warnings.append(mk_bsa_warning(
                _('The following BSAs have a version different from the one '
                  '%(game_name)s expects. This can lead to CTDs, please '
                  'extract and repack them using the %(ck_name)s-provided '
                  'tool.') % {'game_name': bush.game.displayName,
                              'ck_name': bush.game.Ck.long_name},
                bsa_mvers - self.known_mismatched_version_bsas))
            self.known_mismatched_version_bsas |= bsa_mvers
        ba2_colls = bosh.bsaInfos.ba2_collisions
        if warn_bsas and not ba2_colls <= self.known_ba2_collisions:
            multi_warnings.append(mk_bsa_warning(
                _('The following BA2s have filenames whose hashes collide, '
                  'which will cause one or more of them to fail to work '
                  'correctly. This should be corrected by the mod author(s) '
                  'by renaming the files to avoid the collision.'),
                ba2_colls - self.known_ba2_collisions))
            self.known_ba2_collisions |= ba2_colls
        if multi_warnings:
            MultiWarningDialog(self,
                highlight_changes=multi_warnings).show_modeless()

    _ini_missing = _('%(game_ini_file)s does not exist yet. %(game_name)s '
                     'will create this file on first run. INI tweaks will not '
                     'be usable until then.')
    @balt.conversation
    def warn_game_ini(self):
        #--Corrupt Oblivion.ini
        if self.oblivionIniCorrupted != bosh.oblivionIni.isCorrupted:
            self.oblivionIniCorrupted = bosh.oblivionIni.isCorrupted
            if self.oblivionIniCorrupted:
                msg = '\n'.join([self.oblivionIniCorrupted, '', _(
                    'Please replace the INI with a default copy and restart '
                    'Wrye Bash.')])
                showWarning(self, msg, title=_('Corrupted Game INI'))
        elif self.oblivionIniMissing != self._oblivionIniMissing:
            self._oblivionIniMissing = self.oblivionIniMissing
            if self._oblivionIniMissing:
                showWarning(self, self._ini_missing % {
                    'game_ini_file': bosh.oblivionIni.abs_path,
                    'game_name': bush.game.displayName},
                    title=_('Missing Game INI'))

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
                deprint(f'An error occurred while saving settings of '
                        f'the {tab_name} panel:', traceback=True)
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
            goodRoots = {p.fn_body for p in fileInfos}
            backupDir = fileInfos.bash_dir.join(u'Backups')
            if not backupDir.is_dir(): continue
            for back_fname in backupDir.ilist():
                back_path = backupDir.join(back_fname)
                if back_fname.fn_body not in goodRoots and back_path.is_file():
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
        # bash.global_menu == 2 -> Column Menu Only
        show_gm = bass.settings['bash.global_menu'] != 2 and os_name == 'nt'
        self._native_widget.SetMenuBar(self.global_menu._native_widget
                                       if show_gm else None)

    def start_update_check(self):
        """Starts the background update check by creating a new thread and
        passing along a custom event sender that will call
        _on_update_check_done once it's done."""
        version_sender = self._make_custom_event(self._on_update_check_done)
        UCThread(version_sender).start()

    def _on_update_check_done(self, *, newer_version: LatestVersion | None):
        """Internal callback, called from the update checking thread via custom
        event once it has completed its work."""
        if (newer_version is not None and
                newer_version.wb_version > LooseVersion(bass.AppVersion)):
            UpdateNotification.display_dialog(self, newer_version)

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
def InitSettings(): # this must run first !
    """Initializes settings dictionary for bosh and basher."""
    bosh.initSettings(askYes)
    global settings
    balt._settings = bass.settings
    settings = bass.settings
    settings.loadDefaults(settingDefaults)
    bass.settings['bash.mods.renames'] = forward_compat_path_to_fn(
        bass.settings['bash.mods.renames'],
        value_type=lambda x: FName(str(f'{x}'))) # str**2 in case of CIstr
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
    bosh.bain.Installer.init_global_skips(askYes) # must be after loadDefaults - grr #178
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
        if isinstance(color_val, str):
            color_val = str_to_sig(color_val)
        if isinstance(color_val, bytes):
            color_val = _conv_dict[color_val]
            settings[u'bash.colors'][color_key] = color_val
        colors[color_key] = Color(*color_val)
    #--Images
    imgDirJn = bass.dirs[u'images'].join
    def _png(fname): return ImageWrapper(imgDirJn(fname))
    def _svg(fname, bm_px_size):
        """Creates an SVG wrapper.

        :param fname: The SVG's filename, relative to bash/images.
        :param bm_px_size: The size of the resulting bitmap, in
            device-independent pixels (DIP)."""
        return ImageWrapper(imgDirJn(fname), iconSize=bm_px_size)
    # PNGs --------------------------------------------------------------------
    # Checkboxes
    images['checkbox.red.on.16'] = _png('checkbox_red_on.png')
    images['checkbox.red.on.24'] = _png('checkbox_red_on_24.png')
    images['checkbox.red.on.32'] = _png('checkbox_red_on_32.png')
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
    # SVGs --------------------------------------------------------------------
    # Up/Down arrows for UIList columns
    images['arrow.up.16'] = _svg('arrow_up.svg', 16)
    images['arrow.down.16'] = _svg('arrow_down.svg', 16)
    # Modification time button
    images['calendar.16'] = _svg('calendar.svg', 16)
    # DocumentViewer
    images['back.16'] = _svg('back.svg', 16)
    images['forward.16'] = _svg('forward.svg', 16)
    # Browse and Reset buttons
    images['folder.16'] = _svg('folder.svg', 16)
    images['reset.16'] = _svg('reset.svg', 16)
    # DocumentViewer and Restart
    images['reload.16'] = _svg('reload.svg', 16)
    images['reload.24'] = _svg('reload.svg', 24)
    images['reload.32'] = _svg('reload.svg', 32)
    # Checkmark/Cross
    images['checkmark.16'] = _svg('checkmark.svg', 16)
    images['error_cross.16'] = _svg('error_cross.svg', 16)
    # Minus/Plus for the Bash Tags popup
    images['minus.16'] = _svg('minus.svg', 16)
    images['plus.16'] = _svg('plus.svg', 16)
    # Warning icon in various GUIs
    images['warning.32'] = _svg('warning.svg', 32)
    # Settings button
    images['settings_button.16'] = _svg('gear.svg', 16)
    images['settings_button.24'] = _svg('gear.svg', 24)
    images['settings_button.32'] = _svg('gear.svg', 32)
    # Help button(s)
    images['help.16'] = _svg('help.svg', 16)
    images['help.24'] = _svg('help.svg', 24)
    images['help.32'] = _svg('help.svg', 32)
    # Plugin Checker
    images['plugin_checker.16'] = _svg('checklist.svg', 16)
    images['plugin_checker.24'] = _svg('checklist.svg', 24)
    images['plugin_checker.32'] = _svg('checklist.svg', 32)
    # Doc Browser
    images['doc_browser.16'] = _svg('book.svg', 16)
    images['doc_browser.24'] = _svg('book.svg', 24)
    images['doc_browser.32'] = _svg('book.svg', 32)
    # Check/Uncheck All buttons
    images['square_empty.16'] = _svg('square_empty.svg', 16)
    images['square_check.16'] = _svg('square_checked.svg', 16)
    # Deletion dialog button
    images['trash_can.32'] = _svg('trash_can.svg', 32)

##: This hides a circular dependency (__init__ -> links_init -> __init__)
from .links_init import InitLinks
