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
from __future__ import division
import StringIO
import collections
import os
import re
import sys
import time
from collections import OrderedDict, namedtuple
from functools import partial, reduce
from operator import itemgetter
#--wxPython
import wx

#--Local
from .. import bush, bosh, bolt, bass, env, load_order, archives
from ..bolt import GPath, SubProgress, deprint, round_size
from ..bosh import omods
from ..cint import CBashApi
from ..exception import AbstractError, BoltError, CancelError, FileError, \
    SkipError, UnknownListener
from ..localize import format_date, unformat_date

startupinfo = bolt.startupinfo

#--Balt
from .. import balt
from ..balt import CheckLink, EnabledLink, SeparatorLink, Link, \
    ChoiceLink, staticBitmap, AppendableLink, ListBoxes, \
    INIListCtrl, DnDStatusBar, NotebookPanel
from ..balt import colors, images, Resources
from ..balt import Links, ItemLink

from ..gui import Button, CancelButton, CheckBox, HLayout, Label, \
    LayoutOptions, RIGHT, SaveButton, Spacer, Stretch, TextArea, TextField, \
    TOP, VLayout, EventResult, DropDown, DialogWindow, WindowFrame, Spinner, \
    Splitter, NotebookCtrl, PanelWin, CheckListBox, Color, Picture, Image

# Constants -------------------------------------------------------------------
from .constants import colorInfo, settingDefaults, karmacons, installercons

# BAIN wizard support, requires PyWin32, so import will fail if it's not installed
try:
    from .. import belt
    bEnableWizard = True
except ImportError:
    bEnableWizard = False
    deprint(_(u"Error initializing installer wizards:"),traceback=True)

#  - Make sure that python root directory is in PATH, so can access dll's.
if sys.prefix not in set(os.environ['PATH'].split(';')):
    os.environ['PATH'] += ';'+sys.prefix

# Settings --------------------------------------------------------------------
settings = None

# Links -----------------------------------------------------------------------
#------------------------------------------------------------------------------
##: DEPRECATED: Tank link mixins to access the Tank data. They should be
# replaced by self.window.method but I keep them till encapsulation reduces
# their use to a minimum
class Installers_Link(ItemLink):
    """InstallersData mixin"""
    @property
    def idata(self):
        """:rtype: bosh.InstallersData"""
        return self.window.data_store
    @property
    def iPanel(self):
        """:rtype: InstallersPanel"""
        return self.window.panel

class People_Link(Link):
    """PeopleData mixin"""
    @property
    def pdata(self):
        """:rtype: bosh.PeopleData"""
        return self.window.data_store

#--Information about the various Tabs
tabInfo = {
    # InternalName: [className, title, instance]
    'Installers': ['InstallersPanel', _(u"Installers"), None],
    'Mods': ['ModPanel', _(u"Mods"), None],
    'Saves': ['SavePanel', _(u"Saves"), None],
    'INI Edits': ['INIPanel', _(u"INI Edits"), None],
    'Screenshots': ['ScreensPanel', _(u"Screenshots"), None],
    'People':['PeoplePanel', _(u"People"), None],
    # 'BSAs':['BSAPanel', _(u"BSAs"), None],
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
    def SetDetails(self, fileName='SAME'): self._setDetails(fileName)

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
    def esmsFirst(self): return settings.get(self.keyPrefix + '.esmsFirst',
                            True) or self.sort_column in self._esmsFirstCols
    @esmsFirst.setter
    def esmsFirst(self, val): settings[self.keyPrefix + '.esmsFirst'] = val

    @property
    def selectedFirst(self):
        return settings.get(self.keyPrefix + '.selectedFirst', False)
    @selectedFirst.setter
    def selectedFirst(self, val):
        settings[self.keyPrefix + '.selectedFirst'] = val

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
    mainMenu = Links()
    itemMenu = Links()
    keyPrefix = 'bash.masters' # use for settings shared among the lists (cols)
    _editLabels = True
    #--Sorting
    _default_sort_col = 'Num'
    _sort_keys = {
        'Num'          : None, # sort by master index, the key itself
        'File'         : lambda self, a:
            self.data_store[a].curr_name.s.lower(),
        # Missing mods sort last alphabetically
        'Current Order': lambda self, a: self.loadOrderNames.index(
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
        ('File',          lambda self, mi: bosh.modInfos.masterWithVersion(
            self.data_store[mi].curr_name.s)),
        ('Num',           lambda self, mi: u'%02X' % mi),
        ('Current Order', lambda self, mi: bosh.modInfos.hexIndexString(
            self.data_store[mi].curr_name)),
    ])
    # True if we should highlight masters whose stored size does not match the
    # size of the plugin on disk
    _do_size_checks = False

    @property
    def cols(self):
        # using self.__class__.keyPrefix for common saves/mods masters settings
        return settings.getChanged(self.__class__.keyPrefix + '.cols')

    message = _(u"Edit/update the masters list? Note that the update process "
                u"may automatically rename some files. Be sure to review the "
                u"changes before saving.")

    def __init__(self, parent, listData=None, keyPrefix=keyPrefix, panel=None,
                 detailsPanel=None):
        #--Data/Items
        self.edited = False
        self.detailsPanel = detailsPanel
        self.fileInfo = None
        self.loadOrderNames = [] # cache, orders missing last alphabetically
        self._allowEditKey = keyPrefix + '.allowEdit'
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
                   self, self.message, self.keyPrefix + '.update.continue',
                   _(u'Update Masters') + u' ' + _(u'BETA'))):
            return
        bass.settings[self._allowEditKey] = val
        if val:
            self.InitEdit()
        else:
            self.SetFileInfo(self.fileInfo)
            self.detailsPanel.testChanges() # disable buttons if no other edits

    def _handle_select(self, item_key): pass
    def _handle_key_up(self, wrapped_evt, g_list): pass

    def OnDClick(self, lb_dex_and_flags):
        if self.mouse_index < 0: return # nothing was clicked
        mod_name = self.data_store[self.mouse_index].curr_name
        if not mod_name in bosh.modInfos: return
        balt.Link.Frame.notebook.SelectPage('Mods', mod_name)

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
        has_sizes = bush.game.Esp.check_master_sizes and isinstance(
            fileInfo, bosh.ModInfo) # only mods have master sizes
        for mi, masters_name in enumerate(fileInfo.get_masters()):
            masters_size = fileInfo.header.master_sizes[mi] if has_sizes else 0
            self.data_store[mi] = bosh.MasterInfo(masters_name, masters_size)
        self._reList()
        self.PopulateItems()

    #--Get Master Status
    def GetMasterStatus(self, mi):
        masterInfo = self.data_store[mi]
        masters_name = masterInfo.curr_name
        status = masterInfo.getStatus()
        if status == 30: return status # does not exist
        # current load order of master relative to other masters
        loadOrderIndex = self.loadOrderNames.index(masters_name)
        ordered = load_order.cached_active_tuple()
        if mi != loadOrderIndex: # there are active masters out of order
            return 20  # orange
        elif status > 0:
            return status  # never happens
        elif (mi < len(ordered)) and (ordered[mi] == masters_name):
            return -10  # Blue
        else:
            return status  # 0, Green

    def set_item_format(self, mi, item_format):
        masterInfo = self.data_store[mi]
        masters_name = masterInfo.curr_name
        #--Font color
        fileBashTags = masterInfo.getBashTags()
        mouseText = u''
        if masters_name in bosh.modInfos.bashed_patches:
            item_format.text_key = 'mods.text.bashedPatch'
        elif masters_name in bosh.modInfos.mergeable:
            if u'NoMerge' in fileBashTags and not bush.game.check_esl:
                item_format.text_key = 'mods.text.noMerge'
                mouseText += _(u"Technically mergeable but has NoMerge tag.  ")
            else:
                item_format.text_key = 'mods.text.mergeable'
                if bush.game.check_esl:
                    mouseText += _(u"Qualifies to be ESL flagged.  ")
                else:
                    # Merged plugins won't be in master lists
                    mouseText += _(u"Can be merged into Bashed Patch.  ")
        else:
            # NoMerge / Mergeable should take priority over ESL/ESM color
            is_master = load_order.in_master_block(masterInfo)
            is_esl = masterInfo.is_esl()
            if is_master and is_esl:
                item_format.text_key = 'mods.text.eslm'
                mouseText += _(u'ESL Flagged file. Master file.')
            elif is_master:
                item_format.text_key = 'mods.text.esm'
                mouseText += _(u"Master file. ")
            elif is_esl:
                item_format.text_key = 'mods.text.esl'
                mouseText += _(u"ESL Flagged file. ")
        #--Text BG
        if bosh.modInfos.isBadFileName(masters_name.s):
            if load_order.cached_is_active(masters_name):
                item_format.back_key = 'mods.bkgd.doubleTime.load'
            else:
                item_format.back_key = 'mods.bkgd.doubleTime.exists'
        elif masterInfo.hasActiveTimeConflict():
            item_format.back_key = 'mods.bkgd.doubleTime.load'
        elif masterInfo.hasTimeConflict():
            item_format.back_key = 'mods.bkgd.doubleTime.exists'
        elif masterInfo.is_ghost:
            item_format.back_key = 'mods.bkgd.ghosted'
        elif self._do_size_checks and bosh.modInfos.size_mismatch(
                masters_name, masterInfo.stored_size):
            item_format.back_key = u'mods.bkgd.size_mismatch'
            mouseText += _(u'Stored size does not match the one on disk. ')
        if self.allowEdit:
            if masterInfo.old_name in settings['bash.mods.renames']:
                item_format.strong = True
        #--Image
        status = self.GetMasterStatus(mi)
        oninc = load_order.cached_is_active(masters_name) or (
            masters_name in bosh.modInfos.merged and 2)
        on_display = self.detailsPanel.displayed_item
        if status == 30: # master is missing
            mouseText += _(u"Missing master of %s.  ") % on_display
        #--HACK - load order status
        elif on_display in bosh.modInfos:
            if status == 20:
                mouseText += _(u"Reordered relative to other masters.  ")
            lo_index = load_order.cached_lo_index
            if lo_index(on_display) < lo_index(masters_name):
                mouseText += _(u"Loads after %s.  ") % on_display
                status = 20 # paint orange
        item_format.icon_key = status, oninc
        self.mouseTexts[mi] = mouseText

    #--Relist
    def _reList(self):
        fileOrderNames = [v.curr_name for v in self.data_store.itervalues()]
        self.loadOrderNames = load_order.get_ordered(fileOrderNames)

    #--InitEdit
    def InitEdit(self):
        #--Pre-clean
        edited = False
        for mi, masterInfo in self.data_store.items():
            newName = settings['bash.mods.renames'].get(masterInfo.curr_name,
                                                        None)
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

    def OnLabelEdited(self, is_edit_cancelled, evt_label, evt_index, evt_item):
        newName = GPath(evt_label)
        #--No change?
        if newName in bosh.modInfos:
            masterInfo = self.data_store[evt_item]
            masterInfo.set_name(newName)
            self.SetMasterlistEdited()
            settings.getChanged('bash.mods.renames')[
                masterInfo.old_name] = newName
            # populate, refresh must be called last
            self.PopulateItem(itemDex=evt_index)
            return EventResult.FINISH ##: needed?
        elif newName == u'':
            return EventResult.CANCEL
        else:
            balt.showError(self,_(u'File %s does not exist.') % newName.s)
            return EventResult.CANCEL

    #--GetMasters
    def GetNewMasters(self):
        """Returns new master list."""
        return [v.curr_name for k, v in
                sorted(self.data_store.items(), key=itemgetter(0))]

#------------------------------------------------------------------------------
class INIList(balt.UIList):
    mainMenu = Links()  #--Column menu
    itemMenu = Links()  #--Single item menu
    _shellUI = True
    _sort_keys = {'File'     : None,
                  'Installer': lambda self, a: bosh.iniInfos.table.getItem(
                     a, 'installer', u''),
                 }
    def _sortValidFirst(self, items):
        if settings['bash.ini.sortValid']:
            items.sort(key=lambda a: self.data_store[a].tweak_status < 0)
    _extra_sortings = [_sortValidFirst]
    #--Labels
    labels = OrderedDict([
        ('File',      lambda self, p: p.s),
        ('Installer', lambda self, p: self.data_store.table.getItem(
                                                   p, 'installer', u'')),
    ])

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
        for ini_info in self.data_store.itervalues():
            status = ini_info.tweak_status
            if status == -10: invalid += 1
            elif status == 0: not_applied += 1
            elif status == 10: mismatch += 1
            elif status == 20: applied += 1
        return applied,mismatch,not_applied,invalid

    def ListTweaks(self):
        """Returns text list of tweaks"""
        tweaklist = _(u'Active Ini Tweaks:') + u'\n'
        tweaklist += u'[spoiler][xml]\n'
        for tweak, info in sorted(self.data_store.items(), key=itemgetter(0)):
            if not info.tweak_status == 20: continue
            tweaklist+= u'%s\n' % tweak
        tweaklist += u'[/xml][/spoiler]\n'
        return tweaklist

    @staticmethod
    def filterOutDefaultTweaks(ini_tweaks):
        """Filter out default tweaks from tweaks iterable."""
        return filter(lambda x: not bosh.iniInfos[x].is_default_tweak, ini_tweaks)

    def _toDelete(self, items):
        items = super(INIList, self)._toDelete(items)
        return self.filterOutDefaultTweaks(items)

    def set_item_format(self, ini_name, item_format):
        iniInfo = self.data_store[ini_name]
        status = iniInfo.tweak_status
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
            item_format.back_key = 'ini.bkgd.invalid'

    def _handle_left_down(self, wrapped_evt, lb_dex_and_flags):
        """Handle click on icon events
        :param wrapped_evt:
        """
        hitItem = self._getItemClicked(lb_dex_and_flags, on_icon=True)
        if not hitItem: return
        if self.apply_tweaks((bosh.iniInfos[hitItem], )):
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
            else: stat = ini_info.tweak_status
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
        default_ini = bass.dirs[u'app'].join(bush.game.defaultIniFile)
        if default_ini.exists():
            msg += _(u'Do you want Bash to create it by copying '
                     u'%(default_ini)s ?' % {u'default_ini': default_ini})
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
        except (OSError, IOError):
            error_msg = u'Failed to copy %s to %s' % (
                default_ini, target_ini_file.abs_path)
            deprint(error_msg, traceback=True)
            balt.showError(None, error_msg, _(u'Missing game Ini'))
        return False

    @staticmethod
    @balt.conversation
    def _warn_tweak_game_ini(chosen):
        ask = True
        if chosen in bush.game.iniFiles:
            message = (_(u"Apply an ini tweak to %s?") % chosen + u'\n\n' + _(
                u"WARNING: Incorrect tweaks can result in CTDs and even "
                u"damage to your computer!"))
            ask = balt.askContinue(balt.Link.Frame, message,
                                   'bash.iniTweaks.continue', _(u"INI Tweaks"))
        return ask

#------------------------------------------------------------------------------
class INITweakLineCtrl(INIListCtrl):

    def __init__(self, parent, iniContents):
        super(INITweakLineCtrl, self).__init__(parent)
        self.tweakLines = []
        self.iniContents = self._contents = iniContents

    def _get_selected_line(self, index): return self.tweakLines[index][5]

    def RefreshTweakLineCtrl(self, tweakPath):
        if tweakPath is None:
            self.DeleteAllItems()
            return
        # TODO(ut) avoid if ini tweak did not change
        self.tweakLines = bosh.iniInfos.get_tweak_lines_infos(tweakPath)
        num = self.GetItemCount()
        updated = set()
        for i,line in enumerate(self.tweakLines):
            #--Line
            if i >= num:
                self.InsertItem(i, line[0])
            else:
                self.SetItem(i, 0, line[0])
            #--Line color
            status, deleted = line[4], line[6]
            if status == -10: color = colors['tweak.bkgd.invalid']
            elif status == 10: color = colors['tweak.bkgd.mismatched']
            elif status == 20: color = colors['tweak.bkgd.matched']
            elif deleted: color = colors['tweak.bkgd.mismatched']
            else: color = Color.from_wx(self.GetBackgroundColour())
            color = color.to_rgba_tuple()
            self.SetItemBackgroundColour(i, color)
            #--Set iniContents color
            lineNo = line[5]
            if lineNo != -1:
                self.iniContents.SetItemBackgroundColour(lineNo,color)
                updated.add(lineNo)
        #--Delete extra lines
        start = len(self.tweakLines)
        for i in xrange(start, num): self.DeleteItem(start)
        #--Reset line color for other iniContents lines
        background_color = self.iniContents.GetBackgroundColour()
        for i in xrange(self.iniContents.GetItemCount()):
            if i in updated: continue
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

    def RefreshIniContents(self, new_target=False):
        if bosh.iniInfos.ini.isCorrupted: return
        if new_target:
            self.DeleteAllItems()
        num = self.GetItemCount()
        try:
            with bosh.iniInfos.ini.abs_path.open('r') as target_ini_file:
                lines = target_ini_file.readlines()
            if bush.game.iniFiles[0] == bosh.iniInfos.ini.abs_path.stail:
                Link.Frame.oblivionIniMissing = False
            for i,line in enumerate(lines):
                if i >= num:
                    self.InsertItem(i, line.rstrip())
                else:
                    self.SetItem(i, 0, line.rstrip())
            for i in xrange(len(lines), num):
                self.DeleteItem(len(lines))
        except IOError:
            if bush.game.iniFiles[0] == bosh.iniInfos.ini.abs_path.stail:
                Link.Frame.oblivionIniMissing = True
        self.fit_column_to_header(0)

#------------------------------------------------------------------------------
class ModList(_ModsUIList):
    #--Class Data
    mainMenu = Links() #--Column menu
    itemMenu = Links() #--Single item menu
    def _get(self, mod): return partial(self.data_store.table.getItem, mod)
    _sort_keys = {
        'File'      : None,
        'Author'    : lambda self, a: self.data_store[a].header.author.lower(),
        'Rating'    : lambda self, a: self._get(a)('rating', u''),
        'Group'     : lambda self, a: self._get(a)('group', u''),
        'Installer' : lambda self, a: self._get(a)('installer', u''),
        'Load Order': lambda self, a: load_order.cached_lo_index_or_max(a),
        'Modified'  : lambda self, a: self.data_store[a].mtime,
        'Size'      : lambda self, a: self.data_store[a].size,
        'Status'    : lambda self, a: self.data_store[a].getStatus(),
        'Mod Status': lambda self, a: self.data_store[a].txt_status(),
        'CRC'       : lambda self, a: self.data_store[a].cached_mod_crc(),
    }
    _extra_sortings = [_ModsUIList._sortEsmsFirst,
                       _ModsUIList._activeModsFirst]
    _dndList, _dndColumns = True, ['Load Order']
    _sunkenBorder = False
    #--Labels
    labels = OrderedDict([
        ('File',       lambda self, p: self.data_store.masterWithVersion(p.s)),
        ('Load Order', lambda self, p: self.data_store.hexIndexString(p)),
        ('Rating',     lambda self, p: self._get(p)('rating', u'')),
        ('Group',      lambda self, p: self._get(p)('group', u'')),
        ('Installer',  lambda self, p: self._get(p)('installer', u'')),
        ('Modified',   lambda self, p: format_date(self.data_store[p].mtime)),
        ('Size',       lambda self, p: round_size(self.data_store[p].size)),
        ('Author',     lambda self, p: self.data_store[p].header.author if
                                       self.data_store[p].header else u'-'),
        ('CRC',        lambda self, p: self.data_store[p].crc_string()),
        ('Mod Status', lambda self, p: self.data_store[p].txt_status()),
    ])

    #-- Drag and Drop-----------------------------------------------------
    def _dropIndexes(self, indexes, newIndex): # will mess with plugins cache !
        """Drop contiguous indexes on newIndex and return True if LO changed"""
        if newIndex < 0: return False # from OnChar() & moving master esm up
        count = self.item_count
        dropItem = self.GetItem(newIndex if (count > newIndex) else count - 1)
        firstItem = self.GetItem(indexes[0])
        lastItem = self.GetItem(indexes[-1])
        return bosh.modInfos.dropItems(dropItem, firstItem, lastItem)

    def OnDropIndexes(self, indexes, newIndex):
        if self._dropIndexes(indexes, newIndex): self._refreshOnDrop()

    def dndAllow(self, event):
        msg = u''
        continue_key = 'bash.mods.dnd.column.continue'
        if not self.sort_column in self._dndColumns:
            msg = _(u'Reordering mods is only allowed when they are sorted '
                    u'by Load Order.')
        else:
            pinned = load_order.filter_pinned(self.GetSelected())
            if pinned:
                msg = _(u"You can't reorder the following mods:\n" +
                        u', '.join(map(unicode, pinned)))
                continue_key = 'bash.mods.dnd.pinned.continue'
        if msg:
            balt.askContinue(self, msg, continue_key)
            return super(ModList, self).dndAllow(event) # disallow
        return True

    @balt.conversation
    def _refreshOnDrop(self):
        #--Save and Refresh
        try:
            bosh.modInfos.cached_lo_save_all()
        except BoltError as e:
            balt.showError(self, u'%s' % e)
        self.RefreshUI(refreshSaves=True)

    #--Populate Item
    def set_item_format(self, mod_name, item_format):
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
        if mod_name in bosh.modInfos.bad_names:
            mouseText += _(u'Plugin name incompatible, cannot be activated.  ')
        if mod_name in bosh.modInfos.missing_strings:
            mouseText += _(u'Plugin is missing String Localization files.  ')
        if mod_name in bosh.modInfos.bashed_patches:
            item_format.text_key = 'mods.text.bashedPatch'
        elif mod_name in bosh.modInfos.mergeable:
            if u'NoMerge' in fileBashTags and not bush.game.check_esl:
                item_format.text_key = 'mods.text.noMerge'
                mouseText += _(u"Technically mergeable but has NoMerge tag.  ")
            else:
                item_format.text_key = 'mods.text.mergeable'
                if bush.game.check_esl:
                    mouseText += _(u'Can be ESL-flagged. ')
                else:
                    if checkMark == 2:
                        mouseText += _(u"Merged into Bashed Patch.  ")
                    else:
                        mouseText += _(u"Can be merged into Bashed Patch.  ")
        else:
            # NoMerge / Mergeable should take priority over ESL/ESM color
            final_text_key = 'mods.text.es'
            if mod_info.is_esl():
                final_text_key += 'l'
                mouseText += _(u'ESL-flagged plugin. ')
            if load_order.in_master_block(mod_info):
                final_text_key += 'm'
                mouseText += _(u'Master plugin. ')
            # Check if it's special, leave ESPs alone
            if final_text_key != 'mods.text.es':
                item_format.text_key = final_text_key
        #--Image messages
        if status == 30:
            mouseText += _(u"One or more masters are missing.  ")
        else:
            if status in {20, 21}:
                mouseText += _(u"Loads before its master(s).  ")
            if status in {10, 21}:
                mouseText += _(u"Masters have been re-ordered.  ")
        if checkMark == 1:   mouseText += _(u'Active in load order. ')
        elif checkMark == 3: mouseText += _(u"Imported into Bashed Patch.  ")
        #should mod be deactivated
        if u'Deactivate' in fileBashTags:
            item_format.italics = True
        #--Text BG
        if mod_name in bosh.modInfos.bad_names:
            item_format.back_key ='mods.bkgd.doubleTime.exists'
        elif mod_name in bosh.modInfos.missing_strings:
            if load_order.cached_is_active(mod_name):
                item_format.back_key = 'mods.bkgd.doubleTime.load'
            else:
                item_format.back_key = 'mods.bkgd.doubleTime.exists'
        elif mod_info.hasBadMasterNames():
            if load_order.cached_is_active(mod_name):
                item_format.back_key = 'mods.bkgd.doubleTime.load'
            else:
                item_format.back_key = 'mods.bkgd.doubleTime.exists'
            mouseText += _(u"WARNING: Has master names that will not load.  ")
        elif mod_info.hasActiveTimeConflict():
            item_format.back_key = 'mods.bkgd.doubleTime.load'
            mouseText += _(u"WARNING: Has same load order as another mod.  ")
        elif u'Deactivate' in fileBashTags and checkMark == 1:
            item_format.back_key = 'mods.bkgd.deactivate'
            mouseText += _(u"Mod should be imported and deactivated.  ")
        elif mod_info.hasTimeConflict():
            item_format.back_key = 'mods.bkgd.doubleTime.exists'
            mouseText += _(u"Has same time as another (unloaded) mod.  ")
        elif mod_info.isGhost:
            item_format.back_key = 'mods.bkgd.ghosted'
            mouseText += _(u"File is ghosted.  ")
        elif (bush.game.Esp.check_master_sizes
              and mod_info.has_master_size_mismatch()):
            item_format.back_key = u'mods.bkgd.size_mismatch'
            mouseText += _(u'Has one or more size-mismatched masters. ')
        if settings['bash.mods.scanDirty']:
            message = bosh.modInfos.getDirtyMessage(mod_name)
            mouseText += message[1]
            if message[0]: item_format.underline = True
        self.mouseTexts[mod_name] = mouseText

    def RefreshUI(self, **kwargs):
        """Refresh UI for modList - always specify refreshSaves explicitly."""
        super(ModList, self).RefreshUI(**kwargs)
        if kwargs.pop('refreshSaves', False):
            Link.Frame.saveListRefresh(focus_list=False)

    #--Events ---------------------------------------------
    def OnDClick(self, lb_dex_and_flags):
        """Handle doubleclicking a mod in the Mods List."""
        hitItem = self._getItemClicked(lb_dex_and_flags)
        if not hitItem: return
        modInfo = self.data_store[hitItem]
        if not Link.Frame.docBrowser:
            from .frames import DocBrowser
            DocBrowser().show_frame()
            settings['bash.modDocs.show'] = True
        Link.Frame.docBrowser.SetMod(modInfo.name)
        Link.Frame.docBrowser.raise_frame()

    def OnChar(self, wrapped_evt):
        """Char event: Reorder (Ctrl+Up and Ctrl+Down)."""
        code = wrapped_evt.key_code
        if wrapped_evt.is_cmd_down and code in balt.wxArrows:
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
            moveMod = 1 if code in balt.wxArrowDown else -1
            moved = False
            for chunk in chunks:
                newIndex = chunk[0] + moveMod
                if chunk[-1] + moveMod == self.item_count:
                    continue # trying to move last plugin past the list
                moved |= self._dropIndexes(chunk, newIndex)
            if moved: self._refreshOnDrop()
        # Ctrl+Z: Undo last load order or active plugins change
        # Can't use ord('Z') below - check wx._core.KeyEvent docs
        elif wrapped_evt.is_cmd_down and code == 26:
            if self.data_store.undo_load_order():
                self.RefreshUI(refreshSaves=True)
        elif wrapped_evt.is_cmd_down and code == 25:
            if self.data_store.redo_load_order():
                self.RefreshUI(refreshSaves=True)
        else: # correctly update the highlight around selected mod
            return EventResult.CONTINUE
        return EventResult.FINISH

    def _handle_key_up(self, wrapped_evt, g_list):
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
        # Ctrl+C: Copy file(s) to clipboard
        elif wrapped_evt.is_cmd_down and wrapped_evt.key_code == ord(u'C'):
            balt.copyListToClipboard([self.data_store[mod].getPath().s
                                      for mod in self.GetSelected()])
        super(ModList, self)._handle_key_up(wrapped_evt, g_list)

    def _handle_left_down(self, wrapped_evt, lb_dex_and_flags):
        """Left Down: Check/uncheck mods.
        :param wrapped_evt:
        """
        mod_clicked_on_icon = self._getItemClicked(lb_dex_and_flags, on_icon=True)
        if mod_clicked_on_icon:
            self._toggle_active_state(mod_clicked_on_icon)
            # select manually as OnSelectItem() will fire for the wrong
            # index if list is sorted with active mods first
            self.SelectAndShowItem(mod_clicked_on_icon, deselectOthers=True,
                                   focus=True)
            return EventResult.FINISH
        else:
            mod_clicked = self._getItemClicked(lb_dex_and_flags)
            if wrapped_evt.is_alt_down and mod_clicked:
                if self.jump_to_mods_installer(mod_clicked): return
            #--Pass Event onward to OnSelectItem

    def _select(self, modName):
        super(ModList, self)._select(modName)
        if Link.Frame.docBrowser:
            Link.Frame.docBrowser.SetMod(modName)

    @staticmethod
    def _unhide_wildcard():
        return bosh.modInfos.plugin_wildcard()

    #--Helpers ---------------------------------------------
    @balt.conversation
    def _toggle_active_state(self, *mods):
        """Toggle active state of mods given - all mods must be either
        active or inactive."""
        refreshNeeded = False
        active = [mod for mod in mods if load_order.cached_is_active(mod)]
        assert not active or len(active) == len(mods) # empty or all
        inactive = (not active and mods) or []
        changes = collections.defaultdict(dict)
        # Deactivate ?
        touched = set()
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
                refreshNeeded += len(changed)
                if len(changed) > (act in changed): # deactivated children
                    touched |= changed
                    changed = [x for x in changed if x != act]
                    changes[self.__deactivated_key][act] = \
                        load_order.get_ordered(changed)
            except BoltError as e:
                balt.showError(self, u'%s' % e)
        # Activate ?
        touched = set()
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
                refreshNeeded += len(activated)
                if len(activated) > (inact in activated):
                    touched |= set(activated)
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
            balt.askContinue(self, u"You can't deactivate the following "
                                   u'mods:\n%s' %
                             u', '.join(illegal_deactivations),
                             'bash.mods.dnd.illegal_deactivation.continue')
        if illegal_activations:
            balt.askContinue(self, u"You can't activate the following "
                                   u'mods:\n%s' %
                             u', '.join(illegal_activations),
                             'bash.mods.dnd.illegal_activation.continue')
        if refreshNeeded:
            bosh.modInfos.cached_lo_save_active()
            self.__toggle_active_msg(changes)
            self.RefreshUI(refreshSaves=True)

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
        installer = self.get_installer(modName)
        if installer is None:
            return False
        balt.Link.Frame.notebook.SelectPage('Installers', installer)
        return True

    def get_installer(self, modName):
        if not balt.Link.Frame.iPanel or not bass.settings[
            'bash.installers.enabled']: return None
        installer = self.data_store.table.getColumn('installer').get(modName)
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
    def SetFile(self, fileName='SAME'):
        """Set file to be viewed. Leave fileName empty to reset.
        :type fileName: basestring | bolt.Path | None
        """
        #--Reset?
        if fileName == 'SAME':
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
        self.save = SaveButton(buttonsParent)
        self.save.on_clicked.subscribe(self.DoSave)
        self.cancel = CancelButton(buttonsParent)
        self.cancel.on_clicked.subscribe(self.DoCancel)
        self.save.enabled = False
        self.cancel.enabled = False

    # Details panel API
    def SetFile(self, fileName='SAME'):
        #--Edit State
        self.edited = False
        self.save.enabled = False
        self.cancel.enabled = False
        return super(_EditableMixin, self).SetFile(fileName)

    # Abstract edit methods
    @property
    def allowDetailsEdit(self): raise AbstractError

    def SetEdited(self):
        if not self.displayed_item: return
        self.edited = True
        if self.allowDetailsEdit:
            self.save.enabled = True
        self.cancel.enabled = True

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
        return self.file_info.name if self.file_info else None

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
        #--Extension Changed?
        if fileStr[-4:].lower() != self.fileStr[-4:].lower():
            balt.showError(self,_(u"Incorrect file extension: ")+fileStr[-3:])
            self._fname_ctrl.text_content = self.fileStr
        #--Validate the filename - no need to check for extension again
        elif not self._validate_filename(fileStr):
            self._fname_ctrl.text_content = self.fileStr
        #--Else file exists?
        elif self.file_info.dir.join(fileStr).exists():
            balt.showError(self,_(u"File %s already exists.") % fileStr)
            self._fname_ctrl.text_content = self.fileStr
        #--Okay?
        else:
            self.fileStr = fileStr
            self.SetEdited()

    def _validate_filename(self, fileStr):
        return self.panel_uilist.validate_filename(fileStr)[0]

    def OnFileEdit(self, new_text):
        """Event: Editing filename."""
        if not self.file_info: return
        if not self.edited and self.fileStr != new_text:
            self.SetEdited()

    @balt.conversation
    def _refresh_detail_info(self):
        try: # use self.file_info.name, as name may have been updated
            # Although we could avoid rereading the header I leave it here as
            # an extra error check - error handling is WIP
            self.panel_uilist.data_store.new_info(self.file_info.name,
                                                  notify_bain=True)
            return self.file_info.name
        except FileError as e:
            deprint(u'Failed to edit details for %s' % self.displayed_item,
                    traceback=True)
            balt.showError(self,
                           _(u'File corrupted on save!') + u'\n' + e.message)
            return None

class _SashDetailsPanel(_DetailsMixin, SashPanel):
    """Details panel with two splitters"""
    _ui_settings = {u'.subSplitterSashPos' : _UIsetting(lambda self: 0,
        lambda self: self.subSplitter.get_sash_pos(),
        lambda self, sashPos: self.subSplitter.set_sash_pos(sashPos))}
    _ui_settings.update(SashPanel._ui_settings)

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

    def __init__(self, parent, ui_list_panel):
        _SashDetailsPanel.__init__(self, parent)
        # min_pane_size split the bottom panel into the master uilist and mod tags/save notes
        self.masterPanel, self._bottom_low_panel = \
            self.subSplitter.make_panes()
        _EditableMixinOnFileInfos.__init__(self, self.masterPanel,
                                           ui_list_panel)
        #--Masters
        self.uilist = self._master_list_type(
            self.masterPanel, keyPrefix=self.keyPrefix, panel=ui_list_panel,
            detailsPanel=self)
        VLayout(spacing=4, items=[
            Label(self.masterPanel, _(u"Masters:")),
            (self.uilist, LayoutOptions(weight=1, expand=True)),
            HLayout(spacing=4, items=[self.save, self.cancel])
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

class ModDetails(_ModsSavesDetails):
    """Details panel for mod tab."""
    keyPrefix = 'bash.mods.details' # used in sash/scroll position, sorting
    _master_list_type = _ModMasterList

    @property
    def file_info(self): return self.modInfo
    @property
    def file_infos(self): return bosh.modInfos
    @property
    def allowDetailsEdit(self): return bush.game.Esp.canEditHeader

    def __init__(self, parent, ui_list_panel):
        super(ModDetails, self).__init__(parent, ui_list_panel)
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
        self.modified = TextField(top, max_length=32)
        self.modified.on_focus_lost.subscribe(self.OnEditModified)
        self.modified.on_text_changed.subscribe(self.OnModifiedEdit)
        # size=(textWidth, -1),
        #--Description
        self.description = TextArea(top, auto_tooltip=False, max_length=511)
            # size=(textWidth, 128),
        self.description.on_focus_lost.subscribe(self.OnEditDescription)
        self.description.on_text_changed.subscribe(self.OnDescrEdit)
        #--Bash tags
        self.gTags = TextArea(self._bottom_low_panel, auto_tooltip=False,
                              editable=False)
                                # size=(textWidth, 64))
        self.gTags.on_right_clicked.subscribe(self.ShowBashTagsMenu)
        #--Layout
        VLayout(spacing=4, item_expand=True, items=[
            HLayout(items=[Label(top, _(u'File:')), Stretch(), self.version]),
            self._fname_ctrl,
            Label(top, _(u'Author:')), self.gAuthor,
            Label(top, _(u'Modified:')), self.modified,
            Label(top, _(u'Description:')),
            (self.description, LayoutOptions(expand=True, weight=1))
        ]).apply_to(top)
        VLayout(spacing=4, items=[
            Label(self._bottom_low_panel, _(u'Bash Tags:')),
            (self.gTags, LayoutOptions(expand=True, weight=1))
        ]).apply_to(self._bottom_low_panel)

    def _resetDetails(self):
        self.modInfo = None
        self.fileStr = u''
        self.authorStr = u''
        self.modifiedStr = u''
        self.descriptionStr = u''
        self.versionStr = u'v0.00'

    def SetFile(self,fileName='SAME'):
        fileName = super(ModDetails, self).SetFile(fileName)
        if fileName:
            modInfo = self.modInfo = bosh.modInfos[fileName]
            #--Remember values for edit checks
            self.fileStr = modInfo.name.s
            self.authorStr = modInfo.header.author
            self.modifiedStr = format_date(modInfo.mtime)
            self.descriptionStr = modInfo.header.description
            self.versionStr = u'v%0.2f' % modInfo.header.version
            tagsStr = u'\n'.join(sorted(modInfo.getBashTags()))
        else: tagsStr = u''
        #--Set fields
        self._fname_ctrl.text_content = self.fileStr
        self.gAuthor.text_content = self.authorStr
        self.modified.text_content = self.modifiedStr
        self.description.text_content = self.descriptionStr
        self.version.label_text = self.versionStr
        self.uilist.SetFileInfo(self.modInfo)
        self.gTags.text_content = tagsStr
        if fileName and not bosh.modInfos.table.getItem(fileName,'autoBashTags', True):
            self.gTags.set_background_color(
                self.gAuthor.get_background_color())
        else:
            self.gTags.set_background_color(self.get_background_color())
        # TODO(inf) de-wx! - or investigate why it's needed
        self.gTags._native_widget.Refresh()

    def _OnTextEdit(self, old_text, new_text):
        if not self.modInfo: return
        if not self.edited and old_text != new_text: self.SetEdited()

    def OnAuthorEdit(self, new_text):
        self._OnTextEdit(self.authorStr, new_text)
    def OnModifiedEdit(self, new_text):
        self._OnTextEdit(self.modifiedStr, new_text)
    def OnDescrEdit(self, new_text):
        self._OnTextEdit(self.descriptionStr.replace(
            '\r\n', '\n').replace('\r', '\n'), new_text)

    def OnEditAuthor(self):
        if not self.modInfo: return
        authorStr = self.gAuthor.text_content
        if authorStr != self.authorStr:
            self.authorStr = authorStr
            self.SetEdited()

    def OnEditModified(self):
        if not self.modInfo: return
        modifiedStr = self.modified.text_content
        if modifiedStr == self.modifiedStr: return
        try:
            newTimeTup = unformat_date(modifiedStr, '%c')
            time.mktime(newTimeTup)
        except ValueError:
            balt.showError(self,_(u'Unrecognized date: ')+modifiedStr)
            self.modified.text_content = self.modifiedStr
            return
        #--Normalize format
        modifiedStr = time.strftime('%c', newTimeTup)
        self.modifiedStr = modifiedStr
        self.modified.text_content = modifiedStr #--Normalize format
        self.SetEdited()

    def OnEditDescription(self):
        if not self.modInfo: return
        if self.description.text_content != self.descriptionStr.replace('\r\n',
                '\n').replace('\r', '\n'):
            self.descriptionStr = self.description.text_content ##: .replace('\n', 'r\n')
            self.SetEdited()

    bsaAndBlocking = _(u'This mod has an associated archive (%s' +
                       bush.game.Bsa.bsa_extension + u') and an '
        u'associated plugin-name-specific directory (e.g. Sound\\Voice\\%s),'
        u' which will become detached when the mod is renamed.') + u'\n\n' + \
        _(u'Note that the BSA archive may also contain a plugin-name-specific '
        u'directory, which would remain detached even if the archive name is '
        u'adjusted.')
    bsa = _(u'This mod has an associated archive (%s' +
            bush.game.Bsa.bsa_extension + u'), which will become '
        u'detached when the mod is renamed.') + u'\n\n' + _(u'Note that this '
        u'BSA archive may contain a plugin-name-specific directory (e.g. '
        u'Sound\\Voice\\%s), which would remain detached even if the archive '
        u'file name is adjusted.')
    blocking = _(u'This mod has an associated plugin-name-specific directory, '
        u'(e.g. Sound\\Voice\\%s) which will become detached when the mod is '
        u'renamed.')

    def _askResourcesOk(self, fileInfo):
        msg = bosh.modInfos.askResourcesOk(fileInfo,
                                           bsaAndBlocking=self.bsaAndBlocking,
                                           bsa=self.bsa,blocking=self.blocking)
        if not msg: return True # resources ok
        return balt.askWarning(self, msg, _(u'Rename ') + fileInfo.name.s)

    def testChanges(self): # used by the master list when editing is disabled
        modInfo = self.modInfo
        if not modInfo or (self.fileStr == modInfo.name and
                           self.modifiedStr == format_date(modInfo.mtime) and
                           self.authorStr == modInfo.header.author and
                           self.descriptionStr == modInfo.header.description):
            self.DoCancel()

    def DoSave(self):
        modInfo = self.modInfo
        #--Change Tests
        changeName = (self.fileStr != modInfo.name)
        changeDate = (self.modifiedStr != format_date(modInfo.mtime))
        changeHedr = (self.authorStr != modInfo.header.author or
                      self.descriptionStr != modInfo.header.description)
        changeMasters = self.uilist.edited
        #--Warn on rename if file has BSA and/or dialog
        if changeName and not self._askResourcesOk(modInfo): return
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
            oldName,newName = modInfo.name,GPath(self.fileStr.strip())
            #--Bad name?
            if (bosh.modInfos.isBadFileName(newName.s) and
                not balt.askContinue(self,_(
                    u'File name %s cannot be encoded to ASCII.  %s may not be '
                    u'able to activate this plugin because of this.  Do you '
                    u'want to rename the plugin anyway?')
                                     % (newName.s,bush.game.displayName),
                                     'bash.rename.isBadFileName.continue')
                ):
                return
            settings.getChanged('bash.mods.renames')[oldName] = newName
            try:
                bosh.modInfos.rename_info(oldName, newName)
            except (CancelError, OSError, IOError):
                pass
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
        else: detail_item = self.file_info.name
        #--Done
        with load_order.Unlock():
            bosh.modInfos.refresh(refresh_infos=False, _modTimesChange=changeDate)
        refreshSaves = detail_item is None or changeName or (
            changeDate and not load_order.using_txt_file())
        self.panel_uilist.RefreshUI(refreshSaves=refreshSaves,
                                    detail_item=detail_item)

    def _set_date(self, modInfo):
        newTimeTup = unformat_date(self.modifiedStr, '%c')
        newTimeInt = int(time.mktime(newTimeTup))
        modInfo.setmtime(newTimeInt)

    #--Bash Tags
    def ShowBashTagsMenu(self):
        """Show bash tags menu."""
        # Note that we have to return EventResult.FINISH, otherwise the default
        # text menu will get shown after a tag is applied.
        if not self.modInfo: return EventResult.FINISH
        #--Links closure
        mod_info = self.modInfo
        mod_tags = mod_info.getBashTags()
        is_auto = bosh.modInfos.table.getItem(mod_info.name, 'autoBashTags',
                                              True)
        def _refreshUI(): self.panel_uilist.RefreshUI(redraw=[mod_info.name],
                refreshSaves=False) # why refresh saves when updating tags (?)
        def _isAuto():
            return bosh.modInfos.table.getItem(mod_info.name, 'autoBashTags')
        def _setAuto(to):
            bosh.modInfos.table.setItem(mod_info.name, 'autoBashTags', to)
        # Toggle auto Bash tags
        class _TagsAuto(CheckLink):
            _text = _(u'Automatic')
            _help = _(
                u"Use the tags from the description and masterlist/userlist.")
            def _check(self): return is_auto
            def Execute(self):
                """Handle selection of automatic bash tags."""
                _setAuto(not _isAuto()) # toggle
                if _isAuto(): mod_info.reloadBashTags()
                _refreshUI()
        # Copy tags to various places
        bashTagsDesc = mod_info.getBashTagsDesc()
        class _CopyBashTagsDir(EnabledLink):
            _text = _(u'Copy to Data/BashTags')
            _help = _(u'Copies currently applied tags to %s.') % (
                bass.dirs['tag_files'].join(mod_info.name.body + u'.txt'))
            def _enable(self): return not is_auto and mod_tags != bashTagsDesc
            def Execute(self):
                """Copy manually assigned bash tags into the Data/BashTags
                folder."""
                # We need to grab both the ones from the description and from
                # LOOT, since we need to save a diff
                plugin_name = mod_info.name
                added, removed = bosh.configHelpers.getTagsInfoCache(
                    plugin_name)
                # Emulate the effects of applying the LOOT tags
                old_tags = bashTagsDesc.copy()
                old_tags |= added
                old_tags -= removed
                bosh.configHelpers.save_tags_to_dir(plugin_name, mod_tags,
                                                    old_tags)
                _refreshUI()
        class _CopyDesc(EnabledLink):
            _text = _(u'Copy to Description')
            _help = _(u'Copies currently applied tags to the mod description.')
            def _enable(self): return not is_auto and mod_tags != bashTagsDesc
            def Execute(self):
                """Copy manually assigned bash tags into the mod description"""
                if mod_info.setBashTagsDesc(mod_tags):
                    _refreshUI()
                else:
                    thinSplitterWin = self.window.GetParent().GetParent(
                        ).GetParent().GetParent()
                    balt.showError(thinSplitterWin,
                        _(u'Description field including the Bash Tags must be '
                          u'at most 511 characters. Edit the description to '
                          u'leave enough room.'))
        # Tags links
        class _TagLink(CheckLink):
            @property
            def menu_help(self):
                return _(u"Add %(tag)s to %(modname)s") % (
                    {'tag': self._text, 'modname': mod_info.name})
            def _check(self): return self._text in mod_tags
            def Execute(self):
                """Toggle bash tag from menu."""
                if _isAuto(): _setAuto(False)
                modTags = mod_tags ^ {self._text}
                mod_info.setBashTags(modTags)
                _refreshUI()
        # Menu
        class _TagLinks(ChoiceLink):
            choiceLinkType = _TagLink
            def __init__(self):
                super(_TagLinks, self).__init__()
                self.extraItems = [_TagsAuto(), _CopyBashTagsDir(),
                                   _CopyDesc(), SeparatorLink()]
            @property
            def _choices(self): return sorted(bush.game.allTags)
        ##: Popup the menu - ChoiceLink should really be a Links subclass
        tagLinks = Links()
        tagLinks.append(_TagLinks())
        tagLinks.new_menu(self.gTags, None)
        return EventResult.FINISH

#------------------------------------------------------------------------------
class INIDetailsPanel(_DetailsMixin, SashPanel):
    keyPrefix = 'bash.ini.details'

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
        self.lastDir = settings.get('bash.ini.lastDir', bass.dirs['mods'].s)
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

    # Read only wrappers around bass.settings['bash.ini.choices']
    @property
    def current_ini_path(self):
        """Return path of currently chosen ini."""
        return self.target_inis.values()[settings['bash.ini.choice']]

    @property
    def target_inis(self):
        """Return settings['bash.ini.choices'], set in IniInfos#__init__.
        :rtype: OrderedDict[unicode, bolt.Path]"""
        return settings['bash.ini.choices']

    @property
    def _ini_keys(self): return settings['bash.ini.choices'].keys()

    @property
    def ini_name(self): return self._ini_keys[settings['bash.ini.choice']]

    def _resetDetails(self): pass

    def SetFile(self, fileName='SAME'):
        fileName = super(INIDetailsPanel, self).SetFile(fileName)
        self._ini_detail = fileName
        self.tweakContents.RefreshTweakLineCtrl(fileName)
        self.tweakName.text_content = fileName.sbody if fileName else u''

    def _enable_buttons(self):
        isGameIni = bosh.iniInfos.ini in bosh.gameInis
        self.removeButton.enabled = not isGameIni
        self.editButton.enabled = not isGameIni or self.current_ini_path.isfile()

    def _OnRemove(self):
        """Called when the 'Remove' button is pressed."""
        self.__remove(self.ini_name)
        self._combo_reset()
        self.ShowPanel(target_changed=True)
        self._ini_panel.uiList.RefreshUI()

    def _combo_reset(self): self._inis_combo_box.set_choices(self._ini_keys)

    def _clean_targets(self):
        for ini_fname, ini_path in self.target_inis.iteritems():
            if ini_path is not None and not ini_path.isfile():
                if not bosh.get_game_ini(ini_path):
                    self.__remove(ini_fname)
        self._combo_reset()

    def __remove(self, ini_str_name): # does NOT change sorting
        del self.target_inis[ini_str_name]
        settings['bash.ini.choice'] -= 1

    def set_choice(self, ini_str_name, reset_choices=True):
        if reset_choices: self._combo_reset()
        settings['bash.ini.choice'] = self._ini_keys.index(ini_str_name)

    def _on_select_drop_down(self, selection):
        """Called when the user selects a new target INI from the drop down."""
        full_path = self.target_inis[selection]
        if full_path is None:
            # 'Browse...'
            wildcard =  u'|'.join(
                [_(u'Supported files') + u' (*.ini,*.cfg)|*.ini;*.cfg',
                 _(u'INI files') + u' (*.ini)|*.ini',
                 _(u'Config files') + u' (*.cfg)|*.cfg', ])
            full_path = balt.askOpen(self, defaultDir=self.lastDir,
                                     wildcard=wildcard, mustExist=True)
            if full_path: self.lastDir = full_path.shead
            if not full_path or ( # reselected the current target ini
                full_path.stail in self.target_inis and settings[
                  'bash.ini.choice'] == self._ini_keys.index(full_path.stail)):
                self._inis_combo_box.set_selection(settings['bash.ini.choice'])
                return
        # new file or selected an existing one different from current choice
        self.set_choice(full_path.stail, bool(bosh.INIInfos.update_targets(
            {full_path.stail: full_path}))) # reset choices if ini was added
        self.ShowPanel(target_changed=True)
        self._ini_panel.uiList.RefreshUI()

    def ShowPanel(self, target_changed=False, clean_targets=False, **kwargs):
        if self._firstShow:
            super(INIDetailsPanel, self).ShowPanel(**kwargs)
            target_changed = True # to display the target ini
        new_target = bosh.iniInfos.ini.abs_path != self.current_ini_path
        if new_target:
            bosh.iniInfos.ini = self.current_ini_path
        self._enable_buttons() # if a game ini was deleted will disable edit
        if clean_targets: self._clean_targets()
        # first RefreshIniContents as RefreshTweakLineCtrl needs its lines
        if new_target or target_changed:
            self.iniContents.RefreshIniContents(new_target)
            Link.Frame.warn_game_ini()
        self._inis_combo_box.set_selection(settings['bash.ini.choice'])

    def ClosePanel(self, destroy=False):
        super(INIDetailsPanel, self).ClosePanel(destroy)
        settings['bash.ini.lastDir'] = self.lastDir
        if destroy: self._inis_combo_box.unsubscribe_handler_()

class INIPanel(BashTab):
    keyPrefix = 'bash.ini'
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
                  clean_targets=False, focus_list=True, detail_item='SAME',
                  **kwargs):
        changes = bosh.iniInfos.refresh(refresh_infos=refresh_infos,
                                        refresh_target=refresh_target)
        super(INIPanel, self).ShowPanel(target_changed=changes and changes[3],
                                        clean_targets=clean_targets)
        if changes: # we need this to be more granular
            self.uiList.RefreshUI(focus_list=focus_list,
                                  detail_item=detail_item)

    def _sbCount(self):
        stati = self.uiList.CountTweakStatus()
        return _(u'Tweaks:') + u' %d/%d' % (stati[0], sum(stati[:-1]))

#------------------------------------------------------------------------------
class ModPanel(BashTab):
    keyPrefix = 'bash.mods'
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
    mainMenu = Links() #--Column menu
    itemMenu = Links() #--Single item menu
    _editLabels = True
    _sort_keys = {
        'File'    : None, # just sort by name
        'Modified': lambda self, a: self.data_store[a].mtime,
        'Size'    : lambda self, a: self.data_store[a].size,
        'PlayTime': lambda self, a: self.data_store[a].header.gameTicks,
        'Player'  : lambda self, a: self.data_store[a].header.pcName,
        'Cell'    : lambda self, a: self.data_store[a].header.pcLocation,
        'Status'  : lambda self, a: self.data_store[a].getStatus(),
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
        ('File',     lambda self, p: p.s),
        ('Modified', lambda self, p: format_date(self.data_store[p].mtime)),
        ('Size',     lambda self, p: round_size(self.data_store[p].size)),
        ('PlayTime', lambda self, p: self._playTime(self.data_store[p])),
        ('Player',   lambda self, p: self._headInfo(self.data_store[p],
                                                    'pcName')),
        ('Cell',     lambda self, p: self._headInfo(self.data_store[p],
                                                    'pcLocation')),
    ])

    __ext_group = u'(\.(' + bush.game.Ess.ext[1:] + u'|' + \
                  bush.game.Ess.ext[1:-1] + u'r' + u'))' # add bak !!!
    def validate_filename(self, name_new, has_digits=False, ext=u'',
            is_filename=True, _old_path=None):
        if _old_path and bosh.bak_file_pattern.match(_old_path.s): ##: YAK add cosave support for bak
            balt.showError(self, _(u'Renaming bak files is not supported.'))
            return None, None, None ##: this used to not-Skip now it Vetoes
        return super(SaveList, self).validate_filename(name_new,
            has_digits=has_digits, ext=self.__ext_group,
            is_filename=is_filename)

    def OnLabelEdited(self, is_edit_cancelled, evt_label, evt_index, evt_item):
        """Savegame renamed."""
        if is_edit_cancelled: return EventResult.FINISH # todo CANCEL?
        root, newName, _numStr = self.validate_filename(evt_label)
        if not root: return EventResult.CANCEL # validate_filename would Veto
        item_edited = [self.panel.detailsPanel.displayed_item]
        selected = [s for s in self.GetSelected() if
                    not bosh.bak_file_pattern.match(s.s)] # YAK !
        to_select = set()
        to_del = set()
        for save_key in selected:
            newFileName = self.new_name(newName)
            if not self._try_rename(save_key, newFileName, to_select,
                                    item_edited): break
            to_del.add(save_key)
        if to_select:
            self.RefreshUI(redraw=to_select, to_del=to_del, # to_add
                           detail_item=item_edited[0])
            #--Reselect the renamed items
            self.SelectItemsNoCallback(to_select)
        return EventResult.CANCEL # needed ! clears new name from label on exception

    @staticmethod
    def _unhide_wildcard():
        starred = u'*' + bush.game.Ess.ext
        return bush.game.displayName + u' ' + _(
            u'Save files') + u' (' + starred + u')|' + starred

    #--Populate Item
    def set_item_format(self, fileName, item_format):
        save_info = self.data_store[fileName]
        #--Image
        status = save_info.getStatus()
        on = bosh.SaveInfos.is_save_enabled(save_info.getPath()) # yak
        item_format.icon_key = status, on

    #--Events ---------------------------------------------
    def _handle_key_up(self, wrapped_evt, g_list):
        code = wrapped_evt.key_code
        # Ctrl+C: Copy file(s) to clipboard
        if wrapped_evt.is_cmd_down and code == ord(u'C'):
            sel = map(lambda save: self.data_store[save].getPath().s,
                      self.GetSelected())
            balt.copyListToClipboard(sel)
        super(SaveList, self)._handle_key_up(wrapped_evt, g_list)

    def _handle_left_down(self, wrapped_evt, lb_dex_and_flags):
        #--Pass Event onward
        hitItem = self._getItemClicked(lb_dex_and_flags, on_icon=True)
        if not hitItem: return
        msg = _(u"Clicking on a save icon will disable/enable the save "
                u"by changing its extension to %(ess)s (enabled) or .esr "
                u"(disabled). Autosaves and quicksaves will be left alone."
                % {'ess': bush.game.Ess.ext})
        if not balt.askContinue(self, msg, 'bash.saves.askDisable.continue'):
            return
        newEnabled = not bosh.SaveInfos.is_save_enabled(hitItem)
        newName = self.data_store.enable(hitItem, newEnabled)
        if newName != hitItem: self.RefreshUI(redraw=[newName],
                                              to_del=[hitItem])

    # Save profiles
    def set_local_save(self, new_saves, refreshSaveInfos):
        if not INIList.ask_create_target_ini(bosh.oblivionIni, msg=_(
            u'Setting the save profile is done by editing the game ini.')):
            return
        self.data_store.setLocalSave(new_saves, refreshSaveInfos)
        balt.Link.Frame.set_bash_frame_title()

#------------------------------------------------------------------------------
class SaveDetails(_ModsSavesDetails):
    """Savefile details panel."""
    keyPrefix = 'bash.saves.details' # used in sash/scroll position, sorting

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
            background=colors['screens.bkgd.image']) #--Native: 256x192
        #--Save Info
        self.gInfo = TextArea(self._bottom_low_panel, max_length=2048)
        self.gInfo.on_text_changed.subscribe(self.OnInfoEdit)
        # TODO(nycz): GUI set_size size=(textWidth, 64)
        #--Layouts
        VLayout(item_expand=True, items=[
            self._fname_ctrl,
            HLayout(item_expand=True, items=[
                (self.playerInfo, LayoutOptions(weight=1)), self.gCoSaves]),
            (self.picture, LayoutOptions(weight=1))
        ]).apply_to(top)
        VLayout(items=[Label(self._bottom_low_panel, _(u"Save Notes:")),
            (self.gInfo, LayoutOptions(expand=True, weight=1))]
                ).apply_to(self._bottom_low_panel)

    def _resetDetails(self):
        self.saveInfo = None
        self.fileStr = u''
        self.playerNameStr = u''
        self.curCellStr = u''
        self.playerLevel = 0
        self.gameDays = 0
        self.playMinutes = 0
        self.coSaves = u'--\n--'

    def SetFile(self,fileName='SAME'):
        fileName = super(SaveDetails, self).SetFile(fileName)
        if fileName:
            saveInfo = self.saveInfo = bosh.saveInfos[fileName]
            #--Remember values for edit checks
            self.fileStr = saveInfo.name.s
            self.playerNameStr = saveInfo.header.pcName
            self.curCellStr = saveInfo.header.pcLocation
            self.gameDays = saveInfo.header.gameDays
            self.playMinutes = saveInfo.header.gameTicks//60000
            self.playerLevel = saveInfo.header.pcLevel
            self.coSaves = saveInfo.get_cosave_tags()
        #--Set Fields
        self._fname_ctrl.text_content = self.fileStr
        self._set_player_info_label()
        self.gCoSaves.label_text = self.coSaves
        self.uilist.SetFileInfo(self.saveInfo)
        #--Picture
        image_tuple = self.saveInfo.header.image if self.saveInfo else None
        self.picture.set_bitmap(image_tuple)
        #--Info Box
        self.gInfo.modified = False
        note_text = bosh.saveInfos.table.getItem(fileName, 'info',
                                                 u'') if fileName else u''
        self.gInfo.text_content = note_text

    def _set_player_info_label(self):
        self.playerInfo.label_text = (self.playerNameStr + u'\n' +
            _(u'Level') + u' %d, ' + _(u'Day') + u' %d, ' +
            _(u'Play') + u' %d:%02d\n%s') % (
            self.playerLevel, int(self.gameDays), self.playMinutes // 60,
            (self.playMinutes % 60), self.curCellStr)

    def OnInfoEdit(self, new_text):
        """Info field was edited."""
        if self.saveInfo and self.gInfo.modified:
            bosh.saveInfos.table.setItem(self.saveInfo.name, 'info', new_text)

    def _validate_filename(self, fileStr):
        return self.panel_uilist.validate_filename(fileStr,
            _old_path=self.saveInfo.name)[0]

    def testChanges(self): # used by the master list when editing is disabled
        saveInfo = self.saveInfo
        if not saveInfo or self.fileStr == saveInfo.name:
            self.DoCancel()

    def DoSave(self):
        """Event: Clicked Save button."""
        saveInfo = self.saveInfo
        #--Change Tests
        changeName = (self.fileStr != saveInfo.name)
        changeMasters = self.uilist.edited
        #--Backup
        saveInfo.makeBackup() ##: why backup when just renaming - #292
        prevMTime = saveInfo.mtime
        #--Change Name?
        to_del = []
        if changeName:
            (oldName,newName) = (saveInfo.name,GPath(self.fileStr.strip()))
            try:
                bosh.saveInfos.rename_info(oldName, newName)
                to_del = [oldName]
            except (CancelError, OSError, IOError):
                pass
        #--Change masters?
        if changeMasters:
            saveInfo.header.masters = self.uilist.GetNewMasters()
            saveInfo.write_masters()
            saveInfo.setmtime(prevMTime)
            detail_item = self._refresh_detail_info()
        else: detail_item = self.file_info.name
        kwargs = dict(to_del=to_del, detail_item=detail_item)
        if detail_item is None:
            kwargs['to_del'] = to_del + [self.file_info.name]
        else:
            kwargs['redraw'] = [detail_item]
        self.panel_uilist.RefreshUI(**kwargs)

    def RefreshUIColors(self):
        self.picture.SetBackground(colors['screens.bkgd.image'])

#------------------------------------------------------------------------------
class SavePanel(BashTab):
    """Savegames tab."""
    keyPrefix = 'bash.saves'
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
    mainMenu = Links()
    itemMenu = Links()
    icons = installercons
    _sunkenBorder = False
    _shellUI = True
    _editLabels = True
    _default_sort_col = 'Package'
    _sort_keys = {
        'Package' : None,
        'Order'   : lambda self, x: self.data_store[x].order,
        'Modified': lambda self, x: self.data_store[x].modified,
        'Size'    : lambda self, x: self.data_store[x].size,
        'Files'   : lambda self, x: self.data_store[x].num_of_files,
    }
    #--Special sorters
    def _sortStructure(self, items):
        if settings['bash.installers.sortStructure']:
            items.sort(key=lambda self, x: self.data_store[x].type)
    def _sortActive(self, items):
        if settings['bash.installers.sortActive']:
            items.sort(key=lambda x: not self.data_store[x].is_active)
    def _sortProjects(self, items):
        if settings['bash.installers.sortProjects']:
            items.sort(key=lambda x: not isinstance(self.data_store[x],
                                                    bosh.InstallerProject))
    _extra_sortings = [_sortStructure, _sortActive, _sortProjects]
    #--Labels
    labels = OrderedDict([
        ('Package',  lambda self, p: p.s),
        ('Order',    lambda self, p: unicode(self.data_store[p].order)),
        ('Modified', lambda self, p: format_date(self.data_store[p].modified)),
        ('Size',     lambda self, p: self.data_store[p].size_string()),
        ('Files',    lambda self, p: self.data_store[p].number_string(
            self.data_store[p].num_of_files)),
    ])
    #--DnD
    _dndList, _dndFiles, _dndColumns = True, True, ['Order']
    #--GUI
    _status_color = {-20: 'grey', -10: 'red', 0: 'white', 10: 'orange',
                     20: 'yellow', 30: 'green'}
    _type_textKey = {1: 'default.text', 2: 'installers.text.complex'}

    #--Item Info
    def set_item_format(self, item, item_format):
        installer = self.data_store[item]
        #--Text
        if installer.type == 2 and len(installer.subNames) == 2:
            item_format.text_key = self._type_textKey[1]
        elif isinstance(installer, bosh.InstallerMarker):
            item_format.text_key = 'installers.text.marker'
        else: item_format.text_key = self._type_textKey.get(installer.type,
                                             'installers.text.invalid')
        #--Background
        if installer.skipDirFiles:
            item_format.back_key = 'installers.bkgd.skipped'
        mouse_text = u''
        if installer.dirty_sizeCrc:
            item_format.back_key = 'installers.bkgd.dirty'
            mouse_text += _(u'Needs Annealing due to a change in configuration.')
        elif installer.underrides:
            item_format.back_key = 'installers.bkgd.outOfOrder'
            mouse_text += _(u'Needs Annealing due to a change in Install Order.')
        #--Icon
        item_format.icon_key = 'on' if installer.is_active else 'off'
        item_format.icon_key += '.' + self._status_color[installer.status]
        if installer.type < 0: item_format.icon_key = 'corrupt'
        elif isinstance(installer, bosh.InstallerProject): item_format.icon_key += '.dir'
        if settings['bash.installers.wizardOverlay'] and installer.hasWizard:
            item_format.icon_key += '.wiz'
        #if textKey == 'installers.text.invalid': # I need a 'text.markers'
        #    text += _(u'Marker Package. Use for grouping installers together')
        #--TODO: add mouse  mouse tips
        self.mouseTexts[item] = mouse_text

    def OnBeginEditLabel(self, evt_label, uilist_ctrl):
        """Start renaming installers"""
        to_rename = self.GetSelected()
        #--Only rename multiple items of the same type
        renaming_type = type(self.data_store[to_rename[0]])
        last_marker = GPath(u'==Last==')
        for item in to_rename:
            if not isinstance(self.data_store[item], renaming_type):
                balt.showError(self, _(
                    u"Bash can't rename mixed installers types"))
                return EventResult.CANCEL
            #--Also, don't allow renaming the 'Last' marker
            elif item == last_marker:
                return EventResult.CANCEL
        uilist_ctrl.ec_set_on_char_handler(self._OnEditLabelChar)
        #--Markers, change the selection to not include the '=='
        if renaming_type is bosh.InstallerMarker:
            to = len(evt_label) - 2
            uilist_ctrl.ec_set_selection(2, to)
        #--Archives, change the selection to not include the extension
        elif renaming_type is bosh.InstallerArchive:
            return super(InstallersList, self).OnBeginEditLabel(evt_label,
                                                                uilist_ctrl)
        return EventResult.FINISH  ##: needed?

    def _OnEditLabelChar(self, is_f2_down, ec_value, uilist_ctrl):
        """For pressing F2 on the edit box for renaming"""
        if is_f2_down:
            to_rename = self.GetSelected()
            renaming_type = type(self.data_store[to_rename[0]])
            # (start, stop), if start==stop there is no selection
            selection_span = uilist_ctrl.ec_get_selection()
            lenWithExt = len(ec_value)
            if selection_span[0] != 0:
                selection_span = (0,lenWithExt)
            selectedText = GPath(ec_value[selection_span[0]:selection_span[1]])
            textNextLower = selectedText.body
            if textNextLower == selectedText:
                lenNextLower = lenWithExt
            else:
                lenNextLower = len(textNextLower.s)
            if renaming_type is bosh.InstallerArchive:
                selection_span = (0, lenNextLower)
            elif renaming_type is bosh.InstallerMarker:
                selection_span = (2, lenWithExt - 2)
            else:
                selection_span = (0, lenWithExt)
            uilist_ctrl.ec_set_selection(*selection_span)
            return EventResult.FINISH  ##: needed?

    __ext_group = \
        r'(\.(' + u'|'.join(ext[1:] for ext in archives.readExts) + u')+)'
    def OnLabelEdited(self, is_edit_cancelled, evt_label, evt_index, evt_item):
        """Renamed some installers"""
        if is_edit_cancelled: return EventResult.FINISH ##: previous behavior todo TTT
        selected = self.GetSelected()
        renaming_type = type(self.data_store[selected[0]])
        installables = self.data_store.filterInstallables(selected)
        validate = partial(self.validate_filename, evt_label,
                           is_filename=bool(installables))
        if renaming_type is bosh.InstallerArchive:
            root, newName, _numStr = validate(ext=self.__ext_group)
        else:
            root, newName, _numStr = validate()
        if not root: return EventResult.CANCEL
        #--Rename each installer, keeping the old extension (for archives)
        with balt.BusyCursor():
            refreshes, ex = [(False, False, False)], None
            newselected = []
            try:
                for package in selected:
                    name_new = self.new_name(newName)
                    refreshes.append(
                        self.data_store.rename_info(package, name_new))
                    if refreshes[-1][0]: newselected.append(name_new)
            except (CancelError, OSError, IOError) as ex:
                pass
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

    def new_name(self, new_name):
        new_name = GPath(new_name)
        to_rename = self.GetSelected()
        renaming_type = to_rename and type(self.data_store[to_rename[0]])
        if renaming_type is bosh.InstallerMarker:
            new_name, count = GPath(u'==' + new_name.s.strip(u'=') + u'=='), 0
            while new_name in self.data_store:
                count += 1
                new_name = GPath(u'==' + new_name.s.strip(u'=') + (
                    u' (%d)' % count) + u'==')
            return GPath(u'==' + new_name.s.strip(u'=') + u'==')
        return super(InstallersList, self).new_name(new_name)

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
        self.data_store.irefresh(what='N')
        self.RefreshUI()

    def _extractOmods(self, omodnames, progress):
        failed = []
        completed = []
        progress.setFull(len(omodnames))
        try:
            for i, omod in enumerate(omodnames):
                progress(i, omod.stail)
                outDir = bass.dirs['installers'].join(omod.body)
                if outDir.exists():
                    if balt.askYes(progress.dialog, _(
                        u"The project '%s' already exists.  Overwrite "
                        u"with '%s'?") % (omod.sbody, omod.stail)):
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
                    deprint(
                        _(u"Failed to extract '%s'.") % omod.stail + u'\n\n',
                        traceback=True)
                    failed.append(omod.stail)
        except CancelError:
            skipped = set(omodnames) - set(completed)
            msg = u''
            if completed:
                completed = [u' * ' + x.stail for x in completed]
                msg += _(u'The following OMODs were unpacked:') + \
                       u'\n%s\n\n' % u'\n'.join(completed)
            if skipped:
                skipped = [u' * ' + x.stail for x in skipped]
                msg += _(u'The following OMODs were skipped:') + \
                       u'\n%s\n\n' % u'\n'.join(skipped)
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
            self.data_store.irefresh(what='I')
            self.RefreshUI()

    def _askCopyOrMove(self, filenames):
        action = settings['bash.installers.onDropFiles.action']
        if action not in ['COPY','MOVE']:
            if len(filenames):
                message = _(u'You have dragged the following files into Wrye '
                            u'Bash:') + u'\n\n * '
                message += u'\n * '.join(f.s for f in filenames) + u'\n'
            else: message = _(u'You have dragged some converters into Wrye '
                            u'Bash.')
            message += u'\n' + _(u'What would you like to do with them?')
            with DialogWindow(self, _(u'Move or Copy?'),
                              sizes_dict=balt.sizes) as dialog:
                gCheckBox = CheckBox(dialog,
                                     _(u"Don't show this in the future."))
                move_button = Button(dialog, label=_(u'Move'))
                move_button.on_clicked.subscribe(lambda: dialog.exit_modal(1))
                copy_button = Button(dialog, label=_(u'Copy'))
                copy_button.on_clicked.subscribe(lambda: dialog.exit_modal(2))
                VLayout(border=6, spacing=6, items=[
                    HLayout(spacing=6, item_border=6, items=[
                        (staticBitmap(dialog), LayoutOptions(v_align=TOP)),
                        (Label(dialog, message), LayoutOptions(expand=True))
                    ]),
                    Stretch(), Spacer(10), gCheckBox,
                    (HLayout(spacing=4, items=[
                        move_button, copy_button, CancelButton(dialog)
                    ]), LayoutOptions(h_align=RIGHT))
                ]).apply_to(dialog)
                result = dialog.show_modal_raw() # buttons call exit_modal(1/2)
                if result == 1: action = 'MOVE'
                elif result == 2: action = 'COPY'
                if gCheckBox.is_checked:
                    settings['bash.installers.onDropFiles.action'] = action
        return action

    @balt.conversation
    def OnDropFiles(self, x, y, filenames):
        filenames = [GPath(x) for x in filenames]
        omodnames = [x for x in filenames if
                     not x.isdir() and x.cext == u'.omod']
        converters = [x for x in filenames if
                      bosh.converters.ConvertersData.validConverterName(x)]
        filenames = [x for x in filenames if x.isdir()
                     or x.cext in archives.readExts and x not in converters]
        if len(omodnames) > 0:
            with balt.Progress(_(u'Extracting OMODs...'), u'\n' + u' ' * 60,
                                 abort=True) as prog:
                self._extractOmods(omodnames, prog)
        if not filenames and not converters:
            return
        action = self._askCopyOrMove(filenames)
        if action not in ['COPY','MOVE']: return
        with balt.BusyCursor():
            installersJoin = bass.dirs['installers'].join
            convertersJoin = bass.dirs['converters'].join
            filesTo = [installersJoin(x.tail) for x in filenames]
            filesTo.extend(convertersJoin(x.tail) for x in converters)
            filenames.extend(converters)
            try:
                if action == 'MOVE':
                    #--Move the dropped files
                    env.shellMove(filenames, filesTo, parent=self)
                else:
                    #--Copy the dropped files
                    env.shellCopy(filenames, filesTo, parent=self)
            except (CancelError,SkipError):
                pass
        self.panel.frameActivated = True
        self.panel.ShowPanel()

    def dndAllow(self, event):
        if not self.sort_column in self._dndColumns:
            msg = _(u"Drag and drop in the Installer's list is only allowed "
                    u"when the list is sorted by install order")
            balt.askContinue(self, msg, 'bash.installers.dnd.column.continue')
            return super(InstallersList, self).dndAllow(event) # disallow
        return True

    def OnChar(self, wrapped_evt):
        """Char event: Reorder."""
        code = wrapped_evt.key_code
        ##Ctrl+Up/Ctrl+Down - Move installer up/down install order
        if wrapped_evt.is_cmd_down and code in balt.wxArrows:
            selected = self.GetSelected()
            if len(selected) < 1: return
            orderKey = partial(self._sort_keys['Order'], self)
            moveMod = 1 if code in balt.wxArrowDown else -1 # move down or up
            sorted_ = sorted(selected, key=orderKey, reverse=(moveMod == 1))
            # get the index two positions after the last or before the first
            visibleIndex = self.GetIndex(sorted_[0]) + moveMod * 2
            maxPos = max(x.order for x in self.data_store.values())
            for thisFile in sorted_:
                newPos = self.data_store[thisFile].order + moveMod
                if newPos < 0 or maxPos < newPos: break
                self.data_store.moveArchives([thisFile], newPos)
            self.data_store.irefresh(what='N')
            self.RefreshUI()
            visibleIndex = sorted([visibleIndex, 0, maxPos])[1]
            self.EnsureVisibleIndex(visibleIndex)
        elif wrapped_evt.is_cmd_down and code == ord('V'):
            ##Ctrl+V
            balt.clipboardDropFiles(10, self.OnDropFiles)
        # Enter: Open selected installers
        elif code in balt.wxReturn: self.OpenSelected()
        else:
            return EventResult.CONTINUE
        return EventResult.FINISH

    def OnDClick(self, lb_dex_and_flags):
        """Double click, open the installer."""
        item = self._getItemClicked(lb_dex_and_flags)
        if not item: return
        if isinstance(self.data_store[item], bosh.InstallerMarker):
            # Double click on a Marker, select all items below
            # it in install order, up to the next Marker
            sorted_ = self._SortItems(col='Order', sortSpecial=False)
            new = []
            for nextItem in sorted_[self.data_store[item].order + 1:]:
                installer = self.data_store[nextItem]
                if isinstance(installer,bosh.InstallerMarker):
                    break
                new.append(nextItem)
            if new:
                self.SelectItemsNoCallback(new)
                self.SelectItem((new[-1])) # show details for the last one
        else:
            self.OpenSelected(selected=[item])

    def _handle_key_up(self, wrapped_evt, g_list):
        """Char events: Action depends on keys pressed"""
        code = wrapped_evt.key_code
        # Ctrl+Shift+N - Add a marker
        if wrapped_evt.is_cmd_down and wrapped_evt.is_shift_down and \
                code == ord(u'N'):
            self.addMarker()
        # Ctrl+C: Copy file(s) to clipboard
        elif wrapped_evt.is_cmd_down and code == ord(u'C'):
            sel = map(lambda x: bass.dirs['installers'].join(x).s,
                      self.GetSelected())
            balt.copyListToClipboard(sel)
        super(InstallersList, self)._handle_key_up(wrapped_evt, g_list)

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
        toRefresh = self.data_store.filterPackages(toRefresh)
        if not toRefresh: return
        try:
            with balt.Progress(_(u'Refreshing Packages...'), u'\n' + u' ' * 60,
                               abort=abort) as progress:
                progress.setFull(len(toRefresh))
                dest = set() # installer's destination paths rel to Data/
                for index, installer in enumerate(
                        self.data_store.sorted_values(toRefresh)):
                    progress(index, _(u'Refreshing Packages...') + u'\n' +
                             installer.archive)
                    if shallow:
                        op = installer.refreshDataSizeCrc
                    else:
                        op = partial(installer.refreshBasic,
                                     SubProgress(progress, index, index + 1),
                                     calculate_projects_crc)
                    dest.update(op().keys())
                self.data_store.hasChanged = True  # is it really needed ?
                if update_from_data:
                    progress(0, _(u'Refreshing From Data...') + u'\n' + u' ' * 60)
                    self.data_store.update_data_SizeCrcDate(dest, progress)
        except CancelError:  # User canceled the refresh
            if not abort: raise # I guess CancelError is raised on aborting
        self.data_store.irefresh(what='NS')
        self.RefreshUI()

#------------------------------------------------------------------------------
class InstallersDetails(_SashDetailsPanel):
    keyPrefix = 'bash.installers.details'
    defaultSashPos = - 32 # negative so it sets bottom panel's (comments) size
    minimumSize = 32 # so comments dont take too much space
    _ui_settings = {u'.checkListSplitterSashPos' : _UIsetting(lambda self: 0,
        lambda self: self.checkListSplitter.get_sash_pos(),
        lambda self, sashPos: self.checkListSplitter.set_sash_pos(sashPos))}
    _ui_settings.update(_SashDetailsPanel._ui_settings)

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
            first_pane=NotebookCtrl(self.subSplitter, multiline=True),
            second_pane=Splitter(self.subSplitter, min_pane_size=50,
                                 sash_gravity=0.5))
        self.gNotebook.set_min_size(100, 100)
        self.infoPages = []
        infoTitles = (
            ('gGeneral',_(u'General')),
            ('gMatched',_(u'Matched')),
            ('gMissing',_(u'Missing')),
            ('gMismatched',_(u'Mismatched')),
            ('gConflicts',_(u'Conflicts')),
            ('gUnderrides',_(u'Underridden')),
            ('gDirty',_(u'Dirty')),
            ('gSkipped',_(u'Skipped')),
            )
        for cmp_name, page_title in infoTitles:
            gPage = TextArea(self.gNotebook, editable=False,
                             auto_tooltip=False, do_wrap=False)
            gPage.component_name = cmp_name
            self.gNotebook.nb_add_page(gPage, page_title)
            self.infoPages.append([gPage,False])
        self.gNotebook.nb_set_selected_index(settings['bash.installers.page'])
        self.gNotebook.on_nb_page_change.subscribe(self.OnShowInfoPage)
        subPackagesPanel, espmsPanel = self.checkListSplitter.make_panes(
            vertically=True)
        #--Sub-Installers
        subPackagesLabel = Label(subPackagesPanel, _(u'Sub-Packages'))
        self.gSubList = CheckListBox(subPackagesPanel, isExtended=True,
                                     onCheck=self._check_subitem)
        self.gSubList.on_mouse_right_up.subscribe(self._sub_selection_menu)
        #--Espms
        self.espms = []
        self.gEspmList = CheckListBox(espmsPanel, isExtended=True,
                                      onCheck=self._on_check_plugin)
        self.gEspmList.on_mouse_left_dclick.subscribe(
            self._on_plugin_filter_dclick)
        self.gEspmList.on_mouse_right_up.subscribe(self._selection_menu)
        #--Comments
        self.gComments = TextArea(commentsPanel, auto_tooltip=False)
        #--Splitter settings
        commentsSplitter.set_min_pane_size(-self.__class__.defaultSashPos)
        commentsSplitter.set_sash_gravity(1.0)
        #--Layout
        VLayout(items=[subPackagesLabel,
                       (self.gSubList, LayoutOptions(expand=True, weight=1))]
                ).apply_to(subPackagesPanel)
        VLayout(items=[Label(espmsPanel, _(u'Plugin Filter')),
                       (self.gEspmList, LayoutOptions(expand=True, weight=1))]
                ).apply_to(espmsPanel)
        VLayout(item_expand=True, items=[self.gPackage, (
            self.subSplitter, LayoutOptions(weight=1))]).apply_to(top)
        VLayout(items=[Label(commentsPanel, _(u'Comments')),
                       (self.gComments, LayoutOptions(expand=True, weight=1))]
                ).apply_to(commentsPanel)
        VLayout(item_expand=True, item_weight=1, items=[commentsPanel]
                ).apply_to(bottom)

    def _get_sub_splitter(self):
        return Splitter(self.left, min_pane_size=50, sash_gravity=0.5)

    def OnShowInfoPage(self, wx_id, selected_index):
        """A specific info page has been selected."""
        if wx_id == self.gNotebook.wx_id_: # todo because of BashNotebook event??
            # todo use the pages directly not the index
            gPage,initialized = self.infoPages[selected_index]
            if self._displayed_installer and not initialized:
                self.RefreshInfoPage(selected_index, self.file_info)

    def ClosePanel(self, destroy=False):
        """Saves details if they need saving."""
        if not self._firstShow and destroy: # save subsplitters
            super(InstallersDetails, self).ClosePanel(destroy)
            settings['bash.installers.page'] = \
                self.gNotebook.nb_get_selected_index()
        self._save_comments()

    def _save_comments(self):
        installer = self.file_info
        if installer and self.gComments.modified:
            installer.comments = self.gComments.text_content
            self._idata.setChanged()

    def SetFile(self, fileName='SAME'):
        """Refreshes detail view associated with data from item."""
        if self._displayed_installer is not None:
            self._save_comments()
        fileName = super(InstallersDetails, self).SetFile(fileName)
        self._displayed_installer = fileName
        del self.espms[:]
        if fileName:
            installer = self._idata[fileName]
            #--Name
            self.gPackage.text_content = fileName.s
            #--Info Pages
            currentIndex = self.gNotebook.nb_get_selected_index()
            for index,(gPage,state) in enumerate(self.infoPages):
                self.infoPages[index][1] = False
                if index == currentIndex: self.RefreshInfoPage(index,installer)
                else: gPage.text_content = u''
            #--Sub-Packages
            self.gSubList.lb_clear()
            if len(installer.subNames) <= 2:
                self.gSubList.lb_clear()
            else:
                sub_names_ = [x.replace(u'&', u'&&') for x in
                              installer.subNames[1:]]
                vals = installer.subActives[1:]
                self.gSubList.setCheckListItems(sub_names_, vals)
            #--Espms
            if not installer.espms:
                self.gEspmList.lb_clear()
            else:
                names = self.espms = sorted(installer.espms)
                names.sort(key=lambda x: x.cext != u'.esm')
                names_ = [[u'', u'*'][installer.isEspmRenamed(x.s)] +
                          x.s.replace(u'&', u'&&') for x in names]
                vals = [x not in installer.espmNots for x in names]
                self.gEspmList.setCheckListItems(names_, vals)
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
        pageName = gPage.component_name
        def dumpFiles(files, header=u''):
            if files:
                buff = StringIO.StringIO()
                files = bolt.sortFiles(files)
                if header: buff.write(header+u'\n')
                for file in files:
                    oldName = installer.getEspmName(file)
                    buff.write(oldName)
                    if oldName != file:
                        buff.write(u' -> ')
                        buff.write(file)
                    buff.write(u'\n')
                return buff.getvalue()
            elif header:
                return header+u'\n'
            else:
                return u''
        if pageName == 'gGeneral':
            info = u'== '+_(u'Overview')+u'\n'
            info += _(u'Type: ') + installer.type_string + u'\n'
            info += installer.structure_string() + u'\n'
            nConfigured = len(installer.ci_dest_sizeCrc)
            nMissing = len(installer.missingFiles)
            nMismatched = len(installer.mismatchedFiles)
            if isinstance(installer,bosh.InstallerProject):
                info += _(u'Size:') + u' %s\n' % round_size(installer.size)
            elif isinstance(installer,bosh.InstallerMarker):
                info += _(u'Size:')+u' N/A\n'
            elif isinstance(installer,bosh.InstallerArchive):
                if installer.isSolid:
                    if installer.blockSize:
                        sSolid = _(u'Solid, Block Size: %d MB') % installer.blockSize
                    elif installer.blockSize is None:
                        sSolid = _(u'Solid, Block Size: Unknown')
                    else:
                        sSolid = _(u'Solid, Block Size: 7z Default')
                else:
                    sSolid = _(u'Non-solid')
                info += _(u'Size: %s (%s)') % (
                    round_size(installer.size), sSolid) + u'\n'
            else:
                info += _(u'Size: Unrecognized')+u'\n'
            info += (_(u'Modified:') +u' %s\n' % format_date(installer.modified),
                     _(u'Modified:') +u' N/A\n',)[isinstance(installer,bosh.InstallerMarker)]
            info += (_(u'Data CRC:')+u' %08X\n' % installer.crc,
                     _(u'Data CRC:')+u' N/A\n',)[isinstance(installer,bosh.InstallerMarker)]
            info += (_(u'Files:') + u' %s\n' % installer.number_string(
                installer.num_of_files, marker_string=u'N/A'))
            info += (_(u'Configured:')+u' %u (%s)\n' % (
                nConfigured, round_size(installer.unSize)),
                     _(u'Configured:')+u' N/A\n',)[isinstance(installer,bosh.InstallerMarker)]
            info += (_(u'  Matched:') + u' %s\n' % installer.number_string(
                nConfigured - nMissing - nMismatched, marker_string=u'N/A'))
            info += (_(u'  Missing:')+u' %s\n' % installer.number_string(
                nMissing, marker_string=u'N/A'))
            info += (_(u'  Conflicts:')+u' %s\n' % installer.number_string(
                nMismatched, marker_string=u'N/A'))
            info += '\n'
            #--Infoboxes
            gPage.text_content = info + dumpFiles(installer.ci_dest_sizeCrc,
                                          u'== ' + _(u'Configured Files'))
        elif pageName == 'gMatched':
            gPage.text_content = dumpFiles(set(
                installer.ci_dest_sizeCrc) - installer.missingFiles -
                                           installer.mismatchedFiles)
        elif pageName == 'gMissing':
            gPage.text_content = dumpFiles(installer.missingFiles)
        elif pageName == 'gMismatched':
            gPage.text_content = dumpFiles(installer.mismatchedFiles)
        elif pageName == 'gConflicts':
            gPage.text_content = self._idata.getConflictReport(
                installer, 'OVER', bosh.modInfos)
        elif pageName == 'gUnderrides':
            gPage.text_content = self._idata.getConflictReport(
                installer, 'UNDER', bosh.modInfos)
        elif pageName == 'gDirty':
            gPage.text_content = dumpFiles(installer.dirty_sizeCrc)
        elif pageName == 'gSkipped':
            gPage.text_content = u'\n'.join((dumpFiles(
                installer.skipExtFiles, u'== ' + _(u'Skipped (Extension)')),
                                             dumpFiles(
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
        if not balt.getKeyState_Shift():
            self.refreshCurrent(installer)

    def _selection_menu(self, lb_selection_dex):
        """Handle right click in espm list."""
        self.gEspmList.lb_select_index(lb_selection_dex)
        #--Show/Destroy Menu
        InstallersPanel.espmMenu.new_menu(self, lb_selection_dex)

    def _sub_selection_menu(self, lb_selection_dex):
        """Handle right click in espm list."""
        self.gSubList.lb_select_index(lb_selection_dex)
        #--Show/Destroy Menu
        InstallersPanel.subsMenu.new_menu(self, lb_selection_dex)

    def _on_check_plugin(self, lb_selection_dex):
        """Handle check/uncheck of item."""
        espmNots = self.file_info.espmNots
        plugin_name = self.gEspmList.lb_get_str_item_at_index(
            lb_selection_dex).replace('&&', '&')
        if plugin_name[0] == u'*':
            plugin_name = plugin_name[1:]
        espm = GPath(plugin_name)
        if self.gEspmList.lb_is_checked_at_index(lb_selection_dex):
            espmNots.discard(espm)
        else:
            espmNots.add(espm)
        self.gEspmList.lb_select_index(lb_selection_dex)    # so that (un)checking also selects (moves the highlight)
        if not balt.getKeyState_Shift():
            self.refreshCurrent(self.file_info)

    def _on_plugin_filter_dclick(self, selected_index):
        """Handles double-clicking on a plugin in the plugin filter."""
        if selected_index < 0: return
        selected_name = self.gEspmList.lb_get_str_item_at_index(
            selected_index).replace('&&', '&')
        if selected_name[0] == u'*': selected_name = selected_name[1:]
        selected_plugin = GPath(selected_name)
        if selected_plugin not in bosh.modInfos: return
        balt.Link.Frame.notebook.SelectPage('Mods', selected_plugin)

class InstallersPanel(BashTab):
    """Panel for InstallersTank."""
    espmMenu = Links()
    subsMenu = Links()
    keyPrefix = 'bash.installers'
    _ui_list_type = InstallersList
    _details_panel_type = InstallersDetails

    def __init__(self,parent):
        """Initialize."""
        BashFrame.iPanel = self
        self.listData = bosh.bain.InstallersData()
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
        if settings.get('bash.installers.isFirstRun',True):
            settings['bash.installers.isFirstRun'] = False
            message = _(u'Do you want to enable Installers?') + u'\n\n\t' + _(
                u'If you do, Bash will first need to initialize some data. '
                u'This can take on the order of five minutes if there are '
                u'many mods installed.') + u'\n\n\t' + _(
                u"If not, you can enable it at any time by right-clicking "
                u"the column header menu and selecting 'Enabled'.")
            settings['bash.installers.enabled'] = balt.askYes(self, message,
                                                              _(u'Installers'))

    @balt.conversation
    def ShowPanel(self, canCancel=True, fullRefresh=False, scan_data_dir=False,
                  **kwargs):
        """Panel is shown. Update self.data."""
        self._first_run_set_enabled() # must run _before_ if below
        if not settings['bash.installers.enabled'] or self.refreshing or self._user_cancelled:
            self._user_cancelled = False
            return
        try:
            self.refreshing = True
            self._refresh_installers_if_needed(canCancel, fullRefresh,
                                               scan_data_dir)
            super(InstallersPanel, self).ShowPanel()
        finally:
            self.refreshing = False

    @balt.conversation
    @bosh.bain.projects_walk_cache
    def _refresh_installers_if_needed(self, canCancel, fullRefresh,
                                      scan_data_dir):
        if settings.get('bash.installers.updatedCRCs',True): #only checked here
            settings['bash.installers.updatedCRCs'] = False
            self._data_dir_scanned = False
        installers_paths = bass.dirs[
            'installers'].list() if self.frameActivated else ()
        if self.frameActivated and omods.extractOmodsNeeded(installers_paths):
            self.__extractOmods()
        do_refresh = scan_data_dir = scan_data_dir or not self._data_dir_scanned
        if not do_refresh and self.frameActivated:
            refresh_info = self.listData.scan_installers_dir(installers_paths,
                                                             fullRefresh)
            do_refresh = refresh_info.refresh_needed()
        else: refresh_info = None
        refreshui = False
        if do_refresh:
            with balt.Progress(_(u'Refreshing Installers...'),
                               u'\n' + u' ' * 60, abort=canCancel) as progress:
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
        elif self.frameActivated and self.listData.refreshConvertersNeeded():
            with balt.Progress(_(u'Refreshing Converters...'),
                               u'\n' + u' ' * 60) as progress:
                try:
                    refreshui |= self.listData.irefresh(progress, 'C',
                                                        fullRefresh)
                    self.frameActivated = False
                except CancelError:
                    pass # User canceled the refresh
        do_refresh = self.listData.refreshTracked()
        refreshui |= do_refresh and self.listData.refreshInstallersStatus()
        if refreshui: self.uiList.RefreshUI(focus_list=False)

    def __extractOmods(self):
        with balt.Progress(_(u'Extracting OMODs...'),
                           u'\n' + u' ' * 60) as progress:
            dirInstallers = bass.dirs['installers']
            dirInstallersJoin = dirInstallers.join
            omods = [dirInstallersJoin(x) for x in dirInstallers.list() if
                     x.cext == u'.omod']
            progress.setFull(max(len(omods), 1))
            omodMoves, omodRemoves = set(), set()
            for i, omod in enumerate(omods):
                progress(i, omod.stail)
                outDir = dirInstallersJoin(omod.body)
                num = 0
                while outDir.exists():
                    outDir = dirInstallersJoin(u'%s%s' % (omod.sbody, num))
                    num += 1
                try:
                    bosh.omods.OmodFile(omod).extractToProject(
                        outDir, SubProgress(progress, i))
                    omodRemoves.add(omod)
                except (CancelError, SkipError):
                    omodMoves.add(omod)
                except:
                    deprint(_(u"Error extracting OMOD '%s':") % omod.stail,
                            traceback=True)
                    # Ensure we don't infinitely refresh if moving the omod
                    # fails
                    bosh.omods.failedOmods.add(omod.tail)
                    omodMoves.add(omod)
            # Cleanup
            dialog_title = _(u'OMOD Extraction - Cleanup Error')
            # Delete extracted omods
            def _del(files): env.shellDelete(files, parent=self)
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
                env.shellMove(failed, dests, parent=self)
            try:
                omodMoves = list(omodMoves)
                env.shellMakeDirs(dirInstallersJoin(u'Bash', u'Failed OMODs'))
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

    def _sbCount(self):
        active = sum(x.is_active for x in self.listData.itervalues())
        return _(u'Packages:') + u' %d/%d' % (active, len(self.listData))

    def RefreshUIMods(self, mods_changed, inis_changed):
        """Refresh UI plus refresh mods state."""
        self.uiList.RefreshUI()
        if mods_changed:
            BashFrame.modList.RefreshUI(refreshSaves=True, focus_list=False)
            Link.Frame.warn_corrupted(warn_saves=False)
            Link.Frame.warn_load_order()
        if inis_changed:
            if BashFrame.iniList is not None:
                BashFrame.iniList.RefreshUI(focus_list=False)
        bosh.bsaInfos.refresh() # TODO(ut) : add bsas_changed param! (or rather move this inside BAIN)

#------------------------------------------------------------------------------
class ScreensList(balt.UIList):
    mainMenu = Links() #--Column menu
    itemMenu = Links() #--Single item menu
    _shellUI = True
    _editLabels = True
    __ext_group = \
        r'(\.(' + u'|'.join(ext[1:] for ext in bosh.imageExts) + u')+)'

    _sort_keys = {'File'    : None,
                  'Modified': lambda self, a: self.data_store[a].mtime,
                  'Size'    : lambda self, a: self.data_store[a].size,
                 }
    #--Labels
    labels = OrderedDict([
        ('File',     lambda self, p: p.s),
        ('Modified', lambda self, p: format_date(self.data_store[p].mtime)),
        ('Size',     lambda self, p: round_size(self.data_store[p].size)),
    ])

    #--Events ---------------------------------------------
    def OnDClick(self, lb_dex_and_flags):
        """Double click a screenshot"""
        hitItem = self._getItemClicked(lb_dex_and_flags)
        if hitItem:
            self.OpenSelected(selected=[hitItem])
        return EventResult.FINISH

    def OnLabelEdited(self, is_edit_cancelled, evt_label, evt_index, evt_item):
        """Rename selected screenshots."""
        if is_edit_cancelled: return EventResult.CANCEL
        root, _newName, numStr = self.validate_filename(evt_label, has_digits=True,
                                                        ext=self.__ext_group)
        if not (root or numStr): return # allow for number only names
        selected = self.GetSelected()
        #--Rename each screenshot, keeping the old extension
        num = int(numStr or  0)
        digits = len(str(num + len(selected)))
        if numStr: numStr.zfill(digits)
        with balt.BusyCursor():
            to_select = set()
            to_del = set()
            item_edited = [self.panel.detailsPanel.displayed_item]
            for screen in selected:
                newName = GPath(root + numStr + screen.ext)
                if not self._try_rename(screen, newName, to_select,
                                        item_edited): break
                to_del.add(screen)
                num += 1
                numStr = unicode(num).zfill(digits)
            if to_select:
                self.RefreshUI(redraw=to_select, to_del=to_del,
                               detail_item=item_edited[0])
                #--Reselected the renamed items
                self.SelectItemsNoCallback(to_select)
            return EventResult.CANCEL

    def OnChar(self, wrapped_evt):
        # Enter: Open selected screens
        if wrapped_evt.key_code in balt.wxReturn: self.OpenSelected()
        else: super(ScreensList, self)._handle_key_up(wrapped_evt, None)

    def _handle_key_up(self, wrapped_evt, g_list):
        """Char event: Activate selected items, select all items"""
        code = wrapped_evt.key_code
        # Ctrl+C: Copy file(s) to clipboard
        if wrapped_evt.is_cmd_down and code == ord(u'C'):
            sel = map(lambda x: bosh.screen_infos.store_dir.join(x).s,
                      self.GetSelected())
            balt.copyListToClipboard(sel)
        super(ScreensList, self)._handle_key_up(wrapped_evt, g_list)

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
    keyPrefix = 'bash.screens'
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

    mainMenu = Links() #--Column menu
    itemMenu = Links() #--Single item menu
    _sort_keys = {'File'    : None,
                  'Modified': lambda self, a: self.data_store[a].mtime,
                  'Size'    : lambda self, a: self.data_store[a].size,
                 }
    #--Labels
    labels = OrderedDict([
        ('File',     lambda self, p: p.s),
        ('Modified', lambda self, p: format_date(self.data_store[p].mtime)),
        ('Size',     lambda self, p: round_size(self.data_store[p].size)),
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
            HLayout(spacing=4, items=[self.save, self.cancel])
        ]).apply_to(bottom)

    def _resetDetails(self):
        self._bsa_info = None
        self.fileStr = u''

    def SetFile(self, fileName='SAME'):
        """Set file to be viewed."""
        fileName = super(BSADetails, self).SetFile(fileName)
        if fileName:
            self._bsa_info = bosh.bsaInfos[fileName]
            #--Remember values for edit checks
            self.fileStr = self._bsa_info.name.s
        #--Set Fields
        self._fname_ctrl.text_content = self.fileStr
        #--Info Box
        self.gInfo.modified = False
        if fileName:
            self.gInfo.text_content = \
                bosh.bsaInfos.table.getItem(fileName, 'info', _(u'Notes: '))
        else:
            self.gInfo.text_content = _(u'Notes: ')

    def OnInfoEdit(self, new_text):
        """Info field was edited."""
        if self._bsa_info and self.gInfo.modified:
            bosh.bsaInfos.table.setItem(self._bsa_info.name, 'info', new_text)

    def DoSave(self):
        """Event: Clicked Save button."""
        #--Change Tests
        changeName = (self.fileStr != self._bsa_info.name)
        #--Change Name?
        if changeName:
            (oldName, newName) = (
                self._bsa_info.name, GPath(self.fileStr.strip()))
            bosh.bsaInfos.rename_info(oldName, newName)
        self.panel_uilist.RefreshUI(detail_item=self.file_info.name)

#------------------------------------------------------------------------------
class BSAPanel(BashTab):
    """BSA info tab."""
    keyPrefix = 'bash.BSAs'
    _status_str = _(u'BSAs:') + u' %d'
    _ui_list_type = BSAList
    _details_panel_type = BSADetails

    def __init__(self,parent):
        self.listData = bosh.bsaInfos
        bosh.bsaInfos.refresh()
        super(BSAPanel, self).__init__(parent)
        BashFrame.bsaList = self.uiList

#------------------------------------------------------------------------------
class PeopleList(balt.UIList):
    mainMenu = Links()
    itemMenu = Links()
    icons = karmacons
    _sunkenBorder = False
    _recycle = False
    _default_sort_col = 'Name'
    _sort_keys = {'Name'  : lambda self, x: x.lower(),
                  'Karma' : lambda self, x: self.data_store[x][1],
                  'Header': lambda self, x: self.data_store[x][2][:50].lower(),
                 }
    #--Labels
    @staticmethod
    def _karma(personData):
        karma = personData[1]
        return (u'-', u'+')[karma >= 0] * abs(karma)
    labels = OrderedDict([
        ('Name',   lambda self, name_: name_),
        ('Karma',  lambda self, name_: self._karma(self.data_store[name_])),
        ('Header', lambda self, name_:
                            self.data_store[name_][2].split(u'\n', 1)[0][:75]),
    ])

    def set_item_format(self, item, item_format):
        item_format.icon_key = u'karma%+d' % self.data_store[item][1]

#------------------------------------------------------------------------------
class PeopleDetails(_DetailsMixin, NotebookPanel):
    @property
    def displayed_item(self): return self._people_detail
    @property
    def file_infos(self): return self.peoplePanel.listData

    def __init__(self, parent, ui_list_panel):
        super(PeopleDetails, self).__init__(parent)
        self._people_detail = None # type: unicode
        self.peoplePanel = ui_list_panel
        self.gName = TextField(self, editable=False)
        self.gText = TextArea(self)
        self.gKarma = Spinner(self, min_val=-5, max_val=5, onSpin=self.OnSpin)
        self.gKarma.set_min_size(40,-1)
        #--Layout
        VLayout(spacing=4, item_expand=True, items=[
            HLayout(item_expand=True, items=[
                (self.gName, LayoutOptions(weight=1)), self.gKarma]),
            (self.gText, LayoutOptions(weight=1))
        ]).apply_to(self)

    def OnSpin(self):
        """Karma spin."""
        if not self._people_detail: return
        karma = int(self.gKarma.sp_get_value())
        details = self.file_infos[self._people_detail][2]
        self.file_infos[self._people_detail] = (time.time(), karma, details)
        self.peoplePanel.uiList.PopulateItem(item=self._people_detail)
        self.file_infos.setChanged()

    def ClosePanel(self, destroy=False):
        """Saves details if they need saving."""
        if not self.gText.modified: return
        if not self.file_info: return
        mtime, karma, __text = self.file_infos[self._people_detail]
        self.file_infos[self._people_detail] = (
            time.time(), karma, self.gText.text_content.strip())
        self.peoplePanel.uiList.PopulateItem(item=self._people_detail)
        self.file_infos.setChanged()

    def SetFile(self, fileName='SAME'):
        """Refreshes detail view associated with data from item."""
        self.ClosePanel()
        item = super(PeopleDetails, self).SetFile(fileName)
        self._people_detail = item
        if not item: return
        karma, details = self.peoplePanel.listData[item][1:3]
        self.gName.text_content = item
        self.gKarma.sp_set_value(karma)
        self.gText.text_content = details

    def _resetDetails(self):
        self.gKarma.sp_set_value(0)
        self.gName.text_content = u''
        self.gText.text_content = u''

class PeoplePanel(BashTab):
    """Panel for PeopleTank."""
    keyPrefix = 'bash.people'
    _status_str = _(u'People:') + u' %d'
    _ui_list_type = PeopleList
    _details_panel_type = PeopleDetails

    def __init__(self,parent):
        """Initialize."""
        self.listData = bosh.PeopleData()
        super(PeoplePanel, self).__init__(parent)

    def ShowPanel(self, **kwargs):
        if self.listData.refresh(): self.uiList.RefreshUI(focus_list=False)
        super(PeoplePanel, self).ShowPanel()

#------------------------------------------------------------------------------
#--Tabs menu
_widget_to_panel = {}
class _Tab_Link(AppendableLink, CheckLink, EnabledLink):
    """Handle hiding/unhiding tabs."""
    def __init__(self,tabKey,canDisable=True):
        super(_Tab_Link, self).__init__()
        self.tabKey = tabKey
        self.enabled = canDisable
        className, self._text, item = tabInfo.get(self.tabKey,[None,None,None])
        self._help = _(u"Show/Hide the %(tabtitle)s Tab.") % (
            {'tabtitle': self._text})

    def _append(self, window): return self._text is not None

    def _enable(self): return self.enabled

    def _check(self): return bass.settings['bash.tabs.order'][self.tabKey]

    def Execute(self):
        if bass.settings['bash.tabs.order'][self.tabKey]:
            # It was enabled, disable it.
            iMods = None
            iInstallers = None
            iDelete = None
            for i in range(Link.Frame.notebook.GetPageCount()):
                pageTitle = Link.Frame.notebook.GetPageText(i)
                if pageTitle == tabInfo['Mods'][1]:
                    iMods = i
                elif pageTitle == tabInfo['Installers'][1]:
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
            for key, is_enabled in bass.settings['bash.tabs.order'].items():
                if key == self.tabKey: break
                insertAt += is_enabled
            className,title,panel = tabInfo[self.tabKey]
            if not panel:
                panel = globals()[className](Link.Frame.notebook)
                tabInfo[self.tabKey][2] = panel
                _widget_to_panel[panel.wx_id_] = panel
            if insertAt > Link.Frame.notebook.GetPageCount():
                Link.Frame.notebook.AddPage(panel._native_widget,title)
            else:
                Link.Frame.notebook.InsertPage(insertAt,panel._native_widget,title)
        bass.settings['bash.tabs.order'][self.tabKey] ^= True

class BashNotebook(wx.Notebook, balt.TabDragMixin):

    # default tabs order and default enabled state, keys as in tabInfo
    _tabs_enabled_ordered = OrderedDict((('Installers', True),
                                        ('Mods', True),
                                        ('Saves', True),
                                        ('INI Edits', True),
                                        ('Screenshots', True),
                                        ('People', False),
                                        # ('BSAs', False),
                                       ))

    @staticmethod
    def _tabOrder():
        """Return dict containing saved tab order and enabled state of tabs."""
        newOrder = settings.getChanged('bash.tabs.order',
                                       BashNotebook._tabs_enabled_ordered)
        if not isinstance(newOrder, OrderedDict): # convert, on updating to 306
            enabled = settings.getChanged('bash.tabs', # deprecated - never use
                                          BashNotebook._tabs_enabled_ordered)
            newOrder = OrderedDict([(x, enabled[x]) for x in newOrder
            # needed if user updates to 306+ that drops 'bash.tabs', the latter
            # is unchanged from default and the new version also removes a panel
                                    if x in enabled])
        # append any new tabs - appends last
        newTabs = set(tabInfo) - set(newOrder)
        for n in newTabs: newOrder[n] = BashNotebook._tabs_enabled_ordered[n]
        # delete any removed tabs
        deleted = set(newOrder) - set(tabInfo)
        for d in deleted: del newOrder[d]
        # Ensure the 'Mods' tab is always shown
        if 'Mods' not in newOrder: newOrder['Mods'] = True # inserts last
        settings['bash.tabs.order'] = newOrder
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
            # Some page specific stuff
            if page == 'Installers': iInstallers = self.GetPageCount()
            elif page == 'Mods': iMods = self.GetPageCount()
            # Add the page
            try:
                item = panel(self)
                self.AddPage(item._native_widget, title)
                tabInfo[page][2] = item
                _widget_to_panel[item.wx_id_] = item
            except:
                if page == 'Mods':
                    deprint(_(u"Fatal error constructing '%s' panel.") % title)
                    raise
                deprint(_(u"Error constructing '%s' panel.") % title,traceback=True)
                settings['bash.tabs.order'][page] = False
        #--Selection
        pageIndex = max(min(settings['bash.page'], self.GetPageCount() - 1), 0)
        if settings['bash.installers.fastStart'] and pageIndex == iInstallers:
            pageIndex = iMods
        self.SetSelection(pageIndex)
        self.currentPage = _widget_to_panel[
            self.GetPage(self.GetSelection()).GetId()]
        #--Dragging
        self.Bind(balt.EVT_NOTEBOOK_DRAGGED, self.OnTabDragged)
        #--Setup Popup menu for Right Click on a Tab
        self.Bind(wx.EVT_CONTEXT_MENU, self.DoTabMenu)

    @staticmethod
    def tabLinks(menu):
        for key in BashNotebook._tabOrder(): # use tabOrder here - it is used in
            # InitLinks which runs _before_ settings['bash.tabs.order'] is set!
            canDisable = bool(key != 'Mods')
            menu.append(_Tab_Link(key, canDisable))
        return menu

    def SelectPage(self, page_title, item):
        ind = 0
        for title, enabled in settings['bash.tabs.order'].iteritems():
            if title == page_title:
                if not enabled: return
                break
            ind += enabled
        else: raise BoltError('Invalid page: %s' % page_title)
        self.SetSelection(ind)
        tabInfo[page_title][2].SelectUIListItem(item, deselectOthers=True)

    def DoTabMenu(self,event):
        pos = event.GetPosition()
        pos = self.ScreenToClient(pos)
        tabId = self.HitTest(pos)
        if tabId != wx.NOT_FOUND and tabId[0] != wx.NOT_FOUND:
            menu = self.tabLinks(Links())
            menu.new_menu(self, None)
        else:
            event.Skip()

    def OnTabDragged(self, event):
        newPos = event.toIndex
        # Find the key
        removeTitle = self.GetPageText(newPos)
        oldOrder = settings['bash.tabs.order'].keys()
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
        settings['bash.tabs.order'] = OrderedDict(
            (k, settings['bash.tabs.order'][k]) for k in newOrder)
        event.Skip()

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
    SettingsMenu = Links()
    obseButton = None
    laaButton = None

    def UpdateIconSizes(self):
        self.buttons = [] # will be populated with _displayed_ gButtons - g ?
        order = settings['bash.statusbar.order']
        orderChanged = False
        hide = settings['bash.statusbar.hide']
        hideChanged = False
        # Add buttons in order that is saved - on first run order = [] !
        for uid in order[:]:
            link = self.GetLink(uid=uid)
            # Doesn't exist?
            if link is None:
                order.remove(uid)
                orderChanged = True
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
                hideChanged = True
            order.append(uid)
            orderChanged = True
            try:
                self._addButton(link)
            except AttributeError:
                deprint(u'Failed to load button %r' % (uid,), traceback=True)
        # Update settings
        if orderChanged: settings.setChanged('bash.statusbar.order')
        if hideChanged: settings.setChanged('bash.statusbar.hide')
        self._do_refresh(refresh_icon_size=True)

    def HideButton(self,button):
        if button in self.buttons:
            # Find the BashStatusBar_Button instance that made it
            link = self.GetLink(button=button)
            if link:
                button.visible = False
                self.buttons.remove(button)
                settings['bash.statusbar.hide'].add(link.uid)
                settings.setChanged('bash.statusbar.hide')
                self._do_refresh()

    def UnhideButton(self,link):
        uid = link.uid
        settings['bash.statusbar.hide'].discard(uid)
        settings.setChanged('bash.statusbar.hide')
        # Find the position to insert it at
        order = settings['bash.statusbar.order']
        if uid not in order:
            # Not specified, put it at the end
            order.append(uid)
            settings.setChanged('bash.statusbar.order')
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
        self._do_refresh()

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

    def _do_refresh(self, refresh_icon_size=False):
        """Updates status widths and the icon sizes, if refresh_icon_size is
        True. Also propagates resizing events.

        :param refresh_icon_size: Whether or not to update icon sizes too."""
        txt_len = 280 if bush.game.has_esl else 130
        self.SetStatusWidths([self.iconsSize * len(self.buttons), -1, txt_len])
        if refresh_icon_size: self.SetSize((-1, self.iconsSize))
        self.SendSizeEventToParent()
        self.OnSize()

#------------------------------------------------------------------------------
class BashFrame(WindowFrame):
    """Main application frame."""
    ##:ex basher globals - hunt their use down - replace with methods - see #63
    docBrowser = None
    modChecker = None
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
        #--Status Bar
        self._native_widget.SetStatusBar(BashStatusBar(self._native_widget))
        #--Notebook panel
        # attributes used when ini panel is created (warn for missing game ini)
        self.oblivionIniCorrupted = u''
        self.oblivionIniMissing = self._oblivionIniMissing = False
        self.notebook = BashNotebook(self._native_widget)
        #--Data
        self.inRefreshData = False #--Prevent recursion while refreshing.
        self.knownCorrupted = set()
        self.knownInvalidVerions = set()
        self.known_sse_form43_mods = set()
        self.incompleteInstallError = False

    @balt.conversation
    def warnTooManyModsBsas(self):
        if bush.game.fsName != u'Oblivion': return
        if not bass.inisettings['WarnTooManyFiles']: return
        if not len(bosh.bsaInfos): bosh.bsaInfos.refresh()
        if len(bosh.bsaInfos) + len(bosh.modInfos) >= 325 and not \
                settings['bash.mods.autoGhost']:
            message = _(u"It appears that you have more than 325 mods and bsas"
                u" in your data directory and auto-ghosting is disabled. This "
                u"may cause problems in %s; see the readme under auto-ghost "
                u"for more details and please enable auto-ghost.") % \
                      bush.game.displayName
            if len(bosh.bsaInfos) + len(bosh.modInfos) >= 400:
                message = _(u"It appears that you have more than 400 mods and "
                    u"bsas in your data directory and auto-ghosting is "
                    u"disabled. This will cause problems in %s; see the readme"
                    u" under auto-ghost for more details. ") % \
                          bush.game.displayName
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
        bass.update_sys_argv(['--no-uac'])
        # restart
        bass.is_restarting = True
        self.close_win(True)

    def set_bash_frame_title(self):
        """Set title. Set to default if no title supplied."""
        if bush.game.altName and settings['bash.useAltName']:
            title = bush.game.altName + u' %s%s'
        else:
            title = u'Wrye Bash %s%s '+_(u'for')+u' '+bush.game.displayName
        title %= (bass.AppVersion, (u' ' + _(u'(Standalone)')) if settings[
                      'bash.standalone'] else u'')
        if CBashApi.Enabled:
            title += u', CBash %s: ' % (CBashApi.VersionText,)
        else:
            title += u': '
        # chop off save prefix - +1 for the path separator
        maProfile = bosh.saveInfos.localSave[len(
            bush.game.Ini.save_prefix) + 1:]
        if maProfile:
            title += maProfile
        else:
            title += _(u'Default')
        if bosh.modInfos.voCurrent:
            title += u' ['+bosh.modInfos.voCurrent+u']'
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
        bosh.configHelpers.refreshBashTags()
        #--Check bsas, needed to detect string files in modInfos refresh...
        bosh.oblivionIni.get_ini_language(cached=False) # reread ini language
        if not booting and bosh.bsaInfos.refresh():
            popBsas = 'ALL'
        #--Check plugins.txt and mods directory...
        if not booting and bosh.modInfos.refresh():
            popMods = 'ALL'
        #--Check savegames directory...
        if not booting and bosh.saveInfos.refresh():
            popSaves = 'ALL'
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
        self.warn_corrupted()
        self.warn_game_ini()
        self._missingDocsDir()
        #--Done (end recursion blocker)
        self.inRefreshData = False
        return EventResult.FINISH

    def _warn_reset_load_order(self):
        if load_order.warn_locked and not bass.inisettings[
            'SkipResetTimeNotifications']:
            balt.showWarning(self, _(u"Load order has changed outside of Bash "
                u"and has been reverted to the one saved in Bash. You can hit "
                u"Ctrl + Z while the mods list has focus to undo this."),
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

    def warn_corrupted(self, warn_mods=True, warn_saves=True,
                       warn_strings=True): # WIP maybe move to ShowPanel()
        #--Any new corrupted files?
        message = []
        corruptMods = set(bosh.modInfos.corrupted.keys())
        if warn_mods and not corruptMods <= self.knownCorrupted:
            m = [_(u'Plugin warnings'),
                 _(u'The following mod files have unrecognized headers: ')]
            m.extend(sorted(corruptMods))
            message.append(m)
            self.knownCorrupted |= corruptMods
        corruptSaves = set(bosh.saveInfos.corrupted.keys())
        if warn_saves and not corruptSaves <= self.knownCorrupted:
            m = [_(u'Save game warnings'),
                 _(u'The following save files have unrecognized header formats: ')]
            m.extend(sorted(corruptSaves))
            message.append(m)
            self.knownCorrupted |= corruptSaves
        invalidVersions = set([x.name for x in bosh.modInfos.values() if round(
            x.header.version, 6) not in bush.game.Esp.validHeaderVersions])
        if warn_mods and not invalidVersions <= self.knownInvalidVerions:
            m = [_(u'Unrecognized Versions'),
                 _(u'The following mods have unrecognized header versions: ')]
            m.extend(sorted(invalidVersions - self.knownInvalidVerions))
            message.append(m)
            self.knownInvalidVerions |= invalidVersions
        if warn_mods and not bosh.modInfos.sse_form43 <= self.known_sse_form43_mods:
            m = [_(u'Older Plugin Record Version'),
                 _(u"The following mods don't use the current plugin Form Version: ")]
            m.extend(sorted(bosh.modInfos.sse_form43 - self.known_sse_form43_mods))
            message.append(m)
            self.known_sse_form43_mods |= bosh.modInfos.sse_form43
        if warn_strings and bosh.modInfos.new_missing_strings:
            m = [_(u'Missing String Localization files:'),
                 _(u'This will cause CTDs if activated.')]
            m.extend(sorted(bosh.modInfos.missing_strings))
            message.append(m)
            bosh.modInfos.new_missing_strings.clear()
        if message:
            ListBoxes.display_dialog(
              self, _(u'Warnings'), _(u'The following warnings were found:'),
            message, liststyle=u'list', canCancel=False)

    _ini_missing = _(u"%(ini)s does not exist yet.  %(game)s will create this "
        u"file on first run.  INI tweaks will not be usable until then.")
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
                    'ini': bosh.oblivionIni.abs_path,
                    'game': bush.game.displayName}, _(u'Missing game Ini'))

    def _missingDocsDir(self):
        #--Missing docs directory?
        testFile = bass.dirs['mopy'].join(u'Docs', u'wtxt_teal.css')
        if self.incompleteInstallError or testFile.exists(): return
        self.incompleteInstallError = True
        msg = _(u'Installation appears incomplete.  Please re-unzip bash '
        u'to game directory so that ALL files are installed.') + u'\n\n' + _(
        u'Correct installation will create %s\\Mopy and '
        u'%s\\Data\\Docs directories.') % (bush.game.fsName, bush.game.fsName)
        balt.showWarning(self, msg, _(u'Incomplete Installation'))

    def on_closing(self, destroy=True):
        """Handle Close event. Save application data."""
        try:
            # Save sizes here, in the finally clause position is not saved - todo PY3: test if needed
            super(BashFrame, self).on_closing(destroy=False)
            self.bind_refresh(bind=False)
            self.SaveSettings(destroy=True)
        except:
                deprint(_(u'An error occurred while trying to save settings:'),
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
        settings['bash.frameMax'] = self.is_maximized
        settings['bash.page'] = self.notebook.GetSelection()
        # use tabInfo below so we save settings of panels that the user closed
        for _k, (_cname, tab_name, panel) in tabInfo.iteritems():
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
        modNames = set(bosh.modInfos.keys())
        modNames.update(bosh.modInfos.table.keys())
        renames = bass.settings.getChanged('bash.mods.renames')
        for key,value in renames.items():
            if value not in modNames:
                del renames[key]
        #--Clean colors dictionary
        currentColors = set(settings['bash.colors'].keys())
        defaultColors = set(settingDefaults['bash.colors'].keys())
        invalidColors = currentColors - defaultColors
        missingColors = defaultColors - currentColors
        if invalidColors:
            for key in invalidColors:
                del settings['bash.colors'][key]
        if missingColors:
            for key in missingColors:
                settings['bash.colors'][key] = settingDefaults['bash.colors'][key]
        if invalidColors or missingColors:
            settings.setChanged('bash.colors')
        #--Clean backup
        for fileInfos in (bosh.modInfos,bosh.saveInfos):
            goodRoots = set(p.root for p in fileInfos.keys())
            backupDir = fileInfos.bash_dir.join(u'Backups')
            if not backupDir.isdir(): continue
            for name in backupDir.list():
                back_path = backupDir.join(name)
                if name.root not in goodRoots and back_path.isfile():
                    back_path.remove()

    @staticmethod
    def saveListRefresh(focus_list):
        if BashFrame.saveList:
            BashFrame.saveList.RefreshUI(focus_list=focus_list)

    @staticmethod
    def bsaListRefresh(focus_list):
        if BashFrame.bsaList:
            BashFrame.bsaList.RefreshUI(focus_list=focus_list)

#------------------------------------------------------------------------------
class BashApp(wx.App):
    """Bash Application class."""
    def Init(self): # not OnInit(), we need to initialize _after_ the app has been instantiated
        """Initialize the application data and create the BashFrame."""
        #--OnStartup SplashScreen and/or Progress
        #   Progress gets hidden behind splash by default, since it's not very informative anyway
        splashScreen = None
        with balt.Progress(u'Wrye Bash', _(u'Initializing') + u' ' * 10,
                           elapsed=False) as progress:
            # Is splash enabled in ini ?
            if bass.inisettings['EnableSplashScreen']:
                if bass.dirs['images'].join(u'wryesplash.png').exists():
                    try:
                            splashScreen = balt.WryeBashSplashScreen()
                            splashScreen.Show()
                    except:
                            pass
            #--Constants
            self.InitResources()
            #--Init Data
            progress(0.2, _(u'Initializing Data'))
            self.InitData(progress)
            progress(0.7, _(u'Initializing Version'))
            self.InitVersion()
            #--MWFrame
            progress(0.8, _(u'Initializing Windows'))
            frame = BashFrame() # Link.Frame global set here
            progress(1.0, _(u'Done'))
        if splashScreen:
            splashScreen.Destroy()
            splashScreen.Hide() # wont be hidden if warnTooManyModsBsas warns..
        self.SetTopWindow(frame._native_widget)
        frame.show_frame()
        frame._native_widget.Maximize(settings['bash.frameMax'])
        frame.RefreshData(booting=True) # used to bind RefreshData
        # Moved notebook.Bind() callback here as OnShowPage() is explicitly
        # called in RefreshData
        frame.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED,
                            frame.notebook.OnShowPage)
        return frame

    @staticmethod
    def InitResources():
        """Init application resources."""
        Resources.bashBlue = Resources.bashBlue.GetIconBundle()
        Resources.bashRed = Resources.bashRed.GetIconBundle()
        Resources.bashDocBrowser = Resources.bashDocBrowser.GetIconBundle()
        Resources.bashMonkey = Resources.bashMonkey.GetIconBundle()

    @staticmethod
    def InitData(progress):
        """Initialize all data. Called by Init()."""
        progress(0.05, _(u'Initializing BsaInfos'))
        #bsaInfos: used in warnTooManyModsBsas() and modInfos strings detection
        bosh.bsaInfos = bosh.BSAInfos()
        bosh.bsaInfos.refresh(booting=True)
        progress(0.20, _(u'Initializing ModInfos'))
        bosh.modInfos = bosh.ModInfos()
        bosh.modInfos.refresh(booting=True)
        progress(0.50, _(u'Initializing SaveInfos'))
        bosh.saveInfos = bosh.SaveInfos()
        bosh.saveInfos.refresh(booting=True)
        progress(0.60, _(u'Initializing IniInfos'))
        bosh.iniInfos = bosh.INIInfos()
        bosh.iniInfos.refresh(refresh_target=False)
        # screens/people/installers data are refreshed upon showing the panel
        #--Patch check
        if bush.game.Esp.canBash:
            if not bosh.modInfos.bashed_patches and bass.inisettings['EnsurePatchExists']:
                progress(0.68, _(u'Generating Blank Bashed Patch'))
                try:
                    bosh.modInfos.generateNextBashedPatch(selected_mods=())
                except: # YAK but this may blow and has blown on whatever coding error, crashing Bash on boot
                    deprint(u'Failed to create new bashed patch', traceback=True)

    @staticmethod
    def InitVersion():
        """Perform any version to version conversion. Called by Init()."""
        #--Renames dictionary: Strings to Paths.
        bash_version = settings['bash.version']
        if isinstance(bash_version, int):
            if bash_version < 40:
                #--Renames array
                newRenames = {}
                for key,value in settings['bash.mods.renames'].iteritems():
                    newRenames[GPath(key)] = GPath(value)
                settings['bash.mods.renames'] = newRenames
                #--Mod table data
                modTableData = bosh.modInfos.table.data
                for key in modTableData.keys():
                    if not isinstance(key,bolt.Path):
                        modTableData[GPath(key)] = modTableData[key]
                        del modTableData[key]
            #--Window sizes by class name rather than by class
            if bash_version < 43:
                for key,value in balt.sizes.iteritems():
                    if isinstance(key, type):
                        balt.sizes[key.__name__] = value
                        del balt.sizes[key]
        #--Current Version
        if settings['bash.version'] != bass.AppVersion:
            settings['bash.version'] = bass.AppVersion
            # rescan mergeability on version upgrade to detect new mergeable
            bosh.modInfos.rescanMergeable(bosh.modInfos.data, bolt.Progress())
        settings['bash.CBashEnabled'] = CBashApi.Enabled

# Initialization --------------------------------------------------------------
from .gui_patchers import initPatchers
def InitSettings(): # this must run first !
    """Initializes settings dictionary for bosh and basher."""
    bosh.initSettings()
    global settings
    balt._settings = bass.settings
    balt.sizes = bass.settings.getChanged('bash.window.sizes',{})
    settings = bass.settings
    settings.loadDefaults(settingDefaults)
    bosh.bain.Installer.init_global_skips() # must be after loadDefaults - grr #178
    bosh.bain.Installer.init_attributes_process()
    # Plugin encoding used to decode mod string fields
    bolt.pluginEncoding = bass.settings['bash.pluginEncoding']
    #--Wrye Balt
    settings['balt.WryeLog.temp'] = bass.dirs['saveBase'].join(u'WryeLogTemp.html')
    settings['balt.WryeLog.cssDir'] = bass.dirs['mopy'].join(u'Docs')
    #--StandAlone version?
    settings['bash.standalone'] = hasattr(sys,'frozen')
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
    for key, value in settings['bash.colors'].iteritems():
        # Convert any colors that were stored as bytestrings into tuples
        if isinstance(value, str):
            value = settings['bash.colors'][key] = _conv_dict[value]
        colors[key] = value
    #--Images
    imgDirJn = bass.dirs['images'].join
    def _png(fname): return Image(imgDirJn(fname))
    #--Standard
    images['save.on'] = _png(u'save_on.png')
    images['save.off'] = _png(u'save_off.png')
    #--Misc
    #images['oblivion'] = Image(GPath(bass.dirs['images'].join(u'oblivion.png')),png)
    images['help.16'] = _png(u'help16.png')
    images['help.24'] = _png(u'help24.png')
    images['help.32'] = _png(u'help32.png')
    #--ColorChecks
    images['checkbox.red.x'] = _png(u'checkbox_red_x.png')
    images['checkbox.red.x.16'] = _png(u'checkbox_red_x.png')
    images['checkbox.red.x.24'] = _png(u'checkbox_red_x_24.png')
    images['checkbox.red.x.32'] = _png(u'checkbox_red_x_32.png')
    images['checkbox.red.off.16'] = _png(u'checkbox_red_off.png')
    images['checkbox.red.off.24'] = _png(u'checkbox_red_off_24.png')
    images['checkbox.red.off.32'] = _png(u'checkbox_red_off_32.png')

    images['checkbox.green.on.16'] = _png(u'checkbox_green_on.png')
    images['checkbox.green.off.16'] = _png(u'checkbox_green_off.png')
    images['checkbox.green.on.24'] = _png(u'checkbox_green_on_24.png')
    images['checkbox.green.off.24'] = _png(u'checkbox_green_off_24.png')
    images['checkbox.green.on.32'] = _png(u'checkbox_green_on_32.png')
    images['checkbox.green.off.32'] = _png(u'checkbox_green_off_32.png')

    images['checkbox.blue.on.16'] = _png(u'checkbox_blue_on.png')
    images['checkbox.blue.on.24'] = _png(u'checkbox_blue_on_24.png')
    images['checkbox.blue.on.32'] = _png(u'checkbox_blue_on_32.png')
    images['checkbox.blue.off.16'] = _png(u'checkbox_blue_off.png')
    images['checkbox.blue.off.24'] = _png(u'checkbox_blue_off_24.png')
    images['checkbox.blue.off.32'] = _png(u'checkbox_blue_off_32.png')
    #--DocBrowser
    images['doc.16'] = _png(u'docbrowser16.png')
    images['doc.24'] = _png(u'docbrowser24.png')
    images['doc.32'] = _png(u'docbrowser32.png')
    images['settingsbutton.16'] = _png(u'settingsbutton16.png')
    images['settingsbutton.24'] = _png(u'settingsbutton24.png')
    images['settingsbutton.32'] = _png(u'settingsbutton32.png')
    images['modchecker.16'] = _png(u'modchecker16.png')
    images['modchecker.24'] = _png(u'modchecker24.png')
    images['modchecker.32'] = _png(u'modchecker32.png')
    images['pickle.16'] = _png(u'pickle16.png')
    images['pickle.24'] = _png(u'pickle24.png')
    images['pickle.32'] = _png(u'pickle32.png')
    #--Applications Icons
    Resources.bashRed = balt.ImageBundle()
    Resources.bashRed.Add(imgDirJn(u'bash_32-2.ico'))
    #--Application Subwindow Icons
    Resources.bashBlue = balt.ImageBundle()
    Resources.bashBlue.Add(imgDirJn(u'bash_blue.svg-2.ico'))
    Resources.bashDocBrowser = balt.ImageBundle()
    Resources.bashDocBrowser.Add(imgDirJn(u'docbrowser32.ico'))
    #--Bash Patch Dialogue icon
    Resources.bashMonkey = balt.ImageBundle()
    Resources.bashMonkey.Add(imgDirJn(u'wrye_monkey_87_sharp.ico'))

from .links_init import InitLinks
