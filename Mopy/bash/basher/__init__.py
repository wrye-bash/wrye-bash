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
from collections import OrderedDict
import os
import re
import sys
import time
from types import ClassType
from functools import partial
#--wxPython
import collections
import wx
import wx.gizmos

#--Localization
#..Handled by bosh, so import that.
from .. import bush, bosh, bolt, bass, env, load_order
from ..bass import Resources
from ..bolt import BoltError, CancelError, SkipError, GPath, SubProgress, \
    deprint, AbstractError, formatInteger, formatDate, round_size
from ..bosh import omods, CoSaves, projects_walk_cache
from ..cint import CBash

startupinfo = bolt.startupinfo

#--Balt
from .. import balt
from ..balt import fill, CheckLink, EnabledLink, SeparatorLink, \
    Link, ChoiceLink, RoTextCtrl, staticBitmap, AppendableLink, ListBoxes, \
    SaveButton, CancelButton
from ..balt import checkBox, StaticText, spinCtrl, TextCtrl
from ..balt import spacer, hSizer, vSizer
from ..balt import colors, images, Image
from ..balt import Links, ItemLink
from ..balt import splitterStyle

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
    def idata(self): return self.window.data_store  # type: bosh.InstallersData
    @property
    def iPanel(self): return self.window.panel # type: InstallersPanel

class People_Link(Link):
    """PeopleData mixin"""
    @property
    def pdata(self): return self.window.data_store # type: bosh.PeopleData

# Exceptions ------------------------------------------------------------------
class BashError(BoltError): pass

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

# Windows ---------------------------------------------------------------------
#------------------------------------------------------------------------------
class NotebookPanel(wx.Panel):
    """Parent class for notebook panels."""
    # UI settings keys prefix - used for sashPos and uiList gui settings
    keyPrefix = 'OVERRIDE'
    _status_str = u'OVERRIDE:' + u' %d'

    def __init__(self, *args, **kwargs):
        super(NotebookPanel, self).__init__(*args, **kwargs)
        self._firstShow = True

    def RefreshUIColors(self):
        """Called to signal that UI color settings have changed."""
        pass

    def _sbCount(self): return self.__class__._status_str % len(self.listData)

    def SetStatusCount(self):
        """Sets status bar count field."""
        Link.Frame.SetStatusCount(self, self._sbCount())

    def ShowPanel(self):
        """To be called when particular panel is changed to and/or shown for
        first time.

        Default version resizes the columns if auto is on and sets Status bar
        text. It also sets the scroll bar and sash positions on first show.
        """
        if hasattr(self, '_firstShow'):
            self.uiList.SetScrollPosition()
            sashPos = settings.get(self.sashPosKey,
                                   self.__class__.defaultSashPos)
            self.splitter.SetSashPosition(sashPos)
            del self._firstShow
        self.uiList.autosizeColumns()
        self.SetStatusCount()

    def ClosePanel(self):
        """To be manually called when containing frame is closing. Use for
        saving data, scrollpos, etc."""
        if hasattr(self, 'listData'): # must be a _DataStore instance
        # the only SashPanels that do not have this attribute are ModDetails
        # and SaveDetails that use a MasterList whose data is initially {}
            self.listData.save()

#------------------------------------------------------------------------------
class _DetailsViewMixin(object):
    """Mixin to add detailsPanel attribute to a Panel with a details view.

    This is a hasty mixin. I added it to SashPanel so UILists can call
    SetDetails, RefreshDetails and ClearDetails on their panels. TODO !:
     - just mix it only in classes that _do_ have a details view (as it is
     even Details panels inherit it).
     - drop hideous if detailsPanel is not self, due to Installers, People
     using themselves as details (YAK!)
    """
    detailsPanel = None
    def _setDetails(self, fileName):
        if self.detailsPanel: self.detailsPanel.SetFile(
            fileName=fileName)
    def RefreshDetails(self): self._setDetails('SAME')
    def ClearDetails(self): self._setDetails(None)
    def SetDetails(self, fileName): self._setDetails(fileName)

    def RefreshUIColors(self):
        super(_DetailsViewMixin, self).RefreshUIColors()
        if self.detailsPanel: self.detailsPanel.RefreshUIColors()

    def ClosePanel(self):
        super(_DetailsViewMixin, self).ClosePanel()
        if self.detailsPanel and self.detailsPanel is not self:
            self.detailsPanel.ClosePanel()

    def ShowPanel(self):
        super(_DetailsViewMixin, self).ShowPanel()
        if self.detailsPanel and self.detailsPanel is not self:
            self.detailsPanel.ShowPanel()

    def GetDetailsItem(self):
        return self.detailsPanel.file_info if self.detailsPanel else None

class SashPanel(_DetailsViewMixin, NotebookPanel):
    """Subclass of Notebook Panel, designed for two pane panel."""
    defaultSashPos = minimumSize = 256

    def __init__(self, parent, sashGravity=0.5, isVertical=True,
                 style=splitterStyle):
        NotebookPanel.__init__(self, parent)
        self.splitter = splitter = wx.gizmos.ThinSplitterWindow(self,
                                                                style=style)
        self.left = wx.Panel(splitter)
        self.right = wx.Panel(splitter)
        if isVertical:
            splitter.SplitVertically(self.left, self.right)
        else:
            splitter.SplitHorizontally(self.left, self.right)
        self.isVertical = isVertical
        splitter.SetSashGravity(sashGravity)
        self.sashPosKey = self.__class__.keyPrefix + '.sashPos'
        # Don't allow unsplitting
        splitter.Bind(wx.EVT_SPLITTER_DCLICK, lambda self_, event: event.Veto())
        splitter.SetMinimumPaneSize(self.__class__.minimumSize)
        sizer = vSizer(
            (splitter,1,wx.EXPAND),
            )
        self.SetSizer(sizer)

    def ClosePanel(self):
        if not hasattr(self, '_firstShow'): # if the panel was shown
            settings[self.sashPosKey] = self.splitter.GetSashPosition()
            self.uiList.SaveScrollPosition(isVertical=self.isVertical)
        super(SashPanel, self).ClosePanel()

    def SelectUIListItem(self, item, deselectOthers=False):
        self.uiList.SelectAndShowItem(item, deselectOthers=deselectOthers,
                                      focus=True)

#------------------------------------------------------------------------------
class SashTankPanel(SashPanel):

    def __init__(self, parent):
        self.detailsItem = None
        super(SashTankPanel,self).__init__(parent)

    def ClosePanel(self):
        self.SaveDetails()
        super(SashTankPanel, self).ClosePanel()

#------------------------------------------------------------------------------
class _ModsUIList(balt.UIList):

    _esmsFirstCols = balt.UIList.nonReversibleCols
    @property
    def esmsFirst(self): return settings.get(self.keyPrefix + '.esmsFirst',
                            True) or self.sort in self._esmsFirstCols
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

    def forceEsmFirst(self): return self.sort in _ModsUIList._esmsFirstCols

#------------------------------------------------------------------------------
class MasterList(_ModsUIList):
    mainMenu = Links()
    itemMenu = Links()
    keyPrefix = 'bash.masters' # use for settings shared among the lists (cols)
    _editLabels = True
    #--Sorting
    _default_sort_col = 'Num'
    _sort_keys = {'Num'          : None, # sort by master index, the key itself
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
                item_format.font = Resources.fonts.bold
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
        return [self.data_store[item].name for item in sorted(self.GetItems())]

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
            items.sort(key=lambda a: self.data_store[a].status < 0)
    _extra_sortings = [_sortValidFirst]
    #--Labels
    labels = OrderedDict([
        ('File',      lambda self, path: path.s),
        ('Installer', lambda self, path: self.data_store.table.getItem(
                                                   path, 'installer', u'')),
    ])

    def CountTweakStatus(self):
        """Returns number of each type of tweak, in the
        following format:
        (applied,mismatched,not_applied,invalid)"""
        applied = 0
        mismatch = 0
        not_applied = 0
        invalid = 0
        for tweak in self.data_store.keys():
            status = self.data_store[tweak].status
            if status == -10: invalid += 1
            elif status == 0: not_applied += 1
            elif status == 10: mismatch += 1
            elif status == 20: applied += 1
        return applied,mismatch,not_applied,invalid

    def ListTweaks(self):
        """Returns text list of tweaks"""
        tweaklist = _(u'Active Ini Tweaks:') + u'\n'
        tweaklist += u'[spoiler][xml]\n'
        tweaks = self.data_store.keys()
        tweaks.sort()
        for tweak in tweaks:
            if not self.data_store[tweak].status == 20: continue
            tweaklist+= u'%s\n' % tweak
        tweaklist += u'[/xml][/spoiler]\n'
        return tweaklist

    def RefreshUIValid(self):
        valid = [k for k, v in self.data_store.iteritems() if v.status >= 0]
        self.RefreshUI(files=valid)

    @staticmethod
    def filterOutDefaultTweaks(tweaks):
        """Filter out default tweaks from tweaks iterable."""
        return filter(lambda x: bass.dirs['tweaks'].join(x).isfile(), tweaks)

    def _toDelete(self, items):
        items = super(INIList, self)._toDelete(items)
        return self.filterOutDefaultTweaks(items) # will refilter if coming
        # from INI_Delete - expensive but I can't allow default tweaks deletion

    def set_item_format(self, ini_name, item_format):
        iniInfo = self.data_store[ini_name]
        status = iniInfo.getStatus()
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
        tweak = bosh.iniInfos[hitItem]
        if tweak.status == 20: return # already applied
        #-- If we're applying to Oblivion.ini, show the warning
        iniPanel = self.panel
        choice = iniPanel.GetChoice().tail
        if choice in bush.game.iniFiles:
            message = (_(u"Apply an ini tweak to %s?") % choice
                       + u'\n\n' +
                       _(u"WARNING: Incorrect tweaks can result in CTDs and even damage to you computer!")
                       )
            if not balt.askContinue(self, message, 'bash.iniTweaks.continue',
                                    _(u"INI Tweaks")): return
        #--No point applying a tweak that's already applied
        file_ = tweak.dir.join(hitItem)
        self.data_store.ini.applyTweakFile(file_)
        self.RefreshUIValid()
        iniPanel.iniContents.RefreshIniContents()
        iniPanel.tweakContents.RefreshTweakLineCtrl(self.data_store[0])

    def _select(self, tweakfile): self.panel.SelectTweak(tweakfile)

#------------------------------------------------------------------------------
class INITweakLineCtrl(wx.ListCtrl):
    def __init__(self, parent, iniContents, style=wx.LC_REPORT|wx.LC_SINGLE_SEL|wx.LC_NO_HEADER):
        wx.ListCtrl.__init__(self, parent, style=style)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnSelect)
        self.InsertColumn(0,u'')
        self.tweakLines = []
        self.iniContents = iniContents

    def OnSelect(self, event):
        index = event.GetIndex()
        iniLine = self.tweakLines[index][5]
        self.SetItemState(index, 0, wx.LIST_STATE_SELECTED)
        if iniLine != -1:
            self.iniContents.EnsureVisible(iniLine)
            scroll = iniLine - self.iniContents.GetScrollPos(wx.VERTICAL) - index
            self.iniContents.ScrollLines(scroll)
        event.Skip()

    def RefreshTweakLineCtrl(self, tweakPath):
        if tweakPath is None:
            self.DeleteAllItems()
            return
        ini = bosh.iniInfos.ini
        tweakPath = bosh.iniInfos[tweakPath].dir.join(tweakPath)
        self.tweakLines = ini.getTweakFileLines(tweakPath)
        num = self.GetItemCount()
        updated = []
        for i,line in enumerate(self.tweakLines):
            #--Line
            if i >= num:
                self.InsertStringItem(i, line[0])
            else:
                self.SetStringItem(i, 0, line[0])
            #--Line color
            status = line[4]
            if status == -10: color = colors['tweak.bkgd.invalid']
            elif status == 10: color = colors['tweak.bkgd.mismatched']
            elif status == 20: color = colors['tweak.bkgd.matched']
            elif line[6]: color = colors['tweak.bkgd.mismatched']
            else: color = self.GetBackgroundColour()
            self.SetItemBackgroundColour(i, color)
            #--Set iniContents color
            lineNo = line[5]
            if lineNo != -1:
                self.iniContents.SetItemBackgroundColour(lineNo,color)
                updated.append(lineNo)
        #--Delete extra lines
        for i in range(len(self.tweakLines),num):
            self.DeleteItem(len(self.tweakLines))
        #--Reset line color for other iniContents lines
        for i in range(self.iniContents.GetItemCount()):
            if i in updated: continue
            if self.iniContents.GetItemBackgroundColour(i) != self.iniContents.GetBackgroundColour():
                self.iniContents.SetItemBackgroundColour(i, self.iniContents.GetBackgroundColour())
        #--Refresh column width
        self.SetColumnWidth(0,wx.LIST_AUTOSIZE_USEHEADER)

#------------------------------------------------------------------------------
class INILineCtrl(wx.ListCtrl):
    def __init__(self, parent, style=wx.LC_REPORT|wx.LC_SINGLE_SEL|wx.LC_NO_HEADER):
        wx.ListCtrl.__init__(self, parent, style=style)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnSelect)
        self.InsertColumn(0, u'')

    def SetTweakLinesCtrl(self, control):
        self.tweakContents = control

    def OnSelect(self, event):
        index = event.GetIndex()
        self.SetItemState(index, 0, wx.LIST_STATE_SELECTED)
        for i,line in enumerate(self.tweakContents.tweakLines):
            if index == line[5]:
                self.tweakContents.EnsureVisible(i)
                scroll = i - self.tweakContents.GetScrollPos(wx.VERTICAL) - index
                self.tweakContents.ScrollLines(scroll)
                break
        event.Skip()

    def RefreshIniContents(self, resetScroll=False):
        num = self.GetItemCount()
        if resetScroll:
            self.EnsureVisible(0)
        try:
            with bosh.iniInfos.ini.path.open('r') as ini:
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
            if hasattr(Link.Frame, 'notebook'): # we may be called before
                # the notebook is build, in INIPanel.__init__ > SetBaseIni
                page = Link.Frame.notebook.currentPage
                if page != self.GetParent().GetParent().GetParent():
                    warn = False
            else: warn = False # we are booting - queue the warning cause it
            # interrupts building of the UI !
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
        ('File',       lambda self, path: self.data_store.masterWithVersion(path.s)),
        ('Load Order', lambda self, path: self.data_store.hexIndexString(path)),
        ('Rating',     lambda self, path: self._get(path)('rating', u'')),
        ('Group',      lambda self, path: self._get(path)('group', u'')),
        ('Installer',  lambda self, path: self._get(path)('installer', u'')),
        ('Modified',   lambda self, path: formatDate(self.data_store[path].mtime)),
        ('Size',       lambda self, path: round_size(self.data_store[path].size)),
        ('Author',     lambda self, path: self.data_store[path].header.author if
                                      self.data_store[path].header else u'-'),
        ('CRC',        lambda self, path:
                                        u'%08X' % self.data_store[path].cachedCrc()),
        ('Mod Status', lambda self, path: self.data_store[path].txt_status()),
    ])

    #-- Drag and Drop-----------------------------------------------------
    def _dropIndexes(self, indexes, newIndex): # will mess with plugins cache !
        """Drop contiguous indexes on newIndex and return True if LO changed"""
        if newIndex < 0: return False # from OnChar() & moving master esm up
        count = self._gList.GetItemCount()
        dropItem = self.GetItem(newIndex if (count > newIndex) else count - 1)
        firstItem = self.GetItem(indexes[0])
        lastItem = self.GetItem(indexes[-1])
        return bosh.modInfos.dropItems(dropItem, firstItem, lastItem)

    def OnDropIndexes(self, indexes, newIndex):
        if self._dropIndexes(indexes, newIndex): self._refreshOnDrop()

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
            item_format.font = Resources.fonts.italic
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
        if kwargs.pop('refreshSaves', False): Link.Frame.saveListRefresh()

    #--Events ---------------------------------------------
    def OnDClick(self,event):
        """Handle doubleclicking a mod in the Mods List."""
        hitItem = self._getItemClicked(event)
        if not hitItem: return
        fileInfo = self.data_store[hitItem]
        if not Link.Frame.docBrowser:
            from .frames import DocBrowser
            DocBrowser().Show()
            settings['bash.modDocs.show'] = True
        #balt.ensureDisplayed(docBrowser)
        Link.Frame.docBrowser.SetMod(fileInfo.name)
        Link.Frame.docBrowser.Raise()

    def OnChar(self,event):
        """Char event: Reorder (Ctrl+Up and Ctrl+Down)."""
        code = event.GetKeyCode()
        if ((event.CmdDown() and code in balt.wxArrows) and
            (self.sort in self._dndColumns)):
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
                if chunk[-1] + moveMod == self._gList.GetItemCount():
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
            self.SelectItem(mod_clicked_on_icon, deselectOthers=True)
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
    """Bsa/Mods/Saves details, DEPRECATED: we need common data stores API!"""
    @property
    def file_info(self): raise AbstractError
    @property
    def displayed_item(self):
        return self.file_info.name if self.file_info else None

class _SashDetailsPanel(_EditableMixinOnFileInfos, SashPanel):
    """Mod and Saves details panel, feature a master's list."""
    defaultSubSashPos = 0 # that was the default for mods (for saves 500)

    def __init__(self, parent):
        # TODO(ut) use super !! Initialize the UIList here !
        SashPanel.__init__(self, parent, sashGravity=1.0, isVertical=False,
                           style=wx.SW_BORDER | splitterStyle)
        self.top, self.bottom = self.left, self.right
        self.subSplitter = wx.gizmos.ThinSplitterWindow(self.bottom,
                                                        style=splitterStyle)
        self.masterPanel = wx.Panel(self.subSplitter)
        _EditableMixinOnFileInfos.__init__(self, self.masterPanel)

    def ShowPanel(self): ##: does not call super
        if hasattr(self, '_firstShow'):
            sashPos = settings.get(self.sashPosKey,
                                   self.__class__.defaultSashPos)
            self.splitter.SetSashPosition(sashPos)
            sashPos = settings.get(self.keyPrefix + '.subSplitterSashPos',
                                   self.__class__.defaultSubSashPos)
            self.subSplitter.SetSashPosition(sashPos)
            del self._firstShow
        self.uilist.autosizeColumns()

    def ClosePanel(self): ##: does not call super
        if not hasattr(self, '_firstShow'):
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
        modPanel = parent.GetParent().GetParent()
        subSplitter, masterPanel = self.subSplitter, self.masterPanel
        top, bottom = self.top, self.bottom
        #--Data
        self.modInfo = None
        textWidth = 200
        #--Version
        self.version = StaticText(top,u'v0.00')
        #--File Name
        self.file = TextCtrl(top, onKillFocus=self.OnEditFile,
                             onText=self.OnFileEdit, maxChars=textWidth) # size=(textWidth,-1))
        #--Author
        self.author = TextCtrl(top, onKillFocus=self.OnEditAuthor,
                               onText=self.OnAuthorEdit, maxChars=512) # size=(textWidth,-1))
        #--Modified
        self.modified = TextCtrl(top,size=(textWidth, -1),
                                 onKillFocus=self.OnEditModified,
                                 onText=self.OnModifiedEdit, maxChars=32)
        #--Description
        self.description = TextCtrl(top, size=(textWidth, 150),
                                    multiline=True, autotooltip=False,
                                    onKillFocus=self.OnEditDescription,
                                    onText=self.OnDescrEdit, maxChars=512)
        #--Masters
        self.uilist = MasterList(masterPanel, keyPrefix=self.keyPrefix,
                                 panel=modPanel, detailsPanel=self)
        #--Bash tags
        tagPanel = wx.Panel(subSplitter)
        self.allTags = bosh.allTags
        self.gTags = RoTextCtrl(tagPanel, autotooltip=False,
                                size=(textWidth, 100))
        #--Layout
        detailsSizer = vSizer(
            (hSizer(
                (StaticText(top,_(u"File:")),0,wx.TOP,4),
                spacer,
                (self.version,0,wx.TOP|wx.RIGHT,4)
                ),0,wx.EXPAND),
            (hSizer((self.file,1,wx.EXPAND)),0,wx.EXPAND),
            (hSizer((StaticText(top,_(u"Author:")),0,wx.TOP,4)),0,wx.EXPAND),
            (hSizer((self.author,1,wx.EXPAND)),0,wx.EXPAND),
            (hSizer((StaticText(top,_(u"Modified:")),0,wx.TOP,4)),0,wx.EXPAND),
            (hSizer((self.modified,1,wx.EXPAND)),0,wx.EXPAND),
            (hSizer((StaticText(top,_(u"Description:")),0,wx.TOP,4)),0,wx.EXPAND),
            (hSizer((self.description,1,wx.EXPAND)),1,wx.EXPAND))
        detailsSizer.SetSizeHints(top)
        top.SetSizer(detailsSizer)
        subSplitter.SetMinimumPaneSize(100)
        subSplitter.SplitHorizontally(masterPanel,tagPanel)
        subSplitter.SetSashGravity(0.5)
        mastersSizer = vSizer(
            (hSizer((StaticText(masterPanel,_(u"Masters:")),0,wx.TOP,4)),0,wx.EXPAND),
            (hSizer((self.uilist,1,wx.EXPAND)),1,wx.EXPAND),
            (hSizer(
                self.save,
                (self.cancel,0,wx.LEFT,4)
                ),0,wx.EXPAND|wx.TOP,4),)
        tagsSizer = vSizer(
            (StaticText(tagPanel,_(u"Bash Tags:")),0,wx.TOP,4),
            (hSizer((self.gTags,1,wx.EXPAND)),1,wx.EXPAND))
        mastersSizer.SetSizeHints(masterPanel)
        masterPanel.SetSizer(mastersSizer)
        tagsSizer.SetSizeHints(masterPanel)
        tagPanel.SetSizer(tagsSizer)
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
    def OnFileEdit(self, event):
        self._OnTextEdit(event, self.fileStr, self.file)
    def OnAuthorEdit(self, event):
        self._OnTextEdit(event, self.authorStr, self.author)
    def OnModifiedEdit(self, event):
        self._OnTextEdit(event, self.modifiedStr, self.modified)
    def OnDescrEdit(self, event):
        self._OnTextEdit(event, self.descriptionStr.replace(
            '\r\n', '\n').replace('\r', '\n'), self.description)

    def OnEditFile(self):
        if not self.modInfo: return
        #--Changed?
        fileStr = self.file.GetValue()
        if fileStr == self.fileStr: return
        #--Extension Changed?
        if fileStr[-4:].lower() != self.fileStr[-4:].lower():
            balt.showError(self,_(u"Incorrect file extension: ")+fileStr[-3:])
            self.file.SetValue(self.fileStr)
        #--Else file exists?
        elif self.modInfo.dir.join(fileStr).exists():
            balt.showError(self,_(u"File %s already exists.") % fileStr)
            self.file.SetValue(self.fileStr)
        #--Okay?
        else:
            self.fileStr = fileStr
            self.SetEdited()

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

    bsaAndVoice = _(u'This mod has an associated archive (%s.bsa) and an '
        u'associated voice directory (Sound\\Voices\\%s), which will become '
        u'detached when the mod is renamed.') + u'\n\n' + _(u'Note that the '
        u'BSA archive may also contain a voice directory (Sound\\Voices\\%s), '
        u'which would remain detached even if the archive name is adjusted.')
    bsa = _(u'This mod has an associated archive (%s.bsa), which will become '
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
            bosh.modInfos.refresh(scanData=False, _modTimesChange=True)
            BashFrame.modList.RefreshUI(refreshSaves=True) # True ?
            return
        #--Backup
        modInfo.makeBackup()
        #--Change Name?
        fileName = modInfo.name
        if changeName:
            oldName,newName = modInfo.name,GPath(self.fileStr.strip())
            #--Bad name?
            if (bosh.modInfos.isBadFileName(newName.s) and
                not balt.askContinue(self,_(u'File name %s cannot be encoded to ASCII.  %s may not be able to activate this plugin because of this.  Do you want to rename the plugin anyway?')
                                     % (newName.s,bush.game.displayName),
                                     'bash.rename.isBadFileName.continue')
                ):
                return
            settings.getChanged('bash.mods.renames')[oldName] = newName
            bosh.modInfos.rename(oldName,newName)
            fileName = newName
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
        bosh.modInfos.refresh(scanData=False, _modTimesChange=changeDate)
        BashFrame.modList.RefreshUI(refreshSaves=True) # True ?

    #--Bash Tags
    def ShowBashTagsMenu(self):
        """Show bash tags menu."""
        if not self.modInfo: return
        #--Links closure
        mod_info = self.modInfo
        mod_tags = mod_info.getBashTags()
        is_auto = bosh.modInfos.table.getItem(mod_info.name, 'autoBashTags',
                                              True)
        all_tags = self.allTags
        def _refreshUI(): BashFrame.modList.RefreshUI(files=[mod_info.name],
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
                if mod_info.setBashTagsDesc(mod_info.getBashTags()):
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
            def _choices(self): return all_tags
        ##: Popup the menu - ChoiceLink should really be a Links subclass
        tagLinks = Links()
        tagLinks.append(_TagLinks())
        tagLinks.PopupMenu(self.gTags, Link.Frame, None)

#------------------------------------------------------------------------------
class INIPanel(SashPanel):
    keyPrefix = 'bash.ini'

    def __init__(self, parent):
        SashPanel.__init__(self, parent)
        left,right = self.left, self.right
        #--Remove from list button
        self.button = balt.Button(right, _(u'Remove'),
                                  onButClick=self.OnRemove)
        #--Edit button
        self.editButton = balt.Button(right, _(u'Edit...'),
                                      onButClick=self.OnEdit)
        #--Choices
        self.choices = settings['bash.ini.choices']
        self.choice = settings['bash.ini.choice']
        self.CheckTargets()
        self.lastDir = bass.dirs['mods'].s
        self.SortChoices()
        if self.choice < 0 or self.choice >= len(self.sortKeys):
            self.choice = 0
        #--Watch for changes to the target INI
        self.trackedInfo = bosh.TrackedFileInfos(bosh.INIInfo)
        self.trackedInfo.track(self.GetChoice())
        #--Ini file
        self.iniContents = INILineCtrl(right)
        #--Tweak file
        self.tweakContents = INITweakLineCtrl(right,self.iniContents)
        self.iniContents.SetTweakLinesCtrl(self.tweakContents)
        self.tweakName = RoTextCtrl(right, noborder=True, multiline=False)
        self.SetBaseIni(self.GetChoice())
        self.listData = bosh.iniInfos
        self.uiList = BashFrame.iniList = INIList(
            left, listData=self.listData, keyPrefix=self.keyPrefix, panel=self)
        self.comboBox = balt.ComboBox(right, value=self.GetChoiceString(),
                                      choices=self.sortKeys)
        #--Events
        self.comboBox.Bind(wx.EVT_COMBOBOX,self.OnSelectDropDown)
        #--Layout
        iniSizer = vSizer(
                (hSizer(
                    (self.comboBox,1,wx.ALIGN_CENTER|wx.EXPAND|wx.TOP,1),
                    ((4,0),0),
                    (self.button,0,wx.ALIGN_TOP,0),
                    (self.editButton,0,wx.ALIGN_TOP,0),
                    ),0,wx.EXPAND|wx.BOTTOM,4),
                (self.iniContents,1,wx.EXPAND),
                )
        lSizer = hSizer(
            (self.uiList,2,wx.EXPAND),
            )
        rSizer = hSizer(
            (vSizer(
                (self.tweakName,0,wx.EXPAND|wx.TOP,6),
                (self.tweakContents,1,wx.EXPAND),
                ),1,wx.EXPAND|wx.RIGHT,4),
            (iniSizer,1,wx.EXPAND),
            )
        iniSizer.SetSizeHints(right)
        right.SetSizer(rSizer)
        left.SetSizer(lSizer)

    def RefreshUIColors(self):
        self.RefreshPanel()

    def SelectTweak(self, tweakFile):
        self.tweakName.SetValue(tweakFile.sbody)
        self.tweakContents.RefreshTweakLineCtrl(tweakFile)

    def GetChoice(self,index=None):
        """ Return path for a given choice, or the
        currently selected choice if index is None."""
        if index is None:
            return self.choices[self.sortKeys[self.choice]]
        else:
            return self.choices[self.sortKeys[index]]

    def GetChoiceString(self,index=None):
        """Return text for a given choice, or the
        currently selected choice if index is None."""
        if index is None:
            return self.sortKeys[self.choice]
        else:
            return self.sortKeys[index]

    def ShowPanel(self):
        changed = self.trackedInfo.refreshTracked()
        changed = set([x for x in changed if x != bosh.oblivionIni.path])
        if self.GetChoice() in changed:
            self.RefreshPanel()
        super(INIPanel, self).ShowPanel()

    def RefreshPanel(self, what='ALL'):
        if what == 'ALL' or what == 'TARGETS':
            # Refresh the drop down list
            path = self.GetChoice()
            if path is None:
                self.choice -= 1
            elif not path.isfile():
                for iFile in bosh.gameInis:
                    if iFile.path == path:
                        break
                else:
                    del self.choices[self.GetChoiceString()]
                    self.choice -= 1
                    what = 'ALL'
            self.SetBaseIni(self.GetChoice())
            self.comboBox.SetItems(self.SortChoices())
            self.comboBox.SetSelection(self.choice)
        if what == 'ALL' or what == 'TWEAKS':
            self.uiList.RefreshUI()

    def SetBaseIni(self,path=None):
        """Sets the target INI file."""
        choicePath = self.GetChoice()
        for iFile in bosh.gameInis:
            if iFile.path == choicePath:
                isGameIni = True
                target = iFile
                break
        else:
            if not path:
                path = choicePath
            target = bosh.BestIniFile(path)
            isGameIni = False
        refresh = bosh.iniInfos.ini != target
        bosh.iniInfos.ini = target
        self.button.Enable(not isGameIni)
        selected = None
        # iniList can be None below cause we are called in INIPanel.__init__()
        # before iniList is assigned - possibly to avoid the RefreshUI below
        if BashFrame.iniList is not None:
            selected = BashFrame.iniList.GetSelected()
            if len(selected) > 0:
                selected = selected[0]
            else:
                selected = None
        if refresh:
            self.trackedInfo = bosh.TrackedFileInfos(bosh.INIInfo)
            self.trackedInfo.track(self.GetChoice())
        self.iniContents.RefreshIniContents(refresh)
        self.tweakContents.RefreshTweakLineCtrl(selected)
        if BashFrame.iniList is not None: BashFrame.iniList.RefreshUI()

    def OnRemove(self):
        """Called when the 'Remove' button is pressed."""
        selection = self.comboBox.GetValue()
        self.choice -= 1
        del self.choices[selection]
        self.comboBox.SetItems(self.SortChoices())
        self.comboBox.SetSelection(self.choice)
        self.SetBaseIni()
        self.uiList.RefreshUI()

    def OnEdit(self):
        """Called when the 'Edit' button is pressed."""
        selection = self.comboBox.GetValue()
        self.choices[selection].start()

    def CheckTargets(self):
        """Check the list of target INIs, remove any that don't exist"""
        changed = False
        for i in self.choices.keys():
            if i == _(u'Browse...'): continue
            path = self.choices[i]
            # If user started with non-translated, 'Browse...'
            # will still be in here, but in English.  It wont get picked
            # up by the previous check, so we'll just delete any non-Path
            # objects.  That will take care of it.
            if not isinstance(path,bolt.Path) or not path.isfile():
                del self.choices[i]
                changed = True
        csChoices = [x.lower() for x in self.choices]
        for iFile in bosh.gameInis:
            if iFile.path.tail.cs not in csChoices:
                self.choices[iFile.path.stail] = iFile.path
                changed = True
        if _(u'Browse...') not in self.choices:
            self.choices[_(u'Browse...')] = None
            changed = True
        if changed: self.SortChoices()
        if len(self.choices.keys()) <= self.choice + 1:
            self.choice = 0

    def SortChoices(self):
        """Sorts the list of target INIs alphabetically, but with
        Oblivion.ini at the top and 'Browse...' at the bottom"""
        keys = self.choices.keys()
        # Sort alphabetically
        keys.sort()
        # Sort Oblivion.ini to the top, and 'Browse...' to the bottom
        keys.sort(key=lambda a:
                  bush.game.iniFiles.index(a) if a in bush.game.iniFiles
                  else len(bush.game.iniFiles)+1 if a == _(u'Browse...')
                  else len(bush.game.iniFiles))
        self.sortKeys = keys
        return keys

    def _sbCount(self):
        stati = self.uiList.CountTweakStatus()
        return _(u'Tweaks:') + u' %d/%d' % (stati[0], sum(stati[:-1]))

    def AddOrSelectIniDropDown(self, path):
        if path.stail not in self.choices:
            self.choices[path.stail] = path
            self.SortChoices()
            self.comboBox.SetItems(self.sortKeys)
        else:
            if self.choice == self.sortKeys.index(path.stail):
                return
        self.choice = self.sortKeys.index(path.stail)
        self.comboBox.SetSelection(self.choice)
        self.SetBaseIni(path)
        self.uiList.RefreshUI()

    def OnSelectDropDown(self,event):
        """Called when the user selects a new target INI from the drop down."""
        selection = event.GetString()
        path = self.choices[selection]
        if not path:
            # 'Browse...'
            wildcard =  u'|'.join([_(u'Supported files')+u' (*.ini,*.cfg)|*.ini;*.cfg',
                                   _(u'INI files')+u' (*.ini)|*.ini',
                                   _(u'Config files')+u' (*.cfg)|*.cfg',
                                   ])
            path = balt.askOpen(self,defaultDir=self.lastDir,wildcard=wildcard,mustExist=True)
            if not path:
                self.comboBox.SetSelection(self.choice)
                return
            # Make sure the 'new' file isn't already in the list
            if path.stail in self.choices:
                new_choice = self.sortKeys.index(path.stail)
                refresh = new_choice != self.choice
                self.choice = new_choice
                self.comboBox.SetSelection(self.choice)
                if refresh:
                    self.SetBaseIni(path)
                    self.uiList.RefreshUI()
                return
            self.lastDir = path.shead
        self.AddOrSelectIniDropDown(path)

    def ClosePanel(self):
        settings['bash.ini.choices'] = self.choices
        settings['bash.ini.choice'] = self.choice
        super(INIPanel, self).ClosePanel()

#------------------------------------------------------------------------------
class ModPanel(SashPanel):
    keyPrefix = 'bash.mods'

    def __init__(self,parent):
        SashPanel.__init__(self, parent, sashGravity=1.0)
        left,right = self.left, self.right
        self.listData = bosh.modInfos
        self.detailsPanel = ModDetails(right)
        self.uiList = BashFrame.modList = ModList(
            left, listData=self.listData, keyPrefix=self.keyPrefix, panel=self)
        #--Layout
        right.SetSizer(hSizer((self.detailsPanel,1,wx.EXPAND)))
        left.SetSizer(hSizer((self.uiList,2,wx.EXPAND)))

    def RefreshUIColors(self):
        self.uiList.RefreshUI(refreshSaves=False) # refreshing colors

    def _sbCount(self): return _(u'Mods:') + u' %d/%d' % (
        len(load_order.activeCached()), len(bosh.modInfos))

#------------------------------------------------------------------------------
class SaveList(balt.UIList):
    #--Class Data
    mainMenu = Links() #--Column menu
    itemMenu = Links() #--Single item menu
    _editLabels = True
    _sort_keys = {'File'    : None, # just sort by name
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
        ('File',     lambda self, path: path.s),
        ('Modified', lambda self, path: formatDate(self.data_store[path].mtime)),
        ('Size',     lambda self, path: round_size(self.data_store[path].size)),
        ('PlayTime', lambda self, path: self._playTime(self.data_store[path])),
        ('Player',   lambda self, path: self._headInfo(self.data_store[path],
                                                       'pcName')),
        ('Cell',     lambda self, path: self._headInfo(self.data_store[path],
                                                       'pcLocation')),
    ])

    def OnLabelEdited(self, event):
        """Savegame renamed."""
        if event.IsEditCancelled(): return
        #--File Info
        newName = event.GetLabel()
        detail_item = self.panel.GetDetailsItem()
        item_edited = detail_item.name if detail_item else None
        if not newName.lower().endswith(bush.game.ess.ext):
            newName += bush.game.ess.ext
        rePattern = re.compile(ur'^[^/\\:*?"<>|]+?$', re.I | re.U)
        maPattern = rePattern.match(newName)
        if not maPattern:
            balt.showError(self, _(u'Bad extension or file root: ') + newName)
            event.Veto()
            return
        newFileName = newName
        selected = self.GetSelected()
        to_select = set(selected)
        for index, path in enumerate(selected):
            if bosh.saveInfos.bak_file_pattern.match(path.s): continue
            if index:
                newFileName = newName.replace(bush.game.ess.ext, (
                    u'%d' % index) + bush.game.ess.ext)
            newFileName = GPath(newFileName)
            if newFileName != path:
                oldPath = bosh.saveInfos.dir.join(path)
                newPath = bosh.saveInfos.dir.join(newFileName)
                renames = [(oldPath, newPath)]
                renames.extend(CoSaves.get_new_paths(oldPath, newPath))
                if not newPath.exists():
                    try:
                        bosh.saveInfos.rename(path, newFileName)
                        to_select.discard(path)
                        to_select.add(newFileName)
                        if path == item_edited:
                            item_edited = newFileName
                    except (OSError, IOError):
                        deprint('Renaming %s to %s failed'
                                % (oldPath, newPath), traceback=True)
                        ##: WindowsError:[Error 32]The process cannot access...
                        for old, new in renames:
                            if new.exists() and not old.exists():
                                # some cosave move failed, restore files
                                new.moveTo(old)
                            if new.exists() and old.exists(): new.remove()
                        break
        self.RefreshUI(files=to_select)
        #--Reselect the items - renamed or not
        self.SelectItemsNoCallback(to_select)
        if item_edited: self.SelectItem(item_edited)
        event.Veto() # needed ! clears new name from label on exception

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
        savePanel = parent.GetParent().GetParent()
        subSplitter, masterPanel = self.subSplitter, self.masterPanel
        top, bottom = self.top, self.bottom
        #--Data
        self.saveInfo = None
        textWidth = 200
        #--File Name
        self.file = TextCtrl(top, size=(textWidth, -1),
                             onKillFocus=self.OnEditFile,
                             onText=self.OnTextEdit, maxChars=256)
        #--Player Info
        self.playerInfo = StaticText(top,u" \n \n ")
        self.gCoSaves = StaticText(top,u'--\n--')
        #--Picture
        self.picture = balt.Picture(top,textWidth,192*textWidth/256,style=wx.BORDER_SUNKEN,background=colors['screens.bkgd.image']) #--Native: 256x192
        notePanel = wx.Panel(subSplitter)
        #--Masters
        self.uilist = MasterList(masterPanel, keyPrefix=self.keyPrefix,
                                 panel=savePanel, detailsPanel=self)
        #--Save Info
        self.gInfo = TextCtrl(notePanel, size=(textWidth, 100), multiline=True,
                              onText=self.OnInfoEdit, maxChars=2048)
        #--Layout
        detailsSizer = vSizer(
            (self.file,0,wx.EXPAND|wx.TOP,4),
            (hSizer(
                (self.playerInfo,1,wx.EXPAND),
                (self.gCoSaves,0,wx.EXPAND),
                ),0,wx.EXPAND|wx.TOP,4),
            (self.picture,1,wx.TOP|wx.EXPAND,4),
            )
        mastersSizer = vSizer(
            (self.uilist,1,wx.EXPAND|wx.TOP,4),
            (hSizer(
                self.save,
                (self.cancel,0,wx.LEFT,4),
                )),
            )
        noteSizer = vSizer(
            (hSizer((self.gInfo,1,wx.EXPAND)),1,wx.EXPAND),
            )
        detailsSizer.SetSizeHints(top)
        top.SetSizer(detailsSizer)
        subSplitter.SetMinimumPaneSize(100)
        subSplitter.SplitHorizontally(masterPanel,notePanel)
        subSplitter.SetSashGravity(1.0)
        mastersSizer.SetSizeHints(masterPanel)
        masterPanel.SetSizer(mastersSizer)
        noteSizer.SetSizeHints(masterPanel)
        notePanel.SetSizer(noteSizer)
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
        self.playerInfo.SetLabel((self.playerNameStr+u'\n'+
                                  _(u'Level')+u' %d, '+
                                  _(u'Day')+u' %d, '+
                                  _(u'Play')+u' %d:%02d\n%s') %
                                 (self.playerLevel,int(self.gameDays),
                                  self.playMinutes/60,(self.playMinutes%60),
                                  self.curCellStr))
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
        if fileName:
            self.gInfo.SetValue(bosh.saveInfos.table.getItem(fileName,'info',_(u'Notes: ')))
        else:
            self.gInfo.SetValue(_(u'Notes: '))

    def OnInfoEdit(self,event):
        """Info field was edited."""
        if self.saveInfo and self.gInfo.IsModified():
            bosh.saveInfos.table.setItem(self.saveInfo.name, 'info',
                                         self.gInfo.GetValue())
        event.Skip() # not strictly needed - no other handler for onKillFocus

    def OnTextEdit(self,event):
        """Event: Editing file or save name text."""
        if not self.saveInfo: return
        if not self.edited and self.fileStr != self.file.GetValue():
            self.SetEdited()
        event.Skip()

    def OnEditFile(self):
        """Event: Finished editing file name."""
        if not self.saveInfo: return
        #--Changed?
        fileStr = self.file.GetValue()
        if fileStr == self.fileStr: return
        #--Extension Changed?
        if self.fileStr[-4:].lower() not in (bush.game.ess.ext, u'.bak'):
            balt.showError(self,_(u"Incorrect file extension: ")+fileStr[-3:])
            self.file.SetValue(self.fileStr)
        #--Else file exists?
        elif self.saveInfo.dir.join(fileStr).exists():
            balt.showError(self,_(u"File %s already exists.") % (fileStr,))
            self.file.SetValue(self.fileStr)
        #--Okay?
        else:
            self.fileStr = fileStr
            self.SetEdited()

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
            bosh.saveInfos.rename(oldName,newName)
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
            BashFrame.saveListRefresh()
        else: # files=[saveInfo.name], Nope: deleted oldName drives _glist nuts
            BashFrame.saveListRefresh()

    def RefreshUIColors(self):
        self.picture.SetBackground(colors['screens.bkgd.image'])

#------------------------------------------------------------------------------
class SavePanel(SashPanel):
    """Savegames tab."""
    keyPrefix = 'bash.saves'
    _status_str = _(u'Saves:') + u' %d'

    def __init__(self,parent):
        if not bush.game.ess.canReadBasic:
            raise BoltError(u'Wrye Bash cannot read save games for %s.' %
                bush.game.displayName)
        SashPanel.__init__(self, parent, sashGravity=1.0)
        left,right = self.left, self.right
        self.listData = bosh.saveInfos
        self.detailsPanel = SaveDetails(right)
        self.uiList = BashFrame.saveList = SaveList(
            left, listData=self.listData, keyPrefix=self.keyPrefix, panel=self)
        #--Layout
        right.SetSizer(hSizer((self.detailsPanel,1,wx.EXPAND)))
        left.SetSizer(hSizer((self.uiList, 2, wx.EXPAND)))

    def RefreshUIColors(self):
        self.uiList.RefreshUI()
        super(SavePanel, self).RefreshUIColors()

    def ClosePanel(self):
        bosh.saveInfos.profiles.save()
        super(SavePanel, self).ClosePanel()

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
        ('Package',  lambda self, path: path.s),
        ('Order',    lambda self, path: unicode(self.data_store[path].order)),
        ('Modified', lambda self, path: formatDate(self.data_store[path].modified)),
        ('Size',     lambda self, path: self.data_store[path].size_string()),
        ('Files',    lambda self, path: self.data_store[path].number_string(
            self.data_store[path].num_of_files)),
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

    def OnBeginEditLabel(self,event):
        """Start renaming installers"""
        #--Only rename multiple items of the same type
        firstItem = self.data_store[self.GetSelected()[0]]
        if isinstance(firstItem,bosh.InstallerMarker):
            installer_type = bosh.InstallerMarker
        elif isinstance(firstItem,bosh.InstallerArchive):
            installer_type = bosh.InstallerArchive
        elif isinstance(firstItem,bosh.InstallerProject):
            installer_type = bosh.InstallerProject
        else:
            event.Veto()
            return
        for item in self.GetSelected():
            if not isinstance(self.data_store[item], installer_type):
                event.Veto()
                return
            #--Also, don't allow renaming the 'Last' marker
            elif item == u'==Last==':
                event.Veto()
                return
        editbox = self._gList.GetEditControl()
        editbox.Bind(wx.EVT_CHAR, self.OnEditLabelChar)
        #--Markers, change the selection to not include the '=='
        if installer_type is bosh.InstallerMarker:
            to = len(event.GetLabel()) - 2
            editbox.SetSelection(2,to)
        #--Archives, change the selection to not include the extension
        elif installer_type is bosh.InstallerArchive:
            super(InstallersList, self).OnBeginEditLabel(event)

    def OnEditLabelChar(self, event):
        """For pressing F2 on the edit box for renaming"""
        if event.GetKeyCode() == wx.WXK_F2:
            editbox = self._gList.GetEditControl()
            selection = editbox.GetSelection()
            text = editbox.GetValue()
            lenWithExt = len(text)
            if selection[0] != 0:
                selection = (0,lenWithExt)
            selectedText = GPath(text[selection[0]:selection[1]])
            textNextLower = selectedText.body
            if textNextLower == selectedText:
                lenNextLower = lenWithExt
            else:
                lenNextLower = len(textNextLower.s)

            selected = self.data_store[self.GetSelected()[0]]
            if isinstance(selected, bosh.InstallerArchive):
                selection = (0, lenNextLower)
            elif isinstance(selected, bosh.InstallerMarker):
                selection = (2, lenWithExt-2)
            else:
                selection = (0, lenWithExt)
            editbox.SetSelection(*selection)
        else:
            event.Skip()

    def OnLabelEdited(self, event):
        """Renamed some installers"""
        if event.IsEditCancelled(): return
        newName = event.GetLabel()
        selected = self.GetSelected()
        maPattern = self.data_store[selected[0]].match_valid_name(newName)
        if not maPattern:
            balt.showError(self, _(u'Bad extension or file root: ') + newName)
            event.Veto()
            return
        #--Rename each installer, keeping the old extension (for archives)
        with balt.BusyCursor():
            refreshes, ex = [(False, False, False)], None
            try:
                self.data_store.batchRename(selected, maPattern, refreshes)
            except (OSError, IOError) as ex:
                pass
            finally:
                refreshNeeded, modsRefresh, iniRefresh = [
                    any(grouped) for grouped in zip(*refreshes)]
            #--Refresh UI
            if refreshNeeded or ex: # refresh the UI in case of an exception
                if modsRefresh: BashFrame.modList.RefreshUI(refreshSaves=False)
                if iniRefresh and BashFrame.iniList is not None:
                    # It will be None if the INI Edits Tab was hidden at
                    # startup, and never initialized
                    BashFrame.iniList.RefreshUI()
                self.RefreshUI()
            event.Veto()

    #--Drag and Drop-----------------------------------------------------------
    def OnDropIndexes(self, indexes, newPos):
        # See if the column is reverse sorted first
        column = self.sort
        reverse = self.colReverse.get(column,False)
        if reverse:
            newPos = self._gList.GetItemCount() - newPos - 1 - (indexes[-1]-indexes[0])
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
                        (icon,0,wx.ALL,6),
                        (StaticText(dialog,message),1,wx.EXPAND|wx.LEFT,6),
                        ),1,wx.EXPAND|wx.ALL,6),
                    (gCheckBox,0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,6),
                    (hSizer(
                        spacer,
                        balt.Button(dialog,label=_(u'Move'),
                                    onButClick=lambda: dialog.EndModal(1)),
                        (balt.Button(dialog,label=_(u'Copy'),
                                     onButClick=lambda: dialog.EndModal(2)),
                         0,wx.LEFT,4),
                        (CancelButton(dialog),0,wx.LEFT,4),
                        ),0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,6),
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
                     or x.cext in bolt.readExts and x not in converters]
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
        try:
            index = self.GetIndex(GPath(u'===='))
        except KeyError: # u'====' not found in the internal dictionary
            self.data_store.addMarker(u'====')
            self.RefreshUI() # why refresh mods/saves/inis when adding a marker
            index = self.GetIndex(GPath(u'===='))
        if index != -1:
            self.ClearSelected()
            self.SelectItemAtIndex(index)
            self._gList.EditLabel(index)

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
                    apath = bass.dirs['installers'].join(name)
                    dest.update(installer.refreshBasic(apath,
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
class InstallersPanel(SashTankPanel):
    """Panel for InstallersTank."""
    espmMenu = Links()
    subsMenu = Links()
    keyPrefix = 'bash.installers'

    ##: belong to InstallersDetails
    @property
    def displayed_item(self): return self.detailsItem
    @property
    def file_infos(self): return self.listData
    @property
    def file_info(self): return self.file_infos.get(self.displayed_item, None)

    def __init__(self,parent):
        """Initialize."""
        BashFrame.iPanel = self
        self.listData = bosh.InstallersData()
        SashTankPanel.__init__(self, parent)
        left,right = self.left,self.right
        self.commentsSplitter = commentsSplitter = \
            wx.gizmos.ThinSplitterWindow(right, style=splitterStyle)
        subSplitter = wx.gizmos.ThinSplitterWindow(commentsSplitter, style=splitterStyle)
        checkListSplitter = wx.gizmos.ThinSplitterWindow(subSplitter, style=splitterStyle)
        #--Refreshing
        self._data_dir_scanned = False
        self.refreshing = False
        self.frameActivated = False
        #--Contents
        self.detailsPanel = self # YAK
        self.uiList = InstallersList(left, listData=self.listData,
                                     keyPrefix=self.keyPrefix, panel=self)
        #--Package
        self.gPackage = RoTextCtrl(right, noborder=True)
        self.gPackage.HideNativeCaret()
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
        subPackagesPanel = wx.Panel(checkListSplitter)
        subPackagesLabel = StaticText(subPackagesPanel, _(u'Sub-Packages'))
        self.gSubList = balt.listBox(subPackagesPanel, isExtended=True,
                                     kind='checklist')
        self.gSubList.Bind(wx.EVT_CHECKLISTBOX,self.OnCheckSubItem)
        self.gSubList.Bind(wx.EVT_RIGHT_UP,self.SubsSelectionMenu)
        #--Espms
        espmsPanel = wx.Panel(checkListSplitter)
        espmsLabel = StaticText(espmsPanel, _(u'Esp/m Filter'))
        self.espms = []
        self.gEspmList = balt.listBox(espmsPanel, isExtended=True,
                                      kind='checklist')
        self.gEspmList.Bind(wx.EVT_CHECKLISTBOX,self.OnCheckEspmItem)
        self.gEspmList.Bind(wx.EVT_RIGHT_UP,self.SelectionMenu)
        #--Comments
        commentsPanel = wx.Panel(commentsSplitter)
        commentsLabel = StaticText(commentsPanel, _(u'Comments'))
        self.gComments = TextCtrl(commentsPanel, multiline=True)
        #--Splitter settings
        checkListSplitter.SetMinimumPaneSize(50)
        checkListSplitter.SplitVertically(subPackagesPanel, espmsPanel)
        checkListSplitter.SetSashGravity(0.5)
        subSplitter.SetMinimumPaneSize(50)
        subSplitter.SplitHorizontally(self.gNotebook, checkListSplitter)
        subSplitter.SetSashGravity(0.5)
        commentsHeight = self.gPackage.GetSize()[1]
        commentsSplitter.SetMinimumPaneSize(commentsHeight)
        commentsSplitter.SplitHorizontally(subSplitter, commentsPanel)
        commentsSplitter.SetSashGravity(1.0)
        #--Layout
        subPackagesSizer = vSizer(subPackagesLabel, (self.gSubList,1,wx.EXPAND,2))
        subPackagesSizer.SetSizeHints(subPackagesPanel)
        subPackagesPanel.SetSizer(subPackagesSizer)
        espmsSizer = vSizer(espmsLabel, (self.gEspmList,1,wx.EXPAND,2))
        espmsSizer.SetSizeHints(espmsPanel)
        espmsPanel.SetSizer(espmsSizer)
        commentsSizer = vSizer(commentsLabel, (self.gComments,1,wx.EXPAND,2))
        commentsSizer.SetSizeHints(commentsPanel)
        commentsPanel.SetSizer(commentsSizer)
        rightSizer = vSizer(
            (self.gPackage,0,wx.GROW|wx.TOP|wx.LEFT,2),
            (commentsSplitter,1,wx.EXPAND,2))
        rightSizer.SetSizeHints(right)
        right.SetSizer(rightSizer)
        wx.LayoutAlgorithm().LayoutWindow(self, right)
        leftSizer = vSizer(
            (self.uiList,1,wx.EXPAND),
            )
        left.SetSizer(leftSizer)
        wx.LayoutAlgorithm().LayoutWindow(self,left)
        commentsSplitterSavedSashPos = settings.get('bash.installers.commentsSplitterSashPos', 0)
        # restore saved comments text box size
        if 0 == commentsSplitterSavedSashPos:
            commentsSplitter.SetSashPosition(-commentsHeight)
        else:
            commentsSplitter.SetSashPosition(commentsSplitterSavedSashPos)

    def RefreshUIColors(self):
        """Update any controls using custom colors."""
        self.uiList.RefreshUI()

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

    def ShowPanel(self, canCancel=True, fullRefresh=False, scan_data_dir=False):
        """Panel is shown. Update self.data."""
        self._first_run_set_enabled() # must run _before_ if below
        if not settings['bash.installers.enabled'] or self.refreshing: return
        refresh_ui = [False]
        try:
            self.refreshing = True
            self._refresh_installers_if_needed(refresh_ui, canCancel,
                                               fullRefresh, scan_data_dir)
            if refresh_ui[0]: self.uiList.RefreshUI()
            super(InstallersPanel, self).ShowPanel()
        finally:
            self.refreshing = False

    @balt.conversation
    @projects_walk_cache
    def _refresh_installers_if_needed(self, refreshui, canCancel, fullRefresh,
                                      scan_data_dir):
        data = self.listData
        if settings.get('bash.installers.updatedCRCs',True): #only checked here
            settings['bash.installers.updatedCRCs'] = False
            self._data_dir_scanned = False
        installers_paths = bass.dirs[
            'installers'].list() if self.frameActivated else ()
        if self.frameActivated and omods.extractOmodsNeeded(installers_paths):
            self.__extractOmods()
        do_refresh = scan_data_dir = scan_data_dir or not self._data_dir_scanned
        if not do_refresh and self.frameActivated:
            refresh_info = data.scan_installers_dir(installers_paths, fullRefresh)
            do_refresh = refresh_info.refresh_needed()
        else: refresh_info = None
        if do_refresh:
            with balt.Progress(_(u'Refreshing Installers...'),u'\n'+u' '*60, abort=canCancel) as progress:
                try:
                    what = 'DISC' if scan_data_dir else 'IC'
                    refreshui[0] |= data.irefresh(progress, what, fullRefresh, refresh_info)
                    self.frameActivated = False
                except CancelError:
                    pass # User canceled the refresh
                finally:
                    self._data_dir_scanned = True
        elif self.frameActivated and data.refreshConvertersNeeded():
            with balt.Progress(_(u'Refreshing Converters...'),u'\n'+u' '*60) as progress:
                try:
                    refreshui[0] |= data.irefresh(progress, 'C', fullRefresh)
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

    def OnShowInfoPage(self,event):
        """A specific info page has been selected."""
        if event.GetId() == self.gNotebook.GetId():
            index = event.GetSelection()
            gPage,initialized = self.infoPages[index]
            if self.detailsItem and not initialized:
                self.RefreshInfoPage(index, self.listData[self.detailsItem])
            event.Skip()

    def _sbCount(self):
        active = len(filter(lambda x: x.isActive, self.listData.itervalues()))
        return _(u'Packages:') + u' %d/%d' % (active, len(self.listData))

    def ClosePanel(self):
        if not hasattr(self, '_firstShow'): # save comments text box size
            sashPos = self.commentsSplitter.GetSashPosition()
            settings['bash.installers.commentsSplitterSashPos'] = sashPos
        super(InstallersPanel, self).ClosePanel()

    #--Details view (if it exists)
    def SaveDetails(self):
        """Saves details if they need saving."""
        settings['bash.installers.page'] = self.gNotebook.GetSelection()
        if not self.detailsItem: return
        if self.detailsItem not in self.listData: return
        if not self.gComments.IsModified(): return
        installer = self.listData[self.detailsItem]
        installer.comments = self.gComments.GetValue()
        self.listData.setChanged()

    def RefreshUIMods(self, mods_changed, inis_changed):
        """Refresh UI plus refresh mods state."""
        self.uiList.RefreshUI()
        if mods_changed:
            if bosh.modInfos.refresh():
                del bosh.modInfos.mtimesReset[:] ##: not sure why this here
            BashFrame.modList.RefreshUI(refreshSaves=True)
            Link.Frame.warn_corrupted(warn_saves=False)
            Link.Frame.warn_load_order()
        if BashFrame.iniList is not None:
            if inis_changed: ##: why this if below ??
                if bosh.iniInfos.refresh():
                    BashFrame.iniList.panel.RefreshPanel('ALL')
                else:
                    BashFrame.iniList.panel.RefreshPanel('TARGETS')
        bosh.BSAInfos.check_bsa_timestamps()

    def SetFile(self, fileName='SAME'):
        """Refreshes detail view associated with data from item."""
        if fileName == 'SAME': fileName = self.detailsItem
        if fileName not in self.listData: fileName = None
        self.SaveDetails() #--Save previous details
        self.detailsItem = fileName
        del self.espms[:]
        if fileName:
            installer = self.listData[fileName]
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
        else:
            self.gPackage.SetValue(u'')
            for index,(gPage,state) in enumerate(self.infoPages):
                self.infoPages[index][1] = True
                gPage.SetValue(u'')
            self.gSubList.Clear()
            self.gEspmList.Clear()
            self.gComments.SetValue(u'')
        self.gPackage.HideNativeCaret()

    def RefreshInfoPage(self,index,installer):
        """Refreshes notebook page."""
        gPage,initialized = self.infoPages[index]
        if initialized: return
        else: self.infoPages[index][1] = True
        pageName = gPage.GetName()
        sNone = _(u'[None]')
        def sortKey(file):
            dirFile = file.lower().rsplit(u'\\',1)
            if len(dirFile) == 1: dirFile.insert(0,u'')
            return dirFile
        def dumpFiles(installer,files,default=u'',header=u'',isPath=False):
            if files:
                buff = StringIO.StringIO()
                if isPath: files = [x.s for x in files]
                else: files = list(files)
                sortKeys = dict((x,sortKey(x)) for x in files)
                files.sort(key=lambda x: sortKeys[x])
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
            info += _(u'Type: ')
            if isinstance(installer,bosh.InstallerProject):
                info += _(u'Project')
            elif isinstance(installer,bosh.InstallerMarker):
                info += _(u'Marker')
            elif isinstance(installer,bosh.InstallerArchive):
                info += _(u'Archive')
            else:
                info += _(u'Unrecognized')
            info += u'\n'
            if isinstance(installer,bosh.InstallerMarker):
                info += _(u'Structure: N/A')+u'\n'
            elif installer.type == 1:
                info += _(u'Structure: Simple')+u'\n'
            elif installer.type == 2:
                if len(installer.subNames) == 2:
                    info += _(u'Structure: Complex/Simple')+u'\n'
                else:
                    info += _(u'Structure: Complex')+u'\n'
            elif installer.type < 0:
                info += _(u'Structure: Corrupt/Incomplete')+u'\n'
            else:
                info += _(u'Structure: Unrecognized')+u'\n'
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
            gPage.SetValue(info+dumpFiles(installer,installer.data_sizeCrc,sNone,
                u'== '+_(u'Configured Files'),isPath=True))
        elif pageName == 'gMatched':
            gPage.SetValue(dumpFiles(installer,set(installer.data_sizeCrc)
                - installer.missingFiles - installer.mismatchedFiles,isPath=True))
        elif pageName == 'gMissing':
            gPage.SetValue(dumpFiles(installer,installer.missingFiles,isPath=True))
        elif pageName == 'gMismatched':
            gPage.SetValue(dumpFiles(installer,installer.mismatchedFiles,sNone,isPath=True))
        elif pageName == 'gConflicts':
            gPage.SetValue(self.listData.getConflictReport(installer, 'OVER'))
        elif pageName == 'gUnderrides':
            gPage.SetValue(self.listData.getConflictReport(installer, 'UNDER'))
        elif pageName == 'gDirty':
            gPage.SetValue(dumpFiles(installer,installer.dirty_sizeCrc,isPath=True))
        elif pageName == 'gSkipped':
            gPage.SetValue(u'\n'.join((
                dumpFiles(installer,installer.skipExtFiles,sNone,u'== '+_(u'Skipped (Extension)')),
                dumpFiles(installer,installer.skipDirFiles,sNone,u'== '+_(u'Skipped (Dir)')),
                )) or sNone)

    #--Config
    def refreshCurrent(self,installer):
        """Refreshes current item while retaining scroll positions."""
        installer.refreshDataSizeCrc()
        installer.refreshStatus(self.listData)

        # Save scroll bar positions, because gList.RefreshUI will
        subScrollPos  = self.gSubList.GetScrollPos(wx.VERTICAL)
        espmScrollPos = self.gEspmList.GetScrollPos(wx.VERTICAL)
        subIndices = self.gSubList.GetSelections()

        self.uiList.RefreshUI(files=[self.detailsItem])
        for subIndex in subIndices:
            self.gSubList.SetSelection(subIndex)

        # Reset the scroll bars back to their original position
        subScroll = subScrollPos - self.gSubList.GetScrollPos(wx.VERTICAL)
        self.gSubList.ScrollLines(subScroll)

        espmScroll = espmScrollPos - self.gEspmList.GetScrollPos(wx.VERTICAL)
        self.gEspmList.ScrollLines(espmScroll)

    def OnCheckSubItem(self,event):
        """Handle check/uncheck of item."""
        installer = self.listData[self.detailsItem]
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
        installer = self.listData[self.detailsItem]
        espmNots = installer.espmNots
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
            self.refreshCurrent(installer)

#------------------------------------------------------------------------------
class ScreensList(balt.UIList):

    mainMenu = Links() #--Column menu
    itemMenu = Links() #--Single item menu
    _shellUI = True
    _editLabels = True
    _sort_keys = {'File'    : None,
                  'Modified': lambda self, a: self.data_store[a][1],
                 }
    #--Labels
    labels = OrderedDict([
        ('File',     lambda self, path: path.s),
        # ('Modified', lambda self, path: formatDate(self.data_store[path][1])), # unused
    ])

    #--Events ---------------------------------------------
    def OnDClick(self,event):
        """Double click a screenshot"""
        hitItem = self._getItemClicked(event)
        if not hitItem: return
        self.OpenSelected(selected=[hitItem])

    def OnLabelEdited(self, event):
        """Renamed a screenshot"""
        if event.IsEditCancelled(): return
        newName = event.GetLabel()
        selected = self.GetSelected()
        rePattern = re.compile(
            ur'^([^/\\:*?"<>|]+?)(\d*)((\.(jpg|jpeg|png|tif|bmp))+)$',
            re.I | re.U)
        maPattern = rePattern.match(newName)
        if not maPattern:
            balt.showError(self,_(u'Bad extension or file root: ')+newName)
            event.Veto()
            return
        root,numStr = maPattern.groups()[:2]
        #--Rename each screenshot, keeping the old extension
        num = int(numStr or  0)
        digits = len(str(num + len(selected)))
        if numStr: numStr.zfill(digits)
        screensDir = bosh.screensData.dir
        with balt.BusyCursor():
            newselected = []
            for screen in selected:
                newName = GPath(root + numStr + screen.ext)
                newPath = screensDir.join(newName)
                oldPath = screensDir.join(screen)
                if not newPath.exists():
                    try:
                        oldPath.moveTo(newPath)
                        newselected.append(newName)
                    except (OSError, IOError):
                        deprint('Renaming %s to %s failed'
                                % (oldPath, newPath), traceback=True)
                        ##: WindowsError:[Error 32]The process cannot access...
                        if newPath.exists() and oldPath.exists():
                            newPath.remove()
                        break
                num += 1
                numStr = unicode(num).zfill(digits)
            bosh.screensData.refresh()
            self.RefreshUI()
            #--Reselected the renamed items
            self.SelectItemsNoCallback(newselected)
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
            sel = map(lambda x: bosh.screensData.dir.join(x).s,
                      self.GetSelected())
            balt.copyListToClipboard(sel)
        super(ScreensList, self).OnKeyUp(event)

#------------------------------------------------------------------------------
class ScreensDetails(_DetailsMixin, NotebookPanel):

    def __init__(self, parent):
        super(ScreensDetails, self).__init__(parent)
        self.screenshot_control = balt.Picture(parent, 256, 192, background=colors['screens.bkgd.image'])
        self.displayed_screen = None # type: bolt.Path
        parent.SetSizer(hSizer((self.screenshot_control,1,wx.GROW)))

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
        filePath = bosh.screensData.dir.join(self.displayed_screen)
        bitmap = Image(filePath.s).GetBitmap() if filePath.exists() else None
        self.screenshot_control.SetBitmap(bitmap)

    def RefreshUIColors(self):
        self.screenshot_control.SetBackground(colors['screens.bkgd.image'])

    def ClosePanel(self): pass # for _DetailsViewMixin.detailsPanel.ClosePanel
    def ShowPanel(self): pass

class ScreensPanel(SashPanel):
    """Screenshots tab."""
    keyPrefix = 'bash.screens'
    _status_str = _(u'Screens:') + u' %d'

    def __init__(self,parent):
        """Initialize."""
        SashPanel.__init__(self, parent)
        left,right = self.left,self.right
        #--Contents
        self.listData = bosh.screensData = bosh.ScreensData()
        self.detailsPanel = ScreensDetails(right)
        self.uiList = ScreensList(
            left, listData=self.listData, keyPrefix=self.keyPrefix, panel=self)
        #--Layout
        left.SetSizer(hSizer((self.uiList,1,wx.GROW)))
        wx.LayoutAlgorithm().LayoutWindow(self,right)

    def RefreshUIColors(self):
        self.uiList.RefreshUI()
        super(ScreensPanel, self).RefreshUIColors()

    def ShowPanel(self):
        """Panel is shown. Update self.data."""
        if bosh.screensData.refresh():
            self.uiList.RefreshUI()
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
        ('File',     lambda self, path: path.s),
        ('Modified', lambda self, path: formatDate(self.data_store[path].mtime)),
        ('Size',     lambda self, path: round_size(self.data_store[path].size)),
    ])

#------------------------------------------------------------------------------
class BSADetails(_EditableMixinOnFileInfos, SashPanel):
    """BSAfile details panel."""

    @property
    def file_info(self): return self.BSAInfo
    @property
    def file_infos(self): return bosh.bsaInfos
    @property
    def allowDetailsEdit(self): return True

    def __init__(self, parent):
        SashPanel.__init__(self, parent, sashGravity=1.0, isVertical=False,
                           style=wx.TAB_TRAVERSAL)
        self.top, self.bottom = self.left, self.right
        bsaPanel = parent.GetParent().GetParent()
        self.bsaList = bsaPanel.uiList
        _EditableMixinOnFileInfos.__init__(self, self.bottom)
        #--Data
        self.BSAInfo = None
        #--File Name
        self.file = TextCtrl(self.top, onText=self.OnTextEdit,
                             onKillFocus=self.OnEditFile, maxChars=256)

        #--BSA Info
        self.gInfo = TextCtrl(self.bottom, multiline=True,
                              onText=self.OnInfoEdit, maxChars=2048)
        #--Layout
        nameSizer = vSizer(
            (hSizer((StaticText(self.top, _(u'File:')), 0, wx.TOP, 4)), 0,
            wx.EXPAND), (hSizer((self.file, 1, wx.EXPAND)), 0, wx.EXPAND), )
        nameSizer.SetSizeHints(self.top)
        self.top.SetSizer(nameSizer)
        infoSizer = vSizer(
        (hSizer((self.gInfo,1,wx.EXPAND)),0,wx.EXPAND),
        (hSizer(
                self.save,
                (self.cancel,0,wx.LEFT,4),
                ),0,wx.EXPAND|wx.TOP,4),)
        infoSizer.SetSizeHints(self.bottom)
        self.bottom.SetSizer(infoSizer)

    def _resetDetails(self):
        self.BSAInfo = None
        self.fileStr = u''

    def SetFile(self, fileName='SAME'):
        """Set file to be viewed."""
        fileName = super(BSADetails, self).SetFile(fileName)
        if fileName:
            BSAInfo = self.BSAInfo = bosh.bsaInfos[fileName]
            #--Remember values for edit checks
            self.fileStr = BSAInfo.name.s
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
        if self.BSAInfo and self.gInfo.IsModified():
            bosh.bsaInfos.table.setItem(self.BSAInfo.name,'info',self.gInfo.GetValue())
        event.Skip()

    def OnTextEdit(self,event):
        """Event: Editing file or save name text."""
        if not self.BSAInfo : return
        if not self.edited and self.fileStr != self.file.GetValue():
            self.SetEdited()
        event.Skip()

    def OnEditFile(self):
        """Event: Finished editing file name."""
        if not self.BSAInfo: return
        #--Changed?
        fileStr = self.file.GetValue()
        if fileStr == self.fileStr: return
        #--Extension Changed?
        if self.fileStr[-4:].lower() != u'.bsa':
            balt.showError(self,_(u'Incorrect file extension: ')+fileStr[-3:])
            self.file.SetValue(self.fileStr)
        #--Else file exists?
        elif self.BSAInfo.dir.join(fileStr).exists():
            balt.showError(self,_(u'File %s already exists.') % fileStr)
            self.file.SetValue(self.fileStr)
        #--Okay?
        else:
            self.fileStr = fileStr
            self.SetEdited()

    def DoSave(self):
        """Event: Clicked Save button."""
        BSAInfo = self.BSAInfo
        #--Change Tests
        changeName = (self.fileStr != BSAInfo.name)
        #--Backup
        BSAInfo.makeBackup()
        #--Change Name?
        if changeName:
            (oldName,newName) = (BSAInfo.name,GPath(self.fileStr.strip()))
            bosh.bsaInfos.rename(oldName,newName)
        #--Done
        try:
            bosh.bsaInfos.refreshFile(BSAInfo.name)
            self.SetFile(self.BSAInfo.name)
        except bosh.FileError:
            balt.showError(self,_(u'File corrupted on save!'))
            self.SetFile(None)
        self.bsaList.RefreshUI()

    def ClosePanel(self): pass # for _DetailsViewMixin.detailsPanel.ClosePanel
    def ShowPanel(self): pass

#------------------------------------------------------------------------------
class BSAPanel(SashPanel):
    """BSA info tab."""
    keyPrefix = 'bash.BSAs'
    _status_str = _(u'BSAs:') + u' %d'

    def __init__(self,parent):
        super(BSAPanel, self).__init__(parent)
        left,right = self.left, self.right
        self.listData = bosh.bsaInfos
        bosh.bsaInfos.refresh()
        self.uiList = BSAList(
            left, listData=self.listData, keyPrefix=self.keyPrefix, panel=self)
        self.detailsPanel = BSADetails(right)
        #--Layout
        right.SetSizer(hSizer((self.detailsPanel,1,wx.EXPAND)))
        left.SetSizer(hSizer((self.uiList,2,wx.EXPAND)))
        self.detailsPanel.Fit()

    def ClosePanel(self):
        super(BSAPanel, self).ClosePanel()
        # bosh.bsaInfos.profiles.save()

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
class PeoplePanel(SashTankPanel):
    """Panel for PeopleTank."""
    keyPrefix = 'bash.people'
    _status_str = _(u'People:') + u' %d'

    def __init__(self,parent):
        """Initialize."""
        self.listData = bosh.PeopleData()
        SashTankPanel.__init__(self, parent)
        left,right = self.left,self.right
        #--Contents
        self.detailsPanel = self # YAK
        self.uiList = PeopleList(left, listData=self.listData,
                                 keyPrefix=self.keyPrefix, panel=self)
        self.gName = RoTextCtrl(right, multiline=False)
        self.gText = TextCtrl(right, multiline=True)
        self.gKarma = spinCtrl(right,u'0',min=-5,max=5,onSpin=self.OnSpin)
        self.gKarma.SetSizeHints(40,-1)
        #--Layout
        right.SetSizer(vSizer(
            (hSizer(
                (self.gName,1,wx.GROW),
                (self.gKarma,0,wx.GROW),
                ),0,wx.GROW),
            (self.gText,1,wx.GROW|wx.TOP,4),
            ))
        left.SetSizer(vSizer((self.uiList,1,wx.GROW)))
        wx.LayoutAlgorithm().LayoutWindow(self, right)

    def ShowPanel(self):
        if self.listData.refresh(): self.uiList.RefreshUI()
        super(PeoplePanel, self).ShowPanel()

    def OnSpin(self):
        """Karma spin."""
        if not self.detailsItem: return
        karma = int(self.gKarma.GetValue())
        text = self.listData[self.detailsItem][2]
        self.listData[self.detailsItem] = (time.time(), karma, text)
        self.uiList.PopulateItem(item=self.detailsItem)
        self.listData.setChanged()

    #--Details view (if it exists)
    def SaveDetails(self):
        """Saves details if they need saving."""
        if not self.gText.IsModified(): return
        if not self.detailsItem or self.detailsItem not in self.listData: return
        mtime,karma,text = self.listData[self.detailsItem]
        self.listData[self.detailsItem] = (time.time(), karma, self.gText.GetValue().strip())
        self.uiList.PopulateItem(item=self.detailsItem)
        self.listData.setChanged()

    def SetFile(self, fileName='SAME'):
        """Refreshes detail view associated with data from item."""
        item = self.detailsItem if fileName == 'SAME' else fileName
        if item not in self.listData: item = None
        self.SaveDetails()
        if item is None:
            self.gKarma.SetValue(0)
            self.gName.SetValue(u'')
            self.gText.Clear()
        else:
            karma,text = self.listData[item][1:3]
            self.gName.SetValue(item)
            self.gKarma.SetValue(karma)
            self.gText.SetValue(text)
        self.detailsItem = item

    def RefreshUIColors(self): self.uiList.RefreshUI()

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
        # callback was bound before SetSelection() selection - this triggered
        # OnShowPage() - except if pageIndex was 0 (?!). Moved self.Bind() here
        # as OnShowPage() is explicitly called in RefreshData
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED,self.OnShowPage)
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
class BashStatusBar(wx.StatusBar):
    #--Class Data
    buttons = Links()
    SettingsMenu = Links()
    obseButton = None
    laaButton = None

    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent)
        self.SetFieldsCount(3)
        self.UpdateIconSizes()
        #--Bind events
        self.Bind(wx.EVT_SIZE, self.OnSize)
        #--Setup Drag-n-Drop reordering
        self.dragging = wx.NOT_FOUND
        self.dragStart = 0
        self.moved = False

    @property
    def iconsSize(self): return settings['bash.statusbar.iconSize'] + 8

    def _addButton(self,link):
        gButton = link.GetBitmapButton(self,style=wx.NO_BORDER)
        if gButton:
            self.buttons.append(gButton)
            # DnD events
            gButton.Bind(wx.EVT_LEFT_DOWN,self.OnDragStart)
            gButton.Bind(wx.EVT_LEFT_UP,self.OnDragEnd)
            gButton.Bind(wx.EVT_MOUSE_CAPTURE_LOST,self.OnDragEndForced)
            gButton.Bind(wx.EVT_MOTION,self.OnDrag)

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

    def _getButtonIndex(self, mouseEvent):
        id_ = mouseEvent.GetId()
        for i,button in enumerate(self.buttons):
            if button.GetId() == id_:
                x = mouseEvent.GetPosition()[0]
                delta = x / self.iconsSize
                if abs(x) % self.iconsSize > self.iconsSize:
                    delta += x / abs(x)
                i += delta
                if i < 0: i = 0
                elif i > len(self.buttons): i = len(self.buttons)
                return i
        return wx.NOT_FOUND

    def OnDragStart(self,event):
        self.dragging = self._getButtonIndex(event)
        if self.dragging != wx.NOT_FOUND:
            self.dragStart = event.GetPosition()[0]
            button = self.buttons[self.dragging]
            button.CaptureMouse()
        event.Skip()

    def OnDragEndForced(self,event):
        if self.dragging == wx.NOT_FOUND or not self.GetParent().IsActive():
            # The even for clicking the button sends a force capture loss
            # message.  Ignore lost capture messages if we're the active
            # window.  If we're not, that means something else forced the
            # loss of mouse capture.
            self.dragging = wx.NOT_FOUND
            self.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
        event.Skip()

    def OnDragEnd(self,event):
        if self.dragging != wx.NOT_FOUND:
            button = self.buttons[self.dragging]
            try:
                button.ReleaseMouse()
            except:
                pass
            # -*- Hacky code! -*-
            # Since we've got to CaptureMouse to do DnD properly,
            # The button will never get a EVT_BUTTON event if you
            # just click it.  Can't figure out a good way for the
            # two to play nicely, so we'll just simulate it for now
            released = self._getButtonIndex(event)
            if released != self.dragging: released = wx.NOT_FOUND
            self.dragging = wx.NOT_FOUND
            self.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
            if self.moved:
                self.moved = False
                return
            # -*- Rest of hacky code -*-
            if released != wx.NOT_FOUND:
                evt = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED,
                                      button.GetId())
                wx.PostEvent(button,evt)
        event.Skip()

    def OnDrag(self,event):
        if self.dragging != wx.NOT_FOUND:
            if abs(event.GetPosition()[0] - self.dragStart) > 4:
                self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
            over = self._getButtonIndex(event)
            if over >= len(self.buttons): over -= 1
            if over not in (wx.NOT_FOUND, self.dragging):
                self.moved = True
                button = self.buttons[self.dragging]
                # update settings
                uid = self.GetLink(button=button).uid
                overUid = self.GetLink(index=over).uid
                settings['bash.statusbar.order'].remove(uid)
                overIndex = settings['bash.statusbar.order'].index(overUid)
                settings['bash.statusbar.order'].insert(overIndex, uid)
                settings.setChanged('bash.statusbar.order')
                # update self.buttons
                self.buttons.remove(button)
                self.buttons.insert(over,button)
                self.dragging = over
                # Refresh button positions
                self.OnSize()
        event.Skip()

    def OnSize(self,event=None):
        rect = self.GetFieldRect(0)
        (xPos, yPos) = (rect.x + 4, rect.y + 2)
        for button in self.buttons:
            button.SetPosition((xPos, yPos))
            xPos += self.iconsSize
        if event: event.Skip()

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
    # Panels - use sparingly
    iPanel = None # BAIN panel

    @property
    def statusBar(self): return self.GetStatusBar()

    def __init__(self, parent=None, pos=balt.defPos, size=(400, 500)):
        #--Singleton
        balt.Link.Frame = self
        #--Window
        wx.Frame.__init__(self, parent, title=u'Wrye Bash', pos=pos, size=size)
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
        self.notebook = notebook = BashNotebook(self)
        #--Events
        self.Bind(wx.EVT_CLOSE, lambda __event: self.OnCloseWindow())
        self.BindRefresh(bind=True)
        #--Data
        self.inRefreshData = False #--Prevent recursion while refreshing.
        self.booting = True #--Prevent calling refresh on fileInfos twice when booting
        self.knownCorrupted = set()
        self.knownInvalidVerions = set()
        self.incompleteInstallError = False
        #--Layout
        sizer = vSizer((notebook,1,wx.GROW))
        self.SetSizer(sizer)

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

    def SetTitle(self,title=None):
        """Set title. Set to default if no title supplied."""
        if not title:
            ###Remove from Bash after CBash integrated
            if bush.game.altName and settings['bash.useAltName']:
                title = bush.game.altName + u' %s%s'
            else:
                title = u'Wrye Bash %s%s '+_(u'for')+u' '+bush.game.displayName
            title = title % (settings['bash.version'],
                _(u'(Standalone)') if settings['bash.standalone'] else u'')
            if CBash:
                title += u', CBash v%u.%u.%u: ' % (
                    CBash.GetVersionMajor(), CBash.GetVersionMinor(),
                    CBash.GetVersionRevision())
            else:
                title += u': '
            maProfile = re.match(ur'Saves\\(.+)\\$',bosh.saveInfos.localSave,re.U)
            if maProfile:
                title += maProfile.group(1)
            else:
                title += _(u'Default')
            if bosh.modInfos.voCurrent:
                title += u' ['+bosh.modInfos.voCurrent+u']'
        wx.Frame.SetTitle(self,title)

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
    def RefreshData(self, event=None):
        """Refreshes all data. Can be called manually, but is also triggered
        by window activation event.""" # hunt down - performance sink !
        #--Ignore deactivation events.
        if event and not event.GetActive() or self.inRefreshData: return
        #--UPDATES-----------------------------------------
        self.inRefreshData = True
        popMods = popSaves = popInis = None
        #--Config helpers
        bosh.configHelpers.refreshBashTags()
        #--Check plugins.txt and mods directory...
        if not self.booting and bosh.modInfos.refresh():
            popMods = 'ALL'
        #--Have any mtimes been reset?
        if bosh.modInfos.mtimesReset:
            if bosh.modInfos.mtimesReset[0] == 'PLUGINS':
                if not bass.inisettings['SkipResetTimeNotifications']:
                    balt.showWarning(self,_(u"An invalid plugin load order has been corrected."))
            else:
                if bosh.modInfos.mtimesReset[0] == 'FAILED':
                    balt.showWarning(self,_(u"It appears that the current user doesn't have permissions for some or all of the files in ")
                                            + bush.game.fsName+u'\\Data.\n' +
                                            _(u"Specifically had permission denied to change the time on:")
                                            + u'\n' + bosh.modInfos.mtimesReset[1].s)
                if not bass.inisettings['SkipResetTimeNotifications']:
                    message = [u'',_(u'Modified dates have been reset for some mod files')]
                    message.extend(sorted(bosh.modInfos.mtimesReset))
                    ListBoxes.Display(self, _(u'Modified Dates Reset'), _(
                        u'Modified dates have been reset for some mod files.'),
                        [message], liststyle='list', canCancel=False)
            del bosh.modInfos.mtimesReset[:]
            popMods = 'ALL'
        #--Check savegames directory...
        if not self.booting and bosh.saveInfos.refresh():
            popSaves = 'ALL'
        #--Check INI Tweaks...
        if not self.booting and bosh.iniInfos.refresh():
            popInis = 'ALL'
        #--Ensure BSA timestamps are good - Don't touch this for Skyrim though.
        bosh.BSAInfos.check_bsa_timestamps()
        #--Repopulate
        if popMods:
            BashFrame.modList.RefreshUI(refreshSaves=True) ##: True ?
        elif popSaves:
            BashFrame.saveListRefresh()
        if popInis and self.iniList:
            BashFrame.iniList.RefreshUI()
        #--Show current notebook panel
        if self.iPanel: self.iPanel.frameActivated = True
        self.notebook.currentPage.ShowPanel()
        #--WARNINGS----------------------------------------
        self.warn_load_order()
        self.warn_corrupted()
        self.warn_game_ini()
        self._obmmWarn()
        self._missingDocsDir()
        #--Done (end recursion blocker)
        self.inRefreshData = False

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
            m = [_(u'Corrupted Mods'),
                 _(u'The following mod files have corrupted headers: ')]
            m.extend(sorted(corruptMods))
            message.append(m)
            self.knownCorrupted |= corruptMods
        corruptSaves = set(bosh.saveInfos.corrupted.keys())
        if warn_saves and not corruptSaves <= self.knownCorrupted:
            m = [_(u'Corrupted Saves'),
                 _(u'The following save files have corrupted headers: ')]
            m.extend(sorted(corruptSaves))
            message.append(m)
            self.knownCorrupted |= corruptSaves
        invalidVersions = set([x.name for x in bosh.modInfos.values() if round(
            x.header.version, 6) not in bush.game.esp.validHeaderVersions])
        if warn_mods and not invalidVersions <= self.knownInvalidVerions:
            m = [_(u'Unrecognized Versions'),
                 _(u'The following mods have unrecognized TES4 header '
                   u'versions: ')]
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
              self, _(u'Warning: Corrupt/Unrecognized Files'),
              _(u'Some files have corrupted headers or TES4 header versions:'),
              message, liststyle='list', canCancel=False)

    _ini_missing = _(u"%(ini)s does not exist yet.  %(game)s will create this "
        u"file on first run.  INI tweaks will not be usable until then.")
    def warn_game_ini(self):
        #--Corrupt Oblivion.ini
        if self.oblivionIniCorrupted != bosh.oblivionIni.isCorrupted:
            self.oblivionIniCorrupted = bosh.oblivionIni.isCorrupted
            if self.oblivionIniCorrupted:
                msg = _(u'Your %s should begin with a section header '
                        u'(e.g. "[General]"), but does not. You should edit '
                        u'the file to correct this.') % bush.game.iniFiles[0]
                balt.showWarning(self, fill(msg))
        elif self.oblivionIniMissing:
            self.oblivionIniMissing = False
            balt.showWarning(self, self._ini_missing % {
                'ini': bosh.oblivionIni.path, 'game': bush.game.displayName})

    def _obmmWarn(self):
        #--OBMM Warning?
        if settings['bosh.modInfos.obmmWarn'] == 1:
            settings['bosh.modInfos.obmmWarn'] = 2
            message = _(u'Turn Lock Load Order Off?') + u'\n\n' + _(
                u'Lock Load Order is a feature which resets load order to a '
                u'previously memorized state.  While this feature is good '
                u'for maintaining your load order, it will also undo any '
                u'load order changes that you have made in OBMM.')
            lockTimes = not balt.askYes(self, message, _(u'Lock Load Order'))
            bosh.modInfos.lockLOSet(lockTimes)
            message = _(
                u"Lock Load Order is now %s.  To change it in the future, "
                u"right click on the main list header on the Mods tab and "
                u"select 'Lock Load Order'.")
            balt.showOk(self, message % ((_(u'off'), _(u'on'))[lockTimes],),
                        _(u'Lock Load Order'))

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
            self.SaveSettings()
        except: ##: this has swallowed exceptions since forever
                deprint(_(u'An error occurred while trying to save settings:'),
                        traceback=True)
        finally:
            self.Destroy()

    def SaveSettings(self):
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
        for index in range(self.notebook.GetPageCount()):
            try:
                self.notebook.GetPage(index).ClosePanel()
            except:
                deprint(_(u'An error occurred while trying to save settings:'),
                        traceback=True)
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
            goodRoots = set(path.root for path in fileInfos.keys())
            backupDir = fileInfos.bashDir.join(u'Backups')
            if not backupDir.isdir(): continue
            for name in backupDir.list():
                path = backupDir.join(name)
                if name.root not in goodRoots and path.isfile():
                    path.remove()

    @staticmethod
    def saveListRefresh():
        if BashFrame.saveList: BashFrame.saveList.RefreshUI()

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
class WryeBashSplashScreen(wx.SplashScreen):
    """This Creates the Splash Screen widget. (The first image you see when starting the Application.)"""
    def __init__(self, parent=None):
        splashScreenBitmap = wx.Image(name = bass.dirs['images'].join(u'wryesplash.png').s).ConvertToBitmap()
        splashStyle = wx.SPLASH_CENTRE_ON_SCREEN | wx.SPLASH_NO_TIMEOUT  #This centers the image on the screen
        # image will stay until clicked by user or is explicitly destroyed when the main window is ready
        # alternately wx.SPLASH_TIMEOUT and a duration can be used, but then you have to guess how long it should last
        splashDuration = 3500 # Duration in ms the splash screen will be visible (only used with the TIMEOUT option)
        wx.SplashScreen.__init__(self, splashScreenBitmap, splashStyle, splashDuration, parent)
        self.Bind(wx.EVT_CLOSE, self.OnExit)
        wx.Yield()

    def OnExit(self, event):
        self.Hide()
        # The program might/will freeze without this line.
        event.Skip() # Make sure the default handler runs too...

#------------------------------------------------------------------------------
class BashApp(wx.App):
    """Bash Application class."""
    def Init(self): # not OnInit(), we need to initialize _after_ the app has been instantiated
        """Initialize the application data, create and return the BashFrame."""
        global appRestart
        appRestart = False
        """wxWindows: Initialization handler."""
        #--OnStartup SplashScreen and/or Progress
        #   Progress gets hidden behind splash by default, since it's not very informative anyway
        splashScreen = None
        progress = wx.ProgressDialog(u'Wrye Bash',_(u'Initializing')+u' '*10,
             style=wx.PD_AUTO_HIDE|wx.PD_APP_MODAL|wx.PD_SMOOTH)
        # Is splash enabled in ini ?
        if bass.inisettings['EnableSplashScreen']:
            if bass.dirs['images'].join(u'wryesplash.png').exists():
                try:
                        splashScreen = WryeBashSplashScreen()
                        splashScreen.Show()
                except:
                        pass
        #--Constants
        self.InitResources()
        #--Init Data
        progress.Update(20,_(u'Initializing Data'))
        self.InitData(progress)
        progress.Update(70,_(u'Initializing Version'))
        self.InitVersion()
        #--MWFrame
        progress.Update(80,_(u'Initializing Windows'))
        frame = BashFrame( # Link.Frame global set here
             pos=settings['bash.framePos'],
             size=settings['bash.frameSize'])
        progress.Destroy()
        if splashScreen:
            splashScreen.Destroy()
            splashScreen.Hide() # wont be hidden if warnTooManyModsBsas warns..
        self.SetTopWindow(frame)
        frame.Show()
        @balt.conversation
        def maximize(): frame.Maximize(settings['bash.frameMax'])
        maximize()
        balt.ensureDisplayed(frame)
        frame.warnTooManyModsBsas()
        return frame

    def InitResources(self):
        """Init application resources."""
        Resources.bashBlue = Resources.bashBlue.GetIconBundle()
        Resources.bashRed = Resources.bashRed.GetIconBundle()
        Resources.bashDocBrowser = Resources.bashDocBrowser.GetIconBundle()
        Resources.bashMonkey = Resources.bashMonkey.GetIconBundle()
        Resources.fonts = balt.fonts()

    def InitData(self,progress):
        """Initialize all data. Called by Init()."""
        progress.Update(5,_(u'Initializing ModInfos'))
        bosh.gameInis = tuple(bosh.OblivionIni(x) for x in bush.game.iniFiles)
        bosh.oblivionIni = bosh.gameInis[0]
        bosh.modInfos = bosh.ModInfos()
        bosh.modInfos.refresh()
        progress.Update(30,_(u'Initializing SaveInfos'))
        bosh.saveInfos = bosh.SaveInfos()
        bosh.saveInfos.refresh()
        progress.Update(40,_(u'Initializing IniInfos'))
        bosh.iniInfos = bosh.INIInfos()
        bosh.iniInfos.refresh()
        # bsaInfos is used in BashFrame.warnTooManyModsBsas() and RefreshData()
        bosh.bsaInfos = bosh.BSAInfos()
        # screens, messages and Tank datas are refreshed() upon panel showing
        #--Patch check
        if bush.game.esp.canBash:
            if not bosh.modInfos.bashed_patches and bass.inisettings['EnsurePatchExists']:
                progress.Update(68,_(u'Generating Blank Bashed Patch'))
                bosh.modInfos.generateNextBashedPatch()

    def InitVersion(self):
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
        settings['bash.CBashEnabled'] = bool(CBash)

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
