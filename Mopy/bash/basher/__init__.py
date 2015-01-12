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
Relics of basher are some global variables - these must eventually disappear.
Currently there is an effort to unify balt.Tank and List.
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
from types import StringTypes, ClassType
from operator import attrgetter

#--wxPython
import wx
import wx.gizmos

#--Localization
#..Handled by bosh, so import that.
from .. import bush, bosh, bolt, bass
from ..bosh import formatInteger,formatDate
from ..bolt import BoltError, AbstractError, CancelError, SkipError, GPath, \
    SubProgress, deprint, Path
from ..cint import CBash

startupinfo = bolt.startupinfo

#--Balt
from .. import balt
from ..balt import fill, CheckLink, EnabledLink, SeparatorLink, \
    Link, ChoiceLink, copyListToClipboard, roTextCtrl, staticBitmap
from ..balt import button, checkBox, staticText, \
    spinCtrl, textCtrl
from ..balt import spacer, hSizer, vSizer
from ..balt import colors, images, Image
from ..balt import Links, ItemLink
from ..balt import wxListAligns, splitterStyle

# Constants -------------------------------------------------------------------
from .constants import colorInfo, tabInfo, settingDefaults, karmacons, \
    installercons, PNG, JPEG, ICO, BMP, TIF, ID_TAGS

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
isUAC = False      # True if the game is under UAC protection

# Singletons ------------------------------------------------------------------
statusBar = None
modList = None
iniList = None
modDetails = None
saveList = None
saveDetails = None
screensList = None
gInstallers = None
gMessageList = None
bashFrame = None
gPeople = None # New global - yak

# Settings --------------------------------------------------------------------
settings = None

# Links -----------------------------------------------------------------------
#------------------------------------------------------------------------------
def SetUAC(item):
    """Helper function for creating menu items or buttons that need UAC
       Note: for this to work correctly, it needs to be run BEFORE
       appending a menu item to a menu (and so, needs to be enabled/
       diasbled prior to that as well."""
    if isUAC:
        if isinstance(item,wx.MenuItem):
            pass
            #if item.IsEnabled():
            #    bitmap = images['uac.small'].GetBitmap()
            #    item.SetBitmaps(bitmap,bitmap)
        else:
            balt.setUAC(item,isUAC)

# Tank link mixins to access the Tank data - not final
class Installers_Link(ItemLink):
    """InstallersData mixin"""

    @property
    def idata(self): return gInstallers.data # InstallersData singleton

class People_Link(ItemLink):
    """PeopleData mixin"""

    @property
    def pdata(self): return gPeople.data # PeopleData singleton

# Exceptions ------------------------------------------------------------------
class BashError(BoltError): pass

# Images ----------------------------------------------------------------------
#------------------------------------------------------------------------------
class ColorChecks(balt.ImageList):
    """ColorChecks ImageList. Used by several List classes."""
    def __init__(self):
        balt.ImageList.__init__(self,16,16)
        for state in (u'on',u'off',u'inc',u'imp'):
            for status in (u'purple',u'blue',u'green',u'orange',u'yellow',u'red'):
                shortKey = status+u'.'+state
                imageKey = u'checkbox.'+shortKey
                file = GPath(bosh.dirs['images'].join(u'checkbox_'+status+u'_'+state+u'.png'))
                image = images[imageKey] = Image(file,PNG)
                self.Add(image,shortKey)

    def Get(self,status,on):
        self.GetImageList()
        if on == 3:
            if status <= -20: shortKey = 'purple.imp'
            elif status <= -10: shortKey = 'blue.imp'
            elif status <= 0: shortKey = 'green.imp'
            elif status <=10: shortKey = 'yellow.imp'
            elif status <=20: shortKey = 'orange.imp'
            else: shortKey = 'red.imp'
        elif on == 2:
            if status <= -20: shortKey = 'purple.inc'
            elif status <= -10: shortKey = 'blue.inc'
            elif status <= 0: shortKey = 'green.inc'
            elif status <=10: shortKey = 'yellow.inc'
            elif status <=20: shortKey = 'orange.inc'
            else: shortKey = 'red.inc'
        elif on:
            if status <= -20: shortKey = 'purple.on'
            elif status <= -10: shortKey = 'blue.on'
            elif status <= 0: shortKey = 'green.on'
            elif status <=10: shortKey = 'yellow.on'
            elif status <=20: shortKey = 'orange.on'
            else: shortKey = 'red.on'
        else:
            if status <= -20: shortKey = 'purple.off'
            elif status <= -10: shortKey = 'blue.off'
            elif status == 0: shortKey = 'green.off'
            elif status <=10: shortKey = 'yellow.off'
            elif status <=20: shortKey = 'orange.off'
            else: shortKey = 'red.off'
        return self.indices[shortKey]

colorChecks = ColorChecks()

class Resources:
    fonts = None
    #--Icon Bundles
    bashRed = None
    bashBlue = None
    bashDocBrowser = None
    bashMonkey = None

from .dialogs import ListBoxes # TODO(ut): cyclic import
# Windows ---------------------------------------------------------------------
#------------------------------------------------------------------------------
class NotebookPanel(wx.Panel):
    """Parent class for notebook panels."""

    def RefreshUIColors(self):
        """Called to signal that UI color settings have changed."""
        pass

    def SetStatusCount(self): # TODO(ut): eliminate overrides
        """Sets status bar count field."""
        statusBar.SetStatusText(u'',2)

    def OnShow(self):
        """To be called when particular panel is changed to and/or shown for first time.
        Default version does nothing, but derived versions might update data."""
        if bosh.inisettings['AutoSizeListColumns']:
            for i in xrange(self.list.list.GetColumnCount()):
                self.list.list.SetColumnWidth(i, -bosh.inisettings['AutoSizeListColumns'])
        self.SetStatusCount()

    def ClosePanel(self):
        """To be manually called when containing frame is closing. Use for
        saving data, scrollpos, etc."""
        if isinstance(self, ScreensPanel): return # ScreensPanel is not
        # backed up by a pickle file
        if hasattr(self, 'listData'):
            # the only SashPanels that do not override us and do not have this
            # attribute are the ModDetails and SaveDetails panels that use
            # a MasterList whose data is initially {}
            table = self.listData.table
            # items deleted outside Bash
            for deleted in set(table.keys()) - set(self.listData.keys()):
                del table[deleted]
            table.save()

#------------------------------------------------------------------------------
class SashPanel(NotebookPanel):
    """Subclass of Notebook Panel, designed for two pane panel."""
    def __init__(self,parent,sashPosKey=None,sashGravity=0.5,sashPos=0,isVertical=True,minimumSize=50,style=splitterStyle):
        """Initialize."""
        NotebookPanel.__init__(self, parent)
        splitter = wx.gizmos.ThinSplitterWindow(self, style=style)
        self.left = wx.Panel(splitter)
        self.right = wx.Panel(splitter)
        if isVertical:
            splitter.SplitVertically(self.left, self.right)
        else:
            splitter.SplitHorizontally(self.left, self.right)
        splitter.SetSashGravity(sashGravity)
        sashPos = settings.get(sashPosKey, 0) or sashPos or -1
        splitter.SetSashPosition(sashPos)
        if sashPosKey is not None:
            self.sashPosKey = sashPosKey
        # Don't allow unsplitting
        splitter.Bind(wx.EVT_SPLITTER_DCLICK, lambda self_, event: event.Veto())
        splitter.SetMinimumPaneSize(minimumSize)
        sizer = vSizer(
            (splitter,1,wx.EXPAND),
            )
        self.SetSizer(sizer)

    def ClosePanel(self):
        splitter = self.right.GetParent()
        if hasattr(self, 'sashPosKey'):
            settings[self.sashPosKey] = splitter.GetSashPosition()
        super(SashPanel, self).ClosePanel()

#------------------------------------------------------------------------------
class SashTankPanel(SashPanel):
    def __init__(self,data,parent):
        sashPos = data.getParam('sashPos',200)
        minimumSize = 80
        self.data = data
        self.detailsItem = None
        super(SashTankPanel,self).__init__(parent,sashPos=sashPos,minimumSize=minimumSize)

    def ClosePanel(self): # (ut) does not call super
        self.SaveDetails()
        splitter = self.right.GetParent()
        sashPos = splitter.GetSashPosition()
        self.data.setParam('sashPos',sashPos)
        self.data.save()

    def GetDetailsItem(self):
        return self.detailsItem

    def OnShow(self):
        if self.gList.data.refresh():
            self.gList.RefreshUI()
        super(SashTankPanel,self).OnShow()

#------------------------------------------------------------------------------
class List(balt.UIList):
    _sizeHints = (-1, 50) # overrides UIList
    icons = colorChecks

    def __init__(self, parent, listData=None, dndFiles=False, dndList=False,
                 dndColumns=(), **kwargs):
        #--ListCtrl
        #--MasterList: masterInfo = self.data[item], where item is id number
        # rest of List subclasses provide a non None listData
        self.data = {} if listData is None else listData # TODO(ut): to UIList
        balt.UIList.__init__(self, parent, dndFiles=dndFiles, dndList=dndList,
                             dndColumns=dndColumns, **kwargs)
        self.list = self.gList # self.list must go
        self.vScrollPos = 0
        #--Columns
        self.PopulateColumns()
        #--Items
        self.sortDirty = 0
        self.PopulateItems()
        #--Events: Items
        self.hitIcon = 0
        #--Events: Columns
        self.checkcol = []
        self.list.Bind(wx.EVT_UPDATE_UI, self.onUpdateUI)

    #--New way for self.cols, so PopulateColumns will work with
    #  the optional columns menu
    def _getCols(self):
        if hasattr(self,'colsKey'):
            return settings[self.colsKey]
        else:
            return self._cols
    def _setCols(self,value):
        if hasattr(self,'colsKey'):
            del self.colsKey
        self._cols = value
    cols = property(_getCols,_setCols)

    #--Items ----------------------------------------------
    #--Populate Columns
    def PopulateColumns(self):
        """Create/name columns in ListCtrl."""
        cols = self.cols
        self.numCols = len(cols)
        colDict = self.colDict = {}
        for colDex in xrange(self.numCols):
            colKey = cols[colDex]
            colDict[colKey] = colDex
            colName = self.colNames.get(colKey,colKey)
            wxListAlign = wxListAligns[self.colAligns.get(colKey,0)]
            if colDex >= self.list.GetColumnCount():
                # Make a new column
                self.list.InsertColumn(colDex,colName,wxListAlign)
                self.list.SetColumnWidth(colDex,self.colWidths.get(colKey,30))
            else:
                # Update an existing column
                column = self.list.GetColumn(colDex)
                if column.GetText() == colName:
                    # Don't change it, just make sure the width is correct
                    self.list.SetColumnWidth(colDex,self.colWidths.get(colKey,30))
                elif column.GetText() not in self.cols:
                    # Column that doesn't exist anymore
                    self.list.DeleteColumn(colDex)
                    colDex -= 1
                else:
                    # New column
                    self.list.InsertColumn(colDex,colName,wxListAlign)
                    self.list.SetColumnWidth(colDex,self.colWidths.get(colKey,30))
        while self.list.GetColumnCount() > self.numCols:
            self.list.DeleteColumn(self.numCols)
        self.list.SetColumnWidth(self.numCols, wx.LIST_AUTOSIZE_USEHEADER)

    def PopulateItem(self,itemDex,mode=0,selected=set()):
        """Populate ListCtrl for specified item. [ABSTRACT]"""
        raise AbstractError

    def GetItems(self):
        """Set and return self.items."""
        self.items = self.data.keys()
        return self.items

    def PopulateItems(self,col=None,reverse=-2,selected='SAME'):
        """Sort items and populate entire list."""
        self.mouseTexts.clear()
        #--Sort Dirty?
        if self.sortDirty:
            self.sortDirty = 0
            (col, reverse) = (None,-1)
        #--Items to select afterwards. (Defaults to current selection.)
        if selected == 'SAME': selected = set(self.GetSelected())
        #--Reget items
        self.GetItems()
        self.SortItems(col,reverse)
        #--Delete Current items
        listItemCount = self.list.GetItemCount()
        #--Populate items
        for itemDex in xrange(len(self.items)):
            mode = int(itemDex >= listItemCount)
            self.PopulateItem(itemDex,mode,selected)
        #--Delete items?
        while self.list.GetItemCount() > len(self.items):
            self.list.DeleteItem(self.list.GetItemCount()-1)

    def GetSelected(self):
        """Return list of items selected (hilighted) in the interface."""
        #--No items?
        if not 'items' in self.__dict__: return []
        selected = []
        itemDex = -1
        while True:
            itemDex = self.list.GetNextItem(itemDex,
                wx.LIST_NEXT_ALL,wx.LIST_STATE_SELECTED)
            if itemDex == -1 or itemDex >= len(self.items):
                break
            else:
                selected.append(self.items[itemDex])
        return selected

    def DeleteSelected(self,shellUI=False,dontRecycle=False):
        """Deletes selected items."""
        items = self.GetSelected()
        if not items: return
        if shellUI:
            try:
                self.data.delete(items,askOk=True,dontRecycle=dontRecycle)
            except balt.AccessDeniedError:
                pass
            dirJoin = self.data.dir.join
            for item in items:
                itemPath = dirJoin(item)
                if not itemPath.exists():
                    bosh.trackedInfos.track(itemPath)
        else:
            message = [u'',_(u'Uncheck items to skip deleting them if desired.')]
            message.extend(sorted(items))
            with ListBoxes(self, _(u'Delete Items'), _(
                    u'Delete these items?  This operation cannot be '
                    u'undone.'), [message]) as dialog:
                if dialog.ShowModal() == ListBoxes.ID_CANCEL: return # (ut) not needed to refresh I guess
                id = dialog.ids[message[0]]
                checks = dialog.FindWindowById(id)
                if checks:
                    dirJoin = self.data.dir.join
                    for i,mod in enumerate(items):
                        if checks.IsChecked(i):
                            try:
                                self.data.delete(mod)
                                # Temporarily Track this file for BAIN, so BAIN will
                                # update the status of its installers
                                bosh.trackedInfos.track(dirJoin(mod))
                            except bolt.BoltError as e:
                                balt.showError(self, _(u'%s') % e)
        bosh.modInfos.plugins.refresh(True)
        self.RefreshUI()

    def GetSortSettings(self,col,reverse):
        """Return parsed col, reverse arguments. Used by SortSettings.
        col: sort variable.
          Defaults to last sort. (self.sort)
        reverse: sort order
          1: Descending order
          0: Ascending order
         -1: Use current reverse settings for sort variable, unless
             last sort was on same sort variable -- in which case,
             reverse the sort order.
         -2: Use current reverse setting for sort variable.
        """
        #--Sort Column
        if not col:
            col = self.sort
        #--Reverse
        oldReverse = self.colReverse.get(col,0)
        if col == 'Load Order': #--Disallow reverse for load
            reverse = 0
        elif reverse == -1 and col == self.sort:
            reverse = not oldReverse
        elif reverse < 0:
            reverse = oldReverse
        #--Done
        self.sort = col
        self.colReverse[col] = reverse
        return col,reverse

    #--Event Handlers -------------------------------------
    def onUpdateUI(self,event):
        if self.checkcol:
            colDex = self.checkcol[0]
            colName = self.cols[colDex]
            width = self.list.GetColumnWidth(colDex)
            if width < 25:
                width = 25
                self.list.SetColumnWidth(colDex, 25)
                self.list.resizeLastColumn(0)
            self.colWidths[colName] = width
            self.checkcol = []
        event.Skip()

    #--Column Resize
    def OnColumnResize(self,event):
        """Due to a nastyness that ListCtrl.GetColumnWidth(col) returns
        the old size before this event completes just save what
        column is being edited and process after in OnUpdateUI()"""
        self.checkcol = [event.GetColumn()]
        settings.setChanged(self.colWidthsKey)
        event.Skip()

    #--Item Sort
    def OnColumnClick(self, event):
        """List OnColumnClick override - cf Tank."""
        self.PopulateItems(self.cols[event.GetColumn()],-1)

    def OnScroll(self,event):
        """Event: List was scrolled. Save so can be accessed later."""
        if event.GetOrientation() == wx.VERTICAL:
            self.vScrollPos = event.GetPosition()
        event.Skip()

#------------------------------------------------------------------------------
class MasterList(List):
    mainMenu = Links()
    itemMenu = Links()
    keyPrefix = 'bash.masters'

    def __init__(self, parent, fileInfo, setEditedFn, listData=None):
        #--Columns
        self.cols = settings['bash.masters.cols']
        #--Data/Items
        self.edited = False
        self.fileInfo = fileInfo
        self.prevId = -1
        self.items = [] #--Item numbers in display order.
        self.fileOrderItems = []
        self.loadOrderNames = []
        self.esmsFirst = settings['bash.masters.esmsFirst']
        self.selectedFirst = settings['bash.masters.selectedFirst']
        #--Parent init
        List.__init__(self, parent, listData, singleCell=True,
                      editLabels=True, sunkenBorder=False)
        self.gList.Bind(wx.EVT_LIST_END_LABEL_EDIT,self.OnLabelEdited)
        self._setEditedFn = setEditedFn

    colReverse = property(lambda self: {},
                          doc='Do not reverse columns in Master Lists')

    def OnItemSelected(self, event): event.Skip()

    #--NewItemNum
    def newId(self):
        self.prevId += 1
        return self.prevId

    #--Set ModInfo
    def SetFileInfo(self,fileInfo):
        self.ClearSelected()
        self.edited = False
        self.fileInfo = fileInfo
        self.prevId = -1
        self.data.clear()
        del self.items[:]
        del self.fileOrderItems[:]
        #--Null fileInfo?
        if not fileInfo:
            self.PopulateItems()
            return
        #--Fill data and populate
        for masterName in fileInfo.header.masters:
            item = self.newId()
            masterInfo = bosh.MasterInfo(masterName,0)
            self.data[item] = masterInfo
            self.items.append(item)
            self.fileOrderItems.append(item)
        self.ReList()
        self.PopulateItems()

    #--Get Master Status
    def GetMasterStatus(self,item):
        masterInfo = self.data[item]
        masterName = masterInfo.name
        status = masterInfo.getStatus()
        if status == 30:
            return status
        fileOrderIndex = self.fileOrderItems.index(item)
        loadOrderIndex = self.loadOrderNames.index(masterName)
        ordered = bosh.modInfos.ordered
        if fileOrderIndex != loadOrderIndex:
            return 20
        elif status > 0:
            return status
        elif ((fileOrderIndex < len(ordered)) and
            (ordered[fileOrderIndex] == masterName)):
            return -10
        else:
            return status

    #--Get Items
    def GetItems(self):
        return self.items

    #--Populate Item
    def PopulateItem(self,itemDex,mode=0,selected=set()):
        itemId = self.items[itemDex]
        masterInfo = self.data[itemId]
        masterName = masterInfo.name
        cols = self.cols
        for colDex in range(self.numCols):
            #--Value
            col = cols[colDex]
            if col == 'File':
                value = masterName.s
                if masterName == u'Oblivion.esm':
                    voCurrent = bosh.modInfos.voCurrent
                    if voCurrent: value += u' ['+voCurrent+u']'
            elif col == 'Num':
                value = u'%02X' % (self.fileOrderItems.index(itemId),)
            elif col == 'Current Order':
                #print itemId
                if masterName in bosh.modInfos.plugins.LoadOrder:
                    value = u'%02X' % (self.loadOrderNames.index(masterName),)
                else:
                    value = u''
            #--Insert/Set Value
            if mode and (colDex == 0):
                self.list.InsertStringItem(itemDex, value)
            else:
                self.list.SetStringItem(itemDex, colDex, value)
        #--Font color
        item = self.list.GetItem(itemDex)
        if masterInfo.isEsm():
            item.SetTextColour(colors['mods.text.esm'])
        else:
            item.SetTextColour(colors['default.text'])
        #--Text BG
        if bosh.modInfos.isBadFileName(masterName.s):
            if bosh.modInfos.isSelected(masterName):
                item.SetBackgroundColour(colors['mods.bkgd.doubleTime.load'])
            else:
                item.SetBackgroundColour(colors['mods.bkgd.doubleTime.exists'])
        elif masterInfo.hasActiveTimeConflict():
            item.SetBackgroundColour(colors['mods.bkgd.doubleTime.load'])
        elif masterInfo.isExOverLoaded():
            item.SetBackgroundColour(colors['mods.bkgd.exOverload'])
        elif masterInfo.hasTimeConflict():
            item.SetBackgroundColour(colors['mods.bkgd.doubleTime.exists'])
        elif masterInfo.isGhost:
            item.SetBackgroundColour(colors['mods.bkgd.ghosted'])
        else:
            item.SetBackgroundColour(colors['default.bkgd'])
        self.list.SetItem(item)
        #--Image
        status = self.GetMasterStatus(itemId)
        oninc = (masterName in bosh.modInfos.ordered) or (masterName in bosh.modInfos.merged and 2)
        self.list.SetItemImage(itemDex,self.icons.Get(status,oninc))
        #--Selection State
        self.SelectItemAtIndex(itemDex, masterName in selected)

    #--Sort Items
    def SortItems(self,col=None,reverse=-2):
        (col, reverse) = self.GetSortSettings(col,reverse)
        #--Sort
        data = self.data
        #--Start with sort by type
        self.items.sort()
        self.items.sort(key=lambda a: data[a].name.cext)
        if col == 'File':
            pass #--Done by default
        elif col == 'Rating':
            self.items.sort(key=lambda a: bosh.modInfos.table.getItem(a,'rating',u''))
        elif col == 'Group':
            self.items.sort(key=lambda a: bosh.modInfos.table.getItem(a,'group',u''))
        elif col == 'Installer':
            self.items.sort(key=lambda a: bosh.modInfos.table.getItem(a,'installer',u''))
        elif col == 'Modified':
            self.items.sort(key=lambda a: data[a].mtime)
        elif col in ['Save Order','Num']:
            self.items.sort()
        elif col in ['Load Order','Current Order']:
            loadOrderNames = self.loadOrderNames
            data = self.data
            self.items.sort(key=lambda a: loadOrderNames.index(data[a].name))
        elif col == 'Status':
            self.items.sort(lambda a,b: cmp(self.GetMasterStatus(a),self.GetMasterStatus(b)))
        elif col == 'Author':
            self.items.sort(lambda a,b: cmp(data[a].author.lower(),data[b].author.lower()))
        else:
            raise BashError(u'Unrecognized sort key: '+col)
        #--Ascending
        if reverse: self.items.reverse()
        #--ESMs First?
        settings['bash.masters.esmsFirst'] = self.esmsFirst
        if self.esmsFirst or col == 'Load Order':
            self.items.sort(key=lambda a: not data[a].isEsm())

    #--Relist
    def ReList(self):
        fileOrderNames = [self.data[item].name for item in self.fileOrderItems]
        self.loadOrderNames = bosh.modInfos.getOrdered(fileOrderNames,False)

    #--InitEdit
    def InitEdit(self):
        #--Pre-clean
        for itemId in self.items:
            masterInfo = self.data[itemId]
            #--Missing Master?
            if not masterInfo.modInfo:
                masterName = masterInfo.name
                newName = settings['bash.mods.renames'].get(masterName,None)
                #--Rename?
                if newName and newName in bosh.modInfos:
                    masterInfo.setName(newName)
        #--Done
        self.edited = True
        self.ReList()
        self.PopulateItems()
        self._setEditedFn()

    #--Item Sort
    def OnColumnClick(self, event):
        """MasterList: Don't do column head sort."""
        event.Skip()

    #--Column Menu
    def DoColumnMenu(self, event, column=None):
        if self.fileInfo: balt.UIList.DoColumnMenu(self, event, column)

    #--Item Menu
    def DoItemMenu(self,event):
        if not self.edited:
            self.OnLeftDown(event)
        else:
            balt.UIList.DoItemMenu(self, event)

    #--Event: Left Down
    def OnLeftDown(self,event):
        #--Not edited yet?
        if not self.edited and bush.game.ess.canEditMasters:
            message = (_(u"Edit/update the masters list? Note that the update process may automatically rename some files. Be sure to review the changes before saving."))
            if not balt.askContinue(self,message,'bash.masters.update',_(u'Update Masters')):
                return
            self.InitEdit()
        #--Pass event on (for label editing)
        else:
            event.Skip()

    #--Label Edited
    def OnLabelEdited(self,event):
        itemDex = event.m_itemIndex
        newName = GPath(event.GetText())
        #--No change?
        if newName in bosh.modInfos:
            masterInfo = self.data[self.items[itemDex]]
            oldName = masterInfo.name
            masterInfo.setName(newName)
            self.ReList()
            self.PopulateItem(itemDex)
            settings.getChanged('bash.mods.renames')[masterInfo.oldName] = newName
        elif newName == '':
            event.Veto()
        else:
            balt.showError(self,_(u'File %s does not exist.') % newName.s)
            event.Veto()

    #--GetMasters
    def GetNewMasters(self):
        """Returns new master list."""
        return [self.data[item].name for item in self.fileOrderItems]

#------------------------------------------------------------------------------
class INIList(List):
    mainMenu = Links()  #--Column menu
    itemMenu = Links()  #--Single item menu
    keyPrefix = 'bash.ini'

    def __init__(self, parent, listData):
        #--Columns
        self.colsKey = 'bash.ini.cols'
        self.sortValid = settings['bash.ini.sortValid']
        #--Parent init
        List.__init__(self, parent, listData, sunkenBorder=False)
        #--Events
        self.list.Bind(wx.EVT_KEY_UP, self.OnKeyUp)

    def CountTweakStatus(self):
        """Returns number of each type of tweak, in the
        following format:
        (applied,mismatched,not_applied,invalid)"""
        applied = 0
        mismatch = 0
        not_applied = 0
        invalid = 0
        for tweak in self.data.keys():
            status = self.data[tweak].status
            if status == -10: invalid += 1
            elif status == 0: not_applied += 1
            elif status == 10: mismatch += 1
            elif status == 20: applied += 1
        return applied,mismatch,not_applied,invalid

    def ListTweaks(self):
        """Returns text list of tweaks"""
        tweaklist = _(u'Active Ini Tweaks:') + u'\n'
        tweaklist += u'[spoiler][xml]\n'
        tweaks = self.data.keys()
        tweaks.sort()
        for tweak in tweaks:
            if not self.data[tweak].status == 20: continue
            tweaklist+= u'%s\n' % tweak
        tweaklist += u'[/xml][/spoiler]\n'
        return tweaklist

    def RefreshUI(self,files='ALL',detail='SAME'):
        """Refreshes UI for specified files."""
        #--Details
        if detail == 'SAME':
            selected = set(self.GetSelected())
        else:
            selected = {detail}
        #--Populate
        if files == 'VALID':
            files = [GPath(self.items[x]) for x in xrange(len(self.items)) if self.data[GPath(self.items[x])].status >= 0]
        if files == 'ALL':
            self.PopulateItems(selected=selected)
        elif isinstance(files,bolt.Path):
            self.PopulateItem(files,selected=selected)
        else: #--Iterable
            for file in files:
                self.PopulateItem(file,selected=selected)
        bashFrame.SetStatusCount()

    def PopulateItem(self,itemDex,mode=0,selected=set()):
        #--String name of item?
        if not isinstance(itemDex,int):
            itemDex = self.items.index(itemDex)
        fileName = GPath(self.items[itemDex])
        fileInfo = self.data[fileName]
        cols = self.cols
        for colDex in range(self.numCols):
            col = cols[colDex]
            if col == 'File':
                value = fileName.s
            elif col == 'Installer':
                value = self.data.table.getItem(fileName, 'installer', u'')
            if mode and colDex == 0:
                self.list.InsertStringItem(itemDex, value)
            else:
                self.list.SetStringItem(itemDex, colDex, value)
        status = fileInfo.getStatus()
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
        self.mouseTexts[itemDex] = mousetext
        self.list.SetItemImage(itemDex,self.icons.Get(icon,checkMark))
        #--Font/BG Color
        item = self.list.GetItem(itemDex)
        item.SetTextColour(colors['default.text'])
        if status < 0:
            item.SetBackgroundColour(colors['ini.bkgd.invalid'])
        else:
            item.SetBackgroundColour(colors['default.bkgd'])
        self.list.SetItem(item)
        self.SelectItemAtIndex(itemDex, fileName in selected)

    def SortItems(self,col=None,reverse=-2):
        (col, reverse) = self.GetSortSettings(col,reverse)
        settings['bash.ini.sort'] = col
        data = self.data
        #--Start with sort by name
        self.items.sort()
        self.items.sort(key = attrgetter('cext'))
        if col == 'File':
            pass #--Done by default
        elif col == 'Installer':
            self.items.sort(key=lambda a: bosh.iniInfos.table.getItem(a,'installer',u''))
        else:
            raise BashError(u'Unrecognized sort key: '+col)
        #--Ascending
        if reverse: self.items.reverse()
        #--Valid Tweaks first?
        self.sortValid = settings['bash.ini.sortValid']
        if self.sortValid:
            self.items.sort(key=lambda a: self.data[a].status < 0)

    def OnLeftDown(self,event):
        """Handle click on icon events"""
        event.Skip()
        (hitItem,hitFlag) = self.list.HitTest(event.GetPosition())
        if hitItem < 0 or hitFlag != wx.LIST_HITTEST_ONITEMICON: return
        tweak = bosh.iniInfos[self.items[hitItem]]
        if tweak.status == 20: return # already applied
        #-- If we're applying to Oblivion.ini, show the warning
        iniPanel = self.GetParent().GetParent().GetParent()
        choice = iniPanel.GetChoice().tail
        if choice in bush.game.iniFiles:
            message = (_(u"Apply an ini tweak to %s?") % choice
                       + u'\n\n' +
                       _(u"WARNING: Incorrect tweaks can result in CTDs and even damage to you computer!")
                       )
            if not balt.askContinue(self,message,'bash.iniTweaks.continue',_(u"INI Tweaks")):
                return
        dir = tweak.dir
        #--No point applying a tweak that's already applied
        file = dir.join(self.items[hitItem])
        iniList.data.ini.applyTweakFile(file)
        iniList.RefreshUI('VALID')
        iniPanel.iniContents.RefreshUI()
        iniPanel.tweakContents.RefreshUI(self.data[0])

    def OnKeyUp(self,event):
        """Char event: select all items"""
        ##Ctrl+A
        if event.CmdDown() and event.GetKeyCode() == ord('A'):
            self.SelectAll()
        elif event.GetKeyCode() in (wx.WXK_DELETE,wx.WXK_NUMPAD_DELETE):
            with balt.BusyCursor():
                self.DeleteSelected(True,event.ShiftDown())
        event.Skip()

    def OnItemSelected(self, event): event.Skip()

#------------------------------------------------------------------------------
class INITweakLineCtrl(wx.ListCtrl):
    def __init__(self, parent, iniContents, style=wx.LC_REPORT|wx.LC_SINGLE_SEL|wx.LC_NO_HEADER):
        wx.ListCtrl.__init__(self, parent, wx.ID_ANY, style=style)
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

    def RefreshUI(self, tweakPath):
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
        wx.ListCtrl.__init__(self, parent, wx.ID_ANY, style=style)
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

    def RefreshUI(self,resetScroll=False):
        num = self.GetItemCount()
        if resetScroll:
            self.EnsureVisible(0)
        ini = None
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
            if hasattr(bashFrame,'notebook'):
                page = bashFrame.notebook.GetPage(bashFrame.notebook.GetSelection())
                if page != self.GetParent().GetParent().GetParent():
                    warn = False
            if warn:
                balt.showWarning(self, _(u"%(ini)s does not exist yet.  %(game)s will create this file on first run.  INI tweaks will not be usable until then.")
                                 % {'ini':bosh.iniInfos.ini.path,
                                    'game':bush.game.displayName})
        self.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)

#------------------------------------------------------------------------------
class ModList(List):
    #--Class Data
    mainMenu = Links() #--Column menu
    itemMenu = Links() #--Single item menu
    keyPrefix = 'bash.mods'

    def __init__(self, parent, listData):
        #--Columns
        self.colsKey = 'bash.mods.cols'
        #--Data/Items
        self.details = None #--Set by panel
        self.esmsFirst = settings['bash.mods.esmsFirst']
        self.selectedFirst = settings['bash.mods.selectedFirst']
        #--Parent init
        # Image List: Column sorting order indicators # TODO(ut): to UIList
        # explorer style ^ == ascending
        checkboxesIL = self.icons.GetImageList()
        self.sm_up = checkboxesIL.Add(balt.SmallUpArrow.GetBitmap())
        self.sm_dn = checkboxesIL.Add(balt.SmallDnArrow.GetBitmap())
        List.__init__(self, parent, listData, dndList=True,
                      dndColumns=['Load Order'], sunkenBorder=False)
        #--Events
        self.list.Bind(wx.EVT_CHAR, self.OnChar)
        self.list.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        #--ScrollPos
        self.list.ScrollLines(settings.get('bash.mods.scrollPos',0))
        self.vScrollPos = self.list.GetScrollPos(wx.VERTICAL)

    #-- Drag and Drop-----------------------------------------------------
    def OnDropIndexes(self, indexes, newIndex):
        order = bosh.modInfos.plugins.LoadOrder
        # Calculating indexes through order.index() so corrupt mods (which don't show in the ModList) don't break Drag n Drop
        start = order.index(self.items[indexes[0]])
        stop = order.index(self.items[indexes[-1]]) + 1
        newPos = order.index(self.items[newIndex]) if (len(self.items) > newIndex) else order.index(self.items[-1])
        # Dummy checks: can't move the game's master file anywhere else but position 0
        if newPos <= 0: return
        master = bosh.modInfos.masterName
        if master in order[start:stop]: return
        # List of names to move removed and then reinserted at new position
        toMove = order[start:stop]
        del order[start:stop]
        order[newPos:newPos] = toMove
        #--Save and Refresh
        try:
            bosh.modInfos.plugins.saveLoadOrder()
        except bolt.BoltError as e:
            balt.showError(self, _(u'%s') % e)
        bosh.modInfos.plugins.refresh(True)
        bosh.modInfos.refreshInfoLists()
        self.RefreshUI()

    def RefreshUI(self,files='ALL',detail='SAME',refreshSaves=True):
        """Refreshes UI for specified file. Also calls saveList.RefreshUI()!"""
        #--Details
        if detail == 'SAME':
            selected = set(self.GetSelected())
        else:
            selected = {detail}
        #--Populate
        if files == 'ALL':
            self.PopulateItems(selected=selected)
        elif isinstance(files,bolt.Path):
            self.PopulateItem(files,selected=selected)
        else: #--Iterable
            for file in files:
                if file in bosh.modInfos:
                    self.PopulateItem(file,selected=selected)
        modDetails.SetFile(detail)
        bashFrame.SetStatusCount()
        #--Saves
        if refreshSaves and saveList:
            saveList.RefreshUI()

    #--Populate Item
    def PopulateItem(self,itemDex,mode=0,selected=set()):
        #--String name of item?
        if not isinstance(itemDex,int):
            itemDex = self.items.index(itemDex)
        fileName = GPath(self.items[itemDex])
        fileInfo = self.data[fileName]
        fileBashTags = bosh.modInfos[fileName].getBashTags()
        cols = self.cols
        for colDex in range(self.numCols):
            col = cols[colDex]
            #--Get Value
            if col == 'File':
                value = fileName.s
                if fileName == u'Oblivion.esm' and bosh.modInfos.voCurrent:
                    value += u' ['+bosh.modInfos.voCurrent+u']'
            elif col == 'Rating':
                value = bosh.modInfos.table.getItem(fileName,'rating',u'')
            elif col == 'Group':
                value = bosh.modInfos.table.getItem(fileName,'group',u'')
            elif col == 'Installer':
                value = bosh.modInfos.table.getItem(fileName,'installer',u'')
            elif col == 'Modified':
                value = formatDate(fileInfo.getPath().mtime)
            elif col == 'Size':
                value = formatInteger(max(fileInfo.size,1024)/1024 if fileInfo.size else 0)+u' KB'
            elif col == 'Author' and fileInfo.header:
                value = fileInfo.header.author
            elif col == 'Load Order':
                ordered = bosh.modInfos.ordered
                if fileName in ordered:
                    value = u'%02X' % ordered.index(fileName)
                else:
                    value = u''
            elif col == 'CRC':
                value = u'%08X' % fileInfo.cachedCrc()
            elif col == 'Mod Status':
                value = fileInfo.txt_status()
            else:
                value = u'-'
            #--Insert/SetString
            if mode and (colDex == 0):
                self.list.InsertStringItem(itemDex, value)
            else:
                self.list.SetStringItem(itemDex, colDex, value)
        #--Default message
        mouseText = u''
        #--Image
        status = fileInfo.getStatus()
        checkMark = (
            1 if fileName in bosh.modInfos.ordered
            else 2 if fileName in bosh.modInfos.merged
            else 3 if fileName in bosh.modInfos.imported
            else 0)
        self.list.SetItemImage(itemDex,self.icons.Get(status,checkMark))
        #--Font color
        item = self.list.GetItem(itemDex)
        mouseText = u''
        if fileName in bosh.modInfos.bad_names:
            mouseText += _(u'Plugin name incompatible, cannot be activated.  ')
        if fileName in bosh.modInfos.missing_strings:
            mouseText += _(u'Plugin is missing String Localization files.  ')
        if fileInfo.isEsm():
            item.SetTextColour(colors['mods.text.esm'])
            mouseText += _(u"Master file. ")
        elif fileName in bosh.modInfos.mergeable:
            if u'NoMerge' in fileBashTags:
                item.SetTextColour(colors['mods.text.noMerge'])
                mouseText += _(u"Technically mergeable but has NoMerge tag.  ")
            else:
                item.SetTextColour(colors['mods.text.mergeable'])
                if checkMark == 2:
                    mouseText += _(u"Merged into Bashed Patch.  ")
                else:
                    mouseText += _(u"Can be merged into Bashed Patch.  ")
        else:
            item.SetTextColour(colors['default.text'])
        #--Image messages
        if status == 30:     mouseText += _(u"One or more masters are missing.  ")
        elif status == 20:   mouseText += _(u"Masters have been re-ordered.  ")
        if checkMark == 1:   mouseText += _(u"Active in load list.  ")
        elif checkMark == 3: mouseText += _(u"Imported into Bashed Patch.  ")

        #should mod be deactivated
        if u'Deactivate' in fileBashTags:
            item.SetFont(Resources.fonts[2])
        else:
            item.SetFont(Resources.fonts[0])
        #--Text BG
        if fileName in bosh.modInfos.bad_names:
            item.SetBackgroundColour(colors['mods.bkgd.doubleTime.exists'])
        elif fileName in bosh.modInfos.missing_strings:
            if fileName in bosh.modInfos.ordered:
                item.SetBackgroundColour(colors['mods.bkgd.doubleTime.load'])
            else:
                item.SetBackgroundColour(colors['mods.bkgd.doubleTime.exists'])
        elif fileInfo.hasBadMasterNames():
            if bosh.modInfos.isSelected(fileName):
                item.SetBackgroundColour(colors['mods.bkgd.doubleTime.load'])
            else:
                item.SetBackgroundColour(colors['mods.bkgd.doubleTime.exists'])
            mouseText += _(u"WARNING: Has master names that will not load.  ")
        elif fileInfo.hasActiveTimeConflict():
            item.SetBackgroundColour(colors['mods.bkgd.doubleTime.load'])
            mouseText += _(u"WARNING: Has same load order as another mod.  ")
        elif u'Deactivate' in fileBashTags and checkMark == 1:
            item.SetBackgroundColour(colors['mods.bkgd.deactivate'])
            mouseText += _(u"Mod should be imported and deactivated.  ")
        elif fileInfo.isExOverLoaded():
            item.SetBackgroundColour(colors['mods.bkgd.exOverload'])
            mouseText += _(u"WARNING: Exclusion group is overloaded.  ")
        elif fileInfo.hasTimeConflict():
            item.SetBackgroundColour(colors['mods.bkgd.doubleTime.exists'])
            mouseText += _(u"Has same time as another (unloaded) mod.  ")
        elif fileName.s[0] in u'.+=':
            item.SetBackgroundColour(colors['mods.bkgd.groupHeader'])
            mouseText += _(u"Group header.  ")
        elif fileInfo.isGhost:
            item.SetBackgroundColour(colors['mods.bkgd.ghosted'])
            mouseText += _(u"File is ghosted.  ")
        else:
            item.SetBackgroundColour(colors['default.bkgd'])
        if settings['bash.mods.scanDirty']:
            message = fileInfo.getDirtyMessage()
            mouseText += message[1]
            if message[0]:
                font = item.GetFont()
                font.SetUnderlined(True)
                item.SetFont(font)
        self.list.SetItem(item)
        self.mouseTexts[itemDex] = mouseText
        #--Selection State
        self.SelectItemAtIndex(itemDex, fileName in selected)
        #--Status bar text

    #--Sort Items
    def SortItems(self,col=None,reverse=-2):
        (col, reverse) = self.GetSortSettings(col,reverse)
        oldcol = settings['bash.mods.sort']
        settings['bash.mods.sort'] = col
        selected = bosh.modInfos.ordered
        data = self.data
        #--Start with sort by name
        self.items.sort()
        self.items.sort(key = attrgetter('cext'))
        if col == 'File':
            pass #--Done by default
        elif col == 'Author':
            self.items.sort(key=lambda a: data[a].header.author.lower())
        elif col == 'Rating':
            self.items.sort(key=lambda a: bosh.modInfos.table.getItem(a,'rating',u''))
        elif col == 'Group':
            self.items.sort(key=lambda a: bosh.modInfos.table.getItem(a,'group',u''))
        elif col == 'Installer':
            self.items.sort(key=lambda a: bosh.modInfos.table.getItem(a,'installer',u''))
        elif col == 'Load Order':
            self.items = bosh.modInfos.getOrdered(self.items,False)
        elif col == 'Modified':
            self.items.sort(key=lambda a: data[a].getPath().mtime)
        elif col == 'Size':
            self.items.sort(key=lambda a: data[a].size)
        elif col == 'Status':
            self.items.sort(key=lambda a: data[a].getStatus())
        elif col == 'Mod Status':
            self.items.sort(key=lambda a: data[a].txt_status())
        elif col == 'CRC':
            self.items.sort(key=lambda a: data[a].cachedCrc())
        else:
            raise BashError(u'Unrecognized sort key: '+col)
        #--Ascending
        if reverse: self.items.reverse()
        #--Selected First?
        settings['bash.mods.selectedFirst'] = self.selectedFirst
        if self.selectedFirst:
            active = set(selected) | bosh.modInfos.imported | bosh.modInfos.merged
            self.items.sort(key=lambda x: x not in active)
        #set column sort image
        try:
            try: self.list.ClearColumnImage(self.colDict[oldcol])
            except: pass # if old column no longer is active this will fail but not a problem since it doesn't exist anyways.
            if reverse: self.list.SetColumnImage(self.colDict[col], self.sm_dn)
            else: self.list.SetColumnImage(self.colDict[col], self.sm_up)
        except: pass

    #--Events ---------------------------------------------
    def OnDClick(self,event):
        """Handle doubleclicking a mod in the Mods List."""
        (hitItem,hitFlag) = self.list.HitTest(event.GetPosition())
        if hitItem < 0: return
        fileInfo = self.data[self.items[hitItem]]
        if not Link.Frame.docBrowser:
            from .frames import DocBrowser
            DocBrowser().Show()
            settings['bash.modDocs.show'] = True
        #balt.ensureDisplayed(docBrowser)
        Link.Frame.docBrowser.SetMod(fileInfo.name)
        Link.Frame.docBrowser.Raise()

    def OnChar(self,event):
        """Char event: Delete, Reorder, Check/Uncheck."""
        ##Delete
        if event.GetKeyCode() in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self.DeleteSelected(False,event.ShiftDown())
        ##Ctrl+Up and Ctrl+Down
        elif ((event.CmdDown() and event.GetKeyCode() in (wx.WXK_UP,wx.WXK_DOWN,wx.WXK_NUMPAD_UP,wx.WXK_NUMPAD_DOWN)) and
            (settings['bash.mods.sort'] == 'Load Order')
            ):
                orderKey = lambda x: self.items.index(x)
                moveMod = 1 if event.GetKeyCode() in (wx.WXK_DOWN,wx.WXK_NUMPAD_DOWN) else -1
                isReversed = (moveMod != -1)
                for thisFile in sorted(self.GetSelected(),key=orderKey,reverse=isReversed):
                    swapItem = self.items.index(thisFile) + moveMod
                    if swapItem < 0 or len(self.items) - 1 < swapItem: break
                    swapFile = self.items[swapItem]
                    try:
                        bosh.modInfos.swapOrder(thisFile,swapFile)
                    except bolt.BoltError as e:
                        balt.showError(self, _(u'%s') % e)
                    bosh.modInfos.refreshInfoLists()
                    self.RefreshUI(refreshSaves=False)
                self.RefreshUI([],refreshSaves=True)
        event.Skip()

    def OnKeyUp(self,event):
        """Char event: Activate selected items, select all items"""
        ##Space
        code = event.GetKeyCode()
        if code == wx.WXK_SPACE:
            selected = self.GetSelected()
            toActivate = [item for item in selected if not self.data.isSelected(GPath(item))]
            if len(toActivate) == 0 or len(toActivate) == len(selected):
                #--Check/Uncheck all
                self._checkUncheckMod(*selected)
            else:
                #--Check all that aren't
                self._checkUncheckMod(*toActivate)
        ##Ctrl+A
        elif event.CmdDown() and code == ord('A'):
            self.SelectAll()
        # Ctrl+C: Copy file(s) to clipboard
        elif event.CmdDown() and code == ord('C'):
            sel = map(lambda mod: self.data[mod].getPath().s,
                      self.GetSelected())
            copyListToClipboard(sel)
        event.Skip()

    def OnLeftDown(self,event):
        """Left Down: Check/uncheck mods."""
        (hitItem,hitFlag) = self.list.HitTest((event.GetX(),event.GetY()))
        if hitFlag == wx.LIST_HITTEST_ONITEMICON:
            self.list.SetDnD(False)
            self._checkUncheckMod(self.items[hitItem])
        else:
            self.list.SetDnD(True)
        #--Pass Event onward
        event.Skip()

    def OnItemSelected(self,event):
        """Item Selected: Set mod details."""
        modName = self.items[event.m_itemIndex]
        self.details.SetFile(modName)
        if Link.Frame.docBrowser:
            Link.Frame.docBrowser.SetMod(modName)

    #--Helpers ---------------------------------------------
    def _checkUncheckMod(self, *mods):
        removed = []
        notDeactivatable = [ Path(x) for x in bush.game.nonDeactivatableFiles ]
        for item in mods:
            if item in removed or item in notDeactivatable: continue
            oldFiles = bosh.modInfos.ordered[:]
            fileName = GPath(item)
            #--Unselect?
            if self.data.isSelected(fileName):
                try:
                    self.data.unselect(fileName)
                    changed = bolt.listSubtract(oldFiles,bosh.modInfos.ordered)
                    if len(changed) > (fileName in changed):
                        changed.remove(fileName)
                        changed = [x.s for x in changed]
                        removed += changed
                        balt.showList(self,u'${count} '+_(u'Children deactivated:'),changed,10,fileName.s)
                except bosh.liblo.LibloError as e:
                    if e.msg == 'LIBLO_ERROR_INVALID_ARGS:Plugins may not be sorted before the game\'s master file.':
                        msg = _(u'Plugins may not be sorted before the game\'s master file.')
                    else:
                        msg = e.msg
                    balt.showError(self,_(u'%s') % msg)
            #--Select?
            else:
                ## For now, allow selecting unicode named files, for testing
                ## I'll leave the warning in place, but maybe we can get the
                ## game to load these files.s
                #if fileName in self.data.bad_names: return
                try:
                    self.data.select(fileName)
                    changed = bolt.listSubtract(bosh.modInfos.ordered,oldFiles)
                    if len(changed) > ((fileName in changed) + (GPath(u'Oblivion.esm') in changed)):
                        changed.remove(fileName)
                        changed = [x.s for x in changed]
                        balt.showList(self,u'${count} '+_(u'Masters activated:'),changed,10,fileName.s)
                except bosh.PluginsFullError:
                    balt.showError(self,_(u'Unable to add mod %s because load list is full.')
                        % fileName.s)
                    return
        #--Refresh
        bosh.modInfos.refresh()
        self.RefreshUI()
        #--Mark sort as dirty
        if self.selectedFirst:
            self.sortDirty = 1
            self.colReverse[self.sort] = not self.colReverse.get(self.sort,0)

#------------------------------------------------------------------------------
class ModDetails(SashPanel):
    """Details panel for mod tab."""

    def __init__(self,parent):
        SashPanel.__init__(self, parent,'bash.mods.details.SashPos',1.0,
                           isVertical=False,minimumSize=150,style=wx.SW_BORDER|splitterStyle)
        top,bottom = self.left, self.right
        #--Singleton
        global modDetails
        modDetails = self
        #--Data
        self.modInfo = None
        self.edited = False
        textWidth = 200
        if True: #setup
            #--Version
            self.version = staticText(top,u'v0.00')
            #--File Name
            self.file = textCtrl(top, onKillFocus=self.OnEditFile,
                                 onText=self.OnTextEdit)# ,size=(textWidth,-1))
            self.file.SetMaxLength(200)
            #--Author
            self.author = textCtrl(top, onKillFocus=self.OnEditAuthor,
                                 onText=self.OnTextEdit)# ,size=(textWidth,-1))
            self.author.SetMaxLength(512)
            #--Modified
            self.modified = textCtrl(top,size=(textWidth, -1),
                                     onKillFocus=self.OnEditModified,
                                     onText=self.OnTextEdit)
            self.modified.SetMaxLength(32)
            #--Description
            self.description = textCtrl(top, size=(textWidth, 150),
                                        multiline=True,
                                        onKillFocus=self.OnEditDescription,
                                        onText=self.OnTextEdit)
            self.description.SetMaxLength(512)
            subSplitter = self.subSplitter = wx.gizmos.ThinSplitterWindow(bottom,style=splitterStyle)
            masterPanel = wx.Panel(subSplitter)
            tagPanel = wx.Panel(subSplitter)
            #--Masters
            self.masters = MasterList(masterPanel,None,self.SetEdited)
            #--Save/Cancel
            self.save = button(masterPanel,label=_(u'Save'),id=wx.ID_SAVE,onClick=self.DoSave,)
            self.cancel = button(masterPanel,label=_(u'Cancel'),id=wx.ID_CANCEL,onClick=self.DoCancel,)
            self.save.Disable()
            self.cancel.Disable()
            #--Bash tags
            self.allTags = bosh.allTags
            self.gTags = roTextCtrl(tagPanel, size=(textWidth, 100))
        #--Layout
        detailsSizer = vSizer(
            (hSizer(
                (staticText(top,_(u"File:")),0,wx.TOP,4),
                spacer,
                (self.version,0,wx.TOP|wx.RIGHT,4)
                ),0,wx.EXPAND),
            (hSizer((self.file,1,wx.EXPAND)),0,wx.EXPAND),
            (hSizer((staticText(top,_(u"Author:")),0,wx.TOP,4)),0,wx.EXPAND),
            (hSizer((self.author,1,wx.EXPAND)),0,wx.EXPAND),
            (hSizer((staticText(top,_(u"Modified:")),0,wx.TOP,4)),0,wx.EXPAND),
            (hSizer((self.modified,1,wx.EXPAND)),0,wx.EXPAND),
            (hSizer((staticText(top,_(u"Description:")),0,wx.TOP,4)),0,wx.EXPAND),
            (hSizer((self.description,1,wx.EXPAND)),1,wx.EXPAND))
        detailsSizer.SetSizeHints(top)
        top.SetSizer(detailsSizer)
        subSplitter.SetMinimumPaneSize(100)
        subSplitter.SplitHorizontally(masterPanel,tagPanel)
        subSplitter.SetSashGravity(0.5)
        subSplitter.SetSashPosition(settings.get('bash.mods.details.subSplitterSashPos', 0))
        mastersSizer = vSizer(
            (hSizer((staticText(masterPanel,_(u"Masters:")),0,wx.TOP,4)),0,wx.EXPAND),
            (hSizer((self.masters,1,wx.EXPAND)),1,wx.EXPAND),
            (hSizer(
                self.save,
                (self.cancel,0,wx.LEFT,4)
                ),0,wx.EXPAND|wx.TOP,4),)
        tagsSizer = vSizer(
            (staticText(tagPanel,_(u"Bash Tags:")),0,wx.TOP,4),
            (hSizer((self.gTags,1,wx.EXPAND)),1,wx.EXPAND))
        mastersSizer.SetSizeHints(masterPanel)
        masterPanel.SetSizer(mastersSizer)
        tagsSizer.SetSizeHints(masterPanel)
        tagPanel.SetSizer(tagsSizer)
        bottom.SetSizer(vSizer((subSplitter,1,wx.EXPAND)))
        #--Events
        self.gTags.Bind(wx.EVT_CONTEXT_MENU,self.ShowBashTagsMenu)

    def SetFile(self,fileName='SAME'):
        #--Reset?
        if fileName == 'SAME':
            if not self.modInfo or self.modInfo.name not in bosh.modInfos:
                fileName = None
            else:
                fileName = self.modInfo.name
        #--Empty?
        if not fileName:
            modInfo = self.modInfo = None
            self.fileStr = u''
            self.authorStr = u''
            self.modifiedStr = u''
            self.descriptionStr = u''
            self.versionStr = u'v0.00'
            tagsStr = u''
        #--Valid fileName?
        else:
            modInfo = self.modInfo = bosh.modInfos[fileName]
            #--Remember values for edit checks
            self.fileStr = modInfo.name.s
            self.authorStr = modInfo.header.author
            self.modifiedStr = formatDate(modInfo.mtime)
            self.descriptionStr = modInfo.header.description
            self.versionStr = u'v%0.2f' % modInfo.header.version
            tagsStr = u'\n'.join(sorted(modInfo.getBashTags()))
        self.modified.SetEditable(True)
        self.modified.SetBackgroundColour(self.author.GetBackgroundColour())
        #--Set fields
        self.file.SetValue(self.fileStr)
        self.author.SetValue(self.authorStr)
        self.modified.SetValue(self.modifiedStr)
        self.description.SetValue(self.descriptionStr)
        self.version.SetLabel(self.versionStr)
        self.masters.SetFileInfo(modInfo)
        self.gTags.SetValue(tagsStr)
        if fileName and not bosh.modInfos.table.getItem(fileName,'autoBashTags', True):
            self.gTags.SetBackgroundColour(self.author.GetBackgroundColour())
        else:
            self.gTags.SetBackgroundColour(self.GetBackgroundColour())
        self.gTags.Refresh()
        #--Edit State
        self.edited = 0
        self.save.Disable()
        self.cancel.Disable()

    def SetEdited(self):
        if not self.modInfo: return
        self.edited = True
        if bush.game.esp.canEditHeader:
            self.save.Enable()
        self.cancel.Enable()

    def OnTextEdit(self,event):
        if not self.modInfo: return
        if self.modInfo and not self.edited:
            if ((self.fileStr != self.file.GetValue()) or
                (self.authorStr != self.author.GetValue()) or
                (self.modifiedStr != self.modified.GetValue()) or
                (self.descriptionStr != self.description.GetValue()) ):
                self.SetEdited()
        event.Skip()

    def OnEditFile(self,event):
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

    def OnEditAuthor(self,event):
        if not self.modInfo: return
        authorStr = self.author.GetValue()
        if authorStr != self.authorStr:
            self.authorStr = authorStr
            self.SetEdited()

    def OnEditModified(self,event):
        if not self.modInfo: return
        modifiedStr = self.modified.GetValue()
        if modifiedStr == self.modifiedStr: return
        try:
            newTimeTup = bosh.unformatDate(modifiedStr,u'%c')
            time.mktime(newTimeTup)
        except ValueError:
            balt.showError(self,_(u'Unrecognized date: ')+modifiedStr)
            self.modified.SetValue(self.modifiedStr)
            return
        except OverflowError:
            balt.showError(self,_(u'Bash cannot handle files dates greater than January 19, 2038.)'))
            self.modified.SetValue(self.modifiedStr)
            return
        #--Normalize format
        modifiedStr = time.strftime(u'%c',newTimeTup)
        self.modifiedStr = modifiedStr
        self.modified.SetValue(modifiedStr) #--Normalize format
        self.SetEdited()

    def OnEditDescription(self,event):
        if not self.modInfo: return
        descriptionStr = self.description.GetValue()
        if descriptionStr != self.descriptionStr:
            self.descriptionStr = descriptionStr
            self.SetEdited()

    def DoSave(self,event):
        modInfo = self.modInfo
        #--Change Tests
        changeName = (self.fileStr != modInfo.name)
        changeDate = (self.modifiedStr != formatDate(modInfo.mtime))
        changeHedr = (self.authorStr != modInfo.header.author or
                      self.descriptionStr != modInfo.header.description)
        changeMasters = self.masters.edited
        #--Warn on rename if file has BSA and/or dialog
        hasBsa, hasVoices = modInfo.hasResources()
        if changeName and (hasBsa or hasVoices):
            modName = modInfo.name.s
            if hasBsa and hasVoices:
                message = (_(u'This mod has an associated archive (%s.bsa) and an associated voice directory (Sound\\Voices\\%s), which will become detached when the mod is renamed.')
                           + u'\n\n' +
                           _(u'Note that the BSA archive may also contain a voice directory (Sound\\Voices\\%s), which would remain detached even if the archive name is adjusted.')
                           ) % (modName[:-4],modName,modName)
            elif hasBsa:
                message = (_(u'This mod has an associated archive (%s.bsa), which will become detached when the mod is renamed.')
                           + u'\n\n' +
                           _(u'Note that this BSA archive may contain a voice directory (Sound\\Voices\\%s), which would remain detached even if the archive file name is adjusted.')
                           ) % (modName[:-4],modName)
            else: #hasVoices
                message = _(u'This mod has an associated voice directory (Sound\\Voice\\%s), which will become detached when the mod is renamed.') % modName
            if not balt.askOk(self,message):
                return
        #--Only change date?
        if changeDate and not (changeName or changeHedr or changeMasters):
            newTimeTup = bosh.unformatDate(self.modifiedStr,u'%c')
            newTimeInt = int(time.mktime(newTimeTup))
            modInfo.setmtime(newTimeInt)
            self.SetFile(self.modInfo.name)
            bosh.modInfos.refresh(doInfos=False)
            bosh.modInfos.refreshInfoLists()
            modList.RefreshUI()
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
                                     'bash.rename.isBadFileName')
                ):
                return
            modList.items[modList.items.index(oldName)] = newName
            settings.getChanged('bash.mods.renames')[oldName] = newName
            bosh.modInfos.rename(oldName,newName)
            fileName = newName
        #--Change hedr/masters?
        if changeHedr or changeMasters:
            modInfo.header.author = self.authorStr.strip()
            modInfo.header.description = bolt.winNewLines(self.descriptionStr.strip())
            modInfo.header.masters = self.masters.GetNewMasters()
            modInfo.header.changed = True
            modInfo.writeHeader()
        #--Change date?
        if changeDate or changeHedr or changeMasters:
            newTimeTup = bosh.unformatDate(self.modifiedStr,u'%c')
            newTimeInt = int(time.mktime(newTimeTup))
            modInfo.setmtime(newTimeInt)
        #--Done
        try:
            #bosh.modInfos.refresh()
            bosh.modInfos.refreshFile(fileName)
            self.SetFile(fileName)
        except bosh.FileError:
            balt.showError(self,_(u'File corrupted on save!'))
            self.SetFile(None)
        if bosh.modInfos.refresh(doInfos=False):
            bosh.modInfos.refreshInfoLists()
        bosh.modInfos.plugins.refresh()
        modList.RefreshUI()

    def DoCancel(self,event):
        if self.modInfo:
            self.SetFile(self.modInfo.name)
        else:
            self.SetFile(None)

    #--Bash Tags
    def ShowBashTagsMenu(self,event):
        """Show bash tags menu."""
        modInfo = self.modInfo
        if not modInfo: return
        self.modTags = modTags = modInfo.getBashTags()
        #--Build menu
        # (ut) Not the prettiest code in the world but consider this the limit
        # I need to de-wx the code - blame IdList - TODO(ut) ChoiceLink(Links)
        isAuto = bosh.modInfos.table.getItem(modInfo.name,'autoBashTags',True)
        class _TagsAuto(CheckLink):
            id, text = ID_TAGS.AUTO, _(u'Automatic')
            help = _(
                u"Use the tags from the description and masterlist/userlist.")
            def _check(self): return isAuto
        bashTagsDesc = modInfo.getBashTagsDesc()
        class _CopyDesc(EnabledLink):
            id, text = ID_TAGS.COPY, _(u'Copy to Description')
            def _enable(self): return not isAuto and modTags != bashTagsDesc
        class _TagLink(CheckLink):
            def _initData(self, window, data):
                super(_TagLink, self)._initData(window, data)
                self.help = _(u"Add %(tag)s to %(modname)s") % (
                    {'tag': self.text, 'modname': modInfo.name})
            def _check(self): return self.text in modTags
        _self = self
        class _TagLinks(ChoiceLink):
            idList, cls = ID_TAGS, _TagLink
            def __init__(self):
                super(_TagLinks, self).__init__()
                self.extraItems = [_TagsAuto(), _CopyDesc(), SeparatorLink()]
                self.extraActions = {self.idList.AUTO: _self.DoAutoBashTags,
                                     self.idList.COPY: _self.DoCopyBashTags, }
            @property
            def items(self): return _self.allTags
            def DoList(self, event): _self.ToggleBashTag(event)
        tagLinks = Links()
        tagLinks.append(_TagLinks())
        tagLinks.PopupMenu(self.gTags, Link.Frame, None)

    def DoAutoBashTags(self,event):
        """Handle selection of automatic bash tags."""
        modInfo = self.modInfo
        if bosh.modInfos.table.getItem(modInfo.name,'autoBashTags'):
            # Disable autoBashTags
            bosh.modInfos.table.setItem(modInfo.name,'autoBashTags',False)
        else:
            # Enable autoBashTags
            bosh.modInfos.table.setItem(modInfo.name,'autoBashTags',True)
            modInfo.reloadBashTags()
        modList.RefreshUI(self.modInfo.name)

    def DoCopyBashTags(self,event):
        """Copies manually assigned bash tags into the mod description"""
        modInfo = self.modInfo
        modInfo.setBashTagsDesc(modInfo.getBashTags())
        modList.RefreshUI(self.modInfo.name)

    def ToggleBashTag(self,event):
        """Toggle bash tag from menu."""
        if bosh.modInfos.table.getItem(self.modInfo.name,'autoBashTags'):
            # Disable autoBashTags
            bosh.modInfos.table.setItem(self.modInfo.name,'autoBashTags',False)
        tag = self.allTags[event.GetId()-ID_TAGS.BASE]
        modTags = self.modTags ^ {tag}
        self.modInfo.setBashTags(modTags)
        modList.RefreshUI(self.modInfo.name)

#------------------------------------------------------------------------------
class INIPanel(SashPanel):
    def __init__(self, parent):
        SashPanel.__init__(self, parent,'bash.ini.sashPos')
        left,right = self.left, self.right
        #--Remove from list button
        self.button = button(right,_(u'Remove'),onClick=self.OnRemove)
        #--Edit button
        self.editButton = button(right,_(u'Edit...'),onClick=self.OnEdit)
        #--Choices
        self.choices = settings['bash.ini.choices']
        self.choice = settings['bash.ini.choice']
        self.CheckTargets()
        self.lastDir = bosh.dirs['mods'].s
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
        self.tweakName = roTextCtrl(right, noborder=True, multiline=False)
        self.SetBaseIni(self.GetChoice())
        global iniList
        from . import installer_links, ini_links
        self.listData = bosh.iniInfos
        installer_links.iniList = ini_links.iniList = iniList = \
            INIList(left, self.listData)
        self.list = iniList
        self.comboBox = balt.comboBox(right,wx.ID_ANY,value=self.GetChoiceString(),choices=self.sortKeys,style=wx.CB_READONLY)
        #--Events
        wx.EVT_SIZE(self,self.OnSize)
        self.comboBox.Bind(wx.EVT_COMBOBOX,self.OnSelectDropDown)
        iniList.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnSelectTweak)
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
            (iniList,2,wx.EXPAND),
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
        self.RefreshUI()

    def OnSelectTweak(self, event):
        tweakFile = iniList.items[event.GetIndex()]
        self.tweakName.SetValue(tweakFile.sbody)
        self.tweakContents.RefreshUI(tweakFile)
        event.Skip()

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

    def OnShow(self):
        changed = self.trackedInfo.refresh()
        changed = set([x for x in changed if x != bosh.oblivionIni.path])
        if self.GetChoice() in changed:
            self.RefreshUI()
        self.SetStatusCount()

    def RefreshUI(self,what='ALL'):
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
            iniList.RefreshUI()

    def SetBaseIni(self,path=None):
        """Sets the target INI file."""
        refresh = True
        choicePath = self.GetChoice()
        isGameIni = False
        for iFile in bosh.gameInis:
            if iFile.path == choicePath:
                refresh = bosh.iniInfos.ini != iFile
                bosh.iniInfos.setBaseIni(iFile)
                self.button.Enable(False)
                isGameIni = True
                break
        if not isGameIni:
            if not path:
                path = choicePath
            ini = bosh.BestIniFile(path)
            refresh = bosh.iniInfos.ini != ini
            bosh.iniInfos.setBaseIni(ini)
            self.button.Enable(True)
        selected = None
        # iniList can be None below cause we are called in init before iniList
        # is assigned - possibly to avoid a refresh ?
        if iniList is not None:
            selected = iniList.GetSelected()
            if len(selected) > 0:
                selected = selected[0]
            else:
                selected = None
        if refresh:
            self.trackedInfo.clear()
            self.trackedInfo.track(self.GetChoice())
        self.iniContents.RefreshUI(refresh)
        self.tweakContents.RefreshUI(selected)
        if iniList is not None: iniList.RefreshUI()

    def OnRemove(self,event):
        """Called when the 'Remove' button is pressed."""
        selection = self.comboBox.GetValue()
        self.choice -= 1
        del self.choices[selection]
        self.comboBox.SetItems(self.SortChoices())
        self.comboBox.SetSelection(self.choice)
        self.SetBaseIni()
        iniList.RefreshUI()

    def OnEdit(self,event):
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

    def SetStatusCount(self):
        """Sets mod count in last field."""
        stati = iniList.CountTweakStatus()
        text = _(u'Tweaks:') + u' %d/%d' % (stati[0],sum(stati[:-1]))
        statusBar.SetStatusText(text,2)

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
        iniList.RefreshUI()

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
                    iniList.RefreshUI()
                return
            self.lastDir = path.shead
        self.AddOrSelectIniDropDown(path)

    def OnSize(self,event):
        wx.Window.Layout(self)
        iniList.Layout()

    def ClosePanel(self):
        settings['bash.ini.choices'] = self.choices
        settings['bash.ini.choice'] = self.choice
        super(INIPanel, self).ClosePanel()

#------------------------------------------------------------------------------
class ModPanel(SashPanel):
    def __init__(self,parent):
        SashPanel.__init__(self, parent,'bash.mods.sashPos',1.0,minimumSize=150)
        left,right = self.left, self.right
        global modList
        from . import mods_links, mod_links, saves_links, app_buttons, \
            patcher_dialog
        self.listData = bosh.modInfos
        saves_links.modList = mods_links.modList = mod_links.modList = \
        app_buttons.modList = patcher_dialog.modList = modList = \
            ModList(left, self.listData)
        self.list = modList
        self.modDetails = ModDetails(right)
        modList.details = self.modDetails
        #--Events
        wx.EVT_SIZE(self,self.OnSize)
        #--Layout
        right.SetSizer(hSizer((self.modDetails,1,wx.EXPAND)))
        left.SetSizer(hSizer((modList,2,wx.EXPAND)))

    def RefreshUIColors(self):
        self.list.RefreshUI()
        self.modDetails.SetFile()

    def SetStatusCount(self):
        """Sets mod count in last field."""
        text = _(u'Mods:')+u' %d/%d' % (len(bosh.modInfos.ordered),len(bosh.modInfos.data))
        statusBar.SetStatusText(text,2)

    def OnSize(self,event):
        wx.Window.Layout(self)
        modList.Layout()
        self.modDetails.Layout()

    def ClosePanel(self):
        super(ModPanel, self).ClosePanel()
        settings['bash.mods.scrollPos'] = modList.vScrollPos
        # Mod details Sash Positions
        splitter = self.modDetails.right.GetParent()
        settings[self.modDetails.sashPosKey] = splitter.GetSashPosition()
        splitter = self.modDetails.subSplitter
        settings['bash.mods.details.subSplitterSashPos'] = splitter.GetSashPosition()

#------------------------------------------------------------------------------
class SaveList(List):
    #--Class Data
    mainMenu = Links() #--Column menu
    itemMenu = Links() #--Single item menu
    keyPrefix = 'bash.saves'

    def __init__(self, parent, listData):
        #--Columns
        self.colsKey = 'bash.saves.cols'
        #--Data/Items
        self.details = None #--Set by panel
        #--Parent init
        List.__init__(self, parent, listData, editLabels=True)
        #--Events
        self.list.Bind(wx.EVT_CHAR, self.OnChar)
        self.list.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self.list.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginEditLabel)
        self.list.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEditLabel)
        #--ScrollPos
        self.list.ScrollLines(settings.get('bash.saves.scrollPos',0))
        self.vScrollPos = self.list.GetScrollPos(wx.VERTICAL)

    def OnBeginEditLabel(self,event):
        """Start renaming saves"""
        item = self.items[event.GetIndex()]
        # Change the selection to not include the extension
        editbox = self.list.GetEditControl()
        to = len(GPath(event.GetLabel()).sbody)
        editbox.SetSelection(0,to)

    def OnEditLabel(self, event):
        """Savegame renamed."""
        if event.IsEditCancelled(): return
        #--File Info
        newName = event.GetLabel()
        if not newName.lower().endswith(u'.ess'):
            newName += u'.ess'
        newFileName = newName
        selected = self.GetSelected()
        for index, path in enumerate(selected):
            if index:
                newFileName = newName.replace(u'.ess',u'%d.ess' % index)
            if newFileName != path.s:
                oldPath = bosh.saveInfos.dir.join(path.s)
                newPath = bosh.saveInfos.dir.join(newFileName)
                if not newPath.exists():
                    oldPath.moveTo(newPath)
                    if GPath(oldPath.s[:-3]+bush.game.se.shortName.lower()).exists():
                        GPath(oldPath.s[:-3]+bush.game.se.shortName.lower()).moveTo(GPath(newPath.s[:-3]+bush.game.se.shortName.lower()))
                    if GPath(oldPath.s[:-3]+u'pluggy').exists():
                        GPath(oldPath.s[:-3]+u'pluggy').moveTo(GPath(newPath.s[:-3]+u'pluggy'))
        bosh.saveInfos.refresh()
        self.RefreshUI()

    def RefreshUI(self,files='ALL',detail='SAME'):
        """Refreshes UI for specified files."""
        #--Details
        if detail == 'SAME':
            selected = set(self.GetSelected())
        else:
            selected = {detail}
        #--Populate
        if files == 'ALL':
            self.PopulateItems(selected=selected)
        elif isinstance(files,bolt.Path):
            self.PopulateItem(files,selected=selected)
        else: #--Iterable
            for file in files:
                self.PopulateItem(file,selected=selected)
        saveDetails.SetFile(detail)
        bashFrame.SetStatusCount()

    #--Populate Item
    def PopulateItem(self,itemDex,mode=0,selected=set()):
        #--String name of item?
        if not isinstance(itemDex,int):
            itemDex = self.items.index(itemDex)
        fileName = GPath(self.items[itemDex])
        fileInfo = self.data[fileName]
        cols = self.cols
        for colDex in range(self.numCols):
            col = cols[colDex]
            if col == 'File':
                value = fileName.s
            elif col == 'Modified':
                value = formatDate(fileInfo.mtime)
            elif col == 'Size':
                value = formatInteger(max(fileInfo.size,1024)/1024 if fileInfo.size else 0)+u' KB'
            elif col == 'Player' and fileInfo.header:
                value = fileInfo.header.pcName
            elif col == 'PlayTime' and fileInfo.header:
                playMinutes = fileInfo.header.gameTicks/60000
                value = u'%d:%02d' % (playMinutes/60,(playMinutes % 60))
            elif col == 'Cell' and fileInfo.header:
                value = fileInfo.header.pcLocation
            else:
                value = u'-'
            if mode and (colDex == 0):
                self.list.InsertStringItem(itemDex, value)
            else:
                self.list.SetStringItem(itemDex, colDex, value)
        #--Image
        status = fileInfo.getStatus()
        on = fileName.cext == u'.ess'
        self.list.SetItemImage(itemDex,self.icons.Get(status,on))
        #--Selection State
        self.SelectItemAtIndex(itemDex, fileName in selected)

    #--Sort Items
    def SortItems(self,col=None,reverse=-2):
        (col, reverse) = self.GetSortSettings(col,reverse)
        settings['bash.saves.sort'] = col
        data = self.data
        #--Start with sort by name
        self.items.sort()
        if col == 'File':
            pass #--Done by default
        elif col == 'Modified':
            self.items.sort(key=lambda a: data[a].mtime)
        elif col == 'Size':
            self.items.sort(key=lambda a: data[a].size)
        elif col == 'Status':
            self.items.sort(key=lambda a: data[a].getStatus())
        elif col == 'Player':
            self.items.sort(key=lambda a: data[a].header.pcName)
        elif col == 'PlayTime':
            self.items.sort(key=lambda a: data[a].header.gameTicks)
        elif col == 'Cell':
            self.items.sort(key=lambda a: data[a].header.pcLocation)
        else:
            raise BashError(u'Unrecognized sort key: '+col)
        #--Ascending
        if reverse: self.items.reverse()

    #--Events ---------------------------------------------
    def OnChar(self,event):
        """Char event: Reordering."""
        ## Delete
        if event.GetKeyCode() in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self.DeleteSelected()
        ## F2 - Rename
        if event.GetKeyCode() == wx.WXK_F2:
            selected = self.GetSelected()
            if len(selected) > 0:
                index = self.list.FindItem(0,selected[0].s)
                if index != -1:
                    self.list.EditLabel(index)
        event.Skip()

    def OnKeyUp(self,event):
        """Char event: select all items"""
        code = event.GetKeyCode()
        ##Ctrl+A
        if event.CmdDown() and code == ord('A'):
            self.SelectAll()
        # Ctrl+C: Copy file(s) to clipboard
        elif event.CmdDown() and code == ord('C'):
            sel = map(lambda save: self.data[save].getPath().s,
                      self.GetSelected())
            copyListToClipboard(sel)
        event.Skip()
    #--Event: Left Down
    def OnLeftDown(self,event):
        (hitItem,hitFlag) = self.list.HitTest((event.GetX(),event.GetY()))
        if hitFlag == wx.LIST_HITTEST_ONITEMICON:
            fileName = GPath(self.items[hitItem])
            newEnabled = not self.data.isEnabled(fileName)
            newName = self.data.enable(fileName,newEnabled)
            if newName != fileName: self.RefreshUI()
        #--Pass Event onward
        event.Skip()

    def OnItemSelected(self,event=None):
        saveName = self.items[event.m_itemIndex]
        self.details.SetFile(saveName)

#------------------------------------------------------------------------------
class SaveDetails(SashPanel):
    """Savefile details panel."""
    def __init__(self,parent):
        """Initialize."""
        SashPanel.__init__(self, parent,'bash.saves.details.SashPos',0.0,sashPos=230,
                           isVertical=False,minimumSize=230,style=wx.SW_BORDER|splitterStyle)
        top,bottom = self.left, self.right
        readOnlyColour = self.GetBackgroundColour()
        #--Singleton
        global saveDetails
        saveDetails = self
        #--Data
        self.saveInfo = None
        self.edited = False
        textWidth = 200
        #--File Name
        self.file = textCtrl(top, size=(textWidth, -1),
                             onKillFocus=self.OnEditFile,
                             onText=self.OnTextEdit)
        self.file.SetMaxLength(256)
        #--Player Info
        self.playerInfo = staticText(top,u" \n \n ")
        self.gCoSaves = staticText(top,u'--\n--')
        #--Picture
        self.picture = balt.Picture(top,textWidth,192*textWidth/256,style=wx.BORDER_SUNKEN,background=colors['screens.bkgd.image']) #--Native: 256x192
        subSplitter = self.subSplitter = wx.gizmos.ThinSplitterWindow(bottom,style=splitterStyle)
        masterPanel = wx.Panel(subSplitter)
        notePanel = wx.Panel(subSplitter)
        #--Masters
        self.masters = MasterList(masterPanel,None,self.SetEdited)
        #--Save Info
        self.gInfo = textCtrl(notePanel, size=(textWidth, 100),
                              multiline=True, onText=self.OnInfoEdit)
        self.gInfo.SetMaxLength(2048)
        #--Save/Cancel
        self.save = button(masterPanel,id=wx.ID_SAVE,onClick=self.DoSave)
        self.cancel = button(masterPanel,id=wx.ID_CANCEL,onClick=self.DoCancel)
        self.save.Disable()
        self.cancel.Disable()
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
            (self.masters,1,wx.EXPAND|wx.TOP,4),
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
        subSplitter.SetSashPosition(settings.get('bash.saves.details.subSplitterSashPos', 500))
        mastersSizer.SetSizeHints(masterPanel)
        masterPanel.SetSizer(mastersSizer)
        noteSizer.SetSizeHints(masterPanel)
        notePanel.SetSizer(noteSizer)
        bottom.SetSizer(vSizer((subSplitter,1,wx.EXPAND)))

    def SetFile(self,fileName='SAME'):
        """Set file to be viewed."""
        #--Reset?
        if fileName == 'SAME':
            if not self.saveInfo or self.saveInfo.name not in bosh.saveInfos:
                fileName = None
            else:
                fileName = self.saveInfo.name
        #--Null fileName?
        if not fileName:
            saveInfo = self.saveInfo = None
            self.fileStr = u''
            self.playerNameStr = u''
            self.curCellStr = u''
            self.playerLevel = 0
            self.gameDays = 0
            self.playMinutes = 0
            self.picData = None
            self.coSaves = u'--\n--'
        #--Valid fileName?
        else:
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
        self.masters.SetFileInfo(saveInfo)
        #--Picture
        if not self.picData:
            self.picture.SetBitmap(None)
        else:
            width,height,data = self.picData
            image = Image.GetImage(data, height, width)
            self.picture.SetBitmap(image.ConvertToBitmap())
        #--Edit State
        self.edited = 0
        self.save.Disable()
        self.cancel.Disable()
        #--Info Box
        self.gInfo.DiscardEdits()
        if fileName:
            self.gInfo.SetValue(bosh.saveInfos.table.getItem(fileName,'info',_(u'Notes: ')))
        else:
            self.gInfo.SetValue(_(u'Notes: '))

    def SetEdited(self):
        """Mark as edited."""
        self.edited = True
        if bush.game.ess.canEditMasters:
            self.save.Enable()
        self.cancel.Enable()

    def OnInfoEdit(self,event):
        """Info field was edited."""
        if self.saveInfo and self.gInfo.IsModified():
            bosh.saveInfos.table.setItem(self.saveInfo.name, 'info',
                                         self.gInfo.GetValue())
        event.Skip() # not strictly needed - no other handler for onKillFocus

    def OnTextEdit(self,event):
        """Event: Editing file or save name text."""
        if self.saveInfo and not self.edited:
            if self.fileStr != self.file.GetValue():
                self.SetEdited()
        event.Skip()

    def OnEditFile(self,event):
        """Event: Finished editing file name."""
        if not self.saveInfo: return
        #--Changed?
        fileStr = self.file.GetValue()
        if fileStr == self.fileStr: return
        #--Extension Changed?
        if self.fileStr[-4:].lower() not in (u'.ess',u'.bak'):
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

    def DoSave(self,event):
        """Event: Clicked Save button."""
        saveInfo = self.saveInfo
        #--Change Tests
        changeName = (self.fileStr != saveInfo.name)
        changeMasters = self.masters.edited
        #--Backup
        saveInfo.makeBackup()
        prevMTime = saveInfo.mtime
        #--Change Name?
        if changeName:
            (oldName,newName) = (saveInfo.name,GPath(self.fileStr.strip()))
            saveList.items[saveList.items.index(oldName)] = newName
            bosh.saveInfos.rename(oldName,newName)
        #--Change masters?
        if changeMasters:
            saveInfo.header.masters = self.masters.GetNewMasters()
            saveInfo.header.writeMasters(saveInfo.getPath())
            saveInfo.setmtime(prevMTime)
        #--Done
        try:
            bosh.saveInfos.refreshFile(saveInfo.name)
            self.SetFile(self.saveInfo.name)
        except bosh.FileError:
            balt.showError(self,_(u'File corrupted on save!'))
            self.SetFile(None)
            saveList.RefreshUI()
        else:
            saveList.RefreshUI(saveInfo.name)

    def DoCancel(self,event):
        """Event: Clicked cancel button."""
        self.SetFile(self.saveInfo.name)

#------------------------------------------------------------------------------
class SavePanel(SashPanel):
    """Savegames tab."""
    def __init__(self,parent):
        if not bush.game.ess.canReadBasic:
            raise Exception(u'Wrye Bash cannot read save games for %s.' % bush.game.displayName)
        SashPanel.__init__(self, parent,'bash.saves.sashPos',1.0,minimumSize=200)
        left,right = self.left, self.right
        global saveList
        from . import saves_links
        self.listData = bosh.saveInfos
        saves_links.saveList = saveList = SaveList(left, self.listData)
        self.list = saveList
        self.saveDetails = SaveDetails(right)
        saveList.details = self.saveDetails
        #--Events
        wx.EVT_SIZE(self,self.OnSize)
        #--Layout
        right.SetSizer(hSizer((self.saveDetails,1,wx.EXPAND)))
        left.SetSizer(hSizer((saveList,2,wx.EXPAND)))

    def RefreshUIColors(self):
        self.saveDetails.SetFile()
        self.saveDetails.picture.SetBackground(colors['screens.bkgd.image'])

    def SetStatusCount(self):
        """Sets mod count in last field."""
        text = _(u"Saves: %d") % (len(bosh.saveInfos.data))
        statusBar.SetStatusText(text,2)

    def OnSize(self,event=None):
        wx.Window.Layout(self)
        saveList.Layout()
        self.saveDetails.Layout()

    def ClosePanel(self):
        bosh.saveInfos.profiles.save()
        super(SavePanel, self).ClosePanel()
        settings['bash.saves.scrollPos'] = saveList.vScrollPos
        # Save details Sash Positions
        splitter = self.saveDetails.right.GetParent()
        settings[self.saveDetails.sashPosKey] = splitter.GetSashPosition()
        splitter = self.saveDetails.subSplitter
        settings['bash.saves.details.subSplitterSashPos'] = splitter.GetSashPosition()

#------------------------------------------------------------------------------
class InstallersList(balt.Tank):
    keyPrefix = 'bash.installers'
    mainMenu = Links()
    itemMenu = Links()
    icons = installercons

    def __init__(self, parent, data, details=None):
        balt.Tank.__init__(self, parent, data, details=details, dndList=True,
                           dndFiles=True, dndColumns=['Order'],
                           editLabels=True)
        self.gList.Bind(wx.EVT_CHAR, self.OnChar)
        self.gList.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self.gList.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginEditLabel)
        self.gList.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEditLabel)
        self.hitItem = None
        self.hitTime = 0

    def GetColumnDex(self,column):
        return settingDefaults['bash.installers.cols'].index(column)

    def OnBeginEditLabel(self,event):
        """Start renaming installers"""
        #--Only rename multiple items of the same type
        firstItem = self.data[self.GetSelected()[0]]
        InstallerType = None
        if isinstance(firstItem,bosh.InstallerMarker):
            InstallerType = bosh.InstallerMarker
        elif isinstance(firstItem,bosh.InstallerArchive):
            InstallerType = bosh.InstallerArchive
        elif isinstance(firstItem,bosh.InstallerProject):
            InstallerType = bosh.InstallerProject
        else:
            event.Veto()
            return
        for item in self.GetSelected():
            if not isinstance(self.data[item],InstallerType):
                event.Veto()
                return
            #--Also, don't allow renaming the 'Last' marker
            elif item == u'==Last==':
                event.Veto()
                return
        editbox = self.gList.GetEditControl()
        editbox.Bind(wx.EVT_CHAR, self.OnEditLabelChar)
        #--Markers, change the selection to not include the '=='
        if InstallerType is bosh.InstallerMarker:
            to = len(event.GetLabel()) - 2
            editbox.SetSelection(2,to)
        #--Archives, change the selection to not include the extension
        elif InstallerType is bosh.InstallerArchive:
            to = len(GPath(event.GetLabel()).sbody)
            editbox.SetSelection(0,to)

    def OnEditLabelChar(self, event):
        """For pressing F2 on the edit box for renaming"""
        if event.GetKeyCode() == wx.WXK_F2:
            editbox = self.gList.GetEditControl()
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

            selected = self.data[self.GetSelected()[0]]
            if isinstance(selected, bosh.InstallerArchive):
                selection = (0, lenNextLower)
            elif isinstance(selected, bosh.InstallerMarker):
                selection = (2, lenWithExt-2)
            else:
                selection = (0, lenWithExt)
            editbox.SetSelection(*selection)
        else:
            event.Skip()

    def OnEditLabel(self, event):
        """Renamed some installers"""
        if event.IsEditCancelled(): return

        newName = event.GetLabel()

        selected = self.GetSelected()
        if isinstance(self.data[selected[0]], bosh.InstallerArchive):
            InstallerType = bosh.InstallerArchive
            rePattern = re.compile(ur'^([^\\/]+?)(\d*)((\.(7z|rar|zip|001))+)$',re.I|re.U)
        elif isinstance(self.data[selected[0]], bosh.InstallerMarker):
            InstallerType = bosh.InstallerMarker
            rePattern = re.compile(ur'^([^\\/]+?)(\d*)$',re.I|re.U)
        elif isinstance(self.data[selected[0]], bosh.InstallerProject):
            InstallerType = bosh.InstallerProject
            rePattern = re.compile(ur'^([^\\/]+?)(\d*)$',re.I|re.U)
        maPattern = rePattern.match(newName)
        if not maPattern:
            balt.showError(self,_(u'Bad extension or file root: ')+newName)
            event.Veto()
            return
        root,numStr = maPattern.groups()[:2]
        if InstallerType is bosh.InstallerMarker:
            root = root.strip(u'=')
        #--Rename each installer, keeping the old extension (for archives)
        numLen = len(numStr)
        num = int(numStr or 0)
        installersDir = bosh.dirs['installers']
        with balt.BusyCursor():
            refreshNeeded = False
            for archive in selected:
                installer = self.data[archive]
                if InstallerType is bosh.InstallerProject:
                    newName = GPath(root+numStr)
                else:
                    newName = GPath(root+numStr+archive.ext)
                if InstallerType is bosh.InstallerMarker:
                    newName = GPath(u'==' + newName.s + u'==')
                if newName != archive:
                    oldPath = installersDir.join(archive)
                    newPath = installersDir.join(newName)
                    if not newPath.exists():
                        if InstallerType is not bosh.InstallerMarker:
                            oldPath.moveTo(newPath)
                        self.data.pop(installer)
                        installer.archive = newName.s
                        #--Add the new archive to Bash
                        self.data[newName] = installer
                        #--Update the iniInfos & modInfos for 'installer'
                        if InstallerType is not bosh.InstallerMarker:
                            mfiles = (x for x in bosh.modInfos.table.getColumn('installer') if bosh.modInfos.table[x]['installer'] == oldPath.stail)
                            ifiles = (x for x in bosh.iniInfos.table.getColumn('installer') if bosh.iniInfos.table[x]['installer'] == oldPath.stail)
                            for i in mfiles:
                                bosh.modInfos.table[i]['installer'] = newPath.stail
                            for i in ifiles:
                                bosh.iniInfos.table[i]['installer'] = newPath.stail
                    if InstallerType is bosh.InstallerMarker:
                        del self.data[archive]
                    refreshNeeded = True
                num += 1
                numStr = unicode(num)
                numStr = u'0'*(numLen-len(numStr))+numStr
            #--Refresh UI
            if refreshNeeded:
                self.data.refresh(what='I')
                modList.RefreshUI()
                if iniList is not None:
                    # It will be None if the INI Edits Tab was hidden at startup,
                    # and never initialized
                    iniList.RefreshUI()
                self.RefreshUI()
            event.Veto()

    def OnDropFiles(self, x, y, filenames):
        filenames = [GPath(x) for x in filenames]
        omodnames = [x for x in filenames if not x.isdir() and x.cext == u'.omod']
        converters = [x for x in filenames if self.data.validConverterName(x)]
        filenames = [x for x in filenames if x.isdir() or x.cext in bosh.readExts and x not in converters]
        if len(omodnames) > 0:
            failed = []
            completed = []
            progress = balt.Progress(_(u'Extracting OMODs...'),u'\n'+u' '*60,abort=True)
            progress.setFull(len(omodnames))
            try:
                for i,omod in enumerate(omodnames):
                    progress(i,omod.stail)
                    outDir = bosh.dirs['installers'].join(omod.body)
                    if outDir.exists():
                        if balt.askYes(progress.dialog,_(u"The project '%s' already exists.  Overwrite with '%s'?") % (omod.sbody,omod.stail)):
                            balt.shellDelete(outDir,self,False,False,False)
                        else:
                            continue
                    try:
                        bosh.OmodFile(omod).extractToProject(outDir,SubProgress(progress,i))
                        completed.append(omod)
                    except (CancelError,SkipError):
                        # Omod extraction was cancelled, or user denied admin rights if needed
                        raise
                    except:
                        deprint(_(u"Failed to extract '%s'.") % omod.stail + u'\n\n', traceback=True)
            except CancelError:
                skipped = set(omodnames) - set(completed)
                msg = u''
                if len(completed) > 0:
                    completed = [u' * ' + x.stail for x in completed]
                    msg += _(u'The following OMODs were unpacked:')+u'\n%s\n\n' % u'\n'.join(completed)
                if len(skipped) > 0:
                    skipped = [u' * ' + x.stail for x in skipped]
                    msg += _(u'The following OMODs were skipped:')+u'\n%s\n\n' % u'\n'.join(skipped)
                if len(failed) > 0:
                    msg += _(u'The following OMODs failed to extract:')+u'\n%s' % u'\n'.join(failed)
                balt.showOk(self,msg,_(u'OMOD Extraction Canceled'))
            else:
                if len(failed) > 0:
                    balt.showWarning(self,
                                     _(u'The following OMODs failed to extract.  This could be a file IO error, or an unsupported OMOD format:')+u'\n\n'+u'\n'.join(failed),
                                     _(u'OMOD Extraction Complete'))
            finally:
                progress(len(omodnames),_(u'Refreshing...'))
                self.data.refresh(what='I')
                self.RefreshUI()
                progress.Destroy()
        if not filenames and not converters:
            return
        action = settings['bash.installers.onDropFiles.action']
        if action not in ['COPY','MOVE']:
            message = _(u'You have dragged the following files into Wrye Bash:')+u'\n'
            for file in filenames:
                message += u' * ' + file.s + u'\n'
            message += u'\n'
            message += _(u'What would you like to do with them?')

            dialog= balt.Dialog(self,_(u'Move or Copy?'),size=(400,200))
            icon = staticBitmap(dialog)
            gCheckBox = checkBox(dialog,_(u"Don't show this in the future."))

            sizer = vSizer(
                (hSizer(
                    (icon,0,wx.ALL,6),
                    (staticText(dialog,message,style=wx.ST_NO_AUTORESIZE),1,wx.EXPAND|wx.LEFT,6),
                    ),1,wx.EXPAND|wx.ALL,6),
                (gCheckBox,0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,6),
                (hSizer(
                    spacer,
                    button(dialog,label=_(u'Move'),onClick=lambda x: dialog.EndModal(1)),
                    (button(dialog,label=_(u'Copy'),onClick=lambda x: dialog.EndModal(2)),0,wx.LEFT,4),
                    (button(dialog,id=wx.ID_CANCEL),0,wx.LEFT,4),
                    ),0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,6),
                )
            dialog.SetSizer(sizer)
            result = dialog.ShowModal() # buttons call dialog.EndModal(1/2)
            if result == 1:
                action = 'MOVE'
            elif result == 2:
                action = 'COPY'
            else:
                return
            if gCheckBox.GetValue():
                settings['bash.installers.onDropFiles.action'] = action
        with balt.BusyCursor():
            installersJoin = bosh.dirs['installers'].join
            convertersJoin = bosh.dirs['converters'].join
            filesTo = [installersJoin(x.tail) for x in filenames]
            filesTo.extend(convertersJoin(x.tail) for x in converters)
            filenames.extend(converters)
            try:
                if action == 'COPY':
                    #--Copy the dropped files
                    balt.shellCopy(filenames,filesTo,self,False,False,False)
                elif action == 'MOVE':
                    #--Move the dropped files
                    balt.shellMove(filenames,filesTo,self,False,False,False)
                else:
                    return
            except (CancelError,SkipError):
                pass
            modList.RefreshUI()
            if iniList:
                iniList.RefreshUI()
        gInstallers.frameActivated = True
        gInstallers.OnShow()

    def DeleteSelected(self, shellUI=False, noRecycle=False, _refresh=False):
        super(InstallersList, self).DeleteSelected(shellUI, noRecycle, _refresh)
        with balt.BusyCursor():
            # below ripped from Installer_Hide
            self.data.refresh(what='ION')
            self.RefreshUI()

    def OnChar(self,event):
        """Char event: Reorder."""
        code = event.GetKeyCode()
        ##Ctrl+Up/Ctrl+Down - Move installer up/down install order
        if event.CmdDown() and code in (wx.WXK_UP,wx.WXK_DOWN,wx.WXK_NUMPAD_UP,wx.WXK_NUMPAD_DOWN):
            if len(self.GetSelected()) < 1: return
            orderKey = lambda x: self.data.data[x].order
            maxPos = max(self.data.data[x].order for x in self.data.data)
            if code in (wx.WXK_DOWN,wx.WXK_NUMPAD_DOWN):
                moveMod = 1
                visibleIndex = self.GetIndex(sorted(self.GetSelected(),key=orderKey)[-1]) + 2
            else:
                moveMod = -1
                visibleIndex = self.GetIndex(sorted(self.GetSelected(),key=orderKey)[0]) - 2
            for thisFile in sorted(self.GetSelected(),key=orderKey,reverse=(moveMod != -1)):
                newPos = self.data.data[thisFile].order + moveMod
                if newPos < 0 or maxPos < newPos: break
                self.data.moveArchives([thisFile],newPos)
            self.data.refresh(what='IN')
            self.RefreshUI()
            if visibleIndex > maxPos: visibleIndex = maxPos
            elif visibleIndex < 0: visibleIndex = 0
            self.gList.EnsureVisible(visibleIndex)
        elif code in (wx.WXK_RETURN,wx.WXK_NUMPAD_ENTER):
        ##Enter - Open selected Installer/
            selected = self.GetSelected()
            if selected:
                path = self.data.dir.join(selected[0])
                if path.exists(): path.start()
        elif event.CmdDown() and code == ord('V'):
            ##Ctrl+V
            balt.clipboardDropFiles(10, self.OnDrKopFiles)
        else:
            event.Skip()

    def OnDClick(self,event):
        """Double click, open the installer."""
        (hitItem,hitFlag) = self.gList.HitTest(event.GetPosition())
        if hitItem < 0: return
        item = self.GetItem(hitItem)
        if isinstance(self.data[item],bosh.InstallerMarker):
            # Double click on a Marker, select all items below
            # it in install order, up to the next Marker
            sorted = self.data.getSorted('order',False,False)
            item = self.data[item]
            for nextItem in sorted[item.order+1:]:
                installer = self.data[nextItem]
                if isinstance(installer,bosh.InstallerMarker):
                    break
                itemDex = self.GetIndex(nextItem)
                self.SelectItemAtIndex(itemDex)
        else:
            path = self.data.dir.join(self.GetItem(hitItem))
            if path.exists(): path.start()
        event.Skip()

    def OnKeyUp(self,event):
        """Char events: Action depends on keys pressed"""
        code = event.GetKeyCode()
        ##Ctrl+A - select all
        if event.CmdDown() and code == ord('A'):
            self.SelectAll()
        ##Delete - delete
        elif code in (wx.WXK_DELETE,wx.WXK_NUMPAD_DELETE):
            with balt.BusyCursor():
                self.DeleteSelected(shellUI=True, noRecycle=event.ShiftDown())
        ##F2 - Rename selected.
        elif code == wx.WXK_F2:
            selected = self.GetSelected()
            if selected > 0:
                index = self.GetIndex(selected[0])
                if index != -1:
                    self.gList.EditLabel(index)
        ##Ctrl+Shift+N - Add a marker
        elif event.CmdDown() and event.ShiftDown() and code == ord('N'):
            index = self.GetIndex(GPath(u'===='))
            if index == -1:
                self.data.addMarker(u'====')
                self.data.refresh(what='OS')
                gInstallers.RefreshUIMods()
                index = self.GetIndex(GPath(u'===='))
            if index != -1:
                self.ClearSelected()
                self.SelectItemAtIndex(index)
                self.gList.EditLabel(index)
        # Ctrl+C: Copy file(s) to clipboard
        elif event.CmdDown() and code == ord('C'):
            sel = map(lambda x: bosh.dirs['installers'].join(x).s,
                      self.GetSelected())
            copyListToClipboard(sel)
        event.Skip()

#------------------------------------------------------------------------------
class InstallersPanel(SashTankPanel):
    """Panel for InstallersTank."""
    espmMenu = Links()
    subsMenu = Links()

    def __init__(self,parent):
        """Initialize."""
        global gInstallers
        gInstallers = self
        from . import installers_links, installer_links, dialogs
        installers_links.gInstallers = installer_links.gInstallers = \
            dialogs.gInstallers = self
        data = bosh.InstallersData()
        SashTankPanel.__init__(self,data,parent)
        left,right = self.left,self.right
        commentsSplitter = wx.gizmos.ThinSplitterWindow(right, style=splitterStyle)
        subSplitter = wx.gizmos.ThinSplitterWindow(commentsSplitter, style=splitterStyle)
        checkListSplitter = wx.gizmos.ThinSplitterWindow(subSplitter, style=splitterStyle)
        #--Refreshing
        self.refreshed = False
        self.refreshing = False
        self.frameActivated = False
        self.fullRefresh = False
        #--Contents
        self.gList = InstallersList(left, data, details=self)
        bosh.installersWindow = self.gList
        #--Package
        self.gPackage = roTextCtrl(right, noborder=True)
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
            gPage = roTextCtrl(self.gNotebook, name=name, hscroll=True)
            self.gNotebook.AddPage(gPage,title)
            self.infoPages.append([gPage,False])
        self.gNotebook.SetSelection(settings['bash.installers.page'])
        self.gNotebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED,self.OnShowInfoPage)
        #--Sub-Installers
        subPackagesPanel = wx.Panel(checkListSplitter)
        subPackagesLabel = staticText(subPackagesPanel, _(u'Sub-Packages'))
        self.gSubList = balt.listBox(subPackagesPanel, isExtended=True,
                                     kind='checklist')
        self.gSubList.Bind(wx.EVT_CHECKLISTBOX,self.OnCheckSubItem)
        self.gSubList.Bind(wx.EVT_RIGHT_UP,self.SubsSelectionMenu)
        #--Espms
        espmsPanel = wx.Panel(checkListSplitter)
        espmsLabel = staticText(espmsPanel, _(u'Esp/m Filter'))
        self.espms = []
        self.gEspmList = balt.listBox(espmsPanel, isExtended=True,
                                      kind='checklist')
        self.gEspmList.Bind(wx.EVT_CHECKLISTBOX,self.OnCheckEspmItem)
        self.gEspmList.Bind(wx.EVT_RIGHT_UP,self.SelectionMenu)
        #--Comments
        commentsPanel = wx.Panel(commentsSplitter)
        commentsLabel = staticText(commentsPanel, _(u'Comments'))
        self.gComments = textCtrl(commentsPanel, multiline=True)
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
            (self.gList,1,wx.EXPAND),
            )
        left.SetSizer(leftSizer)
        wx.LayoutAlgorithm().LayoutWindow(self,left)
        commentsSplitterSavedSashPos = settings.get('bash.installers.commentsSplitterSashPos', 0)
        # restore saved comments text box size
        if 0 == commentsSplitterSavedSashPos:
            commentsSplitter.SetSashPosition(-commentsHeight)
        else:
            commentsSplitter.SetSashPosition(commentsSplitterSavedSashPos)
        #--Events
        #self.Bind(wx.EVT_SIZE,self.OnSize)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self._onMouseCaptureLost)
        commentsSplitter.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self._OnCommentsSplitterSashPosChanged)

    def RefreshUIColors(self):
        """Update any controls using custom colors."""
        self.gList.RefreshUI()

    def OnShow(self,canCancel=True):
        """Panel is shown. Update self.data."""
        if settings.get('bash.installers.isFirstRun',True):
            # I have no idea why this is neccesary but if the mouseCaptureLost event is not fired before showing the askYes dialog it thorws an exception
            event = wx.CommandEvent()
            event.SetEventType(wx.EVT_MOUSE_CAPTURE_LOST.typeId)
            wx.PostEvent(self.GetEventHandler(), event)

            settings['bash.installers.isFirstRun'] = False
            message = (_(u'Do you want to enable Installers?')
                       + u'\n\n\t' +
                       _(u'If you do, Bash will first need to initialize some data. This can take on the order of five minutes if there are many mods installed.')
                       + u'\n\n\t' +
                       _(u"If not, you can enable it at any time by right-clicking the column header menu and selecting 'Enabled'.")
                       )
            settings['bash.installers.enabled'] = balt.askYes(self,fill(message,80),self.data.title)
        if not settings['bash.installers.enabled']: return
        if self.refreshing: return
        data = self.gList.data
        if settings.get('bash.installers.updatedCRCs',True):
            settings['bash.installers.updatedCRCs'] = False
            self.refreshed = False
        if self.frameActivated and data.extractOmodsNeeded():
            self.refreshing = True
            try:
                with balt.Progress(_(u'Extracting OMODs...'),u'\n'+u' '*60) as progress:
                    dirInstallers = bosh.dirs['installers']
                    dirInstallersJoin = dirInstallers.join
                    omods = [dirInstallersJoin(x) for x in dirInstallers.list() if x.cext == u'.omod']
                    progress.setFull(max(len(omods),1))
                    for i,omod in enumerate(omods):
                        progress(i,x.stail)
                        outDir = dirInstallersJoin(omod.body)
                        num = 0
                        omodRemoves = set()
                        omodMoves = set()
                        while outDir.exists():
                            outDir = dirInstallersJoin(u'%s%s' % (omod.sbody,num))
                            num += 1
                        try:
                            bosh.OmodFile(omod).extractToProject(outDir,SubProgress(progress,i))
                            omodRemoves.add(omod)
                        except (CancelError,SkipError):
                            omodMoves.add(omod)
                        except Exception as e:
                            deprint(_(u"Error extracting OMOD '%s':") % omod.stail,traceback=True)
                            # Ensures we don't infinitely refresh if moving the omod fails
                            data.failedOmods.add(omod.body)
                            omodMoves.add(omod)
                    # Delete extracted omods
                    try:
                        balt.shellDelete(omodRemoves,self,False,False)
                    except (CancelError,SkipError):
                        while balt.askYes(self,_(u'Bash needs Administrator Privileges to delete OMODs that have already been extracted.')
                                          + u'\n\n' +
                                          _(u'Try again?'),_(u'OMOD Extraction - Cleanup Error')):
                            try:
                                omodRemoves = set(x for x in omodRemoves if x.exists())
                                balt.shellDelete(omodRemoves,self,False,False)
                            except (CancelError,SkipError):
                                continue
                            break
                        else:
                            # User decided not to give permission.  Add omod to 'failedOmods' so we know not to try to extract them again
                            for omod in omodRemoves:
                                if omod.exists():
                                    data.failedOmods.add(omod.body)
                    # Move bad omods
                    try:
                        omodMoves = list(omodMoves)
                        omodDests = [dirInstallersJoin(u'Bash',u'Failed OMODs',omod.tail) for omod in omodMoves]
                        balt.shellMakeDirs(dirInstallersJoin(u'Bash',u'Failed OMODs'))
                        balt.shellMove(omodMoves,omodDests,self,False,False,False)
                    except (CancelError,SkipError):
                        while balt.askYes(self,_(u'Bash needs Administrator Privileges to move failed OMODs out of the Bash Installers directory.')
                                          + u'\n\n' +
                                          _(u'Try again?'),_(u'OMOD Extraction - Cleanup Error')):
                            try:
                                omodMoves = [x for x in omodMoves]
                                omodDests = [dirInstallersJoin(u'Bash',u'Failed OMODs',omod.body) for omod in omodMoves]
                                balt.shellMove(omodMoves,omodDests,self,False,False,False)
                            except (CancelError,SkipError):
                                continue
                            break
            finally:
                self.refreshing = False
        if not self.refreshed or (self.frameActivated and data.refreshInstallersNeeded()):
            self.refreshing = True
            with balt.Progress(_(u'Refreshing Installers...'),u'\n'+u' '*60, abort=canCancel) as progress:
                try:
                    what = ('DISC','IC')[self.refreshed]
                    if data.refresh(progress,what,self.fullRefresh):
                        self.gList.RefreshUI()
                    self.fullRefresh = False
                    self.frameActivated = False
                    self.refreshing = False
                    self.refreshed = True
                except CancelError:
                    # User canceled the refresh
                    self.refreshing = False
                    self.refreshed = True
        elif self.frameActivated and data.refreshConvertersNeeded():
            self.refreshing = True
            with balt.Progress(_(u'Refreshing Converters...'),u'\n'+u' '*60) as progress:
                try:
                    if data.refresh(progress,'C',self.fullRefresh):
                        self.gList.RefreshUI()
                    self.fullRefresh = False
                    self.frameActivated = False
                    self.refreshing = False
                except CancelError:
                    # User canceled the refresh
                    self.refreshing = False
        if bosh.inisettings['AutoSizeListColumns']:
            for i in xrange(self.gList.gList.GetColumnCount()):
                self.gList.gList.SetColumnWidth(i, -bosh.inisettings['AutoSizeListColumns'])
        changed = bosh.trackedInfos.refresh()
        if changed:
            # Some tracked files changed, update the ui
            data = self.data.data_sizeCrcDate
            refresh = False
            for file in changed:
                if file.cs.startswith(bosh.dirs['mods'].cs):
                    path = file.relpath(bosh.dirs['mods'])
                else:
                    path = file
                if file.exists():
                    data[path] = (file.size,file.crc,file.mtime)
                    refresh = True
                else:
                    if data.get(path,None) is not None:
                        data.pop(path,None)
                        refresh = True
            if refresh:
                self.data.refreshStatus()
                self.RefreshUIMods()
        self.SetStatusCount()

    def OnShowInfoPage(self,event):
        """A specific info page has been selected."""
        if event.GetId() == self.gNotebook.GetId():
            index = event.GetSelection()
            gPage,initialized = self.infoPages[index]
            if self.detailsItem and not initialized:
                self.RefreshInfoPage(index,self.data[self.detailsItem])
            event.Skip()

    def SetStatusCount(self):
        """Sets status bar count field."""
        active = len([x for x in self.data.itervalues() if x.isActive])
        text = _(u'Packages:')+u' %d/%d' % (active,len(self.data.data))
        statusBar.SetStatusText(text,2)

    def _OnCommentsSplitterSashPosChanged(self, event):
        # ignore spurious events caused by invisible layout adjustments during initialization
        if not self.refreshed: return
        # save new comments text box size
        splitter = event.GetEventObject()
        sashPos = splitter.GetSashPosition() - splitter.GetSize()[1]
        settings['bash.installers.commentsSplitterSashPos'] = sashPos

    def _onMouseCaptureLost(self, event):
        """Handle the onMouseCaptureLost event

        Currently does nothing, but is necessary because without it the first run dialog in OnShow will throw an exception.

        """
        pass

    #--Details view (if it exists)
    def SaveDetails(self):
        """Saves details if they need saving."""
        settings['bash.installers.page'] = self.gNotebook.GetSelection()
        if not self.detailsItem: return
        if self.detailsItem not in self.data: return
        if not self.gComments.IsModified(): return
        installer = self.data[self.detailsItem]
        installer.comments = self.gComments.GetValue()
        self.data.setChanged()

    def RefreshUIMods(self):
        """Refresh UI plus refresh mods state."""
        self.gList.RefreshUI()
        if bosh.modInfos.refresh():
            del bosh.modInfos.mtimesReset[:]
            modList.RefreshUI('ALL')
        if iniList is not None:
            if bosh.iniInfos.refresh():
                #iniList->INIPanel.splitter.left->INIPanel.splitter->INIPanel
                iniList.GetParent().GetParent().GetParent().RefreshUI('ALL')
            else:
                iniList.GetParent().GetParent().GetParent().RefreshUI('TARGETS')

    def RefreshDetails(self,item=None):
        """Refreshes detail view associated with data from item."""
        if item not in self.data: item = None
        self.SaveDetails() #--Save previous details
        self.detailsItem = item
        del self.espms[:]
        if item:
            installer = self.data[item]
            #--Name
            self.gPackage.SetValue(item.s)
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
                info += _(u'Size:')+u' %s KB\n' % formatInteger(max(installer.size,1024)/1024 if installer.size else 0)
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
                info += _(u'Size: %s KB (%s)') % (formatInteger(max(installer.size,1024)/1024 if installer.size else 0),sSolid) + u'\n'
            else:
                info += _(u'Size: Unrecognized')+u'\n'
            info += (_(u'Modified:')+u' %s\n' % formatDate(installer.modified),
                     _(u'Modified:')+u' N/A\n',)[isinstance(installer,bosh.InstallerMarker)]
            info += (_(u'Data CRC:')+u' %08X\n' % installer.crc,
                     _(u'Data CRC:')+u' N/A\n',)[isinstance(installer,bosh.InstallerMarker)]
            info += (_(u'Files:')+u' %s\n' % formatInteger(len(installer.fileSizeCrcs)),
                     _(u'Files:')+u' N/A\n',)[isinstance(installer,bosh.InstallerMarker)]
            info += (_(u'Configured:')+u' %s (%s KB)\n' % (
                formatInteger(nConfigured), formatInteger(max(installer.unSize,1024)/1024 if installer.unSize else 0)),
                     _(u'Configured:')+u' N/A\n',)[isinstance(installer,bosh.InstallerMarker)]
            info += (_(u'  Matched:')+u' %s\n' % formatInteger(nConfigured-nMissing-nMismatched),
                     _(u'  Matched:')+u' N/A\n',)[isinstance(installer,bosh.InstallerMarker)]
            info += (_(u'  Missing:')+u' %s\n' % formatInteger(nMissing),
                     _(u'  Missing:')+u' N/A\n',)[isinstance(installer,bosh.InstallerMarker)]
            info += (_(u'  Conflicts:')+u' %s\n' % formatInteger(nMismatched),
                     _(u'  Conflicts:')+u' N/A\n',)[isinstance(installer,bosh.InstallerMarker)]
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
            gPage.SetValue(self.data.getConflictReport(installer,'OVER'))
        elif pageName == 'gUnderrides':
            gPage.SetValue(self.data.getConflictReport(installer,'UNDER'))
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
        installer.refreshStatus(self.data)

        # Save scroll bar positions, because gList.RefreshUI will
        subScrollPos  = self.gSubList.GetScrollPos(wx.VERTICAL)
        espmScrollPos = self.gEspmList.GetScrollPos(wx.VERTICAL)
        subIndices = self.gSubList.GetSelections()

        self.gList.RefreshUI(self.detailsItem)
        for subIndex in subIndices:
            self.gSubList.SetSelection(subIndex)

        # Reset the scroll bars back to their original position
        subScroll = subScrollPos - self.gSubList.GetScrollPos(wx.VERTICAL)
        self.gSubList.ScrollLines(subScroll)

        espmScroll = espmScrollPos - self.gEspmList.GetScrollPos(wx.VERTICAL)
        self.gEspmList.ScrollLines(espmScroll)

    def OnCheckSubItem(self,event):
        """Handle check/uncheck of item."""
        installer = self.data[self.detailsItem]
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
        InstallersPanel.espmMenu.PopupMenu(self,bashFrame,selected)

    def SubsSelectionMenu(self,event):
        """Handle right click in espm list."""
        x = event.GetX()
        y = event.GetY()
        selected = self.gSubList.HitTest((x,y))
        self.gSubList.SetSelection(selected)
        #--Show/Destroy Menu
        InstallersPanel.subsMenu.PopupMenu(self,bashFrame,selected)

    def OnCheckEspmItem(self,event):
        """Handle check/uncheck of item."""
        installer = self.data[self.detailsItem]
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
class ScreensList(List):
    #--Class Data
    mainMenu = Links() #--Column menu
    itemMenu = Links() #--Single item menu
    _sizeHints = (100, 100)
    keyPrefix = 'bash.screens'
    icons = None # no icons

    def __init__(self, parent, listData):
        #--Columns
        self.colsKey = 'bash.screens.cols'
        #--Parent init
        List.__init__(self, parent, listData, editLabels=True)
        #--Events
        self.list.Bind(wx.EVT_CHAR, self.OnChar)
        self.list.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self.list.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginEditLabel)
        self.list.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEditLabel)

    def OnDClick(self,event):
        """Double click a screenshot"""
        (hitItem,hitFlag) = self.list.HitTest(event.GetPosition())
        if hitItem < 0: return
        item = self.items[hitItem]
        bosh.screensData.dir.join(item).start()

    def OnBeginEditLabel(self,event):
        """Start renaming screenshots"""
        item = self.items[event.GetIndex()]
        # Change the selection to not include the extension
        editbox = self.list.GetEditControl()
        to = len(GPath(event.GetLabel()).sbody)
        editbox.SetSelection(0,to)

    def OnEditLabel(self, event):
        """Renamed a screenshot"""
        if event.IsEditCancelled(): return

        newName = event.GetLabel()

        selected = self.GetSelected()
        rePattern = re.compile(ur'^([^\\/]+?)(\d*)((\.(jpg|jpeg|png|tif|bmp))+)$',re.I|re.U)
        maPattern = rePattern.match(newName)
        if not maPattern:
            balt.showError(self,_(u'Bad extension or file root: ')+newName)
            event.Veto()
            return
        root,numStr = maPattern.groups()[:2]
        #--Rename each screenshot, keeping the old extension
        numLen = len(numStr)
        num = int(numStr or 0)
        screensDir = bosh.screensData.dir
        with balt.BusyCursor():
            newselected = []
            for file in selected:
                newName = GPath(root+numStr+file.ext)
                newselected.append(newName)
                newPath = screensDir.join(newName)
                oldPath = screensDir.join(file)
                if not newPath.exists():
                    oldPath.moveTo(newPath)
                num += 1
                numStr = unicode(num)
                numStr = u'0'*(numLen-len(numStr))+numStr
            bosh.screensData.refresh()
            self.RefreshUI()
            #--Reselected the renamed items
            for file in newselected:
                index = self.list.FindItem(0,file.s)
                if index != -1:
                    self.SelectItemAtIndex(index)
            event.Veto()

    def RefreshUI(self,files='ALL',detail='SAME'):
        """Refreshes UI for specified files."""
        #--Details
        if detail == 'SAME':
            selected = set(self.GetSelected())
        else:
            selected = {detail}
        #--Populate
        if files == 'ALL':
            self.PopulateItems(selected=selected)
        elif isinstance(files,StringTypes):
            self.PopulateItem(files,selected=selected)
        else: #--Iterable
            for file in files:
                self.PopulateItem(file,selected=selected)
        bashFrame.SetStatusCount()

    #--Populate Item
    def PopulateItem(self,itemDex,mode=0,selected=set()):
        #--String name of item?
        if not isinstance(itemDex,int):
            itemDex = self.items.index(itemDex)
        fileName = GPath(self.items[itemDex])
        fileInfo = self.data[fileName]
        cols = self.cols
        for colDex in range(self.numCols):
            col = cols[colDex]
            if col == 'File':
                value = fileName.s
            elif col == 'Modified':
                value = formatDate(fileInfo[1])
            else:
                value = u'-'
            if mode and (colDex == 0):
                self.list.InsertStringItem(itemDex, value)
            else:
                self.list.SetStringItem(itemDex, colDex, value)
        #--Image
        #--Selection State
        self.SelectItemAtIndex(itemDex, fileName in selected)

    #--Sort Items
    def SortItems(self,col=None,reverse=-2):
        (col, reverse) = self.GetSortSettings(col,reverse)
        settings['bash.screens.sort'] = col
        data = self.data
        #--Start with sort by name
        self.items.sort()
        if col == 'File':
            pass #--Done by default
        elif col == 'Modified':
            self.items.sort(key=lambda a: data[a][1])
        else:
            raise BashError(u'Unrecognized sort key: '+col)
        #--Ascending
        if reverse: self.items.reverse()

    #--Events ---------------------------------------------
    def OnChar(self,event):
        """Char event: Activate selected items, select all items"""
        ##F2
        if event.GetKeyCode() == wx.WXK_F2:
            selected = self.GetSelected()
            if len(selected) > 0:
                index = self.list.FindItem(0,selected[0].s)
                if index != -1:
                    self.list.EditLabel(index)
        ##Delete
        elif event.GetKeyCode() in (wx.WXK_DELETE,wx.WXK_NUMPAD_DELETE):
            with balt.BusyCursor():
                self.DeleteSelected(True,event.ShiftDown())
            self.RefreshUI()
        ##Enter
        elif event.GetKeyCode() in (wx.WXK_RETURN,wx.WXK_NUMPAD_ENTER):
            screensDir = bosh.screensData.dir
            for file in self.GetSelected():
                file = screensDir.join(file)
                if file.exists():
                    file.start()
        event.Skip()

    def OnKeyUp(self,event):
        """Char event: Activate selected items, select all items"""
        code = event.GetKeyCode()
        ##Ctrl-A
        if event.CmdDown() and code == ord('A'):
            self.SelectAll()
        # Ctrl+C: Copy file(s) to clipboard
        elif event.CmdDown() and code == ord('C'):
            sel = map(lambda x: bosh.screensData.dir.join(x).s,
                      self.GetSelected())
            copyListToClipboard(sel)
        event.Skip()

    def OnItemSelected(self,event=None):
        fileName = self.items[event.m_itemIndex]
        filePath = bosh.screensData.dir.join(fileName)
        bitmap = Image(filePath.s).GetBitmap() if filePath.exists() else None
        self.picture.SetBitmap(bitmap)

#------------------------------------------------------------------------------
class ScreensPanel(SashPanel):
    """Screenshots tab."""
    def __init__(self,parent):
        """Initialize."""
        sashPos = settings.get('bash.screens.sashPos',120)
        SashPanel.__init__(self,parent,'bash.screens.sashPos',sashPos=sashPos,minimumSize=100)
        left,right = self.left,self.right
        #--Contents
        global screensList
        self.listData = bosh.screensData = bosh.ScreensData()  # TODO(ut): move to InitData()
        screensList = ScreensList(left, self.listData)
        screensList.picture = balt.Picture(right,256,192,background=colors['screens.bkgd.image'])
        self.list = screensList
        #--Layout
        right.SetSizer(hSizer((screensList.picture,1,wx.GROW)))
        left.SetSizer(hSizer((screensList,1,wx.GROW)))
        wx.LayoutAlgorithm().LayoutWindow(self,right)

    def RefreshUIColors(self):
        screensList.picture.SetBackground(colors['screens.bkgd.image'])

    def SetStatusCount(self):
        """Sets status bar count field."""
        text = _(u'Screens:')+u' %d' % (len(screensList.data.data),)
        statusBar.SetStatusText(text,2)

    def OnShow(self):
        """Panel is shown. Update self.data."""
        if bosh.screensData.refresh():
            screensList.RefreshUI()
            #self.Refresh()
        self.SetStatusCount()

#------------------------------------------------------------------------------
class BSAList(List):
    #--Class Data
    mainMenu = Links() #--Column menu
    itemMenu = Links() #--Single item menu
    keyPrefix = 'bash.BSAs'
    icons = None # no icons

    def __init__(self, parent, listData):
        #--Columns
        self.cols = settings['bash.BSAs.cols']
        #--Data/Items
        self.details = None #--Set by panel
        #--Parent init
        List.__init__(self, parent, listData)
        #--Events
        self.list.Bind(wx.EVT_CHAR, self.OnChar)
        #--ScrollPos
        self.list.ScrollLines(settings.get('bash.BSAs.scrollPos',0))
        self.vScrollPos = self.list.GetScrollPos(wx.VERTICAL)

    def RefreshUI(self,files='ALL',detail='SAME'):
        """Refreshes UI for specified files."""
        #--Details
        if detail == 'SAME':
            selected = set(self.GetSelected())
        else:
            selected = {detail}
        #--Populate
        if files == 'ALL':
            self.PopulateItems(selected=selected)
        elif isinstance(files,bolt.Path):
            self.PopulateItem(files,selected=selected)
        else: #--Iterable
            for file in files:
                self.PopulateItem(file,selected=selected)
        BSADetails.SetFile(detail)
        bashFrame.SetStatusCount()

    #--Populate Item
    def PopulateItem(self,itemDex,mode=0,selected=set()):
        #--String name of item?
        if not isinstance(itemDex,int):
            itemDex = self.items.index(itemDex)
        fileName = GPath(self.items[itemDex])
        fileInfo = self.data[fileName]
        cols = self.cols
        for colDex in range(self.numCols):
            col = cols[colDex]
            if col == 'File':
                value = fileName.s
            elif col == 'Modified':
                value = formatDate(fileInfo.mtime)
            elif col == 'Size':
                value = formatInteger(max(fileInfo.size,1024)/1024 if fileInfo.size else 0)+u' KB'
            else:
                value = u'-'
            if mode and (colDex == 0):
                self.list.InsertStringItem(itemDex, value)
            else:
                self.list.SetStringItem(itemDex, colDex, value)
        #--Image
        #status = fileInfo.getStatus()
        # on = fileName.cext == u'.bsa'
        #self.list.SetItemImage(itemDex,self.icons.Get(status,on))
        #--Selection State
        self.SelectItemAtIndex(itemDex, fileName in selected)

    #--Sort Items
    def SortItems(self,col=None,reverse=-2):
        (col, reverse) = self.GetSortSettings(col,reverse)
        settings['bash.BSAs.sort'] = col
        data = self.data
        #--Start with sort by name
        self.items.sort()
        if col == 'File':
            pass #--Done by default
        elif col == 'Modified':
            self.items.sort(key=lambda a: data[a].mtime)
        elif col == 'Size':
            self.items.sort(key=lambda a: data[a].size)
        else:
            raise BashError(u'Unrecognized sort key: '+col)
        #--Ascending
        if reverse: self.items.reverse()

    #--Events ---------------------------------------------
    def OnChar(self,event):
        """Char event: Reordering."""
        if event.GetKeyCode() in (wx.WXK_DELETE,wx.WXK_NUMPAD_DELETE):
            self.DeleteSelected()
        event.Skip()

    #--Event: Left Down
    def OnLeftDown(self,event):
        (hitItem,hitFlag) = self.list.HitTest((event.GetX(),event.GetY()))
        if hitFlag == wx.LIST_HITTEST_ONITEMICON:
            fileName = GPath(self.items[hitItem])
            newEnabled = not self.data.isEnabled(fileName)
            newName = self.data.enable(fileName,newEnabled)
            if newName != fileName: self.RefreshUI()
        #--Pass Event onward
        event.Skip()

    def OnItemSelected(self,event=None):
        BSAName = self.items[event.m_itemIndex]
        self.details.SetFile(BSAName)

#------------------------------------------------------------------------------
class BSADetails(wx.Window):
    """BSAfile details panel."""
    def __init__(self,parent):
        """Initialize."""
        wx.Window.__init__(self, parent, -1, style=wx.TAB_TRAVERSAL)
        readOnlyColour = self.GetBackgroundColour()
        #--Singleton
        global BSADetails
        BSADetails = self
        #--Data
        self.BSAInfo = None
        self.edited = False
        textWidth = 200
        #--File Name
        self.file = textCtrl(self, size=(textWidth, -1),
                             onText=self.OnTextEdit,
                             onKillFocus=self.OnEditFile)
        self.file.SetMaxLength(256)

        #--BSA Info
        self.gInfo = textCtrl(self, size=(textWidth, 100),
                              multiline=True, onText=self.OnInfoEdit)
        self.gInfo.SetMaxLength(2048)
        #--Save/Cancel
        self.save = button(self,id=wx.ID_SAVE,onClick=self.DoSave)
        self.cancel = button(self,id=wx.ID_CANCEL,onClick=self.DoCancel)
        self.save.Disable()
        self.cancel.Disable()
        #--Layout
        sizer = vSizer(
            (staticText(self,_(u'File:')),0,wx.TOP,4),
            (self.file,0,wx.EXPAND|wx.TOP,4),
            (hSizer(
                spacer,
                self.save,
                (self.cancel,0,wx.LEFT,4),
                ),0,wx.EXPAND|wx.TOP,4),
            (self.gInfo,0,wx.TOP,4),
            )
        self.SetSizer(sizer)

    def SetFile(self,fileName='SAME'):
        """Set file to be viewed."""
        #--Reset?
        if fileName == 'SAME':
            if not self.BSAInfo or self.BSAInfo.name not in bosh.BSAInfos:
                fileName = None
            else:
                fileName = self.BSAInfo.name
        #--Null fileName?
        if not fileName:
            BSAInfo = self.BSAInfo = None
            self.fileStr = ''
        #--Valid fileName?
        else:
            BSAInfo = self.BSAInfo = bosh.BSAInfos[fileName]
            #--Remember values for edit checks
            self.fileStr = BSAInfo.name.s
        #--Set Fields
        self.file.SetValue(self.fileStr)
        #--Edit State
        self.edited = 0
        self.save.Disable()
        self.cancel.Disable()
        #--Info Box
        self.gInfo.DiscardEdits()
        if fileName:
            self.gInfo.SetValue(bosh.BSAInfos.table.getItem(fileName,'info',_(u'Notes: ')))
        else:
            self.gInfo.SetValue(_(u'Notes: '))

    def SetEdited(self):
        """Mark as edited."""
        self.edited = True
        self.save.Enable()
        self.cancel.Enable()

    def OnInfoEdit(self,event):
        """Info field was edited."""
        if self.BSAInfo and self.gInfo.IsModified():
            bosh.BSAInfos.table.setItem(self.BSAInfo.name,'info',self.gInfo.GetValue())
        event.Skip()

    def OnTextEdit(self,event):
        """Event: Editing file or save name text."""
        if self.BSAInfo and not self.edited:
            if self.fileStr != self.file.GetValue():
                self.SetEdited()
        event.Skip()

    def OnEditFile(self,event):
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

    def DoSave(self,event):
        """Event: Clicked Save button."""
        BSAInfo = self.BSAInfo
        #--Change Tests
        changeName = (self.fileStr != BSAInfo.name)
        #changeMasters = self.masters.edited
        #--Backup
        BSAInfo.makeBackup()
        prevMTime = BSAInfo.mtime
        #--Change Name?
        if changeName:
            (oldName,newName) = (BSAInfo.name,GPath(self.fileStr.strip()))
            BSAList.items[BSAList.items.index(oldName)] = newName
            bosh.BSAInfos.rename(oldName,newName)
        #--Done
        try:
            bosh.BSAInfos.refreshFile(BSAInfo.name)
            self.SetFile(self.BSAInfo.name)
        except bosh.FileError:
            balt.showError(self,_(u'File corrupted on save!'))
            self.SetFile(None)
        self.SetFile(self.BSAInfo.name)
        BSAList.RefreshUI(BSAInfo.name)

    def DoCancel(self,event):
        """Event: Clicked cancel button."""
        self.SetFile(self.BSAInfo.name)

#------------------------------------------------------------------------------
class BSAPanel(NotebookPanel):
    """BSA info tab."""
    def __init__(self,parent):
        NotebookPanel.__init__(self, parent)
        # global BSAList # was not defined at module level
        self.listData = bosh.BSAInfos
        bsaList = BSAList(self, self.listData)
        self.BSADetails = BSADetails(self)
        BSAList.details = self.BSADetails
        #--Events
        wx.EVT_SIZE(self,self.OnSize)
        #--Layout
        sizer = hSizer(
            (BSAList,1,wx.GROW),
            ((4,-1),0),
            (self.BSADetails,0,wx.EXPAND))
        self.SetSizer(sizer)
        self.BSADetails.Fit()

    def SetStatusCount(self):
        """Sets mod count in last field."""
        text = _(u'BSAs:')+u' %d' % (len(bosh.BSAInfos.data))
        statusBar.SetStatusText(text,2)

    def OnSize(self,event=None):
        wx.Window.Layout(self)
        BSAList.Layout()
        self.BSADetails.Layout()

    def ClosePanel(self):
        super(BSAPanel, self).ClosePanel()
        bosh.BSAInfos.profiles.save()
        settings['bash.BSAs.scrollPos'] = BSAList.vScrollPos

#------------------------------------------------------------------------------
class MessageList(List):
    #--Class Data
    mainMenu = Links() #--Column menu
    itemMenu = Links() #--Single item menu
    _sizeHints = (100, 100)
    keyPrefix = 'bash.messages'
    icons = None # no icons

    def __init__(self, parent, listData):
        #--Columns
        self.colsKey = 'bash.messages.cols'
        #--Other
        self.gText = None
        self.searchResults = None
        #--Parent init
        List.__init__(self, parent, listData)
        #--Events
        self.list.Bind(wx.EVT_KEY_UP, self.OnKeyUp)

    def GetItems(self):
        """Set and return self.items."""
        if self.searchResults is not None:
            self.items = list(self.searchResults)
        else:
            self.items = self.data.keys()
        return self.items

    def RefreshUI(self,files='ALL',detail='SAME'):
        """Refreshes UI for specified files."""
        #--Details
        if detail == 'SAME':
            selected = set(self.GetSelected())
        else:
            selected = {detail}
        #--Populate
        if files == 'ALL':
            self.PopulateItems(selected=selected)
        elif isinstance(files,StringTypes):
            self.PopulateItem(files,selected=selected)
        else: #--Iterable
            for file in files:
                self.PopulateItem(file,selected=selected)
        bashFrame.SetStatusCount()

    #--Populate Item
    def PopulateItem(self,itemDex,mode=0,selected=set()):
        #--String name of item?
        if not isinstance(itemDex,int):
            itemDex = self.items.index(itemDex)
        item = self.items[itemDex]
        subject,author,date = self.data[item][:3]
        cols = self.cols
        for colDex in range(self.numCols):
            col = cols[colDex]
            if col == 'Subject':
                value = subject
            elif col == 'Author':
                value = author
            elif col == 'Date':
                value = formatDate(date)
            else:
                value = u'-'
            if mode and (colDex == 0):
                self.list.InsertStringItem(itemDex, value)
            else:
                self.list.SetStringItem(itemDex, colDex, value)
        #--Image
        #--Selection State
        self.SelectItemAtIndex(itemDex, item in selected)

    #--Sort Items
    def SortItems(self,col=None,reverse=-2):
        (col, reverse) = self.GetSortSettings(col,reverse)
        settings['bash.messages.sort'] = col
        data = self.data
        #--Start with sort by date
        self.items.sort(key=lambda a: data[a][2])
        if col == 'Subject':
            reNoRe = re.compile(u'^Re: *',re.U)
            self.items.sort(key=lambda a: reNoRe.sub(u'',data[a][0]))
        elif col == 'Author':
            self.items.sort(key=lambda a: data[a][1])
        elif col == 'Date':
            pass #--Default sort
        else:
            raise BashError(u'Unrecognized sort key: '+col)
        #--Ascending
        if reverse: self.items.reverse()

    #--Events ---------------------------------------------
    def OnKeyUp(self,event):
        """Char event: Activate selected items, select all items"""
        ##Ctrl-A
        if event.CmdDown() and event.GetKeyCode() == ord('A'):
            self.SelectAll()
        event.Skip()

    def OnItemSelected(self,event=None):
        keys = self.GetSelected()
        path = bosh.dirs['saveBase'].join(u'Messages.html')
        bosh.messages.writeText(path,*keys)
        self.gText.Navigate(path.s,0x2) #--0x2: Clear History

#------------------------------------------------------------------------------
class MessagePanel(SashPanel):
    """Messages tab."""
    def __init__(self,parent):
        """Initialize."""
        import wx.lib.iewin
        sashPos = settings.get('bash.messages.sashPos',120)
        SashPanel.__init__(self,parent,'bash.messages.sashPos',sashPos=sashPos,
                           isVertical=False,minimumSize=100)
        gTop,gBottom = self.left,self.right
        #--Contents
        global gMessageList
        self.listData = bosh.messages = bosh.Messages() # TODO(ut): move to InitData()
        self.listData.refresh() # FIXME(ut): move to InitData()
        gMessageList = MessageList(gTop, self.listData)
        gMessageList.gText = wx.lib.iewin.IEHtmlWindow(gBottom,wx.ID_ANY,style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.list = gMessageList
        #--Search # TODO(ut): move to textCtrl subclass
        gSearchBox = self.gSearchBox = textCtrl(gBottom,style=wx.TE_PROCESS_ENTER)
        gSearchButton = button(gBottom,_(u'Search'),onClick=self.DoSearch)
        gClearButton = button(gBottom,_(u'Clear'),onClick=self.DoClear)
        #--Events
        #--Following line should use EVT_COMMAND_TEXT_ENTER, but that seems broken.
        gSearchBox.Bind(wx.EVT_CHAR,self.OnSearchChar)
        self.Bind(wx.EVT_SIZE,self.OnSize)
        #--Layout
        gTop.SetSizer(hSizer(
            (gMessageList,1,wx.GROW)))
        gBottom.SetSizer(vSizer(
            (gMessageList.gText,1,wx.GROW),
            (hSizer(
                (gSearchBox,1,wx.GROW),
                (gSearchButton,0,wx.LEFT,4),
                (gClearButton,0,wx.LEFT,4),
                ),0,wx.GROW|wx.TOP,4),
            ))
        wx.LayoutAlgorithm().LayoutWindow(self, gTop)
        wx.LayoutAlgorithm().LayoutWindow(self, gBottom)

    def SetStatusCount(self):
        """Sets status bar count field."""
        if gMessageList.searchResults is not None:
            numUsed = len(gMessageList.searchResults)
        else:
            numUsed = len(gMessageList.items)
        text = _(u'PMs:')+u' %d/%d' % (numUsed,len(gMessageList.data.keys()))
        statusBar.SetStatusText(text,2)

    def OnSize(self,event=None):
        wx.LayoutAlgorithm().LayoutWindow(self, self.left)
        wx.LayoutAlgorithm().LayoutWindow(self, self.right)
        if event:
            event.Skip()

    def OnShow(self):
        """Panel is shown. Update self.data."""
        if bosh.messages.refresh():
            gMessageList.RefreshUI()
            #self.Refresh()
        self.SetStatusCount()

    def OnSearchChar(self,event):
        if event.GetKeyCode() in (wx.WXK_RETURN,wx.WXK_NUMPAD_ENTER):
            self.DoSearch(None)
        else:
            event.Skip()

    def DoSearch(self,event):
        """Handle search button."""
        term = self.gSearchBox.GetValue()
        gMessageList.searchResults = gMessageList.data.search(term)
        gMessageList.RefreshUI()

    def DoClear(self,event):
        """Handle clear button."""
        self.gSearchBox.SetValue(u'')
        gMessageList.searchResults = None
        gMessageList.RefreshUI()

    def ClosePanel(self): # (ut) does not call super
        """To be called when containing frame is closing. Use for saving data, scrollpos, etc."""
        if bosh.messages: bosh.messages.save()
        settings['bash.messages.scrollPos'] = gMessageList.vScrollPos

#------------------------------------------------------------------------------
class PeopleList(balt.Tank):
    keyPrefix = 'bash.people'
    mainMenu = Links()
    itemMenu = Links()
    icons = karmacons

    def GetColumnDex(self,column):
        return settingDefaults['bash.people.cols'].index(column)

    def MouseOverItem(self, item):
        """People's Tab: mouse over item is a noop."""
        pass

#------------------------------------------------------------------------------
class PeoplePanel(SashTankPanel):
    """Panel for PeopleTank."""

    def __init__(self,parent):
        """Initialize."""
        global gPeople
        gPeople = self
        data = bosh.PeopleData()
        SashTankPanel.__init__(self,data,parent)
        left,right = self.left,self.right
        #--Contents
        self.gList = PeopleList(left, data, details=self)
        self.gName = roTextCtrl(right, multiline=False)
        self.gText = textCtrl(right, multiline=True)
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
        left.SetSizer(vSizer((self.gList,1,wx.GROW)))
        wx.LayoutAlgorithm().LayoutWindow(self, right)

    def OnShow(self):
        if bosh.inisettings['AutoSizeListColumns']:
            for i in xrange(self.gList.gList.GetColumnCount()): # TODO(ut): self.gList.gList ????
                self.gList.gList.SetColumnWidth(i, -bosh.inisettings['AutoSizeListColumns'])

    def SetStatusCount(self):
        """Sets status bar count field."""
        text = _(u'People:')+u' %d' % len(self.data.data)
        statusBar.SetStatusText(text,2)

    def OnSpin(self,event):
        """Karma spin."""
        if not self.detailsItem: return
        karma = int(self.gKarma.GetValue())
        text = self.data[self.detailsItem][2]
        self.data[self.detailsItem] = (time.time(),karma,text)
        self.gList.UpdateItem(self.gList.GetIndex(self.detailsItem))
        self.data.setChanged()

    #--Details view (if it exists)
    def SaveDetails(self):
        """Saves details if they need saving."""
        if not self.gText.IsModified(): return
        if not self.detailsItem or self.detailsItem not in self.data: return
        mtime,karma,text = self.data[self.detailsItem]
        self.data[self.detailsItem] = (time.time(),karma,self.gText.GetValue().strip())
        self.gList.UpdateItem(self.gList.GetIndex(self.detailsItem))
        self.data.setChanged()

    def RefreshDetails(self,item=None):
        """Refreshes detail view associated with data from item."""
        item = item or self.detailsItem
        if item not in self.data: item = None
        self.SaveDetails()
        if item is None:
            self.gKarma.SetValue(0)
            self.gName.SetValue(u'')
            self.gText.Clear()
        else:
            karma,text = self.data[item][1:3]
            self.gName.SetValue(item)
            self.gKarma.SetValue(karma)
            self.gText.SetValue(text)
        self.detailsItem = item

#------------------------------------------------------------------------------
from .misc_links import Tab_Link # TODO(ut) don't want to import here

class BashNotebook(wx.Notebook, balt.TabDragMixin):
    def __init__(self, parent, id):
        wx.Notebook.__init__(self, parent, id)
        balt.TabDragMixin.__init__(self)
        #--Pages
        # Ensure the 'Mods' tab is always shown
        if 'Mods' not in settings['bash.tabs.order']:
            settings['bash.tabs.order'] = ['Mods']+settings['bash.tabs.order']
        iInstallers = iMods = -1
        for page in settings['bash.tabs.order']:
            enabled = settings['bash.tabs'].get(page,False)
            if not enabled: continue
            className,title,item = tabInfo.get(page,[None,None,None])
            if title is None: continue
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
            except Exception, e:
                if isinstance(e, ImportError):
                    if page == 'PM Archive':
                        deprint(title+_(u' panel disabled due to Import Error (most likely comtypes)'),traceback=True)
                        continue
                if page == 'Mods':
                    deprint(_(u"Fatal error constructing '%s' panel.") % title,traceback=True)
                    raise
                deprint(_(u"Error constructing '%s' panel.") % title,traceback=True)
                if page in settings['bash.tabs']:
                    settings['bash.tabs'][page] = False
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED,self.OnShowPage)
        #--Selection
        pageIndex = max(min(settings['bash.page'],self.GetPageCount()-1),0)
        if settings['bash.installers.fastStart'] and pageIndex == iInstallers:
            pageIndex = iMods
        self.SetSelection(pageIndex)
        #--Dragging
        self.Bind(balt.EVT_NOTEBOOK_DRAGGED, self.OnTabDragged)
        #--Setup Popup menu for Right Click on a Tab
        self.Bind(wx.EVT_CONTEXT_MENU, self.DoTabMenu)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self._onMouseCaptureLost)

    def DoTabMenu(self,event):
        pos = event.GetPosition()
        pos = self.ScreenToClient(pos)
        tabId = self.HitTest(pos)
        if tabId != wx.NOT_FOUND and tabId[0] != wx.NOT_FOUND:
            menu = Links()
            for key in settings['bash.tabs.order']:
                canDisable = bool(key != 'Mods')
                menu.append(Tab_Link(key,canDisable))
            menu.PopupMenu(self,bashFrame,None)
        else:
            event.Skip()

    def OnTabDragged(self, event):
        oldPos = event.fromIndex
        newPos = event.toIndex
        # Update the settings
        removeTitle = self.GetPageText(newPos)
        oldOrder = settings['bash.tabs.order']
        for removeKey in oldOrder:
            if tabInfo[removeKey][1] == removeTitle:
                break
        oldOrder.remove(removeKey)
        if newPos == 0:
            # Moved to the front
            newOrder = [removeKey]+oldOrder
        elif newPos == self.GetPageCount() - 1:
            # Moved to the end
            newOrder = oldOrder+[removeKey]
        else:
            # Moved somewhere in the middle
            beforeTitle = self.GetPageText(newPos+1)
            for beforeKey in oldOrder:
                if tabInfo[beforeKey][1] == beforeTitle:
                    break
            beforeIndex = oldOrder.index(beforeKey)
            newOrder = oldOrder[:beforeIndex]+[removeKey]+oldOrder[beforeIndex:]
        settings['bash.tabs.order'] = newOrder
        event.Skip()

    def OnShowPage(self,event):
        """Call page's OnShow command."""
        if event.GetId() == self.GetId():
            bolt.GPathPurge()
            self.GetPage(event.GetSelection()).OnShow()
            event.Skip()

    def _onMouseCaptureLost(self, event):
        """Handle the onMouseCaptureLost event
        Currently does nothing, but is necessary because without it the first run dialog in OnShow will throw an exception.
        """
        pass

#------------------------------------------------------------------------------
class BashStatusBar(wx.StatusBar):
    #--Class Data
    buttons = Links()
    SettingsMenu = Links()
    obseButton = None
    laaButton = None

    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent, wx.ID_ANY)
        global statusBar
        statusBar = self
        self.SetFieldsCount(3)
        self.UpdateIconSizes()
        #--Bind events
        wx.EVT_SIZE(self,self.OnSize)
        #--Clear text notice
        self.Bind(wx.EVT_TIMER, self.OnTimer)
        #--Setup Drag-n-Drop reordering
        self.dragging = wx.NOT_FOUND
        self.dragStart = 0
        self.moved = False

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
        self.size = settings['bash.statusbar.iconSize']
        self.size += 8
        self.buttons = []
        buttons = BashStatusBar.buttons
        order = settings['bash.statusbar.order']
        orderChanged = False
        hide = settings['bash.statusbar.hide']
        hideChanged = False
        remove = set()
        # Add buttons in order that is saved
        for uid in order:
            link = self.GetLink(uid=uid)
            # Doesn't exist?
            if link is None:
                remove.add(uid)
                continue
            # Hidden?
            if uid in hide: continue
            # Add it
            self._addButton(link)
        for uid in remove:
            order.remove(uid)
        if remove:
            orderChanged = True
        # Add any new buttons
        for link in buttons:
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
        self.SetStatusWidths([self.size*len(self.buttons),-1,130])
        self.SetSize((-1, self.size))
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
                self.SetStatusWidths([self.size*len(self.buttons),-1,130])
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
            thisIndex = order.index(link.uid)
            self._addButton(link)
            button = self.buttons.pop()
            insertBefore = 0
            for i in range(len(self.buttons)):
                otherlink = self.GetLink(index=i)
                indexOther = order.index(otherlink.uid)
                if indexOther > thisIndex:
                    insertBefore = i
                    break
            self.buttons.insert(i,button)
        # Refresh
        self.SetStatusWidths([self.size*len(self.buttons),-1,130])
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

    def HitTest(self,mouseEvent):
        id = mouseEvent.GetId()
        for i,button in enumerate(self.buttons):
            if button.GetId() == id:
                x = mouseEvent.GetPosition()[0]
                delta = x/self.size
                if abs(x) % self.size > self.size:
                    delta += x/abs(x)
                i += delta
                if i < 0: i = 0
                elif i > len(self.buttons): i = len(self.buttons)
                return i
        return wx.NOT_FOUND

    def OnDragStart(self,event):
        self.dragging = self.HitTest(event)
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
            released = self.HitTest(event)
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
            over = self.HitTest(event)
            if over >= len(self.buttons): over -= 1
            if over not in (wx.NOT_FOUND, self.dragging):
                self.moved = True
                # update self.buttons
                button = self.buttons[self.dragging]
                self.buttons.remove(button)
                self.buttons.insert(over,button)
                # update settings
                uid = self.GetLink(button=button).uid
                settings['bash.statusbar.order'].remove(uid)
                settings['bash.statusbar.order'].insert(over,uid)
                settings.setChanged('bash.statusbar.order')
                self.dragging = over
                # Refresh button positions
                self.OnSize()
        event.Skip()

    def OnSize(self,event=None):
        rect = self.GetFieldRect(0)
        (xPos,yPos) = (rect.x+4,rect.y+2)
        for button in self.buttons:
            button.SetPosition((xPos,yPos))
            xPos += self.size
        if event: event.Skip()

    def SetText(self,text=u'',timeout=5):
        """Set's display text as specified. Empty string clears the field."""
        self.SetStatusText(text,1)
        if timeout > 0:
            wx.Timer(self).Start(timeout*1000,wx.TIMER_ONE_SHOT)

    def OnTimer(self,evt):
        """Clears display text as specified. Empty string clears the field."""
        self.SetStatusText(u'',1)

#------------------------------------------------------------------------------
class BashFrame(wx.Frame):
    """Main application frame."""
    # (ut) till I find a better place
    docBrowser = None
    modChecker = None

    def __init__(self, parent=None, pos=balt.defPos, size=(400, 500)):
        #--Singleton
        global bashFrame
        bashFrame = self
        balt.Link.Frame = self
        #--Window
        wx.Frame.__init__(self, parent, wx.ID_ANY, u'Wrye Bash', pos, size)
        minSize = settings['bash.frameSize.min']
        self.SetSizeHints(minSize[0],minSize[1])
        self.SetTitle()
        self.Maximize(settings['bash.frameMax'])
        #--Application Icons
        self.SetIcons(Resources.bashRed)
        #--Status Bar
        self.SetStatusBar(BashStatusBar(self))
        #--Notebook panel
        self.notebook = notebook = BashNotebook(self,wx.ID_ANY)
        #--Events
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.Bind(wx.EVT_ACTIVATE, self.RefreshData)
        #--Data
        self.inRefreshData = False #--Prevent recursion while refreshing.
        self.knownCorrupted = set()
        self.knownInvalidVerions = set()
        self.oblivionIniCorrupted = False
        self.incompleteInstallError = False
        bosh.bsaInfos = bosh.BSAInfos() # TODO(ut): move to InitData()
        #--Layout
        sizer = vSizer((notebook,1,wx.GROW))
        self.SetSizer(sizer)
        if len(bosh.bsaInfos.data) + len(bosh.modInfos.data) >= 325 and not settings['bash.mods.autoGhost']:
            message = _(u"It appears that you have more than 325 mods and bsas in your data directory and auto-ghosting is disabled. This may cause problems in %s; see the readme under auto-ghost for more details and please enable auto-ghost.") % bush.game.displayName
            if len(bosh.bsaInfos.data) + len(bosh.modInfos.data) >= 400:
                message = _(u"It appears that you have more than 400 mods and bsas in your data directory and auto-ghosting is disabled. This will cause problems in %s; see the readme under auto-ghost for more details. ") % bush.game.displayName
            balt.showWarning(bashFrame,message,_(u'Too many mod files.'))

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

    def SetStatusCount(self):
        """Sets the status bar count field. Actual work is done by current panel."""
        if hasattr(self,'notebook'): #--Hack to get around problem with screens tab.
            selection = self.notebook.GetSelection()
            selection = max(min(selection,self.notebook.GetPageCount()),0)
            self.notebook.GetPage(selection).SetStatusCount()

    #--Events ---------------------------------------------
    def RefreshData(self, event=None):
        """Refreshes all data. Can be called manually, but is also triggered by window activation event."""
        def listFiles(files):
            text = u'\n* '
            text += u'\n* '.join(x.s for x in files[:min(15,len(files))])
            if len(files)>10:
                text += '\n+ %d '%(len(files)-15) + _(u'others')
            return text
        #--Ignore deactivation events.
        if event and not event.GetActive() or self.inRefreshData: return
        #--UPDATES-----------------------------------------
        self.inRefreshData = True
        popMods = popSaves = popInis = None
        #--Config helpers
        bosh.configHelpers.refresh()
        #--Check plugins.txt and mods directory...
        modInfosChanged = bosh.modInfos.refresh()
        if modInfosChanged:
            popMods = 'ALL'
        #--Have any mtimes been reset?
        if bosh.modInfos.mtimesReset:
            if bosh.modInfos.mtimesReset[0] == 'PLUGINS':
                if not bosh.inisettings['SkipResetTimeNotifications']:
                    balt.showWarning(self,_(u"An invalid plugin load order has been corrected."))
            else:
                if bosh.modInfos.mtimesReset[0] == 'FAILED':
                    balt.showWarning(self,_(u"It appears that the current user doesn't have permissions for some or all of the files in ")
                                            + bush.game.fsName+u'\\Data.\n' +
                                            _(u"Specifically had permission denied to change the time on:")
                                            + u'\n' + bosh.modInfos.mtimesReset[1].s)
                if not bosh.inisettings['SkipResetTimeNotifications']:
                    message = [u'',_(u'Modified dates have been reset for some mod files')]
                    message.extend(sorted(bosh.modInfos.mtimesReset))
                    ListBoxes.Display(self, _(u'Modified Dates Reset'), _(
                        u'Modified dates have been reset for some mod files.'),
                                      [message], liststyle='list',Cancel=False)
            del bosh.modInfos.mtimesReset[:]
            popMods = 'ALL'
        #--Check savegames directory...
        if bosh.saveInfos.refresh():
            popSaves = 'ALL'
        #--Check INI Tweaks...
        if bosh.iniInfos.refresh():
            popInis = 'ALL'
        #--Ensure BSA timestamps are good - Don't touch this for Skyrim though.
        if bush.game.fsName != 'Skyrim':
            if bosh.inisettings['ResetBSATimestamps']:
                if bosh.bsaInfos.refresh():
                    bosh.bsaInfos.resetMTimes()
        #--Repopulate
        if popMods:
            modList.RefreshUI(popMods) #--Will repop saves too.
        elif popSaves:
            saveList.RefreshUI(popSaves)
        if popInis:
            iniList.RefreshUI(popInis)
        #--Current notebook panel
        if gInstallers: gInstallers.frameActivated = True
        self.notebook.GetPage(self.notebook.GetSelection()).OnShow()
        #--WARNINGS----------------------------------------
        #--Does plugins.txt have any bad or missing files?
        ## Not applicable now with libloadorder - perhaps find a way to simulate this warning
        #if bosh.modInfos.plugins.selectedBad:
        #    message = [u'',_(u'Missing files have been removed from load list:')]
        #    message.extend(sorted(bosh.modInfos.plugins.selectedBad))
        #    dialog = ListBoxes(self,_(u'Warning: Load List Sanitized'),
        #             _(u'Missing files have been removed from load list:'),
        #             [message],liststyle='list',Cancel=False)
        #    dialog.ShowModal()
        #    dialog.Destroy()
        #    del bosh.modInfos.plugins.selectedBad[:]
        #    bosh.modInfos.plugins.save()
        #--Was load list too long? or bad filenames?
        ## Net to recode this with libloadorder as well
        #if bosh.modInfos.plugins.selectedExtra:## or bosh.modInfos.activeBad:
        #    message = []
        #    ## Disable this message for now, until we're done testing if
        #    ## we can get the game to load these files
        #    #if bosh.modInfos.activeBad:
        #    #    msg = [u'Incompatible names:',u'Incompatible file names deactivated:']
        #    #    msg.extend(bosh.modInfos.bad_names)
        #    #    bosh.modInfos.activeBad = set()
        #    #    message.append(msg)
        #    if bosh.modInfos.plugins.selectedExtra:
        #        msg = [u'Too many files:',_(u'Load list is overloaded.  Some files have been deactivated:')]
        #        msg.extend(sorted(bosh.modInfos.plugins.selectedExtra))
        #        message.append(msg)
        #    dialog = ListBoxes(self,_(u'Warning: Load List Sanitized'),
        #             _(u'Files have been removed from load list:'),
        #             message,liststyle='list',Cancel=False)
        #    dialog.ShowModal()
        #    dialog.Destroy()
        #    del bosh.modInfos.plugins.selectedExtra[:]
        #    bosh.modInfos.plugins.save()
        #--Any new corrupted files?
        message = []
        corruptMods = set(bosh.modInfos.corrupted.keys())
        if not corruptMods <= self.knownCorrupted:
            m = [_(u'Corrupted Mods'),_(u'The following mod files have corrupted headers: ')]
            m.extend(sorted(corruptMods))
            message.append(m)
            self.knownCorrupted |= corruptMods
        corruptSaves = set(bosh.saveInfos.corrupted.keys())
        if not corruptSaves <= self.knownCorrupted:
            m = [_(u'Corrupted Saves'),_(u'The following save files have corrupted headers: ')]
            m.extend(sorted(corruptSaves))
            message.append(m)
            self.knownCorrupted |= corruptSaves
        invalidVersions = set([x for x in bosh.modInfos.data if round(bosh.modInfos[x].header.version,6) not in bush.game.esp.validHeaderVersions])
        if not invalidVersions <= self.knownInvalidVerions:
            m = [_(u'Unrecognized Versions'),_(u'The following mods have unrecognized TES4 header versions: ')]
            m.extend(sorted(invalidVersions))
            message.append(m)
            self.knownInvalidVerions |= invalidVersions
        if bosh.modInfos.new_missing_strings:
            m = [_(u'Missing String Localization files:'),_(u'This will cause CTDs if activated.')]
            m.extend(sorted(bosh.modInfos.missing_strings))
            message.append(m)
            bosh.modInfos.new_missing_strings.clear()
        if message:
            ListBoxes.Display(self, _(u'Warning: Corrupt/Unrecognized Files'),
                      _(u'Some files have corrupted headers or TES4 header '
                        u'versions:'), message, liststyle='list', Cancel=False)
        #--Corrupt Oblivion.ini
        if self.oblivionIniCorrupted != bosh.oblivionIni.isCorrupted:
            self.oblivionIniCorrupted = bosh.oblivionIni.isCorrupted
            if self.oblivionIniCorrupted:
                message = _(u'Your %s should begin with a section header (e.g. "[General]"), but does not. You should edit the file to correct this.') % bush.game.iniFiles[0]
                balt.showWarning(self,fill(message))
        #--Any Y2038 Resets?
        if bolt.Path.mtimeResets:
            message = [u'',_(u"Bash cannot handle dates greater than January 19, 2038. Accordingly, the dates for the following files have been reset to an earlier date: ")]
            message.extend(sorted(bolt.Path.mtimeResets))
            with ListBoxes(self, _(u'Warning: Dates Reset'), _(
                    u'Modified dates have been reset to an earlier date for  '
                    u'these files'), [message], liststyle='list',
                           Cancel=False) as dialog:
                dialog.ShowModal()
            del bolt.Path.mtimeResets[:]
        #--OBMM Warning?
        if settings['bosh.modInfos.obmmWarn'] == 1:
            settings['bosh.modInfos.obmmWarn'] = 2
            message = (_(u'Turn Lock Load Order Off?')
                       + u'\n\n' +
                       _(u'Lock Load Order is a feature which resets load order to a previously memorized state.  While this feature is good for maintaining your load order, it will also undo any load order changes that you have made in OBMM.')
                       )
            lockTimes = not balt.askYes(self,message,_(u'Lock Load Order'))
            bosh.modInfos.lockTimes = settings['bosh.modInfos.resetMTimes'] = lockTimes
            if lockTimes:
                bosh.modInfos.resetMTimes()
            else:
                bosh.modInfos.mtimes.clear()
            message = _(u"Lock Load Order is now %s.  To change it in the future, right click on the main list header on the Mods tab and select 'Lock Load Order'.")
            balt.showOk(self,message % ((_(u'off'),_(u'on'))[lockTimes],),_(u'Lock Load Order'))
        #--Missing docs directory?
        testFile = GPath(bosh.dirs['mopy']).join(u'Docs',u'wtxt_teal.css')
        if not self.incompleteInstallError and not testFile.exists():
            self.incompleteInstallError = True
            message = (_(u'Installation appears incomplete.  Please re-unzip bash to game directory so that ALL files are installed.')
                       + u'\n\n' +
                       _(u'Correct installation will create %s\\Mopy and %s\\Data\\Docs directories.')
                       % (bush.game.fsName,bush.game.fsName)
                       )
            balt.showWarning(self,message,_(u'Incomplete Installation'))
        #--Merge info
        oldMergeable = set(bosh.modInfos.mergeable)
        scanList = bosh.modInfos.refreshMergeable()
        difMergeable = oldMergeable ^ bosh.modInfos.mergeable
        if scanList:
            with balt.Progress(_(u'Mark Mergeable')+u' '*30) as progress:
                progress.setFull(len(scanList))
                bosh.modInfos.rescanMergeable(scanList,progress)
        if scanList or difMergeable:
            modList.RefreshUI(scanList + list(difMergeable))
        #--Done (end recursion blocker)
        self.inRefreshData = False

    def OnCloseWindow(self, event):
        """Handle Close event. Save application data."""
        try:
            self.SaveSettings()
        except: # raise # TODO(ut): this has swallowed exceptions since forever
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
            settings['bash.framePos'] = self.GetPositionTuple()
            settings['bash.frameSize'] = self.GetSizeTuple()
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
        modNames = set(bosh.modInfos.data.keys())
        modNames.update(bosh.modInfos.table.data.keys())
        renames = bosh.settings.getChanged('bash.mods.renames')
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
            goodRoots = set(path.root for path in fileInfos.data.keys())
            backupDir = fileInfos.bashDir.join(u'Backups')
            if not backupDir.isdir(): continue
            for name in backupDir.list():
                path = backupDir.join(name)
                if name.root not in goodRoots and path.isfile():
                    path.remove()

#------------------------------------------------------------------------------
def GetBashVersion():
    return bass.AppVersion

    #--Version from readme
    #readme = bosh.dirs['mopy'].join(u'Wrye Bash.txt')
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
        splashScreenBitmap = wx.Image(name = bosh.dirs['images'].join(u'wryesplash.png').s).ConvertToBitmap()
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
        if bosh.inisettings['EnableSplashScreen']:
            if bosh.dirs['images'].join(u'wryesplash.png').exists():
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
        frame = BashFrame( # basher.bashFrame global set here
             pos=settings['bash.framePos'],
             size=settings['bash.frameSize'])
        progress.Destroy()
        if splashScreen:
            splashScreen.Destroy()
        self.SetTopWindow(frame)
        frame.Show()
        balt.ensureDisplayed(frame)
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
        bosh.gameInis = [bosh.OblivionIni(x) for x in bush.game.iniFiles]
        bosh.oblivionIni = bosh.gameInis[0]
        bosh.trackedInfos = bosh.TrackedFileInfos(bosh.INIInfo)
        bosh.modInfos = bosh.ModInfos()
        bosh.modInfos.refresh()
        progress.Update(30,_(u'Initializing SaveInfos'))
        bosh.saveInfos = bosh.SaveInfos()
        bosh.saveInfos.refresh()
        progress.Update(40,_(u'Initializing IniInfos'))
        bosh.iniInfos = bosh.INIInfos()
        bosh.iniInfos.refresh()
        #--Patch check
        if bush.game.esp.canBash:
            if not bosh.modInfos.bashed_patches and bosh.inisettings['EnsurePatchExists']:
                progress.Update(68,_(u'Generating Blank Bashed Patch'))
                bosh.PatchFile.generateNextBashedPatch()

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
        settings['bash.version'] = 43
        if settings['bash.version'] != GetBashVersion():
            settings['bash.version'] = GetBashVersion()
            # rescan mergeability
            if not CBash: #Because it is rescanned on showing of patch dialogue anyways so that would double up in CBash Mode.
                nullProgress = bolt.Progress()
                bosh.modInfos.rescanMergeable(bosh.modInfos.data,nullProgress)
        elif settings['bash.CBashEnabled'] != bool(CBash) and not CBash:
            nullProgress = bolt.Progress()
            bosh.modInfos.rescanMergeable(bosh.modInfos.data,nullProgress)
        settings['bash.CBashEnabled'] = bool(CBash)

# Initialization --------------------------------------------------------------
from .gui_patchers import initPatchers
def InitSettings(): # this must run first !
    """Initializes settings dictionary for bosh and basher."""
    bosh.initSettings()
    global settings
    balt._settings = bosh.settings
    balt.sizes = bosh.settings.getChanged('bash.window.sizes',{})
    settings = bosh.settings
    settings.loadDefaults(settingDefaults) # called in bosh.initSettings() also
    # with bosh.settingDefaults passed in
    #--Wrye Balt
    settings['balt.WryeLog.temp'] = bosh.dirs['saveBase'].join(u'WryeLogTemp.html')
    settings['balt.WryeLog.cssDir'] = bosh.dirs['mopy'].join(u'Docs')
    #--StandAlone version?
    settings['bash.standalone'] = hasattr(sys,'frozen')
    initPatchers()

def InitImages():
    """Initialize color and image collections."""
    #--Colors
    for key,value in settings['bash.colors'].iteritems():
        colors[key] = value

    #--Standard
    images['save.on'] = Image(GPath(bosh.dirs['images'].join(u'save_on.png')),PNG)
    images['save.off'] = Image(GPath(bosh.dirs['images'].join(u'save_off.png')),PNG)
    #--Misc
    #images['oblivion'] = Image(GPath(bosh.dirs['images'].join(u'oblivion.png')),png)
    images['help.16'] = Image(GPath(bosh.dirs['images'].join(u'help16.png')))
    images['help.24'] = Image(GPath(bosh.dirs['images'].join(u'help24.png')))
    images['help.32'] = Image(GPath(bosh.dirs['images'].join(u'help32.png')))
    #--ColorChecks
    images['checkbox.red.x'] = Image(GPath(bosh.dirs['images'].join(u'checkbox_red_x.png')),PNG)
    images['checkbox.red.x.16'] = Image(GPath(bosh.dirs['images'].join(u'checkbox_red_x.png')),PNG)
    images['checkbox.red.x.24'] = Image(GPath(bosh.dirs['images'].join(u'checkbox_red_x_24.png')),PNG)
    images['checkbox.red.x.32'] = Image(GPath(bosh.dirs['images'].join(u'checkbox_red_x_32.png')),PNG)
    images['checkbox.red.off.16'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_red_off.png')),PNG))
    images['checkbox.red.off.24'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_red_off_24.png')),PNG))
    images['checkbox.red.off.32'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_red_off_32.png')),PNG))

    images['checkbox.green.on.16'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_green_on.png')),PNG))
    images['checkbox.green.off.16'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_green_off.png')),PNG))
    images['checkbox.green.on.24'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_green_on_24.png')),PNG))
    images['checkbox.green.off.24'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_green_off_24.png')),PNG))
    images['checkbox.green.on.32'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_green_on_32.png')),PNG))
    images['checkbox.green.off.32'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_green_off_32.png')),PNG))

    images['checkbox.blue.on.16'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_blue_on.png')),PNG))
    images['checkbox.blue.on.24'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_blue_on_24.png')),PNG))
    images['checkbox.blue.on.32'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_blue_on_32.png')),PNG))
    images['checkbox.blue.off.16'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_blue_off.png')),PNG))
    images['checkbox.blue.off.24'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_blue_off_24.png')),PNG))
    images['checkbox.blue.off.32'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_blue_off_32.png')),PNG))
    #--Bash
    images['bash.16'] = Image(GPath(bosh.dirs['images'].join(u'bash_16.png')),PNG)
    images['bash.24'] = Image(GPath(bosh.dirs['images'].join(u'bash_24.png')),PNG)
    images['bash.32'] = Image(GPath(bosh.dirs['images'].join(u'bash_32.png')),PNG)
    images['bash.16.blue'] = Image(GPath(bosh.dirs['images'].join(u'bash_16_blue.png')),PNG)
    images['bash.24.blue'] = Image(GPath(bosh.dirs['images'].join(u'bash_24_blue.png')),PNG)
    images['bash.32.blue'] = Image(GPath(bosh.dirs['images'].join(u'bash_32_blue.png')),PNG)
    #--Bash Patch Dialogue
    images['monkey.16'] = Image(GPath(bosh.dirs['images'].join(u'wryemonkey16.jpg')),JPEG)
    #images['monkey.32'] = Image(GPath(bosh.dirs['images'].join(u'wryemonkey32.jpg')),JPEG)
    #--DocBrowser
    images['doc.16'] = Image(GPath(bosh.dirs['images'].join(u'DocBrowser16.png')),PNG)
    images['doc.24'] = Image(GPath(bosh.dirs['images'].join(u'DocBrowser24.png')),PNG)
    images['doc.32'] = Image(GPath(bosh.dirs['images'].join(u'DocBrowser32.png')),PNG)
    #--UAC icons
    #images['uac.small'] = Image(GPath(balt.getUACIcon('small')),ICO)
    #images['uac.large'] = Image(GPath(balt.getUACIcon('large')),ICO)
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
