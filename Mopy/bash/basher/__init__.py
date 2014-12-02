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

"""This module provides the GUI interface for Wrye Bash. (However, the Wrye
Bash application is actually launched by the bash module.)

The module is generally organized starting with lower level elements, working
up to higher level elements (up the BashApp). This is followed by definition
of menus and buttons classes, and finally by several initialization functions.

Non-GUI objects and functions are provided by the bosh module. Of those, the
primary objects used are the plugins, modInfos and saveInfos singletons -- each
representing external data structures (the plugins.txt file and the Data and
Saves directories respectively). Persistent storage for the app is primarily
provided through the settings singleton (however the modInfos singleton also
has its own data store)."""

# Imports ---------------------------------------------------------------------
#--Localization
#..Handled by bosh, so import that.
from .. import bush, bosh, bolt, loot, barb, bass, bweb, patcher
from ..bosh import formatInteger,formatDate
from ..bolt import BoltError, AbstractError, ArgumentError, StateError, \
    UncodedError, CancelError, SkipError
from ..bolt import LString, GPath, SubProgress, deprint, sio
from ..cint import *

startupinfo = bolt.startupinfo

#--Python
import StringIO
import copy
import datetime
import os
import re
import string
import sys
import time
from types import *
from operator import attrgetter

#--wxPython
import wx
import wx.gizmos

#--Balt
from .. import balt
from ..balt import tooltip, fill, bell
from ..balt import bitmapButton, button, toggleButton, checkBox, staticText, spinCtrl, textCtrl
from ..balt import spacer, hSizer, vSizer, hsbSizer
from ..balt import colors, images, Image
from ..balt import Links, Link, SeparatorLink, MenuLink
from ..balt import ListCtrl

# BAIN wizard support, requires PyWin32, so import will fail if it's not installed
try:
    from .. import belt
    bEnableWizard = True
except ImportError:
    bEnableWizard = False
    deprint(_(u"Error initializing installer wizards:"),traceback=True)

# If comtypes is not installed, he IE ActiveX control cannot be imported
try:
    import wx.lib.iewin
    bHaveComTypes = True
except ImportError:
    bHaveComTypes = False
    deprint(_(u'Comtypes is missing, features utilizing HTML will be disabled'))


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
docBrowser = None
modChecker = None

# Settings --------------------------------------------------------------------
settings = None

# Constants --------------------------------------------------------------------
from .constants import colorInfo, tabInfo, settingDefaults, karmacons, \
    installercons, PNG, JPEG, ICO, BMP, TIF, ID_TAGS

# Exceptions ------------------------------------------------------------------
class BashError(BoltError): pass

# Gui Ids ---------------------------------------------------------------------
#------------------------------------------------------------------------------
# Constants
#--Indexed
wxListAligns = [wx.LIST_FORMAT_LEFT, wx.LIST_FORMAT_RIGHT, wx.LIST_FORMAT_CENTRE]
splitterStyle = wx.BORDER_NONE|wx.SP_LIVE_UPDATE#|wx.FULL_REPAINT_ON_RESIZE - doesn't seem to need this to work properly

#--Generic
ID_RENAME = 6000
ID_SET    = 6001
ID_SELECT = 6002
ID_BROWSER = 6003
#ID_NOTES  = 6004
ID_EDIT   = 6005 # TODO(ut): only this is used
ID_BACK   = 6006
ID_NEXT   = 6007

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

# Windows ---------------------------------------------------------------------
#------------------------------------------------------------------------------
class NotebookPanel(wx.Panel):
    """Parent class for notebook panels."""

    def RefreshUIColors(self):
        """Called to signal that UI color settings have changed."""
        pass

    def SetStatusCount(self):
        """Sets status bar count field."""
        statusBar.SetStatusText(u'',2)

    def OnShow(self):
        """To be called when particular panel is changed to and/or shown for first time.
        Default version does nothing, but derived versions might update data."""
        if bosh.inisettings['AutoSizeListColumns']:
            for i in xrange(self.list.list.GetColumnCount()):
                self.list.list.SetColumnWidth(i, -bosh.inisettings['AutoSizeListColumns'])
        self.SetStatusCount()

    def OnCloseWindow(self):
        """To be called when containing frame is closing. Use for saving data, scrollpos, etc."""
        pass

#------------------------------------------------------------------------------
class SashPanel(NotebookPanel):
    """Subclass of Notebook Panel, designed for two pane panel."""
    def __init__(self,parent,sashPosKey=None,sashGravity=0.5,sashPos=0,mode=wx.VERTICAL,minimumSize=50,style=splitterStyle):
        """Initialize."""
        NotebookPanel.__init__(self, parent, wx.ID_ANY)
        splitter = wx.gizmos.ThinSplitterWindow(self, wx.ID_ANY, style=style)
        self.left = wx.Panel(splitter)
        self.right = wx.Panel(splitter)
        if mode == wx.VERTICAL:
            splitter.SplitVertically(self.left, self.right)
        else:
            splitter.SplitHorizontally(self.left, self.right)
        splitter.SetSashGravity(sashGravity)
        sashPos = settings.get(sashPosKey, 0) or sashPos or -1
        splitter.SetSashPosition(sashPos)
        if sashPosKey is not None:
            self.sashPosKey = sashPosKey
        splitter.Bind(wx.EVT_SPLITTER_DCLICK, self.OnDClick)
        splitter.SetMinimumPaneSize(minimumSize)
        sizer = vSizer(
            (splitter,1,wx.EXPAND),
            )
        self.SetSizer(sizer)

    def OnDClick(self, event):
        """Don't allow unsplitting"""
        event.Veto()

    def OnCloseWindow(self):
        splitter = self.right.GetParent()
        if hasattr(self, 'sashPosKey'):
            settings[self.sashPosKey] = splitter.GetSashPosition()

class SashTankPanel(SashPanel):
    def __init__(self,data,parent):
        sashPos = data.getParam('sashPos',200)
        minimumSize = 80
        self.data = data
        self.detailsItem = None
        super(SashTankPanel,self).__init__(parent,sashPos=sashPos,minimumSize=minimumSize)

    def OnCloseWindow(self):
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
class List(wx.Panel):
    def __init__(self,parent,id=wx.ID_ANY,ctrlStyle=wx.LC_REPORT|wx.LC_SINGLE_SEL,
                 dndFiles=False,dndList=False,dndColumns=[]):
        wx.Panel.__init__(self,parent,id, style=wx.WANTS_CHARS)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        self.SetSizeHints(-1,50)
        self.dndColumns = dndColumns
        #--ListCtrl
        listId = self.listId = wx.NewId()
        self.list = ListCtrl(self, listId, style=ctrlStyle,
                             dndFiles=dndFiles, dndList=dndList,
                             fnDndAllow=self.dndAllow,
                             fnDropFiles=self.OnDropFiles,
                             fnDropIndexes=self.OnDropIndexes)
        self.checkboxes = colorChecks
        self.mouseItem = None
        self.mouseTexts = {}
        self.mouseTextPrev = u''
        self.vScrollPos = 0
        #--Columns
        self.PopulateColumns()
        #--Items
        self.sortDirty = 0
        self.PopulateItems()
        #--Events
        wx.EVT_SIZE(self, self.OnSize)
        #--Events: Items
        self.hitIcon = 0
        wx.EVT_LEFT_DOWN(self.list,self.OnLeftDown)
        self.list.Bind(wx.EVT_CONTEXT_MENU, self.DoItemMenu)
        #--Events: Columns
        wx.EVT_LIST_COL_CLICK(self, listId, self.DoItemSort)
        wx.EVT_LIST_COL_RIGHT_CLICK(self, listId, self.DoColumnMenu)
        self.checkcol = []
        wx.EVT_LIST_COL_END_DRAG(self,listId, self.OnColumnResize)
        wx.EVT_UPDATE_UI(self, listId, self.onUpdateUI)
        #--Mouse movement
        self.list.Bind(wx.EVT_MOTION,self.OnMouse)
        self.list.Bind(wx.EVT_LEAVE_WINDOW,self.OnMouse)
        self.list.Bind(wx.EVT_SCROLLWIN,self.OnScroll)

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

    #--Drag and Drop---------------------------------------
    def dndAllow(self):
        col = self.sort
        return col in self.dndColumns
    def OnDropFiles(self, x, y, filenames): raise AbstractError
    def OnDropIndexes(self, indexes, newPos): raise AbstractError

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

    def ClearSelected(self):
        for itemDex in xrange(self.list.GetItemCount()):
            self.list.SetItemState(itemDex, 0, wx.LIST_STATE_SELECTED)

    def SelectAll(self):
        for itemDex in range(self.list.GetItemCount()):
            self.list.SetItemState(itemDex,wx.LIST_STATE_SELECTED,wx.LIST_STATE_SELECTED)

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

    def checkUncheckMod(self, *mods):
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

    def OnMouse(self,event):
        """Check mouse motion to detect right click event."""
        if event.Moving():
            (mouseItem,mouseHitFlag) = self.list.HitTest(event.GetPosition())
            if mouseItem != self.mouseItem:
                self.mouseItem = mouseItem
                self.MouseEnteredItem(mouseItem)
        elif event.Leaving() and self.mouseItem is not None:
            self.mouseItem = None
            self.MouseEnteredItem(None)
        event.Skip()

    def MouseEnteredItem(self,item):
        """Handle mouse entered item by showing tip or similar."""
        text = self.mouseTexts.get(item) or ''
        if text != self.mouseTextPrev:
            statusBar.SetStatusText(text,1)
            self.mouseTextPrev = text

    #--Column Menu
    def DoColumnMenu(self,event,column = None):
        if not self.mainMenu: return
        #--Build Menu
        if column is None: column = event.GetColumn()
        #--Show/Destroy Menu
        self.mainMenu.PopupMenu(self,bashFrame,column)

    #--Column Resize
    def OnColumnResize(self,event):
        """Due to a nastyness that ListCtrl.GetColumnWidth(col) returns
        the old size before this event completes just save what
        column is being edited and process after in OnUpdateUI()"""
        self.checkcol = [event.GetColumn()]
        event.Skip()

    #--Item Sort
    def DoItemSort(self, event):
        self.PopulateItems(self.cols[event.GetColumn()],-1)

    #--Item Menu
    def DoItemMenu(self,event):
        selected = self.GetSelected()
        if not selected:
            self.DoColumnMenu(event,0)
            return
        #--Show/Destroy Menu
        self.itemMenu.PopupMenu(self,bashFrame,selected)

    #--Size Change
    def OnSize(self, event):
        size = self.GetClientSizeTuple()
        #print self,size
        self.list.SetSize(size)

    #--Event: Left Down
    def OnLeftDown(self,event):
        #self.hitTest = self.list.HitTest((event.GetX(),event.GetY()))
        #self.pos[0] = event.GetX()
        #deprint(event.GetX())
        event.Skip()

    def OnScroll(self,event):
        """Event: List was scrolled. Save so can be accessed later."""
        if event.GetOrientation() == wx.VERTICAL:
            self.vScrollPos = event.GetPosition()
        event.Skip()

#------------------------------------------------------------------------------
class MasterList(List):
    mainMenu = Links()
    itemMenu = Links()

    def __init__(self,parent,fileInfo,setEditedFn):
        #--Columns
        self.cols = settings['bash.masters.cols']
        self.colNames = settings['bash.colNames']
        self.colWidths = settings['bash.masters.colWidths']
        self.colAligns = settings['bash.masters.colAligns']
        self.colReverse = settings['bash.masters.colReverse'].copy()
        #--Data/Items
        self.edited = False
        self.fileInfo = fileInfo
        self.prevId = -1
        self.data = {}  #--masterInfo = self.data[item], where item is id number
        self.items = [] #--Item numbers in display order.
        self.fileOrderItems = []
        self.loadOrderNames = []
        self.sort = settings['bash.masters.sort']
        self.esmsFirst = settings['bash.masters.esmsFirst']
        self.selectedFirst = settings['bash.masters.selectedFirst']
        #--Links
        self.mainMenu = MasterList.mainMenu
        self.itemMenu = MasterList.itemMenu
        #--Parent init
        List.__init__(self,parent,wx.ID_ANY,ctrlStyle=(wx.LC_REPORT|wx.LC_SINGLE_SEL|wx.LC_EDIT_LABELS))
        wx.EVT_LIST_END_LABEL_EDIT(self,self.listId,self.OnLabelEdited)
        #--Image List
        checkboxesIL = self.checkboxes.GetImageList()
        self.list.SetImageList(checkboxesIL,wx.IMAGE_LIST_SMALL)
        self._setEditedFn = setEditedFn

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
        self.list.SetItemImage(itemDex,self.checkboxes.Get(status,oninc))
        #--Selection State
        if masterName in selected:
            self.list.SetItemState(itemDex,wx.LIST_STATE_SELECTED,wx.LIST_STATE_SELECTED)
        else:
            self.list.SetItemState(itemDex,0,wx.LIST_STATE_SELECTED)

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
    def DoItemSort(self, event):
        pass #--Don't do column head sort.

    #--Column Menu
    def DoColumnMenu(self,event,column=None):
        if not self.fileInfo: return
        List.DoColumnMenu(self,event,column)

    #--Item Menu
    def DoItemMenu(self,event):
        if not self.edited:
            self.OnLeftDown(event)
        else:
            List.DoItemMenu(self,event)

    #--Column Resize
    def OnColumnResize(self,event):
        super(MasterList,self).OnColumnResize(event)
        settings.setChanged('bash.masters.colWidths')

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

    def __init__(self,parent):
        #--Columns
        self.colsKey = 'bash.ini.cols'
        self.colAligns = settings['bash.ini.colAligns']
        self.colNames = settings['bash.colNames']
        self.colReverse = settings.getChanged('bash.ini.colReverse')
        self.colWidths = settings['bash.ini.colWidths']
        self.sortValid = settings['bash.ini.sortValid']
        #--Data/Items
        self.data = bosh.iniInfos
        self.sort = settings['bash.ini.sort']
        #--Links
        self.mainMenu = INIList.mainMenu
        self.itemMenu = INIList.itemMenu
        #--Parent init
        List.__init__(self,parent,wx.ID_ANY,ctrlStyle=wx.LC_REPORT)
        #--Events
        self.list.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        #--Image List
        checkboxesIL = colorChecks.GetImageList()
        self.list.SetImageList(checkboxesIL,wx.IMAGE_LIST_SMALL)
        #--ScrollPos

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
        self.list.SetItemImage(itemDex,self.checkboxes.Get(icon,checkMark))
        #--Font/BG Color
        item = self.list.GetItem(itemDex)
        item.SetTextColour(colors['default.text'])
        if status < 0:
            item.SetBackgroundColour(colors['ini.bkgd.invalid'])
        else:
            item.SetBackgroundColour(colors['default.bkgd'])
        self.list.SetItem(item)
        if fileName in selected:
            self.list.SetItemState(itemDex,wx.LIST_STATE_SELECTED,wx.LIST_STATE_SELECTED)
        else:
            self.list.SetItemState(itemDex,0,wx.LIST_STATE_SELECTED)

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

    def OnColumnResize(self,event):
        """Column resize: Stored modified column widths."""
        super(INIList,self).OnColumnResize(event)
        settings.setChanged('bash.ini.colWidths')

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

    def __init__(self,parent):
        #--Columns
        self.colsKey = 'bash.mods.cols'
        self.colAligns = settings['bash.mods.colAligns']
        self.colNames = settings['bash.colNames']
        self.colReverse = settings.getChanged('bash.mods.colReverse')
        self.colWidths = settings['bash.mods.colWidths']
        #--Data/Items
        self.data = data = bosh.modInfos
        self.details = None #--Set by panel
        self.sort = settings['bash.mods.sort']
        self.esmsFirst = settings['bash.mods.esmsFirst']
        self.selectedFirst = settings['bash.mods.selectedFirst']
        #--Links
        self.mainMenu = ModList.mainMenu
        self.itemMenu = ModList.itemMenu
        #--Parent init
        List.__init__(self,parent,wx.ID_ANY,ctrlStyle=wx.LC_REPORT, dndList=True, dndColumns=['Load Order'])#|wx.SUNKEN_BORDER))
        #--Image List
        checkboxesIL = colorChecks.GetImageList()
        self.sm_up = checkboxesIL.Add(balt.SmallUpArrow.GetBitmap())
        self.sm_dn = checkboxesIL.Add(balt.SmallDnArrow.GetBitmap())
        self.list.SetImageList(checkboxesIL,wx.IMAGE_LIST_SMALL)
        #--Events
        wx.EVT_LIST_ITEM_SELECTED(self,self.listId,self.OnItemSelected)
        self.list.Bind(wx.EVT_CHAR, self.OnChar)
        self.list.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)
        self.list.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        #--ScrollPos
        self.list.ScrollLines(settings.get('bash.mods.scrollPos',0))
        self.vScrollPos = self.list.GetScrollPos(wx.VERTICAL)

    #-- Drag and Drop-----------------------------------------------------
    def OnDropIndexes(self, indexes, newIndex):
        # Make sure we're not auto-sorting
        for thisFile in self.GetSelected():
            if GPath(thisFile) in bosh.modInfos.autoSorted:
                balt.showError(self,_(u"Auto-ordered files cannot be manually moved."))
                return
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
        self.list.SetItemImage(itemDex,self.checkboxes.Get(status,checkMark))
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
        if fileName in selected:
            self.list.SetItemState(itemDex,wx.LIST_STATE_SELECTED,wx.LIST_STATE_SELECTED)
        else:
            self.list.SetItemState(itemDex,0,wx.LIST_STATE_SELECTED)
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
            if reverse: self.list.SetColumnImage(self.colDict[col], self.sm_up)
            else: self.list.SetColumnImage(self.colDict[col], self.sm_dn)
        except: pass

    #--Events ---------------------------------------------
    def OnDoubleClick(self,event):
        """Handle doubclick event."""
        (hitItem,hitFlag) = self.list.HitTest(event.GetPosition())
        if hitItem < 0: return
        fileInfo = self.data[self.items[hitItem]]
        if not docBrowser:
            DocBrowser().Show()
            settings['bash.modDocs.show'] = True
        #balt.ensureDisplayed(docBrowser)
        docBrowser.SetMod(fileInfo.name)
        docBrowser.Raise()

    def OnChar(self,event):
        """Char event: Delete, Reorder, Check/Uncheck."""
        ##Delete
        if event.GetKeyCode() in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self.DeleteSelected(False,event.ShiftDown())
        ##Ctrl+Up and Ctrl+Down
        elif ((event.CmdDown() and event.GetKeyCode() in (wx.WXK_UP,wx.WXK_DOWN,wx.WXK_NUMPAD_UP,wx.WXK_NUMPAD_DOWN)) and
            (settings['bash.mods.sort'] == 'Load Order')
            ):
                for thisFile in self.GetSelected():
                    if GPath(thisFile) in bosh.modInfos.autoSorted:
                        balt.showError(self,_(u"Auto-ordered files cannot be manually moved."))
                        event.Skip()
                        break
                else:
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
                self.checkUncheckMod(*selected)
            else:
                #--Check all that aren't
                self.checkUncheckMod(*toActivate)
        ##Ctrl+A
        elif event.CmdDown() and code == ord('A'):
            self.SelectAll()
        # Ctrl+C: Copy file(s) to clipboard
        elif event.CmdDown() and code == ord('C'):
            selected = self.GetSelected()
            if selected and not wx.TheClipboard.IsOpened():
                wx.TheClipboard.Open()
                clipData = wx.FileDataObject()
                for mod in selected:
                    clipData.AddFile(self.data[mod].getPath().s)
                wx.TheClipboard.SetData(clipData)
                wx.TheClipboard.Close()
        event.Skip()

    def OnColumnResize(self,event):
        """Column resize: Stored modified column widths."""
        super(ModList,self).OnColumnResize(event)
        settings.setChanged('bash.mods.colWidths')

    def OnLeftDown(self,event):
        """Left Down: Check/uncheck mods."""
        (hitItem,hitFlag) = self.list.HitTest((event.GetX(),event.GetY()))
        if hitFlag == wx.LIST_HITTEST_ONITEMICON:
            self.list.SetDnD(False)
            self.checkUncheckMod(self.items[hitItem])
        else:
            self.list.SetDnD(True)
        #--Pass Event onward
        event.Skip()

    def OnItemSelected(self,event):
        """Item Selected: Set mod details."""
        modName = self.items[event.m_itemIndex]
        self.details.SetFile(modName)
        if docBrowser:
            docBrowser.SetMod(modName)

#------------------------------------------------------------------------------
class ModDetails(SashPanel):
    """Details panel for mod tab."""

    def __init__(self,parent):
        SashPanel.__init__(self, parent,'bash.mods.details.SashPos',1.0,mode=wx.HORIZONTAL,minimumSize=150,style=wx.SW_BORDER|splitterStyle)
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
            id = self.fileId = wx.NewId()
            #--File Name
            self.file = textCtrl(top,id)#,size=(textWidth,-1))
            self.file.SetMaxLength(200)
            self.file.Bind(wx.EVT_KILL_FOCUS, self.OnEditFile)
            self.file.Bind(wx.EVT_TEXT, self.OnTextEdit)
            #--Author
            id = self.authorId = wx.NewId()
            self.author = textCtrl(top,id)#,size=(textWidth,-1))
            self.author.SetMaxLength(512)
            wx.EVT_KILL_FOCUS(self.author,self.OnEditAuthor)
            wx.EVT_TEXT(self.author,id,self.OnTextEdit)
            #--Modified
            id = self.modifiedId = wx.NewId()
            self.modified = textCtrl(top,id,size=(textWidth,-1))
            self.modified.SetMaxLength(32)
            wx.EVT_KILL_FOCUS(self.modified,self.OnEditModified)
            wx.EVT_TEXT(self.modified,id,self.OnTextEdit)
            #--Description
            id = self.descriptionId = wx.NewId()
            self.description = (
                wx.TextCtrl(top,id,u'',size=(textWidth,150),style=wx.TE_MULTILINE))
            self.description.SetMaxLength(512)
            wx.EVT_KILL_FOCUS(self.description,self.OnEditDescription)
            wx.EVT_TEXT(self.description,id,self.OnTextEdit)
            subSplitter = self.subSplitter = wx.gizmos.ThinSplitterWindow(bottom,style=splitterStyle)
            masterPanel = wx.Panel(subSplitter)
            tagPanel = wx.Panel(subSplitter)
            #--Masters
            id = self.mastersId = wx.NewId()
            self.masters = MasterList(masterPanel,None,self.SetEdited)
            #--Save/Cancel
            self.save = button(masterPanel,label=_(u'Save'),id=wx.ID_SAVE,onClick=self.DoSave,)
            self.cancel = button(masterPanel,label=_(u'Cancel'),id=wx.ID_CANCEL,onClick=self.DoCancel,)
            self.save.Disable()
            self.cancel.Disable()
            #--Bash tags
            self.allTags = bosh.allTags
            id = self.tagsId = wx.NewId()
            self.gTags = (
                wx.TextCtrl(tagPanel,id,u'',size=(textWidth,100),style=wx.TE_MULTILINE|wx.TE_READONLY))
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
        wx.EVT_MENU(self,ID_TAGS.AUTO,self.DoAutoBashTags)
        wx.EVT_MENU(self,ID_TAGS.COPY,self.DoCopyBashTags)
        wx.EVT_MENU_RANGE(self, ID_TAGS.BASE, ID_TAGS.MAX, self.ToggleBashTag)

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
        #--Editable mtime?
        if fileName in bosh.modInfos.autoSorted:
            self.modified.SetEditable(False)
            self.modified.SetBackgroundColour(self.GetBackgroundColour())
        else:
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
        if not self.modInfo: return
        self.modTags = self.modInfo.getBashTags()
        #--Build menu
        menu = wx.Menu()
        #--Revert to auto
        #--Separator
        isAuto = bosh.modInfos.table.getItem(self.modInfo.name,'autoBashTags',True)
        menuItem = wx.MenuItem(menu,ID_TAGS.AUTO,_(u'Automatic'),kind=wx.ITEM_CHECK,
            help=_(u"Use the tags from the description and masterlist/userlist."))
        menu.AppendItem(menuItem)
        menuItem.Check(isAuto)
        menuItem = wx.MenuItem(menu,ID_TAGS.COPY,_(u'Copy to Description'))
        menu.AppendItem(menuItem)
        menuItem.Enable(not isAuto and self.modTags != self.modInfo.getBashTagsDesc())
        menu.AppendSeparator()
        for id,tag in zip(ID_TAGS,self.allTags):
            menu.AppendCheckItem(id,tag,help=_(u"Add %(tag)s to %(modname)s") % ({'tag':tag,'modname':self.modInfo.name}))
            menu.Check(id,tag in self.modTags)
        self.gTags.PopupMenu(menu)
        menu.Destroy()

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
        self.edit = button(right,_(u'Edit...'),onClick=self.OnEdit)
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
        self.tweakName = textCtrl(right, style=wx.TE_READONLY|wx.NO_BORDER)
        self.SetBaseIni(self.GetChoice())
        global iniList
        from . import installer_links, ini_links
        installer_links.iniList = ini_links.iniList = iniList = INIList(left)
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
                    (self.edit,0,wx.ALIGN_TOP,0),
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

    def OnCloseWindow(self):
        """To be called when containing frame is closing.  Use for saving data, scrollpos, etc."""
        settings['bash.ini.choices'] = self.choices
        settings['bash.ini.choice'] = self.choice
        bosh.iniInfos.table.save()
        splitter = self.right.GetParent()
        if hasattr(self, 'sashPosKey'):
            settings[self.sashPosKey] = splitter.GetSashPosition()

#------------------------------------------------------------------------------
class ModPanel(SashPanel):
    def __init__(self,parent):
        SashPanel.__init__(self, parent,'bash.mods.sashPos',1.0,minimumSize=150)
        left,right = self.left, self.right
        global modList
        from . import mods_links, mod_links, saves_links, app_buttons, \
            patcher_dialog
        saves_links.modList = mods_links.modList = mod_links.modList = \
            app_buttons.modList = patcher_dialog.modList = modList \
            = ModList(left)
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

    def OnCloseWindow(self):
        """To be called when containing frame is closing. Use for saving data, scrollpos, etc."""
        bosh.modInfos.table.save()
        settings['bash.mods.scrollPos'] = modList.vScrollPos
        splitter = self.right.GetParent()
        settings[self.sashPosKey] = splitter.GetSashPosition()
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

    def __init__(self,parent):
        #--Columns
        self.colsKey = 'bash.saves.cols'
        self.colAligns = settings['bash.saves.colAligns']
        self.colNames = settings['bash.colNames']
        self.colReverse = settings.getChanged('bash.saves.colReverse')
        self.colWidths = settings['bash.saves.colWidths']
        #--Data/Items
        self.data = data = bosh.saveInfos
        self.details = None #--Set by panel
        self.sort = settings['bash.saves.sort']
        #--Links
        self.mainMenu = SaveList.mainMenu
        self.itemMenu = SaveList.itemMenu
        #--Parent init
        List.__init__(self,parent,-1,ctrlStyle=(wx.LC_REPORT|wx.SUNKEN_BORDER|wx.LC_EDIT_LABELS))
        #--Image List
        checkboxesIL = self.checkboxes.GetImageList()
        self.list.SetImageList(checkboxesIL,wx.IMAGE_LIST_SMALL)
        #--Events
        self.list.Bind(wx.EVT_CHAR, self.OnChar)
        wx.EVT_LIST_ITEM_SELECTED(self,self.listId,self.OnItemSelected)
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
        self.list.SetItemImage(itemDex,self.checkboxes.Get(status,on))
        #--Selection State
        if fileName in selected:
            self.list.SetItemState(itemDex,wx.LIST_STATE_SELECTED,wx.LIST_STATE_SELECTED)
        else:
            self.list.SetItemState(itemDex,0,wx.LIST_STATE_SELECTED)

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

    #--Column Resize
    def OnColumnResize(self,event):
        super(SaveList,self).OnColumnResize(event)
        settings.setChanged('bash.saves.colWidths')

    def OnKeyUp(self,event):
        """Char event: select all items"""
        code = event.GetKeyCode()
        ##Ctrl+A
        if event.CmdDown() and code == ord('A'):
            self.SelectAll()
        # Ctrl+C: Copy file(s) to clipboard
        elif event.CmdDown() and code == ord('C'):
            selected = self.GetSelected()
            if selected and not wx.TheClipboard.IsOpened():
                wx.TheClipboard.Open()
                clipData = wx.FileDataObject()
                for save in selected:
                    clipData.AddFile(self.data[save].getPath().s)
                wx.TheClipboard.SetData(clipData)
                wx.TheClipboard.Close()
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
        SashPanel.__init__(self, parent,'bash.saves.details.SashPos',0.0,sashPos=230,mode=wx.HORIZONTAL,minimumSize=230,style=wx.SW_BORDER|splitterStyle)
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
        id = self.fileId = wx.NewId()
        self.file = wx.TextCtrl(top,id,u'',size=(textWidth,-1))
        self.file.SetMaxLength(256)
        wx.EVT_KILL_FOCUS(self.file,self.OnEditFile)
        wx.EVT_TEXT(self.file,id,self.OnTextEdit)
        #--Player Info
        self.playerInfo = staticText(top,u" \n \n ")
        self.gCoSaves = staticText(top,u'--\n--')
        #--Picture
        self.picture = balt.Picture(top,textWidth,192*textWidth/256,style=wx.BORDER_SUNKEN,background=colors['screens.bkgd.image']) #--Native: 256x192
        subSplitter = self.subSplitter = wx.gizmos.ThinSplitterWindow(bottom,style=splitterStyle)
        masterPanel = wx.Panel(subSplitter)
        notePanel = wx.Panel(subSplitter)
        #--Masters
        id = self.mastersId = wx.NewId()
        self.masters = MasterList(masterPanel,None,self.SetEdited)
        #--Save Info
        self.gInfo = wx.TextCtrl(notePanel,wx.ID_ANY,u'',size=(textWidth,100),style=wx.TE_MULTILINE)
        self.gInfo.SetMaxLength(2048)
        self.gInfo.Bind(wx.EVT_TEXT,self.OnInfoEdit)
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
            image = wx.EmptyImage(width,height)
            image.SetData(data)
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
            bosh.saveInfos.table.setItem(self.saveInfo.name,'info',self.gInfo.GetValue())

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
        saves_links.saveList = saveList = SaveList(left)
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

    def OnCloseWindow(self):
        """To be called when containing frame is closing. Use for saving data, scrollpos, etc."""
        table = bosh.saveInfos.table
        for saveName in table.keys():
            if saveName not in bosh.saveInfos:
                del table[saveName]
        table.save()
        bosh.saveInfos.profiles.save()
        settings['bash.saves.scrollPos'] = saveList.vScrollPos
        splitter = self.right.GetParent()
        settings[self.sashPosKey] = splitter.GetSashPosition()
        # Mod details Sash Positions
        splitter = self.saveDetails.right.GetParent()
        settings[self.saveDetails.sashPosKey] = splitter.GetSashPosition()
        splitter = self.saveDetails.subSplitter
        settings['bash.saves.details.subSplitterSashPos'] = splitter.GetSashPosition()

#------------------------------------------------------------------------------
class InstallersList(balt.Tank):
    def __init__(self,parent,data,icons=None,mainMenu=None,itemMenu=None,
            details=None,id=-1,style=(wx.LC_REPORT | wx.LC_SINGLE_SEL)):
        self.colNames = settings['bash.colNames']
        self.colAligns = settings['bash.installers.colAligns']
        self.colReverse = settings['bash.installers.colReverse']
        self.colWidths = settings['bash.installers.colWidths']
        self.sort = settings['bash.installers.sort']
        balt.Tank.__init__(self,parent,data,icons,mainMenu,itemMenu,
            details,id,style|wx.LC_EDIT_LABELS,dndList=True,dndFiles=True,dndColumns=['Order'])
        self.gList.Bind(wx.EVT_CHAR, self.OnChar)
        self.gList.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self.gList.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginEditLabel)
        self.gList.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEditLabel)
        self.hitItem = None
        self.hitTime = 0

    @property
    def cols(self): return settings['bash.installers.cols']

    def SetSort(self,sort):
        self.sort = settings['bash.installers.sort'] = sort

    def SetColumnReverse(self,column,reverse):
        settings['bash.installers.colReverse'][column] = reverse
        settings.setChanged('bash.installers.colReverse')

    def GetColumnDex(self,column):
        return settingDefaults['bash.installers.cols'].index(column)

    def OnColumnResize(self,event):
        """Column has been resized."""
        super(InstallersList, self).OnColumnResize(event)
        settings.setChanged('bash.installers.colWidths')

    def MouseOverItem(self,item):
        """Handle mouse entered item by showing tip or similar."""
        if item < 0: return
        item = self.GetItem(item)
        text = self.mouseTexts.get(item) or u''
        if text != self.mouseTextPrev:
            statusBar.SetStatusText(text,1)
            self.mouseTextPrev = text

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

            dialog= wx.Dialog(self,wx.ID_ANY,_(u'Move or Copy?'),size=(400,200),style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
            icon = wx.StaticBitmap(dialog,wx.ID_ANY,wx.ArtProvider_GetBitmap(wx.ART_WARNING,wx.ART_MESSAGE_BOX, (32,32)))
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

    def SelectAll(self):
        for itemDex in range(self.gList.GetItemCount()):
            self.SelectItemAtIndex(itemDex)

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
            if wx.TheClipboard.Open():
                if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_FILENAME)):
                    obj = wx.FileDataObject()
                    wx.TheClipboard.GetData(obj)
                    wx.CallLater(10,self.OnDropFiles,0,0,obj.GetFilenames())
                wx.TheClipboard.Close()
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
                self.gList.SetItemState(itemDex,wx.LIST_STATE_SELECTED,
                                        wx.LIST_STATE_SELECTED)
        else:
            path = self.data.dir.join(self.GetItem(hitItem))
            if path.exists(): path.start()
        event.Skip()

    def OnLeftDown(self,event):
        """Left click, do stuff; currently nothing."""
        event.Skip()
        return

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
            selected = self.GetSelected()
            if selected and not wx.TheClipboard.IsOpened():
                wx.TheClipboard.Open()
                clipData = wx.FileDataObject()
                for installer in selected:
                    clipData.AddFile(bosh.dirs['installers'].join(installer).s)
                wx.TheClipboard.SetData(clipData)
                wx.TheClipboard.Close()
        event.Skip()

#------------------------------------------------------------------------------
class InstallersPanel(SashTankPanel):
    """Panel for InstallersTank."""
    mainMenu = Links()
    itemMenu = Links()
    espmMenu = Links()
    subsMenu = Links()

    def __init__(self,parent):
        """Initialize."""
        global gInstallers
        gInstallers = self
        from . import installers_links, installer_links
        installers_links.gInstallers = installer_links.gInstallers = self
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
        self.gList = InstallersList(left,data,
            installercons, InstallersPanel.mainMenu, InstallersPanel.itemMenu,
            details=self, style=wx.LC_REPORT)
        self.gList.SetSizeHints(100,100)
        #--Package
        self.gPackage = wx.TextCtrl(right,wx.ID_ANY,style=wx.TE_READONLY|wx.NO_BORDER)
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
            gPage = wx.TextCtrl(self.gNotebook,wx.ID_ANY,style=wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL,name=name)
            self.gNotebook.AddPage(gPage,title)
            self.infoPages.append([gPage,False])
        self.gNotebook.SetSelection(settings['bash.installers.page'])
        self.gNotebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED,self.OnShowInfoPage)
        #--Sub-Installers
        subPackagesPanel = wx.Panel(checkListSplitter)
        subPackagesLabel = staticText(subPackagesPanel, _(u'Sub-Packages'))
        self.gSubList = wx.CheckListBox(subPackagesPanel, style=wx.LB_EXTENDED)
        self.gSubList.Bind(wx.EVT_CHECKLISTBOX,self.OnCheckSubItem)
        self.gSubList.Bind(wx.EVT_RIGHT_UP,self.SubsSelectionMenu)
        #--Espms
        espmsPanel = wx.Panel(checkListSplitter)
        espmsLabel = staticText(espmsPanel, _(u'Esp/m Filter'))
        self.espms = []
        self.gEspmList = wx.CheckListBox(espmsPanel, style=wx.LB_EXTENDED)
        self.gEspmList.Bind(wx.EVT_CHECKLISTBOX,self.OnCheckEspmItem)
        self.gEspmList.Bind(wx.EVT_RIGHT_UP,self.SelectionMenu)
        #--Comments
        commentsPanel = wx.Panel(commentsSplitter)
        commentsLabel = staticText(commentsPanel, _(u'Comments'))
        self.gComments = wx.TextCtrl(commentsPanel, wx.ID_ANY, style=wx.TE_MULTILINE)
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
        if bosh.modInfos.refresh(doAutoGroup=True):
            del bosh.modInfos.mtimesReset[:]
            bosh.modInfos.autoGrouped.clear()
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

    def __init__(self,parent):
        #--Columns
        self.colsKey = 'bash.screens.cols'
        self.colAligns = settings['bash.screens.colAligns']
        self.colNames = settings['bash.colNames']
        self.colReverse = settings.getChanged('bash.screens.colReverse')
        self.colWidths = settings['bash.screens.colWidths']
        #--Data/Items
        self.data = bosh.screensData = bosh.ScreensData()
        self.sort = settings['bash.screens.sort']
        #--Links
        self.mainMenu = ScreensList.mainMenu
        self.itemMenu = ScreensList.itemMenu
        #--Parent init
        List.__init__(self,parent,-1,ctrlStyle=(wx.LC_REPORT|wx.SUNKEN_BORDER|wx.LC_EDIT_LABELS))
        #--Events
        wx.EVT_LIST_ITEM_SELECTED(self,self.listId,self.OnItemSelected)
        self.list.Bind(wx.EVT_CHAR, self.OnChar)
        self.list.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self.list.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginEditLabel)
        self.list.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEditLabel)
        self.list.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)

    def OnDoubleClick(self,event):
        """Double click a screeshot"""
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
                    self.list.SetItemState(index,wx.LIST_STATE_SELECTED,wx.LIST_STATE_SELECTED)
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
        if fileName in selected:
            self.list.SetItemState(itemDex,wx.LIST_STATE_SELECTED,wx.LIST_STATE_SELECTED)
        else:
            self.list.SetItemState(itemDex,0,wx.LIST_STATE_SELECTED)

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
            selected = self.GetSelected()
            if selected and not wx.TheClipboard.IsOpened():
                wx.TheClipboard.Open()
                clipData = wx.FileDataObject()
                for screenshot in selected:
                    clipData.AddFile(bosh.screensData.dir.join(screenshot).s)
                wx.TheClipboard.SetData(clipData)
                wx.TheClipboard.Close()
        event.Skip()

    #--Column Resize
    def OnColumnResize(self,event):
        super(ScreensList,self).OnColumnResize(event)
        settings.setChanged('bash.screens.colWidths')

    def OnItemSelected(self,event=None):
        fileName = self.items[event.m_itemIndex]
        filePath = bosh.screensData.dir.join(fileName)
        bitmap = wx.Bitmap(filePath.s) if filePath.exists() else None
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
        screensList = ScreensList(left)
        screensList.SetSizeHints(100,100)
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

    def __init__(self,parent):
        #--Columns
        self.cols = settings['bash.BSAs.cols']
        self.colAligns = settings['bash.BSAs.colAligns']
        self.colNames = settings['bash.colNames']
        self.colReverse = settings.getChanged('bash.BSAs.colReverse')
        self.colWidths = settings['bash.BSAs.colWidths']
        #--Data/Items
        self.data = data = bosh.BSAInfos
        self.details = None #--Set by panel
        self.sort = settings['bash.BSAs.sort']
        #--Links
        self.mainMenu = BSAList.mainMenu
        self.itemMenu = BSAList.itemMenu
        #--Parent init
        List.__init__(self,parent,-1,ctrlStyle=(wx.LC_REPORT|wx.SUNKEN_BORDER))
        #--Image List
        checkboxesIL = self.checkboxes.GetImageList()
        self.list.SetImageList(checkboxesIL,wx.IMAGE_LIST_SMALL)
        #--Events
        self.list.Bind(wx.EVT_CHAR, self.OnChar)
        wx.EVT_LIST_ITEM_SELECTED(self,self.listId,self.OnItemSelected)
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
        on = fileName.cext == u'.bsa'
        #self.list.SetItemImage(itemDex,self.checkboxes.Get(status,on))
        #--Selection State
        if fileName in selected:
            self.list.SetItemState(itemDex,wx.LIST_STATE_SELECTED,wx.LIST_STATE_SELECTED)
        else:
            self.list.SetItemState(itemDex,0,wx.LIST_STATE_SELECTED)

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

    #--Column Resize
    def OnColumnResize(self,event):
        super(BSAList,self).OnColumnResize(event)
        settings.setChanged('bash.BSAs.colWidths')

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
        id = self.fileId = wx.NewId()
        self.file = wx.TextCtrl(self,id,u'',size=(textWidth,-1))
        self.file.SetMaxLength(256)
        wx.EVT_KILL_FOCUS(self.file,self.OnEditFile)
        wx.EVT_TEXT(self.file,id,self.OnTextEdit)

        #--BSA Info
        self.gInfo = wx.TextCtrl(self,wx.ID_ANY,u'',size=(textWidth,100),style=wx.TE_MULTILINE)
        self.gInfo.SetMaxLength(2048)
        self.gInfo.Bind(wx.EVT_TEXT,self.OnInfoEdit)
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
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        global BSAList
        BSAList = BSAList(self)
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

    def OnCloseWindow(self):
        """To be called when containing frame is closing. Use for saving data, scrollpos, etc."""
        table = bosh.BSAInfos.table
        for BSAName in table.keys():
            if BSAName not in bosh.BSAInfos:
                del table[BSAName]
        table.save()
        bosh.BSAInfos.profiles.save()
        settings['bash.BSAs.scrollPos'] = BSAList.vScrollPos

#------------------------------------------------------------------------------
class MessageList(List):
    #--Class Data
    mainMenu = Links() #--Column menu
    itemMenu = Links() #--Single item menu

    def __init__(self,parent):
        #--Columns
        self.colsKey = 'bash.messages.cols'
        self.colAligns = settings['bash.messages.colAligns']
        self.colNames = settings['bash.colNames']
        self.colReverse = settings.getChanged('bash.messages.colReverse')
        self.colWidths = settings['bash.messages.colWidths']
        #--Data/Items
        self.data = bosh.messages = bosh.Messages()
        self.data.refresh()
        self.sort = settings['bash.messages.sort']
        #--Links
        self.mainMenu = MessageList.mainMenu
        self.itemMenu = MessageList.itemMenu
        #--Other
        self.gText = None
        self.searchResults = None
        #--Parent init
        List.__init__(self,parent,wx.ID_ANY,ctrlStyle=(wx.LC_REPORT|wx.SUNKEN_BORDER))
        #--Events
        wx.EVT_LIST_ITEM_SELECTED(self,self.listId,self.OnItemSelected)
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
        if item in selected:
            self.list.SetItemState(itemDex,wx.LIST_STATE_SELECTED,wx.LIST_STATE_SELECTED)
        else:
            self.list.SetItemState(itemDex,0,wx.LIST_STATE_SELECTED)

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

    #--Column Resize
    def OnColumnResize(self,event):
        super(MessageList,self).OnColumnResize(event)
        settings.setChanged('bash.messages.colWidths')

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
        SashPanel.__init__(self,parent,'bash.messages.sashPos',sashPos=120,mode=wx.HORIZONTAL,minimumSize=100)
        gTop,gBottom = self.left,self.right
        #--Contents
        global gMessageList
        gMessageList = MessageList(gTop)
        gMessageList.SetSizeHints(100,100)
        gMessageList.gText = wx.lib.iewin.IEHtmlWindow(gBottom,wx.ID_ANY,style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.list = gMessageList
        #--Search
        gSearchBox = self.gSearchBox = wx.TextCtrl(gBottom,wx.ID_ANY,u'',style=wx.TE_PROCESS_ENTER)
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

    def OnCloseWindow(self):
        """To be called when containing frame is closing. Use for saving data, scrollpos, etc."""
        if bosh.messages: bosh.messages.save()
        settings['bash.messages.scrollPos'] = gMessageList.vScrollPos

#------------------------------------------------------------------------------
class PeopleList(balt.Tank):
    def __init__(self,*args,**kwdargs):
        self.colNames = settings['bash.colNames']
        self.colAligns = settings['bash.people.colAligns']
        self.colWidths = settings['bash.people.colWidths']
        self.colReverse = settings['bash.people.colReverse']
        self.sort = settings['bash.people.sort']
        balt.Tank.__init__(self, *args, **kwdargs)

    @property
    def cols(self): return settings['bash.people.cols']

    def SetSort(self,sort):
        self.sort = settings['bash.people.sort'] = sort

    def SetColumnReverse(self,column,reverse):
        settings['bash.people.colReverse'][column] = reverse
        settings.setChanged('bash.people.colReverse')

    def OnColumnResize(self,event):
        """Column resized."""
        super(PeopleList,self).OnColumnResize(event)
        settings.setChanged('bash.people.colWidths')

    def GetColumnDex(self,column):
        return settingDefaults['bash.people.cols'].index(column)

#------------------------------------------------------------------------------
class PeoplePanel(SashTankPanel):
    """Panel for PeopleTank."""
    mainMenu = Links()
    itemMenu = Links()

    def __init__(self,parent):
        """Initialize."""
        data = bosh.PeopleData()
        SashTankPanel.__init__(self,data,parent)
        left,right = self.left,self.right
        #--Contents
        self.gList = PeopleList(left,data,
            karmacons, PeoplePanel.mainMenu, PeoplePanel.itemMenu,
            details=self, style=wx.LC_REPORT)
        self.gList.SetSizeHints(100,100)
        self.gName = wx.TextCtrl(right,wx.ID_ANY,style=wx.TE_READONLY)
        self.gText = wx.TextCtrl(right,wx.ID_ANY,style=wx.TE_MULTILINE)
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
class ModBasePanel(SashTankPanel):
    """Panel for ModBaseTank."""
    mainMenu = Links()
    itemMenu = Links()

    def __init__(self,parent):
        """Initialize."""
        data = bosh.ModBaseData()
        SashTankPanel.__init__(self, data, parent)
        #--Left
        left,right = self.left, self.right
        #--Contents
        self.gList = balt.Tank(left,data,
            karmacons, ModBasePanel.mainMenu, ModBasePanel.itemMenu,
            details=self, style=wx.LC_REPORT)
        self.gList.SetSizeHints(100,100)
        #--Right header
        self.gPackage = wx.TextCtrl(right,wx.ID_ANY,style=wx.TE_READONLY)
        self.gAuthor = wx.TextCtrl(right,wx.ID_ANY)
        self.gVersion = wx.TextCtrl(right,wx.ID_ANY)
        #--Right tags, abstract, review
        self.gTags = wx.TextCtrl(right,wx.ID_ANY)
        self.gAbstract = wx.TextCtrl(right,wx.ID_ANY,style=wx.TE_MULTILINE)
        #--Fields (for zipping)
        self.index_field = {
            1: self.gAuthor,
            2: self.gVersion,
            4: self.gTags,
            5: self.gAbstract,
            }
        #--Header
        fgSizer = wx.FlexGridSizer(4,2,2,4)
        fgSizer.AddGrowableCol(1,1)
        fgSizer.AddMany([
            staticText(right,_(u'Package')),
            (self.gPackage,0,wx.GROW),
            staticText(right,_(u'Author')),
            (self.gAuthor,0,wx.GROW),
            staticText(right,_(u'Version')),
            (self.gVersion,0,wx.GROW),
            staticText(right,_(u'Tags')),
            (self.gTags,0,wx.GROW),
            ])
        #--Events
        self.Bind(wx.EVT_SIZE,self.OnSize)
        #--Layout
        right.SetSizer(vSizer(
            (fgSizer,0,wx.GROW|wx.TOP|wx.LEFT,3),
            staticText(right,_(u'Abstract')),
            (self.gAbstract,1,wx.GROW|wx.TOP,4),
            ))
        wx.LayoutAlgorithm().LayoutWindow(self, right)

    def SetStatusCount(self):
        """Sets status bar count field."""
        text = _(u'ModBase:')+u' %d' % (len(self.data.data),)
        statusBar.SetStatusText(text,2)

    #--Details view (if it exists)
    def SaveDetails(self):
        """Saves details if they need saving."""
        item = self.detailsItem
        if not item or item not in self.data: return
        if not sum(x.IsModified() for x in self.index_field.values()): return
        entry = self.data[item]
        for index,field in self.index_field.items():
            entry[index] = field.GetValue().strip()
        self.gList.UpdateItem(self.gList.GetIndex(item))
        self.data.setChanged()

    def RefreshDetails(self,item=None):
        """Refreshes detail view associated with data from item."""
        item = item or self.detailsItem
        if item not in self.data: item = None
        self.SaveDetails()
        if item is None:
            self.gPackage.Clear()
            for field in self.index_field.values():
                field.Clear()
        else:
            entry = self.data[item]
            self.gPackage.SetValue(item)
            for index,field in self.index_field.items():
                field.SetValue(entry[index])
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
    def __init__(self, parent=None,pos=wx.DefaultPosition,size=(400,500),
             style = wx.DEFAULT_FRAME_STYLE):
        """Initialization."""
        #--Singleton
        global bashFrame
        bashFrame = self
        balt.Link.Frame = self
        #--Window
        wx.Frame.__init__(self, parent, wx.ID_ANY, u'Wrye Bash', pos, size, style)
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
        bosh.bsaInfos = bosh.BSAInfos()
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
        modInfosChanged = bosh.modInfos.refresh(doAutoGroup=True)
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
                    with ListBoxes(self,_(u'Modified Dates Reset'),
                            _(u'Modified dates have been reset for some mod files.'),
                            [message],liststyle='list',Cancel=False) as dialog:
                        dialog.ShowModal()
            del bosh.modInfos.mtimesReset[:]
            popMods = 'ALL'
        #--Mods autogrouped?
        if bosh.modInfos.autoGrouped:
            message = [u'',_(u'Auto-grouped files')]
            agDict = bosh.modInfos.autoGrouped
            ordered = bosh.modInfos.getOrdered(agDict.keys())
            message.extend(ordered)
            agDict.clear()
            with ListBoxes(self, _(u'Some mods have been auto-grouped:'),
                           _(u'Some mods have been auto-grouped:'), [message],
                           liststyle='list', Cancel=False) as dialog:
                dialog.ShowModal()
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
            with ListBoxes(self, _(u'Warning: Corrupt/Unrecognized Files'), _(
                    u'Some files have corrupted headers or TES4 header '
                    u'versions:'), message, liststyle='list',
                           Cancel=False) as dialog:
                dialog.ShowModal()
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
        except:
            deprint(u'An error occurred while trying to save settings:', traceback=True)
            pass
        self.Destroy()

    def SaveSettings(self):
        """Save application data."""
        # Purge some memory
        bolt.GPathPurge()
        # Clean out unneeded settings
        self.CleanSettings()
        if docBrowser: docBrowser.DoSave()
        if not (self.IsIconized() or self.IsMaximized()):
            settings['bash.framePos'] = self.GetPositionTuple()
            settings['bash.frameSize'] = self.GetSizeTuple()
        settings['bash.frameMax'] = self.IsMaximized()
        settings['bash.page'] = self.notebook.GetSelection()
        for index in range(self.notebook.GetPageCount()):
            self.notebook.GetPage(index).OnCloseWindow()
        settings.save()

    def CleanSettings(self):
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
from ..balt import _Link

class CheckList_SelectAll(_Link):
    def __init__(self,select=True):
        super(CheckList_SelectAll, self).__init__()
        self.select = select
        self.text = _(u'Select All') if select else _(u'Select None')

    def Execute(self,event):
        for i in xrange(self.window.GetCount()):
            self.window.Check(i,self.select)

#------------------------------------------------------------------------------
class ListBoxes(wx.Dialog):
    """A window with 1 or more lists."""
    # TODO(ut): attrs below must go - askContinue method ? Also eliminate destroy calls
    ID_OK = wx.ID_OK
    ID_CANCEL = wx.ID_CANCEL

    # TODO(ut):USE THOSE
    #  __enter__ and __exit__ for use with the 'with' statement
    def __enter__(self):
        return self
    def __exit__(self,type,value,traceback):
        self.Destroy()

    def __init__(self,parent,title,message,lists,liststyle='check',style=wx.DEFAULT_DIALOG_STYLE,changedlabels={},Cancel=True):
        """lists is in this format:
        if liststyle == 'check' or 'list'
        [title,tooltip,item1,item2,itemn],
        [title,tooltip,....],
        elif liststyle == 'tree'
        [title,tooltip,{item1:[subitem1,subitemn],item2:[subitem1,subitemn],itemn:[subitem1,subitemn]}],
        [title,tooltip,....],
        """
        wx.Dialog.__init__(self,parent,wx.ID_ANY,title,style=style)
        self.itemMenu = Links()
        self.itemMenu.append(CheckList_SelectAll())
        self.itemMenu.append(CheckList_SelectAll(False))
        self.SetIcons(Resources.bashBlue)
        minWidth = self.GetTextExtent(title)[0]*1.2+64
        sizer = wx.FlexGridSizer(len(lists)+1,1)
        self.ids = {}
        labels = {wx.ID_CANCEL:_(u'Cancel'),wx.ID_OK:_(u'OK')}
        labels.update(changedlabels)
        self.SetSize(wx.Size(self.GetTextExtent(title)[0]*1.2+64,-1))
        for i,group in enumerate(lists):
            title = group[0]
            tip = group[1]
            try: items = [x.s for x in group[2:]]
            except: items = [x for x in group[2:]]
            if len(items) == 0: continue
            box = wx.StaticBox(self,wx.ID_ANY,title)
            subsizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
            if liststyle == 'check':
                checks = wx.CheckListBox(self,wx.ID_ANY,choices=items,style=wx.LB_SINGLE|wx.LB_HSCROLL)
                checks.Bind(wx.EVT_KEY_UP,self.OnKeyUp)
                checks.Bind(wx.EVT_CONTEXT_MENU,self.OnContext)
                for i in xrange(len(items)):
                    checks.Check(i,True)
            elif liststyle == 'list':
                checks = wx.ListBox(self,wx.ID_ANY,choices=items,style=wx.LB_SINGLE|wx.LB_HSCROLL)
            else:
                checks = wx.TreeCtrl(self,wx.ID_ANY,size=(150,200),style=wx.TR_DEFAULT_STYLE|wx.TR_FULL_ROW_HIGHLIGHT|wx.TR_HIDE_ROOT)
                root = checks.AddRoot(title)
                for item in group[2]:
                    child = checks.AppendItem(root,item.s)
                    for subitem in group[2][item]:
                        sub = checks.AppendItem(child,subitem.s)
            self.ids[title] = checks.GetId()
            checks.SetToolTip(balt.tooltip(tip))
            subsizer.Add(checks,1,wx.EXPAND|wx.ALL,2)
            sizer.Add(subsizer,0,wx.EXPAND|wx.ALL,5)
            sizer.AddGrowableRow(i)
        okButton = button(self,id=wx.ID_OK,label=labels[wx.ID_OK])
        okButton.SetDefault()
        buttonSizer = hSizer(balt.spacer,
                             (okButton,0,wx.ALIGN_RIGHT),
                             )
        for id,label in labels.iteritems():
            if id in (wx.ID_OK,wx.ID_CANCEL):
                continue
            but = button(self,id=id,label=label)
            but.Bind(wx.EVT_BUTTON,self.OnClick)
            buttonSizer.Add(but,0,wx.ALIGN_RIGHT|wx.LEFT,2)
        if Cancel:
            buttonSizer.Add(button(self,id=wx.ID_CANCEL,label=labels[wx.ID_CANCEL]),0,wx.ALIGN_RIGHT|wx.LEFT,2)
        sizer.Add(buttonSizer,1,wx.EXPAND|wx.BOTTOM|wx.LEFT|wx.RIGHT,5)
        sizer.AddGrowableCol(0)
        sizer.SetSizeHints(self)
        self.SetSizer(sizer)
        #make sure that minimum size is at least the size of title
        if self.GetSize()[0] < minWidth:
            self.SetSize(wx.Size(minWidth,-1))

    def OnKeyUp(self,event):
        """Char events"""
        ##Ctrl-A - check all
        obj = event.GetEventObject()
        if event.CmdDown() and event.GetKeyCode() == ord('A'):
            check = not event.ShiftDown()
            for i in xrange(len(obj.GetStrings())):
                    obj.Check(i,check)
        else:
            event.Skip()

    def OnContext(self,event):
        """Context Menu"""
        self.itemMenu.PopupMenu(event.GetEventObject(),bashFrame,event.GetEventObject().GetSelections())
        event.Skip()

    def OnClick(self,event):
        id = event.GetId()
        if id not in (wx.ID_OK,wx.ID_CANCEL):
            self.EndModal(id)
        else:
            event.Skip()

#------------------------------------------------------------------------------
class ColorDialog(wx.Dialog):
    """Color configuration dialog"""
    def __init__(self,parent):
        wx.Dialog.__init__(self,parent,wx.ID_ANY,_(u'Color Configuration'))
        self.changes = dict()
        #--ComboBox
        keys = [x for x in colors]
        keys.sort()
        choices = [colorInfo[x][0] for x in keys]
        choice = choices[0]
        self.text_key = dict()
        for key in keys:
            text = colorInfo[key][0]
            self.text_key[text] = key
        choiceKey = self.text_key[choice]
        self.comboBox = balt.comboBox(self,wx.ID_ANY,choice,choices=choices,style=wx.CB_READONLY)
        #--Color Picker
        self.picker = wx.ColourPickerCtrl(self,wx.ID_ANY)
        self.picker.SetColour(colors[choiceKey])
        #--Description
        help = colorInfo[choiceKey][1]
        self.textCtrl = wx.TextCtrl(self,wx.ID_ANY,help,style=wx.TE_MULTILINE|wx.TE_READONLY)
        #--Buttons
        self.default = button(self,_(u'Default'),onClick=self.OnDefault)
        self.defaultAll = button(self,_(u'All Defaults'),onClick=self.OnDefaultAll)
        self.apply = button(self,id=wx.ID_APPLY,onClick=self.OnApply)
        self.applyAll = button(self,_(u'Apply All'),onClick=self.OnApplyAll)
        self.exportConfig = button(self,_(u'Export...'),onClick=self.OnExport)
        self.importConfig = button(self,_(u'Import...'),onClick=self.OnImport)
        self.ok = button(self,id=wx.ID_OK)
        self.ok.SetDefault()
        #--Events
        self.comboBox.Bind(wx.EVT_COMBOBOX,self.OnComboBox)
        self.picker.Bind(wx.EVT_COLOURPICKER_CHANGED,self.OnColorPicker)
        #--Layout
        sizer = vSizer(
            (hSizer(
                (self.comboBox,1,wx.EXPAND|wx.RIGHT,5), self.picker,
                ),0,wx.EXPAND|wx.ALL,5),
            (self.textCtrl,1,wx.EXPAND|wx.ALL,5),
            (hSizer(
                (self.defaultAll,0,wx.RIGHT,5),
                (self.applyAll,0,wx.RIGHT,5), self.exportConfig,
                ),0,wx.EXPAND|wx.ALL,5),
            (hSizer(
                (self.default,0,wx.RIGHT,5),
                (self.apply,0,wx.RIGHT,5), self.importConfig, spacer, self.ok,
                ),0,wx.EXPAND|wx.ALL,5),
            )
        self.comboBox.SetFocus()
        self.SetSizer(sizer)
        self.SetIcons(Resources.bashBlue)
        self.UpdateUIButtons()

    def GetChoice(self):
        return self.text_key[self.comboBox.GetValue()]

    def UpdateUIColors(self):
        """Update the bashFrame with the new colors"""
        nb = bashFrame.notebook
        with balt.BusyCursor():
            for (className,title,panel) in tabInfo.itervalues():
                if panel is not None:
                    panel.RefreshUIColors()

    def UpdateUIButtons(self):
        # Apply All and Default All
        for key in self.changes.keys():
            if self.changes[key] == colors[key]:
                del self.changes[key]
        anyChanged = bool(self.changes)
        allDefault = True
        for key in colors:
            if key in self.changes:
                color = self.changes[key]
            else:
                color = colors[key]
            default = bool(color == settingDefaults['bash.colors'][key])
            if not default:
                allDefault = False
                break
        # Apply and Default
        choice = self.GetChoice()
        changed = bool(choice in self.changes)
        if changed:
            color = self.changes[choice]
        else:
            color = colors[choice]
        default = bool(color == settingDefaults['bash.colors'][choice])
        # Update the Buttons, ComboBox, and ColorPicker
        self.apply.Enable(changed)
        self.applyAll.Enable(anyChanged)
        self.default.Enable(not default)
        self.defaultAll.Enable(not allDefault)
        self.picker.SetColour(color)
        self.comboBox.SetFocusFromKbd()

    def OnDefault(self,event):
        event.Skip()
        choice = self.GetChoice()
        newColor = settingDefaults['bash.colors'][choice]
        self.changes[choice] = newColor
        self.UpdateUIButtons()

    def OnDefaultAll(self,event):
        event.Skip()
        for key in colors:
            default = settingDefaults['bash.colors'][key]
            if colors[key] != default:
                self.changes[key] = default
        self.UpdateUIButtons()

    def OnApply(self,event):
        event.Skip()
        choice = self.GetChoice()
        newColor = self.changes[choice]
        #--Update settings and colors
        settings['bash.colors'][choice] = newColor
        settings.setChanged('bash.colors')
        colors[choice] = newColor
        self.UpdateUIButtons()
        self.UpdateUIColors()

    def OnApplyAll(self,event):
        event.Skip()
        for key,newColor in self.changes.iteritems():
            settings['bash.colors'][key] = newColor
            colors[key] = newColor
        settings.setChanged('bash.colors')
        self.UpdateUIButtons()
        self.UpdateUIColors()

    def OnExport(self,event):
        event.Skip()
        outDir = bosh.dirs['patches']
        outDir.makedirs()
        #--File dialog
        outPath = balt.askSave(self,_(u'Export color configuration to:'), outDir, _(u'Colors.txt'), u'*.txt')
        if not outPath: return
        try:
            with outPath.open('w') as file:
                for key in colors:
                    if key in self.changes:
                        color = self.changes[key]
                    else:
                        color = colors[key]
                    file.write(key+u': '+color+u'\n')
        except Exception,e:
            balt.showError(self,_(u'An error occurred writing to ')+outPath.stail+u':\n\n%s'%e)

    def OnImport(self,event):
        event.Skip()
        inDir = bosh.dirs['patches']
        inDir.makedirs()
        #--File dialog
        inPath = balt.askOpen(self,_(u'Import color configuration from:'), inDir, _(u'Colors.txt'), u'*.txt', mustExist=True)
        if not inPath: return
        try:
            with inPath.open('r') as file:
                for line in file:
                    # Format validation
                    if u':' not in line:
                        continue
                    split = line.split(u':')
                    if len(split) != 2:
                        continue
                    key = split[0]
                    # Verify color exists
                    if key not in colors:
                        continue
                    # Color format verification
                    color = eval(split[1])
                    if not isinstance(color, tuple) or len(color) not in (3,4):
                        continue
                    ok = True
                    for value in color:
                        if not isinstance(value,int):
                            ok = False
                            break
                        if value < 0x00 or value > 0xFF:
                            ok = False
                            break
                    if not ok:
                        continue
                    # Save it
                    if color == colors[key]: continue
                    self.changes[key] = color
        except Exception, e:
            balt.showError(bashFrame,_(u'An error occurred reading from ')+inPath.stail+u':\n\n%s'%e)
        self.UpdateUIButtons()

    def OnComboBox(self,event):
        event.Skip()
        self.UpdateUIButtons()
        choice = self.GetChoice()
        help = colorInfo[choice][1]
        self.textCtrl.SetValue(help)

    def OnColorPicker(self,event):
        event.Skip()
        choice = self.GetChoice()
        newColor = self.picker.GetColour()
        self.changes[choice] = newColor
        self.UpdateUIButtons()

#------------------------------------------------------------------------------
class DocBrowser(wx.Frame):
    """Doc Browser frame."""
    def __init__(self,modName=None):
        """Intialize.
        modName -- current modname (or None)."""
        #--Data
        self.modName = GPath(modName or u'')
        self.data = bosh.modInfos.table.getColumn('doc')
        self.docEdit = bosh.modInfos.table.getColumn('docEdit')
        self.docType = None
        self.docIsWtxt = False
        #--Clean data
        for key,doc in self.data.items():
            if not isinstance(doc,bolt.Path):
                self.data[key] = GPath(doc)
        #--Singleton
        global docBrowser
        from . import mod_links, app_buttons
        mod_links.docBrowser = app_buttons.docBrowser = docBrowser = self
        #--Window
        pos = settings['bash.modDocs.pos']
        size = settings['bash.modDocs.size']
        wx.Frame.__init__(self, bashFrame, wx.ID_ANY, _(u'Doc Browser'), pos, size,
            style=wx.DEFAULT_FRAME_STYLE)
        self.SetBackgroundColour(wx.NullColour)
        self.SetSizeHints(250,250)
        #--Mod Name
        self.modNameBox = wx.TextCtrl(self,wx.ID_ANY,style=wx.TE_READONLY)
        self.modNameList = wx.ListBox(self,wx.ID_ANY,choices=sorted(x.s for x in self.data.keys()),style=wx.LB_SINGLE|wx.LB_SORT)
        self.modNameList.Bind(wx.EVT_LISTBOX,self.DoSelectMod)
        #wx.EVT_COMBOBOX(self.modNameBox,ID_SELECT,self.DoSelectMod)
        #--Application Icons
        self.SetIcons(Resources.bashDocBrowser)
        #--Set Doc
        self.setButton = button(self,_(u'Set Doc...'),onClick=self.DoSet)
        #--Forget Doc
        self.forgetButton = button(self,_(u'Forget Doc...'),onClick=self.DoForget)
        #--Rename Doc
        self.renameButton = button(self,_(u'Rename Doc...'),onClick=self.DoRename)
        #--Edit Doc
        self.editButton = wx.ToggleButton(self,ID_EDIT,_(u'Edit Doc...'))
        wx.EVT_TOGGLEBUTTON(self.editButton,ID_EDIT,self.DoEdit)
        self.openButton = button(self,_(u'Open Doc...'),onClick=self.DoOpen,tip=_(u'Open doc in external editor.'))
        #--Doc Name
        self.docNameBox = wx.TextCtrl(self,wx.ID_ANY,style=wx.TE_READONLY)
        #--Doc display
        self.plainText = wx.TextCtrl(self,wx.ID_ANY,style=wx.TE_READONLY|wx.TE_MULTILINE|wx.TE_RICH2|wx.SUNKEN_BORDER)
        if bHaveComTypes:
            self.htmlText = wx.lib.iewin.IEHtmlWindow(self,wx.ID_ANY,style=wx.NO_FULL_REPAINT_ON_RESIZE)
            #--Html Back
            bitmap = wx.ArtProvider_GetBitmap(wx.ART_GO_BACK,wx.ART_HELP_BROWSER, (16,16))
            self.prevButton = bitmapButton(self,bitmap,onClick=self.DoPrevPage)
            #--Html Forward
            bitmap = wx.ArtProvider_GetBitmap(wx.ART_GO_FORWARD,wx.ART_HELP_BROWSER, (16,16))
            self.nextButton = bitmapButton(self,bitmap,onClick=self.DoNextPage)
        else:
            self.htmlText = None
            self.prevButton = None
            self.nextButton = None
        #--Events
        wx.EVT_CLOSE(self, self.OnCloseWindow)
        #--Layout
        self.mainSizer = vSizer(
            (hSizer( #--Buttons
                (self.setButton,0,wx.GROW),
                (self.forgetButton,0,wx.GROW),
                (self.renameButton,0,wx.GROW),
                (self.editButton,0,wx.GROW),
                (self.openButton,0,wx.GROW),
                (self.prevButton,0,wx.GROW),
                (self.nextButton,0,wx.GROW),
                ),0,wx.GROW|wx.ALL^wx.BOTTOM,4),
            (hSizer( #--Mod name, doc name
                #(self.modNameBox,2,wx.GROW|wx.RIGHT,4),
                (self.docNameBox,2,wx.GROW),
                ),0,wx.GROW|wx.TOP|wx.BOTTOM,4),
            (self.plainText,3,wx.GROW),
            (self.htmlText,3,wx.GROW),
            )
        sizer = hSizer(
            (vSizer(
                (self.modNameBox,0,wx.GROW),
                (self.modNameList,1,wx.GROW|wx.TOP,4),
                ),0,wx.GROW|wx.TOP|wx.RIGHT,4),
            (self.mainSizer,1,wx.GROW),
            )
        #--Set
        self.SetSizer(sizer)
        self.SetMod(modName)
        self.SetDocType('txt')

    def GetIsWtxt(self,docPath=None):
        """Determines whether specified path is a wtxt file."""
        docPath = docPath or GPath(self.data.get(self.modName,u''))
        if not docPath.exists():
            return False
        try:
            with docPath.open('r',encoding='utf-8-sig') as textFile:
                maText = re.match(ur'^=.+=#\s*$',textFile.readline(),re.U)
            return maText is not None
        except UnicodeDecodeError:
            return False

    def DoPrevPage(self, event):
        """Handle "Back" button click."""
        self.htmlText.GoBack()

    def DoNextPage(self, event):
        """Handle "Next" button click."""
        self.htmlText.GoForward()

    def DoOpen(self,event):
        """Handle "Open Doc" button."""
        docPath = self.data.get(self.modName)
        if not docPath:
            return bell()
        if not docPath.isfile():
            balt.showWarning(self, _(u'The assigned document is not present:')
                             + '\n  ' + docPath.s)
        else:
            docPath.start()

    def DoEdit(self,event):
        """Handle "Edit Doc" button click."""
        self.DoSave()
        editing = self.editButton.GetValue()
        self.docEdit[self.modName] = editing
        self.docIsWtxt = self.GetIsWtxt()
        if self.docIsWtxt:
            self.SetMod(self.modName)
        else:
            self.plainText.SetEditable(editing)

    def DoForget(self,event):
        """Handle "Forget Doc" button click.
        Sets help document for current mod name to None."""
        #--Already have mod data?
        modName = self.modName
        if modName not in self.data:
            return
        index = self.modNameList.FindString(modName.s)
        if index != wx.NOT_FOUND:
            self.modNameList.Delete(index)
        del self.data[modName]
        self.SetMod(modName)

    def DoSelectMod(self,event):
        """Handle mod name combobox selection."""
        self.SetMod(event.GetString())

    def DoSet(self,event):
        """Handle "Set Doc" button click."""
        #--Already have mod data?
        modName = self.modName
        if modName in self.data:
            (docsDir,fileName) = self.data[modName].headTail
        else:
            docsDir = settings['bash.modDocs.dir'] or bosh.dirs['mods']
            fileName = GPath(u'')
        #--Dialog
        path = balt.askOpen(self,_(u'Select doc for %s:') % modName.s,
            docsDir,fileName, u'*.*',mustExist=True)
        if not path: return
        settings['bash.modDocs.dir'] = path.head
        if modName not in self.data:
            self.modNameList.Append(modName.s)
        self.data[modName] = path
        self.SetMod(modName)

    def DoRename(self,event):
        """Handle "Rename Doc" button click."""
        modName = self.modName
        oldPath = self.data[modName]
        (workDir,fileName) = oldPath.headTail
        #--Dialog
        path = balt.askSave(self,_(u'Rename file to:'),workDir,fileName, u'*.*')
        if not path or path == oldPath: return
        #--OS renaming
        path.remove()
        oldPath.moveTo(path)
        if self.docIsWtxt:
            oldHtml, newHtml = (x.root+u'.html' for x in (oldPath,path))
            if oldHtml.exists(): oldHtml.moveTo(newHtml)
            else: newHtml.remove()
        #--Remember change
        self.data[modName] = path
        self.SetMod(modName)

    def DoSave(self):
        """Saves doc, if necessary."""
        if not self.plainText.IsModified(): return
        docPath = self.data.get(self.modName)
        self.plainText.DiscardEdits()
        if not docPath:
            raise BoltError(_(u'Filename not defined.'))
        with docPath.open('w',encoding='utf-8-sig') as out:
            out.write(self.plainText.GetValue())
        if self.docIsWtxt:
            docsDir = bosh.modInfos.dir.join(u'Docs')
            bolt.WryeText.genHtml(docPath, None, docsDir)

    def SetMod(self,modName=None):
        """Sets the mod to show docs for."""
        #--Save Current Edits
        self.DoSave()
        #--New modName
        self.modName = modName = GPath(modName or u'')
        #--ModName
        if modName:
            self.modNameBox.SetValue(modName.s)
            index = self.modNameList.FindString(modName.s)
            self.modNameList.SetSelection(index)
            self.setButton.Enable(True)
        else:
            self.modNameBox.SetValue(u'')
            self.modNameList.SetSelection(wx.NOT_FOUND)
            self.setButton.Enable(False)
        #--Doc Data
        docPath = self.data.get(modName) or GPath(u'')
        docExt = docPath.cext
        self.docNameBox.SetValue(docPath.stail)
        self.forgetButton.Enable(docPath != u'')
        self.renameButton.Enable(docPath != u'')
        #--Edit defaults to false.
        self.editButton.SetValue(False)
        self.editButton.Enable(False)
        self.openButton.Enable(False)
        self.plainText.SetEditable(False)
        self.docIsWtxt = False
        #--View/edit doc.
        if not docPath:
            self.plainText.SetValue(u'')
            self.SetDocType('txt')
        elif not docPath.exists():
            myTemplate = bosh.modInfos.dir.join(u'Docs',u'My Readme Template.txt')
            bashTemplate = bosh.modInfos.dir.join(u'Docs',u'Bash Readme Template.txt')
            if myTemplate.exists():
                template = u''.join(myTemplate.open().readlines())
            elif bashTemplate.exists():
                template = u''.join(bashTemplate.open().readlines())
            else:
                template = u'= $modName '+(u'='*(74-len(modName)))+u'#\n'+docPath.s
            defaultText = string.Template(template).substitute(modName=modName.s)
            self.plainText.SetValue(defaultText)
            self.SetDocType('txt')
            if docExt in (u'.txt',u'.etxt'):
                self.editButton.Enable(True)
                self.openButton.Enable(True)
                editing = self.docEdit.get(modName,True)
                self.editButton.SetValue(editing)
                self.plainText.SetEditable(editing)
            self.docIsWtxt = (docExt == u'.txt')
        elif docExt in (u'.htm',u'.html',u'.mht') and bHaveComTypes:
            self.htmlText.Navigate(docPath.s,0x2) #--0x2: Clear History
            self.SetDocType('html')
        else:
            self.editButton.Enable(True)
            self.openButton.Enable(True)
            editing = self.docEdit.get(modName,False)
            self.editButton.SetValue(editing)
            self.plainText.SetEditable(editing)
            self.docIsWtxt = self.GetIsWtxt(docPath)
            htmlPath = self.docIsWtxt and docPath.root+u'.html'
            if htmlPath and (not htmlPath.exists() or (docPath.mtime > htmlPath.mtime)):
                docsDir = bosh.modInfos.dir.join(u'Docs')
                bolt.WryeText.genHtml(docPath,None,docsDir)
            if not editing and htmlPath and htmlPath.exists() and bHaveComTypes:
                self.htmlText.Navigate(htmlPath.s,0x2) #--0x2: Clear History
                self.SetDocType('html')
            else:
                # Oddly, wxPython's LoadFile function doesn't read unicode correctly,
                # even in unicode builds
                try:
                    with docPath.open('r',encoding='utf-8-sig') as ins:
                        data = ins.read()
                except UnicodeDecodeError:
                    with docPath.open('r') as ins:
                        data = ins.read()
                self.plainText.SetValue(data)
                self.SetDocType('txt')

    #--Set Doc Type
    def SetDocType(self,docType):
        """Shows the plainText or htmlText view depending on document type (i.e. file name extension)."""
        if docType == self.docType:
            return
        sizer = self.mainSizer
        if docType == 'html' and bHaveComTypes:
            sizer.Show(self.plainText,False)
            sizer.Show(self.htmlText,True)
            self.prevButton.Enable(True)
            self.nextButton.Enable(True)
        else:
            sizer.Show(self.plainText,True)
            if bHaveComTypes:
                sizer.Show(self.htmlText,False)
                self.prevButton.Enable(False)
                self.nextButton.Enable(False)
        self.Layout()

    #--Window Closing
    def OnCloseWindow(self, event):
        """Handle window close event.
        Remember window size, position, etc."""
        self.DoSave()
        settings['bash.modDocs.show'] = False
        if not self.IsIconized() and not self.IsMaximized():
            settings['bash.modDocs.pos'] = self.GetPositionTuple()
            settings['bash.modDocs.size'] = self.GetSizeTuple()
        global docBrowser
        docBrowser = None
        self.Destroy()

#------------------------------------------------------------------------------
class ModChecker(wx.Frame):
    """Mod Checker frame."""
    def __init__(self):
        """Intialize."""
        #--Singleton
        global modChecker
        from . import app_buttons
        app_buttons.modChecker = modChecker = self
        #--Window
        pos = settings.get('bash.modChecker.pos',balt.defPos)
        size = settings.get('bash.modChecker.size',(475,500))
        wx.Frame.__init__(self, bashFrame, wx.ID_ANY, _(u'Mod Checker'), pos, size,
            style=wx.DEFAULT_FRAME_STYLE)
        self.SetBackgroundColour(wx.NullColour)
        self.SetSizeHints(250,250)
        self.SetIcons(Resources.bashBlue)
        #--Data
        self.ordered = None
        self.merged = None
        self.imported = None
        #--Text
        if bHaveComTypes:
            self.gTextCtrl = wx.lib.iewin.IEHtmlWindow(self,wx.ID_ANY,style=wx.NO_FULL_REPAINT_ON_RESIZE)
            #--Buttons
            bitmap = wx.ArtProvider_GetBitmap(wx.ART_GO_BACK,wx.ART_HELP_BROWSER, (16,16))
            gBackButton = bitmapButton(self,bitmap,onClick=lambda evt: self.gTextCtrl.GoBack())
            bitmap = wx.ArtProvider_GetBitmap(wx.ART_GO_FORWARD,wx.ART_HELP_BROWSER, (16,16))
            gForwardButton = bitmapButton(self,bitmap,onClick=lambda evt: self.gTextCtrl.GoForward())
        else:
            self.gTextCtrl = wx.TextCtrl(self,wx.ID_ANY,style=wx.TE_READONLY|wx.TE_MULTILINE|wx.TE_RICH2|wx.SUNKEN_BORDER)
            gBackButton = None
            gForwardButton = None
        gUpdateButton = button(self,_(u'Update'),onClick=lambda event: self.CheckMods())
        self.gShowModList = toggleButton(self,_(u'Mod List'),onClick=self.CheckMods)
        self.gShowRuleSets = toggleButton(self,_(u'Rule Sets'),onClick=self.CheckMods)
        self.gShowNotes = toggleButton(self,_(u'Notes'),onClick=self.CheckMods)
        self.gShowConfig = toggleButton(self,_(u'Configuration'),onClick=self.CheckMods)
        self.gShowSuggest = toggleButton(self,_(u'Suggestions'),onClick=self.CheckMods)
        self.gShowCRC = toggleButton(self,_(u'CRCs'),onClick=self.CheckMods)
        self.gShowVersion = toggleButton(self,_(u'Version Numbers'),onClick=self.CheckMods)
        if settings['bash.CBashEnabled']:
            self.gScanDirty = toggleButton(self,_(u'Scan for Dirty Edits'),onClick=self.CheckMods)
        else:
            self.gScanDirty = toggleButton(self,_(u"Scan for UDR's"),onClick=self.CheckMods)
        self.gCopyText = button(self,_(u'Copy Text'),onClick=self.OnCopyText)
        self.gShowModList.SetValue(settings.get('bash.modChecker.showModList',False))
        self.gShowNotes.SetValue(settings.get('bash.modChecker.showNotes',True))
        self.gShowConfig.SetValue(settings.get('bash.modChecker.showConfig',True))
        self.gShowSuggest.SetValue(settings.get('bash.modChecker.showSuggest',True))
        self.gShowCRC.SetValue(settings.get('bash.modChecker.showCRC',False))
        self.gShowVersion.SetValue(settings.get('bash.modChecker.showVersion',True))
        #--Events
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.Bind(wx.EVT_ACTIVATE, self.OnActivate)
        #--Layout
        self.SetSizer(
            vSizer(
                (self.gTextCtrl,1,wx.EXPAND|wx.ALL^wx.BOTTOM,2),
                (hSizer(
                    gBackButton,
                    gForwardButton,
                    (self.gShowModList,0,wx.LEFT,4),
                    (self.gShowRuleSets,0,wx.LEFT,4),
                    (self.gShowNotes,0,wx.LEFT,4),
                    (self.gShowConfig,0,wx.LEFT,4),
                    (self.gShowSuggest,0,wx.LEFT,4),
                    ),0,wx.ALL|wx.EXPAND,4),
                (hSizer(
                    (self.gShowVersion,0,wx.LEFT,4),
                    (self.gShowCRC,0,wx.LEFT,4),
                    (self.gScanDirty,0,wx.LEFT,4),
                    (self.gCopyText,0,wx.LEFT,4),
                    spacer,
                    gUpdateButton,
                    ),0,wx.ALL|wx.EXPAND,4),
                )
            )
        self.CheckMods()

    def OnCopyText(self,event=None):
        """Copies text of report to clipboard."""
        text = u'[spoiler]\n'+self.text+u'[/spoiler]'
        text = re.sub(ur'\[\[.+?\|\s*(.+?)\]\]',ur'\1',text,re.U)
        text = re.sub(u'(__|\*\*|~~)',u'',text,re.U)
        text = re.sub(u'&bull; &bull;',u'**',text,re.U)
        text = re.sub(u'<[^>]+>','',text,re.U)
        balt.copyToClipboard(text)

    def CheckMods(self,event=None):
        """Do mod check."""
        settings['bash.modChecker.showModList'] = self.gShowModList.GetValue()
        settings['bash.modChecker.showRuleSets'] = self.gShowRuleSets.GetValue()
        if not settings['bash.modChecker.showRuleSets']:
            self.gShowNotes.SetValue(False)
            self.gShowConfig.SetValue(False)
            self.gShowSuggest.SetValue(False)
        settings['bash.modChecker.showNotes'] = self.gShowNotes.GetValue()
        settings['bash.modChecker.showConfig'] = self.gShowConfig.GetValue()
        settings['bash.modChecker.showSuggest'] = self.gShowSuggest.GetValue()
        settings['bash.modChecker.showCRC'] = self.gShowCRC.GetValue()
        settings['bash.modChecker.showVersion'] = self.gShowVersion.GetValue()
        #--Cache info from modinfos to support auto-update.
        self.ordered = bosh.modInfos.ordered
        self.merged = bosh.modInfos.merged.copy()
        self.imported = bosh.modInfos.imported.copy()
        #--Do it
        self.text = bosh.configHelpers.checkMods(
            settings['bash.modChecker.showModList'],
            settings['bash.modChecker.showRuleSets'],
            settings['bash.modChecker.showNotes'],
            settings['bash.modChecker.showConfig'],
            settings['bash.modChecker.showSuggest'],
            settings['bash.modChecker.showCRC'],
            settings['bash.modChecker.showVersion'],
            scanDirty=(None,modChecker)[self.gScanDirty.GetValue()]
            )
        if bHaveComTypes:
            logPath = bosh.dirs['saveBase'].join(u'ModChecker.html')
            cssDir = settings.get('balt.WryeLog.cssDir', GPath(u''))
            ins = StringIO.StringIO(self.text+u'\n{{CSS:wtxt_sand_small.css}}')
            with logPath.open('w',encoding='utf-8-sig') as out:
                bolt.WryeText.genHtml(ins,out,cssDir)
            self.gTextCtrl.Navigate(logPath.s,0x2) #--0x2: Clear History
        else:
            self.gTextCtrl.SetValue(self.text)


    def OnActivate(self,event):
        """Handle window activate/deactive. Use for auto-updating list."""
        if (event.GetActive() and (
            self.ordered != bosh.modInfos.ordered or
            self.merged != bosh.modInfos.merged or
            self.imported != bosh.modInfos.imported)
            ):
            self.CheckMods()

    def OnCloseWindow(self, event):
        """Handle window close event.
        Remember window size, position, etc."""
        if not self.IsIconized() and not self.IsMaximized():
            settings['bash.modChecker.pos'] = self.GetPositionTuple()
            settings['bash.modChecker.size'] = self.GetSizeTuple()
        self.Destroy()

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
        bosh.modInfos.refresh(doAutoGroup=True)
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

# Misc Dialogs ----------------------------------------------------------------
#------------------------------------------------------------------------------
class ImportFaceDialog(wx.Dialog):
    """Dialog for importing faces."""
    def __init__(self,parent,id,title,fileInfo,faces):
        #--Data
        self.fileInfo = fileInfo
        if faces and isinstance(faces.keys()[0],(IntType,LongType)):
            self.data = dict((u'%08X %s' % (key,face.pcName),face) for key,face in faces.items())
        else:
            self.data = faces
        self.items = sorted(self.data.keys(),key=string.lower)
        #--GUI
        wx.Dialog.__init__(self,parent,id,title,
            style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        wx.EVT_CLOSE(self, self.OnCloseWindow)
        self.SetSizeHints(550,300)
        #--List Box
        self.list = wx.ListBox(self,wx.ID_OK,choices=self.items,style=wx.LB_SINGLE)
        self.list.SetSizeHints(175,150)
        wx.EVT_LISTBOX(self,wx.ID_OK,self.EvtListBox)
        #--Name,Race,Gender Checkboxes
        self.nameCheck = checkBox(self,_(u'Name'))
        self.raceCheck = checkBox(self,_(u'Race'))
        self.genderCheck = checkBox(self,_(u'Gender'))
        self.statsCheck = checkBox(self,_(u'Stats'))
        self.classCheck = checkBox(self,_(u'Class'))
        flags = bosh.PCFaces.flags(settings.get('bash.faceImport.flags',0x4))
        self.nameCheck.SetValue(flags.name)
        self.raceCheck.SetValue(flags.race)
        self.genderCheck.SetValue(flags.gender)
        self.statsCheck.SetValue(flags.stats)
        self.classCheck.SetValue(flags.iclass)
        #--Name,Race,Gender Text
        self.nameText  = staticText(self,u'-----------------------------')
        self.raceText  = staticText(self,u'')
        self.genderText  = staticText(self,u'')
        self.statsText  = staticText(self,u'')
        self.classText  = staticText(self,u'')
        #--Other
        importButton = button(self,_(u'Import'),onClick=self.DoImport)
        importButton.SetDefault()
        self.picture = balt.Picture(self,350,210,scaling=2)
        #--Layout
        fgSizer = wx.FlexGridSizer(3,2,2,4)
        fgSizer.AddGrowableCol(1,1)
        fgSizer.AddMany([
            self.nameCheck,
            self.nameText,
            self.raceCheck,
            self.raceText,
            self.genderCheck,
            self.genderText,
            self.statsCheck,
            self.statsText,
            self.classCheck,
            self.classText,
            ])
        sizer = hSizer(
            (self.list,1,wx.EXPAND|wx.TOP,4),
            (vSizer(
                self.picture,
                (hSizer(
                    (fgSizer,1),
                    (vSizer(
                        (importButton,0,wx.ALIGN_RIGHT),
                        (button(self,id=wx.ID_CANCEL),0,wx.TOP,4),
                        )),
                    ),0,wx.EXPAND|wx.TOP,4),
                ),0,wx.EXPAND|wx.ALL,4),
            )
        #--Done
        if 'ImportFaceDialog' in balt.sizes:
            self.SetSizer(sizer)
            self.SetSize(balt.sizes['ImportFaceDialog'])
        else:
            self.SetSizerAndFit(sizer)

    def EvtListBox(self,event):
        """Responds to listbox selection."""
        itemDex = event.GetSelection()
        item = self.items[itemDex]
        face = self.data[item]
        self.nameText.SetLabel(face.pcName)
        self.raceText.SetLabel(face.getRaceName())
        self.genderText.SetLabel(face.getGenderName())
        self.statsText.SetLabel(_(u'Health ')+unicode(face.health))
        itemImagePath = bosh.dirs['mods'].join(u'Docs',u'Images','%s.jpg' % item)
        bitmap = (itemImagePath.exists() and
            wx.Bitmap(itemImagePath.s,JPEG)) or None
        self.picture.SetBitmap(bitmap)

    def DoImport(self,event):
        """Imports selected face into save file."""
        selections = self.list.GetSelections()
        if not selections:
            wx.Bell()
            return
        itemDex = selections[0]
        item = self.items[itemDex]
        #--Do import
        flags = bosh.PCFaces.flags()
        flags.hair = flags.eye = True
        flags.name = self.nameCheck.GetValue()
        flags.race = self.raceCheck.GetValue()
        flags.gender = self.genderCheck.GetValue()
        flags.stats = self.statsCheck.GetValue()
        flags.iclass = self.classCheck.GetValue()
        #deprint(flags.getTrueAttrs())
        settings['bash.faceImport.flags'] = int(flags)
        bosh.PCFaces.save_setFace(self.fileInfo,self.data[item],flags)
        balt.showOk(self,_(u'Face imported.'),self.fileInfo.name.s)
        self.EndModal(wx.ID_OK)

    #--Window Closing
    def OnCloseWindow(self, event):
        """Handle window close event.
        Remember window size, position, etc."""
        balt.sizes['ImportFaceDialog'] = self.GetSizeTuple()
        self.Destroy()

class InstallerProject_OmodConfigDialog(wx.Frame):
    """Dialog for editing omod configuration data."""
    def __init__(self,parent,data,project):
        #--Data
        self.data = data
        self.project = project
        self.config = config = data[project].getOmodConfig(project)
        #--GUI
        wx.Frame.__init__(self,parent,wx.ID_ANY,_(u'Omod Config: ')+project.s,
            style=(wx.RESIZE_BORDER | wx.CAPTION | wx.CLIP_CHILDREN |wx.TAB_TRAVERSAL))
        self.SetIcons(Resources.bashBlue)
        self.SetSizeHints(300,300)
        self.SetBackgroundColour(wx.NullColour)
        #--Fields
        self.gName = wx.TextCtrl(self,wx.ID_ANY,config.name)
        self.gVersion = wx.TextCtrl(self,wx.ID_ANY,u'%d.%02d' % (config.vMajor,config.vMinor))
        self.gWebsite = wx.TextCtrl(self,wx.ID_ANY,config.website)
        self.gAuthor = wx.TextCtrl(self,wx.ID_ANY,config.author)
        self.gEmail = wx.TextCtrl(self,wx.ID_ANY,config.email)
        self.gAbstract = wx.TextCtrl(self,wx.ID_ANY,config.abstract,style=wx.TE_MULTILINE)
        #--Max Lenght
        self.gName.SetMaxLength(100)
        self.gVersion.SetMaxLength(32)
        self.gWebsite.SetMaxLength(512)
        self.gAuthor.SetMaxLength(512)
        self.gEmail.SetMaxLength(512)
        self.gAbstract.SetMaxLength(4*1024)
        #--Layout
        fgSizer = wx.FlexGridSizer(0,2,4,4)
        fgSizer.AddGrowableCol(1,1)
        fgSizer.AddMany([
            staticText(self,_(u"Name:")), (self.gName,1,wx.EXPAND),
            staticText(self,_(u"Version:")),(self.gVersion,1,wx.EXPAND),
            staticText(self,_(u"Website:")),(self.gWebsite,1,wx.EXPAND),
            staticText(self,_(u"Author:")),(self.gAuthor,1,wx.EXPAND),
            staticText(self,_(u"Email:")),(self.gEmail,1,wx.EXPAND),
            ])
        sizer = vSizer(
            (fgSizer,0,wx.EXPAND|wx.ALL^wx.BOTTOM,4),
            (staticText(self,_(u"Abstract")),0,wx.LEFT|wx.RIGHT,4),
            (self.gAbstract,1,wx.EXPAND|wx.ALL^wx.BOTTOM,4),
            (hSizer(
                spacer,
                (button(self,id=wx.ID_SAVE,onClick=self.DoSave),0,),
                (button(self,id=wx.ID_CANCEL,onClick=self.DoCancel),0,wx.LEFT,4),
                ),0,wx.EXPAND|wx.ALL,4),
            )
        #--Done
        self.FindWindowById(wx.ID_SAVE).SetDefault()
        self.SetSizerAndFit(sizer)
        self.SetSizer(sizer)
        self.SetSize((350,400))

    #--Save/Cancel
    def DoCancel(self,event):
        """Handle save button."""
        self.Destroy()

    def DoSave(self,event):
        """Handle save button."""
        config = self.config
        #--Text fields
        config.name = self.gName.GetValue().strip()
        config.website = self.gWebsite.GetValue().strip()
        config.author = self.gAuthor.GetValue().strip()
        config.email = self.gEmail.GetValue().strip()
        config.abstract = self.gAbstract.GetValue().strip()
        #--Version
        maVersion = re.match(ur'(\d+)\.(\d+)',self.gVersion.GetValue().strip(),flags=re.U)
        if maVersion:
            config.vMajor,config.vMinor = map(int,maVersion.groups())
        else:
            config.vMajor,config.vMinor = (0,0)
        #--Done
        self.data[self.project].writeOmodConfig(self.project,self.config)
        self.Destroy()

class Mod_BaloGroups_Edit(wx.Dialog):
    """Dialog for editing Balo groups."""
    def __init__(self,parent):
        #--Data
        self.parent = parent
        self.groups = [list(x) for x in bosh.modInfos.getBaloGroups(True)]
        self.removed = set()
        #--GUI
        wx.Dialog.__init__(self,parent,wx.ID_ANY,_(u"Balo Groups"),style=wx.CAPTION|wx.RESIZE_BORDER)
        #--List
        self.gList = wx.ListBox(self,wx.ID_ANY,choices=self.GetItems(),style=wx.LB_SINGLE)
        self.gList.SetSizeHints(125,150)
        self.gList.Bind(wx.EVT_LISTBOX,self.DoSelect)
        #--Bounds
        self.gLowerBounds = spinCtrl(self,u'-10',size=(15,15),min=-10,max=0,onSpin=self.OnSpin)
        self.gUpperBounds = spinCtrl(self,u'10',size=(15,15),min=0,max=10, onSpin=self.OnSpin)
        self.gLowerBounds.SetSizeHints(35,-1)
        self.gUpperBounds.SetSizeHints(35,-1)
        #--Buttons
        self.gAdd = button(self,_(u'Add'),onClick=self.DoAdd)
        self.gRename = button(self,_(u'Rename'),onClick=self.DoRename)
        self.gRemove = button(self,_(u'Remove'),onClick=self.DoRemove)
        self.gMoveEarlier = button(self,_(u'Move Up'),onClick=self.DoMoveEarlier)
        self.gMoveLater = button(self,_(u'Move Down'),onClick=self.DoMoveLater)
        #--Layout
        topLeftCenter= wx.ALIGN_CENTER|wx.LEFT|wx.TOP
        sizer = hSizer(
            (self.gList,1,wx.EXPAND|wx.TOP,4),
            (vSizer(
                (self.gAdd,0,topLeftCenter,4),
                (self.gRename,0,topLeftCenter,4),
                (self.gRemove,0,topLeftCenter,4),
                (self.gMoveEarlier,0,topLeftCenter,4),
                (self.gMoveLater,0,topLeftCenter,4),
                (hsbSizer((self,wx.ID_ANY,_(u'Offsets')),
                    (self.gLowerBounds,1,wx.EXPAND|wx.LEFT|wx.TOP,4),
                    (self.gUpperBounds,1,wx.EXPAND|wx.TOP,4),
                    ),0,wx.LEFT|wx.TOP,4),
                    spacer,
                    (button(self,id=wx.ID_SAVE,onClick=self.DoSave),0,topLeftCenter,4),
                    (button(self,id=wx.ID_CANCEL,onClick=self.DoCancel),0,topLeftCenter|wx.BOTTOM,4),
                ),0,wx.EXPAND|wx.RIGHT,4),
            )
        #--Done
        self.SetSizeHints(200,300)
        className = self.__class__.__name__
        if className in balt.sizes:
            self.SetSizer(sizer)
            self.SetSize(balt.sizes[className])
        else:
            self.SetSizerAndFit(sizer)
        self.Refresh(0)

    #--Support
    def AskNewName(self,message,title):
        """Ask user for new/copy name."""
        newName = (balt.askText(self,message,title) or u'').strip()
        if not newName: return None
        maValid = re.match(u'([a-zA-Z][ _a-zA-Z]+)',newName,flags=re.U)
        if not maValid or maValid.group(1) != newName:
            balt.showWarning(self,
                _(u"Group name must be letters, spaces, underscores only!"),title)
            return None
        elif newName in self.GetItems():
            balt.showWarning(self,_(u"group %s already exists.") % newName,title)
            return None
        elif len(newName) >= 40:
            balt.showWarning(self,_(u"Group names must be less than forty characters."),title)
            return None
        else:
            return newName

    def GetItems(self):
        """Return a list of item strings."""
        return [x[5] for x in self.groups]

    def GetItemLabel(self,index):
        info = self.groups[index]
        lower,upper,group = info[1],info[2],info[5]
        if lower == upper:
            return group
        else:
            return u'%s  %d : %d' % (group,lower,upper)

    def Refresh(self,index):
        """Refresh items in list."""
        labels = [self.GetItemLabel(x) for x in range(len(self.groups))]
        self.gList.Set(labels)
        self.gList.SetSelection(index)
        self.RefreshButtons()

    def RefreshBounds(self,index):
        """Refresh bounds info."""
        if index < 0 or index >= len(self.groups):
            lower,upper = 0,0
        else:
            lower,upper,usedStart,usedStop = self.groups[index][1:5]
        self.gLowerBounds.SetRange(-10,usedStart)
        self.gUpperBounds.SetRange(usedStop-1,10)
        self.gLowerBounds.SetValue(lower)
        self.gUpperBounds.SetValue(upper)

    def RefreshButtons(self,index=None):
        """Updates buttons."""
        if index is None:
            index = (self.gList.GetSelections() or (0,))[0]
        self.RefreshBounds(index)
        usedStart,usedStop = self.groups[index][3:5]
        mutable = index <= len(self.groups) - 3
        self.gAdd.Enable(mutable)
        self.gRename.Enable(mutable)
        self.gRemove.Enable(mutable and usedStart == usedStop)
        self.gMoveEarlier.Enable(mutable and index > 0)
        self.gMoveLater.Enable(mutable and index <= len(self.groups) - 4)
        self.gLowerBounds.Enable(index != len(self.groups) - 2)
        self.gUpperBounds.Enable(index != len(self.groups) - 2)

    #--Event Handling
    def DoAdd(self,event):
        """Adds a new item."""
        title = _(u"Add Balo Group")
        index = (self.gList.GetSelections() or (0,))[0]
        if index < 0 or index >= len(self.groups) - 2: return bell()
        #--Ask for and then check new name
        oldName = self.groups[index][0]
        message = _(u"Name of new group (spaces and letters only):")
        newName = self.AskNewName(message,title)
        if newName:
            self.groups.insert(index+1,[u'',0,0,0,0,newName])
            self.Refresh(index+1)

    def DoMoveEarlier(self,event):
        """Moves selected group up (earlier) in order.)"""
        index = (self.gList.GetSelections() or (0,))[0]
        if index < 1 or index >= (len(self.groups)-2): return bell()
        swapped = [self.groups[index],self.groups[index-1]]
        self.groups[index-1:index+1] = swapped
        self.Refresh(index-1)

    def DoMoveLater(self,event):
        """Moves selected group down (later) in order.)"""
        index = (self.gList.GetSelections() or (0,))[0]
        if index < 0 or index >= (len(self.groups) - 3): return bell()
        swapped = [self.groups[index+1],self.groups[index]]
        self.groups[index:index+2] = swapped
        self.Refresh(index+1)

    def DoRename(self,event):
        """Renames selected item."""
        title = _(u"Rename Balo Group")
        index = (self.gList.GetSelections() or (0,))[0]
        if index < 0 or index >= len(self.groups): return bell()
        #--Ask for and then check new name
        oldName = self.groups[index][5]
        message = _(u"Rename %s to (spaces, letters and underscores only):") % oldName
        newName = self.AskNewName(message,title)
        if newName:
            self.groups[index][5] = newName
            self.gList.SetString(index,self.GetItemLabel(index))

    def DoRemove(self,event):
        """Removes selected item."""
        index = (self.gList.GetSelections() or (0,))[0]
        if index < 0 or index >= len(self.groups): return bell()
        name = self.groups[index][0]
        if name: self.removed.add(name)
        del self.groups[index]
        self.gList.Delete(index)
        self.Refresh(index)

    def DoSelect(self,event):
        """Handle select event."""
        self.Refresh(event.GetSelection())
        self.gList.SetFocus()

    def OnSpin(self,event):
        """Show label editing dialog."""
        index = (self.gList.GetSelections() or (0,))[0]
        self.groups[index][1] = self.gLowerBounds.GetValue()
        self.groups[index][2] = self.gUpperBounds.GetValue()
        self.gList.SetString(index,self.GetItemLabel(index))
        event.Skip()

    #--Save/Cancel
    def DoSave(self,event):
        """Handle save button."""
        balt.sizes[self.__class__.__name__] = self.GetSizeTuple()
        settings['bash.balo.full'] = True
        bosh.modInfos.setBaloGroups(self.groups,self.removed)
        bosh.modInfos.updateAutoGroups()
        bosh.modInfos.refresh()
        modList.RefreshUI()
        self.EndModal(wx.ID_OK)

    def DoCancel(self,event):
        """Handle save button."""
        balt.sizes[self.__class__.__name__] = self.GetSizeTuple()
        self.EndModal(wx.ID_CANCEL)

class CreateNewProject(wx.Dialog):
    def __init__(self,parent=None,id=wx.ID_ANY,title=_(u'Create New Project')):
        wx.Dialog.__init__(self,parent,id,title=_(u'Create New Project'),size=wx.DefaultSize,style=wx.DEFAULT_DIALOG_STYLE)

        #--Build a list of existind directories
        #  The text control will use this to change background color when name collisions occur
        self.existingProjects = [x for x in bosh.dirs['installers'].list() if bosh.dirs['installers'].join(x).isdir()]

        #--Attributes
        self.textName = wx.TextCtrl(self,wx.ID_ANY,_(u'New Project Name-#####'))
        self.checkEsp = wx.CheckBox(self,wx.ID_ANY,_(u'Blank.esp'))
        self.checkEsp.SetValue(True)
        self.checkWizard = wx.CheckBox(self,wx.ID_ANY,_(u'Blank wizard.txt'))
        self.checkWizardImages = wx.CheckBox(self,wx.ID_ANY,_(u'Wizard Images Directory'))
        if not bEnableWizard:
            # pywin32 not installed
            self.checkWizard.Disable()
            self.checkWizardImages.Disable()
        self.checkDocs = wx.CheckBox(self,wx.ID_ANY,_(u'Docs Directory'))
        self.checkScreenshot = wx.CheckBox(self,wx.ID_ANY,_(u'Preview Screenshot(No.ext)(re-enable for BAIT)'))
        self.checkScreenshot.Disable() #Remove this when BAIT gets preview stuff done
        okButton = wx.Button(self,wx.ID_OK)
        cancelButton = wx.Button(self,wx.ID_CANCEL)
        # Panel Layout
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(okButton,0,wx.ALL|wx.ALIGN_CENTER,10)
        hsizer.Add(cancelButton,0,wx.ALL|wx.ALIGN_CENTER,10)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(wx.StaticText(self,wx.ID_ANY,_(u'What do you want to name the New Project?'),style=wx.TE_RICH2),0,wx.ALL|wx.ALIGN_CENTER,10)
        vsizer.Add(self.textName,0,wx.ALL|wx.ALIGN_CENTER|wx.EXPAND,2)
        vsizer.Add(wx.StaticText(self,wx.ID_ANY,_(u'What do you want to add to the New Project?')),0,wx.ALL|wx.ALIGN_CENTER,10)
        vsizer.Add(self.checkEsp,0,wx.ALL|wx.ALIGN_TOP,5)
        vsizer.Add(self.checkWizard,0,wx.ALL|wx.ALIGN_TOP,5)
        vsizer.Add(self.checkWizardImages,0,wx.ALL|wx.ALIGN_TOP,5)
        vsizer.Add(self.checkDocs,0,wx.ALL|wx.ALIGN_TOP,5)
        vsizer.Add(self.checkScreenshot,0,wx.ALL|wx.ALIGN_TOP,5)
        vsizer.Add(wx.StaticLine(self,wx.ID_ANY))
        vsizer.AddStretchSpacer()
        vsizer.Add(hsizer,0,wx.ALIGN_CENTER)
        vsizer.AddStretchSpacer()
        self.SetSizer(vsizer)
        self.SetInitialSize()
        # Event Handlers
        self.textName.Bind(wx.EVT_TEXT,self.OnCheckProjectsColorTextCtrl)
        self.checkEsp.Bind(wx.EVT_CHECKBOX,self.OnCheckBoxChange)
        self.checkWizard.Bind(wx.EVT_CHECKBOX,self.OnCheckBoxChange)
        okButton.Bind(wx.EVT_BUTTON,self.OnClose)
        cancelButton.Bind(wx.EVT_BUTTON,self.OnClose)
        # Dialog Icon Handlers
        self.SetIcon(wx.Icon(bosh.dirs['images'].join(u'diamond_white_off.png').s,PNG))
        self.OnCheckBoxChange(self)

    def OnCheckProjectsColorTextCtrl(self,event):
        projectName = GPath(self.textName.GetValue())
        if projectName in self.existingProjects: #Fill this in. Compare this with the self.existingprojects list
            self.textName.SetBackgroundColour('#FF0000')
            self.textName.SetToolTip(tooltip(_(u'There is already a project with that name!')))
        else:
            self.textName.SetBackgroundColour('#FFFFFF')
            self.textName.SetToolTip(None)
        self.textName.Refresh()

    def OnCheckBoxChange(self, event):
        """ Change the Dialog Icon to represent what the project status will
        be when created. """
        if self.checkEsp.IsChecked():
            if self.checkWizard.IsChecked():
                self.SetIcon(wx.Icon(bosh.dirs['images'].join(u'diamond_white_off_wiz.png').s,PNG))
            else:
                self.SetIcon(wx.Icon(bosh.dirs['images'].join(u'diamond_white_off.png').s,PNG))
        else:
            self.SetIcon(wx.Icon(bosh.dirs['images'].join(u'diamond_grey_off.png').s,PNG))

    def OnClose(self,event):
        """ Create the New Project and add user specified extras. """
        if event.GetId() == wx.ID_CANCEL:
            event.Skip()
            return

        projectName = GPath(self.textName.GetValue())
        projectDir = bosh.dirs['installers'].join(projectName)

        if projectDir.exists():
            balt.showError(self,_(u'There is already a project with that name!')
                                + u'\n' +
                                _(u'Pick a different name for the project and try again.'))
            return
        event.Skip()

        # Create project in temp directory, so we can move it via
        # Shell commands (UAC workaround)
        tempDir = bolt.Path.tempDir(u'WryeBash_')
        tempProject = tempDir.join(projectName)
        extrasDir = bosh.dirs['templates'].join(bush.game.fsName)
        if self.checkEsp.IsChecked():
            # Copy blank esp into project
            fileName = u'Blank, %s.esp' % bush.game.fsName
            extrasDir.join(fileName).copyTo(tempProject.join(fileName))
        if self.checkWizard.IsChecked():
            # Create empty wizard.txt
            wizardPath = tempProject.join(u'wizard.txt')
            with wizardPath.open('w',encoding='utf-8') as out:
                out.write(u'; %s BAIN Wizard Installation Script\n' % projectName)
        if self.checkWizardImages.IsChecked():
            # Create 'Wizard Images' directory
            tempProject.join(u'Wizard Images').makedirs()
        if self.checkDocs.IsChecked():
            #Create the 'Docs' Directory
            tempProject.join(u'Docs').makedirs()
        if self.checkScreenshot.IsChecked():
            #Copy the dummy default 'Screenshot' into the New Project
            extrasDir.join(u'Screenshot').copyTo(tempProject.join(u'Screenshot'))

        # Move into the target location
        try:
            balt.shellMove(tempProject,projectDir,self,False,False,False)
        except:
            pass
        finally:
            tempDir.rmtree(tempDir.s)

        # Move successfull
        self.fullRefresh = False
        gInstallers.refreshed = False
        gInstallers.fullRefresh = self.fullRefresh
        gInstallers.OnShow()

# Links -----------------------------------------------------------------
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

# Initialization --------------------------------------------------------------
from .gui_patchers import initPatchers
def InitSettings(): # this must run first !
    """Initializes settings dictionary for bosh and basher."""
    bosh.initSettings()
    global settings
    balt._settings = bosh.settings
    balt.sizes = bosh.settings.getChanged('bash.window.sizes',{})
    settings = bosh.settings
    settings.loadDefaults(settingDefaults) # TODO(ut) this is called in bosh.initSettings() also !
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

from .links import * # TODO(ut): move this to links.py - only import InitLinks
def InitLinks():
    """Call other link initializers."""
    InitStatusBar()
    InitSettingsLinks()
    InitMasterLinks()
    InitInstallerLinks()
    InitINILinks()
    InitModLinks()
    InitSaveLinks()
    InitScreenLinks()
    InitMessageLinks()
    InitPeopleLinks()
    #InitBSALinks()

# Main ------------------------------------------------------------------------
if __name__ == '__main__':
    print _(u'Compiled')
