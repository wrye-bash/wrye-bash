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
#  Wrye Bash copyright (C) 2005, 2006, 2007, 2008, 2009 Wrye
#
# =============================================================================

"""This module provides the GUI interface for Wrye Bash. (However, the Wrye
Bash application is actually launched by the bash module.)

The module is generally organized starting with lower level elements, working
up to higher level elements (up the BashApp). This is followed by definition
of menus and buttons classes, and finally by a several initialization functions.

Non-GUI objects and functions are provided by the bosh module. Of those, the
primary objects used are the plugins, modInfos and saveInfos singletons -- each
representing external data structures (the plugins.txt file and the Data and
Saves directories respectively). Persistent storage for the app is primarily
provided through the settings singleton (however the modInfos singleton also
has its own data store)."""

# Imports ---------------------------------------------------------------------
#--Localization
#..Handled by bosh, so import that.
import bush
import bosh
import bolt
import barb

from bosh import formatInteger,formatDate
from bolt import BoltError, AbstractError, ArgumentError, StateError, UncodedError, CancelError
from bolt import _, LString, Unicode, Encode, GPath, SubProgress, deprint, delist
from cint import *
startupinfo = bolt.startupinfo

#--Python
import ConfigParser
import cStringIO
import StringIO
import copy
import os
import re
import shutil
import string
import struct
import sys
import textwrap
import time
import subprocess
from types import *
from operator import attrgetter,itemgetter

#--wxPython
import wx
import wx.gizmos
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

#--Balt
import balt
from balt import tooltip, fill, bell
from balt import bitmapButton, button, toggleButton, checkBox, staticText, spinCtrl, textCtrl
from balt import leftSash, topSash
from balt import spacer, hSizer, vSizer, hsbSizer, vsbSizer
from balt import colors, images, Image
from balt import Links, Link, SeparatorLink, MenuLink
from balt import ListCtrl

# BAIN wizard support, requires PyWin32, so import will fail if it's not installed
try:
    import belt
    bEnableWizard = True
except ImportError:
    bEnableWizard = False
    if bolt.deprintOn:
        raise

#  - Make sure that python root directory is in PATH, so can access dll's.
if sys.prefix not in set(os.environ['PATH'].split(';')):
    os.environ['PATH'] += ';'+sys.prefix

appRestart = False # restart Bash if true

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
SettingsMenu = None

# Settings --------------------------------------------------------------------
settings = None

#--Load config/defaults
settingDefaults = {
    #--Basics
    'bash.version': 0,
    'bash.readme': (0,'0'),
    'bash.CBashEnabled': False,
    'bash.backupPath': None,
    'bash.framePos': (-1,-1),
    'bash.frameSize': (600,500),
    'bash.frameSize.min': (400,600),
    'bash.page':1,
    #--BSA Redirection
    'bash.bsaRedirection':False,
    #--Wrye Bash: Load Lists
    'bash.loadLists.data': {
        'Bethesda ESMs': [
            GPath('Oblivion.esm'),
            ],
        },
    #--Wrye Bash: Statistics
    'bash.fileStats.cols': ['Type','Count','Size'],
    'bash.fileStats.sort': 'Type',
    'bash.fileStats.colReverse': {
        'Count':1,
        'Size':1,
        },
    'bash.fileStats.colWidths': {
        'Type':50,
        'Count':50,
        'Size':75,
        },
    'bash.fileStats.colAligns': {
        'Count':1,
        'Size':1,
        },
    #--Wrye Bash: Group and Rating
    'bash.mods.autoGhost':False,
    'bash.mods.groups': [x[0] for x in bush.baloGroups],
    'bash.mods.ratings': ['+','1','2','3','4','5','=','~'],
    'bash.balo.autoGroup': True,
    'bash.balo.full': False,
    #--Wrye Bash: Col (Sort) Names
    'bash.colNames': {
        'Author': _('Author'),
        'Cell': _('Cell'),
        'Current Order': _('Current LO'),
        'Date': _('Date'),
        'Day': _('Day'),
        'File': _('File'),
        'Files': _('Files'),
        'Group': _('Group'),
        'Header': _('Header'),
        'Installer':_('Installer'),
        'Karma': _('Karma'),
        'Load Order': _('Load Order'),
        'Modified': _('Modified'),
        'Name': _('Name'),
        'Num': _('MI'),
        'Order': _('Order'),
        'Package': _('Package'),
        'PlayTime':_('Hours'),
        'Player': _('Player'),
        'Rating': _('Rating'),
        'Rating':_('Rating'),
        'Save Order': _('Save Order'),
        'Size': _('Size'),
        'Status': _('Status'),
        'Subject': _('Subject'),
        },
    #--Wrye Bash: Masters
    'bash.masters.cols': ['File','Num', 'Current Order'],
    'bash.masters.esmsFirst': 1,
    'bash.masters.selectedFirst': 0,
    'bash.masters.sort': 'Save Order',
    'bash.masters.colReverse': {},
    'bash.masters.colWidths': {
        'File':80,
        'Num':30,
        'Current Order':60,
        },
    'bash.masters.colAligns': {
        'Save Order':1,
        },
    #--Wrye Bash: Mod Docs
    'bash.modDocs.show': False,
    'bash.modDocs.size': (300,400),
    'bash.modDocs.pos': wx.DefaultPosition,
    'bash.modDocs.dir': None,
    #--Installers
    'bash.installers.cols': ['Package','Order','Modified','Size','Files'],
    'bash.installers.colReverse': {},
    'bash.installers.sort': 'Package',
    'bash.installers.colWidths': {
        'Package': 100,
        'Order': 10,
        'Modified': 60,
        'Size': 40,
        'Files': 20,
        },
    'bash.installers.colAligns': {
        'Order': 1,
        'Modified': 1,
        'Size': 1,
        'Files': 1,
        },
    'bash.installers.page':0,
    'bash.installers.enabled': True,
    'bash.installers.autoAnneal': True,
    'bash.installers.autoWizard':False,
    'bash.installers.wizardOverlay':True,
    'bash.installers.fastStart': True,
    'bash.installers.autoRefreshBethsoft': False,
    'bash.installers.autoRefreshProjects': True,
    'bash.installers.removeEmptyDirs':True,
    'bash.installers.skipScreenshots':False,
    'bash.installers.skipImages':False,
    'bash.installers.skipDocs':False,
    'bash.installers.skipDistantLOD':False,
    'bash.installers.skipLandscapeLODMeshes':False,
    'bash.installers.skipLandscapeLODTextures':False,
    'bash.installers.skipLandscapeLODNormals':False,
    'bash.installers.allowOBSEPlugins':False,
    'bash.installers.sortProjects':True,
    'bash.installers.sortActive':False,
    'bash.installers.sortStructure':False,
    'bash.installers.conflictsReport.showLower':True,
    'bash.installers.conflictsReport.showInactive':False,
    'bash.installers.goodDlls':{},
    'bash.installers.badDlls':{},
    'bash.installers.onDropFiles.action':None,
    'bash.installers.commentsSplitterSashPos':0,
    #--Wrye Bash: Wizards
    'bash.wizard.size': (600,500),
    'bash.wizard.pos': wx.DefaultPosition,
    #--Wrye Bash: INI Tweaks
    'bash.ini.cols': ['File','Installer'],
    'bash.ini.sort': 'File',
    'bash.ini.colReverse': {},
    'bash.ini.sortValid': True,
    'bash.ini.colWidths': {
        'File':200,
        'Installer':100,
        },
    'bash.ini.colAligns': {},
    'bash.ini.choices': {},
    'bash.ini.choice': 0,
    #--Wrye Bash: Mods
    'bash.mods.cols': ['File','Load Order','Rating','Group','Installer','Modified','Size','Author'],
    'bash.mods.esmsFirst': 1,
    'bash.mods.selectedFirst': 0,
    'bash.mods.sort': 'File',
    'bash.mods.colReverse': {},
    'bash.mods.colWidths': {
        'Author':100,
        'File':200,
        'Group':20,
        'Installer':100,
        'Load Order':20,
        'Modified':150,
        'Rating':20,
        'Size':75,
        },
    'bash.mods.colAligns': {
        'Size':1,
        'Load Order':1,
        },
    'bash.mods.renames': {},
    'bash.mods.scanDirty': False,
    #--Wrye Bash: Saves
    'bash.saves.cols': ['File','Modified','Size','PlayTime','Player','Cell'],
    'bash.saves.sort': 'Modified',
    'bash.saves.colReverse': {
        'Modified':1,
        },
    'bash.saves.colWidths': {
        'File':150,
        'Modified':150,
        'Size':75,
        'PlayTime':75,
        'Player':100,
        'Cell':150,
        },
    'bash.saves.colAligns': {
        'Size':1,
        'PlayTime':1,
        },
    #Wrye Bash: BSAs
    'bash.BSAs.cols': ['File','Modified','Size'],
    'bash.BSAs.colAligns': {
        'Size':1,
        'Modified':1,
        },
    'bash.BSAs.colReverse': {
        'Modified':1,
        },
    'bash.BSAs.colWidths': {
        'File':150,
        'Modified':150,
        'Size':75,
        },
    'bash.BSAs.sort': 'File',
    #--Wrye Bash: Replacers
    'bash.replacers.show':False,
    'bash.replacers.cols': ['File'],
    'bash.replacers.sort': 'File',
    'bash.replacers.colReverse': {
        },
    'bash.replacers.colWidths': {
        'File':150,
        },
    'bash.replacers.colAligns': {},
    'bash.replacers.autoChecked':False,
    #--Wrye Bash: Screens
    'bash.screens.cols': ['File'],
    'bash.screens.sort': 'File',
    'bash.screens.colReverse': {
        'Modified':1,
        },
    'bash.screens.colWidths': {
        'File':150,
        'Modified':150,
        'Size':75,
        },
    'bash.screens.colAligns': {},
    'bash.screens.jpgQuality': 95,
    'bash.screens.jpgCustomQuality': 75,
    #--Wrye Bash: Messages
    'bash.messages.cols': ['Subject','Author','Date'],
    'bash.messages.sort': 'Date',
    'bash.messages.colReverse': {
        },
    'bash.messages.colWidths': {
        'Subject':250,
        'Author':100,
        'Date':150,
        },
    'bash.messages.colAligns': {},
    #--Wrye Bash: People
    'bash.people.cols': ['Name','Karma','Header'],
    'bash.people.sort': 'Name',
    'bash.people.colReverse': {},
    'bash.people.colWidths': {
        'Name': 30,
        'Karma': 30,
        'Header': 30,
        },
    'bash.people.colAligns': {
        'Karma': 1,
        },
    #--Tes4View/Edit/Trans
    'tes4View.iKnowWhatImDoing':False,
    #--BOSS:
    'BOSS.ClearLockTimes':False,
    'BOSS.AlwaysUpdate':False,
    }

if bolt.bUseUnicode:
    stringBuffer = StringIO.StringIO
else:
    stringBuffer = cStringIO.StringIO

# Exceptions ------------------------------------------------------------------
class BashError(BoltError): pass

# Gui Ids ---------------------------------------------------------------------
#------------------------------------------------------------------------------
# Constants
#--Indexed
wxListAligns = [wx.LIST_FORMAT_LEFT, wx.LIST_FORMAT_RIGHT, wx.LIST_FORMAT_CENTRE]

#--Generic
ID_RENAME = 6000
ID_SET    = 6001
ID_SELECT = 6002
ID_BROWSER = 6003
#ID_NOTES  = 6004
ID_EDIT   = 6005
ID_BACK   = 6006
ID_NEXT   = 6007

#--File Menu
ID_REVERT_BACKUP = 6100
ID_REVERT_FIRST  = 6101
ID_BACKUP_NOW    = 6102

#--Label Menus
ID_LOADERS   = balt.IdList(10000, 90,'SAVE','EDIT','NONE')
ID_GROUPS    = balt.IdList(10100,290,'EDIT','NONE')
ID_RATINGS   = balt.IdList(10400, 90,'EDIT','NONE')
ID_PROFILES  = balt.IdList(10500, 90,'EDIT','DEFAULT')
ID_PROFILES2 = balt.IdList(10700, 90,'EDIT','DEFAULT') #Needed for Save_Move()
ID_TAGS      = balt.IdList(10600, 90,'AUTO','COPY')

# Images ----------------------------------------------------------------------
#------------------------------------------------------------------------------
class ColorChecks(balt.ImageList):
    """ColorChecks ImageList. Used by several List classes."""
    def __init__(self):
        balt.ImageList.__init__(self,16,16)
        for state in ('on','off','inc','imp'):
            for status in ('purple','blue','green','orange','yellow','red'):
                shortKey = status+'.'+state
                imageKey = 'checkbox.'+shortKey
                file = GPath(r'images/checkbox_'+status+'_'+state+'.png')
                image = images[imageKey] = Image(file,wx.BITMAP_TYPE_PNG)
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

#--Image lists
colorChecks = ColorChecks()
karmacons = balt.ImageList(16,16)
karmacons.data.extend({
    'karma+5': Image(r'images/checkbox_purple_inc.png',wx.BITMAP_TYPE_PNG),
    'karma+4': Image(r'images/checkbox_blue_inc.png',wx.BITMAP_TYPE_PNG),
    'karma+3': Image(r'images/checkbox_blue_inc.png',wx.BITMAP_TYPE_PNG),
    'karma+2': Image(r'images/checkbox_green_inc.png',wx.BITMAP_TYPE_PNG),
    'karma+1': Image(r'images/checkbox_green_inc.png',wx.BITMAP_TYPE_PNG),
    'karma+0': Image(r'images/checkbox_white_off.png',wx.BITMAP_TYPE_PNG),
    'karma-1': Image(r'images/checkbox_yellow_off.png',wx.BITMAP_TYPE_PNG),
    'karma-2': Image(r'images/checkbox_yellow_off.png',wx.BITMAP_TYPE_PNG),
    'karma-3': Image(r'images/checkbox_orange_off.png',wx.BITMAP_TYPE_PNG),
    'karma-4': Image(r'images/checkbox_orange_off.png',wx.BITMAP_TYPE_PNG),
    'karma-5': Image(r'images/checkbox_red_off.png',wx.BITMAP_TYPE_PNG),
    }.items())
installercons = balt.ImageList(16,16)
installercons.data.extend({
    #--Off/Archive
    'off.green':  Image(r'images/checkbox_green_off.png',wx.BITMAP_TYPE_PNG),
    'off.grey':   Image(r'images/checkbox_grey_off.png',wx.BITMAP_TYPE_PNG),
    'off.red':    Image(r'images/checkbox_red_off.png',wx.BITMAP_TYPE_PNG),
    'off.white':  Image(r'images/checkbox_white_off.png',wx.BITMAP_TYPE_PNG),
    'off.orange': Image(r'images/checkbox_orange_off.png',wx.BITMAP_TYPE_PNG),
    'off.yellow': Image(r'images/checkbox_yellow_off.png',wx.BITMAP_TYPE_PNG),
    #--Off/Archive - Wizard
    'off.green.wiz':    Image(r'images/checkbox_green_off_wiz.png',wx.BITMAP_TYPE_PNG),
    #grey
    'off.red.wiz':      Image(r'images/checkbox_red_off_wiz.png',wx.BITMAP_TYPE_PNG),
    'off.white.wiz':    Image(r'images/checkbox_white_off_wiz.png',wx.BITMAP_TYPE_PNG),
    'off.orange.wiz':   Image(r'images/checkbox_orange_off_wiz.png',wx.BITMAP_TYPE_PNG),
    'off.yellow.wiz':   Image(r'images/checkbox_yellow_off_wiz.png',wx.BITMAP_TYPE_PNG),
    #--On/Archive
    'on.green':  Image(r'images/checkbox_green_inc.png',wx.BITMAP_TYPE_PNG),
    'on.grey':   Image(r'images/checkbox_grey_inc.png',wx.BITMAP_TYPE_PNG),
    'on.red':    Image(r'images/checkbox_red_inc.png',wx.BITMAP_TYPE_PNG),
    'on.white':  Image(r'images/checkbox_white_inc.png',wx.BITMAP_TYPE_PNG),
    'on.orange': Image(r'images/checkbox_orange_inc.png',wx.BITMAP_TYPE_PNG),
    'on.yellow': Image(r'images/checkbox_yellow_inc.png',wx.BITMAP_TYPE_PNG),
    #--On/Archive - Wizard
    'on.green.wiz':  Image(r'images/checkbox_green_inc_wiz.png',wx.BITMAP_TYPE_PNG),
    #grey
    'on.red.wiz':    Image(r'images/checkbox_red_inc_wiz.png',wx.BITMAP_TYPE_PNG),
    'on.white.wiz':  Image(r'images/checkbox_white_inc_wiz.png',wx.BITMAP_TYPE_PNG),
    'on.orange.wiz': Image(r'images/checkbox_orange_inc_wiz.png',wx.BITMAP_TYPE_PNG),
    'on.yellow.wiz': Image(r'images/checkbox_yellow_inc_wiz.png',wx.BITMAP_TYPE_PNG),
    #--Off/Directory
    'off.green.dir':  Image(r'images/diamond_green_off.png',wx.BITMAP_TYPE_PNG),
    'off.grey.dir':   Image(r'images/diamond_grey_off.png',wx.BITMAP_TYPE_PNG),
    'off.red.dir':    Image(r'images/diamond_red_off.png',wx.BITMAP_TYPE_PNG),
    'off.white.dir':  Image(r'images/diamond_white_off.png',wx.BITMAP_TYPE_PNG),
    'off.orange.dir': Image(r'images/diamond_orange_off.png',wx.BITMAP_TYPE_PNG),
    'off.yellow.dir': Image(r'images/diamond_yellow_off.png',wx.BITMAP_TYPE_PNG),
    #--Off/Directory - Wizard
    'off.green.dir.wiz':  Image(r'images/diamond_green_off_wiz.png',wx.BITMAP_TYPE_PNG),
    #grey
    'off.red.dir.wiz':    Image(r'images/diamond_red_off_wiz.png',wx.BITMAP_TYPE_PNG),
    'off.white.dir.wiz':  Image(r'images/diamond_white_off_wiz.png',wx.BITMAP_TYPE_PNG),
    'off.orange.dir.wiz': Image(r'images/diamond_orange_off_wiz.png',wx.BITMAP_TYPE_PNG),
    'off.yellow.dir.wiz': Image(r'images/diamond_yellow_off_wiz.png',wx.BITMAP_TYPE_PNG),
    #--On/Directory
    'on.green.dir':  Image(r'images/diamond_green_inc.png',wx.BITMAP_TYPE_PNG),
    'on.grey.dir':   Image(r'images/diamond_grey_inc.png',wx.BITMAP_TYPE_PNG),
    'on.red.dir':    Image(r'images/diamond_red_inc.png',wx.BITMAP_TYPE_PNG),
    'on.white.dir':  Image(r'images/diamond_white_inc.png',wx.BITMAP_TYPE_PNG),
    'on.orange.dir': Image(r'images/diamond_orange_inc.png',wx.BITMAP_TYPE_PNG),
    'on.yellow.dir': Image(r'images/diamond_yellow_inc.png',wx.BITMAP_TYPE_PNG),
    #--On/Directory - Wizard
    'on.green.dir.wiz':  Image(r'images/diamond_green_inc_wiz.png',wx.BITMAP_TYPE_PNG),
    #grey
    'on.red.dir.wiz':    Image(r'images/diamond_red_inc_wiz.png',wx.BITMAP_TYPE_PNG),
    'on.white.dir.wiz':  Image(r'images/diamond_white_off_wiz.png',wx.BITMAP_TYPE_PNG),
    'on.orange.dir.wiz': Image(r'images/diamond_orange_inc_wiz.png',wx.BITMAP_TYPE_PNG),
    'on.yellow.dir.wiz': Image(r'images/diamond_yellow_inc_wiz.png',wx.BITMAP_TYPE_PNG),
    #--Broken
    'corrupt':   Image(r'images/red_x.png',wx.BITMAP_TYPE_PNG),
    }.items())

#--Icon Bundles
bashRed = None
bashBlue = None
bashDocBrowser = None
bashMonkey = None

# Windows ---------------------------------------------------------------------
#------------------------------------------------------------------------------
class NotebookPanel(wx.Panel):
    """Parent class for notebook panels."""

    def SetStatusCount(self):
        """Sets status bar count field."""
        statusBar.SetStatusText('',2)

    def OnShow(self):
        """To be called when particular panel is changed to and/or shown for first time.
        Default version does nothing, but derived versions might update data."""
        self.SetStatusCount()

    def OnCloseWindow(self):
        """To be called when containing frame is closing. Use for saving data, scrollpos, etc."""
        pass

#------------------------------------------------------------------------------
class SashPanel(NotebookPanel):
    """Subclass of Notebook Panel, designed for two pane panel."""
    def __init__(self,parent,sashPosKey=None,sashGravity=0.5,sashPos=0,mode=wx.VERTICAL):
        """Initialize."""
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        splitter = wx.gizmos.ThinSplitterWindow(self, wx.ID_ANY, style=wx.BORDER_NONE|wx.SP_LIVE_UPDATE|wx.FULL_REPAINT_ON_RESIZE)
        self.left = wx.Panel(splitter)
        self.right = wx.Panel(splitter)
        if mode == wx.VERTICAL:
            splitter.SplitVertically(self.left, self.right)
        else:
            splitter.SplitHorizontally(self.left, self.right)
        splitter.SetSashGravity(sashGravity)
        sashPos = settings.get(sashPosKey, 0) or sashPos
        splitter.SetSashPosition(sashPos)
        if sashPosKey is not None:
            self.sashPosKeyKey = sashPosKey
        splitter.Bind(wx.EVT_SPLITTER_DCLICK, self.OnDClick)
        splitter.SetMinimumPaneSize(50)
        sizer = vSizer(
            (splitter,1,wx.EXPAND),
            )
        self.SetSizer(sizer)

    def OnDClick(self, event):
        """Don't allow unsplitting"""
        event.Veto()

    def OnWindowClose(self, event):
        splitter = self.right.GetParent()
        if hasattr(self, 'sashPosKey'):
            settings[self.sashPosKey] = splitter.GetSashPosition()
        event.Skip()

class SashTankPanel(NotebookPanel):
    """Subclass of a notebook panel designed for a two pane tank panel."""
    def __init__(self,data,parent):
        """Initialize."""
        wx.Panel.__init__(self, parent,-1)
        self.data = data
        self.detailsItem = None
        sashPos = data.getParam('sashPos',200)
        self.left = leftSash(self,defaultSize=(sashPos,100),onSashDrag=self.OnSashDrag)
        self.right = wx.Panel(self,style=wx.NO_BORDER)
        #--Events
        self.Bind(wx.EVT_SIZE,self.OnSize)

    def OnShow(self):
        """Panel is shown. Update self.data."""
        if self.gList.data.refresh():
            self.gList.RefreshUI()
        self.SetStatusCount()

    def OnSashDrag(self,event):
        """Handle sash moved."""
        wMin,wMax = 80,self.GetSizeTuple()[0]-80
        sashPos = max(wMin,min(wMax,event.GetDragRect().width))
        self.left.SetDefaultSize((sashPos,10))
        wx.LayoutAlgorithm().LayoutWindow(self, self.right)
        self.data.setParam('sashPos',sashPos)

    def OnSize(self,event=None):
        wx.LayoutAlgorithm().LayoutWindow(self, self.right)

    def OnCloseWindow(self):
        """To be called when containing frame is closing. Use for saving data, scrollpos, etc."""
        self.SaveDetails()
        self.data.save()

    def GetDetailsItem(self):
        """Returns item currently being shown in details view."""
        return self.detailsItem

#------------------------------------------------------------------------------
class List(wx.Panel):
    def __init__(self,parent,id=-1,ctrlStyle=(wx.LC_REPORT | wx.LC_SINGLE_SEL),
                 dndFiles=False, dndList=False, dndColumns=[]):
        wx.Panel.__init__(self,parent,id, style=wx.WANTS_CHARS)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        self.SetSizeHints(-1,50)
        self.dndColumns = dndColumns
        #--ListCtrl
        listId = self.listId = wx.NewId()
        self.list = ListCtrl(self, listId, style=ctrlStyle,
                             dndFiles=dndFiles, dndList=dndList,
                             fnDndAllow=self.dndAllow, fnDropFiles=self.OnDropFiles, fnDropIndexes=self.OnDropIndexes)
        self.checkboxes = colorChecks
        self.mouseItem = None
        self.mouseTexts = {}
        self.mouseTextPrev = ''
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
        wx.EVT_LIST_COL_END_DRAG(self,listId, self.OnColumnResize)
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
        if col not in self.dndColumns: return False
        return True
    def OnDropFiles(self, x, y, filenames): raise AbstractError
    def OnDropIndexes(self, indexes, newPos): raise AbstractError

    #--Items ----------------------------------------------
    #--Populate Columns
    def PopulateColumns(self):
        """Create/name columns in ListCtrl."""
        cols = self.cols
        self.numCols = len(cols)
        for colDex in range(self.numCols):
            colKey = cols[colDex]
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
        for itemDex in range(len(self.items)):
            mode = int(itemDex >= listItemCount)
            self.PopulateItem(itemDex,mode,selected)
        #--Delete items?
        while self.list.GetItemCount() > len(self.items):
            self.list.DeleteItem(self.list.GetItemCount()-1)

    def ClearSelected(self):
        for itemDex in range(self.list.GetItemCount()):
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

    def DeleteSelected(self):
        """Deletes selected items."""
        items = self.GetSelected()
        if items:
            message = _(r'Delete these items? This operation cannot be undone.')
            message += '\n* ' + '\n* '.join(x.s for x in sorted(items))
            if balt.askYes(self,message,_('Delete Items')):
                for item in items:
                    self.data.delete(item)
                self.RefreshUI()

    def checkUncheckMod(self, *mods):
        removed = []
        for item in mods:
            if item in removed: continue
            oldFiles = bosh.modInfos.ordered[:]
            fileName = GPath(item)
            #--Unselect?
            if self.data.isSelected(fileName):
                self.data.unselect(fileName)
                changed = bolt.listSubtract(oldFiles,bosh.modInfos.ordered)
                if len(changed) > (fileName in changed):
                    changed.remove(fileName)
                    changed = [x.s for x in changed]
                    removed += changed
                    balt.showList(self,_('${count} Children deactivated:'),changed,10,_("%s") % fileName.s)
            #--Select?
            else:
                try:
                    self.data.select(fileName)
                    changed = bolt.listSubtract(bosh.modInfos.ordered,oldFiles)
                    if len(changed) > ((fileName in changed) + (GPath('Oblivion.esm') in changed)):
                        changed.remove(fileName)
                        changed = [x.s for x in changed]
                        balt.showList(self,_('${count} Masters activated:'),changed,10,_("%s") % fileName.s)
                except bosh.PluginsFullError:
                    balt.showError(self,_("Unable to add mod %s because load list is full." )
                        % (fileName.s,))
                    return
        #--Refresh
        self.RefreshUI()
        #--Mark sort as dirty
        if self.selectedFirst:
            self.sortDirty = 1

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
        return (col,reverse)

    #--Event Handlers -------------------------------------
    def OnMouse(self,event):
        """Check mouse motion to detect right click event."""
        if event.Moving():
            (mouseItem,mouseHitFlag) = self.list.HitTest(event.GetPosition())
            if mouseItem != self.mouseItem:
                self.mouseItem = mouseItem
                self.MouseEnteredItem(mouseItem)
        elif event.Leaving() and self.mouseItem != None:
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
        colDex = event.GetColumn()
        colName = self.cols[colDex]
        width = self.list.GetColumnWidth(colDex)
        if width < 5:
            width = 5
            self.list.SetColumnWidth(colDex, 5)
            event.Veto()
            self.list.resizeLastColumn(0)
        else:
            event.Skip()
        self.colWidths[colName] = width

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

    def __init__(self,parent,fileInfo):
        self.parent = parent
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
        List.__init__(self,parent,-1,ctrlStyle=(wx.LC_REPORT|wx.LC_SINGLE_SEL|wx.LC_EDIT_LABELS))
        wx.EVT_LIST_END_LABEL_EDIT(self,self.listId,self.OnLabelEdited)
        #--Image List
        checkboxesIL = self.checkboxes.GetImageList()
        self.list.SetImageList(checkboxesIL,wx.IMAGE_LIST_SMALL)

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
        self.SortItems()
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
                if masterName == 'Oblivion.esm':
                    voCurrent = bosh.modInfos.voCurrent
                    if voCurrent: value += ' ['+voCurrent+']'
            elif col == 'Num':
                value = '%02X' % (self.fileOrderItems.index(itemId),)
            elif col == 'Current Order':
                #print itemId
                value = '%02X' % (self.loadOrderNames.index(masterName),)
            #--Insert/Set Value
            if mode and (colDex == 0):
                self.list.InsertStringItem(itemDex, value)
            else:
                self.list.SetStringItem(itemDex, colDex, value)
        #--Font color
        item = self.list.GetItem(itemDex)
        if masterInfo.isEsm():
            item.SetTextColour(wx.BLUE)
        else:
            item.SetTextColour(wx.BLACK)
        #--Text BG
        if masterInfo.hasActiveTimeConflict():
            item.SetBackgroundColour(colors['bash.doubleTime.load'])
        elif masterInfo.isExOverLoaded():
            item.SetBackgroundColour(colors['bash.exOverLoaded'])
        elif masterInfo.hasTimeConflict():
            item.SetBackgroundColour(colors['bash.doubleTime.exists'])
        elif masterInfo.isGhost:
            item.SetBackgroundColour(colors['bash.mods.isGhost'])
        else:
            item.SetBackgroundColour(colors['bash.doubleTime.not'])
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
            self.items.sort(key=lambda a: bosh.modInfos.table.getItem(a,'rating',''))
        elif col == 'Group':
            self.items.sort(key=lambda a: bosh.modInfos.table.getItem(a,'group',''))
        elif col == 'Installer':
             self.items.sort(key=lambda a: bosh.modInfos.table.getItem(a,'installer',''))
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
            raise BashError(_('Unrecognized sort key: ')+col)
        #--Ascending
        if reverse: self.items.reverse()
        #--ESMs First?
        settings['bash.masters.esmsFirst'] = self.esmsFirst
        if self.esmsFirst or col == 'Load Order':
            self.items.sort(key=lambda a:data[a].name.cext)

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
        self.parent.SetEdited()

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
        if not self.edited:
            message = (_("Edit/update the masters list? Note that the update process may automatically rename some files. Be sure to review the changes before saving."))
            if not balt.askContinue(self,message,'bash.masters.update',_('Update Masters')):
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
            balt.showError(self,_('File "%s" does not exist.') % (newName.s,))
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
        List.__init__(self,parent,-1,ctrlStyle=(wx.LC_REPORT))
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
        return (applied,mismatch,not_applied,invalid)

    def RefreshUI(self,files='ALL',detail='SAME'):
        """Refreshes UI for specified files."""
        #--Details
        if detail == 'SAME':
            selected = set(self.GetSelected())
        else:
            selected = set([detail])
        #--Populate
        if files == 'VALID':
            files = [GPath(self.items[x]) for x in range(len(self.items)) if self.data[GPath(self.items[x])].status >= 0]
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
                value = self.data.table.getItem(fileName, 'installer', '')
            if mode and colDex == 0:
                self.list.InsertStringItem(itemDex, value)
            else:
                self.list.SetStringItem(itemDex, colDex, value)
        status = fileInfo.getStatus()
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
            mousetext = _('Some settings are applied.  Some are overwritten by another tweak from the same installer.')
        elif status == 10:
            # Ok tweak, some parts are applied, others not
            icon = 10
            checkMark = 3
            mousetext = _('Some settings are changed.')
        elif status == -10:
            # Bad tweak
            icon = 20
            mousetext = _('Tweak is invalid')
        self.mouseTexts[itemDex] = mousetext
        self.list.SetItemImage(itemDex,self.checkboxes.Get(icon,checkMark))
        #--Font/BG Color
        item = self.list.GetItem(itemDex)
        item.SetTextColour(wx.BLACK)
        if status < 0:
            item.SetBackgroundColour(colors['bash.installers.outOfOrder'])
        else:
            item.SetBackgroundColour(wx.WHITE)
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
            self.items.sort(key=lambda a: bosh.iniInfos.table.getItem(a,'installer',''))
        else:
            raise BashError(_('Unrecognized sort key: ')+col)
        #--Ascending
        if reverse: self.items.reverse()
        #--Valid Tweaks first?
        self.sortValid = settings['bash.ini.sortValid']
        if self.sortValid:
            self.items.sort(key=lambda a: self.data[a].status < 0)


    def OnKeyUp(self,event):
        """Char event: select all items"""
        ##Ctrl+A
        if event.ControlDown() and event.GetKeyCode() in (65,97):
            self.SelectAll()
        elif event.GetKeyCode() in (wx.WXK_DELETE,wx.WXK_NUMPAD_DELETE):
            try:
                wx.BeginBusyCursor()
                self.DeleteSelected()
            finally:
                wx.EndBusyCursor()
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
        self.InsertColumn(0,'')
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
        tweakPath = bosh.iniInfos.dir.join(tweakPath)
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
            if line[4] == -10: color = colors['bash.ini.invalid']
            elif line[4] == 10: color = colors['bash.ini.mismatched']
            elif line[4] == 20: color = colors['bash.ini.matched']
            else: color = self.GetBackgroundColour()
            self.SetItemBackgroundColour(i, color)
            #--Set iniContents color
            if line[5] != -1:
                self.iniContents.SetItemBackgroundColour(line[5],color)
                updated.append(line[5])
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
        self.InsertColumn(0, '')

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

    def RefreshUI(self):
        ini = bosh.iniInfos.ini.path.open('r')
        lines = ini.readlines()
        ini.close()

        num = self.GetItemCount()
        self.EnsureVisible(0)
        for i,line in enumerate(lines):
            if i >= num:
                self.InsertStringItem(i, line)
            else:
                self.SetStringItem(i, 0, line)
        for i in range(len(lines), num):
            self.DeleteItem(len(lines))
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
        List.__init__(self,parent,-1,ctrlStyle=(wx.LC_REPORT), dndList=True, dndColumns=['Load Order'])#|wx.SUNKEN_BORDER))
        #--Image List
        checkboxesIL = colorChecks.GetImageList()
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
    def OnDropIndexes(self, indexes, newPos):
        # Make sure we're not auto-sorting
        for thisFile in self.GetSelected():
            if GPath(thisFile) in bosh.modInfos.autoSorted:
                balt.showError(self,_("Auto-ordered files cannot be manually moved."))
                return
        # Watch out for errors in range
        if newPos > indexes[0]:   inc = 1
        elif newPos < indexes[0]: inc = -1
        else: return
        howMany = indexes[-1]-indexes[0]
        # Make sure we don't go out of bounds
        target = indexes[0]
        thisFile = self.items[target]
        while True:
            if target < 0: break
            if target + howMany >= len(self.items) - inc: break
            if target == newPos: break
            swapFile = self.items[target]
            if thisFile.cext != swapFile.cext: break
            target += inc
        if inc == 1 and target + howMany <= indexes[-1]: return
        if inc == -1 and target >= indexes[0]: return
        # Adjust for going up/down
        if inc > 0:
            target += howMany
        else:
            indexes.reverse()
        # Gather time codes
        i = indexes[0]
        times = []
        while i != target + inc:
            info = bosh.modInfos[self.items[i]]
            times.append(info.mtime)
            i += inc
        # Rearrange them for the new load order
        times.reverse()
        newThisTimes = times[:howMany+1]
        newSwapTimes = times[howMany+1:]
        times = newSwapTimes + newThisTimes
        # Apply new times
        i = indexes[0]
        while i != target + inc:
            info = bosh.modInfos[self.items[i]]
            info.setmtime(times.pop())
            i += inc
        # Refresh
        bosh.modInfos.refreshInfoLists()
        self.RefreshUI()

    def RefreshUI(self,files='ALL',detail='SAME',refreshSaves=True):
        """Refreshes UI for specified file. Also calls saveList.RefreshUI()!"""
        #--Details
        if detail == 'SAME':
            selected = set(self.GetSelected())
        else:
            selected = set([detail])
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
        if refreshSaves:
            saveList.RefreshUI()

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
            #--Get Value
            if col == 'File':
                value = fileName.s
                if fileName == 'Oblivion.esm' and bosh.modInfos.voCurrent:
                    value += ' ['+bosh.modInfos.voCurrent+']'
            elif col == 'Rating':
                value = bosh.modInfos.table.getItem(fileName,'rating','')
            elif col == 'Group':
                value = bosh.modInfos.table.getItem(fileName,'group','')
            elif col == 'Installer':
                value = bosh.modInfos.table.getItem(fileName,'installer', '')
            elif col == 'Modified':
                value = formatDate(fileInfo.mtime)
            elif col == 'Size':
                value = formatInteger(fileInfo.size/1024)+' KB'
            elif col == 'Author' and fileInfo.header:
                value = fileInfo.header.author
            elif col == 'Load Order':
                ordered = bosh.modInfos.ordered
                if fileName in ordered:
                    value = '%02X' % (list(ordered).index(fileName),)
                else:
                    value = ''
            else:
                value = '-'
            #--Insert/SetString
            if mode and (colDex == 0):
                self.list.InsertStringItem(itemDex, value)
            else:
                self.list.SetStringItem(itemDex, colDex, value)
        #--Default message
        mouseText = ''
        #--Image
        status = fileInfo.getStatus()
        checkMark = (
            (fileName in bosh.modInfos.ordered and 1) or
            (fileName in bosh.modInfos.merged and 2) or
            (fileName in bosh.modInfos.imported and 3))
        self.list.SetItemImage(itemDex,self.checkboxes.Get(status,checkMark))
        #--Font color
        item = self.list.GetItem(itemDex)
        mouseText = ""
        if fileInfo.isEsm():
            item.SetTextColour(wx.BLUE)
            mouseText += _("Master file. ")
        elif fileName in bosh.modInfos.mergeable:
            if 'NoMerge' in bosh.modInfos[fileName].getBashTags():
                item.SetTextColour(colors['bash.mods.isSemiMergeable'])
                mouseText += _("Technically mergeable but has NoMerge tag. ")
            else:
                item.SetTextColour(colors['bash.mods.isMergeable'])
                mouseText += _("Can be merged into Bashed Patch. ")
        else:
            item.SetTextColour(wx.BLACK)
        #--Image messages
        if status == 30:     mouseText += _("One or more masters are missing. ")
        elif checkMark == 1: mouseText += _("Active in load list. ")
        elif checkMark == 2: mouseText = _("Merged into Bashed Patch. ")
        elif checkMark == 3: mouseText += _("Imported into Bashed Patch. ")
        elif status == 20:   mouseText += _("Masters have been re-ordered. ")
        #should mod be deactivated
        if 'Deactivate' in bosh.modInfos[fileName].getBashTags():
            item.SetFont(wx.Font(8, wx.NORMAL, wx.SLANT, wx.NORMAL))
        else:
            item.SetFont(wx.Font(8, wx.NORMAL, wx.NORMAL, wx.NORMAL))
        #--Text BG
        if fileInfo.hasActiveTimeConflict():
            item.SetBackgroundColour(colors['bash.doubleTime.load'])
            mouseText += _("WARNING: Has same load order as another mod. ")
        elif 'Deactivate' in bosh.modInfos[fileName].getBashTags() and checkMark == 1:
            item.SetBackgroundColour(colors['bash.doubleTime.load'])
            mouseText += _("Mod should be imported and deactivated. ")
        elif fileInfo.isExOverLoaded():
            item.SetBackgroundColour(colors['bash.exOverLoaded'])
            mouseText += _("WARNING: Exclusion group is overloaded. ")
        elif fileInfo.hasTimeConflict():
            item.SetBackgroundColour(colors['bash.doubleTime.exists'])
            mouseText += _("Has same time as another (unloaded) mod. ")
        elif fileName.s[0] in '.+=':
            item.SetBackgroundColour(colors['bash.mods.groupHeader'])
            mouseText += _("Group header. ")
        elif fileInfo.isGhost:
            item.SetBackgroundColour(colors['bash.mods.isGhost'])
            mouseText += _("File is ghosted. ")
        else:
            item.SetBackgroundColour(colors['bash.doubleTime.not'])
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
            self.items.sort(key=lambda a: bosh.modInfos.table.getItem(a,'rating',''))
        elif col == 'Group':
            self.items.sort(key=lambda a: bosh.modInfos.table.getItem(a,'group',''))
        elif col == 'Installer':
            self.items.sort(key=lambda a: bosh.modInfos.table.getItem(a,'installer',''))
        elif col == 'Load Order':
            self.items = bosh.modInfos.getOrdered(self.items,False)
        elif col == 'Modified':
            self.items.sort(key=lambda a: data[a].mtime)
        elif col == 'Size':
            self.items.sort(key=lambda a: data[a].size)
        elif col == 'Status':
            self.items.sort(key=lambda a: data[a].getStatus())
        else:
            raise BashError(_('Unrecognized sort key: ')+col)
        #--Ascending
        if reverse: self.items.reverse()
        #--ESMs First?
        settings['bash.mods.esmsFirst'] = self.esmsFirst
        if self.esmsFirst or col == 'Load Order':
            self.items.sort(key = lambda x: x.cext)
        #--Selected First?
        settings['bash.mods.selectedFirst'] = self.selectedFirst
        if self.selectedFirst:
            active = set(selected) | bosh.modInfos.imported | bosh.modInfos.merged
            self.items.sort(key=lambda x: x not in active)

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
            self.DeleteSelected()
        ##Ctrl+Up and Ctrl+Down
        elif ((event.ControlDown() and event.GetKeyCode() in (wx.WXK_UP,wx.WXK_DOWN)) and
            (settings['bash.mods.sort'] == 'Load Order')
            ):
                for thisFile in self.GetSelected():
                    if GPath(thisFile) in bosh.modInfos.autoSorted:
                        balt.showError(self,_("Auto-ordered files cannot be manually moved."))
                        event.Skip()
                        break
                else:
                    orderKey = lambda x: self.items.index(x)
                    moveMod = (-1,1)[event.GetKeyCode() == wx.WXK_DOWN]
                    isReversed = (moveMod != -1)
                    for thisFile in sorted(self.GetSelected(),key=orderKey,reverse=isReversed):
                        swapItem = self.items.index(thisFile) + moveMod
                        if swapItem < 0 or len(self.items) - 1 < swapItem: break
                        swapFile = self.items[swapItem]
                        if thisFile.cext != swapFile.cext: break
                        thisInfo, swapInfo = bosh.modInfos[thisFile], bosh.modInfos[swapFile]
                        thisTime, swapTime = thisInfo.mtime, swapInfo.mtime
                        if thisTime == swapTime:
                            thisTime = bosh.modInfos.getFreeTime(thisTime,thisTime,reverse=isReversed)
                            #swapTime = bosh.modInfos.getFreeTime(swapTime,swapTime,reverse=isReversed)
                        thisInfo.setmtime(swapTime)
                        swapInfo.setmtime(thisTime)
                        bosh.modInfos.refreshInfoLists()
                        self.RefreshUI(refreshSaves=False)
                    self.RefreshUI([],refreshSaves=True)
        event.Skip()

    def OnKeyUp(self,event):
        """Char event: Activate selected items, select all items"""
        ##Space
        if (event.GetKeyCode() == wx.WXK_SPACE):
            selected = self.GetSelected()
            toActivate = [item for item in selected if not self.data.isSelected(GPath(item))]
            if len(toActivate) == 0 or len(toActivate) == len(selected):
                #--Check/Uncheck all
                self.checkUncheckMod(*selected)
            else:
                #--Check all that aren't
                self.checkUncheckMod(*toActivate)
        ##Ctrl+A
        elif event.ControlDown() and event.GetKeyCode() in (65,97):
            self.SelectAll()
        event.Skip()

    def OnColumnResize(self,event):
        """Column resize: Stored modified column widths."""
        super(ModList,self).OnColumnResize(event)
        settings.setChanged('bash.mods.colWidths')

    def OnLeftDown(self,event):
        """Left Down: Check/uncheck mods."""
        (hitItem,hitFlag) = self.list.HitTest((event.GetX(),event.GetY()))
        if hitFlag == 32:
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
class ModDetails(wx.Window):
    """Details panel for mod tab."""
    def __init__(self,parent):
        wx.Window.__init__(self, parent, -1, style=wx.TAB_TRAVERSAL)
        #--Singleton
        global modDetails
        modDetails = self
        #--Data
        self.modInfo = None
        self.edited = False
        textWidth = 200
        #--Version
        self.version = staticText(self,'v0.0')
        id = self.fileId = wx.NewId()
        #--File Name
        self.file = textCtrl(self,id,size=(textWidth,-1))
        self.file.SetMaxLength(200)
        self.file.Bind(wx.EVT_KILL_FOCUS, self.OnEditFile)
        self.file.Bind(wx.EVT_TEXT, self.OnTextEdit)
        #--Author
        id = self.authorId = wx.NewId()
        self.author = textCtrl(self,id,size=(textWidth,-1))
        self.author.SetMaxLength(512)
        wx.EVT_KILL_FOCUS(self.author,self.OnEditAuthor)
        wx.EVT_TEXT(self.author,id,self.OnTextEdit)
        #--Modified
        id = self.modifiedId = wx.NewId()
        self.modified = textCtrl(self,id,size=(textWidth,-1))
        self.modified.SetMaxLength(32)
        wx.EVT_KILL_FOCUS(self.modified,self.OnEditModified)
        wx.EVT_TEXT(self.modified,id,self.OnTextEdit)
        #--Description
        id = self.descriptionId = wx.NewId()
        self.description = (
            wx.TextCtrl(self,id,"",size=(textWidth,150),style=wx.TE_MULTILINE))
        self.description.SetMaxLength(512)
        wx.EVT_KILL_FOCUS(self.description,self.OnEditDescription)
        wx.EVT_TEXT(self.description,id,self.OnTextEdit)
        #--Masters
        id = self.mastersId = wx.NewId()
        self.masters = MasterList(self,None)
        #--Save/Cancel
        self.save = button(self,label=_('Save'),id=wx.ID_SAVE,onClick=self.DoSave,)
        self.cancel = button(self,label=_('Cancel'),id=wx.ID_CANCEL,onClick=self.DoCancel,)
        self.save.Disable()
        self.cancel.Disable()
        #--Bash tags
        self.allTags = bosh.allTags
        id = self.tagsId = wx.NewId()
        self.gTags = (
            wx.TextCtrl(self,id,"",size=(textWidth,100),style=wx.TE_MULTILINE|wx.TE_READONLY))
        #--Layout
        sizer = vSizer(
            (hSizer(
                (staticText(self,_("File:")),0,wx.TOP,4),
                spacer,
                (self.version,0,wx.TOP|wx.RIGHT,4)
                ),0,wx.EXPAND),
            self.file,
            (staticText(self,_("Author:")),0,wx.TOP,4),
            self.author,
            (staticText(self,_("Modified:")),0,wx.TOP,4),
            self.modified,
            (staticText(self,_("Description:")),0,wx.TOP,4),
            self.description,
            (staticText(self,_("Masters:")),0,wx.TOP,4),
            (self.masters,1,wx.EXPAND),
            (hSizer(
                spacer,
                self.save,
                (self.cancel,0,wx.LEFT,4)
                ),0,wx.EXPAND|wx.TOP,4),
            (staticText(self,_("Bash Tags:")),0,wx.TOP,4),
            self.gTags,
            )
        self.SetSizer(sizer)
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
            self.fileStr = ''
            self.authorStr = ''
            self.modifiedStr = ''
            self.descriptionStr = ''
            self.versionStr = 'v0.0'
            tagsStr = ''
        #--Valid fileName?
        else:
            modInfo = self.modInfo = bosh.modInfos[fileName]
            #--Remember values for edit checks
            self.fileStr = modInfo.name.s
            self.authorStr = modInfo.header.author
            self.modifiedStr = formatDate(modInfo.mtime)
            self.descriptionStr = modInfo.header.description
            self.versionStr = 'v%0.1f' % (modInfo.header.version,)
            tagsStr = '\n'.join(sorted(modInfo.getBashTags()))
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
        if fileName and bosh.modInfos.table.getItem(fileName,'bashTags', None) != None:
            self.gTags.SetBackgroundColour(self.author.GetBackgroundColour())
        else:
            self.gTags.SetBackgroundColour(self.GetBackgroundColour())
        #--Edit State
        self.edited = 0
        self.save.Disable()
        self.cancel.Disable()

    def SetEdited(self):
        self.edited = True
        self.save.Enable()
        self.cancel.Enable()

    def OnTextEdit(self,event):
        if self.modInfo and not self.edited:
            if ((self.fileStr != self.file.GetValue()) or
                (Unicode(self.authorStr) != Unicode(self.author.GetValue())) or
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
            balt.showError(self,_("Incorrect file extension: ")+fileStr[-3:])
            self.file.SetValue(self.fileStr)
        #--Else file exists?
        elif self.modInfo.dir.join(fileStr).exists():
            balt.showError(self,_("File %s already exists.") % (fileStr,))
            self.file.SetValue(self.fileStr)
        #--Okay?
        else:
            self.fileStr = fileStr
            self.SetEdited()

    def OnEditAuthor(self,event):
        if not self.modInfo: return
        authorStr = Unicode(self.author.GetValue())
        if authorStr != Unicode(self.authorStr):
            self.authorStr = authorStr
            self.SetEdited()

    def OnEditModified(self,event):
        if not self.modInfo: return
        modifiedStr = self.modified.GetValue()
        if modifiedStr == self.modifiedStr: return
        try:
            newTimeTup = bosh.unformatDate(modifiedStr,'%c')
            time.mktime(newTimeTup)
        except ValueError:
            balt.showError(self,_('Unrecognized date: ')+modifiedStr)
            self.modified.SetValue(self.modifiedStr)
            return
        except OverflowError:
            balt.showError(self,_('Bash cannot handle files dates greater than January 19, 2038.)'))
            self.modified.SetValue(self.modifiedStr)
            return
        #--Normalize format
        modifiedStr = time.strftime('%c',newTimeTup)
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
        changeHedr = ((self.authorStr != Unicode(modInfo.header.author)) or
            (self.descriptionStr != modInfo.header.description ))
        changeMasters = self.masters.edited
        #--Warn on rename if file has BSA and/or dialog
        hasBsa, hasVoices = modInfo.hasResources()
        if changeName and (hasBsa or hasVoices):
            modName = modInfo.name.s
            if hasBsa and hasVoices:
                message = _("This mod has an associated archive (%s.bsa) and an associated voice directory (Sound\\Voices\\%s), which will become detached when the mod is renamed.\n\nNote that the BSA archive may also contain a voice directory (Sound\\Voices\\%s), which would remain detached even if the archive name is adjusted.") % (modName[:-4],modName,modName)
            elif hasBsa:
                message = _("This mod has an associated archive (%s.bsa), which will become detached when the mod is renamed.\n\nNote that this BSA archive may contain a voice directory (Sound\\Voices\\%s), which would remain detached even if the archive file name is adjusted.") % (modName[:-4],modName)
            else: #hasVoices
                message = _("This mod has an associated voice directory (Sound\\Voice\\%s), which will become detached when the mod is renamed.") % (modName,)
            if not balt.askOk(self,message):
                return
        #--Only change date?
        if changeDate and not (changeName or changeHedr or changeMasters):
            newTimeTup = bosh.unformatDate(self.modifiedStr,'%c')
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
            (oldName,newName) = (modInfo.name,GPath(self.fileStr.strip()))
            modList.items[modList.items.index(oldName)] = newName
            settings.getChanged('bash.mods.renames')[oldName] = newName
            bosh.modInfos.rename(oldName,newName)
            fileName = newName
        #--Change hedr/masters?
        if changeHedr or changeMasters:
            modInfo.header.author = Encode(self.authorStr.strip())
            modInfo.header.description = bolt.winNewLines(self.descriptionStr.strip())
            modInfo.header.masters = self.masters.GetNewMasters()
            modInfo.header.changed = True
            modInfo.writeHeader()
        #--Change date?
        if (changeDate or changeHedr or changeMasters):
            newTimeTup = bosh.unformatDate(self.modifiedStr,'%c')
            newTimeInt = int(time.mktime(newTimeTup))
            modInfo.setmtime(newTimeInt)
        #--Done
        try:
            #bosh.modInfos.refresh()
            bosh.modInfos.refreshFile(fileName)
            self.SetFile(fileName)
        except bosh.FileError:
            balt.showError(self,_('File corrupted on save!'))
            self.SetFile(None)
        if bosh.modInfos.refresh(doInfos=False):
            bosh.modInfos.refreshInfoLists()
        modList.RefreshUI()

    def DoCancel(self,event):
        self.SetFile(self.modInfo.name)

    #--Bash Tags
    def ShowBashTagsMenu(self,event):
        """Show bash tags menu."""
        if not self.modInfo: return
        self.modTags = self.modInfo.getBashTags()
        #--Build menu
        menu = wx.Menu()
        #--Revert to auto
        #--Separator
        isAuto = bosh.modInfos.table.getItem(self.modInfo.name,'bashTags',None) is None
        menuItem = wx.MenuItem(menu,ID_TAGS.AUTO,_('Automatic'),kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        menuItem.Check(isAuto)
        menuItem = wx.MenuItem(menu,ID_TAGS.COPY,_('Copy to Description'))
        menu.AppendItem(menuItem)
        menuItem.Enable(not isAuto and self.modTags != self.modInfo.getBashTagsDesc())
        menu.AppendSeparator()
        for id,tag in zip(ID_TAGS,self.allTags):
            menu.AppendCheckItem(id,tag)
            menu.Check(id,tag in self.modTags)
        self.gTags.PopupMenu(menu)
        menu.Destroy()

    def DoAutoBashTags(self,event):
        """Handle selection of automatic bash tags."""
        modInfo = self.modInfo
        if bosh.modInfos.table.getItem(modInfo.name,'bashTags',None) is None:
            modInfo.setBashTags(modInfo.getBashTags())
        else:
            bosh.modInfos.table.delItem(modInfo.name,'bashTags')
        modList.RefreshUI(self.modInfo.name)

    def DoCopyBashTags(self,event):
        """Handle selection of automatic bash tags."""
        modInfo = self.modInfo
        modInfo.setBashTagsDesc(modInfo.getBashTags())
        modList.RefreshUI(self.modInfo.name)

    def ToggleBashTag(self,event):
        """Toggle bash tag from menu."""
        tag = self.allTags[event.GetId()-ID_TAGS.BASE]
        modTags = self.modTags ^ set((tag,))
        self.modInfo.setBashTags(modTags)
        modList.RefreshUI(self.modInfo.name)

#------------------------------------------------------------------------------
class INIPanel(SashPanel):
    def __init__(self, parent):
        SashPanel.__init__(self, parent,'bash.ini.sashPos')
        left,right = self.left, self.right
        #--Remove from list button
        self.button = button(right,_('Remove'),onClick=self.OnRemove)
        #--Edit button
        self.edit = button(right,_('Edit...'),onClick=self.OnEdit)
        #--Choices
        self.choices = settings['bash.ini.choices']
        self.choice = settings['bash.ini.choice']
        self.CheckTargets()
        self.lastDir = bosh.dirs['mods'].s
        self.SortChoices()
        #--Ini file
        self.iniContents = INILineCtrl(right)
        #--Tweak file
        self.tweakContents = INITweakLineCtrl(right,self.iniContents)
        self.iniContents.SetTweakLinesCtrl(self.tweakContents)
        self.tweakName = textCtrl(right, style=wx.TE_READONLY|wx.NO_BORDER)
        self.SetBaseIni(self.GetChoice())
        global iniList
        iniList = INIList(left)
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

    def RefreshUI(self,what='ALL'):
        if what == 'ALL' or what == 'TARGETS':
            # Refresh the drop down list
            path = self.GetChoice()
            if path is None:
                self.choice -= 1
            elif not path.isfile():
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
        if self.choice == 0:
            bosh.iniInfos.setBaseIni(bosh.oblivionIni)
            self.button.Enable(False)
        else:
            if not path:
                path = self.GetChoice()
            bosh.iniInfos.setBaseIni(bosh.BestIniFile(path))
            self.button.Enable(True)
        selected = None
        if iniList is not None:
            selected = iniList.GetSelected()
            if len(selected) > 0:
                selected = selected[0]
            else:
                selected = None
        self.iniContents.RefreshUI()
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
            if i == _('Browse...'): continue
            path = self.choices[i]
            if not path.isfile():
                del self.choices[i]
                changed = True
        if 'Oblivion.ini' not in self.choices:
            self.choices['Oblivion.ini'] = bosh.oblivionIni.path
            changed = True
        if _('Browse...') not in self.choices:
            self.choices[_('Browse...')] = None
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
        keys.sort(key=lambda a: (a != 'Oblivion.ini') + (a == _('Browse...')))
        self.sortKeys = keys
        return keys

    def SetStatusCount(self):
        """Sets mod count in last field."""
        stati = iniList.CountTweakStatus()
        text = _("Tweaks: %d/%d") % (stati[0],sum(stati[:-1]))
        statusBar.SetStatusText(text,2)

    def AddOrSelectIniDropDown(self, path):
        if path.stail not in self.choices:
            self.choices[path.stail] = path
            self.SortChoices()
            self.comboBox.SetItems(self.sortKeys)
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
            path = balt.askOpen(self,defaultDir=self.lastDir,wildcard='INI files (*.ini)|*.ini',mustExist=True)
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

#------------------------------------------------------------------------------
class ModPanel(NotebookPanel):
    def __init__(self,parent):
        wx.Panel.__init__(self, parent, -1)
        global modList
        modList = ModList(self)
        self.modDetails = ModDetails(self)
        modList.details = self.modDetails
        #--Events
        wx.EVT_SIZE(self,self.OnSize)
        #--Layout
        sizer = hSizer(
            (modList,1,wx.GROW),
            ((4,-1),0),
            (self.modDetails,0,wx.EXPAND))
        self.SetSizer(sizer)
        self.modDetails.Fit()

    def SetStatusCount(self):
        """Sets mod count in last field."""
        text = _("Mods: %d/%d") % (len(bosh.modInfos.ordered),len(bosh.modInfos.data))
        statusBar.SetStatusText(text,2)

    def OnSize(self,event):
        wx.Window.Layout(self)
        modList.Layout()
        self.modDetails.Layout()

    def OnCloseWindow(self):
        """To be called when containing frame is closing. Use for saving data, scrollpos, etc."""
        bosh.modInfos.table.save()
        settings['bash.mods.scrollPos'] = modList.vScrollPos

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
        if not newName.lower().endswith('.ess'):
            newName += '.ess'
        newFileName = newName
        selected = self.GetSelected()
        for index, path in enumerate(selected):
            if index:
                newFileName = newName.replace('.ess','%d.ess' % index)
            if newFileName != path.s:
                oldPath = bosh.saveInfos.dir.join(path.s)
                newPath = bosh.saveInfos.dir.join(newFileName)
                if not newPath.exists():
                    oldPath.moveTo(newPath)
                    if GPath(oldPath.s[:-3]+'obse').exists():
                        GPath(oldPath.s[:-3]+'obse').moveTo(GPath(newPath.s[:-3]+'obse'))
                    if GPath(oldPath.s[:-3]+'pluggy').exists():
                        GPath(oldPath.s[:-3]+'pluggy').moveTo(GPath(newPath.s[:-3]+'pluggy'))
        bosh.saveInfos.refresh()
        self.RefreshUI()

    def RefreshUI(self,files='ALL',detail='SAME'):
        """Refreshes UI for specified files."""
        #--Details
        if detail == 'SAME':
            selected = set(self.GetSelected())
        else:
            selected = set([detail])
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
                value = formatInteger(fileInfo.size/1024)+' KB'
            elif col == 'Player' and fileInfo.header:
                value = fileInfo.header.pcName
            elif col == 'PlayTime' and fileInfo.header:
                playMinutes = fileInfo.header.gameTicks/60000
                value = "%d:%02d" % (playMinutes/60,(playMinutes % 60))
            elif col == 'Cell' and fileInfo.header:
                value = fileInfo.header.pcLocation
            else:
                value = '-'
            if mode and (colDex == 0):
                self.list.InsertStringItem(itemDex, value)
            else:
                self.list.SetStringItem(itemDex, colDex, value)
        #--Image
        status = fileInfo.getStatus()
        on = fileName.cext == '.ess'
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
            raise BashError(_('Unrecognized sort key: ')+col)
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
        ##Ctrl+A
        if event.ControlDown() and event.GetKeyCode() in (65,97):
            self.SelectAll()
        event.Skip()
    #--Event: Left Down
    def OnLeftDown(self,event):
        (hitItem,hitFlag) = self.list.HitTest((event.GetX(),event.GetY()))
        if hitFlag == 32:
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
class SaveDetails(wx.Window):
    """Savefile details panel."""
    def __init__(self,parent):
        """Initialize."""
        wx.Window.__init__(self, parent, -1, style=wx.TAB_TRAVERSAL)
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
        self.file = wx.TextCtrl(self,id,"",size=(textWidth,-1))
        self.file.SetMaxLength(256)
        wx.EVT_KILL_FOCUS(self.file,self.OnEditFile)
        wx.EVT_TEXT(self.file,id,self.OnTextEdit)
        #--Player Info
        self.playerInfo = staticText(self," \n \n ")
        self.gCoSaves = staticText(self,'--\n--')
        #--Picture
        self.picture = balt.Picture(self,textWidth,192*textWidth/256,style=wx.BORDER_SUNKEN ) #--Native: 256x192
        #--Masters
        id = self.mastersId = wx.NewId()
        self.masters = MasterList(self,None)
        #--Save Info
        self.gInfo = wx.TextCtrl(self,-1,"",size=(textWidth,100),style=wx.TE_MULTILINE)
        self.gInfo.SetMaxLength(2048)
        self.gInfo.Bind(wx.EVT_TEXT,self.OnInfoEdit)
        #--Save/Cancel
        self.save = button(self,id=wx.ID_SAVE,onClick=self.DoSave)
        self.cancel = button(self,id=wx.ID_CANCEL,onClick=self.DoCancel)
        self.save.Disable()
        self.cancel.Disable()
        #--Layout
        sizer = vSizer(
            #(staticText(self,_("File:")),0,wx.TOP,4),
            (self.file,0,wx.EXPAND|wx.TOP,4),
            (hSizer(
                (self.playerInfo,1,wx.EXPAND),
                (self.gCoSaves,0,wx.EXPAND),
                ),0,wx.EXPAND|wx.TOP,4),
            (self.picture,0,wx.TOP,4),
            #(staticText(self,_("Masters:")),0,wx.TOP,4),
            (self.masters,2,wx.EXPAND|wx.TOP,4),
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
            if not self.saveInfo or self.saveInfo.name not in bosh.saveInfos:
                fileName = None
            else:
                fileName = self.saveInfo.name
        #--Null fileName?
        if not fileName:
            saveInfo = self.saveInfo = None
            self.fileStr = ''
            self.playerNameStr = ''
            self.curCellStr = ''
            self.playerLevel = 0
            self.gameDays = 0
            self.playMinutes = 0
            self.picData = None
            self.coSaves = '--\n--'
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
            self.coSaves = '%s\n%s' % saveInfo.coSaves().getTags()
        #--Set Fields
        self.file.SetValue(self.fileStr)
        self.playerInfo.SetLabel(_("%s\nLevel %d, Day %d, Play %d:%02d\n%s") %
            (self.playerNameStr,self.playerLevel,int(self.gameDays),self.playMinutes/60,(self.playMinutes % 60),self.curCellStr))
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
            self.gInfo.SetValue(bosh.saveInfos.table.getItem(fileName,'info',_('Notes: ')))
        else:
            self.gInfo.SetValue(_('Notes: '))

    def SetEdited(self):
        """Mark as edited."""
        self.edited = True
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
        if self.fileStr[-4:].lower() not in ('.ess','.bak'):
            balt.showError(self,"Incorrect file extension: "+fileStr[-3:])
            self.file.SetValue(self.fileStr)
        #--Else file exists?
        elif self.saveInfo.dir.join(fileStr).exists():
            balt.showError(self,"File %s already exists." % (fileStr,))
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
            balt.showError(self,_('File corrupted on save!'))
            self.SetFile(None)
        self.SetFile(self.saveInfo.name)
        saveList.RefreshUI(saveInfo.name)

    def DoCancel(self,event):
        """Event: Clicked cancel button."""
        self.SetFile(self.saveInfo.name)

#------------------------------------------------------------------------------
class SavePanel(NotebookPanel):
    """Savegames tab."""
    def __init__(self,parent):
        wx.Panel.__init__(self, parent, -1)
        global saveList
        saveList = SaveList(self)
        self.saveDetails = SaveDetails(self)
        saveList.details = self.saveDetails
        #--Events
        wx.EVT_SIZE(self,self.OnSize)
        #--Layout
        sizer = hSizer(
            (saveList,1,wx.GROW),
            ((4,-1),0),
            (self.saveDetails,0,wx.EXPAND))
        self.SetSizer(sizer)
        self.saveDetails.Fit()

    def SetStatusCount(self):
        """Sets mod count in last field."""
        text = _("Saves: %d") % (len(bosh.saveInfos.data))
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

    def OnBeginEditLabel(self,event):
        """Start renaming installers"""
        #--Only rename multiple items of the same type
        firstItem = self.data[self.GetSelected()[0]]
        InstallerType = None
        if(isinstance(firstItem,bosh.InstallerMarker)):
            InstallerType = bosh.InstallerMarker
        elif(isinstance(firstItem,bosh.InstallerArchive)):
            InstallerType = bosh.InstallerArchive
        elif(isinstance(firstItem,bosh.InstallerProject)):
            InstallerType = bosh.InstallerProject
        else:
            event.Veto()
            return
        for item in self.GetSelected():
            if not isinstance(self.data[item],InstallerType):
                event.Veto()
                return
            #--Also, don't allow renaming the 'Last' marker
            elif item.s == '==Last==':
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
            rePattern = re.compile(r'^([^\\/]+?)(\d*)((\.(7z|rar|zip|001))+)$',re.I)
        elif isinstance(self.data[selected[0]], bosh.InstallerMarker):
            InstallerType = bosh.InstallerMarker
            rePattern = re.compile(r'^([^\\/]+?)(\d*)$',re.I)
        elif isinstance(self.data[selected[0]], bosh.InstallerProject):
            InstallerType = bosh.InstallerProject
            rePattern = re.compile(r'^([^\\/]+?)(\d*)$',re.I)
        maPattern = rePattern.match(newName)
        if not maPattern:
            balt.showError(self,_('Bad extension or file root: ')+newName)
            event.Veto()
            return
        root,numStr = maPattern.groups()[:2]
        if InstallerType is bosh.InstallerMarker:
            root = root.strip('=')
        #--Rename each installer, keeping the old extension (for archives)
        numLen = len(numStr)
        num = int(numStr or 0)
        installersDir = bosh.dirs['installers']
        wx.BeginBusyCursor()
        for archive in selected:
            installer = self.data[archive]
            newName = GPath(root+numStr+archive.ext)
            if InstallerType is bosh.InstallerMarker:
                newName = GPath('==' + newName.s + '==')
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
                        mfiles = [x for x in bosh.modInfos.table.getColumn('installer') if bosh.modInfos.table[x]['installer'] == oldPath.stail]
                        ifiles = [x for x in bosh.iniInfos.table.getColumn('installer') if bosh.iniInfos.table[x]['installer'] == oldPath.stail]
                        for i in mfiles:
                            bosh.modInfos.table[i]['installer'] = newPath.stail
                        for i in ifiles:
                            bosh.iniInfos.table[i]['installer'] = newPath.stail
            num += 1
            numStr = `num`
            numStr = '0'*(numLen-len(numStr))+numStr
        if InstallerType is bosh.InstallerMarker:
            #--For markers, we're actually making a new one, and deleting the old ones
            for item in selected:
                del self.data[item]
        #--Refresh UI
        self.data.refresh(what='I')
        modList.RefreshUI()
        iniList.RefreshUI()
        self.RefreshUI()
        event.Veto()
        wx.EndBusyCursor()

    def OnDropFiles(self, x, y, filenames):
        filenames = [GPath(x) for x in filenames]
        omodnames = [x for x in filenames if not x.isdir() and x.cext == '.omod']
        filenames = [x for x in filenames if x.isdir() or x.cext in ['.7z','.rar','.zip']]
        if len(omodnames) > 0:
            failed = []
            completed = []
            progress = balt.Progress(_('Extracting OMODs...'),'\n'+' '*60,abort=True)
            progress.setFull(len(omodnames))
            try:
                for i,omod in enumerate(omodnames):
                    progress(i,omod.stail)
                    outDir = bosh.dirs['installers'].join(omod.body)
                    if outDir.exists():
                        if balt.askYes(progress.dialog,_("The project '%s' already exitsts.  Overwrite with '%s'?") % (omod.sbody,omod.stail)):
                            outDir.rmtree(omod.sbody)
                        else:
                            continue
                    try:
                        bosh.OmodFile(omod).extractToProject(outDir,SubProgress(progress,i))
                        completed.append(omod)
                    except CancelError:
                        # Clean up from current omod that is extracting
                        try:
                            outDir.rmtree(omod.sbody)
                        except:
                            bolt.deprint("Failed to clean up output dir:\n", traceback=True)
                        try:
                            bosh.dirs['mopy'].join('temp').rmtree('temp')
                        except:
                            bolt.deprint("Failed to clean up temp dir:\n", traceback=True)
                        raise
                    except:
                        bolt.deprint("Failed to extract '%s'.\n\n" % omod.stail, traceback=True)

                        # Clean up
                        failed.append(' * ' + omod.stail)
                        try:
                            outDir.rmtree(omod.sbody)
                        except:
                            bolt.deprint("Failed to clean up output dir:\n", traceback=True)
                        try:
                            bosh.dirs['mopy'].join('temp').rmtree('temp')
                        except:
                            bolt.deprint("Failed to clean up temp dir:\n", taceback=True)
            except CancelError:
                skipped = set(omodnames) - set(completed)
                msg = ''
                if len(completed) > 0:
                    completed = [' * ' + x.stail for x in completed]
                    msg += _("The following OMOds were unpacked:\n%s\n\n") % '\n'.join(completed)
                if len(skipped) > 0:
                    skipped = [' * ' + x.stail for x in skipped]
                    msg += _("The following OMODs were skipped:\n%s\n\n") % '\n'.join(skipped)
                if len(failed) > 0:
                    msg += _("The following OMODs failed to extract:\n%s") % '\n'.join(failed)
                balt.showOk(self,msg,_("OMOD Extraction Canceled"))
            else:
                if len(failed) > 0:
                    balt.showWarning(self,
                                     _("The following OMODs failed to extract.  This could be a file IO error, or an unsupported OMOD format:\n\n")+'\n'.join(failed),
                                     _("OMOD Extraction Complete"))
            finally:
                progress(len(omodnames),'Refreshing...')
                self.data.refresh(what='I')
                self.RefreshUI()
                progress.Destroy()
        if len(filenames) == 0:
            return
        action = settings['bash.installers.onDropFiles.action']
        if action not in ['COPY','MOVE']:
            message = _('You have dragged the following files into Wrye Bash:\n')
            for file in filenames:
                message += ' * ' + file.s + '\n'
            message += '\n'
            message += _('What would you like to do with them?')

            self.dialog = dialog= wx.Dialog(self,-1,_('Move or Copy?'),size=(400,200),style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
            icon = wx.StaticBitmap(dialog,-1,wx.ArtProvider_GetBitmap(wx.ART_WARNING,wx.ART_MESSAGE_BOX, (32,32)))
            gCheckBox = checkBox(dialog,_("Don't show this in the future."))

            sizer = vSizer(
                (hSizer(
                    (icon,0,wx.ALL,6),
                    (staticText(dialog,message,style=wx.ST_NO_AUTORESIZE),1,wx.EXPAND|wx.LEFT,6),
                    ),1,wx.EXPAND|wx.ALL,6),
                (gCheckBox,0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,6),
                (hSizer(
                    spacer,
                    button(dialog,id=606,label='Move',onClick=self.OnClickMove),
                    (button(dialog,id=607,label='Copy',onClick=self.OnClickCopy),0,wx.LEFT,4),
                    (button(dialog,id=wx.ID_CANCEL),0,wx.LEFT,4),
                    ),0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,6),
                )
            dialog.SetSizer(sizer)
            result = dialog.ShowModal()
            if result == 1:
                action = 'MOVE'
            elif result == 2:
                action = 'COPY'
            else:
                return
            if gCheckBox.GetValue():
                settings['bash.installers.onDropFiles.action'] = action
        if action == 'COPY':
            #--Copy the dropped files
            wx.BeginBusyCursor()
            for file in filenames:
                file.copyTo(bosh.dirs['installers'].join(file.tail))
        elif action == 'MOVE':
            wx.BeginBusyCursor()
            for file in filenames:
                file.moveTo(bosh.dirs['installers'].join(file.tail))
        else:
            return
        modList.RefreshUI()
        iniList.RefreshUI()
        self.data.refresh()
        self.RefreshUI()
        wx.EndBusyCursor()

    def OnClickMove(self,event):
        self.dialog.EndModal(1)

    def OnClickCopy(self,event):
        self.dialog.EndModal(2)

    def SelectAll(self):
        for itemDex in range(self.gList.GetItemCount()):
            self.gList.SetItemState(itemDex,wx.LIST_STATE_SELECTED,wx.LIST_STATE_SELECTED)

    def OnChar(self,event):
        """Char event: Reorder."""
        ##Ctrl+Up/Ctrl+Down - Move installer up/down install order
        if ((event.ControlDown() and event.GetKeyCode() in (wx.WXK_UP,wx.WXK_DOWN))):
            if len(self.GetSelected()) < 1: return
            orderKey = lambda x: self.data.data[x].order
            maxPos = max(self.data.data[x].order for x in self.data.data)
            if(event.GetKeyCode() == wx.WXK_DOWN):
                moveMod = 1
                visibleIndex = self.GetIndex(sorted(self.GetSelected(),key=orderKey)[-1]) + 2
            else:
                moveMod = -1
                visibleIndex = self.GetIndex(sorted(self.GetSelected(),key=orderKey)[0]) - 2
            for thisFile in sorted(self.GetSelected(),key=orderKey,reverse=(moveMod != -1)):
                newPos = self.data.data[thisFile].order + moveMod
                if newPos < 0 or maxPos < newPos: break
                self.data.moveArchives([thisFile],newPos)
            self.data.refresh(what='I')
            self.RefreshUI()
            if visibleIndex > maxPos: visibleIndex = maxPos
            elif visibleIndex < 0: visibleIndex = 0
            self.gList.EnsureVisible(visibleIndex)
        elif event.GetKeyCode() in (wx.WXK_RETURN,wx.WXK_NUMPAD_ENTER):
        ##Enter - Open selected Installer/
            if len(self.GetSelected()):
                path = self.data.dir.join(self.GetSelected()[0])
                if path.exists(): path.start()
        else:
            event.Skip()

    def OnDClick(self,event):
        """Double click, open the installer."""
        (hitItem,hitFlag) = self.gList.HitTest(event.GetPosition())
        if hitItem < 0: return
        path = self.data.dir.join(self.GetItem(hitItem))
        if path.exists(): path.start()

    def OnLeftDown(self,event):
        """Left click, do stuff; currently nothing."""
        event.Skip()
        return

    def OnKeyUp(self,event):
        """Char events: Action depends on keys pressed"""
        ##Ctrl+A - select all
        if event.ControlDown() and event.GetKeyCode() in (65,97):
            self.SelectAll()
        ##Delete - delete
        elif event.GetKeyCode() in (wx.WXK_DELETE,wx.WXK_NUMPAD_DELETE):
            try:
                wx.BeginBusyCursor()
                self.DeleteSelected()
            finally:
                wx.EndBusyCursor()
        ##F2 - Rename selected.
        elif event.GetKeyCode() == wx.WXK_F2:
            if len(self.GetSelected()) > 0:
                index = self.GetIndex(self.GetSelected()[0])
                if index != -1:
                    self.gList.EditLabel(index)
        ##Ctrl+Shift+N - Add a marker
        elif (event.ControlDown() and event.ShiftDown()) and event.GetKeyCode() in (ord('n'),ord('N')):
            index = self.GetIndex(GPath('===='))
            if index == -1:
                self.data.addMarker('====')
                self.data.refresh(what='OS')
                gInstallers.RefreshUIMods()
                index = self.GetIndex(GPath('===='))
            if index != -1:
                self.ClearSelected()
                self.gList.SetItemState(index,wx.LIST_STATE_SELECTED,wx.LIST_STATE_SELECTED)
                self.gList.EditLabel(index)
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
        data = bosh.InstallersData()
        SashTankPanel.__init__(self,data,parent)
        left,right = self.left,self.right
        splitterStyle = wx.NO_BORDER|wx.SP_LIVE_UPDATE|wx.FULL_REPAINT_ON_RESIZE
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
        self.gPackage = wx.TextCtrl(right,-1,style=wx.TE_READONLY|wx.NO_BORDER)
        self.gPackage.SetBackgroundColour(self.GetBackgroundColour())
        #--Info Tabs
        self.gNotebook = wx.Notebook(subSplitter,style=wx.NB_MULTILINE)
        self.gNotebook.SetSizeHints(100,100)
        self.infoPages = []
        infoTitles = (
            ('gGeneral',_("General")),
            ('gMatched',_("Matched")),
            ('gMissing',_("Missing")),
            ('gMismatched',_("Mismatched")),
            ('gConflicts',_("Conflicts")),
            ('gUnderrides',_("Underridden")),
            ('gDirty',_("Dirty")),
            ('gSkipped',_("Skipped")),
            )
        for name,title in infoTitles:
            gPage = wx.TextCtrl(self.gNotebook,-1,style=wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL,name=name)
            self.gNotebook.AddPage(gPage,title)
            self.infoPages.append([gPage,False])
        self.gNotebook.SetSelection(settings['bash.installers.page'])
        self.gNotebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED,self.OnShowInfoPage)
        #--Sub-Installers
        subPackagesPanel = wx.Panel(checkListSplitter)
        subPackagesLabel = staticText(subPackagesPanel, _('Sub-Packages'))
        self.gSubList = wx.CheckListBox(subPackagesPanel, style=wx.LB_EXTENDED)
        self.gSubList.Bind(wx.EVT_CHECKLISTBOX,self.OnCheckSubItem)
        self.gSubList.Bind(wx.EVT_RIGHT_UP,self.SubsSelectionMenu)
        #--Espms
        espmsPanel = wx.Panel(checkListSplitter)
        espmsLabel = staticText(espmsPanel, _('Esp/m Filter'))
        self.espms = []
        self.gEspmList = wx.CheckListBox(espmsPanel, style=wx.LB_EXTENDED)
        self.gEspmList.Bind(wx.EVT_CHECKLISTBOX,self.OnCheckEspmItem)
        self.gEspmList.Bind(wx.EVT_RIGHT_UP,self.SelectionMenu)
        #--Comments
        commentsPanel = wx.Panel(commentsSplitter)
        commentsLabel = staticText(commentsPanel, _('Comments'))
        self.gComments = wx.TextCtrl(commentsPanel, -1, style=wx.TE_MULTILINE)
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
        commentsSplitterSavedSashPos = settings.get('bash.installers.commentsSplitterSashPos', 0)
        # restore saved comments text box size
        if 0 == commentsSplitterSavedSashPos:
            commentsSplitter.SetSashPosition(-commentsHeight)
        else:
            commentsSplitter.SetSashPosition(commentsSplitterSavedSashPos)
        #--Events
        self.Bind(wx.EVT_SIZE,self.OnSize)
        commentsSplitter.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self._OnCommentsSplitterSashPosChanged)

    def OnShow(self):
        """Panel is shown. Update self.data."""
        if settings.get('bash.installers.isFirstRun',True):
            settings['bash.installers.isFirstRun'] = False
            message = _("Do you want to enable Installers If you do, Bash will first need to initialize some data. If you have many mods installed, this can take on the order of five minutes.\n\nIf you prefer to not enable Installers at this time, you can always enable it later from the column header context menu.")
            settings['bash.installers.enabled'] = balt.askYes(self,fill(message,80),self.data.title)
        if not settings['bash.installers.enabled']: return
        if self.refreshing: return
        data = self.gList.data
        if settings.get('bash.installers.updatedCRCs',True):
            settings['bash.installers.updatedCRCs'] = False
            self.refreshed = False
        if not self.refreshed or (self.frameActivated and data.refreshInstallersNeeded()):
            self.refreshing = True
            progress = balt.Progress(_("Refreshing Installers..."),'\n'+' '*60, abort=True)
            try:
                what = ('DISC','IC')[self.refreshed]
                if data.refresh(progress,what,self.fullRefresh):
                    self.gList.RefreshUI()
                self.fullRefresh = False
                self.frameActivated = False
                self.refreshing = False
                self.refreshed = True
                if bosh.inisettings['ClearRO']:
                    cmd = r'attrib -R "%s\*" /S /D' % (bosh.dirs['mods'])
                    ins,err = subprocess.Popen(cmd, stdout=subprocess.PIPE, startupinfo=startupinfo).communicate()
            except CancelError:
                # User canceled the refresh
                self.refreshing = False
                self.refreshed = True
            finally:
                if progress != None: progress.Destroy()
        elif self.frameActivated and data.refreshConvertersNeeded():
            self.refreshing = True
            progress = balt.Progress(_("Refreshing Converters..."),'\n'+' '*60)
            try:
                what = ('C')
                if data.refresh(progress,what,self.fullRefresh):
                    self.gList.RefreshUI()
                self.fullRefresh = False
                self.frameActivated = False
                self.refreshing = False
            except CancelError:
                # User canceled the refresh
                self.refreshing = False
            finally:
                if progress != None: progress.Destroy()
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
        text = _('Packages: %d/%d') % (active,len(self.data.data))
        statusBar.SetStatusText(text,2)

    def _OnCommentsSplitterSashPosChanged(self, event):
        # ignore spurious events caused by invisible layout adjustments during initialization
        if not self.refreshed: return
        # save new comments text box size
        splitter = event.GetEventObject()
        sashPos = splitter.GetSashPosition() - splitter.GetSize()[1]
        settings['bash.installers.commentsSplitterSashPos'] = sashPos

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
            del bosh.modInfos.plugins.selectedBad[:]
            bosh.modInfos.autoGrouped.clear()
            modList.RefreshUI('ALL')
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
                if (index == currentIndex): self.RefreshInfoPage(index,installer)
                else: gPage.SetValue('')
            #--Sub-Packages
            self.gSubList.Clear()
            if len(installer.subNames) <= 2:
                self.gSubList.Clear()
            else:
                balt.setCheckListItems(self.gSubList, installer.subNames[1:],installer.subActives[1:])
            #--Espms
            if not installer.espms:
                self.gEspmList.Clear()
            else:
                names = self.espms = sorted(installer.espms)
                names.sort(key=lambda x: x.cext != '.esm')
                balt.setCheckListItems(self.gEspmList, [['','*'][installer.isEspmRenamed(x.s)]+x.s for x in names],
                    [x not in installer.espmNots for x in names])
            #--Comments
            self.gComments.SetValue(installer.comments)
        else:
            self.gPackage.SetValue('')
            for index,(gPage,state) in enumerate(self.infoPages):
                self.infoPages[index][1] = True
                gPage.SetValue('')
            self.gSubList.Clear()
            self.gEspmList.Clear()
            self.gComments.SetValue('')

    def RefreshInfoPage(self,index,installer):
        """Refreshes notebook page."""
        gPage,initialized = self.infoPages[index]
        if initialized: return
        else: self.infoPages[index][1] = True
        pageName = gPage.GetName()
        sNone = _('[None]')
        def sortKey(file):
            dirFile = file.lower().rsplit('\\',1)
            if len(dirFile) == 1: dirFile.insert(0,'')
            return dirFile
        def dumpFiles(installer,files,default='',header='',isPath=False):
            if files:
                buff = stringBuffer()
                if isPath: files = [x.s for x in files]
                else: files = list(files)
                sortKeys = dict((x,sortKey(x)) for x in files)
                files.sort(key=lambda x: sortKeys[x])
                if header: buff.write(header+'\n')
                for file in files:
                    oldName = installer.getEspmName(file)
                    buff.write(oldName)
                    if oldName != file:
                        buff.write(' -> ')
                        buff.write(file)
                    buff.write('\n')
                return buff.getvalue()
            elif header:
                return header+'\n'
            else:
                return ''
        if pageName == 'gGeneral':
            info = _("== Overview\n")
            info += _("Type: ")
            if isinstance(installer,bosh.InstallerProject):
                info += _('Project')
            elif isinstance(installer,bosh.InstallerMarker):
                info += _('Marker')
            elif isinstance(installer,bosh.InstallerArchive):
                info += _('Archive')
            else:
                info += _('Unrecognized')
            info += '\n'
            if isinstance(installer,bosh.InstallerMarker):
                info += _("Structure: N/A\n")
            elif installer.type == 1:
                info += _("Structure: Simple\n")
            elif installer.type == 2:
                if len(installer.subNames) == 2:
                    info += _("Structure: Complex/Simple\n")
                else:
                    info += _("Structure: Complex\n")
            elif installer.type < 0:
                info += _("Structure: Corrupt/Incomplete\n")
            else:
                info += _("Structure: Unrecognized\n")
            nConfigured = len(installer.data_sizeCrc)
            nMissing = len(installer.missingFiles)
            nMismatched = len(installer.mismatchedFiles)
            if isinstance(installer,bosh.InstallerProject):
                info += _("Size: %s KB\n") % formatInteger(installer.size/1024)
            elif isinstance(installer,bosh.InstallerMarker):
                info += _("Size: N/A\n")
            elif isinstance(installer,bosh.InstallerArchive):
                if installer.isSolid:
                    if installer.blockSize:
                        sSolid = _("Solid, Block Size: %d MB") % installer.blockSize
                    elif installer.blockSize is None:
                        sSolid = _("Solid, Block Size: Unknown")
                    else:
                        sSolid = _("Solid, Block Size: 7z Default")
                else:
                    sSolid = _("Non-solid")
                info += _("Size: %s KB (%s)\n") % (formatInteger(installer.size/1024),sSolid)
            else:
                info += _("Size: Unrecognized\n")
            info += (_("Modified: %s\n") % formatDate(installer.modified),_(
                "Modified: N/A\n"),)[isinstance(installer,bosh.InstallerMarker)]
            info += (_("Data CRC: %08X\n") % (installer.crc),_(
                "Data CRC: N/A\n"),)[isinstance(installer,bosh.InstallerMarker)]
            info += (_("Files: %s\n") % formatInteger(len(installer.fileSizeCrcs)),_(
                "Files: N/A\n"),)[isinstance(installer,bosh.InstallerMarker)]
            info += (_("Configured: %s (%s KB)\n") % (
                formatInteger(nConfigured), formatInteger(installer.unSize/1024)),_(
                "Configured: N/A\n"),)[isinstance(installer,bosh.InstallerMarker)]
            info += (_("  Matched: %s\n") % formatInteger(nConfigured-nMissing-nMismatched),_(
                "  Matched: N/A\n"),)[isinstance(installer,bosh.InstallerMarker)]
            info += (_("  Missing: %s\n") % formatInteger(nMissing),_(
                "  Missing: N/A\n"),)[isinstance(installer,bosh.InstallerMarker)]
            info += (_("  Conflicts: %s\n") % formatInteger(nMismatched),_(
                "  Conflicts: N/A\n"),)[isinstance(installer,bosh.InstallerMarker)]
            info += '\n'
            #--Infoboxes
            gPage.SetValue(info+dumpFiles(installer,installer.data_sizeCrc,sNone,
                _("== Configured Files"),isPath=True))
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
            gPage.SetValue('\n'.join((
                dumpFiles(installer,installer.skipExtFiles,sNone,_('== Skipped (Extension)')),
                dumpFiles(installer,installer.skipDirFiles,sNone,_('== Skipped (Dir)')),
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
        if not wx.GetKeyState(wx.WXK_SHIFT):
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
        name = self.gEspmList.GetString(index)
        if name[0] == '*':
            name = name[1:]
        espm = GPath(name)
        if self.gEspmList.IsChecked(index):
            espmNots.discard(espm)
        else:
            espmNots.add(espm)
        self.gEspmList.SetSelection(index)    # so that (un)checking also selects (moves the highlight)
        if not wx.GetKeyState(wx.WXK_SHIFT):
            self.refreshCurrent(installer)

#------------------------------------------------------------------------------
class ReplacersList(List):
    #--Class Data
    mainMenu = Links() #--Column menu
    itemMenu = Links() #--Single item menu

    def __init__(self,parent):
        #--Columns
        self.cols = settings['bash.replacers.cols']
        self.colAligns = settings['bash.replacers.colAligns']
        self.colNames = settings['bash.colNames']
        self.colReverse = settings.getChanged('bash.replacers.colReverse')
        self.colWidths = settings['bash.replacers.colWidths']
        #--Data/Items
        self.data = bosh.replacersData = bosh.ReplacersData()
        self.sort = settings['bash.replacers.sort']
        #--Links
        self.mainMenu = ReplacersList.mainMenu
        self.itemMenu = ReplacersList.itemMenu
        #--Parent init
        List.__init__(self,parent,-1,ctrlStyle=(wx.LC_REPORT|wx.SUNKEN_BORDER))
        #--Image List
        checkboxesIL = colorChecks.GetImageList()
        self.list.SetImageList(checkboxesIL,wx.IMAGE_LIST_SMALL)
        #--Events
        #wx.EVT_LIST_ITEM_SELECTED(self,self.listId,self.OnItemSelected)

    def RefreshUI(self,files='ALL',detail='SAME'):
        """Refreshes UI for specified files."""
        #--Details
        if detail == 'SAME':
            selected = set(self.GetSelected())
        else:
            selected = set([detail])
        #--Populate
        if files == 'ALL':
            self.PopulateItems(selected=selected)
        elif isinstance(files,bolt.Path):
            self.PopulateItem(files,selected=selected)
        else: #--Iterable
            for file in files:
                self.PopulateItem(file,selected=selected)

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
            else:
                value = '-'
            if mode and (colDex == 0):
                self.list.InsertStringItem(itemDex, value)
            else:
                self.list.SetStringItem(itemDex, colDex, value)
        #--Image
        self.list.SetItemImage(itemDex,self.checkboxes.Get(0,fileInfo.isApplied()))

    #--Sort Items
    def SortItems(self,col=None,reverse=-2):
        (col, reverse) = self.GetSortSettings(col,reverse)
        settings['bash.screens.sort'] = col
        data = self.data
        #--Start with sort by name
        self.items.sort()
        if col == 'File':
            pass #--Done by default
        else:
            raise BashError(_('Unrecognized sort key: ')+col)
        #--Ascending
        if reverse: self.items.reverse()

    #--Events ---------------------------------------------
    #--Column Resize
    def OnColumnResize(self,event):
        super(ReplacersList,self).OnColumnResize(event)
        settings.setChanged('bash.screens.colWidths')

    #--Event: Left Down
    def OnLeftDown(self,event):
        (hitItem,hitFlag) = self.list.HitTest((event.GetX(),event.GetY()))
        if hitFlag == 32:
            item = GPath(self.items[hitItem])
            replacer = self.data[item]
            #--Unselect?
            if replacer.isApplied():
                try:
                    wx.BeginBusyCursor()
                    replacer.remove()
                finally:
                    wx.EndBusyCursor()
            #--Select?
            else:
                progress = None
                try:
                    progress = balt.Progress(item.s)
                    replacer.apply(progress)
                finally:
                    if progress != None: progress.Destroy()
            self.RefreshUI(item)
            bosh.modInfos.refresh()
            modList.RefreshUI()
            return True
        #--Pass Event onward
        event.Skip()

#------------------------------------------------------------------------------
class ReplacersPanel(NotebookPanel):
    """Replacers tab."""
    def __init__(self,parent):
        """Initialize."""
        wx.Panel.__init__(self, parent, -1)
        self.gList = ReplacersList(self)
        #--Buttons
        self.gAuto = checkBox(self,_("Automatic"),onCheck=self.OnAutomatic,
            tip=_("Automatically update Textures BSA after adding/removing a replacer."))
        self.gAuto.SetValue(settings['bash.replacers.autoChecked'])
        self.gInvalidate = button(self,_("Update"),onClick=self.OnInvalidateTextures,
            tip=_("Enable replacement textures by updating Textures archive."))
        self.gReset = button(self,_("Restore"),onClick=self.OnResetTextures,
            tip=_("Restore Textures archive to its original state."))
        #--Layout
        self.gTexturesBsa = vsbSizer((self,-1,_("Textures BSA")),
            ((0,4),),
            (self.gAuto,0,wx.ALL^wx.BOTTOM,4),
            ((0,8),),
            (self.gInvalidate,0,wx.ALL^wx.BOTTOM,4),
            (self.gReset,0,wx.ALL,4),
            )
        sizer = hSizer(
            (self.gTexturesBsa,0,wx.ALL|10),
            (self.gList,1,wx.GROW|wx.LEFT,4))
        self.SetSizer(sizer)

    def SetStatusCount(self):
        """Sets status bar count field."""
        numUsed = len([info for info in self.gList.data.values() if info.isApplied()])
        text = _('Reps: %d/%d') % (numUsed,len(self.gList.data.data))
        statusBar.SetStatusText(text,2)

    def OnShow(self):
        """Panel is shown. Update self.data."""
        if bosh.replacersData.refresh():
            self.gList.RefreshUI()
        #--vs. OBMM?
        enableBsaEdits = not (
            bosh.dirs['mods'].join('ConsoleBSAEditData2').exists() or
            bosh.dirs['app'].join('OBMM','BSAedits').exists())
        self.gAuto.Enable(enableBsaEdits)
        self.gInvalidate.Enable(enableBsaEdits)
        self.gReset.Enable(enableBsaEdits)
        if enableBsaEdits:
            self.gTexturesBsa.GetStaticBox().SetToolTip(None)
            settings['bash.replacers.autoEditBSAs'] = settings['bash.replacers.autoChecked']
        else:
            self.gTexturesBsa.GetStaticBox().SetToolTip(tooltip(
                _("BSA editing disabled becase OBMM or BSAPatch is in use.")))
            settings['bash.replacers.autoEditBSAs'] = False
        self.SetStatusCount()

    def ContinueEdit(self):
        """Continuation warning for Invalidate and Reset."""
        message = _("Edit Textures BSA?\n\nThis command directly edits the Oblivion - Textures - Compressed.bsa file. If the file becomes corrupted (very unlikely), you will need to reinstall Oblivion or restore it from another source.")
        return balt.askContinue(self,message,'bash.replacers.editBSAs.continue',_('Textures BSA'))

    def OnAutomatic(self,event=None):
        """Automatic checkbox changed."""
        isChecked = self.gAuto.IsChecked()
        if isChecked and not self.ContinueEdit():
            self.gAuto.SetValue(False)
            return
        settings['bash.replacers.autoChecked'] = isChecked
        settings['bash.replacers.autoEditBSAs'] = isChecked

    def OnInvalidateTextures(self,event):
        """Invalid."""
        if not self.ContinueEdit(): return
        bsaPath = bosh.modInfos.dir.join('Oblivion - Textures - Compressed.bsa')
        bsaFile = bosh.BsaFile(bsaPath)
        bsaFile.scan()
        result = bsaFile.invalidate()
        balt.showOk(self,
            _("BSA Hashes reset: %d\nBSA Hashes Invalidated: %d.\nAIText entries: %d.") %
            tuple(map(len,result)))

    def OnResetTextures(self,event):
        """Invalid."""
        if not self.ContinueEdit(): return
        bsaPath = bosh.modInfos.dir.join('Oblivion - Textures - Compressed.bsa')
        bsaFile = bosh.BsaFile(bsaPath)
        bsaFile.scan()
        resetCount = bsaFile.reset()
        balt.showOk(self,_("BSA Hashes reset: %d") % (resetCount,))

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
        rePattern = re.compile(r'^([^\\/]+?)(\d*)((\.(jpg|jpeg|png|tif|bmp))+)$',re.I)
        maPattern = rePattern.match(newName)
        if not maPattern:
            balt.showError(self,_('Bad extension or file root: ')+newName)
            event.Veto()
            return
        root,numStr = maPattern.groups()[:2]
        #--Rename each screenshot, keeping the old extension
        numLen = len(numStr)
        num = int(numStr or 0)
        screensDir = bosh.screensData.dir
        wx.BeginBusyCursor()
        newselected = []
        for file in selected:
            newName = GPath(root+numStr+file.ext)
            newselected.append(newName)
            newPath = screensDir.join(newName)
            oldPath = screensDir.join(file)
            if not newPath.exists():
                oldPath.moveTo(newPath)
            num += 1
            numStr = `num`
            numStr = '0'*(numLen-len(numStr))+numStr
        bosh.screensData.refresh()
        self.RefreshUI()
        #--Reselected the renamed items
        for file in newselected:
            index = self.list.FindItem(0,file.s)
            if index != -1:
                self.list.SetItemState(index,wx.LIST_STATE_SELECTED,wx.LIST_STATE_SELECTED)
        event.Veto()
        wx.EndBusyCursor()

    def RefreshUI(self,files='ALL',detail='SAME'):
        """Refreshes UI for specified files."""
        #--Details
        if detail == 'SAME':
            selected = set(self.GetSelected())
        else:
            selected = set([detail])
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
                value = '-'
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
            raise BashError(_('Unrecognized sort key: ')+col)
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
            try:
                wx.BeginBusyCursor()
                self.DeleteSelected()
            finally:
                wx.EndBusyCursor()
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
        ##Ctrl-A
        if event.ControlDown() and event.GetKeyCode() in (65,97):
            self.SelectAll()
        event.Skip()

    #--Column Resize
    def OnColumnResize(self,event):
        super(ScreensList,self).OnColumnResize(event)
        settings.setChanged('bash.screens.colWidths')

    def OnItemSelected(self,event=None):
        fileName = self.items[event.m_itemIndex]
        filePath = bosh.screensData.dir.join(fileName)
        bitmap = (filePath.exists() and wx.Bitmap(filePath.s)) or None
        self.picture.SetBitmap(bitmap)

#------------------------------------------------------------------------------
class ScreensPanel(NotebookPanel):
    """Screenshots tab."""
    def __init__(self,parent):
        """Initialize."""
        wx.Panel.__init__(self, parent, -1)
        #--Left
        sashPos = settings.get('bash.screens.sashPos',120)
        left = self.left = leftSash(self,defaultSize=(sashPos,100),onSashDrag=self.OnSashDrag)
        right = self.right =  wx.Panel(self,style=wx.NO_BORDER)
        #--Contents
        global screensList
        screensList = ScreensList(left)
        screensList.SetSizeHints(100,100)
        screensList.picture = balt.Picture(right,256,192)
        #--Events
        self.Bind(wx.EVT_SIZE,self.OnSize)
        #--Layout
        #left.SetSizer(hSizer((screensList,1,wx.GROW),((10,0),0)))
        right.SetSizer(hSizer((screensList.picture,1,wx.GROW)))
        wx.LayoutAlgorithm().LayoutWindow(self, right)

    def SetStatusCount(self):
        """Sets status bar count field."""
        text = _('Screens: %d') % (len(screensList.data.data),)
        statusBar.SetStatusText(text,2)

    def OnSashDrag(self,event):
        """Handle sash moved."""
        wMin,wMax = 80,self.GetSizeTuple()[0]-80
        sashPos = max(wMin,min(wMax,event.GetDragRect().width))
        self.left.SetDefaultSize((sashPos,10))
        wx.LayoutAlgorithm().LayoutWindow(self, self.right)
        screensList.picture.Refresh()
        settings['bash.screens.sashPos'] = sashPos

    def OnSize(self,event=None):
        wx.LayoutAlgorithm().LayoutWindow(self, self.right)

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
            selected = set([detail])
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
                value = formatInteger(fileInfo.size/1024)+' KB'
            else:
                value = '-'
            if mode and (colDex == 0):
                self.list.InsertStringItem(itemDex, value)
            else:
                self.list.SetStringItem(itemDex, colDex, value)
        #--Image
        #status = fileInfo.getStatus()
        on = fileName.cext == '.bsa'
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
            raise BashError(_('Unrecognized sort key: ')+col)
        #--Ascending
        if reverse: self.items.reverse()

    #--Events ---------------------------------------------
    def OnChar(self,event):
        """Char event: Reordering."""
        if (event.GetKeyCode() == 127):
            self.DeleteSelected()
        event.Skip()

    #--Column Resize
    def OnColumnResize(self,event):
        super(BSAList,self).OnColumnResize(event)
        settings.setChanged('bash.BSAs.colWidths')

    #--Event: Left Down
    def OnLeftDown(self,event):
        (hitItem,hitFlag) = self.list.HitTest((event.GetX(),event.GetY()))
        if hitFlag == 32:
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
        self.file = wx.TextCtrl(self,id,"",size=(textWidth,-1))
        self.file.SetMaxLength(256)
        wx.EVT_KILL_FOCUS(self.file,self.OnEditFile)
        wx.EVT_TEXT(self.file,id,self.OnTextEdit)

        #--BSA Info
        self.gInfo = wx.TextCtrl(self,-1,"",size=(textWidth,100),style=wx.TE_MULTILINE)
        self.gInfo.SetMaxLength(2048)
        self.gInfo.Bind(wx.EVT_TEXT,self.OnInfoEdit)
        #--Save/Cancel
        self.save = button(self,id=wx.ID_SAVE,onClick=self.DoSave)
        self.cancel = button(self,id=wx.ID_CANCEL,onClick=self.DoCancel)
        self.save.Disable()
        self.cancel.Disable()
        #--Layout
        sizer = vSizer(
            (staticText(self,_("File:")),0,wx.TOP,4),
            (self.file,0,wx.EXPAND|wx.TOP,4),
            #(hSizer(
            #    (self.playerInfo,1,wx.EXPAND),
            #    (self.gCoSaves,0,wx.EXPAND),
            #    ),0,wx.EXPAND|wx.TOP,4),
            #(self.picture,0,wx.TOP,4),
            #(staticText(self,_("Masters:")),0,wx.TOP,4),
            #(self.masters,2,wx.EXPAND|wx.TOP,4),
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
        #--Picture
        #if not self.picData:
        #    self.picture.SetBitmap(None)
        #else:
        #    width,height,data = self.picData
        #    image = wx.EmptyImage(width,height)
        #    image.SetData(data)
        #    self.picture.SetBitmap(image.ConvertToBitmap())
        #--Edit State
        self.edited = 0
        self.save.Disable()
        self.cancel.Disable()
        #--Info Box
        self.gInfo.DiscardEdits()
        if fileName:
            self.gInfo.SetValue(bosh.BSAInfos.table.getItem(fileName,'info',_('Notes: ')))
        else:
            self.gInfo.SetValue(_('Notes: '))

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
        if self.fileStr[-4:].lower() not in ('.bsa'):
            balt.showError(self,"Incorrect file extension: "+fileStr[-3:])
            self.file.SetValue(self.fileStr)
        #--Else file exists?
        elif self.BSAInfo.dir.join(fileStr).exists():
            balt.showError(self,"File %s already exists." % (fileStr,))
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
        #--Change masters?
        #if changeMasters:
        #    BSAInfo.header.masters = self.masters.GetNewMasters()
        #    BSAInfo.header.writeMasters(BSAInfo.getPath())
        #    BSAInfo.setmtime(prevMTime)
        #--Done
        try:
            bosh.BSAInfos.refreshFile(BSAInfo.name)
            self.SetFile(self.BSAInfo.name)
        except bosh.FileError:
            balt.showError(self,_('File corrupted on save!'))
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
        wx.Panel.__init__(self, parent, -1)
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
        text = _("BSAs: %d") % (len(bosh.BSAInfos.data))
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
        List.__init__(self,parent,-1,ctrlStyle=(wx.LC_REPORT|wx.SUNKEN_BORDER))
        #--Events
        wx.EVT_LIST_ITEM_SELECTED(self,self.listId,self.OnItemSelected)
        self.list.Bind(wx.EVT_KEY_UP, self.OnKeyUp)

    def GetItems(self):
        """Set and return self.items."""
        if self.searchResults != None:
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
            selected = set([detail])
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
                value = '-'
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
            reNoRe = re.compile('^Re: *')
            self.items.sort(key=lambda a: reNoRe.sub('',data[a][0]))
        elif col == 'Author':
            self.items.sort(key=lambda a: data[a][1])
        elif col == 'Date':
            pass #--Default sort
        else:
            raise BashError(_('Unrecognized sort key: ')+col)
        #--Ascending
        if reverse: self.items.reverse()

    #--Events ---------------------------------------------
    def OnKeyUp(self,event):
        """Char event: Activate selected items, select all items"""
        ##Ctrl-A
        if event.ControlDown() and event.GetKeyCode() in (65,97):
            self.SelectAll()
        event.Skip()

    #--Column Resize
    def OnColumnResize(self,event):
        super(MessageList,self).OnColumnResize(event)
        settings.setChanged('bash.messages.colWidths')

    def OnItemSelected(self,event=None):
        keys = self.GetSelected()
        path = bosh.dirs['saveBase'].join('Messages.html')
        bosh.messages.writeText(path,*keys)
        self.gText.Navigate(path.s,0x2) #--0x2: Clear History
        #self.list.SetFocus()

#------------------------------------------------------------------------------
class MessagePanel(NotebookPanel):
    """Messages tab."""
    def __init__(self,parent):
        """Initialize."""
        import wx.lib.iewin
        wx.Panel.__init__(self, parent, -1)
        #--Left
        sashPos = settings.get('bash.messages.sashPos',120)
        gTop = self.gTop =  topSash(self,defaultSize=(100,sashPos),onSashDrag=self.OnSashDrag)
        gBottom = self.gBottom =  wx.Panel(self,style=wx.NO_BORDER)
        #--Contents
        global gMessageList
        gMessageList = MessageList(gTop)
        gMessageList.SetSizeHints(100,100)
        gMessageList.gText = wx.lib.iewin.IEHtmlWindow(gBottom, -1, style = wx.NO_FULL_REPAINT_ON_RESIZE)
        #--Search
        gSearchBox = self.gSearchBox = wx.TextCtrl(gBottom,-1,"",style=wx.TE_PROCESS_ENTER)
        gSearchButton = button(gBottom,_("Search"),onClick=self.DoSearch)
        gClearButton = button(gBottom,_("Clear"),onClick=self.DoClear)
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
        if gMessageList.searchResults != None:
            numUsed = len(gMessageList.searchResults)
        else:
            numUsed = len(gMessageList.items)
        text = _('PMs: %d/%d') % (numUsed,len(gMessageList.data.keys()))
        statusBar.SetStatusText(text,2)

    def OnSashDrag(self,event):
        """Handle sash moved."""
        hMin,hMax = 80,self.GetSizeTuple()[1]-80
        sashPos = max(hMin,min(hMax,event.GetDragRect().height))
        self.gTop.SetDefaultSize((10,sashPos))
        wx.LayoutAlgorithm().LayoutWindow(self, self.gBottom)
        settings['bash.messages.sashPos'] = sashPos

    def OnSize(self,event=None):
        wx.LayoutAlgorithm().LayoutWindow(self, self.gTop)
        wx.LayoutAlgorithm().LayoutWindow(self, self.gBottom)

    def OnShow(self):
        """Panel is shown. Update self.data."""
        if bosh.messages.refresh():
            gMessageList.RefreshUI()
            #self.Refresh()
        self.SetStatusCount()

    def OnSearchChar(self,event):
        if event.GetKeyCode() == 13:
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
        self.gSearchBox.SetValue("")
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
        self.gName = wx.TextCtrl(right,-1,style=wx.TE_READONLY)
        self.gText = wx.TextCtrl(right,-1,style=wx.TE_MULTILINE)
        self.gKarma = spinCtrl(right,'0',min=-5,max=5,onSpin=self.OnSpin)
        self.gKarma.SetSizeHints(40,-1)
        #--Events
        self.Bind(wx.EVT_SIZE,self.OnSize)
        #--Layout
        right.SetSizer(vSizer(
            (hSizer(
                (self.gName,1,wx.GROW),
                (self.gKarma,0,wx.GROW),
                ),0,wx.GROW),
            (self.gText,1,wx.GROW|wx.TOP,4),
            ))
        wx.LayoutAlgorithm().LayoutWindow(self, right)

    def SetStatusCount(self):
        """Sets status bar count field."""
        text = _('People: %d') % (len(self.data.data),)
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
            self.gName.SetValue('')
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
        self.gPackage = wx.TextCtrl(right,-1,style=wx.TE_READONLY)
        self.gAuthor = wx.TextCtrl(right,-1)
        self.gVersion = wx.TextCtrl(right,-1)
        #--Right tags, abstract, review
        self.gTags = wx.TextCtrl(right,-1)
        self.gAbstract = wx.TextCtrl(right,-1,style=wx.TE_MULTILINE)
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
            staticText(right,_('Package')),
            (self.gPackage,0,wx.GROW),
            staticText(right,_('Author')),
            (self.gAuthor,0,wx.GROW),
            staticText(right,_('Version')),
            (self.gVersion,0,wx.GROW),
            staticText(right,_('Tags')),
            (self.gTags,0,wx.GROW),
            ])
        #--Events
        self.Bind(wx.EVT_SIZE,self.OnSize)
        #--Layout
        right.SetSizer(vSizer(
            (fgSizer,0,wx.GROW|wx.TOP|wx.LEFT,3),
            staticText(right,_('Abstract')),
            (self.gAbstract,1,wx.GROW|wx.TOP,4),
            ))
        wx.LayoutAlgorithm().LayoutWindow(self, right)

    def SetStatusCount(self):
        """Sets status bar count field."""
        text = _('ModBase: %d') % (len(self.data.data),)
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
class BashNotebook(wx.Notebook):
    def __init__(self, parent, id):
        wx.Notebook.__init__(self, parent, id)
        #--Pages
        self.AddPage(InstallersPanel(self),_("Installers"))
        iInstallers = self.GetPageCount()-1
        if bosh.inisettings['EnableReplacers'] and (settings['bash.replacers.show'] or bosh.dirs['mods'].join("Replacers").list()):
            self.AddPage(ReplacersPanel(self),_("Replacers"))
        self.AddPage(ModPanel(self),_("Mods"))
        iMods = self.GetPageCount()-1
        #self.AddPage(BSAPanel(self),_("BSAs"))
        self.AddPage(SavePanel(self),_("Saves"))
        self.AddPage(INIPanel(self),_("INI Edits"))
        self.AddPage(ScreensPanel(self),_("Screenshots"))
        if re.match('win',sys.platform):
            try:
                self.AddPage(MessagePanel(self),_("PM Archive"))
            except ImportError:
                if bolt.deprintOn:
                    print _("PM Archive panel disabled due to Import Error (most likely comtypes)")
        self.AddPage(PeoplePanel(self),_("People"))
        #self.AddPage(ModBasePanel(self),_("ModBase"))
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED,self.OnShowPage)
        #--Selection
        pageIndex = min(settings['bash.page'],self.GetPageCount()-1)
        if settings['bash.installers.fastStart'] and pageIndex == iInstallers:
            pageIndex = iMods
        self.SetSelection(pageIndex)

    def OnShowPage(self,event):
        """Call page's OnShow command."""
        if event.GetId() == self.GetId():
            self.GetPage(event.GetSelection()).OnShow()
            event.Skip()

#------------------------------------------------------------------------------
class BashStatusBar(wx.StatusBar):
    #--Class Data
    buttons = Links()

    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent, -1)
        global statusBar
        statusBar = self
        self.SetFieldsCount(3)
        buttons = BashStatusBar.buttons
        self.size = int(bosh.inisettings['IconSize'])
        self.size += 8
        self.buttons = []
        for link in buttons:
            gButton = link.GetBitmapButton(self,style=wx.NO_BORDER)
            if gButton: self.buttons.append(gButton)
        self.SetStatusWidths([self.size*len(self.buttons),-1, 130])
        self.SetSize((-1, self.size))
        self.GetParent().SendSizeEvent()
        self.OnSize() #--Position buttons
        wx.EVT_SIZE(self,self.OnSize)
        #--Bind events
        #--Clear text notice
        self.Bind(wx.EVT_TIMER, self.OnTimer)

    def OnSize(self,event=None):
        rect = self.GetFieldRect(0)
        (xPos,yPos) = (rect.x+1,rect.y+1)
        for button in self.buttons:
            button.SetPosition((xPos,yPos))
            xPos += self.size
        if event: event.Skip()

    def SetText(self,text="",timeout=5):
        """Set's display text as specified. Empty string clears the field."""
        self.SetStatusText(text,1)
        if timeout > 0:
            wx.Timer(self).Start(timeout*1000,wx.TIMER_ONE_SHOT)

    def OnTimer(self,evt):
        """Clears display text as specified. Empty string clears the field."""
        self.SetStatusText("",1)

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
        wx.Frame.__init__(self, parent, -1, 'Wrye Bash', pos, size,style)
        minSize = settings['bash.frameSize.min']
        self.SetSizeHints(minSize[0],minSize[1])
        self.SetTitle()
        #--Application Icons
        self.SetIcons(bashRed)
        #--Status Bar
        self.SetStatusBar(BashStatusBar(self))
        #--Notebook panel
        self.notebook = notebook = BashNotebook(self,-1)
        #--Events
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.Bind(wx.EVT_ACTIVATE, self.RefreshData)
        #--Data
        self.inRefreshData = False #--Prevent recursion while refreshing.
        self.knownCorrupted = set()
        self.oblivionIniCorrupted = False
        self.incompleteInstallError = False
        bosh.bsaInfos = bosh.BSAInfos()
        #--Layout
        sizer = vSizer((notebook,1,wx.GROW))
        self.SetSizer(sizer)

    def SetTitle(self,title=None):
        """Set title. Set to default if no title supplied."""
        if not title:
            ###Remove from Bash after CBash integrated
            if not CBash:
                title = "Wrye Bash %s: " % (settings['bash.readme'][1],)
            else:
                title = "Wrye Bash %s, CBash v%u.%u.%u: " % (settings['bash.readme'][1], CBash.GetVersionMajor(), CBash.GetVersionMinor(), CBash.GetVersionRevision())
            maProfile = re.match(r'Saves\\(.+)\\$',bosh.saveInfos.localSave)
            if maProfile:
                title += maProfile.group(1)
            else:
                title += _("Default")
            if bosh.modInfos.voCurrent:
                title += ' ['+bosh.modInfos.voCurrent+']'
        wx.Frame.SetTitle(self,title)

    def SetStatusCount(self):
        """Sets the status bar count field. Actual work is done by current panel."""
        if hasattr(self,'notebook'): #--Hack to get around problem with screens tab.
            self.notebook.GetPage(self.notebook.GetSelection()).SetStatusCount()

    #--Events ---------------------------------------------
    def RefreshData(self, event=None):
        """Refreshes all data. Can be called manually, but is also triggered by window activation event."""
        def listFiles(files):
            text = '\n* '
            text += '\n* '.join(x.s for x in files[:min(15,len(files))])
            if len(files)>10:
                text += _('\n+ %d others') % (len(files)-15,)
            return text
        #--Ignore deactivation events.
        if event and not event.GetActive() or self.inRefreshData: return
        #--UPDATES-----------------------------------------
        self.inRefreshData = True
        popMods = popSaves = popInis = None
        #--Config helpers
        bosh.configHelpers.refresh()
        #--Check plugins.txt and mods directory...
        if bosh.modInfos.refresh(doAutoGroup=True):
            popMods = 'ALL'
        #--Have any mtimes been reset?
        if bosh.modInfos.mtimesReset:
            if bosh.modInfos.mtimesReset[0] == 'FAILED':
                balt.showWarning(self,_("It appears that the current user doesn't have permissions for some or all of the files in Oblivion\\Data.\nSpecifically had permission denied to change the time on:\n%s") % bosh.modInfos.mtimesReset[1].s)
            if not bosh.inisettings['SkipResetTimeNotifications']:
                message = _('Modified dates have been reset for some mod files:')
                message += listFiles(sorted(bosh.modInfos.mtimesReset))
                balt.showInfo(self,message)
            del bosh.modInfos.mtimesReset[:]
            popMods = 'ALL'
        #--Mods autogrouped?
        if bosh.modInfos.autoGrouped:
            message = _("Some mods have been auto-grouped:")
            agDict = bosh.modInfos.autoGrouped
            ordered = bosh.modInfos.getOrdered(agDict.keys())
            agList = [x+': '+agDict[x]for x in ordered]
            message += listFiles(agList)
            agDict.clear()
            balt.showInfo(self,message)
        #--Check savegames directory...
        if bosh.saveInfos.refresh():
            popSaves = 'ALL'
        #--Check INI Tweaks...
        if bosh.iniInfos.refresh():
            popInis = 'ALL'
        #--Ensure BSA timestamps are good
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
        if bosh.modInfos.plugins.selectedBad:
            message = _("Missing files have been removed from load list:")
            message += listFiles(bosh.modInfos.plugins.selectedBad)
            del bosh.modInfos.plugins.selectedBad[:]
            bosh.modInfos.plugins.save()
            balt.showWarning(self,message)
        #--Was load list too long?
        if bosh.modInfos.plugins.selectedExtra:
            message = _("Load list is overloaded. Some files have been de-activated:")
            message += listFiles(bosh.modInfos.plugins.selectedExtra)
            del bosh.modInfos.plugins.selectedExtra[:]
            bosh.modInfos.plugins.save()
            balt.showWarning(self,message)
        #--Any new corrupted files?
        message = ''
        corruptMods = set(bosh.modInfos.corrupted.keys())
        if not corruptMods <= self.knownCorrupted:
            message += _("The following mod files have corrupted headers: ")
            message += listFiles(sorted(corruptMods))
            self.knownCorrupted |= corruptMods
        corruptSaves = set(bosh.saveInfos.corrupted.keys())
        if not corruptSaves <= self.knownCorrupted:
            if message: message += '\n'
            message += _("The following save files have corrupted headers: ")
            message += listFiles(sorted(corruptSaves))
            self.knownCorrupted |= corruptSaves
        if message: balt.showWarning(self,message)
        #--Corrupt Oblivion.ini
        if self.oblivionIniCorrupted != bosh.oblivionIni.isCorrupted:
            self.oblivionIniCorrupted = bosh.oblivionIni.isCorrupted
            if self.oblivionIniCorrupted:
                message = _('Your Oblivion.ini should begin with a section header (e.g. "[General]"), but does not. You should edit the file to correct this.')
                balt.showWarning(self,fill(message))
        #--Any Y2038 Resets?
        if bolt.Path.mtimeResets:
            message = _("Bash cannot handle dates greater than January 19, 2038. Accordingly, the dates for the following files have been reset to an earlier date: ")
            message += listFiles(sorted(bolt.Path.mtimeResets))
            del bolt.Path.mtimeResets[:]
            balt.showWarning(self,message)
        #--OBMM Warning?
        if settings['bosh.modInfos.obmmWarn'] == 1:
            settings['bosh.modInfos.obmmWarn'] = 2
            message = _("Turn Lock Times Off?\n\nLock Times a feature which resets load order to a previously memorized state. While this feature is good for maintaining your load order, it will also undo any load order changes that you have made in OBMM.")
            lockTimes = not balt.askYes(self,message,_("Lock Times"))
            bosh.modInfos.lockTimes = settings['bosh.modInfos.resetMTimes'] = lockTimes
            if lockTimes:
                bosh.modInfos.resetMTimes()
            else:
                bosh.modInfos.mtimes.clear()
            message = _("Lock Times is now %s. To change it in the future, right click on the main list header on the Mods tab and select 'Lock Times'.")
            balt.showOk(self,message % ((_('off'),_('on'))[lockTimes],),_("Lock Times"))
        #--Missing docs directory?
        testFile = GPath(bosh.dirs['app']).join('Data','Docs','wtxt_teal.css')
        if not self.incompleteInstallError and not testFile.exists():
            self.incompleteInstallError = True
            message = _("Installation appears incomplete. Please re-unzip bash to Oblivion directory so that ALL files are installed.\n\nCorrect installation will create Oblivion\\Mopy, Oblivion\\Data\\Docs and Oblivion\\Data\\INI Tweaks directories.")
            balt.showWarning(self,message,_("Incomplete Installation"))
        #--Merge info
        oldMergeable = set(bosh.modInfos.mergeable)
        scanList = bosh.modInfos.refreshMergeable()
        difMergeable = oldMergeable ^ bosh.modInfos.mergeable
        if scanList:
            progress = balt.Progress(_("Mark Mergeable")+' '*30)
            progress.setFull(len(scanList))
            try:
                bosh.modInfos.rescanMergeable(scanList,progress)
            finally:
                progress.Destroy()
        if scanList or difMergeable:
            modList.RefreshUI(scanList + list(difMergeable))
        #--Done (end recursion blocker)
        self.inRefreshData = False

    def OnCloseWindow(self, event):
        """Handle Close event. Save application data."""
        self.SaveSettings()
        self.Destroy()

    def SaveSettings(self):
        """Save application data."""
        self.CleanSettings()
        if docBrowser: docBrowser.DoSave()
        if not self.IsIconized() or self.IsMaximized():
            settings['bash.framePos'] = self.GetPositionTuple()
            settings['bash.frameSize'] = self.GetSizeTuple()
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
        #--Clean backup
        for fileInfos in (bosh.modInfos,bosh.saveInfos):
            goodRoots = set(path.root for path in fileInfos.data.keys())
            backupDir = fileInfos.bashDir.join('Backups')
            if not backupDir.isdir(): continue
            for name in backupDir.list():
                path = backupDir.join(name)
                if name.root not in goodRoots and path.isfile():
                    path.remove()

#------------------------------------------------------------------------------
class DocBrowser(wx.Frame):
    """Doc Browser frame."""
    def __init__(self,modName=None):
        """Intialize.
        modName -- current modname (or None)."""
        import wx.lib.iewin
        #--Data
        self.modName = GPath(modName or '')
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
        docBrowser = self
        #--Window
        pos = settings['bash.modDocs.pos']
        size = settings['bash.modDocs.size']
        wx.Frame.__init__(self, bashFrame, -1, _('Doc Browser'), pos, size,
            style=wx.DEFAULT_FRAME_STYLE)
        self.SetBackgroundColour(wx.NullColour)
        self.SetSizeHints(250,250)
        #--Mod Name
        self.modNameBox = wx.TextCtrl(self,-1,style=wx.TE_READONLY)
        self.modNameList = wx.ListBox(self,-1,choices=sorted(x.s for x in self.data.keys()),style=wx.LB_SINGLE|wx.LB_SORT)
        self.modNameList.Bind(wx.EVT_LISTBOX,self.DoSelectMod)
        #wx.EVT_COMBOBOX(self.modNameBox,ID_SELECT,self.DoSelectMod)
        #--Application Icons
        self.SetIcons(bashDocBrowser)
        #--Set Doc
        self.setButton = button(self,_("Set Doc..."),onClick=self.DoSet)
        #--Forget Doc
        self.forgetButton = button(self,_("Forget Doc..."),onClick=self.DoForget)
        #--Rename Doc
        self.renameButton = button(self,_("Rename Doc..."),onClick=self.DoRename)
        #--Edit Doc
        self.editButton = wx.ToggleButton(self,ID_EDIT,_("Edit Doc..."))
        wx.EVT_TOGGLEBUTTON(self.editButton,ID_EDIT,self.DoEdit)
        self.openButton = button(self,_("Open Doc..."),onClick=self.DoOpen,tip=_("Open doc in external editor."))
        #--Html Back
        bitmap = wx.ArtProvider_GetBitmap(wx.ART_GO_BACK,wx.ART_HELP_BROWSER, (16,16))
        self.prevButton = bitmapButton(self,bitmap,onClick=self.DoPrevPage)
        #--Html Forward
        bitmap = wx.ArtProvider_GetBitmap(wx.ART_GO_FORWARD,wx.ART_HELP_BROWSER, (16,16))
        self.nextButton = bitmapButton(self,bitmap,onClick=self.DoNextPage)
        #--Doc Name
        self.docNameBox = wx.TextCtrl(self,-1,style=wx.TE_READONLY)
        #--Doc display
        self.plainText = wx.TextCtrl(self,-1,style=wx.TE_READONLY|wx.TE_MULTILINE|wx.TE_RICH2|wx.SUNKEN_BORDER)
        self.htmlText = wx.lib.iewin.IEHtmlWindow(self, -1, style = wx.NO_FULL_REPAINT_ON_RESIZE)
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
        docPath = docPath or GPath(self.data.get(self.modName,''))
        if not docPath.exists(): return False
        textFile = docPath.open()
        maText = re.match(r'^=.+=#\s*$',textFile.readline())
        textFile.close()
        return (maText != None)

    def DoHome(self, event):
        """Handle "Home" button click."""
        self.htmlText.GoHome()

    def DoPrevPage(self, event):
        """Handle "Back" button click."""
        self.htmlText.GoBack()

    def DoNextPage(self, event):
        """Handle "Next" button click."""
        self.htmlText.GoForward()

    def DoOpen(self,event):
        """Handle "Open Doc" button."""
        docPath = self.data.get(self.modName)
        if not docPath: return bell()
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
            fileName = GPath('')
        #--Dialog
        path = balt.askOpen(self,_("Select doc for %s:") % (modName.s,),
            docsDir,fileName, '*.*',mustExist=True)
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
        path = balt.askSave(self,_("Rename file to:"),workDir,fileName, '*.*')
        if not path or path == oldPath: return
        #--OS renaming
        path.remove()
        oldPath.moveTo(path)
        if self.docIsWtxt:
            oldHtml, newHtml = (x.root+'.html' for x in (oldPath,path))
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
            raise BoltError(_('Filename not defined.'))
        self.plainText.SaveFile(docPath.s)
        if self.docIsWtxt:
            docsDir = bosh.modInfos.dir.join('Docs')
            bolt.WryeText.genHtml(docPath, None, docsDir)

    def SetMod(self,modName=None):
        """Sets the mod to show docs for."""
        #--Save Current Edits
        self.DoSave()
        #--New modName
        self.modName = modName = GPath(modName or '')
        #--ModName
        if modName:
            self.modNameBox.SetValue(modName.s)
            index = self.modNameList.FindString(modName.s)
            self.modNameList.SetSelection(index)
            self.setButton.Enable(True)
        else:
            self.modNameBox.SetValue('')
            self.modNameList.SetSelection(wx.NOT_FOUND)
            self.setButton.Enable(False)
        #--Doc Data
        docPath = self.data.get(modName) or GPath('')
        docExt = docPath.cext
        self.docNameBox.SetValue(docPath.stail)
        self.forgetButton.Enable(docPath != '')
        self.renameButton.Enable(docPath != '')
        #--Edit defaults to false.
        self.editButton.SetValue(False)
        self.editButton.Enable(False)
        self.openButton.Enable(False)
        self.plainText.SetEditable(False)
        self.docIsWtxt = False
        #--View/edit doc.
        if not docPath:
            self.plainText.SetValue('')
            self.SetDocType('txt')
        elif not docPath.exists():
            myTemplate = bosh.modInfos.dir.join('Docs',_('My Readme Template.txt'))
            bashTemplate = bosh.modInfos.dir.join('Docs',_('Bash Readme Template.txt'))
            if myTemplate.exists():
                template = ''.join(myTemplate.open().readlines())
            elif bashTemplate.exists():
                template = ''.join(bashTemplate.open().readlines())
            else:
                template = '= $modName '+('='*(74-len(modName)))+'#\n'+docPath
            defaultText = string.Template(template).substitute(modName=modName.s)
            self.plainText.SetValue(defaultText)
            self.SetDocType('txt')
            if docExt in ('.txt','.etxt'):
                self.editButton.Enable(True)
                self.openButton.Enable(True)
                editing = self.docEdit.get(modName,True)
                self.editButton.SetValue(editing)
                self.plainText.SetEditable(editing)
            self.docIsWtxt = (docExt == '.txt')
        elif docExt in ('.htm','.html','.mht'):
            self.htmlText.Navigate(docPath.s,0x2) #--0x2: Clear History
            self.SetDocType('html')
        else:
            self.editButton.Enable(True)
            self.openButton.Enable(True)
            editing = self.docEdit.get(modName,False)
            self.editButton.SetValue(editing)
            self.plainText.SetEditable(editing)
            self.docIsWtxt = self.GetIsWtxt(docPath)
            htmlPath = self.docIsWtxt and docPath.root+'.html'
            if htmlPath and (not htmlPath.exists() or (docPath.mtime > htmlPath.mtime)):
                docsDir = bosh.modInfos.dir.join('Docs')
                bolt.WryeText.genHtml(docPath,None,docsDir)
            if not editing and htmlPath and htmlPath.exists():
                self.htmlText.Navigate(htmlPath.s,0x2) #--0x2: Clear History
                self.SetDocType('html')
            else:
                self.plainText.LoadFile(docPath.s)
                self.SetDocType('txt')

    #--Set Doc Type
    def SetDocType(self,docType):
        """Shows the plainText or htmlText view depending on document type (i.e. file name extension)."""
        if docType == self.docType:
            return
        sizer = self.mainSizer
        if docType == 'html':
            sizer.Show(self.plainText,False)
            sizer.Show(self.htmlText,True)
            self.prevButton.Enable(True)
            self.nextButton.Enable(True)
        else:
            sizer.Show(self.plainText,True)
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
        self.Destroy()

#------------------------------------------------------------------------------
class ModChecker(wx.Frame):
    """Mod Checker frame."""
    def __init__(self):
        """Intialize."""
        import wx.lib.iewin
        #--Singleton
        global modChecker
        modChecker = self
        #--Window
        pos = settings.get('bash.modChecker.pos',balt.defPos)
        size = settings.get('bash.modChecker.size',(400,440))
        wx.Frame.__init__(self, bashFrame, -1, _('Mod Checker'), pos, size,
            style=wx.DEFAULT_FRAME_STYLE)
        self.SetBackgroundColour(wx.NullColour)
        self.SetSizeHints(250,250)
        self.SetIcons(bashBlue)
        #--Data
        self.ordered = None
        self.merged = None
        self.imported = None
        #--Text
        self.gTextCtrl = wx.lib.iewin.IEHtmlWindow(self, -1, style = wx.NO_FULL_REPAINT_ON_RESIZE)
        #--Buttons
        bitmap = wx.ArtProvider_GetBitmap(wx.ART_GO_BACK,wx.ART_HELP_BROWSER, (16,16))
        gBackButton = bitmapButton(self,bitmap,onClick=lambda evt: self.gTextCtrl.GoBack())
        bitmap = wx.ArtProvider_GetBitmap(wx.ART_GO_FORWARD,wx.ART_HELP_BROWSER, (16,16))
        gForwardButton = bitmapButton(self,bitmap,onClick=lambda evt: self.gTextCtrl.GoForward())
        gUpdateButton = button(self,_('Update'),onClick=lambda event: self.CheckMods())
        self.gShowModList = toggleButton(self,_("Mod List"),onClick=self.CheckMods)
        self.gShowRuleSets = toggleButton(self,_("Rule Sets"),onClick=self.CheckMods)
        self.gShowNotes = toggleButton(self,_("Notes"),onClick=self.CheckMods)
        self.gShowConfig = toggleButton(self,_("Configuration"),onClick=self.CheckMods)
        self.gShowSuggest = toggleButton(self,_("Suggestions"),onClick=self.CheckMods)
        self.gCopyText = button(self,_("Copy Text"),onClick=self.OnCopyText)
        self.gShowModList.SetValue(settings.get('bash.modChecker.showModList',False))
        self.gShowNotes.SetValue(settings.get('bash.modChecker.showNotes',True))
        self.gShowConfig.SetValue(settings.get('bash.modChecker.showConfig',True))
        self.gShowSuggest.SetValue(settings.get('bash.modChecker.showSuggest',True))
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
                    (self.gCopyText,0,wx.LEFT,4),
                    spacer,
                    gUpdateButton,
                    ),0,wx.ALL|wx.EXPAND,4),
                )
            )
        self.CheckMods()

    def OnCopyText(self,event=None):
        """Copies text of report to clipboard."""
        text = '[spoiler]'+self.text+'[/spoiler]'
        text = re.sub(r'\[\[.+?\|\s*(.+?)\]\]',r'\1',text)
        text = re.sub('(__|\*\*|~~)','',text)
        text = re.sub('&bull; &bull;','**',text)
        text = re.sub('<[^>]+>','',text)
        if (wx.TheClipboard.Open()):
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()

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
        #--Cache info from modinfs to support auto-update.
        self.ordered = bosh.modInfos.ordered
        self.merged = bosh.modInfos.merged.copy()
        self.imported = bosh.modInfos.imported.copy()
        #--Do it
        self.text = bosh.configHelpers.checkMods(
            self.gShowModList.GetValue(),
            self.gShowRuleSets.GetValue(),
            settings['bash.modChecker.showNotes'],
            settings['bash.modChecker.showConfig'],
            settings['bash.modChecker.showSuggest']
            )
        logPath = bosh.dirs['saveBase'].join('ModChecker.html')
        cssDir = settings.get('balt.WryeLog.cssDir', GPath(''))
        ins = stringBuffer(self.text+'\n{{CSS:wtxt_sand_small.css}}')
        out = logPath.open('w')
        bolt.WryeText.genHtml(ins,out,cssDir)
        out.close()
        self.gTextCtrl.Navigate(logPath.s,0x2) #--0x2: Clear History

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
    #--Version from readme
    readme = bosh.dirs['mopy'].join('Wrye Bash.txt')
    if readme.exists() and readme.mtime != settings['bash.readme'][0]:
        reVersion = re.compile("^=== ([\.\d]+) \[")
        for line in readme.open():
            maVersion = reVersion.match(line)
            if maVersion:
                return (readme.mtime,maVersion.group(1))
    return settings['bash.readme'] #readme file not found or not changed

#------------------------------------------------------------------------------
class BashApp(wx.App):
    """Bash Application class."""
    def Init(self): # not OnInit(), we need to initialize _after_ the app has been instanced
        global appRestart
        appRestart = False
        """wxWindows: Initialization handler."""
        #--Constants
        self.InitResources()
        #--Init Data
        progress = wx.ProgressDialog("Wrye Bash",_("Initializing Data")+' '*10,
            style=wx.PD_AUTO_HIDE | wx.PD_APP_MODAL | (sys.version[:3] != '2.4' and wx.PD_SMOOTH))
        self.InitData(progress)
        progress.Update(70,_("Initializing Version"))
        self.InitVersion()
        #--MWFrame
        progress.Update(80,_("Initializing Windows"))
        frame = BashFrame(
             pos=settings['bash.framePos'],
             size=settings['bash.frameSize'])
        progress.Destroy()
        self.SetTopWindow(frame)
        frame.Show()
        balt.ensureDisplayed(frame)
        #--DocBrowser
        if settings['bash.modDocs.show']:
            #DocBrowser().Show()
            pass #--Better to not refresh doc browser, I think.
        #balt.ensureDisplayed(docBrowser)

    def InitResources(self):
        """Init application resources."""
        global bashBlue, bashRed, bashDocBrowser, bashMonkey
        bashBlue = bashBlue.GetIconBundle()
        bashRed = bashRed.GetIconBundle()
        bashDocBrowser = bashDocBrowser.GetIconBundle()
        bashMonkey = bashMonkey.GetIconBundle()

    def InitData(self,progress):
        """Initialize all data. Called by OnInit()."""
        progress.Update(5,_("Initializing ModInfos"))
        bosh.configHelpers = bosh.ConfigHelpers()
        bosh.configHelpers.refresh()
        bosh.oblivionIni = bosh.OblivionIni()
        bosh.modInfos = bosh.ModInfos()
        bosh.modInfos.refresh(doAutoGroup=True)
        progress.Update(30,_("Initializing SaveInfos"))
        bosh.saveInfos = bosh.SaveInfos()
        bosh.saveInfos.refresh()
        progress.Update(40,_("Initializing IniInfos"))
        bosh.iniInfos = bosh.INIInfos()
        bosh.iniInfos.refresh()
        #progress.Update(55,_("Initializing BSAInfos"))
        #bosh.BSAInfos = bosh.BSAInfos()
        #bosh.BSAInfos.refresh()
        #--Patch check
        firstBashed = settings.get('bash.patch.firstBashed',False)
        if not firstBashed:
            for modInfo in bosh.modInfos.values():
                if modInfo.header.author == 'BASHED PATCH': break
            else:
                progress.Update(68,_("Generating Blank Bashed Patch"))
                patchInfo = bosh.ModInfo(bosh.modInfos.dir,GPath('Bashed Patch, 0.esp'))
                patchInfo.mtime = max([time.time()]+[info.mtime for info in bosh.modInfos.values()])
                patchFile = bosh.ModFile(patchInfo)
                patchFile.tes4.author = 'BASHED PATCH'
                patchFile.safeSave()
                bosh.modInfos.refresh()
            settings['bash.patch.firstBashed'] = True

    def InitVersion(self):
        """Perform any version to version conversion. Called by OnInit()."""
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
        if settings['bash.readme'] != GetBashVersion():
            settings['bash.readme'] = GetBashVersion()
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
            self.data = dict(('%08X %s' % (key,face.pcName),face) for key,face in faces.items())
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
        self.nameCheck = checkBox(self,_('Name'))
        self.raceCheck = checkBox(self,_('Race'))
        self.genderCheck = checkBox(self,_('Gender'))
        self.statsCheck = checkBox(self,_('Stats'))
        self.classCheck = checkBox(self,_('Class'))
        flags = bosh.PCFaces.flags(settings.get('bash.faceImport.flags',0x4))
        self.nameCheck.SetValue(flags.name)
        self.raceCheck.SetValue(flags.race)
        self.genderCheck.SetValue(flags.gender)
        self.statsCheck.SetValue(flags.stats)
        self.classCheck.SetValue(flags.iclass)
        #--Name,Race,Gender Text
        self.nameText  = staticText(self,'-----------------------------')
        self.raceText  = staticText(self,'')
        self.genderText  = staticText(self,'')
        self.statsText  = staticText(self,'')
        self.classText  = staticText(self,'')
        #--Other
        importButton = button(self,_('Import'),onClick=self.DoImport)
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
        self.statsText.SetLabel(_('Health ')+`face.health`)
        itemImagePath = bosh.dirs['mods'].join(r'Docs/Images/%s.jpg' % (item,))
        bitmap = (itemImagePath.exists() and
            wx.Bitmap(itemImagePath.s,wx.BITMAP_TYPE_JPEG)) or None
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
        balt.showOk(self,_('Face imported.'),self.fileInfo.name.s)
        self.EndModal(wx.ID_OK)

    #--Window Closing
    def OnCloseWindow(self, event):
        """Handle window close event.
        Remember window size, position, etc."""
        balt.sizes['ImportFaceDialog'] = self.GetSizeTuple()
        self.Destroy()

# Patchers 00 ------------------------------------------------------------------
#------------------------------------------------------------------------------
class PatchDialog(wx.Dialog):
    """Bash Patch update dialog."""
    patchers = [] #--All patchers. These are copied as needed.

    def __init__(self,parent,patchInfo):
        """Initialized."""
        self.parent = parent
        size = balt.sizes.get(self.__class__.__name__,(400,400))
        wx.Dialog.__init__(self,parent,-1,_("Update ")+patchInfo.name.s, size=size,
            style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.SetSizeHints(400,300)
        #--Data
        groupOrder = dict([(group,index) for index,group in
            enumerate((_('General'),_('Importers'),_('Tweakers'),_('Special')))])
        patchConfigs = bosh.modInfos.table.getItem(patchInfo.name,'bash.patch.configs',{})
        self.patchInfo = patchInfo
        self.patchers = [copy.deepcopy(patcher) for patcher in PatchDialog.patchers]
        self.patchers.sort(key=lambda a: a.__class__.name)
        self.patchers.sort(key=lambda a: groupOrder[a.__class__.group])
        for patcher in self.patchers:
            patcher.getConfig(patchConfigs) #--Will set patcher.isEnabled
            if 'UNDEFINED' in (patcher.__class__.group, patcher.__class__.group):
                raise UncodedError('Name or group not defined for: '+patcher.__class__.__name__)
        self.currentPatcher = None
        patcherNames = [patcher.getName() for patcher in self.patchers]
        #--GUI elements
        self.gExecute = button(self,id=wx.ID_OK,label=_('Build Patch'),onClick=self.Execute)
        self.gRevertConfig = button(self,id=wx.ID_REVERT_TO_SAVED,label=_('Revert To Saved'),onClick=self.RevertConfig)
        self.gSelectAll = button(self,id=wx.wx.ID_SELECTALL,label=_('Select All'),onClick=self.SelectAll)
        self.gDeselectAll = button(self,id=wx.wx.ID_SELECTALL,label=_('Deselect All'),onClick=self.DeselectAll)
        self.gExportConfig = button(self,id=wx.ID_SAVEAS,label=_('Export Patch Configuration'),onClick=self.ExportConfig)
        self.gImportConfig = button(self,id=wx.ID_OPEN,label=_('Import Patch Configuration'),onClick=self.ImportConfig)
        self.gPatchers = wx.CheckListBox(self,-1,choices=patcherNames,style=wx.LB_SINGLE)
        for index,patcher in enumerate(self.patchers):
            self.gPatchers.Check(index,patcher.isEnabled)
        self.gTipText = staticText(self,'')
        #--Events
        self.Bind(wx.EVT_SIZE,self.OnSize)
        self.gPatchers.Bind(wx.EVT_LISTBOX, self.OnSelect)
        self.gPatchers.Bind(wx.EVT_CHECKLISTBOX, self.OnCheck)
        self.gPatchers.Bind(wx.EVT_MOTION,self.OnMouse)
        self.gPatchers.Bind(wx.EVT_LEAVE_WINDOW,self.OnMouse)
        self.gPatchers.Bind(wx.EVT_CHAR,self.OnChar)
        self.mouseItem = -1
        #--Layout
        self.gConfigSizer = gConfigSizer = vSizer()
        sizer = vSizer(
            (hSizer(
                (self.gPatchers,0,wx.EXPAND),
                (self.gConfigSizer,1,wx.EXPAND|wx.LEFT,4),
                ),1,wx.EXPAND|wx.ALL,4),
            (self.gTipText,0,wx.EXPAND|wx.ALL^wx.TOP,4),
            (wx.StaticLine(self),0,wx.EXPAND|wx.BOTTOM,4),
            (hSizer(
                spacer,
                (self.gRevertConfig,0,wx.LEFT,4),
                (self.gExportConfig,0,wx.LEFT,4),
                (self.gImportConfig,0,wx.LEFT,4),
                ),0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,4),
            (hSizer(
                spacer,
                self.gExecute,
                (self.gSelectAll,0,wx.LEFT,4),
                (self.gDeselectAll,0,wx.LEFT,4),
                (button(self,id=wx.ID_CANCEL,label=_('Cancel')),0,wx.LEFT,4),
                ),0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,4)
            )
        self.SetSizer(sizer)
        self.SetIcons(bashMonkey)
        #--Patcher panels
        for patcher in self.patchers:
            gConfigPanel = patcher.GetConfigPanel(self,gConfigSizer,self.gTipText)
            gConfigSizer.Show(gConfigPanel,False)
        self.ShowPatcher(self.patchers[0])
        self.SetOkEnable()

    #--Core -------------------------------
    def SetOkEnable(self):
        """Sets enable state for Ok button."""
        for patcher in self.patchers:
            if patcher.isEnabled:
                return self.gExecute.Enable(True)
        self.gExecute.Enable(False)

    def ShowPatcher(self,patcher):
        """Show patcher panel."""
        gConfigSizer = self.gConfigSizer
        if patcher == self.currentPatcher: return
        if self.currentPatcher != None:
            gConfigSizer.Show(self.currentPatcher.gConfigPanel,False)
        gConfigPanel = patcher.GetConfigPanel(self,gConfigSizer,self.gTipText)
        gConfigSizer.Show(gConfigPanel,True)
        self.Layout()
        patcher.Layout()
        self.currentPatcher = patcher

    def Execute(self,event=None):
        """Do the patch."""
        self.EndModal(wx.ID_OK)
        patchName = self.patchInfo.name
        progress = balt.Progress(patchName.s,(' '*60+'\n'), abort=True)
        ###Remove from Bash after CBash integrated
        if not CBash:
            try:
                from datetime import timedelta
                timer1 = time.clock()
                #--Save configs
                patchConfigs = {'ImportedMods':set()}
                for patcher in self.patchers:
                    patcher.saveConfig(patchConfigs)
                bosh.modInfos.table.setItem(patchName,'bash.patch.configs',patchConfigs)
                #--Do it
                log = bolt.LogFile(stringBuffer())
                nullProgress = bolt.Progress()
                patchers = [patcher for patcher in self.patchers if patcher.isEnabled]
                patchFile = bosh.PatchFile(self.patchInfo,patchers)
                patchFile.initData(SubProgress(progress,0,0.1)) #try to speed this up!
                patchFile.initFactories(SubProgress(progress,0.1,0.2)) #no speeding needed/really possible (less than 1/4 second even with large LO)
                patchFile.scanLoadMods(SubProgress(progress,0.2,0.8)) #try to speed this up!
                patchFile.buildPatch(log,SubProgress(progress,0.8,0.9))#no speeding needed/really possible (less than 1/4 second even with large LO)
                #--Save
                progress.setCancel(False)
                progress(0.9,patchName.s+_('\nSaving...'))
                try:
                    patchFile.safeSave()
                except WindowsError, werr:
                    if werr.winerror != 32: raise
                    while balt.askYes(self,_('Bash encountered an error when saving %s.\n\nThe file is in use by another process such as TES4Edit.\nPlease close the other program that is accessing %s.\n\nTry again?') % (patchName.s,patchName.s),_('Bash Patch - Save Error')):
                        try:
                            patchFile.safeSave()
                        except WindowsError, werr:
                            continue
                        break
                    else:
                        raise

                #--Cleanup
                self.patchInfo.refresh()
                modList.RefreshUI(patchName)
                #--Done
                progress.Destroy()
                timer2 = time.clock()
                #--Readme and log
                log.setHeader(None)
                log('{{CSS:wtxt_sand_small.css}}')
                logValue = log.out.getvalue()
                timerString = str(timedelta(seconds=round(timer2 - timer1, 3))).rstrip('0')
                logValue = re.sub('TIMEPLACEHOLDER', timerString, logValue, 1)
                readme = bosh.modInfos.dir.join('Docs',patchName.sroot+'.txt')
                readme.open('w').write(logValue)
                bosh.modInfos.table.setItem(patchName,'doc',readme)
                #--Convert log/readme to wtxt and show log
                docsDir = bosh.modInfos.dir.join('Docs')
                bolt.WryeText.genHtml(readme,None,docsDir)
                balt.showWryeLog(self.parent,readme.root+'.html',patchName.s,icons=bashBlue)
                #--Select?
                message = _("Activate %s?") % (patchName.s,)
                if bosh.modInfos.isSelected(patchName) or balt.askYes(self.parent,message,patchName.s):
                    try:
                        oldFiles = bosh.modInfos.ordered[:]
                        bosh.modInfos.select(patchName)
                        changedFiles = bolt.listSubtract(bosh.modInfos.ordered,oldFiles)
                        if len(changedFiles) > 1:
                            statusBar.SetText(_("Masters Activated: ") + `len(changedFiles)-1`)
                    except bosh.PluginsFullError:
                        balt.showError(self,_("Unable to add mod %s because load list is full." )
                            % (fileName.s,))
                    modList.RefreshUI()
            except bosh.FileEditError, error:
                progress.Destroy()
                balt.showError(self,str(error),_("File Edit Error"))
            except CancelError:
                pass
            finally:
                progress.Destroy()
        else:
            try:
                from datetime import timedelta
                timer1 = time.clock()
                fullName = self.patchInfo.getPath().tail
                #--Save configs
                patchConfigs = {'ImportedMods':set()}
                for patcher in self.patchers:
                    patcher.saveConfig(patchConfigs)
                bosh.modInfos.table.setItem(patchName,'bash.patch.configs',patchConfigs)
                #--Do it
                log = bolt.LogFile(stringBuffer())
                patchers = [patcher for patcher in self.patchers if patcher.isEnabled]

                patchFile = bosh.CBash_PatchFile(patchName,patchers)
                patchFile.initData(SubProgress(progress,0,0.1)) #try to speed this up!
                patchFile.buildPatch(SubProgress(progress,0.1,0.9)) #try to speed this up!
                patchFile.buildPatchLog(patchName,log,SubProgress(progress,0.95,0.99))#no speeding needed/really possible (less than 1/4 second even with large LO)
                #--Save
                #patchFile.CleanMasters()
                progress.setCancel(False)
                progress(1.0,patchName.s+_('\nSaving...'))
                patchFile.save()
                patchTime = fullName.mtime
                try:
                    patchName.untemp()
                except WindowsError, werr:
                    if werr.winerror != 32: raise
                    while balt.askYes(self,_('Bash encountered an error when renaming %s to %s.\n\nThe file is in use by another process such as TES4Edit.\nPlease close the other program that is accessing %s.\n\nTry again?') % (patchName.temp.s, patchName.s, patchName.s),_('Bash Patch - Save Error')):
                        try:
                            patchName.untemp()
                        except WindowsError, werr:
                            continue
                        break
                    else:
                        raise
                patchName.mtime = patchTime
                #--Cleanup
                self.patchInfo.refresh()
                modList.RefreshUI(patchName)
                #--Done
                progress.Destroy()
                timer2 = time.clock()
                #--Readme and log
                log.setHeader(None)
                log('{{CSS:wtxt_sand_small.css}}')
                logValue = log.out.getvalue()
                timerString = str(timedelta(seconds=round(timer2 - timer1, 3))).rstrip('0')
                logValue = re.sub('TIMEPLACEHOLDER', timerString, logValue, 1)
                readme = bosh.modInfos.dir.join('Docs',patchName.sroot+'.txt')
                readme.open('w').write(logValue)
                bosh.modInfos.table.setItem(patchName,'doc',readme)
                #--Convert log/readme to wtxt and show log
                docsDir = bosh.modInfos.dir.join('Docs')
                bolt.WryeText.genHtml(readme,None,docsDir)
                balt.showWryeLog(self.parent,readme.root+'.html',patchName.s,icons=bashBlue)
                #--Select?
                message = _("Activate %s?") % (patchName.s,)
                if bosh.modInfos.isSelected(patchName) or balt.askYes(self.parent,message,patchName.s):
                    try:
                        oldFiles = bosh.modInfos.ordered[:]
                        bosh.modInfos.select(patchName)
                        changedFiles = bolt.listSubtract(bosh.modInfos.ordered,oldFiles)
                        if len(changedFiles) > 1:
                            statusBar.SetText(_("Masters Activated: ") + `len(changedFiles)-1`)
                    except bosh.PluginsFullError:
                        balt.showError(self,_("Unable to add mod %s because load list is full." )
                            % (fileName.s,))
                    modList.RefreshUI()
                del patchFile
            except bosh.FileEditError, error:
                progress.Destroy()
                balt.showError(self,str(error),_("File Edit Error"))
            except CancelError:
                del patchFile
            finally:
                progress.Destroy()

    def SaveConfig(self,event=None):
        """Save the configuration"""
        patchName = self.patchInfo.name
        patchConfigs = {'ImportedMods':set()}
        for patcher in self.patchers:
            patcher.saveConfig(patchConfigs)
        bosh.modInfos.table.setItem(patchName,'bash.patch.configs',patchConfigs)

    def ExportConfig(self,event=None):
        """Export the configuration to a user selected dat file."""
        patchName = self.patchInfo.name + _('_Configuration.dat')
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.parent,_('Export Bashed Patch configuration to:'),textDir,patchName, '*Configuration.dat')
        if not textPath: return
        pklPath = textPath+'.pkl'
        table = bolt.Table(bosh.PickleDict(textPath, pklPath))
        patchConfigs = {'ImportedMods':set()}
        for patcher in self.patchers:
            patcher.saveConfig(patchConfigs)
        table.setItem(bolt.Path('Saved Bashed Patch Configuration'),'bash.patch.configs',patchConfigs)
        table.save()

    def ImportConfig(self,event=None):
        """Import the configuration to a user selected dat file."""
        patchName = self.patchInfo.name + _('_Configuration.dat')
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askOpen(self.parent,_('Import Bashed Patch configuration from:'),textDir,patchName, '*.dat',mustExist=True)
        if not textPath: return
        pklPath = textPath+'.pkl'
        table = bolt.Table(bosh.PickleDict(
            textPath, pklPath))
        patchConfigs = table.getItem(bolt.Path('Saved Bashed Patch Configuration'),'bash.patch.configs',{})
        for index,patcher in enumerate(self.patchers):
            patcher.getConfig(patchConfigs)
            self.gPatchers.Check(index,patcher.isEnabled)
            if isinstance(patcher, ListPatcher):
                if patcher.getName() == 'Leveled Lists': continue #not handled yet!
                for index, item in enumerate(patcher.items):
                    try:
                        patcher.gList.Check(index,patcher.configChecks[item])
                    except KeyError: deprint(_('item %s not in saved configs') % (item))
            elif isinstance(patcher, TweakPatcher):
                for index, item in enumerate(patcher.tweaks):
                    try:
                        patcher.gList.Check(index,item.isEnabled)
                    except: deprint(_('item %s not in saved configs') % (item))
        self.SetOkEnable()

    def RevertConfig(self,event=None):
        """Revert configuration back to saved"""
        patchConfigs = bosh.modInfos.table.getItem(self.patchInfo.name,'bash.patch.configs',{})
        for index,patcher in enumerate(self.patchers):
            patcher.getConfig(patchConfigs)
            self.gPatchers.Check(index,patcher.isEnabled)
            if isinstance(patcher, ListPatcher):
                if patcher.getName() == 'Leveled Lists': continue #not handled yet!
                for index, item in enumerate(patcher.items):
                    patcher.gList.Check(index,patcher.configChecks[item])
            elif isinstance(patcher, TweakPatcher):
                for index, item in enumerate(patcher.tweaks):
                    patcher.gList.Check(index,item.isEnabled)
        self.SetOkEnable()

    def SelectAll(self,event=None):
        """Select all patchers and entries in patchers with child entries."""
        for index,patcher in enumerate(self.patchers):
            self.gPatchers.Check(index,True)
            patcher.isEnabled = True
            if isinstance(patcher, ListPatcher):
                if patcher.getName() == 'Leveled Lists': continue
                for index, item in enumerate(patcher.items):
                    patcher.gList.Check(index,True)
                    patcher.configChecks[item] = True
            elif isinstance(patcher, TweakPatcher):
                for index, item in enumerate(patcher.tweaks):
                    patcher.gList.Check(index,True)
                    item.isEnabled = True
            self.gExecute.Enable(True)

    def DeselectAll(self,event=None):
        """Deselect all patchers and entries in patchers with child entries."""
        for index,patcher in enumerate(self.patchers):
            self.gPatchers.Check(index,False)
            patcher.isEnabled = False
            if not hasattr(patcher, 'gList'): continue
            if patcher.getName() == 'Leveled Lists': continue # special case that one.
            patcher.gList.SetChecked([])
            patcher.OnListCheck()
        self.gExecute.Enable(False)

    #--GUI --------------------------------
    def OnSize(self,event):
        balt.sizes[self.__class__.__name__] = self.GetSizeTuple()
        self.Layout()
        self.currentPatcher.Layout()

    def OnSelect(self,event):
        """Responds to patchers list selection."""
        itemDex = event.GetSelection()
        self.ShowPatcher(self.patchers[itemDex])

    def OnCheck(self,event):
        """Toggle patcher activity state."""
        index = event.GetSelection()
        patcher = self.patchers[index]
        patcher.isEnabled = self.gPatchers.IsChecked(index)
        self.gPatchers.SetSelection(index)
        self.ShowPatcher(patcher)
        self.SetOkEnable()

    def OnMouse(self,event):
        """Check mouse motion to detect right click event."""
        if event.Moving():
            mouseItem = (event.m_y/self.gPatchers.GetItemHeight() +
                self.gPatchers.GetScrollPos(wx.VERTICAL))
            if mouseItem != self.mouseItem:
                self.mouseItem = mouseItem
                self.MouseEnteredItem(mouseItem)
        elif event.Leaving():
            self.gTipText.SetLabel('')
            self.mouseItem = -1
        event.Skip()

    def MouseEnteredItem(self,item):
        """Show tip text when changing item."""
        #--Following isn't displaying correctly.
        if item < len(self.patchers):
            patcherClass = self.patchers[item].__class__
            tip = patcherClass.tip or re.sub(r'\..*','.',patcherClass.text.split('\n')[0])
            self.gTipText.SetLabel(tip)
        else:
            self.gTipText.SetLabel('')

    def OnChar(self,event):
        """Keyboard input to the patchers list box"""
        if event.GetKeyCode() == 1 and event.ControlDown(): # Ctrl+'A'
            patcher = self.currentPatcher
            if patcher is not None:
                if event.ShiftDown():
                    patcher.DeselectAll()
                else:
                    patcher.SelectAll()
                return
        event.Skip()

#------------------------------------------------------------------------------
class Patcher:
    """Basic patcher panel with no options."""
    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if not self.gConfigPanel:
            self.gTipText = gTipText
            gConfigPanel = self.gConfigPanel = wx.Window(parent,-1)
            text = fill(self.text,70)
            gText = staticText(self.gConfigPanel,text)
            gSizer = vSizer(gText)
            gConfigPanel.SetSizer(gSizer)
            gConfigSizer.Add(gConfigPanel,1,wx.EXPAND)
        return self.gConfigPanel

    def Layout(self):
        """Layout control components."""
        if self.gConfigPanel:
            self.gConfigPanel.Layout()

    def SelectAll(self,event=None):
        """'Select All' Button was pressed, update all configChecks states."""
        if hasattr(self, 'items'): items = self.items
        elif hasattr(self, 'tweaks'): items = self.tweaks
        else: return
        try:
            for index, item in enumerate(items):
                self.gList.Check(index,True)
            self.OnListCheck()
        except AttributeError:
            pass #ListBox instead of CheckListBox
        self.gConfigPanel.GetParent().gPatchers.SetFocusFromKbd()

    def DeselectAll(self,event=None):
        """'Deselect All' Button was pressed, update all configChecks states."""
        if hasattr(self, 'gList'):
            try:
                self.gList.SetChecked([])
                self.OnListCheck()
            except AttributeError:
                pass #ListBox instead of CheckListBox
            self.gConfigPanel.GetParent().gPatchers.SetFocusFromKbd()
#------------------------------------------------------------------------------
class AliasesPatcher(Patcher,bosh.AliasesPatcher):
    """Basic patcher panel with no options."""
    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        #--Else...
        #--Tip
        self.gTipText = gTipText
        gConfigPanel = self.gConfigPanel = wx.Window(parent,-1)
        text = fill(self.__class__.text,70)
        gText = staticText(gConfigPanel,text)
        #gExample = staticText(gConfigPanel,
        #    _("Example Mod 1.esp >> Example Mod 1.2.esp"))
        #--Aliases Text
        self.gAliases = wx.TextCtrl(gConfigPanel,-1,'',style=wx.TE_MULTILINE)
        self.gAliases.Bind(wx.EVT_KILL_FOCUS, self.OnEditAliases)
        self.SetAliasText()
        #--Sizing
        gSizer = vSizer(
            gText,
            #(gExample,0,wx.EXPAND|wx.TOP,8),
            (self.gAliases,1,wx.EXPAND|wx.TOP,4))
        gConfigPanel.SetSizer(gSizer)
        gConfigSizer.Add(gConfigPanel,1,wx.EXPAND)
        return self.gConfigPanel

    def SetAliasText(self):
        """Sets alias text according to current aliases."""
        self.gAliases.SetValue('\n'.join([
            '%s >> %s' % (key.s,value.s) for key,value in sorted(self.aliases.items())]))

    def OnEditAliases(self,event):
        text = self.gAliases.GetValue()
        self.aliases.clear()
        for line in text.split('\n'):
            fields = map(string.strip,line.split('>>'))
            if len(fields) != 2 or not fields[0] or not fields[1]: continue
            self.aliases[GPath(fields[0])] = GPath(fields[1])
        self.SetAliasText()

class CBash_AliasesPatcher(Patcher,bosh.CBash_AliasesPatcher):
    """Basic patcher panel with no options."""
    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        #--Else...
        #--Tip
        self.gTipText = gTipText
        gConfigPanel = self.gConfigPanel = wx.Window(parent,-1)
        text = fill(self.text,70)
        gText = staticText(gConfigPanel,text)
        #gExample = staticText(gConfigPanel,
        #    _("Example Mod 1.esp >> Example Mod 1.2.esp"))
        #--Aliases Text
        self.gAliases = wx.TextCtrl(gConfigPanel,-1,'',style=wx.TE_MULTILINE)
        self.gAliases.Bind(wx.EVT_KILL_FOCUS, self.OnEditAliases)
        self.SetAliasText()
        #--Sizing
        gSizer = vSizer(
            gText,
            #(gExample,0,wx.EXPAND|wx.TOP,8),
            (self.gAliases,1,wx.EXPAND|wx.TOP,4))
        gConfigPanel.SetSizer(gSizer)
        gConfigSizer.Add(gConfigPanel,1,wx.EXPAND)
        return self.gConfigPanel

    def SetAliasText(self):
        """Sets alias text according to current aliases."""
        self.gAliases.SetValue('\n'.join([
            '%s >> %s' % (key.s,value.s) for key,value in sorted(self.aliases.items())]))

    def OnEditAliases(self,event):
        text = self.gAliases.GetValue()
        self.aliases.clear()
        for line in text.split('\n'):
            fields = map(string.strip,line.split('>>'))
            if len(fields) != 2 or not fields[0] or not fields[1]: continue
            self.aliases[GPath(fields[0])] = GPath(fields[1])
        self.SetAliasText()
#------------------------------------------------------------------------------
class ListPatcher(Patcher):
    """Patcher panel with option to select source elements."""
    listLabel = _("Source Mods/Files")

    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        #--Else...
        self.forceItemCheck = self.__class__.forceItemCheck
        self.selectCommands = self.__class__.selectCommands
        self.gTipText = gTipText
        gConfigPanel = self.gConfigPanel = wx.Window(parent,-1)
        text = fill(self.text,70)
        gText = staticText(self.gConfigPanel,text)
        if self.forceItemCheck:
            self.gList = wx.ListBox(gConfigPanel,-1)
        else:
            self.gList =wx.CheckListBox(gConfigPanel,-1)
            self.gList.Bind(wx.EVT_CHECKLISTBOX,self.OnListCheck)
        #--Events
        self.gList.Bind(wx.EVT_MOTION,self.OnMouse)
        self.gList.Bind(wx.EVT_RIGHT_DOWN,self.OnMouse)
        self.gList.Bind(wx.EVT_RIGHT_UP,self.OnMouse)
        self.mouseItem = -1
        self.mouseState = None
        #--Manual controls
        if self.forceAuto:
            gManualSizer = None
            self.SetItems(self.getAutoItems())
        else:
            self.gAuto = checkBox(gConfigPanel,_("Automatic"),onCheck=self.OnAutomatic)
            self.gAuto.SetValue(self.autoIsChecked)
            self.gAdd = button(gConfigPanel,_("Add"),onClick=self.OnAdd)
            self.gRemove = button(gConfigPanel,_("Remove"),onClick=self.OnRemove)
            self.OnAutomatic()
            gManualSizer = (vSizer(
                (self.gAuto,0,wx.TOP,2),
                (self.gAdd,0,wx.TOP,12),
                (self.gRemove,0,wx.TOP,4),
                ),0,wx.EXPAND|wx.LEFT,4)
        if self.selectCommands:
            self.gSelectAll= button(gConfigPanel,_("Select All"),onClick=self.SelectAll)
            self.gDeselectAll = button(gConfigPanel,_("Deselect All"),onClick=self.DeselectAll)
            gSelectSizer = (vSizer(
                (self.gSelectAll,0,wx.TOP,12),
                (self.gDeselectAll,0,wx.TOP,4),
                ),0,wx.EXPAND|wx.LEFT,4)
        else: gSelectSizer = None
        #--Init GUI
        self.SetItems(self.configItems)
        #--Layout
        gSizer = vSizer(
            (gText,),
            (hsbSizer((gConfigPanel,-1,self.__class__.listLabel),
                ((4,0),0,wx.EXPAND),
                (self.gList,1,wx.EXPAND|wx.TOP,2),
                gManualSizer,gSelectSizer,
                ),1,wx.EXPAND|wx.TOP,4),
            )
        gConfigPanel.SetSizer(gSizer)
        gConfigSizer.Add(gConfigPanel,1,wx.EXPAND)
        return gConfigPanel

    def SetItems(self,items):
        """Set item to specified set of items."""
        items = self.items = self.sortConfig(items)
        forceItemCheck = self.forceItemCheck
        defaultItemCheck = self.__class__.defaultItemCheck
        self.gList.Clear()
        for index,item in enumerate(items):
            self.gList.Insert(self.getItemLabel(item),index)
            if forceItemCheck:
                self.configChecks[item] = True
            else:
                self.gList.Check(index,self.configChecks.setdefault(item,defaultItemCheck))
        self.configItems = items

    def OnListCheck(self,event=None):
        """One of list items was checked. Update all configChecks states."""
        for index,item in enumerate(self.items):
            self.configChecks[item] = self.gList.IsChecked(index)

    def OnAutomatic(self,event=None):
        """Automatic checkbox changed."""
        self.autoIsChecked = self.gAuto.IsChecked()
        self.gAdd.Enable(not self.autoIsChecked)
        self.gRemove.Enable(not self.autoIsChecked)
        if self.autoIsChecked:
            self.SetItems(self.getAutoItems())

    def OnAdd(self,event):
        """Add button clicked."""
        srcDir = bosh.modInfos.dir
        wildcard = _('Oblivion Mod Files')+' (*.esp;*.esm)|*.esp;*.esm'
        #--File dialog
        title = _("Get ")+self.__class__.listLabel
        srcPaths = balt.askOpenMulti(self.gConfigPanel,title,srcDir, '', wildcard)
        if not srcPaths: return
        #--Get new items
        for srcPath in srcPaths:
            dir,name = srcPath.headTail
            if dir == srcDir and name not in self.configItems:
                self.configItems.append(name)
        self.SetItems(self.configItems)

    def OnRemove(self,event):
        """Remove button clicked."""
        selected = self.gList.GetSelections()
        newItems = [item for index,item in enumerate(self.configItems) if index not in selected]
        self.SetItems(newItems)

    #--Choice stuff ---------------------------------------
    def OnMouse(self,event):
        """Check mouse motion to detect right click event."""
        if event.RightDown():
            self.mouseState = (event.m_x,event.m_y)
            event.Skip()
        elif event.RightUp() and self.mouseState:
            self.ShowChoiceMenu(event)
        elif event.Dragging():
            if self.mouseState:
                oldx,oldy = self.mouseState
                if max(abs(event.m_x-oldx),abs(event.m_y-oldy)) > 4:
                    self.mouseState = None
        else:
            self.mouseState = False
            event.Skip()

    def ShowChoiceMenu(self,event):
        """Displays a popup choice menu if applicable.
        NOTE: Assume that configChoice returns a set of chosen items."""
        if not self.choiceMenu: return
        #--Item Index
        if self.forceItemCheck:
            itemHeight = self.gList.GetCharHeight()
        else:
            itemHeight = self.gList.GetItemHeight()
        itemIndex = event.m_y/itemHeight + self.gList.GetScrollPos(wx.VERTICAL)
        if itemIndex >= len(self.items): return
        self.gList.SetSelection(itemIndex)
        self.rightClickItemIndex = itemIndex
        choiceSet = self.getChoice(self.items[itemIndex])
        #--Build Menu
        menu = wx.Menu()
        for index,label in enumerate(self.choiceMenu):
            if label == '----':
                menu.AppendSeparator()
            else:
                menuItem = wx.MenuItem(menu,index,label,kind=wx.ITEM_CHECK)
                menu.AppendItem(menuItem)
                if label in choiceSet: menuItem.Check()
                wx.EVT_MENU(self.gList,index,self.OnItemChoice)
        #--Show/Destroy Menu
        self.gList.PopupMenu(menu)
        menu.Destroy()

    def OnItemChoice(self,event):
        """Handle choice menu selection."""
        itemIndex = self.rightClickItemIndex
        item =self.items[itemIndex]
        choice = self.choiceMenu[event.GetId()]
        choiceSet = self.configChoices[item]
        choiceSet ^= set((choice,))
        if choice != 'Auto':
            choiceSet.discard('Auto')
        elif 'Auto' in self.configChoices[item]:
            self.getChoice(item)
        self.gList.SetString(itemIndex,self.getItemLabel(item))

#------------------------------------------------------------------------------
class TweakPatcher(Patcher):
    """Patcher panel with list of checkable, configurable tweaks."""
    listLabel = _("Tweaks")

    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        #--Else...
        self.gTipText = gTipText
        gConfigPanel = self.gConfigPanel = wx.Window(parent,-1)
        text = fill(self.__class__.text,70)
        gText = staticText(self.gConfigPanel,text)
        self.gList = wx.CheckListBox(gConfigPanel,-1)
        #--Events
        self.gList.Bind(wx.EVT_CHECKLISTBOX,self.OnListCheck)
        self.gList.Bind(wx.EVT_MOTION,self.OnMouse)
        self.gList.Bind(wx.EVT_LEAVE_WINDOW,self.OnMouse)
        self.gList.Bind(wx.EVT_RIGHT_DOWN,self.OnMouse)
        self.gList.Bind(wx.EVT_RIGHT_UP,self.OnMouse)
        self.mouseItem = -1
        self.mouseState = None
        if self.selectCommands:
            self.gSelectAll= button(gConfigPanel,_("Select All"),onClick=self.SelectAll)
            self.gDeselectAll = button(gConfigPanel,_("Deselect All"),onClick=self.DeselectAll)
            gSelectSizer = (vSizer(
                (self.gSelectAll,0,wx.TOP,12),
                (self.gDeselectAll,0,wx.TOP,4),
                ),0,wx.EXPAND|wx.LEFT,4)
        else: gSelectSizer = None
        #--Init GUI
        self.SetItems()
        #--Layout
        gSizer = vSizer(
            (gText,),
            (hsbSizer((gConfigPanel,-1,self.__class__.listLabel),
                ((4,0),0,wx.EXPAND),
                (self.gList,1,wx.EXPAND|wx.TOP,2),
                gSelectSizer,
                ),1,wx.EXPAND|wx.TOP,4),
            )
        gConfigPanel.SetSizer(gSizer)
        gConfigSizer.Add(gConfigPanel,1,wx.EXPAND)
        return gConfigPanel

    def SetItems(self):
        """Set item to specified set of items."""
        self.gList.Clear()
        for index,tweak in enumerate(self.tweaks):
            label = tweak.getListLabel()
            if tweak.choiceLabels and tweak.choiceLabels[tweak.chosen].startswith('Custom'):
                label += ' %4.2f ' % tweak.choiceValues[tweak.chosen][0]
            self.gList.Insert(label,index)
            self.gList.Check(index,tweak.isEnabled)

    def OnListCheck(self,event=None):
        """One of list items was checked. Update all check states."""
        for index, tweak in enumerate(self.tweaks):
            tweak.isEnabled = self.gList.IsChecked(index)

    def OnMouse(self,event):
        """Check mouse motion to detect right click event."""
        if event.RightDown():
            self.mouseState = (event.m_x,event.m_y)
            event.Skip()
        elif event.RightUp() and self.mouseState:
            self.ShowChoiceMenu(event)
        elif event.Leaving():
            self.gTipText.SetLabel('')
            self.mouseState = False
            event.Skip()
        elif event.Dragging():
            if self.mouseState:
                oldx,oldy = self.mouseState
                if max(abs(event.m_x-oldx),abs(event.m_y-oldy)) > 4:
                    self.mouseState = None
        elif event.Moving():
            mouseItem = event.m_y/self.gList.GetItemHeight() + self.gList.GetScrollPos(wx.VERTICAL)
            self.mouseState = False
            if mouseItem != self.mouseItem:
                self.mouseItem = mouseItem
                self.MouseEnteredItem(mouseItem)
            event.Skip()
        else:
            self.mouseState = False
            event.Skip()

    def MouseEnteredItem(self,item):
        """Show tip text when changing item."""
        #--Following isn't displaying correctly.
        tip = item < len(self.tweaks) and self.tweaks[item].tip
        if tip:
            self.gTipText.SetLabel(tip)
        else:
            self.gTipText.SetLabel('')

    def ShowChoiceMenu(self,event):
        """Displays a popup choice menu if applicable."""
        #--Tweak Index
        tweakIndex = event.m_y/self.gList.GetItemHeight() + self.gList.GetScrollPos(wx.VERTICAL)
        self.rightClickTweakIndex = tweakIndex
        #--Tweaks
        tweaks = self.tweaks
        if tweakIndex >= len(tweaks): return
        choiceLabels = tweaks[tweakIndex].choiceLabels
        if len(choiceLabels) <= 1: return
        chosen = tweaks[tweakIndex].chosen
        self.gList.SetSelection(tweakIndex)
        #--Build Menu
        menu = wx.Menu()
        for index,label in enumerate(choiceLabels):
            if label == '----':
                menu.AppendSeparator()
            elif label.startswith(_('Custom')):
                menulabel = label + ' %4.2f ' % tweaks[tweakIndex].choiceValues[index][0]
                menuItem = wx.MenuItem(menu,index,menulabel,kind=wx.ITEM_CHECK)
                menu.AppendItem(menuItem)
                if index == chosen: menuItem.Check()
                wx.EVT_MENU(self.gList,index,self.OnTweakCustomChoice)
            else:
                menuItem = wx.MenuItem(menu,index,label,kind=wx.ITEM_CHECK)
                menu.AppendItem(menuItem)
                if index == chosen: menuItem.Check()
                wx.EVT_MENU(self.gList,index,self.OnTweakChoice)
        #--Show/Destroy Menu
        self.gList.PopupMenu(menu)
        menu.Destroy()

    def OnTweakChoice(self,event):
        """Handle choice menu selection."""
        tweakIndex = self.rightClickTweakIndex
        self.tweaks[tweakIndex].chosen = event.GetId()
        self.gList.SetString(tweakIndex,self.tweaks[tweakIndex].getListLabel())

    def OnTweakCustomChoice(self,event):
        """Handle choice menu selection."""
        tweakIndex = self.rightClickTweakIndex
        index = event.GetId()
        tweak = self.tweaks[tweakIndex]
        tweak.chosen = index
        if tweak.float: label = _('Enter the desired custom tweak value.\nDue to an inability to get decimal numbers from the wxPython prompt please enter an extra zero after your choice if it is not meant to be a decimal.\nIf you are trying to enter a decimal multiply it by 10, for example for 0.3 enter 3 instead.')
        else: label = _('Enter the desired custom tweak value.')
        value = balt.askNumber(self.gConfigPanel,label,prompt=_('Value'),title=_('Custom Tweak Value'),value=self.tweaks[tweakIndex].choiceValues[index][0],min=-10000,max=10000)
        if not value: value = self.tweaks[tweakIndex].choiceValues[index][0]
        if tweak.float: value = float(value) / 10
        self.tweaks[tweakIndex].choiceValues[index] = (value,)
        self.gList.SetString(tweakIndex,(self.tweaks[tweakIndex].getListLabel()+' %4.2f ' % (value)))

# Patchers 10 ------------------------------------------------------------------
class PatchMerger(bosh.PatchMerger,ListPatcher):
    listLabel = _("Mergeable Mods")
class CBash_PatchMerger(bosh.CBash_PatchMerger,ListPatcher):
    listLabel = _("Mergeable Mods")
# Patchers 20 ------------------------------------------------------------------
class GraphicsPatcher(bosh.GraphicsPatcher,ListPatcher): pass
class CBash_GraphicsPatcher(bosh.CBash_GraphicsPatcher,ListPatcher): pass

class ActorAnimPatcher(bosh.KFFZPatcher,ListPatcher): pass
class CBash_ActorAnimPatcher(bosh.CBash_KFFZPatcher,ListPatcher): pass

class NPCAIPackagePatcher(bosh.NPCAIPackagePatcher,ListPatcher): pass
class CBash_NPCAIPackagePatcher(bosh.CBash_NPCAIPackagePatcher,ListPatcher): pass

class ActorImporter(bosh.ActorImporter,ListPatcher): pass
class CBash_ActorImporter(bosh.CBash_ActorImporter,ListPatcher): pass

class DeathItemPatcher(bosh.DeathItemPatcher,ListPatcher): pass
class CBash_DeathItemPatcher(bosh.CBash_DeathItemPatcher,ListPatcher): pass

class CellImporter(bosh.CellImporter,ListPatcher): pass
class CBash_CellImporter(bosh.CBash_CellImporter,ListPatcher): pass

class ImportFactions(bosh.ImportFactions,ListPatcher): pass
class CBash_ImportFactions(bosh.CBash_ImportFactions,ListPatcher): pass

class ImportRelations(bosh.ImportRelations,ListPatcher): pass
class CBash_ImportRelations(bosh.CBash_ImportRelations,ListPatcher): pass

class ImportInventory(bosh.ImportInventory,ListPatcher): pass
class CBash_ImportInventory(bosh.CBash_ImportInventory,ListPatcher): pass

class ImportActorsSpells(bosh.ImportActorsSpells,ListPatcher): pass
class CBash_ImportActorsSpells(bosh.CBash_ImportActorsSpells,ListPatcher): pass

class NamesPatcher(bosh.NamesPatcher,ListPatcher): pass
class CBash_NamesPatcher(bosh.CBash_NamesPatcher,ListPatcher): pass

class NpcFacePatcher(bosh.NpcFacePatcher,ListPatcher): pass
class CBash_NpcFacePatcher(bosh.CBash_NpcFacePatcher,ListPatcher): pass

class RacePatcher(bosh.RacePatcher,ListPatcher):
    listLabel = _("Race Mods")
class CBash_RacePatcher(bosh.CBash_RacePatcher,ListPatcher):
    listLabel = _("Race Mods")

class RoadImporter(bosh.RoadImporter,ListPatcher): pass
class CBash_RoadImporter(bosh.CBash_RoadImporter,ListPatcher): pass

class SoundPatcher(bosh.SoundPatcher,ListPatcher): pass
class CBash_SoundPatcher(bosh.CBash_SoundPatcher,ListPatcher): pass

class StatsPatcher(bosh.StatsPatcher,ListPatcher): pass
class CBash_StatsPatcher(bosh.CBash_StatsPatcher,ListPatcher): pass

class ImportScripts(bosh.ImportScripts,ListPatcher):pass
class CBash_ImportScripts(bosh.CBash_ImportScripts,ListPatcher):pass

class ImportScriptContents(bosh.ImportScriptContents,ListPatcher):pass
##class CBash_ImportScriptContents(bosh.CBash_ImportScriptContents,ListPatcher):pass

class ImportSpells(bosh.SpellsPatcher,ListPatcher):pass
class CBash_ImportSpells(bosh.CBash_SpellsPatcher,ListPatcher):pass

# Patchers 30 ------------------------------------------------------------------
class AssortedTweaker(bosh.AssortedTweaker,TweakPatcher): pass
class CBash_AssortedTweaker(bosh.CBash_AssortedTweaker,TweakPatcher): pass

class ClothesTweaker(bosh.ClothesTweaker,TweakPatcher): pass
class CBash_ClothesTweaker(bosh.CBash_ClothesTweaker,TweakPatcher): pass

class GlobalsTweaker(bosh.GlobalsTweaker,TweakPatcher): pass
class CBash_GlobalsTweaker(bosh.CBash_GlobalsTweaker,TweakPatcher): pass

class GmstTweaker(bosh.GmstTweaker,TweakPatcher): pass
class CBash_GmstTweaker(bosh.CBash_GmstTweaker,TweakPatcher): pass

class NamesTweaker(bosh.NamesTweaker,TweakPatcher): pass
class CBash_NamesTweaker(bosh.CBash_NamesTweaker,TweakPatcher): pass

class TweakActors(bosh.TweakActors,TweakPatcher): pass
class CBash_TweakActors(bosh.CBash_TweakActors,TweakPatcher): pass

# Patchers 40 ------------------------------------------------------------------
class AlchemicalCatalogs(bosh.AlchemicalCatalogs,Patcher): pass
class CBash_AlchemicalCatalogs(bosh.CBash_AlchemicalCatalogs,Patcher): pass

class CoblExhaustion(bosh.CoblExhaustion,ListPatcher): pass
class CBash_CoblExhaustion(bosh.CBash_CoblExhaustion,ListPatcher): pass

class UpdateReferences(bosh.UpdateReferences,ListPatcher): pass
class CBash_UpdateReferences(bosh.CBash_UpdateReferences,ListPatcher): pass

class ListsMerger(bosh.ListsMerger,ListPatcher):
    listLabel = _("Override Delev/Relev Tags")
class CBash_ListsMerger(bosh.CBash_ListsMerger,ListPatcher):
    listLabel = _("Override Delev/Relev Tags")

class MFactMarker(bosh.MFactMarker,ListPatcher): pass
class CBash_MFactMarker(bosh.CBash_MFactMarker,ListPatcher): pass

class PowerExhaustion(bosh.PowerExhaustion,Patcher): pass
class CBash_PowerExhaustion(bosh.CBash_PowerExhaustion,Patcher): pass

class SEWorldEnforcer(bosh.SEWorldEnforcer,Patcher): pass
class CBash_SEWorldEnforcer(bosh.CBash_SEWorldEnforcer,Patcher): pass

class ContentsChecker(bosh.ContentsChecker,Patcher): pass
class CBash_ContentsChecker(bosh.CBash_ContentsChecker,Patcher): pass

##class ForceMerger(bosh.ForceMerger,Patcher): pass
##class CBash_ForceMerger(bosh.CBash_ForceMerger,ListPatcher): pass

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# Init Patchers
if not CBash:
    PatchDialog.patchers.extend((
        AliasesPatcher(),
        AssortedTweaker(),
        PatchMerger(),
        AlchemicalCatalogs(),
        ActorAnimPatcher(),
        ActorImporter(),
        DeathItemPatcher(),
        NPCAIPackagePatcher(),
        CoblExhaustion(),
        UpdateReferences(),
        CellImporter(),
        ClothesTweaker(),
        GlobalsTweaker(),
        GmstTweaker(),
        GraphicsPatcher(),
        ImportFactions(),
        ImportInventory(),
        ImportSpells(),
        TweakActors(),
        ImportRelations(),
        ImportScripts(),
        ImportScriptContents(),
        ImportActorsSpells(),
        ListsMerger(),
        MFactMarker(),
        NamesPatcher(),
        NamesTweaker(),
        NpcFacePatcher(),
        PowerExhaustion(),
        RacePatcher(),
        RoadImporter(),
        SoundPatcher(),
        StatsPatcher(),
        SEWorldEnforcer(),
        ContentsChecker(),
        ))
else:
    PatchDialog.patchers.extend((
        CBash_AliasesPatcher(),
        CBash_AssortedTweaker(),
        CBash_PatchMerger(),
        CBash_AlchemicalCatalogs(),
        CBash_ActorAnimPatcher(),
        CBash_ActorImporter(),
        CBash_DeathItemPatcher(),
        CBash_NPCAIPackagePatcher(),
        CBash_CoblExhaustion(),
        CBash_UpdateReferences(),
        CBash_CellImporter(),
        CBash_ClothesTweaker(),
        CBash_GlobalsTweaker(),
        CBash_GmstTweaker(),
        CBash_GraphicsPatcher(),
        CBash_ImportFactions(),
        CBash_ImportInventory(),
        CBash_ImportSpells(),
        CBash_TweakActors(),
        CBash_ImportRelations(),
        CBash_ImportScripts(),
##        CBash_ImportScriptContents(),
        CBash_ImportActorsSpells(),
        CBash_ListsMerger(),
        CBash_MFactMarker(),
        CBash_NamesPatcher(),
        CBash_NamesTweaker(),
        CBash_NpcFacePatcher(),
        CBash_PowerExhaustion(),
        CBash_RacePatcher(),
        CBash_RoadImporter(),
        CBash_SoundPatcher(),
        CBash_StatsPatcher(),
        CBash_SEWorldEnforcer(),
        CBash_ContentsChecker(),
##        CBash_ForceMerger(),
        ))
# Files Links -----------------------------------------------------------------
#------------------------------------------------------------------------------
class BoolLink(Link):
    """Simple link that just toggles a setting."""
    def __init__(self, text, key, help=''):
        Link.__init__(self)
        self.text = text
        self.help = help
        self.key = key

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,self.text,self.help,kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        menuItem.Check(settings[self.key])

    def Execute(self,event):
        settings[self.key] ^= True


#------------------------------------------------------------------------------
class Files_Open(Link):
    """Opens data directory in explorer."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Open...'), _("Open '%s'") % (window.data.dir.tail))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        """Handle selection."""
        dir = self.window.data.dir
        dir.makedirs()
        dir.start()

#------------------------------------------------------------------------------
class Files_SortBy(Link):
    """Sort files by specified key (sortCol)."""
    def __init__(self,sortCol,prefix=''):
        Link.__init__(self)
        self.sortCol = sortCol
        self.sortName = settings['bash.colNames'][sortCol]
        self.prefix = prefix

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,self.prefix+self.sortName,_('Sort by %s') % (self.sortName),kind=wx.ITEM_RADIO)
        menu.AppendItem(menuItem)
        if window.sort == self.sortCol: menuItem.Check()

    def Execute(self,event):
        if hasattr(self, 'gTank'):
            self.gTank.SortItems(self.sortCol,'INVERT')
        else:
            self.window.PopulateItems(self.sortCol,-1)

#------------------------------------------------------------------------------
class Files_Unhide(Link):
    """Unhide file(s). (Move files back to Data Files or Save directory.)"""
    def __init__(self,type):
        Link.__init__(self)
        self.type = type

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_("Unhide..."), _("Unhides hidden %ss.") % self.type)
        menu.AppendItem(menuItem)

    def Execute(self,event):
        srcDir = bosh.dirs['modsBash'].join('Hidden')
        if self.type == 'mod':
            wildcard = 'Oblivion Mod Files (*.esp;*.esm)|*.esp;*.esm'
            destDir = self.window.data.dir
        elif self.type == 'save':
            wildcard = 'Oblivion Save files (*.ess)|*.ess'
            srcDir = self.window.data.bashDir.join('Hidden')
            destDir = self.window.data.dir
        elif self.type == 'installer':
            window = self.gTank
            wildcard = 'Oblivion Mod Archives (*.7z;*.zip;*.rar)|*.7z;*.zip;*.rar'
            destDir = bosh.dirs['installers']
            srcPaths = balt.askOpenMulti(window,_('Unhide files:'),srcDir, '.Folder Selection.', wildcard)
        else:
            wildcard = '*.*'
        isSave = (destDir == bosh.saveInfos.dir)
        #--File dialog
        srcDir.makedirs()
        if not self.type == 'installer':
            window = self.window
            srcPaths = balt.askOpenMulti(window,_('Unhide files:'),srcDir, '', wildcard)
        if not srcPaths: return
        #--Iterate over Paths
        for srcPath in srcPaths:
            #--Copy from dest directory?
            (newSrcDir,srcFileName) = srcPath.headTail
            if newSrcDir == destDir:
                balt.showError(window,_("You can't unhide files from this directory."))
                return
            #--Folder selection?
            if srcFileName.csbody == '.folder selection':
                if newSrcDir == srcDir:
                    #--Folder selection on the 'Hidden' folder
                    return
                (newSrcDir,srcFileName) = newSrcDir.headTail
                srcPath = srcPath.head
            #--File already unhidden?
            destPath = destDir.join(srcFileName)
            if destPath.exists():
                balt.showWarning(window,_("File skipped: %s. File is already present.")
                    % (srcFileName.s,))
            #--Move it?
            else:
                srcPath.moveTo(destPath)
                if isSave:
                    bosh.CoSaves(srcPath).move(destPath)
        #--Repopulate
        bashFrame.RefreshData()

# File Links ------------------------------------------------------------------
#------------------------------------------------------------------------------
class File_Delete(Link):
    """Delete the file and all backups."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menu.AppendItem(wx.MenuItem(menu,self.id,_('Delete')))

    def Execute(self,event):
        message = _(r'Delete these files? This operation cannot be undone.')
        message += '\n* ' + '\n* '.join(sorted(x.s for x in self.data))
        if not balt.askYes(self.window,message,_('Delete Files')):
            return
        #--Do it
        for fileName in self.data:
            self.window.data.delete(fileName)
        #--Refresh stuff
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class File_Duplicate(Link):
    """Create a duplicate of the file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.title = (_('Duplicate'),_('Duplicate...'))[len(data) == 1]
        menuItem = wx.MenuItem(menu,self.id,self.title, _("Make a copy of '%s'") % (data[0]))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        data = self.data
        for item in data:
            fileName = GPath(item)
            fileInfos = self.window.data
            fileInfo = fileInfos[fileName]
            #--Mod with resources?
            #--Warn on rename if file has bsa and/or dialog
            if fileInfo.isMod() and tuple(fileInfo.hasResources()) != (False,False):
                hasBsa, hasVoices = fileInfo.hasResources()
                modName = fileInfo.name
                if hasBsa and hasVoices:
                    message = _("This mod has an associated archive (%s.bsa) and an associated voice directory (Sound\\Voices\\%s), which will not be attached to the duplicate mod.\n\nNote that the BSA archive may also contain a voice directory (Sound\\Voices\\%s), which would remain detached even if a duplicate archive were also created.") % (modName.sroot,modName.s,modName.s)
                elif hasBsa:
                    message = _("This mod has an associated archive (%s.bsa), which will not be attached to the duplicate mod.\n\nNote that this BSA archive may contain a voice directory (Sound\\Voices\\%s), which would remain detached even if a duplicate archive were also created.") % (modName.sroot,modName.s)
                else: #hasVoices
                    message = _("This mod has an associated voice directory (Sound\\Voice\\%s), which will not be attached to the duplicate mod.") % (modName.s,)
                if not balt.askWarning(self.window,message,_("Duplicate ")+fileName.s):
                    continue
            #--Continue copy
            (root,ext) = fileName.rootExt
            if ext.lower() == '.bak': ext = '.ess'
            (destDir,wildcard) = (fileInfo.dir, '*'+ext)
            destName = GPath(root+' Copy'+ext)
            destPath = GPath(destDir).join(destName)
            count = 0
            while destPath.exists() and count < 1000:
                count += 1
                destName = GPath(root + ' Copy %d'  % (count,) + ext)
                destPath = GPath(destDir).join(destName)
            destName = destName.s
            destDir.makedirs()
            if len(data) == 1:
                destPath = balt.askSave(self.window,_('Duplicate as:'), destDir,destName,wildcard)
                if not destPath: return
                destDir,destName = destPath.headTail
            if (destDir == fileInfo.dir) and (destName == fileName):
                balt.showError(self.window,_("Files cannot be duplicated to themselves!"))
                continue
            if(fileInfo.isMod()):
                newTime = bosh.modInfos.getFreeTime(fileInfo.getPath().mtime)
            else:
                newTime = '+1'
            fileInfos.copy(fileName,destDir,destName,mtime=newTime)
            if destDir == fileInfo.dir:
                fileInfos.table.copyRow(fileName,destName)
                if fileInfos.table.getItem(fileName,'mtime'):
                    destInfo = fileInfos[destName]
                    fileInfos.table.setItem(destName,'mtime',destInfo.mtime)
                if fileInfo.isMod():
                    fileInfos.autoSort()
            self.window.RefreshUI()

#------------------------------------------------------------------------------
class File_Hide(Link):
    """Hide the file. (Move it to Bash/Hidden directory.)"""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menu.AppendItem(wx.MenuItem(menu,self.id,_('Hide')))

    def Execute(self,event):
        if not bosh.inisettings['SkipHideConfirmation']:
            message = _(r'Hide these files? Note that hidden files are simply moved to the Bash\Hidden subdirectory.')
            if not balt.askYes(self.window,message,_('Hide Files')): return
        #--Do it
        destRoot = self.window.data.bashDir.join('Hidden')
        fileInfos = self.window.data
        fileGroups = fileInfos.table.getColumn('group')
        for fileName in self.data:
            destDir = destRoot
            #--Use author subdirectory instead?
            author = getattr(fileInfos[fileName].header,'author','NOAUTHOR') #--Hack for save files.
            authorDir = destRoot.join(author)
            if author and authorDir.isdir():
                destDir = authorDir
            #--Use group subdirectory instead?
            elif fileName in fileGroups:
                groupDir = destRoot.join(fileGroups[fileName])
                if groupDir.isdir():
                    destDir = groupDir
            if not self.window.data.moveIsSafe(fileName,destDir):
                message = (_('A file named %s already exists in the hidden files directory. Overwrite it?')
                    % (fileName.s,))
                if not balt.askYes(self.window,message,_('Hide Files')): continue
            #--Do it
            self.window.data.move(fileName,destDir,False)
        #--Refresh stuff
        bashFrame.RefreshData()

#------------------------------------------------------------------------------
class File_ListMasters(Link):
    """Copies list of masters to clipboard."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_("List Masters..."))
        menu.AppendItem(menuItem)
        if len(data) != 1: menuItem.Enable(False)

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        text = bosh.modInfos.getModList(fileInfo)
        if (wx.TheClipboard.Open()):
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        balt.showLog(self.window,text,fileName.s,asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class File_Redate(Link):
    """Move the selected files to start at a specified date."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Redate...'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        #--Get current start time.
        modInfos = self.window.data
        fileNames = [mod for mod in self.data if mod not in modInfos.autoSorted]
        if not fileNames: return
        #--Ask user for revised time.
        newTimeStr = balt.askText(self.window,_('Redate selected mods starting at...'),
            _('Redate Mods'),formatDate(int(time.time())))
        if not newTimeStr: return
        try:
            newTimeTup = bosh.unformatDate(newTimeStr,'%c')
            newTime = int(time.mktime(newTimeTup))
        except ValueError:
            balt.showError(self.window,_('Unrecognized date: ')+newTimeStr)
            return
        except OverflowError:
            balt.showError(self,_('Bash cannot handle dates greater than January 19, 2038.)'))
            return
        #--Do it
        selInfos = [modInfos[fileName] for fileName in fileNames]
        selInfos.sort(key=attrgetter('mtime'))
        for fileInfo in selInfos:
            fileInfo.setmtime(newTime)
            newTime += 60
        #--Refresh
        modInfos.refresh(doInfos=False)
        modInfos.refreshInfoLists()
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class File_Sort(Link):
    """Sort the selected files."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Sort'))
        menu.AppendItem(menuItem)
        if len(data) < 2: menuItem.Enable(False)

    def Execute(self,event):
        message = _("Reorder selected mods in alphabetical order? The first file will be given the date/time of the current earliest file in the group, with consecutive files following at 1 minute increments.\n\nNote that this operation cannot be undone. Note also that some mods need to be in a specific order to work correctly, and this sort operation may break that order.")
        if not balt.askContinue(self.window,message,'bash.sortMods.continue',_('Sort Mods')):
            return
        #--Get first time from first selected file.
        modInfos = self.window.data
        fileNames = [mod for mod in self.data if mod not in modInfos.autoSorted]
        if not fileNames: return
        dotTimes = [modInfos[fileName].mtime for fileName in fileNames if fileName.s[0] in '.=+']
        if dotTimes:
            newTime = min(dotTimes)
        else:
            newTime = min(modInfos[fileName].mtime for fileName in self.data)
        #--Do it
        fileNames.sort(key=lambda a: a.s[:-4].lower())
        fileNames.sort(key=lambda a: a.s[0] not in '.=')
        for fileName in fileNames:
            modInfos[fileName].setmtime(newTime)
            newTime += 60
        #--Refresh
        modInfos.refresh(doInfos=False)
        modInfos.refreshInfoLists()
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class File_Snapshot(Link):
    """Take a snapshot of the file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.title = (_('Snapshot'),_('Snapshot...'))[len(data) == 1]
        menuItem = wx.MenuItem(menu,self.id,self.title)
        menu.AppendItem(menuItem)

    def Execute(self,event):
        data = self.data
        for item in data:
            fileName = GPath(item)
            fileInfo = self.window.data[fileName]
            (destDir,destName,wildcard) = fileInfo.getNextSnapshot()
            destDir.makedirs()
            if len(data) == 1:
                destPath = balt.askSave(self.window,_('Save snapshot as:'),
                    destDir,destName,wildcard)
                if not destPath: return
                (destDir,destName) = destPath.headTail
            #--Extract version number
            fileRoot = fileName.root
            destRoot = destName.root
            fileVersion = bolt.getMatch(re.search(r'[ _]+v?([\.0-9]+)$',fileRoot.s),1)
            snapVersion = bolt.getMatch(re.search(r'-[0-9\.]+$',destRoot.s))
            fileHedr = fileInfo.header
            if fileInfo.isMod() and (fileVersion or snapVersion) and bosh.reVersion.search(fileHedr.description):
                if fileVersion and snapVersion:
                    newVersion = fileVersion+snapVersion
                elif snapVersion:
                    newVersion = snapVersion[1:]
                else:
                    newVersion = fileVersion
                newDescription = bosh.reVersion.sub(r'\1 '+newVersion, fileHedr.description,1)
                fileInfo.writeDescription(newDescription)
                self.window.details.SetFile(fileName)
            #--Copy file
            self.window.data.copy(fileName,destDir,destName)

#------------------------------------------------------------------------------
class File_RevertToSnapshot(Link):
    """Revert to Snapshot."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Revert to Snapshot...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data) == 1)

    def Execute(self,event):
        """Handle menu item selection."""
        fileInfo = self.window.data[self.data[0]]
        fileName = fileInfo.name
        #--Snapshot finder
        destDir = self.window.data.dir
        srcDir = self.window.data.bashDir.join('Snapshots')
        wildcard = fileInfo.getNextSnapshot()[2]
        #--File dialog
        srcDir.makedirs()
        snapPath = balt.askOpen(self.window,_('Revert %s to snapshot:') % (fileName.s,),
            srcDir, '', wildcard,mustExist=True)
        if not snapPath: return
        snapName = snapPath.tail
        #--Warning box
        message = (_("Revert %s to snapshot %s dated %s?")
            % (fileInfo.name.s, snapName.s, formatDate(snapPath.mtime)))
        if not balt.askYes(self.window,message,_('Revert to Snapshot')): return
        wx.BeginBusyCursor()
        destPath = fileInfo.getPath()
        snapPath.copyTo(destPath)
        fileInfo.setmtime()
        try:
            self.window.data.refreshFile(fileName)
        except bosh.FileError:
            balt.showError(self,_('Snapshot file is corrupt!'))
            self.window.details.SetFile(None)
        wx.EndBusyCursor()
        self.window.RefreshUI(fileName)

#------------------------------------------------------------------------------
class File_Backup(Link):
    """Backup file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Backup'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        for item in self.data:
            fileInfo = self.window.data[item]
            fileInfo.makeBackup(True)

#------------------------------------------------------------------------------
class File_RevertToBackup:
    """Revert to last or first backup."""
    def AppendToMenu(self,menu,window,data):
        self.window = window
        self.data = data
        #--Backup Files
        singleSelect = len(data) == 1
        self.fileInfo = window.data[data[0]]
        #--Backup Item
        wx.EVT_MENU(window,ID_REVERT_BACKUP,self.Execute)
        menuItem = wx.MenuItem(menu,ID_REVERT_BACKUP,_('Revert to Backup'))
        menu.AppendItem(menuItem)
        self.backup = self.fileInfo.bashDir.join('Backups',self.fileInfo.name)
        menuItem.Enable(singleSelect and self.backup.exists())
        #--First Backup item
        wx.EVT_MENU(window,ID_REVERT_FIRST,self.Execute)
        menuItem = wx.MenuItem(menu,ID_REVERT_FIRST,_('Revert to First Backup'))
        menu.AppendItem(menuItem)
        self.firstBackup = self.backup +'f'
        menuItem.Enable(singleSelect and self.firstBackup.exists())

    def Execute(self,event):
        fileInfo = self.fileInfo
        fileName = fileInfo.name
        #--Backup/FirstBackup?
        if event.GetId() ==  ID_REVERT_BACKUP:
            backup = self.backup
        else:
            backup = self.firstBackup
        #--Warning box
        message = _("Revert %s to backup dated %s?") % (fileName.s,
            formatDate(backup.mtime))
        if balt.askYes(self.window,message,_('Revert to Backup')):
            wx.BeginBusyCursor()
            dest = fileInfo.dir.join(fileName)
            backup.copyTo(dest)
            fileInfo.setmtime()
            if fileInfo.isEss(): #--Handle CoSave (.pluggy and .obse) files.
                bosh.CoSaves(backup).copy(dest)
            try:
                self.window.data.refreshFile(fileName)
            except bosh.FileError:
                balt.showError(self,_('Old file is corrupt!'))
            wx.EndBusyCursor()
        self.window.RefreshUI(fileName)

#------------------------------------------------------------------------------
class File_Open(Link):
    """Open specified file(s)."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        if len(data) == 1:
            help = _("Open '%s' with the system's default program.") % data[0]
        else:
            help = _('Open the selected files.')
        menuItem = wx.MenuItem(menu,self.id,_('Open...'),help)
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)>0)

    def Execute(self,event):
        """Handle selection."""
        dir = self.window.data.dir
        for file in self.data:
            dir.join(file).start()
#------------------------------------------------------------------------------
class List_Column(Link):
    def __init__(self,columnsKey,colName,enable=True):
        Link.__init__(self)
        self.colName = colName
        self.columnsKey = columnsKey
        self.enable = enable

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        colName = settings['bash.colNames'][self.colName]
        check = self.colName in settings[self.columnsKey]
        help = _("Show/Hide '%s' column.") % colName
        menuItem = wx.MenuItem(menu,self.id,colName,help,kind=wx.ITEM_CHECK)
        menuItem.Enable(self.enable)
        menu.AppendItem(menuItem)
        menuItem.Check(check)

    def Execute(self,event):
        if self.colName in settings[self.columnsKey]:
            settings[self.columnsKey].remove(self.colName)
            settings.setChanged(self.columnsKey)
        else:
            #--Ensure the same order each time
            settings[self.columnsKey] = [x for x in settingDefaults[self.columnsKey] if x in settings[self.columnsKey] or x == self.colName]
        self.window.PopulateColumns()
        self.window.RefreshUI()

#------------------------------------------------------------------------------

class List_Columns(Link):
    """Customize visible columns."""
    def __init__(self,columnsKey,persistantColumns=[]):
        Link.__init__(self)
        self.columnsKey = columnsKey
        self.persistant = persistantColumns

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        subMenu = wx.Menu()
        menu.AppendMenu(self.id,_("Columns"),subMenu)
        for col in settingDefaults[self.columnsKey]:
            enable = col not in self.persistant
            List_Column(self.columnsKey,col,enable).AppendToMenu(subMenu,window,data)

#------------------------------------------------------------------------------
class Installers_AddMarker(Link):
    """Add an installer marker."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Add Marker...'),_('Adds a Marker, a special type of package useful for seperating and labeling your packages.'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        """Handle selection."""
        index = self.gTank.GetIndex(GPath('===='))
        if index == -1:
            self.data.addMarker('====')
            self.data.refresh(what='OS')
            gInstallers.RefreshUIMods()
            index = self.gTank.GetIndex(GPath('===='))
        if index != -1:
            self.gTank.ClearSelected()
            self.gTank.gList.SetItemState(index,wx.LIST_STATE_SELECTED,wx.LIST_STATE_SELECTED)
            self.gTank.gList.EditLabel(index)
# Installers Links ------------------------------------------------------------
#------------------------------------------------------------------------------
class Installers_AnnealAll(Link):
    """Anneal all packages."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Anneal All'),_('This will install any missing files (for active installers) and correct all install order and reconfiguration errors.'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        """Handle selection."""
        progress = balt.Progress(_("Annealing..."),'\n'+' '*60)
        try:
            self.data.anneal(progress=progress)
        finally:
            progress.Destroy()
            self.data.refresh(what='NS')
            gInstallers.RefreshUIMods()
            bashFrame.RefreshData()

#------------------------------------------------------------------------------
class Installers_AutoAnneal(BoolLink):
    def __init__(self):
        BoolLink.__init__(self,
                          _('Auto-Anneal'),
                          'bash.installers.autoAnneal',
                          _("Enable/Disable automatic annealing of packages.")
                          )

#------------------------------------------------------------------------------
class Installers_AutoWizard(BoolLink):
    def __init__(self):
        BoolLink.__init__(self,
                          _('Auto-Anneal/Install Wizards'),
                          'bash.installers.autoWizard',
                          _("Enable/Disable automatic installing or anneal (as applicable) of packages after running its wizard.")
                          )

#------------------------------------------------------------------------------
class Installers_WizardOverlay(BoolLink):
    """Toggle using the wizard overlay icon"""
    def __init__(self):
        BoolLink.__init__(self,
                          _('Wizard Icon Overlay'),
                          'bash.installers.wizardOverlay',
                          _("Enable/Disable the magic wand icon overlay for packages with Wizards.")
                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        gInstallers.gList.RefreshUI()

#------------------------------------------------------------------------------
class Installers_AutoRefreshProjects(BoolLink):
    """Toggle autoRefreshProjects setting and update."""
    def __init__(self):
        BoolLink.__init__(self,
                          _('Auto-Refresh Projects'),
                          'bash.installers.autoRefreshProjects',
                          )

#------------------------------------------------------------------------------
class Installers_AutoRefreshBethsoft(BoolLink):
    """Toggle refreshVanilla setting and update."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Auto-Refresh Bethsoft Content'),
                                         'bash.installers.autoRefreshBethsoft',
                                         )

    def Execute(self,event):
        if not settings[self.key]:
            message = balt.fill(_("Enable refreshing Bethsoft Content?  This will cause data refreshing to take much longer if the timestamps on Bethsoft BSA's, ESP's, or ESM's change."))
            if not balt.askWarning(self.gTank,fill(message,80),self.title): return
        BoolLink.Execute(self,event)

#------------------------------------------------------------------------------
class Installers_Enabled(BoolLink):
    """Flips installer state."""
    def __init__(self): BoolLink.__init__(self,
                                         _('Enabled'),
                                         'bash.installers.enabled',
                                         _('Enable/Disable the Installers tab.')
                                         )

    def Execute(self,event):
        """Handle selection."""
        enabled = settings[self.key]
        message = _("Do you want to enable Installers? If you do, Bash will first need to initialize some data. If there are many new mods to process, then this may take on the order of five minutes.")
        if not enabled and not balt.askYes(self.gTank,fill(message,80),self.title):
            return
        enabled = settings[self.key] = not enabled
        if enabled:
            gInstallers.refreshed = False
            gInstallers.OnShow()
            gInstallers.gList.RefreshUI()
        else:
            gInstallers.gList.gList.DeleteAllItems()
            gInstallers.RefreshDetails(None)

#------------------------------------------------------------------------------
class Installers_BsaRedirection(BoolLink):
    """Toggle BSA Redirection."""
    def __init__(self):
        BoolLink.__init__(self,
                          _('BSA Redirection'),
                          'bash.bsaRedirection',
                          )

    def Execute(self,event):
        """Handle selection."""
        BoolLink.Execute(self,event)
        if settings[self.key]:
            bsaPath = bosh.modInfos.dir.join(bosh.inisettings['OblivionTexturesBSAName'])
            bsaFile = bosh.BsaFile(bsaPath)
            bsaFile.scan()
            resetCount = bsaFile.reset()
            #balt.showOk(self,_("BSA Hashes reset: %d") % (resetCount,))
        bosh.oblivionIni.setBsaRedirection(settings[self.key])

#------------------------------------------------------------------------------
class Installers_ConflictsReportShowsInactive(BoolLink):
    """Toggles option to show inactive on conflicts report."""
    def __init__(self):
        BoolLink.__init__(self,
                          _('Show Inactive Conflicts'),
                          'bash.installers.conflictsReport.showInactive',
                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class Installers_ConflictsReportShowsLower(BoolLink):
    """Toggles option to show lower on conflicts report."""
    def __init__(self):
        BoolLink.__init__(self,
                          _('Show Lower Conflicts'),
                          'bash.installers.conflictsReport.showLower',
                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class Installers_AvoidOnStart(BoolLink):
    """Ensures faster bash startup by preventing Installers from being startup tab."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Avoid at Startup'),
                                          'bash.installers.fastStart',
                                          _("Toggles Wrye Bash to avoid the Installers tab on startup, avoiding unnecessary data scanning.")
                                          )

#------------------------------------------------------------------------------
class Installers_Refresh(Link):
    """Refreshes all Installers data."""
    def __init__(self,fullRefresh=False):
        Link.__init__(self)
        self.fullRefresh = fullRefresh

    def AppendToMenu(self,menu,window,data):
        if not settings['bash.installers.enabled']: return
        Link.AppendToMenu(self,menu,window,data)
        self.title = (_('Refresh Data'),_('Full Refresh'))[self.fullRefresh]
        if self.fullRefresh:
            help = _("Perform a full refresh of all data files, recalculating all CRCs.  This can take 5-15 minutes.")
        else:
            help = _("Rescan the Data directory and all project directories.")
        menuItem = wx.MenuItem(menu,self.id,self.title,help)
        menu.AppendItem(menuItem)

    def Execute(self,event):
        """Handle selection."""
        if self.fullRefresh:
            message = balt.fill(_("Refresh ALL data from scratch? This may take five to ten minutes (or more) depending on the number of mods you have installed."))
            if not balt.askWarning(self.gTank,fill(message,80),self.title): return
        gInstallers.refreshed = False
        gInstallers.fullRefresh = self.fullRefresh
        gInstallers.OnShow()

#------------------------------------------------------------------------------
class Installers_RemoveEmptyDirs(BoolLink):
    """Toggles option to remove empty directories on file scan."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Clean Data Directory'),
                                          'bash.installers.removeEmptyDirs',
                                          )

#------------------------------------------------------------------------------
class Installers_ShowReplacers(BoolLink):
    """Toggles option to show replacers menu."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Show Replacers Tab'),
                                          'bash.replacers.show',
                                          _("Show/Hide the Replacers tab.")
                                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        message = _("This option will take effect when Bash is restarted. Note that if any files are present in Data\\Replacers, then the Replacers tab will be shown regardless of this setting.")
        balt.showOk(self.gTank,message,self.text)

#------------------------------------------------------------------------------
class Installers_Skip(BoolLink):
    """Toggle various skip settings and update."""
    def Execute(self,event):
        BoolLink.Execute(self,event)
        for installer in self.data.itervalues():
            installer.refreshDataSizeCrc()
        self.data.refresh(what='NS')
        self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class Installers_SkipScreenshots(Installers_Skip):
    """Toggle skipScreenshots setting and update."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Skip Screenshots'),
                                          'bash.installers.skipScreenshots',
                                          )

#------------------------------------------------------------------------------
class Installers_SkipImages(Installers_Skip):
    """Toggle skipImages setting and update."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Skip Images'),
                                          'bash.installers.skipImages',
                                          )

#------------------------------------------------------------------------------
class Installers_SkipDocs(Installers_Skip):
    """Toggle skipDocs setting and update."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Skip Docs'),
                                          'bash.installers.skipDocs',
                                          )

#------------------------------------------------------------------------------
class Installers_SkipDistantLOD(Installers_Skip):
    """Toggle skipDistantLOD setting and update."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Skip DistantLOD'),
                                          'bash.installers.skipDistantLOD',
                                          )

#------------------------------------------------------------------------------
class Installers_skipLandscapeLODMeshes(Installers_Skip):
    """Toggle skipLandscapeLODMeshes setting and update."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Skip LOD Meshes'),
                                          'bash.installers.skipLandscapeLODMeshes',
                                          )

#------------------------------------------------------------------------------
class Installers_skipLandscapeLODTextures(Installers_Skip):
    """Toggle skipDistantLOD setting and update."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Skip LOD Textures'),
                                          'bash.installers.skipLandscapeLODTextures',
                                          )

#------------------------------------------------------------------------------
class Installers_skipLandscapeLODNormals(Installers_Skip):
    """Toggle skipDistantLOD setting and update."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Skip LOD Normals'),
                                          'bash.installers.skipLandscapeLODNormals',
                                          )

#------------------------------------------------------------------------------
class Installers_SkipOBSEPlugins(Installers_Skip):
    """Toggle skipDistantLOD setting and update."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Skip OBSE Plugins'),
                                          'bash.installers.allowOBSEPlugins',
                                          )

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,self.text,self.help,kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        menuItem.Check(not settings[self.key])
        bosh.installersWindow = self.gTank

#------------------------------------------------------------------------------
class Installers_SortActive(BoolLink):
    """Sort by type."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Sort by Active'),
                                          'bash.installers.sortActive',
                                          _('If selected, active installers will be sorted to the top of the list.')
                                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        self.gTank.SortItems()

#------------------------------------------------------------------------------
class Installers_SortProjects(BoolLink):
    """Sort dirs to the top."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Projects First'),
                                          'bash.installers.sortProjects',
                                          _('If selected, projects will be sorted to the top of the list.')
                                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        self.gTank.SortItems()

#------------------------------------------------------------------------------
class Installers_SortStructure(BoolLink):
    """Sort by type."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Sort by Structure'),
                                          'bash.installers.sortStructure',
                                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        self.gTank.SortItems()

#------------------------------------------------------------------------------
class Installers_ExportDllInfo(Link):
    """Sort by type."""
    def AppendToMenu(self,menu,window,data):
        self.wdw = window
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_("Export list of allowed/disallowed OBSE plugin dlls"))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.wdw,_('Export list of allowed/disallowed OBSE plugin dlls to:'), textDir, _("OBSE dll permissions.txt"), '*.txt')
        if not textPath: return
        try:
            out = textPath.open("w")
            out.write('goodDlls (those dlls that you have chosen to allow to be installed)\n')
            if settings['bash.installers.goodDlls']:
                for dll in settings['bash.installers.goodDlls']:
                    out.write('dll:'+dll+':\n')
                    for index, version in enumerate(settings['bash.installers.goodDlls'][dll]):
                        out.write('version %02d: %s\n' % (index, version))
            else: out.write("None")
            out.write('badDlls (those dlls that you have chosen to NOT allow to be installed)\n')
            if settings['bash.installers.badDlls']:
                for dll in settings['bash.installers.badDlls']:
                    out.write('dll:'+dll+':\n')
                    for index, version in enumerate(settings['bash.installers.badDlls'][dll]):
                        out.write('version %02d: %s\n' % (index, version))
            else: out.write("None")
        finally: out.close

class Installers_ImportDllInfo(Link):
    """Sort by type."""
    def AppendToMenu(self,menu,window,data):
        self.wdw = window
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_("Import list of allowed/disallowed OBSE plugin dlls"))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askOpen(self.wdw,_('Import list of allowed/disallowed OBSE plugin dlls from:'),
            textDir, _("OBSE dll permissions.txt"), '*.txt',mustExist=True)
        if not textPath: return
        message = _("Merge permissions from file with current dll permissions?\n('No' Replaces current permissions instead.)")
        if not balt.askYes(self.wdw,message,_('Merge permissions?')): replace = True
        else: replace = False
        try:
            inp = textPath.open("r")
            Dlls = {'goodDlls':{},'badDlls':{}}
            for line in inp:
                if line.startswith('goodDlls'):
                    current = Dlls['goodDlls']
                if line.startswith('badDlls'):
                    current = Dlls['badDlls']
                elif line.startswith('dll:'):
                    dll = line[4:-2]
                    current.setdefault(dll,[])
                elif line.startswith('version'):
                    ver = line[13:-2].strip("'").split(",")
                    current[dll].append([ver[0].strip("'"),int(ver[1]),long(ver[2])])
        finally: inp.close
        if not replace:
            settings['bash.installers.goodDlls'].update(Dlls['goodDlls'])
            settings['bash.installers.badDlls'].update(Dlls['badDlls'])
        else:
            settings['bash.installers.goodDlls'], settings['bash.installers.badDlls'] = Dlls['goodDlls'], Dlls['badDlls']

# Installer Links -------------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerLink(Link):
    """Common functions for installer links..."""

    def isSingleInstallable(self):
        if len(self.selected) == 1:
            installer = self.data[self.selected[0]]
            if not (isinstance(installer,bosh.InstallerProject) or isinstance(installer,bosh.InstallerArchive)):
                return False
            elif installer.type not in (1,2):
                return False
            return True
        return False

    def filterInstallables(self):
        return [archive for archive in self.selected if archive in self.data and self.data[archive].type in (1,2) and (isinstance(self.data[archive], bosh.InstallerProject) or isinstance(self.data[archive], bosh.InstallerArchive))]

    def hasMarker(self):
        if len(self.selected) > 0:
            for i in self.selected:
                if isinstance(self.data[i],bosh.InstallerMarker):
                    return True
        return False

    def isSingle(self):
        """Indicates whether or not is single installer."""
        return len(self.selected) == 1

    def isSingleMarker(self):
        """Indicates wheter or not is single installer marker."""
        if len(self.selected) != 1: return False
        else: return isinstance(self.data[self.selected[0]],bosh.InstallerMarker)

    def isSingleProject(self):
        """Indicates whether or not is single project."""
        if len(self.selected) != 1: return False
        else: return isinstance(self.data[self.selected[0]],bosh.InstallerProject)

    def isSingleArchive(self):
        """Indicates whether or not is single archive."""
        if len(self.selected) != 1: return False
        else: return isinstance(self.data[self.selected[0]],bosh.InstallerArchive)

    def isSelectedArchives(self):
        """Indicates whether or not selected is all archives."""
        for selected in self.selected:
            if not isinstance(self.data[selected],bosh.InstallerArchive): return False
        return True

    def getProjectPath(self):
        """Returns whether build directory exists."""
        archive = self.selected[0]
        return bosh.dirs['builds'].join(archive.sroot)

    def projectExists(self):
        if not len(self.selected) == 1: return False
        return self.getProjectPath().exists()

#------------------------------------------------------------------------------
class Installer_EditWizard(InstallerLink):
    """Edit the wizard.txt associated with this project"""
    def AppendToMenu(self, menu, window, data):
        Link.AppendToMenu(self, menu, window, data)
        menuItem = wx.MenuItem(menu, self.id, _('Edit Wizard...'))
        menu.AppendItem(menuItem)
        if self.isSingleProject():
            menuItem.Enable(self.data[self.selected[0]].hasWizard != False)
        else:
            menuItem.Enable(False)

    def Execute(self, event):
        path = self.selected[0]
        dir = self.data.dir
        dir.join(path.s, self.data[path].hasWizard).start()


class Installer_Wizard(InstallerLink):
    """Runs the install wizard to select subpackages and esp/m filtering"""
    parentWindow = ''

    def __init__(self, bAuto):
        InstallerLink.__init__(self)
        self.bAuto = bAuto

    def AppendToMenu(self, menu, window, data):
        Link.AppendToMenu(self, menu, window, data)
        if not self.bAuto:
            menuItem = wx.MenuItem(menu, self.id, _('Wizard'))
        else:
            menuItem = wx.MenuItem(menu, self.id, _('Auto Wizard'))
        menu.AppendItem(menuItem)
        if self.isSingle():
            installer = self.data[self.selected[0]]
            menuItem.Enable(installer.hasWizard != False)
        else:
            menuItem.Enable(False)

    def Execute(self, event):
        wx.BeginBusyCursor()
        installer = self.data[self.selected[0]]
        subs = []
        oldRemaps = installer.remaps
        installer.resetAllEspmNames()
        gInstallers.refreshCurrent(installer)
        for index in range(gInstallers.gSubList.GetCount()):
            subs.append(gInstallers.gSubList.GetString(index))
        saved = settings['bash.wizard.size']
        default = settingDefaults['bash.wizard.size']
        pos = settings['bash.wizard.pos']
        pageSize = (max(saved[0],default[0]),max(saved[1],default[1]))
        wizard = belt.InstallerWizard(self, subs, pageSize, pos)
        balt.ensureDisplayed(wizard)
        wx.EndBusyCursor()
        ret = wizard.Run()
        settings['bash.wizard.size'] = ret.PageSize
        settings['bash.wizard.pos'] = ret.Pos
        if ret.Canceled:
            installer.remaps = oldRemaps
            gInstallers.refreshCurrent(installer)
            return
        #Check the sub-packages that were selected by the wizard
        for index in range(gInstallers.gSubList.GetCount()):
            select = installer.subNames[index + 1] in ret.SelectSubPackages
            gInstallers.gSubList.Check(index, select)
            installer.subActives[index + 1] = select
        gInstallers.refreshCurrent(installer)
        #Check the espms that were selected by the wizard
        espms = gInstallers.gEspmList.GetStrings()
        installer.espmNots = set()
        for index, espm in enumerate(gInstallers.espms):
            if espms[index] in ret.SelectEspms:
                gInstallers.gEspmList.Check(index, True)
            else:
                gInstallers.gEspmList.Check(index, False)
                installer.espmNots.add(espm)
        gInstallers.refreshCurrent(installer)
        #Rename the espms that need renaming
        for oldName in ret.RenameEspms:
            installer.setEspmName(oldName, ret.RenameEspms[oldName])
        gInstallers.refreshCurrent(installer)
        #Install if necessary
        if settings['bash.installers.autoWizard']:
            #If it's currently installed, anneal
            if self.data[self.selected[0]].isActive:
                #Anneal
                progress = balt.Progress(_('Annealing...'), '\n'+' '*60)
                try:
                    self.data.anneal(self.selected, progress)
                finally:
                    progress.Destroy()
                    self.data.refresh(what='NS')
                    gInstallers.RefreshUIMods()
            else:
                #Install, if it's not installed
                progress = balt.Progress(_("Installing..."),'\n'+' '*60)
                try:
                    self.data.install(self.selected, progress)
                finally:
                    progress.Destroy()
                    self.data.refresh(what='N')
                    gInstallers.RefreshUIMods()
            bashFrame.RefreshData()
        #Build any ini tweaks
        manuallyApply = []  # List of tweaks the user needs to  manually apply
        for iniFile in ret.IniEdits:
            outFile = bosh.dirs['mods'].join('INI Tweaks','%s - Wizard Tweak [%s].ini' % (installer.archive, iniFile.sbody))
            file = outFile.open('w')
            file.write('; Generated by Wrye Bash %s for \'%s\' via wizard\n' % (settings['bash.readme'][1], iniFile.s))
            for section in ret.IniEdits[iniFile]:
                if section == ']set[':
                    format = 'set %(setting)s to %(value)s\n'
                elif section == ']setgs[':
                    format = 'setgs %(setting)s %(value)s\n'
                else:
                    file.write('\n[%s]\n' % section)
                    format = '%(setting)s = %(value)s\n'
                for setting in ret.IniEdits[iniFile][section]:
                    file.write(format % (dict(setting=setting, value=ret.IniEdits[iniFile][section][setting])))
            file.close()
            bosh.iniInfos.refresh()
            bosh.iniInfos.table.setItem(outFile.tail, 'installer', installer.archive)
            iniList.RefreshUI()
            if iniFile in installer.data_sizeCrc or iniFile.cs == 'oblivion.ini':
                if not settings['bash.installers.autoWizard'] and iniFile.cs != 'oblivion.ini':
                    # Can only automatically apply ini tweaks if the ini was actually installed.  Since
                    # BAIN is setup to not auto install after the wizard, we'll show a message telling the
                    # User what tweaks to apply manually.
                    manuallyApply.append((outFile,iniFile))
                    continue
                # Editing an INI file from this installer is ok, but editing Oblivion.ini
                # give a warning message
                if iniFile.cs == 'oblivion.ini':
                    message = _("Apply an ini tweak to Oblivion.ini?\n\nWARNING: Incorrect tweaks can result in CTDs and even damage to you computer!")
                    if not balt.askContinue(self.gTank,message,'bash.iniTweaks.continue',_("INI Tweaks")):
                        continue
                # INIPanel->splitter->left->iniList
                panel = iniList.GetParent().GetParent().GetParent()
                panel.AddOrSelectIniDropDown(bosh.dirs['mods'].join(iniFile))
                if bosh.iniInfos[outFile.tail] == 20: continue
                iniList.data.ini.applyTweakFile(outFile)
                iniList.RefreshUI('VALID')
                panel.tweakContents.RefreshUI(outFile.tail)
            else:
                # We wont automatically apply tweaks to anything other than Oblivion.ini or an ini from
                # this installer
                manuallyApply.append((outFile,iniFile))
        if len(manuallyApply) > 0:
            message = balt.fill(_('The following INI Tweaks were not automatically applied.  Be sure to apply them after installing the package.'))
            message += '\n\n'
            message += '\n'.join([' * ' + x[0].stail + '\n   TO: ' + x[1].s for x in manuallyApply])
            balt.showInfo(self.gTank,message)

#------------------------------------------------------------------------------
class Installer_Anneal(InstallerLink):
    """Anneal all packages."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Anneal'))
        menu.AppendItem(menuItem)
        selected = self.filterInstallables()
        menuItem.Enable(len(selected))

    def Execute(self,event):
        """Handle selection."""
        progress = balt.Progress(_("Annealing..."),'\n'+' '*60)
        try:
            self.data.anneal(self.filterInstallables(),progress)
        finally:
            progress.Destroy()
            self.data.refresh(what='NS')
            gInstallers.RefreshUIMods()
            bashFrame.RefreshData()

#------------------------------------------------------------------------------
class Installer_Duplicate(InstallerLink):
    """Duplicate selected Installers."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.title = _('Duplicate...')
        menuItem = wx.MenuItem(menu,self.id,self.title)
        menu.AppendItem(menuItem)
        menuItem.Enable(self.isSingle() and not self.isSingleMarker())

    def Execute(self,event):
        """Handle selection."""
        curName = self.selected[0]
        isdir = self.data.dir.join(curName).isdir()
        if isdir: root,ext = curName,''
        else: root,ext = curName.rootExt
        newName = root+' Copy'+ext
        index = 0
        while newName in self.data:
            newName = root + (_(' Copy (%d)') % index) + ext
            index += 1
        result = balt.askText(self.gTank,_("Duplicate %s to:") % curName.s,
            self.title,newName.s)
        result = (result or '').strip()
        if not result: return
        #--Error checking
        newName = GPath(result).tail
        if not newName.s:
            balt.ShowWarning(self.gTank,_("%s is not a valid name.") % result)
            return
        if newName in self.data:
            balt.ShowWarning(self.gTank,_("%s already exists.") % newName.s)
            return
        if self.data.dir.join(curName).isfile() and curName.cext != newName.cext:
            balt.ShowWarning(self.gTank,
                _("%s does not have correct extension (%s).") % (newName.s,curName.ext))
            return
        #--Duplicate
        try:
            wx.BeginBusyCursor()
            self.data.copy(curName,newName)
        finally:
            wx.EndBusyCursor()
        self.data.refresh(what='N')
        self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class Installer_Hide(InstallerLink):
    """Hide selected Installers."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.title = _('Hide...')
        menuItem = wx.MenuItem(menu,self.id,self.title)
        menu.AppendItem(menuItem)
        for item in window.GetSelected():
            if isinstance(window.data[item],bosh.InstallerMarker):
                menuItem.Enable(False)
                return
        menuItem.Enable(True)

    def Execute(self,event):
        """Handle selection."""
        if not bosh.inisettings['SkipHideConfirmation']:
            message = _(r'Hide these files? Note that hidden files are simply moved to the Bash\Hidden subdirectory.')
            if not balt.askYes(self.gTank,message,_('Hide Files')): return
        destDir = bosh.dirs['modsBash'].join('Hidden')
        for curName in self.selected:
            newName = destDir.join(curName)
            if newName.exists():
                message = (_('A file named %s already exists in the hidden files directory. Overwrite it?')
                    % (newName.stail,))
                if not balt.askYes(self.gTank,message,_('Hide Files')): return
            #Move
            try:
                wx.BeginBusyCursor()
                file = bosh.dirs['installers'].join(curName)
                file.moveTo(newName)
            finally:
                wx.EndBusyCursor()
        self.data.refresh(what='ION')
        self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class Installer_Rename(InstallerLink):
    """Renames files by pattern."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Rename...'))
        menu.AppendItem(menuItem)
        self.InstallerType = None
        ##Only enable if all selected items are of the same type
        firstItem = window.data[window.GetSelected()[0]]
        if(isinstance(firstItem,bosh.InstallerMarker)):
            self.InstallerType = bosh.InstallerMarker
        elif(isinstance(firstItem,bosh.InstallerArchive)):
            self.InstallerType = bosh.InstallerArchive
        elif(isinstance(firstItem,bosh.InstallerProject)):
            self.InstallerType = bosh.InstallerProject

        if(self.InstallerType):
            for item in window.GetSelected():
                if not isinstance(window.data[item],self.InstallerType):
                    menuItem.Enable(False)
                    return

        menuItem.Enable(True)

    def Execute(self,event):
        if len(self.selected) > 0:
            index = self.gTank.GetIndex(self.selected[0])
            if index != -1:
                self.gTank.gList.EditLabel(index)
#------------------------------------------------------------------------------
class Installer_HasExtraData(InstallerLink):
    """Toggle hasExtraData flag on installer."""

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Has Extra Directories'),kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        if self.isSingleInstallable():
            installer = self.data[self.selected[0]]
            menuItem.Check(installer.hasExtraData)
            menuItem.Enable(True)
        else:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        installer = self.data[self.selected[0]]
        installer.hasExtraData ^= True
        installer.refreshDataSizeCrc()
        installer.refreshStatus(self.data)
        self.data.refresh(what='N')
        self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class Installer_OverrideSkips(InstallerLink):
    """Toggle overrideSkips flag on installer."""

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Override Skips'),kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        if self.isSingleInstallable():
            installer = self.data[self.selected[0]]
            menuItem.Check(installer.overrideSkips)
            menuItem.Enable(True)
        else:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        installer = self.data[self.selected[0]]
        installer.overrideSkips ^= True
        installer.refreshDataSizeCrc()
        installer.refreshStatus(self.data)
        self.data.refresh(what='N')
        self.gTank.RefreshUI()
#------------------------------------------------------------------------------
class Installer_Install(InstallerLink):
    """Install selected packages."""
    mode_title = {'DEFAULT':_('Install'),'LAST':_('Install Last'),'MISSING':_('Install Missing')}

    def __init__(self,mode='DEFAULT'):
        Link.__init__(self)
        self.mode = mode

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.title = self.mode_title[self.mode]
        menuItem = wx.MenuItem(menu,self.id,self.title)
        menu.AppendItem(menuItem)
        selected = self.filterInstallables()
        menuItem.Enable(len(selected))

    def Execute(self,event):
        """Handle selection."""
        dir = self.data.dir
        progress = balt.Progress(_("Installing..."),'\n'+' '*60)
        try:
            last = (self.mode == 'LAST')
            override = (self.mode != 'MISSING')
            self.data.install(self.filterInstallables(),progress,last,override)
        finally:
            progress.Destroy()
            self.data.refresh(what='N')
            gInstallers.RefreshUIMods()
            bashFrame.RefreshData()

#------------------------------------------------------------------------------
class Installer_ListPackages(InstallerLink):
    """Copies list of Bain files to clipboard."""
    def AppendToMenu(self,menu,window,data):
        InstallerLink.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_("List Packages..."),_("Displays a list of all packages.  Also copies that list to the clipboard.  Useful for posting your package order on forums."))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        #--Get masters list
        message = _('Only show Installed Packages?\n(Else shows all packages)')
        if balt.askYes(self.gTank,message,_('Only Show Installed?')):
            text = self.data.getPackageList(False)
        else: text = self.data.getPackageList()
        if (wx.TheClipboard.Open()):
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        balt.showLog(self.gTank,text,_("BAIN Packages"),asDialog=False,fixedFont=False,icons=bashBlue)
#------------------------------------------------------------------------------
class Installer_ListStructure(InstallerLink):   # Provided by Waruddar
    """Copies folder structure of installer to clipboard."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.title = _("List Structure...")
        menuItem = wx.MenuItem(menu,self.id,self.title)
        menu.AppendItem(menuItem)
        if not self.isSingle() or isinstance(self.data[self.selected[0]], bosh.InstallerMarker):
            menuItem.Enable(False)
        else:
            menuItem.Enable(True)

    def Execute(self,event):
        archive = self.selected[0]
        installer = self.data[archive]
        text = installer.listSource(archive)

        #--Get masters list
        if (wx.TheClipboard.Open()):
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        balt.showLog(self.gTank,text,_("Package Structure"),asDialog=False,fixedFont=False,icons=bashBlue)
#------------------------------------------------------------------------------
class Installer_Move(InstallerLink):
    """Moves selected installers to desired spot."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Move To...'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        """Handle selection."""
        curPos = min(self.data[x].order for x in self.selected)
        message = _("Move selected archives to what position?\nEnter position number.\nLast: -1; First of Last: -2; Semi-Last: -3.")
        newPos = balt.askText(self.gTank,message,self.title,`curPos`)
        if not newPos: return
        newPos = newPos.strip()
        if not re.match('-?\d+',newPos):
            balt.showError(self.gTank,_("Position must be an integer."))
            return
        newPos = int(newPos)
        if newPos == -3: newPos = self.data[self.data.lastKey].order
        elif newPos == -2: newPos = self.data[self.data.lastKey].order+1
        elif newPos < 0: newPos = len(self.data.data)
        self.data.moveArchives(self.selected,newPos)
        self.data.refresh(what='N')
        self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class Installer_Open(balt.Tank_Open):
    """Open selected file(s)."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Open...'), _("Open '%s'") % (self.data.dir.tail))
        menu.AppendItem(menuItem)
        self.selected = [x for x in self.selected if not isinstance(self.data.data[x],bosh.InstallerMarker)]
        menuItem.Enable(bool(self.selected))

#------------------------------------------------------------------------------
class InstallerOpenAt_MainMenu(balt.MenuLink):
    """Main Open At Menu"""
    def AppendToMenu(self,menu,window,data):
        subMenu = wx.Menu()
        menu.AppendMenu(-1,self.name,subMenu)
        #--Only enable the menu and append the subMenu's if one archive is selected
        if len(window.GetSelected()) > 1:
            id = menu.FindItem(self.name)
            menu.Enable(id,False)
        else:
            for item in window.GetSelected():
                if not isinstance(window.data[item],bosh.InstallerArchive):
                    id = menu.FindItem(self.name)
                    menu.Enable(id,False)
                    break
            else:
                for link in self.links:
                    link.AppendToMenu(subMenu,window,data)

class Installer_OpenTesNexus(InstallerLink):
    """Open selected file(s)."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('TES Nexus...'))
        menu.AppendItem(menuItem)
        x = bosh.reTesNexus.search(data[0].s)
        menuItem.Enable(bool(self.isSingleArchive() and x and x.group(2)))

    def Execute(self,event):
        """Handle selection."""
        message = _("Attempt to open this as a mod at TES Nexus? This assumes that the trailing digits in the package's name are actually the id number of the mod at TES Nexus. If this assumption is wrong, you'll just get a random mod page (or error notice) at TES Nexus.")
        if balt.askContinue(self.gTank,message,'bash.installers.openTesNexus',_('Open at TES Nexus')):
            id = bosh.reTesNexus.search(self.selected[0].s).group(2)
            os.startfile('http://tesnexus.com/downloads/file.php?id='+id)

class Installer_OpenSearch(InstallerLink):
    """Open selected file(s)."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Google...'))
        menu.AppendItem(menuItem)
        x = bosh.reTesNexus.search(data[0].s)
        menuItem.Enable(bool(self.isSingleArchive() and x and x.group(1)))

    def Execute(self,event):
        """Handle selection."""
        message = _("Open a search for this on Google?")
        if balt.askContinue(self.gTank,message,'bash.installers.opensearch',_('Open a search')):
            os.startfile('http://www.google.com/search?hl=en&q='+bosh.reTesNexus.search(self.selected[0].s).group(1))

class Installer_OpenTESA(InstallerLink):
    """Open selected file(s)."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('TES Alliance...'))
        menu.AppendItem(menuItem)
        x = bosh.reTESA.search(data[0].s)
        menuItem.Enable(bool(self.isSingleArchive() and x and x.group(2)))

    def Execute(self,event):
        """Handle selection."""
        message = _("Attempt to open this as a mod at TES Alliance? This assumes that the trailing digits in the package's name are actually the id number of the mod at TES Alliance. If this assumption is wrong, you'll just get a random mod page (or error notice) at TES Alliance.")
        if balt.askContinue(self.gTank,message,'bash.installers.openTESA',_('Open at TES Alliance')):
            id = bosh.reTESA.search(self.selected[0].s).group(2)
            os.startfile('http://www.invision.tesalliance.org/forums/index.php?app=downloads&showfile='+id)

class Installer_OpenPES(InstallerLink):
    """Open selected file(s)."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Planet Elderscrolls...'))
        menu.AppendItem(menuItem)
        x = bosh.reTESA.search(data[0].s)
        menuItem.Enable(bool(self.isSingleArchive() and x and x.group(2)))

    def Execute(self,event):
        """Handle selection."""
        message = _("Attempt to open this as a mod at Planet Elderscrolls? This assumes that the trailing digits in the package's name are actually the id number of the mod at Planet Elderscrolls. If this assumption is wrong, you'll just get a random mod page (or error notice) at Planet Elderscrolls.")
        if balt.askContinue(self.gTank,message,'bash.installers.openPES',_('Open at Planet Elderscrolls')):
            id = bosh.reTESA.search(self.selected[0].s).group(2)
            os.startfile('http://planetelderscrolls.gamespy.com/View.php?view=OblivionMods.Detail&id='+id)
#------------------------------------------------------------------------------
class Installer_Refresh(InstallerLink):
    """Rescans selected Installers."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Refresh'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        """Handle selection."""
        dir = self.data.dir
        progress = balt.Progress(_("Refreshing Packages..."),'\n'+' '*60, abort=True)
        progress.setFull(len(self.selected))
        try:
            for index,archive in enumerate(self.selected):
                progress(index,_("Refreshing Packages...\n")+archive.s)
                installer = self.data[archive]
                apath = bosh.dirs['installers'].join(archive)
                installer.refreshBasic(apath,SubProgress(progress,index,index+1),True)
                self.data.hasChanged = True
        except CancelError:
            # User canceled the refresh
            pass
        finally:
            if progress != None: progress.Destroy()
        self.data.refresh(what='NSC')
        self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class Installer_SkipVoices(InstallerLink):
    """Toggle skipVoices flag on installer."""

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Skip Voices'),kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        if self.isSingleInstallable():
            installer = self.data[self.selected[0]]
            menuItem.Check(installer.skipVoices)
            menuItem.Enable(True)
        else:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        installer = self.data[self.selected[0]]
        installer.skipVoices ^= True
        installer.refreshDataSizeCrc()
        self.data.refresh(what='NS')
        self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class Installer_Uninstall(InstallerLink):
    """Uninstall selected Installers."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Uninstall'))
        menu.AppendItem(menuItem)
        selected = self.filterInstallables()
        menuItem.Enable(len(selected))

    def Execute(self,event):
        """Handle selection."""
        dir = self.data.dir
        progress = balt.Progress(_("Uninstalling..."),'\n'+' '*60)
        try:
            self.data.uninstall(self.filterInstallables(),progress)
        finally:
            progress.Destroy()
            self.data.refresh(what='NS')
            gInstallers.RefreshUIMods()
            bashFrame.RefreshData()

#------------------------------------------------------------------------------
class Installer_CopyConflicts(InstallerLink):
    """For Modders only - copy conflicts to a new project."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.title = _('Copy Conflicts to Project')
        menuItem = wx.MenuItem(menu,self.id,self.title)
        menu.AppendItem(menuItem)
        menuItem.Enable(self.isSingleInstallable())

    def Execute(self,event):
        """Handle selection."""
        dir = self.data.dir
        data = self.data
        srcConflicts = set()
        packConflicts = []
        progress = balt.Progress(_("Copying Conflicts..."),'\n'+' '*60)
        try:
            srcArchive = self.selected[0]
            srcInstaller = self.data[srcArchive]
            src_sizeCrc = srcInstaller.data_sizeCrc
            mismatched = set(src_sizeCrc)
            if mismatched:
                numFiles = 0
                curFile = 1
                srcOrder = srcInstaller.order
                destDir = GPath("%03d - Conflicts" % (srcOrder))
                getArchiveOrder =  lambda x: data[x].order
                for package in sorted(data.data,key=getArchiveOrder):
                    installer = data[package]
                    curConflicts = set()
                    for x,y in installer.refreshDataSizeCrc().iteritems():
                        if x in mismatched and installer.data_sizeCrc[x] != src_sizeCrc[x]:
                            curConflicts.add(y)
                            srcConflicts.add(src_sizeCrc[x])
                    numFiles += len(curConflicts)
                    if curConflicts: packConflicts.append((installer.order,installer,package,curConflicts))
                srcConflicts = set(src for src, size, crc in srcInstaller.fileSizeCrcs if (size,crc) in srcConflicts)
                numFiles += len(srcConflicts)
                if numFiles:
                    progress.setFull(numFiles)
                    if isinstance(srcInstaller,bosh.InstallerProject):
                        for src in srcConflicts:
                            srcFull = bosh.dirs['installers'].join(srcArchive,src)
                            destFull = bosh.dirs['installers'].join(destDir,GPath(srcArchive.s),src)
                            if srcFull.exists():
                                progress(curFile, _("%s\nCopying files...\n%s")%(srcArchive.s,src))
                                srcFull.copyTo(destFull)
                                curFile += 1
                    else:
                        srcInstaller.unpackToTemp(srcArchive, srcConflicts,SubProgress(progress,0,len(srcConflicts),numFiles))
                        srcInstaller.tempDir.moveTo(bosh.dirs['installers'].join(destDir,GPath(srcArchive.s)))
                    curFile = len(srcConflicts)
                    for order, installer, package, curConflicts in packConflicts:
                        if isinstance(installer,bosh.InstallerProject):
                            for src in curConflicts:
                                srcFull = bosh.dirs['installers'].join(package,src)
                                destFull = bosh.dirs['installers'].join(destDir,GPath("%03d - %s" % (order, package.s)),src)
                                if srcFull.exists():
                                    progress(curFile, _("%s\nCopying files...\n%s")%(srcArchive.s,src))
                                    srcFull.copyTo(destFull)
                                    curFile += 1
                        else:
                            installer.unpackToTemp(package, curConflicts,SubProgress(progress,curFile,curFile+len(curConflicts),numFiles))
                            installer.tempDir.moveTo(bosh.dirs['installers'].join(destDir,GPath("%03d - %s" % (order, package.s))))
                            curFile += len(curConflicts)
                    project = destDir.root
                    if project not in self.data:
                        self.data[project] = bosh.InstallerProject(project)
                    iProject = self.data[project]
                    pProject = bosh.dirs['installers'].join(project)
                    iProject.refreshed = False
                    iProject.refreshBasic(pProject,None,True)
                    if iProject.order == -1:
                        self.data.moveArchives([project],srcInstaller.order+1)
                    self.data.refresh(what='I')
                    self.gTank.RefreshUI()
        finally:
            progress.Destroy()

# InstallerDetails Espm Links ------------------------------------------------------
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
class Installer_Espm_SelectAll(InstallerLink):
    """Select All Esp/ms in installer for installation."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Select All'))
        menu.AppendItem(menuItem)
        if len(gInstallers.espms) == 0:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        installer.espmNots = set()
        for i in range(len(gInstallers.espms)):
            gInstallers.gEspmList.Check(i, True)
        gInstallers.refreshCurrent(installer)

class Installer_Espm_DeselectAll(InstallerLink):
    """Deselect All Esp/ms in installer for installation."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Deselect All'))
        menu.AppendItem(menuItem)
        if len(gInstallers.espms) == 0:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        espmNots = installer.espmNots = set()
        for i in range(len(gInstallers.espms)):
            gInstallers.gEspmList.Check(i, False)
            espm = GPath(gInstallers.gEspmList.GetString(i))
            espmNots.add(espm)
        gInstallers.refreshCurrent(installer)

class Installer_Espm_Rename(InstallerLink):
    """Changes the installed name for an Esp/m."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Rename...'))
        menu.AppendItem(menuItem)
        if data == -1:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        curName = gInstallers.gEspmList.GetString(self.data)
        if curName[0] == '*':
            curName = curName[1:]
        file = GPath(curName)
        newName = balt.askText(self.window,_("Enter new name (without the extension):"),
                               _("Rename Esp/m"), file.sbody)
        if not newName: return
        if newName in gInstallers.espms: return
        installer.setEspmName(curName,newName+file.cext)
        gInstallers.refreshCurrent(installer)

class Installer_Espm_Reset(InstallerLink):
    """Resets the installed name for an Esp/m."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Reset Name'))
        menu.AppendItem(menuItem)
        if data == -1:
            menuItem.Enable(False)
            return
        installer = gInstallers.data[gInstallers.detailsItem]
        curName = gInstallers.gEspmList.GetString(self.data)
        if curName[0] == '*':
            curName = curName[1:]
        menuItem.Enable(installer.isEspmRenamed(curName))

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        curName = gInstallers.gEspmList.GetString(self.data)
        if curName[0] == '*':
            curName = curName[1:]
        installer.resetEspmName(curName)
        gInstallers.refreshCurrent(installer)

class Installer_Espm_ResetAll(InstallerLink):
    """Resets all renamed Esp/ms."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Reset All Names'))
        menu.AppendItem(menuItem)
        if len(gInstallers.espms) == 0:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        installer.resetAllEspmNames()
        gInstallers.refreshCurrent(installer)
# InstallerDetails Subpackage Links ------------------------------------------------------
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
class Installer_Subs_SelectAll(InstallerLink):
    """Select All sub-packages in installer for installation."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Select All'))
        menu.AppendItem(menuItem)
        if gInstallers.gSubList.GetCount() < 2:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        for index in range(gInstallers.gSubList.GetCount()):
            gInstallers.gSubList.Check(index, True)
            installer.subActives[index + 1] = True
        gInstallers.refreshCurrent(installer)

class Installer_Subs_DeselectAll(InstallerLink):
    """Deselect All sub-packages in installer for installation."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Deselect All'))
        menu.AppendItem(menuItem)
        if gInstallers.gSubList.GetCount() < 2:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        for index in range(gInstallers.gSubList.GetCount()):
            gInstallers.gSubList.Check(index, False)
            installer.subActives[index + 1] = False
        gInstallers.refreshCurrent(installer)

class Installer_Subs_ToggleSelection(InstallerLink):
    """Toggles selection state of all sub-packages in installer for installation."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Toggle Selection'))
        menu.AppendItem(menuItem)
        if gInstallers.gSubList.GetCount() < 2:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        for index in range(gInstallers.gSubList.GetCount()):
            check = not installer.subActives[index+1]
            gInstallers.gSubList.Check(index, check)
            installer.subActives[index + 1] = check
        gInstallers.refreshCurrent(installer)

class Installer_Subs_ListSubPackages(InstallerLink):
    """Lists all sub-packages in installer for user information/w/e."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('List Sub-packages'))
        menu.AppendItem(menuItem)
        if gInstallers.gSubList.GetCount() < 2:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        subs = _('[spoiler]\nSub-Packages List for "%s"\n') % (gInstallers.data[gInstallers.detailsItem].archive)
        for index in range(gInstallers.gSubList.GetCount()):
            subs += gInstallers.gSubList.GetString(index) + '\n'
        subs += '[/spoiler]'
        if (wx.TheClipboard.Open()):
            wx.TheClipboard.SetData(wx.TextDataObject(subs))
            wx.TheClipboard.Close()
        balt.showLog(self.window,subs,_("Sub-Package List"),asDialog=False,fixedFont=False,icons=bashBlue)
# InstallerArchive Links ------------------------------------------------------
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerArchive_Unpack(InstallerLink):
    """Install selected packages."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        if self.isSelectedArchives():
            self.title = _('Unpack to Project(s)...')
            menuItem = wx.MenuItem(menu,self.id,self.title)
            menu.AppendItem(menuItem)

    def Execute(self,event):
        if self.isSingleArchive():
            archive = self.selected[0]
            installer = self.data[archive]
            project = archive.root
            result = balt.askText(self.gTank,_("Unpack %s to Project:") % archive.s,
                self.title,project.s)
            result = (result or '').strip()
            if not result: return
            #--Error checking
            project = GPath(result).tail
            if not project.s or project.cext in bosh.readExts:
                balt.ShowWarning(self.gTank,_("%s is not a valid project name.") % result)
                return
            if self.data.dir.join(project).isfile():
                balt.ShowWarning(self.gTank,_("%s is a file.") % project.s)
                return
            if project in self.data:
                if not balt.askYes(self.gTank,_("%s already exists. Overwrite it?") % project.s,self.title,False):
                    return
        #--Copy to Build
        progress = balt.Progress(_("Unpacking to Project..."),'\n'+' '*60)
        try:
            if self.isSingleArchive():
                installer.unpackToProject(archive,project,SubProgress(progress,0,0.8))
                if project not in self.data:
                    self.data[project] = bosh.InstallerProject(project)
                iProject = self.data[project]
                pProject = bosh.dirs['installers'].join(project)
                iProject.refreshed = False
                iProject.refreshBasic(pProject,SubProgress(progress,0.8,0.99),True)
                if iProject.order == -1:
                    self.data.moveArchives([project],installer.order+1)
                self.data.refresh(what='NS')
                self.gTank.RefreshUI()
                #pProject.start()
            else:
                for archive in self.selected:
                    project = archive.root
                    installer = self.data[archive]
                    if project in self.data:
                        if not balt.askYes(self.gTank,_("%s already exists. Overwrite it?") % project.s,self.title,False):
                            continue
                    installer.unpackToProject(archive,project,SubProgress(progress,0,0.8))
                    if project not in self.data:
                        self.data[project] = bosh.InstallerProject(project)
                    iProject = self.data[project]
                    pProject = bosh.dirs['installers'].join(project)
                    iProject.refreshed = False
                    iProject.refreshBasic(pProject,SubProgress(progress,0.8,0.99),True)
                    if iProject.order == -1:
                        self.data.moveArchives([project],installer.order+1)
                self.data.refresh(what='NS')
                self.gTank.RefreshUI()
        finally:
            progress.Destroy()

# InstallerProject Links ------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerProject_OmodConfigDialog(wx.Frame):
    """Dialog for editing omod configuration data."""
    def __init__(self,parent,data,project):
        #--Data
        self.data = data
        self.project = project
        self.config = config = data[project].getOmodConfig(project)
        #--GUI
        wx.Frame.__init__(self,parent,-1,_('Omod Config: ')+project.s,
            style=(wx.RESIZE_BORDER | wx.CAPTION | wx.CLIP_CHILDREN))
        self.SetIcons(bashBlue)
        self.SetSizeHints(300,300)
        self.SetBackgroundColour(wx.NullColour)
        #--Fields
        self.gName = wx.TextCtrl(self,-1,config.name)
        self.gVersion = wx.TextCtrl(self,-1,'%d.%02d' % (config.vMajor,config.vMinor))
        self.gWebsite = wx.TextCtrl(self,-1,config.website)
        self.gAuthor = wx.TextCtrl(self,-1,config.author)
        self.gEmail = wx.TextCtrl(self,-1,config.email)
        self.gAbstract = wx.TextCtrl(self,-1,config.abstract,style=wx.TE_MULTILINE)
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
            staticText(self,_("Name:")), (self.gName,1,wx.EXPAND),
            staticText(self,_("Version:")),(self.gVersion,1,wx.EXPAND),
            staticText(self,_("Website:")),(self.gWebsite,1,wx.EXPAND),
            staticText(self,_("Author:")),(self.gAuthor,1,wx.EXPAND),
            staticText(self,_("Email:")),(self.gEmail,1,wx.EXPAND),
            ])
        sizer = vSizer(
            (fgSizer,0,wx.EXPAND|wx.ALL^wx.BOTTOM,4),
            (staticText(self,_("Abstract")),0,wx.LEFT|wx.RIGHT,4),
            (self.gAbstract,1,wx.EXPAND|wx.ALL^wx.BOTTOM,4),
            (hSizer(
                spacer,
                (button(self,id=wx.ID_SAVE,onClick=self.DoSave),0,),
                (button(self,id=wx.ID_CANCEL,onClick=self.DoCancel),0,wx.LEFT,4),
                ),0,wx.EXPAND|wx.ALL,4),
            )
        #--Done
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
        maVersion = re.match(r'(\d+)\.(\d+)',self.gVersion.GetValue().strip())
        if maVersion:
            config.vMajor,config.vMinor = map(int,maVersion.groups())
        else:
            config.vMajor,config.vMinor = (0,0)
        #--Done
        self.data[self.project].writeOmodConfig(self.project,self.config)
        self.Destroy()

#------------------------------------------------------------------------------
class InstallerProject_OmodConfig(InstallerLink):
    """Install selected packages."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.title = _('Omod Info...')
        menuItem = wx.MenuItem(menu,self.id,self.title)
        menu.AppendItem(menuItem)
        menuItem.Enable(self.isSingleProject())

    def Execute(self,event):
        project = self.selected[0]
        dialog = InstallerProject_OmodConfigDialog(self.gTank,self.data,project)
        dialog.Show()

#------------------------------------------------------------------------------
class InstallerProject_Sync(InstallerLink):
    """Install selected packages."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.title = _('Sync from Data')
        menuItem = wx.MenuItem(menu,self.id,self.title)
        menu.AppendItem(menuItem)
        enabled = False
        if self.isSingleProject():
            project = self.selected[0]
            installer = self.data[project]
            enabled = bool(installer.missingFiles or installer.mismatchedFiles)
        menuItem.Enable(enabled)

    def Execute(self,event):
        project = self.selected[0]
        installer = self.data[project]
        missing = installer.missingFiles
        mismatched = installer.mismatchedFiles
        message = _("Update %s according to data directory?\nFiles to delete: %d\nFiles to update: %d") % (
            project.s,len(missing),len(mismatched))
        if not balt.askWarning(self.gTank,message,self.title): return
        #--Sync it, baby!
        progress = balt.Progress(self.title,'\n'+' '*60)
        try:
            progress(0.1,_("Updating files."))
            installer.syncToData(project,missing|mismatched)
            pProject = bosh.dirs['installers'].join(project)
            installer.refreshed = False
            installer.refreshBasic(pProject,SubProgress(progress,0.1,0.99),True)
            self.data.refresh(what='NS')
            self.gTank.RefreshUI()
        finally:
            progress.Destroy()

#------------------------------------------------------------------------------
class InstallerProject_SyncPack(InstallerLink):
    """Install selected packages."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Sync and Pack'))
        menu.AppendItem(menuItem)
        menuItem.Enable(self.projectExists())

    def Execute(self,event):
        raise UncodedError

#------------------------------------------------------------------------------
class InstallerProject_Pack(InstallerLink):
    """Pack project to an archive."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        #--Pack is appended whenever Unpack isn't, and vice-versa
        if self.isSingleProject():
            self.title = _('Pack to Archive...')
            menuItem = wx.MenuItem(menu,self.id,self.title)
            menu.AppendItem(menuItem)

    def Execute(self,event):
        #--Generate default filename from the project name and the default extension
        project = self.selected[0]
        installer = self.data[project]
        archive = bosh.GPath(project.s + bosh.defaultExt)
        #--Confirm operation
        result = balt.askText(self.gTank,_("Pack %s to Archive:") % project.s,
            self.title,archive.s)
        result = (result or '').strip()
        if not result: return
        #--Error checking
        archive = GPath(result).tail
        if not archive.s:
            balt.ShowWarning(self.gTank,_("%s is not a valid archive name.") % result)
            return
        if self.data.dir.join(archive).isdir():
            balt.ShowWarning(self.gTank,_("%s is a directory.") % archive.s)
            return
        if archive.cext not in bosh.writeExts:
            balt.showWarning(self.gTank,_("The %s extension is unsupported. Using %s instead.") % (archive.cext, bosh.defaultExt))
            archive = GPath(archive.sroot + bosh.defaultExt).tail
        if archive in self.data:
            if not balt.askYes(self.gTank,_("%s already exists. Overwrite it?") % archive.s,self.title,False): return
        #--Archive configuration options
        blockSize = None
        if archive.cext in bosh.noSolidExts:
            isSolid = False
        else:
            if not '-ms=' in bosh.inisettings['7zExtraCompressionArguments']:
                isSolid = balt.askYes(self.gTank,_("Use solid compression for %s?") % archive.s,self.title,False)
                if isSolid:
                    blockSize = balt.askNumber(self.gTank,_("Use what maximum size for each solid block?\nEnter '0' to use 7z's default size."),'MB',self.title,0,0,102400)
            else: isSolid = True
        progress = balt.Progress(_("Packing to Archive..."),'\n'+' '*60)
        try:
            #--Pack
            installer.packToArchive(project,archive,isSolid,blockSize,SubProgress(progress,0,0.8))
            #--Add the new archive to Bash
            if archive not in self.data:
                self.data[archive] = bosh.InstallerArchive(archive)
            #--Refresh UI
            iArchive = self.data[archive]
            pArchive = bosh.dirs['installers'].join(archive)
            iArchive.blockSize = blockSize
            iArchive.refreshed = False
            iArchive.refreshBasic(pArchive,SubProgress(progress,0.8,0.99),True)
            if iArchive.order == -1:
                self.data.moveArchives([archive],installer.order+1)
            #--Refresh UI
            self.data.refresh(what='I')
            self.gTank.RefreshUI()
        finally:
            progress.Destroy()
#------------------------------------------------------------------------------
class InstallerProject_ReleasePack(InstallerLink):
    """Pack project to an archive for release. Ignores dev files/folders."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.title = _('Package for Release...')
        menuItem = wx.MenuItem(menu,self.id,self.title)
        menu.AppendItem(menuItem)
        menuItem.Enable(self.isSingleProject())

    def Execute(self,event):
        #--Generate default filename from the project name and the default extension
        project = self.selected[0]
        installer = self.data[project]
        archive = bosh.GPath(project.s + bosh.defaultExt)
        #--Confirm operation
        result = balt.askText(self.gTank,_("Pack %s to Archive:") % project.s,
            self.title,archive.s)
        result = (result or '').strip()
        if not result: return
        #--Error checking
        archive = GPath(result).tail
        if not archive.s:
            balt.ShowWarning(self.gTank,_("%s is not a valid archive name.") % result)
            return
        if self.data.dir.join(archive).isdir():
            balt.ShowWarning(self.gTank,_("%s is a directory.") % archive.s)
            return
        if archive.cext not in bosh.writeExts:
            balt.showWarning(self.gTank,_("The %s extension is unsupported. Using %s instead.") % (archive.cext, bosh.defaultExt))
            archive = GPath(archive.sroot + bosh.defaultExt).tail
        if archive in self.data:
            if not balt.askYes(self.gTank,_("%s already exists. Overwrite it?") % archive.s,self.title,False): return
        #--Archive configuration options
        blockSize = None
        if archive.cext in bosh.noSolidExts:
            isSolid = False
        else:
            if not '-ms=' in bosh.inisettings['7zExtraCompressionArguments']:
                isSolid = balt.askYes(self.gTank,_("Use solid compression for %s?") % archive.s,self.title,False)
                if isSolid:
                    blockSize = balt.askNumber(self.gTank,_("Use what maximum size for each solid block?\nEnter '0' to use 7z's default size."),'MB',self.title,0,0,102400)
            else: isSolid = True
        progress = balt.Progress(_("Packing to Archive..."),'\n'+' '*60)
        try:
            #--Pack
            installer.packToArchive(project,archive,isSolid,blockSize,SubProgress(progress,0,0.8),release=True)
            #--Add the new archive to Bash
            if archive not in self.data:
                self.data[archive] = bosh.InstallerArchive(archive)
            #--Refresh UI
            iArchive = self.data[archive]
            pArchive = bosh.dirs['installers'].join(archive)
            iArchive.blockSize = blockSize
            iArchive.refreshed = False
            iArchive.refreshBasic(pArchive,SubProgress(progress,0.8,0.99),True)
            if iArchive.order == -1:
                self.data.moveArchives([archive],installer.order+1)
            #--Refresh UI
            self.data.refresh(what='I')
            self.gTank.RefreshUI()
        finally:
            progress.Destroy()

#------------------------------------------------------------------------------
class InstallerConverter_Apply(InstallerLink):
    """Apply a Bain Conversion File."""
    def __init__(self,converter,numAsterisks):
        InstallerLink.__init__(self)
        self.converter = converter
        #--Add asterisks to indicate the number of unselected archives that the BCF uses
        self.dispName = ''.join((self.converter.fullPath.sbody,'*' * numAsterisks))

    def AppendToMenu(self,menu,window,data):
        InstallerLink.AppendToMenu(self,menu,window,data)
        self.title = _("Apply BCF...")
        menuItem = wx.MenuItem(menu,self.id,_(self.dispName))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        #--Generate default filename from BCF filename
        result = self.converter.fullPath.sbody[:-4]
        #--List source archives
        message = _("Using:\n* ")
        message += '\n* '.join(sorted("(%08X) - %s" % (x,self.data.crc_installer[x].archive) for x in self.converter.srcCRCs)) + '\n'
        #--Confirm operation
        result = balt.askText(self.gTank,message,self.title,result + bosh.defaultExt)
        result = (result or '').strip()
        if not result: return
        #--Error checking
        destArchive = GPath(result).tail
        if not destArchive.s:
            balt.showWarning(self.gTank,_("%s is not a valid archive name.") % result)
            return
        if destArchive.cext not in bosh.writeExts:
            balt.showWarning(self.gTank,_("The %s extension is unsupported. Using %s instead.") % (destArchive.cext, bosh.defaultExt))
            destArchive = GPath(destArchive.sroot + bosh.defaultExt).tail
        if destArchive in self.data:
            if not balt.askYes(self.gTank,_("%s already exists. Overwrite it?") % destArchive.s,self.title,False): return
        progress = balt.Progress(_("Converting to Archive..."),'\n'+' '*60)
        try:
            #--Perform the conversion
            self.converter.apply(destArchive,self.data.crc_installer,SubProgress(progress,0.0,0.99))
            #--Add the new archive to Bash
            if destArchive not in self.data:
                self.data[destArchive] = bosh.InstallerArchive(destArchive)
            #--Apply settings from the BCF to the new InstallerArchive
            iArchive = self.data[destArchive]
            self.converter.applySettings(iArchive)
            #--Refresh UI
            pArchive = bosh.dirs['installers'].join(destArchive)
            iArchive.refreshed = False
            iArchive.refreshBasic(pArchive,SubProgress(progress,0.99,1.0),True)
            if iArchive.order == -1:
                lastInstaller = self.data[self.selected[-1]]
                self.data.moveArchives([destArchive],lastInstaller.order+1)
            self.data.refresh(what='I')
            self.gTank.RefreshUI()
        finally:
            progress.Destroy()

#------------------------------------------------------------------------------
class InstallerConverter_ConvertMenu(balt.MenuLink):
    """Apply BCF SubMenu."""
    def AppendToMenu(self,menu,window,data):
        subMenu = wx.Menu()
        menu.AppendMenu(-1,self.name,subMenu)
        linkSet = set()
        #--Converters are linked by CRC, not archive name
        #--So, first get all the selected archive CRCs
        selectedCRCs = set(window.data[archive].crc for archive in window.GetSelected())
        crcInstallers = set(window.data.crc_installer)
        srcCRCs = set(window.data.srcCRC_converters)
        #--There is no point in testing each converter unless
        #--every selected archive has an associated converter
        if selectedCRCs <= srcCRCs:
            #--List comprehension is faster than unrolling the for loops, but readability suffers
            #--Test every converter for every selected archive
            #--Only add a link to the converter if it uses all selected archives,
            #--and all of its required archives are available (but not necessarily selected)
            linkSet = set([converter for installerCRC in selectedCRCs for converter in window.data.srcCRC_converters[installerCRC] if selectedCRCs <= converter.srcCRCs <= crcInstallers])
##            for installerCRC in selectedCRCs:
##                for converter in window.data.srcCRC_converters[installerCRC]:
##                    if selectedCRCs <= converter.srcCRCs <= set(window.data.crc_installer): linkSet.add(converter)
        #--Disable the menu if there were no valid converters found
        if not linkSet:
            id = menu.FindItem(self.name)
            menu.Enable(id,False)
        else:
            #--Otherwise add each link in alphabetical order, and
            #--indicate the number of additional, unselected archives
            #--that the converter requires
            for converter in sorted(linkSet,key=lambda x: x.fullPath.stail.lower()):
                numAsterisks = len(converter.srcCRCs - selectedCRCs)
                newMenu = InstallerConverter_Apply(converter,numAsterisks)
                newMenu.AppendToMenu(subMenu,window,data)

#------------------------------------------------------------------------------
class InstallerConverter_Create(InstallerLink):
    """Create BAIN conversion file."""

    def AppendToMenu(self,menu,window,data):
        InstallerLink.AppendToMenu(self,menu,window,data)
        self.title = _("Create BCF...")
        menuItem = wx.MenuItem(menu,self.id,_('Create...'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        #--Generate allowable targets
        readTypes = '*%s' % ';*'.join(bosh.readExts)
        #--Select target archive
        destArchive = balt.askOpen(self.gTank,_('Select the BAIN\'ed Archive:'),self.data.dir,'', readTypes,mustExist=True)
        if not destArchive: return
        #--Error Checking
        BCFArchive = destArchive = destArchive.tail
        if not destArchive.s or destArchive.cext not in bosh.readExts:
            balt.showWarning(self.gTank,_("%s is not a valid archive name.") % destArchive.s)
            return
        if destArchive not in self.data:
            balt.showWarning(self.gTank,_("%s must be in the Bash Installers directory.") % destArchive.s)
            return
        if BCFArchive.csbody[-4:] != _('-bcf'):
            BCFArchive = GPath(BCFArchive.sbody + _('-BCF') + bosh.defaultExt).tail
        #--List source archives and target archive
        message = _("Convert:")
        message += '\n* ' + '\n* '.join(sorted("(%08X) - %s" % (self.data[x].crc,x.s) for x in self.selected))
        message += _('\n\nTo:\n* (%08X) - %s') % (self.data[destArchive].crc,destArchive.s) + '\n'
        #--Confirm operation
        result = balt.askText(self.gTank,message,self.title,BCFArchive.s)
        result = (result or '').strip()
        if not result: return
        #--Error checking
        BCFArchive = GPath(result).tail
        if not BCFArchive.s:
            balt.showWarning(self.gTank,_("%s is not a valid archive name.") % result)
            return
        if BCFArchive.csbody[-4:] != _('-bcf'):
            BCFArchive = GPath(BCFArchive.sbody + _('-BCF') + BCFArchive.cext).tail
        if BCFArchive.cext != bosh.defaultExt:
            balt.showWarning(self.gTank,_("BCF's only support %s. The %s extension will be discarded.") % (bosh.defaultExt, BCFArchive.cext))
            BCFArchive = GPath(BCFArchive.sbody + bosh.defaultExt).tail
        if bosh.dirs['converters'].join(BCFArchive).exists():
            if not balt.askYes(self.gTank,_("%s already exists. Overwrite it?") % BCFArchive.s,self.title,False): return
            #--It is safe to removeConverter, even if the converter isn't overwritten or removed
            #--It will be picked back up by the next refresh.
            self.data.removeConverter(BCFArchive)
        destInstaller = self.data[destArchive]
        blockSize = None
        if destInstaller.isSolid:
            blockSize = balt.askNumber(self.gTank,'mb',_("Use what maximum size for each solid block?\nEnter '0' to use 7z's default size."),self.title,destInstaller.blockSize or 0,0,102400)
        progress = balt.Progress(_("Creating %s...") % BCFArchive.s,'\n'+' '*60)
        log = None
        try:
            #--Create the converter
            converter = bosh.InstallerConverter(self.selected, self.data, destArchive, BCFArchive, blockSize, progress)
            #--Add the converter to Bash
            self.data.addConverter(converter)
            #--Refresh UI
            self.data.refresh(what='C')
            #--Generate log
            log = bolt.LogFile(stringBuffer())
            log.setHeader(_('== Overview\n'))
##            log('{{CSS:wtxt_sand_small.css}}')
            log(_('. Name: %s') % BCFArchive.s)
            log(_('. Size: %s KB') % formatInteger(converter.fullPath.size/1024))
            log(_('. Remapped: %s file') % formatInteger(len(converter.convertedFiles)) + ('',_('s'))[len(converter.convertedFiles) > 1])
            log.setHeader(_('. Requires: %s file') % formatInteger(len(converter.srcCRCs)) +  ('',_('s'))[len(converter.srcCRCs) > 1])
            log('  * ' + '\n  * '.join(sorted("(%08X) - %s" % (x, self.data.crc_installer[x].archive) for x in converter.srcCRCs if x in self.data.crc_installer)))
            log.setHeader(_('. Options:'))
            log(_('  *  Skip Voices   = %s') % bool(converter.skipVoices))
            log(_('  *  Solid Archive = %s') % bool(converter.isSolid))
            if converter.isSolid:
                if converter.blockSize:
                    log(_('    *  Solid Block Size = %d') % (converter.blockSize))
                else:
                    log(_('    *  Solid Block Size = 7z default'))
            log(_('  *  Has Comments  = %s') % bool(converter.comments))
            log(_('  *  Has Extra Directories = %s') % bool(converter.hasExtraData))
            log(_('  *  Has Esps Unselected   = %s') % bool(converter.espmNots))
            log(_('  *  Has Packages Selected = %s') % bool(converter.subActives))
            log.setHeader(_('. Contains: %s file') % formatInteger(len(converter.missingFiles)) +  ('',_('s'))[len(converter.missingFiles) > 1])
            log('  * ' + '\n  * '.join(sorted("%s" % (x) for x in converter.missingFiles)))
        finally:
            progress.Destroy()
            if log:
               balt.showLog(self.gTank, log.out.getvalue(), _("BCF Information"))

#------------------------------------------------------------------------------
class InstallerConverter_MainMenu(balt.MenuLink):
    """Main BCF Menu"""
    def AppendToMenu(self,menu,window,data):
        subMenu = wx.Menu()
        menu.AppendMenu(-1,self.name,subMenu)
        #--Only enable the menu and append the subMenu's if all of the selected items are archives
        for item in window.GetSelected():
            if not isinstance(window.data[item],bosh.InstallerArchive):
                id = menu.FindItem(self.name)
                menu.Enable(id,False)
                break
        else:
            for link in self.links:
                link.AppendToMenu(subMenu,window,data)

# Mods Links ------------------------------------------------------------------
class Mods_ReplacersData:
    """Empty version of a now removed class. Here for compatibility with
    older settings files."""
    pass

class Mod_MergedLists_Data:
    """Empty version of a now removed class. Here for compatibility with
    older settings files."""
    pass

#------------------------------------------------------------------------------
class Mods_LoadListData(balt.ListEditorData):
    """Data capsule for load list editing dialog."""
    def __init__(self,parent):
        """Initialize."""
        self.data = settings['bash.loadLists.data']
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
                _('Name must be between 1 and 64 characters long.'))
            return False
        #--Rename
        settings.setChanged('bash.loadLists.data')
        self.data[newName] = self.data[oldName]
        del self.data[oldName]
        return newName

    def remove(self,item):
        """Removes load list."""
        settings.setChanged('bash.loadLists.data')
        del self.data[item]
        return True

#------------------------------------------------------------------------------
class Mods_LoadList:
    """Add load list links."""
    def __init__(self):
        self.data = settings['bash.loadLists.data']

    def GetItems(self):
        items = self.data.keys()
        items.sort(lambda a,b: cmp(a.lower(),b.lower()))
        return items

    def SortWindow(self):
        self.window.PopulateItems()

    def AppendToMenu(self,menu,window,data):
        self.window = window
        menu.Append(ID_LOADERS.NONE,_('None'))
        menu.Append(ID_LOADERS.SAVE,_('Save List...'))
        menu.Append(ID_LOADERS.EDIT,_('Edit Lists...'))
        menu.AppendSeparator()
        for id,item in zip(ID_LOADERS,self.GetItems()):
            menu.Append(id,item)
        #--Disable Save?
        if not bosh.modInfos.ordered:
            menu.FindItemById(ID_LOADERS.SAVE).Enable(False)
        #--Events
        wx.EVT_MENU(bashFrame,ID_LOADERS.NONE,self.DoNone)
        wx.EVT_MENU(bashFrame,ID_LOADERS.SAVE,self.DoSave)
        wx.EVT_MENU(bashFrame,ID_LOADERS.EDIT,self.DoEdit)
        wx.EVT_MENU_RANGE(bashFrame,ID_LOADERS.BASE,ID_LOADERS.MAX,self.DoList)

    def DoNone(self,event):
        """Unselect all mods."""
        bosh.modInfos.selectExact([])
        modList.RefreshUI()

    def DoList(self,event):
        """Select mods in list."""
        item = self.GetItems()[event.GetId()-ID_LOADERS.BASE]
        selectList = [GPath(modName) for modName in self.data[item]]
        errorMessage = bosh.modInfos.selectExact(selectList)
        modList.RefreshUI()
        if errorMessage:
            balt.showError(self.window,errorMessage,item)

    def DoSave(self,event):
        #--No slots left?
        if len(self.data) >= (ID_LOADERS.MAX - ID_LOADERS.BASE + 1):
            balt.showError(self,_('All load list slots are full. Please delete an existing load list before adding another.'))
            return
        #--Dialog
        newItem = (balt.askText(self.window,_('Save current load list as:'),'Wrye Bash') or '').strip()
        if not newItem: return
        if len(newItem) > 64:
            message = _('Load list name must be between 1 and 64 characters long.')
            return balt.showError(self.window,message)
        self.data[newItem] = bosh.modInfos.ordered[:]
        settings.setChanged('bash.loadLists.data')

    def DoEdit(self,event):
        data = Mods_LoadListData(self.window)
        dialog = balt.ListEditor(self.window,-1,_('Load Lists'),data)
        dialog.ShowModal()
        dialog.Destroy()

#------------------------------------------------------------------------------
class INI_SortValid(BoolLink):
    """Sort valid INI Tweaks to the top."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Valid Tweaks First'),
                                          'bash.ini.sortValid',
                                          _('Valid tweak files will be shown first.')
                                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        iniList.RefreshUI()

#-------------------------------------------------------------------------------
class INI_ListErrors(Link):
    """List errors that make an INI Tweak invalid."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('List Errors...'),_('Lists any errors in the tweak file causing it to be invalid.'))
        menu.AppendItem(menuItem)

        bEnable = False
        for i in data:
            if bosh.iniInfos[i].getStatus() < 0:
                bEnable = True
                break
        menuItem.Enable(bEnable)

    def Execute(self,event):
        """Handle printing out the errors."""
        if (wx.TheClipboard.Open()):
            text = ''
            for i in self.data:
                fileInfo = bosh.iniInfos[i]
                text += '%s\n' % fileInfo.listErrors()
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        balt.showLog(self.window,text,_('INI Tweak Errors'),asDialog=False,fixedFont=False,icons=bashBlue)
#-------------------------------------------------------------------------------
class INI_Apply(Link):
    """Apply an INI Tweak."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        ini = self.window.GetParent().GetParent().GetParent().comboBox.GetValue()
        tweak = data[0]
        menuItem = wx.MenuItem(menu,self.id,_('Apply'),_("Applies '%s' to '%s'.") % (tweak, ini))
        menu.AppendItem(menuItem)

        bEnable = True
        for i in data:
            iniInfo = bosh.iniInfos[i]
            if iniInfo.status < 0:
                bEnable = False
                break
        menuItem.Enable(bEnable)

    def Execute(self,event):
        """Handle applying INI Tweaks."""
        #-- If we're applying to Oblivion.ini, show the warning
        if self.window.GetParent().GetParent().GetParent().comboBox.GetSelection() == 0:
            message = _("Apply an ini tweak to Oblivion.ini?\n\nWARNING: Incorrect tweaks can result in CTDs and even damage to you computer!")
            if not balt.askContinue(self.window,message,'bash.iniTweaks.continue',_("INI Tweaks")):
                return
        dir = self.window.data.dir
        needsRefresh = False
        for item in self.data:
            #--No point applying a tweak that's already applied
            if bosh.iniInfos[item].status == 20: continue
            needsRefresh = True
            file = dir.join(item)
            iniList.data.ini.applyTweakFile(file)
        if needsRefresh:
            #--Refresh status of all the tweaks valid for this ini
            iniList.RefreshUI('VALID')
            self.window.GetParent().GetParent().GetParent().tweakContents.RefreshUI(self.data[0])

#------------------------------------------------------------------------------
class INI_CreateNew(Link):
    """Create a new INI Tweak using the settings from the tweak file, but values from the target INI."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        ini = self.window.GetParent().GetParent().GetParent().comboBox.GetValue()
        tweak = data[0]
        menuItem = wx.MenuItem(menu,self.id,_('Copy to new Tweak...'),_("Creates a new tweak based on '%s' but with values from '%s'.") % (tweak, ini))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) == 1)

    def Execute(self,event):
        """Handle creating a new INI tweak."""
        pathFrom = self.data[0]
        fileName = pathFrom.sbody + ' - Copy' + pathFrom.ext
        path = balt.askSave(self.window,_('Copy to new Tweak...'),bosh.dirs['mods'].join('INI Tweaks'),fileName,_('INI Tweak File (*.ini)|*.ini'))
        if not path: return
        bosh.dirs['mods'].join('INI Tweaks', pathFrom).copyTo(path)
        # Now edit it with the values from the target INI
        iniList.data.refresh()
        oldTarget = iniList.data.ini
        # Set new target as the tweak we're creating
        iniList.data.setBaseIni(bosh.BestIniFile(path))
        iniList.data.ini.applyTweakFile(oldTarget.path)
        # Restore the old target and refresh
        iniList.data.ini = oldTarget
        iniList.RefreshUI(detail=path)
        self.window.GetParent().GetParent().GetParent().tweakContents.RefreshUI(path.tail)

#------------------------------------------------------------------------------
class Mods_EsmsFirst(Link):
    """Sort esms to the top."""
    def __init__(self,prefix=''):
        Link.__init__(self)
        self.prefix = prefix

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,self.prefix+_('Type'),_('Sort masters by type'),kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        menuItem.Check(window.esmsFirst)

    def Execute(self,event):
        self.window.esmsFirst = not self.window.esmsFirst
        self.window.PopulateItems()

#------------------------------------------------------------------------------
class Mods_SelectedFirst(Link):
    """Sort loaded mods to the top."""
    def __init__(self,prefix=''):
        Link.__init__(self)
        self.prefix = prefix

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,self.prefix+_('Selection'),kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        if window.selectedFirst: menuItem.Check()

    def Execute(self,event):
        self.window.selectedFirst = not self.window.selectedFirst
        self.window.PopulateItems()

#------------------------------------------------------------------------------
class Mods_ScanDirty(BoolLink):
    """Read mod CRC's to check for dirty mods."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Scan for dirty edits (requires BOSS 1.7+)'),
                                          'bash.mods.scanDirty',
                                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        self.window.PopulateItems()

#------------------------------------------------------------------------------
class Mods_AutoGhost(BoolLink):
    """Toggle Auto-ghosting."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Auto-Ghost'),
                                          'bash.mods.autoGhost',
                                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        files = bosh.modInfos.autoGhost(True)
        self.window.RefreshUI(files)

#------------------------------------------------------------------------------
class Mods_AutoGroup(BoolLink):
    """Turn on autogrouping."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Auto Group'),
                                          'bash.balo.autoGroup',
                                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        bosh.modInfos.updateAutoGroups()

#------------------------------------------------------------------------------
class Mods_Deprint(Link):
    """Turn on deprint/delist."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Debug Mode'),kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        menuItem.Check(bolt.deprintOn)

    def Execute(self,event):
        deprint(_('Debug Printing: Off'))
        bolt.deprintOn = not bolt.deprintOn
        deprint(_('Debug Printing: On'))

#------------------------------------------------------------------------------
class Mods_FullBalo(BoolLink):
    """Turn Full Balo off/on."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Full Balo'),
                                          'bash.balo.full',
                                          )

    def Execute(self,event):
        if not settings[self.key]:
            message = _("Activate Full Balo?\n\nFull Balo segregates mods by groups, and then autosorts mods within those groups by alphabetical order. Full Balo is still in development and may have some rough edges.")
            if balt.askContinue(self.window,message,'bash.balo.full.continue',_('Balo Groups')):
                dialog = Mod_BaloGroups_Edit(self.window)
                dialog.ShowModal()
                dialog.Destroy()
            return
        else:
            settings[self.key] = False
            bosh.modInfos.fullBalo = False
            bosh.modInfos.refresh(doInfos=False)

#------------------------------------------------------------------------------
class Mods_DumpTranslator(Link):
    """Dumps new translation key file using existing key, value pairs."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Dump Translator'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        message = _("Generate Bash program translator file?\n\nThis function is for translating Bash itself (NOT mods) into non-English languages. For more info, see Internationalization section of Bash readme.")
        if not balt.askContinue(self.window,message,'bash.dumpTranslator.continue',_('Dump Translator')):
            return
        import locale
        language = locale.getlocale()[0].split('_',1)[0]
        outPath = bosh.dirs['mopy'].join('Data','NEW%s.txt' % (language,))
        outFile = outPath.open('w')
        #--Scan for keys and dump to
        keyCount = 0
        dumpedKeys = set()
        reKey = re.compile(r'_\([\'\"](.+?)[\'\"]\)')
        reTrans = bolt.reTrans
        for pyPath in (GPath(x+'.py') for x in ('bolt','balt','bush','bosh','bash','basher','bashmon','belt')):
            pyText = pyPath.open()
            for lineNum,line in enumerate(pyText):
                line = re.sub('#.*','',line)
                for key in reKey.findall(line):
                    key = reTrans.match(key).group(2)
                    if key in dumpedKeys: continue
                    outFile.write('=== %s, %d\n' % (pyPath.s,lineNum+1))
                    outFile.write(key+'\n>>>>\n')
                    value = _(key,False)
                    if value != key:
                        outFile.write(value)
                    outFile.write('\n')
                    dumpedKeys.add(key)
                    keyCount += 1
            pyText.close()
        outFile.close()
        balt.showOk(self.window,
            (_('%d translation keys written to Mopy\\Data\\%s.') % (keyCount,outPath.stail)),
            _('Dump Translator')+': '+outPath.stail)

#------------------------------------------------------------------------------
class Mods_ListMods(Link):
    """Copies list of mod files to clipboard."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_("List Mods..."))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        #--Get masters list
        text = bosh.modInfos.getModList()
        if (wx.TheClipboard.Open()):
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        balt.showLog(self.window,text,_("Active Mod Files"),asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class Mods_ListBashTags(Link):
    """Copies list of bash tags to clipboard."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_("List Bash Tags..."))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        #--Get masters list
        text = bosh.modInfos.getTagList()
        if (wx.TheClipboard.Open()):
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        balt.showLog(self.window,text,_("Bash Tags"),asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class Mods_LockTimes(Link):
    """Turn on resetMTimes feature."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Lock Times'),kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        menuItem.Check(bosh.modInfos.lockTimes)

    def Execute(self,event):
        lockTimes = not bosh.modInfos.lockTimes
        if not lockTimes: bosh.modInfos.mtimes.clear()
        settings['bosh.modInfos.resetMTimes'] = bosh.modInfos.lockTimes = lockTimes
        bosh.modInfos.refresh(doInfos=False)
        modList.RefreshUI()

#------------------------------------------------------------------------------
class Mods_OblivionVersion(Link):
    """Specify/set Oblivion version."""
    def __init__(self,key,setProfile=False):
        Link.__init__(self)
        self.key = key
        self.setProfile = setProfile

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,self.key,kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        menuItem.Enable(bosh.modInfos.voCurrent != None and self.key in bosh.modInfos.voAvailable)
        if bosh.modInfos.voCurrent == self.key: menuItem.Check()

    def Execute(self,event):
        """Handle selection."""
        if bosh.modInfos.voCurrent == self.key: return
        bosh.modInfos.setOblivionVersion(self.key)
        bosh.modInfos.refresh()
        modList.RefreshUI()
        if self.setProfile:
            bosh.saveInfos.profiles.setItem(bosh.saveInfos.localSave,'vOblivion',self.key)
        bashFrame.SetTitle()

#------------------------------------------------------------------------------
class Mods_Tes4ViewExpert(BoolLink):
    """Toggle Tes4Edit expert mode (when launched via Bash)."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Tes4Edit Expert'),
                                          'tes4View.iKnowWhatImDoing',
                                          )

#------------------------------------------------------------------------------
class Mods_BOSSDisableLockTimes(BoolLink):
    """Toggle Lock Times disabling when launching BOSS through Bash."""
    def __init__(self): BoolLink.__init__(self,
                                          _('BOSS Disable Lock Times'),
                                          'BOSS.ClearLockTimes',
                                          _("If selected, will temporarilly disable Bash's Lock Times when running BOSS through Bash.")
                                          )

#------------------------------------------------------------------------------
class Mods_BOSSShowUpdate(BoolLink):
    """Toggle Lock Times disabling when launching BOSS through Bash."""
    def __init__(self): BoolLink.__init__(self,
                                          _('Always Update BOSS Masterlist prior to running BOSS.'),
                                          'BOSS.AlwaysUpdate',
                                          _("If selected, will tell BOSS to update the masterlist before sorting the mods.")
                                          )

#------------------------------------------------------------------------------
class User_BackupSettings(Link):
    """Saves Bash's settings and user data.."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Backup Settings...'),help="Backup all of Wrye Bash's settings/data to an archive file.",kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)

    def Execute(self,event):
        BashFrame.SaveSettings(bashFrame)
        backup = barb.BackupSettings(bashFrame)
        try:
            if backup.PromptConfirm(): backup.Apply()
        except StateError:
            backup.WarnFailed()
        except barb.BackupCancelled:
            pass
        #end try
        backup = None

#------------------------------------------------------------------------------
class User_RestoreSettings(Link):
    """Saves Bash's settings and user data.."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Restore Settings...'),help="Restore all of Wrye Bash's settings/data from a backup archive file.",kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)

    def Execute(self,event):
        try:
            backup = barb.RestoreSettings(bashFrame)
            if backup.PromptConfirm(): backup.Apply()
        except barb.BackupCancelled: #cancelled
            pass
        #end try
        backup = None

#------------------------------------------------------------------------------
class User_SaveSettings(Link):
    """Saves Bash's settings and user data.."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Save Settings'),help="Save all of Wrye Bash's settings/data now.",kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)

    def Execute(self,event):
        BashFrame.SaveSettings(bashFrame)

#------------------------------------------------------------------------------
class Mods_UpdateInvalidator(Link):
    """Mod Replacers dialog."""
    def AppendToMenu(self,menu,window,data):
        """Append ref replacer items to menu."""
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Update Archive Invalidator'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        message = (_("Update ArchiveInvalidation.txt? This updates the file that forces the game engine to recognize replaced textures. Note that this feature is experimental and most probably somewhat incomplete. You may prefer to use another program to do AI.txt file updating."))
        if not balt.askContinue(self.window,message,'bash.updateAI.continue',_('ArchiveInvalidation.txt')):
            return
        bosh.ResourceReplacer.updateInvalidator()
        balt.showOk(self.window,"ArchiveInvalidation.txt updated.")

# Mod Links -------------------------------------------------------------------
#------------------------------------------------------------------------------
class Mod_ActorLevels_Export(Link):
    """Export actor levels from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('NPC Levels...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        message = (_("This command will export the level info for NPCs whose level is offset with respect to the PC. The exported file can be edited with most spreadsheet programs and then reimported.\n\nSee the Bash help file for more info."))
        if not balt.askContinue(self.window,message,'bash.actorLevels.export.continue',_('Export NPC Levels')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_NPC_Levels.csv')
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_('Export NPC levels to:'),textDir,textName, '*_NPC_Levels.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        progress = balt.Progress(_("Export Factions"))
        try:
            if CBash:
                actorLevels = bosh.CBash_ActorLevels()
            else:
                actorLevels = bosh.ActorLevels()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_("Reading %s.") % (fileName.s,))
                actorLevels.readFromMod(fileInfo)
            progress(0.8,_("Exporting to %s.") % (textName.s,))
            actorLevels.writeToText(textPath)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()

#------------------------------------------------------------------------------
class Mod_ActorLevels_Import(Link):
    """Imports actor levels from text file to mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('NPC Levels...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = (_("This command will import NPC level info from a previously exported file.\n\nSee the Bash help file for more info."))
        if not balt.askContinue(self.window,message,'bash.actorLevels.import.continue',_('Import NPC Levels')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_NPC_Levels.csv')
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_('Import NPC levels from:'),
            textDir, textName, '*_NPC_Levels.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != '.csv':
            balt.showError(self.window,_('Source file must be a _NPC_Levels.csv file.'))
            return
        #--Export
        progress = balt.Progress(_("Import NPC Levels"))
        changed = None
        try:
            if CBash:
                actorLevels = bosh.CBash_ActorLevels()
            else:
                actorLevels = bosh.ActorLevels()
            progress(0.1,_("Reading %s.") % (textName.s,))
            actorLevels.readFromText(textPath)
            progress(0.2,_("Applying to %s.") % (fileName.s,))
            changed = actorLevels.writeToMod(fileInfo)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()
        #--Log
        if not changed:
            balt.showOk(self.window,_("No relevant NPC levels to import."),_("Import NPC Levels"))
        else:
            buff = stringBuffer()
            buff.write('* %03d  %s\n' % (changed, fileName.s))
            balt.showLog(self.window,buff.getvalue(),_('Import NPC Levels'),icons=bashBlue)
#------------------------------------------------------------------------------
class Mod_AddMaster(Link):
    """Adds master."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Add Master...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data)==1)

    def Execute(self,event):
        message = _("WARNING! For advanced modders only! Adds specified master to list of masters, thus ceding ownership of new content of this mod to the new master. Useful for splitting mods into esm/esp pairs.")
        if not balt.askContinue(self.window,message,'bash.addMaster.continue',_('Add Master')):
            return
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        wildcard = _('Oblivion Masters')+' (*.esm;*.esp)|*.esm;*.esp'
        masterPath = balt.askOpen(self.window,_('Add master:'),fileInfo.dir, '', wildcard,mustExist=True)
        if not masterPath: return
        (dir,name) = masterPath.headTail
        if dir != fileInfo.dir:
            return balt.showError(self.window,
                _("File must be selected from Oblivion Data Files directory."))
        if name in fileInfo.header.masters:
            return balt.showError(self.window,_("%s is already a master!") % (name.s,))
        if name in bosh.modInfos:
            #--Avoid capitalization errors by getting the actual name from modinfos.
            name = bosh.modInfos[name].name
        fileInfo.header.masters.append(name)
        fileInfo.header.changed = True
        fileInfo.writeHeader()
        bosh.modInfos.refreshFile(fileInfo.name)
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class Mod_BaloGroups_Edit(wx.Dialog):
    """Dialog for editing Balo groups."""
    def __init__(self,parent):
        #--Data
        self.parent = parent
        self.groups = [list(x) for x in bosh.modInfos.getBaloGroups(True)]
        self.removed = set()
        #--GUI
        wx.Dialog.__init__(self,parent,-1,_("Balo Groups"),style=wx.CAPTION|wx.RESIZE_BORDER)
        #--List
        self.gList = wx.ListBox(self,-1,choices=self.GetItems(),style=wx.LB_SINGLE)
        self.gList.SetSizeHints(125,150)
        self.gList.Bind(wx.EVT_LISTBOX,self.DoSelect)
        #--Bounds
        self.gLowerBounds = spinCtrl(self,'-10',size=(15,15),min=-10,max=0,onSpin=self.OnSpin)
        self.gUpperBounds = spinCtrl(self,'10',size=(15,15),min=0,max=10, onSpin=self.OnSpin)
        self.gLowerBounds.SetSizeHints(35,-1)
        self.gUpperBounds.SetSizeHints(35,-1)
        #--Buttons
        self.gAdd = button(self,_('Add'),onClick=self.DoAdd)
        self.gRename = button(self,_('Rename'),onClick=self.DoRename)
        self.gRemove = button(self,_('Remove'),onClick=self.DoRemove)
        self.gMoveEarlier = button(self,_('Move Up'),onClick=self.DoMoveEarlier)
        self.gMoveLater = button(self,_('Move Down'),onClick=self.DoMoveLater)
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
                (hsbSizer((self,-1,_('Offsets')),
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
        newName = (balt.askText(self,message,title) or '').strip()
        if not newName: return None
        maValid = re.match('([a-zA-Z][ _a-zA-Z]+)',newName)
        if not maValid or maValid.group(1) != newName:
            showWarning(self,
                _("Group name must be letters, spaces, underscores only!"),title)
            return None
        elif newName in self.GetItems():
            showWarning(self,_("group %s already exists.") % (newName,),title)
            return None
        elif len(newName) >= 40:
            showWarning(self,_("Group names must be less than forty characters."),title)
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
            return '%s  %d : %d' % (group,lower,upper)

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
        if index == None:
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
        title = _("Add Balo Group")
        index = (self.gList.GetSelections() or (0,))[0]
        if index < 0 or index >= len(self.groups) - 2: return bell()
        #--Ask for and then check new name
        oldName = self.groups[index][0]
        message = _("Name of new group (spaces and letters only):")
        newName = self.AskNewName(message,title)
        if newName:
            self.groups.insert(index+1,['',0,0,0,0,newName])
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
        title = _("Rename Balo Group")
        index = (self.gList.GetSelections() or (0,))[0]
        if index < 0 or index >= len(self.groups): return bell()
        #--Ask for and then check new name
        oldName = self.groups[index][5]
        message = _("Rename %s to (spaces, letters and underscores only):") % (oldName,)
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

#------------------------------------------------------------------------------
class Mod_BaloGroups:
    """Select Balo group to use."""
    def __init__(self):
        """Initialize."""
        self.id_group = {}
        self.idList = ID_GROUPS

    def GetItems(self):
        items = self.labels[:]
        items.sort(key=lambda a: a.lower())
        return items

    def AppendToMenu(self,menu,window,data):
        """Append label list to menu."""
        if not settings.get('bash.balo.full'): return
        self.window = window
        self.data = data
        id_group = self.id_group
        menu.Append(self.idList.EDIT,_('Edit...'))
        setableMods = [GPath(x) for x in self.data if GPath(x) not in bosh.modInfos.autoHeaders]
        if setableMods:
            menu.AppendSeparator()
            ids = iter(self.idList)
            if len(setableMods) == 1:
                modGroup = bosh.modInfos.table.getItem(setableMods[0],'group')
            else:
                modGroup = None
            for group,lower,upper in bosh.modInfos.getBaloGroups():
                if lower == upper:
                    id = ids.next()
                    id_group[id] = group
                    menu.AppendCheckItem(id,group)
                    menu.Check(id,group == modGroup)
                else:
                    subMenu = wx.Menu()
                    for x in range(lower,upper+1):
                        offGroup = bosh.joinModGroup(group,x)
                        id = ids.next()
                        id_group[id] = offGroup
                        subMenu.AppendCheckItem(id,offGroup)
                        subMenu.Check(id,offGroup == modGroup)
                    menu.AppendMenu(-1,group,subMenu)
        #--Events
        wx.EVT_MENU(bashFrame,self.idList.EDIT,self.DoEdit)
        wx.EVT_MENU_RANGE(bashFrame,self.idList.BASE,self.idList.MAX,self.DoList)

    def DoList(self,event):
        """Handle selection of label."""
        label = self.id_group[event.GetId()]
        mod_group = bosh.modInfos.table.getColumn('group')
        for mod in self.data:
            if mod not in bosh.modInfos.autoHeaders:
                mod_group[mod] = label
        if bosh.modInfos.refresh(doInfos=False):
            modList.SortItems()
        self.window.RefreshUI()

    def DoEdit(self,event):
        """Show label editing dialog."""
        dialog = Mod_BaloGroups_Edit(self.window)
        dialog.ShowModal()
        dialog.Destroy()

#------------------------------------------------------------------------------
class Mod_AllowAllGhosting(Link):
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_("Allow Ghosting"))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        files = []
        for fileName in self.data:
            fileInfo = bosh.modInfos[fileName]
            allowGhosting = True
            bosh.modInfos.table.setItem(fileName,'allowGhosting',allowGhosting)
            toGhost = fileName not in bosh.modInfos.ordered
            oldGhost = fileInfo.isGhost
            if fileInfo.setGhost(toGhost) != oldGhost:
                files.append(fileName)
        self.window.RefreshUI(files)

#------------------------------------------------------------------------------
class Mod_ListBashTags(Link):
    """Copies list of bash tags to clipboard."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_("List Bash Tags..."))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        #--Get masters list
        files = []
        for fileName in self.data:
            files.append(bosh.modInfos[fileName])
        text = bosh.modInfos.getTagList(files)
        if (wx.TheClipboard.Open()):
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        balt.showLog(self.window,text,_("Bash Tags"),asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_AllowNoGhosting(Link):
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_("Disallow Ghosting"))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        files = []
        for fileName in self.data:
            fileInfo = bosh.modInfos[fileName]
            allowGhosting = False
            bosh.modInfos.table.setItem(fileName,'allowGhosting',allowGhosting)
            toGhost = False
            oldGhost = fileInfo.isGhost
            if fileInfo.setGhost(toGhost) != oldGhost:
                files.append(fileName)
        self.window.RefreshUI(files)

#------------------------------------------------------------------------------
class Mod_AllowInvertGhosting(Link):
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_("Invert Ghosting"))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        files = []
        for fileName in self.data:
            fileInfo = bosh.modInfos[fileName]
            allowGhosting = bosh.modInfos.table.getItem(fileName,'allowGhosting',True) ^ True
            bosh.modInfos.table.setItem(fileName,'allowGhosting',allowGhosting)
            toGhost = allowGhosting and fileName not in bosh.modInfos.ordered
            oldGhost = fileInfo.isGhost
            if fileInfo.setGhost(toGhost) != oldGhost:
                files.append(fileName)
        self.window.RefreshUI(files)

#------------------------------------------------------------------------------
class Mod_AllowGhosting(Link):
    """Toggles Ghostability."""

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        if len(data) == 1:
            menuItem = wx.MenuItem(menu,self.id,_("Don't Ghost"),kind=wx.ITEM_CHECK)
            menu.AppendItem(menuItem)
            self.allowGhosting = bosh.modInfos.table.getItem(data[0],'allowGhosting',True)
            menuItem.Check(not self.allowGhosting)
        else:
            subMenu = wx.Menu()
            menu.AppendMenu(-1,"Ghosting",subMenu)
            Mod_AllowAllGhosting().AppendToMenu(subMenu,window,data)
            Mod_AllowNoGhosting().AppendToMenu(subMenu,window,data)
            Mod_AllowInvertGhosting().AppendToMenu(subMenu,window,data)

    def Execute(self,event):
        fileName = self.data[0]
        fileInfo = bosh.modInfos[fileName]
        allowGhosting = self.allowGhosting ^ True
        bosh.modInfos.table.setItem(fileName,'allowGhosting',allowGhosting)
        toGhost = allowGhosting and fileName not in bosh.modInfos.ordered
        oldGhost = fileInfo.isGhost
        if fileInfo.setGhost(toGhost) != oldGhost:
            self.window.RefreshUI(fileName)

#------------------------------------------------------------------------------
class Mod_SkipDirtyCheckAll(Link):
    def __init__(self, bSkip):
        Link.__init__(self)
        self.skip = bSkip

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        if self.skip:
            menuItem = wx.MenuItem(menu,self.id,_("Don't scan for dirty edits"))
        else:
            menuItem = wx.MenuItem(menu,self.id,_("Scan for dirty edits"))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        for fileName in self.data:
            fileInfo = bosh.modInfos[fileName]
            bosh.modInfos.table.setItem(fileName,'ignoreDirty',self.skip)
        self.window.RefreshUI(self.data)

#------------------------------------------------------------------------------
class Mod_SkipDirtyCheckInvert(Link):
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_("Invert dirty edit scanning"))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        for fileName in self.data:
            fileInfo = bosh.modInfos[fileName]
            ignoreDiry = bosh.modInfos.table.getItem(fileName,'ignoreDirty',False) ^ True
            bosh.modInfos.table.setItem(fileName,'ignoreDirty',ignoreDiry)
        self.window.RefreshUI(files)

#------------------------------------------------------------------------------
class Mod_SkipDirtyCheck(Link):
    """Toggles scanning for dirty mods on a per-mod basis."""

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        if len(data) == 1:
            menuItem = wx.MenuItem(menu,self.id,_("Don't scan for dirty edits (requires BOSS 1.7+)"),kind=wx.ITEM_CHECK)
            menu.AppendItem(menuItem)
            self.ignoreDirty = bosh.modInfos.table.getItem(data[0],'ignoreDirty',False)
            menuItem.Check(self.ignoreDirty)
        else:
            subMenu = wx.Menu()
            menu.AppendMenu(-1,_("Dirty edit scanning"),subMenu)
            Mod_SkipDirtyCheckAll(True).AppendToMenu(subMenu,window,data)
            Mod_SkipDirtyCheckAll(False).AppendToMenu(subMenu,window,data)
            Mod_SkipDirtyCheckInvert().AppendToMenu(subMenu,window,data)

    def Execute(self,event):
        fileName = self.data[0]
        fileInfo = bosh.modInfos[fileName]
        self.ignoreDirty ^= True
        bosh.modInfos.table.setItem(fileName,'ignoreDirty',self.ignoreDirty)
        self.window.RefreshUI(fileName)

#------------------------------------------------------------------------------
class Mod_CleanMod(Link):
    """Fix fog on selected csll."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Nvidia Fog Fix'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        message = _("Apply Nvidia fog fix. This modify fog values in interior cells to avoid the Nvidia black screen bug.")
        if not balt.askContinue(self.window,message,'bash.cleanMod.continue',
            _('Nvidia Fog Fix')):
            return
        progress = balt.Progress(_("Nvidia Fog Fix"))
        progress.setFull(len(self.data))
        try:
            fixed = []
            for index,fileName in enumerate(map(GPath,self.data)):
                if fileName == 'Oblivion.esm': continue
                progress(index,_("Scanning %s.") % (fileName.s,))
                fileInfo = bosh.modInfos[fileName]
                cleanMod = bosh.CleanMod(fileInfo)
                cleanMod.clean(SubProgress(progress,index,index+1))
                if cleanMod.fixedCells:
                    fixed.append('* %4d %s' % (len(cleanMod.fixedCells),fileName.s))
            progress.Destroy()
            if fixed:
                message = _("===Cells Fixed:\n")+('\n'.join(fixed))
                balt.showWryeLog(self.window,message,_('Nvidia Fog Fix'),icons=bashBlue)
            else:
                message = _("No changes required.")
                balt.showOk(self.window,message,_('Nvidia Fog Fix'))
        finally:
            progress = progress.Destroy()

#------------------------------------------------------------------------------
class Mod_CreateBlank(Link):
    """Create a duplicate of the file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('New Mod...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) == 1)

    def Execute(self,event):
        data = self.data
        fileName = GPath(data[0])
        fileInfos = self.window.data
        fileInfo = fileInfos[fileName]
        count = 0
        newName = GPath('New Mod.esp')
        while newName in fileInfos:
            count += 1
            newName = GPath('New Mod %d.esp' % (count,))
        newInfo = bosh.ModInfo(fileInfo.dir,newName)
        newTime = fileInfo.mtime + 20
        newInfo.mtime = bosh.modInfos.getFreeTime(newTime,newTime)
        newFile = bosh.ModFile(newInfo,bosh.LoadFactory(True))
        newFile.tes4.masters = [GPath('Oblivion.esm')]
        newFile.safeSave()
        mod_group = bosh.modInfos.table.getColumn('group')
        mod_group[newName] = mod_group.get(fileName,'')
        bosh.modInfos.refresh()
        self.window.RefreshUI(detail=newName)

#------------------------------------------------------------------------------
class Mod_FactionRelations_Export(Link):
    """Export faction relations from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Relations...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_Relations.csv')
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_('Export faction relations to:'),textDir,textName, '*Relations.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        progress = balt.Progress(_("Export Relations"))
        try:
            if not CBash:
                factionRelations = bosh.FactionRelations()
            else:
                factionRelations = bosh.CBash_FactionRelations()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_("Reading %s.") % (fileName.s,))
                factionRelations.readFromMod(fileInfo)
            progress(0.8,_("Exporting to %s.") % (textName.s,))
            factionRelations.writeToText(textPath)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()

#------------------------------------------------------------------------------
class Mod_FactionRelations_Import(Link):
    """Imports faction relations from text file to mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Relations...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = (_("This command will import faction relation info from a previously exported file.\n\nSee the Bash help file for more info."))
        if not balt.askContinue(self.window,message,'bash.factionRelations.import.continue',_('Import Relations')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_Relations.csv')
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_('Import faction relations from:'),
            textDir, textName, '*_Relations.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != '.csv':
            balt.showError(self.window,_('Source file must be a _Relations.csv file.'))
            return
        #--Export
        progress = balt.Progress(_("Import Relations"))
        changed = None
        try:
            if not CBash:
                factionRelations = bosh.FactionRelations()
            else:
                factionRelations = bosh.CBash_FactionRelations()
            progress(0.1,_("Reading %s.") % (textName.s,))
            factionRelations.readFromText(textPath)
            progress(0.2,_("Applying to %s.") % (fileName.s,))
            changed = factionRelations.writeToMod(fileInfo)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()
        #--Log
        if not changed:
            balt.showOk(self.window,_("No relevant faction relations to import."),_("Import Relations"))
        else:
            buff = stringBuffer()
            buff.write('* %03d  %s\n' % (changed, fileName.s))
            balt.showLog(self.window,buff.getvalue(),_('Import Relations'),icons=bashBlue)
#------------------------------------------------------------------------------
class Mod_Factions_Export(Link):
    """Export factions from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Factions...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_Factions.csv')
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_('Export factions to:'),textDir,textName, '*Factions.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        progress = balt.Progress(_("Export Factions"))
        try:
            if CBash:
                actorFactions = bosh.CBash_ActorFactions()
            else:
                actorFactions = bosh.ActorFactions()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_("Reading %s.") % (fileName.s,))
                actorFactions.readFromMod(fileInfo)
            progress(0.8,_("Exporting to %s.") % (textName.s,))
            actorFactions.writeToText(textPath)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()

#------------------------------------------------------------------------------
class Mod_Factions_Import(Link):
    """Imports factions from text file to mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Factions...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = (_("This command will import faction ranks from a previously exported file.\n\nSee the Bash help file for more info."))
        if not balt.askContinue(self.window,message,'bash.factionRanks.import.continue',_('Import Factions')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_Factions.csv')
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_('Import Factions from:'),
            textDir, textName, '*_Factions.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != '.csv':
            balt.showError(self.window,_('Source file must be a _Factions.csv file.'))
            return
        #--Export
        progress = balt.Progress(_("Import Factions"))
        changed = None
        try:
            if CBash:
                actorFactions = bosh.CBash_ActorFactions()
            else:
                actorFactions = bosh.ActorFactions()
            progress(0.1,_("Reading %s.") % (textName.s,))
            actorFactions.readFromText(textPath)
            progress(0.2,_("Applying to %s.") % (fileName.s,))
            changed = actorFactions.writeToMod(fileInfo)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()
        #--Log
        if not changed:
            balt.showOk(self.window,_("No relevant faction ranks to import."),_("Import Factions"))
        else:
            buff = stringBuffer()
            for groupName in sorted(changed):
                buff.write('* %s : %03d  %s\n' % (groupName, changed[groupName], fileName.s))
            balt.showLog(self.window,buff.getvalue(),_('Import Factions'),icons=bashBlue)
#------------------------------------------------------------------------------
class Mod_MarkLevelers(Link):
    """Marks (tags) selected mods as Delevs and/or Relevs according to Leveled Lists.csv."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Mark Levelers...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(data))

    def Execute(self,event):
        message = _('Obsolete. Mods are now automatically tagged when possible.')
        balt.showInfo(self.window,message,_('Mark Levelers'))

#------------------------------------------------------------------------------
class Mod_MarkMergeable(Link):
    """Returns true if can act as patch mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Mark Mergeable...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(data))

    def Execute(self,event):
        yes,no = [],[]
        mod_mergeInfo = bosh.modInfos.table.getColumn('mergeInfo')
        for fileName in map(GPath,self.data):
            if fileName in ('Oblivion.esm','Oblivion_1.1.esm'): continue
            fileInfo = bosh.modInfos[fileName]
            if not CBash:
                canMerge = bosh.PatchFile.modIsMergeable(fileInfo)
            else:
                canMerge = bosh.CBash_PatchFile.modIsMergeable(fileInfo)
            if canMerge == True:
                mod_mergeInfo[fileName] = (fileInfo.size,True)
                yes.append(fileName)
            else:
                if canMerge == "\n.    Has 'NoMerge' tag.":
                    mod_mergeInfo[fileName] = (fileInfo.size,True)
                else:
                    mod_mergeInfo[fileName] = (fileInfo.size,False)
                no.append("%s:%s" % (fileName.s,canMerge))
        message = ''
        if yes:
            message += _('=== Mergeable\n* ') + '\n\n* '.join(x.s for x in yes)
        if yes and no:
            message += '\n\n'
        if no:
            message += _('=== Not Mergeable\n* ') + '\n\n* '.join(no)
        self.window.RefreshUI(yes)
        self.window.RefreshUI(no)
        if message != '':
            balt.showWryeLog(self.window,message,_('Mark Mergeable'),icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_CopyToEsmp(Link):
    """Create an esp(esm) copy of selected esm(esp)."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        fileInfo = bosh.modInfos[data[0]]
        isEsm = fileInfo.isEsm()
        self.label = (_('Copy to Esm'),_('Copy to Esp'))[fileInfo.isEsm()]
        menuItem = wx.MenuItem(menu,self.id,self.label)
        menu.AppendItem(menuItem)
        for item in data:
            fileInfo = bosh.modInfos[item]
            if fileInfo.isInvertedMod() or fileInfo.isEsm() != isEsm:
                menuItem.Enable(False)
                return

    def Execute(self,event):
        for item in self.data:
            fileInfo = bosh.modInfos[item]
            newType = (fileInfo.isEsm() and 'esp') or 'esm'
            modsDir = fileInfo.dir
            curName = fileInfo.name
            newName = curName.root+'.'+newType
            #--Replace existing file?
            if modsDir.join(newName).exists():
                if not balt.askYes(self.window,_('Replace existing %s?') % (newName.s,),self.label):
                    continue
                bosh.modInfos[newName].makeBackup()
            #--New Time
            modInfos = bosh.modInfos
            timeSource = (curName,newName)[newName in modInfos]
            newTime = modInfos[timeSource].mtime
            #--Copy, set type, update mtime.
            modInfos.copy(curName,modsDir,newName,newTime)
            modInfos.table.copyRow(curName,newName)
            newInfo = modInfos[newName]
            newInfo.setType(newType)
            newInfo.setmtime(newTime)
            #--Repopulate
            self.window.RefreshUI(detail=newName)

#------------------------------------------------------------------------------
class Mod_Face_Import(Link):
    """Imports a face from a save to an esp."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Face...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) == 1)

    def Execute(self,event):
        #--Select source face file
        srcDir = bosh.saveInfos.dir
        wildcard = _('Oblivion Files')+' (*.ess;*.esr)|*.ess;*.esr'
        #--File dialog
        srcPath = balt.askOpen(self.window,'Face Source:',srcDir, '', wildcard,mustExist=True)
        if not srcPath: return
        #--Get face
        srcDir,srcName = srcPath.headTail
        srcInfo = bosh.SaveInfo(srcDir,srcName)
        srcFace = bosh.PCFaces.save_getFace(srcInfo)
        #--Save Face
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        npc = bosh.PCFaces.mod_addFace(fileInfo,srcFace)
        #--Save Face picture?
        imagePath = bosh.modInfos.dir.join('Docs','Images',npc.eid+'.jpg')
        if not imagePath.exists():
            srcInfo.getHeader()
            width,height,data = srcInfo.header.image
            image = wx.EmptyImage(width,height)
            image.SetData(data)
            imagePath.head.makedirs()
            image.SaveFile(imagePath.s,wx.BITMAP_TYPE_JPEG)
        self.window.RefreshUI()
        balt.showOk(self.window,_('Imported face to: %s') % (npc.eid,),fileName.s)

#------------------------------------------------------------------------------
class Mod_FlipMasters(Link):
    """Swaps masters between esp and esm versions."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Esmify Masters'))
        menu.AppendItem(menuItem)
        #--FileInfo
        fileInfo = self.fileInfo = window.data[data[0]]
        menuItem.Enable(False)
        self.toEsp = False
        if len(data) == 1 and len(fileInfo.header.masters) > 1:
            espMasters = [master for master in fileInfo.header.masters if bosh.reEspExt.search(master.s)]
            if not espMasters: return
            for masterName in espMasters:
                masterInfo = bosh.modInfos.get(GPath(masterName),None)
                if masterInfo and masterInfo.isInvertedMod():
                    menuItem.SetText(_('Espify Masters'))
                    self.toEsm = False
                    break
            else:
                self.toEsm = True
            menuItem.Enable(True)

    def Execute(self,event):
        message = _("WARNING! For advanced modders only! Flips esp/esm bit of esp masters to convert them to/from esm state. Useful for building/analyzing esp mastered mods.")
        if not balt.askContinue(self.window,message,'bash.flipMasters.continue'):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        updated = [fileName]
        espMasters = [GPath(master) for master in fileInfo.header.masters
            if bosh.reEspExt.search(master.s)]
        for masterPath in espMasters:
            masterInfo = bosh.modInfos.get(masterPath,None)
            if masterInfo:
                masterInfo.header.flags1.esm = self.toEsm
                masterInfo.writeHeader()
                updated.append(masterPath)
        self.window.RefreshUI(updated,fileName)

#------------------------------------------------------------------------------
class Mod_FlipSelf(Link):
    """Flip an esp(esm) to an esm(esp)."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        fileInfo = bosh.modInfos[data[0]]
        isEsm = fileInfo.isEsm()
        self.label = (_('Esmify Self'),_('Espify Self'))[isEsm]
        menuItem = wx.MenuItem(menu,self.id,self.label)
        menu.AppendItem(menuItem)
        for item in data:
            fileInfo = bosh.modInfos[item]
            if fileInfo.isEsm() != isEsm or not item.cext[-1] == 'p':
                menuItem.Enable(False)
                return

    def Execute(self,event):
        message = _('WARNING! For advanced modders only!\n\nThis command flips an internal bit in the mod, converting an esp to an esm and vice versa. Note that it is this bit and NOT the file extension that determines the esp/esm state of the mod.')
        if not balt.askContinue(self.window,message,'bash.flipToEsmp.continue',_('Flip to Esm')):
            return
        for item in self.data:
            fileInfo = bosh.modInfos[item]
            header = fileInfo.header
            header.flags1.esm = not header.flags1.esm
            fileInfo.writeHeader()
            #--Repopulate
            self.window.RefreshUI(detail=fileInfo.name)


#------------------------------------------------------------------------------
class Mod_LabelsData(balt.ListEditorData):
    """Data capsule for label editing dialog."""
    def __init__(self,parent,strings):
        """Initialize."""
        #--Strings
        self.column = strings.column
        self.setKey = strings.setKey
        self.addPrompt = strings.addPrompt
        #--Key/type
        self.data = settings[self.setKey]
        #--GUI
        balt.ListEditorData.__init__(self,parent)
        self.showAdd = True
        self.showRename = True
        self.showRemove = True

    def getItemList(self):
        """Returns load list keys in alpha order."""
        return sorted(self.data,key=lambda a: a.lower())

    def add(self):
        """Adds a new group."""
        #--Name Dialog
        #--Dialog
        dialog = wx.TextEntryDialog(self.parent,self.addPrompt)
        result = dialog.ShowModal()
        #--Okay?
        if result != wx.ID_OK:
            dialog.Destroy()
            return
        newName = dialog.GetValue()
        dialog.Destroy()
        if newName in self.data:
            balt.showError(self.parent,_('Name must be unique.'))
            return False
        elif len(newName) == 0 or len(newName) > 64:
            balt.showError(self.parent,
                _('Name must be between 1 and 64 characters long.'))
            return False
        settings.setChanged(self.setKey)
        self.data.append(newName)
        self.data.sort()
        return newName

    def rename(self,oldName,newName):
        """Renames oldName to newName."""
        #--Right length?
        if len(newName) == 0 or len(newName) > 64:
            balt.showError(self.parent,
                _('Name must be between 1 and 64 characters long.'))
            return False
        #--Rename
        settings.setChanged(self.setKey)
        self.data.remove(oldName)
        self.data.append(newName)
        self.data.sort()
        #--Edit table entries.
        colGroup = bosh.modInfos.table.getColumn(self.column)
        for fileName in colGroup.keys():
            if colGroup[fileName] == oldName:
                colGroup[fileName] = newName
        self.parent.PopulateItems()
        #--Done
        return newName

    def remove(self,item):
        """Removes group."""
        settings.setChanged(self.setKey)
        self.data.remove(item)
        #--Edit table entries.
        colGroup = bosh.modInfos.table.getColumn(self.column)
        for fileName in colGroup.keys():
            if colGroup[fileName] == item:
                del colGroup[fileName]
        self.parent.PopulateItems()
        #--Done
        return True

#------------------------------------------------------------------------------
class Mod_Labels:
    """Add mod label links."""
    def __init__(self):
        """Initialize."""
        self.labels = settings[self.setKey]

    def GetItems(self):
        items = self.labels[:]
        items.sort(key=lambda a: a.lower())
        return items

    def AppendToMenu(self,menu,window,data):
        """Append label list to menu."""
        self.window = window
        self.data = data
        menu.Append(self.idList.EDIT,self.editMenu)
        menu.AppendSeparator()
        menu.Append(self.idList.NONE,_('None'))
        for id,item in zip(self.idList,self.GetItems()):
            menu.Append(id,item)
        #--Events
        wx.EVT_MENU(bashFrame,self.idList.EDIT,self.DoEdit)
        wx.EVT_MENU(bashFrame,self.idList.NONE,self.DoNone)
        wx.EVT_MENU_RANGE(bashFrame,self.idList.BASE,self.idList.MAX,self.DoList)

    def DoNone(self,event):
        """Handle selection of None."""
        fileLabels = bosh.modInfos.table.getColumn(self.column)
        for fileName in self.data:
            fileLabels[fileName] = ''
        self.window.PopulateItems()

    def DoList(self,event):
        """Handle selection of label."""
        label = self.GetItems()[event.GetId()-self.idList.BASE]
        fileLabels = bosh.modInfos.table.getColumn(self.column)
        for fileName in self.data:
            fileLabels[fileName] = label
        if isinstance(self,Mod_Groups) and bosh.modInfos.refresh(doInfos=False):
            modList.SortItems()
        self.window.RefreshUI()

    def DoEdit(self,event):
        """Show label editing dialog."""
        data = Mod_LabelsData(self.window,self)
        dialog = balt.ListEditor(self.window,-1,self.editWindow,data)
        dialog.ShowModal()
        dialog.Destroy()

#------------------------------------------------------------------------------
class Mod_Groups(Mod_Labels):
    """Add mod group links."""
    def __init__(self):
        """Initialize."""
        self.column     = 'group'
        self.setKey     = 'bash.mods.groups'
        self.editMenu   = _('Edit Groups...')
        self.editWindow = _('Groups')
        self.addPrompt  = _('Add group:')
        self.idList     = ID_GROUPS
        Mod_Labels.__init__(self)

    def AppendToMenu(self,menu,window,data):
        """Append label list to menu."""
        #--For group labels
        if not settings.get('bash.balo.full'):
            Mod_Labels.AppendToMenu(self,menu,window,data)

#------------------------------------------------------------------------------
class Mod_Groups_Export(Link):
    """Export mod groups to text file."""
    def AppendToMenu(self,menu,window,data):
        data = bosh.ModGroups.filter(data)
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Groups...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = 'My_Groups.csv'
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_('Export groups to:'),textDir,textName, '*Groups.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        modGroups = bosh.ModGroups()
        modGroups.readFromModInfos(self.data)
        modGroups.writeToText(textPath)
        balt.showOk(self.window,
            _("Exported %d mod/groups.") % (len(modGroups.mod_group),),
            _("Export Groups"))

#------------------------------------------------------------------------------
class Mod_Groups_Import(Link):
    """Import editor ids from text file or other mod."""
    def AppendToMenu(self,menu,window,data):
        data = bosh.ModGroups.filter(data)
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Groups...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        message = _("Import groups from a text file. Any mods that are moved into new auto-sorted groups will be immediately reordered.")
        if not balt.askContinue(self.window,message,'bash.groups.import.continue',
            _('Import Groups')):
            return
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_('Import names from:'),textDir,
            '', '*Groups.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        if textName.cext != '.csv':
            balt.showError(self.window,_('Source file must be a csv file.'))
            return
        #--Import
        modGroups = bosh.ModGroups()
        modGroups.readFromText(textPath)
        changed = modGroups.writeToModInfos(self.data)
        bosh.modInfos.refresh()
        self.window.RefreshUI()
        balt.showOk(self.window,
            _("Imported %d mod/groups (%d changed).") % (len(modGroups.mod_group),changed),
            _("Import Groups"))

#------------------------------------------------------------------------------
class Mod_EditorIds_Export(Link):
    """Export editor ids from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Editor Ids...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_Eids.csv')
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_('Export eids to:'),textDir,textName, '*Eids.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        progress = balt.Progress(_("Export Editor Ids"))
        try:
            if CBash:
                editorIds = bosh.CBash_EditorIds()
            else:
                editorIds = bosh.EditorIds()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_("Reading %s.") % (fileName.s,))
                editorIds.readFromMod(fileInfo)
            progress(0.8,_("Exporting to %s.") % (textName.s,))
            editorIds.writeToText(textPath)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()

#------------------------------------------------------------------------------
class Mod_EditorIds_Import(Link):
    """Import editor ids from text file or other mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Editor Ids...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = (_("Import editor ids from a text file. This will replace existing ids and is not reversible!"))
        if not balt.askContinue(self.window,message,'bash.editorIds.import.continue',
            _('Import Editor Ids')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_Eids.csv')
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_('Import names from:'),textDir,
            textName, '*Eids.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        if textName.cext != '.csv':
            balt.showError(self.window,_('Source file must be a csv file.'))
            return
        #--Export
        progress = balt.Progress(_("Import Editor Ids"))
        changed = None
        try:
            if CBash:
                editorIds = bosh.CBash_EditorIds()
            else:
                editorIds = bosh.EditorIds()
            progress(0.1,_("Reading %s.") % (textName.s,))
            editorIds.readFromText(textPath)
            progress(0.2,_("Applying to %s.") % (fileName.s,))
            changed = editorIds.writeToMod(fileInfo)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()
        #--Log
        if not changed:
            balt.showOk(self.window,_("No changes required."))
        else:
            buff = stringBuffer()
            format = '%s >> %s\n'
            for old_new in sorted(changed):
                buff.write(format % old_new)
            balt.showLog(self.window,buff.getvalue(),_('Objects Changed'),icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_DecompileAll(Link):
    """Removes effects of a "recompile all" on the mod."""

    def AppendToMenu(self,menu,window,data):
        """Append link to a menu."""
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Decompile All'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data) != 1 or (self.data[0] != 'Oblivion.esm' and self.data[0] != 'Oblivion_1.1.esm'))


    def Execute(self,event):
        message = _("This command will remove the effects of a 'compile all' by removing all scripts whose texts appear to be identical to the version that they override.")
        if not balt.askContinue(self.window,message,'bash.decompileAll.continue',_('Decompile All')):
            return
        for item in self.data:
            fileName = GPath(item)
            if item == 'Oblivion.esm' or item == 'Oblivion_1.1.esm':
                balt.showWarning(self.window,_("Skipping %s") % fileName.s,_('Decompile All'))
                continue
            fileInfo = bosh.modInfos[fileName]
            loadFactory = bosh.LoadFactory(True,bosh.MreScpt)
            modFile = bosh.ModFile(fileInfo,loadFactory)
            modFile.load(True)
            badGenericLore = False
            removed = []
            id_text = {}
            if modFile.SCPT.getNumRecords(False):
                loadFactory = bosh.LoadFactory(False,bosh.MreScpt)
                for master in modFile.tes4.masters:
                    masterFile = bosh.ModFile(bosh.modInfos[master],loadFactory)
                    masterFile.load(True)
                    mapper = masterFile.getLongMapper()
                    for record in masterFile.SCPT.getActiveRecords():
                        id_text[mapper(record.fid)] = record.scriptText
                mapper = modFile.getLongMapper()
                newRecords = []
                for record in modFile.SCPT.records:
                    fid = mapper(record.fid)
                    #--Special handling for genericLoreScript
                    if (fid in id_text and record.fid == 0x00025811 and
                        record.compiledSize == 4 and record.lastIndex == 0):
                        removed.append(record.eid)
                        badGenericLore = True
                    elif fid in id_text and id_text[fid] == record.scriptText:
                        removed.append(record.eid)
                    else:
                        newRecords.append(record)
                modFile.SCPT.records = newRecords
                modFile.SCPT.setChanged()
            if len(removed) >= 50 or badGenericLore:
                modFile.safeSave()
                balt.showOk(self.window,_("Scripts removed: %d.\nScripts remaining: %d") % (len(removed),len(modFile.SCPT.records)),fileName.s)
            elif removed:
                balt.showOk(self.window,_("Only %d scripts were identical. This is probably intentional, so no changes have been made.") % len(removed),fileName.s)
            else:
                balt.showOk(self.window,_("No changes required."),fileName.s)

#------------------------------------------------------------------------------
class Mod_Fids_Replace(Link):
    """Replace fids according to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Form IDs...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = _("For advanced modders only! Systematically replaces one set of Form Ids with another in npcs, creatures, containers and leveled lists according to a Replacers.csv file.")
        if not balt.askContinue(self.window,message,'bash.formIds.replace.continue',
            _('Import Form IDs')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_('Form ID mapper file:'),textDir,
            '', '*Formids.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        if textName.cext != '.csv':
            balt.showError(self.window,_('Source file must be a csv file.'))
            return
        #--Export
        progress = balt.Progress(_("Import Form IDs"))
        changed = None
        try:
            if not CBash:
                replacer = bosh.FidReplacer()
            else:
                replacer = bosh.CBash_FidReplacer()
            progress(0.1,_("Reading %s.") % (textName.s,))
            replacer.readFromText(textPath)
            progress(0.2,_("Applying to %s.") % (fileName.s,))
            changed = replacer.updateMod(fileInfo)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()
        #--Log
        if not changed:
            balt.showOk(self.window,_("No changes required."))
        else:
            balt.showLog(self.window,changed,_('Objects Changed'),icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_FullNames_Export(Link):
    """Export full names from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Names...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_Names.csv')
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_('Export names to:'),
            textDir,textName, '*Names.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        progress = balt.Progress(_("Export Names"))
        try:
            if not CBash:
                fullNames = bosh.FullNames()
            else:
                fullNames = bosh.CBash_FullNames()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_("Reading %s.") % (fileName.s,))
                fullNames.readFromMod(fileInfo)
            progress(0.8,_("Exporting to %s.") % (textName.s,))
            fullNames.writeToText(textPath)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()

#------------------------------------------------------------------------------
class Mod_FullNames_Import(Link):
    """Import full names from text file or other mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Names...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = (_("Import record names from a text file. This will replace existing names and is not reversible!"))
        if not balt.askContinue(self.window,message,'bash.fullNames.import.continue',
            _('Import Names')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_Names.csv')
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_('Import names from:'),
            textDir,textName, 'Mod/Text File|*Names.csv;*.esp;*.esm',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext not in ('.esp','.esm','.csv'):
            balt.showError(self.window,_('Source file must be mod (.esp or .esm) or csv file.'))
            return
        #--Export
        progress = balt.Progress(_("Import Names"))
        renamed = None
        try:
            if not CBash:
                fullNames = bosh.FullNames()
            else:
                fullNames = bosh.CBash_FullNames()
            progress(0.1,_("Reading %s.") % (textName.s,))
            if ext == '.csv':
                fullNames.readFromText(textPath)
            else:
                srcInfo = bosh.ModInfo(textDir,textName)
                fullNames.readFromMod(srcInfo)
            progress(0.2,_("Applying to %s.") % (fileName.s,))
            renamed = fullNames.writeToMod(fileInfo)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()
        #--Log
        if not renamed:
            balt.showOk(self.window,_("No changes required."))
        else:
            buff = stringBuffer()
            format = '%s:   %s >> %s\n'
            #buff.write(format % (_('Editor Id'),_('Name')))
            for eid in sorted(renamed.keys()):
                full,newFull = renamed[eid]
                buff.write(format % (eid,full,newFull))
            balt.showLog(self.window,buff.getvalue(),_('Objects Renamed'),icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_Patch_Update(Link):
    """Updates a Bashed Patch."""
    def AppendToMenu(self,menu,window,data):
        """Append link to a menu."""
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Rebuild Patch...'))
        menu.AppendItem(menuItem)
        enable = (len(self.data) == 1 and
            bosh.modInfos[self.data[0]].header.author in ('BASHED PATCH','BASHED LISTS'))
        menuItem.Enable(enable)

    def Execute(self,event):
        """Handle activation event."""
        wx.BeginBusyCursor() # just to show users that it hasn't stalled but is doing stuff.
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        if not bosh.modInfos.ordered:
            balt.showWarning(self.window,_("That which does not exist cannot be patched.\nLoad some mods and try again."),_("Existential Error"))
            return
        if not CBash:
            bosh.PatchFile.patchTime = fileInfo.mtime
        else:
            bosh.CBash_PatchFile.patchTime = fileInfo.mtime
            nullProgress = bolt.Progress()
            bosh.modInfos.rescanMergeable(bosh.modInfos.data,nullProgress)
            modList.RefreshUI()
        message = ""
        ActivePriortoPatch = [x for x in bosh.modInfos.ordered if bosh.modInfos[x].mtime < fileInfo.mtime]
        unfiltered = [x for x in ActivePriortoPatch if 'Filter' in bosh.modInfos[x].getBashTags()]
        merge = [x for x in ActivePriortoPatch if 'NoMerge' not in bosh.modInfos[x].getBashTags() and x in bosh.modInfos.mergeable]
        noMerge = [x for x in ActivePriortoPatch if 'NoMerge' in bosh.modInfos[x].getBashTags() and x in bosh.modInfos.mergeable]
        deactivate = [x for x in ActivePriortoPatch if 'Deactivate' in bosh.modInfos[x].getBashTags() and not 'Filter' in bosh.modInfos[x].getBashTags()]
        if deactivate: message += _("The following mods are tagged 'Deactivate'. These should be deactivated before building the patch, and then imported into the patch during build.\n*%s") % ('\n* '.join(x.s for x in deactivate)) + '\n\n'
        if unfiltered: message += _("The following mods are tagged 'Filter'. These should be deactivated before building the patch, and then merged into the patch during build.\n*%s") % ('\n* '.join(x.s for x in unfiltered)) + '\n\n'
        if merge: message += _("The following mods are mergeable. While it is not important to Wrye Bash functionality or the end contents of the bashed patch, it is suggest that they be deactivated and merged into the patch; this (helps) avoid the  Oblivion maximum esp/m limit.\n*%s") % ('\n* '.join(x.s for x in merge)) + '\n\n'
        if noMerge: message += _("The following mods are tagged 'NoMerge'. These should be deactivated before building the patch and imported according to tag(s), and preferences.\n*%s") % ('\n* '.join(x.s for x in noMerge)) + '\n\n'
        wx.EndBusyCursor()
        if message:
            message += 'Automatically deactivate those mods now?'
            if balt.showLog(self.window,message,_('Deactivate Suggested Mods?'),icons=bashBlue,question=True):
                wx.BeginBusyCursor()
                if deactivate:
                    for mod in deactivate:
                        bosh.modInfos.unselect(mod,False)
                if unfiltered:
                    for mod in unfiltered:
                        bosh.modInfos.unselect(mod,False)
                if merge:
                    for mod in merge:
                        bosh.modInfos.unselect(mod,False)
                if noMerge:
                    for mod in noMerge:
                        bosh.modInfos.unselect(mod,False)
                bosh.modInfos.refreshInfoLists()
                bosh.modInfos.plugins.save()
                self.window.RefreshUI(detail=fileName)
                wx.EndBusyCursor()
        previousMods = set()
        text = ''
        for mod in bosh.modInfos.ordered:
            if mod == fileName: break
            for master in bosh.modInfos[mod].header.masters:
                if master not in bosh.modInfos.ordered:
                    label = _('MISSING MASTER')
                elif master not in previousMods:
                    label = _('DELINQUENT MASTER')
                else:
                    label = ''
                if label:
                    text += '* '+mod.s+'\n'
                    text += '    %s: %s\n' % (label,master.s)
            previousMods.add(mod)
        if text:
            warning = balt.askYes(self.window,(_('WARNING!\nThe following mod(s) have master file error(s):\n%sPlease adjust your load order to rectify those probem(s) before continuing. However you can still proceed if you want to. Proceed?') % (text)),_("Missing or Delinquent Master Errors"))
            if not warning:
                return
        patchDialog = PatchDialog(self.window,fileInfo)
        patchDialog.ShowModal()
        self.window.RefreshUI(detail=fileName)
        # save data to disc in case of later improper shutdown leaving the user guessing as to what options they built the patch with
        BashFrame.SaveSettings(bashFrame)

#------------------------------------------------------------------------------
class Mod_Ratings(Mod_Labels):
    """Add mod rating links."""
    def __init__(self):
        """Initialize."""
        self.column     = 'rating'
        self.setKey     = 'bash.mods.ratings'
        self.editMenu   = _('Edit Ratings...')
        self.editWindow = _('Ratings')
        self.addPrompt  = _('Add rating:')
        self.idList     = ID_RATINGS
        Mod_Labels.__init__(self)

#------------------------------------------------------------------------------
class Mod_SetVersion(Link):
    """Sets version of file back to 0.8."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.fileInfo = window.data[data[0]]
        menuItem = wx.MenuItem(menu,self.id,_('Version 0.8'))
        menu.AppendItem(menuItem)
        #print self.fileInfo.header.version
        menuItem.Enable((len(data) == 1) and (int(10*self.fileInfo.header.version) != 8))

    def Execute(self,event):
        message = _("WARNING! For advanced modders only! This feature allows you to edit newer official mods in the TES Construction Set by resetting the internal file version number back to 0.8. While this will make the mod editable, it may also break the mod in some way.")
        if not balt.askContinue(self.window,message,'bash.setModVersion.continue',_('Set File Version')):
            return
        self.fileInfo.header.version = 0.8
        self.fileInfo.header.setChanged()
        self.fileInfo.writeHeader()
        #--Repopulate
        self.window.RefreshUI(detail=self.fileInfo.name)

#------------------------------------------------------------------------------
class Mod_Details(Link):
    """Show Mod Details"""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.fileInfo = window.data[data[0]]
        menuItem = wx.MenuItem(menu,self.id,_('Details...'))
        menu.AppendItem(menuItem)
        menuItem.Enable((len(data) == 1))

    def Execute(self,event):
        modName = GPath(self.data[0])
        modInfo = bosh.modInfos[modName]
        progress = balt.Progress(_(modName.s))
        try:
            modDetails = bosh.ModDetails()
            modDetails.readFromMod(modInfo,SubProgress(progress,0.1,0.7))
            buff = stringBuffer()
            progress(0.7,_("Sorting records."))
            for group in sorted(modDetails.group_records):
                buff.write(group+'\n')
                if group in ('CELL','WRLD','DIAL'):
                    buff.write(_('  (Details not provided for this record type.)\n\n'))
                    continue
                records = modDetails.group_records[group]
                records.sort(key = lambda a: a[1].lower())
                #if group != 'GMST': records.sort(key = lambda a: a[0] >> 24)
                for fid,eid in records:
                    buff.write('  %08X %s\n' % (fid,eid))
                buff.write('\n')
            balt.showLog(self.window,buff.getvalue(), modInfo.name.s,
                asDialog=False, fixedFont=True, icons=bashBlue)
            progress.Destroy()
            buff.close()
        finally:
            if progress: progress.Destroy()

#------------------------------------------------------------------------------
class Mod_RemoveWorldOrphans(Link):
    """Remove orphaned cell records."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Remove World Orphans'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data) != 1 or (self.data[0] != 'Oblivion.esm' and self.data[0] != 'Oblivion_1.1.esm'))

    def Execute(self,event):
        message = _("In some circumstances, editing a mod will leave orphaned cell records in the world group. This command will remove such orphans.")
        if not balt.askContinue(self.window,message,'bash.removeWorldOrphans.continue',_('Remove World Orphans')):
            return
        for item in self.data:
            fileName = GPath(item)
            if item == 'Oblivion.esm' or item == 'Oblivion_1.1.esm':
                balt.showWarning(self.window,_("Skipping %s") % fileName.s,_('Remove World Orphans'))
                continue
            fileInfo = bosh.modInfos[fileName]
            #--Export
            progress = balt.Progress(_("Remove World Orphans"))
            orphans = 0
            try:
                loadFactory = bosh.LoadFactory(True,bosh.MreCell,bosh.MreWrld)
                modFile = bosh.ModFile(fileInfo,loadFactory)
                progress(0,_("Reading %s.") % (fileName.s,))
                modFile.load(True,SubProgress(progress,0,0.7))
                orphans = ('WRLD' in modFile.tops) and modFile.WRLD.orphansSkipped
                if orphans:
                    progress(0.1,_("Saving %s.") % (fileName.s,))
                    modFile.safeSave()
                progress(1.0,_("Done."))
            finally:
                progress = progress.Destroy()
            #--Log
            if orphans:
                balt.showOk(self.window,_("Orphan cell blocks removed: %d.") % (orphans,),fileName.s)
            else:
                balt.showOk(self.window,_("No changes required."),fileName.s)

#------------------------------------------------------------------------------
class Mod_ShowReadme(Link):
    """Open the readme."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Readme...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) == 1)

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        if not docBrowser:
            DocBrowser().Show()
            settings['bash.modDocs.show'] = True
        #balt.ensureDisplayed(docBrowser)
        docBrowser.SetMod(fileInfo.name)
        docBrowser.Raise()

#------------------------------------------------------------------------------
class Mod_Scripts_Export(Link):
    """Export scripts from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Scripts...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        defaultPath = bosh.dirs['patches'].join(fileName.s+' Exported Scripts')
        skip = balt.askText(self.window,_('Skip prefix (leave blank to not skip any), non-case sensitive):'),
            _('Skip Prefix?'),'')
        if skip == None: return
        deprefix = balt.askText(self.window,_('Remove prefix from file names f.e. enter cob to save script cobDenockInit\nas DenockInit.ext rather than as cobDenockInit.ext  (leave blank to not cut any prefix, non-case sensitive):'),
            _('Remove Prefix from file names?'),'')
        if deprefix == None: return
        if not defaultPath.exists():
            defaultPath.makedirs()
        textDir = balt.askDirectory(self.window,
            _('Choose directory to export scripts to'),defaultPath)
        if not textDir == defaultPath:
            for asDir,sDirs,sFiles in os.walk(defaultPath.s):
                if not (sDirs or sFiles):
                    defaultPath.removedirs()
        if not textDir: return
        #--Export
        #try:
        if not CBash:
            ScriptText = bosh.ScriptText()
        else:
            ScriptText = bosh.CBash_ScriptText()
        ScriptText.readFromMod(fileInfo,fileName.s)
        exportedScripts = ScriptText.writeToText(fileInfo,skip,textDir,deprefix,fileName.s)
        #finally:
        balt.showLog(self.window,exportedScripts,_('Export Scripts'),icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_Scripts_Import(Link):
    """Import scripts from text file or other mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Scripts...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = (_("Import script from a text file. This will replace existing scripts and is not reversible (except by restoring from backup)!"))
        if not balt.askContinue(self.window,message,'bash.scripts.import.continue',
            _('Import Scripts')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        defaultPath = bosh.dirs['patches'].join(fileName.s+' Exported Scripts')
        if not defaultPath.exists():
            defaultPath = bosh.dirs['patches']
        textDir = balt.askDirectory(self.window,
            _('Choose directory to import scripts from'),defaultPath)
        if textDir is None:
            #balt.showError(self.window,_('Source folder must be selected.')) #causes warning to show when canceled
            return
        message = _("Import scripts that don't exist in the esp as new scripts?\n(If not they will just be skipped).")
        makeNew = balt.askYes(self.window,message,_('Import Scripts'),icon=wx.ICON_QUESTION)
        if not CBash:
            ScriptText = bosh.ScriptText()
        else:
            ScriptText = bosh.CBash_ScriptText()
        ScriptText.readFromText(textDir.s,fileInfo)
        changed, added = ScriptText.writeToMod(fileInfo,makeNew)
    #--Log
        if not (len(changed) or len(added)):
            balt.showOk(self.window,_("No changed or new scripts to import."),_("Import Scripts"))
        else:
            if changed:
                changedScripts = (_('Imported %d changed scripts from %s:\n%s') % (len(changed),textDir.s,'*'+'\n*'.join(sorted(changed))))
            else:
                changedScripts = ''
            if added:
                addedScripts = (_('Imported %d new scripts from %s:\n%s') % (len(added),textDir.s,'*'+'\n*'.join(sorted(added))))
            else:
                addedScripts = ''
            if changed and added:
                report = changedScripts + '\n\n' + addedScripts
            elif changed:
                report = changedScripts
            elif added:
                report = addedScripts
            balt.showLog(self.window,report,_('Import Scripts'),icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_Stats_Export(Link):
    """Export armor and weapon stats from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Stats...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_Stats.csv')
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_('Export stats to:'),
            textDir, textName, '*Stats.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        progress = balt.Progress(_("Export Stats"))
        try:
            if not CBash:
                itemStats = bosh.ItemStats()
            else:
                itemStats = bosh.CBash_ItemStats()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_("Reading %s.") % (fileName.s,))
                itemStats.readFromMod(fileInfo)
            progress(0.8,_("Exporting to %s.") % (textName.s,))
            itemStats.writeToText(textPath)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()

#------------------------------------------------------------------------------
class Mod_Stats_Import(Link):
    """Import stats from text file or other mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Stats...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = (_("Import item stats from a text file. This will replace existing stats and is not reversible!"))
        if not balt.askContinue(self.window,message,'bash.stats.import.continue',
            _('Import Stats')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_Stats.csv')
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_('Import stats from:'),
            textDir, textName, '*Stats.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != '.csv':
            balt.showError(self.window,_('Source file must be a Stats.csv file.'))
            return
        #--Export
        progress = balt.Progress(_("Import Stats"))
        changed = None
        try:
            if CBash:
                itemStats = bosh.CBash_ItemStats()
            else:
                itemStats = bosh.ItemStats()
            progress(0.1,_("Reading %s.") % (textName.s,))
            itemStats.readFromText(textPath)
            progress(0.2,_("Applying to %s.") % (fileName.s,))
            changed = itemStats.writeToMod(fileInfo)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()
        #--Log
        if not changed:
            balt.showOk(self.window,_("No relevant stats to import."),_("Import Stats"))
        else:
            if not len(changed):
                balt.showOk(self.window,_("No changed stats to import."),_("Import Stats"))
            else:
                buff = stringBuffer()
                for modName in sorted(changed):
                    buff.write('* %03d  %s:\n' % (changed[modName], modName.s))
                balt.showLog(self.window,buff.getvalue(),_('Import Stats'),icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_ItemData_Export(Link):
    """Export pretty much complete item data from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Item Data...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_ItemData.csv')
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_('Export item data to:'),
            textDir, textName, '*ItemData.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        progress = balt.Progress(_("Export Item Data"))
        try:
            if CBash:
                itemStats = bosh.CBash_CompleteItemData()
            else:
                itemStats = bosh.CompleteItemData()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_("Reading %s.") % (fileName.s,))
                itemStats.readFromMod(fileInfo)
            progress(0.8,_("Exporting to %s.") % (textName.s,))
            itemStats.writeToText(textPath)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()

#------------------------------------------------------------------------------
class Mod_ItemData_Import(Link):
    """Import stats from text file or other mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Item Data...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = (_("Import pretty much complete item data from a text file. This will replace existing data and is not reversible!"))
        if not balt.askContinue(self.window,message,'bash.itemdata.import.continue',
            _('Import Item Data')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_ItemData.csv')
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_('Import item data from:'),
            textDir, textName, '*ItemData.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != '.csv':
            balt.showError(self.window,_('Source file must be a ItemData.csv file.'))
            return
        #--Export
        progress = balt.Progress(_('Import Item Data'))
        changed = None
        try:
            itemStats = bosh.CompleteItemData()
            progress(0.1,_("Reading %s.") % (textName.s,))
            if ext == '.csv':
                itemStats.readFromText(textPath)
            else:
                srcInfo = bosh.ModInfo(textDir,textName)
                itemStats.readFromMod(srcInfo)
            progress(0.2,_("Applying to %s.") % (fileName.s,))
            changed = itemStats.writeToMod(fileInfo)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()
        #--Log
        if not changed:
            balt.showOk(self.window,_("No relevant data to import."),_("Import Item Data"))
        else:
            buff = stringBuffer()
            for modName in sorted(changed):
                buff.write(_('Imported Item Data:\n* %03d  %s:\n') % (changed[modName], modName.s))
            balt.showLog(self.window,buff.getvalue(),_('Import Item Data'),icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_Prices_Export(Link):
    """Export item prices from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Prices...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_Prices.csv')
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_('Export prices to:'),
            textDir, textName, '*Prices.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        progress = balt.Progress(_("Export Prices"))
        try:
            if CBash:
                itemPrices = bosh.CBash_ItemPrices()
            else:
                itemPrices = bosh.ItemPrices()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_("Reading %s.") % (fileName.s,))
                itemPrices.readFromMod(fileInfo)
            progress(0.8,_("Exporting to %s.") % (textName.s,))
            itemPrices.writeToText(textPath)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()

#------------------------------------------------------------------------------
class Mod_Prices_Import(Link):
    """Import prices from text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Prices...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = (_("Import item prices from a text file. This will replace existing prices and is not reversible!"))
        if not balt.askContinue(self.window,message,'bash.prices.import.continue',
            _('Import prices')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_Prices.csv')
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_('Import prices from:'),
            textDir, textName, '*Prices.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext not in ['.csv','.ghost','.esm','.esp']:
            balt.showError(self.window,_('Source file must be a Prices.csv file or esp/m.'))
            return
        #--Export
        progress = balt.Progress(_("Import Prices"))
        changed = None
        try:
            if CBash:
                itemPrices = bosh.CBash_ItemPrices()
            else:
                itemPrices = bosh.ItemPrices()
            progress(0.1,_("Reading %s.") % (textName.s,))
            if ext == '.csv':
                itemPrices.readFromText(textPath)
            else:
                srcInfo = bosh.ModInfo(textDir,textName)
                itemPrices.readFromMod(srcInfo)
            progress(0.2,_("Applying to %s.") % (fileName.s,))
            changed = itemPrices.writeToMod(fileInfo)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()
        #--Log
        if not changed:
            balt.showOk(self.window,_("No relevant prices to import."),_("Import Prices"))
        else:
            buff = stringBuffer()
            for modName in sorted(changed):
                buff.write(_('Imported Prices:\n* %s: %d\n') % (modName.s,changed[modName]))
            balt.showLog(self.window,buff.getvalue(),_('Import Prices'),icons=bashBlue)

#------------------------------------------------------------------------------
class CBash_Mod_MapMarkers_Export(Link):
    """Export armor and weapon stats from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Map Markers...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data) and bool(CBash))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_MapMarkers.csv')
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_('Export Map Markers to:'),
            textDir, textName, '*MapMarkers.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        progress = balt.Progress(_("Export Map Markers"))
        try:
            mapMarkers = bosh.CBash_MapMarkers()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_("Reading %s.") % (fileName.s,))
                mapMarkers.readFromMod(fileInfo)
            progress(0.8,_("Exporting to %s.") % (textName.s,))
            mapMarkers.writeToText(textPath)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()

#------------------------------------------------------------------------------
class CBash_Mod_MapMarkers_Import(Link):
    """Import MapMarkers from text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Map Markers...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data) == 1 and bool(CBash))

    def Execute(self,event):
        message = (_("Import Map Markers data from a text file. This will replace existing the data on map markers with the same editor ids and is not reversible!"))
        if not balt.askContinue(self.window,message,'bash.MapMarkers.import.continue',
            _('Import Map Markers')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_MapMarkers.csv')
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_('Import Map Markers from:'),
            textDir, textName, '*MapMarkers.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext not in ['.csv']:
            balt.showError(self.window,_('Source file must be a MapMarkers.csv file'))
            return
        #--Export
        progress = balt.Progress(_("Import Map Markers"))
        changed = None
        try:
            MapMarkers = bosh.CBash_MapMarkers()
            progress(0.1,_("Reading %s.") % (textName.s,))
            MapMarkers.readFromText(textPath)
            progress(0.2,_("Applying to %s.") % (fileName.s,))
            changed = MapMarkers.writeToMod(fileInfo)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()
        #--Log
        if not changed:
            balt.showOk(self.window,_("No relevant Map Markers to import."),_("Import Map Markers"))
        else:
            buff = stringBuffer()
            buff.write('Imported Map Markers to mod %s:\n' % (fileName.s,))
            for eid in sorted(changed):
                buff.write('* %s\n' % (eid))
            balt.showLog(self.window,buff.getvalue(),_('Import Map Markers'),icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_SigilStoneDetails_Export(Link):
    """Export Sigil Stone details from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Sigil Stones...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_SigilStones.csv')
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_('Export Sigil Stone details to:'),textDir,textName, '*_SigilStones.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        progress = balt.Progress(_("Export Sigil Stone details"))
        try:
            if CBash:
                sigilStones = bosh.CBash_SigilStoneDetails()
            else:
                sigilStones = bosh.SigilStoneDetails()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_("Reading %s.") % (fileName.s,))
                sigilStones.readFromMod(fileInfo)
            progress(0.8,_("Exporting to %s.") % (textName.s,))
            sigilStones.writeToText(textPath)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()
#------------------------------------------------------------------------------
class Mod_SigilStoneDetails_Import(Link):
    """Import Sigil Stone details from text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Sigil Stones...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data) == 1)

    def Execute(self,event):
        message = (_("Import Sigil Stone details from a text file. This will replace existing the data on sigil stones with the same form ids and is not reversible!"))
        if not balt.askContinue(self.window,message,'bash.SigilStone.import.continue',
            _('Import Sigil Stones details')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_SigilStones.csv')
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_('Import Sigil Stone details from:'),
            textDir, textName, '*_SigilStones.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext not in ['.csv']:
            balt.showError(self.window,_('Source file must be a _SigilStones.csv file'))
            return
        #--Export
        progress = balt.Progress(_("Import Sigil Stone details"))
        changed = None
        try:
            if CBash:
                sigilStones = bosh.CBash_SigilStoneDetails()
            else:
                sigilStones = bosh.SigilStoneDetails()
            progress(0.1,_("Reading %s.") % (textName.s,))
            sigilStones.readFromText(textPath)
            progress(0.2,_("Applying to %s.") % (fileName.s,))
            changed = sigilStones.writeToMod(fileInfo)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()
        #--Log
        if not changed:
            balt.showOk(self.window,_("No relevant Sigil Stone details to import."),_("Import Sigil Stone details"))
        else:
            buff = stringBuffer()
            buff.write('Imported Sigil Stone details to mod %s:\n' % (fileName.s,))
            for eid in sorted(changed):
                buff.write('* %s\n' % (eid))
            balt.showLog(self.window,buff.getvalue(),_('Import Sigil Stone details'),icons=bashBlue)
#------------------------------------------------------------------------------
class Mod_SpellRecords_Export(Link):
    """Export Spell details from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Spells...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_Spells.csv')
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_('Export Spell details to:'),textDir,textName, '*_Spells.csv')
        if not textPath: return
        message = _("Export flags and effects?\n(If not they will just be skipped).")
        doDetailed = balt.askYes(self.window,message,_('Export Spells'),icon=wx.ICON_QUESTION)
        (textDir,textName) = textPath.headTail
        #--Export
        progress = balt.Progress(_("Export Spell details"))
        try:
            if CBash:
                spellRecords = bosh.CBash_SpellRecords(detailed=doDetailed)
            else:
                spellRecords = bosh.SpellRecords(detailed=doDetailed)
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_("Reading %s.") % (fileName.s,))
                spellRecords.readFromMod(fileInfo)
            progress(0.8,_("Exporting to %s.") % (textName.s,))
            spellRecords.writeToText(textPath)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()
#------------------------------------------------------------------------------
class Mod_SpellRecords_Import(Link):
    """Import Spell details from text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Spells...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data) == 1)

    def Execute(self,event):
        message = (_("Import Spell details from a text file. This will replace existing the data on spells with the same form ids and is not reversible!"))
        if not balt.askContinue(self.window,message,'bash.SpellRecords.import.continue',
            _('Import Spell details')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_Spells.csv')
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_('Import Spell details from:'),
            textDir, textName, '*_Spells.csv',mustExist=True)
        if not textPath: return
        message = _("Import flags and effects?\n(If not they will just be skipped).")
        doDetailed = balt.askYes(self.window,message,_('Import Spell details'),icon=wx.ICON_QUESTION)
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext not in ['.csv']:
            balt.showError(self.window,_('Source file must be a _Spells.csv file'))
            return
        #--Export
        progress = balt.Progress(_("Import Spell details"))
        changed = None
        try:
            if CBash:
                spellRecords = bosh.CBash_SpellRecords(detailed=doDetailed)
            else:
                spellRecords = bosh.SpellRecords(detailed=doDetailed)
            progress(0.1,_("Reading %s.") % (textName.s,))
            spellRecords.readFromText(textPath)
            progress(0.2,_("Applying to %s.") % (fileName.s,))
            changed = spellRecords.writeToMod(fileInfo)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()
        #--Log
        if not changed:
            balt.showOk(self.window,_("No relevant Spell details to import."),_("Import Spell details"))
        else:
            buff = stringBuffer()
            buff.write('Imported Spell details to mod %s:\n' % (fileName.s,))
            for eid in sorted(changed):
                buff.write('* %s\n' % (eid))
            balt.showLog(self.window,buff.getvalue(),_('Import Spell details'),icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_IngredientDetails_Export(Link):
    """Export Ingredient details from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Ingredients...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_Ingredients.csv')
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_('Export Ingredient details to:'),textDir,textName, '*_Ingredients.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        progress = balt.Progress(_("Export Ingredient details"))
        try:
            if CBash:
                Ingredients = bosh.CBash_IngredientDetails()
            else:
                Ingredients = bosh.IngredientDetails()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_("Reading %s.") % (fileName.s,))
                Ingredients.readFromMod(fileInfo)
            progress(0.8,_("Exporting to %s.") % (textName.s,))
            Ingredients.writeToText(textPath)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()
class Mod_IngredientDetails_Import(Link):
    """Import Ingredient details from text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Ingredients...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data) == 1)

    def Execute(self,event):
        message = (_("Import Ingredient details from a text file. This will replace existing the data on Ingredients with the same form ids and is not reversible!"))
        if not balt.askContinue(self.window,message,'bash.Ingredient.import.continue',
            _('Import Ingredients details')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+_('_Ingredients.csv')
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_('Import Ingredient details from:'),
            textDir, textName, '*_Ingredients.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext not in ['.csv']:
            balt.showError(self.window,_('Source file must be a _Ingredients.csv file'))
            return
        #--Export
        progress = balt.Progress(_("Import Ingredient details"))
        changed = None
        try:
            if CBash:
                Ingredients = bosh.CBash_IngredientDetails()
            else:
                Ingredients = bosh.IngredientDetails()
            progress(0.1,_("Reading %s.") % (textName.s,))
            Ingredients.readFromText(textPath)
            progress(0.2,_("Applying to %s.") % (fileName.s,))
            changed = Ingredients.writeToMod(fileInfo)
            progress(1.0,_("Done."))
        finally:
            progress = progress.Destroy()
        #--Log
        if not changed:
            balt.showOk(self.window,_("No relevant Ingredient details to import."),_("Import Ingredient details"))
        else:
            buff = stringBuffer()
            buff.write('Imported Ingredient details to mod %s:\n' % (fileName.s,))
            for eid in sorted(changed):
                buff.write('* %s\n' % (eid))
            balt.showLog(self.window,buff.getvalue(),_('Import Ingredient details'),icons=bashBlue)
#------------------------------------------------------------------------------
class Mod_UndeleteRefs(Link):
    """Undeletes refs in cells."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Undelete Refs'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data) != 1 or (self.data[0] != 'Oblivion.esm' and self.data[0] != 'Oblivion_1.1.esm'))

    def Execute(self,event):
        message = _("Changes deleted refs to ignored. This is a very advanced feature and should only be used by modders who know exactly what they're doing.")
        if not balt.askContinue(self.window,message,'bash.undeleteRefs.continue',
            _('Undelete Refs')):
            return
        progress = balt.Progress(_("Undelete Refs"))
        progress.setFull(len(self.data))
        try:
            hasFixed = False
            log = bolt.LogFile(stringBuffer())
            for index,fileName in enumerate(map(GPath,self.data)):
                if fileName == 'Oblivion.esm'or fileName == 'Oblivion_1.1.esm':
                    balt.showWarning(self.window,_("Skipping %s") % fileName.s,_('Undelete Refs'))
                    continue
                progress(index,_("Scanning %s.") % (fileName.s,))
                fileInfo = bosh.modInfos[fileName]
                undeleteRefs = bosh.UndeleteRefs(fileInfo)
                undeleteRefs.undelete(SubProgress(progress,index,index+1))
                if undeleteRefs.fixedRefs:
                    hasFixed = True
                    log.setHeader('==%s' % (fileName.s,))
                    for fid in sorted(undeleteRefs.fixedRefs):
                        log('. %08X' % (fid,))
            progress.Destroy()
            if hasFixed:
                message = log.out.getvalue()
                balt.showWryeLog(self.window,message,_('Undelete Refs'),icons=bashBlue)
            else:
                message = _("No changes required.")
                balt.showOk(self.window,message,_('Undelete Refs'))
        finally:
            progress = progress.Destroy()

# Saves Links ------------------------------------------------------------------
#------------------------------------------------------------------------------
class Saves_ProfilesData(balt.ListEditorData):
    """Data capsule for save profiles editing dialog."""
    def __init__(self,parent):
        """Initialize."""
        self.baseSaves = bosh.dirs['saveBase'].join('Saves')
        #--GUI
        balt.ListEditorData.__init__(self,parent)
        self.showAdd    = True
        self.showRename = True
        self.showRemove = True
        self.showInfo   = True
        self.infoWeight = 2
        self.infoReadOnly = False

    def getItemList(self):
        """Returns load list keys in alpha order."""
        #--Get list of directories in Hidden, but do not include default.
        items = [x.s for x in bosh.saveInfos.getLocalSaveDirs()]
        items.sort(key=lambda a: a.lower())
        return items

    #--Info box
    def getInfo(self,item):
        """Returns string info on specified item."""
        profileSaves = 'Saves\\'+item+'\\'
        return bosh.saveInfos.profiles.getItem(profileSaves,'info',_('About %s:') % (item,))
    def setInfo(self,item,text):
        """Sets string info on specified item."""
        profileSaves = 'Saves\\'+item+'\\'
        bosh.saveInfos.profiles.setItem(profileSaves,'info',text)

    def add(self):
        """Adds a new profile."""
        newName = balt.askText(self.parent,_("Enter profile name:"))
        if not newName:
            return False
        if newName in self.getItemList():
            balt.showError(self.parent,_('Name must be unique.'))
            return False
        if len(newName) == 0 or len(newName) > 64:
            balt.showError(self.parent,
                _('Name must be between 1 and 64 characters long.'))
            return False
        self.baseSaves.join(newName).makedirs()
        newSaves = 'Saves\\'+newName+'\\'
        bosh.saveInfos.profiles.setItem(newSaves,'vOblivion',bosh.modInfos.voCurrent)
        return newName

    def rename(self,oldName,newName):
        """Renames profile oldName to newName."""
        newName = newName.strip()
        lowerNames = [name.lower() for name in self.getItemList()]
        #--Error checks
        if newName.lower() in lowerNames:
            balt.showError(self,_('Name must be unique.'))
            return False
        if len(newName) == 0 or len(newName) > 64:
            balt.showError(self.parent,
                _('Name must be between 1 and 64 characters long.'))
            return False
        #--Rename
        oldDir,newDir = (self.baseSaves.join(dir) for dir in (oldName,newName))
        oldDir.moveTo(newDir)
        oldSaves,newSaves = (('Saves\\'+name+'\\') for name in (oldName,newName))
        if bosh.saveInfos.localSave == oldSaves:
            bosh.saveInfos.setLocalSave(newSaves)
            bashFrame.SetTitle()
        bosh.saveInfos.profiles.moveRow(oldSaves,newSaves)
        return newName

    def remove(self,profile):
        """Removes load list."""
        profileSaves = 'Saves\\'+profile+'\\'
        #--Can't remove active or Default directory.
        if bosh.saveInfos.localSave == profileSaves:
            balt.showError(self.parent,_('Active profile cannot be removed.'))
            return False
        #--Get file count. If > zero, verify with user.
        profileDir = bosh.dirs['saveBase'].join(profileSaves)
        files = [file for file in profileDir.list() if bosh.reSaveExt.search(file.s)]
        if files:
            message = _('Delete profile %s and the %d save files it contains?') % (profile,len(files))
            if not balt.askYes(self.parent,message,_('Delete Profile')):
                return False
        #--Remove directory
        if GPath('Oblivion/Saves').s not in profileDir.s:
            raise BoltError(_('Sanity check failed: No "Oblivion\\Saves" in %s.') % (profileDir.s,))
        shutil.rmtree(profileDir.s) #--DO NOT SCREW THIS UP!!!
        bosh.saveInfos.profiles.delRow(profileSaves)
        return True

#------------------------------------------------------------------------------
class Saves_Profiles:
    """Select a save set profile -- i.e., the saves directory."""
    def __init__(self):
        """Initialize."""
        self.idList = ID_PROFILES

    def GetItems(self):
        return [x.s for x in bosh.saveInfos.getLocalSaveDirs()]

    def AppendToMenu(self,menu,window,data):
        """Append label list to menu."""
        self.window = window
        #--Edit
        menu.Append(self.idList.EDIT,_("Edit Profiles..."))
        menu.AppendSeparator()
        #--List
        localSave = bosh.saveInfos.localSave
        menuItem = wx.MenuItem(menu,self.idList.DEFAULT,_('Default'),kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        menuItem.Check(localSave == 'Saves\\')
        for id,item in zip(self.idList,self.GetItems()):
            menuItem = wx.MenuItem(menu,id,item,kind=wx.ITEM_CHECK)
            menu.AppendItem(menuItem)
            menuItem.Check(localSave == ('Saves\\'+item+'\\'))
        #--Events
        wx.EVT_MENU(bashFrame,self.idList.EDIT,self.DoEdit)
        wx.EVT_MENU(bashFrame,self.idList.DEFAULT,self.DoDefault)
        wx.EVT_MENU_RANGE(bashFrame,self.idList.BASE,self.idList.MAX,self.DoList)

    def DoEdit(self,event):
        """Show profiles editing dialog."""
        data = Saves_ProfilesData(self.window)
        dialog = balt.ListEditor(self.window,-1,_('Save Profiles'),data)
        dialog.ShowModal()
        dialog.Destroy()

    def DoDefault(self,event):
        """Handle selection of Default."""
        arcSaves,newSaves = bosh.saveInfos.localSave,'Saves\\'
        bosh.saveInfos.setLocalSave(newSaves)
        self.swapPlugins(arcSaves,newSaves)
        self.swapOblivionVersion(newSaves)
        bashFrame.SetTitle()
        self.window.details.SetFile(None)
        modList.RefreshUI()
        bashFrame.RefreshData()

    def DoList(self,event):
        """Handle selection of label."""
        profile = self.GetItems()[event.GetId()-self.idList.BASE]
        arcSaves = bosh.saveInfos.localSave
        newSaves = 'Saves\\%s\\' % (profile,)
        bosh.saveInfos.setLocalSave(newSaves)
        self.swapPlugins(arcSaves,newSaves)
        self.swapOblivionVersion(newSaves)
        bashFrame.SetTitle()
        self.window.details.SetFile(None)
        bashFrame.RefreshData()
        bosh.modInfos.autoGhost()
        modList.RefreshUI()

    def swapPlugins(self,arcSaves,newSaves):
        """Saves current plugins into arcSaves directory and loads plugins
        from newSaves directory (if present)."""
        arcPath,newPath = (bosh.dirs['saveBase'].join(saves,'plugins.txt')
            for saves in (arcSaves,newSaves))
        #--Archive old Saves
        bosh.modInfos.plugins.path.copyTo(arcPath)
        if newPath.exists():
            newPath.copyTo(bosh.modInfos.plugins.path)

    def swapOblivionVersion(self,newSaves):
        """Swaps Oblivion version to memorized version."""
        voNew = bosh.saveInfos.profiles.setItemDefault(newSaves,'vOblivion',bosh.modInfos.voCurrent)
        if voNew in bosh.modInfos.voAvailable:
            bosh.modInfos.setOblivionVersion(voNew)

#------------------------------------------------------------------------------
class Save_LoadMasters(Link):
    """Sets the load list to the save game's masters."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Load Masters'))
        menu.AppendItem(menuItem)
        if len(data) != 1: menuItem.Enable(False)

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        errorMessage = bosh.modInfos.selectExact(fileInfo.masterNames)
        modList.PopulateItems()
        saveList.PopulateItems()
        self.window.details.SetFile(fileName)
        if errorMessage:
            balt.showError(self.window,errorMessage,fileName.s)

#------------------------------------------------------------------------------
class Save_ImportFace(Link):
    """Imports a face from another save."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Import Face...'))
        menu.AppendItem(menuItem)
        if len(data) != 1: menuItem.Enable(False)

    def Execute(self,event):
        #--File Info
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        #--Select source face file
        srcDir = fileInfo.dir
        wildcard = _('Oblivion Files')+' (*.esp;*.esm;*.ess;*.esr)|*.esp;*.esm;*.ess;*.esr'
        #--File dialog
        srcPath = balt.askOpen(self.window,'Face Source:',srcDir, '', wildcard,mustExist=True)
        if not srcPath: return
        if bosh.reSaveExt.search(srcPath.s):
            self.FromSave(fileInfo,srcPath)
        elif bosh.reModExt.search(srcPath.s):
            self.FromMod(fileInfo,srcPath)

    def FromSave(self,fileInfo,srcPath):
        """Import from a save."""
        #--Get face
        srcDir,srcName = GPath(srcPath).headTail
        srcInfo = bosh.SaveInfo(srcDir,srcName)
        progress = balt.Progress(srcName.s)
        try:
            saveFile = bosh.SaveFile(srcInfo)
            saveFile.load(progress)
            progress.Destroy()
            srcFaces = bosh.PCFaces.save_getFaces(saveFile)
            #--Dialog
            dialog = ImportFaceDialog(self.window,-1,srcName.s,fileInfo,srcFaces)
            dialog.ShowModal()
            dialog.Destroy()
        finally:
            if progress: progress.Destroy()

    def FromMod(self,fileInfo,srcPath):
        """Import from a mod."""
        #--Get faces
        srcDir,srcName = GPath(srcPath).headTail
        srcInfo = bosh.ModInfo(srcDir,srcName)
        srcFaces = bosh.PCFaces.mod_getFaces(srcInfo)
        #--No faces to import?
        if not srcFaces:
            balt.showOk(self.window,_('No player (PC) faces found in %s.') % (srcName.s,),srcName.s)
            return
        #--Dialog
        dialog = ImportFaceDialog(self.window,-1,srcName.s,fileInfo,srcFaces)
        dialog.ShowModal()
        dialog.Destroy()

#------------------------------------------------------------------------------
class Save_RenamePlayer(Link):
    """Renames the Player character in a save game."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Rename Player...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) != 0)

    def Execute(self,event):
        saveInfo = bosh.saveInfos[self.data[0]]
        newName = balt.askText(self.window,_("Enter new player name. E.g. Conan the Bold"),
            _("Rename player"),saveInfo.header.pcName)
        if not newName: return
        for save in self.data:
            savedPlayer = bosh.Save_NPCEdits(self.window.data[GPath(save)])
            savedPlayer.renamePlayer(newName)
        bosh.saveInfos.refresh()
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class Save_DiffMasters(Link):
    """Shows how saves masters differ from active mod list."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Diff Masters...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) in (1,2))

    def Execute(self,event):
        oldNew = map(GPath,self.data)
        oldNew.sort(key = lambda x: bosh.saveInfos.dir.join(x).mtime)
        oldName = oldNew[0]
        oldInfo = self.window.data[GPath(oldName)]
        oldMasters = set(oldInfo.masterNames)
        if len(self.data) == 1:
            newName = GPath(_("Active Masters"))
            newMasters = set(bosh.modInfos.ordered)
        else:
            newName = oldNew[1]
            newInfo = self.window.data[GPath(newName)]
            newMasters = set(newInfo.masterNames)
        missing = oldMasters - newMasters
        extra = newMasters - oldMasters
        if not missing and not extra:
            message = _("Masters are the same.")
            balt.showInfo(self.window,message,_("Diff Masters"))
        else:
            message = ''
            if missing:
                message += _("=== Removed Masters (%s):\n* ") % (oldName.s,)
                message += '\n* '.join(x.s for x in bosh.modInfos.getOrdered(missing))
                if extra: message += '\n\n'
            if extra:
                message += _("=== Added Masters (%s):\n* ") % (newName.s,)
                message += '\n* '.join(x.s for x in bosh.modInfos.getOrdered(extra))
            balt.showWryeLog(self.window,message,_("Diff Masters"))

#--------------------------------------------------------------------------
class Save_Rename(Link):
    """Renames Save File."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Rename...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) != 0)

    def Execute(self,event):
        if len(self.data) > 0:
            index = self.window.list.FindItem(0,self.data[0].s)
            if index != -1:
                self.window.list.EditLabel(index)
#--------------------------------------------------------------------------
class Save_Renumber(Link):
    """Renamumbers a whole lot of save files."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Re-number Save(s)...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) != 0)

    def Execute(self,event):
        #--File Info
        newNumber = balt.askNumber(self.window,_("Enter new number to start numbering the selected saves at."),
            prompt=_('Save Number'),title=_('Re-number Saves'),value=1,min=1,max=10000)
        if not newNumber: return
        rePattern = re.compile(r'^(save )(\d*)(.*)',re.I)
        for index, name in enumerate(self.data):
            maPattern = rePattern.match(name.s)
            if not maPattern: continue
            maPattern = maPattern.groups()
            if not maPattern[1]: continue
            newFileName = "%s%d%s" % (maPattern[0],newNumber,maPattern[2])
            if newFileName != name.s:
                oldPath = bosh.saveInfos.dir.join(name.s)
                newPath = bosh.saveInfos.dir.join(newFileName)
                if not newPath.exists():
                    oldPath.moveTo(newPath)
                    if GPath(oldPath.s[:-3]+'obse').exists():
                        GPath(oldPath.s[:-3]+'obse').moveTo(GPath(newPath.s[:-3]+'obse'))
                    if GPath(oldPath.s[:-3]+'pluggy').exists():
                        GPath(oldPath.s[:-3]+'pluggy').moveTo(GPath(newPath.s[:-3]+'pluggy'))
                newNumber += 1
        bosh.saveInfos.refresh()
        self.window.RefreshUI()
#--------------------------------------------------------------------------
class Save_EditCreatedData(balt.ListEditorData):
    """Data capsule for custom item editing dialog."""
    def __init__(self,parent,saveFile,recordTypes):
        """Initialize."""
        self.changed = False
        self.saveFile = saveFile
        data = self.data = {}
        self.enchantments = {}
        #--Parse records and get into data
        for index,record in enumerate(saveFile.created):
            if record.recType == 'ENCH':
                self.enchantments[record.fid] = record.getTypeCopy()
            elif record.recType in recordTypes:
                record = record.getTypeCopy()
                if not record.full: continue
                record.getSize() #--Since type copy makes it changed.
                saveFile.created[index] = record
                if record.full not in data: data[record.full] = (record.full,[])
                data[record.full][1].append(record)
        #--GUI
        balt.ListEditorData.__init__(self,parent)
        self.showRename = True
        self.showInfo = True
        self.showSave = True
        self.showCancel = True

    def getItemList(self):
        """Returns load list keys in alpha order."""
        items = sorted(self.data.keys())
        items.sort(key=lambda x: self.data[x][1][0].recType)
        return items

    def getInfo(self,item):
        """Returns string info on specified item."""
        buff = stringBuffer()
        name,records = self.data[item]
        record = records[0]
        #--Armor, clothing, weapons
        if record.recType == 'ARMO':
            buff.write(_('Armor\nFlags: '))
            buff.write(', '.join(record.flags.getTrueAttrs())+'\n')
            for attr in ('strength','value','weight'):
                buff.write('%s: %s\n' % (attr,getattr(record,attr)))
        elif record.recType == 'CLOT':
            buff.write(_('Clothing\nFlags: '))
            buff.write(', '.join(record.flags.getTrueAttrs())+'\n')
        elif record.recType == 'WEAP':
            buff.write(bush.weaponTypes[record.weaponType]+'\n')
            for attr in ('damage','value','speed','reach','weight'):
                buff.write('%s: %s\n' % (attr,getattr(record,attr)))
        #--Enchanted? Switch record to enchantment.
        if hasattr(record,'enchantment') and record.enchantment in self.enchantments:
            buff.write('\nEnchantment:\n')
            record = self.enchantments[record.enchantment].getTypeCopy()
        #--Magic effects
        if record.recType in ('ALCH','SPEL','ENCH'):
            buff.write(record.getEffectsSummary())
        #--Done
        return buff.getvalue()

    def rename(self,oldName,newName):
        """Renames oldName to newName."""
        #--Right length?
        if len(newName) == 0:
            return False
        elif len(newName) > 128:
            balt.showError(self.parent,_('Name is too long.'))
            return False
        elif newName in self.data:
            balt.showError(self.parent,_("Name is already used."))
            return False
        #--Rename
        self.data[newName] = self.data.pop(oldName)
        self.changed = True
        return newName

    def save(self):
        """Handles save button."""
        if not self.changed:
            balt.showOk(self.parent,_("No changes made."))
        else:
            self.changed = False #--Allows graceful effort if close fails.
            count = 0
            for newName,(oldName,records) in self.data.items():
                if newName == oldName: continue
                for record in records:
                    record.full = newName
                    record.setChanged()
                    record.getSize()
                count += 1
            self.saveFile.safeSave()
            balt.showOk(self.parent, _("Names modified: %d.") % (count,),self.saveFile.fileInfo.name.s)

#------------------------------------------------------------------------------
class Save_EditCreated(Link):
    """Allows user to rename custom items (spells, enchantments, etc)."""
    menuNames = {'ENCH':_('Rename Enchanted...'),'SPEL':_('Rename Spells...'),'ALCH':_('Rename Potions...')}
    recordTypes = {'ENCH':('ARMO','CLOT','WEAP')}

    def __init__(self,type):
        if type not in Save_EditCreated.menuNames:
            raise ArgumentError
        Link.__init__(self)
        self.type = type
        self.menuName = Save_EditCreated.menuNames[self.type]

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id, self.menuName)
        menu.AppendItem(menuItem)
        if len(data) != 1: menuItem.Enable(False)

    def Execute(self,event):
        """Handle menu selection."""
        #--Get save info for file
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        #--Get SaveFile
        progress = balt.Progress(_("Loading..."))
        try:
            saveFile = bosh.SaveFile(fileInfo)
            saveFile.load(progress)
        finally:
            if progress: progress.Destroy()
        #--No custom items?
        recordTypes = Save_EditCreated.recordTypes.get(self.type,(self.type,))
        records = [record for record in saveFile.created if record.recType in recordTypes]
        if not records:
            balt.showOk(self.window,_('No items to edit.'))
            return
        #--Open editor dialog
        data = Save_EditCreatedData(self.window,saveFile,recordTypes)
        dialog = balt.ListEditor(self.window,-1,self.menuName,data)
        dialog.ShowModal()
        dialog.Destroy()

#--------------------------------------------------------------------------
class Save_EditPCSpellsData(balt.ListEditorData):
    """Data capsule for pc spell editing dialog."""
    def __init__(self,parent,saveInfo):
        """Initialize."""
        self.saveSpells = bosh.SaveSpells(saveInfo)
        progress = balt.Progress(_('Loading Masters'))
        try:
            self.saveSpells.load(progress)
        finally:
            progress = progress.Destroy()
        self.data = self.saveSpells.getPlayerSpells()
        self.removed = set()
        #--GUI
        balt.ListEditorData.__init__(self,parent)
        self.showRemove = True
        self.showInfo = True
        self.showSave = True
        self.showCancel = True

    def getItemList(self):
        """Returns load list keys in alpha order."""
        return sorted(self.data.keys(),key=lambda a: a.lower())

    def getInfo(self,item):
        """Returns string info on specified item."""
        iref,record = self.data[item]
        return record.getEffectsSummary()

    def remove(self,item):
        """Removes item. Return true on success."""
        if not item in self.data: return False
        iref,record = self.data[item]
        self.removed.add(iref)
        del self.data[item]
        return True

    def save(self):
        """Handles save button click."""
        self.saveSpells.removePlayerSpells(self.removed)

#------------------------------------------------------------------------------
class Save_EditPCSpells(Link):
    """Save spell list editing dialog."""
    def AppendToMenu(self,menu,window,data):
        """Append ref replacer items to menu."""
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Delete Spells...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) == 1)

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        data = Save_EditPCSpellsData(self.window,fileInfo)
        dialog = balt.ListEditor(self.window,-1,_('Player Spells'),data)
        dialog.ShowModal()
        dialog.Destroy()

#------------------------------------------------------------------------------
class Save_EditCreatedEnchantmentCosts(Link):
    """Dialogue and Menu for setting number of uses for Cast When Used Enchantments."""
    def AppendToMenu(self,menu,window,data):
        """Append to menu."""
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Set Number of Uses for Weapon Enchantments...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) == 1)

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        dialog = balt.askNumber(self.window,_('Enter the number of uses you desire per recharge for all custom made enchantements.\n(Enter 0 for unlimited uses)'),prompt=_('Uses'),title=_('Number of Uses'),value=50,min=0,max=10000)
        if not dialog: return
        Enchantments = bosh.SaveEnchantments(fileInfo)
        Enchantments.load()
        Enchantments.setCastWhenUsedEnchantmentNumberOfUses(dialog)

#------------------------------------------------------------------------------
class Save_Move:
    """Moves or copies selected files to alternate profile."""
    def __init__(self,copyMode=False):
        """Initialize."""
        if copyMode:
            self.idList = ID_PROFILES
        else:
            self.idList = ID_PROFILES2
        self.copyMode = copyMode

    def GetItems(self):
        return [x.s for x in bosh.saveInfos.getLocalSaveDirs()]

    def AppendToMenu(self,menu,window,data):
        """Append label list to menu."""
        self.window = window
        self.data = data
        #--List
        localSave = bosh.saveInfos.localSave
        menuItem = wx.MenuItem(menu,self.idList.DEFAULT,_('Default'),kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        menuItem.Enable(localSave != 'Saves\\')
        for id,item in zip(self.idList,self.GetItems()):
            menuItem = wx.MenuItem(menu,id,item,kind=wx.ITEM_CHECK)
            menu.AppendItem(menuItem)
            menuItem.Enable(localSave != ('Saves\\'+item+'\\'))
        #--Events
        wx.EVT_MENU(bashFrame,self.idList.DEFAULT,self.DoDefault)
        wx.EVT_MENU_RANGE(bashFrame,self.idList.BASE,self.idList.MAX,self.DoList)

    def DoDefault(self,event):
        """Handle selection of Default."""
        self.MoveFiles(_('Default'))

    def DoList(self,event):
        """Handle selection of label."""
        profile = self.GetItems()[event.GetId()-self.idList.BASE]
        self.MoveFiles(profile)

    def MoveFiles(self,profile):
        fileInfos = self.window.data
        destDir = bosh.dirs['saveBase'].join('Saves')
        if profile != _('Default'):
            destDir = destDir.join(profile)
        if destDir == fileInfos.dir:
            balt.showError(self.window,_("You can't move saves to the current profile!"))
            return
        savesTable = bosh.saveInfos.table
        #--bashDir
        destTable = bolt.Table(bosh.PickleDict(destDir.join('Bash','Table.dat')))
        count = 0
        ask = True
        for fileName in self.data:
            if ask and not self.window.data.moveIsSafe(fileName,destDir):
                message = (_('A file named %s already exists in %s. Overwrite it?')
                    % (fileName.s,profile))
                result = balt.askContinueShortTerm(self.window,message,_('Move File'))
                #if result is true just do the job but ask next time if applicable as well
                if not result: continue
                elif result == 2: ask = False #so don't warn for rest of operation
            if self.copyMode:
                bosh.saveInfos.copy(fileName,destDir)
            else:
                bosh.saveInfos.move(fileName,destDir,False)
            if fileName in savesTable:
                destTable[fileName] = savesTable.pop(fileName)
            count += 1
        destTable.save()
        bashFrame.RefreshData()
        if self.copyMode:
            balt.showInfo(self.window,_('%d files copied to %s.') % (count,profile),_('Copy File'))

#------------------------------------------------------------------------------
class Save_RepairAbomb(Link):
    """Repairs animation slowing by resetting counter(?) at end of TesClass data."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Repair Abomb'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) == 1)

    def Execute(self,event):
        #--File Info
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        #--Check current value
        saveFile = bosh.SaveFile(fileInfo)
        saveFile.load()
        (tcSize,abombCounter,abombFloat) = saveFile.getAbomb()
        #--Continue?
        progress = 100*abombFloat/struct.unpack('f',struct.pack('I',0x49000000))[0]
        newCounter = 0x41000000
        if abombCounter <= newCounter:
            balt.showOk(self.window,_('Abomb counter is too low to reset.'),_('Repair Abomb'))
            return
        message = _("Reset Abomb counter? (Current progress: %.0f%%.)\n\nNote: Abomb animation slowing won't occur until progress is near 100%%.") % (progress,)
        if balt.askYes(self.window,message,_('Repair Abomb'),default=False):
            saveFile.setAbomb(newCounter)
            saveFile.safeSave()
            balt.showOk(self.window,_('Abomb counter reset.'),_('Repair Abomb'))

#------------------------------------------------------------------------------
class Save_RepairFactions(Link):
    """Repair factions from v 105 Bash error, plus mod faction changes."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Repair Factions'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(bosh.modInfos.ordered) and len(data) == 1)

    def Execute(self,event):
        debug = False
        message = _('This will (mostly) repair faction membership errors due to Wrye Bash v 105 bug and/or faction changes in underlying mods.\n\nWARNING! This repair is NOT perfect! Do not use it unless you have to!')
        if not balt.askContinue(self.window,message,'bash.repairFactions.continue',_('Update NPC Levels')):
            return
        question = _("Restore dropped factions too? WARNING: This may involve clicking through a LOT of yes/no dialogs.")
        restoreDropped = balt.askYes(self.window, question, _('Repair Factions'),default=False)
        progress = balt.Progress(_('Repair Factions'))
        legitNullSpells = bush.repairFactions_legitNullSpells
        legitNullFactions = bush.repairFactions_legitNullFactions
        legitDroppedFactions = bush.repairFactions_legitDroppedFactions
        try:
            #--Loop over active mods
            log = bolt.LogFile(stringBuffer())
            offsetFlag = 0x80
            npc_info = {}
            fact_eid = {}
            loadFactory = bosh.LoadFactory(False,bosh.MreNpc,bosh.MreFact)
            ordered = list(bosh.modInfos.ordered)
            subProgress = SubProgress(progress,0,0.4,len(ordered))
            for index,modName in enumerate(ordered):
                subProgress(index,_("Scanning ") + modName.s)
                modInfo = bosh.modInfos[modName]
                modFile = bosh.ModFile(modInfo,loadFactory)
                modFile.load(True)
                #--Loop over mod NPCs
                mapToOrdered = bosh.MasterMap(modFile.tes4.masters+[modName], ordered)
                for npc in modFile.NPC_.getActiveRecords():
                    fid = mapToOrdered(npc.fid,None)
                    if not fid: continue
                    factions = []
                    for entry in npc.factions:
                        faction = mapToOrdered(entry.faction,None)
                        if not faction: continue
                        factions.append((faction,entry.rank))
                    npc_info[fid] = (npc.eid,factions)
                #--Loop over mod factions
                for fact in modFile.FACT.getActiveRecords():
                    fid = mapToOrdered(fact.fid,None)
                    if not fid: continue
                    fact_eid[fid] = fact.eid
            #--Loop over savefiles
            subProgress = SubProgress(progress,0.4,1.0,len(self.data))
            message = _("NPC Factions Restored/UnNulled:")
            for index,saveName in enumerate(self.data):
                log.setHeader('== '+saveName.s,True)
                subProgress(index,_("Updating ") + saveName.s)
                saveInfo = self.window.data[saveName]
                saveFile = bosh.SaveFile(saveInfo)
                saveFile.load()
                records = saveFile.records
                mapToOrdered = bosh.MasterMap(saveFile.masters, ordered)
                mapToSave = bosh.MasterMap(ordered,saveFile.masters)
                refactionedCount = unNulledCount = 0
                for recNum in xrange(len(records)):
                    unFactioned = unSpelled = unModified = refactioned = False
                    (recId,recType,recFlags,version,data) = records[recNum]
                    if recType != 35: continue
                    orderedRecId = mapToOrdered(recId,None)
                    eid = npc_info.get(orderedRecId,('',))[0]
                    npc = bosh.SreNPC(recFlags,data)
                    recFlags = bosh.SreNPC.flags(recFlags)
                    #--Fix Bash v 105 null array bugs
                    if recFlags.factions and not npc.factions and recId not in legitNullFactions:
                        log('. %08X %s -- Factions' % (recId,eid))
                        npc.factions = None
                        unFactioned = True
                    if recFlags.modifiers and not npc.modifiers:
                        log('. %08X %s -- Modifiers' % (recId,eid))
                        npc.modifiers = None
                        unModified = True
                    if recFlags.spells and not npc.spells and recId not in legitNullSpells:
                        log('. %08X %s -- Spells' % (recId,eid))
                        npc.spells = None
                        unSpelled = True
                    unNulled = (unFactioned or unSpelled or unModified)
                    unNulledCount += (0,1)[unNulled]
                    #--Player, player faction
                    if recId == 7:
                        playerStartSpell = saveFile.getIref(0x00000136)
                        if npc.spells != None and playerStartSpell not in npc.spells:
                            log('. %08X %s -- **DefaultPlayerSpell**' % (recId,eid))
                            npc.spells.append(playerStartSpell)
                            refactioned = True #--I'm lying, but... close enough.
                        playerFactionIref = saveFile.getIref(0x0001dbcd)
                        if (npc.factions != None and
                            playerFactionIref not in [iref for iref,level in npc.factions]
                            ):
                                log('. %08X %s -- **PlayerFaction, 0**' % (recId,eid))
                                npc.factions.append((playerFactionIref,0))
                                refactioned = True
                    #--Compare to mod data
                    elif orderedRecId in npc_info and restoreDropped:
                        (npcEid,factions) = npc_info[orderedRecId]
                        #--Refaction?
                        if npc.factions and factions:
                            curFactions = set([iref for iref,level in npc.factions])
                            for orderedId,level in factions:
                                fid = mapToSave(orderedId,None)
                                if not fid: continue
                                iref = saveFile.getIref(fid)
                                if iref not in curFactions and (recId,fid) not in legitDroppedFactions:
                                    factEid = fact_eid.get(orderedId,'------')
                                    question = _('Restore %s to %s faction?') % (npcEid,factEid)
                                    if debug:
                                        print 'refactioned %08X %08X %s %s' % (recId,fid,npcEid,factEid)
                                    elif not balt.askYes(self.window, question, saveName.s,default=False):
                                        continue
                                    log('. %08X %s -- **%s, %d**' % (recId,eid,factEid,level))
                                    npc.factions.append((iref,level))
                                    refactioned = True
                    refactionedCount += (0,1)[refactioned]
                    #--Save record changes?
                    if unNulled or refactioned:
                        saveFile.records[recNum] = (recId,recType,npc.getFlags(),version,npc.getData())
                #--Save changes?
                subProgress(index+0.5,_("Updating ") + saveName.s)
                if unNulledCount or refactionedCount:
                    saveFile.safeSave()
                message += '\n%d %d %s' % (refactionedCount,unNulledCount,saveName.s,)
            progress.Destroy()
            #balt.showOk(self.window,message,_('Repair Factions'))
            message = log.out.getvalue()
            balt.showWryeLog(self.window,message,_('Repair Factions'),icons=bashBlue)
        finally:
            if progress: progress.Destroy()

#------------------------------------------------------------------------------
class Save_RepairHair(Link):
    """Repairs hair that has been zeroed due to removal of a hair mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Repair Hair'))
        menu.AppendItem(menuItem)
        if len(data) != 1: menuItem.Enable(False)

    def Execute(self,event):
        #--File Info
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        if bosh.PCFaces.save_repairHair(fileInfo):
            balt.showOk(self.window,_('Hair repaired.'))
        else:
            balt.showOk(self.window,_('No repair necessary.'),fileName.s)

#------------------------------------------------------------------------------
class Save_ReweighPotions(Link):
    """Changes weight of all player potions to specified value."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Reweigh Potions...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) == 1)

    def Execute(self,event):
        #--Query value
        result = balt.askText(self.window,
            _("Set weight of all player potions to..."),
            _("Reweigh Potions"),
            '%0.2f' % (settings.get('bash.reweighPotions.newWeight',0.2),))
        if not result: return
        newWeight = float(result.strip())
        if newWeight < 0 or newWeight > 100:
            balt.showOk(self.window,_('Invalid weight: %f') % (newWeight,))
            return
        settings['bash.reweighPotions.newWeight'] = newWeight
        #--Do it
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        progress = balt.Progress(_("Reweigh Potions"))
        try:
            saveFile = bosh.SaveFile(fileInfo)
            saveFile.load(SubProgress(progress,0,0.5))
            count = 0
            progress(0.5,_("Processing."))
            for index,record in enumerate(saveFile.created):
                if record.recType == 'ALCH':
                    record = record.getTypeCopy()
                    record.weight = newWeight
                    record.getSize()
                    saveFile.created[index] = record
                    count += 1
            if count:
                saveFile.safeSave(SubProgress(progress,0.6,1.0))
                progress.Destroy()
                balt.showOk(self.window,_('Potions reweighed: %d.') % (count,),fileName.s)
            else:
                progress.Destroy()
                balt.showOk(self.window,_('No potions to reweigh!'),fileName.s)
        finally:
            if progress: progress.Destroy()

#------------------------------------------------------------------------------
class Save_Stats(Link):
    """Show savefile statistics."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Statistics'))
        menu.AppendItem(menuItem)
        if len(data) != 1: menuItem.Enable(False)

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        saveFile = bosh.SaveFile(fileInfo)
        progress = balt.Progress(_("Statistics"))
        try:
            saveFile.load(SubProgress(progress,0,0.9))
            log = bolt.LogFile(stringBuffer())
            progress(0.9,_("Calculating statistics."))
            saveFile.logStats(log)
            progress.Destroy()
            text = log.out.getvalue()
            balt.showLog(self.window,text,fileName.s,asDialog=False,fixedFont=False,icons=bashBlue)
        finally:
            progress.Destroy()

#------------------------------------------------------------------------------
class Save_StatObse(Link):
    """Dump .obse records."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('.obse Statistics'))
        menu.AppendItem(menuItem)
        if len(data) != 1:
            menuItem.Enable(False)
        else:
            fileName = GPath(self.data[0])
            fileInfo = self.window.data[fileName]
            fileName = fileInfo.getPath().root+'.obse'
            menuItem.Enable(fileName.exists())

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        saveFile = bosh.SaveFile(fileInfo)
        progress = balt.Progress(_(".obse"))
        try:
            saveFile.load(SubProgress(progress,0,0.9))
            log = bolt.LogFile(stringBuffer())
            progress(0.9,_("Calculating statistics."))
            saveFile.logStatObse(log)
            progress.Destroy()
            text = log.out.getvalue()
            log.out.close()
            balt.showLog(self.window,text,fileName.s,asDialog=False,fixedFont=False,icons=bashBlue)
        finally:
            progress.Destroy()

#------------------------------------------------------------------------------
class Save_Unbloat(Link):
    """Unbloats savegame."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Remove Bloat...'))
        menu.AppendItem(menuItem)
        if len(data) != 1: menuItem.Enable(False)

    def Execute(self,event):
        #--File Info
        saveName = GPath(self.data[0])
        saveInfo = self.window.data[saveName]
        progress = balt.Progress(_("Scanning for Bloat"))
        delObjRefs = 0
        try:
            #--Scan and report
            saveFile = bosh.SaveFile(saveInfo)
            saveFile.load(SubProgress(progress,0,0.8))
            createdCounts,nullRefCount = saveFile.findBloating(SubProgress(progress,0.8,1.0))
            progress.Destroy()
            #--Dialog
            if not createdCounts and not nullRefCount:
                balt.showOk(self.window,_("No bloating found."),saveName.s)
                return
            message = ''
            if createdCounts:
                #message += _('Excess Created Objects\n')
                for type,name in sorted(createdCounts):
                    message += '  %s %s: %s\n' % (type,name,formatInteger(createdCounts[(type,name)]))
            if nullRefCount:
                message += _('  Null Ref Objects: %s\n') % (formatInteger(nullRefCount),)
            message = _("Remove savegame bloating?\n%s\nWARNING: This is a risky procedure that may corrupt your savegame! Use only if necessary!") % (message,)
            if not balt.askYes(self.window,message,_("Remove bloating?")):
                return
            #--Remove bloating
            progress = balt.Progress(_("Removing Bloat"))
            nums = saveFile.removeBloating(createdCounts.keys(),True,SubProgress(progress,0,0.9))
            progress(0.9,_("Saving..."))
            saveFile.safeSave()
            progress.Destroy()
            balt.showOk(self.window,
                _("Uncreated Objects: %d\nUncreated Refs: %d\nUnNulled Refs: %d") % nums,
                saveName.s)
            self.window.RefreshUI(saveName)
        finally:
            progress.Destroy()


#------------------------------------------------------------------------------
class Save_UpdateNPCLevels(Link):
    """Update NPC levels from active mods."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Update NPC Levels...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(data and bosh.modInfos.ordered))

    def Execute(self,event):
        debug = True
        message = _('This will relevel the NPCs in the selected save game(s) according to the npc levels in the currently active mods. This supercedes the older "Import NPC Levels" command.')
        if not balt.askContinue(self.window,message,'bash.updateNpcLevels.continue',_('Update NPC Levels')):
            return
        progress = balt.Progress(_('Update NPC Levels'))
        try:
            #--Loop over active mods
            offsetFlag = 0x80
            npc_info = {}
            loadFactory = bosh.LoadFactory(False,bosh.MreNpc)
            ordered = list(bosh.modInfos.ordered)
            subProgress = SubProgress(progress,0,0.4,len(ordered))
            modErrors = []
            for index,modName in enumerate(ordered):
                subProgress(index,_("Scanning ") + modName.s)
                modInfo = bosh.modInfos[modName]
                modFile = bosh.ModFile(modInfo,loadFactory)
                try:
                    modFile.load(True)
                except bosh.ModError, x:
                    modErrors.append(str(x))
                    continue
                if 'NPC_' not in modFile.tops: continue
                #--Loop over mod NPCs
                mapToOrdered = bosh.MasterMap(modFile.tes4.masters+[modName], ordered)
                for npc in modFile.NPC_.getActiveRecords():
                    fid = mapToOrdered(npc.fid,None)
                    if not fid: continue
                    npc_info[fid] = (npc.eid, npc.level, npc.calcMin, npc.calcMax, npc.flags.pcLevelOffset)
            #--Loop over savefiles
            subProgress = SubProgress(progress,0.4,1.0,len(self.data))
            message = _("NPCs Releveled:")
            for index,saveName in enumerate(self.data):
                #deprint(saveName, '==============================')
                subProgress(index,_("Updating ") + saveName.s)
                saveInfo = self.window.data[saveName]
                saveFile = bosh.SaveFile(saveInfo)
                saveFile.load()
                records = saveFile.records
                mapToOrdered = bosh.MasterMap(saveFile.masters, ordered)
                releveledCount = 0
                #--Loop over change records
                for recNum in xrange(len(records)):
                    releveled = False
                    (recId,recType,recFlags,version,data) = records[recNum]
                    orderedRecId = mapToOrdered(recId,None)
                    if recType != 35 or recId == 7 or orderedRecId not in npc_info: continue
                    (eid,level,calcMin,calcMax,pcLevelOffset) = npc_info[orderedRecId]
                    npc = bosh.SreNPC(recFlags,data)
                    acbs = npc.acbs
                    if acbs and (
                        (acbs.level != level) or
                        (acbs.calcMin != calcMin) or
                        (acbs.calcMax != calcMax) or
                        (acbs.flags.pcLevelOffset != pcLevelOffset)
                        ):
                        acbs.flags.pcLevelOffset = pcLevelOffset
                        acbs.level = level
                        acbs.calcMin = calcMin
                        acbs.calcMax = calcMax
                        (recId,recType,recFlags,version,data) = saveFile.records[recNum]
                        records[recNum] = (recId,recType,npc.getFlags(),version,npc.getData())
                        releveledCount += 1
                        saveFile.records[recNum] = npc.getTuple(recId,version)
                        #deprint(hex(recId), eid, acbs.level, acbs.calcMin, acbs.calcMax, acbs.flags.getTrueAttrs())
                #--Save changes?
                subProgress(index+0.5,_("Updating ") + saveName.s)
                if releveledCount:
                    saveFile.safeSave()
                message += '\n%d %s' % (releveledCount,saveName.s,)
            progress.Destroy()
            if modErrors:
                message += _("\n\nSome mods had load errors and were skipped:\n* ")
                message += '\n* '.join(modErrors)
            balt.showOk(self.window,message,_('Update NPC Levels'))
        finally:
            if progress: progress.Destroy()

# Screen Links ------------------------------------------------------------------
#------------------------------------------------------------------------------
class Screens_NextScreenShot(Link):
    """Sets screenshot base name and number."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Next Shot...'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        oblivionIni = bosh.oblivionIni
        base = oblivionIni.getSetting('Display','sScreenShotBaseName','ScreenShot')
        next = oblivionIni.getSetting('Display','iScreenShotIndex','0')
        rePattern = re.compile(r'^(.+?)(\d*)$',re.I)
        pattern = balt.askText(self.window,_("Screenshot base name, optionally with next screenshot number.\nE.g. ScreenShot or ScreenShot_101 or Subdir\\ScreenShot_201."),_("Next Shot..."),base+next)
        if not pattern: return
        maPattern = rePattern.match(pattern)
        newBase,newNext = maPattern.groups()
        settings = {LString('Display'):{
            LString('SScreenShotBaseName'): newBase,
            LString('iScreenShotIndex'): (newNext or next),
            LString('bAllowScreenShot'): '1',
            }}
        screensDir = GPath(newBase).head
        if screensDir:
            if not screensDir.isabs(): screensDir = bosh.dirs['app'].join(screensDir)
            screensDir.makedirs()
        oblivionIni.saveSettings(settings)
        bosh.screensData.refresh()
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class Screen_ConvertTo(Link):
    """Converts selected images to another type."""
    def __init__(self,ext,imageType):
        Link.__init__(self)
        self.ext = ext.lower()
        self.imageType = imageType

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Convert to %s') % self.ext)
        menu.AppendItem(menuItem)
        convertable = [name for name in self.data if GPath(name).cext != '.'+self.ext]
        menuItem.Enable(len(convertable) > 0)

    def Execute(self,event):
        srcDir = bosh.screensData.dir
        progress = balt.Progress(_("Converting to %s") % self.ext)
        try:
            progress.setFull(len(self.data))
            for index,fileName in enumerate(self.data):
                progress(index,fileName.s)
                srcPath = srcDir.join(fileName)
                destPath = srcPath.root+'.'+self.ext
                if srcPath == destPath or destPath.exists(): continue
                bitmap = wx.Image(srcPath.s)
                # This only has an effect on jpegs, so it's ok to do it on every kind
                bitmap.SetOptionInt(wx.IMAGE_OPTION_QUALITY,settings['bash.screens.jpgQuality'])
                result = bitmap.SaveFile(destPath.s,self.imageType)
                if not result: continue
                srcPath.remove()
        finally:
            if progress: progress.Destroy()
            self.window.data.refresh()
            self.window.RefreshUI()

#------------------------------------------------------------------------------
class Screen_JpgQuality(Link):
    """Sets JPEG quality for saving."""
    def __init__(self,quality):
        Link.__init__(self)
        self.quality = quality
        self.label = '%i' % self.quality

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,self.label,kind=wx.ITEM_RADIO)
        menu.AppendItem(menuItem)
        if self.quality == settings['bash.screens.jpgQuality']:
            menuItem.Check(True)

    def Execute(self,event):
        settings['bash.screens.jpgQuality'] = self.quality

#------------------------------------------------------------------------------
class Screen_JpgQualityCustom(Screen_JpgQuality):
    """Sets a custom JPG quality."""
    def __init__(self):
        Screen_JpgQuality.__init__(self,settings['bash.screens.jpgCustomQuality'])
        self.label = _('Custom [%i]') % self.quality

    def Execute(self,event):
        quality = balt.askNumber(self.window,_('JPEG Quality'),value=self.quality,min=0,max=100)
        if quality is None: return
        self.quality = quality
        settings['bash.screens.jpgCustomQuality'] = self.quality
        self.label = _('Custom [%i]') % quality
        Screen_JpgQuality.Execute(self,event)

#------------------------------------------------------------------------------
class Screen_Rename(Link):
    """Renames files by pattern."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Rename...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) > 0)

    def Execute(self,event):
        if len(self.data) > 0:
            index = self.window.list.FindItem(0,self.data[0].s)
            if index != -1:
                self.window.list.EditLabel(index)
# Messages Links ------------------------------------------------------------------
#------------------------------------------------------------------------------
class Messages_Archive_Import(Link):
    """Import messages from html message archive."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Import Archives...'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        textDir = settings.get('bash.workDir',bosh.dirs['app'])
        #--File dialog
        paths = balt.askOpenMulti(self.window,_('Import message archive(s):'),textDir,
            '', '*.html')
        if not paths: return
        settings['bash.workDir'] = paths[0].head
        for path in paths:
            bosh.messages.importArchive(path)
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class Message_Delete(Link):
    """Delete the file and all backups."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menu.AppendItem(wx.MenuItem(menu,self.id,_('Delete')))

    def Execute(self,event):
        message = _(r'Delete these %d message(s)? This operation cannot be undone.') % (len(self.data),)
        if not balt.askYes(self.window,message,_('Delete Messages')):
            return
        #--Do it
        for message in self.data:
            self.window.data.delete(message)
        #--Refresh stuff
        self.window.RefreshUI()

# People Links ------------------------------------------------------------------
#------------------------------------------------------------------------------
class People_AddNew(Link):
    """Add a new record."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Add...'))
        menu.AppendItem(menuItem)
        self.title = _('Add New Person')

    def Execute(self,event):
        name = balt.askText(self.gTank,_("Add new person:"),self.title)
        if not name: return
        if name in self.data:
            return balt.showInfo(self.gTank,name+_(" already exists."),self.title)
        self.data[name] = (time.time(),0,'')
        self.gTank.RefreshUI(details=name)
        self.gTank.gList.EnsureVisible(self.gTank.GetIndex(name))
        self.data.setChanged()

#------------------------------------------------------------------------------
class People_Export(Link):
    """Export people to text archive."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Export...'))
        menu.AppendItem(menuItem)
        self.title = _("Export People")

    def Execute(self,event):
        textDir = settings.get('bash.workDir',bosh.dirs['app'])
        #--File dialog
        path = balt.askSave(self.gTank,_('Export people to text file:'),textDir,
            'People.txt', '*.txt')
        if not path: return
        settings['bash.workDir'] = path.head
        self.data.dumpText(path,self.selected)
        balt.showInfo(self.gTank,_('Records exported: %d.') % (len(self.selected),),self.title)

#------------------------------------------------------------------------------
class People_Import(Link):
    """Import people from text archive."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Import...'))
        menu.AppendItem(menuItem)
        self.title = _("Import People")

    def Execute(self,event):
        textDir = settings.get('bash.workDir',bosh.dirs['app'])
        #--File dialog
        path = balt.askOpen(self.gTank,_('Import people from text file:'),textDir,
            '', '*.txt',mustExist=True)
        if not path: return
        settings['bash.workDir'] = path.head
        newNames = self.data.loadText(path)
        balt.showInfo(self.gTank,_("People imported: %d") % (len(newNames),),self.title)
        self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class People_Karma(Link):
    """Add Karma setting links."""

    def AppendToMenu(self,menu,window,data):
        """Append Karma item submenu."""
        Link.AppendToMenu(self,menu,window,data)
        idList = ID_GROUPS
        labels = ['%+d' % (x,) for x in range(5,-6,-1)]
        subMenu = wx.Menu()
        for id,item in zip(idList,labels):
            subMenu.Append(id,item)
        wx.EVT_MENU_RANGE(bashFrame,idList.BASE,idList.MAX,self.DoList)
        menu.AppendMenu(-1,'Karma',subMenu)

    def DoList(self,event):
        """Handle selection of label."""
        idList = ID_GROUPS
        karma = range(5,-6,-1)[event.GetId()-idList.BASE]
        for item in self.selected:
            text = self.data[item][2]
            self.data[item] = (time.time(),karma,text)
        self.gTank.RefreshUI()
        self.data.setChanged()

# Masters Links ---------------------------------------------------------------
#------------------------------------------------------------------------------
class Master_ChangeTo(Link):
    """Rename/replace master through file dialog."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_("Change to..."))
        menu.AppendItem(menuItem)
        menuItem.Enable(self.window.edited)

    def Execute(self,event):
        itemId = self.data[0]
        masterInfo = self.window.data[itemId]
        masterName = masterInfo.name
        #--File Dialog
        wildcard = _('Oblivion Mod Files')+' (*.esp;*.esm)|*.esp;*.esm'
        newPath = balt.askOpen(self.window,_('Change master name to:'),
            bosh.modInfos.dir, masterName, wildcard,mustExist=True)
        if not newPath: return
        (newDir,newName) = newPath.headTail
        #--Valid directory?
        if newDir != bosh.modInfos.dir:
            balt.showError(self.window,
                _("File must be selected from Oblivion Data Files directory."))
            return
        elif newName == masterName:
            return
        #--Save Name
        masterInfo.setName(newName)
        self.window.ReList()
        self.window.PopulateItems()
        settings.getChanged('bash.mods.renames')[masterName] = newName

#------------------------------------------------------------------------------
class Master_Disable(Link):
    """Rename/replace master through file dialog."""
    def AppendToMenu(self,menu,window,data):
        if window.fileInfo.isMod(): return #--Saves only
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_("Disable"))
        menu.AppendItem(menuItem)
        menuItem.Enable(self.window.edited)

    def Execute(self,event):
        itemId = self.data[0]
        masterInfo = self.window.data[itemId]
        masterName = masterInfo.name
        newName = GPath(re.sub('[mM]$','p','XX'+masterName.s))
        #--Save Name
        masterInfo.setName(newName)
        self.window.ReList()
        self.window.PopulateItems()

# App Links -------------------------------------------------------------------
#------------------------------------------------------------------------------
class App_Button(Link):
    """Launch an application."""
    obseButtons = []

    def __init__(self,exePathArgs,image,tip,obseTip=None,obseArg=None):
        """Initialize
        exePathArgs (string): exePath
        exePathArgs (tuple): (exePath,*exeArgs)"""
        Link.__init__(self)
        self.gButton = None
        if isinstance(exePathArgs,tuple):
            self.exePath = exePathArgs[0]
            self.exeArgs = exePathArgs[1:]
        else:
            self.exePath = exePathArgs
            self.exeArgs = tuple()
        self.image = image
        self.tip = tip
        #--Exe stuff
        if self.exePath and self.exePath.ext.lower() == '.exe': #Sometimes exePath is "None"
            self.isExe = True
        else:
            self.isExe = False
        #--Java stuff
        if self.exePath and self.exePath.ext.lower() == '.jar': #Sometimes exePath is "None"
            self.isJava = True
            self.java = GPath(os.environ['SYSTEMROOT']).join('system32','javaw.exe')
            self.jar = self.exePath
            self.appArgs = ''.join(self.exeArgs)
        else:
            self.isJava = False
        #--OBSE stuff
        self.obseTip = obseTip
        self.obseArg = obseArg
        exeObse = bosh.dirs['app'].join('obse_loader.exe')

    def IsPresent(self):
        if self.isJava:
            return self.java.exists() and self.jar.exists()
        else:
            if self.exePath in bosh.undefinedPaths:
                return False
            return self.exePath.exists()

    def GetBitmapButton(self,window,style=0):
        if self.IsPresent():
            self.gButton = bitmapButton(window,self.image.GetBitmap(),style=style,
                onClick=self.Execute,tip=self.tip)
            if self.obseTip != None:
                App_Button.obseButtons.append(self)
                exeObse = bosh.dirs['app'].join('obse_loader.exe')
                if settings.get('bash.obse.on',False) and exeObse.exists():
                    self.gButton.SetToolTip(tooltip(self.obseTip))
            return self.gButton
        else:
            return None

    def Execute(self,event,extraArgs=None):
        if self.IsPresent():
            if self.isJava:
                cwd = bolt.Path.getcwd()
                self.jar.head.setcwd()
                try:
                    subprocess.Popen((self.java.stail,'-jar',self.jar.stail,self.appArgs), executable=self.java.s, close_fds=True) #close_fds is needed for the one instance checker
                except Exception, error:
                    print error
                    print _("Used Path: %s") % exePath.s
                    print _("Used Arguments: "), exeArgs
                    print
                    raise
                finally:
                    cwd.setcwd()
            elif self.isExe:
                exeObse = bosh.dirs['app'].join('obse_loader.exe')
                exeArgs = ' '.join(self.exeArgs)
                if self.obseArg != None and settings.get('bash.obse.on',False) and exeObse.exists():
                    if bosh.inisettings['SteamInstall'] and '\\oblivion.exe' in self.exePath.s:
                        exePath = self.exePath
                    else:
                        exePath = exeObse
                    if self.obseArg != '': exeArgs += " %s" % self.obseArg
                else:
                    exePath = self.exePath
                if extraArgs: exeArgs += ' '+' '.join(extraArgs)
                statusBar.SetStatusText(exeArgs,1)
                cwd = bolt.Path.getcwd()
                exePath.head.setcwd()
                try:
                    subprocess.Popen(exeArgs, executable=exePath.s, close_fds=True) #close_fds is needed for the one instance checker
                except Exception, error:
                    print error
                    print _("Used Path: %s") % exePath.s
                    print _("Used Arguments: "), exeArgs
                    print
                    raise
                finally:
                    cwd.setcwd()
            else:
                try:
                    os.startfile(self.exePath.s, (str(self.exeArgs))[2:-3])
                except Exception, error:
                    print error
                    print _("Used Path: %s") % exePath.s
                    print _("Used Arguments: "), exeArgs
                    print
                    raise
        else:
            raise StateError('Application missing: %s' % self.exePath.s)

class App_Tes4Gecko(App_Button):
    """Left in for unpickling compatibility reasons."""
    def __setstate__(self, state):
        self.__dict__.update(state)
        self.__class__ = App_Button


class App_OblivionBookCreator(App_Button):
    """Left in for unpickling compatibility reasons."""
    def __setstate__(self, state):
        self.__dict__.update(state)
        self.__class__ = App_Button
#------------------------------------------------------------------------------
class App_Tes4View(App_Button):
    """Allow some extra args for Tes4View."""

# arguments
# -fixup (wbAllowInternalEdit true default)
# -nofixup (wbAllowInternalEdit false)
# -showfixup (wbShowInternalEdit true default)
# -hidefixup (wbShowInternalEdit false)
# -skipbsa (wbLoadBSAs false)
# -forcebsa (wbLoadBSAs true default)
# -fixuppgrd
# -IKnowWhatImDoing
# -FNV
#  or name begins with FNV
# -FO3
#  or name begins with FO3
# -TES4
#  or name begins with TES4
# -lodgen
#  or name ends with LODGen.exe
#  (requires TES4 mode)
# -masterupdate
#  or name ends with MasterUpdate.exe
#  (requires FO3 or FNV)
#  -filteronam
#  -FixPersistence
#  -NoFixPersistence
# -masterrestore
#  or name ends with MasterRestore.exe
#  (requires FO3 or FNV)
# -edit
#  or name ends with Edit.exe
# -translate
#  or name ends with Trans.exe

    def IsPresent(self):
        if self.exePath in bosh.undefinedPaths or not self.exePath.exists():
            testPath = bosh.tooldirs['Tes4ViewPath']
            if testPath not in bosh.undefinedPaths and testPath.exists():
                self.exePath = testPath
                return True
            return False
        return True

    def Execute(self,event):
        extraArgs = []
        if wx.GetKeyState(wx.WXK_CONTROL):
            extraArgs.append('-FixupPGRD')
        if wx.GetKeyState(wx.WXK_SHIFT):
            extraArgs.append('-skipbsa')
        if settings['tes4View.iKnowWhatImDoing']:
            extraArgs.append('-IKnowWhatImDoing')
        App_Button.Execute(self,event,tuple(extraArgs))

#------------------------------------------------------------------------------
class App_BOSS(App_Button):
    """loads BOSS"""

    def Execute(self,event,extraArgs=None):
        if self.IsPresent():
            exeObse = bosh.dirs['app'].join('obse_loader.exe')
            exeArgs = self.exeArgs
            if self.obseArg != None and settings.get('bash.obse.on',False) and exeObse.exists():
                exePath = exeObse
                if self.obseArg != '': exeArgs += (self.obseArg,)
            else:
                exePath = self.exePath
            exeArgs = (exePath.stail,)+exeArgs
            if extraArgs: exeArgs += extraArgs
            statusBar.SetStatusText(' '.join(exeArgs),1)
            cwd = bolt.Path.getcwd()
            exePath.head.setcwd()
            progress = balt.Progress(_("Executing BOSS"))
            version = bosh.configHelpers.bossVersion
            if settings.get('bash.mods.autoGhost') and not version:
                progress(0.05,_("Processing... deghosting mods"))
                for fileName in bosh.modInfos:
                    bosh.modInfos[fileName].setGhost(False)
            if version >= 1:
                if settings['BOSS.AlwaysUpdate'] or wx.GetKeyState(85):
                    exeArgs += ('-u',) # Update - BOSS version 1.6+
                if wx.GetKeyState(82) and wx.GetKeyState(wx.WXK_SHIFT):
                    exeArgs += ('-r 2',) # Revert level 2 - BOSS version 1.6+
                elif wx.GetKeyState(82):
                    exeArgs += ('-r 1',) # Revert level 1 - BOSS version 1.6+
                if wx.GetKeyState(83):
                    exeArgs += ('-s',) # Silent Mode - BOSS version 1.6+
            if version in [1, 393217]:
                if wx.GetKeyState(86):
                    exeArgs += ('-V-',) # Disable version parsing - syntax BOSS version 1.6 - 1.6.1
            elif version >= 393218:
                if wx.GetKeyState(86) or wx.GetKeyState(78):
                    exeArgs += ('-n',) # Disable version parsing - syntax BOSS version 1.6.2+
            progress(0.05,_("Processing... launching BOSS."))
            try:
                subprocess.call((exePath.s,) + exeArgs[1:], startupinfo=bosh.startupinfo)
                # Clear the saved times from before
                bosh.modInfos.mtimes.clear()
                # And refresh to get the new times so WB will keep the order that BOSS specifies
                bosh.modInfos.refresh(doInfos=False)
            except Exception, error:
                print error
                print _("Used Path: %s") % exePath.s
                print _("Used Arguments: "), exeArgs
                print
                raise
            finally:
                if progress: progress.Destroy()
                cwd.setcwd()
        else:
            raise StateError('Application missing: %s' % self.exePath.s)

#------------------------------------------------------------------------------
class Oblivion_Button(App_Button):
    """Will close app on execute if autoquit is on."""
    def Execute(self,event):
        App_Button.Execute(self,event)
        if settings.get('bash.autoQuit.on',False):
            bashFrame.Close()

#------------------------------------------------------------------------------
class Obse_Button(Link):
    """Obse on/off state button."""
    def __init__(self):
        Link.__init__(self)
        self.gButton = None

    def SetState(self,state=None):
        """Sets state related info. If newState != none, sets to new state first.
        For convenience, returns state when done."""
        if state == None: #--Default
            state = settings.get('bash.obse.on',False)
        elif state == -1: #--Invert
            state = not settings.get('bash.obse.on',False)
        settings['bash.obse.on'] = state
        image = images[('checkbox.green.off.' + bosh.inisettings['IconSize'],'checkbox.green.on.' + bosh.inisettings['IconSize'])[state]]
        tip = (_("OBSE Disabled"),_("OBSE Enabled"))[state]
        self.gButton.SetBitmapLabel(image.GetBitmap())
        self.gButton.SetToolTip(tooltip(tip))
        tipAttr = ('tip','obseTip')[state]
        for button in App_Button.obseButtons:
            button.gButton.SetToolTip(tooltip(getattr(button,tipAttr,'')))

    def GetBitmapButton(self,window,style=0):
        exeObse = bosh.dirs['app'].join('obse_loader.exe')
        if exeObse.exists():
            bitmap = images['checkbox.green.off.' + bosh.inisettings['IconSize']].GetBitmap()
            self.gButton = bitmapButton(window,bitmap,style=style,onClick=self.Execute)
            self.SetState()
            return self.gButton
        else:
            return None

    def Execute(self,event):
        """Invert state."""
        self.SetState(-1)

#------------------------------------------------------------------------------
class AutoQuit_Button(Link):
    """Button toggling application closure when launching Oblivion."""
    def __init__(self):
        Link.__init__(self)
        self.gButton = None

    def SetState(self,state=None):
        """Sets state related info. If newState != none, sets to new state first.
        For convenience, returns state when done."""
        if state == None: #--Default
            state = settings.get('bash.autoQuit.on',False)
        elif state == -1: #--Invert
            state = not settings.get('bash.autoQuit.on',False)
        settings['bash.autoQuit.on'] = state
        image = images[('checkbox.red.off.' + bosh.inisettings['IconSize'],'checkbox.red.x.' + bosh.inisettings['IconSize'])[state]]
        tip = (_("Auto-Quit Disabled"),_("Auto-Quit Enabled"))[state]
        self.gButton.SetBitmapLabel(image.GetBitmap())
        self.gButton.SetToolTip(tooltip(tip))

    def GetBitmapButton(self,window,style=0):
        bitmap = images['checkbox.red.off.' + bosh.inisettings['IconSize']].GetBitmap()
        self.gButton = bitmapButton(window,bitmap,style=style,onClick=self.Execute)
        self.SetState()
        return self.gButton

    def Execute(self,event):
        """Invert state."""
        self.SetState(-1)

#------------------------------------------------------------------------------
class App_Help(Link):
    """Show help browser."""
    def GetBitmapButton(self,window,style=0):
        if not self.id: self.id = wx.NewId()
        gButton = bitmapButton(window,images['help'].GetBitmap(),style=style,
            onClick=self.Execute,tip=_("Help File"))
        return gButton

    def Execute(self,event):
        """Handle menu selection."""
        html = bosh.dirs['mopy'].join('Wrye Bash.html')
        if not html.exists():
            bolt.WryeText.genHtml(bosh.dirs['mopy'].join('Wrye Bash.txt').s, None, bosh.dirs['mopy'])
        html.start()

#------------------------------------------------------------------------------
class App_DocBrowser(Link):
    """Show doc browser."""
    def GetBitmapButton(self,window,style=0):
        if not self.id: self.id = wx.NewId()

        gButton = bitmapButton(window,Image(r'images/DocBrowser'+bosh.inisettings['IconSize']+'.png').GetBitmap(),style=style,
            onClick=self.Execute,tip=_("Doc Browser"))
        return gButton

    def Execute(self,event):
        """Handle menu selection."""
        if not docBrowser:
            DocBrowser().Show()
            settings['bash.modDocs.show'] = True
        #balt.ensureDisplayed(docBrowser)
        docBrowser.Raise()

#------------------------------------------------------------------------------
class App_ModChecker(Link):
    """Show mod checker."""
    def GetBitmapButton(self,window,style=0):
        if not self.id: self.id = wx.NewId()
        gButton = bitmapButton(window,Image(r'images/ModChecker'+bosh.inisettings['IconSize']+'.png').GetBitmap(),style=style,
            onClick=self.Execute,tip=_("Mod Checker"))
        return gButton

    def Execute(self,event):
        """Handle menu selection."""
        if not modChecker:
            ModChecker().Show()
        #balt.ensureDisplayed(docBrowser)
        modChecker.Raise()

# Initialization --------------------------------------------------------------
def InitSettings():
    """Initializes settings dictionary for bosh and basher."""
    bosh.initSettings()
    global settings
    balt._settings = bosh.settings
    balt.sizes = bosh.settings.getChanged('bash.window.sizes',{})
    settings = bosh.settings
    settings.loadDefaults(settingDefaults)
    #--Wrye Balt
    settings['balt.WryeLog.temp'] = bosh.dirs['saveBase'].join('WryeLogTemp.html')
    settings['balt.WryeLog.cssDir'] = bosh.dirs['mods'].join('Docs')

def InitImages():
    """Initialize color and image collections."""
    #--Colors
    colors['bash.esm'] = (220,220,255)
    colors['bash.doubleTime.not'] = (255,255,255)
    colors['bash.doubleTime.exists'] = (255,220,220)
    colors['bash.doubleTime.load'] = (255,100,100)
    colors['bash.exOverLoaded'] = (0xFF,0x99,0)
    colors['bash.masters.remapped'] = (100,255,100)
    colors['bash.masters.changed'] = (220,255,220)
    colors['bash.mods.isMergeable'] = (0x00,0x99,0x00)
    colors['bash.mods.isSemiMergeable'] = (153,0,153)
    colors['bash.mods.groupHeader'] = (0xD8,0xD8,0xD8)
    colors['bash.mods.isGhost'] = (0xe8,0xe8,0xe8)
    colors['bash.installers.skipped'] = (0xe0,0xe0,0xe0)
    colors['bash.installers.outOfOrder'] = (0xDF,0xDF,0xC5)
    colors['bash.installers.dirty'] = (0xFF,0xBB,0x33)
    colors['bash.ini.invalid'] = (0xFF,0xD5,0xAA)
    colors['bash.ini.mismatched'] = (0xFF,0xFF,0xBF)
    colors['bash.ini.matched'] = (0xC1,0xFF,0xC1)

    #--Standard
    images['save.on'] = Image(r'images/save_on.png',wx.BITMAP_TYPE_PNG)
    images['save.off'] = Image(r'images/save_off.png',wx.BITMAP_TYPE_PNG)
    #--Misc
    #images['oblivion'] = Image(r'images/oblivion.png',wx.BITMAP_TYPE_PNG)
    images['help'] = Image(r'images/help'+bosh.inisettings['IconSize']+'.png',wx.BITMAP_TYPE_PNG)
    #--Tools
    images['doc.on'] = Image(r'images/page_find'+bosh.inisettings['IconSize']+'.png',wx.BITMAP_TYPE_PNG)
    images['bashmon'] = Image(r'images/bashmon'+bosh.inisettings['IconSize']+'.png',wx.BITMAP_TYPE_PNG)
    images['modChecker'] = Image(r'images/table_error'+bosh.inisettings['IconSize']+'.png',wx.BITMAP_TYPE_PNG)
    #--ColorChecks
    images['checkbox.red.x'] = Image(r'images/checkbox_red_x.png',wx.BITMAP_TYPE_PNG)
    images['checkbox.red.x.16'] = Image(r'images/checkbox_red_x.png',wx.BITMAP_TYPE_PNG)
    images['checkbox.red.x.32'] = Image(r'images/checkbox_red_x_32.png',wx.BITMAP_TYPE_PNG)
    images['checkbox.red.off.16'] = (Image(r'images/checkbox_red_off.png',wx.BITMAP_TYPE_PNG))
    images['checkbox.red.off.32'] = (Image(r'images/checkbox_red_off_32.png',wx.BITMAP_TYPE_PNG))

    images['checkbox.green.on.16'] = (Image(r'images/checkbox_green_on.png',wx.BITMAP_TYPE_PNG))
    images['checkbox.green.off.16'] = (Image(r'images/checkbox_green_off.png',wx.BITMAP_TYPE_PNG))
    images['checkbox.green.on.32'] = (Image(r'images/checkbox_green_on_32.png',wx.BITMAP_TYPE_PNG))
    images['checkbox.green.off.32'] = (Image(r'images/checkbox_green_off_32.png',wx.BITMAP_TYPE_PNG))
    #--Bash
    images['bash.16'] = Image(r'images/bash_16.png',wx.BITMAP_TYPE_PNG)
    images['bash.32'] = Image(r'images/bash_32.png',wx.BITMAP_TYPE_PNG)
    images['bash.16.blue'] = Image(r'images/bash_16_blue.png',wx.BITMAP_TYPE_PNG)
    images['bash.32.blue'] = Image(r'images/bash_32_blue.png',wx.BITMAP_TYPE_PNG)
    #--Bash Patch Dialogue
    images['monkey.16'] = Image(r'images/wryemonkey16.jpg',wx.BITMAP_TYPE_JPEG)
  #  images['monkey.32'] = Image(r'images/wryemonkey32.jpg',wx.BITMAP_TYPE_JPEG)
    #--DocBrowser
    images['doc.16'] = Image(r'images/DocBrowser16.png',wx.BITMAP_TYPE_PNG)
    images['doc.32'] = Image(r'images/DocBrowser32.png',wx.BITMAP_TYPE_PNG)
    #--Applications Icons
    global bashRed
    bashRed = balt.ImageBundle()
    bashRed.Add(images['bash.16'])
    bashRed.Add(images['bash.32'])
    #--Application Subwindow Icons
    global bashBlue
    bashBlue = balt.ImageBundle()
    bashBlue.Add(images['bash.16.blue'])
    bashBlue.Add(images['bash.32.blue'])
    global bashDocBrowser
    bashDocBrowser = balt.ImageBundle()
    bashDocBrowser.Add(images['doc.16'])
    bashDocBrowser.Add(images['doc.32'])
    global bashMonkey
    bashMonkey = balt.ImageBundle()
    bashMonkey.Add(images['monkey.16'])

def InitStatusBar():
    """Initialize status bar links."""
    #--Bash Status/LinkBar
    BashStatusBar.buttons.append(Obse_Button())
    BashStatusBar.buttons.append(AutoQuit_Button())
    BashStatusBar.buttons.append( #OBLIVION
        Oblivion_Button(
            bosh.dirs['app'].join('Oblivion.exe'),
            Image(r'images/oblivion'+bosh.inisettings['IconSize']+'.png'),
            _("Launch Oblivion"),
            _("Launch Oblivion + OBSE"),
            ''))
    BashStatusBar.buttons.append( #TESCS
        App_Button(
            bosh.dirs['app'].join('TESConstructionSet.exe'),
            Image(r'images/tescs'+bosh.inisettings['IconSize']+'.png'),
            _("Launch TESCS"),
            _("Launch TESCS + OBSE"),
            '-editor'))
    BashStatusBar.buttons.append( #OBMM
        App_Button(
            bosh.dirs['app'].join('OblivionModManager.exe'),
            Image(r'images/obmm'+bosh.inisettings['IconSize']+'.png'),
            _("Launch OBMM")))
    BashStatusBar.buttons.append( #ISOBL
        App_Button(
            bosh.tooldirs['ISOBL'],
            Image(r'images/ISOBL'+bosh.inisettings['IconSize']+'.png'),
            _("Launch InsanitySorrow's Oblivion Launcher")))
    BashStatusBar.buttons.append( #ISRMG
        App_Button(
            bosh.tooldirs['ISRMG'],
            Image(r"images/Insanity'sReadmeGenerator"+bosh.inisettings['IconSize']+'.png'),
            _("Launch InsanitySorrow's Readme Generator")))
    BashStatusBar.buttons.append( #ISRNG
        App_Button(
            bosh.tooldirs['ISRNG'],
            Image(r"images/Insanity'sRNG"+bosh.inisettings['IconSize']+'.png'),
            _("Launch InsanitySorrow's Random Name Generator")))
    BashStatusBar.buttons.append( #ISRNPCG
        App_Button(
            bosh.tooldirs['ISRNPCG'],
            Image(r'images/RandomNPC'+bosh.inisettings['IconSize']+'.png'),
            _("Launch InsanitySorrow's Random NPC Generator")))
    BashStatusBar.buttons.append( #OBFEL
        App_Button(
            bosh.tooldirs['OBFEL'],
            Image(r'images/OblivionFaceExchangerLite'+bosh.inisettings['IconSize']+'.png'),
            _("Oblivion Face Exchange Lite")))
    BashStatusBar.buttons.append( #OBMLG
        App_Button(
            bosh.tooldirs['OBMLG'],
            Image(r'images/ModListGenerator'+bosh.inisettings['IconSize']+'.png'),
            _("Oblivion Mod List Generator")))
    BashStatusBar.buttons.append( #OblivionBookCreator
        App_Button(
            (bosh.tooldirs['OblivionBookCreatorPath'],bosh.inisettings['OblivionBookCreatorJavaArg']),
            Image(r'images/OblivionBookCreator'+bosh.inisettings['IconSize']+'.png'),
            _("Launch Oblivion Book Creator")))
    BashStatusBar.buttons.append( #BSACommander
        App_Button(
            bosh.tooldirs['BSACMD'],
            Image(r'images/BSACommander'+bosh.inisettings['IconSize']+'.png'),
            _("Launch BSA Commander")))
    BashStatusBar.buttons.append( #Tabula
        App_Button(
            bosh.tooldirs['Tabula'],
            Image(r'images/Tabula'+bosh.inisettings['IconSize']+'.png'),
            _("Launch Tabula")))
    BashStatusBar.buttons.append( #Tes4Files
        App_Button(
            bosh.tooldirs['Tes4FilesPath'],
            Image(r'images/tes4files'+bosh.inisettings['IconSize']+'.png'),
            _("Launch TES4Files")))
    BashStatusBar.buttons.append( #Tes4Gecko
        App_Button(
            (bosh.tooldirs['Tes4GeckoPath'],bosh.inisettings['Tes4GeckoJavaArg']),
            Image(r'images/TES4Gecko'+bosh.inisettings['IconSize']+'.png'),
            _("Launch Tes4Gecko")))
    BashStatusBar.buttons.append( #Tes4View
        App_Tes4View(
            (bosh.tooldirs['Tes4ViewPath'],'-TES4'), #no cmd argument to force view mode
            Image(r'images/tes4view'+bosh.inisettings['IconSize']+'.png'),
            _("Launch TES4View")))
    BashStatusBar.buttons.append( #Tes4Edit
        App_Tes4View(
            (bosh.tooldirs['Tes4EditPath'],'-TES4 -edit'),
            Image(r'images/TES4Edit'+bosh.inisettings['IconSize']+'.png'),
            _("Launch TES4Edit")))
    BashStatusBar.buttons.append( #Tes4Trans
        App_Tes4View(
            (bosh.tooldirs['Tes4TransPath'],'-TES4 -translate'),
            Image(r'images/TES4Trans'+bosh.inisettings['IconSize']+'.png'),
            _("Launch TES4Trans")))
    BashStatusBar.buttons.append( #Tes4LODGen
        App_Tes4View(
            (bosh.tooldirs['Tes4LodGenPath'],'-TES4 -lodgen'),
            Image(r'images/Tes4LODGen'+bosh.inisettings['IconSize']+'.png'),
            _("Launch Tes4LODGen")))
    configHelpers = bosh.ConfigHelpers()
    configHelpers.refresh()
    version = configHelpers.bossVersion
    if version > 2: version = 1
    elif version < 0: version = 0
    BashStatusBar.buttons.append( #BOSS --
        App_BOSS(
            (bosh.dirs['app'].join('Data\\BOSS.bat'),bosh.dirs['app'].join('Data\\BOSS.exe'),bosh.dirs['app'].join('BOSS\\BOSS.exe'))[version],
            Image(r'images/Boss'+bosh.inisettings['IconSize']+'.png'),
            _("Launch BOSS")))
    if bosh.inisettings['ShowModelingToolLaunchers']:
        BashStatusBar.buttons.append( #AutoCad
            App_Button(
                bosh.tooldirs['AutoCad'],
                Image(r'images/AutoCad'+bosh.inisettings['IconSize']+'.png'),
                _("Launch AutoCad")))
        BashStatusBar.buttons.append( #Blender
            App_Button(
                bosh.tooldirs['BlenderPath'],
                Image(r'images/Blender'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Blender")))
        BashStatusBar.buttons.append( #Dogwaffle
            App_Button(
                bosh.tooldirs['Dogwaffle'],
                Image(r'images/Dogwaffle'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Dogwaffle")))
        BashStatusBar.buttons.append( #GMax
            App_Button(
                bosh.tooldirs['GmaxPath'],
                Image(r'images/gmax'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Gmax")))
        BashStatusBar.buttons.append( #Maya
            App_Button(
                bosh.tooldirs['MayaPath'],
                Image(r'images/Maya'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Maya")))
        BashStatusBar.buttons.append( #Max
            App_Button(
                bosh.tooldirs['MaxPath'],
                Image(r'images/3dsMax'+bosh.inisettings['IconSize']+'.png'),
                _("Launch 3dsMax")))
        BashStatusBar.buttons.append( #Milkshape3D
            App_Button(
                bosh.tooldirs['Milkshape3D'],
                Image(r'images/Milkshape3D'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Milkshape 3D")))
        BashStatusBar.buttons.append( #Mudbox
            App_Button(
                bosh.tooldirs['Mudbox'],
                Image(r'images/Mudbox'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Mudbox")))
        BashStatusBar.buttons.append( #Sculptris
            App_Button(
                bosh.tooldirs['Sculptris'],
                Image(r'images/Sculptris'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Sculptris")))
        BashStatusBar.buttons.append( #Softimage Mod Tool
            App_Button(
                (bosh.tooldirs['SoftimageModTool'],'-mod'),
                Image(r'images/SoftimageModTool'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Softimage Mod Tool")))
        BashStatusBar.buttons.append( #SpeedTree
            App_Button(
                bosh.tooldirs['SpeedTree'],
                Image(r'images/SpeedTree'+bosh.inisettings['IconSize']+'.png'),
                _("Launch SpeedTree")))
        BashStatusBar.buttons.append( #Tree[d]
            App_Button(
                bosh.tooldirs['Treed'],
                Image(r'images/Treed'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Tree\[d\]")))
        BashStatusBar.buttons.append( #Wings3D
            App_Button(
                bosh.tooldirs['Wings3D'],
                Image(r'images/Wings3D'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Wings 3D")))
    if bosh.inisettings['ShowModelingToolLaunchers'] or bosh.inisettings['ShowTextureToolLaunchers']:
        BashStatusBar.buttons.append( #Nifskope
            App_Button(
                bosh.tooldirs['NifskopePath'],
                Image(r'images/nifskope'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Nifskope")))
    if bosh.inisettings['ShowTextureToolLaunchers']:
        BashStatusBar.buttons.append( #AniFX
            App_Button(
                bosh.tooldirs['AniFX'],
                Image(r'images/AniFX'+bosh.inisettings['IconSize']+'.png'),
                _("Launch AniFX")))
        BashStatusBar.buttons.append( #Art Of Illusion
            App_Button(
                bosh.tooldirs['ArtOfIllusion'],
                Image(r'images/ArtOfIllusion'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Art Of Illusion")))
        BashStatusBar.buttons.append( #Artweaver
            App_Button(
                bosh.tooldirs['Artweaver'],
                Image(r'images/artweaver'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Artweaver")))
        BashStatusBar.buttons.append( #CrazyBump
            App_Button(
                bosh.tooldirs['CrazyBump'],
                Image(r'images/CrazyBump'+bosh.inisettings['IconSize']+'.png'),
                _("Launch CrazyBump")))
        BashStatusBar.buttons.append( #DDSConverter
            App_Button(
                bosh.tooldirs['DDSConverter'],
                Image(r'images/DDSConverter'+bosh.inisettings['IconSize']+'.png'),
                _("Launch DDSConverter")))
        BashStatusBar.buttons.append( #DeepPaint
            App_Button(
                bosh.tooldirs['DeepPaint'],
                Image(r'images/DeepPaint'+bosh.inisettings['IconSize']+'.png'),
                _("Launch DeepPaint")))
        BashStatusBar.buttons.append( #FastStone Image Viewer
            App_Button(
                bosh.tooldirs['FastStone'],
                Image(r'images/FastStoneImageViewer'+bosh.inisettings['IconSize']+'.png'),
                _("Launch FastStone Image Viewer")))
        BashStatusBar.buttons.append( #Genetica
            App_Button(
                bosh.tooldirs['Genetica'],
                Image(r'images/Genetica'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Genetica")))
        BashStatusBar.buttons.append( #Genetica Viewer
            App_Button(
                bosh.tooldirs['GeneticaViewer'],
                Image(r'images/GeneticaViewer'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Genetica Viewer")))
        BashStatusBar.buttons.append( #GIMP
            App_Button(
                bosh.tooldirs['GIMP'],
                Image(r'images/gimp'+bosh.inisettings['IconSize']+'.png'),
                _("Launch GIMP")))
        BashStatusBar.buttons.append( #GIMP Shop
            App_Button(
                bosh.tooldirs['GimpShop'],
                Image(r'images/GIMPShop'+bosh.inisettings['IconSize']+'.png'),
                _("Launch GIMP Shop")))
        BashStatusBar.buttons.append( #IcoFX
            App_Button(
                bosh.tooldirs['IcoFX'],
                Image(r'images/IcoFX'+bosh.inisettings['IconSize']+'.png'),
                _("Launch IcoFX")))
        BashStatusBar.buttons.append( #Inkscape
            App_Button(
                bosh.tooldirs['Inkscape'],
                Image(r'images/Inkscape'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Inkscape")))
        BashStatusBar.buttons.append( #IrfanView
            App_Button(
                bosh.tooldirs['IrfanView'],
                Image(r'images/IrfanView'+bosh.inisettings['IconSize']+'.png'),
                _("Launch IrfanView")))
        BashStatusBar.buttons.append( #MaPZone
            App_Button(
                bosh.tooldirs['MaPZone'],
                Image(r'images/MaPZone'+bosh.inisettings['IconSize']+'.png'),
                _("Launch MaPZone")))
        BashStatusBar.buttons.append( #MyPaint
            App_Button(
                bosh.tooldirs['MyPaint'],
                Image(r'images/MyPaint'+bosh.inisettings['IconSize']+'.png'),
                _("Launch MyPaint")))
        BashStatusBar.buttons.append( #NVIDIAMelody
            App_Button(
                bosh.tooldirs['NVIDIAMelody'],
                Image(r'images/NVIDIAMelody'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Nvidia Melody")))
        BashStatusBar.buttons.append( #Paint.net
            App_Button(
                bosh.tooldirs['PaintNET'],
                Image(r'images/paint.net'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Paint.NET")))
        BashStatusBar.buttons.append( #PaintShop Photo Pro
            App_Button(
                bosh.tooldirs['PaintShopPhotoPro'],
                Image(r'images/PaintshopProX3'+bosh.inisettings['IconSize']+'.png'),
                _("Launch PaintShop Photo Pro")))
        BashStatusBar.buttons.append( #Photoshop
            App_Button(
                bosh.tooldirs['PhotoshopPath'],
                Image(r'images/photoshop'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Photoshop")))
        BashStatusBar.buttons.append( #PhotoScape
            App_Button(
                bosh.tooldirs['PhotoScape'],
                Image(r'images/PhotoScape'+bosh.inisettings['IconSize']+'.png'),
                _("Launch PhotoScape")))
        BashStatusBar.buttons.append( #PhotoSEAM
            App_Button(
                bosh.tooldirs['PhotoSEAM'],
                Image(r'images/PhotoSEAM'+bosh.inisettings['IconSize']+'.png'),
                _("Launch PhotoSEAM")))
        BashStatusBar.buttons.append( #Photobie Design Studio
            App_Button(
                bosh.tooldirs['Photobie'],
                Image(r'images/Photobie'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Photobie")))
        BashStatusBar.buttons.append( #PhotoFiltre
            App_Button(
                bosh.tooldirs['PhotoFiltre'],
                Image(r'images/PhotoFiltre'+bosh.inisettings['IconSize']+'.png'),
                _("Launch PhotoFiltre")))
        BashStatusBar.buttons.append( #Pixel Studio Pro
            App_Button(
                bosh.tooldirs['PixelStudio'],
                Image(r'images/PixelStudioPro'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Pixel Studio Pro")))
        BashStatusBar.buttons.append( #Pixia
            App_Button(
                bosh.tooldirs['Pixia'],
                Image(r'images/Pixia'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Pixia")))
        BashStatusBar.buttons.append( #TextureMaker
            App_Button(
                bosh.tooldirs['TextureMaker'],
                Image(r'images/TextureMaker'+bosh.inisettings['IconSize']+'.png'),
                _("Launch TextureMaker")))
        BashStatusBar.buttons.append( #Twisted Brush
            App_Button(
                bosh.tooldirs['TwistedBrush'],
                Image(r'images/TwistedBrush'+bosh.inisettings['IconSize']+'.png'),
                _("Launch TwistedBrush")))
        BashStatusBar.buttons.append( #Windows Texture Viewer
            App_Button(
                bosh.tooldirs['WTV'],
                Image(r'images/WTV'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Windows Texture Viewer")))
        BashStatusBar.buttons.append( #xNormal
            App_Button(
                bosh.tooldirs['xNormal'],
                Image(r'images/xNormal'+bosh.inisettings['IconSize']+'.png'),
                _("Launch xNormal")))
        BashStatusBar.buttons.append( #XnView
            App_Button(
                bosh.tooldirs['XnView'],
                Image(r'images/XnView'+bosh.inisettings['IconSize']+'.png'),
                _("Launch XnView")))
    if bosh.inisettings['ShowAudioToolLaunchers']:
        BashStatusBar.buttons.append( #Audacity
            App_Button(
                bosh.tooldirs['Audacity'],
                Image(r'images/audacity'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Audacity")))
        BashStatusBar.buttons.append( #ABCAmberAudioConverter
            App_Button(
                bosh.tooldirs['ABCAmberAudioConverter'],
                Image(r'images/ABCAmberAudioConverter'+bosh.inisettings['IconSize']+'.png'),
                _("Launch ABC Amber Audio Converter")))
        BashStatusBar.buttons.append( #Switch
            App_Button(
                bosh.tooldirs['Switch'],
                Image(r'images/Switch'+bosh.inisettings['IconSize']+'.png'),
                _("Launch Switch")))
    BashStatusBar.buttons.append( #Fraps
        App_Button(
            bosh.tooldirs['Fraps'],
            Image(r'images/fraps'+bosh.inisettings['IconSize']+'.png'),
            _("Launch Fraps")))
    BashStatusBar.buttons.append( #MAP
        App_Button(
            bosh.tooldirs['MAP'],
            Image(r'images/InteractiveMapofCyrodiil'+bosh.inisettings['IconSize']+'.png'),
            _("Interactive Map of Cyrodiil and Shivering Isles")))
    BashStatusBar.buttons.append( #LogitechKeyboard
        App_Button(
            bosh.tooldirs['LogitechKeyboard'],
            Image(r'images/LogitechKeyboard'+bosh.inisettings['IconSize']+'.png'),
            _("Launch LogitechKeyboard")))
    BashStatusBar.buttons.append( #MediaMonkey
        App_Button(
            bosh.tooldirs['MediaMonkey'],
            Image(r'images/MediaMonkey'+bosh.inisettings['IconSize']+'.png'),
            _("Launch MediaMonkey")))
    BashStatusBar.buttons.append( #NPP
        App_Button(
            bosh.tooldirs['NPP'],
            Image(r'images/notepad++'+bosh.inisettings['IconSize']+'.png'),
            _("Launch Notepad++")))
    BashStatusBar.buttons.append( #Steam
        App_Button(
            bosh.tooldirs['Steam'],
            Image(r'images/Steam'+bosh.inisettings['IconSize']+'.png'),
            _("Launch Steam")))
    BashStatusBar.buttons.append( #EVGA Precision
        App_Button(
            bosh.tooldirs['EVGAPrecision'],
            Image(r'images/EVGAPrecision'+bosh.inisettings['IconSize']+'.png'),
            _("Launch EVGA Precision")))
    BashStatusBar.buttons.append( #WinMerge
        App_Button(
            bosh.tooldirs['WinMerge'],
            Image(r'images/WinMerge'+bosh.inisettings['IconSize']+'.png'),
            _("Launch WinMerge")))
    BashStatusBar.buttons.append( #Freemind
        App_Button(
            bosh.tooldirs['FreeMind'],
            Image(r'images/FreeMind'+bosh.inisettings['IconSize']+'.png'),
            _("Launch FreeMind")))
    BashStatusBar.buttons.append( #Freeplane
        App_Button(
            bosh.tooldirs['Freeplane'],
            Image(r'images/Freeplane'+bosh.inisettings['IconSize']+'.png'),
            _("Launch Freeplane")))
    BashStatusBar.buttons.append( #FileZilla
        App_Button(
            bosh.tooldirs['FileZilla'],
            Image(r'images/FileZilla'+bosh.inisettings['IconSize']+'.png'),
            _("Launch FileZilla")))
    BashStatusBar.buttons.append( #EggTranslator
        App_Button(
            bosh.tooldirs['EggTranslator'],
            Image(r'images/EggTranslator'+bosh.inisettings['IconSize']+'.png'),
            _("Launch Egg Translator")))
    BashStatusBar.buttons.append( #RADVideoTools
        App_Button(
            bosh.tooldirs['RADVideo'],
            Image(r'images/RADVideoTools'+bosh.inisettings['IconSize']+'.png'),
            _("Launch RAD Video Tools")))
    BashStatusBar.buttons.append( #WinSnap
        App_Button(
            bosh.tooldirs['WinSnap'],
            Image(r'images/WinSnap'+bosh.inisettings['IconSize']+'.png'),
            _("Launch WinSnap")))
    if bosh.inisettings['Custom1opt']:
        BashStatusBar.buttons.append(
            App_Button(
                (bosh.tooldirs['Custom1'], bosh.inisettings['Custom1opt']),
                Image(r'images/custom1'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom1txt'])))
    else:
        BashStatusBar.buttons.append(
            App_Button(
                bosh.tooldirs['Custom1'],
                Image(r'images/custom1'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom1txt'])))
    if bosh.inisettings['Custom2opt']:
        BashStatusBar.buttons.append(
            App_Button(
                (bosh.tooldirs['Custom2'], bosh.inisettings['Custom2opt']),
                Image(r'images/custom2'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom2txt'])))
    else:
        BashStatusBar.buttons.append(
            App_Button(
                bosh.tooldirs['Custom2'],
                Image(r'images/custom2'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom2txt'])))
    if bosh.inisettings['Custom3opt']:
        BashStatusBar.buttons.append(
            App_Button(
                (bosh.tooldirs['Custom3'], bosh.inisettings['Custom3opt']),
                Image(r'images/custom3'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom3txt'])))
    else:
        BashStatusBar.buttons.append(
            App_Button(
                bosh.tooldirs['Custom3'],
                Image(r'images/custom3'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom3txt'])))
    if bosh.inisettings['Custom4opt']:
        BashStatusBar.buttons.append(
            App_Button(
                (bosh.tooldirs['Custom4'], bosh.inisettings['Custom4opt']),
                Image(r'images/custom4'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom4txt'])))
    else:
        BashStatusBar.buttons.append(
            App_Button(
                bosh.tooldirs['Custom4'],
                Image(r'images/custom4'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom4txt'])))
    if bosh.inisettings['Custom5opt']:
        BashStatusBar.buttons.append(
            App_Button(
                (bosh.tooldirs['Custom5'], bosh.inisettings['Custom5opt']),
                Image(r'images/custom5'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom5txt'])))
    else:
        BashStatusBar.buttons.append(
            App_Button(
                bosh.tooldirs['Custom5'],
                Image(r'images/custom5'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom5txt'])))
    if bosh.inisettings['Custom6opt']:
        BashStatusBar.buttons.append(
            App_Button(
                (bosh.tooldirs['Custom6'], bosh.inisettings['Custom6opt']),
                Image(r'images/custom6'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom6txt'])))
    else:
        BashStatusBar.buttons.append(
            App_Button(
                bosh.tooldirs['Custom6'],
                Image(r'images/custom6'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom6txt'])))
    if bosh.inisettings['Custom7opt']:
        BashStatusBar.buttons.append(
            App_Button(
                (bosh.tooldirs['Custom7'], bosh.inisettings['Custom7opt']),
                Image(r'images/custom7'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom7txt'])))
    else:
        BashStatusBar.buttons.append(
            App_Button(
                bosh.tooldirs['Custom7'],
                Image(r'images/custom7'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom7txt'])))
    if bosh.inisettings['Custom8opt']:
        BashStatusBar.buttons.append(
            App_Button(
                (bosh.tooldirs['Custom8'], bosh.inisettings['Custom8opt']),
                Image(r'images/custom8'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom8txt'])))
    else:
        BashStatusBar.buttons.append(
            App_Button(
                bosh.tooldirs['Custom8'],
                Image(r'images/custom8'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom8txt'])))
    if bosh.inisettings['Custom9opt']:
        BashStatusBar.buttons.append(
            App_Button(
                (bosh.tooldirs['Custom9'], bosh.inisettings['Custom9opt']),
                Image(r'images/custom9'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom9txt'])))
    else:
        BashStatusBar.buttons.append(
            App_Button(
                bosh.tooldirs['Custom9'],
                Image(r'images/custom9'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom9txt'])))
    if bosh.inisettings['Custom10opt']:
        BashStatusBar.buttons.append(
            App_Button(
                (bosh.tooldirs['Custom10'], bosh.inisettings['Custom10opt']),
                Image(r'images/custom10'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom10txt'])))
    else:
        BashStatusBar.buttons.append(
            App_Button(
                bosh.tooldirs['Custom10'],
                Image(r'images/custom10'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom10txt'])))
    if bosh.inisettings['Custom11opt']:
        BashStatusBar.buttons.append(
            App_Button(
                (bosh.tooldirs['Custom11'], bosh.inisettings['Custom11opt']),
                Image(r'images/custom11'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom11txt'])))
    else:
        BashStatusBar.buttons.append(
            App_Button(
                bosh.tooldirs['Custom11'],
                Image(r'images/custom11'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom11txt'])))
    if bosh.inisettings['Custom12opt']:
        BashStatusBar.buttons.append(
            App_Button(
                (bosh.tooldirs['Custom12'], bosh.inisettings['Custom12opt']),
                Image(r'images/custom12'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom12txt'])))
    else:
        BashStatusBar.buttons.append(
            App_Button(
                bosh.tooldirs['Custom12'],
                Image(r'images/custom12'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom12txt'])))
    if bosh.inisettings['Custom13opt']:
        BashStatusBar.buttons.append(
            App_Button(
                (bosh.tooldirs['Custom13'], bosh.inisettings['Custom13opt']),
                Image(r'images/custom13'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom13txt'])))
    else:
        BashStatusBar.buttons.append(
            App_Button(
                bosh.tooldirs['Custom13'],
                Image(r'images/custom13'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom13txt'])))
    if bosh.inisettings['Custom14opt']:
        BashStatusBar.buttons.append(
            App_Button(
                (bosh.tooldirs['Custom14'], bosh.inisettings['Custom14opt']),
                Image(r'images/custom14'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom14txt'])))
    else:
        BashStatusBar.buttons.append(
            App_Button(
                bosh.tooldirs['Custom14'],
                Image(r'images/custom14'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom14txt'])))
    if bosh.inisettings['Custom15opt']:
        BashStatusBar.buttons.append(
            App_Button(
                (bosh.tooldirs['Custom15'], bosh.inisettings['Custom15opt']),
                Image(r'images/custom15'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom15txt'])))
    else:
        BashStatusBar.buttons.append(
            App_Button(
                bosh.tooldirs['Custom15'],
                Image(r'images/custom15'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom15txt'])))
    if bosh.inisettings['Custom16opt']:
        BashStatusBar.buttons.append(
            App_Button(
                (bosh.tooldirs['Custom16'], bosh.inisettings['Custom16opt']),
                Image(r'images/custom16'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom16txt'])))
    else:
        BashStatusBar.buttons.append(
            App_Button(
                bosh.tooldirs['Custom16'],
                Image(r'images/custom16'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom16txt'])))
    if bosh.inisettings['Custom17opt']:
        BashStatusBar.buttons.append(
            App_Button(
                (bosh.tooldirs['Custom17'], bosh.inisettings['Custom17opt']),
                Image(r'images/custom17'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom17txt'])))
    else:
        BashStatusBar.buttons.append(
            App_Button(
                bosh.tooldirs['Custom17'],
                Image(r'images/custom17'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom17txt'])))
    if bosh.inisettings['Custom18opt']:
        BashStatusBar.buttons.append(
            App_Button(
                (bosh.tooldirs['Custom18'], bosh.inisettings['Custom18opt']),
                Image(r'images/custom18'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom18txt'])))
    else:
        BashStatusBar.buttons.append(
            App_Button(
                bosh.tooldirs['Custom18'],
                Image(r'images/custom18'+bosh.inisettings['IconSize']+'.png'),
                (bosh.inisettings['Custom18txt'])))
    BashStatusBar.buttons.append(
        App_Button(
            bosh.dirs['mopy'].join('bashmon.py'),
            Image(r'images/Bashmon'+bosh.inisettings['IconSize']+'.png'),
            _("Launch BashMon")))
    BashStatusBar.buttons.append(App_DocBrowser())
    BashStatusBar.buttons.append(App_ModChecker())
    BashStatusBar.buttons.append(App_Help())

def InitMasterLinks():
    """Initialize master list menus."""
    #--MasterList: Column Links
    if True: #--Sort by
        sortMenu = MenuLink(_("Sort by"))
        sortMenu.links.append(Mods_EsmsFirst())
        sortMenu.links.append(SeparatorLink())
        sortMenu.links.append(Files_SortBy('File'))
        sortMenu.links.append(Files_SortBy('Author'))
        sortMenu.links.append(Files_SortBy('Group'))
        sortMenu.links.append(Files_SortBy('Installer'))
        sortMenu.links.append(Files_SortBy('Load Order'))
        sortMenu.links.append(Files_SortBy('Modified'))
        sortMenu.links.append(Files_SortBy('Save Order'))
        sortMenu.links.append(Files_SortBy('Status'))
        MasterList.mainMenu.append(sortMenu)

    #--MasterList: Item Links
    MasterList.itemMenu.append(Master_ChangeTo())
    MasterList.itemMenu.append(Master_Disable())

def InitInstallerLinks():
    """Initialize people tab menus."""
    #--Column links
    #--Sorting
    if True:
        sortMenu = MenuLink(_("Sort by"))
        sortMenu.links.append(Installers_SortActive())
        sortMenu.links.append(Installers_SortProjects())
        #InstallersPanel.mainMenu.append(Installers_SortStructure())
        sortMenu.links.append(SeparatorLink())
        sortMenu.links.append(Files_SortBy('Package'))
        sortMenu.links.append(Files_SortBy('Order'))
        sortMenu.links.append(Files_SortBy('Modified'))
        sortMenu.links.append(Files_SortBy('Size'))
        sortMenu.links.append(Files_SortBy('Files'))
        InstallersPanel.mainMenu.append(sortMenu)
    #--Columns
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(List_Columns('bash.installers.cols',['Package']))
    #--Actions
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(balt.Tanks_Open())
    InstallersPanel.mainMenu.append(Installers_Refresh(fullRefresh=False))
    InstallersPanel.mainMenu.append(Installers_Refresh(fullRefresh=True))
    InstallersPanel.mainMenu.append(Installers_AddMarker())
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(Installer_ListPackages())
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(Installers_AnnealAll())
    InstallersPanel.mainMenu.append(Files_Unhide('installer'))
    #--Behavior
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(Installers_AvoidOnStart())
    InstallersPanel.mainMenu.append(Installers_Enabled())
    if bosh.inisettings['EnableReplacers']:
        InstallersPanel.mainMenu.append(Installers_ShowReplacers())
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(Installers_AutoAnneal())
    if bEnableWizard:
        InstallersPanel.mainMenu.append(Installers_AutoWizard())
    InstallersPanel.mainMenu.append(Installers_AutoRefreshProjects())
    InstallersPanel.mainMenu.append(Installers_AutoRefreshBethsoft())
    InstallersPanel.mainMenu.append(Installers_BsaRedirection())
    InstallersPanel.mainMenu.append(Installers_RemoveEmptyDirs())
    InstallersPanel.mainMenu.append(Installers_ConflictsReportShowsInactive())
    InstallersPanel.mainMenu.append(Installers_ConflictsReportShowsLower())
    InstallersPanel.mainMenu.append(Installers_WizardOverlay())
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(Installers_SkipOBSEPlugins())
    InstallersPanel.mainMenu.append(Installers_SkipScreenshots())
    InstallersPanel.mainMenu.append(Installers_SkipImages())
    InstallersPanel.mainMenu.append(Installers_SkipDocs())
    InstallersPanel.mainMenu.append(Installers_SkipDistantLOD())
    InstallersPanel.mainMenu.append(Installers_skipLandscapeLODMeshes())
    InstallersPanel.mainMenu.append(Installers_skipLandscapeLODTextures())
    InstallersPanel.mainMenu.append(Installers_skipLandscapeLODNormals())
    #--Settings
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(SettingsMenu)

    #--Item links
    #--File
    InstallersPanel.itemMenu.append(Installer_Open())
    InstallersPanel.itemMenu.append(Installer_Duplicate())
    InstallersPanel.itemMenu.append(balt.Tank_Delete())
    if True: #--Open At...
        openAtMenu = InstallerOpenAt_MainMenu(_("Open at"))
        openAtMenu.links.append(Installer_OpenSearch())
        openAtMenu.links.append(Installer_OpenTesNexus())
        openAtMenu.links.append(Installer_OpenTESA())
        openAtMenu.links.append(Installer_OpenPES())
        InstallersPanel.itemMenu.append(openAtMenu)
    InstallersPanel.itemMenu.append(Installer_Hide())
    InstallersPanel.itemMenu.append(Installer_Rename())
    #--Install, uninstall, etc.
    InstallersPanel.itemMenu.append(SeparatorLink())
    InstallersPanel.itemMenu.append(Installer_Refresh())
    InstallersPanel.itemMenu.append(Installer_Move())
    InstallersPanel.itemMenu.append(SeparatorLink())
    InstallersPanel.itemMenu.append(Installer_HasExtraData())
    InstallersPanel.itemMenu.append(Installer_OverrideSkips())
    InstallersPanel.itemMenu.append(Installer_SkipVoices())
    InstallersPanel.itemMenu.append(SeparatorLink())
    if bEnableWizard:
        InstallersPanel.itemMenu.append(Installer_Wizard(False))
        InstallersPanel.itemMenu.append(Installer_Wizard(True))
        InstallersPanel.itemMenu.append(Installer_EditWizard())
        InstallersPanel.itemMenu.append(SeparatorLink())
    InstallersPanel.itemMenu.append(Installer_Anneal())
    InstallersPanel.itemMenu.append(Installer_Install())
    InstallersPanel.itemMenu.append(Installer_Install('LAST'))
    InstallersPanel.itemMenu.append(Installer_Install('MISSING'))
    InstallersPanel.itemMenu.append(Installer_Uninstall())
    InstallersPanel.itemMenu.append(SeparatorLink())
    #--Build
    if True: #--BAIN Conversion
        conversionsMenu = InstallerConverter_MainMenu(_("Conversions"))
        conversionsMenu.links.append(InstallerConverter_Create())
        conversionsMenu.links.append(InstallerConverter_ConvertMenu(_("Apply")))
        InstallersPanel.itemMenu.append(conversionsMenu)
    InstallersPanel.itemMenu.append(InstallerProject_Pack())
    InstallersPanel.itemMenu.append(InstallerArchive_Unpack())
    InstallersPanel.itemMenu.append(InstallerProject_ReleasePack())
    InstallersPanel.itemMenu.append(InstallerProject_Sync())
    InstallersPanel.itemMenu.append(Installer_CopyConflicts())
    InstallersPanel.itemMenu.append(InstallerProject_OmodConfig())
    InstallersPanel.itemMenu.append(Installer_ListStructure())

    #--espms Main Menu
    InstallersPanel.espmMenu.append(Installer_Espm_SelectAll())
    InstallersPanel.espmMenu.append(Installer_Espm_DeselectAll())
    InstallersPanel.espmMenu.append(SeparatorLink())
    #--espms Item Menu
    InstallersPanel.espmMenu.append(Installer_Espm_Rename())
    InstallersPanel.espmMenu.append(Installer_Espm_Reset())
    InstallersPanel.espmMenu.append(SeparatorLink())
    InstallersPanel.espmMenu.append(Installer_Espm_ResetAll())

    #--Sub-Package Main Menu
    InstallersPanel.subsMenu.append(Installer_Subs_SelectAll())
    InstallersPanel.subsMenu.append(Installer_Subs_DeselectAll())
    InstallersPanel.subsMenu.append(Installer_Subs_ToggleSelection())
    InstallersPanel.subsMenu.append(SeparatorLink())
    InstallersPanel.subsMenu.append(Installer_Subs_ListSubPackages())

def InitReplacerLinks():
    """Initialize replacer tab menus."""
    #--Header links
    ReplacersList.mainMenu.append(Files_Open())
    #--Settings
    ReplacersList.mainMenu.append(SettingsMenu)

    #--Item links
    ReplacersList.itemMenu.append(File_Open())

def InitINILinks():
    """Initialize INI Edits tab menus."""
    #--Column Links
    if True: #--Sort by
        sortMenu = MenuLink(_("Sort by"))
        sortMenu.links.append(INI_SortValid())
        sortMenu.links.append(SeparatorLink())
        sortMenu.links.append(Files_SortBy('File'))
        sortMenu.links.append(Files_SortBy('Installer'))
    INIList.mainMenu.append(sortMenu)
    INIList.mainMenu.append(SeparatorLink())
    INIList.mainMenu.append(List_Columns('bash.ini.cols',['File']))
    INIList.mainMenu.append(SeparatorLink())
    INIList.mainMenu.append(Files_Open())
    #--Settings
    INIList.mainMenu.append(SeparatorLink())
    INIList.mainMenu.append(SettingsMenu)

    #--Item menu
    INIList.itemMenu.append(INI_Apply())
    INIList.itemMenu.append(INI_CreateNew())
    INIList.itemMenu.append(INI_ListErrors())
    INIList.itemMenu.append(SeparatorLink())
    INIList.itemMenu.append(File_Open())
    INIList.itemMenu.append(File_Delete())

def InitModLinks():
    """Initialize Mods tab menus."""
    #--ModList: Column Links
    if True: #--Load
        loadMenu = MenuLink(_("Load"))
        loadMenu.links.append(Mods_LoadList())
        ModList.mainMenu.append(loadMenu)
    if True: #--Sort by
        sortMenu = MenuLink(_("Sort by"))
        sortMenu.links.append(Mods_EsmsFirst())
        sortMenu.links.append(Mods_SelectedFirst())
        sortMenu.links.append(SeparatorLink())
        sortMenu.links.append(Files_SortBy('File'))
        sortMenu.links.append(Files_SortBy('Author'))
        sortMenu.links.append(Files_SortBy('Group'))
        sortMenu.links.append(Files_SortBy('Installer'))
        sortMenu.links.append(Files_SortBy('Load Order'))
        sortMenu.links.append(Files_SortBy('Modified'))
        sortMenu.links.append(Files_SortBy('Rating'))
        sortMenu.links.append(Files_SortBy('Size'))
        sortMenu.links.append(Files_SortBy('Status'))
        ModList.mainMenu.append(sortMenu)
    if True: #--Versions
        versionsMenu = MenuLink("Oblivion.esm")
        versionsMenu.links.append(Mods_OblivionVersion('1.1'))
        versionsMenu.links.append(Mods_OblivionVersion('1.2'))
        versionsMenu.links.append(Mods_OblivionVersion('SI'))
        ModList.mainMenu.append(versionsMenu)
    #--Columns ----------------------------------
    ModList.mainMenu.append(SeparatorLink())
    ModList.mainMenu.append(List_Columns('bash.mods.cols',['File']))
    #--------------------------------------------
    ModList.mainMenu.append(SeparatorLink())
    ModList.mainMenu.append(Files_Open())
    ModList.mainMenu.append(Files_Unhide('mod'))
    ModList.mainMenu.append(SeparatorLink())
    ModList.mainMenu.append(Mods_ListMods())
    ModList.mainMenu.append(Mods_ListBashTags())
    ModList.mainMenu.append(SeparatorLink())
    ModList.mainMenu.append(Mods_AutoGhost())
    if bosh.inisettings['EnableBalo']:
        ModList.mainMenu.append(Mods_AutoGroup())
        ModList.mainMenu.append(Mods_FullBalo())
    ModList.mainMenu.append(Mods_LockTimes())
    ModList.mainMenu.append(SeparatorLink())
    ModList.mainMenu.append(Mods_Deprint())
    ModList.mainMenu.append(Mods_DumpTranslator())
    ModList.mainMenu.append(Mods_Tes4ViewExpert())
    #--BOSS options
    ModList.mainMenu.append(SeparatorLink())
    ModList.mainMenu.append(Mods_BOSSDisableLockTimes())
    ModList.mainMenu.append(Mods_BOSSShowUpdate())
    ModList.mainMenu.append(Mods_ScanDirty())
    #--Settings
    ModList.mainMenu.append(SeparatorLink())
    ModList.mainMenu.append(SettingsMenu)

    #--ModList: Item Links
    if True: #--File
        fileMenu = MenuLink(_("File"))
        fileMenu.links.append(Mod_CreateBlank())
        fileMenu.links.append(SeparatorLink())
        fileMenu.links.append(File_Backup())
        fileMenu.links.append(File_Duplicate())
        fileMenu.links.append(File_Snapshot())
        fileMenu.links.append(SeparatorLink())
        fileMenu.links.append(File_Delete())
        fileMenu.links.append(File_Hide())
        fileMenu.links.append(File_Redate())
        fileMenu.links.append(File_Sort())
        fileMenu.links.append(SeparatorLink())
        fileMenu.links.append(File_RevertToBackup())
        fileMenu.links.append(File_RevertToSnapshot())
        ModList.itemMenu.append(fileMenu)
    if True: #--Groups
        groupMenu = MenuLink(_("Group"))
        groupMenu.links.append(Mod_Groups())
        if bosh.inisettings['EnableBalo']:
            groupMenu.links.append(Mod_BaloGroups())
        ModList.itemMenu.append(groupMenu)
    if True: #--Ratings
        ratingMenu = MenuLink(_("Rating"))
        ratingMenu.links.append(Mod_Ratings())
        ModList.itemMenu.append(ratingMenu)
    #--------------------------------------------
    ModList.itemMenu.append(SeparatorLink())
    ModList.itemMenu.append(Mod_Details())
    ModList.itemMenu.append(File_ListMasters())
    ModList.itemMenu.append(Mod_ShowReadme())
    ModList.itemMenu.append(Mod_ListBashTags())
    #--------------------------------------------
    ModList.itemMenu.append(SeparatorLink())
    ModList.itemMenu.append(Mod_AllowGhosting())
    ModList.itemMenu.append(Mod_SkipDirtyCheck())
    #ModList.itemMenu.append(Mod_MarkLevelers())
    ModList.itemMenu.append(Mod_MarkMergeable())
    ModList.itemMenu.append(Mod_Patch_Update())
    #--Advanced
    ModList.itemMenu.append(SeparatorLink())
    if True: #--Export
        exportMenu = MenuLink(_("Export"))
        exportMenu.links.append(Mod_EditorIds_Export())
        exportMenu.links.append(Mod_Groups_Export())
##        exportMenu.links.append(Mod_ItemData_Export())
        exportMenu.links.append(Mod_Factions_Export())
        exportMenu.links.append(Mod_FullNames_Export())
        exportMenu.links.append(Mod_ActorLevels_Export())
        exportMenu.links.append(CBash_Mod_MapMarkers_Export())
        exportMenu.links.append(Mod_Prices_Export())
        exportMenu.links.append(Mod_FactionRelations_Export())
        exportMenu.links.append(Mod_IngredientDetails_Export())
        exportMenu.links.append(Mod_Scripts_Export())
        exportMenu.links.append(Mod_SigilStoneDetails_Export())
        exportMenu.links.append(Mod_SpellRecords_Export())
        exportMenu.links.append(Mod_Stats_Export())
        ModList.itemMenu.append(exportMenu)
    if True: #--Import
        importMenu = MenuLink(_("Import"))
        importMenu.links.append(Mod_EditorIds_Import())
        importMenu.links.append(Mod_Groups_Import())
##        importMenu.links.append(Mod_ItemData_Import())
        importMenu.links.append(Mod_Factions_Import())
        importMenu.links.append(Mod_FullNames_Import())
        importMenu.links.append(Mod_ActorLevels_Import())
        importMenu.links.append(CBash_Mod_MapMarkers_Import())
        importMenu.links.append(Mod_Prices_Import())
        importMenu.links.append(Mod_FactionRelations_Import())
        importMenu.links.append(Mod_IngredientDetails_Import())
        importMenu.links.append(Mod_Scripts_Import())
        importMenu.links.append(Mod_SigilStoneDetails_Import())
        importMenu.links.append(Mod_SpellRecords_Import())
        importMenu.links.append(Mod_Stats_Import())
        importMenu.links.append(SeparatorLink())
        importMenu.links.append(Mod_Face_Import())
        importMenu.links.append(Mod_Fids_Replace())
        ModList.itemMenu.append(importMenu)
    ModList.itemMenu.append(Mod_AddMaster())
    ModList.itemMenu.append(Mod_CopyToEsmp())
    ModList.itemMenu.append(Mod_DecompileAll())
    ModList.itemMenu.append(Mod_FlipSelf())
    ModList.itemMenu.append(Mod_FlipMasters())
    ModList.itemMenu.append(Mod_RemoveWorldOrphans())
    ModList.itemMenu.append(Mod_CleanMod())
    ModList.itemMenu.append(Mod_SetVersion())
    ModList.itemMenu.append(Mod_UndeleteRefs())
#    if bosh.inisettings['showadvanced'] == 1:
#        advmenu = MenuLink(_("Advanced Scripts"))
#        advmenu.links.append(Mod_DiffScripts())
        #advmenu.links.append(())

def InitSaveLinks():
    """Initialize save tab menus."""
    #--SaveList: Column Links
    if True: #--Sort
        sortMenu = MenuLink(_("Sort by"))
        sortMenu.links.append(Files_SortBy('File'))
        sortMenu.links.append(Files_SortBy('Cell'))
        sortMenu.links.append(Files_SortBy('PlayTime'))
        sortMenu.links.append(Files_SortBy('Modified'))
        sortMenu.links.append(Files_SortBy('Player'))
        sortMenu.links.append(Files_SortBy('Status'))
        SaveList.mainMenu.append(sortMenu)
    if True: #--Versions
        versionsMenu = MenuLink("Oblivion.esm")
        versionsMenu.links.append(Mods_OblivionVersion('1.1',True))
        versionsMenu.links.append(Mods_OblivionVersion('1.2',True))
        versionsMenu.links.append(Mods_OblivionVersion('SI',True))
        SaveList.mainMenu.append(versionsMenu)
    if True: #--Save Profiles
        subDirMenu = MenuLink(_("Profile"))
        subDirMenu.links.append(Saves_Profiles())
        SaveList.mainMenu.append(subDirMenu)
    #--Columns --------------------------------
    SaveList.mainMenu.append(SeparatorLink())
    SaveList.mainMenu.append(List_Columns('bash.saves.cols',['File']))
    #------------------------------------------
    SaveList.mainMenu.append(SeparatorLink())
    SaveList.mainMenu.append(Files_Open())
    SaveList.mainMenu.append(Files_Unhide('save'))
    #--Settings
    SaveList.mainMenu.append(SeparatorLink())
    SaveList.mainMenu.append(SettingsMenu)

    #--SaveList: Item Links
    if True: #--File
        fileMenu = MenuLink(_("File")) #>>
        fileMenu.links.append(File_Backup())
        fileMenu.links.append(File_Duplicate())
        #fileMenu.links.append(File_Snapshot())
        fileMenu.links.append(SeparatorLink())
        fileMenu.links.append(File_Delete())
        fileMenu.links.append(File_Hide())
        fileMenu.links.append(SeparatorLink())
        fileMenu.links.append(File_RevertToBackup())
        fileMenu.links.append(Save_Rename())
        fileMenu.links.append(Save_Renumber())
        #fileMenu.links.append(File_RevertToSnapshot())
        SaveList.itemMenu.append(fileMenu)
    if True: #--Move to Profile
        moveMenu = MenuLink(_("Move To"))
        moveMenu.links.append(Save_Move())
        SaveList.itemMenu.append(moveMenu)
    if True: #--Copy to Profile
        copyMenu = MenuLink(_("Copy To"))
        copyMenu.links.append(Save_Move(True))
        SaveList.itemMenu.append(copyMenu)
    #--------------------------------------------
    SaveList.itemMenu.append(SeparatorLink())
    SaveList.itemMenu.append(Save_LoadMasters())
    SaveList.itemMenu.append(File_ListMasters())
    SaveList.itemMenu.append(Save_DiffMasters())
    SaveList.itemMenu.append(Save_Stats())
    SaveList.itemMenu.append(Save_StatObse())
    #--------------------------------------------
    SaveList.itemMenu.append(SeparatorLink())
    SaveList.itemMenu.append(Save_EditPCSpells())
    SaveList.itemMenu.append(Save_RenamePlayer())
    SaveList.itemMenu.append(Save_EditCreatedEnchantmentCosts())
    SaveList.itemMenu.append(Save_ImportFace())
    SaveList.itemMenu.append(Save_EditCreated('ENCH'))
    SaveList.itemMenu.append(Save_EditCreated('ALCH'))
    SaveList.itemMenu.append(Save_EditCreated('SPEL'))
    SaveList.itemMenu.append(Save_ReweighPotions())
    SaveList.itemMenu.append(Save_UpdateNPCLevels())
    #--------------------------------------------
    SaveList.itemMenu.append(SeparatorLink())
    SaveList.itemMenu.append(Save_Unbloat())
    SaveList.itemMenu.append(Save_RepairAbomb())
    SaveList.itemMenu.append(Save_RepairFactions())
    SaveList.itemMenu.append(Save_RepairHair())

def InitBSALinks():
    """Initialize save tab menus."""
    #--BSAList: Column Links
    if True: #--Sort
        sortMenu = MenuLink(_("Sort by"))
        sortMenu.links.append(Files_SortBy('File'))
        sortMenu.links.append(Files_SortBy('Modified'))
        sortMenu.links.append(Files_SortBy('Size'))
        BSAList.mainMenu.append(sortMenu)
    BSAList.mainMenu.append(SeparatorLink())
    BSAList.mainMenu.append(Files_Open())
    BSAList.mainMenu.append(Files_Unhide('save'))

    #--BSAList: Item Links
    if True: #--File
        fileMenu = MenuLink(_("File")) #>>
        fileMenu.links.append(File_Backup())
        fileMenu.links.append(File_Duplicate())
        #fileMenu.links.append(File_Snapshot())
        fileMenu.links.append(SeparatorLink())
        fileMenu.links.append(File_Delete())
        fileMenu.links.append(File_Hide())
        fileMenu.links.append(SeparatorLink())
        fileMenu.links.append(File_RevertToBackup())
        #fileMenu.links.append(File_RevertToSnapshot())
        BSAList.itemMenu.append(fileMenu)
    #--------------------------------------------
    BSAList.itemMenu.append(SeparatorLink())
    BSAList.itemMenu.append(Save_LoadMasters())
    BSAList.itemMenu.append(File_ListMasters())
    BSAList.itemMenu.append(Save_DiffMasters())
    BSAList.itemMenu.append(Save_Stats())
    #--------------------------------------------
    BSAList.itemMenu.append(SeparatorLink())
    BSAList.itemMenu.append(Save_EditPCSpells())
    BSAList.itemMenu.append(Save_ImportFace())
    BSAList.itemMenu.append(Save_EditCreated('ENCH'))
    BSAList.itemMenu.append(Save_EditCreated('ALCH'))
    BSAList.itemMenu.append(Save_EditCreated('SPEL'))
    BSAList.itemMenu.append(Save_ReweighPotions())
    BSAList.itemMenu.append(Save_UpdateNPCLevels())
    #--------------------------------------------
    BSAList.itemMenu.append(SeparatorLink())
    BSAList.itemMenu.append(Save_Unbloat())
    BSAList.itemMenu.append(Save_RepairAbomb())
    BSAList.itemMenu.append(Save_RepairFactions())
    BSAList.itemMenu.append(Save_RepairHair())

def InitScreenLinks():
    """Initialize screens tab menus."""
    #--SaveList: Column Links
    ScreensList.mainMenu.append(Files_Open())
    ScreensList.mainMenu.append(SeparatorLink())
    ScreensList.mainMenu.append(List_Columns('bash.screens.cols',['File']))
    ScreensList.mainMenu.append(SeparatorLink())
    ScreensList.mainMenu.append(Screens_NextScreenShot())
    #--JPEG Quality
    if True:
        qualityMenu = MenuLink(_('JPEG Quality'))
        for i in range(100,80,-5):
            qualityMenu.links.append(Screen_JpgQuality(i))
        qualityMenu.links.append(Screen_JpgQualityCustom())
        ScreensList.mainMenu.append(SeparatorLink())
        ScreensList.mainMenu.append(qualityMenu)
    #--Settings
    ScreensList.mainMenu.append(SeparatorLink())
    ScreensList.mainMenu.append(SettingsMenu)

    #--ScreensList: Item Links
    ScreensList.itemMenu.append(File_Open())
    ScreensList.itemMenu.append(Screen_Rename())
    ScreensList.itemMenu.append(File_Delete())
    ScreensList.itemMenu.append(SeparatorLink())
    if True: #--Convert
        convertMenu = MenuLink(_('Convert'))
        convertMenu.links.append(Screen_ConvertTo('jpg',wx.BITMAP_TYPE_JPEG))
        convertMenu.links.append(Screen_ConvertTo('png',wx.BITMAP_TYPE_PNG))
        convertMenu.links.append(Screen_ConvertTo('bmp',wx.BITMAP_TYPE_BMP))
        convertMenu.links.append(Screen_ConvertTo('tif',wx.BITMAP_TYPE_TIF))
        ScreensList.itemMenu.append(convertMenu)

def InitMessageLinks():
    """Initialize messages tab menus."""
    #--SaveList: Column Links
    MessageList.mainMenu.append(Messages_Archive_Import())
    MessageList.mainMenu.append(SeparatorLink())
    MessageList.mainMenu.append(List_Columns('bash.messages.cols',['Subject']))
    #--Settings
    MessageList.mainMenu.append(SeparatorLink())
    MessageList.mainMenu.append(SettingsMenu)

    #--ScreensList: Item Links
    MessageList.itemMenu.append(Message_Delete())

def InitPeopleLinks():
    """Initialize people tab menus."""
    #--Header links
    PeoplePanel.mainMenu.append(People_AddNew())
    PeoplePanel.mainMenu.append(People_Import())
    PeoplePanel.mainMenu.append(SeparatorLink())
    PeoplePanel.mainMenu.append(List_Columns('bash.people.cols',['Name']))
    #--Settings
    PeoplePanel.mainMenu.append(SeparatorLink())
    PeoplePanel.mainMenu.append(SettingsMenu)
    #--Item links
    PeoplePanel.itemMenu.append(People_Karma())
    PeoplePanel.itemMenu.append(SeparatorLink())
    PeoplePanel.itemMenu.append(People_AddNew())
    PeoplePanel.itemMenu.append(balt.Tank_Delete())
    PeoplePanel.itemMenu.append(People_Export())

def InitSettingsLinks():
    """Initialize settings menu."""
    global SettingsMenu
    SettingsMenu = MenuLink(_('Settings'))
    SettingsMenu.links.append(User_BackupSettings())
    SettingsMenu.links.append(User_SaveSettings())
    SettingsMenu.links.append(Installers_ExportDllInfo())
    SettingsMenu.links.append(Installers_ImportDllInfo())

def InitLinks():
    """Call other link initializers."""
    InitStatusBar()
    InitSettingsLinks()
    InitMasterLinks()
    InitInstallerLinks()
    InitINILinks()
    InitModLinks()
    InitReplacerLinks()
    InitSaveLinks()
    InitScreenLinks()
    InitMessageLinks()
    InitPeopleLinks()
    #InitBSALinks()

# Main ------------------------------------------------------------------------
if __name__ == '__main__':
    print _('Compiled')
