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
links.py          : the initialization functions for menus, defines menu order
dialogs.py        : subclasses of balt.Dialog (except patcher dialog)
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
import StringIO
import os
import re
import sys
import time
from collections import OrderedDict
from functools import partial
from operator import itemgetter
from types import ClassType
#--wxPython
import collections
import wx

#--Localization
#..Handled by bosh, so import that.
from .. import bush, bosh, bolt, bass, env, load_order, archives
from ..bass import Resources
from ..bolt import BoltError, CancelError, SkipError, GPath, SubProgress, \
    deprint, AbstractError, formatInteger, formatDate, round_size
from ..bosh import omods, projects_walk_cache
from ..cint import CBashApi

startupinfo = bolt.startupinfo

#--Balt
from .. import balt
from ..balt import fill, CheckLink, EnabledLink, SeparatorLink, \
    Link, ChoiceLink, RoTextCtrl, staticBitmap, AppendableLink, ListBoxes, \
    SaveButton, CancelButton, INIListCtrl, DnDStatusBar, NotebookPanel
from ..balt import checkBox, StaticText, spinCtrl, TextCtrl
from ..balt import hspacer, hSizer, vSizer, hspace, vspace
from ..balt import colors, images, Image
from ..balt import Links, ItemLink

# Constants -------------------------------------------------------------------
from .constants import colorInfo, settingDefaults, karmacons, installercons, \
    PNG, JPEG, ICO, BMP, TIF

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

appRestart = False # restart Bash if true
uacRestart = False # restart Bash with Admin Rights if true

# Settings --------------------------------------------------------------------
settings = None

# Links -----------------------------------------------------------------------
#------------------------------------------------------------------------------
def SetUAC(item): # item must define a GetHandle() method
    """Helper function for creating menu items or buttons that need UAC
       Note: for this to work correctly, it needs to be run BEFORE
       appending a menu item to a menu (and so, needs to be enabled/
       disabled prior to that as well."""
    if env.isUAC:
        if isinstance(item, wx.MenuItem):
            pass
            #if item.IsEnabled():
            #    bitmap = images['uac.small'].GetBitmap()
            #    item.SetBitmaps(bitmap,bitmap)
        else:
            env.setUAC(item.GetHandle(), True)

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

    Mix it in to SashUIListPanel so UILists can call SetDetails, RefreshDetails
    and ClearDetails on their panels."""
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

    def GetDetailsItem(self): return self.detailsPanel.file_info

class SashPanel(NotebookPanel):
    """Subclass of Notebook Panel, designed for two pane panel."""
    defaultSashPos = minimumSize = 256

    def __init__(self, parent, isVertical=True):
        super(SashPanel, self).__init__(parent)
        self.splitter = splitter = balt.Splitter(self)
        self.left = wx.Panel(splitter)
        self.right = wx.Panel(splitter)
        if isVertical:
            splitter.SplitVertically(self.left, self.right)
        else:
            splitter.SplitHorizontally(self.left, self.right)
        self.isVertical = isVertical
        self.sashPosKey = self.__class__.keyPrefix + '.sashPos'
        # Don't allow unsplitting
        splitter.Bind(wx.EVT_SPLITTER_DCLICK, lambda self_, event: event.Veto())
        splitter.SetMinimumPaneSize(self.__class__.minimumSize)
        sizer = vSizer(
            (splitter,1,wx.EXPAND),
            )
        self.SetSizer(sizer)

    def ShowPanel(self, **kwargs):
        if self._firstShow:
            sashPos = settings.get(self.sashPosKey,
                                   self.__class__.defaultSashPos)
            self.splitter.SetSashPosition(sashPos)
            self._firstShow = False

    def ClosePanel(self, destroy=False):
        if not self._firstShow and destroy: # if the panel was shown
            settings[self.sashPosKey] = self.splitter.GetSashPosition()

class SashUIListPanel(SashPanel):
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
        Link.Frame.SetStatusCount(self, self._sbCount())

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
        # the only SashPanels that do not have this attribute are ModDetails
        # and SaveDetails that use a MasterList whose data is initially {}
        self.listData.save()

class BashTab(_DetailsViewMixin, SashUIListPanel):
    _details_panel_type = None # type: type
    defaultSashPos = 512
    minimumSize = 256

    def __init__(self, parent, isVertical=True):
        super(BashTab, self).__init__(parent, isVertical)
        self.detailsPanel = self._details_panel_type(self.right)
        #--Layout
        self.right.SetSizer(hSizer((self.detailsPanel, 1, wx.EXPAND)))
        self.left.SetSizer(hSizer((self.uiList, 2, wx.EXPAND)))

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
            items.sort(key=lambda a: not self.data_store[a].isEsm())

    def _activeModsFirst(self, items):
        if self.selectedFirst:
            items.sort(key=lambda x: x not in set(load_order.activeCached()
                ) | bosh.modInfos.imported | bosh.modInfos.merged)

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
        'File'         : lambda self, a: self.data_store[a].name.s.lower(),
        'Current Order': lambda self, a: self.loadOrderNames.index(
           self.data_store[a].name), #missing mods sort last alphabetically
    }
    def _activeModsFirst(self, items):
        if self.selectedFirst:
            items.sort(key=lambda x: self.data_store[x].name not in set(
                load_order.activeCached()) | bosh.modInfos.imported
                                           | bosh.modInfos.merged)
    _extra_sortings = [_ModsUIList._sortEsmsFirst, _activeModsFirst]
    _sunkenBorder, _singleCell = False, True
    #--Labels
    labels = OrderedDict([
        ('File',          lambda self, mi: bosh.modInfos.masterWithVersion(
                                                self.data_store[mi].name.s)),
        ('Num',           lambda self, mi: u'%02X' % mi),
        ('Current Order', lambda self, mi: bosh.modInfos.hexIndexString(
            self.data_store[mi].name)),
    ])

    @property
    def cols(self):
        # using self.__class__.keyPrefix for common saves/mods masters settings
        return settings.getChanged(self.__class__.keyPrefix + '.cols')

    message = _(u"Edit/update the masters list? Note that the update process "
                u"may automatically rename some files. Be sure to review the "
                u"changes before saving.")
    seName = bush.game.se.shortName
    saves192warn = u'\n\n' + _(u"Note that %(scrExtender)s cosaves are NOT "
            u"supported, meaning that if you have a save that has a cosave "
            u"the masters in the cosave WON'T be updated leading to "
            u"crashes/lost information and whatnot." % {'scrExtender': seName})

    def __init__(self, parent, listData=None, keyPrefix=keyPrefix, panel=None,
                 detailsPanel=None):
        #--Data/Items
        self.edited = False
        self.detailsPanel = detailsPanel
        self.fileInfo = None
        self.loadOrderNames = [] # cache, orders missing last alphabetically
        self._allowEditKey = keyPrefix + '.allowEdit'
        if isinstance(detailsPanel, SaveDetails): # yak ! fix #192
            self.message += self.saves192warn
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

    def OnItemSelected(self, event): event.Skip()
    def OnKeyUp(self, event): event.Skip()

    def OnDClick(self, event):
        BashFrame.modList.RefreshUI()
        BashFrame.modList.SelectAndShowItem(self.data_store[self.mouse_index].name, deselectOthers=True)

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
        for mi, masters_name in enumerate(fileInfo.header.masters):
            masterInfo = bosh.MasterInfo(masters_name, 0)
            self.data_store[mi] = masterInfo
        self._reList()
        self.PopulateItems()

    #--Get Master Status
    def GetMasterStatus(self, mi):
        masterInfo = self.data_store[mi]
        masters_name = masterInfo.name
        status = masterInfo.getStatus()
        if status == 30: return status # does not exist
        # current load order of master relative to other masters
        loadOrderIndex = self.loadOrderNames.index(masters_name)
        ordered = load_order.activeCached()
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
        masters_name = masterInfo.name
        #--Font color
        fileBashTags = masterInfo.getBashTags()
        mouseText = u''
        if masterInfo.isEsm():
            item_format.text_key = 'mods.text.esm'
            mouseText += _(u"Master file. ")
        elif masters_name in bosh.modInfos.mergeable:
            if u'NoMerge' in fileBashTags:
                item_format.text_key = 'mods.text.noMerge'
                mouseText += _(u"Technically mergeable but has NoMerge tag.  ")
            else:
                item_format.text_key = 'mods.text.mergeable'
        #--Text BG
        if bosh.modInfos.isBadFileName(masters_name.s):
            if load_order.isActiveCached(masters_name):
                item_format.back_key = 'mods.bkgd.doubleTime.load'
            else:
                item_format.back_key = 'mods.bkgd.doubleTime.exists'
        elif masterInfo.hasActiveTimeConflict():
            item_format.back_key = 'mods.bkgd.doubleTime.load'
        elif masterInfo.isExOverLoaded():
            item_format.back_key = 'mods.bkgd.exOverload'
        elif masterInfo.hasTimeConflict():
            item_format.back_key = 'mods.bkgd.doubleTime.exists'
        elif masterInfo.isGhost:
            item_format.back_key = 'mods.bkgd.ghosted'
        if self.allowEdit:
            if masterInfo.oldName in settings['bash.mods.renames']:
                item_format.strong = True
        #--Image
        status = self.GetMasterStatus(mi)
        oninc = load_order.isActiveCached(masters_name) or (
            masters_name in bosh.modInfos.merged and 2)
        on_display = self.detailsPanel.displayed_item
        if status == 30: # master is missing
            mouseText += _(u"Missing master of %s.  ") % on_display
        #--HACK - load order status
        elif on_display in bosh.modInfos:
            if status == 20:
                mouseText += _(u"Reordered relative to other masters.  ")
            if load_order.loIndexCached(on_display) < load_order.loIndexCached(masters_name):
                mouseText += _(u"Loads after %s.  ") % on_display
                status = 20 # paint orange
        item_format.icon_key = status, oninc
        self.mouseTexts[mi] = mouseText

    #--Relist
    def _reList(self):
        fileOrderNames = [v.name for v in self.data_store.values()]
        self.loadOrderNames = load_order.get_ordered(fileOrderNames)

    #--InitEdit
    def InitEdit(self):
        #--Pre-clean
        edited = False
        for mi, masterInfo in self.data_store.items():
            newName = settings['bash.mods.renames'].get(masterInfo.name, None)
            #--Rename?
            if newName and newName in bosh.modInfos:
                masterInfo.setName(newName)
                edited = True
        #--Done
        if edited: self.SetMasterlistEdited(repopulate=True)

    def SetMasterlistEdited(self, repopulate=False):
        self._reList()
        if repopulate: self.PopulateItems()
        self.edited = True
        self.detailsPanel.SetEdited() # inform the details panel

    #--Column Menu
    def DoColumnMenu(self, event, column=None):
        if self.fileInfo: super(MasterList, self).DoColumnMenu(event, column)

    def OnLeftDown(self,event):
        if self.allowEdit: self.InitEdit()
        event.Skip()

    #--Events: Label Editing
    def OnBeginEditLabel(self, event):
        if not self.allowEdit:
            event.Veto()
        else: # pass event on (for label editing)
            super(MasterList, self).OnBeginEditLabel(event)

    def OnLabelEdited(self,event):
        itemDex = event.m_itemIndex
        newName = GPath(event.GetText())
        #--No change?
        if newName in bosh.modInfos:
            masterInfo = self.data_store[self.GetItem(itemDex)]
            masterInfo.setName(newName)
            self.SetMasterlistEdited()
            settings.getChanged('bash.mods.renames')[
                masterInfo.oldName] = newName
            self.PopulateItem(itemDex) # populate, refresh must be called last
        elif newName == u'':
            event.Veto()
        else:
            balt.showError(self,_(u'File %s does not exist.') % newName.s)
            event.Veto()

    #--GetMasters
    def GetNewMasters(self):
        """Returns new master list."""
        return [v.name for k, v in
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
    def filterOutDefaultTweaks(tweaks):
        """Filter out default tweaks from tweaks iterable."""
        return filter(lambda x: not bosh.iniInfos[x].is_default_tweak, tweaks)

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
        elif status == -10:
            # Bad tweak
            if not settings['bash.ini.allowNewLines']: icon = 20
            else: icon = 0
            mousetext = _(u'Tweak is invalid')
        if iniInfo.is_default_tweak:
            mousetext = _(u'Default Bash Tweak') + (
                (u'.  ' + mousetext) if mousetext else u'')
            item_format.italics = True
        self.mouseTexts[ini_name] = mousetext
        item_format.icon_key = icon, checkMark
        #--Font/BG Color
        if status < 0:
            item_format.back_key = 'ini.bkgd.invalid'

    def OnLeftDown(self,event):
        """Handle click on icon events"""
        event.Skip()
        hitItem = self._getItemClicked(event, on_icon=True)
        if not hitItem: return
        tweak = bosh.iniInfos[hitItem] # type: bosh.INIInfo
        if tweak.tweak_status == 20: return # already applied
        #-- If we're applying to Oblivion.ini, show the warning
        target, gameIni = self.data_store.ini, bosh.oblivionIni
        if target is gameIni and not gameIni.ask_create_game_ini(
                msg=_(u'The game ini must exist to apply a tweak to it.')):
            return
        choice = self.panel.detailsPanel.current_ini_path.tail
        if not self.warn_tweak_game_ini(choice): return
        target.applyTweakFile(tweak.read_ini_lines())
        self.panel.ShowPanel(refresh_target=True)

    @staticmethod
    @balt.conversation
    def warn_tweak_game_ini(choice):
        ask = True
        if choice in bush.game.iniFiles:
            message = (_(u"Apply an ini tweak to %s?") % choice + u'\n\n' + _(
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
                self.InsertStringItem(i, line[0])
            else:
                self.SetStringItem(i, 0, line[0])
            #--Line color
            status, deleted = line[4], line[6]
            if status == -10: color = colors['tweak.bkgd.invalid']
            elif status == 10: color = colors['tweak.bkgd.mismatched']
            elif status == 20: color = colors['tweak.bkgd.matched']
            elif deleted: color = colors['tweak.bkgd.mismatched']
            else: color = self.GetBackgroundColour()
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
        self.SetColumnWidth(0,wx.LIST_AUTOSIZE_USEHEADER)

#------------------------------------------------------------------------------
class TargetINILineCtrl(INIListCtrl):

    def SetTweakLinesCtrl(self, control):
        self._contents = control

    def _get_selected_line(self, index):
        for i, line in enumerate(self._contents.tweakLines):
            if index == line[5]: return i
        return -1

    def RefreshIniContents(self, new_target=False):
        if new_target:
            self.DeleteAllItems()
        num = self.GetItemCount()
        try:
            with bosh.iniInfos.ini.abs_path.open('r') as ini:
                lines = ini.readlines()
                for i,line in enumerate(lines):
                    if i >= num:
                        self.InsertStringItem(i, line.rstrip())
                    else:
                        self.SetStringItem(i, 0, line.rstrip())
                for i in xrange(len(lines), num):
                    self.DeleteItem(len(lines))
        except IOError:
            warn = True
            page = Link.Frame.notebook.currentPage
            if page != self.GetParent().GetParent().GetParent():
                warn = False
            Link.Frame.queue_game_ini_missing()
            if warn: Link.Frame.warn_game_ini()
        self.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)

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
        'Load Order': lambda self, a: load_order.loIndexCachedOrMax(a),
        'Modified'  : lambda self, a: self.data_store[a].mtime,
        'Size'      : lambda self, a: self.data_store[a].size,
        'Status'    : lambda self, a: self.data_store[a].getStatus(),
        'Mod Status': lambda self, a: self.data_store[a].txt_status(),
        'CRC'       : lambda self, a: self.data_store[a].cachedCrc(),
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
        ('Modified',   lambda self, p: formatDate(self.data_store[p].mtime)),
        ('Size',       lambda self, p: round_size(self.data_store[p].size)),
        ('Author',     lambda self, p: self.data_store[p].header.author if
                                       self.data_store[p].header else u'-'),
        ('CRC',        lambda self, p:
                                    u'%08X' % self.data_store[p].cachedCrc()),
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
        except bolt.BoltError as e:
            balt.showError(self, u'%s' % e)
        self.RefreshUI(refreshSaves=True)

    #--Populate Item
    def set_item_format(self, mod_name, item_format):
        modInfo = self.data_store[mod_name]
        #--Image
        status = modInfo.getStatus()
        checkMark = (
            1 if load_order.isActiveCached(mod_name)
            else 2 if mod_name in bosh.modInfos.merged
            else 3 if mod_name in bosh.modInfos.imported
            else 0)
        status_image_key = 20 if 20 <= status < 30 else status
        item_format.icon_key = status_image_key, checkMark
        #--Default message
        mouseText = u''
        fileBashTags = modInfo.getBashTags()
        if mod_name in bosh.modInfos.bad_names:
            mouseText += _(u'Plugin name incompatible, cannot be activated.  ')
        if mod_name in bosh.modInfos.missing_strings:
            mouseText += _(u'Plugin is missing String Localization files.  ')
        if modInfo.isEsm():
            item_format.text_key = 'mods.text.esm'
            mouseText += _(u"Master file. ")
        elif mod_name in bosh.modInfos.bashed_patches:
            item_format.text_key = 'mods.text.bashedPatch'
        elif mod_name in bosh.modInfos.mergeable:
            if u'NoMerge' in fileBashTags:
                item_format.text_key = 'mods.text.noMerge'
                mouseText += _(u"Technically mergeable but has NoMerge tag.  ")
            else:
                item_format.text_key = 'mods.text.mergeable'
                if checkMark == 2:
                    mouseText += _(u"Merged into Bashed Patch.  ")
                else:
                    mouseText += _(u"Can be merged into Bashed Patch.  ")
        #--Image messages
        if status == 30:
            mouseText += _(u"One or more masters are missing.  ")
        else:
            if status in {21, 22}:
                mouseText += _(u"Loads before its master(s).  ")
            if status in {20, 22}:
                mouseText += _(u"Masters have been re-ordered.  ")
        if checkMark == 1:   mouseText += _(u"Active in load list.  ")
        elif checkMark == 3: mouseText += _(u"Imported into Bashed Patch.  ")
        #should mod be deactivated
        if u'Deactivate' in fileBashTags:
            item_format.italics = True
        #--Text BG
        if mod_name in bosh.modInfos.bad_names:
            item_format.back_key ='mods.bkgd.doubleTime.exists'
        elif mod_name in bosh.modInfos.missing_strings:
            if load_order.isActiveCached(mod_name):
                item_format.back_key = 'mods.bkgd.doubleTime.load'
            else:
                item_format.back_key = 'mods.bkgd.doubleTime.exists'
        elif modInfo.hasBadMasterNames():
            if load_order.isActiveCached(mod_name):
                item_format.back_key = 'mods.bkgd.doubleTime.load'
            else:
                item_format.back_key = 'mods.bkgd.doubleTime.exists'
            mouseText += _(u"WARNING: Has master names that will not load.  ")
        elif modInfo.hasActiveTimeConflict():
            item_format.back_key = 'mods.bkgd.doubleTime.load'
            mouseText += _(u"WARNING: Has same load order as another mod.  ")
        elif u'Deactivate' in fileBashTags and checkMark == 1:
            item_format.back_key = 'mods.bkgd.deactivate'
            mouseText += _(u"Mod should be imported and deactivated.  ")
        elif modInfo.isExOverLoaded():
            item_format.back_key = 'mods.bkgd.exOverload'
            mouseText += _(u"WARNING: Exclusion group is overloaded.  ")
        elif modInfo.hasTimeConflict():
            item_format.back_key = 'mods.bkgd.doubleTime.exists'
            mouseText += _(u"Has same time as another (unloaded) mod.  ")
        elif modInfo.isGhost:
            item_format.back_key = 'mods.bkgd.ghosted'
            mouseText += _(u"File is ghosted.  ")
        if settings['bash.mods.scanDirty']:
            message = modInfo.getDirtyMessage()
            mouseText += message[1]
            if message[0]: item_format.underline = True
        self.mouseTexts[mod_name] = mouseText

    def RefreshUI(self, **kwargs):
        """Refresh UI for modList - always specify refreshSaves explicitly."""
        super(ModList, self).RefreshUI(**kwargs)
        if kwargs.pop('refreshSaves', False):
            Link.Frame.saveListRefresh(focus_list=False)

    #--Events ---------------------------------------------
    def OnDClick(self,event):
        """Handle doubleclicking a mod in the Mods List."""
        hitItem = self._getItemClicked(event)
        if not hitItem: return
        modInfo = self.data_store[hitItem]
        if not Link.Frame.docBrowser:
            from .frames import DocBrowser
            DocBrowser().Show()
            settings['bash.modDocs.show'] = True
        #balt.ensureDisplayed(docBrowser)
        Link.Frame.docBrowser.SetMod(modInfo.name)
        Link.Frame.docBrowser.Raise()

    def OnChar(self,event):
        """Char event: Reorder (Ctrl+Up and Ctrl+Down)."""
        code = event.GetKeyCode()
        if event.CmdDown() and code in balt.wxArrows:
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
        elif event.CmdDown() and code == 26:
            if self.data_store.undo_load_order():
                self.RefreshUI(refreshSaves=True)
        elif event.CmdDown() and code == 25:
            if self.data_store.redo_load_order():
                self.RefreshUI(refreshSaves=True)
        else: event.Skip() # correctly update the highlight around selected mod

    def OnKeyUp(self,event):
        """Char event: Activate selected items, select all items"""
        ##Space
        code = event.GetKeyCode()
        if code == wx.WXK_SPACE:
            selected = self.GetSelected()
            toActivate = [item for item in selected if
                          not load_order.isActiveCached(GPath(item))]
            if len(toActivate) == 0 or len(toActivate) == len(selected):
                #--Check/Uncheck all
                self._toggle_active_state(*selected)
            else:
                #--Check all that aren't
                self._toggle_active_state(*toActivate)
        # Ctrl+C: Copy file(s) to clipboard
        elif event.CmdDown() and code == ord('C'):
            sel = map(lambda mod: self.data_store[mod].getPath().s,
                      self.GetSelected())
            balt.copyListToClipboard(sel)
        super(ModList, self).OnKeyUp(event)

    def OnLeftDown(self,event):
        """Left Down: Check/uncheck mods."""
        mod_clicked_on_icon = self._getItemClicked(event, on_icon=True)
        if mod_clicked_on_icon:
            self._toggle_active_state(mod_clicked_on_icon)
            # select manually as OnSelectItem() will fire for the wrong
            # index if list is sorted with selected first
            self.SelectAndShowItem(mod_clicked_on_icon, deselectOthers=True, focus=True)
        else:
            mod_clicked = self._getItemClicked(event)
            if event.AltDown() and mod_clicked:
                if self.jump_to_mods_installer(mod_clicked): return
            #--Pass Event onward to OnSelectItem
            event.Skip()

    def _select(self, modName):
        super(ModList, self)._select(modName)
        if Link.Frame.docBrowser:
            Link.Frame.docBrowser.SetMod(modName)

    @staticmethod
    def _unhide_wildcard():
        return bush.game.displayName + u' ' + _(
            u'Mod Files') + u' (*.esp;*.esm)|*.esp;*.esm'

    #--Helpers ---------------------------------------------
    @balt.conversation
    def _toggle_active_state(self, *mods):
        """Toggle active state of mods given - all mods must be either
        active or inactive."""
        refreshNeeded = False
        keys = map(GPath, mods)
        active = [mod for mod in keys if load_order.isActiveCached(mod)]
        inactive = [mod for mod in keys if not load_order.isActiveCached(mod)]
        assert len(active) == len(keys) or len(inactive) == len(keys)
        changes = collections.defaultdict(dict)
        # Deactivate ?
        touched = set()
        for act in active:
            if act in touched: continue # already deactivated
            try:
                changed = self.data_store.lo_deactivate(act, doSave=False)
                refreshNeeded += len(changed)
                if len(changed) > (act in changed): # deactivated children
                    touched |= changed
                    changed = [x for x in changed if x != act]
                    changes[self.__deactivated_key][act] = load_order.get_ordered(changed)
            except BoltError as e:
                balt.showError(self, u'%s' % e)
        # Activate ?
        touched = set()
        for inact in inactive:
            if inact in touched: continue # already activated
            ## For now, allow selecting unicode named files, for testing
            ## I'll leave the warning in place, but maybe we can get the
            ## game to load these files.s
            #if fileName in self.data_store.bad_names: return
            try:
                activated = self.data_store.lo_activate(inact, doSave=False)
                refreshNeeded += len(activated)
                if len(activated) > (inact in activated):
                    touched |= set(activated)
                    activated = [x for x in activated if x != inact]
                    changes[self.__activated_key][inact] = activated
            except bolt.BoltError as e:
                balt.showError(self, u'%s' % e)
                break
        #--Refresh
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
        if not checklists: return
        ListBoxes.Display(self, _(u'Masters/Children affected'), msg,
                          [checklists], liststyle='tree', canCancel=False)

    def jump_to_mods_installer(self, modName):
        if not balt.Link.Frame.iPanel or not bass.settings[
            'bash.installers.enabled']: return False
        installer = self.data_store.table.getColumn('installer').get(modName)
        if installer is None:
            return False
        balt.Link.Frame.notebook.SelectPage('Installers', installer)
        return True

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
        """Set file to be viewed."""
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

    def __init__(self, buttonsParent):
        self.edited = False
        #--Save/Cancel
        self.save = SaveButton(buttonsParent, onButClick=self.DoSave)
        self.cancel = CancelButton(buttonsParent, onButClick=self.DoCancel)
        self.save.Disable()
        self.cancel.Disable()

    # Details panel API
    def SetFile(self, fileName='SAME'):
        #--Edit State
        self.edited = 0
        self.save.Disable()
        self.cancel.Disable()
        return super(_EditableMixin, self).SetFile(fileName)

    # Abstract edit methods
    @property
    def allowDetailsEdit(self): raise AbstractError

    def SetEdited(self):
        if not self.displayed_item: return
        self.edited = True
        if self.allowDetailsEdit:
            self.save.Enable()
        self.cancel.Enable()

    def DoSave(self): raise AbstractError

    def DoCancel(self): self.SetFile(self.displayed_item)

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
        _EditableMixin.__init__(self, masterPanel)
        #--File Name
        self.file = TextCtrl(self.top, onKillFocus=self.OnFileEdited,
                             onText=self.OnFileEdit,
                             maxChars=self._max_filename_chars,
                             size=(self._min_controls_width, -1))
        self.panel_uilist = ui_list_panel.uiList

    def OnFileEdited(self):
        """Event: Finished editing file name."""
        if not self.file_info: return
        #--Changed?
        fileStr = self.file.GetValue()
        if fileStr == self.fileStr: return
        #--Extension Changed?
        if fileStr[-4:].lower() != self.fileStr[-4:].lower():
            balt.showError(self,_(u"Incorrect file extension: ")+fileStr[-3:])
            self.file.SetValue(self.fileStr)
        #--Validate the filename - no need to check for extension again
        elif not self._validate_filename(fileStr):
            self.file.SetValue(self.fileStr)
        #--Else file exists?
        elif self.file_info.dir.join(fileStr).exists():
            balt.showError(self,_(u"File %s already exists.") % fileStr)
            self.file.SetValue(self.fileStr)
        #--Okay?
        else:
            self.fileStr = fileStr
            self.SetEdited()

    def _validate_filename(self, fileStr):
        return self.panel_uilist.validate_filename(None, fileStr)[0]

    def OnFileEdit(self, event):
        """Event: Editing filename."""
        if not self.file_info: return
        if not self.edited and self.fileStr != self.file.GetValue():
            self.SetEdited()
        event.Skip()

class _SashDetailsPanel(_EditableMixinOnFileInfos, SashPanel):
    """Mod and Saves details panel, feature a master's list.

    I named the master list attribute 'uilist' to stand out from the usual
    uiList of SashPanels.
    :type uilist: MasterList"""
    defaultSubSashPos = 0 # that was the default for mods (for saves 500)
    _subsplitterSashGravity = 1.0 # max resize the top (masters) panel

    def __init__(self, parent):
        SashPanel.__init__(self, parent, isVertical=False)
        self.top, self.bottom = self.left, self.right
        self.subSplitter = balt.Splitter(self.bottom)
        # split the bottom panel into the master uilist and mod tags/save notes
        self.masterPanel = wx.Panel(self.subSplitter)
        self._bottom_low_panel = wx.Panel(self.subSplitter)
        # needed so subpanels do not collapse
        self.subSplitter.SetMinimumPaneSize(64)
        self.subSplitter.SplitHorizontally(self.masterPanel,
                                           self._bottom_low_panel)
        self.subSplitter.SetSashGravity(self._subsplitterSashGravity)
        mod_or_save_panel = parent.GetParent().GetParent()
        _EditableMixinOnFileInfos.__init__(self, self.masterPanel,
                                           mod_or_save_panel)
        #--Masters
        self.uilist = MasterList(self.masterPanel, keyPrefix=self.keyPrefix,
                                 panel=mod_or_save_panel, detailsPanel=self)
        mastersSizer = vSizer(
            vspace(), hSizer(StaticText(self.masterPanel,_(u"Masters:"))),
            (hSizer((self.uilist,1,wx.EXPAND)),1,wx.EXPAND),
            vspace(), hSizer(self.save, hspace(), self.cancel))
        self.masterPanel.SetSizer(mastersSizer)

    def ShowPanel(self, **kwargs):
        if self._firstShow:
            super(_SashDetailsPanel, self).ShowPanel() # set sashPosition
            sashPos = settings.get(self.keyPrefix + '.subSplitterSashPos',
                                   self.__class__.defaultSubSashPos)
            self.subSplitter.SetSashPosition(sashPos)
        self.uilist.autosizeColumns()

    def ClosePanel(self, destroy=False):
        if not self._firstShow:
            # Mod details Sash Positions
            settings[self.sashPosKey] = self.splitter.GetSashPosition()
            settings[self.keyPrefix + '.subSplitterSashPos'] = \
                self.subSplitter.GetSashPosition()

    def testChanges(self): raise AbstractError

class ModDetails(_SashDetailsPanel):
    """Details panel for mod tab."""
    keyPrefix = 'bash.mods.details' # used in sash/scroll position, sorting

    @property
    def file_info(self): return self.modInfo
    @property
    def file_infos(self): return bosh.modInfos
    @property
    def allowDetailsEdit(self): return bush.game.esp.canEditHeader

    def __init__(self, parent):
        super(ModDetails, self).__init__(parent)
        subSplitter, masterPanel = self.subSplitter, self.masterPanel
        top, bottom = self.top, self.bottom
        #--Data
        self.modInfo = None
        textWidth = 200
        #--Version
        self.version = StaticText(top,u'v0.00')
        #--Author
        self.author = TextCtrl(top, onKillFocus=self.OnEditAuthor,
                               onText=self.OnAuthorEdit, maxChars=511) # size=(textWidth,-1))
        #--Modified
        self.modified = TextCtrl(top,size=(textWidth, -1),
                                 onKillFocus=self.OnEditModified,
                                 onText=self.OnModifiedEdit, maxChars=32)
        #--Description
        self.description = TextCtrl(top, size=(textWidth, 128),
                                    multiline=True, autotooltip=False,
                                    onKillFocus=self.OnEditDescription,
                                    onText=self.OnDescrEdit, maxChars=511)
        #--Bash tags
        self.gTags = RoTextCtrl(self._bottom_low_panel, autotooltip=False,
                                size=(textWidth, 64))
        #--Layout
        detailsSizer = vSizer(vspace(),
            (hSizer(
                (StaticText(top,_(u"File:"))), hspacer,
                self.version, hspace()
                ),0,wx.EXPAND),
            (hSizer((self.file,1,wx.EXPAND)),0,wx.EXPAND),
            vspace(), (hSizer(StaticText(top,_(u"Author:"))),0,wx.EXPAND),
            (hSizer((self.author,1,wx.EXPAND)),0,wx.EXPAND),
            vspace(), (hSizer(StaticText(top,_(u"Modified:"))),0,wx.EXPAND),
            (hSizer((self.modified,1,wx.EXPAND)),0,wx.EXPAND),
            vspace(), (hSizer(StaticText(top,_(u"Description:"))),0,wx.EXPAND),
            (hSizer((self.description,1,wx.EXPAND)),1,wx.EXPAND))
        detailsSizer.SetSizeHints(top)
        top.SetSizer(detailsSizer)
        tagsSizer = vSizer(vspace(),
            (StaticText(self._bottom_low_panel, _(u"Bash Tags:"))),
            (hSizer((self.gTags, 1, wx.EXPAND)), 1, wx.EXPAND))
        tagsSizer.SetSizeHints(masterPanel)
        self._bottom_low_panel.SetSizer(tagsSizer)
        bottom.SetSizer(vSizer((subSplitter,1,wx.EXPAND)))
        #--Events
        self.gTags.Bind(wx.EVT_CONTEXT_MENU,
                        lambda __event: self.ShowBashTagsMenu())

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
            self.modifiedStr = formatDate(modInfo.mtime)
            self.descriptionStr = modInfo.header.description
            self.versionStr = u'v%0.2f' % modInfo.header.version
            tagsStr = u'\n'.join(sorted(modInfo.getBashTags()))
        else: tagsStr = u''
        self.modified.SetEditable(True)
        self.modified.SetBackgroundColour(self.author.GetBackgroundColour())
        #--Set fields
        self.file.SetValue(self.fileStr)
        self.author.SetValue(self.authorStr)
        self.modified.SetValue(self.modifiedStr)
        self.description.SetValue(self.descriptionStr)
        self.version.SetLabel(self.versionStr)
        self.uilist.SetFileInfo(self.modInfo)
        self.gTags.SetValue(tagsStr)
        if fileName and not bosh.modInfos.table.getItem(fileName,'autoBashTags', True):
            self.gTags.SetBackgroundColour(self.author.GetBackgroundColour())
        else:
            self.gTags.SetBackgroundColour(self.GetBackgroundColour())
        self.gTags.Refresh()

    def _OnTextEdit(self, event, value, control):
        if not self.modInfo: return
        if not self.edited and value != control.GetValue(): self.SetEdited()
        event.Skip()
    def OnAuthorEdit(self, event):
        self._OnTextEdit(event, self.authorStr, self.author)
    def OnModifiedEdit(self, event):
        self._OnTextEdit(event, self.modifiedStr, self.modified)
    def OnDescrEdit(self, event):
        self._OnTextEdit(event, self.descriptionStr.replace(
            '\r\n', '\n').replace('\r', '\n'), self.description)

    def OnEditAuthor(self):
        if not self.modInfo: return
        authorStr = self.author.GetValue()
        if authorStr != self.authorStr:
            self.authorStr = authorStr
            self.SetEdited()

    def OnEditModified(self):
        if not self.modInfo: return
        modifiedStr = self.modified.GetValue()
        if modifiedStr == self.modifiedStr: return
        try:
            newTimeTup = bolt.unformatDate(modifiedStr, u'%c')
            time.mktime(newTimeTup)
        except ValueError:
            balt.showError(self,_(u'Unrecognized date: ')+modifiedStr)
            self.modified.SetValue(self.modifiedStr)
            return
        #--Normalize format
        modifiedStr = time.strftime(u'%c',newTimeTup)
        self.modifiedStr = modifiedStr
        self.modified.SetValue(modifiedStr) #--Normalize format
        self.SetEdited()

    def OnEditDescription(self):
        if not self.modInfo: return
        if self.description.GetValue() != self.descriptionStr.replace('\r\n',
                '\n').replace('\r', '\n'):
            self.descriptionStr = self.description.GetValue() ##: .replace('\n', 'r\n')
            self.SetEdited()

    bsaAndVoice = _(u'This mod has an associated archive (%s.' +
                    bush.game.bsa_extension + u') and an '
        u'associated voice directory (Sound\\Voices\\%s), which will become '
        u'detached when the mod is renamed.') + u'\n\n' + _(u'Note that the '
        u'BSA archive may also contain a voice directory (Sound\\Voices\\%s), '
        u'which would remain detached even if the archive name is adjusted.')
    bsa = _(u'This mod has an associated archive (%s.' +
                    bush.game.bsa_extension + u'), which will become '
        u'detached when the mod is renamed.') + u'\n\n' + _(u'Note that this '
        u'BSA archive may contain a voice directory (Sound\\Voices\\%s), which'
        u' would remain detached even if the archive file name is adjusted.')
    voice = _(u'This mod has an associated voice directory (Sound\\Voice\\%s),'
        u' which will become detached when the mod is renamed.')

    def _askResourcesOk(self, fileInfo):
        return bosh.modInfos.askResourcesOk(fileInfo, parent=self,
            title=_(u'Rename '), bsaAndVoice=self.bsaAndVoice, bsa=self.bsa,
            voice=self.voice)

    def testChanges(self): # used by the master list when editing is disabled
        modInfo = self.modInfo
        if not modInfo or (self.fileStr == modInfo.name and
                self.modifiedStr == formatDate(modInfo.mtime) and
                self.authorStr == modInfo.header.author and
                self.descriptionStr == modInfo.header.description):
            self.DoCancel()

    def DoSave(self):
        modInfo = self.modInfo
        #--Change Tests
        changeName = (self.fileStr != modInfo.name)
        changeDate = (self.modifiedStr != formatDate(modInfo.mtime))
        changeHedr = (self.authorStr != modInfo.header.author or
                      self.descriptionStr != modInfo.header.description)
        changeMasters = self.uilist.edited
        #--Warn on rename if file has BSA and/or dialog
        if changeName and not self._askResourcesOk(modInfo): return
        #--Only change date?
        if changeDate and not (changeName or changeHedr or changeMasters):
            newTimeTup = bolt.unformatDate(self.modifiedStr, u'%c')
            newTimeInt = int(time.mktime(newTimeTup))
            modInfo.setmtime(newTimeInt)
            self.SetFile(self.displayed_item)
            with load_order.Unlock():
                bosh.modInfos.refresh(refresh_infos=False, _modTimesChange=True)
            BashFrame.modList.RefreshUI( # refresh saves if lo changed
                refreshSaves=not load_order.using_txt_file())
            return
        #--Backup
        modInfo.makeBackup()
        #--Change Name?
        fileName = modInfo.name
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
                fileName = newName
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
        if changeDate or changeHedr or changeMasters:
            newTimeTup = bolt.unformatDate(self.modifiedStr, u'%c')
            newTimeInt = int(time.mktime(newTimeTup))
            modInfo.setmtime(newTimeInt)
        #--Done
        try:
            bosh.modInfos.refreshFile(fileName)
            self.SetFile(fileName)
        except bosh.FileError:
            balt.showError(self,_(u'File corrupted on save!'))
            self.SetFile(None)
        with load_order.Unlock():
            bosh.modInfos.refresh(refresh_infos=False, _modTimesChange=changeDate)
        refreshSaves = changeName or (
            changeDate and not load_order.using_txt_file())
        self.panel_uilist.RefreshUI(refreshSaves=refreshSaves)
        self.panel_uilist.SelectAndShowItem(self.modInfo.name)

    #--Bash Tags
    def ShowBashTagsMenu(self):
        """Show bash tags menu."""
        if not self.modInfo: return
        #--Links closure
        mod_info = self.modInfo
        mod_tags = mod_info.getBashTags()
        is_auto = bosh.modInfos.table.getItem(mod_info.name, 'autoBashTags',
                                              True)
        def _refreshUI(): self.panel_uilist.RefreshUI(files=[mod_info.name],
                refreshSaves=False) # why refresh saves when updating tags (?)
        def _isAuto():
            return bosh.modInfos.table.getItem(mod_info.name, 'autoBashTags')
        def _setAuto(to):
            bosh.modInfos.table.setItem(mod_info.name, 'autoBashTags', to)
        # Toggle auto Bash tags
        class _TagsAuto(CheckLink):
            text = _(u'Automatic')
            help = _(
                u"Use the tags from the description and masterlist/userlist.")
            def _check(self): return is_auto
            def Execute(self):
                """Handle selection of automatic bash tags."""
                _setAuto(not _isAuto()) # toggle
                if _isAuto(): mod_info.reloadBashTags()
                _refreshUI()
        # Copy tags to mod description
        bashTagsDesc = mod_info.getBashTagsDesc()
        class _CopyDesc(EnabledLink):
            text = _(u'Copy to Description')
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
            def _initData(self, window, selection):
                super(_TagLink, self)._initData(window, selection)
                self.help = _(u"Add %(tag)s to %(modname)s") % (
                    {'tag': self.text, 'modname': mod_info.name})
            def _check(self): return self.text in mod_tags
            def Execute(self):
                """Toggle bash tag from menu."""
                if _isAuto(): _setAuto(False)
                modTags = mod_tags ^ {self.text}
                mod_info.setBashTags(modTags)
                _refreshUI()
        # Menu
        class _TagLinks(ChoiceLink):
            choiceLinkType = _TagLink
            def __init__(self):
                super(_TagLinks, self).__init__()
                self.extraItems = [_TagsAuto(), _CopyDesc(), SeparatorLink()]
            @property
            def _choices(self): return bosh.allTags
        ##: Popup the menu - ChoiceLink should really be a Links subclass
        tagLinks = Links()
        tagLinks.append(_TagLinks())
        tagLinks.PopupMenu(self.gTags, Link.Frame, None)

#------------------------------------------------------------------------------
class INIDetailsPanel(_DetailsMixin, SashPanel):
    """:type target_inis: dict[unicode, bolt.Path]"""
    keyPrefix = 'bash.ini.details'

    @property
    def displayed_item(self): return self._ini_detail
    @property
    def file_infos(self): return bosh.iniInfos

    def __init__(self, parent):
        super(INIDetailsPanel, self).__init__(parent, isVertical=True)
        self._ini_panel = parent.GetParent().GetParent()
        self._ini_detail = None
        left,right = self.left, self.right
        #--Remove from list button
        self.button = balt.Button(right, _(u'Remove'),
                                  onButClick=self._OnRemove)
        #--Edit button
        self.editButton = balt.Button(right, _(u'Edit...'),
                                      onButClick=self._OnEdit)
        #--Choices
        self.target_inis = settings['bash.ini.choices'] # set in IniInfos init
        self.choice = settings['bash.ini.choice'] # type: int
        if self.choice == -1: # ini removed
            self.choice, previous_ini = 0, None
        else:
            previous_ini = self.target_inis.keys()[self.choice]
        self.SortChoices()
        if previous_ini:
            self.choice = self.target_inis.keys().index(previous_ini)
        self.lastDir = settings.get('bash.ini.lastDir', bass.dirs['mods'].s)
        #--Ini file
        self.iniContents = TargetINILineCtrl(right)
        #--Tweak file
        self.tweakContents = INITweakLineCtrl(left, self.iniContents)
        self.iniContents.SetTweakLinesCtrl(self.tweakContents)
        self.tweakName = RoTextCtrl(left, noborder=True, multiline=False)
        self._enable_buttons()
        self.comboBox = balt.ComboBox(right, value=self.ini_name,
                                      choices=self.target_inis.keys())
        #--Events
        self.comboBox.Bind(wx.EVT_COMBOBOX,self.OnSelectDropDown)
        #--Layout
        iniSizer = vSizer(
                (hSizer(
                    (self.comboBox,1,wx.ALIGN_CENTER|wx.EXPAND|wx.TOP,1),
                    ((4,0),0),
                    (self.button,0,wx.ALIGN_TOP,0),
                    (self.editButton,0,wx.ALIGN_TOP,0),
                    ),0,wx.EXPAND), vspace(),
                (self.iniContents,1,wx.EXPAND),
                )
        right.SetSizer(iniSizer)
        iniSizer.SetSizeHints(right)
        lSizer = hSizer(
            (vSizer(
                vspace(6), (self.tweakName,0,wx.EXPAND),
                (self.tweakContents,1,wx.EXPAND),
                ),1,wx.EXPAND),
            )
        left.SetSizer(lSizer)

    @property
    def current_ini_path(self):
        """ Return path of currently chosen ini."""
        return self.target_inis.values()[self.choice]

    @property
    def ini_name(self): return self.target_inis.keys()[self.choice]

    def _resetDetails(self): pass

    def SetFile(self, fileName='SAME'):
        fileName = super(INIDetailsPanel, self).SetFile(fileName)
        self._ini_detail = fileName
        self.tweakContents.RefreshTweakLineCtrl(fileName)
        self.tweakName.SetValue(fileName.sbody if fileName else u'')

    def _enable_buttons(self):
        isGameIni = bosh.iniInfos.ini in bosh.gameInis
        self.button.Enable(not isGameIni)
        self.editButton.Enable(not isGameIni or self.current_ini_path.isfile())

    def _OnRemove(self):
        """Called when the 'Remove' button is pressed."""
        del self.target_inis[self.ini_name]
        self.choice -= 1
        self.comboBox.SetItems(self.SortChoices())
        self.ShowPanel(target_changed=True)
        self._ini_panel.uiList.RefreshUI()

    def _clean_targets(self):
        resort = False
        for name, ini_path in self.target_inis.iteritems():
            if ini_path is not None and not ini_path.isfile():
                for iFile in bosh.gameInis:
                    if iFile.abs_path == ini_path:
                        break
                else:
                    del self.target_inis[name]
                    self.choice -= 1
                    resort = True
        if resort: self.comboBox.SetItems(self.SortChoices())

    def _OnEdit(self):
        """Called when the 'Edit' button is pressed."""
        selection = self.comboBox.GetValue()
        self.target_inis[selection].start()

    def SortChoices(self):
        """Sorts the list of target INIs alphabetically, but with
        Oblivion.ini at the top and 'Browse...' at the bottom"""
        keys = self.target_inis.keys()
        # Sort alphabetically
        keys.sort()
        # Sort Oblivion.ini to the top, and 'Browse...' to the bottom
        len_inis = len(bush.game.iniFiles)
        keys.sort(key=lambda a:
                  bush.game.iniFiles.index(a) if a in bush.game.iniFiles
                  else (len_inis + 1 if a == _(u'Browse...') else len_inis))
        self.target_inis = collections.OrderedDict(
            [(k, self.target_inis[k]) for k in keys])
        return keys

    def add_targets(self, paths):
        for abs_target_path in paths:
            if abs_target_path.stail not in self.target_inis:
                current_choice = self.ini_name
                self.target_inis[abs_target_path.stail] = abs_target_path
                self.comboBox.SetItems(self.SortChoices())
                self.choice = self.target_inis.keys().index(current_choice)

    def set_choice(self, target_path):
        self.choice = self.target_inis.keys().index(target_path.stail)

    def OnSelectDropDown(self,event):
        """Called when the user selects a new target INI from the drop down."""
        selection = event.GetString()
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
                full_path.stail in self.target_inis and
                self.choice == self.target_inis.keys().index(full_path.stail)):
                self.comboBox.SetSelection(self.choice)
                return
        # new file or selected an existing one different from current choice
        if full_path.stail not in self.target_inis: # added
            self.target_inis[full_path.stail] = full_path
            self.comboBox.SetItems(self.SortChoices()) # to set self.choice
        self.choice = self.target_inis.keys().index(full_path.stail)
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
        self.comboBox.SetSelection(self.choice)

    def ClosePanel(self, destroy=False):
        super(INIDetailsPanel, self).ClosePanel(destroy)
        settings['bash.ini.choices'] = self.target_inis
        settings['bash.ini.choice'] = self.choice
        settings['bash.ini.lastDir'] = self.lastDir
        if destroy: self.comboBox.Unbind(wx.EVT_SIZE)

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

    def ShowPanel(self, refresh_infos=False, refresh_target=False,
                  clean_targets=False, focus_list=True, **kwargs):
        changes = bosh.iniInfos.refresh(refresh_infos=refresh_infos,
                                        refresh_target=refresh_target)
        super(INIPanel, self).ShowPanel(target_changed=changes and changes[3],
                                        clean_targets=clean_targets)
        if changes: # we need this to be more granular
            self.uiList.RefreshUI(focus_list=focus_list) # resets the details

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

    def _sbCount(self): return _(u'Mods:') + u' %d/%d' % (
        len(load_order.activeCached()), len(bosh.modInfos))

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
        playMinutes = saveInfo.header.gameTicks / 60000
        return u'%d:%02d' % (playMinutes/60, (playMinutes % 60))
    labels = OrderedDict([
        ('File',     lambda self, p: p.s),
        ('Modified', lambda self, p: formatDate(self.data_store[p].mtime)),
        ('Size',     lambda self, p: round_size(self.data_store[p].size)),
        ('PlayTime', lambda self, p: self._playTime(self.data_store[p])),
        ('Player',   lambda self, p: self._headInfo(self.data_store[p],
                                                    'pcName')),
        ('Cell',     lambda self, p: self._headInfo(self.data_store[p],
                                                    'pcLocation')),
    ])

    __ext_group = u'(\.(' + bush.game.ess.ext[1:] + u'|' + \
                  bush.game.ess.ext[1:-1] + u'r' + u'))' # add bak !!!
    def validate_filename(self, event, name_new=None, has_digits=False,
                          ext=u'', is_filename=True, _old_path=None):
        if _old_path and bosh.saveInfos.bak_file_pattern.match(_old_path.s): ##: YAK add cosave support for bak
            balt.showError(self, _(u'Renaming bak files is not supported.'))
            return None, None, None
        return super(SaveList, self).validate_filename(event, name_new,
            has_digits=has_digits, ext=self.__ext_group,
            is_filename=is_filename)

    def OnLabelEdited(self, event):
        """Savegame renamed."""
        root, newName, _numStr = self.validate_filename(event)
        if not root: return
        detail_item = self.panel.GetDetailsItem()
        item_edited = [detail_item.name if detail_item else None]
        selected = [s for s in self.GetSelected() if
                    not bosh.saveInfos.bak_file_pattern.match(s.s)] # YAK !
        to_select = set()
        for save_key in selected:
            newFileName = self.new_name(newName)
            if not self._try_rename(save_key, newFileName, to_select,
                                    item_edited): break
        if to_select:
            self.RefreshUI()
            #--Reselect the renamed items
            self.SelectItemsNoCallback(to_select)
            if item_edited[0]: self.SelectItem(item_edited[0])
        event.Veto() # needed ! clears new name from label on exception

    @staticmethod
    def _unhide_wildcard():
        starred = u'*' + bush.game.ess.ext
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
    def OnKeyUp(self,event):
        code = event.GetKeyCode()
        # Ctrl+C: Copy file(s) to clipboard
        if event.CmdDown() and code == ord('C'):
            sel = map(lambda save: self.data_store[save].getPath().s,
                      self.GetSelected())
            balt.copyListToClipboard(sel)
        super(SaveList, self).OnKeyUp(event)

    def OnLeftDown(self,event):
        #--Pass Event onward
        event.Skip()
        hitItem = self._getItemClicked(event, on_icon=True)
        if not hitItem: return
        msg = _(u"Clicking on a save icon will disable/enable the save "
                u"by changing its extension to %(ess)s (enabled) or .esr "
                u"(disabled). Autosaves and quicksaves will be left alone."
                 % {'ess': bush.game.ess.ext})
        if not balt.askContinue(self, msg, 'bash.saves.askDisable.continue'):
            return
        newEnabled = not bosh.SaveInfos.is_save_enabled(hitItem)
        newName = self.data_store.enable(hitItem, newEnabled)
        if newName != hitItem: self.RefreshUI() ##: files=[fileName]

#------------------------------------------------------------------------------
class SaveDetails(_SashDetailsPanel):
    """Savefile details panel."""
    keyPrefix = 'bash.saves.details' # used in sash/scroll position, sorting

    @property
    def file_info(self): return self.saveInfo
    @property
    def file_infos(self): return bosh.saveInfos
    @property
    def allowDetailsEdit(self): return bush.game.ess.canEditMasters

    def __init__(self,parent):
        super(SaveDetails, self).__init__(parent)
        subSplitter, masterPanel = self.subSplitter, self.masterPanel
        top, bottom = self.top, self.bottom
        #--Data
        self.saveInfo = None
        textWidth = 200
        #--Player Info
        self._resetDetails()
        self.playerInfo = StaticText(top,u" \n \n ")
        self._set_player_info_label()
        self.gCoSaves = StaticText(top,u'--\n--')
        #--Picture
        self.picture = balt.Picture(top, textWidth, 192 * textWidth / 256,
            background=colors['screens.bkgd.image']) #--Native: 256x192
        #--Save Info
        self.gInfo = TextCtrl(self._bottom_low_panel, size=(textWidth, 64),
                              multiline=True, onText=self.OnInfoEdit,
                              maxChars=2048)
        #--Layout
        detailsSizer = vSizer(
            vspace(), (self.file,0,wx.EXPAND),
            vspace(), (hSizer(
                (self.playerInfo,1,wx.EXPAND), (self.gCoSaves,0,wx.EXPAND),)
            ,0,wx.EXPAND),
            vspace(), (self.picture,1,wx.EXPAND),
            )
        detailsSizer.SetSizeHints(top)
        top.SetSizer(detailsSizer)
        noteSizer = vSizer(vspace(),
            (StaticText(self._bottom_low_panel, _(u"Save Notes:"))),
            (hSizer((self.gInfo,1,wx.EXPAND)),1,wx.EXPAND),
            )
        noteSizer.SetSizeHints(masterPanel)
        self._bottom_low_panel.SetSizer(noteSizer)
        bottom.SetSizer(vSizer((subSplitter,1,wx.EXPAND)))

    def _resetDetails(self):
        self.saveInfo = None
        self.fileStr = u''
        self.playerNameStr = u''
        self.curCellStr = u''
        self.playerLevel = 0
        self.gameDays = 0
        self.playMinutes = 0
        self.picData = None
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
            self.playMinutes = saveInfo.header.gameTicks/60000
            self.playerLevel = saveInfo.header.pcLevel
            self.picData = saveInfo.header.image
            self.coSaves = u'%s\n%s' % saveInfo.coSaves().getTags()
        #--Set Fields
        self.file.SetValue(self.fileStr)
        self._set_player_info_label()
        self.gCoSaves.SetLabel(self.coSaves)
        self.uilist.SetFileInfo(self.saveInfo)
        #--Picture
        if not self.picData:
            self.picture.SetBitmap(None)
        else:
            width,height,data = self.picData
            image = Image.GetImage(data, height, width)
            self.picture.SetBitmap(image.ConvertToBitmap())
        #--Info Box
        self.gInfo.DiscardEdits()
        note_text = bosh.saveInfos.table.getItem(fileName, 'info',
                                                 u'') if fileName else u''
        self.gInfo.SetValue(note_text)

    def _set_player_info_label(self):
        self.playerInfo.SetLabel((self.playerNameStr + u'\n' +
            _(u'Level') + u' %d, ' + _(u'Day') + u' %d, ' +
            _(u'Play') + u' %d:%02d\n%s') % (
            self.playerLevel, int(self.gameDays), self.playMinutes / 60,
            (self.playMinutes % 60), self.curCellStr))

    def OnInfoEdit(self,event):
        """Info field was edited."""
        if self.saveInfo and self.gInfo.IsModified():
            bosh.saveInfos.table.setItem(self.saveInfo.name, 'info',
                                         self.gInfo.GetValue())
        event.Skip() # not strictly needed - no other handler for onKillFocus

    def _validate_filename(self, fileStr):
        return self.panel_uilist.validate_filename(
            None, fileStr, _old_path=self.saveInfo.name)[0]

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
        saveInfo.makeBackup()
        prevMTime = saveInfo.mtime
        #--Change Name?
        if changeName:
            (oldName,newName) = (saveInfo.name,GPath(self.fileStr.strip()))
            try:
                bosh.saveInfos.rename_info(oldName, newName)
            except (CancelError, OSError, IOError):
                pass
        #--Change masters?
        if changeMasters:
            saveInfo.header.masters = self.uilist.GetNewMasters()
            saveInfo.header.writeMasters(saveInfo.getPath())
            saveInfo.setmtime(prevMTime)
        #--Done
        try:
            bosh.saveInfos.refreshFile(saveInfo.name)
            self.SetFile(self.saveInfo.name)
        except bosh.FileError:
            balt.showError(self,_(u'File corrupted on save!'))
            self.SetFile(None)
        # files=[saveInfo.name], Nope: deleted oldName drives _gList nuts
        self.panel_uilist.RefreshUI()
        self.panel_uilist.SelectAndShowItem(self.saveInfo.name)

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
        if not bush.game.ess.canReadBasic:
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
            items.sort(key=lambda x: not self.data_store[x].isActive)
    def _sortProjects(self, items):
        if settings['bash.installers.sortProjects']:
            items.sort(key=lambda x: not isinstance(self.data_store[x],
                                                    bosh.InstallerProject))
    _extra_sortings = [_sortStructure, _sortActive, _sortProjects]
    #--Labels
    labels = OrderedDict([
        ('Package',  lambda self, p: p.s),
        ('Order',    lambda self, p: unicode(self.data_store[p].order)),
        ('Modified', lambda self, p: formatDate(self.data_store[p].modified)),
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
        text = u''
        if installer.dirty_sizeCrc:
            item_format.back_key = 'installers.bkgd.dirty'
            text += _(u'Needs Annealing due to a change in configuration.')
        elif installer.underrides:
            item_format.back_key = 'installers.bkgd.outOfOrder'
            text += _(u'Needs Annealing due to a change in Install Order.')
        #--Icon
        item_format.icon_key = 'on' if installer.isActive else 'off'
        item_format.icon_key += '.' + self._status_color[installer.status]
        if installer.type < 0: item_format.icon_key = 'corrupt'
        elif isinstance(installer, bosh.InstallerProject): item_format.icon_key += '.dir'
        if settings['bash.installers.wizardOverlay'] and installer.hasWizard:
            item_format.icon_key += '.wiz'
        #if textKey == 'installers.text.invalid': # I need a 'text.markers'
        #    text += _(u'Marker Package. Use for grouping installers together')
        #--TODO: add mouse  mouse tips
        self.mouseTexts[item] = text

    __renaming_type = None # type of items currently being renamed
    def OnBeginEditLabel(self,event):
        """Start renaming installers"""
        to_rename = self.GetSelected()
        #--Only rename multiple items of the same type
        self.__renaming_type = type(self.data_store[to_rename[0]])
        for item in to_rename[1:]:
            if not isinstance(self.data_store[item], self.__renaming_type):
                balt.showError(self, _(
                    u"Bash can't rename mixed installers types"))
                event.Veto()
                return
            #--Also, don't allow renaming the 'Last' marker
            elif item == u'==Last==':
                event.Veto()
                return
        self.edit_control.Bind(wx.EVT_CHAR, self._OnEditLabelChar)
        #--Markers, change the selection to not include the '=='
        if self.__renaming_type is bosh.InstallerMarker:
            to = len(event.GetLabel()) - 2
            self.edit_control.SetSelection(2, to)
        #--Archives, change the selection to not include the extension
        elif self.__renaming_type is bosh.InstallerArchive:
            super(InstallersList, self).OnBeginEditLabel(event)

    def _OnEditLabelChar(self, event):
        """For pressing F2 on the edit box for renaming"""
        if event.GetKeyCode() == wx.WXK_F2:
            editbox = self.edit_control
            # (start, stop), if start==stop there is no selection
            selection_span = editbox.GetSelection()
            text = editbox.GetValue()
            lenWithExt = len(text)
            if selection_span[0] != 0:
                selection_span = (0,lenWithExt)
            selectedText = GPath(text[selection_span[0]:selection_span[1]])
            textNextLower = selectedText.body
            if textNextLower == selectedText:
                lenNextLower = lenWithExt
            else:
                lenNextLower = len(textNextLower.s)
            if self.__renaming_type is bosh.InstallerArchive:
                selection_span = (0, lenNextLower)
            elif self.__renaming_type is bosh.InstallerMarker:
                selection_span = (2, lenWithExt - 2)
            else:
                selection_span = (0, lenWithExt)
            editbox.SetSelection(*selection_span)
        else:
            event.Skip()

    __ext_group = \
        u'(\.(' + ur'|'.join(ext[1:] for ext in archives.readExts) + u')+)'
    def OnLabelEdited(self, event):
        """Renamed some installers"""
        selected = self.GetSelected()
        installables = self.data_store.filterInstallables(selected)
        validate = partial(self.validate_filename, event,
                           is_filename=bool(installables))
        if self.__renaming_type is bosh.InstallerArchive:
            root, newName, _numStr = validate(ext=self.__ext_group)
        else:
            root, newName, _numStr = validate()
        if not root: return
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
            event.Veto()

    @staticmethod
    def _unhide_wildcard():
        starred = u';'.join(archives.readExts)
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

    def _extractOmods(self, omodnames):
        failed = []
        completed = []
        progress = balt.Progress(_(u'Extracting OMODs...'), u'\n' + u' ' * 60,
                                 abort=True)
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
            progress.Destroy()

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
            with balt.Dialog(self,_(u'Move or Copy?')) as dialog:
                icon = staticBitmap(dialog)
                gCheckBox = checkBox(dialog,
                                     _(u"Don't show this in the future."))
                sizer = vSizer(
                    (hSizer(
                        (icon,0,wx.ALL,6), hspace(6),
                        (StaticText(dialog,message),1,wx.EXPAND),
                        ),1,wx.EXPAND|wx.ALL,6),
                    (gCheckBox,0,wx.EXPAND|wx.ALL^wx.TOP,6),
                    (hSizer(
                        hspacer,
                        balt.Button(dialog,label=_(u'Move'),
                                    onButClick=lambda: dialog.EndModal(1)),
                        hspace(),
                        balt.Button(dialog, label=_(u'Copy'),
                                    onButClick=lambda: dialog.EndModal(2)),
                        hspace(), CancelButton(dialog),
                        ),0,wx.EXPAND|wx.ALL^wx.TOP,6),
                    )
                dialog.SetSizer(sizer)
                result = dialog.ShowModal() # buttons call dialog.EndModal(1/2)
                if result == 1: action = 'MOVE'
                elif result == 2: action = 'COPY'
                if gCheckBox.GetValue():
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
        if len(omodnames) > 0: self._extractOmods(omodnames)
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

    def OnChar(self,event):
        """Char event: Reorder."""
        code = event.GetKeyCode()
        ##Ctrl+Up/Ctrl+Down - Move installer up/down install order
        if event.CmdDown() and code in balt.wxArrows:
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
        elif event.CmdDown() and code == ord('V'):
            ##Ctrl+V
            balt.clipboardDropFiles(10, self.OnDropFiles)
        # Enter: Open selected installers
        elif code in balt.wxReturn: self.OpenSelected()
        else:
            event.Skip()

    def OnDClick(self,event):
        """Double click, open the installer."""
        event.Skip()
        item = self._getItemClicked(event)
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

    def OnKeyUp(self,event):
        """Char events: Action depends on keys pressed"""
        code = event.GetKeyCode()
        # Ctrl+Shift+N - Add a marker
        if event.CmdDown() and event.ShiftDown() and code == ord('N'):
            self.addMarker()
        # Ctrl+C: Copy file(s) to clipboard
        elif event.CmdDown() and code == ord('C'):
            sel = map(lambda x: bass.dirs['installers'].join(x).s,
                      self.GetSelected())
            balt.copyListToClipboard(sel)
        super(InstallersList, self).OnKeyUp(event)

    # Installer specific ------------------------------------------------------
    def addMarker(self):
        selected_installers = self.GetSelected()
        if selected_installers:
            pairs = self.data_store.sorted_pairs(selected_installers)
            max_order = pairs[-1][1].order + 1 # place it after last selected
        else:
            max_order = None
        new_marker = GPath(u'====')
        try:
            index = self.GetIndex(new_marker)
        except KeyError: # u'====' not found in the internal dictionary
            self.data_store.add_marker(u'====', max_order)
            self.RefreshUI() # why refresh mods/saves/inis when adding a marker
            index = self.GetIndex(new_marker)
        if index != -1:
            self.ClearSelected()
            self.SelectItemAtIndex(index)
            self.Rename([new_marker])

    def rescanInstallers(self, toRefresh, abort, update_from_data=True,
                         calculate_projects_crc=False):
        """Refresh installers, ignoring skip refresh flag.

        Will also update InstallersData for the paths this installer would
        install, in case a refresh is requested because those files were
        modified/deleted (BAIN only scans Data/ once or boot)."""
        if not toRefresh: return
        try:
            with balt.Progress(_(u'Refreshing Packages...'), u'\n' + u' ' * 60,
                               abort=abort) as progress:
                progress.setFull(len(toRefresh))
                dest = set() # installer's destination paths rel to Data/
                for index, (name, installer) in enumerate(
                        self.data_store.sorted_pairs(toRefresh)):
                    progress(index, _(u'Refreshing Packages...') + u'\n' +
                                    name.s)
                    dest.update(installer.refreshBasic(
                        SubProgress(progress, index, index + 1),
                        recalculate_project_crc=calculate_projects_crc).keys())
                self.data_store.hasChanged = True  # is it really needed ?
                if update_from_data:
                    progress(0, _(u'Refreshing From Data...') + u'\n' + u' ' * 60)
                    self.data_store.update_data_SizeCrcDate(dest, progress)
        except CancelError:  # User canceled the refresh
            if not abort: raise # I guess CancelError is raised on aborting
        self.data_store.irefresh(what='NSC')
        self.RefreshUI()

#------------------------------------------------------------------------------
class InstallersDetails(_DetailsMixin, SashPanel):
    keyPrefix = 'bash.installers.details'
    defaultSashPos = - 32 # negative so it sets bottom panel's (comments) size
    defaultSubSashPos = 0
    minimumSize = 32 # so comments dont take too much space

    @property
    def displayed_item(self): return self._displayed_installer
    @property
    def file_infos(self): return self._idata

    def __init__(self,parent):
        """Initialize."""
        super(InstallersDetails, self).__init__(parent, isVertical=False)
        self.installersPanel = parent.GetParent().GetParent()
        self._idata = self.installersPanel.listData
        self._displayed_installer = None
        top, bottom = self.left, self.right
        commentsSplitter = self.splitter
        self.subSplitter = subSplitter = balt.Splitter(top)
        self.checkListSplitter = balt.Splitter(subSplitter)
        #--Package
        self.gPackage = RoTextCtrl(top, noborder=True)
        #--Info Tabs
        self.gNotebook = wx.Notebook(subSplitter,style=wx.NB_MULTILINE)
        self.gNotebook.SetSizeHints(100,100)
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
        for name,title in infoTitles:
            gPage = RoTextCtrl(self.gNotebook, name=name, hscroll=True,
                               autotooltip=False)
            self.gNotebook.AddPage(gPage,title)
            self.infoPages.append([gPage,False])
        self.gNotebook.SetSelection(settings['bash.installers.page'])
        self.gNotebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED,self.OnShowInfoPage)
        #--Sub-Installers
        subPackagesPanel = wx.Panel(self.checkListSplitter)
        subPackagesLabel = StaticText(subPackagesPanel, _(u'Sub-Packages'))
        self.gSubList = balt.listBox(subPackagesPanel, isExtended=True,
                                     kind='checklist',
                                     onCheck=self.OnCheckSubItem)
        self.gSubList.Bind(wx.EVT_RIGHT_UP,self.SubsSelectionMenu)
        #--Espms
        espmsPanel = wx.Panel(self.checkListSplitter)
        espmsLabel = StaticText(espmsPanel, _(u'Esp/m Filter'))
        self.espms = []
        self.gEspmList = balt.listBox(espmsPanel, isExtended=True,
                                      kind='checklist',
                                      onCheck=self.OnCheckEspmItem)
        self.gEspmList.Bind(wx.EVT_RIGHT_UP,self.SelectionMenu)
        #--Comments
        commentsPanel = wx.Panel(bottom)
        commentsLabel = StaticText(commentsPanel, _(u'Comments'))
        self.gComments = TextCtrl(commentsPanel, multiline=True)
        #--Splitter settings
        self.checkListSplitter.SetMinimumPaneSize(50)
        self.checkListSplitter.SplitVertically(subPackagesPanel, espmsPanel)
        self.checkListSplitter.SetSashGravity(0.5)
        subSplitter.SetMinimumPaneSize(50)
        subSplitter.SplitHorizontally(self.gNotebook, self.checkListSplitter)
        subSplitter.SetSashGravity(0.5)
        commentsSplitter.SetMinimumPaneSize(-self.__class__.defaultSashPos)
        commentsSplitter.SplitHorizontally(subSplitter, commentsPanel)
        commentsSplitter.SetSashGravity(1.0)
        #--Layout
        subPackagesSizer = vSizer(subPackagesLabel,(self.gSubList,1,wx.EXPAND))
        subPackagesSizer.SetSizeHints(subPackagesPanel)
        subPackagesPanel.SetSizer(subPackagesSizer)
        espmsSizer = vSizer(espmsLabel, (self.gEspmList, 1, wx.EXPAND))
        espmsSizer.SetSizeHints(espmsPanel)
        espmsPanel.SetSizer(espmsSizer)
        topSizer = vSizer(vspace(2),
            (self.gPackage,0,wx.EXPAND|wx.LEFT,3),
            (subSplitter,1,wx.EXPAND),
            )
        top.SetSizer(topSizer)
        commentsSizer = vSizer(commentsLabel, (self.gComments,1,wx.EXPAND))
        commentsSizer.SetSizeHints(commentsPanel)
        commentsPanel.SetSizer(commentsSizer)
        bottomSizer = vSizer(
            (commentsPanel,1,wx.EXPAND))
        bottomSizer.SetSizeHints(bottom)
        bottom.SetSizer(bottomSizer)

    def OnShowInfoPage(self,event):
        """A specific info page has been selected."""
        if event.GetId() == self.gNotebook.GetId():
            index = event.GetSelection()
            gPage,initialized = self.infoPages[index]
            if self._displayed_installer and not initialized:
                self.RefreshInfoPage(index, self.file_info)
            event.Skip()

    def ClosePanel(self, destroy=False, only_details=False):
        """Saves details if they need saving."""
        super(InstallersDetails, self).ClosePanel(destroy)
        if not self._firstShow and not only_details: # save subsplitters
            settings[self.__class__.keyPrefix + '.subSplitterSashPos'] = \
                self.subSplitter.GetSashPosition()
            settings[self.__class__.keyPrefix + '.checkListSplitterSashPos'] =\
                self.checkListSplitter.GetSashPosition()
            settings['bash.installers.page'] = self.gNotebook.GetSelection()
        installer = self.file_info
        if not installer or not self.gComments.IsModified(): return
        installer.comments = self.gComments.GetValue()
        self._idata.setChanged()

    def SetFile(self, fileName='SAME'):
        """Refreshes detail view associated with data from item."""
        if self._displayed_installer is not None:
            self.ClosePanel(only_details=True) #--Save previous details
        fileName = super(InstallersDetails, self).SetFile(fileName)
        self._displayed_installer = fileName
        del self.espms[:]
        if fileName:
            installer = self._idata[fileName]
            #--Name
            self.gPackage.SetValue(fileName.s)
            #--Info Pages
            currentIndex = self.gNotebook.GetSelection()
            for index,(gPage,state) in enumerate(self.infoPages):
                self.infoPages[index][1] = False
                if index == currentIndex: self.RefreshInfoPage(index,installer)
                else: gPage.SetValue(u'')
            #--Sub-Packages
            self.gSubList.Clear()
            if len(installer.subNames) <= 2:
                self.gSubList.Clear()
            else:
                balt.setCheckListItems(self.gSubList, [x.replace(u'&',u'&&') for x in installer.subNames[1:]], installer.subActives[1:])
            #--Espms
            if not installer.espms:
                self.gEspmList.Clear()
            else:
                names = self.espms = sorted(installer.espms)
                names.sort(key=lambda x: x.cext != u'.esm')
                balt.setCheckListItems(self.gEspmList, [[u'',u'*'][installer.isEspmRenamed(x.s)]+x.s.replace(u'&',u'&&') for x in names],
                    [x not in installer.espmNots for x in names])
            #--Comments
            self.gComments.SetValue(installer.comments)
        self.gPackage.HideNativeCaret()

    def _resetDetails(self):
        self.gPackage.SetValue(u'')
        for index, (gPage, state) in enumerate(self.infoPages):
            self.infoPages[index][1] = True
            gPage.SetValue(u'')
        self.gSubList.Clear()
        self.gEspmList.Clear()
        self.gComments.SetValue(u'')

    def ShowPanel(self, **kwargs):
        if self._firstShow:
            super(InstallersDetails, self).ShowPanel() # set sash position
            sashPos = settings.get(
                self.keyPrefix + '.checkListSplitterSashPos',
                self.__class__.defaultSubSashPos)
            self.checkListSplitter.SetSashPosition(sashPos)
            sashPos = settings.get(self.keyPrefix + '.subSplitterSashPos',
                                   self.__class__.defaultSubSashPos)
            self.subSplitter.SetSashPosition(sashPos)

    def RefreshInfoPage(self,index,installer):
        """Refreshes notebook page."""
        gPage,initialized = self.infoPages[index]
        if initialized: return
        else: self.infoPages[index][1] = True
        pageName = gPage.GetName()
        def dumpFiles(files, header=u'', isPath=True):
            if files:
                buff = StringIO.StringIO()
                if isPath: files = [x.s for x in files]
                else: files = list(files)
                files = bosh.Installer.sortFiles(files)
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
            nConfigured = len(installer.data_sizeCrc)
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
            info += (_(u'Modified:')+u' %s\n' % formatDate(installer.modified),
                     _(u'Modified:')+u' N/A\n',)[isinstance(installer,bosh.InstallerMarker)]
            info += (_(u'Data CRC:')+u' %08X\n' % installer.crc,
                     _(u'Data CRC:')+u' N/A\n',)[isinstance(installer,bosh.InstallerMarker)]
            info += (_(u'Files:') + u' %s\n' % installer.number_string(
                installer.num_of_files, marker_string=u'N/A'))
            info += (_(u'Configured:')+u' %s (%s)\n' % (
                formatInteger(nConfigured), round_size(installer.unSize)),
                     _(u'Configured:')+u' N/A\n',)[isinstance(installer,bosh.InstallerMarker)]
            info += (_(u'  Matched:') + u' %s\n' % installer.number_string(
                nConfigured - nMissing - nMismatched, marker_string=u'N/A'))
            info += (_(u'  Missing:')+u' %s\n' % installer.number_string(
                nMissing, marker_string=u'N/A'))
            info += (_(u'  Conflicts:')+u' %s\n' % installer.number_string(
                nMismatched, marker_string=u'N/A'))
            info += '\n'
            #--Infoboxes
            gPage.SetValue(info + dumpFiles(installer.data_sizeCrc,
                                            u'== ' + _(u'Configured Files')))
        elif pageName == 'gMatched':
            gPage.SetValue(dumpFiles(set(installer.data_sizeCrc) -
                        installer.missingFiles - installer.mismatchedFiles))
        elif pageName == 'gMissing':
            gPage.SetValue(dumpFiles(installer.missingFiles))
        elif pageName == 'gMismatched':
            gPage.SetValue(dumpFiles(installer.mismatchedFiles))
        elif pageName == 'gConflicts':
            gPage.SetValue(self._idata.getConflictReport(installer, 'OVER'))
        elif pageName == 'gUnderrides':
            gPage.SetValue(self._idata.getConflictReport(installer, 'UNDER'))
        elif pageName == 'gDirty':
            gPage.SetValue(dumpFiles(installer.dirty_sizeCrc))
        elif pageName == 'gSkipped':
            gPage.SetValue(u'\n'.join((
                dumpFiles(installer.skipExtFiles,
                          u'== ' + _(u'Skipped (Extension)'), isPath=False),
                dumpFiles(installer.skipDirFiles, u'== ' + _(u'Skipped (Dir)'),
                          isPath=False),)) or _(u'[None]'))

    #--Config
    def refreshCurrent(self,installer):
        """Refreshes current item while retaining scroll positions."""
        installer.refreshDataSizeCrc()
        installer.refreshStatus(self._idata)
        # Save scroll bar positions, because gList.RefreshUI will
        subScrollPos  = self.gSubList.GetScrollPos(wx.VERTICAL)
        espmScrollPos = self.gEspmList.GetScrollPos(wx.VERTICAL)
        subIndices = self.gSubList.GetSelections()
        self.installersPanel.uiList.RefreshUI(files=[self.displayed_item])
        for subIndex in subIndices:
            self.gSubList.SetSelection(subIndex)
        # Reset the scroll bars back to their original position
        subScroll = subScrollPos - self.gSubList.GetScrollPos(wx.VERTICAL)
        self.gSubList.ScrollLines(subScroll)
        espmScroll = espmScrollPos - self.gEspmList.GetScrollPos(wx.VERTICAL)
        self.gEspmList.ScrollLines(espmScroll)

    def OnCheckSubItem(self,event):
        """Handle check/uncheck of item."""
        installer = self.file_info
        index = event.GetSelection()
        self.gSubList.SetSelection(index)
        for index in range(self.gSubList.GetCount()):
            installer.subActives[index+1] = self.gSubList.IsChecked(index)
        if not balt.getKeyState_Shift():
            self.refreshCurrent(installer)

    def SelectionMenu(self,event):
        """Handle right click in espm list."""
        x = event.GetX()
        y = event.GetY()
        selected = self.gEspmList.HitTest((x,y))
        self.gEspmList.SetSelection(selected)
        #--Show/Destroy Menu
        InstallersPanel.espmMenu.PopupMenu(self, Link.Frame, selected)

    def SubsSelectionMenu(self,event):
        """Handle right click in espm list."""
        x = event.GetX()
        y = event.GetY()
        selected = self.gSubList.HitTest((x,y))
        self.gSubList.SetSelection(selected)
        #--Show/Destroy Menu
        InstallersPanel.subsMenu.PopupMenu(self, Link.Frame, selected)

    def OnCheckEspmItem(self,event):
        """Handle check/uncheck of item."""
        espmNots = self.file_info.espmNots
        index = event.GetSelection()
        name = self.gEspmList.GetString(index).replace('&&','&')
        if name[0] == u'*':
            name = name[1:]
        espm = GPath(name)
        if self.gEspmList.IsChecked(index):
            espmNots.discard(espm)
        else:
            espmNots.add(espm)
        self.gEspmList.SetSelection(index)    # so that (un)checking also selects (moves the highlight)
        if not balt.getKeyState_Shift():
            self.refreshCurrent(self.file_info)

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
        self.listData = bosh.InstallersData()
        super(InstallersPanel, self).__init__(parent)
        #--Refreshing
        self._data_dir_scanned = False
        self.refreshing = False
        self.frameActivated = False

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
        if not settings['bash.installers.enabled'] or self.refreshing: return
        refresh_ui = [False]
        try:
            self.refreshing = True
            self._refresh_installers_if_needed(refresh_ui, canCancel,
                                               fullRefresh, scan_data_dir)
            if refresh_ui[0]: self.uiList.RefreshUI(focus_list=False)
            super(InstallersPanel, self).ShowPanel()
        finally:
            self.refreshing = False

    @balt.conversation
    @projects_walk_cache
    def _refresh_installers_if_needed(self, refreshui, canCancel, fullRefresh,
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
        if do_refresh:
            with balt.Progress(_(u'Refreshing Installers...'),
                               u'\n' + u' ' * 60, abort=canCancel) as progress:
                try:
                    what = 'DISC' if scan_data_dir else 'IC'
                    refreshui[0] |= self.listData.irefresh(progress, what,
                                                           fullRefresh,
                                                           refresh_info)
                    self.frameActivated = False
                except CancelError:
                    pass # User canceled the refresh
                finally:
                    self._data_dir_scanned = True
        elif self.frameActivated and self.listData.refreshConvertersNeeded():
            with balt.Progress(_(u'Refreshing Converters...'),
                               u'\n' + u' ' * 60) as progress:
                try:
                    refreshui[0] |= self.listData.irefresh(progress, 'C',
                                                           fullRefresh)
                    self.frameActivated = False
                except CancelError:
                    pass # User canceled the refresh
        changed = bosh.InstallersData.miscTrackedFiles.refreshTracked()
        if changed:
            # Some tracked files changed, update the ui
            data_sizeCrcDate = self.listData.data_sizeCrcDate
            refresh = False
            for apath in changed:
                # the Game/Data dir - will give correct relative path for both
                # Ini tweaks and mods - those are keyed in data by rel path...
                if apath.cs.startswith(bass.dirs['mods'].cs):
                    path = apath.relpath(bass.dirs['mods'])
                else:
                    path = apath
                if apath.exists():
                    data_sizeCrcDate[path] = (apath.size,apath.crc,apath.mtime)
                    refresh = True
                else:
                    refresh |= bool(data_sizeCrcDate.pop(path, None))
            if refresh:
                refreshui[0] |= self.listData.refreshInstallersStatus()

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
        active = len(filter(lambda x: x.isActive, self.listData.itervalues()))
        return _(u'Packages:') + u' %d/%d' % (active, len(self.listData))

    def RefreshUIMods(self, mods_changed, inis_changed):
        """Refresh UI plus refresh mods state."""
        self.uiList.RefreshUI()
        if mods_changed:
            with load_order.Unlock():
                bosh.modInfos.refresh()
            BashFrame.modList.RefreshUI(refreshSaves=True, focus_list=False)
            Link.Frame.warn_corrupted(warn_saves=False)
            Link.Frame.warn_load_order()
        if inis_changed:
            bosh.iniInfos.refresh(refresh_target=False)
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
        u'(\.(' + ur'|'.join(ext[1:] for ext in bosh.imageExts) + u')+)'
    def _order_by_number(self, items):
        if self.sort_column != 'File': return
        regex = re.compile(u'(.*?)(\d*)' + self.__ext_group + u'$')
        keys = {k: regex.match(k.s) for k in items}
        keys = {k: (v.groups()[0].lower(), int(v.groups()[1] or 0)) for k, v in
                keys.iteritems()}
        items.sort(key=keys.__getitem__,
                   reverse=self.colReverse.get('File', False))

    _sort_keys = {'File'    : None,
                  'Modified': lambda self, a: self.data_store[a][1],
                 }
    #--Labels
    labels = OrderedDict([
        ('File',     lambda self, p: p.s),
        # ('Modified', lambda self, path: formatDate(self.data_store[path][1])), # unused
    ])
    _extra_sortings = [_order_by_number]

    #--Events ---------------------------------------------
    def OnDClick(self,event):
        """Double click a screenshot"""
        hitItem = self._getItemClicked(event)
        if not hitItem: return
        self.OpenSelected(selected=[hitItem])
    def OnLabelEdited(self, event):
        """Rename selected screenshots."""
        root, _newName, numStr = self.validate_filename(event, has_digits=True,
                                                        ext=self.__ext_group)
        if not (root or numStr): return # allow for number only names
        selected = self.GetSelected()
        #--Rename each screenshot, keeping the old extension
        num = int(numStr or  0)
        digits = len(str(num + len(selected)))
        if numStr: numStr.zfill(digits)
        with balt.BusyCursor():
            to_select = set()
            for screen in selected:
                newName = GPath(root + numStr + screen.ext)
                if not self._try_rename(screen, newName, to_select): break
                num += 1
                numStr = unicode(num).zfill(digits)
            if to_select:
                self.RefreshUI()
                #--Reselected the renamed items
                self.SelectItemsNoCallback(to_select)
            event.Veto()

    def OnChar(self,event):
        # Enter: Open selected screens
        code = event.GetKeyCode()
        if code in balt.wxReturn: self.OpenSelected()
        else: super(ScreensList, self).OnKeyUp(event)

    def OnKeyUp(self,event):
        """Char event: Activate selected items, select all items"""
        code = event.GetKeyCode()
        # Ctrl+C: Copy file(s) to clipboard
        if event.CmdDown() and code == ord('C'):
            sel = map(lambda x: bosh.screensData.store_dir.join(x).s,
                      self.GetSelected())
            balt.copyListToClipboard(sel)
        super(ScreensList, self).OnKeyUp(event)

#------------------------------------------------------------------------------
class ScreensDetails(_DetailsMixin, NotebookPanel):

    def __init__(self, parent):
        super(ScreensDetails, self).__init__(parent)
        self.screenshot_control = balt.Picture(parent, 256, 192, background=colors['screens.bkgd.image'])
        self.displayed_screen = None # type: bolt.Path
        self.SetSizer(hSizer((self.screenshot_control,1,wx.GROW)))

    @property
    def displayed_item(self): return self.displayed_screen
    @property
    def file_infos(self): return bosh.screensData

    def _resetDetails(self):
        self.screenshot_control.SetBitmap(None)

    def SetFile(self, fileName='SAME'):
        """Set file to be viewed."""
        #--Reset?
        self.displayed_screen = super(ScreensDetails, self).SetFile(fileName)
        if not self.displayed_screen: return
        filePath = bosh.screensData.store_dir.join(self.displayed_screen)
        bitmap = Image(filePath.s).GetBitmap() if filePath.exists() else None
        self.screenshot_control.SetBitmap(bitmap)

    def RefreshUIColors(self):
        self.screenshot_control.SetBackground(colors['screens.bkgd.image'])

class ScreensPanel(BashTab):
    """Screenshots tab."""
    keyPrefix = 'bash.screens'
    _status_str = _(u'Screens:') + u' %d'
    _ui_list_type = ScreensList
    _details_panel_type = ScreensDetails

    def __init__(self,parent):
        """Initialize."""
        self.listData = bosh.screensData = bosh.ScreensData()
        super(ScreensPanel, self).__init__(parent)

    def ShowPanel(self, **kwargs):
        """Panel is shown. Update self.data."""
        if bosh.screensData.refresh():
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
        ('Modified', lambda self, p: formatDate(self.data_store[p].mtime)),
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

    def __init__(self, parent):
        SashPanel.__init__(self, parent, isVertical=False)
        self.top, self.bottom = self.left, self.right
        bsa_panel = self.GetParent().GetParent().GetParent()
        _EditableMixinOnFileInfos.__init__(self, self.bottom, bsa_panel)
        #--Data
        self._bsa_info = None
        #--BSA Info
        self.gInfo = TextCtrl(self.bottom, multiline=True,
                              onText=self.OnInfoEdit, maxChars=2048)
        #--Layout
        nameSizer = vSizer(vspace(),
            (hSizer(StaticText(self.top, _(u'File:'))), 0, wx.EXPAND),
            (hSizer((self.file, 1, wx.EXPAND)), 0, wx.EXPAND))
        nameSizer.SetSizeHints(self.top)
        self.top.SetSizer(nameSizer)
        infoSizer = vSizer(
            (hSizer((self.gInfo,1,wx.EXPAND)),0,wx.EXPAND),
            vspace(),
        (hSizer(self.save, hspace(), self.cancel,),0,wx.EXPAND),)
        infoSizer.SetSizeHints(self.bottom)
        self.bottom.SetSizer(infoSizer)

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
        self.file.SetValue(self.fileStr)
        #--Info Box
        self.gInfo.DiscardEdits()
        if fileName:
            self.gInfo.SetValue(
                bosh.bsaInfos.table.getItem(fileName, 'info', _(u'Notes: ')))
        else:
            self.gInfo.SetValue(_(u'Notes: '))

    def OnInfoEdit(self,event):
        """Info field was edited."""
        if self._bsa_info and self.gInfo.IsModified():
            bosh.bsaInfos.table.setItem(self._bsa_info.name, 'info', self.gInfo.GetValue())
        event.Skip()

    def DoSave(self):
        """Event: Clicked Save button."""
        #--Change Tests
        changeName = (self.fileStr != self._bsa_info.name)
        #--Backup
        self._bsa_info.makeBackup()
        #--Change Name?
        if changeName:
            (oldName, newName) = (
                self._bsa_info.name, GPath(self.fileStr.strip()))
            bosh.bsaInfos.rename_info(oldName, newName)
        #--Done
        try:
            bosh.bsaInfos.refreshFile(self._bsa_info.name)
            self.SetFile(self._bsa_info.name)
        except bosh.FileError:
            balt.showError(self,_(u'File corrupted on save!'))
            self.SetFile(None)
        self.panel_uilist.RefreshUI()

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
        ('Name',   lambda self, name: name),
        ('Karma',  lambda self, name: self._karma(self.data_store[name])),
        ('Header', lambda self, name:
                            self.data_store[name][2].split(u'\n', 1)[0][:75]),
    ])

    def set_item_format(self, item, item_format):
        item_format.icon_key = u'karma%+d' % self.data_store[item][1]

#------------------------------------------------------------------------------
class PeopleDetails(_DetailsMixin, NotebookPanel):
    @property
    def displayed_item(self): return self._people_detail
    @property
    def file_infos(self): return self.peoplePanel.listData

    def __init__(self, parent):
        super(PeopleDetails, self).__init__(parent)
        self._people_detail = None # type: unicode
        self.peoplePanel = parent.GetParent().GetParent()
        self.gName = RoTextCtrl(self, multiline=False)
        self.gText = TextCtrl(self, multiline=True)
        self.gKarma = spinCtrl(self,u'0',min=-5,max=5,onSpin=self.OnSpin)
        self.gKarma.SetSizeHints(40,-1)
        #--Layout
        self.SetSizer(vSizer(
            (hSizer((self.gName, 1, wx.GROW),
                    (self.gKarma, 0, wx.GROW),
                    ), 0, wx.GROW),
            vspace(), (self.gText, 1, wx.GROW),
        ))

    def OnSpin(self):
        """Karma spin."""
        if not self._people_detail: return
        karma = int(self.gKarma.GetValue())
        text = self.file_infos[self._people_detail][2]
        self.file_infos[self._people_detail] = (time.time(), karma, text)
        self.peoplePanel.uiList.PopulateItem(item=self._people_detail)
        self.file_infos.setChanged()

    def ClosePanel(self, destroy=False):
        """Saves details if they need saving."""
        if not self.gText.IsModified(): return
        if not self.file_info: return
        mtime, karma, text = self.file_infos[self._people_detail]
        self.file_infos[self._people_detail] = (
            time.time(), karma, self.gText.GetValue().strip())
        self.peoplePanel.uiList.PopulateItem(item=self._people_detail)
        self.file_infos.setChanged()

    def SetFile(self, fileName='SAME'):
        """Refreshes detail view associated with data from item."""
        self.ClosePanel()
        item = super(PeopleDetails, self).SetFile(fileName)
        self._people_detail = item
        if not item: return
        karma, text = self.peoplePanel.listData[item][1:3]
        self.gName.SetValue(item)
        self.gKarma.SetValue(karma)
        self.gText.SetValue(text)

    def _resetDetails(self):
        self.gKarma.SetValue(0)
        self.gName.SetValue(u'')
        self.gText.Clear()

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
class _Tab_Link(AppendableLink, CheckLink, EnabledLink):
    """Handle hiding/unhiding tabs."""
    def __init__(self,tabKey,canDisable=True):
        super(_Tab_Link, self).__init__()
        self.tabKey = tabKey
        self.enabled = canDisable
        className, self.text, item = tabInfo.get(self.tabKey,[None,None,None])
        self.help = _(u"Show/Hide the %(tabtitle)s Tab.") % (
            {'tabtitle': self.text})

    def _append(self, window): return self.text is not None

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
            # TODO(ut): we should call ClosePanel and make sure there are no leaks
            tabInfo[self.tabKey][2].ClosePanel()
            page = Link.Frame.notebook.GetPage(iDelete)
            Link.Frame.notebook.RemovePage(iDelete)
            page.Show(False)
        else:
            # It was disabled, enable it
            insertAt = 0
            for i,key in enumerate(bass.settings['bash.tabs.order']):
                if key == self.tabKey: break
                if bass.settings['bash.tabs.order'][key]:
                    insertAt = i+1
            className,title,panel = tabInfo[self.tabKey]
            if not panel:
                panel = globals()[className](Link.Frame.notebook)
                tabInfo[self.tabKey][2] = panel
            if insertAt > Link.Frame.notebook.GetPageCount():
                Link.Frame.notebook.AddPage(panel,title)
            else:
                Link.Frame.notebook.InsertPage(insertAt,panel,title)
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
                self.AddPage(item,title)
                tabInfo[page][2] = item
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
        self.currentPage = self.GetPage(self.GetSelection())
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
        for ind, title in enumerate(settings['bash.tabs.order']):
            if title == page_title: break
        else: raise BoltError('Invalid page: %s' % page_title)
        self.SetSelection(ind)
        tabInfo[page_title][2].SelectUIListItem(GPath(item),
                                                deselectOthers=True)

    def DoTabMenu(self,event):
        pos = event.GetPosition()
        pos = self.ScreenToClient(pos)
        tabId = self.HitTest(pos)
        if tabId != wx.NOT_FOUND and tabId[0] != wx.NOT_FOUND:
            menu = self.tabLinks(Links())
            menu.PopupMenu(self, Link.Frame, None)
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
            self.currentPage = self.GetPage(event.GetSelection())
            self.currentPage.ShowPanel()
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
            # Add it
            self._addButton(link)
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
            self._addButton(link)
        # Update settings
        if orderChanged: settings.setChanged('bash.statusbar.order')
        if hideChanged: settings.setChanged('bash.statusbar.hide')
        # Refresh
        self.SetStatusWidths([self.iconsSize * len(self.buttons), -1, 130])
        self.SetSize((-1, self.iconsSize))
        self.GetParent().SendSizeEvent()
        self.OnSize()

    def HideButton(self,button):
        if button in self.buttons:
            # Find the BashStatusBar_Button instance that made it
            link = self.GetLink(button=button)
            if link:
                button.Show(False)
                self.buttons.remove(button)
                settings['bash.statusbar.hide'].add(link.uid)
                settings.setChanged('bash.statusbar.hide')
                # Refresh
                self.SetStatusWidths(
                    [self.iconsSize * len(self.buttons), -1, 130])
                self.GetParent().SendSizeEvent()
                self.OnSize()

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
        # Refresh
        self.SetStatusWidths([self.iconsSize * len(self.buttons), -1, 130])
        self.GetParent().SendSizeEvent()
        self.OnSize()

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

#------------------------------------------------------------------------------
class BashFrame(wx.Frame):
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

    @property
    def statusBar(self): return self.GetStatusBar()

    def __init__(self, parent=None):
        #--Singleton
        balt.Link.Frame = self
        #--Window
        wx.Frame.__init__(self, parent, title=u'Wrye Bash',
                          pos=settings['bash.framePos'],
                          size=settings['bash.frameSize'])
        minSize = settings['bash.frameSize.min']
        self.SetSizeHints(minSize[0],minSize[1])
        self.SetTitle()
        #--Application Icons
        self.SetIcons(Resources.bashRed)
        #--Status Bar
        self.SetStatusBar(BashStatusBar(self))
        #--Notebook panel
        # attributes used when ini panel is created (warn for missing game ini)
        self.oblivionIniCorrupted = self.oblivionIniMissing = False
        self.notebook = BashNotebook(self)
        #--Events
        self.Bind(wx.EVT_CLOSE, lambda __event: self.OnCloseWindow())
        #--Data
        self.inRefreshData = False #--Prevent recursion while refreshing.
        self.knownCorrupted = set()
        self.knownInvalidVerions = set()
        self.incompleteInstallError = False

    @balt.conversation
    def warnTooManyModsBsas(self):
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

    def queue_game_ini_missing(self): self.oblivionIniMissing = True

    def BindRefresh(self, bind=True, __event=wx.EVT_ACTIVATE):
        self.Bind(__event, self.RefreshData) if bind else self.Unbind(__event)

    def Restart(self,args=True,uac=False):
        if not args: return

        def argConvert(arg):
            """Converts --args into -a args"""
            if not isinstance(arg,basestring): return arg
            elif arg in sys.argv: return arg
            elif arg[:2] == '--': return '-'+arg[2]
            else: return arg

        newargs = []
        if isinstance(args,(list,tuple)):
            args = [[argConvert(x) for x in arg] if isinstance(arg,(list,tuple))
                    else argConvert(arg)
                    for arg in args]
        elif isinstance(args,set):
            # Special case for restarting for an update: args passed in as set()
            pass
        else:
            args = argConvert(args)

        global appRestart
        appRestart = args

        global uacRestart
        uacRestart = uac
        self.Close(True)

    def SetTitle(*args, **kwargs):
        """Set title. Set to default if no title supplied."""
        if bush.game.altName and settings['bash.useAltName']:
            title = bush.game.altName + u' %s%s'
        else:
            title = u'Wrye Bash %s%s '+_(u'for')+u' '+bush.game.displayName
        title = title % (settings['bash.version'],
            _(u'(Standalone)') if settings['bash.standalone'] else u'')
        if CBashApi.Enabled:
            title += u', CBash %s: ' % (CBashApi.VersionText,)
        else:
            title += u': '
        maProfile = re.match(ur'Saves\\(.+)\\$',bosh.saveInfos.localSave,re.U)
        if maProfile:
            title += maProfile.group(1)
        else:
            title += _(u'Default')
        if bosh.modInfos.voCurrent:
            title += u' ['+bosh.modInfos.voCurrent+u']'
        wx.Frame.SetTitle(args[0], title)

    def SetStatusCount(self, requestingPanel, countTxt):
        """Sets status bar count field."""
        if self.notebook.currentPage is requestingPanel: # we need to check if
        # requesting Panel is currently shown because Refresh UI path may call
        # Refresh UI of other tabs too - this results for instance in mods
        # count flickering when deleting a save in saves tab - ##: hunt down
            self.statusBar.SetStatusText(countTxt, 2)

    def SetStatusInfo(self, infoTxt):
        """Sets status bar info field."""
        self.statusBar.SetStatusText(infoTxt, 1)

    #--Events ---------------------------------------------
    @balt.conversation
    def RefreshData(self, event=None, booting=False):
        """Refresh all data - window activation event callback, called also
        on boot."""
        #--Ignore deactivation events.
        if event and not event.GetActive() or self.inRefreshData: return
        #--UPDATES-----------------------------------------
        self.inRefreshData = True
        popMods = popSaves = popBsas = None
        #--Config helpers
        bosh.configHelpers.refreshBashTags()
        #--Check bsas, needed to detect string files in modInfos refresh...
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
                                            clean_targets=not booting,
                                            refresh_target=True)
        #--WARNINGS----------------------------------------
        if booting: self.warnTooManyModsBsas()
        self.warn_load_order()
        self._warn_reset_load_order()
        self.warn_corrupted()
        self.warn_game_ini()
        self._missingDocsDir()
        #--Done (end recursion blocker)
        self.inRefreshData = False

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
            ListBoxes.Display(self, title, message, [lists], liststyle='list',
                              canCancel=False)
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
            x.header.version, 6) not in bush.game.esp.validHeaderVersions])
        if warn_mods and not invalidVersions <= self.knownInvalidVerions:
            m = [_(u'Unrecognized Versions'),
                 _(u'The following mods have unrecognized header versions: ')]
            m.extend(sorted(invalidVersions))
            message.append(m)
            self.knownInvalidVerions |= invalidVersions
        if warn_strings and bosh.modInfos.new_missing_strings:
            m = [_(u'Missing String Localization files:'),
                 _(u'This will cause CTDs if activated.')]
            m.extend(sorted(bosh.modInfos.missing_strings))
            message.append(m)
            bosh.modInfos.new_missing_strings.clear()
        if message:
            ListBoxes.Display(
              self, _(u'Warnings'), _(u'The following warnings were found:'),
            message, liststyle='list', canCancel=False)

    _ini_missing = _(u"%(ini)s does not exist yet.  %(game)s will create this "
        u"file on first run.  INI tweaks will not be usable until then.")
    @balt.conversation
    def warn_game_ini(self):
        #--Corrupt Oblivion.ini
        if self.oblivionIniCorrupted != bosh.oblivionIni.isCorrupted:
            self.oblivionIniCorrupted = bosh.oblivionIni.isCorrupted
            if self.oblivionIniCorrupted:
                msg = _(u'Your %s should begin with a section header '
                        u'(e.g. "[General]"), but does not. You should edit '
                        u'the file to correct this.') % bush.game.iniFiles[0]
                balt.showWarning(self, fill(msg), _(u'Corrupted game Ini'))
        elif self.oblivionIniMissing:
            self.oblivionIniMissing = False
            balt.showWarning(self, self._ini_missing % {
                'ini': bosh.oblivionIni.abs_path, 'game': bush.game.displayName},
                             _(u'Missing game Ini'))

    def _missingDocsDir(self):
        #--Missing docs directory?
        testFile = GPath(bass.dirs['mopy']).join(u'Docs', u'wtxt_teal.css')
        if self.incompleteInstallError or testFile.exists(): return
        self.incompleteInstallError = True
        msg = _(u'Installation appears incomplete.  Please re-unzip bash '
        u'to game directory so that ALL files are installed.') + u'\n\n' + _(
        u'Correct installation will create %s\\Mopy and '
        u'%s\\Data\\Docs directories.') % (bush.game.fsName, bush.game.fsName)
        balt.showWarning(self, msg, _(u'Incomplete Installation'))

    def OnCloseWindow(self):
        """Handle Close event. Save application data."""
        try:
            self.BindRefresh(bind=False)
            self.SaveSettings(destroy=True)
        except: ##: this has swallowed exceptions since forever
                deprint(_(u'An error occurred while trying to save settings:'),
                        traceback=True)
        finally:
            self.Destroy()

    def SaveSettings(self, destroy=False):
        """Save application data."""
        # Purge some memory
        bolt.GPathPurge()
        # Clean out unneeded settings
        self.CleanSettings()
        if Link.Frame.docBrowser: Link.Frame.docBrowser.DoSave()
        if not (self.IsIconized() or self.IsMaximized()):
            settings['bash.framePos'] = tuple(self.GetPosition())
            settings['bash.frameSize'] = tuple(self.GetSize())
        settings['bash.frameMax'] = self.IsMaximized()
        settings['bash.page'] = self.notebook.GetSelection()
        # use tabInfo below so we save settings of panels that the user closed
        for _k, (_cname, name, panel) in tabInfo.iteritems():
            if panel is None: continue
            try:
                panel.ClosePanel(destroy)
            except:
                deprint(u'An error occurred while saving settings of '
                        u'the %s panel:' % name, traceback=True)
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
def GetBashVersion():
    return bass.AppVersion

    #--Version from readme
    #readme = bass.dirs['mopy'].join(u'Wrye Bash.txt')
    #if readme.exists() and readme.mtime != settings['bash.readme'][0]:
    #    reVersion = re.compile(ur'^=== (\d+(\.(dev|beta)?\d*)?) \[', re.I|re.U)
    #    for line in readme.open(encoding='utf-8-sig'):
    #        maVersion = reVersion.match(line)
    #        if maVersion:
    #            return (readme.mtime,maVersion.group(1))
    #return settings['bash.readme'] #readme file not found or not changed

#------------------------------------------------------------------------------
class BashApp(wx.App):
    """Bash Application class."""
    def Init(self): # not OnInit(), we need to initialize _after_ the app has been instantiated
        """Initialize the application data and create the BashFrame."""
        global appRestart
        appRestart = False
        #--OnStartup SplashScreen and/or Progress
        #   Progress gets hidden behind splash by default, since it's not very informative anyway
        splashScreen = None
        progress = balt.Progress(u'Wrye Bash', _(u'Initializing') + u' ' * 10,
                                 elapsed=False)
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
        progress(1.0)
        progress.Destroy()
        if splashScreen:
            splashScreen.Destroy()
            splashScreen.Hide() # wont be hidden if warnTooManyModsBsas warns..
        self.SetTopWindow(frame)
        frame.Show()
        frame.Maximize(settings['bash.frameMax'])
        frame.RefreshData(booting=True)
        balt.ensureDisplayed(frame)
        # Moved notebook.Bind() callback here as OnShowPage() is explicitly
        # called in RefreshData
        frame.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED,
                            frame.notebook.OnShowPage)
        frame.BindRefresh(bind=True)

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
        bosh.gameInis = tuple(bosh.OblivionIni(x) for x in bush.game.iniFiles)
        progress(0.05, _(u'Initializing BsaInfos'))
        #bsaInfos: used in warnTooManyModsBsas() and modInfos strings detection
        bosh.bsaInfos = bosh.BSAInfos()
        bosh.bsaInfos.refresh()
        progress(0.20, _(u'Initializing ModInfos'))
        bosh.oblivionIni = bosh.gameInis[0]
        bosh.modInfos = bosh.ModInfos()
        bosh.modInfos.refresh()
        progress(0.50, _(u'Initializing SaveInfos'))
        bosh.saveInfos = bosh.SaveInfos()
        bosh.saveInfos.refresh()
        progress(0.60, _(u'Initializing IniInfos'))
        bosh.iniInfos = bosh.INIInfos()
        bosh.iniInfos.refresh(refresh_target=False)
        # screens/people/installers data are refreshed upon showing the panel
        #--Patch check
        if bush.game.esp.canBash:
            if not bosh.modInfos.bashed_patches and bass.inisettings['EnsurePatchExists']:
                progress(0.68, _(u'Generating Blank Bashed Patch'))
                bosh.modInfos.generateNextBashedPatch(selected_mods=())

    @staticmethod
    def InitVersion():
        """Perform any version to version conversion. Called by Init()."""
        #--Renames dictionary: Strings to Paths.
        if settings['bash.version'] < 40:
            #--Renames array
            newRenames = {}
            for key,value in settings['bash.mods.renames'].items():
                newRenames[GPath(key)] = GPath(value)
            settings['bash.mods.renames'] = newRenames
            #--Mod table data
            modTableData = bosh.modInfos.table.data
            for key in modTableData.keys():
                if not isinstance(key,bolt.Path):
                    modTableData[GPath(key)] = modTableData[key]
                    del modTableData[key]
        #--Window sizes by class name rather than by class
        if settings['bash.version'] < 43:
            for key,value in balt.sizes.items():
                if isinstance(key,ClassType):
                    balt.sizes[key.__name__] = value
                    del balt.sizes[key]
        #--Current Version
        if settings['bash.version'] != GetBashVersion():
            settings['bash.version'] = GetBashVersion()
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
    bosh.Installer.init_global_skips() # must be after loadDefaults - grr #178
    bosh.Installer.init_attributes_process()
    #--Wrye Balt
    settings['balt.WryeLog.temp'] = bass.dirs['saveBase'].join(u'WryeLogTemp.html')
    settings['balt.WryeLog.cssDir'] = bass.dirs['mopy'].join(u'Docs')
    #--StandAlone version?
    settings['bash.standalone'] = hasattr(sys,'frozen')
    initPatchers()

def InitImages():
    """Initialize color and image collections."""
    #--Colors
    for key,value in settings['bash.colors'].iteritems(): colors[key] = value
    #--Images
    imgDirJn = bass.dirs['images'].join
    def _png(name): return Image(GPath(imgDirJn(name)),PNG)
    #--Standard
    images['save.on'] = _png(u'save_on.png')
    images['save.off'] = _png(u'save_off.png')
    #--Misc
    #images['oblivion'] = Image(GPath(bass.dirs['images'].join(u'oblivion.png')),png)
    images['help.16'] = Image(GPath(imgDirJn(u'help16.png')))
    images['help.24'] = Image(GPath(imgDirJn(u'help24.png')))
    images['help.32'] = Image(GPath(imgDirJn(u'help32.png')))
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
    #--Bash
    images['bash.16'] = _png(u'bash_16.png')
    images['bash.24'] = _png(u'bash_24.png')
    images['bash.32'] = _png(u'bash_32.png')
    images['bash.16.blue'] = _png(u'bash_16_blue.png')
    images['bash.24.blue'] = _png(u'bash_24_blue.png')
    images['bash.32.blue'] = _png(u'bash_32_blue.png')
    #--Bash Patch Dialogue
    images['monkey.16'] = Image(GPath(imgDirJn(u'wryemonkey16.jpg')),JPEG)
    #--DocBrowser
    images['doc.16'] = _png(u'DocBrowser16.png')
    images['doc.24'] = _png(u'DocBrowser24.png')
    images['doc.32'] = _png(u'DocBrowser32.png')
    images['settingsbutton.16'] = _png(u'settingsbutton16.png')
    images['settingsbutton.24'] = _png(u'settingsbutton24.png')
    images['settingsbutton.32'] = _png(u'settingsbutton32.png')
    images['modchecker.16'] = _png(u'ModChecker16.png')
    images['modchecker.24'] = _png(u'ModChecker24.png')
    images['modchecker.32'] = _png(u'ModChecker32.png')
    images['pickle.16'] = _png(u'pickle16.png')
    images['pickle.24'] = _png(u'pickle24.png')
    images['pickle.32'] = _png(u'pickle32.png')
    #--Applications Icons
    Resources.bashRed = balt.ImageBundle()
    Resources.bashRed.Add(images['bash.16'])
    Resources.bashRed.Add(images['bash.24'])
    Resources.bashRed.Add(images['bash.32'])
    #--Application Subwindow Icons
    Resources.bashBlue = balt.ImageBundle()
    Resources.bashBlue.Add(images['bash.16.blue'])
    Resources.bashBlue.Add(images['bash.24.blue'])
    Resources.bashBlue.Add(images['bash.32.blue'])
    Resources.bashDocBrowser = balt.ImageBundle()
    Resources.bashDocBrowser.Add(images['doc.16'])
    Resources.bashDocBrowser.Add(images['doc.24'])
    Resources.bashDocBrowser.Add(images['doc.32'])
    Resources.bashMonkey = balt.ImageBundle()
    Resources.bashMonkey.Add(images['monkey.16'])

from .links import InitLinks

# Main ------------------------------------------------------------------------
if __name__ == '__main__':
    print _(u'Compiled')
