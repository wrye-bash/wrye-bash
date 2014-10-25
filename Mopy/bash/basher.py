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
import bush
import bosh
import bolt
import loot
import barb
import bass
import bweb

from bosh import formatInteger,formatDate
from bolt import BoltError, AbstractError, ArgumentError, StateError, UncodedError, CancelError, SkipError
from bolt import LString, GPath, SubProgress, deprint, sio
from cint import *
from patcher.patchers.base import MultiTweaker, CBash_MultiTweaker, \
    AliasesPatcher, CBash_AliasesPatcher, PatchMerger, CBash_PatchMerger, \
    UpdateReferences, CBash_UpdateReferences
from patcher.patchers.importers import CellImporter, \
    CBash_CellImporter, GraphicsPatcher, CBash_GraphicsPatcher, ActorImporter, \
    CBash_ActorImporter, KFFZPatcher, CBash_KFFZPatcher, NPCAIPackagePatcher, \
    CBash_NPCAIPackagePatcher, DeathItemPatcher, CBash_DeathItemPatcher, \
    ImportFactions, CBash_ImportFactions, ImportRelations, \
    CBash_ImportRelations, ImportScripts, CBash_ImportScripts, ImportInventory, \
    CBash_ImportInventory, ImportActorsSpells, CBash_ImportActorsSpells, \
    NamesPatcher, CBash_NamesPatcher, NpcFacePatcher, CBash_NpcFacePatcher, \
    RoadImporter, CBash_RoadImporter, SoundPatcher, CBash_SoundPatcher, \
    StatsPatcher, CBash_StatsPatcher, SpellsPatcher, CBash_SpellsPatcher
from patcher.patchers.multitweak_actors import TweakActors, \
    CBash_TweakActors
from patcher.patchers.multitweak_assorted import AssortedTweaker, \
    CBash_AssortedTweaker
from patcher.patchers.multitweak_clothes import ClothesTweaker, \
    CBash_ClothesTweaker
from patcher.patchers.multitweak_names import NamesTweaker, \
    CBash_NamesTweaker
from patcher.patchers.multitweak_settings import GmstTweaker, \
    CBash_GmstTweaker
from patcher.patchers.races_multitweaks import RacePatcher, \
    CBash_RacePatcher
from patcher.patchers.special import ContentsChecker, CBash_ContentsChecker
from patcher.patchers.special import ListsMerger as ListsMerger_
from patcher.patchers.special import \
    CBash_ListsMerger as CBash_ListsMerger_

startupinfo = bolt.startupinfo

#--Python
import ConfigParser
import StringIO
import copy
import datetime
import os
import re
import shutil
import string
import struct
import sys
import textwrap
import time
import subprocess
import locale
import win32gui
import multiprocessing
import webbrowser
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
SettingsMenu = None
obseButton = None
laaButton = None

# Settings --------------------------------------------------------------------
settings = None

# Color Descriptions ----------------------------------------------------------
colorInfo = {
    'default.text': (_(u'Default Text'),
                     _(u'This is the text color used for list items when no other is specified.  For example, an ESP that is not mergeable or ghosted, and has no other problems.'),
                     ),
    'default.bkgd': (_(u'Default Background'),
                     _(u'This is the text background color used for list items when no other is specified.  For example, an ESM that is not ghosted.'),
                     ),
    'mods.text.esm': (_(u'ESM'),
                      _(u'Tabs: Mods, Saves')
                      + u'\n\n' +
                      _(u'This is the text color used for ESMs in the Mods Tab, and in the Masters info on both the Mods Tab and Saves Tab.'),
                      ),
    'mods.text.mergeable': (_(u'Mergeable Plugin'),
                            _(u'Tabs: Mods')
                            + u'\n\n' +
                            _(u'This is the text color used for mergeable plugins.'),
                            ),
    'mods.text.noMerge': (_(u"'NoMerge' Plugin"),
                          _(u'Tabs: Mods')
                          + u'\n\n' +
                          _(u"This is the text color used for a mergeable plugin that is tagged 'NoMerge'."),
                          ),
    'mods.bkgd.doubleTime.exists': (_(u'Inactive Time Conflict'),
                                    _(u'Tabs: Mods')
                                    + u'\n\n' +
                                    _(u'This is the background color used for a plugin with an inactive time conflict.  This means that two or more plugins have the same timestamp, but only one (or none) of them is active.'),
                                    ),
    'mods.bkgd.doubleTime.load': (_(u'Active Time Conflict'),
                                  _(u'Tabs: Mods')
                                  + u'\n\n' +
                                  _(u'This is the background color used for a plugin with an active time conflict.  This means that two or more plugins with the same timestamp are active.'),
                                  ),
    'mods.bkgd.deactivate': (_(u"'Deactivate' Plugin"),
                             _(u'Tabs: Mods')
                             + u'\n\n' +
                             _(u"This is the background color used for an active plugin that is tagged 'Deactivate'."),
                             ),
    'mods.bkgd.exOverload': (_(u'Exclusion Group Overloaded'),
                             _(u'Tabs: Mods')
                             + u'\n\n' +
                             _(u'This is the background color used for an active plugin in an overloaded Exclusion Group.  This means that two or more plugins in an Exclusion Group are active, where an Exclusion Group is any group of mods that start with the same name, followed by a comma.')
                             + u'\n\n' +
                             _(u'An example exclusion group:')
                             + u'\n' +
                             _(u'Bashed Patch, 0.esp')
                             + u'\n' +
                             _(u'Bashed Patch, 1.esp')
                             + u'\n\n' +
                             _(u'Both of the above plugins belong to the "Bashed Patch," Exclusion Group.'),
                             ),
    'mods.bkgd.ghosted': (_(u'Ghosted Plugin'),
                          _(u'Tabs: Mods')
                          + u'\n\n' +
                          _(u'This is the background color used for a ghosted plugin.'),
                          ),
    'mods.bkgd.groupHeader': (_(u'Group Header'),
                              _(u'Tabs: Mods')
                              + u'\n\n' +
                              _(u'This is the background color used for a Group marker.'),
                              ),
    'ini.bkgd.invalid': (_(u'Invalid INI Tweak'),
                         _(u'Tabs: INI Edits')
                         + u'\n\n' +
                         _(u'This is the background color used for a tweak file that is invalid for the currently selected target INI.'),
                         ),
    'tweak.bkgd.invalid': (_(u'Invalid Tweak Line'),
                           _(u'Tabs: INI Edits')
                           + u'\n\n' +
                           _(u'This is the background color used for a line in a tweak file that is invalid for the currently selected target INI.'),
                           ),
    'tweak.bkgd.mismatched': (_(u'Mismatched Tweak Line'),
                              _(u'Tabs: INI Edits')
                              + u'\n\n' +
                              _(u'This is the background color used for a line in a tweak file that does not match what is set in the target INI.'),
                              ),
    'tweak.bkgd.matched': (_(u'Matched Tweak Line'),
                           _(u'Tabs: INI Edits')
                           + u'\n\n' +
                           _(u'This is the background color used for a line in a tweak file that matches what is set in the target INI.'),
                           ),
    'installers.text.complex': (_(u'Complex Installer'),
                                _(u'Tabs: Installers')
                                + u'\n\n' +
                                _(u'This is the text color used for a complex BAIN package.'),
                                ),
    'installers.text.invalid': (_(u'Marker'),
                                _(u'Tabs: Installers')
                                + u'\n\n' +
                                _(u'This is the text color used for Markers.'),
                                ),
    'installers.bkgd.skipped': (_(u'Skipped Files'),
                                _(u'Tabs: Installers')
                                + u'\n\n' +
                                _(u'This is the background color used for a package with files that will not be installed by BAIN.  This means some files are selected to be installed, but due to your current Skip settings (for example, Skip DistantLOD), will not be installed.'),
                                ),
    'installers.bkgd.outOfOrder': (_(u'Installer Out of Order'),
                                   _(u'Tabs: Installers')
                                   + u'\n\n' +
                                   _(u'This is the background color used for an installer with files installed, that should be overridden by a package with a higher install order.  It can be repaired with an Anneal or Anneal All.'),
                                   ),
    'installers.bkgd.dirty': (_(u'Dirty Installer'),
                              _(u'Tabs: Installers')
                              + u'\n\n' +
                              _(u'This is the background color used for an installer that is configured in a "dirty" manner.  This means changes have been made to its configuration, and an Anneal or Install needs to be performed to make the install match what is configured.'),
                              ),
    'screens.bkgd.image': (_(u'Screenshot Background'),
                           _(u'Tabs: Saves, Screens')
                           + u'\n\n' +
                           _(u'This is the background color used for images.'),
                           ),
    }

#--Information about the various Tabs
tabInfo = {
    # InternalName: [className, title, instance]
    'Installers': ['InstallersPanel', _(u"Installers"), None],
    'Mods': ['ModPanel', _(u"Mods"), None],
    'Saves': ['SavePanel', _(u"Saves"), None],
    'INI Edits': ['INIPanel', _(u"INI Edits"), None],
    'Screenshots': ['ScreensPanel', _(u"Screenshots"), None],
    'PM Archive':['MessagePanel', _(u"PM Archive"), None],
    'People':['PeoplePanel', _(u"People"), None],
    }

#--Load config/defaults
settingDefaults = {
    #--Basics
    'bash.version': 0,
    'bash.readme': (0,u'0'),
    'bash.CBashEnabled': True,
    'bash.backupPath': None,
    'bash.framePos': (-1,-1),
    'bash.frameSize': (1024,600),
    'bash.frameSize.min': (400,600),
    'bash.frameMax': False, # True if maximized
    'bash.page':1,
    'bash.useAltName':True,
    'bash.pluginEncoding': 'cp1252',    # Western European
    #--Colors
    'bash.colors': {
        #--Common Colors
        'default.text':                 'BLACK',
        'default.bkgd':                 'WHITE',
        #--Mods Tab
        'mods.text.esm':                'BLUE',
        'mods.text.mergeable':          (0x00, 0x99, 0x00),
        'mods.text.noMerge':            (0x99, 0x00, 0x99),
        'mods.bkgd.doubleTime.exists':  (0xFF, 0xDC, 0xDC),
        'mods.bkgd.doubleTime.load':    (0xFF, 0x64, 0x64),
        'mods.bkgd.deactivate':         (0xFF, 0x64, 0x64),
        'mods.bkgd.exOverload':         (0xFF, 0x99, 0x00),
        'mods.bkgd.ghosted':            (0xE8, 0xE8, 0xE8),
        'mods.bkgd.groupHeader':        (0xD8, 0xD8, 0xD8),
        #--INI Edits Tab
        'ini.bkgd.invalid':             (0xDF, 0xDF, 0xDF),
        'tweak.bkgd.invalid':           (0xFF, 0xD5, 0xAA),
        'tweak.bkgd.mismatched':        (0xFF, 0xFF, 0xBF),
        'tweak.bkgd.matched':           (0xC1, 0xFF, 0xC1),
        #--Installers Tab
        'installers.text.complex':      'NAVY',
        'installers.text.invalid':      'GREY',
        'installers.bkgd.skipped':      (0xE0, 0xE0, 0xE0),
        'installers.bkgd.outOfOrder':   (0xFF, 0xFF, 0x00),
        'installers.bkgd.dirty':        (0xFF, 0xBB, 0x33),
        #--Screens Tab
        'screens.bkgd.image':           (0x64, 0x64, 0x64),
        },
    #--BSA Redirection
    'bash.bsaRedirection':True,
    #--Wrye Bash: Load Lists
    'bash.loadLists.data': {},
    #--Wrye Bash: Tabs
    'bash.tabs': {
        'Installers': True,
        'Mods': True,
        'Saves': True,
        'INI Edits': True,
        'Screenshots': True,
        'PM Archive': False,
        'People': False,
        },
    'bash.tabs.order': [
        'Installers',
        'Mods',
        'Saves',
        'INI Edits',
        'Screenshots',
        'PM Archive',
        'People',
        ],
    #--Wrye Bash: StatusBar
    'bash.statusbar.iconSize': 16,
    'bash.statusbar.hide': set(),
    'bash.statusbar.order': [],
    'bash.statusbar.showversion': False,
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
        'Mod Status': _(u'Mod Status'),
        'Author': _(u'Author'),
        'Cell': _(u'Cell'),
        'CRC':_(u'CRC'),
        'Current Order': _(u'Current LO'),
        'Date': _(u'Date'),
        'Day': _(u'Day'),
        'File': _(u'File'),
        'Files': _(u'Files'),
        'Group': _(u'Group'),
        'Header': _(u'Header'),
        'Installer':_(u'Installer'),
        'Karma': _(u'Karma'),
        'Load Order': _(u'Load Order'),
        'Modified': _(u'Modified'),
        'Name': _(u'Name'),
        'Num': _(u'MI'),
        'Order': _(u'Order'),
        'Package': _(u'Package'),
        'PlayTime':_(u'Hours'),
        'Player': _(u'Player'),
        'Rating': _(u'Rating'),
        'Save Order': _(u'Save Order'),
        'Size': _(u'Size'),
        'Status': _(u'Status'),
        'Subject': _(u'Subject'),
        },
    #--Wrye Bash: Masters
    'bash.masters.cols': ['File','Num', 'Current Order'],
    'bash.masters.esmsFirst': 1,
    'bash.masters.selectedFirst': 0,
    'bash.masters.sort': 'Num',
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
    'bash.installers.allCols': ['Package','Order','Modified','Size','Files'],
    'bash.installers.cols': ['Package','Order','Modified','Size','Files'],
    'bash.installers.colReverse': {},
    'bash.installers.sort': 'Order',
    'bash.installers.colWidths': {
        'Package':230,
        'Order':25,
        'Modified':135,
        'Size':75,
        'Files':55,
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
    'bash.installers.autoWizard':True,
    'bash.installers.wizardOverlay':True,
    'bash.installers.fastStart': True,
    'bash.installers.autoRefreshBethsoft': False,
    'bash.installers.autoRefreshProjects': True,
    'bash.installers.autoApplyEmbeddedBCFs': True,
    'bash.installers.removeEmptyDirs':True,
    'bash.installers.skipScreenshots':False,
    'bash.installers.skipImages':False,
    'bash.installers.skipDocs':False,
    'bash.installers.skipDistantLOD':False,
    'bash.installers.skipLandscapeLODMeshes':False,
    'bash.installers.skipLandscapeLODTextures':False,
    'bash.installers.skipLandscapeLODNormals':False,
    'bash.installers.allowOBSEPlugins':True,
    'bash.installers.renameStrings':True,
    'bash.installers.sortProjects':False,
    'bash.installers.sortActive':False,
    'bash.installers.sortStructure':False,
    'bash.installers.conflictsReport.showLower':True,
    'bash.installers.conflictsReport.showInactive':False,
    'bash.installers.conflictsReport.showBSAConflicts':False,
    'bash.installers.goodDlls':{},
    'bash.installers.badDlls':{},
    'bash.installers.onDropFiles.action':None,
    'bash.installers.commentsSplitterSashPos':0,

    #--Wrye Bash: Wizards
    'bash.wizard.size': (600,500),
    'bash.wizard.pos': wx.DefaultPosition,

    #--Wrye Bash: INI Tweaks
    'bash.ini.allCols': ['File','Installer'],
    'bash.ini.cols': ['File','Installer'],
    'bash.ini.sort': 'File',
    'bash.ini.colReverse': {},
    'bash.ini.sortValid': True,
    'bash.ini.colWidths': {
        'File':300,
        'Installer':100,
        },
    'bash.ini.colAligns': {},
    'bash.ini.choices': {},
    'bash.ini.choice': 0,
    'bash.ini.allowNewLines': bush.game.ini.allowNewLines,
    #--Wrye Bash: Mods
    'bash.mods.allCols': ['File','Load Order','Rating','Group','Installer','Modified','Size','Author','CRC','Mod Status'],
    'bash.mods.cols': ['File','Load Order','Installer','Modified','Size','Author','CRC'],
    'bash.mods.esmsFirst': 1,
    'bash.mods.selectedFirst': 0,
    'bash.mods.sort': 'Load Order',
    'bash.mods.colReverse': {},
    'bash.mods.colWidths': {
        'Author':100,
        'File':200,
        'Group':10,
        'Installer':100,
        'Load Order':25,
        'Modified':135,
        'Rating':10,
        'Size':75,
        'CRC':60,
        'Mod Status':50,
        },
    'bash.mods.colAligns': {
        'Size':1,
        'Load Order':1,
        },
    'bash.mods.renames': {},
    'bash.mods.scanDirty': False,
    'bash.mods.export.skip': u'',
    'bash.mods.export.deprefix': u'',
    'bash.mods.export.skipcomments': False,
    #--Wrye Bash: Saves
    'bash.saves.allCols': ['File','Modified','Size','PlayTime','Player','Cell'],
    'bash.saves.cols': ['File','Modified','Size','PlayTime','Player','Cell'],
    'bash.saves.sort': 'Modified',
    'bash.saves.colReverse': {
        'Modified':1,
        },
    'bash.saves.colWidths': {
        'File':375,
        'Modified':135,
        'Size':65,
        'PlayTime':50,
        'Player':70,
        'Cell':80,
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
    #--Wrye Bash: Screens
    'bash.screens.allCols': ['File'],
    'bash.screens.cols': ['File'],
    'bash.screens.sort': 'File',
    'bash.screens.colReverse': {
        'Modified':1,
        },
    'bash.screens.colWidths': {
        'File':100,
        'Modified':150,
        'Size':75,
        },
    'bash.screens.colAligns': {},
    'bash.screens.jpgQuality': 95,
    'bash.screens.jpgCustomQuality': 75,
    #--Wrye Bash: Messages
    'bash.messages.allCols': ['Subject','Author','Date'],
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
    'bash.people.allCols': ['Name','Karma','Header'],
    'bash.people.cols': ['Name','Karma','Header'],
    'bash.people.sort': 'Name',
    'bash.people.colReverse': {},
    'bash.people.colWidths': {
        'Name': 80,
        'Karma': 25,
        'Header': 50,
        },
    'bash.people.colAligns': {
        'Karma': 1,
        },
    #--Tes4View/Edit/Trans
    'tes4View.iKnowWhatImDoing':False,
    'tes5View.iKnowWhatImDoing':False,
    #--BOSS:
    'BOSS.ClearLockTimes':True,
    'BOSS.AlwaysUpdate':True,
    'BOSS.UseGUI':False,
    }

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
ID_EDIT   = 6005
ID_BACK   = 6006
ID_NEXT   = 6007

#--File Menu
ID_REVERT_BACKUP = 6100
ID_REVERT_FIRST  = 6101
ID_BACKUP_NOW    = 6102

#--Label Menus
ID_LOADERS   = balt.IdList(10000, 90,'SAVE','EDIT','NONE','ALL')
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
        for state in (u'on',u'off',u'inc',u'imp'):
            for status in (u'purple',u'blue',u'green',u'orange',u'yellow',u'red'):
                shortKey = status+u'.'+state
                imageKey = u'checkbox.'+shortKey
                file = GPath(bosh.dirs['images'].join(u'checkbox_'+status+u'_'+state+u'.png'))
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
    'karma+5': Image(GPath(bosh.dirs['images'].join(u'checkbox_purple_inc.png')),wx.BITMAP_TYPE_PNG),
    'karma+4': Image(GPath(bosh.dirs['images'].join(u'checkbox_blue_inc.png')),wx.BITMAP_TYPE_PNG),
    'karma+3': Image(GPath(bosh.dirs['images'].join(u'checkbox_blue_inc.png')),wx.BITMAP_TYPE_PNG),
    'karma+2': Image(GPath(bosh.dirs['images'].join(u'checkbox_green_inc.png')),wx.BITMAP_TYPE_PNG),
    'karma+1': Image(GPath(bosh.dirs['images'].join(u'checkbox_green_inc.png')),wx.BITMAP_TYPE_PNG),
    'karma+0': Image(GPath(bosh.dirs['images'].join(u'checkbox_white_off.png')),wx.BITMAP_TYPE_PNG),
    'karma-1': Image(GPath(bosh.dirs['images'].join(u'checkbox_yellow_off.png')),wx.BITMAP_TYPE_PNG),
    'karma-2': Image(GPath(bosh.dirs['images'].join(u'checkbox_yellow_off.png')),wx.BITMAP_TYPE_PNG),
    'karma-3': Image(GPath(bosh.dirs['images'].join(u'checkbox_orange_off.png')),wx.BITMAP_TYPE_PNG),
    'karma-4': Image(GPath(bosh.dirs['images'].join(u'checkbox_orange_off.png')),wx.BITMAP_TYPE_PNG),
    'karma-5': Image(GPath(bosh.dirs['images'].join(u'checkbox_red_off.png')),wx.BITMAP_TYPE_PNG),
    }.items())
installercons = balt.ImageList(16,16)
installercons.data.extend({
    #--Off/Archive
    'off.green':  Image(GPath(bosh.dirs['images'].join(u'checkbox_green_off.png')),wx.BITMAP_TYPE_PNG),
    'off.grey':   Image(GPath(bosh.dirs['images'].join(u'checkbox_grey_off.png')),wx.BITMAP_TYPE_PNG),
    'off.red':    Image(GPath(bosh.dirs['images'].join(u'checkbox_red_off.png')),wx.BITMAP_TYPE_PNG),
    'off.white':  Image(GPath(bosh.dirs['images'].join(u'checkbox_white_off.png')),wx.BITMAP_TYPE_PNG),
    'off.orange': Image(GPath(bosh.dirs['images'].join(u'checkbox_orange_off.png')),wx.BITMAP_TYPE_PNG),
    'off.yellow': Image(GPath(bosh.dirs['images'].join(u'checkbox_yellow_off.png')),wx.BITMAP_TYPE_PNG),
    #--Off/Archive - Wizard
    'off.green.wiz':    Image(GPath(bosh.dirs['images'].join(u'checkbox_green_off_wiz.png')),wx.BITMAP_TYPE_PNG),
    #grey
    'off.red.wiz':      Image(GPath(bosh.dirs['images'].join(u'checkbox_red_off_wiz.png')),wx.BITMAP_TYPE_PNG),
    'off.white.wiz':    Image(GPath(bosh.dirs['images'].join(u'checkbox_white_off_wiz.png')),wx.BITMAP_TYPE_PNG),
    'off.orange.wiz':   Image(GPath(bosh.dirs['images'].join(u'checkbox_orange_off_wiz.png')),wx.BITMAP_TYPE_PNG),
    'off.yellow.wiz':   Image(GPath(bosh.dirs['images'].join(u'checkbox_yellow_off_wiz.png')),wx.BITMAP_TYPE_PNG),
    #--On/Archive
    'on.green':  Image(GPath(bosh.dirs['images'].join(u'checkbox_green_inc.png')),wx.BITMAP_TYPE_PNG),
    'on.grey':   Image(GPath(bosh.dirs['images'].join(u'checkbox_grey_inc.png')),wx.BITMAP_TYPE_PNG),
    'on.red':    Image(GPath(bosh.dirs['images'].join(u'checkbox_red_inc.png')),wx.BITMAP_TYPE_PNG),
    'on.white':  Image(GPath(bosh.dirs['images'].join(u'checkbox_white_inc.png')),wx.BITMAP_TYPE_PNG),
    'on.orange': Image(GPath(bosh.dirs['images'].join(u'checkbox_orange_inc.png')),wx.BITMAP_TYPE_PNG),
    'on.yellow': Image(GPath(bosh.dirs['images'].join(u'checkbox_yellow_inc.png')),wx.BITMAP_TYPE_PNG),
    #--On/Archive - Wizard
    'on.green.wiz':  Image(GPath(bosh.dirs['images'].join(u'checkbox_green_inc_wiz.png')),wx.BITMAP_TYPE_PNG),
    #grey
    'on.red.wiz':    Image(GPath(bosh.dirs['images'].join(u'checkbox_red_inc_wiz.png')),wx.BITMAP_TYPE_PNG),
    'on.white.wiz':  Image(GPath(bosh.dirs['images'].join(u'checkbox_white_inc_wiz.png')),wx.BITMAP_TYPE_PNG),
    'on.orange.wiz': Image(GPath(bosh.dirs['images'].join(u'checkbox_orange_inc_wiz.png')),wx.BITMAP_TYPE_PNG),
    'on.yellow.wiz': Image(GPath(bosh.dirs['images'].join(u'checkbox_yellow_inc_wiz.png')),wx.BITMAP_TYPE_PNG),
    #--Off/Directory
    'off.green.dir':  Image(GPath(bosh.dirs['images'].join(u'diamond_green_off.png')),wx.BITMAP_TYPE_PNG),
    'off.grey.dir':   Image(GPath(bosh.dirs['images'].join(u'diamond_grey_off.png')),wx.BITMAP_TYPE_PNG),
    'off.red.dir':    Image(GPath(bosh.dirs['images'].join(u'diamond_red_off.png')),wx.BITMAP_TYPE_PNG),
    'off.white.dir':  Image(GPath(bosh.dirs['images'].join(u'diamond_white_off.png')),wx.BITMAP_TYPE_PNG),
    'off.orange.dir': Image(GPath(bosh.dirs['images'].join(u'diamond_orange_off.png')),wx.BITMAP_TYPE_PNG),
    'off.yellow.dir': Image(GPath(bosh.dirs['images'].join(u'diamond_yellow_off.png')),wx.BITMAP_TYPE_PNG),
    #--Off/Directory - Wizard
    'off.green.dir.wiz':  Image(GPath(bosh.dirs['images'].join(u'diamond_green_off_wiz.png')),wx.BITMAP_TYPE_PNG),
    #grey
    'off.red.dir.wiz':    Image(GPath(bosh.dirs['images'].join(u'diamond_red_off_wiz.png')),wx.BITMAP_TYPE_PNG),
    'off.white.dir.wiz':  Image(GPath(bosh.dirs['images'].join(u'diamond_white_off_wiz.png')),wx.BITMAP_TYPE_PNG),
    'off.orange.dir.wiz': Image(GPath(bosh.dirs['images'].join(u'diamond_orange_off_wiz.png')),wx.BITMAP_TYPE_PNG),
    'off.yellow.dir.wiz': Image(GPath(bosh.dirs['images'].join(u'diamond_yellow_off_wiz.png')),wx.BITMAP_TYPE_PNG),
    #--On/Directory
    'on.green.dir':  Image(GPath(bosh.dirs['images'].join(u'diamond_green_inc.png')),wx.BITMAP_TYPE_PNG),
    'on.grey.dir':   Image(GPath(bosh.dirs['images'].join(u'diamond_grey_inc.png')),wx.BITMAP_TYPE_PNG),
    'on.red.dir':    Image(GPath(bosh.dirs['images'].join(u'diamond_red_inc.png')),wx.BITMAP_TYPE_PNG),
    'on.white.dir':  Image(GPath(bosh.dirs['images'].join(u'diamond_white_inc.png')),wx.BITMAP_TYPE_PNG),
    'on.orange.dir': Image(GPath(bosh.dirs['images'].join(u'diamond_orange_inc.png')),wx.BITMAP_TYPE_PNG),
    'on.yellow.dir': Image(GPath(bosh.dirs['images'].join(u'diamond_yellow_inc.png')),wx.BITMAP_TYPE_PNG),
    #--On/Directory - Wizard
    'on.green.dir.wiz':  Image(GPath(bosh.dirs['images'].join(u'diamond_green_inc_wiz.png')),wx.BITMAP_TYPE_PNG),
    #grey
    'on.red.dir.wiz':    Image(GPath(bosh.dirs['images'].join(u'diamond_red_inc_wiz.png')),wx.BITMAP_TYPE_PNG),
    'on.white.dir.wiz':  Image(GPath(bosh.dirs['images'].join(u'diamond_white_off_wiz.png')),wx.BITMAP_TYPE_PNG),
    'on.orange.dir.wiz': Image(GPath(bosh.dirs['images'].join(u'diamond_orange_inc_wiz.png')),wx.BITMAP_TYPE_PNG),
    'on.yellow.dir.wiz': Image(GPath(bosh.dirs['images'].join(u'diamond_yellow_inc_wiz.png')),wx.BITMAP_TYPE_PNG),
    #--Broken
    'corrupt':   Image(GPath(bosh.dirs['images'].join(u'red_x.png')),wx.BITMAP_TYPE_PNG),
    }.items())

#--Icon Bundles
bashRed = None
bashBlue = None
bashDocBrowser = None
bashMonkey = None

fonts = None
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
        if items:
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
                dialog = ListBoxes(self,_(u'Delete Items'),
                             _(u'Delete these items?  This operation cannot be undone.'),
                             [message])
                if dialog.ShowModal() != wx.ID_CANCEL:
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
            item.SetFont(fonts[2])
        else:
            item.SetFont(fonts[0])
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
        iniList = INIList(left)
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
        modList = ModList(left)
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
        saveList = SaveList(left)
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

            self.dialog = dialog= wx.Dialog(self,wx.ID_ANY,_(u'Move or Copy?'),size=(400,200),style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
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
                    button(dialog,label=_(u'Move'),onClick=self.OnClickMove),
                    (button(dialog,label=_(u'Copy'),onClick=self.OnClickCopy),0,wx.LEFT,4),
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

    def OnClickMove(self,event):
        self.dialog.EndModal(1)

    def OnClickCopy(self,event):
        self.dialog.EndModal(2)

    def SelectAll(self):
        for itemDex in range(self.gList.GetItemCount()):
            self.gList.SetItemState(itemDex,wx.LIST_STATE_SELECTED,wx.LIST_STATE_SELECTED)

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
                self.DeleteSelected(True,event.ShiftDown())
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
                self.gList.SetItemState(index,wx.LIST_STATE_SELECTED,wx.LIST_STATE_SELECTED)
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
        name = self.gEspmList.GetString(index).replace('&&','&')
        if name[0] == u'*':
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
                menu.append(Settings_Tab(key,canDisable))
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
        self.SetIcons(bashRed)
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
                    dialog = ListBoxes(self,_(u'Modified Dates Reset'),
                            _(u'Modified dates have been reset for some mod files.'),
                            [message],liststyle='list',Cancel=False)
                    dialog.ShowModal()
                    dialog.Destroy()
            del bosh.modInfos.mtimesReset[:]
            popMods = 'ALL'
        #--Mods autogrouped?
        if bosh.modInfos.autoGrouped:
            message = [u'',_(u'Auto-grouped files')]
            agDict = bosh.modInfos.autoGrouped
            ordered = bosh.modInfos.getOrdered(agDict.keys())
            message.extend(ordered)
            agDict.clear()
            dialog = ListBoxes(self,_(u'Some mods have been auto-grouped:'),
                               _(u'Some mods have been auto-grouped:'),
                               [message],liststyle='list',Cancel=False)
            dialog.ShowModal()
            dialog.Destroy()
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
            dialog = ListBoxes(self,_(u'Warning: Corrupt/Unrecognized Files'),
                     _(u'Some files have corrupted headers or TES4 header versions:'),
                     message,liststyle='list',Cancel=False)
            dialog.ShowModal()
            dialog.Destroy()
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
            dialog = ListBoxes(self,_(u'Warning: Dates Reset'),
                     _(u'Modified dates have been reset to an earlier date for  these files'),
                     [message],liststyle='list',Cancel=False)
            dialog.ShowModal()
            dialog.Destroy()
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
class CheckList_SelectAll(Link):
    def __init__(self,select=True):
        Link.__init__(self)
        self.select = select

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        if self.select:
            text = _(u'Select All')
        else:
            text = _(u'Select None')
        menuItem = wx.MenuItem(menu,self.id,text)
        menu.AppendItem(menuItem)

    def Execute(self,event):
        for i in xrange(self.window.GetCount()):
            self.window.Check(i,self.select)

#------------------------------------------------------------------------------
class ListBoxes(wx.Dialog):
    """A window with 1 or more lists."""
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
        self.SetIcons(bashBlue)
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
        self.SetIcons(bashBlue)
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
        docBrowser = self
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
        self.SetIcons(bashDocBrowser)
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
        modChecker = self
        #--Window
        pos = settings.get('bash.modChecker.pos',balt.defPos)
        size = settings.get('bash.modChecker.size',(475,500))
        wx.Frame.__init__(self, bashFrame, wx.ID_ANY, _(u'Mod Checker'), pos, size,
            style=wx.DEFAULT_FRAME_STYLE)
        self.SetBackgroundColour(wx.NullColour)
        self.SetSizeHints(250,250)
        self.SetIcons(bashBlue)
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
        if wx.TheClipboard.Open():
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
    def Init(self): # not OnInit(), we need to initialize _after_ the app has been instanced
        global appRestart
        appRestart = False
        """wxWindows: Initialization handler."""
        #--OnStartup SplashScreen and/or Progress
        #   Progress gets hidden behind splash by default, since it's not very informative anyway
        splashScreen = None
        progress = wx.ProgressDialog(u'Wrye Bash',_(u'Initializing')+u' '*10,
             style=wx.PD_AUTO_HIDE|wx.PD_APP_MODAL|wx.PD_SMOOTH)
        #   Any users who prefer the progress dialog can rename or delete wryesplash.png
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
        frame = BashFrame(
             pos=settings['bash.framePos'],
             size=settings['bash.frameSize'])
        progress.Destroy()
        if splashScreen:
            splashScreen.Destroy()
        self.SetTopWindow(frame)
        frame.Show()
        balt.ensureDisplayed(frame)

    def InitResources(self):
        """Init application resources."""
        global bashBlue, bashRed, bashDocBrowser, bashMonkey, fonts
        bashBlue = bashBlue.GetIconBundle()
        bashRed = bashRed.GetIconBundle()
        bashDocBrowser = bashDocBrowser.GetIconBundle()
        bashMonkey = bashMonkey.GetIconBundle()
        fonts = balt.fonts()

    def InitData(self,progress):
        """Initialize all data. Called by OnInit()."""
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
        balt.showOk(self,_(u'Face imported.'),self.fileInfo.name.s)
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
    patchers = []       #--All patchers. These are copied as needed.
    CBash_patchers = [] #--All patchers (CBash mode).  These are copied as needed.

    def __init__(self,parent,patchInfo,doCBash=None,importConfig=True):
        """Initialized."""
        self.parent = parent
        if (doCBash or doCBash is None) and settings['bash.CBashEnabled']:
            doCBash = True
        else:
            doCBash = False
        self.doCBash = doCBash
        size = balt.sizes.get(self.__class__.__name__,(500,600))
        wx.Dialog.__init__(self,parent,wx.ID_ANY,_(u'Update ')+patchInfo.name.s+[u'',u' (CBash)'][doCBash], size=size,
            style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.SetSizeHints(400,300)
        #--Data
        groupOrder = dict([(group,index) for index,group in
            enumerate((_(u'General'),_(u'Importers'),_(u'Tweakers'),_(u'Special')))])
        patchConfigs = bosh.modInfos.table.getItem(patchInfo.name,'bash.patch.configs',{})
        # If the patch config isn't from the same mode (CBash/Python), try converting
        # it over to the current mode
        configIsCBash = bosh.CBash_PatchFile.configIsCBash(patchConfigs)
        if configIsCBash != self.doCBash:
            if importConfig:
                patchConfigs = self.ConvertConfig(patchConfigs)
            else:
                patchConfigs = {}
        isFirstLoad = 0 == len(patchConfigs)
        self.patchInfo = patchInfo
        if doCBash:
            self.patchers = [copy.deepcopy(patcher) for patcher in PatchDialog.CBash_patchers]
        else:
            self.patchers = [copy.deepcopy(patcher) for patcher in PatchDialog.patchers]
        self.patchers.sort(key=lambda a: a.__class__.name)
        self.patchers.sort(key=lambda a: groupOrder[a.__class__.group])
        for patcher in self.patchers:
            patcher.getConfig(patchConfigs) #--Will set patcher.isEnabled
            if u'UNDEFINED' in (patcher.__class__.group, patcher.__class__.group):
                raise UncodedError(u'Name or group not defined for: %s' % patcher.__class__.__name__)
            patcher.SetCallbackFns(self._CheckPatcher, self._BoldPatcher)
            patcher.SetIsFirstLoad(isFirstLoad)
        self.currentPatcher = None
        patcherNames = [patcher.getName() for patcher in self.patchers]
        #--GUI elements
        self.gExecute = button(self,id=wx.ID_OK,label=_(u'Build Patch'),onClick=self.Execute)
        SetUAC(self.gExecute)
        self.gSelectAll = button(self,id=wx.wx.ID_SELECTALL,label=_(u'Select All'),onClick=self.SelectAll)
        self.gDeselectAll = button(self,id=wx.wx.ID_SELECTALL,label=_(u'Deselect All'),onClick=self.DeselectAll)
        cancelButton = button(self,id=wx.ID_CANCEL,label=_(u'Cancel'))
        self.gPatchers = wx.CheckListBox(self,wx.ID_ANY,choices=patcherNames,style=wx.LB_SINGLE)
        self.gExportConfig = button(self,id=wx.ID_SAVEAS,label=_(u'Export'),onClick=self.ExportConfig)
        self.gImportConfig = button(self,id=wx.ID_OPEN,label=_(u'Import'),onClick=self.ImportConfig)
        self.gRevertConfig = button(self,id=wx.ID_REVERT_TO_SAVED,label=_(u'Revert To Saved'),onClick=self.RevertConfig)
        self.gRevertToDefault = button(self,id=wx.ID_REVERT,label=_(u'Revert To Default'),onClick=self.DefaultConfig)
        for index,patcher in enumerate(self.patchers):
            self.gPatchers.Check(index,patcher.isEnabled)
        self.defaultTipText = _(u'Items that are new since the last time this patch was built are displayed in bold')
        self.gTipText = staticText(self,self.defaultTipText)
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
                (self.gExportConfig,0,wx.LEFT,4),
                (self.gImportConfig,0,wx.LEFT,4),
                (self.gRevertConfig,0,wx.LEFT,4),
                (self.gRevertToDefault,0,wx.LEFT,4),
                ),0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,4),
            (hSizer(
                spacer,
                self.gExecute,
                (self.gSelectAll,0,wx.LEFT,4),
                (self.gDeselectAll,0,wx.LEFT,4),
                (cancelButton,0,wx.LEFT,4),
                ),0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,4)
            )
        self.SetSizer(sizer)
        self.SetIcons(bashMonkey)
        #--Patcher panels
        for patcher in self.patchers:
            gConfigPanel = patcher.GetConfigPanel(self,gConfigSizer,self.gTipText)
            gConfigSizer.Show(gConfigPanel,False)
        self.gPatchers.Select(1)
        self.ShowPatcher(self.patchers[1])
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
        if self.currentPatcher is not None:
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
        progress = balt.Progress(patchName.s,(u' '*60+u'\n'), abort=True)
        ###Remove from Bash after CBash integrated
        patchFile = None
        if self.doCBash: # TODO: factor out duplicated code in this if/else!!
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
                log = bolt.LogFile(StringIO.StringIO())
                patchers = [patcher for patcher in self.patchers if patcher.isEnabled]

                patchFile = bosh.CBash_PatchFile(patchName,patchers)
                #try to speed this up!
                patchFile.initData(SubProgress(progress,0,0.1))
                #try to speed this up!
                patchFile.buildPatch(SubProgress(progress,0.1,0.9))
                #no speeding needed/really possible (less than 1/4 second even with large LO)
                patchFile.buildPatchLog(patchName,log,SubProgress(progress,0.95,0.99))
                #--Save
                progress.setCancel(False)
                progress(1.0,patchName.s+u'\n'+_(u'Saving...'))
                patchFile.save()
                patchTime = fullName.mtime
                try:
                    patchName.untemp()
                except WindowsError, werr:
                    if werr.winerror != 32: raise
                    while balt.askYes(self,(_(u'Bash encountered an error when renaming %s to %s.')
                                            + u'\n\n' +
                                            _(u'The file is in use by another process such as TES4Edit.')
                                            + u'\n' +
                                            _(u'Please close the other program that is accessing %s.')
                                            + u'\n\n' +
                                            _(u'Try again?')) % (patchName.temp.s, patchName.s, patchName.s),
                                      _(u'Bash Patch - Save Error')):
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
                log(u'{{CSS:wtxt_sand_small.css}}')
                logValue = log.out.getvalue()
                log.out.close()
                timerString = unicode(timedelta(seconds=round(timer2 - timer1, 3))).rstrip(u'0')
                logValue = re.sub(u'TIMEPLACEHOLDER', timerString, logValue, 1)
                readme = bosh.modInfos.dir.join(u'Docs',patchName.sroot+u'.txt')
                with readme.open('w',encoding='utf-8') as file:
                    file.write(logValue)
                bosh.modInfos.table.setItem(patchName,'doc',readme)
                #--Convert log/readme to wtxt and show log
                docsDir = settings.get('balt.WryeLog.cssDir', GPath(u'')) #bosh.modInfos.dir.join(u'Docs')
                bolt.WryeText.genHtml(readme,None,docsDir)
                balt.playSound(self.parent,bosh.inisettings['SoundSuccess'].s)
                balt.showWryeLog(self.parent,readme.root+u'.html',patchName.s,icons=bashBlue)
                #--Select?
                message = _(u'Activate %s?') % patchName.s
                if bosh.inisettings['PromptActivateBashedPatch'] \
                         and (bosh.modInfos.isSelected(patchName) or
                         balt.askYes(self.parent,message,patchName.s)):
                    try:
                        oldFiles = bosh.modInfos.ordered[:]
                        bosh.modInfos.select(patchName)
                        changedFiles = bolt.listSubtract(bosh.modInfos.ordered,oldFiles)
                        if len(changedFiles) > 1:
                            statusBar.SetText(_(u'Masters Activated: ') + unicode(len(changedFiles)-1))
                        bosh.modInfos[patchName].setGhost(False)
                        bosh.modInfos.refreshInfoLists()
                    except bosh.PluginsFullError:
                        balt.showError(self,
                            _(u'Unable to add mod %s because load list is full.')
                            % patchName.s)
                    modList.RefreshUI()
            except bolt.FileEditError, error:
                balt.playSound(self.parent,bosh.inisettings['SoundError'].s)
                balt.showError(self,u'%s'%error,_(u'File Edit Error'))
            except BoltError, error:
                balt.playSound(self.parent,bosh.inisettings['SoundError'].s)
                balt.showError(self,u'%s'%error,_(u'Processing Error'))
            except CancelError:
                pass
            except:
                balt.playSound(self.parent,bosh.inisettings['SoundError'].s)
                raise
            finally:
                try:
                    patchFile.Current.Close()
                except:
                    pass
                progress.Destroy()
        else:
            try:
                from datetime import timedelta
                timer1 = time.clock()
                #--Save configs
                patchConfigs = {'ImportedMods':set()}
                for patcher in self.patchers:
                    patcher.saveConfig(patchConfigs)
                bosh.modInfos.table.setItem(patchName,'bash.patch.configs',patchConfigs)
                #--Do it
                log = bolt.LogFile(StringIO.StringIO())
                nullProgress = bolt.Progress()
                patchers = [patcher for patcher in self.patchers if patcher.isEnabled]
                patchFile = bosh.PatchFile(self.patchInfo,patchers)
                patchFile.initData(SubProgress(progress,0,0.1)) #try to speed this up!
                patchFile.initFactories(SubProgress(progress,0.1,0.2)) #no speeding needed/really possible (less than 1/4 second even with large LO)
                patchFile.scanLoadMods(SubProgress(progress,0.2,0.8)) #try to speed this up!
                patchFile.buildPatch(log,SubProgress(progress,0.8,0.9))#no speeding needed/really possible (less than 1/4 second even with large LO)
                #--Save
                progress.setCancel(False)
                progress(0.9,patchName.s+u'\n'+_(u'Saving...'))
                message = (_(u'Bash encountered and error when saving %(patchName)s.')
                           + u'\n\n' +
                           _(u'Either Bash needs Administrator Privileges to save the file, or the file is in use by another process such as TES4Edit.')
                           + u'\n' +
                           _(u'Please close any program that is accessing %(patchName)s, and provide Administrator Privileges if prompted to do so.')
                           + u'\n\n' +
                           _(u'Try again?')) % {'patchName':patchName.s}
                while True:
                    try:
                        patchFile.safeSave()
                    except (CancelError,SkipError,WindowsError) as error:
                        if isinstance(error,WindowsError) and error.winerror != 32:
                            raise
                        if balt.askYes(self,message,_(u'Bash Patch - Save Error')):
                            continue
                        raise CancelError
                    break

                #--Cleanup
                self.patchInfo.refresh()
                modList.RefreshUI(patchName)
                #--Done
                progress.Destroy()
                timer2 = time.clock()
                #--Readme and log
                log.setHeader(None)
                log(u'{{CSS:wtxt_sand_small.css}}')
                logValue = log.out.getvalue()
                log.out.close()
                timerString = unicode(timedelta(seconds=round(timer2 - timer1, 3))).rstrip(u'0')
                logValue = re.sub(u'TIMEPLACEHOLDER', timerString, logValue, 1)
                readme = bosh.modInfos.dir.join(u'Docs',patchName.sroot+u'.txt')
                tempReadmeDir = Path.tempDir(u'WryeBash_').join(u'Docs')
                tempReadme = tempReadmeDir.join(patchName.sroot+u'.txt')
                #--Write log/readme to temp dir first
                with tempReadme.open('w',encoding='utf-8-sig') as file:
                    file.write(logValue)
                #--Convert log/readmeto wtxt
                docsDir = settings.get('balt.WryeLog.cssDir', GPath(u''))
                bolt.WryeText.genHtml(tempReadme,None,docsDir)
                #--Try moving temp log/readme to Docs dir
                try:
                    balt.shellMove(tempReadmeDir,bosh.dirs['mods'],self,False,False,False)
                except (CancelError,SkipError):
                    # User didn't allow UAC, move to My Games directoy instead
                    balt.shellMove([tempReadme,tempReadme.root+u'.html'],bosh.dirs['saveBase'],self,False,False,False)
                    readme = bosh.dirs['saveBase'].join(readme.tail)
                #finally:
                #    tempReadmeDir.head.rmtree(safety=tempReadmeDir.head.stail)
                bosh.modInfos.table.setItem(patchName,'doc',readme)
                #--Convert log/readme to wtxt and show log
                balt.playSound(self.parent,bosh.inisettings['SoundSuccess'].s)
                balt.showWryeLog(self.parent,readme.root+u'.html',patchName.s,icons=bashBlue)
                #--Select?
                message = _(u'Activate %s?') % patchName.s
                if bosh.inisettings['PromptActivateBashedPatch'] \
                         and (bosh.modInfos.isSelected(patchName) or
                          balt.askYes(self.parent,message,patchName.s)):
                    try:
                        # Note to the regular WB devs:
                        #  The bashed patch wasn't activating when it had been manually deleting. So, on
                        #   startup, WB would create a new one, but something, somewhere (libloadorder?) wasn't
                        #   registering this so when this: bosh.modInfos.select(patchName) executed, bash
                        #   couldn't actually find anything to execute. This fix really belongs somewhere else
                        #   (after the patch is recreated?), but I don't know where it goes, so I'm sticking it
                        #   here until one of you come back or I find a better place.
                        bosh.modInfos.plugins.refresh(True)
                        oldFiles = bosh.modInfos.ordered[:]
                        bosh.modInfos.select(patchName)
                        changedFiles = bolt.listSubtract(bosh.modInfos.ordered,oldFiles)
                        if len(changedFiles) > 1:
                            statusBar.SetText(_(u'Masters Activated: ') + unicode(len(changedFiles)-1))
                        bosh.modInfos[patchName].setGhost(False)
                        bosh.modInfos.refreshInfoLists()
                    except bosh.PluginsFullError:
                        balt.showError(self,
                            _(u'Unable to add mod %s because load list is full.')
                            % patchName.s)
                    modList.RefreshUI()
            except bolt.FileEditError, error:
                balt.playSound(self.parent,bosh.inisettings['SoundError'].s)
                balt.showError(self,u'%s'%error,_(u'File Edit Error'))
            except BoltError, error:
                balt.playSound(self.parent,bosh.inisettings['SoundError'].s)
                balt.showError(self,u'%s'%error,_(u'Processing Error'))
            except CancelError:
                pass
            except:
                balt.playSound(self.parent,bosh.inisettings['SoundError'].s)
                raise
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
        patchName = self.patchInfo.name + _(u'_Configuration.dat')
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.parent,_(u'Export Bashed Patch configuration to:'),
                                textDir,patchName, u'*Configuration.dat')
        if not textPath: return
        pklPath = textPath+u'.pkl'
        table = bolt.Table(bosh.PickleDict(textPath, pklPath))
        patchConfigs = {'ImportedMods':set()}
        for patcher in self.patchers:
            patcher.saveConfig(patchConfigs)
        table.setItem(GPath(u'Saved Bashed Patch Configuration (%s)' % ([u'Python',u'CBash'][self.doCBash])),'bash.patch.configs',patchConfigs)
        table.save()

    def ImportConfig(self,event=None):
        """Import the configuration to a user selected dat file."""
        patchName = self.patchInfo.name + _(u'_Configuration.dat')
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askOpen(self.parent,_(u'Import Bashed Patch configuration from:'),textDir,patchName, u'*.dat',mustExist=True)
        if not textPath: return
        pklPath = textPath+u'.pkl'
        table = bolt.Table(bosh.PickleDict(
            textPath, pklPath))
        #try the current Bashed Patch mode.
        patchConfigs = table.getItem(GPath(u'Saved Bashed Patch Configuration (%s)' % ([u'Python',u'CBash'][self.doCBash])),'bash.patch.configs',{})
        if not patchConfigs: #try the old format:
            patchConfigs = table.getItem(GPath(u'Saved Bashed Patch Configuration'),'bash.patch.configs',{})
            if patchConfigs:
                configIsCBash = bosh.CBash_PatchFile.configIsCBash(patchConfigs)
                if configIsCBash != self.doCBash:
                    patchConfigs = self.UpdateConfig(patchConfigs)
            else:   #try the non-current Bashed Patch mode:
                patchConfigs = table.getItem(GPath(u'Saved Bashed Patch Configuration (%s)' % ([u'CBash',u'Python'][self.doCBash])),'bash.patch.configs',{})
                if patchConfigs:
                    patchConfigs = self.UpdateConfig(patchConfigs)
        if patchConfigs is None:
            patchConfigs = {}
        for index,patcher in enumerate(self.patchers):
            patcher.SetIsFirstLoad(False)
            patcher.getConfig(patchConfigs)
            self.gPatchers.Check(index,patcher.isEnabled)
            if hasattr(patcher, 'gList'):
                if patcher.getName() == 'Leveled Lists': continue #not handled yet!
                for index, item in enumerate(patcher.items):
                    try:
                        patcher.gList.Check(index,patcher.configChecks[item])
                    except KeyError: pass#deprint(_(u'item %s not in saved configs') % (item))
            if hasattr(patcher, 'gTweakList'):
                for index, item in enumerate(patcher.tweaks):
                    try:
                        patcher.gTweakList.Check(index,item.isEnabled)
                        patcher.gTweakList.SetString(index,item.getListLabel())
                    except: deprint(_(u'item %s not in saved configs') % item)
        self.SetOkEnable()

    def UpdateConfig(self,patchConfigs,event=None):
        if not balt.askYes(self.parent,
            _(u"Wrye Bash detects that the selected file was saved in Bash's %s mode, do you want Wrye Bash to attempt to adjust the configuration on import to work with %s mode (Good chance there will be a few mistakes)? (Otherwise this import will have no effect.)")
                % ([u'CBash',u'Python'][self.doCBash],
                   [u'Python',u'CBash'][self.doCBash])):
            return
        if self.doCBash:
            bosh.PatchFile.patchTime = bosh.CBash_PatchFile.patchTime
            bosh.PatchFile.patchName = bosh.CBash_PatchFile.patchName
        else:
            bosh.CBash_PatchFile.patchTime = bosh.PatchFile.patchTime
            bosh.CBash_PatchFile.patchName = bosh.PatchFile.patchName
        return self.ConvertConfig(patchConfigs)

    def ConvertConfig(self,patchConfigs):
        newConfig = {}
        for key in patchConfigs:
            if key in otherPatcherDict:
                newConfig[otherPatcherDict[key].__class__.__name__] = patchConfigs[key]
            else:
                newConfig[key] = patchConfigs[key]
        return newConfig

    def RevertConfig(self,event=None):
        """Revert configuration back to saved"""
        patchConfigs = bosh.modInfos.table.getItem(self.patchInfo.name,'bash.patch.configs',{})
        if bosh.CBash_PatchFile.configIsCBash(patchConfigs) and not self.doCBash:
            patchConfigs = self.ConvertConfig(patchConfigs)
        for index,patcher in enumerate(self.patchers):
            patcher.SetIsFirstLoad(False)
            patcher.getConfig(patchConfigs)
            self.gPatchers.Check(index,patcher.isEnabled)
            if hasattr(patcher, 'gList'):
                if patcher.getName() == 'Leveled Lists': continue #not handled yet!
                for index, item in enumerate(patcher.items):
                    try: patcher.gList.Check(index,patcher.configChecks[item])
                    except Exception, err: deprint(_(u'Error reverting Bashed patch configuration (error is: %s). Item %s skipped.') % (err,item))
            if hasattr(patcher, 'gTweakList'):
                for index, item in enumerate(patcher.tweaks):
                    try:
                        patcher.gTweakList.Check(index,item.isEnabled)
                        patcher.gTweakList.SetString(index,item.getListLabel())
                    except Exception, err: deprint(_(u'Error reverting Bashed patch configuration (error is: %s). Item %s skipped.') % (err,item))
        self.SetOkEnable()

    def DefaultConfig(self,event=None):
        """Revert configuration back to default"""
        patchConfigs = {}
        for index,patcher in enumerate(self.patchers):
            patcher.SetIsFirstLoad(True)
            patcher.getConfig(patchConfigs)
            self.gPatchers.Check(index,patcher.isEnabled)
            if hasattr(patcher, 'gList'):
                patcher.SetItems(patcher.getAutoItems())
            if hasattr(patcher, 'gTweakList'):
                for index, item in enumerate(patcher.tweaks):
                    try:
                        patcher.gTweakList.Check(index,item.isEnabled)
                        patcher.gTweakList.SetString(index,item.getListLabel())
                    except Exception, err: deprint(_(u'Error reverting Bashed patch configuration (error is: %s). Item %s skipped.') % (err,item))
        self.SetOkEnable()

    def SelectAll(self,event=None):
        """Select all patchers and entries in patchers with child entries."""
        for index,patcher in enumerate(self.patchers):
            self.gPatchers.Check(index,True)
            patcher.isEnabled = True
            if hasattr(patcher, 'gList'):
                if patcher.getName() == 'Leveled Lists': continue
                for index, item in enumerate(patcher.items):
                    patcher.gList.Check(index,True)
                    patcher.configChecks[item] = True
            if hasattr(patcher, 'gTweakList'):
                for index, item in enumerate(patcher.tweaks):
                    patcher.gTweakList.Check(index,True)
                    item.isEnabled = True
            self.gExecute.Enable(True)

    def DeselectAll(self,event=None):
        """Deselect all patchers and entries in patchers with child entries."""
        for index,patcher in enumerate(self.patchers):
            self.gPatchers.Check(index,False)
            patcher.isEnabled = False
            if patcher.getName() in [_(u'Leveled Lists'),_(u"Alias Mod Names")]: continue # special case that one.
            if hasattr(patcher, 'gList'):
                patcher.gList.SetChecked([])
                patcher.OnListCheck()
            if hasattr(patcher, 'gTweakList'):
                patcher.gTweakList.SetChecked([])
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

    def _CheckPatcher(self,patcher):
        """Remotely enables a patcher.  Called from a particular patcher's OnCheck method."""
        index = self.patchers.index(patcher)
        self.gPatchers.Check(index)
        patcher.isEnabled = True
        self.SetOkEnable()

    def _BoldPatcher(self,patcher):
        """Set the patcher label to bold font.  Called from a patcher when it realizes it has something new in its list"""
        index = self.patchers.index(patcher)
        font = self.gPatchers.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        self.gPatchers.SetItemFont(index, font)

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
            self.gTipText.SetLabel(self.defaultTipText)
            self.mouseItem = -1
        event.Skip()

    def MouseEnteredItem(self,item):
        """Show tip text when changing item."""
        #--Following isn't displaying correctly.
        if item < len(self.patchers):
            patcherClass = self.patchers[item].__class__
            tip = patcherClass.tip or re.sub(ur'\..*',u'.',patcherClass.text.split(u'\n')[0],flags=re.U)
            self.gTipText.SetLabel(tip)
        else:
            self.gTipText.SetLabel(self.defaultTipText)

    def OnChar(self,event):
        """Keyboard input to the patchers list box"""
        if event.GetKeyCode() == 1 and event.CmdDown(): # Ctrl+'A'
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
    def SetCallbackFns(self,checkPatcherFn,boldPatcherFn):
        self._checkPatcherFn = checkPatcherFn
        self._boldPatcherFn = boldPatcherFn

    def SetIsFirstLoad(self,isFirstLoad):
        self._isFirstLoad = isFirstLoad

    def _EnsurePatcherEnabled(self):
        if hasattr(self, '_checkPatcherFn'):
            self._checkPatcherFn(self)

    def _BoldPatcherLabel(self):
        if hasattr(self, '_boldPatcherFn'):
            self._boldPatcherFn(self)

    def _GetIsFirstLoad(self):
        if hasattr(self, '_isFirstLoad'):
            return self._isFirstLoad
        else:
            return False

    """Basic patcher panel with no options."""
    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if not self.gConfigPanel:
            self.gTipText = gTipText
            gConfigPanel = self.gConfigPanel = wx.Window(parent,wx.ID_ANY)
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

#------------------------------------------------------------------------------
class AliasesPatcher(Patcher, AliasesPatcher):
    """Basic patcher panel with no options."""
    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        #--Else...
        #--Tip
        self.gTipText = gTipText
        gConfigPanel = self.gConfigPanel = wx.Window(parent,wx.ID_ANY)
        text = fill(self.__class__.text,70)
        gText = staticText(gConfigPanel,text)
        #gExample = staticText(gConfigPanel,
        #    _(u"Example Mod 1.esp >> Example Mod 1.2.esp"))
        #--Aliases Text
        self.gAliases = wx.TextCtrl(gConfigPanel,wx.ID_ANY,u'',style=wx.TE_MULTILINE)
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
        self.gAliases.SetValue(u'\n'.join([
            u'%s >> %s' % (key.s,value.s) for key,value in sorted(self.aliases.items())]))

    def OnEditAliases(self,event):
        text = self.gAliases.GetValue()
        self.aliases.clear()
        for line in text.split(u'\n'):
            fields = map(string.strip,line.split(u'>>'))
            if len(fields) != 2 or not fields[0] or not fields[1]: continue
            self.aliases[GPath(fields[0])] = GPath(fields[1])
        self.SetAliasText()

class CBash_AliasesPatcher(Patcher, CBash_AliasesPatcher):
    """Basic patcher panel with no options."""
    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        #--Else...
        #--Tip
        self.gTipText = gTipText
        gConfigPanel = self.gConfigPanel = wx.Window(parent,wx.ID_ANY)
        text = fill(self.text,70)
        gText = staticText(gConfigPanel,text)
        #gExample = staticText(gConfigPanel,
        #    _(u"Example Mod 1.esp >> Example Mod 1.2.esp"))
        #--Aliases Text
        self.gAliases = wx.TextCtrl(gConfigPanel,wx.ID_ANY,u'',style=wx.TE_MULTILINE)
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
        self.gAliases.SetValue(u'\n'.join([
            u'%s >> %s' % (key.s,value.s) for key,value in sorted(self.aliases.items())]))

    def OnEditAliases(self,event):
        text = self.gAliases.GetValue()
        self.aliases.clear()
        for line in text.split(u'\n'):
            fields = map(string.strip,line.split(u'>>'))
            if len(fields) != 2 or not fields[0] or not fields[1]: continue
            self.aliases[GPath(fields[0])] = GPath(fields[1])
        self.SetAliasText()

#------------------------------------------------------------------------------
class ListPatcher(Patcher):
    """Patcher panel with option to select source elements."""
    listLabel = _(u'Source Mods/Files')

    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        #--Else...
        self.forceItemCheck = self.__class__.forceItemCheck
        self.selectCommands = self.__class__.selectCommands
        self.gTipText = gTipText
        gConfigPanel = self.gConfigPanel = wx.Window(parent,wx.ID_ANY)
        text = fill(self.text,70)
        gText = staticText(self.gConfigPanel,text)
        if self.forceItemCheck:
            self.gList = wx.ListBox(gConfigPanel,wx.ID_ANY)
        else:
            self.gList =wx.CheckListBox(gConfigPanel,wx.ID_ANY)
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
            self.gAuto = checkBox(gConfigPanel,_(u'Automatic'),onCheck=self.OnAutomatic)
            self.gAuto.SetValue(self.autoIsChecked)
            self.gAdd = button(gConfigPanel,_(u'Add'),onClick=self.OnAdd)
            self.gRemove = button(gConfigPanel,_(u'Remove'),onClick=self.OnRemove)
            self.OnAutomatic()
            gManualSizer = (vSizer(
                (self.gAuto,0,wx.TOP,2),
                (self.gAdd,0,wx.TOP,12),
                (self.gRemove,0,wx.TOP,4),
                ),0,wx.EXPAND|wx.LEFT,4)
        if self.selectCommands:
            self.gSelectAll= button(gConfigPanel,_(u'Select All'),onClick=self.SelectAll)
            self.gDeselectAll = button(gConfigPanel,_(u'Deselect All'),onClick=self.DeselectAll)
            gSelectSizer = (vSizer(
                (self.gSelectAll,0,wx.TOP,12),
                (self.gDeselectAll,0,wx.TOP,4),
                ),0,wx.EXPAND|wx.LEFT,4)
        else: gSelectSizer = None
        #--Layout
        gSizer = vSizer(
            (gText,),
            (hsbSizer((gConfigPanel,wx.ID_ANY,self.__class__.listLabel),
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
        defaultItemCheck = self.__class__.canAutoItemCheck and bosh.inisettings['AutoItemCheck']
        self.gList.Clear()
        isFirstLoad = self._GetIsFirstLoad()
        patcherOn = False
        patcherBold = False
        for index,item in enumerate(items):
            itemLabel = self.getItemLabel(item)
            self.gList.Insert(itemLabel,index)
            if forceItemCheck:
                if self.configChecks.get(item) is None:
                    patcherOn = True
                self.configChecks[item] = True
            else:
                effectiveDefaultItemCheck = defaultItemCheck and not itemLabel.endswith(u'.csv')
                if self.configChecks.get(item) is None:
                    if effectiveDefaultItemCheck:
                        patcherOn = True
                    if not isFirstLoad:
                        # indicate that this is a new item by bolding it and its parent patcher
                        font = self.gConfigPanel.GetFont()
                        font.SetWeight(wx.FONTWEIGHT_BOLD)
                        self.gList.SetItemFont(index, font)
                        patcherBold = True
                self.gList.Check(index,self.configChecks.setdefault(item,effectiveDefaultItemCheck))
        self.configItems = items
        if patcherOn:
            self._EnsurePatcherEnabled()
        if patcherBold:
            self._BoldPatcherLabel()

    def OnListCheck(self,event=None):
        """One of list items was checked. Update all configChecks states."""
        ensureEnabled = False
        for index,item in enumerate(self.items):
            checked = self.gList.IsChecked(index)
            self.configChecks[item] = checked
            if checked:
                ensureEnabled = True
        if event is not None:
            if self.gList.IsChecked(event.GetSelection()):
                self._EnsurePatcherEnabled()
        elif ensureEnabled:
            self._EnsurePatcherEnabled()

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
        wildcard = bush.game.displayName+_(u' Mod Files')+u' (*.esp;*.esm)|*.esp;*.esm'
        #--File dialog
        title = _(u'Get ')+self.__class__.listLabel
        srcPaths = balt.askOpenMulti(self.gConfigPanel,title,srcDir, u'', wildcard)
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
            if label == u'----':
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
        choiceSet ^= {choice}
        if choice != u'Auto':
            choiceSet.discard(u'Auto')
        elif u'Auto' in self.configChoices[item]:
            self.getChoice(item)
        self.gList.SetString(itemIndex,self.getItemLabel(item))

    def SelectAll(self,event=None):
        """'Select All' Button was pressed, update all configChecks states."""
        try:
            for index, item in enumerate(self.items):
                self.gList.Check(index,True)
            self.OnListCheck()
        except AttributeError:
            pass #ListBox instead of CheckListBox
        self.gConfigPanel.GetParent().gPatchers.SetFocusFromKbd()

    def DeselectAll(self,event=None):
        """'Deselect All' Button was pressed, update all configChecks states."""
        try:
            self.gList.SetChecked([])
            self.OnListCheck()
        except AttributeError:
            pass #ListBox instead of CheckListBox
        self.gConfigPanel.GetParent().gPatchers.SetFocusFromKbd()
#------------------------------------------------------------------------------
class TweakPatcher(Patcher):
    """Patcher panel with list of checkable, configurable tweaks."""
    listLabel = _(u"Tweaks")

    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        #--Else...
        self.gTipText = gTipText
        gConfigPanel = self.gConfigPanel = wx.Window(parent,wx.ID_ANY,style=wx.TAB_TRAVERSAL)
        text = fill(self.__class__.text,70)
        gText = staticText(self.gConfigPanel,text)
        self.gTweakList = wx.CheckListBox(gConfigPanel,wx.ID_ANY)
        #--Events
        self.gTweakList.Bind(wx.EVT_CHECKLISTBOX,self.TweakOnListCheck)
        self.gTweakList.Bind(wx.EVT_MOTION,self.TweakOnMouse)
        self.gTweakList.Bind(wx.EVT_LEAVE_WINDOW,self.TweakOnMouse)
        self.gTweakList.Bind(wx.EVT_RIGHT_DOWN,self.TweakOnMouse)
        self.gTweakList.Bind(wx.EVT_RIGHT_UP,self.TweakOnMouse)
        self.mouseItem = -1
        self.mouseState = None
        if self.selectCommands:
            self.gSelectAll= button(gConfigPanel,_(u'Select All'),onClick=self.TweakSelectAll)
            self.gDeselectAll = button(gConfigPanel,_(u'Deselect All'),onClick=self.TweakDeselectAll)
            gSelectSizer = (vSizer(
                (self.gSelectAll,0,wx.TOP,12),
                (self.gDeselectAll,0,wx.TOP,4),
                ),0,wx.EXPAND|wx.LEFT,4)
        else: gSelectSizer = None
        #--Init GUI
        self.SetTweaks()
        #--Layout
        gSizer = vSizer(
            (gText,),
            (hsbSizer((gConfigPanel,wx.ID_ANY,self.__class__.listLabel),
                ((4,0),0,wx.EXPAND),
                (self.gTweakList,1,wx.EXPAND|wx.TOP,2),
                gSelectSizer,
                ),1,wx.EXPAND|wx.TOP,4),
            )
        gConfigPanel.SetSizer(gSizer)
        gConfigSizer.Add(gConfigPanel,1,wx.EXPAND)
        return gConfigPanel

    def SetTweaks(self):
        """Set item to specified set of items."""
        self.gTweakList.Clear()
        isFirstLoad = self._GetIsFirstLoad()
        patcherBold = False
        for index,tweak in enumerate(self.tweaks):
            label = tweak.getListLabel()
            if tweak.choiceLabels and tweak.choiceLabels[tweak.chosen].startswith(u'Custom'):
                if isinstance(tweak.choiceValues[tweak.chosen][0],basestring):
                    label += u' %s' % tweak.choiceValues[tweak.chosen][0]
                else:
                    label += u' %4.2f ' % tweak.choiceValues[tweak.chosen][0]
            self.gTweakList.Insert(label,index)
            self.gTweakList.Check(index,tweak.isEnabled)
            if not isFirstLoad and tweak.isNew():
                # indicate that this is a new item by bolding it and its parent patcher
                font = self.gConfigPanel.GetFont()
                font.SetWeight(wx.FONTWEIGHT_BOLD)
                self.gTweakList.SetItemFont(index, font)
                patcherBold = True
        if patcherBold:
            self._BoldPatcherLabel()

    def TweakOnListCheck(self,event=None):
        """One of list items was checked. Update all check states."""
        ensureEnabled = False
        for index, tweak in enumerate(self.tweaks):
            checked = self.gTweakList.IsChecked(index)
            tweak.isEnabled = checked
            if checked:
                ensureEnabled = True
        if event is not None:
            if self.gTweakList.IsChecked(event.GetSelection()):
                self._EnsurePatcherEnabled()
        elif ensureEnabled:
            self._EnsurePatcherEnabled()

    def TweakOnMouse(self,event):
        """Check mouse motion to detect right click event."""
        if event.RightDown():
            self.mouseState = (event.m_x,event.m_y)
            event.Skip()
        elif event.RightUp() and self.mouseState:
            self.ShowChoiceMenu(event)
        elif event.Leaving():
            self.gTipText.SetLabel(u'')
            self.mouseState = False
            event.Skip()
        elif event.Dragging():
            if self.mouseState:
                oldx,oldy = self.mouseState
                if max(abs(event.m_x-oldx),abs(event.m_y-oldy)) > 4:
                    self.mouseState = None
        elif event.Moving():
            mouseItem = event.m_y/self.gTweakList.GetItemHeight() + self.gTweakList.GetScrollPos(wx.VERTICAL)
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
            self.gTipText.SetLabel(u'')

    def ShowChoiceMenu(self,event):
        """Displays a popup choice menu if applicable."""
        #--Tweak Index
        tweakIndex = event.m_y/self.gTweakList.GetItemHeight() + self.gTweakList.GetScrollPos(wx.VERTICAL)
        self.rightClickTweakIndex = tweakIndex
        #--Tweaks
        tweaks = self.tweaks
        if tweakIndex >= len(tweaks): return
        choiceLabels = tweaks[tweakIndex].choiceLabels
        if len(choiceLabels) <= 1: return
        chosen = tweaks[tweakIndex].chosen
        self.gTweakList.SetSelection(tweakIndex)
        #--Build Menu
        menu = wx.Menu()
        for index,label in enumerate(choiceLabels):
            if label == u'----':
                menu.AppendSeparator()
            elif label.startswith(_(u'Custom')):
                if isinstance(tweaks[tweakIndex].choiceValues[index][0],basestring):
                    menulabel = label + u' %s' % tweaks[tweakIndex].choiceValues[index][0]
                else:
                    menulabel = label + u' %4.2f ' % tweaks[tweakIndex].choiceValues[index][0]
                menuItem = wx.MenuItem(menu,index,menulabel,kind=wx.ITEM_CHECK)
                menu.AppendItem(menuItem)
                if index == chosen: menuItem.Check()
                wx.EVT_MENU(self.gTweakList,index,self.OnTweakCustomChoice)
            else:
                menuItem = wx.MenuItem(menu,index,label,kind=wx.ITEM_CHECK)
                menu.AppendItem(menuItem)
                if index == chosen: menuItem.Check()
                wx.EVT_MENU(self.gTweakList,index,self.OnTweakChoice)
        #--Show/Destroy Menu
        self.gTweakList.PopupMenu(menu)
        menu.Destroy()

    def OnTweakChoice(self,event):
        """Handle choice menu selection."""
        tweakIndex = self.rightClickTweakIndex
        self.tweaks[tweakIndex].chosen = event.GetId()
        self.gTweakList.SetString(tweakIndex,self.tweaks[tweakIndex].getListLabel())

    def OnTweakCustomChoice(self,event):
        """Handle choice menu selection."""
        tweakIndex = self.rightClickTweakIndex
        index = event.GetId()
        tweak = self.tweaks[tweakIndex]
        value = []
        for i, v in enumerate(tweak.choiceValues[index]):
            if isinstance(v,float):
                label = (_(u'Enter the desired custom tweak value.')
                         + u'\n' +
                         _(u'Due to an inability to get decimal numbers from the wxPython prompt please enter an extra zero after your choice if it is not meant to be a decimal.')
                         + u'\n' +
                         _(u'If you are trying to enter a decimal multiply it by 10, for example for 0.3 enter 3 instead.')
                         + u'\n' + tweak.key[i])
                new = balt.askNumber(self.gConfigPanel,label,prompt=_(u'Value'),
                    title=tweak.label+_(u' ~ Custom Tweak Value'),value=self.tweaks[tweakIndex].choiceValues[index][i],min=-10000,max=10000)
                if new is None: #user hit cancel
                    return
                value.append(float(new)/10)
            elif isinstance(v,int):
                label = _(u'Enter the desired custom tweak value.')+u'\n'+tweak.key[i]
                new = balt.askNumber(self.gConfigPanel,label,prompt=_(u'Value'),
                    title=tweak.label+_(u' ~ Custom Tweak Value'),value=self.tweaks[tweakIndex].choiceValues[index][i],min=-10000,max=10000)
                if new is None: #user hit cancel
                    return
                value.append(new)
            elif isinstance(v,basestring):
                label = _(u'Enter the desired custom tweak text.')+u'\n'+tweak.key[i]
                new = balt.askText(self.gConfigPanel,label,
                    title=tweak.label+_(u' ~ Custom Tweak Text'),default=self.tweaks[tweakIndex].choiceValues[index][i])
                if new is None: #user hit cancel
                    return
                value.append(new)
        if not value: value = tweak.choiceValues[index]
        tweak.choiceValues[index] = tuple(value)
        tweak.chosen = index
        if isinstance(tweak.choiceValues[index][0],basestring):
            menulabel = tweak.getListLabel() + u' %s' % tweak.choiceValues[index][0]
        else:
            menulabel = tweak.getListLabel() + u' %4.2f ' % tweak.choiceValues[index][0]
        self.gTweakList.SetString(tweakIndex, menulabel)

    def TweakSelectAll(self,event=None):
        """'Select All' Button was pressed, update all configChecks states."""
        try:
            for index, item in enumerate(self.tweaks):
                self.gTweakList.Check(index,True)
            self.TweakOnListCheck()
        except AttributeError:
            pass #ListBox instead of CheckListBox
        self.gConfigPanel.GetParent().gPatchers.SetFocusFromKbd()

    def TweakDeselectAll(self,event=None):
        """'Deselect All' Button was pressed, update all configChecks states."""
        try:
            self.gTweakList.SetChecked([])
            self.TweakOnListCheck()
        except AttributeError:
            pass #ListBox instead of CheckListBox
        self.gConfigPanel.GetParent().gPatchers.SetFocusFromKbd()

#------------------------------------------------------------------------------
class DoublePatcher(TweakPatcher,ListPatcher):
    """Patcher panel with option to select source elements."""
    listLabel = _(u'Source Mods/Files')

    def GetConfigPanel(self,parent,gConfigSizer,gTipText):
        """Show config."""
        if self.gConfigPanel: return self.gConfigPanel
        #--Else...
        self.gTipText = gTipText
        gConfigPanel = self.gConfigPanel = wx.Window(parent,wx.ID_ANY)
        text = fill(self.text,70)
        gText = staticText(self.gConfigPanel,text)
        #--Import List
        self.gList = wx.CheckListBox(gConfigPanel,wx.ID_ANY)
        self.gList.Bind(wx.EVT_MOTION,self.OnMouse)
        self.gList.Bind(wx.EVT_RIGHT_DOWN,self.OnMouse)
        self.gList.Bind(wx.EVT_RIGHT_UP,self.OnMouse)
        #--Tweak List
        self.gTweakList = wx.CheckListBox(gConfigPanel,wx.ID_ANY)
        self.gTweakList.Bind(wx.EVT_CHECKLISTBOX,self.TweakOnListCheck)
        self.gTweakList.Bind(wx.EVT_MOTION,self.TweakOnMouse)
        self.gTweakList.Bind(wx.EVT_LEAVE_WINDOW,self.TweakOnMouse)
        self.gTweakList.Bind(wx.EVT_RIGHT_DOWN,self.TweakOnMouse)
        self.gTweakList.Bind(wx.EVT_RIGHT_UP,self.TweakOnMouse)
        self.mouseItem = -1
        self.mouseState = None
        #--Buttons
        self.gSelectAll = button(gConfigPanel,_(u'Select All'),onClick=self.SelectAll)
        self.gDeselectAll = button(gConfigPanel,_(u'Deselect All'),onClick=self.DeselectAll)
        gSelectSizer = (vSizer(
            (self.gSelectAll,0,wx.TOP,12),
            (self.gDeselectAll,0,wx.TOP,4),
            ),0,wx.EXPAND|wx.LEFT,4)
        self.gTweakSelectAll = button(gConfigPanel,_(u'Select All'),onClick=self.TweakSelectAll)
        self.gTweakDeselectAll = button(gConfigPanel,_(u'Deselect All'),onClick=self.TweakDeselectAll)
        gTweakSelectSizer = (vSizer(
            (self.gTweakSelectAll,0,wx.TOP,12),
            (self.gTweakDeselectAll,0,wx.TOP,4),
            ),0,wx.EXPAND|wx.LEFT,4)
        #--Layout
        gSizer = vSizer(
            (gText,),
            (hsbSizer((gConfigPanel,wx.ID_ANY,self.__class__.listLabel),
                ((4,0),0,wx.EXPAND),
                (self.gList,1,wx.EXPAND|wx.TOP,2),
                gSelectSizer,),1,wx.EXPAND|wx.TOP,4),
            (hsbSizer((gConfigPanel,wx.ID_ANY,self.__class__.subLabel),
                ((4,0),0,wx.EXPAND),
                (self.gTweakList,1,wx.EXPAND|wx.TOP,2),
                gTweakSelectSizer,),1,wx.EXPAND|wx.TOP,4),
            )
        gConfigPanel.SetSizer(gSizer)
        gConfigSizer.Add(gConfigPanel,1,wx.EXPAND)
        #--Initialize
        self.SetItems(self.getAutoItems())
        self.SetTweaks()
        return gConfigPanel

# TODO: dynamically create those (game independent ?) UI patchers based on
# dictionaries in bash.patcher.__init__.py (see the game specific creation
# below)
#------------------------------------------------------------------------------
# Patchers 10 -----------------------------------------------------------------
class PatchMerger(PatchMerger,ListPatcher):
    listLabel = _(u'Mergeable Mods')
class CBash_PatchMerger(CBash_PatchMerger,ListPatcher):
    listLabel = _(u'Mergeable Mods')
# Patchers 20 -----------------------------------------------------------------
class GraphicsPatcher(GraphicsPatcher,ListPatcher): pass
class CBash_GraphicsPatcher(CBash_GraphicsPatcher,ListPatcher): pass

class KFFZPatcher(KFFZPatcher,ListPatcher): pass
class CBash_KFFZPatcher(CBash_KFFZPatcher,ListPatcher): pass

class NPCAIPackagePatcher(NPCAIPackagePatcher,ListPatcher): pass
class CBash_NPCAIPackagePatcher(CBash_NPCAIPackagePatcher,ListPatcher): pass

class ActorImporter(ActorImporter,ListPatcher): pass
class CBash_ActorImporter(CBash_ActorImporter,ListPatcher): pass

class DeathItemPatcher(DeathItemPatcher,ListPatcher): pass
class CBash_DeathItemPatcher(CBash_DeathItemPatcher,ListPatcher): pass

class CellImporter(CellImporter,ListPatcher): pass
class CBash_CellImporter(CBash_CellImporter,ListPatcher): pass

class ImportFactions(ImportFactions,ListPatcher): pass
class CBash_ImportFactions(CBash_ImportFactions,ListPatcher): pass

class ImportRelations(ImportRelations,ListPatcher): pass
class CBash_ImportRelations(CBash_ImportRelations,ListPatcher): pass

class ImportInventory(ImportInventory,ListPatcher): pass
class CBash_ImportInventory(CBash_ImportInventory,ListPatcher): pass

class ImportActorsSpells(ImportActorsSpells,ListPatcher): pass
class CBash_ImportActorsSpells(CBash_ImportActorsSpells,ListPatcher): pass

class NamesPatcher(NamesPatcher,ListPatcher): pass
class CBash_NamesPatcher(CBash_NamesPatcher,ListPatcher): pass

class NpcFacePatcher(NpcFacePatcher,ListPatcher): pass
class CBash_NpcFacePatcher(CBash_NpcFacePatcher,ListPatcher): pass

class RacePatcher(RacePatcher,DoublePatcher):
    listLabel = _(u'Race Mods')
class CBash_RacePatcher(CBash_RacePatcher,DoublePatcher):
    listLabel = _(u'Race Mods')

class RoadImporter(RoadImporter,ListPatcher): pass
class CBash_RoadImporter(CBash_RoadImporter,ListPatcher): pass

class SoundPatcher(SoundPatcher,ListPatcher): pass
class CBash_SoundPatcher(CBash_SoundPatcher,ListPatcher): pass

class StatsPatcher(StatsPatcher,ListPatcher): pass
class CBash_StatsPatcher(CBash_StatsPatcher,ListPatcher): pass

class ImportScripts(ImportScripts,ListPatcher):pass
class CBash_ImportScripts(CBash_ImportScripts,ListPatcher):pass

class SpellsPatcher(SpellsPatcher,ListPatcher):pass
class CBash_SpellsPatcher(CBash_SpellsPatcher,ListPatcher):pass

# Patchers 30 -----------------------------------------------------------------
class AssortedTweaker(AssortedTweaker,TweakPatcher): pass
class CBash_AssortedTweaker(CBash_AssortedTweaker,TweakPatcher): pass

class ClothesTweaker(ClothesTweaker,TweakPatcher): pass
class CBash_ClothesTweaker(CBash_ClothesTweaker,TweakPatcher): pass

class GmstTweaker(GmstTweaker,TweakPatcher): pass
class CBash_GmstTweaker(CBash_GmstTweaker,TweakPatcher): pass

class NamesTweaker(NamesTweaker,TweakPatcher): pass
class CBash_NamesTweaker(CBash_NamesTweaker,TweakPatcher): pass

class TweakActors(TweakActors,TweakPatcher): pass
class CBash_TweakActors(CBash_TweakActors,TweakPatcher): pass

# Patchers 40 -----------------------------------------------------------------
class UpdateReferences(UpdateReferences,ListPatcher): pass
class CBash_UpdateReferences(CBash_UpdateReferences,ListPatcher): pass

class ListsMerger(ListsMerger_,ListPatcher):
    listLabel = _(u'Override Delev/Relev Tags')
class CBash_ListsMerger(CBash_ListsMerger_,ListPatcher):
    listLabel = _(u'Override Delev/Relev Tags')

class ContentsChecker(ContentsChecker,Patcher): pass
class CBash_ContentsChecker(CBash_ContentsChecker,Patcher): pass
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# TODO: what is this about ? Can we bin it ?? Complicates the dynamic
# patcher types creation...
otherPatcherDict = {
    AliasesPatcher().__class__.__name__ : CBash_AliasesPatcher(),
    AssortedTweaker().__class__.__name__ : CBash_AssortedTweaker(),
    PatchMerger().__class__.__name__ : CBash_PatchMerger(),
    KFFZPatcher().__class__.__name__ : CBash_KFFZPatcher(),
    ActorImporter().__class__.__name__ : CBash_ActorImporter(),
    DeathItemPatcher().__class__.__name__ : CBash_DeathItemPatcher(),
    NPCAIPackagePatcher().__class__.__name__ : CBash_NPCAIPackagePatcher(),
    UpdateReferences().__class__.__name__ : CBash_UpdateReferences(),
    CellImporter().__class__.__name__ : CBash_CellImporter(),
    ClothesTweaker().__class__.__name__ : CBash_ClothesTweaker(),
    GmstTweaker().__class__.__name__ : CBash_GmstTweaker(),
    GraphicsPatcher().__class__.__name__ : CBash_GraphicsPatcher(),
    ImportFactions().__class__.__name__ : CBash_ImportFactions(),
    ImportInventory().__class__.__name__ : CBash_ImportInventory(),
    SpellsPatcher().__class__.__name__ : CBash_SpellsPatcher(),
    TweakActors().__class__.__name__ : CBash_TweakActors(),
    ImportRelations().__class__.__name__ : CBash_ImportRelations(),
    ImportScripts().__class__.__name__ : CBash_ImportScripts(),
    ImportActorsSpells().__class__.__name__ : CBash_ImportActorsSpells(),
    ListsMerger().__class__.__name__ : CBash_ListsMerger(),
    NamesPatcher().__class__.__name__ : CBash_NamesPatcher(),
    NamesTweaker().__class__.__name__ : CBash_NamesTweaker(),
    NpcFacePatcher().__class__.__name__ : CBash_NpcFacePatcher(),
    RacePatcher().__class__.__name__ : CBash_RacePatcher(),
    RoadImporter().__class__.__name__ : CBash_RoadImporter(),
    SoundPatcher().__class__.__name__ : CBash_SoundPatcher(),
    StatsPatcher().__class__.__name__ : CBash_StatsPatcher(),
    ContentsChecker().__class__.__name__ : CBash_ContentsChecker(),
    CBash_AliasesPatcher().__class__.__name__ : AliasesPatcher(),
    CBash_AssortedTweaker().__class__.__name__ : AssortedTweaker(),
    CBash_PatchMerger().__class__.__name__ : PatchMerger(),
    CBash_KFFZPatcher().__class__.__name__ : KFFZPatcher(),
    CBash_ActorImporter().__class__.__name__ : ActorImporter(),
    CBash_DeathItemPatcher().__class__.__name__ : DeathItemPatcher(),
    CBash_NPCAIPackagePatcher().__class__.__name__ : NPCAIPackagePatcher(),
    CBash_UpdateReferences().__class__.__name__ : UpdateReferences(),
    CBash_CellImporter().__class__.__name__ : CellImporter(),
    CBash_ClothesTweaker().__class__.__name__ : ClothesTweaker(),
    CBash_GmstTweaker().__class__.__name__ : GmstTweaker(),
    CBash_GraphicsPatcher().__class__.__name__ : GraphicsPatcher(),
    CBash_ImportFactions().__class__.__name__ : ImportFactions(),
    CBash_ImportInventory().__class__.__name__ : ImportInventory(),
    CBash_SpellsPatcher().__class__.__name__ : SpellsPatcher(),
    CBash_TweakActors().__class__.__name__ : TweakActors(),
    CBash_ImportRelations().__class__.__name__ : ImportRelations(),
    CBash_ImportScripts().__class__.__name__ : ImportScripts(),
    CBash_ImportActorsSpells().__class__.__name__ : ImportActorsSpells(),
    CBash_ListsMerger().__class__.__name__ : ListsMerger(),
    CBash_NamesPatcher().__class__.__name__ : NamesPatcher(),
    CBash_NamesTweaker().__class__.__name__ : NamesTweaker(),
    CBash_NpcFacePatcher().__class__.__name__ : NpcFacePatcher(),
    CBash_RacePatcher().__class__.__name__ : RacePatcher(),
    CBash_RoadImporter().__class__.__name__ : RoadImporter(),
    CBash_SoundPatcher().__class__.__name__ : SoundPatcher(),
    CBash_StatsPatcher().__class__.__name__ : StatsPatcher(),
    CBash_ContentsChecker().__class__.__name__ : ContentsChecker(),
    }

# Dynamically create game specific UI patcher classes and add them to basher's
# scope
from importlib import import_module
gamePatcher = import_module('.patcher', # TODO: move in bush.py !
                       package=bush.game.__name__)
for name, typeInfo in gamePatcher.gameSpecificPatchers.items():
    globals()[name] = type(name, (typeInfo[0], Patcher), {})
    if typeInfo[1]:
        otherPatcherDict[name] = typeInfo[1]()
for name, typeInfo in gamePatcher.gameSpecificListPatchers.items():
    globals()[name] = type(name, (typeInfo[0], ListPatcher), {})
    if typeInfo[1]:
        otherPatcherDict[name] = typeInfo[1]()

# Init Patchers
def initPatchers():
    PatchDialog.patchers.extend((
        globals()[x]() for x in bush.game.patchers
        ))
    PatchDialog.CBash_patchers.extend((
        globals()[x]() for x in bush.game.CBash_patchers
        ))

# Files Links -----------------------------------------------------------------
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

class BoolLink(Link):
    """Simple link that just toggles a setting."""
    def __init__(self, text, key, help='', opposite=False):
        Link.__init__(self)
        self.text = text
        self.help = help
        self.key = key
        self.opposite = opposite

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,self.text,self.help,kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        menuItem.Check(settings[self.key] ^ self.opposite)

    def Execute(self,event):
        settings[self.key] ^= True

#------------------------------------------------------------------------------
class Files_Open(Link):
    """Opens data directory in explorer."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Open...'), _(u"Open '%s'") % window.data.dir.tail)
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
        menuItem = wx.MenuItem(menu,self.id,self.prefix+self.sortName,_(u'Sort by %s') % self.sortName,kind=wx.ITEM_RADIO)
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
        menuItem = wx.MenuItem(menu,self.id,_(u"Unhide..."), _(u"Unhides hidden %ss.") % self.type)
        menu.AppendItem(menuItem)

    def Execute(self,event):
        srcDir = bosh.dirs['modsBash'].join(u'Hidden')
        if self.type == 'mod':
            wildcard = bush.game.displayName+u' '+_(u'Mod Files')+u' (*.esp;*.esm)|*.esp;*.esm'
            destDir = self.window.data.dir
        elif self.type == 'save':
            wildcard = bush.game.displayName+u' '+_(u'Save files')+u' (*.ess)|*.ess'
            srcDir = self.window.data.bashDir.join(u'Hidden')
            destDir = self.window.data.dir
        elif self.type == 'installer':
            window = self.gTank
            wildcard = bush.game.displayName+u' '+_(u'Mod Archives')+u' (*.7z;*.zip;*.rar)|*.7z;*.zip;*.rar'
            destDir = bosh.dirs['installers']
            srcPaths = balt.askOpenMulti(window,_(u'Unhide files:'),srcDir, u'.Folder Selection.', wildcard)
        else:
            wildcard = u'*.*'
        isSave = (destDir == bosh.saveInfos.dir)
        #--File dialog
        srcDir.makedirs()
        if not self.type == 'installer':
            window = self.window
            srcPaths = balt.askOpenMulti(window,_(u'Unhide files:'),srcDir, u'', wildcard)
        if not srcPaths: return
        #--Iterate over Paths
        srcFiles = []
        destFiles = []
        coSavesMoves = {}
        for srcPath in srcPaths:
            #--Copy from dest directory?
            (newSrcDir,srcFileName) = srcPath.headTail
            if newSrcDir == destDir:
                balt.showError(window,_(u"You can't unhide files from this directory."))
                return
            #--Folder selection?
            if srcFileName.csbody == u'.folder selection':
                if newSrcDir == srcDir:
                    #--Folder selection on the 'Hidden' folder
                    return
                (newSrcDir,srcFileName) = newSrcDir.headTail
                srcPath = srcPath.head
            #--File already unhidden?
            destPath = destDir.join(srcFileName)
            if destPath.exists():
                balt.showWarning(window,_(u"File skipped: %s. File is already present.")
                    % (srcFileName.s,))
            #--Move it?
            else:
                srcFiles.append(srcPath)
                destFiles.append(destPath)
                if isSave:
                    coSavesMoves[destPath] = bosh.CoSaves(srcPath)
        #--Now move everything at once
        if not srcFiles:
            return
        try:
            balt.shellMove(srcFiles,destFiles,window,False,False,False)
            for dest in coSavesMoves:
                coSavesMoves[dest].move(dest)
        except (CancelError,SkipError):
            pass
        bashFrame.RefreshData()

# File Links ------------------------------------------------------------------
#------------------------------------------------------------------------------
class File_Delete(Link):
    """Delete the file and all backups."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Delete'),
                               help=_(u"Delete %(filename)s.") % ({'filename':data[0]}))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        message = [u'',_(u'Uncheck files to skip deleting them if desired.')]
        message.extend(sorted(self.data))
        dialog = ListBoxes(self.window,_(u'Delete Files'),
                     _(u'Delete these files? This operation cannot be undone.'),
                     [message])
        if dialog.ShowModal() != wx.ID_CANCEL:
            id = dialog.ids[message[0]]
            checks = dialog.FindWindowById(id)
            if checks:
                for i,mod in enumerate(self.data):
                    if checks.IsChecked(i):
                        try:
                            self.window.data.delete(mod)
                        except bolt.BoltError as e:
                            balt.showError(self.window, _(u'%s') % e)
            self.window.RefreshUI()
        dialog.Destroy()

#------------------------------------------------------------------------------
class File_Duplicate(Link):
    """Create a duplicate of the file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.title = (_(u'Duplicate'),_(u'Duplicate...'))[len(data) == 1]
        menuItem = wx.MenuItem(menu,self.id,self.title, _(u"Make a copy of '%s'") % (data[0]))
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
                    message = (_(u"This mod has an associated archive (%s.bsa) and an associated voice directory (Sound\\Voices\\%s), which will not be attached to the duplicate mod.")
                               + u'\n\n' +
                               _(u'Note that the BSA archive may also contain a voice directory (Sound\\Voices\\%s), which would remain detached even if a duplicate archive were also created.')
                               ) % (modName.sroot,modName.s,modName.s)
                elif hasBsa:
                    message = (_(u'This mod has an associated archive (%s.bsa), which will not be attached to the duplicate mod.')
                               + u'\n\n' +
                               _(u'Note that this BSA archive may contain a voice directory (Sound\\Voices\\%s), which would remain detached even if a duplicate archive were also created.')
                               ) % (modName.sroot,modName.s)
                else: #hasVoices
                    message = _(u'This mod has an associated voice directory (Sound\\Voice\\%s), which will not be attached to the duplicate mod.') % modName.s
                if not balt.askWarning(self.window,message,_(u'Duplicate ')+fileName.s):
                    continue
            #--Continue copy
            (root,ext) = fileName.rootExt
            if ext.lower() == u'.bak': ext = u'.ess'
            (destDir,wildcard) = (fileInfo.dir, u'*'+ext)
            destName = GPath(root+u' Copy'+ext)
            destPath = destDir.join(destName)
            count = 0
            while destPath.exists() and count < 1000:
                count += 1
                destName = GPath(root + u' Copy %d'  % count + ext)
                destPath = destDir.join(destName)
            destName = destName.s
            destDir.makedirs()
            if len(data) == 1:
                destPath = balt.askSave(self.window,_(u'Duplicate as:'), destDir,destName,wildcard)
                if not destPath: return
                destDir,destName = destPath.headTail
            if (destDir == fileInfo.dir) and (destName == fileName):
                balt.showError(self.window,_(u"Files cannot be duplicated to themselves!"))
                continue
            if fileInfo.isMod():
                newTime = bosh.modInfos.getFreeTime(fileInfo.getPath().mtime)
            else:
                newTime = '+1'
            fileInfos.copy(fileName,destDir,destName,mtime=newTime)
            if destDir == fileInfo.dir:
                fileInfos.table.copyRow(fileName,destName)
                if fileInfos.table.getItem(fileName,'mtime'):
                    fileInfos.table.setItem(destName,'mtime',newTime)
                if fileInfo.isMod():
                    fileInfos.autoSort()
            self.window.RefreshUI()

#------------------------------------------------------------------------------
class File_Hide(Link):
    """Hide the file. (Move it to Bash/Hidden directory.)"""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Hide'),
                               help=_(u"Move %(filename)s to the Bash/Hidden directory.") % ({'filename':data[0]}))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        if not bosh.inisettings['SkipHideConfirmation']:
            message = _(u'Hide these files? Note that hidden files are simply moved to the Bash\\Hidden subdirectory.')
            if not balt.askYes(self.window,message,_(u'Hide Files')): return
        #--Do it
        destRoot = self.window.data.bashDir.join(u'Hidden')
        fileInfos = self.window.data
        fileGroups = fileInfos.table.getColumn('group')
        for fileName in self.data:
            destDir = destRoot
            #--Use author subdirectory instead?
            author = getattr(fileInfos[fileName].header,'author',u'NOAUTHOR') #--Hack for save files.
            authorDir = destRoot.join(author)
            if author and authorDir.isdir():
                destDir = authorDir
            #--Use group subdirectory instead?
            elif fileName in fileGroups:
                groupDir = destRoot.join(fileGroups[fileName])
                if groupDir.isdir():
                    destDir = groupDir
            if not self.window.data.moveIsSafe(fileName,destDir):
                message = (_(u'A file named %s already exists in the hidden files directory. Overwrite it?')
                    % fileName.s)
                if not balt.askYes(self.window,message,_(u'Hide Files')): continue
            #--Do it
            self.window.data.move(fileName,destDir,False)
        #--Refresh stuff
        bashFrame.RefreshData()

#------------------------------------------------------------------------------
class File_ListMasters(Link):
    """Copies list of masters to clipboard."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u"List Masters..."),
                help=_(u"Copies list of %(filename)s's masters to the clipboard.") % ({'filename':data[0]}))
        menu.AppendItem(menuItem)
        if len(data) != 1: menuItem.Enable(False)

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        text = bosh.modInfos.getModList(fileInfo=fileInfo)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        balt.showLog(self.window,text,fileName.s,asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class File_Redate(Link):
    """Move the selected files to start at a specified date."""
    def AppendToMenu(self,menu,window,data):
        if bosh.lo.LoadOrderMethod == bosh.liblo.LIBLO_METHOD_TEXTFILE:
            return
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Redate...'),
                help=_(u"Move the selected files to start at a specified date."))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        #--Get current start time.
        modInfos = self.window.data
        fileNames = [mod for mod in self.data if mod not in modInfos.autoSorted]
        if not fileNames: return
        #--Ask user for revised time.
        newTimeStr = balt.askText(self.window,_(u'Redate selected mods starting at...'),
            _(u'Redate Mods'),formatDate(int(time.time())))
        if not newTimeStr: return
        try:
            newTimeTup = bosh.unformatDate(newTimeStr,u'%c')
            newTime = int(time.mktime(newTimeTup))
        except ValueError:
            balt.showError(self.window,_(u'Unrecognized date: ')+newTimeStr)
            return
        except OverflowError:
            balt.showError(self,_(u'Bash cannot handle dates greater than January 19, 2038.)'))
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
        menuItem = wx.MenuItem(menu,self.id,_(u'Sort'),
                help=_(u"sort the selected files."))
        menu.AppendItem(menuItem)
        if len(data) < 2: menuItem.Enable(False)

    def Execute(self,event):
        message = (_(u'Reorder selected mods in alphabetical order?  The first file will be given the date/time of the current earliest file in the group, with consecutive files following at 1 minute increments.')
                   + u'\n\n' +
                   _(u'Note that this operation cannot be undone.  Note also that some mods need to be in a specific order to work correctly, and this sort operation may break that order.')
                   )
        if not balt.askContinue(self.window,message,'bash.sortMods.continue',_(u'Sort Mods')):
            return
        #--Get first time from first selected file.
        modInfos = self.window.data
        fileNames = [mod for mod in self.data if mod not in modInfos.autoSorted]
        if not fileNames: return
        dotTimes = [modInfos[fileName].mtime for fileName in fileNames if fileName.s[0] in u'.=+']
        if dotTimes:
            newTime = min(dotTimes)
        else:
            newTime = min(modInfos[fileName].mtime for fileName in self.data)
        #--Do it
        fileNames.sort(key=lambda a: a.cext)
        fileNames.sort(key=lambda a: a.s[0] not in u'.=')
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
        self.title = (_(u'Snapshot'),_(u'Snapshot...'))[len(data) == 1]
        menuItem = wx.MenuItem(menu,self.id,self.title,
            help=_(u"Creates a snapshot copy of the current mod in a subdirectory (Bash\Snapshots)."))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        data = self.data
        for item in data:
            fileName = GPath(item)
            fileInfo = self.window.data[fileName]
            (destDir,destName,wildcard) = fileInfo.getNextSnapshot()
            destDir.makedirs()
            if len(data) == 1:
                destPath = balt.askSave(self.window,_(u'Save snapshot as:'),
                    destDir,destName,wildcard)
                if not destPath: return
                (destDir,destName) = destPath.headTail
            #--Extract version number
            fileRoot = fileName.root
            destRoot = destName.root
            fileVersion = bolt.getMatch(re.search(ur'[ _]+v?([\.\d]+)$',fileRoot.s,re.U),1)
            snapVersion = bolt.getMatch(re.search(ur'-[\d\.]+$',destRoot.s,re.U))
            fileHedr = fileInfo.header
            if fileInfo.isMod() and (fileVersion or snapVersion) and bosh.reVersion.search(fileHedr.description):
                if fileVersion and snapVersion:
                    newVersion = fileVersion+snapVersion
                elif snapVersion:
                    newVersion = snapVersion[1:]
                else:
                    newVersion = fileVersion
                newDescription = bosh.reVersion.sub(u'\\1 '+newVersion, fileHedr.description,1,flags=re.U)
                fileInfo.writeDescription(newDescription)
                self.window.details.SetFile(fileName)
            #--Copy file
            self.window.data.copy(fileName,destDir,destName)

#------------------------------------------------------------------------------
class File_RevertToSnapshot(Link):
    """Revert to Snapshot."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Revert to Snapshot...'),
            help=_(u"Revert to a previously created snapshot from the Bash/Snapshots dir."))
        menuItem.Enable(len(self.data) == 1)
        menu.AppendItem(menuItem)

    def Execute(self,event):
        """Handle menu item selection."""
        fileInfo = self.window.data[self.data[0]]
        fileName = fileInfo.name
        #--Snapshot finder
        destDir = self.window.data.dir
        srcDir = self.window.data.bashDir.join(u'Snapshots')
        wildcard = fileInfo.getNextSnapshot()[2]
        #--File dialog
        srcDir.makedirs()
        snapPath = balt.askOpen(self.window,_(u'Revert %s to snapshot:') % fileName.s,
            srcDir, u'', wildcard,mustExist=True)
        if not snapPath: return
        snapName = snapPath.tail
        #--Warning box
        message = (_(u"Revert %s to snapshot %s dated %s?")
            % (fileInfo.name.s, snapName.s, formatDate(snapPath.mtime)))
        if not balt.askYes(self.window,message,_(u'Revert to Snapshot')): return
        with balt.BusyCursor():
            destPath = fileInfo.getPath()
            snapPath.copyTo(destPath)
            fileInfo.setmtime()
            try:
                self.window.data.refreshFile(fileName)
            except bosh.FileError:
                balt.showError(self,_(u'Snapshot file is corrupt!'))
                self.window.details.SetFile(None)
            self.window.RefreshUI(fileName)

#------------------------------------------------------------------------------
class File_Backup(Link):
    """Backup file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Backup'),
            help=_(u"Create a backup of the slected file(s)."))
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
        menuItem = wx.MenuItem(menu,ID_REVERT_BACKUP,_(u'Revert to Backup'))
        self.backup = self.fileInfo.bashDir.join(u'Backups',self.fileInfo.name)
        menuItem.Enable(singleSelect and self.backup.exists())
        menu.AppendItem(menuItem)
        #--First Backup item
        wx.EVT_MENU(window,ID_REVERT_FIRST,self.Execute)
        menuItem = wx.MenuItem(menu,ID_REVERT_FIRST,_(u'Revert to First Backup'))
        self.firstBackup = self.backup +u'f'
        menuItem.Enable(singleSelect and self.firstBackup.exists())
        menu.AppendItem(menuItem)

    def Execute(self,event):
        fileInfo = self.fileInfo
        fileName = fileInfo.name
        #--Backup/FirstBackup?
        if event.GetId() ==  ID_REVERT_BACKUP:
            backup = self.backup
        else:
            backup = self.firstBackup
        #--Warning box
        message = _(u"Revert %s to backup dated %s?") % (fileName.s,
            formatDate(backup.mtime))
        if balt.askYes(self.window,message,_(u'Revert to Backup')):
            with balt.BusyCursor():
                dest = fileInfo.dir.join(fileName)
                backup.copyTo(dest)
                fileInfo.setmtime()
                if fileInfo.isEss(): #--Handle CoSave (.pluggy and .obse) files.
                    bosh.CoSaves(backup).copy(dest)
                try:
                    self.window.data.refreshFile(fileName)
                except bosh.FileError:
                    balt.showError(self,_(u'Old file is corrupt!'))
                self.window.RefreshUI(fileName)

#------------------------------------------------------------------------------
class File_Open(Link):
    """Open specified file(s)."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        if len(data) == 1:
            help = _(u"Open '%s' with the system's default program.") % data[0]
        else:
            help = _(u'Open the selected files.')
        menuItem = wx.MenuItem(menu,self.id,_(u'Open...'),help)
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)>0)

    def Execute(self,event):
        """Handle selection."""
        dir = self.window.data.dir
        for file in self.data:
            dir.join(file).start()
#------------------------------------------------------------------------------
class List_Column(Link):
    def __init__(self,columnsKey,allColumnsKey,colName,enable=True):
        Link.__init__(self)
        self.colName = colName
        self.columnsKey = columnsKey
        self.allColumnsKey = allColumnsKey
        self.enable = enable

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        colName = settings['bash.colNames'][self.colName]
        check = self.colName in settings[self.columnsKey]
        help = _(u"Show/Hide '%s' column.") % colName
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
            settings[self.columnsKey] = [x for x in settingDefaults[self.allColumnsKey] if x in settings[self.columnsKey] or x == self.colName]
        self.window.PopulateColumns()
        self.window.RefreshUI()

#------------------------------------------------------------------------------

class List_Columns(Link):
    """Customize visible columns."""
    def __init__(self,columnsKey,allColumnsKey,persistantColumns=[]):
        Link.__init__(self)
        self.columnsKey = columnsKey
        self.allColumnsKey = allColumnsKey
        self.persistant = persistantColumns

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        subMenu = wx.Menu()
        menu.AppendMenu(self.id,_(u"Columns"),subMenu)
        for col in settingDefaults[self.allColumnsKey]:
            enable = col not in self.persistant
            List_Column(self.columnsKey,self.allColumnsKey,col,enable).AppendToMenu(subMenu,window,data)

#------------------------------------------------------------------------------
class Installers_AddMarker(Link):
    """Add an installer marker."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Add Marker...'),_(u'Adds a Marker, a special type of package useful for separating and labelling your packages.'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        """Handle selection."""
        index = self.gTank.GetIndex(GPath(u'===='))
        if index == -1:
            self.data.addMarker(u'====')
            self.data.refresh(what='OS')
            gInstallers.RefreshUIMods()
            index = self.gTank.GetIndex(GPath(u'===='))
        if index != -1:
            self.gTank.ClearSelected()
            self.gTank.gList.SetItemState(index,wx.LIST_STATE_SELECTED,wx.LIST_STATE_SELECTED)
            self.gTank.gList.EditLabel(index)

#------------------------------------------------------------------------------
class Installers_MonitorInstall(Link):
    """Monitors Data folder for external installation."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Monitor External Installation...'),
                               _(u'Monitors the Data folder during installation via manual install or 3rd party tools.'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        """Handle Selection."""
        if not balt.askOk(self.gTank,_(u'Wrye Bash will monitor your data folder for changes when installing a mod via an external application or manual install.  This will require two refreshes of the Data folder and may take some time.')
                          ,_(u'External Installation')):
            return
        # Refresh Data
        gInstallers.refreshed = False
        gInstallers.fullRefresh = False
        gInstallers.OnShow(canCancel=False)
        # Backup CRC data
        data = copy.copy(gInstallers.data.data_sizeCrcDate)
        # Install and wait
        balt.showOk(self.gTank,_(u'You may now install your mod.  When installation is complete, press Ok.'),_(u'External Installation'))
        # Refresh Data
        gInstallers.refreshed = False
        gInstallers.fullRefresh = False
        gInstallers.OnShow(canCancel=False)
        # Determine changes
        curData = gInstallers.data.data_sizeCrcDate
        oldFiles = set(data)
        curFiles = set(curData)
        newFiles = curFiles - oldFiles
        delFiles = oldFiles - curFiles
        sameFiles = curFiles & oldFiles
        changedFiles = set(file for file in sameFiles if data[file][1] != curData[file][1])
        touchedFiles = set(file for file in sameFiles if data[file][2] != curData[file][2])
        touchedFiles -= changedFiles

        if not newFiles and not changedFiles and not touchedFiles:
            balt.showOk(self.gTank,_(u'No changes were detected in the Data directory.'),_(u'External Installation'))
            return

        # Change to list for sorting
        newFiles = list(newFiles)
        newFiles.sort()
        delFiles = list(delFiles)
        changedFiles = list(changedFiles)
        changedFiles.sort()
        touchedFiles = list(touchedFiles)
        touchedFiles.sort()
        # Show results, select which files to include
        checklists = []
        newFilesKey = _(u'New Files: %(count)i') % {'count':len(newFiles)}
        changedFilesKey = _(u'Changed Files: %(count)i') % {'count':len(changedFiles)}
        touchedFilesKey = _(u'Touched Files: %(count)i') % {'count':len(touchedFiles)}
        delFilesKey = _(u'Deleted Files')
        if newFiles:
            group = [newFilesKey,
                     _(u'These files are newly added to the Data directory.'),
                     ]
            group.extend(newFiles)
            checklists.append(group)
        if changedFiles:
            group = [changedFilesKey,
                     _(u'These files were modified.'),
                     ]
            group.extend(changedFiles)
            checklists.append(group)
        if touchedFiles:
            group = [touchedFilesKey,
                     _(u'These files were not changed, but had their modification time altered.  Most likely, these files are included in the external installation, but were the same version as already existed.'),
                     ]
            group.extend(touchedFiles)
            checklists.append(group)
        if delFiles:
            group = [delFilesKey,
                     _(u'These files were deleted.  BAIN does not have the capability to remove files when installing.'),
                     ]
            group.extend(delFiles)
        dialog = ListBoxes(self.gTank,_(u'External Installation'),
                           _(u'The following changes were detected in the Data directory'),
                           checklists,changedlabels={wx.ID_OK:_(u'Create Project')})
        choice = dialog.ShowModal()
        if choice == wx.ID_CANCEL:
            dialog.Destroy()
            return
        include = set()
        for (lst,key) in [(newFiles,newFilesKey),
                           (changedFiles,changedFilesKey),
                           (touchedFiles,touchedFilesKey),
                           ]:
            if lst:
                id = dialog.ids[key]
                checks = dialog.FindWindowById(id)
                if checks:
                    for i,file in enumerate(lst):
                        if checks.IsChecked(i):
                            include.add(file)
        dialog.Destroy()
        # Create Project
        if not include:
            return
        projectName = balt.askText(self.gTank,_(u'Project Name'),_(u'External Installation'))
        if not projectName:
            return
        path = bosh.dirs['installers'].join(projectName).root
        if path.exists():
            num = 2
            tmpPath = path + u' (%i)' % num
            while tmpPath.exists():
                num += 1
                tmpPath = path + u' (%i)' % num
            path = tmpPath
        # Copy Files
        with balt.Progress(_(u'Creating Project...'),u'\n'+u' '*60) as progress:
            bosh.InstallerProject.createFromData(path,include,progress)
        # Refresh Installers - so we can manipulate the InstallerProject item
        gInstallers.OnShow()
        # Update the status of the installer (as installer last)
        path = path.relpath(bosh.dirs['installers'])
        self.data.install([path],None,True,False)
        # Refresh UI
        gInstallers.RefreshUIMods()
        # Select new installer
        gList = self.gTank.gList
        gList.SetItemState(gList.GetItemCount()-1,wx.LIST_STATE_SELECTED,wx.LIST_STATE_SELECTED)

# Installers Links ------------------------------------------------------------
#------------------------------------------------------------------------------
class Installers_AnnealAll(Link):
    """Anneal all packages."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Anneal All'),_(u'This will install any missing files (for active installers) and correct all install order and reconfiguration errors.'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        """Handle selection."""
        try:
            with balt.Progress(_(u"Annealing..."),u'\n'+u' '*60) as progress:
                self.data.anneal(progress=progress)
        finally:
            self.data.refresh(what='NS')
            gInstallers.RefreshUIMods()
            bashFrame.RefreshData()

#------------------------------------------------------------------------------
class Installers_UninstallAllPackages(Link):
    """Uninstall all packages."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Uninstall All Packages'),_(u'This will uninstall all packages.'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        """Handle selection."""
        if not balt.askYes(self.gTank,fill(_(u"Really uninstall All Packages?"),70),self.title): return
        try:
            with balt.Progress(_(u"Uninstalling..."),u'\n'+u' '*60) as progress:
                self.data.uninstall(unArchives='ALL',progress=progress)
        finally:
            self.data.refresh(what='NS')
            gInstallers.RefreshUIMods()
            bashFrame.RefreshData()

#------------------------------------------------------------------------------
class Installers_UninstallAllUnknownFiles(Link):
    """Uninstall all files that do not come from a current package/bethesda files.
       For safety just moved to Oblivion Mods\Bash Installers\Bash\Data Folder Contents (date/time)\."""
    def __init__(self):
        Link.__init__(self)
        self._helpMessage = _(u'This will remove all mod files that are not linked to an active installer out of the Data folder.')

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Clean Data'),self._helpMessage)
        menu.AppendItem(menuItem)

    def Execute(self,event):
        """Handle selection."""
        fullMessage = _(u"Clean Data directory?") + u"  " + self._helpMessage + u"  " + _(u'This includes files that were installed manually or by another program.  Files will be moved to the "%s" directory instead of being deleted so you can retrieve them later if necessary.  Note that if you use TES4LODGen, this will also clean out the DistantLOD folder, so on completion please run TES4LodGen again.') % u'Oblivion Mods\\Bash Installers\\Bash\\Data Folder Contents <date>'
        if not balt.askYes(self.gTank,fill(fullMessage,70),self.title):
            return
        try:
            with balt.Progress(_(u"Cleaning Data Files..."),u'\n'+u' '*65) as progress:
                self.data.clean(progress=progress)
        finally:
            self.data.refresh(what='NS')
            gInstallers.RefreshUIMods()
            bashFrame.RefreshData()

#------------------------------------------------------------------------------
class Installers_AutoAnneal(BoolLink):
    def __init__(self):
        BoolLink.__init__(self,
                          _(u'Auto-Anneal'),
                          'bash.installers.autoAnneal',
                          _(u"Enable/Disable automatic annealing of packages.")
                          )

#------------------------------------------------------------------------------
class Installers_AutoWizard(BoolLink):
    def __init__(self):
        BoolLink.__init__(self,
                          _(u'Auto-Anneal/Install Wizards'),
                          'bash.installers.autoWizard',
                          _(u"Enable/Disable automatic installing or anneal (as applicable) of packages after running its wizard.")
                          )

#------------------------------------------------------------------------------
class Installers_WizardOverlay(BoolLink):
    """Toggle using the wizard overlay icon"""
    def __init__(self):
        BoolLink.__init__(self,
                          _(u'Wizard Icon Overlay'),
                          'bash.installers.wizardOverlay',
                          _(u"Enable/Disable the magic wand icon overlay for packages with Wizards.")
                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        gInstallers.gList.RefreshUI()

#------------------------------------------------------------------------------
class Installers_AutoRefreshProjects(BoolLink):
    """Toggle autoRefreshProjects setting and update."""
    def __init__(self):
        BoolLink.__init__(self,
                          _(u'Auto-Refresh Projects'),
                          'bash.installers.autoRefreshProjects',
                          )

#------------------------------------------------------------------------------
class Installers_AutoApplyEmbeddedBCFs(BoolLink):
    """Toggle autoApplyEmbeddedBCFs setting and update."""
    def __init__(self):
        BoolLink.__init__(self,
                          _(u'Auto-Apply Embedded BCFs'),
                          'bash.installers.autoApplyEmbeddedBCFs',
                          _(u'If enabled, embedded BCFs will automatically be applied to archives.')
                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        gInstallers.OnShow()

#------------------------------------------------------------------------------
class Installers_AutoRefreshBethsoft(BoolLink):
    """Toggle refreshVanilla setting and update."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Skip Bethsoft Content'),
                                         'bash.installers.autoRefreshBethsoft',
                                         u'Skip installing Bethesda ESMs, ESPs, and BSAs.',
                                         True
                                         )

    def Execute(self,event):
        if not settings[self.key]:
            message = balt.fill(_(u"Enable installation of Bethsoft Content?") + u'\n\n' +
                                _(u"In order to support this, Bethesda ESPs, ESMs, and BSAs need to have their CRCs calculatted.  This will be accomplished by a full refresh of BAIN data an may take quite some time.  Are you sure you want to continue?")
                                )
            if not balt.askYes(self.gTank,fill(message,80),self.title): return
        BoolLink.Execute(self,event)
        if settings[self.key]:
            # Refresh Data - only if we are now including Bethsoft files
            gInstallers.refreshed = False
            gInstallers.fullRefresh = False
            gInstallers.OnShow()
        # Refresh Installers
        toRefresh = set()
        for name in gInstallers.data.data:
            installer = gInstallers.data.data[name]
            if installer.hasBethFiles:
                toRefresh.add((name,installer))
        if toRefresh:
            with balt.Progress(_(u'Refreshing Packages...'),u'\n'+u' '*60) as progress:
                progress.setFull(len(toRefresh))
                for index,(name,installer) in enumerate(toRefresh):
                    progress(index,_(u'Refreshing Packages...')+u'\n'+name.s)
                    apath = bosh.dirs['installers'].join(name)
                    installer.refreshBasic(apath,SubProgress(progress,index,index+1),True)
                    gInstallers.data.hasChanged = True
            gInstallers.data.refresh(what='NSC')
            gInstallers.gList.RefreshUI()

#------------------------------------------------------------------------------
class Installers_Enabled(BoolLink):
    """Flips installer state."""
    def __init__(self): BoolLink.__init__(self,
                                         _(u'Enabled'),
                                         'bash.installers.enabled',
                                         _(u'Enable/Disable the Installers tab.')
                                         )

    def Execute(self,event):
        """Handle selection."""
        enabled = settings[self.key]
        message = (_(u"Do you want to enable Installers?")
                   + u'\n\n\t' +
                   _(u"If you do, Bash will first need to initialize some data. This can take on the order of five minutes if there are many mods installed.")
                   )
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
                          _(u'BSA Redirection'),
                          'bash.bsaRedirection',
                          )

    def AppendToMenu(self,menu,window,data):
        section,key = bush.game.ini.bsaRedirection
        if not section or not key:
            return
        BoolLink.AppendToMenu(self,menu,window,data)

    def Execute(self,event):
        """Handle selection."""
        BoolLink.Execute(self,event)
        if settings[self.key]:
            bsaPath = bosh.modInfos.dir.join(bosh.inisettings['OblivionTexturesBSAName'])
            bsaFile = bosh.BsaFile(bsaPath)
            bsaFile.scan()
            resetCount = bsaFile.reset()
            #balt.showOk(self,_(u"BSA Hashes reset: %d") % (resetCount,))
        bosh.oblivionIni.setBsaRedirection(settings[self.key])

#------------------------------------------------------------------------------
class Installers_ConflictsReportShowsInactive(BoolLink):
    """Toggles option to show inactive on conflicts report."""
    def __init__(self):
        BoolLink.__init__(self,
                          _(u'Show Inactive Conflicts'),
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
                          _(u'Show Lower Conflicts'),
                          'bash.installers.conflictsReport.showLower',
                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class Installers_ConflictsReportShowBSAConflicts(BoolLink):
    """Toggles option to show files inside BSAs on conflicts report."""
    def __init__(self):
        BoolLink.__init__(self,
                          _(u'Show BSA Conflicts'),
                          'bash.installers.conflictsReport.showBSAConflicts',
                          )

    def Execute(self,event):
        BoolLink.Execute(self, event)
        self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class Installers_AvoidOnStart(BoolLink):
    """Ensures faster bash startup by preventing Installers from being startup tab."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Avoid at Startup'),
                                          'bash.installers.fastStart',
                                          _(u"Toggles Wrye Bash to avoid the Installers tab on startup, avoiding unnecessary data scanning.")
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
        self.title = (_(u'Refresh Data'),_(u'Full Refresh'))[self.fullRefresh]
        if self.fullRefresh:
            help = _(u"Perform a full refresh of all data files, recalculating all CRCs.  This can take 5-15 minutes.")
        else:
            help = _(u"Rescan the Data directory and all project directories.")
        menuItem = wx.MenuItem(menu,self.id,self.title,help)
        menu.AppendItem(menuItem)

    def Execute(self,event):
        """Handle selection."""
        if self.fullRefresh:
            message = balt.fill(_(u"Refresh ALL data from scratch? This may take five to ten minutes (or more) depending on the number of mods you have installed."))
            if not balt.askWarning(self.gTank,fill(message,80),self.title): return
        gInstallers.refreshed = False
        gInstallers.fullRefresh = self.fullRefresh
        gInstallers.OnShow()

#------------------------------------------------------------------------------
class Installers_RemoveEmptyDirs(BoolLink):
    """Toggles option to remove empty directories on file scan."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Clean Data Directory'),
                                          'bash.installers.removeEmptyDirs',
                                          )

#------------------------------------------------------------------------------
class Installers_Skip(BoolLink):
    """Toggle various skip settings and update."""
    def Execute(self,event):
        BoolLink.Execute(self,event)
        with balt.Progress(_(u'Refreshing Packages...'),u'\n'+u' '*60, abort=False) as progress:
            progress.setFull(len(self.data))
            for index,dataItem in enumerate(self.data.iteritems()):
                progress(index,_(u'Refreshing Packages...')+u'\n'+dataItem[0].s)
                dataItem[1].refreshDataSizeCrc()
        self.data.refresh(what='NS')
        self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class Installers_SkipScreenshots(Installers_Skip):
    """Toggle skipScreenshots setting and update."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Skip Screenshots'),
                                          'bash.installers.skipScreenshots',
                                          )

#------------------------------------------------------------------------------
class Installers_SkipImages(Installers_Skip):
    """Toggle skipImages setting and update."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Skip Images'),
                                          'bash.installers.skipImages',
                                          )

#------------------------------------------------------------------------------
class Installers_SkipDocs(Installers_Skip):
    """Toggle skipDocs setting and update."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Skip Docs'),
                                          'bash.installers.skipDocs',
                                          )

#------------------------------------------------------------------------------
class Installers_SkipDistantLOD(Installers_Skip):
    """Toggle skipDistantLOD setting and update."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Skip DistantLOD'),
                                          'bash.installers.skipDistantLOD',
                                          )

#------------------------------------------------------------------------------
class Installers_skipLandscapeLODMeshes(Installers_Skip):
    """Toggle skipLandscapeLODMeshes setting and update."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Skip LOD Meshes'),
                                          'bash.installers.skipLandscapeLODMeshes',
                                          )

#------------------------------------------------------------------------------
class Installers_skipLandscapeLODTextures(Installers_Skip):
    """Toggle skipDistantLOD setting and update."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Skip LOD Textures'),
                                          'bash.installers.skipLandscapeLODTextures',
                                          )

#------------------------------------------------------------------------------
class Installers_skipLandscapeLODNormals(Installers_Skip):
    """Toggle skipDistantLOD setting and update."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Skip LOD Normals'),
                                          'bash.installers.skipLandscapeLODNormals',
                                          )

#------------------------------------------------------------------------------
class Installers_SkipOBSEPlugins(Installers_Skip):
    """Toggle allowOBSEPlugins setting and update."""
    def __init__(self):
        BoolLink.__init__(self,_(u'Skip %s Plugins') % bush.game.se_sd,
                          'bash.installers.allowOBSEPlugins')

    def AppendToMenu(self,menu,window,data):
        if not bush.game.se_sd: return
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,self.text,self.help,kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        menuItem.Check(not settings[self.key])
        bosh.installersWindow = self.gTank

#------------------------------------------------------------------------------
class Installers_RenameStrings(Installers_Skip):
    """Toggle auto-renaming of .STRINGS files"""
    def __init__(self):
        BoolLink.__init__(self,
                          _(u'Auto-name String Translation Files'),
                          'bash.installers.renameStrings',
                          )

    def AppendToMenu(self,menu,window,data):
        if bush.game.esp.stringsFiles:
            Installers_Skip.AppendToMenu(self,menu,window,data)

#------------------------------------------------------------------------------
class Installers_SortActive(BoolLink):
    """Sort by type."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Sort by Active'),
                                          'bash.installers.sortActive',
                                          _(u'If selected, active installers will be sorted to the top of the list.')
                                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        self.gTank.SortItems()

#------------------------------------------------------------------------------
class Installers_SortProjects(BoolLink):
    """Sort dirs to the top."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Projects First'),
                                          'bash.installers.sortProjects',
                                          _(u'If selected, projects will be sorted to the top of the list.')
                                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        self.gTank.SortItems()

#------------------------------------------------------------------------------
class Installers_SortStructure(BoolLink):
    """Sort by type."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Sort by Structure'),
                                          'bash.installers.sortStructure',
                                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        self.gTank.SortItems()

# Installer Links -------------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerLink(Link):
    """Common functions for installer links..."""

    def isSingleInstallable(self):
        if len(self.selected) == 1:
            installer = self.data[self.selected[0]]
            if not isinstance(installer,(bosh.InstallerProject,bosh.InstallerArchive)):
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
        if self.isSingleArchive():
            title = _(u'View Wizard...')
        else:
            title = _(u'Edit Wizard...')
        menuItem = wx.MenuItem(menu, self.id, title,
            help=_(u"Edit the wizard.txt associated with this project."))
        menu.AppendItem(menuItem)
        if self.isSingleInstallable():
            menuItem.Enable(bool(self.data[self.selected[0]].hasWizard))
        else:
            menuItem.Enable(False)

    def Execute(self, event):
        path = self.selected[0]
        if self.isSingleProject():
            # Project, open for edit
            dir = self.data.dir
            dir.join(path.s, self.data[path].hasWizard).start()
        else:
            # Archive, open for viewing
            archive = self.data[path]
            with balt.BusyCursor():
                # This is going to leave junk temp files behind...
                try:
                    archive.unpackToTemp(path, [archive.hasWizard])
                    archive.getTempDir().join(archive.hasWizard).start()
                except:
                    # Don't clean up temp dir here.  Sometimes the editor
                    # That starts to open the wizard.txt file is slower than
                    # Bash, and the file will be deleted before it opens.
                    # Just allow Bash's atexit function to clean it when
                    # quitting.
                    pass

class Installer_Wizard(InstallerLink):
    """Runs the install wizard to select subpackages and esp/m filtering"""
    parentWindow = ''

    def __init__(self, bAuto):
        InstallerLink.__init__(self)
        self.bAuto = bAuto

    def AppendToMenu(self, menu, window, data):
        Link.AppendToMenu(self, menu, window, data)
        if not self.bAuto:
            menuItem = wx.MenuItem(menu, self.id, _(u'Wizard'),
                help=_(u"Run the install wizard."))
        else:
            menuItem = wx.MenuItem(menu, self.id, _(u'Auto Wizard'),
                help=_(u"Run the install wizard."))
        menu.AppendItem(menuItem)
        if self.isSingle():
            installer = self.data[self.selected[0]]
            menuItem.Enable(installer.hasWizard != False)
        else:
            menuItem.Enable(False)

    def Execute(self, event):
        with balt.BusyCursor():
            installer = self.data[self.selected[0]]
            subs = []
            oldRemaps = copy.copy(installer.remaps)
            installer.remaps = {}
            gInstallers.refreshCurrent(installer)
            for index in range(gInstallers.gSubList.GetCount()):
                subs.append(gInstallers.gSubList.GetString(index))
            saved = settings['bash.wizard.size']
            default = settingDefaults['bash.wizard.size']
            pos = settings['bash.wizard.pos']
            # Sanity checks on saved size/position
            if not isinstance(pos,tuple) or len(pos) != 2:
                deprint(_(u'Saved Wizard position (%s) was not a tuple (%s), reverting to default position.') % (pos,type(pos)))
                pos = wx.DefaultPosition
            if not isinstance(saved,tuple) or len(saved) != 2:
                deprint(_(u'Saved Wizard size (%s) was not a tuple (%s), reverting to default size.') % (saved, type(saved)))
                pageSize = tuple(default)
            else:
                pageSize = (max(saved[0],default[0]),max(saved[1],default[1]))
            try:
                wizard = belt.InstallerWizard(self, subs, pageSize, pos)
            except bolt.CancelError:
                return
            balt.ensureDisplayed(wizard)
        ret = wizard.Run()
        # Sanity checks on returned size/position
        if not isinstance(ret.Pos,wx.Point):
            deprint(_(u'Returned Wizard position (%s) was not a wx.Point (%s), reverting to default position.') % (ret.Pos, type(ret.Pos)))
            ret.Pos = wx.DefaultPosition
        if not isinstance(ret.PageSize,wx.Size):
            deprint(_(u'Returned Wizard size (%s) was not a wx.Size (%s), reverting to default size.') % (ret.PageSize, type(ret.PageSize)))
            ret.PageSize = tuple(default)
        settings['bash.wizard.size'] = (ret.PageSize[0],ret.PageSize[1])
        settings['bash.wizard.pos'] = (ret.Pos[0],ret.Pos[1])
        if ret.Canceled:
            installer.remaps = oldRemaps
            gInstallers.refreshCurrent(installer)
            return
        #Check the sub-packages that were selected by the wizard
        installer.resetAllEspmNames()
        for index in xrange(gInstallers.gSubList.GetCount()):
            select = installer.subNames[index + 1] in ret.SelectSubPackages
            gInstallers.gSubList.Check(index, select)
            installer.subActives[index + 1] = select
        gInstallers.refreshCurrent(installer)
        #Check the espms that were selected by the wizard
        espms = gInstallers.gEspmList.GetStrings()
        espms = [x.replace(u'&&',u'&') for x in espms]
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
        if ret.Install:
            #If it's currently installed, anneal
            if self.data[self.selected[0]].isActive:
                #Anneal
                try:
                    with balt.Progress(_(u'Annealing...'), u'\n'+u' '*60) as progress:
                        self.data.anneal(self.selected, progress)
                finally:
                    self.data.refresh(what='NS')
                    gInstallers.RefreshUIMods()
            else:
                #Install, if it's not installed
                try:
                    with balt.Progress(_(u'Installing...'),u'\n'+u' '*60) as progress:
                        self.data.install(self.selected, progress)
                finally:
                    self.data.refresh(what='N')
                    gInstallers.RefreshUIMods()
            bashFrame.RefreshData()
        #Build any ini tweaks
        manuallyApply = []  # List of tweaks the user needs to  manually apply
        lastApplied = None
        #       iniList-> left    -> splitter ->INIPanel
        panel = iniList.GetParent().GetParent().GetParent()
        for iniFile in ret.IniEdits:
            outFile = bosh.dirs['tweaks'].join(u'%s - Wizard Tweak [%s].ini' % (installer.archive, iniFile.sbody))
            with outFile.open('w') as out:
                for line in belt.generateTweakLines(ret.IniEdits[iniFile],iniFile):
                    out.write(line+u'\n')
            bosh.iniInfos.refresh()
            bosh.iniInfos.table.setItem(outFile.tail, 'installer', installer.archive)
            iniList.RefreshUI()
            if iniFile in installer.data_sizeCrc or any([iniFile == x for x in bush.game.iniFiles]):
                if not ret.Install and not any([iniFile == x for x in bush.game.iniFiles]):
                    # Can only automatically apply ini tweaks if the ini was actually installed.  Since
                    # BAIN is setup to not auto install after the wizard, we'll show a message telling the
                    # User what tweaks to apply manually.
                    manuallyApply.append((outFile,iniFile))
                    continue
                # Editing an INI file from this installer is ok, but editing Oblivion.ini
                # give a warning message
                if any([iniFile == x for x in bush.game.iniFiles]):
                    message = (_(u'Apply an ini tweak to %s?')
                               + u'\n\n' +
                               _(u'WARNING: Incorrect tweaks can result in CTDs and even damage to you computer!')
                               ) % iniFile.sbody
                    if not balt.askContinue(self.gTank,message,'bash.iniTweaks.continue',_(u'INI Tweaks')):
                        continue
                panel.AddOrSelectIniDropDown(bosh.dirs['mods'].join(iniFile))
                if bosh.iniInfos[outFile.tail] == 20: continue
                iniList.data.ini.applyTweakFile(outFile)
                lastApplied = outFile.tail
            else:
                # We wont automatically apply tweaks to anything other than Oblivion.ini or an ini from
                # this installer
                manuallyApply.append((outFile,iniFile))
        #--Refresh after all the tweaks are applied
        if lastApplied is not None:
            iniList.RefreshUI('VALID')
            panel.iniContents.RefreshUI()
            panel.tweakContents.RefreshUI(lastApplied)
        if len(manuallyApply) > 0:
            message = balt.fill(_(u'The following INI Tweaks were not automatically applied.  Be sure to apply them after installing the package.'))
            message += u'\n\n'
            message += u'\n'.join([u' * ' + x[0].stail + u'\n   TO: ' + x[1].s for x in manuallyApply])
            balt.showInfo(self.gTank,message)

class Installer_OpenReadme(InstallerLink):
    """Opens the installer's readme if BAIN can find one"""

    def AppendToMenu(self, menu, window, data):
        Link.AppendToMenu(self, menu, window, data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Open Readme'),
            help=_(u"Opens the installer's readme."))
        menu.AppendItem(menuItem)
        if self.isSingle():
            installer = self.data[self.selected[0]]
            menuItem.Enable(bool(installer.hasReadme))
        else:
            menuItem.Enable(False)

    def Execute(self, event):
        installer = self.selected[0]
        if self.isSingleProject():
            # Project, open for edit
            dir = self.data.dir
            dir.join(installer.s, self.data[installer].hasReadme).start()
        else:
            # Archive, open for viewing
            archive = self.data[installer]
            with balt.BusyCursor():
                # This is going to leave junk temp files behind...
                archive.unpackToTemp(installer, [archive.hasReadme])
            archive.getTempDir().join(archive.hasReadme).start()

#------------------------------------------------------------------------------
class Installer_Anneal(InstallerLink):
    """Anneal all packages."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Anneal'),
            help=_(u"Anneal all packages."))
        menu.AppendItem(menuItem)
        selected = self.filterInstallables()
        menuItem.Enable(len(selected))

    def Execute(self,event):
        """Handle selection."""
        try:
            with balt.Progress(_(u"Annealing..."),u'\n'+u' '*60) as progress:
                self.data.anneal(self.filterInstallables(),progress)
        except (CancelError,SkipError):
            pass
        finally:
            self.data.refresh(what='NS')
            gInstallers.RefreshUIMods()
            bashFrame.RefreshData()

#------------------------------------------------------------------------------
class Installer_Duplicate(InstallerLink):
    """Duplicate selected Installer."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.title = _(u'Duplicate...')
        menuItem = wx.MenuItem(menu,self.id,self.title,
            help=_(u"Duplicate selected %(installername)s.") % ({'installername':self.selected[0]}))
        menu.AppendItem(menuItem)
        menuItem.Enable(self.isSingle() and not self.isSingleMarker())

    def Execute(self,event):
        """Handle selection."""
        curName = self.selected[0]
        isdir = self.data.dir.join(curName).isdir()
        if isdir: root,ext = curName,u''
        else: root,ext = curName.rootExt
        newName = root+_(u' Copy')+ext
        index = 0
        while newName in self.data:
            newName = root + (_(u' Copy (%d)') % index) + ext
            index += 1
        result = balt.askText(self.gTank,_(u"Duplicate %s to:") % curName.s,
            self.title,newName.s)
        result = (result or u'').strip()
        if not result: return
        #--Error checking
        newName = GPath(result).tail
        if not newName.s:
            balt.showWarning(self.gTank,_(u"%s is not a valid name.") % result)
            return
        if newName in self.data:
            balt.showWarning(self.gTank,_(u"%s already exists.") % newName.s)
            return
        if self.data.dir.join(curName).isfile() and curName.cext != newName.cext:
            balt.showWarning(self.gTank,
                _(u"%s does not have correct extension (%s).") % (newName.s,curName.ext))
            return
        #--Duplicate
        with balt.BusyCursor():
            self.data.copy(curName,newName)
            self.data.refresh(what='N')
            self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class Installer_Hide(InstallerLink):
    """Hide selected Installers."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.title = _(u'Hide...')
        menuItem = wx.MenuItem(menu,self.id,self.title,
            help=_(u"Hide selected installer(s)."))
        menu.AppendItem(menuItem)
        for item in window.GetSelected():
            if isinstance(window.data[item],bosh.InstallerMarker):
                menuItem.Enable(False)
                return
        menuItem.Enable(True)

    def Execute(self,event):
        """Handle selection."""
        if not bosh.inisettings['SkipHideConfirmation']:
            message = _(u'Hide these files? Note that hidden files are simply moved to the Bash\\Hidden subdirectory.')
            if not balt.askYes(self.gTank,message,_(u'Hide Files')): return
        destDir = bosh.dirs['modsBash'].join(u'Hidden')
        for curName in self.selected:
            newName = destDir.join(curName)
            if newName.exists():
                message = (_(u'A file named %s already exists in the hidden files directory. Overwrite it?')
                    % newName.stail)
                if not balt.askYes(self.gTank,message,_(u'Hide Files')): return
            #Move
            with balt.BusyCursor():
                file = bosh.dirs['installers'].join(curName)
                file.moveTo(newName)
        self.data.refresh(what='ION')
        self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class Installer_Rename(InstallerLink):
    """Renames files by pattern."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Rename...'),
            help=_(u"Rename selected installer(s)."))
        menu.AppendItem(menuItem)
        self.InstallerType = None
        ##Only enable if all selected items are of the same type
        firstItem = window.data[window.GetSelected()[0]]
        if isinstance(firstItem,bosh.InstallerMarker):
            self.InstallerType = bosh.InstallerMarker
        elif isinstance(firstItem,bosh.InstallerArchive):
            self.InstallerType = bosh.InstallerArchive
        elif isinstance(firstItem,bosh.InstallerProject):
            self.InstallerType = bosh.InstallerProject

        if self.InstallerType:
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
        menuItem = wx.MenuItem(menu,self.id,_(u'Has Extra Directories'),kind=wx.ITEM_CHECK,
            help=_(u"Allow installation of files in non-standard directories."))
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
        menuItem = wx.MenuItem(menu,self.id,_(u'Override Skips'),kind=wx.ITEM_CHECK,
            help=_(u"Override global file type skipping for %(installername)s.") % ({'installername':self.selected[0]}))
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
class Installer_SkipRefresh(InstallerLink):
    """Toggle skipRefresh flag on installer."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u"Don't Refresh"),kind=wx.ITEM_CHECK,
            help=_(u"Don't automatically refresh project."))
        menu.AppendItem(menuItem)
        if self.isSingleProject():
            installer = self.data[self.selected[0]]
            menuItem.Check(installer.skipRefresh)
            menuItem.Enable(True)
        else:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        installer = self.data[self.selected[0]]
        installer.skipRefresh ^= True
        if not installer.skipRefresh:
            # Check to see if we need to refresh this Project
            file = bosh.dirs['installers'].join(installer.archive)
            if (installer.size,installer.modified) != (file.size,file.getmtime(True)):
                installer.refreshDataSizeCrc()
                installer.refreshBasic(file)
                installer.refreshStatus(self.data)
                self.data.refresh(what='N')
                self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class Installer_Install(InstallerLink):
    """Install selected packages."""
    mode_title = {'DEFAULT':_(u'Install'),'LAST':_(u'Install Last'),'MISSING':_(u'Install Missing')}

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
        try:
            with balt.Progress(_(u'Installing...'),u'\n'+u' '*60) as progress:
                last = (self.mode == 'LAST')
                override = (self.mode != 'MISSING')
                try:
                    tweaks = self.data.install(self.filterInstallables(),progress,last,override)
                except (CancelError,SkipError):
                    pass
                except StateError as e:
                    balt.showError(self.window,u'%s'%e)
                else:
                    if tweaks:
                        balt.showInfo(self.window,
                            _(u'The following INI Tweaks were created, because the existing INI was different than what BAIN installed:')
                            +u'\n' + u'\n'.join([u' * %s\n' % x.stail for (x,y) in tweaks]),
                            _(u'INI Tweaks')
                            )
        finally:
            self.data.refresh(what='N')
            gInstallers.RefreshUIMods()
            bashFrame.RefreshData()

#------------------------------------------------------------------------------
class Installer_ListPackages(InstallerLink):
    """Copies list of Bain files to clipboard."""
    def AppendToMenu(self,menu,window,data):
        InstallerLink.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'List Packages...'),
            _(u'Displays a list of all packages.  Also copies that list to the clipboard.  Useful for posting your package order on forums.'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        #--Get masters list
        message = (_(u'Only show Installed Packages?')
                   + u'\n' +
                   _(u'(Else shows all packages)')
                   )
        if balt.askYes(self.gTank,message,_(u'Only Show Installed?')):
            text = self.data.getPackageList(False)
        else: text = self.data.getPackageList()
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        balt.showLog(self.gTank,text,_(u'BAIN Packages'),asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class Installer_ListStructure(InstallerLink):   # Provided by Waruddar
    """Copies folder structure of installer to clipboard."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.title = _(u"List Structure...")
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
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        balt.showLog(self.gTank,text,_(u'Package Structure'),asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class Installer_Move(InstallerLink):
    """Moves selected installers to desired spot."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Move To...'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        """Handle selection."""
        curPos = min(self.data[x].order for x in self.selected)
        message = (_(u'Move selected archives to what position?')
                   + u'\n' +
                   _(u'Enter position number.')
                   + u'\n' +
                   _(u'Last: -1; First of Last: -2; Semi-Last: -3.')
                   )
        newPos = balt.askText(self.gTank,message,self.title,unicode(curPos))
        if not newPos: return
        newPos = newPos.strip()
        try:
            newPos = int(newPos)
        except:
            balt.showError(self.gTank,_(u'Position must be an integer.'))
            return
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
        menuItem = wx.MenuItem(menu,self.id,_(u'Open...'), _(u"Open '%s'") % self.data.dir.tail)
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

class Installer_OpenNexus(InstallerLink):
    """Open selected file(s)."""
    def AppendToMenu(self,menu,window,data):
        if not bush.game.nexusUrl:
            return
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(bush.game.nexusName))
        menu.AppendItem(menuItem)
        x = bosh.reTesNexus.search(data[0].s)
        menuItem.Enable(bool(self.isSingleArchive() and x and x.group(2)))

    def Execute(self,event):
        """Handle selection."""
        message = _(u"Attempt to open this as a mod at %(nexusName)s? This assumes that the trailing digits in the package's name are actually the id number of the mod at %(nexusName)s. If this assumption is wrong, you'll just get a random mod page (or error notice) at %(nexusName)s.") % {'nexusName':bush.game.nexusName}
        if balt.askContinue(self.gTank,message, bush.game.nexusKey,_(u'Open at %(nexusName)s') % {'nexusName':bush.game.nexusName}):
            id = bosh.reTesNexus.search(self.selected[0].s).group(2)
            webbrowser.open(bush.game.nexusUrl+u'mods/'+id)

class Installer_OpenSearch(InstallerLink):
    """Open selected file(s)."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Google...'))
        menu.AppendItem(menuItem)
        x = bosh.reTesNexus.search(data[0].s)
        menuItem.Enable(bool(self.isSingleArchive() and x and x.group(1)))

    def Execute(self,event):
        """Handle selection."""
        message = _(u"Open a search for this on Google?")
        if balt.askContinue(self.gTank,message,'bash.installers.opensearch',_(u'Open a search')):
            webbrowser.open(u'http://www.google.com/search?hl=en&q='+u'+'.join(re.split(ur'\W+|_+',bosh.reTesNexus.search(self.selected[0].s).group(1))))

class Installer_OpenTESA(InstallerLink):
    """Open selected file(s)."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'TES Alliance...'))
        menu.AppendItem(menuItem)
        x = bosh.reTESA.search(data[0].s)
        menuItem.Enable(bool(self.isSingleArchive() and x and x.group(2)))

    def Execute(self,event):
        """Handle selection."""
        message = _(u"Attempt to open this as a mod at TES Alliance? This assumes that the trailing digits in the package's name are actually the id number of the mod at TES Alliance. If this assumption is wrong, you'll just get a random mod page (or error notice) at TES Alliance.")
        if balt.askContinue(self.gTank,message,'bash.installers.openTESA',_(u'Open at TES Alliance')):
            id = bosh.reTESA.search(self.selected[0].s).group(2)
            webbrowser.open(u'http://tesalliance.org/forums/index.php?app=downloads&showfile='+id)

class Installer_OpenPES(InstallerLink):
    """Open selected file(s)."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Planet Elderscrolls...'))
        menu.AppendItem(menuItem)
        x = bosh.reTESA.search(data[0].s)
        menuItem.Enable(bool(self.isSingleArchive() and x and x.group(2)))

    def Execute(self,event):
        """Handle selection."""
        message = _(u"Attempt to open this as a mod at Planet Elderscrolls? This assumes that the trailing digits in the package's name are actually the id number of the mod at Planet Elderscrolls. If this assumption is wrong, you'll just get a random mod page (or error notice) at Planet Elderscrolls.")
        if balt.askContinue(self.gTank,message,'bash.installers.openPES',_(u'Open at Planet Elderscrolls')):
            id = bosh.reTESA.search(self.selected[0].s).group(2)
            webbrowser.open(u'http://planetelderscrolls.gamespy.com/View.php?view=OblivionMods.Detail&id='+id)

#------------------------------------------------------------------------------
class Installer_Refresh(InstallerLink):
    """Rescans selected Installers."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Refresh'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        """Handle selection."""
        dir = self.data.dir
        try:
            with balt.Progress(_(u'Refreshing Packages...'),u'\n'+u' '*60, abort=True) as progress:
                progress.setFull(len(self.selected))
                for index,archive in enumerate(self.selected):
                    progress(index,_(u'Refreshing Packages...')+u'\n'+archive.s)
                    installer = self.data[archive]
                    apath = bosh.dirs['installers'].join(archive)
                    installer.refreshBasic(apath,SubProgress(progress,index,index+1),True)
                    self.data.hasChanged = True
        except CancelError:
            # User canceled the refresh
            pass
        self.data.refresh(what='NSC')
        self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class Installer_SkipVoices(InstallerLink):
    """Toggle skipVoices flag on installer."""

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Skip Voices'),kind=wx.ITEM_CHECK)
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
        menuItem = wx.MenuItem(menu,self.id,_(u'Uninstall'))
        menu.AppendItem(menuItem)
        selected = self.filterInstallables()
        menuItem.Enable(len(selected))

    def Execute(self,event):
        """Handle selection."""
        dir = self.data.dir
        try:
            with balt.Progress(_(u"Uninstalling..."),u'\n'+u' '*60) as progress:
                self.data.uninstall(self.filterInstallables(),progress)
        except (CancelError,SkipError):
            pass
        finally:
            self.data.refresh(what='NS')
            bosh.modInfos.plugins.saveLoadOrder()
            gInstallers.RefreshUIMods()
            bashFrame.RefreshData()

#------------------------------------------------------------------------------
class Installer_CopyConflicts(InstallerLink):
    """For Modders only - copy conflicts to a new project."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.title = _(u'Copy Conflicts to Project')
        menuItem = wx.MenuItem(menu,self.id,self.title)
        menu.AppendItem(menuItem)
        menuItem.Enable(self.isSingleInstallable())

    def Execute(self,event):
        """Handle selection."""
        data = self.data # bosh.InstallersData instance
        installers_dir = data.dir
        srcConflicts = set()
        packConflicts = []
        with balt.Progress(_(u"Copying Conflicts..."),
                           u'\n' + u' ' * 60) as progress:
            srcArchive = self.selected[0]
            srcInstaller = data[srcArchive]
            src_sizeCrc = srcInstaller.data_sizeCrc
            mismatched = set(src_sizeCrc)
            if mismatched:
                numFiles = 0
                curFile = 1
                srcOrder = srcInstaller.order
                destDir = GPath(u"%03d - Conflicts" % srcOrder)
                getArchiveOrder = lambda y: data[y].order
                for package in sorted(data.data,key=getArchiveOrder):
                    installer = data[package]
                    curConflicts = set()
                    for z,y in installer.refreshDataSizeCrc().iteritems():
                        if z in mismatched and installer.data_sizeCrc[z] != \
                                src_sizeCrc[z]:
                            curConflicts.add(y)
                            srcConflicts.add(src_sizeCrc[z])
                    numFiles += len(curConflicts)
                    if curConflicts: packConflicts.append(
                        (installer.order,installer,package,curConflicts))
                srcConflicts = set(
                    src for src,size,crc in srcInstaller.fileSizeCrcs if
                    (size,crc) in srcConflicts)
                numFiles += len(srcConflicts)
                if numFiles:
                    progress.setFull(numFiles)
                    if isinstance(srcInstaller,bosh.InstallerProject):
                        for src in srcConflicts:
                            srcFull = installers_dir.join(srcArchive,src)
                            destFull = installers_dir.join(destDir,
                                                           GPath(srcArchive.s),
                                                           src)
                            if srcFull.exists():
                                progress(curFile,srcArchive.s + u'\n' + _(
                                    u'Copying files...') + u'\n' + src)
                                srcFull.copyTo(destFull)
                                curFile += 1
                    else:
                        srcInstaller.unpackToTemp(srcArchive,srcConflicts,
                                                  SubProgress(progress,0,len(
                                                      srcConflicts),numFiles))
                        srcInstaller.getTempDir().moveTo(
                            installers_dir.join(destDir,GPath(srcArchive.s)))
                    curFile = len(srcConflicts)
                    for order,installer,package,curConflicts in packConflicts:
                        if isinstance(installer,bosh.InstallerProject):
                            for src in curConflicts:
                                srcFull = installers_dir.join(package,src)
                                destFull = installers_dir.join(destDir,GPath(
                                    u"%03d - %s" % (order,package.s)),src)
                                if srcFull.exists():
                                    progress(curFile,srcArchive.s + u'\n' + _(
                                        u'Copying files...') + u'\n' + src)
                                    srcFull.copyTo(destFull)
                                    curFile += 1
                        else:
                            installer.unpackToTemp(package,curConflicts,
                                                   SubProgress(progress,
                                                               curFile,
                                                               curFile + len(
                                                                 curConflicts),
                                                               numFiles))
                            installer.getTempDir().moveTo(
                                installers_dir.join(destDir,GPath(
                                    u"%03d - %s" % (order,package.s))))
                            curFile += len(curConflicts)
                    project = destDir.root
                    if project not in data:
                        data[project] = bosh.InstallerProject(project)
                    iProject = data[project]
                    pProject = installers_dir.join(project)
                    iProject.refreshed = False
                    iProject.refreshBasic(pProject,None,True)
                    if iProject.order == -1:
                        data.moveArchives([project],srcInstaller.order + 1)
                    data.refresh(what='I')
                    self.gTank.RefreshUI()

# InstallerDetails Espm Links -------------------------------------------------
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
class Installer_Espm_SelectAll(InstallerLink):
    """Select All Esp/ms in installer for installation."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Select All'))
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
        menuItem = wx.MenuItem(menu,self.id,_(u'Deselect All'))
        menu.AppendItem(menuItem)
        if len(gInstallers.espms) == 0:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        espmNots = installer.espmNots = set()
        for i in range(len(gInstallers.espms)):
            gInstallers.gEspmList.Check(i, False)
            espm = GPath(gInstallers.gEspmList.GetString(i).replace(u'&&',u'&'))
            espmNots.add(espm)
        gInstallers.refreshCurrent(installer)

class Installer_Espm_Rename(InstallerLink):
    """Changes the installed name for an Esp/m."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Rename...'))
        menu.AppendItem(menuItem)
        if data == -1:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        curName = gInstallers.gEspmList.GetString(self.data).replace(u'&&',u'&')
        if curName[0] == u'*':
            curName = curName[1:]
        file = GPath(curName)
        newName = balt.askText(self.window,_(u"Enter new name (without the extension):"),
                               _(u"Rename Esp/m"), file.sbody)
        if not newName: return
        if newName in gInstallers.espms: return
        installer.setEspmName(curName,newName+file.cext)
        gInstallers.refreshCurrent(installer)

class Installer_Espm_Reset(InstallerLink):
    """Resets the installed name for an Esp/m."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Reset Name'))
        menu.AppendItem(menuItem)
        if data == -1:
            menuItem.Enable(False)
            return
        installer = gInstallers.data[gInstallers.detailsItem]
        curName = gInstallers.gEspmList.GetString(self.data).replace(u'&&',u'&')
        if curName[0] == u'*':
            curName = curName[1:]
        menuItem.Enable(installer.isEspmRenamed(curName))

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        curName = gInstallers.gEspmList.GetString(self.data).replace(u'&&',u'&')
        if curName[0] == u'*':
            curName = curName[1:]
        installer.resetEspmName(curName)
        gInstallers.refreshCurrent(installer)

class Installer_Espm_ResetAll(InstallerLink):
    """Resets all renamed Esp/ms."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Reset All Names'))
        menu.AppendItem(menuItem)
        if len(gInstallers.espms) == 0:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        installer.resetAllEspmNames()
        gInstallers.refreshCurrent(installer)

class Installer_Espm_List(InstallerLink):
    """Lists all Esp/ms in installer for user information/w/e."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'List Esp/ms'))
        menu.AppendItem(menuItem)
        if len(gInstallers.espms) == 0:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        subs = _(u'Esp/m List for %s:') % gInstallers.data[gInstallers.detailsItem].archive + u'\n[spoiler]\n'
        for index in range(gInstallers.gEspmList.GetCount()):
            subs += [u'   ',u'** '][gInstallers.gEspmList.IsChecked(index)] + gInstallers.gEspmList.GetString(index) + '\n'
        subs += u'[/spoiler]'
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(subs))
            wx.TheClipboard.Close()
        balt.showLog(self.window,subs,_(u'Esp/m List'),asDialog=False,fixedFont=False,icons=bashBlue)

# InstallerDetails Subpackage Links -------------------------------------------
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
class Installer_Subs_SelectAll(InstallerLink):
    """Select All sub-packages in installer for installation."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Select All'))
        menu.AppendItem(menuItem)
        if gInstallers.gSubList.GetCount() < 2:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        for index in xrange(gInstallers.gSubList.GetCount()):
            gInstallers.gSubList.Check(index, True)
            installer.subActives[index + 1] = True
        gInstallers.refreshCurrent(installer)

class Installer_Subs_DeselectAll(InstallerLink):
    """Deselect All sub-packages in installer for installation."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Deselect All'))
        menu.AppendItem(menuItem)
        if gInstallers.gSubList.GetCount() < 2:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        for index in xrange(gInstallers.gSubList.GetCount()):
            gInstallers.gSubList.Check(index, False)
            installer.subActives[index + 1] = False
        gInstallers.refreshCurrent(installer)

class Installer_Subs_ToggleSelection(InstallerLink):
    """Toggles selection state of all sub-packages in installer for installation."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Toggle Selection'))
        menu.AppendItem(menuItem)
        if gInstallers.gSubList.GetCount() < 2:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        for index in xrange(gInstallers.gSubList.GetCount()):
            check = not installer.subActives[index+1]
            gInstallers.gSubList.Check(index, check)
            installer.subActives[index + 1] = check
        gInstallers.refreshCurrent(installer)

class Installer_Subs_ListSubPackages(InstallerLink):
    """Lists all sub-packages in installer for user information/w/e."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'List Sub-packages'))
        menu.AppendItem(menuItem)
        if gInstallers.gSubList.GetCount() < 2:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        subs = _(u'Sub-Packages List for %s:') % installer.archive + u'\n[spoiler]\n'
        for index in xrange(gInstallers.gSubList.GetCount()):
            subs += [u'   ',u'** '][gInstallers.gSubList.IsChecked(index)] + gInstallers.gSubList.GetString(index) + u'\n'
        subs += u'[/spoiler]'
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(subs))
            wx.TheClipboard.Close()
        balt.showLog(self.window,subs,_(u'Sub-Package Lists'),asDialog=False,fixedFont=False,icons=bashBlue)
# InstallerArchive Links ------------------------------------------------------
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerArchive_Unpack(InstallerLink):
    """Install selected packages."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        if self.isSelectedArchives():
            self.title = _(u'Unpack to Project(s)...')
            menuItem = wx.MenuItem(menu,self.id,self.title)
            menu.AppendItem(menuItem)

    def Execute(self,event):
        if self.isSingleArchive():
            archive = self.selected[0]
            installer = self.data[archive]
            project = archive.root
            result = balt.askText(self.gTank,_(u"Unpack %s to Project:") % archive.s,
                self.title,project.s)
            result = (result or u'').strip()
            if not result: return
            #--Error checking
            project = GPath(result).tail
            if not project.s or project.cext in bosh.readExts:
                balt.showWarning(self.gTank,_(u"%s is not a valid project name.") % result)
                return
            if self.data.dir.join(project).isfile():
                balt.showWarning(self.gTank,_(u"%s is a file.") % project.s)
                return
            if project in self.data:
                if not balt.askYes(self.gTank,_(u"%s already exists. Overwrite it?") % project.s,self.title,False):
                    return
        #--Copy to Build
        with balt.Progress(_(u"Unpacking to Project..."),u'\n'+u' '*60) as progress:
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
                        if not balt.askYes(self.gTank,_(u"%s already exists. Overwrite it?") % project.s,self.title,False):
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
        wx.Frame.__init__(self,parent,wx.ID_ANY,_(u'Omod Config: ')+project.s,
            style=(wx.RESIZE_BORDER | wx.CAPTION | wx.CLIP_CHILDREN |wx.TAB_TRAVERSAL))
        self.SetIcons(bashBlue)
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

#------------------------------------------------------------------------------
class InstallerProject_OmodConfig(InstallerLink):
    """Install selected packages."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.title = _(u'Omod Info...')
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
        self.title = _(u'Sync from Data')
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
        message = (_(u'Update %s according to data directory?')
                   + u'\n' +
                   _(u'Files to delete:')
                   + u'%d\n' +
                   _(u'Files to update:')
                   + u'%d') % (project.s,len(missing),len(mismatched))
        if not balt.askWarning(self.gTank,message,self.title): return
        #--Sync it, baby!
        with balt.Progress(self.title,u'\n'+u' '*60) as progress:
            progress(0.1,_(u'Updating files.'))
            installer.syncToData(project,missing|mismatched)
            pProject = bosh.dirs['installers'].join(project)
            installer.refreshed = False
            installer.refreshBasic(pProject,SubProgress(progress,0.1,0.99),True)
            self.data.refresh(what='NS')
            self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class InstallerProject_SyncPack(InstallerLink):
    """Install selected packages."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Sync and Pack'))
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
            self.title = _(u'Pack to Archive...')
            menuItem = wx.MenuItem(menu,self.id,self.title)
            menu.AppendItem(menuItem)

    def Execute(self,event):
        #--Generate default filename from the project name and the default extension
        project = self.selected[0]
        installer = self.data[project]
        archive = bosh.GPath(project.s + bosh.defaultExt)
        #--Confirm operation
        result = balt.askText(self.gTank,_(u'Pack %s to Archive:') % project.s,
            self.title,archive.s)
        result = (result or u'').strip()
        if not result: return
        #--Error checking
        archive = GPath(result).tail
        if not archive.s:
            balt.showWarning(self.gTank,_(u'%s is not a valid archive name.') % result)
            return
        if self.data.dir.join(archive).isdir():
            balt.showWarning(self.gTank,_(u'%s is a directory.') % archive.s)
            return
        if archive.cext not in bosh.writeExts:
            balt.showWarning(self.gTank,_(u'The %s extension is unsupported. Using %s instead.') % (archive.cext, bosh.defaultExt))
            archive = GPath(archive.sroot + bosh.defaultExt).tail
        if archive in self.data:
            if not balt.askYes(self.gTank,_(u'%s already exists. Overwrite it?') % archive.s,self.title,False): return
        #--Archive configuration options
        blockSize = None
        if archive.cext in bosh.noSolidExts:
            isSolid = False
        else:
            if not u'-ms=' in bosh.inisettings['7zExtraCompressionArguments']:
                isSolid = balt.askYes(self.gTank,_(u'Use solid compression for %s?') % archive.s,self.title,False)
                if isSolid:
                    blockSize = balt.askNumber(self.gTank,
                        _(u'Use what maximum size for each solid block?')
                        + u'\n' +
                        _(u"Enter '0' to use 7z's default size.")
                        ,u'MB',self.title,0,0,102400)
            else: isSolid = True
        with balt.Progress(_(u'Packing to Archive...'),u'\n'+u' '*60) as progress:
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

#------------------------------------------------------------------------------
class InstallerProject_ReleasePack(InstallerLink):
    """Pack project to an archive for release. Ignores dev files/folders."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.title = _(u'Package for Release...')
        menuItem = wx.MenuItem(menu,self.id,self.title)
        menu.AppendItem(menuItem)
        menuItem.Enable(self.isSingleProject())

    def Execute(self,event):
        #--Generate default filename from the project name and the default extension
        project = self.selected[0]
        installer = self.data[project]
        archive = bosh.GPath(project.s + bosh.defaultExt)
        #--Confirm operation
        result = balt.askText(self.gTank,_(u"Pack %s to Archive:") % project.s,
            self.title,archive.s)
        result = (result or u'').strip()
        if not result: return
        #--Error checking
        archive = GPath(result).tail
        if not archive.s:
            balt.showWarning(self.gTank,_(u"%s is not a valid archive name.") % result)
            return
        if self.data.dir.join(archive).isdir():
            balt.showWarning(self.gTank,_(u"%s is a directory.") % archive.s)
            return
        if archive.cext not in bosh.writeExts:
            balt.showWarning(self.gTank,_(u"The %s extension is unsupported. Using %s instead.") % (archive.cext, bosh.defaultExt))
            archive = GPath(archive.sroot + bosh.defaultExt).tail
        if archive in self.data:
            if not balt.askYes(self.gTank,_(u"%s already exists. Overwrite it?") % archive.s,self.title,False): return
        #--Archive configuration options
        blockSize = None
        if archive.cext in bosh.noSolidExts:
            isSolid = False
        else:
            if not u'-ms=' in bosh.inisettings['7zExtraCompressionArguments']:
                isSolid = balt.askYes(self.gTank,_(u"Use solid compression for %s?") % archive.s,self.title,False)
                if isSolid:
                    blockSize = balt.askNumber(self.gTank,
                        _(u'Use what maximum size for each solid block?')
                        + u'\n' +
                        _(u"Enter '0' to use 7z's default size."),'MB',self.title,0,0,102400)
            else: isSolid = True
        with balt.Progress(_(u"Packing to Archive..."),u'\n'+u' '*60) as progress:
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

#------------------------------------------------------------------------------
class InstallerConverter_Apply(InstallerLink):
    """Apply a Bain Conversion File."""
    def __init__(self,converter,numAsterisks):
        InstallerLink.__init__(self)
        self.converter = converter
        #--Add asterisks to indicate the number of unselected archives that the BCF uses
        self.dispName = u''.join((self.converter.fullPath.sbody,u'*' * numAsterisks))

    def AppendToMenu(self,menu,window,data):
        InstallerLink.AppendToMenu(self,menu,window,data)
        self.title = _(u'Apply BCF...')
        menuItem = wx.MenuItem(menu,self.id,self.dispName)
        menu.AppendItem(menuItem)

    def Execute(self,event):
        #--Generate default filename from BCF filename
        result = self.converter.fullPath.sbody[:-4]
        #--List source archives
        message = _(u'Using:')+u'\n* '
        message += u'\n* '.join(sorted(u'(%08X) - %s' % (x,self.data.crc_installer[x].archive) for x in self.converter.srcCRCs)) + u'\n'
        #--Confirm operation
        result = balt.askText(self.gTank,message,self.title,result + bosh.defaultExt)
        result = (result or u'').strip()
        if not result: return
        #--Error checking
        destArchive = GPath(result).tail
        if not destArchive.s:
            balt.showWarning(self.gTank,_(u'%s is not a valid archive name.') % result)
            return
        if destArchive.cext not in bosh.writeExts:
            balt.showWarning(self.gTank,_(u'The %s extension is unsupported. Using %s instead.') % (destArchive.cext, bosh.defaultExt))
            destArchive = GPath(destArchive.sroot + bosh.defaultExt).tail
        if destArchive in self.data:
            if not balt.askYes(self.gTank,_(u'%s already exists. Overwrite it?') % destArchive.s,self.title,False): return
        with balt.Progress(_(u'Converting to Archive...'),u'\n'+u' '*60) as progress:
            #--Perform the conversion
            self.converter.apply(destArchive,self.data.crc_installer,SubProgress(progress,0.0,0.99))
            if hasattr(self.converter, 'hasBCF') and not self.converter.hasBCF:
                deprint(u'An error occued while attempting to apply an Auto-BCF:',traceback=True)
                balt.showWarning(self.gTank,
                    _(u'%s: An error occured while applying an Auto-BCF.' % destArchive.s))
                # hasBCF will be set to False if there is an error while
                # rearranging files
                return
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

#------------------------------------------------------------------------------
class InstallerConverter_ApplyEmbedded(InstallerLink):
    def AppendToMenu(self,menu,window,data):
        InstallerLink.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Embedded BCF'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        name = self.selected[0]
        archive = self.data[name]

        #--Ask for an output filename
        destArchive = balt.askText(self.gTank,_(u'Output file:'),_(u'Apply BCF...'),name.stail)
        destArchive = (destArchive if destArchive else u'').strip()
        if not destArchive: return
        destArchive = GPath(destArchive)

        #--Error checking
        if not destArchive.s:
            balt.showWarning(self.gTank,_(u'%s is not a valid archive name.') % destArchive.s)
            return
        if destArchive.cext not in bosh.writeExts:
            balt.showWarning(self.gTank,_(u'The %s extension is unsupported. Using %s instead.') % (destArchive.cext, bosh.defaultExt))
            destArchive = GPath(destArchive.sroot + bosh.defaultExt).tail
        if destArchive in self.data:
            if not balt.askYes(self.gTank,_(u'%s already exists. Overwrite it?') % destArchive.s,_(u'Apply BCF...'),False):
                return

        with balt.Progress(_(u'Extracting BCF...'),u'\n'+u' '*60) as progress:
            self.data.applyEmbeddedBCFs([archive],[destArchive],progress)
            iArchive = self.data[destArchive]
            if iArchive.order == -1:
                lastInstaller = self.data[self.selected[-1]]
                self.data.moveArchives([destArchive],lastInstaller.order+1)
            self.data.refresh(what='I')
            self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class InstallerConverter_ConvertMenu(balt.MenuLink):
    """Apply BCF SubMenu."""
    def AppendToMenu(self,menu,window,data):
        subMenu = wx.Menu()
        menu.AppendMenu(-1,self.name,subMenu)
        linkSet = set()
        #--Converters are linked by CRC, not archive name
        #--So, first get all the selected archive CRCs
        selected = window.GetSelected()
        selectedCRCs = set(window.data[archive].crc for archive in selected)
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
        #--If the archive is a single archive with an embedded BCF, add that
        if len(selected) == 1 and window.data[selected[0]].hasBCF:
            newMenu = InstallerConverter_ApplyEmbedded()
            newMenu.AppendToMenu(subMenu,window,data)
        #--Disable the menu if there were no valid converters found
        elif not linkSet:
            id = menu.FindItem(self.name)
            menu.Enable(id,False)
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
        self.title = _(u'Create BCF...')
        menuItem = wx.MenuItem(menu,self.id,_(u'Create...'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        #--Generate allowable targets
        readTypes = u'*%s' % u';*'.join(bosh.readExts)
        #--Select target archive
        destArchive = balt.askOpen(self.gTank,_(u"Select the BAIN'ed Archive:"),
                                   self.data.dir,u'', readTypes,mustExist=True)
        if not destArchive: return
        #--Error Checking
        BCFArchive = destArchive = destArchive.tail
        if not destArchive.s or destArchive.cext not in bosh.readExts:
            balt.showWarning(self.gTank,_(u'%s is not a valid archive name.') % destArchive.s)
            return
        if destArchive not in self.data:
            balt.showWarning(self.gTank,_(u'%s must be in the Bash Installers directory.') % destArchive.s)
            return
        if BCFArchive.csbody[-4:] != u'-bcf':
            BCFArchive = GPath(BCFArchive.sbody + u'-BCF' + bosh.defaultExt).tail
        #--List source archives and target archive
        message = _(u'Convert:')
        message += u'\n* ' + u'\n* '.join(sorted(u'(%08X) - %s' % (self.data[x].crc,x.s) for x in self.selected))
        message += (u'\n\n'+_(u'To:')+u'\n* (%08X) - %s') % (self.data[destArchive].crc,destArchive.s) + u'\n'
        #--Confirm operation
        result = balt.askText(self.gTank,message,self.title,BCFArchive.s)
        result = (result or u'').strip()
        if not result: return
        #--Error checking
        BCFArchive = GPath(result).tail
        if not BCFArchive.s:
            balt.showWarning(self.gTank,_(u'%s is not a valid archive name.') % result)
            return
        if BCFArchive.csbody[-4:] != u'-bcf':
            BCFArchive = GPath(BCFArchive.sbody + u'-BCF' + BCFArchive.cext).tail
        if BCFArchive.cext != bosh.defaultExt:
            balt.showWarning(self.gTank,_(u"BCF's only support %s. The %s extension will be discarded.") % (bosh.defaultExt, BCFArchive.cext))
            BCFArchive = GPath(BCFArchive.sbody + bosh.defaultExt).tail
        if bosh.dirs['converters'].join(BCFArchive).exists():
            if not balt.askYes(self.gTank,_(u'%s already exists. Overwrite it?') % BCFArchive.s,self.title,False): return
            #--It is safe to removeConverter, even if the converter isn't overwritten or removed
            #--It will be picked back up by the next refresh.
            self.data.removeConverter(BCFArchive)
        destInstaller = self.data[destArchive]
        blockSize = None
        if destInstaller.isSolid:
            blockSize = balt.askNumber(self.gTank,u'mb',
                _(u'Use what maximum size for each solid block?')
                + u'\n' +
                _(u"Enter '0' to use 7z's default size."),
                self.title,destInstaller.blockSize or 0,0,102400)
        progress = balt.Progress(_(u'Creating %s...') % BCFArchive.s,u'\n'+u' '*60)
        log = None
        try:
            #--Create the converter
            converter = bosh.InstallerConverter(self.selected, self.data, destArchive, BCFArchive, blockSize, progress)
            #--Add the converter to Bash
            self.data.addConverter(converter)
            #--Refresh UI
            self.data.refresh(what='C')
            #--Generate log
            log = bolt.LogFile(StringIO.StringIO())
            log.setHeader(u'== '+_(u'Overview')+u'\n')
##            log('{{CSS:wtxt_sand_small.css}}')
            log(u'. '+_(u'Name')+u': '+BCFArchive.s)
            log(u'. '+_(u'Size')+u': %s KB'% formatInteger(max(converter.fullPath.size,1024)/1024 if converter.fullPath.size else 0))
            log(u'. '+_(u'Remapped')+u': %s'%formatInteger(len(converter.convertedFiles))+(_(u'file'),_(u'files'))[len(converter.convertedFiles) > 1])
            log.setHeader(u'. '+_(u'Requires')+u': %s'%formatInteger(len(converter.srcCRCs))+(_(u'file'),_(u'files'))[len(converter.srcCRCs) > 1])
            log(u'  * '+u'\n  * '.join(sorted(u'(%08X) - %s' % (x, self.data.crc_installer[x].archive) for x in converter.srcCRCs if x in self.data.crc_installer)))
            log.setHeader(u'. '+_(u'Options:'))
            log(u'  * '+_(u'Skip Voices')+u'   = %s'%bool(converter.skipVoices))
            log(u'  * '+_(u'Solid Archive')+u' = %s'%bool(converter.isSolid))
            if converter.isSolid:
                if converter.blockSize:
                    log(u'    *  '+_(u'Solid Block Size')+u' = %d'%converter.blockSize)
                else:
                    log(u'    *  '+_(u'Solid Block Size')+u' = 7z default')
            log(u'  *  '+_(u'Has Comments')+u'  = %s'%bool(converter.comments))
            log(u'  *  '+_(u'Has Extra Directories')+u' = %s'%bool(converter.hasExtraData))
            log(u'  *  '+_(u'Has Esps Unselected')+u'   = %s'%bool(converter.espmNots))
            log(u'  *  '+_(u'Has Packages Selected')+u' = %s'%bool(converter.subActives))
            log.setHeader(u'. '+_(u'Contains')+u': %s'%formatInteger(len(converter.missingFiles))+ (_(u'file'),_(u'files'))[len(converter.missingFiles) > 1])
            log(u'  * '+u'\n  * '.join(sorted(u'%s' % x for x in converter.missingFiles)))
        finally:
            progress.Destroy()
            if log:
                balt.showLog(self.gTank, log.out.getvalue(), _(u'BCF Information'))

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
        self.data['Bethesda ESMs'] = [
            GPath(x) for x in bush.game.bethDataFiles
            if x.endswith(u'.esm')
            ]
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
                _(u'Name must be between 1 and 64 characters long.'))
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
        self.data['Bethesda ESMs'] = [
            GPath(x) for x in bush.game.bethDataFiles
            if x.endswith(u'.esm')
            ]

    def GetItems(self):
        items = self.data.keys()
        items.sort(lambda a,b: cmp(a.lower(),b.lower()))
        return items

    def SortWindow(self):
        self.window.PopulateItems()

    def AppendToMenu(self,menu,window,data):
        self.window = window
        menu.Append(ID_LOADERS.ALL,_(u'All'))
        menu.Append(ID_LOADERS.NONE,_(u'None'))
        menu.Append(ID_LOADERS.SAVE,_(u'Save List...'))
        menu.Append(ID_LOADERS.EDIT,_(u'Edit Lists...'))
        menu.AppendSeparator()
        for id,item in zip(ID_LOADERS,self.GetItems()):
            menu.Append(id,item)
        #--Disable Save?
        if not bosh.modInfos.ordered:
            menu.FindItemById(ID_LOADERS.SAVE).Enable(False)
        #--Events
        wx.EVT_MENU(bashFrame,ID_LOADERS.NONE,self.DoNone)
        wx.EVT_MENU(bashFrame,ID_LOADERS.ALL,self.DoAll)
        wx.EVT_MENU(bashFrame,ID_LOADERS.SAVE,self.DoSave)
        wx.EVT_MENU(bashFrame,ID_LOADERS.EDIT,self.DoEdit)
        wx.EVT_MENU_RANGE(bashFrame,ID_LOADERS.BASE,ID_LOADERS.MAX,self.DoList)

    def DoNone(self,event):
        """Unselect all mods."""
        bosh.modInfos.selectExact([])
        modList.RefreshUI()

    def DoAll(self,event):
        """Select all mods."""
        modInfos = bosh.modInfos
        try:
            # first select the bashed patch(es) and their masters
            for bashedPatch in [GPath(modName) for modName in modList.items if modInfos[modName].header.author in (u'BASHED PATCH',u'BASHED LISTS')]:
                if not modInfos.isSelected(bashedPatch):
                    modInfos.select(bashedPatch, False)
            # then activate mods that are not tagged NoMerge or Deactivate or Filter
            for mod in [GPath(modName) for modName in modList.items if modName not in modInfos.mergeable and u'Deactivate' not in modInfos[modName].getBashTags() and u'Filter' not in modInfos[modName].getBashTags()]:
                if not modInfos.isSelected(mod):
                    modInfos.select(mod, False)
            # then activate as many of the remaining mods as we can
            for mod in modInfos.mergeable:
                if u'Deactivate' in modInfos[mod].getBashTags(): continue
                if u'Filter' in modInfos[mod].getBashTags(): continue
                if not modInfos.isSelected(mod):
                    modInfos.select(mod, False)
            modInfos.plugins.save()
            modInfos.refreshInfoLists()
            modInfos.autoGhost()
        except bosh.PluginsFullError:
            balt.showError(self.window, _(u"Mod list is full, so some mods were skipped"), _(u'Select All'))
        modList.RefreshUI()

    def DoList(self,event):
        """Select mods in list."""
        item = self.GetItems()[event.GetId()-ID_LOADERS.BASE]
        selectList = [GPath(modName) for modName in modList.items if GPath(modName) in self.data[item]]
        errorMessage = bosh.modInfos.selectExact(selectList)
        modList.RefreshUI()
        if errorMessage:
            balt.showError(self.window,errorMessage,item)

    def DoSave(self,event):
        #--No slots left?
        if len(self.data) >= (ID_LOADERS.MAX - ID_LOADERS.BASE + 1):
            balt.showError(self,_(u'All load list slots are full. Please delete an existing load list before adding another.'))
            return
        #--Dialog
        newItem = (balt.askText(self.window,_(u'Save current load list as:'),u'Wrye Bash') or u'').strip()
        if not newItem: return
        if len(newItem) > 64:
            message = _(u'Load list name must be between 1 and 64 characters long.')
            return balt.showError(self.window,message)
        self.data[newItem] = bosh.modInfos.ordered[:]
        settings.setChanged('bash.loadLists.data')

    def DoEdit(self,event):
        data = Mods_LoadListData(self.window)
        dialog = balt.ListEditor(self.window,-1,_(u'Load Lists'),data)
        dialog.ShowModal()
        dialog.Destroy()

#------------------------------------------------------------------------------
class INI_SortValid(BoolLink):
    """Sort valid INI Tweaks to the top."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Valid Tweaks First'),
                                          'bash.ini.sortValid',
                                          _(u'Valid tweak files will be shown first.')
                                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        iniList.RefreshUI()

#------------------------------------------------------------------------------
class INI_AllowNewLines(BoolLink):
    """Consider INI Tweaks with new lines valid."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Allow Tweaks with New Lines'),
                                          'bash.ini.allowNewLines',
                                          _(u'Tweak files with new lines are considered valid..')
                                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        iniList.RefreshUI()

#------------------------------------------------------------------------------
class INI_ListINIs(Link):
    """List errors that make an INI Tweak invalid."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'List Active INIs...'),_(u'Lists all fully applied tweak files.'))
        menu.AppendItem(menuItem)
        menuItem.Enable(True)

    def Execute(self,event):
        """Handle printing out the errors."""
        text = iniList.ListTweaks()
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        balt.showLog(self.window,text,_(u'Active INIs'),asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class INI_ListErrors(Link):
    """List errors that make an INI Tweak invalid."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'List Errors...'),_(u'Lists any errors in the tweak file causing it to be invalid.'))
        menu.AppendItem(menuItem)

        bEnable = False
        for i in data:
            if bosh.iniInfos[i].getStatus() < 0:
                bEnable = True
                break
        menuItem.Enable(bEnable)

    def Execute(self,event):
        """Handle printing out the errors."""
        if wx.TheClipboard.Open():
            text = u''
            for i in self.data:
                fileInfo = bosh.iniInfos[i]
                text += u'%s\n' % fileInfo.listErrors()
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        balt.showLog(self.window,text,_(u'INI Tweak Errors'),asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class INI_FileOpenOrCopy(Link):
    """Open specified file(s) only if they aren't Bash supplied defaults."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        if not len(data) == 1:
            label = _(u'Open/Copy...')
            help = _(u'Only one INI file can be opened or copied at a time.')
        elif bosh.dirs['tweaks'].join(data[0]).isfile():
            label = _(u'Open...')
            help = _(u"Open '%s' with the system's default program.") % data[0]
        else:
            label = _(u'Copy...')
            help = _(u"Make an editable copy of the default tweak '%s'.") % data[0]
        menuItem = wx.MenuItem(menu,self.id,label,help)
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)>0 and len(data) == 1)

    def Execute(self,event):
        """Handle selection."""
        dir = self.window.data.dir
        for file in self.data:
            if bosh.dirs['tweaks'].join(file).isfile():
                dir.join(file).start()
            else:
                srcFile = bosh.iniInfos[file].dir.join(file)
                destFile = bosh.dirs['tweaks'].join(file)
                balt.shellMakeDirs(bosh.dirs['tweaks'],self.window)
                balt.shellCopy(srcFile,destFile,self.window,False,False,False)
                iniList.data.refresh()
                iniList.RefreshUI()

#------------------------------------------------------------------------------
class INI_Delete(Link):
    """Delete the file and all backups."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        if bosh.dirs['tweaks'].join(data[0]).isfile():
            menu.AppendItem(wx.MenuItem(menu,self.id,_(u'Delete'),
                help=_(u"Delete %(filename)s.") % ({'filename':data[0]})))
        else:
            menuItem = wx.MenuItem(menu,self.id,_(u'Delete'),
                help=_(u'Bash default tweaks can\'t be deleted.'))
            menu.AppendItem(menuItem)
            menuItem.Enable(False)

    def Execute(self,event):
        message = [u'',_(u'Uncheck files to skip deleting them if desired.')]
        message.extend(sorted(self.data))
        dialog = ListBoxes(self.window,_(u'Delete Files'),
                     _(u'Delete these files? This operation cannot be undone.'),
                     [message])
        if dialog.ShowModal() != wx.ID_CANCEL:
            id = dialog.ids[message[0]]
            checks = dialog.FindWindowById(id)
            if checks:
                for i,mod in enumerate(self.data):
                    if checks.IsChecked(i) and bosh.dirs['tweaks'].join(mod).isfile():
                        self.window.data.delete(mod)
            self.window.RefreshUI()
        dialog.Destroy()

#------------------------------------------------------------------------------
class INI_Apply(Link):
    """Apply an INI Tweak."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        ini = self.window.GetParent().GetParent().GetParent().comboBox.GetValue()
        tweak = data[0]
        menuItem = wx.MenuItem(menu,self.id,_(u'Apply'),_(u"Applies '%s' to '%s'.") % (tweak, ini))
        menu.AppendItem(menuItem)

        if not settings['bash.ini.allowNewLines']:
            for i in data:
                iniInfo = bosh.iniInfos[i]
                if iniInfo.status < 0:
                    menuItem.Enable(False) # temp disabled for testing
                    return

    def Execute(self,event):
        """Handle applying INI Tweaks."""
        #-- If we're applying to Oblivion.ini, show the warning
        iniPanel = self.window.GetParent().GetParent().GetParent()
        choice = iniPanel.GetChoice().tail
        if choice in bush.game.iniFiles:
            message = (_(u'Apply an ini tweak to %s?') % choice
                       + u'\n\n' +
                       _(u'WARNING: Incorrect tweaks can result in CTDs and even damage to your computer!')
                       )
            if not balt.askContinue(self.window,message,'bash.iniTweaks.continue',_(u'INI Tweaks')):
                return
        needsRefresh = False
        for item in self.data:
            #--No point applying a tweak that's already applied
            if bosh.iniInfos[item].status == 20: continue
            needsRefresh = True
            if bosh.dirs['tweaks'].join(item).isfile():
                iniList.data.ini.applyTweakFile(bosh.dirs['tweaks'].join(item))
            else:
                iniList.data.ini.applyTweakFile(bosh.dirs['defaultTweaks'].join(item))
        if needsRefresh:
            #--Refresh status of all the tweaks valid for this ini
            iniList.RefreshUI('VALID')
            iniPanel.iniContents.RefreshUI()
            iniPanel.tweakContents.RefreshUI(self.data[0])

#------------------------------------------------------------------------------
class INI_CreateNew(Link):
    """Create a new INI Tweak using the settings from the tweak file, but values from the target INI."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        ini = self.window.GetParent().GetParent().GetParent().comboBox.GetValue()
        tweak = data[0]
        menuItem = wx.MenuItem(menu,self.id,_(u'Create Tweak with current settings...'),_(u"Creates a new tweak based on '%s' but with values from '%s'.") % (tweak, ini))
        menu.AppendItem(menuItem)
        if len(data) != 1 or bosh.iniInfos[data[0]].status < 0:
            menuItem.Enable(False)

    def Execute(self,event):
        """Handle creating a new INI tweak."""
        pathFrom = self.data[0]
        fileName = pathFrom.sbody + u' - Copy' + pathFrom.ext
        path = balt.askSave(self.window,_(u'Copy Tweak with current settings...'),bosh.dirs['tweaks'],fileName,_(u'INI Tweak File (*.ini)|*.ini'))
        if not path: return
        bosh.iniInfos[pathFrom].dir.join(pathFrom).copyTo(path)
        # Now edit it with the values from the target INI
        iniList.data.refresh()
        oldTarget = iniList.data.ini
        target = bosh.BestIniFile(path)
        settings,deleted = target.getSettings()
        new_settings,deleted = oldTarget.getSettings()
        deleted = {}
        for section in settings:
            if section in new_settings:
                for setting in settings[section]:
                    if setting in new_settings[section]:
                        settings[section][setting] = new_settings[section][setting]
        target.saveSettings(settings)
        iniList.RefreshUI(detail=path)
        self.window.GetParent().GetParent().GetParent().tweakContents.RefreshUI(path.tail)

#------------------------------------------------------------------------------
class Mods_EsmsFirst(Link):
    """Sort esms to the top."""
    def __init__(self,prefix=u''):
        Link.__init__(self)
        self.prefix = prefix

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,self.prefix+_(u'Type'),_(u'Sort masters by type'),kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        menuItem.Check(window.esmsFirst)

    def Execute(self,event):
        self.window.esmsFirst = not self.window.esmsFirst
        self.window.PopulateItems()

#------------------------------------------------------------------------------
class Mods_SelectedFirst(Link):
    """Sort loaded mods to the top."""
    def __init__(self,prefix=u''):
        Link.__init__(self)
        self.prefix = prefix

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,self.prefix+_(u'Selection'),kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        if window.selectedFirst: menuItem.Check()

    def Execute(self,event):
        self.window.selectedFirst = not self.window.selectedFirst
        self.window.PopulateItems()

#------------------------------------------------------------------------------
class Mods_ScanDirty(BoolLink):
    """Read mod CRC's to check for dirty mods."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u"Check mods against BOSS's dirty mod list"),
                                          'bash.mods.scanDirty',
                                          )

    def Execute(self,event):
        BoolLink.Execute(self,event)
        self.window.PopulateItems()

#------------------------------------------------------------------------------
class Mods_AutoGhost(BoolLink):
    """Toggle Auto-ghosting."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Auto-Ghost'),
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
                                          _(u'Auto Group (Deprecated -- Please use BOSS instead)'),
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
        menuItem = wx.MenuItem(menu,self.id,_(u'Debug Mode'),kind=wx.ITEM_CHECK,
            help=_(u"Turns on extra debug prints to help debug an error or just for advanced testing."))
        menu.AppendItem(menuItem)
        menuItem.Check(bolt.deprintOn)

    def Execute(self,event):
        deprint(_(u'Debug Printing: Off'))
        bolt.deprintOn = not bolt.deprintOn
        deprint(_(u'Debug Printing: On'))

#------------------------------------------------------------------------------
class Mods_FullBalo(BoolLink):
    """Turn Full Balo off/on."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Full Balo (Deprecated -- Please use BOSS instead)'),
                                          'bash.balo.full',
                                          )

    def Execute(self,event):
        if not settings[self.key]:
            message = (_(u'Activate Full Balo?')
                       + u'\n\n' +
                       _(u'Full Balo segregates mods by groups, and then autosorts mods within those groups by alphabetical order.  Full Balo is still in development and may have some rough edges.')
                       )
            if balt.askContinue(self.window,message,'bash.balo.full.continue',_(u'Balo Groups')):
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
        if not hasattr(sys,'frozen'):
            # Can't dump the strings if the files don't exist.
            Link.AppendToMenu(self,menu,window,data)
            menuItem = wx.MenuItem(menu,self.id,_(u'Dump Translator'),
                help=_(u"Generate a new version of the translator file for your locale."))
            menu.AppendItem(menuItem)

    def Execute(self,event):
        message = (_(u'Generate Bash program translator file?')
                   + u'\n\n' +
                   _(u'This function is for translating Bash itself (NOT mods) into non-English languages.  For more info, see Internationalization section of Bash readme.')
                   )
        if not balt.askContinue(self.window,message,'bash.dumpTranslator.continue',_(u'Dump Translator')):
            return
        language = bass.language if bass.language else locale.getlocale()[0].split('_',1)[0]
        outPath = bosh.dirs['l10n']
        bashPath = GPath(u'bash')
        files = [bashPath.join(x+u'.py').s for x in (u'bolt',
                                                     u'balt',
                                                     u'bush',
                                                     u'bosh',
                                                     u'bash',
                                                     u'basher',
                                                     u'bashmon',
                                                     u'belt',
                                                     u'bish',
                                                     u'barg',
                                                     u'barb',
                                                     u'bass',
                                                     u'cint',
                                                     u'ScriptParser')]
        # Include Game files
        bashPath = bashPath.join(u'game')
        files.extend([bashPath.join(x).s for x in bosh.dirs['mopy'].join(u'bash','game').list() if x.cext == u'.py' and x != u'__init__.py'])
        with balt.BusyCursor():
            outFile = bolt.dumpTranslator(outPath.s,language,*files)
        balt.showOk(self.window,
            _(u'Translation keys written to ')+u'Mopy\\bash\\l10n\\'+outFile,
            _(u'Dump Translator')+u': '+outPath.stail)

#------------------------------------------------------------------------------
class Mods_ListMods(Link):
    """Copies list of mod files to clipboard."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u"List Mods..."),
            help=_(u"Copies list of active mod files to clipboard."))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        #--Get masters list
        text = bosh.modInfos.getModList(showCRC=wx.GetKeyState(67))
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        balt.showLog(self.window,text,_(u"Active Mod Files"),asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class Mods_ListBashTags(Link):
    """Copies list of bash tags to clipboard."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u"List Bash Tags..."),
            help=_(u"Copies list of bash tags to clipboard."))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        #--Get masters list
        text = bosh.modInfos.getTagList()
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        balt.showLog(self.window,text,_(u"Bash Tags"),asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class Mods_LockTimes(Link):
    """Turn on resetMTimes feature."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Lock Load Order'),kind=wx.ITEM_CHECK,
            help=_(u"Will reset mod Load Order to whatever Wrye Bash has saved for them whenever Wrye Bash refreshs data/starts up."))
        menu.AppendItem(menuItem)
        menuItem.Check(bosh.modInfos.lockLO)

    def Execute(self,event):
        lockLO = not bosh.modInfos.lockLO
        if not lockLO: bosh.modInfos.mtimes.clear()
        settings['bosh.modInfos.resetMTimes'] = bosh.modInfos.lockLO = lockLO
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
        menuItem.Enable(bosh.modInfos.voCurrent is not None and self.key in bosh.modInfos.voAvailable)
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
                                          _(u'Tes4Edit Expert'),
                                          'tes4View.iKnowWhatImDoing',
                                          )
#------------------------------------------------------------------------------
class Mods_Tes5ViewExpert(BoolLink):
    """Toggle Tes5Edit expert mode (when launched via Bash)."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Tes5Edit Expert'),
                                          'tes5View.iKnowWhatImDoing',
                                          )

#------------------------------------------------------------------------------
class Mods_BOSSDisableLockTimes(BoolLink):
    """Toggle Lock Load Order disabling when launching BOSS through Bash."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'BOSS Disable Lock Load Order'),
                                          'BOSS.ClearLockTimes',
                                          _(u"If selected, will temporarily disable Bash's Lock Load Order when running BOSS through Bash.")
                                          )

#------------------------------------------------------------------------------
class Mods_BOSSLaunchGUI(BoolLink):
    """If BOSS.exe is available then BOSS GUI.exe should be too."""
    def __init__(self): BoolLink.__init__(self,
                                          _(u'Launch using GUI'),
                                          'BOSS.UseGUI',
                                          _(u"If selected, Bash will run BOSS's GUI.")
                                          )

# Settings Links --------------------------------------------------------------
#------------------------------------------------------------------------------
class Settings_BackupSettings(Link):
    """Saves Bash's settings and user data.."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Backup Settings...'),
            help=_(u"Backup all of Wrye Bash's settings/data to an archive file."),
            kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)

    def Execute(self,event):
        def OnClickAll(event):
            dialog.EndModal(2)
        def OnClickNone(event):
            dialog.EndModal(1)
        def PromptConfirm(msg=None):
            msg = msg or _(u'Do you want to backup your Bash settings now?')
            return balt.askYes(bashFrame,msg,_(u'Backup Bash Settings?'))

        BashFrame.SaveSettings(bashFrame)
        #backup = barb.BackupSettings(bashFrame)
        try:
            if PromptConfirm():
                dialog = wx.Dialog(bashFrame,wx.ID_ANY,_(u'Backup Images?'),size=(400,200),style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
                icon = wx.StaticBitmap(dialog,wx.ID_ANY,wx.ArtProvider_GetBitmap(wx.ART_WARNING,wx.ART_MESSAGE_BOX, (32,32)))
                sizer = vSizer(
                    (hSizer(
                        (icon,0,wx.ALL,6),
                        (staticText(dialog,_(u'Do you want to backup any images?'),style=wx.ST_NO_AUTORESIZE),1,wx.EXPAND|wx.LEFT,6),
                        ),1,wx.EXPAND|wx.ALL,6),
                    (hSizer(
                        spacer,
                        button(dialog,label=_(u'Backup All Images'),onClick=OnClickAll),
                        (button(dialog,label=_(u'Backup Changed Images'),onClick=OnClickNone),0,wx.LEFT,4),
                        (button(dialog,id=wx.ID_CANCEL,label=_(u'None')),0,wx.LEFT,4),
                        ),0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,6),
                    )
                dialog.SetSizer(sizer)
                backup = barb.BackupSettings(bashFrame,backup_images=dialog.ShowModal())
                backup.Apply()
        except StateError:
            backup.WarnFailed()
        except barb.BackupCancelled:
            pass
        #end try
        backup = None

#------------------------------------------------------------------------------
class Settings_RestoreSettings(Link):
    """Saves Bash's settings and user data.."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Restore Settings...'),
            help=_(u"Restore all of Wrye Bash's settings/data from a backup archive file."),
            kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)

    def Execute(self,event):
        try:
            backup = barb.RestoreSettings(bashFrame)
            if backup.PromptConfirm():
                backup.restore_images = balt.askYes(bashFrame,
                    _(u'Do you want to restore saved images as well as settings?'),
                    _(u'Restore Settings'))
                backup.Apply()
        except barb.BackupCancelled: #cancelled
            pass
        #end try
        backup = None

#------------------------------------------------------------------------------
class Settings_SaveSettings(Link):
    """Saves Bash's settings and user data."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Save Settings'),
            help=_(u"Save all of Wrye Bash's settings/data now."),
            kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)

    def Execute(self,event):
        BashFrame.SaveSettings(bashFrame)

#------------------------------------------------------------------------------
class Settings_ExportDllInfo(Link):
    """Exports list of good and bad dll's."""
    def AppendToMenu(self,menu,window,data):
        if not bush.game.se_sd: return
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,
            _(u"Export list of allowed/disallowed %s plugin dlls") % bush.game.se_sd,
            _(u"Export list of allowed/disallowed plugin dlls to a txt file (for BAIN)."))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,
            _(u'Export list of allowed/disallowed %s plugin dlls to:') % bush.game.se_sd,
            textDir, bush.game.se.shortName+u' '+_(u'dll permissions')+u'.txt',
            u'*.txt')
        if not textPath: return
        with textPath.open('w',encoding='utf-8-sig') as out:
            out.write(u'goodDlls '+_(u'(those dlls that you have chosen to allow to be installed)')+u'\r\n')
            if settings['bash.installers.goodDlls']:
                for dll in settings['bash.installers.goodDlls']:
                    out.write(u'dll:'+dll+u':\r\n')
                    for index, version in enumerate(settings['bash.installers.goodDlls'][dll]):
                        out.write(u'version %02d: %s\r\n' % (index, version))
            else: out.write(u'None\r\n')
            out.write(u'badDlls '+_(u'(those dlls that you have chosen to NOT allow to be installed)')+u'\r\n')
            if settings['bash.installers.badDlls']:
                for dll in settings['bash.installers.badDlls']:
                    out.write(u'dll:'+dll+u':\r\n')
                    for index, version in enumerate(settings['bash.installers.badDlls'][dll]):
                        out.write(u'version %02d: %s\r\n' % (index, version))
            else: out.write(u'None\r\n')

#------------------------------------------------------------------------------
class Settings_ImportDllInfo(Link):
    """Imports list of good and bad dll's."""
    def AppendToMenu(self,menu,window,data):
        if not bush.game.se_sd: return
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,
            _(u"Import list of allowed/disallowed %s plugin dlls") % bush.game.se_sd,
            help=_(u"Import list of allowed/disallowed plugin dlls from a txt file (for BAIN)."))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askOpen(self.window,
            _(u'Import list of allowed/disallowed %s plugin dlls from:') % bush.game.se_sd,
            textDir, bush.game.se.shortName+u' '+_(u'dll permissions')+u'.txt',
            u'*.txt',mustExist=True)
        if not textPath: return
        message = (_(u'Merge permissions from file with current dll permissions?')
                   + u'\n' +
                   _(u"('No' Replaces current permissions instead.)")
                   )
        if not balt.askYes(self.window,message,_(u'Merge permissions?')): replace = True
        else: replace = False
        try:
            with textPath.open('r',encoding='utf-8-sig') as ins:
                Dlls = {'goodDlls':{},'badDlls':{}}
                for line in ins:
                    line = line.strip()
                    if line.startswith(u'goodDlls'):
                        current = Dlls['goodDlls']
                    if line.startswith(u'badDlls'):
                        current = Dlls['badDlls']
                    elif line.startswith(u'dll:'):
                        dll = line.split(u':',1)[1].strip()
                        current.setdefault(dll,[])
                    elif line.startswith(u'version'):
                        ver = line.split(u':',1)[1]
                        ver = eval(ver)
                        current[dll].append(ver)
                        print dll,':',ver
            if not replace:
                settings['bash.installers.goodDlls'].update(Dlls['goodDlls'])
                settings['bash.installers.badDlls'].update(Dlls['badDlls'])
            else:
                settings['bash.installers.goodDlls'], settings['bash.installers.badDlls'] = Dlls['goodDlls'], Dlls['badDlls']
        except UnicodeError:
            balt.showError(self.window,_(u'Wrye Bash could not load %s, because it is not saved in UTF-8 format.  Please resave it in UTF-8 format and try again.') % textPath.s)
        except Exception as e:
            deprint(u'Error reading', textPath.s, traceback=True)
            balt.showError(self.window,_(u'Wrye Bash could not load %s, because there was an error in the format of the file.') % textPath.s)

#------------------------------------------------------------------------------
class Settings_Colors(Link):
    """Shows the color configuration dialog."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Colors...'),
            help=_(u"Configure the custom colors used in the UI."))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        dialog = ColorDialog(bashFrame)
        dialog.ShowModal()
        dialog.Destroy()

#------------------------------------------------------------------------------
class Settings_Tab(Link):
    """Handle hiding/unhiding tabs."""
    def __init__(self,tabKey,canDisable=True):
        Link.__init__(self)
        self.tabKey = tabKey
        self.enabled = canDisable

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        className,title,item = tabInfo.get(self.tabKey,[None,None,None])
        if title is None: return
        help = _(u"Show/Hide the %s Tab.") % title
        check = settings['bash.tabs'][self.tabKey]
        menuItem = wx.MenuItem(menu,self.id,title,kind=wx.ITEM_CHECK,help=help)
        menu.AppendItem(menuItem)
        menuItem.Check(check)
        menuItem.Enable(self.enabled)

    def Execute(self,event):
        if settings['bash.tabs'][self.tabKey]:
            # It was enabled, disable it.
            iMods = None
            iInstallers = None
            iDelete = None
            for i in range(bashFrame.notebook.GetPageCount()):
                pageTitle = bashFrame.notebook.GetPageText(i)
                if pageTitle == tabInfo['Mods'][1]:
                    iMods = i
                elif pageTitle == tabInfo['Installers'][1]:
                    iInstallers = i
                if pageTitle == tabInfo[self.tabKey][1]:
                    iDelete = i
            if iDelete == bashFrame.notebook.GetSelection():
                # We're deleting the current page...
                if ((iDelete == 0 and iInstallers == 1) or
                    (iDelete - 1 == iInstallers)):
                    # The auto-page change will change to
                    # the 'Installers' tab.  Change to the
                    # 'Mods' tab instead.
                    bashFrame.notebook.SetSelection(iMods)
            page = bashFrame.notebook.GetPage(iDelete)
            bashFrame.notebook.RemovePage(iDelete)
            page.Show(False)
        else:
            # It was disabled, enable it
            insertAt = 0
            for i,key in enumerate(settings['bash.tabs.order']):
                if key == self.tabKey: break
                if settings['bash.tabs'][key]:
                    insertAt = i+1
            className,title,panel = tabInfo[self.tabKey]
            if not panel:
                panel = globals()[className](bashFrame.notebook)
                tabInfo[self.tabKey][2] = panel
            if insertAt > bashFrame.notebook.GetPageCount():
                bashFrame.notebook.AddPage(panel,title)
            else:
                bashFrame.notebook.InsertPage(insertAt,panel,title)
        settings['bash.tabs'][self.tabKey] ^= True
        settings.setChanged('bash.tabs')

#------------------------------------------------------------------------------
class Settings_IconSize(Link):
    def __init__(self, size):
        Link.__init__(self)
        self.size = size

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,unicode(self.size),kind=wx.ITEM_RADIO,
            help=_(u"Sets the status bar icons to %(size)s pixels") % ({'size':unicode(self.size)}))
        menu.AppendItem(menuItem)
        menuItem.Check(self.size == settings['bash.statusbar.iconSize'])

    def Execute(self,event):
        settings['bash.statusbar.iconSize'] = self.size
        bashFrame.GetStatusBar().UpdateIconSizes()

#------------------------------------------------------------------------------
class Settings_StatusBar_ShowVersions(Link):
    """Show/Hide version numbers for buttons on the statusbar."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Show App Version'),kind=wx.ITEM_CHECK,
            help=_(u"Show/hide version numbers for buttons on the status bar."))
        menu.AppendItem(menuItem)
        menuItem.Check(settings['bash.statusbar.showversion'])

    def Execute(self,event):
        settings['bash.statusbar.showversion'] ^= True
        for button in BashStatusBar.buttons:
            if isinstance(button, App_Button):
                if button.gButton:
                    button.gButton.SetToolTip(tooltip(button.tip))
        if settings['bash.obse.on']:
            for button in App_Button.obseButtons:
                button.gButton.SetToolTip(tooltip(getattr(button,'obseTip',u'')))

#------------------------------------------------------------------------------
class Settings_Languages(Link):
    """Menu for available Languages."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        languages = []
        for file in bosh.dirs['l10n'].list():
            if file.cext == u'.txt' and file.csbody[-3:] != u'new':
                languages.append(file.body)
        if languages:
            subMenu = wx.Menu()
            menu.AppendMenu(self.id,_(u'Language'),subMenu)
            for language in languages:
                Settings_Language(language.s).AppendToMenu(subMenu,window,data)
            if GPath('english') not in languages:
                Settings_Language('English').AppendToMenu(subMenu,window,data)
        else:
            menuItem = wx.MenuItem(menu,self.id,_(u'Language'),
                help=_("Wrye Bash was unable to detect any translation files."))
            menu.AppendItem(menuItem)
            menuItem.Enable(False)

#------------------------------------------------------------------------------
class Settings_Language(Link):
    """Specific language for Wrye Bash."""
    languageMap = {
        u'chinese (simplified)': _(u'Chinese (Simplified)') + u' (简体中文)',
        u'chinese (traditional)': _(u'Chinese (Traditional)') + u' (繁体中文)',
        u'de': _(u'German') + u' (Deutsch)',
        u'pt_opt': _(u'Portuguese') + u' (português)',
        u'italian': _(u'Italian') + u' (italiano)',
        u'russian': _(u'Russian') + u' (ру́сский язы́к)',
        u'english': _(u'English') + u' (English)',
        }

    def __init__(self,language):
        Link.__init__(self)
        self.language = language

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        label = self.__class__.languageMap.get(self.language.lower(),self.language)
        bassLang = bass.language if bass.language else locale.getlocale()[0].split('_',1)[0]
        if self.language == bassLang:
            menuItem = wx.MenuItem(menu,self.id,label,kind=wx.ITEM_RADIO,
                help=_("Currently using %(languagename)s as the active language.") % ({'languagename':label}))
        else:
            menuItem = wx.MenuItem(menu,self.id,label,
                help=_("Restart Wrye Bash and use %(languagename)s as the active language.") % ({'languagename':label}))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        bassLang = bass.language if bass.language else locale.getlocale()[0].split('_',1)[0]
        if self.language == bassLang: return
        if balt.askYes(bashFrame,
                       _(u'Wrye Bash needs to restart to change languages.  Do you want to restart?'),
                       _(u'Restart Wrye Bash')):
            bashFrame.Restart(('--Language',self.language))

#------------------------------------------------------------------------------
class Settings_PluginEncodings(Link):
    encodings = {
        'gbk': _(u'Chinese (Simplified)'),
        'big5': _(u'Chinese (Traditional)'),
        'cp1251': _(u'Russian'),
        'cp932': _(u'Japanese'),
        'cp1252': _(u'Western European (English, French, German, etc)'),
        }
    def __init__(self):
        Link.__init__(self)
        bolt.pluginEncoding = settings['bash.pluginEncoding']

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        subMenu = wx.Menu()
        menu.AppendMenu(self.id,_(u'Plugin Encoding'),subMenu)
        Settings_PluginEncoding(_(u'Automatic'),None).AppendToMenu(subMenu,window,data)
        SeparatorLink().AppendToMenu(subMenu,window,data)
        enc_name = sorted(Settings_PluginEncodings.encodings.items(),key=lambda x: x[1])
        for encoding,name in enc_name:
            Settings_PluginEncoding(name,encoding).AppendToMenu(subMenu,window,data)

#------------------------------------------------------------------------------
class Settings_PluginEncoding(Link):
    def __init__(self,name,encoding):
        Link.__init__(self)
        self.name = name
        self.encoding = encoding

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        if self.encoding == settings['bash.pluginEncoding']:
            menuItem = wx.MenuItem(menu,self.id,self.name,kind=wx.ITEM_RADIO,
                help=_("Select %(encodingname)s encoding for Wrye Bash to use.") % ({'encodingname':self.name}))
        else:
            menuItem = wx.MenuItem(menu,self.id,self.name,
                help=_("Select %(encodingname)s encoding for Wrye Bash to use.") % ({'encodingname':self.name}))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        settings['bash.pluginEncoding'] = self.encoding
        bolt.pluginEncoding = self.encoding

#------------------------------------------------------------------------------
class Settings_Games(Link):
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        foundGames,allGames,name = bush.detectGames()
        subMenu = wx.Menu()
        menu.AppendMenu(self.id,_(u'Game'),subMenu)
        for game in foundGames:
            game = game[0].upper()+game[1:]
            Settings_Game(game).AppendToMenu(subMenu,window,data)

class Settings_Game(Link):
    def __init__(self,game):
        Link.__init__(self)
        self.game = game

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,self.game,kind=wx.ITEM_RADIO,
            help=_("Restart Wrye Bash to manage %(game)s.") % ({'game':self.game}))
        menu.AppendItem(menuItem)
        if self.game.lower() == bush.game.fsName.lower():
            menuItem.Check(True)

    def Execute(self,event):
        if self.game.lower() == bush.game.fsName.lower(): return
        bashFrame.Restart(('--game',self.game))

#------------------------------------------------------------------------------
class Settings_UnHideButtons(Link):
    """Menu to unhide a StatusBar button."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        hide = settings['bash.statusbar.hide']
        hidden = []
        for link in BashStatusBar.buttons:
            if link.uid in hide:
                hidden.append(link)
        if hidden:
            subMenu = wx.Menu()
            menu.AppendMenu(self.id,_(u'Unhide Buttons'),subMenu)
            for link in hidden:
                Settings_UnHideButton(link).AppendToMenu(subMenu,window,data)
        else:
            menuItem = wx.MenuItem(menu,self.id,_(u'Unhide Buttons'),
                help=_(u"No hidden buttons available to unhide."))
            menu.AppendItem(menuItem)
            menuItem.Enable(False)

#------------------------------------------------------------------------------
class Settings_UnHideButton(Link):
    """Unhide a specific StatusBar button."""
    def __init__(self,link):
        Link.__init__(self)
        self.link = link

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        button = self.link.gButton
        # Get a title for the hidden button
        if button:
            # If the wx.Button object exists (it was hidden this session),
            # Use the tooltip from it
            tip = button.GetToolTip().GetTip()
        else:
            # If the link is an App_Button, it will have a 'tip' attribute
            tip = getattr(self.link,'tip',None)
        if tip is None:
            # No good, use it's uid as a last resort
            tip = self.link.uid
        help = _(u"Unhide the '%s' status bar button.") % tip
        menuItem = wx.MenuItem(menu,self.id,tip,help)
        menu.AppendItem(menuItem)

    def Execute(self,event):
        bashFrame.GetStatusBar().UnhideButton(self.link)

#------------------------------------------------------------------------------
class Settings_UseAltName(BoolLink):
    def __init__(self): BoolLink.__init__(
        self,_(u'Use Alternate Wrye Bash Name'),
        'bash.useAltName',
        _(u'Use an alternate display name for Wrye Bash based on the game it is managing.'))

    def Execute(self,event):
        BoolLink.Execute(self,event)
        bashFrame.SetTitle()

#------------------------------------------------------------------------------
class Settings_UAC(Link):
    def AppendToMenu(self,menu,window,data):
        if not isUAC:
            return
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Administrator Mode'),
                               help=_(u'Restart Wrye Bash with administrator privileges.'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        if balt.askYes(bashFrame,
                       _(u'Restart Wrye Bash with administrator privileges?'),
                       _(u'Administrator Mode'),
                       ):
            bashFrame.Restart(True,True)

# StatusBar Links--------------------------------------------------------------
#------------------------------------------------------------------------------
class StatusBar_Hide(Link):
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        tip = window.GetToolTip().GetTip()
        menuItem = wx.MenuItem(menu,self.id,_(u"Hide '%s'") % tip,
                help=_(u"Hides %(buttonname)s's status bar button (can be restored through the settings menu).") % ({'buttonname':tip}))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        sb = bashFrame.GetStatusBar()
        sb.HideButton(self.window)

# Mod Links -------------------------------------------------------------------
#------------------------------------------------------------------------------
from patcher.utilities import ActorLevels, CBash_ActorLevels

class Mod_ActorLevels_Export(Link):
    """Export actor levels from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'NPC Levels...'),
                help=_(u"Export NPC level info from mod to text file."))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        message = (_(u'This command will export the level info for NPCs whose level is offset with respect to the PC.  The exported file can be edited with most spreadsheet programs and then reimported.')
                   + u'\n\n' +
                   _(u'See the Bash help file for more info.'))
        if not balt.askContinue(self.window,message,
                'bash.actorLevels.export.continue',
                _(u'Export NPC Levels')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_NPC_Levels.csv'
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_(u'Export NPC levels to:'),textDir,
                                textName, u'*_NPC_Levels.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        with balt.Progress(_(u'Export Factions')) as progress:
            if CBash:
                actorLevels = CBash_ActorLevels()
            else:
                actorLevels = ActorLevels()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_(u'Reading')+u' '+fileName.s)
                actorLevels.readFromMod(fileInfo)
            progress(0.8,_(u'Exporting to')+u' '+textName.s+u'.')
            actorLevels.writeToText(textPath)
            progress(1.0,_(u'Done.'))

#------------------------------------------------------------------------------
class Mod_ActorLevels_Import(Link):
    """Imports actor levels from text file to mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'NPC Levels...'),
                help=_(u"Import NPC level info from text fiile to mod"))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = (_(u'This command will import NPC level info from a previously exported file.')
                   + u'\n\n' +
                   _(u'See the Bash help file for more info.'))
        if not balt.askContinue(self.window,message,
                'bash.actorLevels.import.continue',
                _(u'Import NPC Levels')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_NPC_Levels.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import NPC levels from:'),
            textDir,textName,u'*_NPC_Levels.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != u'.csv':
            balt.showError(self.window,_(u'Source file must be a _NPC_Levels.csv file.'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u'Import NPC Levels')) as progress:
            if CBash:
                actorLevels = CBash_ActorLevels()
            else:
                actorLevels = ActorLevels()
            progress(0.1,_(u'Reading')+u' '+textName.s+u'.')
            actorLevels.readFromText(textPath)
            progress(0.2,_(u'Applying to')+u' '+fileName.s+u'.')
            changed = actorLevels.writeToMod(fileInfo)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed:
            balt.showOk(self.window,_(u'No relevant NPC levels to import.'),
                        _(u'Import NPC Levels'))
        else:
            buff = StringIO.StringIO()
            buff.write(u'* %03d  %s\n' % (changed, fileName.s))
            balt.showLog(self.window,buff.getvalue(),_(u'Import NPC Levels'),
                         icons=bashBlue)

#------------------------------------------------------------------------------
class MasterList_AddMasters(Link):
    """Adds a master."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Add Masters...'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        message = _(u"WARNING!  For advanced modders only!  Adds specified master to list of masters, thus ceding ownership of new content of this mod to the new master.  Useful for splitting mods into esm/esp pairs.")
        if not balt.askContinue(self.window,message,'bash.addMaster.continue',_(u'Add Masters')):
            return
        modInfo = self.window.fileInfo
        wildcard = bush.game.displayName+u' '+_(u'Masters')+u' (*.esm;*.esp)|*.esm;*.esp'
        masterPaths = balt.askOpenMulti(self.window,_(u'Add masters:'),
                        modInfo.dir, u'', wildcard)
        if not masterPaths: return
        names = []
        for masterPath in masterPaths:
            (dir,name) = masterPath.headTail
            if dir != modInfo.dir:
                return balt.showError(self.window,
                    _(u"File must be selected from %s Data Files directory.")
                    % bush.game.fsName)
            if name in modInfo.header.masters:
                return balt.showError(self.window,
                    name.s+u' '+_(u"is already a master."))
            names.append(name)
        for masterName in bosh.modInfos.getOrdered(names, asTuple=False):
            if masterName in bosh.modInfos:
                masterName = bosh.modInfos[masterName].name
            modInfo.header.masters.append(masterName)
        modInfo.header.changed = True
        self.window.SetFileInfo(modInfo)
        self.window.InitEdit()

#------------------------------------------------------------------------------
class MasterList_CleanMasters(Link):
    """Remove unneeded masters."""
    def AppendToMenu(self,menu,window,data):
        if not settings['bash.CBashEnabled']: return
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Clean Masters...'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        message = _(u"WARNING!  For advanced modders only!  Removes masters that are not referenced in any records.")
        if not balt.askContinue(self.window,message,'bash.cleanMaster.continue',
                                _(u'Clean Masters')):
            return
        modInfo = self.window.fileInfo
        path = modInfo.getPath()

        with ObCollection(ModsPath=bosh.dirs['mods'].s) as Current:
            modFile = Current.addMod(path.stail)
            Current.load()
            oldMasters = modFile.TES4.masters
            cleaned = modFile.CleanMasters()

            if cleaned:
                newMasters = modFile.TES4.masters
                removed = [GPath(x) for x in oldMasters if x not in newMasters]
                removeKey = _(u'Masters')
                group = [removeKey,
                              _(u'These master files are not referenced within the mod, and can safely be removed.'),
                              ]
                group.extend(removed)
                checklists = [group]
                dialog = ListBoxes(bashFrame,_(u'Remove these masters?'),
                                        _(u'The following master files can be safely removed.'),
                                        checklists)
                if dialog.ShowModal() == wx.ID_CANCEL:
                    dialog.Destroy()
                    return
                id = dialog.ids[removeKey]
                checks = dialog.FindWindowById(id)
                if checks:
                    for i,mod in enumerate(removed):
                        if not checks.IsChecked(i):
                            newMasters.append(mod)

                modFile.TES4.masters = newMasters
                modFile.save()
                dialog.Destroy()
                deprint(u'to remove:', removed)
            else:
                balt.showOk(self.window,_(u'No Masters to clean.'),
                            _(u'Clean Masters'))

#------------------------------------------------------------------------------
class Mod_FullLoad(Link):
    """Tests all record definitions against a specific mod"""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Test Full Record Definitions...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data)==1)

    def Execute(self,event):
        fileName = GPath(self.data[0])
        with balt.Progress(_(u'Loading:')+u'\n%s'%fileName.stail) as progress:
            print bosh.MreRecord.type_class
            readClasses = bosh.MreRecord.type_class
            print readClasses.values()
            loadFactory = bosh.LoadFactory(False, *readClasses.values())
            modFile = bosh.ModFile(bosh.modInfos[fileName],loadFactory)
            try:
                modFile.load(True,progress)
            except:
                deprint('execption:\n', traceback=True)

#------------------------------------------------------------------------------
class Mod_AddMaster(Link):
    """Adds master."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Add Master...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data)==1)

    def Execute(self,event):
        message = _(u"WARNING! For advanced modders only! Adds specified master to list of masters, thus ceding ownership of new content of this mod to the new master. Useful for splitting mods into esm/esp pairs.")
        if not balt.askContinue(self.window,message,'bash.addMaster.continue',_(u'Add Master')):
            return
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        wildcard = _(u'%s Masters')%bush.game.displayName+u' (*.esm;*.esp)|*.esm;*.esp'
        masterPaths = balt.askOpenMulti(self.window,_(u'Add master:'),fileInfo.dir, u'', wildcard)
        if not masterPaths: return
        names = []
        for masterPath in masterPaths:
            (dir,name) = masterPath.headTail
            if dir != fileInfo.dir:
                return balt.showError(self.window,
                    _(u"File must be selected from %s Data Files directory.") % bush.game.fsName)
            if name in fileInfo.header.masters:
                return balt.showError(self.window,_(u"%s is already a master!") % name.s)
            names.append(name)
        # actually do the modification
        for masterName in bosh.modInfos.getOrdered(names, asTuple=False):
            if masterName in bosh.modInfos:
                #--Avoid capitalization errors by getting the actual name from modinfos.
                masterName = bosh.modInfos[masterName].name
            fileInfo.header.masters.append(masterName)
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
        menu.Append(self.idList.EDIT,_(u'Edit...'))
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
        menuItem = wx.MenuItem(menu,self.id,_(u"Allow Ghosting"))
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
class Mod_CreateBOSSReport(Link):
    """Copies appropriate information for making a report in the BOSS thread."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u"Create BOSS Report..."))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data) != 1 or (not bosh.reOblivion.match(self.data[0].s)))

    def Execute(self,event):
        text = u''
        if len(self.data) > 5:
            spoiler = True
            text += u'[spoiler]\n'
        else:
            spoiler = False
        # Scan for ITM and UDR's
        modInfos = [bosh.modInfos[x] for x in self.data]
        try:
            with balt.Progress(_(u"Dirty Edits"),u'\n'+u' '*60,abort=True) as progress:
                udr_itm_fog = bosh.ModCleaner.scan_Many(modInfos,progress=progress)
        except bolt.CancelError:
            return
        # Create the report
        for i,fileName in enumerate(self.data):
            if fileName == u'Oblivion.esm': continue
            fileInfo = bosh.modInfos[fileName]
            #-- Name of file, plus a link if we can figure it out
            installer = bosh.modInfos.table.getItem(fileName,'installer',u'')
            if not installer:
                text += fileName.s
            else:
                # Try to get the url of the file
                # Order of priority will be:
                #  TESNexus
                #  TESAlliance
                url = None
                ma = bosh.reTesNexus.search(installer)
                if ma and ma.group(2):
                    url = bush.game.nexusUrl+u'downloads/file.php?id='+ma.group(2)
                if not url:
                    ma = bosh.reTESA.search(installer)
                    if ma and ma.group(2):
                        url = u'http://tesalliance.org/forums/index.php?app=downloads&showfile='+ma.group(2)
                if url:
                    text += u'[url='+url+u']'+fileName.s+u'[/url]'
                else:
                    text += fileName.s
            #-- Version, if it exists
            version = bosh.modInfos.getVersion(fileName)
            if version:
                text += u'\n'+_(u'Version')+u': %s' % version
            #-- CRC
            text += u'\n'+_(u'CRC')+u': %08X' % fileInfo.cachedCrc()
            #-- Dirty edits
            if udr_itm_fog:
                udrs,itms,fogs = udr_itm_fog[i]
                if udrs or itms:
                    if settings['bash.CBashEnabled']:
                        text += (u'\nUDR: %i, ITM: %i '+_(u'(via Wrye Bash)')) % (len(udrs),len(itms))
                    else:
                        text += (u'\nUDR: %i, ITM not scanned '+_(u'(via Wrye Bash)')) % len(udrs)
            text += u'\n\n'
        if spoiler: text += u'[/spoiler]'

        # Show results + copy to clipboard
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        balt.showLog(self.window,text,_(u'BOSS Report'),asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_CopyModInfo(Link):
    """Copies the basic info about selected mod(s)."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Copy Mod Info...'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        text = u''
        if len(self.data) > 5:
            spoiler = True
            text += u'[spoiler]'
        else:
            spoiler = False
        # Create the report
        isFirst = True
        for i,fileName in enumerate(self.data):
            # add a blank line in between mods
            if isFirst: isFirst = False
            else: text += u'\n\n'
            fileInfo = bosh.modInfos[fileName]
            #-- Name of file, plus a link if we can figure it out
            installer = bosh.modInfos.table.getItem(fileName,'installer',u'')
            if not installer:
                text += fileName.s
            else:
                # Try to get the url of the file
                # Order of priority will be:
                #  TESNexus
                #  TESAlliance
                url = None
                ma = bosh.reTesNexus.search(installer)
                if ma and ma.group(2):
                    url = bush.game.nexusUrl+u'downloads/file.php?id='+ma.group(2)
                if not url:
                    ma = bosh.reTESA.search(installer)
                    if ma and ma.group(2):
                        url = u'http://tesalliance.org/forums/index.php?app=downloads&showfile='+ma.group(2)
                if url:
                    text += u'[url=%s]%s[/url]' % (url, fileName.s)
                else:
                    text += fileName.s
            for col in settings['bash.mods.cols']:
                if col == 'File': continue
                elif col == 'Rating':
                    value = bosh.modInfos.table.getItem(fileName,'rating',u'')
                elif col == 'Group':
                    value = bosh.modInfos.table.getItem(fileName,'group',u'')
                elif col == 'Installer':
                    value = bosh.modInfos.table.getItem(fileName,'installer', u'')
                elif col == 'Modified':
                    value = formatDate(fileInfo.mtime)
                elif col == 'Size':
                    value = formatInteger(max(fileInfo.size,1024)/1024 if fileInfo.size else 0)+u' KB'
                elif col == 'Author' and fileInfo.header:
                    value = fileInfo.header.author
                elif col == 'Load Order':
                    ordered = bosh.modInfos.ordered
                    if fileName in ordered:
                        value = u'%02X' % list(ordered).index(fileName)
                    else:
                        value = u''
                elif col == 'CRC':
                    value = u'%08X' % fileInfo.cachedCrc()
                elif col == 'Mod Status':
                    value = fileInfo.txt_status()
                text += u'\n%s: %s' % (col, value)
            #-- Version, if it exists
            version = bosh.modInfos.getVersion(fileName)
            if version:
                text += u'\n'+_(u'Version')+u': %s' % version
        if spoiler: text += u'[/spoiler]'

        # Show results + copy to clipboard
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        balt.showLog(self.window,text,_(u'Mod Info Report'),asDialog=False,
                     fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_ListBashTags(Link):
    """Copies list of bash tags to clipboard."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u"List Bash Tags..."))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        #--Get masters list
        files = []
        for fileName in self.data:
            files.append(bosh.modInfos[fileName])
        text = bosh.modInfos.getTagList(files)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        balt.showLog(self.window,text,_(u"Bash Tags"),asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_AllowNoGhosting(Link):
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u"Disallow Ghosting"))
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
class Mod_Ghost(Link):
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u"Ghost"))
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
class Mod_AllowInvertGhosting(Link):
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u"Invert Ghosting"))
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
            menuItem = wx.MenuItem(menu,self.id,_(u"Don't Ghost"),kind=wx.ITEM_CHECK)
            menu.AppendItem(menuItem)
            self.allowGhosting = bosh.modInfos.table.getItem(data[0],'allowGhosting',True)
            menuItem.Check(not self.allowGhosting)
        else:
            subMenu = wx.Menu()
            menu.AppendMenu(-1,_(u"Ghosting"),subMenu)
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
            menuItem = wx.MenuItem(menu,self.id,_(u"Don't check against LOOT's dirty mod list"),kind=wx.ITEM_CHECK)
        else:
            menuItem = wx.MenuItem(menu,self.id,_(u"Check against LOOT's dirty mod list"),kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        for fileName in self.data:
            if bosh.modInfos.table.getItem(fileName,'ignoreDirty',self.skip) != self.skip:
                menuItem.Check(False)
                break
        else: menuItem.Check(True)

    def Execute(self,event):
        for fileName in self.data:
            fileInfo = bosh.modInfos[fileName]
            bosh.modInfos.table.setItem(fileName,'ignoreDirty',self.skip)
        self.window.RefreshUI(self.data)

#------------------------------------------------------------------------------
class Mod_SkipDirtyCheckInvert(Link):
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u"Invert checking against LOOT's dirty mod list"))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        for fileName in self.data:
            fileInfo = bosh.modInfos[fileName]
            ignoreDiry = bosh.modInfos.table.getItem(fileName,'ignoreDirty',False) ^ True
            bosh.modInfos.table.setItem(fileName,'ignoreDirty',ignoreDiry)
        self.window.RefreshUI(self.data)

#------------------------------------------------------------------------------
class Mod_SkipDirtyCheck(Link):
    """Toggles scanning for dirty mods on a per-mod basis."""

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        if len(data) == 1:
            menuItem = wx.MenuItem(menu,self.id,_(u"Don't check against LOOT's dirty mod list"),kind=wx.ITEM_CHECK)
            menu.AppendItem(menuItem)
            self.ignoreDirty = bosh.modInfos.table.getItem(data[0],'ignoreDirty',False)
            menuItem.Check(self.ignoreDirty)
        else:
            subMenu = wx.Menu()
            menu.AppendMenu(-1,_(u"Dirty edit scanning"),subMenu)
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
        menuItem = wx.MenuItem(menu,self.id,_(u'Nvidia Fog Fix'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        message = _(u'Apply Nvidia fog fix.  This modify fog values in interior cells to avoid the Nvidia black screen bug.')
        if not balt.askContinue(self.window,message,'bash.cleanMod.continue',
            _(u'Nvidia Fog Fix')):
            return
        with balt.Progress(_(u'Nvidia Fog Fix')) as progress:
            progress.setFull(len(self.data))
            fixed = []
            for index,fileName in enumerate(map(GPath,self.data)):
                if fileName.cs in bush.game.masterFiles: continue
                progress(index,_(u'Scanning')+fileName.s)
                fileInfo = bosh.modInfos[fileName]
                cleanMod = bosh.CleanMod(fileInfo)
                cleanMod.clean(SubProgress(progress,index,index+1))
                if cleanMod.fixedCells:
                    fixed.append(u'* %4d %s' % (len(cleanMod.fixedCells),fileName.s))
        if fixed:
            message = u'==='+_(u'Cells Fixed')+u':\n'+u'\n'.join(fixed)
            balt.showWryeLog(self.window,message,_(u'Nvidia Fog Fix'),
                             icons=bashBlue)
        else:
            message = _(u'No changes required.')
            balt.showOk(self.window,message,_(u'Nvidia Fog Fix'))

#------------------------------------------------------------------------------
class Mod_CreateBlankBashedPatch(Link):
    """Create a new bashed patch."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'New Bashed Patch...'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        newPatchName = bosh.PatchFile.generateNextBashedPatch(self.window)
        if newPatchName is not None:
            self.window.RefreshUI(detail=newPatchName)

#------------------------------------------------------------------------------
class Mod_CreateBlank(Link):
    """Create a new blank mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'New Mod...'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        data = self.window.GetSelected()
        fileInfos = self.window.data
        count = 0
        newName = GPath(u'New Mod.esp')
        while newName in fileInfos:
            count += 1
            newName = GPath(u'New Mod %d.esp' % count)
        newInfo = fileInfos.factory(fileInfos.dir,newName)
        if data:
            newTime = max(fileInfos[x].mtime for x in data)
        else:
            newTime = max(fileInfos[x].mtime for x in fileInfos.data)
        newInfo.mtime = fileInfos.getFreeTime(newTime,newTime)
        newFile = bosh.ModFile(newInfo,bosh.LoadFactory(True))
        newFile.tes4.masters = [GPath(bush.game.masterFiles[0])]
        newFile.safeSave()
        mod_group = fileInfos.table.getColumn('group')
        mod_group[newName] = mod_group.get(newName,u'')
        bosh.modInfos.refresh()
        self.window.RefreshUI(detail=newName)

#------------------------------------------------------------------------------
class Mod_CreateDummyMasters(Link):
    """TES4Edit tool, makes dummy plugins for each missing master, for use if looking at a 'Filter' patch."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Create Dummy Masters...'))
        if len(data) == 1 and bosh.modInfos[data[0]].getStatus() == 30: # Missing masters
            menuItem.Enable(True)
        else:
            menuItem.Enable(False)
        menu.AppendItem(menuItem)

    def Execute(self,event):
        """Handle execution."""
        if not balt.askYes(self.window,
                           _(u"This is an advanced feature for editing 'Filter' patches in TES4Edit.  It will create dummy plugins for each missing master.  Are you sure you want to continue?")
                           + u'\n\n' +
                           _(u"To remove these files later, use 'Clean Dummy Masters...'"),
                           _(u'Create Files')):
            return
        doCBash = False #settings['bash.CBashEnabled'] - something odd's going on, can't rename temp names
        modInfo = bosh.modInfos[self.data[0]]
        lastTime = modInfo.mtime - 1
        if doCBash:
            newFiles = []
        refresh = []
        for master in modInfo.header.masters:
            if master in bosh.modInfos:
                lastTime = bosh.modInfos[master].mtime
                continue
            # Missing master, create a dummy plugin for it
            newInfo = bosh.ModInfo(modInfo.dir,master)
            newTime = lastTime
            newInfo.mtime = bosh.modInfos.getFreeTime(newTime,newTime)
            refresh.append(master)
            if doCBash:
                # TODO: CBash doesn't handle unicode.  Make this make temp unicode safe
                # files, then rename them to the correct unicode name later
                newFiles.append(newInfo.getPath().stail)
            else:
                newFile = bosh.ModFile(newInfo,bosh.LoadFactory(True))
                newFile.tes4.author = u'BASHED DUMMY'
                newFile.safeSave()
        if doCBash:
            with ObCollection(ModsPath=bosh.dirs['mods'].s) as Current:
                tempname = u'_DummyMaster.esp.tmp'
                modFile = Current.addMod(tempname, CreateNew=True)
                Current.load()
                modFile.TES4.author = u'BASHED DUMMY'
                for newFile in newFiles:
                    modFile.save(CloseCollection=False,DestinationName=newFile)
        bashFrame.RefreshData()
        self.window.RefreshUI()

class Mods_CleanDummyMasters(Link):
    """Clean up after using a 'Create Dummy Masters...' command"""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Remove Dummy Masters...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(False)
        for fileName in bosh.modInfos.data:
            fileInfo = bosh.modInfos[fileName]
            if fileInfo.header.author == u'BASHED DUMMY':
                menuItem.Enable(True)
                break

    def Execute(self,event):
        """Handle execution."""
        remove = []
        for fileName in bosh.modInfos.data:
            fileInfo = bosh.modInfos[fileName]
            if fileInfo.header.author == u'BASHED DUMMY':
                remove.append(fileName)
        remove = bosh.modInfos.getOrdered(remove)
        message = [u'',_(u'Uncheck items to skip deleting them if desired.')]
        message.extend(remove)
        dialog = ListBoxes(bashFrame,_(u'Delete Dummy Masters'),
                     _(u'Delete these items? This operation cannot be undone.'),
                     [message])
        if dialog.ShowModal() == wx.ID_CANCEL:
            dialog.Destroy()
            return
        id = dialog.ids[u'']
        checks = dialog.FindWindowById(id)
        if checks:
            for i,mod in enumerate(remove):
                if checks.IsChecked(i):
                    self.window.data.delete(mod)
        dialog.Destroy()
        bashFrame.RefreshData()
        self.window.RefreshUI()

#------------------------------------------------------------------------------
from patcher.utilities import FactionRelations, CBash_FactionRelations

class Mod_FactionRelations_Export(Link):
    """Export faction relations from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Relations...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Relations.csv'
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_(u'Export faction relations to:'),
                                textDir,textName, u'*_Relations.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        with balt.Progress(_(u'Export Relations')) as progress:
            if CBash:
                factionRelations = CBash_FactionRelations()
            else:
                factionRelations = FactionRelations()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_(u'Reading')+u' '+fileName.s+u'.')
                factionRelations.readFromMod(fileInfo)
            progress(0.8,_(u'Exporting to')+u' '+textName.s+u'.')
            factionRelations.writeToText(textPath)
            progress(1.0,_(u'Done.'))

#------------------------------------------------------------------------------
class Mod_FactionRelations_Import(Link):
    """Imports faction relations from text file to mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Relations...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = (_(u"This command will import faction relation info from a previously exported file.")
                   + u'\n\n' +
                   _(u"See the Bash help file for more info."))
        if not balt.askContinue(self.window,message,
                'bash.factionRelations.import.continue',_(u'Import Relations')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Relations.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import faction relations from:'),
            textDir, textName, u'*_Relations.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != u'.csv':
            balt.showError(self.window,_(u'Source file must be a _Relations.csv file.'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u'Import Relations')) as progress:
            if CBash:
                factionRelations = CBash_FactionRelations()
            else:
                factionRelations = FactionRelations()
            progress(0.1,_(u'Reading')+u' '+textName.s+u'.')
            factionRelations.readFromText(textPath)
            progress(0.2,_(u'Applying to')+u' '+fileName.s+u'.')
            changed = factionRelations.writeToMod(fileInfo)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed:
            balt.showOk(self.window,
                _(u'No relevant faction relations to import.'),
                _(u'Import Relations'))
        else:
            buff = StringIO.StringIO()
            buff.write(u'* %03d  %s\n' % (changed, fileName.s))
            text = buff.getvalue()
            buff.close()
            balt.showLog(self.window,text,_(u'Import Relations'),icons=bashBlue)

#------------------------------------------------------------------------------
from patcher.utilities import ActorFactions, CBash_ActorFactions

class Mod_Factions_Export(Link):
    """Export factions from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Factions...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Factions.csv'
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_(u'Export factions to:'),textDir,
                                textName, u'*_Factions.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        with balt.Progress(_(u'Export Factions')) as progress:
            if CBash:
                actorFactions = CBash_ActorFactions()
            else:
                actorFactions = ActorFactions()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_(u'Reading')+u' '+fileName.s+u'.')
                actorFactions.readFromMod(fileInfo)
            progress(0.8,_(u'Exporting to ')+u' '+textName.s+u'.')
            actorFactions.writeToText(textPath)
            progress(1.0,_(u'Done.'))

#------------------------------------------------------------------------------
class Mod_Factions_Import(Link):
    """Imports factions from text file to mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Factions...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = (_(u"This command will import faction ranks from a previously exported file.")
                   + u'\n\n' +
                   _(u'See the Bash help file for more info.'))
        if not balt.askContinue(self.window,message,
                'bash.factionRanks.import.continue',_(u'Import Factions')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Factions.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import Factions from:'),
            textDir, textName, u'*_Factions.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != u'.csv':
            balt.showError(self.window,
                _(u'Source file must be a _Factions.csv file.'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u'Import Factions')) as progress:
            if CBash:
                actorFactions = CBash_ActorFactions()
            else:
                actorFactions = ActorFactions()
            progress(0.1,_(u'Reading')+u' '+textName.s+u'.')
            actorFactions.readFromText(textPath)
            progress(0.2,_(u'Applying to')+u' '+fileName.s+u'.')
            changed = actorFactions.writeToMod(fileInfo)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed:
            balt.showOk(self.window,_(u'No relevant faction ranks to import.'),
                        _(u'Import Factions'))
        else:
            buff = StringIO.StringIO()
            for groupName in sorted(changed):
                buff.write(u'* %s : %03d  %s\n' % (groupName,changed[groupName],fileName.s))
            text = buff.getvalue()
            buff.close()
            balt.showLog(self.window,text,_(u'Import Factions'),icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_MarkLevelers(Link):
    """Marks (tags) selected mods as Delevs and/or Relevs according to Leveled Lists.csv."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Mark Levelers...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(data))

    def Execute(self,event):
        message = _(u'Obsolete. Mods are now automatically tagged when possible.')
        balt.showInfo(self.window,message,_(u'Mark Levelers'))

#------------------------------------------------------------------------------
class Mod_MarkMergeable(Link):
    """Returns true if can act as patch mod."""
    def __init__(self,doCBash):
        Link.__init__(self)
        self.doCBash = doCBash

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        if self.doCBash:
            title = _(u'Mark Mergeable (CBash)...')
        else:
            title = _(u'Mark Mergeable...')
        menuItem = wx.MenuItem(menu,self.id,title)
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(data))

    def Execute(self,event):
        yes,no = [],[]
        mod_mergeInfo = bosh.modInfos.table.getColumn('mergeInfo')
        for fileName in map(GPath,self.data):
            if not self.doCBash and bosh.reOblivion.match(fileName.s): continue
            fileInfo = bosh.modInfos[fileName]
            if self.doCBash:
                if fileName == u"Oscuro's_Oblivion_Overhaul.esp":
                    reason = u'\n.    '+_(u'Marked non-mergeable at request of mod author.')
                else:
                    reason = bosh.CBash_PatchFile.modIsMergeable(fileInfo,True)
            else:
                reason = bosh.PatchFile.modIsMergeable(fileInfo,True)

            if reason == True:
                mod_mergeInfo[fileName] = (fileInfo.size,True)
                yes.append(fileName)
            else:
                if (u'\n.    '+_(u"Has 'NoMerge' tag.")) in reason:
                    mod_mergeInfo[fileName] = (fileInfo.size,True)
                else:
                    mod_mergeInfo[fileName] = (fileInfo.size,False)
                no.append(u"%s:%s" % (fileName.s,reason))
        message = u'== %s ' % ([u'Python',u'CBash'][self.doCBash])+_(u'Mergeability')+u'\n\n'
        if yes:
            message += u'=== '+_(u'Mergeable')+u'\n* '+u'\n\n* '.join(x.s for x in yes)
        if yes and no:
            message += u'\n\n'
        if no:
            message += u'=== '+_(u'Not Mergeable')+u'\n* '+'\n\n* '.join(no)
        self.window.RefreshUI(yes)
        self.window.RefreshUI(no)
        if message != u'':
            balt.showWryeLog(self.window,message,_(u'Mark Mergeable'),icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_CopyToEsmp(Link):
    """Create an esp(esm) copy of selected esm(esp)."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        fileInfo = bosh.modInfos[data[0]]
        isEsm = fileInfo.isEsm()
        self.label = _(u'Copy to Esp') if fileInfo.isEsm() else _(u'Copy to Esm')
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
            newType = (fileInfo.isEsm() and u'esp') or u'esm'
            modsDir = fileInfo.dir
            curName = fileInfo.name
            newName = curName.root+u'.'+newType
            #--Replace existing file?
            if modsDir.join(newName).exists():
                if not balt.askYes(self.window,_(u'Replace existing %s?') % (newName.s,),self.label):
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
        menuItem = wx.MenuItem(menu,self.id,_(u'Face...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) == 1)

    def Execute(self,event):
        #--Select source face file
        srcDir = bosh.saveInfos.dir
        wildcard = _(u'%s Files')%bush.game.displayName+u' (*.ess;*.esr)|*.ess;*.esr'
        #--File dialog
        srcPath = balt.askOpen(self.window,_(u'Face Source:'),srcDir, u'', wildcard,mustExist=True)
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
        imagePath = bosh.modInfos.dir.join(u'Docs',u'Images',npc.eid+u'.jpg')
        if not imagePath.exists():
            srcInfo.getHeader()
            width,height,data = srcInfo.header.image
            image = wx.EmptyImage(width,height)
            image.SetData(data)
            imagePath.head.makedirs()
            image.SaveFile(imagePath.s,wx.BITMAP_TYPE_JPEG)
        self.window.RefreshUI()
        balt.showOk(self.window,_(u'Imported face to: %s') % npc.eid,fileName.s)

#------------------------------------------------------------------------------
class Mod_FlipMasters(Link):
    """Swaps masters between esp and esm versions."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Esmify Masters'))
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
                    menuItem.SetText(_(u'Espify Masters'))
                    self.toEsm = False
                    break
            else:
                self.toEsm = True
            menuItem.Enable(True)

    def Execute(self,event):
        message = _(u"WARNING! For advanced modders only! Flips esp/esm bit of esp masters to convert them to/from esm state. Useful for building/analyzing esp mastered mods.")
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
        self.label = _(u'Espify Self') if isEsm else _(u'Esmify Self')
        menuItem = wx.MenuItem(menu,self.id,self.label)
        menu.AppendItem(menuItem)
        for item in data:
            fileInfo = bosh.modInfos[item]
            if fileInfo.isEsm() != isEsm or not item.cext[-1] == u'p':
                menuItem.Enable(False)
                return

    def Execute(self,event):
        message = (_(u'WARNING! For advanced modders only!')
                   + u'\n\n' +
                   _(u'This command flips an internal bit in the mod, converting an esp to an esm and vice versa.  Note that it is this bit and NOT the file extension that determines the esp/esm state of the mod.')
                   )
        if not balt.askContinue(self.window,message,'bash.flipToEsmp.continue',_(u'Flip to Esm')):
            return
        for item in self.data:
            fileInfo = bosh.modInfos[item]
            header = fileInfo.header
            header.flags1.esm = not header.flags1.esm
            fileInfo.writeHeader()
            #--Repopulate
            bosh.modInfos.refresh(doInfos=False)
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
            balt.showError(self.parent,_(u'Name must be unique.'))
            return False
        elif len(newName) == 0 or len(newName) > 64:
            balt.showError(self.parent,
                _(u'Name must be between 1 and 64 characters long.'))
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
                _(u'Name must be between 1 and 64 characters long.'))
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
        menu.Append(self.idList.NONE,_(u'None'))
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
            fileLabels[fileName] = u''
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
        self.editMenu   = _(u'Edit Groups...')
        self.editWindow = _(u'Groups')
        self.addPrompt  = _(u'Add group:')
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
        menuItem = wx.MenuItem(menu,self.id,_(u'Groups...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = u'My_Groups.csv'
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_(u'Export groups to:'),textDir,textName, u'*_Groups.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        modGroups = bosh.ModGroups()
        modGroups.readFromModInfos(self.data)
        modGroups.writeToText(textPath)
        balt.showOk(self.window,
            _(u"Exported %d mod/groups.") % (len(modGroups.mod_group),),
            _(u"Export Groups"))

#------------------------------------------------------------------------------
class Mod_Groups_Import(Link):
    """Import editor ids from text file or other mod."""
    def AppendToMenu(self,menu,window,data):
        data = bosh.ModGroups.filter(data)
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Groups...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        message = _(u"Import groups from a text file. Any mods that are moved into new auto-sorted groups will be immediately reordered.")
        if not balt.askContinue(self.window,message,'bash.groups.import.continue',
            _(u'Import Groups')):
            return
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import names from:'),textDir,
            u'', u'*_Groups.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        if textName.cext != u'.csv':
            balt.showError(self.window,_(u'Source file must be a csv file.'))
            return
        #--Import
        modGroups = bosh.ModGroups()
        modGroups.readFromText(textPath)
        changed = modGroups.writeToModInfos(self.data)
        bosh.modInfos.refresh()
        self.window.RefreshUI()
        balt.showOk(self.window,
            _(u"Imported %d mod/groups (%d changed).") % (len(modGroups.mod_group),changed),
            _(u"Import Groups"))

#------------------------------------------------------------------------------
from patcher.utilities import EditorIds, CBash_EditorIds

class Mod_EditorIds_Export(Link):
    """Export editor ids from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Editor Ids...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Eids.csv'
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_(u'Export eids to:'),textDir,textName, u'*_Eids.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        with balt.Progress(_(u"Export Editor Ids")) as progress:
            if CBash:
                editorIds = CBash_EditorIds()
            else:
                editorIds = EditorIds()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_(u"Reading %s.") % (fileName.s,))
                editorIds.readFromMod(fileInfo)
            progress(0.8,_(u"Exporting to %s.") % (textName.s,))
            editorIds.writeToText(textPath)
            progress(1.0,_(u"Done."))

#------------------------------------------------------------------------------
class Mod_EditorIds_Import(Link):
    """Import editor ids from text file or other mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Editor Ids...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = (_(u"Import editor ids from a text file. This will replace existing ids and is not reversible!"))
        if not balt.askContinue(self.window,message,'bash.editorIds.import.continue',
            _(u'Import Editor Ids')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Eids.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import names from:'),textDir,
            textName, u'*_Eids.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        if textName.cext != u'.csv':
            balt.showError(self.window,_(u'Source file must be a csv file.'))
            return
        #--Import
        questionableEidsSet = set()
        badEidsList = []
        try:
            changed = None
            with balt.Progress(_(u"Import Editor Ids")) as progress:
                if CBash:
                    editorIds = CBash_EditorIds()
                else:
                    editorIds = EditorIds()
                progress(0.1,_(u"Reading %s.") % (textName.s,))
                editorIds.readFromText(textPath,questionableEidsSet,badEidsList)
                progress(0.2,_(u"Applying to %s.") % (fileName.s,))
                changed = editorIds.writeToMod(fileInfo)
                progress(1.0,_(u"Done."))
            #--Log
            if not changed:
                balt.showOk(self.window,_(u"No changes required."))
            else:
                buff = StringIO.StringIO()
                format = u"%s'%s' >> '%s'\n"
                for old,new in sorted(changed):
                    if new in questionableEidsSet:
                        prefix = u'* '
                    else:
                        prefix = u''
                    buff.write(format % (prefix,old,new))
                if questionableEidsSet:
                    buff.write(u'\n* '+_(u'These editor ids begin with numbers and may therefore cause the script compiler to generate unexpected results')+u'\n')
                if badEidsList:
                    buff.write(u'\n'+_(u'The following EIDs are malformed and were not imported:')+u'\n')
                    for badEid in badEidsList:
                        buff.write(u"  '%s'\n" % badEid)
                text = buff.getvalue()
                buff.close()
                balt.showLog(self.window,text,_(u'Objects Changed'),icons=bashBlue)
        except bolt.BoltError as e:
            balt.showWarning(self.window,'%'%e)

#------------------------------------------------------------------------------
class Mod_DecompileAll(Link):
    """Removes effects of a "recompile all" on the mod."""

    def AppendToMenu(self,menu,window,data):
        """Append link to a menu."""
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Decompile All'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data) != 1 or (not bosh.reOblivion.match(self.data[0].s)))


    def Execute(self,event):
        message = _(u"This command will remove the effects of a 'compile all' by removing all scripts whose texts appear to be identical to the version that they override.")
        if not balt.askContinue(self.window,message,'bash.decompileAll.continue',_(u'Decompile All')):
            return
        for item in self.data:
            fileName = GPath(item)
            if bosh.reOblivion.match(fileName.s):
                balt.showWarning(self.window,_(u"Skipping %s") % fileName.s,_(u'Decompile All'))
                continue
            fileInfo = bosh.modInfos[fileName]
            loadFactory = bosh.LoadFactory(True,bosh.MreRecord.type_class['SCPT'])
            modFile = bosh.ModFile(fileInfo,loadFactory)
            modFile.load(True)
            badGenericLore = False
            removed = []
            id_text = {}
            if modFile.SCPT.getNumRecords(False):
                loadFactory = bosh.LoadFactory(False,bosh.MreRecord.type_class['SCPT'])
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
                balt.showOk(self.window,
                            (_(u'Scripts removed: %d.')
                             + u'\n' +
                             _(u'Scripts remaining: %d')
                             ) % (len(removed),len(modFile.SCPT.records)),
                            fileName.s)
            elif removed:
                balt.showOk(self.window,_(u"Only %d scripts were identical.  This is probably intentional, so no changes have been made.") % len(removed),fileName.s)
            else:
                balt.showOk(self.window,_(u"No changes required."),fileName.s)

#------------------------------------------------------------------------------
from patcher.utilities import FidReplacer, CBash_FidReplacer

class Mod_Fids_Replace(Link):
    """Replace fids according to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Form IDs...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = _(u"For advanced modders only! Systematically replaces one set of Form Ids with another in npcs, creatures, containers and leveled lists according to a Replacers.csv file.")
        if not balt.askContinue(self.window,message,'bash.formIds.replace.continue',
            _(u'Import Form IDs')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Form ID mapper file:'),textDir,
            u'', u'*_Formids.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        if textName.cext != u'.csv':
            balt.showError(self.window,_(u'Source file must be a csv file.'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u"Import Form IDs")) as progress:
            if CBash:
                replacer = CBash_FidReplacer()
            else:
                replacer = FidReplacer()
            progress(0.1,_(u"Reading %s.") % textName.s)
            replacer.readFromText(textPath)
            progress(0.2,_(u"Applying to %s.") % fileName.s)
            changed = replacer.updateMod(fileInfo)
            progress(1.0,_(u"Done."))
        #--Log
        if not changed:
            balt.showOk(self.window,_(u"No changes required."))
        else:
            balt.showLog(self.window,changed,_(u'Objects Changed'),icons=bashBlue)

#------------------------------------------------------------------------------
from patcher.utilities import FullNames, CBash_FullNames

class Mod_FullNames_Export(Link):
    """Export full names from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Names...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Names.csv'
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_(u'Export names to:'),
            textDir,textName, u'*_Names.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        with balt.Progress(_(u"Export Names")) as progress:
            if CBash:
                fullNames = CBash_FullNames()
            else:
                fullNames = FullNames()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_(u"Reading %s.") % fileName.s)
                fullNames.readFromMod(fileInfo)
            progress(0.8,_(u"Exporting to %s.") % textName.s)
            fullNames.writeToText(textPath)
            progress(1.0,_(u"Done."))

#------------------------------------------------------------------------------
class Mod_FullNames_Import(Link):
    """Import full names from text file or other mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Names...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = (_(u"Import record names from a text file. This will replace existing names and is not reversible!"))
        if not balt.askContinue(self.window,message,'bash.fullNames.import.continue',
            _(u'Import Names')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Names.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import names from:'),
            textDir,textName, _(u'Mod/Text File')+u'|*_Names.csv;*.esp;*.esm',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext not in (u'.esp',u'.esm',u'.csv'):
            balt.showError(self.window,_(u'Source file must be mod (.esp or .esm) or csv file.'))
            return
        #--Export
        renamed = None
        with balt.Progress(_(u"Import Names")) as progress:
            if CBash:
                fullNames = CBash_FullNames()
            else:
                fullNames = FullNames()
            progress(0.1,_(u"Reading %s.") % textName.s)
            if ext == u'.csv':
                fullNames.readFromText(textPath)
            else:
                srcInfo = bosh.ModInfo(textDir,textName)
                fullNames.readFromMod(srcInfo)
            progress(0.2,_(u"Applying to %s.") % fileName.s)
            renamed = fullNames.writeToMod(fileInfo)
            progress(1.0,_(u"Done."))
        #--Log
        if not renamed:
            balt.showOk(self.window,_(u"No changes required."))
        else:
            with sio() as buff:
                format = u'%s:   %s >> %s\n'
                #buff.write(format % (_(u'Editor Id'),_(u'Name')))
                for eid in sorted(renamed.keys()):
                    full,newFull = renamed[eid]
                    try:
                        buff.write(format % (eid,full,newFull))
                    except:
                        print u'unicode error:', (format, eid, full, newFull)
                balt.showLog(self.window,buff.getvalue(),_(u'Objects Renamed'),icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_Patch_Update(Link):
    """Updates a Bashed Patch."""
    def __init__(self,doCBash=False):
        Link.__init__(self)
        self.doCBash = doCBash
        self.CBashMismatch = False

    def AppendToMenu(self,menu,window,data):
        """Append link to a menu."""
        Link.AppendToMenu(self,menu,window,data)
        if self.doCBash:
            title = _(u'Rebuild Patch (CBash *BETA*)...')
        else:
            title = _(u'Rebuild Patch...')
        enable = (len(self.data) == 1 and
            bosh.modInfos[self.data[0]].header.author in (u'BASHED PATCH',u'BASHED LISTS'))
        check = False
        # Detect if the patch was build with Python or CBash
        config = bosh.modInfos.table.getItem(self.data[0],'bash.patch.configs',{})
        thisIsCBash = bosh.CBash_PatchFile.configIsCBash(config)
        self.CBashMismatch = bool(thisIsCBash != self.doCBash)
        if enable and settings['bash.CBashEnabled']:
            menuItem = wx.MenuItem(menu,self.id,title,kind=wx.ITEM_RADIO)
        else:
            menuItem = wx.MenuItem(menu,self.id,title)
        menuItem.Enable(enable)
        menu.AppendItem(menuItem)
        if enable and settings['bash.CBashEnabled']:
            menuItem.Check(not self.CBashMismatch)

    def Execute(self,event):
        """Handle activation event."""
        # Clean up some memory
        bolt.GPathPurge()
        # Create plugin dictionaries -- used later. Speeds everything up! Yay!
        fullLoadOrder   = bosh.modInfos.plugins.LoadOrder   #CDC used this cached value no need to requery

        index = 0
        for name in fullLoadOrder:
            bush.fullLoadOrder[name] = index
            index += 1

        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        if not bosh.modInfos.ordered:
            balt.showWarning(self.window,
                             (_(u'That which does not exist cannot be patched.')
                              + u'\n' +
                              _(u'Load some mods and try again.')
                              ),
                              _(u'Existential Error'))
            return
        # Verify they want to build a previous Python patch in CBash mode, or vice versa
        if self.doCBash and not balt.askContinue(self.window,
            _(u"Building with CBash is cool.  It's faster and allows more things to be handled, but it is still in BETA.  If you have problems, post them in the official thread, then use the non-CBash build function."),
            'bash.patch.ReallyUseCBash.295'): # We'll re-enable this warning for each release, until CBash isn't beta anymore
            return
        importConfig = True
        if self.CBashMismatch:
            if not balt.askYes(self.window,
                    _(u"The patch you are rebuilding (%s) was created in %s mode.  You are trying to rebuild it using %s mode.  Should Wrye Bash attempt to import your settings (some may not be copied correctly)?  Selecting 'No' will load the bashed patch defaults.")
                        % (self.data[0].s,[u'CBash',u'Python'][self.doCBash],[u'Python',u'CBash'][self.doCBash]),
                    'bash.patch.CBashMismatch'):
                importConfig = False
        with balt.BusyCursor(): # just to show users that it hasn't stalled but is doing stuff.
            if self.doCBash:
                bosh.CBash_PatchFile.patchTime = fileInfo.mtime
                bosh.CBash_PatchFile.patchName = fileInfo.name
                nullProgress = bolt.Progress()
                bosh.modInfos.rescanMergeable(bosh.modInfos.data,nullProgress,True)
                self.window.RefreshUI()
            else:
                bosh.PatchFile.patchTime = fileInfo.mtime
                bosh.PatchFile.patchName = fileInfo.name
                if settings['bash.CBashEnabled']:
                    # CBash is enabled, so it's very likely that the merge info currently is from a CBash mode scan
                    with balt.Progress(_(u"Mark Mergeable")+u' '*30) as progress:
                        bosh.modInfos.rescanMergeable(bosh.modInfos.data,progress,False)
                    self.window.RefreshUI()

        #--Check if we should be deactivating some plugins
        ActivePriortoPatch = [x for x in bosh.modInfos.ordered if bosh.modInfos[x].mtime < fileInfo.mtime]
        unfiltered = [x for x in ActivePriortoPatch if u'Filter' in bosh.modInfos[x].getBashTags()]
        merge = [x for x in ActivePriortoPatch if u'NoMerge' not in bosh.modInfos[x].getBashTags() and x in bosh.modInfos.mergeable and x not in unfiltered]
        noMerge = [x for x in ActivePriortoPatch if u'NoMerge' in bosh.modInfos[x].getBashTags() and x in bosh.modInfos.mergeable and x not in unfiltered and x not in merge]
        deactivate = [x for x in ActivePriortoPatch if u'Deactivate' in bosh.modInfos[x].getBashTags() and not 'Filter' in bosh.modInfos[x].getBashTags() and x not in unfiltered and x not in merge and x not in noMerge]

        checklists = []
        unfilteredKey = _(u"Tagged 'Filter'")
        mergeKey = _(u"Mergeable")
        noMergeKey = _(u"Mergeable, but tagged 'NoMerge'")
        deactivateKey = _(u"Tagged 'Deactivate'")
        if unfiltered:
            group = [unfilteredKey,
                     _(u"These mods should be deactivated before building the patch, and then merged or imported into the Bashed Patch."),
                     ]
            group.extend(unfiltered)
            checklists.append(group)
        if merge:
            group = [mergeKey,
                     _(u"These mods are mergeable.  While it is not important to Wrye Bash functionality or the end contents of the Bashed Patch, it is suggested that they be deactivated and merged into the patch.  This helps avoid the Oblivion maximum esp/esm limit."),
                     ]
            group.extend(merge)
            checklists.append(group)
        if noMerge:
            group = [noMergeKey,
                     _(u"These mods are mergeable, but tagged 'NoMerge'.  They should be deactivated before building the patch and imported into the Bashed Patch."),
                     ]
            group.extend(noMerge)
            checklists.append(group)
        if deactivate:
            group = [deactivateKey,
                     _(u"These mods are tagged 'Deactivate'.  They should be deactivated before building the patch, and merged or imported into the Bashed Patch."),
                     ]
            group.extend(deactivate)
            checklists.append(group)
        if checklists:
            dialog = ListBoxes(bashFrame,_(u"Deactivate these mods prior to patching"),
                _(u"The following mods should be deactivated prior to building the patch."),
                checklists,changedlabels={wx.ID_CANCEL:_(u'Skip')})
            if dialog.ShowModal() != wx.ID_CANCEL:
                deselect = set()
                for (list,key) in [(unfiltered,unfilteredKey),
                                   (merge,mergeKey),
                                   (noMerge,noMergeKey),
                                   (deactivate,deactivateKey),
                                   ]:
                    if list:
                        id = dialog.ids[key]
                        checks = dialog.FindWindowById(id)
                        if checks:
                            for i,mod in enumerate(list):
                                if checks.IsChecked(i):
                                    deselect.add(mod)
                dialog.Destroy()
                if deselect:
                    with balt.BusyCursor():
                        for mod in deselect:
                            bosh.modInfos.unselect(mod,False)
                        bosh.modInfos.refreshInfoLists()
                        bosh.modInfos.plugins.save()
                        self.window.RefreshUI(detail=fileName)

        previousMods = set()
        missing = {}
        delinquent = {}
        for mod in bosh.modInfos.ordered:
            if mod == fileName: break
            for master in bosh.modInfos[mod].header.masters:
                if master not in bosh.modInfos.ordered:
                    missing.setdefault(mod,[]).append(master)
                elif master not in previousMods:
                    delinquent.setdefault(mod,[]).append(master)
            previousMods.add(mod)
        if missing or delinquent:
            warning = ListBoxes(bashFrame,_(u'Master Errors'),
                _(u'WARNING!')+u'\n'+_(u'The following mod(s) have master file error(s).  Please adjust your load order to rectify those problem(s) before continuing.  However you can still proceed if you want to.  Proceed?'),
                [[_(u'Missing Master Errors'),_(u'These mods have missing masters; which will make your game unusable, and you will probably have to regenerate your patch after fixing them.  So just go fix them now.'),missing],
                [_(u'Delinquent Master Errors'),_(u'These mods have delinquent masters which will make your game unusable and you quite possibly will have to regenerate your patch after fixing them.  So just go fix them now.'),delinquent]],
                liststyle='tree',style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER,changedlabels={wx.ID_OK:_(u'Continue Despite Errors')})
            if warning.ShowModal() == wx.ID_CANCEL:
                return
        try:
            patchDialog = PatchDialog(self.window,fileInfo,self.doCBash,importConfig)
        except CancelError:
            return
        patchDialog.ShowModal()
        self.window.RefreshUI(detail=fileName)
        # save data to disc in case of later improper shutdown leaving the user guessing as to what options they built the patch with
        BashFrame.SaveSettings(bashFrame)

#------------------------------------------------------------------------------
class Mod_ListPatchConfig(Link):
    """Lists the Bashed Patch configuration and copies to the clipboard."""
    def AppendToMenu(self,menu,window,data):
        """Append link to a menu."""
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'List Patch Config...'))
        menu.AppendItem(menuItem)
        enable = (len(self.data) == 1 and
            bosh.modInfos[self.data[0]].header.author in (u'BASHED PATCH',
                                                          u'BASHED LISTS'))
        menuItem.Enable(enable)

    def Execute(self,event):
        """Handle execution."""
        #--Patcher info
        groupOrder = dict([(group,index) for index,group in
            enumerate((_(u'General'),_(u'Importers'),
                       _(u'Tweakers'),_(u'Special')))])
        #--Config
        config = bosh.modInfos.table.getItem(self.data[0],'bash.patch.configs',{})
        # Detect CBash/Python mode patch
        doCBash = bosh.CBash_PatchFile.configIsCBash(config)
        if doCBash:
            patchers = [copy.deepcopy(x) for x in PatchDialog.CBash_patchers]
        else:
            patchers = [copy.deepcopy(x) for x in PatchDialog.patchers]
        patchers.sort(key=lambda a: a.__class__.name)
        patchers.sort(key=lambda a: groupOrder[a.__class__.group])
        patcherNames = [x.__class__.__name__ for x in patchers]
        #--Log & Clipboard text
        log = bolt.LogFile(StringIO.StringIO())
        log.setHeader(u'= %s %s' % (self.data[0],_(u'Config')))
        log(_(u'This is the current configuration of this Bashed Patch.  This report has also been copied into your clipboard.')+u'\n')
        clip = StringIO.StringIO()
        clip.write(u'%s %s:\n' % (self.data[0],_(u'Config')))
        clip.write(u'[spoiler][xml]\n')
        # CBash/Python patch?
        log.setHeader(u'== '+_(u'Patch Mode'))
        clip.write(u'== '+_(u'Patch Mode')+u'\n')
        if doCBash:
            if settings['bash.CBashEnabled']:
                msg = u'CBash v%u.%u.%u' % (CBash.GetVersionMajor(),CBash.GetVersionMinor(),CBash.GetVersionRevision())
            else:
                # It's a CBash patch config, but CBash.dll is unavailable (either by -P command line, or it's not there)
                msg = u'CBash'
            log(msg)
            clip.write(u' ** %s\n' % msg)
        else:
            log(u'Python')
            clip.write(u' ** Python\n')
        for patcher in patchers:
            className = patcher.__class__.__name__
            humanName = patcher.__class__.name
            # Patcher in the config?
            if not className in config: continue
            # Patcher active?
            conf = config[className]
            if not conf.get('isEnabled',False): continue
            # Active
            log.setHeader(u'== '+humanName)
            clip.write(u'\n')
            clip.write(u'== '+humanName+u'\n')
            if isinstance(patcher, (CBash_MultiTweaker, MultiTweaker)):
                # Tweak patcher
                patcher.getConfig(config)
                for tweak in patcher.tweaks:
                    if tweak.key in conf:
                        enabled,value = conf.get(tweak.key,(False,u''))
                        label = tweak.getListLabel().replace(u'[[',u'[').replace(u']]',u']')
                        if enabled:
                            log(u'* __%s__' % label)
                            clip.write(u' ** %s\n' % label)
                        else:
                            log(u'. ~~%s~~' % label)
                            clip.write(u'    %s\n' % label)
            elif isinstance(patcher, (CBash_ListsMerger_, ListsMerger_)):
                # Leveled Lists
                patcher.configChoices = conf.get('configChoices',{})
                for item in conf.get('configItems',[]):
                    log(u'. __%s__' % patcher.getItemLabel(item))
                    clip.write(u'    %s\n' % patcher.getItemLabel(item))
            elif isinstance(patcher, (CBash_AliasesPatcher,
                                      AliasesPatcher)):
                # Alias mod names
                aliases = conf.get('aliases',{})
                for mod in aliases:
                    log(u'* __%s__ >> %s' % (mod.s, aliases[mod].s))
                    clip.write(u'  %s >> %s\n' % (mod.s, aliases[mod].s))
            else:
                items = conf.get('configItems',[])
                if len(items) == 0:
                    log(u' ')
                for item in conf.get('configItems',[]):
                    checks = conf.get('configChecks',{})
                    checked = checks.get(item,False)
                    if checked:
                        log(u'* __%s__' % item)
                        clip.write(u' ** %s\n' % item)
                    else:
                        log(u'. ~~%s~~' % item)
                        clip.write(u'    %s\n' % item)
        #-- Show log
        clip.write(u'[/xml][/spoiler]')
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(clip.getvalue()))
            wx.TheClipboard.Close()
        clip.close()
        text = log.out.getvalue()
        log.out.close()
        balt.showWryeLog(self.window,text,_(u'Bashed Patch Configuration'),
                         icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_ExportPatchConfig(Link):
    """Exports the Bashed Patch configuration to a Wrye Bash readable file."""
    def AppendToMenu(self,menu,window,data):
        """Append link to a menu."""
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Export Patch Config...'))
        menu.AppendItem(menuItem)
        enable = (len(self.data) == 1 and
            bosh.modInfos[self.data[0]].header.author in (u'BASHED PATCH',
                                                          u'BASHED LISTS'))
        menuItem.Enable(enable)

    def Execute(self,event):
        """Handle execution."""
        #--Config
        config = bosh.modInfos.table.getItem(self.data[0],'bash.patch.configs',{})
        patchName = self.data[0].s + u'_Configuration.dat'
        outDir = bosh.dirs['patches']
        outDir.makedirs()
        #--File dialog
        outPath = balt.askSave(self.window,_(u'Export Bashed Patch configuration to:'),outDir,patchName, u'*_Configuration.dat')
        if not outPath: return
        pklPath = outPath+u'.pkl'
        table = bolt.Table(bosh.PickleDict(outPath, pklPath))
        table.setItem(GPath(u'Saved Bashed Patch Configuration (%s)' % ([u'Python',u'CBash'][bosh.CBash_PatchFile.configIsCBash(config)])),'bash.patch.configs',config)
        table.save()

#------------------------------------------------------------------------------
class Mod_Ratings(Mod_Labels):
    """Add mod rating links."""
    def __init__(self):
        """Initialize."""
        self.column     = 'rating'
        self.setKey     = 'bash.mods.ratings'
        self.editMenu   = _(u'Edit Ratings...')
        self.editWindow = _(u'Ratings')
        self.addPrompt  = _(u'Add rating:')
        self.idList     = ID_RATINGS
        Mod_Labels.__init__(self)

#------------------------------------------------------------------------------
class Mod_SetVersion(Link):
    """Sets version of file back to 0.8."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        self.fileInfo = window.data[data[0]]
        menuItem = wx.MenuItem(menu,self.id,_(u'Version 0.8'))
        menu.AppendItem(menuItem)
        #print self.fileInfo.header.version
        menuItem.Enable((len(data) == 1) and (int(10*self.fileInfo.header.version) != 8))

    def Execute(self,event):
        message = _(u"WARNING! For advanced modders only! This feature allows you to edit newer official mods in the TES Construction Set by resetting the internal file version number back to 0.8. While this will make the mod editable, it may also break the mod in some way.")
        if not balt.askContinue(self.window,message,'bash.setModVersion.continue',_(u'Set File Version')):
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
        menuItem = wx.MenuItem(menu,self.id,_(u'Details...'))
        menu.AppendItem(menuItem)
        menuItem.Enable((len(data) == 1))

    def Execute(self,event):
        modName = GPath(self.data[0])
        modInfo = bosh.modInfos[modName]
        with balt.Progress(modName.s) as progress:
            modDetails = bosh.ModDetails()
            modDetails.readFromMod(modInfo,SubProgress(progress,0.1,0.7))
            buff = StringIO.StringIO()
            progress(0.7,_(u'Sorting records.'))
            for group in sorted(modDetails.group_records):
                buff.write(group+u'\n')
                if group in ('CELL','WRLD','DIAL'):
                    buff.write(u'  '+_(u'(Details not provided for this record type.)')+u'\n\n')
                    continue
                records = modDetails.group_records[group]
                records.sort(key = lambda a: a[1].lower())
                #if group != 'GMST': records.sort(key = lambda a: a[0] >> 24)
                for fid,eid in records:
                    buff.write(u'  %08X %s\n' % (fid,eid))
                buff.write(u'\n')
            balt.showLog(self.window,buff.getvalue(), modInfo.name.s,
                asDialog=False, fixedFont=True, icons=bashBlue)
            buff.close()

#------------------------------------------------------------------------------
class Mod_RemoveWorldOrphans(Link):
    """Remove orphaned cell records."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Remove World Orphans'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data) != 1 or (not bosh.reOblivion.match(self.data[0].s)))

    def Execute(self,event):
        message = _(u"In some circumstances, editing a mod will leave orphaned cell records in the world group. This command will remove such orphans.")
        if not balt.askContinue(self.window,message,'bash.removeWorldOrphans.continue',_(u'Remove World Orphans')):
            return
        for item in self.data:
            fileName = GPath(item)
            if bosh.reOblivion.match(fileName.s):
                balt.showWarning(self.window,_(u"Skipping %s") % fileName.s,_(u'Remove World Orphans'))
                continue
            fileInfo = bosh.modInfos[fileName]
            #--Export
            orphans = 0
            with balt.Progress(_(u"Remove World Orphans")) as progress:
                loadFactory = bosh.LoadFactory(True,bosh.MreRecord.type_class['CELL'],bosh.MreRecord.type_class['WRLD'])
                modFile = bosh.ModFile(fileInfo,loadFactory)
                progress(0,_(u"Reading %s.") % fileName.s)
                modFile.load(True,SubProgress(progress,0,0.7))
                orphans = ('WRLD' in modFile.tops) and modFile.WRLD.orphansSkipped
                if orphans:
                    progress(0.1,_(u"Saving %s.") % fileName.s)
                    modFile.safeSave()
                progress(1.0,_(u"Done."))
            #--Log
            if orphans:
                balt.showOk(self.window,_(u"Orphan cell blocks removed: %d.") % orphans,fileName.s)
            else:
                balt.showOk(self.window,_(u"No changes required."),fileName.s)

#------------------------------------------------------------------------------
class Mod_ShowReadme(Link):
    """Open the readme."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Readme...'))
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
from patcher.utilities import ScriptText, CBash_ScriptText

class Mod_Scripts_Export(Link):
    """Export scripts from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Scripts...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        defaultPath = bosh.dirs['patches'].join(fileName.s+u' Exported Scripts')
        def OnOk(event):
            dialog.EndModal(1)
            settings['bash.mods.export.deprefix'] = gdeprefix.GetValue().strip()
            settings['bash.mods.export.skip'] = gskip.GetValue().strip()
            settings['bash.mods.export.skipcomments'] = gskipcomments.GetValue()
        dialog = wx.Dialog(bashFrame,wx.ID_ANY,_(u'Export Scripts Options'),
                           size=(400,180),style=wx.DEFAULT_DIALOG_STYLE)
        gskip = textCtrl(dialog)
        gdeprefix = textCtrl(dialog)
        gskipcomments = toggleButton(dialog,_(u'Filter Out Comments'),
            tip=_(u"If active doesn't export comments in the scripts"))
        gskip.SetValue(settings['bash.mods.export.skip'])
        gdeprefix.SetValue(settings['bash.mods.export.deprefix'])
        gskipcomments.SetValue(settings['bash.mods.export.skipcomments'])
        sizer = vSizer(
            staticText(dialog,_(u"Skip prefix (leave blank to not skip any), non-case sensitive):"),style=wx.ST_NO_AUTORESIZE),
            gskip,
            spacer,
            staticText(dialog,(_(u'Remove prefix from file names i.e. enter cob to save script cobDenockInit')
                               + u'\n' +
                               _(u'as DenockInit.ext rather than as cobDenockInit.ext')
                               + u'\n' +
                               _(u'(Leave blank to not cut any prefix, non-case sensitive):')
                               ),style=wx.ST_NO_AUTORESIZE),
            gdeprefix,
            spacer,
            gskipcomments,
            (hSizer(
                spacer,
                button(dialog,id=wx.ID_OK,onClick=OnOk),
                (button(dialog,id=wx.ID_CANCEL),0,wx.LEFT,4),
                ),0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,6),
            )
        dialog.SetSizer(sizer)
        questions = dialog.ShowModal()
        if questions != 1: return #because for some reason cancel/close dialogue is returning 5101!
        if not defaultPath.exists():
            defaultPath.makedirs()
        textDir = balt.askDirectory(self.window,
            _(u'Choose directory to export scripts to'),defaultPath)
        if textDir != defaultPath:
            for asDir,sDirs,sFiles in os.walk(defaultPath.s):
                if not (sDirs or sFiles):
                    defaultPath.removedirs()
        if not textDir: return
        #--Export
        #try:
        if CBash:
            ScriptText = CBash_ScriptText()
        else:
            ScriptText = ScriptText()
        ScriptText.readFromMod(fileInfo,fileName.s)
        exportedScripts = ScriptText.writeToText(fileInfo,settings['bash.mods.export.skip'],textDir,settings['bash.mods.export.deprefix'],fileName.s,settings['bash.mods.export.skipcomments'])
        #finally:
        balt.showLog(self.window,exportedScripts,_(u'Export Scripts'),
                     icons=bashBlue)

#------------------------------------------------------------------------------
class Mod_Scripts_Import(Link):
    """Import scripts from text file or other mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Scripts...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = (_(u"Import script from a text file.  This will replace existing scripts and is not reversible (except by restoring from backup)!"))
        if not balt.askContinue(self.window,message,'bash.scripts.import.continue',
            _(u'Import Scripts')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        defaultPath = bosh.dirs['patches'].join(fileName.s+u' Exported Scripts')
        if not defaultPath.exists():
            defaultPath = bosh.dirs['patches']
        textDir = balt.askDirectory(self.window,
            _(u'Choose directory to import scripts from'),defaultPath)
        if textDir is None:
            return
        message = (_(u"Import scripts that don't exist in the esp as new scripts?")
                   + u'\n' +
                   _(u'(If not they will just be skipped).')
                   )
        makeNew = balt.askYes(self.window,message,_(u'Import Scripts'),icon=wx.ICON_QUESTION)
        if CBash:
            ScriptText = CBash_ScriptText()
        else:
            ScriptText = ScriptText()
        ScriptText.readFromText(textDir.s,fileInfo)
        changed, added = ScriptText.writeToMod(fileInfo,makeNew)
    #--Log
        if not (len(changed) or len(added)):
            balt.showOk(self.window,_(u"No changed or new scripts to import."),
                        _(u"Import Scripts"))
        else:
            if changed:
                changedScripts = (_(u'Imported %d changed scripts from %s:')
                                  + u'\n%s') % (len(changed),textDir.s,u'*'+u'\n*'.join(sorted(changed)))
            else:
                changedScripts = u''
            if added:
                addedScripts = (_(u'Imported %d new scripts from %s:')
                                + u'\n%s') % (len(added),textDir.s,u'*'+u'\n*'.join(sorted(added)))
            else:
                addedScripts = u''
            if changed and added:
                report = changedScripts + u'\n\n' + addedScripts
            elif changed:
                report = changedScripts
            elif added:
                report = addedScripts
            balt.showLog(self.window,report,_(u'Import Scripts'),icons=bashBlue)

#------------------------------------------------------------------------------
from patcher.utilities import ItemStats, CBash_ItemStats

class Mod_Stats_Export(Link):
    """Export armor and weapon stats from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Stats...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Stats.csv'
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_(u'Export stats to:'),
            textDir, textName, u'*_Stats.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        with balt.Progress(_(u"Export Stats")) as progress:
            if CBash:
                itemStats = CBash_ItemStats()
            else:
                itemStats = ItemStats()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_(u"Reading %s.") % fileName.s)
                itemStats.readFromMod(fileInfo)
            progress(0.8,_(u"Exporting to %s.") % textName.s)
            itemStats.writeToText(textPath)
            progress(1.0,_(u"Done."))

#------------------------------------------------------------------------------
class Mod_Stats_Import(Link):
    """Import stats from text file or other mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Stats...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = (_(u"Import item stats from a text file. This will replace existing stats and is not reversible!"))
        if not balt.askContinue(self.window,message,'bash.stats.import.continue',
            _(u'Import Stats')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Stats.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import stats from:'),
            textDir, textName, u'*_Stats.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != u'.csv':
            balt.showError(self.window,_(u'Source file must be a Stats.csv file.'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u"Import Stats")) as progress:
            if CBash:
                itemStats = CBash_ItemStats()
            else:
                itemStats = ItemStats()
            progress(0.1,_(u"Reading %s.") % textName.s)
            itemStats.readFromText(textPath)
            progress(0.2,_(u"Applying to %s.") % fileName.s)
            changed = itemStats.writeToMod(fileInfo)
            progress(1.0,_(u"Done."))
        #--Log
        if not changed:
            balt.showOk(self.window,_(u"No relevant stats to import."),_(u"Import Stats"))
        else:
            if not len(changed):
                balt.showOk(self.window,_(u"No changed stats to import."),_(u"Import Stats"))
            else:
                buff = StringIO.StringIO()
                for modName in sorted(changed):
                    buff.write(u'* %03d  %s\n' % (changed[modName], modName.s))
                balt.showLog(self.window,buff.getvalue(),_(u'Import Stats'),icons=bashBlue)
                buff.close()

#------------------------------------------------------------------------------
from patcher.utilities import CompleteItemData, CBash_CompleteItemData

class Mod_ItemData_Export(Link):
    """Export pretty much complete item data from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Item Data...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_ItemData.csv'
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_(u'Export item data to:'),
            textDir, textName, u'*_ItemData.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        with balt.Progress(_(u"Export Item Data")) as progress:
            if CBash:
                itemStats = CBash_CompleteItemData()
            else:
                itemStats = CompleteItemData()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_(u"Reading %s.") % fileName.s)
                itemStats.readFromMod(fileInfo)
            progress(0.8,_(u"Exporting to %s.") % textName.s)
            itemStats.writeToText(textPath)
            progress(1.0,_(u"Done."))

#------------------------------------------------------------------------------
class Mod_ItemData_Import(Link):
    """Import stats from text file or other mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Item Data...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = (_(u"Import pretty much complete item data from a text file.  This will replace existing data and is not reversible!"))
        if not balt.askContinue(self.window,message,'bash.itemdata.import.continue',
            _(u'Import Item Data')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_ItemData.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import item data from:'),
            textDir, textName, u'*_ItemData.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != '.csv':
            balt.showError(self.window,_(u'Source file must be a ItemData.csv file.'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u'Import Item Data')) as progress:
            itemStats = CompleteItemData() # FIXME - why not if CBash: ?
            progress(0.1,_(u'Reading')+u' '+textName.s+u'.')
            if ext == u'.csv':
                itemStats.readFromText(textPath)
            else:
                srcInfo = bosh.ModInfo(textDir,textName)
                itemStats.readFromMod(srcInfo)
            progress(0.2,_(u'Applying to')+u' '+fileName.s+u'.')
            changed = itemStats.writeToMod(fileInfo)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed:
            balt.showOk(self.window,_(u'No relevant data to import.'),
                        _(u'Import Item Data'))
        else:
            buff = StringIO.StringIO()
            for modName in sorted(changed):
                buff.write(_(u'Imported Item Data:')
                           + u'\n* %03d  %s:\n' % (changed[modName], modName.s))
            balt.showLog(self.window,buff.getvalue(),_(u'Import Item Data'),icons=bashBlue)
            buff.close()

#------------------------------------------------------------------------------
from patcher.utilities import ItemPrices, CBash_ItemPrices

class Mod_Prices_Export(Link):
    """Export item prices from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Prices...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Prices.csv'
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_(u'Export prices to:'),
            textDir, textName, u'*_Prices.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        with balt.Progress(_(u'Export Prices')) as progress:
            if CBash:
                itemPrices = CBash_ItemPrices()
            else:
                itemPrices = ItemPrices()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_(u'Reading')+u' '+fileName.s+u'.')
                itemPrices.readFromMod(fileInfo)
            progress(0.8,_(u'Exporting to')+u' '+textName.s+'.')
            itemPrices.writeToText(textPath)
            progress(1.0,_(u'Done.'))

#------------------------------------------------------------------------------
class Mod_Prices_Import(Link):
    """Import prices from text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Prices...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data)==1)

    def Execute(self,event):
        message = (_(u"Import item prices from a text file.  This will replace existing prices and is not reversible!"))
        if not balt.askContinue(self.window,message,
            'bash.prices.import.continue',_(u'Import prices')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Prices.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import prices from:'),
            textDir, textName, u'*_Prices.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext not in [u'.csv',u'.ghost',u'.esm',u'.esp']:
            balt.showError(self.window,_(u'Source file must be a Prices.csv file or esp/m.'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u'Import Prices')) as progress:
            if CBash:
                itemPrices = CBash_ItemPrices()
            else:
                itemPrices = ItemPrices()
            progress(0.1,_(u'Reading')+u' '+textName.s+u'.')
            if ext == u'.csv':
                itemPrices.readFromText(textPath)
            else:
                srcInfo = bosh.ModInfo(textDir,textName)
                itemPrices.readFromMod(srcInfo)
            progress(0.2,_(u'Applying to')+u' '+fileName.s+u'.')
            changed = itemPrices.writeToMod(fileInfo)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed:
            balt.showOk(self.window,_(u'No relevant prices to import.'),
                        _(u'Import Prices'))
        else:
            buff = StringIO.StringIO()
            for modName in sorted(changed):
                buff.write(_(u'Imported Prices:')
                           + u'\n* %s: %d\n' % (modName.s,changed[modName]))
            balt.showLog(self.window,buff.getvalue(),_(u'Import Prices'),
                         icons=bashBlue)
            buff.close()

#------------------------------------------------------------------------------
from patcher.utilities import CBash_MapMarkers

class CBash_Mod_MapMarkers_Export(Link):
    """Export map marker stats from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Map Markers...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data) and bool(CBash))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_MapMarkers.csv'
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_(u'Export Map Markers to:'),
            textDir, textName, u'*_MapMarkers.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        with balt.Progress(_(u'Export Map Markers')) as progress:
            mapMarkers = CBash_MapMarkers()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_(u'Reading')+u' '+fileName.s+u'.')
                mapMarkers.readFromMod(fileInfo)
            progress(0.8,_(u'Exporting to')+u' '+textName.s+u'.')
            mapMarkers.writeToText(textPath)
            progress(1.0,_(u'Done.'))

#------------------------------------------------------------------------------
class CBash_Mod_MapMarkers_Import(Link):
    """Import MapMarkers from text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Map Markers...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data) == 1 and bool(CBash))

    def Execute(self,event):
        message = (_(u"Import Map Markers data from a text file.  This will replace existing the data on map markers with the same editor ids and is not reversible!"))
        if not balt.askContinue(self.window,message,
            'bash.MapMarkers.import.continue',_(u'Import Map Markers')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_MapMarkers.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import Map Markers from:'),
            textDir, textName, u'*_MapMarkers.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != u'.csv':
            balt.showError(self.window,_(u'Source file must be a MapMarkers.csv file'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u'Import Map Markers')) as progress:
            MapMarkers = CBash_MapMarkers()
            progress(0.1,_(u'Reading')+u' '+textName.s)
            MapMarkers.readFromText(textPath)
            progress(0.2,_(u'Applying to')+u' '+fileName.s)
            changed = MapMarkers.writeToMod(fileInfo)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed:
            balt.showOk(self.window,_(u'No relevant Map Markers to import.'),
                        _(u'Import Map Markers'))
        else:
            buff = StringIO.StringIO()
            buff.write((_(u'Imported Map Markers to mod %s:')
                        + u'\n') % (fileName.s,))
            for eid in sorted(changed):
                buff.write(u'* %s\n' % eid)
            balt.showLog(self.window,buff.getvalue(),_(u'Import Map Markers'),
                         icons=bashBlue)
            buff.close()

#------------------------------------------------------------------------------
from patcher.utilities import CBash_CellBlockInfo

class CBash_Mod_CellBlockInfo(Link):
    """Export Cell Block Info to text file.
    (in the form of Cell, block, subblock"""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Cell Block Info...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data) and bool(CBash))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_CellBlockInfo.csv'
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_(u'Export Cell Block Info to:'),
            textDir, textName, u'*_CellBlockInfo.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        with balt.Progress(_(u"Export Cell Block Info")) as progress:
            cellblocks = CBash_CellBlockInfo()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_(u"Reading %s.") % fileName.s)
                cellblocks.readFromMod(fileInfo)
            progress(0.8,_(u"Exporting to %s.") % textName.s)
            cellblocks.writeToText(textPath)
            progress(1.0,_(u"Done."))

#------------------------------------------------------------------------------
from patcher.utilities import SigilStoneDetails, CBash_SigilStoneDetails

class Mod_SigilStoneDetails_Export(Link):
    """Export Sigil Stone details from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Sigil Stones...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_SigilStones.csv'
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,
            _(u'Export Sigil Stone details to:'),
            textDir,textName, u'*_SigilStones.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        with balt.Progress(_(u'Export Sigil Stone details')) as progress:
            if CBash:
                sigilStones = CBash_SigilStoneDetails()
            else:
                sigilStones = SigilStoneDetails()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_(u'Reading')+u' '+fileName.s+u'.')
                sigilStones.readFromMod(fileInfo)
            progress(0.8,_(u'Exporting to')+u' '+textName.s+u'.')
            sigilStones.writeToText(textPath)
            progress(1.0,_(u'Done.'))

#------------------------------------------------------------------------------
class Mod_SigilStoneDetails_Import(Link):
    """Import Sigil Stone details from text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Sigil Stones...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data) == 1)

    def Execute(self,event):
        message = (_(u"Import Sigil Stone details from a text file.  This will replace existing the data on sigil stones with the same form ids and is not reversible!"))
        if not balt.askContinue(self.window,message,
            'bash.SigilStone.import.continue',
            _(u'Import Sigil Stones details')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_SigilStones.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,
            _(u'Import Sigil Stone details from:'),
            textDir, textName, u'*_SigilStones.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != u'.csv':
            balt.showError(self.window,_(u'Source file must be a _SigilStones.csv file'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u'Import Sigil Stone details')) as progress:
            if CBash:
                sigilStones = CBash_SigilStoneDetails()
            else:
                sigilStones = SigilStoneDetails()
            progress(0.1,_(u'Reading')+u' '+textName.s+u'.')
            sigilStones.readFromText(textPath)
            progress(0.2,_(u'Applying to')+u' '+fileName.s+u'.')
            changed = sigilStones.writeToMod(fileInfo)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed:
            balt.showOk(self.window,
                _(u'No relevant Sigil Stone details to import.'),
                _(u'Import Sigil Stone details'))
        else:
            buff = StringIO.StringIO()
            buff.write((_(u'Imported Sigil Stone details to mod %s:')
                        +u'\n') % fileName.s)
            for eid in sorted(changed):
                buff.write(u'* %s\n' % eid)
            balt.showLog(self.window,buff.getvalue(),
                         _(u'Import Sigil Stone details'),icons=bashBlue)
            buff.close()

#------------------------------------------------------------------------------
from patcher.utilities import SpellRecords, CBash_SpellRecords

class Mod_SpellRecords_Export(Link):
    """Export Spell details from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Spells...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Spells.csv'
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_(u'Export Spell details to:'),textDir,textName, u'*_Spells.csv')
        if not textPath: return
        message = (_(u'Export flags and effects?')
                   + u'\n' +
                   _(u'(If not they will just be skipped).')
                   )
        doDetailed = balt.askYes(self.window,message,_(u'Export Spells'),icon=wx.ICON_QUESTION)
        (textDir,textName) = textPath.headTail
        #--Export
        with balt.Progress(_(u'Export Spell details')) as progress:
            if CBash:
                spellRecords = CBash_SpellRecords(detailed=doDetailed)
            else:
                spellRecords = SpellRecords(detailed=doDetailed)
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_(u'Reading')+u' '+fileName.s+u'.')
                spellRecords.readFromMod(fileInfo)
            progress(0.8,_(u'Exporting to')+u' '+textName.s+u'.')
            spellRecords.writeToText(textPath)
            progress(1.0,_(u'Done.'))

#------------------------------------------------------------------------------
class Mod_SpellRecords_Import(Link):
    """Import Spell details from text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Spells...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data) == 1)

    def Execute(self,event):
        message = (_(u"Import Spell details from a text file.  This will replace existing the data on spells with the same form ids and is not reversible!"))
        if not balt.askContinue(self.window,message,
            'bash.SpellRecords.import.continue',
            _(u'Import Spell details')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Spells.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import Spell details from:'),
            textDir, textName, u'*_Spells.csv',mustExist=True)
        if not textPath: return
        message = (_(u'Import flags and effects?')
                   + u'\n' +
                   _(u'(If not they will just be skipped).')
                   )
        doDetailed = balt.askYes(self.window,message,_(u'Import Spell details'),
                                 icon=wx.ICON_QUESTION)
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != u'.csv':
            balt.showError(self.window,_(u'Source file must be a _Spells.csv file'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u'Import Spell details')) as progress:
            if CBash:
                spellRecords = CBash_SpellRecords(detailed=doDetailed)
            else:
                spellRecords = SpellRecords(detailed=doDetailed)
            progress(0.1,_(u'Reading')+u' '+textName.s+u'.')
            spellRecords.readFromText(textPath)
            progress(0.2,_(u'Applying to')+u' '+fileName.s+u'.')
            changed = spellRecords.writeToMod(fileInfo)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed:
            balt.showOk(self.window,_(u'No relevant Spell details to import.'),
                        _(u'Import Spell details'))
        else:
            buff = StringIO.StringIO()
            buff.write((_(u'Imported Spell details to mod %s:')
                        +u'\n') % fileName.s)
            for eid in sorted(changed):
                buff.write(u'* %s\n' % eid)
            balt.showLog(self.window,buff.getvalue(),_(u'Import Spell details'),

                         icons=bashBlue)
            buff.close()

#------------------------------------------------------------------------------
from patcher.utilities import IngredientDetails, CBash_IngredientDetails

class Mod_IngredientDetails_Export(Link):
    """Export Ingredient details from mod to text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Ingredients...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.data))

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Ingredients.csv'
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,_(u'Export Ingredient details to:'),
                                textDir,textName,u'*_Ingredients.csv')
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Export
        with balt.Progress(_(u'Export Ingredient details')) as progress:
            if CBash:
                Ingredients = CBash_IngredientDetails()
            else:
                Ingredients = IngredientDetails()
            readProgress = SubProgress(progress,0.1,0.8)
            readProgress.setFull(len(self.data))
            for index,fileName in enumerate(map(GPath,self.data)):
                fileInfo = bosh.modInfos[fileName]
                readProgress(index,_(u'Reading')+u' '+fileName.s+u'.')
                Ingredients.readFromMod(fileInfo)
            progress(0.8,_(u'Exporting to')+u' '+textName.s+u'.')
            Ingredients.writeToText(textPath)
            progress(1.0,_(u'Done.'))

class Mod_IngredientDetails_Import(Link):
    """Import Ingredient details from text file."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Ingredients...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data) == 1)

    def Execute(self,event):
        message = (_(u"Import Ingredient details from a text file.  This will replace existing the data on Ingredients with the same form ids and is not reversible!"))
        if not balt.askContinue(self.window,message,
            'bash.Ingredient.import.continue',
            _(u'Import Ingredients details')):
            return
        fileName = GPath(self.data[0])
        fileInfo = bosh.modInfos[fileName]
        textName = fileName.root+u'_Ingredients.csv'
        textDir = bosh.dirs['patches']
        #--File dialog
        textPath = balt.askOpen(self.window,_(u'Import Ingredient details from:'),
            textDir,textName,u'*_Ingredients.csv',mustExist=True)
        if not textPath: return
        (textDir,textName) = textPath.headTail
        #--Extension error check
        ext = textName.cext
        if ext != u'.csv':
            balt.showError(self.window,_(u'Source file must be a _Ingredients.csv file'))
            return
        #--Export
        changed = None
        with balt.Progress(_(u'Import Ingredient details')) as progress:
            if CBash:
                Ingredients = CBash_IngredientDetails()
            else:
                Ingredients = IngredientDetails()
            progress(0.1,_(u'Reading %s.') % textName.s)
            Ingredients.readFromText(textPath)
            progress(0.2,_(u'Applying to %s.') % fileName.s)
            changed = Ingredients.writeToMod(fileInfo)
            progress(1.0,_(u'Done.'))
        #--Log
        if not changed:
            balt.showOk(self.window,
                _(u'No relevant Ingredient details to import.'),
                _(u'Import Ingredient details'))
        else:
            buff = StringIO.StringIO()
            buff.write((_(u'Imported Ingredient details to mod %s:')
                        + u'\n') % fileName.s)
            for eid in sorted(changed):
                buff.write(u'* %s\n' % eid)
            balt.showLog(self.window,buff.getvalue(),
                _(u'Import Ingredient details'),icons=bashBlue)
            buff.close()

#------------------------------------------------------------------------------
class Mod_UndeleteRefs(Link):
    """Undeletes refs in cells."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Undelete Refs'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.data) != 1 or (not bosh.reOblivion.match(self.data[0].s)))

    def Execute(self,event):
        message = _(u"Changes deleted refs to ignored.  This is a very advanced feature and should only be used by modders who know exactly what they're doing.")
        if not balt.askContinue(self.window,message,'bash.undeleteRefs.continue',
            _(u'Undelete Refs')):
            return
        with balt.Progress(_(u'Undelete Refs')) as progress:
            progress.setFull(len(self.data))
            hasFixed = False
            log = bolt.LogFile(StringIO.StringIO())
            for index,fileName in enumerate(map(GPath,self.data)):
                if bosh.reOblivion.match(fileName.s):
                    balt.showWarning(self.window,_(u'Skipping')+u' '+fileName.s,
                                     _(u'Undelete Refs'))
                    continue
                progress(index,_(u'Scanning')+u' '+fileName.s+u'.')
                fileInfo = bosh.modInfos[fileName]
                cleaner = bosh.ModCleaner(fileInfo)
                cleaner.clean(bosh.ModCleaner.UDR,SubProgress(progress,index,index+1))
                if cleaner.udr:
                    hasFixed = True
                    log.setHeader(u'== '+fileName.s)
                    for fid in sorted(cleaner.udr):
                        log(u'. %08X' % fid)
        if hasFixed:
            message = log.out.getvalue()
        else:
            message = _(u"No changes required.")
        balt.showWryeLog(self.window,message,_(u'Undelete Refs'),icons=bashBlue)
        log.out.close()

#------------------------------------------------------------------------------
class Mod_ScanDirty(Link):
    """Give detailed printout of what Wrye Bash is detecting as UDR and ITM records"""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        if settings['bash.CBashEnabled']:
            menuItem = wx.MenuItem(menu,self.id,_(u'Scan for Dirty Edits'))
        else:
            menuItem = wx.MenuItem(menu,self.id,_(u"Scan for UDR's"))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        """Handle execution"""
        modInfos = [bosh.modInfos[x] for x in self.data]
        try:
            with balt.Progress(_(u'Dirty Edits'),u'\n'+u' '*60,abort=True) as progress:
                ret = bosh.ModCleaner.scan_Many(modInfos,progress=progress,detailed=True)
        except bolt.CancelError:
            return
        log = bolt.LogFile(StringIO.StringIO())
        log.setHeader(u'= '+_(u'Scan Mods'))
        log(_(u'This is a report of records that were detected as either Identical To Master (ITM) or a deleted reference (UDR).')
            + u'\n')
        # Change a FID to something more usefull for displaying
        if settings['bash.CBashEnabled']:
            def strFid(fid):
                return u'%s: %06X' % (fid[0],fid[1])
        else:
            def strFid(fid):
                modId = (0xFF000000 & fid) >> 24
                modName = modInfo.masterNames[modId]
                id = 0x00FFFFFF & fid
                return u'%s: %06X' % (modName,id)
        dirty = []
        clean = []
        error = []
        for i,modInfo in enumerate(modInfos):
            udrs,itms,fog = ret[i]
            if modInfo.name == GPath(u'Unofficial Oblivion Patch.esp'):
                # Record for non-SI users, shows up as ITM if SI is installed (OK)
                if settings['bash.CBashEnabled']:
                    itms.discard(FormID(GPath(u'Oblivion.esm'),0x00AA3C))
                else:
                    itms.discard((GPath(u'Oblivion.esm'),0x00AA3C))
            if modInfo.header.author in (u'BASHED PATCH',u'BASHED LISTS'): itms = set()
            if udrs or itms:
                pos = len(dirty)
                dirty.append(u'* __'+modInfo.name.s+u'__:\n')
                dirty[pos] += u'  * %s: %i\n' % (_(u'UDR'),len(udrs))
                for udr in sorted(udrs):
                    if udr.parentEid:
                        parentStr = u"%s '%s'" % (strFid(udr.parentFid),udr.parentEid)
                    else:
                        parentStr = strFid(udr.parentFid)
                    if udr.parentType == 0:
                        # Interior CELL
                        item = u'%s -  %s attached to Interior CELL (%s)' % (
                            strFid(udr.fid),udr.type,parentStr)
                    else:
                        # Exterior CELL
                        if udr.parentParentEid:
                            parentParentStr = u"%s '%s'" % (strFid(udr.parentParentFid),udr.parentParentEid)
                        else:
                            parentParentStr = strFid(udr.parentParentFid)
                        if udr.pos is None:
                            atPos = u''
                        else:
                            atPos = u' at %s' % (udr.pos,)
                        item = u'%s - %s attached to Exterior CELL (%s), attached to WRLD (%s)%s' % (
                            strFid(udr.fid),udr.type,parentStr,parentParentStr,atPos)
                    dirty[pos] += u'    * %s\n' % item
                if not settings['bash.CBashEnabled']: continue
                if itms:
                    dirty[pos] += u'  * %s: %i\n' % (_(u'ITM'),len(itms))
                for fid in sorted(itms):
                    dirty[pos] += u'    * %s\n' % strFid(fid)
            elif udrs is None or itms is None:
                error.append(u'* __'+modInfo.name.s+u'__')
            else:
                clean.append(u'* __'+modInfo.name.s+u'__')
        #-- Show log
        if dirty:
            log(_(u'Detected %d dirty mods:') % len(dirty))
            for mod in dirty: log(mod)
            log(u'\n')
        if clean:
            log(_(u'Detected %d clean mods:') % len(clean))
            for mod in clean: log(mod)
            log(u'\n')
        if error:
            log(_(u'The following %d mods had errors while scanning:') % len(error))
            for mod in error: log(mod)
        balt.showWryeLog(self.window,log.out.getvalue(),
            _(u'Dirty Edit Scan Results'),asDialog=False,icons=bashBlue)
        log.out.close()

# Saves Links -----------------------------------------------------------------
#------------------------------------------------------------------------------
class Saves_ProfilesData(balt.ListEditorData):
    """Data capsule for save profiles editing dialog."""
    def __init__(self,parent):
        """Initialize."""
        self.baseSaves = bosh.dirs['saveBase'].join(u'Saves')
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
        profileSaves = u'Saves\\'+item+u'\\'
        return bosh.saveInfos.profiles.getItem(profileSaves,'info',_(u'About %s:') % item)
    def setInfo(self,item,text):
        """Sets string info on specified item."""
        profileSaves = u'Saves\\'+item+u'\\'
        bosh.saveInfos.profiles.setItem(profileSaves,'info',text)

    def add(self):
        """Adds a new profile."""
        newName = balt.askText(self.parent,_(u"Enter profile name:"))
        if not newName:
            return False
        if newName in self.getItemList():
            balt.showError(self.parent,_(u'Name must be unique.'))
            return False
        if len(newName) == 0 or len(newName) > 64:
            balt.showError(self.parent,
                _(u'Name must be between 1 and 64 characters long.'))
            return False
        try:
            newName.encode('cp1252')
        except UnicodeEncodeError:
            balt.showError(self.parent,
                _(u'Name must be encodable in Windows Codepage 1252 (Western European), due to limitations of %(gameIni)s.') % {'gameIni':bush.game.iniFiles[0]})
            return False
        self.baseSaves.join(newName).makedirs()
        newSaves = u'Saves\\'+newName+u'\\'
        bosh.saveInfos.profiles.setItem(newSaves,'vOblivion',bosh.modInfos.voCurrent)
        return newName

    def rename(self,oldName,newName):
        """Renames profile oldName to newName."""
        newName = newName.strip()
        lowerNames = [name.lower() for name in self.getItemList()]
        #--Error checks
        if newName.lower() in lowerNames:
            balt.showError(self,_(u'Name must be unique.'))
            return False
        if len(newName) == 0 or len(newName) > 64:
            balt.showError(self.parent,
                _(u'Name must be between 1 and 64 characters long.'))
            return False
        #--Rename
        oldDir,newDir = (self.baseSaves.join(dir) for dir in (oldName,newName))
        oldDir.moveTo(newDir)
        oldSaves,newSaves = ((u'Saves\\'+name+u'\\') for name in (oldName,newName))
        if bosh.saveInfos.localSave == oldSaves:
            bosh.saveInfos.setLocalSave(newSaves)
            bashFrame.SetTitle()
        bosh.saveInfos.profiles.moveRow(oldSaves,newSaves)
        return newName

    def remove(self,profile):
        """Removes load list."""
        profileSaves = u'Saves\\'+profile+u'\\'
        #--Can't remove active or Default directory.
        if bosh.saveInfos.localSave == profileSaves:
            balt.showError(self.parent,_(u'Active profile cannot be removed.'))
            return False
        #--Get file count. If > zero, verify with user.
        profileDir = bosh.dirs['saveBase'].join(profileSaves)
        files = [file for file in profileDir.list() if bosh.reSaveExt.search(file.s)]
        if files:
            message = _(u'Delete profile %s and the %d save files it contains?') % (profile,len(files))
            if not balt.askYes(self.parent,message,_(u'Delete Profile')):
                return False
        #--Remove directory
        if GPath(bush.game.fsName).join(u'Saves').s not in profileDir.s:
            raise BoltError(u'Sanity check failed: No "%s\\Saves" in %s.' % (bush.game.fsName,profileDir.s))
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
        menu.Append(self.idList.EDIT,_(u"Edit Profiles..."))
        menu.AppendSeparator()
        #--List
        localSave = bosh.saveInfos.localSave
        menuItem = wx.MenuItem(menu,self.idList.DEFAULT,_(u'Default'),kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        menuItem.Check(localSave == u'Saves\\')
        for id,item in zip(self.idList,self.GetItems()):
            menuItem = wx.MenuItem(menu,id,item,kind=wx.ITEM_CHECK)
            menu.AppendItem(menuItem)
            menuItem.Check(localSave == (u'Saves\\'+item+u'\\'))
        #--Events
        wx.EVT_MENU(bashFrame,self.idList.EDIT,self.DoEdit)
        wx.EVT_MENU(bashFrame,self.idList.DEFAULT,self.DoDefault)
        wx.EVT_MENU_RANGE(bashFrame,self.idList.BASE,self.idList.MAX,self.DoList)

    def DoEdit(self,event):
        """Show profiles editing dialog."""
        data = Saves_ProfilesData(self.window)
        dialog = balt.ListEditor(self.window,wx.ID_ANY,_(u'Save Profiles'),data)
        dialog.ShowModal()
        dialog.Destroy()

    def DoDefault(self,event):
        """Handle selection of Default."""
        arcSaves,newSaves = bosh.saveInfos.localSave,u'Saves\\'
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
        newSaves = u'Saves\\%s\\' % (profile,)
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
        arcPath,newPath = (bosh.dirs['saveBase'].join(saves)
            for saves in (arcSaves,newSaves))
        #--Archive old Saves
        bosh.modInfos.plugins.copyTo(arcPath)
        bosh.modInfos.plugins.copyFrom(newPath)

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
        menuItem = wx.MenuItem(menu,self.id,_(u'Load Masters'))
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
        menuItem = wx.MenuItem(menu,self.id,_(u'Import Face...'))
        menu.AppendItem(menuItem)
        if len(data) != 1: menuItem.Enable(False)

    def Execute(self,event):
        #--File Info
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        #--Select source face file
        srcDir = fileInfo.dir
        wildcard = _(u'%s Files')%bush.game.displayName+u' (*.esp;*.esm;*.ess;*.esr)|*.esp;*.esm;*.ess;*.esr'
        #--File dialog
        srcPath = balt.askOpen(self.window,_(u'Face Source:'),srcDir, u'', wildcard,mustExist=True)
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
        with balt.Progress(srcName.s) as progress:
            saveFile = bosh.SaveFile(srcInfo)
            saveFile.load(progress)
            progress.Destroy()
            srcFaces = bosh.PCFaces.save_getFaces(saveFile)
            #--Dialog
            dialog = ImportFaceDialog(self.window,-1,srcName.s,fileInfo,srcFaces)
            dialog.ShowModal()
            dialog.Destroy()

    def FromMod(self,fileInfo,srcPath):
        """Import from a mod."""
        #--Get faces
        srcDir,srcName = GPath(srcPath).headTail
        srcInfo = bosh.ModInfo(srcDir,srcName)
        srcFaces = bosh.PCFaces.mod_getFaces(srcInfo)
        #--No faces to import?
        if not srcFaces:
            balt.showOk(self.window,_(u'No player (PC) faces found in %s.') % srcName.s,srcName.s)
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
        menuItem = wx.MenuItem(menu,self.id,_(u'Rename Player...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) != 0)

    def Execute(self,event):
        saveInfo = bosh.saveInfos[self.data[0]]
        newName = balt.askText(self.window,_(u"Enter new player name. E.g. Conan the Bold"),
            _(u"Rename player"),saveInfo.header.pcName)
        if not newName: return
        for save in self.data:
            savedPlayer = bosh.Save_NPCEdits(self.window.data[GPath(save)])
            savedPlayer.renamePlayer(newName)
        bosh.saveInfos.refresh()
        self.window.RefreshUI()

class Save_ExportScreenshot(Link):
    """exports the saved screenshot from a save game."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Export Screenshot...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) == 1)

    def Execute(self,event):
        saveInfo = bosh.saveInfos[self.data[0]]
        imagePath = balt.askSave(bashFrame,_(u'Save Screenshot as:'), bosh.dirs['patches'].s,_(u'Screenshot %s.jpg') % self.data[0].s,u'*.jpg')
        if not imagePath: return
        width,height,data = saveInfo.header.image
        image = wx.EmptyImage(width,height)
        image.SetData(data)
        image.SaveFile(imagePath.s,wx.BITMAP_TYPE_JPEG)

#------------------------------------------------------------------------------
class Save_DiffMasters(Link):
    """Shows how saves masters differ from active mod list."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Diff Masters...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) in (1,2))

    def Execute(self,event):
        oldNew = map(GPath,self.data)
        oldNew.sort(key = lambda x: bosh.saveInfos.dir.join(x).mtime)
        oldName = oldNew[0]
        oldInfo = self.window.data[GPath(oldName)]
        oldMasters = set(oldInfo.masterNames)
        if len(self.data) == 1:
            newName = GPath(_(u'Active Masters'))
            newMasters = set(bosh.modInfos.ordered)
        else:
            newName = oldNew[1]
            newInfo = self.window.data[GPath(newName)]
            newMasters = set(newInfo.masterNames)
        missing = oldMasters - newMasters
        extra = newMasters - oldMasters
        if not missing and not extra:
            message = _(u'Masters are the same.')
            balt.showInfo(self.window,message,_(u'Diff Masters'))
        else:
            message = u''
            if missing:
                message += u'=== '+_(u'Removed Masters')+u' (%s):\n* ' % oldName.s
                message += u'\n* '.join(x.s for x in bosh.modInfos.getOrdered(missing))
                if extra: message += u'\n\n'
            if extra:
                message += u'=== '+_(u'Added Masters')+u' (%s):\n* ' % newName.s
                message += u'\n* '.join(x.s for x in bosh.modInfos.getOrdered(extra))
            balt.showWryeLog(self.window,message,_(u'Diff Masters'))

#------------------------------------------------------------------------------
class Save_Rename(Link):
    """Renames Save File."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Rename...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) != 0)

    def Execute(self,event):
        if len(self.data) > 0:
            index = self.window.list.FindItem(0,self.data[0].s)
            if index != -1:
                self.window.list.EditLabel(index)

#------------------------------------------------------------------------------
class Save_Renumber(Link):
    """Renamumbers a whole lot of save files."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Re-number Save(s)...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) != 0)

    def Execute(self,event):
        #--File Info
        newNumber = balt.askNumber(self.window,_(u"Enter new number to start numbering the selected saves at."),
            prompt=_(u'Save Number'),title=_(u'Re-number Saves'),value=1,min=1,max=10000)
        if not newNumber: return
        rePattern = re.compile(ur'^(save )(\d*)(.*)',re.I|re.U)
        for index, name in enumerate(self.data):
            maPattern = rePattern.match(name.s)
            if not maPattern: continue
            maPattern = maPattern.groups()
            if not maPattern[1]: continue
            newFileName = u"%s%d%s" % (maPattern[0],newNumber,maPattern[2])
            if newFileName != name.s:
                oldPath = bosh.saveInfos.dir.join(name.s)
                newPath = bosh.saveInfos.dir.join(newFileName)
                if not newPath.exists():
                    oldPath.moveTo(newPath)
                    if GPath(oldPath.s[:-3]+bush.game.se.shortName.lower()).exists():
                        GPath(oldPath.s[:-3]+bush.game.se.shortName.lower()).moveTo(GPath(newPath.s[:-3]+bush.game.se.shortName.lower()))
                    if GPath(oldPath.s[:-3]+u'pluggy').exists():
                        GPath(oldPath.s[:-3]+u'pluggy').moveTo(GPath(newPath.s[:-3]+u'pluggy'))
                newNumber += 1
        bosh.saveInfos.refresh()
        self.window.RefreshUI()

#------------------------------------------------------------------------------
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
                record_full = record.full
                if record_full not in data: data[record_full] = (record_full,[])
                data[record_full][1].append(record)
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
        buff = StringIO.StringIO()
        name,records = self.data[item]
        record = records[0]
        #--Armor, clothing, weapons
        if record.recType == 'ARMO':
            buff.write(_(u'Armor')+u'\n'+_(u'Flags: '))
            buff.write(u', '.join(record.flags.getTrueAttrs())+u'\n')
            for attr in ('strength','value','weight'):
                buff.write(u'%s: %s\n' % (attr,getattr(record,attr)))
        elif record.recType == 'CLOT':
            buff.write(_(u'Clothing')+u'\n'+_(u'Flags: '))
            buff.write(u', '.join(record.flags.getTrueAttrs())+u'\n')
        elif record.recType == 'WEAP':
            buff.write(bush.game.weaponTypes[record.weaponType]+u'\n')
            for attr in ('damage','value','speed','reach','weight'):
                buff.write(u'%s: %s\n' % (attr,getattr(record,attr)))
        #--Enchanted? Switch record to enchantment.
        if hasattr(record,'enchantment') and record.enchantment in self.enchantments:
            buff.write(u'\n'+_(u'Enchantment:')+u'\n')
            record = self.enchantments[record.enchantment].getTypeCopy()
        #--Magic effects
        if record.recType in ('ALCH','SPEL','ENCH'):
            buff.write(record.getEffectsSummary())
        #--Done
        ret = buff.getvalue()
        buff.close()
        return ret

    def rename(self,oldName,newName):
        """Renames oldName to newName."""
        #--Right length?
        if len(newName) == 0:
            return False
        elif len(newName) > 128:
            balt.showError(self.parent,_(u'Name is too long.'))
            return False
        elif newName in self.data:
            balt.showError(self.parent,_(u'Name is already used.'))
            return False
        #--Rename
        self.data[newName] = self.data.pop(oldName)
        self.changed = True
        return newName

    def save(self):
        """Handles save button."""
        if not self.changed:
            balt.showOk(self.parent,_(u'No changes made.'))
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
            balt.showOk(self.parent, _(u'Names modified: %d.') % count,self.saveFile.fileInfo.name.s)

#------------------------------------------------------------------------------
class Save_EditCreated(Link):
    """Allows user to rename custom items (spells, enchantments, etc)."""
    menuNames = {'ENCH':_(u'Rename Enchanted...'),
                 'SPEL':_(u'Rename Spells...'),
                 'ALCH':_(u'Rename Potions...')
                 }
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
        with balt.Progress(_(u"Loading...")) as progress:
            saveFile = bosh.SaveFile(fileInfo)
            saveFile.load(progress)
        #--No custom items?
        recordTypes = Save_EditCreated.recordTypes.get(self.type,(self.type,))
        records = [record for record in saveFile.created if record.recType in recordTypes]
        if not records:
            balt.showOk(self.window,_(u'No items to edit.'))
            return
        #--Open editor dialog
        data = Save_EditCreatedData(self.window,saveFile,recordTypes)
        dialog = balt.ListEditor(self.window,-1,self.menuName,data)
        dialog.ShowModal()
        dialog.Destroy()

#------------------------------------------------------------------------------
class Save_EditPCSpellsData(balt.ListEditorData):
    """Data capsule for pc spell editing dialog."""
    def __init__(self,parent,saveInfo):
        """Initialize."""
        self.saveSpells = bosh.SaveSpells(saveInfo)
        with balt.Progress(_(u'Loading Masters')) as progress:
            self.saveSpells.load(progress)
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
        menuItem = wx.MenuItem(menu,self.id,_(u'Delete Spells...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) == 1)

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        data = Save_EditPCSpellsData(self.window,fileInfo)
        dialog = balt.ListEditor(self.window,wx.ID_ANY,_(u'Player Spells'),data)
        dialog.ShowModal()
        dialog.Destroy()

#------------------------------------------------------------------------------
class Save_EditCreatedEnchantmentCosts(Link):
    """Dialogue and Menu for setting number of uses for Cast When Used Enchantments."""
    def AppendToMenu(self,menu,window,data):
        """Append to menu."""
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Set Number of Uses for Weapon Enchantments...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) == 1)

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        dialog = balt.askNumber(self.window,
            (_(u'Enter the number of uses you desire per recharge for all custom made enchantments.')
             + u'\n' +
             _(u'(Enter 0 for unlimited uses)')),
            prompt=_(u'Uses'),title=_(u'Number of Uses'),value=50,min=0,max=10000)
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
        menuItem = wx.MenuItem(menu,self.idList.DEFAULT,_(u'Default'),kind=wx.ITEM_CHECK)
        menu.AppendItem(menuItem)
        menuItem.Enable(localSave != u'Saves\\')
        for id,item in zip(self.idList,self.GetItems()):
            menuItem = wx.MenuItem(menu,id,item,kind=wx.ITEM_CHECK)
            menu.AppendItem(menuItem)
            menuItem.Enable(localSave != (u'Saves\\'+item+u'\\'))
        #--Events
        wx.EVT_MENU(bashFrame,self.idList.DEFAULT,self.DoDefault)
        wx.EVT_MENU_RANGE(bashFrame,self.idList.BASE,self.idList.MAX,self.DoList)

    def DoDefault(self,event):
        """Handle selection of Default."""
        self.MoveFiles(_(u'Default'))

    def DoList(self,event):
        """Handle selection of label."""
        profile = self.GetItems()[event.GetId()-self.idList.BASE]
        self.MoveFiles(profile)

    def MoveFiles(self,profile):
        fileInfos = self.window.data
        destDir = bosh.dirs['saveBase'].join(u'Saves')
        if profile != _(u'Default'):
            destDir = destDir.join(profile)
        if destDir == fileInfos.dir:
            balt.showError(self.window,_(u"You can't move saves to the current profile!"))
            return
        savesTable = bosh.saveInfos.table
        #--bashDir
        destTable = bolt.Table(bosh.PickleDict(destDir.join('Bash','Table.dat')))
        count = 0
        ask = True
        for fileName in self.data:
            if ask and not self.window.data.moveIsSafe(fileName,destDir):
                message = (_(u'A file named %s already exists in %s. Overwrite it?')
                    % (fileName.s,profile))
                result = balt.askContinueShortTerm(self.window,message,_(u'Move File'))
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
            balt.showInfo(self.window,_(u'%d files copied to %s.') % (count,profile),_(u'Copy File'))

#------------------------------------------------------------------------------
class Save_RepairAbomb(Link):
    """Repairs animation slowing by resetting counter(?) at end of TesClass data."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Repair Abomb'))
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
            balt.showOk(self.window,_(u'Abomb counter is too low to reset.'),_(u'Repair Abomb'))
            return
        message = (_(u"Reset Abomb counter? (Current progress: %.0f%%.)")
                   + u'\n\n' +
                   _(u"Note: Abomb animation slowing won't occur until progress is near 100%%.")
                   ) % progress
        if balt.askYes(self.window,message,_(u'Repair Abomb'),default=False):
            saveFile.setAbomb(newCounter)
            saveFile.safeSave()
            balt.showOk(self.window,_(u'Abomb counter reset.'),_(u'Repair Abomb'))

#------------------------------------------------------------------------------
## TODO: This is probably unneccessary now.  v105 was a long time ago
class Save_RepairFactions(Link):
    """Repair factions from v 105 Bash error, plus mod faction changes."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Repair Factions'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(bosh.modInfos.ordered) and len(data) == 1)

    def Execute(self,event):
        debug = False
        message = (_(u'This will (mostly) repair faction membership errors due to Wrye Bash v 105 bug and/or faction changes in underlying mods.')
                   + u'\n\n' +
                   _(u'WARNING!  This repair is NOT perfect!  Do not use it unless you have to!')
                   )
        if not balt.askContinue(self.window,message,
                'bash.repairFactions.continue',_(u'Repair Factions')):
            return
        question = _(u"Restore dropped factions too?  WARNING:  This may involve clicking through a LOT of yes/no dialogs.")
        restoreDropped = balt.askYes(self.window, question, _(u'Repair Factions'),default=False)
        legitNullSpells = bush.repairFactions_legitNullSpells
        legitNullFactions = bush.repairFactions_legitNullFactions
        legitDroppedFactions = bush.repairFactions_legitDroppedFactions
        with balt.Progress(_(u'Repair Factions')) as progress:
            #--Loop over active mods
            log = bolt.LogFile(StringIO.StringIO())
            offsetFlag = 0x80
            npc_info = {}
            fact_eid = {}
            loadFactory = bosh.LoadFactory(False,bosh.MreRecord.type_class['NPC_'],
                                                 bosh.MreRecord.type_class['FACT'])
            ordered = list(bosh.modInfos.ordered)
            subProgress = SubProgress(progress,0,0.4,len(ordered))
            for index,modName in enumerate(ordered):
                subProgress(index,_(u'Scanning ') + modName.s)
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
            message = _(u'NPC Factions Restored/UnNulled:')
            for index,saveName in enumerate(self.data):
                log.setHeader(u'== '+saveName.s,True)
                subProgress(index,_(u'Updating ') + saveName.s)
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
                        log(u'. %08X %s -- ' % (recId,eid) + _(u'Factions'))
                        npc.factions = None
                        unFactioned = True
                    if recFlags.modifiers and not npc.modifiers:
                        log(u'. %08X %s -- ' % (recId,eid) + _(u'Modifiers'))
                        npc.modifiers = None
                        unModified = True
                    if recFlags.spells and not npc.spells and recId not in legitNullSpells:
                        log(u'. %08X %s -- ' % (recId,eid) + _(u'Spells'))
                        npc.spells = None
                        unSpelled = True
                    unNulled = (unFactioned or unSpelled or unModified)
                    unNulledCount += (0,1)[unNulled]
                    #--Player, player faction
                    if recId == 7:
                        playerStartSpell = saveFile.getIref(0x00000136)
                        if npc.spells is not None and playerStartSpell not in npc.spells:
                            log(u'. %08X %s -- **%s**' % (recId,eid._(u'DefaultPlayerSpell')))
                            npc.spells.append(playerStartSpell)
                            refactioned = True #--I'm lying, but... close enough.
                        playerFactionIref = saveFile.getIref(0x0001dbcd)
                        if (npc.factions is not None and
                            playerFactionIref not in [iref for iref,level in npc.factions]
                            ):
                                log(u'. %08X %s -- **%s**' % (recId,eid,_(u'PlayerFaction, 0')))
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
                                    question = _(u'Restore %s to %s faction?') % (npcEid,factEid)
                                    deprint(_(u'refactioned') +u' %08X %08X %s %s' % (recId,fid,npcEid,factEid))
                                    if not balt.askYes(self.window, question, saveName.s,default=False):
                                        continue
                                    log(u'. %08X %s -- **%s, %d**' % (recId,eid,factEid,level))
                                    npc.factions.append((iref,level))
                                    refactioned = True
                    refactionedCount += (0,1)[refactioned]
                    #--Save record changes?
                    if unNulled or refactioned:
                        saveFile.records[recNum] = (recId,recType,npc.getFlags(),version,npc.getData())
                #--Save changes?
                subProgress(index+0.5,_(u'Updating ') + saveName.s)
                if unNulledCount or refactionedCount:
                    saveFile.safeSave()
                message += u'\n%d %d %s' % (refactionedCount,unNulledCount,saveName.s,)
        balt.showWryeLog(self.window,log.out.getvalue(),_(u'Repair Factions'),icons=bashBlue)
        log.out.close()

#------------------------------------------------------------------------------
class Save_RepairHair(Link):
    """Repairs hair that has been zeroed due to removal of a hair mod."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Repair Hair'))
        menu.AppendItem(menuItem)
        if len(data) != 1: menuItem.Enable(False)

    def Execute(self,event):
        #--File Info
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        if bosh.PCFaces.save_repairHair(fileInfo):
            balt.showOk(self.window,_(u'Hair repaired.'))
        else:
            balt.showOk(self.window,_(u'No repair necessary.'),fileName.s)

#------------------------------------------------------------------------------
class Save_ReweighPotions(Link):
    """Changes weight of all player potions to specified value."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Reweigh Potions...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) == 1)

    def Execute(self,event):
        #--Query value
        result = balt.askText(self.window,
            _(u"Set weight of all player potions to..."),
            _(u"Reweigh Potions"),
            u'%0.2f' % (settings.get('bash.reweighPotions.newWeight',0.2),))
        if not result: return
        try:
            newWeight = float(result.strip())
            if newWeight < 0 or newWeight > 100:
                raise Exception('')
        except:
            balt.showOk(self.window,_(u'Invalid weight: %s') % newWeight)
            return
        settings['bash.reweighPotions.newWeight'] = newWeight
        #--Do it
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        with balt.Progress(_(u"Reweigh Potions")) as progress:
            saveFile = bosh.SaveFile(fileInfo)
            saveFile.load(SubProgress(progress,0,0.5))
            count = 0
            progress(0.5,_(u"Processing."))
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
                balt.showOk(self.window,_(u'Potions reweighed: %d.') % count,fileName.s)
            else:
                progress.Destroy()
                balt.showOk(self.window,_(u'No potions to reweigh!'),fileName.s)

#------------------------------------------------------------------------------
class Save_Stats(Link):
    """Show savefile statistics."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Statistics'))
        menu.AppendItem(menuItem)
        if len(data) != 1: menuItem.Enable(False)

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        saveFile = bosh.SaveFile(fileInfo)
        with balt.Progress(_(u"Statistics")) as progress:
            saveFile.load(SubProgress(progress,0,0.9))
            log = bolt.LogFile(StringIO.StringIO())
            progress(0.9,_(u"Calculating statistics."))
            saveFile.logStats(log)
            progress.Destroy()
            text = log.out.getvalue()
            balt.showLog(self.window,text,fileName.s,asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class Save_StatObse(Link):
    """Dump .obse records."""
    def AppendToMenu(self,menu,window,data):
        if bush.game.se.shortName == '': return
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'.%s Statistics') % bush.game.se.shortName.lower())
        menu.AppendItem(menuItem)
        if len(data) != 1:
            menuItem.Enable(False)
        else:
            fileName = GPath(self.data[0])
            fileInfo = self.window.data[fileName]
            fileName = fileInfo.getPath().root+u'.'+bush.game.se.shortName
            menuItem.Enable(fileName.exists())

    def Execute(self,event):
        fileName = GPath(self.data[0])
        fileInfo = self.window.data[fileName]
        saveFile = bosh.SaveFile(fileInfo)
        with balt.Progress(u'.'+bush.game.se.shortName) as progress:
            saveFile.load(SubProgress(progress,0,0.9))
            log = bolt.LogFile(StringIO.StringIO())
            progress(0.9,_(u"Calculating statistics."))
            saveFile.logStatObse(log)
        text = log.out.getvalue()
        log.out.close()
        balt.showLog(self.window,text,fileName.s,asDialog=False,fixedFont=False,icons=bashBlue)

#------------------------------------------------------------------------------
class Save_Unbloat(Link):
    """Unbloats savegame."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Remove Bloat...'))
        menu.AppendItem(menuItem)
        if len(data) != 1: menuItem.Enable(False)

    def Execute(self,event):
        #--File Info
        saveName = GPath(self.data[0])
        saveInfo = self.window.data[saveName]
        delObjRefs = 0
        with balt.Progress(_(u'Scanning for Bloat')) as progress:
            #--Scan and report
            saveFile = bosh.SaveFile(saveInfo)
            saveFile.load(SubProgress(progress,0,0.8))
            createdCounts,nullRefCount = saveFile.findBloating(SubProgress(progress,0.8,1.0))
        #--Dialog
        if not createdCounts and not nullRefCount:
            balt.showOk(self.window,_(u'No bloating found.'),saveName.s)
            return
        message = u''
        if createdCounts:
            for type,name in sorted(createdCounts):
                message += u'  %s %s: %s\n' % (type,name,formatInteger(createdCounts[(type,name)]))
        if nullRefCount:
            message += u'  '+_(u'Null Ref Objects:')+ u' %s\n' % formatInteger(nullRefCount)
        message = (_(u'Remove savegame bloating?')
                   + u'\n'+message+u'\n' +
                   _(u'WARNING: This is a risky procedure that may corrupt your savegame!  Use only if necessary!')
                   )
        if not balt.askYes(self.window,message,_(u'Remove bloating?')):
            return
        #--Remove bloating
        with balt.Progress(_(u'Removing Bloat')) as progress:
            nums = saveFile.removeBloating(createdCounts.keys(),True,SubProgress(progress,0,0.9))
            progress(0.9,_(u'Saving...'))
            saveFile.safeSave()
        balt.showOk(self.window,
            (_(u'Uncreated Objects: %d')
             + u'\n' +
             _(u'Uncreated Refs: %d')
             + u'\n' +
             _(u'UnNulled Refs: %d')
             ) % nums,
            saveName.s)
        self.window.RefreshUI(saveName)

#------------------------------------------------------------------------------
class Save_UpdateNPCLevels(Link):
    """Update NPC levels from active mods."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Update NPC Levels...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(data and bosh.modInfos.ordered))

    def Execute(self,event):
        debug = True
        message = _(u'This will relevel the NPCs in the selected save game(s) according to the npc levels in the currently active mods.  This supersedes the older "Import NPC Levels" command.')
        if not balt.askContinue(self.window,message,'bash.updateNpcLevels.continue',_(u'Update NPC Levels')):
            return
        with balt.Progress(_(u'Update NPC Levels')) as progress:
            #--Loop over active mods
            offsetFlag = 0x80
            npc_info = {}
            loadFactory = bosh.LoadFactory(False,bosh.MreRecord.type_class['NPC_'])
            ordered = list(bosh.modInfos.ordered)
            subProgress = SubProgress(progress,0,0.4,len(ordered))
            modErrors = []
            for index,modName in enumerate(ordered):
                subProgress(index,_(u'Scanning ') + modName.s)
                modInfo = bosh.modInfos[modName]
                modFile = bosh.ModFile(modInfo,loadFactory)
                try:
                    modFile.load(True)
                except bosh.ModError, x:
                    modErrors.append(u'%s'%x)
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
            message = _(u'NPCs Releveled:')
            for index,saveName in enumerate(self.data):
                subProgress(index,_(u'Updating ') + saveName.s)
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
                #--Save changes?
                subProgress(index+0.5,_(u'Updating ') + saveName.s)
                if releveledCount:
                    saveFile.safeSave()
                message += u'\n%d %s' % (releveledCount,saveName.s)
        if modErrors:
            message += u'\n\n'+_(u'Some mods had load errors and were skipped:')+u'\n* '
            message += u'\n* '.join(modErrors)
        balt.showOk(self.window,message,_(u'Update NPC Levels'))

# Screen Links ----------------------------------------------------------------
#------------------------------------------------------------------------------
class Screens_NextScreenShot(Link):
    """Sets screenshot base name and number."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Next Shot...'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        oblivionIni = bosh.oblivionIni
        base = oblivionIni.getSetting(u'Display',u'sScreenShotBaseName',u'ScreenShot')
        next = oblivionIni.getSetting(u'Display',u'iScreenShotIndex',u'0')
        rePattern = re.compile(ur'^(.+?)(\d*)$',re.I|re.U)
        pattern = balt.askText(self.window,(_(u"Screenshot base name, optionally with next screenshot number.")
                                            + u'\n' +
                                            _(u"E.g. ScreenShot or ScreenShot_101 or Subdir\\ScreenShot_201.")
                                            ),_(u"Next Shot..."),base+next)
        if not pattern: return
        maPattern = rePattern.match(pattern)
        newBase,newNext = maPattern.groups()
        settings = {LString(u'Display'):{
            LString(u'SScreenShotBaseName'): newBase,
            LString(u'iScreenShotIndex'): (newNext or next),
            LString(u'bAllowScreenShot'): u'1',
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
        menuItem = wx.MenuItem(menu,self.id,_(u'Convert to %s') % self.ext)
        menu.AppendItem(menuItem)
        convertable = [name for name in self.data if GPath(name).cext != u'.'+self.ext]
        menuItem.Enable(len(convertable) > 0)

    def Execute(self,event):
        srcDir = bosh.screensData.dir
        try:
            with balt.Progress(_(u"Converting to %s") % self.ext) as progress:
                progress.setFull(len(self.data))
                for index,fileName in enumerate(self.data):
                    progress(index,fileName.s)
                    srcPath = srcDir.join(fileName)
                    destPath = srcPath.root+u'.'+self.ext
                    if srcPath == destPath or destPath.exists(): continue
                    bitmap = wx.Image(srcPath.s)
                    # This only has an effect on jpegs, so it's ok to do it on every kind
                    bitmap.SetOptionInt(wx.IMAGE_OPTION_QUALITY,settings['bash.screens.jpgQuality'])
                    result = bitmap.SaveFile(destPath.s,self.imageType)
                    if not result: continue
                    srcPath.remove()
        finally:
            self.window.data.refresh()
            self.window.RefreshUI()

#------------------------------------------------------------------------------
class Screen_JpgQuality(Link):
    """Sets JPEG quality for saving."""
    def __init__(self,quality):
        Link.__init__(self)
        self.quality = quality
        self.label = u'%i' % self.quality

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
        self.label = _(u'Custom [%i]') % self.quality

    def Execute(self,event):
        quality = balt.askNumber(self.window,_(u'JPEG Quality'),value=self.quality,min=0,max=100)
        if quality is None: return
        self.quality = quality
        settings['bash.screens.jpgCustomQuality'] = self.quality
        self.label = _(u'Custom [%i]') % quality
        Screen_JpgQuality.Execute(self,event)

#------------------------------------------------------------------------------
class Screen_Rename(Link):
    """Renames files by pattern."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Rename...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(data) > 0)

    def Execute(self,event):
        if len(self.data) > 0:
            index = self.window.list.FindItem(0,self.data[0].s)
            if index != -1:
                self.window.list.EditLabel(index)

# Messages Links --------------------------------------------------------------
#------------------------------------------------------------------------------
class Messages_Archive_Import(Link):
    """Import messages from html message archive."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Import Archives...'))
        menu.AppendItem(menuItem)

    def Execute(self,event):
        textDir = settings.get('bash.workDir',bosh.dirs['app'])
        #--File dialog
        paths = balt.askOpenMulti(self.window,_(u'Import message archive(s):'),textDir,
            u'', u'*.html')
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
        menu.AppendItem(wx.MenuItem(menu,self.id,_(u'Delete')))

    def Execute(self,event):
        message = _(u'Delete these %d message(s)? This operation cannot be undone.') % len(self.data)
        if not balt.askYes(self.window,message,_(u'Delete Messages')):
            return
        #--Do it
        for message in self.data:
            self.window.data.delete(message)
        #--Refresh stuff
        self.window.RefreshUI()

# People Links ----------------------------------------------------------------
#------------------------------------------------------------------------------
class People_AddNew(Link):
    """Add a new record."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Add...'))
        menu.AppendItem(menuItem)
        self.title = _(u'Add New Person')

    def Execute(self,event):
        name = balt.askText(self.gTank,_(u"Add new person:"),self.title)
        if not name: return
        if name in self.data:
            return balt.showInfo(self.gTank,name+_(u" already exists."),self.title)
        self.data[name] = (time.time(),0,u'')
        self.gTank.RefreshUI(details=name)
        self.gTank.gList.EnsureVisible(self.gTank.GetIndex(name))
        self.data.setChanged()

#------------------------------------------------------------------------------
class People_Export(Link):
    """Export people to text archive."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Export...'))
        menu.AppendItem(menuItem)
        self.title = _(u"Export People")

    def Execute(self,event):
        textDir = settings.get('bash.workDir',bosh.dirs['app'])
        #--File dialog
        path = balt.askSave(self.gTank,_(u'Export people to text file:'),textDir,
            u'People.txt', u'*.txt')
        if not path: return
        settings['bash.workDir'] = path.head
        self.data.dumpText(path,self.selected)
        balt.showInfo(self.gTank,_(u'Records exported: %d.') % len(self.selected),self.title)

#------------------------------------------------------------------------------
class People_Import(Link):
    """Import people from text archive."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Import...'))
        menu.AppendItem(menuItem)
        self.title = _(u"Import People")

    def Execute(self,event):
        textDir = settings.get('bash.workDir',bosh.dirs['app'])
        #--File dialog
        path = balt.askOpen(self.gTank,_(u'Import people from text file:'),textDir,
            u'', u'*.txt',mustExist=True)
        if not path: return
        settings['bash.workDir'] = path.head
        newNames = self.data.loadText(path)
        balt.showInfo(self.gTank,_(u"People imported: %d") % len(newNames),self.title)
        self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class People_Karma(Link):
    """Add Karma setting links."""

    def AppendToMenu(self,menu,window,data):
        """Append Karma item submenu."""
        Link.AppendToMenu(self,menu,window,data)
        idList = ID_GROUPS
        labels = [u'%+d'%x for x in xrange(5,-6,-1)]
        subMenu = wx.Menu()
        for id,item in zip(idList,labels):
            subMenu.Append(id,item)
        wx.EVT_MENU_RANGE(bashFrame,idList.BASE,idList.MAX,self.DoList)
        menu.AppendMenu(-1,_(u'Karma'),subMenu)

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
        menuItem = wx.MenuItem(menu,self.id,_(u"Change to..."))
        menu.AppendItem(menuItem)
        menuItem.Enable(self.window.edited)

    def Execute(self,event):
        itemId = self.data[0]
        masterInfo = self.window.data[itemId]
        masterName = masterInfo.name
        #--File Dialog
        wildcard = _(u'%s Mod Files')%bush.game.displayName+u' (*.esp;*.esm)|*.esp;*.esm'
        newPath = balt.askOpen(self.window,_(u'Change master name to:'),
            bosh.modInfos.dir, masterName, wildcard,mustExist=True)
        if not newPath: return
        (newDir,newName) = newPath.headTail
        #--Valid directory?
        if newDir != bosh.modInfos.dir:
            balt.showError(self.window,
                _(u"File must be selected from Oblivion Data Files directory."))
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
        menuItem = wx.MenuItem(menu,self.id,_(u"Disable"))
        menu.AppendItem(menuItem)
        menuItem.Enable(self.window.edited)

    def Execute(self,event):
        itemId = self.data[0]
        masterInfo = self.window.data[itemId]
        masterName = masterInfo.name
        newName = GPath(re.sub(u'[mM]$','p',u'XX'+masterName.s))
        #--Save Name
        masterInfo.setName(newName)
        self.window.ReList()
        self.window.PopulateItems()

# App Links -------------------------------------------------------------------
#------------------------------------------------------------------------------
class StatusBar_Button(Link):
    """Launch an application."""
    def __init__(self,uid=None,canHide=True,tip=u''):
        """ui: Unique identifier, used for saving the order of status bar icons
               and whether they are hidden/shown.
           canHide: True if this button is allowed to be hidden."""
        Link.__init__(self)
        self.mainMenu = Links()
        self.canHide = canHide
        self.gButton = None
        self._tip = tip
        if uid is None: uid = (self.__class__.__name__,tip)
        self.uid = uid

    def createButton(self, *args, **kwdargs):
        if len(args) < 11 and 'onRClick' not in kwdargs:
            kwdargs['onRClick'] = self.DoPopupMenu
        if len(args) < 9 and 'onClick' not in kwdargs:
            kwdargs['onClick'] = self.Execute
        if self.gButton is not None:
            self.gButton.Destroy()
        self.gButton = bitmapButton(*args, **kwdargs)
        return self.gButton

    def DoPopupMenu(self,event):
        if self.canHide:
            if len(self.mainMenu) == 0 or not isinstance(self.mainMenu[-1],StatusBar_Hide):
                if len(self.mainMenu) > 0:
                    self.mainMenu.append(SeparatorLink())
                self.mainMenu.append(StatusBar_Hide())
        if len(self.mainMenu) > 0:
            self.mainMenu.PopupMenu(self.gButton,bashFrame,0)
        else:
            event.Skip()

    # Helper function to get OBSE version
    @property
    def obseVersion(self):
        if bosh.inisettings['SteamInstall']:
            file = bush.game.se.steamExe
        else:
            file = bush.game.se.exe
        version = bosh.dirs['app'].join(file).strippedVersion
        return u'.'.join([u'%s'%x for x in version])

#------------------------------------------------------------------------------
class App_Button(StatusBar_Button):
    """Launch an application."""
    obseButtons = []

    @property
    def version(self):
        if not self.isJava and self.IsPresent():
            version = self.exePath.strippedVersion
            if version != (0,):
                version = u'.'.join([u'%s'%x for x in version])
                return version
        return ''

    @property
    def tip(self):
        if not settings['bash.statusbar.showversion']: return self._tip
        else:
            return self._tip + u' ' + self.version

    @property
    def obseTip(self):
        if self._obseTip is not None:
            if not settings['bash.statusbar.showversion']: return self._obseTip % (dict(version=u''))
            else: return self._obseTip % (dict(version=self.version))
        else: return None

    @staticmethod
    def getJava():
        # Locate Java executable
        win = GPath(os.environ['SYSTEMROOT'])
        # Default location: Windows\System32\javaw.exe
        java = win.join(u'system32', u'javaw.exe')
        if not java.exists():
            # 1st possibility:
            #  - Bash is running as 32-bit
            #  - The only Java installed is 64-bit
            # Because Bash is 32-bit, Windows\System32 redirects to
            # Windows\SysWOW64.  So look in the ACTUAL System32 folder
            # by using Windows\SysNative
            java = win.join(u'sysnative', u'javaw.exe')
        if not java.exists():
            # 2nd possibility
            #  - Bash is running as 64-bit
            #  - The only Java installed is 32-bit
            # So javaw.exe would actually be in Windows\SysWOW64
            java = win.join(u'syswow64', u'javaw.exe')
        return java

    def __init__(self,exePathArgs,images,tip,obseTip=None,obseArg=None,workingDir=None,uid=None,canHide=True):
        """Initialize
        exePathArgs (string): exePath
        exePathArgs (tuple): (exePath,*exeArgs)
        exePathArgs (list):  [exePathArgs,altExePathArgs,...]
        images: [16x16,24x24,32x32] images
        """
        StatusBar_Button.__init__(self,uid,canHide,tip)
        if isinstance(exePathArgs, list):
            use = exePathArgs[0]
            for item in exePathArgs:
                if isinstance(item, tuple):
                    exePath = item[0]
                else:
                    exePath = item
                if exePath.exists():
                    # Use this one
                    use = item
                    break
            exePathArgs = use
        if isinstance(exePathArgs,tuple):
            self.exePath = exePathArgs[0]
            self.exeArgs = exePathArgs[1:]
        else:
            self.exePath = exePathArgs
            self.exeArgs = tuple()
        self.images = images
        if workingDir:
            self.workingDir = GPath(workingDir)
        else:
            self.workingDir = None
        #--Exe stuff
        if self.exePath and self.exePath.cext == u'.exe': #Sometimes exePath is "None"
            self.isExe = True
        else:
            self.isExe = False
        #--Java stuff
        if self.exePath and self.exePath.cext == u'.jar': #Sometimes exePath is "None"
            self.isJava = True
            self.java = self.getJava()
            self.jar = self.exePath
            self.appArgs = u''.join(self.exeArgs)
        else:
            self.isJava = False
        #--shortcut
        if self.exePath and self.exePath.cext == u'.lnk': #Sometimes exePath is "None"
            self.isShortcut = True
        else:
            self.isShortcut = False
        #--Folder
        if self.exePath and self.exePath.isdir():
            self.isFolder = True
        else:
            self.isFolder = False
        #--**SE stuff
        self._obseTip = obseTip
        self.obseArg = obseArg
        exeObse = bosh.dirs['app'].join(bush.game.se.exe)

    def IsPresent(self):
        if self.isJava:
            return self.java.exists() and self.jar.exists()
        else:
            if self.exePath in bosh.undefinedPaths:
                return False
            return self.exePath.exists()

    def GetBitmapButton(self,window,style=0):
        if self.IsPresent():
            size = settings['bash.statusbar.iconSize']
            idex = (size/8)-2
            self.createButton(window,self.images[idex].GetBitmap(),
                              style=style,tip=self.tip)
            if self.obseTip is not None:
                App_Button.obseButtons.append(self)
                exeObse = bosh.dirs['app'].join(bush.game.se.exe)
                if settings.get('bash.obse.on',False) and exeObse.exists():
                    self.gButton.SetToolTip(tooltip(self.obseTip))
            return self.gButton
        else:
            return None

    def ShowError(self,error):
        balt.showError(bashFrame,
                       (u'%s'%error + u'\n\n' +
                        _(u'Used Path: ') + self.exePath.s + u'\n' +
                        _(u'Used Arguments: ') + u'%s' % (self.exeArgs,)),
                       _(u"Could not launch '%s'") % self.exePath.stail)

    def Execute(self,event,extraArgs=None,wait=False):
        if self.IsPresent():
            if self.isShortcut or self.isFolder:
                webbrowser.open(self.exePath.s)
            elif self.isJava:
                cwd = bolt.Path.getcwd()
                if self.workingDir:
                    self.workingDir.setcwd()
                else:
                    self.jar.head.setcwd()
                try:
                    subprocess.Popen((self.java.stail,u'-jar',self.jar.stail,self.appArgs), executable=self.java.s, close_fds=bolt.close_fds) #close_fds is needed for the one instance checker
                except UnicodeError:
                    balt.showError(bashFrame,
                                   _(u'Execution failed, because one or more of the command line arguments failed to encode.'),
                                   _(u"Could not launch '%s'") % self.exePath.stail)
                except Exception as error:
                    self.ShowError(error)
                finally:
                    cwd.setcwd()
            elif self.isExe:
                exeObse = bosh.dirs['app'].join(bush.game.se.exe)
                exeLaa = bosh.dirs['app'].join(bush.game.laa.exe)
                if exeLaa.exists() and settings.get('bash.laa.on',True) and self.exePath.tail == bush.game.exe:
                    # Should use the LAA Launcher
                    exePath = exeLaa
                    args = [exePath.s]
                elif self.obseArg is not None and settings.get('bash.obse.on',False) and exeObse.exists():
                    if bosh.inisettings['SteamInstall'] and self.exePath.tail == u'Oblivion.exe':
                        exePath = self.exePath
                    else:
                        exePath = exeObse
                    args = [exePath.s]
                    if self.obseArg != u'':
                        args.append(u'%s' % self.obseArg)
                else:
                    exePath = self.exePath
                    args = [exePath.s]
                args.extend(self.exeArgs)
                if extraArgs: args.extend(extraArgs)
                statusBar.SetStatusText(u' '.join(args[1:]),1)
                cwd = bolt.Path.getcwd()
                if self.workingDir:
                    self.workingDir.setcwd()
                else:
                    exePath.head.setcwd()
                try:
                    popen = subprocess.Popen(args, close_fds=bolt.close_fds) #close_fds is needed for the one instance checker
                    if wait:
                        popen.wait()
                except UnicodeError:
                    balt.showError(bashFrame,
                                   _(u'Execution failed, because one or more of the command line arguments failed to encode.'),
                                   _(u"Could not launch '%s'") % self.exePath.stail)
                except WindowsError as werr:
                    if werr.winerror != 740:
                        self.ShowError(werr)
                    try:
                        import win32api
                        win32api.ShellExecute(0,'runas',exePath.s,u'%s'%self.exeArgs,bosh.dirs['app'].s,1)
                    except:
                        self.ShowError(werr)
                except Exception as error:
                    self.ShowError(error)
                finally:
                    cwd.setcwd()
            else:
                try:
                    if self.workingDir:
                        dir = self.workingDir.s
                    else:
                        dir = bolt.Path.getcwd().s

                    import win32api
                    r, executable = win32api.FindExecutable(self.exePath.s)
                    executable = win32api.GetLongPathName(executable)
                    args = u'"%s"' % self.exePath.s
                    args += u' '.join([u'%s' % arg for arg in self.exeArgs])
                    win32api.ShellExecute(0,u"open",executable,args,dir,1)
                except Exception as error:
                    if isinstance(error,WindowsError) and error.winerror == 740:
                        # Requires elevated permissions
                        try:
                            import win32api
                            win32api.ShellExecute(0,'runas',executable,args,dir,1)
                        except Exception as error:
                            self.ShowError(error)
                    else:
                        # Most likely we're here because FindExecutable failed (no file association)
                        # Or because win32api import failed.  Try doing it using os.startfile
                        # ...Changed to webbrowser.open because os.startfile is windows specific and is not cross platform compatible
                        cwd = bolt.Path.getcwd()
                        if self.workingDir:
                            self.workingDir.setcwd()
                        else:
                            self.exePath.head.setcwd()
                        try:
                            webbrowser.open(self.exePath.s)
                        except UnicodeError:
                            balt.showError(bashFrame,
                                           _(u'Execution failed, because one or more of the command line arguments failed to encode.'),
                                           _(u"Could not launch '%s'") % self.exePath.stail)
                        except Exception as error:
                            self.ShowError(error)
                        finally:
                            cwd.setcwd()
        else:
            balt.showError(bashFrame,
                           _(u'Application missing: %s') % self.exePath.s,
                           _(u"Could not launch '%s'" % self.exePath.stail)
                           )

#------------------------------------------------------------------------------
class Tooldir_Button(App_Button):
    """Just an App_Button that's path is in bosh.tooldirs
       Use this to automatically set the uid for the App_Button."""
    def __init__(self,toolKey,images,tip,obseTip=None,obseArg=None,workingDir=None,canHide=True):
        App_Button.__init__(self,bosh.tooldirs[toolKey],images,tip,obseTip,obseArg,workingDir,toolKey,canHide)

#------------------------------------------------------------------------------
class App_Tes4Gecko(App_Button):
    """Left in for unpickling compatibility reasons."""
    def __setstate__(self, state):
        self.__dict__.update(state)
        self.__class__ = App_Button

#------------------------------------------------------------------------------
class App_Tes5Gecko(App_Button):
    """Left in for unpickling compatibility reasons."""
    def __setstate__(self, state):
        self.__dict__.update(state)
        self.__class__ = App_Button

#------------------------------------------------------------------------------
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
# -TES5
#  or name begins with TES5
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
    def __init__(self,*args,**kwdargs):
        App_Button.__init__(self,*args,**kwdargs)
        if bush.game.fsName == 'Skyrim':
            self.mainMenu.append(Mods_Tes5ViewExpert())
        elif bush.game.fsName == 'Oblivion' or bush.game.fsName == 'Nehrim':
            self.mainMenu.append(Mods_Tes4ViewExpert())

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
            extraArgs.append(u'-FixupPGRD')
        if wx.GetKeyState(wx.WXK_SHIFT):
            extraArgs.append(u'-skipbsa')
        if bush.game.fsName == 'Oblivion' or bush.game.fsName == 'Nehrim':
            if settings['tes4View.iKnowWhatImDoing']:
                extraArgs.append(u'-IKnowWhatImDoing')
        if bush.game.fsName == 'Skyrim':
            if settings['tes5View.iKnowWhatImDoing']:
                extraArgs.append(u'-IKnowWhatImDoing')
        App_Button.Execute(self,event,tuple(extraArgs))

#------------------------------------------------------------------------------
class App_BOSS(App_Button):
    """loads BOSS"""
    def __init__(self, *args, **kwdargs):
        App_Button.__init__(self, *args, **kwdargs)
        self.mainMenu.append(Mods_BOSSLaunchGUI())
        self.mainMenu.append(Mods_BOSSDisableLockTimes())

    def Execute(self,event,extraArgs=None):
        if settings['BOSS.UseGUI']:
            self.exePath = self.exePath.head.join(u'BOSS GUI.exe')
        if settings['BOSS.ClearLockTimes']:
            wait = True
        else:
            wait = False
        extraArgs = []
        if wx.GetKeyState(82) and wx.GetKeyState(wx.WXK_SHIFT):
            extraArgs.append(u'-r 2',) # Revert level 2 - BOSS version 1.6+
        elif wx.GetKeyState(82):
            extraArgs.append(u'-r 1',) # Revert level 1 - BOSS version 1.6+
        if wx.GetKeyState(83):
            extraArgs.append(u'-s',) # Silent Mode - BOSS version 1.6+
        if wx.GetKeyState(67): #c - print crc calculations in BOSS log.
            extraArgs.append(u'-c',)
        if bosh.tooldirs['boss'].version >= (2,0,0,0):
            # After version 2.0, need to pass in the -g argument
            extraArgs.append(u'-g%s' % bush.game.fsName,)
        App_Button.Execute(self,event,tuple(extraArgs), wait)
        if settings['BOSS.ClearLockTimes']:
            # Clear the saved times from before
            bosh.modInfos.mtimes.clear()
            # And refresh to get the new times so WB will keep the order that BOSS specifies
            bosh.modInfos.refresh(doInfos=False)
            # Refresh UI, so WB is made aware of the changes to loadorder.txt
            modList.RefreshUI('ALL')

#------------------------------------------------------------------------------
class Oblivion_Button(App_Button):
    """Will close app on execute if autoquit is on."""
    @property
    def tip(self):
        if not settings['bash.statusbar.showversion']:
            tip = self._tip
        else:
            tip = self._tip + u' ' + self.version
        if bosh.dirs['app'].join(bush.game.laa.exe).exists() and settings.get('bash.laa.on',True):
            tip += u' + ' + bush.game.laa.name
        return tip

    @property
    def obseTip(self):
        # Oblivion (version)
        if settings['bash.statusbar.showversion']:
            tip = self._obseTip % (dict(version=self.version))
        else:
            tip = self._obseTip % (dict(version=''))
        # + OBSE
        tip += u' + %s %s' % (bush.game.se.shortName, self.obseVersion)
        # + LAA
        if bosh.dirs['app'].join(bush.game.laa.exe).exists() and settings.get('bash.laa.on',True):
            tip += u' + ' + bush.game.laa.name
        return tip

    def Execute(self,event):
        App_Button.Execute(self,event)
        if settings.get('bash.autoQuit.on',False):
            bashFrame.Close(True)

#------------------------------------------------------------------------------
class TESCS_Button(App_Button):
    """CS button.  Needs a special Tooltip when OBSE is enabled."""
    @property
    def obseTip(self):
        # TESCS (version)
        if settings['bash.statusbar.showversion']:
            tip = self._obseTip % (dict(version=self.version))
        else:
            tip = self._obseTip % (dict(version=''))
        if not self.obseArg: return tip
        # + OBSE
        tip += u' + %s %s' % (bush.game.se.shortName, self.obseVersion)
        # + CSE
        path = bosh.dirs['mods'].join(u'obse',u'plugins',u'Construction Set Extender.dll')
        if path.exists():
            version = path.strippedVersion
            if version != (0,):
                version = u'.'.join([u'%i'%x for x in version])
            else:
                version = u''
            tip += u' + CSE %s' % version
        return tip

#------------------------------------------------------------------------------
class Obse_Button(StatusBar_Button):
    """Obse on/off state button."""
    def SetState(self,state=None):
        """Sets state related info. If newState != none, sets to new state first.
        For convenience, returns state when done."""
        if state is None: #--Default
            state = settings.get('bash.obse.on',True)
        elif state == -1: #--Invert
            state = not settings.get('bash.obse.on',False)
        settings['bash.obse.on'] = state
        if bush.game.laa.launchesSE and not state and laaButton.gButton is not None:
            # 4GB Launcher automatically launches the SE, so turning of the SE
            # required turning off the 4GB Laucner as well
            laaButton.SetState(state)
        # BitmapButton
        image = images[(u'checkbox.green.off.%s'%settings['bash.statusbar.iconSize'],
                        u'checkbox.green.on.%s'%settings['bash.statusbar.iconSize'])[state]]
        tip = ((_(u"%s %s Disabled"),_(u"%s %s Enabled"))[state]) % (bush.game.se.shortName, self.obseVersion)
        self.gButton.SetBitmapLabel(image.GetBitmap())
        self.gButton.SetToolTip(tooltip(tip))
        self.UpdateToolTips(state)

    def UpdateToolTips(self,state=None):
        if state is None:
            state = settings.get('bash.obse.on',True)
        tipAttr = ('tip','obseTip')[state]
        for button in App_Button.obseButtons:
            button.gButton.SetToolTip(tooltip(getattr(button,tipAttr,u'')))
        return state

    def GetBitmapButton(self,window,style=0):
        exeObse = bosh.dirs['app'].join(bush.game.se.exe)
        if exeObse.exists():
            bitmap = images[u'checkbox.green.off.%s'%settings['bash.statusbar.iconSize']].GetBitmap()
            self.createButton(window,bitmap,style=style)
            self.SetState()
            return self.gButton
        else:
            return None

    def Execute(self,event):
        """Invert state."""
        self.SetState(-1)

class LAA_Button(Obse_Button):
    """4GB Launcher on/off state button."""
    def SetState(self,state=None):
        """Sets state related info.  If newState != none, sets to new state first.
        For convenience, returns state when done."""
        if state is None: #--Default
            state = settings.get('bash.laa.on',True)
        elif state == -1: #--Invert
            state = not settings.get('bash.laa.on',False)
        settings['bash.laa.on'] = state
        if bush.game.laa.launchesSE and obseButton.gButton is not None:
            if state:
                # If the 4gb launcher launces the SE, enable the SE when enabling this
                obseButton.SetState(state)
            else:
                # We need the obse button to update the tooltips anyway
                obseButton.UpdateToolTips()
        # BitmapButton
        image = images[(u'checkbox.blue.off.%s'%settings['bash.statusbar.iconSize'],
                        u'checkbox.blue.on.%s'%settings['bash.statusbar.iconSize'])[state]]
        tip = bush.game.laa.name + (_(u' Disabled'),_(u' Enabled'))[state]
        if self.gButton:
            self.gButton.SetBitmapLabel(image.GetBitmap())
            self.gButton.SetToolTip(tooltip(tip))
        return state

    def GetBitmapButton(self,window,style=0):
        exeLAA = bosh.dirs['app'].join(bush.game.laa.exe)
        if exeLAA.exists():
            bitmap = images[u'checkbox.blue.off.%s'%settings['bash.statusbar.iconSize']].GetBitmap()
            self.createButton(window,bitmap,style=style)
            self.SetState()
            return self.gButton
        else:
            return None

#------------------------------------------------------------------------------
class AutoQuit_Button(StatusBar_Button):
    """Button toggling application closure when launching Oblivion."""
    def SetState(self,state=None):
        """Sets state related info. If newState != none, sets to new state first.
        For convenience, returns state when done."""
        if state is None: #--Default
            state = settings.get('bash.autoQuit.on',False)
        elif state == -1: #--Invert
            state = not settings.get('bash.autoQuit.on',False)
        settings['bash.autoQuit.on'] = state
        image = images[(u'checkbox.red.off.%s'%settings['bash.statusbar.iconSize'],
                        u'checkbox.red.x.%s'%settings['bash.statusbar.iconSize'])[state]]
        tip = (_(u"Auto-Quit Disabled"),_(u"Auto-Quit Enabled"))[state]
        self.gButton.SetBitmapLabel(image.GetBitmap())
        self.gButton.SetToolTip(tooltip(tip))

    def GetBitmapButton(self,window,style=0):
        bitmap = images[u'checkbox.red.off.%s'%settings['bash.statusbar.iconSize']].GetBitmap()
        self.createButton(window,bitmap,style=style)
        self.SetState()
        return self.gButton

    def Execute(self,event):
        """Invert state."""
        self.SetState(-1)

#------------------------------------------------------------------------------
class App_Help(StatusBar_Button):
    """Show help browser."""
    def GetBitmapButton(self,window,style=0):
        if not self.id: self.id = wx.NewId()
        self.createButton(
            window,
            images[u'help.%s'%settings['bash.statusbar.iconSize']].GetBitmap(),
            style=style,
            tip=_(u"Help File"))
        return self.gButton

    def Execute(self,event):
        """Handle menu selection."""
        html = bosh.dirs['mopy'].join(u'Docs\Wrye Bash General Readme.html')
        if html.exists():
            html.start()
        else:
            balt.showError(bashFrame, _(u'Cannot find General Readme file.'))

#------------------------------------------------------------------------------
class App_DocBrowser(StatusBar_Button):
    """Show doc browser."""
    def GetBitmapButton(self,window,style=0):
        if not self.id: self.id = wx.NewId()
        self.createButton(
            window,
            images[u'doc.%s'%settings['bash.statusbar.iconSize']].GetBitmap(),
            style=style,
            tip=_(u"Doc Browser"))
        return self.gButton

    def Execute(self,event):
        """Handle menu selection."""
        if not docBrowser:
            DocBrowser().Show()
            settings['bash.modDocs.show'] = True
        #balt.ensureDisplayed(docBrowser)
        docBrowser.Raise()

#------------------------------------------------------------------------------
class App_Settings(StatusBar_Button):
    """Show color configuration dialog."""
    def GetBitmapButton(self,window,style=0):
        if not self.id: self.id = wx.NewId()
        self.createButton(
            window,
            Image(GPath(bosh.dirs['images'].join(u'settingsbutton%s.png'%settings['bash.statusbar.iconSize']))).GetBitmap(),
            style=style,
            tip=_(u'Settings'),
            onRClick=self.Execute)
        return self.gButton

    def Execute(self,event):
        SettingsMenu.PopupMenu(bashFrame.GetStatusBar(),bashFrame,None)

#------------------------------------------------------------------------------
class App_Restart(StatusBar_Button):
    """Restart Wrye Bash"""
    def GetBitmapButton(self,window,style=0):
        if not self.id: self.id = wx.NewId()
        if self.gButton is not None: self.gButton.Destroy()
        self.gButton = bitmapButton(window,
            wx.ArtProvider.GetBitmap(wx.ART_UNDO,wx.ART_TOOLBAR,
                (settings['bash.statusbar.iconSize'],
                 settings['bash.statusbar.iconSize'])),
            style=style,
            tip=_(u'Restart'),
            onClick = self.Execute,
            onRClick = self.DoPopupMenu)
        return self.gButton

    def Execute(self,event):
        bashFrame.Restart()

#------------------------------------------------------------------------------
class App_GenPickle(StatusBar_Button):
    """Generate PKL File. Ported out of bish.py which wasn't working."""
    def GetBitmapButton(self,window,style=0):
        if not self.id: self.id = wx.NewId()
        return self.createButton(
            window,
            Image(GPath(bosh.dirs['images'].join(u'pickle%s.png'%settings['bash.statusbar.iconSize']))).GetBitmap(),
            style=style,
            tip=_(u"Generate PKL File"))

    def Execute(self,event,fileName=None):
        """Updates map of GMST eids to fids in bash\db\Oblivion_ids.pkl, based either
        on a list of new eids or the gmsts in the specified mod file. Updated pkl file
        is dropped in Mopy directory."""
        #--Data base
        import cPickle
        try:
            fids = cPickle.load(GPath(bush.game.pklfile).open('r'))['GMST']
            if fids:
                maxId = max(fids.values())
            else:
                maxId = 0
        except:
            fids = {}
            maxId = 0
        maxId = max(maxId,0xf12345)
        maxOld = maxId
        print 'maxId',hex(maxId)
        #--Eid list? - if the GMST has a 00000000 eid when looking at it in the cs with nothing
        # but oblivion.esm loaded you need to add the gmst to this list, rebuild the pickle and overwrite the old one.
        for eid in bush.game.gmstEids:
            if eid not in fids:
                maxId += 1
                fids[eid] = maxId
                print '%08X  %08X %s' % (0,maxId,eid)
                #--Source file
        if fileName:
            sorter = lambda a: a.eid
            loadFactory = bosh.LoadFactory(False,bosh.MreGmst)
            modInfo = bosh.modInfos[GPath(fileName)]
            modFile = bosh.ModFile(modInfo,loadFactory)
            modFile.load(True)
            for gmst in sorted(modFile.GMST.records,key=sorter):
                print gmst.eid, gmst.value
                if gmst.eid not in fids:
                    maxId += 1
                    fids[gmst.eid] = maxId
                    print '%08X  %08X %s' % (gmst.fid,maxId,gmst.eid)
        #--Changes?
        if maxId > maxOld:
            outData = {'GMST':fids}
            cPickle.dump(outData,GPath(bush.game.pklfile).open('w'))
            print _(u"%d new gmst ids written to "+bush.game.pklfile) % ((maxId - maxOld),)
        else:
            print _(u'No changes necessary. PKL data unchanged.')

#------------------------------------------------------------------------------
class App_ModChecker(StatusBar_Button):
    """Show mod checker."""
    def GetBitmapButton(self,window,style=0):
        if not self.id: self.id = wx.NewId()
        return self.createButton(
            window,
            Image(GPath(bosh.dirs['images'].join(u'ModChecker%s.png'%settings['bash.statusbar.iconSize']))).GetBitmap(),
            style=style,
            tip=_(u"Mod Checker"))

    def Execute(self,event):
        """Handle menu selection."""
        if not modChecker:
            ModChecker().Show()
        #balt.ensureDisplayed(modChecker)
        modChecker.Raise()

#------------------------------------------------------------------------------
class CreateNewProject(wx.Dialog):
    def __init__(self,parent,id,title):
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
        self.SetIcon(wx.Icon(bosh.dirs['images'].join(u'diamond_white_off.png').s,wx.BITMAP_TYPE_PNG))
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
                self.SetIcon(wx.Icon(bosh.dirs['images'].join(u'diamond_white_off_wiz.png').s,wx.BITMAP_TYPE_PNG))
            else:
                self.SetIcon(wx.Icon(bosh.dirs['images'].join(u'diamond_white_off.png').s,wx.BITMAP_TYPE_PNG))
        else:
            self.SetIcon(wx.Icon(bosh.dirs['images'].join(u'diamond_grey_off.png').s,wx.BITMAP_TYPE_PNG))

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

class Installer_CreateNewProject(InstallerLink):
    """Open the Create New Project Dialog"""
    def AppendToMenu(self, menu, window, data):
        Link.AppendToMenu(self, menu, window, data)
        title = _(u'Create New Project...')
        menuItem = wx.MenuItem(menu,self.id,title,help=_(u'Create a new project...'))
        menu.AppendItem(menuItem)

    def Execute(self, event):
        dialog = CreateNewProject(None,wx.ID_ANY,_(u'Create New Project'))
        dialog.ShowModal()
        dialog.Destroy()

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
    images['save.on'] = Image(GPath(bosh.dirs['images'].join(u'save_on.png')),wx.BITMAP_TYPE_PNG)
    images['save.off'] = Image(GPath(bosh.dirs['images'].join(u'save_off.png')),wx.BITMAP_TYPE_PNG)
    #--Misc
    #images['oblivion'] = Image(GPath(bosh.dirs['images'].join(u'oblivion.png')),wx.BITMAP_TYPE_PNG)
    images['help.16'] = Image(GPath(bosh.dirs['images'].join(u'help16.png')))
    images['help.24'] = Image(GPath(bosh.dirs['images'].join(u'help24.png')))
    images['help.32'] = Image(GPath(bosh.dirs['images'].join(u'help32.png')))
    #--ColorChecks
    images['checkbox.red.x'] = Image(GPath(bosh.dirs['images'].join(u'checkbox_red_x.png')),wx.BITMAP_TYPE_PNG)
    images['checkbox.red.x.16'] = Image(GPath(bosh.dirs['images'].join(u'checkbox_red_x.png')),wx.BITMAP_TYPE_PNG)
    images['checkbox.red.x.24'] = Image(GPath(bosh.dirs['images'].join(u'checkbox_red_x_24.png')),wx.BITMAP_TYPE_PNG)
    images['checkbox.red.x.32'] = Image(GPath(bosh.dirs['images'].join(u'checkbox_red_x_32.png')),wx.BITMAP_TYPE_PNG)
    images['checkbox.red.off.16'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_red_off.png')),wx.BITMAP_TYPE_PNG))
    images['checkbox.red.off.24'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_red_off_24.png')),wx.BITMAP_TYPE_PNG))
    images['checkbox.red.off.32'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_red_off_32.png')),wx.BITMAP_TYPE_PNG))

    images['checkbox.green.on.16'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_green_on.png')),wx.BITMAP_TYPE_PNG))
    images['checkbox.green.off.16'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_green_off.png')),wx.BITMAP_TYPE_PNG))
    images['checkbox.green.on.24'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_green_on_24.png')),wx.BITMAP_TYPE_PNG))
    images['checkbox.green.off.24'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_green_off_24.png')),wx.BITMAP_TYPE_PNG))
    images['checkbox.green.on.32'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_green_on_32.png')),wx.BITMAP_TYPE_PNG))
    images['checkbox.green.off.32'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_green_off_32.png')),wx.BITMAP_TYPE_PNG))

    images['checkbox.blue.on.16'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_blue_on.png')),wx.BITMAP_TYPE_PNG))
    images['checkbox.blue.on.24'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_blue_on_24.png')),wx.BITMAP_TYPE_PNG))
    images['checkbox.blue.on.32'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_blue_on_32.png')),wx.BITMAP_TYPE_PNG))
    images['checkbox.blue.off.16'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_blue_off.png')),wx.BITMAP_TYPE_PNG))
    images['checkbox.blue.off.24'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_blue_off_24.png')),wx.BITMAP_TYPE_PNG))
    images['checkbox.blue.off.32'] = (Image(GPath(bosh.dirs['images'].join(u'checkbox_blue_off_32.png')),wx.BITMAP_TYPE_PNG))
    #--Bash
    images['bash.16'] = Image(GPath(bosh.dirs['images'].join(u'bash_16.png')),wx.BITMAP_TYPE_PNG)
    images['bash.24'] = Image(GPath(bosh.dirs['images'].join(u'bash_24.png')),wx.BITMAP_TYPE_PNG)
    images['bash.32'] = Image(GPath(bosh.dirs['images'].join(u'bash_32.png')),wx.BITMAP_TYPE_PNG)
    images['bash.16.blue'] = Image(GPath(bosh.dirs['images'].join(u'bash_16_blue.png')),wx.BITMAP_TYPE_PNG)
    images['bash.24.blue'] = Image(GPath(bosh.dirs['images'].join(u'bash_24_blue.png')),wx.BITMAP_TYPE_PNG)
    images['bash.32.blue'] = Image(GPath(bosh.dirs['images'].join(u'bash_32_blue.png')),wx.BITMAP_TYPE_PNG)
    #--Bash Patch Dialogue
    images['monkey.16'] = Image(GPath(bosh.dirs['images'].join(u'wryemonkey16.jpg')),wx.BITMAP_TYPE_JPEG)
    #images['monkey.32'] = Image(GPath(bosh.dirs['images'].join(u'wryemonkey32.jpg')),wx.BITMAP_TYPE_JPEG)
    #--DocBrowser
    images['doc.16'] = Image(GPath(bosh.dirs['images'].join(u'DocBrowser16.png')),wx.BITMAP_TYPE_PNG)
    images['doc.24'] = Image(GPath(bosh.dirs['images'].join(u'DocBrowser24.png')),wx.BITMAP_TYPE_PNG)
    images['doc.32'] = Image(GPath(bosh.dirs['images'].join(u'DocBrowser32.png')),wx.BITMAP_TYPE_PNG)
    #--UAC icons
    #images['uac.small'] = Image(GPath(balt.getUACIcon('small')),wx.BITMAP_TYPE_ICO)
    #images['uac.large'] = Image(GPath(balt.getUACIcon('large')),wx.BITMAP_TYPE_ICO)
    #--Applications Icons
    global bashRed
    bashRed = balt.ImageBundle()
    bashRed.Add(images['bash.16'])
    bashRed.Add(images['bash.24'])
    bashRed.Add(images['bash.32'])
    #--Application Subwindow Icons
    global bashBlue
    bashBlue = balt.ImageBundle()
    bashBlue.Add(images['bash.16.blue'])
    bashBlue.Add(images['bash.24.blue'])
    bashBlue.Add(images['bash.32.blue'])
    global bashDocBrowser
    bashDocBrowser = balt.ImageBundle()
    bashDocBrowser.Add(images['doc.16'])
    bashDocBrowser.Add(images['doc.24'])
    bashDocBrowser.Add(images['doc.32'])
    global bashMonkey
    bashMonkey = balt.ImageBundle()
    bashMonkey.Add(images['monkey.16'])

def InitStatusBar():
    """Initialize status bar links."""
    dirImages = bosh.dirs['images']
    def imageList(template):
        return [Image(dirImages.join(template % x)) for x in (16,24,32)]
    #--Bash Status/LinkBar
    global obseButton
    obseButton = Obse_Button(uid=u'OBSE')
    BashStatusBar.buttons.append(obseButton)
    global laaButton
    laaButton = LAA_Button(uid=u'LAA')
    BashStatusBar.buttons.append(laaButton)
    BashStatusBar.buttons.append(AutoQuit_Button(uid=u'AutoQuit'))
    BashStatusBar.buttons.append( # Game
        Oblivion_Button(
            bosh.dirs['app'].join(bush.game.exe),
            imageList(u'%s%%s.png' % bush.game.fsName.lower()),
            u' '.join((_(u"Launch"),bush.game.displayName)),
            u' '.join((_(u"Launch"),bush.game.displayName,u'%(version)s')),
            u'',
            uid=u'Oblivion'))
    BashStatusBar.buttons.append( #TESCS/CreationKit
        TESCS_Button(
            bosh.dirs['app'].join(bush.game.cs.exe),
            imageList(bush.game.cs.imageName),
            u' '.join((_(u"Launch"),bush.game.cs.shortName)),
            u' '.join((_(u"Launch"),bush.game.cs.shortName,u'%(version)s')),
            bush.game.cs.seArgs,
            uid=u'TESCS'))
    BashStatusBar.buttons.append( #OBMM
        App_Button(
            bosh.dirs['app'].join(u'OblivionModManager.exe'),
            imageList(u'obmm%s.png'),
            _(u"Launch OBMM"),
            uid=u'OBMM'))
    BashStatusBar.buttons.append( #ISOBL
        Tooldir_Button(
            u'ISOBL',
            imageList(u'tools/isobl%s.png'),
            _(u"Launch InsanitySorrow's Oblivion Launcher")))
    BashStatusBar.buttons.append( #ISRMG
        Tooldir_Button(
            u'ISRMG',
            imageList(u"tools/insanity'sreadmegenerator%s.png"),
            _(u"Launch InsanitySorrow's Readme Generator")))
    BashStatusBar.buttons.append( #ISRNG
        Tooldir_Button(
            u'ISRNG',
            imageList(u"tools/insanity'srng%s.png"),
            _(u"Launch InsanitySorrow's Random Name Generator")))
    BashStatusBar.buttons.append( #ISRNPCG
        Tooldir_Button(
            u'ISRNPCG',
            imageList(u'tools/randomnpc%s.png'),
            _(u"Launch InsanitySorrow's Random NPC Generator")))
    BashStatusBar.buttons.append( #OBFEL
        Tooldir_Button(
            u'OBFEL',
            imageList(u'tools/oblivionfaceexchangerlite%s.png'),
            _(u"Oblivion Face Exchange Lite")))
    BashStatusBar.buttons.append( #OBMLG
        Tooldir_Button(
            u'OBMLG',
            imageList(u'tools/modlistgenerator%s.png'),
            _(u"Oblivion Mod List Generator")))
    BashStatusBar.buttons.append( #OblivionBookCreator
        App_Button(
            (bosh.tooldirs['OblivionBookCreatorPath'],bosh.inisettings['OblivionBookCreatorJavaArg']),
            imageList(u'tools/oblivionbookcreator%s.png'),
            _(u"Launch Oblivion Book Creator"),
            uid=u'OblivionBookCreator'))
    BashStatusBar.buttons.append( #BSACommander
        Tooldir_Button(
            u'BSACMD',
            imageList(u'tools/bsacommander%s.png'),
            _(u"Launch BSA Commander")))
    BashStatusBar.buttons.append( #Tabula
        Tooldir_Button(
            u'Tabula',
            imageList(u'tools/tabula%s.png'),
            _(u"Launch Tabula")))
    BashStatusBar.buttons.append( #Tes4Files
        Tooldir_Button(
            u'Tes4FilesPath',
            imageList(u'tools/tes4files%s.png'),
            _(u"Launch TES4Files")))
    BashStatusBar.buttons.append( #Tes4Gecko
        App_Button(
            (bosh.tooldirs['Tes4GeckoPath'],bosh.inisettings['Tes4GeckoJavaArg']),
            imageList(u'tools/tes4gecko%s.png'),
            _(u"Launch Tes4Gecko"),
            uid=u'Tes4Gecko'))
    BashStatusBar.buttons.append( #Tes4View
        App_Tes4View(
            (bosh.tooldirs['Tes4ViewPath'],u'-TES4'), #no cmd argument to force view mode
            imageList(u'tools/tes4view%s.png'),
            _(u"Launch TES4View"),
            uid=u'TES4View'))
    BashStatusBar.buttons.append( #Tes4Edit
        App_Tes4View(
            (bosh.tooldirs['Tes4EditPath'],u'-TES4 -edit'),
            imageList(u'tools/tes4edit%s.png'),
            _(u"Launch TES4Edit"),
            uid=u'TES4Edit'))
    BashStatusBar.buttons.append( #Tes5Edit
        App_Tes4View(
            (bosh.tooldirs['Tes5EditPath'],u'-TES5 -edit'),
            imageList(u'tools/tes4edit%s.png'),
            _(u"Launch TES5Edit"),
            uid=u'TES5Edit'))
    BashStatusBar.buttons.append( #TesVGecko
        App_Button( (bosh.tooldirs['Tes5GeckoPath']),
            imageList(u'tools/tesvgecko%s.png'),
            _(u"Launch TesVGecko"),
            uid=u'TesVGecko'))
    BashStatusBar.buttons.append( #Tes4Trans
        App_Tes4View(
            (bosh.tooldirs['Tes4TransPath'],u'-TES4 -translate'),
            imageList(u'tools/tes4trans%s.png'),
            _(u"Launch TES4Trans"),
            uid=u'TES4Trans'))
    BashStatusBar.buttons.append( #Tes4LODGen
        App_Tes4View(
            (bosh.tooldirs['Tes4LodGenPath'],u'-TES4 -lodgen'),
            imageList(u'tools/tes4lodgen%s.png'),
            _(u"Launch Tes4LODGen"),
            uid=u'TES4LODGen'))
    BashStatusBar.buttons.append( #BOSS
        App_BOSS(
            (bosh.tooldirs['boss']),
            imageList(u'boss%s.png'),
            _(u"Launch BOSS"),
            uid=u'BOSS'))
    if bosh.inisettings['ShowModelingToolLaunchers']:
        BashStatusBar.buttons.append( #AutoCad
            Tooldir_Button(
                'AutoCad',
                imageList(u'tools/autocad%s.png'),
                _(u"Launch AutoCad")))
        BashStatusBar.buttons.append( #Blender
            Tooldir_Button(
                'BlenderPath',
                imageList(u'tools/blender%s.png'),
                _(u"Launch Blender")))
        BashStatusBar.buttons.append( #Dogwaffle
            Tooldir_Button(
                'Dogwaffle',
                imageList(u'tools/dogwaffle%s.png'),
                _(u"Launch Dogwaffle")))
        BashStatusBar.buttons.append( #GMax
            Tooldir_Button(
                'GmaxPath',
                imageList(u'tools/gmax%s.png'),
                _(u"Launch Gmax")))
        BashStatusBar.buttons.append( #Maya
            Tooldir_Button(
                'MayaPath',
                imageList(u'tools/maya%s.png'),
                _(u"Launch Maya")))
        BashStatusBar.buttons.append( #Max
            Tooldir_Button(
                'MaxPath',
                imageList(u'tools/3dsmax%s.png'),
                _(u"Launch 3dsMax")))
        BashStatusBar.buttons.append( #Milkshape3D
            Tooldir_Button(
                'Milkshape3D',
                imageList(u'tools/milkshape3d%s.png'),
                _(u"Launch Milkshape 3D")))
        BashStatusBar.buttons.append( #Mudbox
            Tooldir_Button(
                'Mudbox',
                imageList(u'tools/mudbox%s.png'),
                _(u"Launch Mudbox")))
        BashStatusBar.buttons.append( #Sculptris
            Tooldir_Button(
                'Sculptris',
                imageList(u'tools/sculptris%s.png'),
                _(u"Launch Sculptris")))
        BashStatusBar.buttons.append( #Softimage Mod Tool
            App_Button(
                (bosh.tooldirs['SoftimageModTool'],u'-mod'),
                imageList(u'tools/softimagemodtool%s.png'),
                _(u"Launch Softimage Mod Tool"),
                uid=u'SoftimageModTool'))
        BashStatusBar.buttons.append( #SpeedTree
            Tooldir_Button(
                'SpeedTree',
                imageList(u'tools/speedtree%s.png'),
                _(u"Launch SpeedTree")))
        BashStatusBar.buttons.append( #Tree[d]
            Tooldir_Button(
                'Treed',
                imageList(u'tools/treed%s.png'),
                _(u"Launch Tree\[d\]")))
        BashStatusBar.buttons.append( #Wings3D
            Tooldir_Button(
                'Wings3D',
                imageList(u'tools/wings3d%s.png'),
                _(u"Launch Wings 3D")))
    if bosh.inisettings['ShowModelingToolLaunchers'] or bosh.inisettings['ShowTextureToolLaunchers']:
        BashStatusBar.buttons.append( #Nifskope
            Tooldir_Button(
                'NifskopePath',
                imageList(u'tools/nifskope%s.png'),
                _(u"Launch Nifskope")))
    if bosh.inisettings['ShowTextureToolLaunchers']:
        BashStatusBar.buttons.append( #AniFX
            Tooldir_Button(
                'AniFX',
                imageList(u'tools/anifx%s.png'),
                _(u"Launch AniFX")))
        BashStatusBar.buttons.append( #Art Of Illusion
            Tooldir_Button(
                'ArtOfIllusion',
                imageList(u'tools/artofillusion%s.png'),
                _(u"Launch Art Of Illusion")))
        BashStatusBar.buttons.append( #Artweaver
            Tooldir_Button(
                'Artweaver',
                imageList(u'tools/artweaver%s.png'),
                _(u"Launch Artweaver")))
        BashStatusBar.buttons.append( #CrazyBump
            Tooldir_Button(
                'CrazyBump',
                imageList(u'tools/crazybump%s.png'),
                _(u"Launch CrazyBump")))
        BashStatusBar.buttons.append( #DDSConverter
            Tooldir_Button(
                'DDSConverter',
                imageList(u'tools/ddsconverter%s.png'),
                _(u"Launch DDSConverter")))
        BashStatusBar.buttons.append( #DeepPaint
            Tooldir_Button(
                'DeepPaint',
                imageList(u'tools/deeppaint%s.png'),
                _(u"Launch DeepPaint")))
        BashStatusBar.buttons.append( #FastStone Image Viewer
            Tooldir_Button(
                'FastStone',
                imageList(u'tools/faststoneimageviewer%s.png'),
                _(u"Launch FastStone Image Viewer")))
        BashStatusBar.buttons.append( #Genetica
            Tooldir_Button(
                'Genetica',
                imageList(u'tools/genetica%s.png'),
                _(u"Launch Genetica")))
        BashStatusBar.buttons.append( #Genetica Viewer
            Tooldir_Button(
                'GeneticaViewer',
                imageList(u'tools/geneticaviewer%s.png'),
                _(u"Launch Genetica Viewer")))
        BashStatusBar.buttons.append( #GIMP
            Tooldir_Button(
                'GIMP',
                imageList(u'tools/gimp%s.png'),
                _(u"Launch GIMP")))
        BashStatusBar.buttons.append( #GIMP Shop
            Tooldir_Button(
                'GimpShop',
                imageList(u'tools/gimpshop%s.png'),
                _(u"Launch GIMP Shop")))
        BashStatusBar.buttons.append( #IcoFX
            Tooldir_Button(
                'IcoFX',
                imageList(u'tools/icofx%s.png'),
                _(u"Launch IcoFX")))
        BashStatusBar.buttons.append( #Inkscape
            Tooldir_Button(
                'Inkscape',
                imageList(u'tools/inkscape%s.png'),
                _(u"Launch Inkscape")))
        BashStatusBar.buttons.append( #IrfanView
            Tooldir_Button(
                'IrfanView',
                imageList(u'tools/irfanview%s.png'),
                _(u"Launch IrfanView")))
        BashStatusBar.buttons.append( #MaPZone
            Tooldir_Button(
                'MaPZone',
                imageList(u'tools/mapzone%s.png'),
                _(u"Launch MaPZone")))
        BashStatusBar.buttons.append( #MyPaint
            Tooldir_Button(
                'MyPaint',
                imageList(u'tools/mypaint%s.png'),
                _(u"Launch MyPaint")))
        BashStatusBar.buttons.append( #NVIDIAMelody
            Tooldir_Button(
                'NVIDIAMelody',
                imageList(u'tools/nvidiamelody%s.png'),
                _(u"Launch Nvidia Melody")))
        BashStatusBar.buttons.append( #Paint.net
            Tooldir_Button(
                'PaintNET',
                imageList(u'tools/paint.net%s.png'),
                _(u"Launch Paint.NET")))
        BashStatusBar.buttons.append( #PaintShop Photo Pro
            Tooldir_Button(
                'PaintShopPhotoPro',
                imageList(u'tools/paintshopprox3%s.png'),
                _(u"Launch PaintShop Photo Pro")))
        BashStatusBar.buttons.append( #Photoshop
            Tooldir_Button(
                'PhotoshopPath',
                imageList(u'tools/photoshop%s.png'),
                _(u"Launch Photoshop")))
        BashStatusBar.buttons.append( #PhotoScape
            Tooldir_Button(
                'PhotoScape',
                imageList(u'tools/photoscape%s.png'),
                _(u"Launch PhotoScape")))
        BashStatusBar.buttons.append( #PhotoSEAM
            Tooldir_Button(
                'PhotoSEAM',
                imageList(u'tools/photoseam%s.png'),
                _(u"Launch PhotoSEAM")))
        BashStatusBar.buttons.append( #Photobie Design Studio
            Tooldir_Button(
                'Photobie',
                imageList(u'tools/photobie%s.png'),
                _(u"Launch Photobie")))
        BashStatusBar.buttons.append( #PhotoFiltre
            Tooldir_Button(
                'PhotoFiltre',
                imageList(u'tools/photofiltre%s.png'),
                _(u"Launch PhotoFiltre")))
        BashStatusBar.buttons.append( #Pixel Studio Pro
            Tooldir_Button(
                'PixelStudio',
                imageList(u'tools/pixelstudiopro%s.png'),
                _(u"Launch Pixel Studio Pro")))
        BashStatusBar.buttons.append( #Pixia
            Tooldir_Button(
                'Pixia',
                imageList(u'tools/pixia%s.png'),
                _(u"Launch Pixia")))
        BashStatusBar.buttons.append( #TextureMaker
            Tooldir_Button(
                'TextureMaker',
                imageList(u'tools/texturemaker%s.png'),
                _(u"Launch TextureMaker")))
        BashStatusBar.buttons.append( #Twisted Brush
            Tooldir_Button(
                'TwistedBrush',
                imageList(u'tools/twistedbrush%s.png'),
                _(u"Launch TwistedBrush")))
        BashStatusBar.buttons.append( #Windows Texture Viewer
            Tooldir_Button(
                'WTV',
                imageList(u'tools/wtv%s.png'),
                _(u"Launch Windows Texture Viewer")))
        BashStatusBar.buttons.append( #xNormal
            Tooldir_Button(
                'xNormal',
                imageList(u'tools/xnormal%s.png'),
                _(u"Launch xNormal")))
        BashStatusBar.buttons.append( #XnView
            Tooldir_Button(
                'XnView',
                imageList(u'tools/xnview%s.png'),
                _(u"Launch XnView")))
    if bosh.inisettings['ShowAudioToolLaunchers']:
        BashStatusBar.buttons.append( #Audacity
            Tooldir_Button(
                'Audacity',
                imageList(u'tools/audacity%s.png'),
                _(u"Launch Audacity")))
        BashStatusBar.buttons.append( #ABCAmberAudioConverter
            Tooldir_Button(
                'ABCAmberAudioConverter',
                imageList(u'tools/abcamberaudioconverter%s.png'),
                _(u"Launch ABC Amber Audio Converter")))
        BashStatusBar.buttons.append( #Switch
            Tooldir_Button(
                'Switch',
                imageList(u'tools/switch%s.png'),
                _(u"Launch Switch")))
    BashStatusBar.buttons.append( #Fraps
        Tooldir_Button(
            'Fraps',
            imageList(u'tools/fraps%s.png'),
            _(u"Launch Fraps")))
    BashStatusBar.buttons.append( #MAP
        Tooldir_Button(
            'MAP',
            imageList(u'tools/interactivemapofcyrodiil%s.png'),
            _(u"Interactive Map of Cyrodiil and Shivering Isles")))
    BashStatusBar.buttons.append( #LogitechKeyboard
        Tooldir_Button(
            'LogitechKeyboard',
            imageList(u'tools/logitechkeyboard%s.png'),
            _(u"Launch LogitechKeyboard")))
    BashStatusBar.buttons.append( #MediaMonkey
        Tooldir_Button(
            'MediaMonkey',
            imageList(u'tools/mediamonkey%s.png'),
            _(u"Launch MediaMonkey")))
    BashStatusBar.buttons.append( #NPP
        Tooldir_Button(
            'NPP',
            imageList(u'tools/notepad++%s.png'),
            _(u"Launch Notepad++")))
    BashStatusBar.buttons.append( #Steam
        Tooldir_Button(
            'Steam',
            imageList(u'steam%s.png'),
            _(u"Launch Steam")))
    BashStatusBar.buttons.append( #EVGA Precision
        Tooldir_Button(
            'EVGAPrecision',
            imageList(u'tools/evgaprecision%s.png'),
            _(u"Launch EVGA Precision")))
    BashStatusBar.buttons.append( #WinMerge
        Tooldir_Button(
            'WinMerge',
            imageList(u'tools/winmerge%s.png'),
            _(u"Launch WinMerge")))
    BashStatusBar.buttons.append( #Freemind
        Tooldir_Button(
            'FreeMind',
            imageList(u'tools/freemind%s.png'),
            _(u"Launch FreeMind")))
    BashStatusBar.buttons.append( #Freeplane
        Tooldir_Button(
            'Freeplane',
            imageList(u'tools/freeplane%s.png'),
            _(u"Launch Freeplane")))
    BashStatusBar.buttons.append( #FileZilla
        Tooldir_Button(
            'FileZilla',
            imageList(u'tools/filezilla%s.png'),
            _(u"Launch FileZilla")))
    BashStatusBar.buttons.append( #EggTranslator
        Tooldir_Button(
            'EggTranslator',
            imageList(u'tools/eggtranslator%s.png'),
            _(u"Launch Egg Translator")))
    BashStatusBar.buttons.append( #RADVideoTools
        Tooldir_Button(
            'RADVideo',
            imageList(u'tools/radvideotools%s.png'),
            _(u"Launch RAD Video Tools")))
    BashStatusBar.buttons.append( #WinSnap
        Tooldir_Button(
            'WinSnap',
            imageList(u'tools/winsnap%s.png'),
            _(u"Launch WinSnap")))
    #--Custom Apps
    dirApps = bosh.dirs['mopy'].join(u'Apps')
    bosh.initLinks(dirApps)
    folderIcon = None
    badIcons = [Image(bosh.dirs['images'].join(u'x.png'))] * 3
    for link in bosh.links:
        (target,workingdir,args,icon,description) = bosh.links[link]
        path = dirApps.join(link)
        if target.lower().find(ur'installer\{') != -1:
            target = path
        else:
            target = GPath(target)
        if target.exists():
            icon,idex = icon.split(u',')
            if icon == u'':
                if target.cext == u'.exe':
                    # Use the icon embedded in the exe
                    try:
                        win32gui.ExtractIcon(0, target.s, 0)
                        icon = target
                    except Exception as e:
                        icon = u'' # Icon will be set to a red x further down.
                else:
                    # Use the default icon for that file type
                    try:
                        import _winreg
                        if target.isdir():
                            if folderIcon is None:
                                # Special handling of the Folder icon
                                folderkey = _winreg.OpenKey(
                                    _winreg.HKEY_CLASSES_ROOT,
                                    u'Folder')
                                iconkey = _winreg.OpenKey(
                                    folderkey,
                                    u'DefaultIcon')
                                filedata = _winreg.EnumValue(
                                    iconkey,0)
                                filedata = filedata[1]
                                folderIcon = filedata
                            else:
                                filedata = folderIcon
                        else:
                            icon_path = _winreg.QueryValue(
                                _winreg.HKEY_CLASSES_ROOT,
                                target.cext)
                            pathKey = _winreg.OpenKey(
                                _winreg.HKEY_CLASSES_ROOT,
                                u'%s\\DefaultIcon' % icon_path)
                            filedata = _winreg.EnumValue(pathKey, 0)[1]
                            _winreg.CloseKey(pathKey)
                        icon,idex = filedata.split(u',')
                        icon = os.path.expandvars(icon)
                        if not os.path.isabs(icon):
                            # Get the correct path to the dll
                            for dir in os.environ['PATH'].split(u';'):
                                test = GPath(dir).join(icon)
                                if test.exists():
                                    icon = test
                                    break
                    except:
                        deprint(_(u'Error finding icon for %s:') % target.s,traceback=True)
                        icon = u'not\\a\\path'
            icon = GPath(icon)
            # First try a custom icon
            fileName = u'%s%%i.png' % path.sbody
            customIcons = [dirApps.join(fileName % x) for x in (16,24,32)]
            if customIcons[0].exists():
                icon = customIcons
            # Next try the shortcut specified icon
            else:
                if icon.exists():
                    fileName = u';'.join((icon.s,idex))
                    icon = [Image(fileName,wx.BITMAP_TYPE_ICO,x) for x in (16,24,32)]
            # Last, use the 'x' icon
                else:
                    icon = badIcons
            BashStatusBar.buttons.append(
                App_Button(
                    (path,()),
                    icon, description,
                    canHide=False
                    ))
    #--Final couple
    BashStatusBar.buttons.append(
        App_Button(
            (bosh.dirs['mopy'].join(u'Wrye Bash Launcher.pyw'), u'-d', u'--bashmon'),
            imageList(u'bashmon%s.png'),
            _(u"Launch BashMon"),
            uid=u'Bashmon'))
    BashStatusBar.buttons.append(App_DocBrowser(uid=u'DocBrowser'))
    BashStatusBar.buttons.append(App_ModChecker(uid=u'ModChecker'))
    BashStatusBar.buttons.append(App_Settings(uid=u'Settings',canHide=False))
    BashStatusBar.buttons.append(App_Help(uid=u'Help',canHide=False))
    if bosh.inisettings['ShowDevTools']:
        BashStatusBar.buttons.append(App_Restart(uid=u'Restart'))
        BashStatusBar.buttons.append(App_GenPickle(uid=u'Generate PKL File'))

def InitMasterLinks():
    """Initialize master list menus."""
    #--MasterList: Column Links
    if True: #--Sort by
        sortMenu = MenuLink(_(u"Sort by"))
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
    """Initialize Installers tab menus."""
    #--Column links
    #--Sorting
    if True:
        sortMenu = MenuLink(_(u"Sort by"))
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
    InstallersPanel.mainMenu.append(List_Columns('bash.installers.cols','bash.installers.allCols',['Package']))
    #--Actions
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(balt.Tanks_Open())
    InstallersPanel.mainMenu.append(Installers_Refresh(fullRefresh=False))
    InstallersPanel.mainMenu.append(Installers_Refresh(fullRefresh=True))
    InstallersPanel.mainMenu.append(Installers_AddMarker())
    InstallersPanel.mainMenu.append(Installer_CreateNewProject())
    InstallersPanel.mainMenu.append(Installers_MonitorInstall())
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(Installer_ListPackages())
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(Installers_AnnealAll())
    InstallersPanel.mainMenu.append(Files_Unhide('installer'))
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(Installers_UninstallAllPackages())
    InstallersPanel.mainMenu.append(Installers_UninstallAllUnknownFiles())
    #--Behavior
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(Installers_AvoidOnStart())
    InstallersPanel.mainMenu.append(Installers_Enabled())
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(Installers_AutoAnneal())
    if bEnableWizard:
        InstallersPanel.mainMenu.append(Installers_AutoWizard())
    InstallersPanel.mainMenu.append(Installers_AutoRefreshProjects())
    InstallersPanel.mainMenu.append(Installers_AutoRefreshBethsoft())
    InstallersPanel.mainMenu.append(Installers_AutoApplyEmbeddedBCFs())
    InstallersPanel.mainMenu.append(Installers_BsaRedirection())
    InstallersPanel.mainMenu.append(Installers_RemoveEmptyDirs())
    InstallersPanel.mainMenu.append(Installers_ConflictsReportShowsInactive())
    InstallersPanel.mainMenu.append(Installers_ConflictsReportShowsLower())
    InstallersPanel.mainMenu.append(Installers_ConflictsReportShowBSAConflicts())
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
    InstallersPanel.mainMenu.append(Installers_RenameStrings())

    #--Item links
    #--File
    InstallersPanel.itemMenu.append(Installer_Open())
    InstallersPanel.itemMenu.append(Installer_Duplicate())
    InstallersPanel.itemMenu.append(balt.Tank_Delete())
    if True: #--Open At...
        openAtMenu = InstallerOpenAt_MainMenu(_(u"Open at"))
        openAtMenu.links.append(Installer_OpenSearch())
        openAtMenu.links.append(Installer_OpenNexus())
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
    InstallersPanel.itemMenu.append(Installer_SkipRefresh())
    InstallersPanel.itemMenu.append(SeparatorLink())
    if bEnableWizard:
        InstallersPanel.itemMenu.append(Installer_Wizard(False))
        InstallersPanel.itemMenu.append(Installer_Wizard(True))
        InstallersPanel.itemMenu.append(Installer_EditWizard())
        InstallersPanel.itemMenu.append(SeparatorLink())
    InstallersPanel.itemMenu.append(Installer_OpenReadme())
    InstallersPanel.itemMenu.append(Installer_Anneal())
    InstallersPanel.itemMenu.append(Installer_Install())
    InstallersPanel.itemMenu.append(Installer_Install('LAST'))
    InstallersPanel.itemMenu.append(Installer_Install('MISSING'))
    InstallersPanel.itemMenu.append(Installer_Uninstall())
    InstallersPanel.itemMenu.append(SeparatorLink())
    #--Build
    if True: #--BAIN Conversion
        conversionsMenu = InstallerConverter_MainMenu(_(u"Conversions"))
        conversionsMenu.links.append(InstallerConverter_Create())
        conversionsMenu.links.append(InstallerConverter_ConvertMenu(_(u"Apply")))
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
    InstallersPanel.espmMenu.append(Installer_Espm_List())
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

def InitINILinks():
    """Initialize INI Edits tab menus."""
    #--Column Links
    if True: #--Sort by
        sortMenu = MenuLink(_(u"Sort by"))
        sortMenu.links.append(INI_SortValid())
        sortMenu.links.append(SeparatorLink())
        sortMenu.links.append(Files_SortBy('File'))
        sortMenu.links.append(Files_SortBy('Installer'))
    INIList.mainMenu.append(sortMenu)
    INIList.mainMenu.append(SeparatorLink())
    INIList.mainMenu.append(List_Columns('bash.ini.cols','bash.ini.allCols',['File']))
    INIList.mainMenu.append(SeparatorLink())
    INIList.mainMenu.append(INI_AllowNewLines())
    INIList.mainMenu.append(Files_Open())
    INIList.mainMenu.append(INI_ListINIs())

    #--Item menu
    INIList.itemMenu.append(INI_Apply())
    INIList.itemMenu.append(INI_CreateNew())
    INIList.itemMenu.append(INI_ListErrors())
    INIList.itemMenu.append(SeparatorLink())
    INIList.itemMenu.append(INI_FileOpenOrCopy())
    INIList.itemMenu.append(INI_Delete())

def InitModLinks():
    """Initialize Mods tab menus."""
    #--ModList: Column Links
    if True: #--Load
        loadMenu = MenuLink(_(u"Load"))
        loadMenu.links.append(Mods_LoadList())
        ModList.mainMenu.append(loadMenu)
    if True: #--Sort by
        sortMenu = MenuLink(_(u"Sort by"))
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
        sortMenu.links.append(Files_SortBy('CRC'))
        sortMenu.links.append(Files_SortBy('Mod Status'))
        ModList.mainMenu.append(sortMenu)
    if bush.game.fsName == u'Oblivion': #--Versions
        versionsMenu = MenuLink(u"Oblivion.esm")
        versionsMenu.links.append(Mods_OblivionVersion(u'1.1'))
        versionsMenu.links.append(Mods_OblivionVersion(u'1.1b'))
        versionsMenu.links.append(Mods_OblivionVersion(u'GOTY non-SI'))
        versionsMenu.links.append(Mods_OblivionVersion(u'SI'))
        ModList.mainMenu.append(versionsMenu)
    #--Columns ----------------------------------
    ModList.mainMenu.append(SeparatorLink())
    ModList.mainMenu.append(List_Columns('bash.mods.cols','bash.mods.allCols',['File']))
    #--------------------------------------------
    ModList.mainMenu.append(SeparatorLink())
    #--File Menu---------------------------------
    if True:
        fileMenu = MenuLink(_(u'File'))
        if bush.game.esp.canBash:
            fileMenu.links.append(Mod_CreateBlankBashedPatch())
            fileMenu.links.append(Mod_CreateBlank())
            fileMenu.links.append(SeparatorLink())
        fileMenu.links.append(Files_Open())
        fileMenu.links.append(Files_Unhide('mod'))
        ModList.mainMenu.append(fileMenu)
    ModList.mainMenu.append(SeparatorLink())
    ModList.mainMenu.append(Mods_ListMods())
    ModList.mainMenu.append(Mods_ListBashTags())
    ModList.mainMenu.append(Mods_CleanDummyMasters())
    ModList.mainMenu.append(SeparatorLink())
    ModList.mainMenu.append(Mods_AutoGhost())
    if bosh.inisettings['EnableBalo']:
        ModList.mainMenu.append(Mods_AutoGroup())
        ModList.mainMenu.append(Mods_FullBalo())
    if bush.game.fsName != u'Skyrim':
        ModList.mainMenu.append(Mods_LockTimes())
    ModList.mainMenu.append(Mods_ScanDirty())

    #--ModList: Item Links
    if bosh.inisettings['ShowDevTools']:
        ModList.itemMenu.append(Mod_FullLoad())
    if True: #--File
        fileMenu = MenuLink(_(u"File"))
        if bush.game.esp.canBash:
            fileMenu.links.append(Mod_CreateDummyMasters())
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
        groupMenu = MenuLink(_(u"Group"))
        groupMenu.links.append(Mod_Groups())
        if bosh.inisettings['EnableBalo']:
            groupMenu.links.append(Mod_BaloGroups())
        ModList.itemMenu.append(groupMenu)
    if True: #--Ratings
        ratingMenu = MenuLink(_(u"Rating"))
        ratingMenu.links.append(Mod_Ratings())
        ModList.itemMenu.append(ratingMenu)
    #--------------------------------------------
    ModList.itemMenu.append(SeparatorLink())
    if bush.game.esp.canBash:
        ModList.itemMenu.append(Mod_Details())
    ModList.itemMenu.append(File_ListMasters())
    ModList.itemMenu.append(Mod_ShowReadme())
    ModList.itemMenu.append(Mod_ListBashTags())
    ModList.itemMenu.append(Mod_CreateBOSSReport())
    ModList.itemMenu.append(Mod_CopyModInfo())
    #--------------------------------------------
    ModList.itemMenu.append(SeparatorLink())
    ModList.itemMenu.append(Mod_AllowGhosting())
    ModList.itemMenu.append(Mod_Ghost())
    if bush.game.esp.canBash:
        ModList.itemMenu.append(SeparatorLink())
        ModList.itemMenu.append(Mod_MarkMergeable(False))
        if CBash:
            ModList.itemMenu.append(Mod_MarkMergeable(True))
        ModList.itemMenu.append(Mod_Patch_Update(False))
        if CBash:
            ModList.itemMenu.append(Mod_Patch_Update(True))
        ModList.itemMenu.append(Mod_ListPatchConfig())
        ModList.itemMenu.append(Mod_ExportPatchConfig())
        #--Advanced
        ModList.itemMenu.append(SeparatorLink())
        if True: #--Export
            exportMenu = MenuLink(_(u"Export"))
            exportMenu.links.append(CBash_Mod_CellBlockInfo())
            exportMenu.links.append(Mod_EditorIds_Export())
            exportMenu.links.append(Mod_Groups_Export())
    ##        exportMenu.links.append(Mod_ItemData_Export())
            if bush.game.fsName == u'Skyrim':
                exportMenu.links.append(Mod_FullNames_Export())
                exportMenu.links.append(Mod_Prices_Export())
                exportMenu.links.append(Mod_Stats_Export())
            elif bush.game.fsName == u'Oblivion':
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
            importMenu = MenuLink(_(u"Import"))
            importMenu.links.append(Mod_EditorIds_Import())
            importMenu.links.append(Mod_Groups_Import())
    ##        importMenu.links.append(Mod_ItemData_Import())
            if bush.game.fsName == u'Skyrim':
                importMenu.links.append(Mod_FullNames_Import())
                importMenu.links.append(Mod_Prices_Import())
                importMenu.links.append(Mod_Stats_Import())
            elif bush.game.fsName == u'Oblivion':
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
        if True: #--Cleaning
            cleanMenu = MenuLink(_(u"Mod Cleaning"))
            cleanMenu.links.append(Mod_SkipDirtyCheck())
            cleanMenu.links.append(SeparatorLink())
            cleanMenu.links.append(Mod_ScanDirty())
            cleanMenu.links.append(Mod_RemoveWorldOrphans())
            cleanMenu.links.append(Mod_CleanMod())
            cleanMenu.links.append(Mod_UndeleteRefs())
            ModList.itemMenu.append(cleanMenu)
        ModList.itemMenu.append(Mod_AddMaster())
        ModList.itemMenu.append(Mod_CopyToEsmp())
        if bush.game.fsName != u'Skyrim':
            ModList.itemMenu.append(Mod_DecompileAll())
        ModList.itemMenu.append(Mod_FlipSelf())
        ModList.itemMenu.append(Mod_FlipMasters())
        if bush.game.fsName == u'Oblivion':
            ModList.itemMenu.append(Mod_SetVersion())
#    if bosh.inisettings['showadvanced'] == 1:
#        advmenu = MenuLink(_(u"Advanced Scripts"))
#        advmenu.links.append(Mod_DiffScripts())
        #advmenu.links.append(())

def InitSaveLinks():
    """Initialize save tab menus."""
    #--SaveList: Column Links
    if True: #--Sort
        sortMenu = MenuLink(_(u"Sort by"))
        sortMenu.links.append(Files_SortBy('File'))
        sortMenu.links.append(Files_SortBy('Cell'))
        sortMenu.links.append(Files_SortBy('PlayTime'))
        sortMenu.links.append(Files_SortBy('Modified'))
        sortMenu.links.append(Files_SortBy('Player'))
        sortMenu.links.append(Files_SortBy('Status'))
        SaveList.mainMenu.append(sortMenu)
    if bush.game.fsName == u'Oblivion': #--Versions
        versionsMenu = MenuLink(u"Oblivion.esm")
        versionsMenu.links.append(Mods_OblivionVersion(u'1.1',True))
        versionsMenu.links.append(Mods_OblivionVersion(u'1.1b',True))
        versionsMenu.links.append(Mods_OblivionVersion(u'GOTY non-SI',True))
        versionsMenu.links.append(Mods_OblivionVersion(u'SI',True))
        SaveList.mainMenu.append(versionsMenu)
    if True: #--Save Profiles
        subDirMenu = MenuLink(_(u"Profile"))
        subDirMenu.links.append(Saves_Profiles())
        SaveList.mainMenu.append(subDirMenu)
    #--Columns --------------------------------
    SaveList.mainMenu.append(SeparatorLink())
    SaveList.mainMenu.append(List_Columns('bash.saves.cols','bash.saves.allCols',['File']))
    #------------------------------------------
    SaveList.mainMenu.append(SeparatorLink())
    SaveList.mainMenu.append(Files_Open())
    SaveList.mainMenu.append(Files_Unhide('save'))

    #--SaveList: Item Links
    if True: #--File
        fileMenu = MenuLink(_(u"File")) #>>
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
        moveMenu = MenuLink(_(u"Move To"))
        moveMenu.links.append(Save_Move())
        SaveList.itemMenu.append(moveMenu)
    if True: #--Copy to Profile
        copyMenu = MenuLink(_(u"Copy To"))
        copyMenu.links.append(Save_Move(True))
        SaveList.itemMenu.append(copyMenu)
    #--------------------------------------------
    SaveList.itemMenu.append(SeparatorLink())
    SaveList.itemMenu.append(Save_LoadMasters())
    SaveList.itemMenu.append(File_ListMasters())
    SaveList.itemMenu.append(Save_DiffMasters())
    if bush.game.ess.canEditMore:
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
    SaveList.itemMenu.append(Save_ExportScreenshot())
    #--------------------------------------------
    if bush.game.ess.canEditMore:
        SaveList.itemMenu.append(SeparatorLink())
        SaveList.itemMenu.append(Save_Unbloat())
        SaveList.itemMenu.append(Save_RepairAbomb())
        SaveList.itemMenu.append(Save_RepairFactions())
        SaveList.itemMenu.append(Save_RepairHair())

def InitBSALinks():
    """Initialize save tab menus."""
    #--BSAList: Column Links
    if True: #--Sort
        sortMenu = MenuLink(_(u"Sort by"))
        sortMenu.links.append(Files_SortBy('File'))
        sortMenu.links.append(Files_SortBy('Modified'))
        sortMenu.links.append(Files_SortBy('Size'))
        BSAList.mainMenu.append(sortMenu)
    BSAList.mainMenu.append(SeparatorLink())
    BSAList.mainMenu.append(Files_Open())
    BSAList.mainMenu.append(Files_Unhide('save'))

    #--BSAList: Item Links
    if True: #--File
        fileMenu = MenuLink(_(u"File")) #>>
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
    ScreensList.mainMenu.append(List_Columns('bash.screens.cols','bash.screens.allCols',['File']))
    ScreensList.mainMenu.append(SeparatorLink())
    ScreensList.mainMenu.append(Screens_NextScreenShot())
    #--JPEG Quality
    if True:
        qualityMenu = MenuLink(_(u'JPEG Quality'))
        for i in range(100,80,-5):
            qualityMenu.links.append(Screen_JpgQuality(i))
        qualityMenu.links.append(Screen_JpgQualityCustom())
        ScreensList.mainMenu.append(SeparatorLink())
        ScreensList.mainMenu.append(qualityMenu)

    #--ScreensList: Item Links
    ScreensList.itemMenu.append(File_Open())
    ScreensList.itemMenu.append(Screen_Rename())
    ScreensList.itemMenu.append(File_Delete())
    ScreensList.itemMenu.append(SeparatorLink())
    if True: #--Convert
        convertMenu = MenuLink(_(u'Convert'))
        convertMenu.links.append(Screen_ConvertTo(u'jpg',wx.BITMAP_TYPE_JPEG))
        convertMenu.links.append(Screen_ConvertTo(u'png',wx.BITMAP_TYPE_PNG))
        convertMenu.links.append(Screen_ConvertTo(u'bmp',wx.BITMAP_TYPE_BMP))
        convertMenu.links.append(Screen_ConvertTo(u'tif',wx.BITMAP_TYPE_TIF))
        ScreensList.itemMenu.append(convertMenu)

def InitMessageLinks():
    """Initialize messages tab menus."""
    #--SaveList: Column Links
    MessageList.mainMenu.append(Messages_Archive_Import())
    MessageList.mainMenu.append(SeparatorLink())
    MessageList.mainMenu.append(List_Columns('bash.messages.cols','bash.messages.allCols',['Subject']))

    #--ScreensList: Item Links
    MessageList.itemMenu.append(Message_Delete())

def InitPeopleLinks():
    """Initialize people tab menus."""
    #--Header links
    PeoplePanel.mainMenu.append(People_AddNew())
    PeoplePanel.mainMenu.append(People_Import())
    PeoplePanel.mainMenu.append(SeparatorLink())
    PeoplePanel.mainMenu.append(List_Columns('bash.people.cols','bash.people.allCols',['Name']))
    #--Item links
    PeoplePanel.itemMenu.append(People_Karma())
    PeoplePanel.itemMenu.append(SeparatorLink())
    PeoplePanel.itemMenu.append(People_AddNew())
    PeoplePanel.itemMenu.append(balt.Tank_Delete())
    PeoplePanel.itemMenu.append(People_Export())

def InitSettingsLinks():
    """Initialize settings menu."""
    global SettingsMenu
    SettingsMenu = Links()
    #--User settings
    SettingsMenu.append(Settings_BackupSettings())
    SettingsMenu.append(Settings_RestoreSettings())
    SettingsMenu.append(Settings_SaveSettings())
    #--OBSE Dll info
    SettingsMenu.append(SeparatorLink())
    SettingsMenu.append(Settings_ExportDllInfo())
    SettingsMenu.append(Settings_ImportDllInfo())
    #--Color config
    SettingsMenu.append(SeparatorLink())
    SettingsMenu.append(Settings_Colors())
    if True:
        tabsMenu = MenuLink(_(u'Tabs'))
        for key in settings['bash.tabs.order']:
            canDisable = bool(key != 'Mods')
            tabsMenu.links.append(Settings_Tab(key,canDisable))
        SettingsMenu.append(tabsMenu)
    #--StatusBar
    if True:
        sbMenu = MenuLink(_(u'Status bar'))
        #--Icon size
        if True:
            sizeMenu = MenuLink(_(u'Icon size'))
            for size in (16,24,32):
                sizeMenu.links.append(Settings_IconSize(size))
            sbMenu.links.append(sizeMenu)
        sbMenu.links.append(Settings_UnHideButtons())
        sbMenu.links.append(Settings_StatusBar_ShowVersions())
        SettingsMenu.append(sbMenu)
    SettingsMenu.append(Settings_Languages())
    SettingsMenu.append(Settings_PluginEncodings())
    SettingsMenu.append(Settings_Games())
    SettingsMenu.append(SeparatorLink())
    SettingsMenu.append(Settings_UseAltName())
    SettingsMenu.append(Mods_Deprint())
    SettingsMenu.append(Mods_DumpTranslator())
    SettingsMenu.append(Settings_UAC())


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
