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
"""This module contains some constants ripped out of basher.py"""

from .. import bush, bosh # I hope this bosh import is valid...
from ..balt import Image, ImageList, IdList
from ..bolt import GPath
import wx # TODO(ut): this must go - also wrap long lines

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
settingDefaults = { # TODO(ut): belongs to bosh (or better to a settings package)
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
    'bash.mods.groups': bush.defaultGroups,
    'bash.mods.ratings': ['+','1','2','3','4','5','=','~'],
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

# Images ----------------------------------------------------------------------
#------------------------------------------------------------------------------
PNG = Image.typesDict['png']
JPEG = Image.typesDict['jpg']
ICO = Image.typesDict['ico']
BMP = Image.typesDict['bmp']
TIF = Image.typesDict['tif']

#--Image lists
karmacons = ImageList(16,16)
karmacons.data.extend({
    'karma+5': Image(GPath((bosh.dirs['images']).join(u'checkbox_purple_inc.png')),PNG),
    'karma+4': Image(GPath((bosh.dirs['images']).join(u'checkbox_blue_inc.png')),PNG),
    'karma+3': Image(GPath((bosh.dirs['images']).join(u'checkbox_blue_inc.png')),PNG),
    'karma+2': Image(GPath((bosh.dirs['images']).join(u'checkbox_green_inc.png')),PNG),
    'karma+1': Image(GPath((bosh.dirs['images']).join(u'checkbox_green_inc.png')),PNG),
    'karma+0': Image(GPath((bosh.dirs['images']).join(u'checkbox_white_off.png')),PNG),
    'karma-1': Image(GPath((bosh.dirs['images']).join(u'checkbox_yellow_off.png')),PNG),
    'karma-2': Image(GPath((bosh.dirs['images']).join(u'checkbox_yellow_off.png')),PNG),
    'karma-3': Image(GPath((bosh.dirs['images']).join(u'checkbox_orange_off.png')),PNG),
    'karma-4': Image(GPath((bosh.dirs['images']).join(u'checkbox_orange_off.png')),PNG),
    'karma-5': Image(GPath((bosh.dirs['images']).join(u'checkbox_red_off.png')),PNG),
    }.items())
installercons = ImageList(16,16)
installercons.data.extend({
    #--Off/Archive
    'off.green':  Image(GPath((bosh.dirs['images']).join(u'checkbox_green_off.png')),PNG),
    'off.grey':   Image(GPath((bosh.dirs['images']).join(u'checkbox_grey_off.png')),PNG),
    'off.red':    Image(GPath((bosh.dirs['images']).join(u'checkbox_red_off.png')),PNG),
    'off.white':  Image(GPath((bosh.dirs['images']).join(u'checkbox_white_off.png')),PNG),
    'off.orange': Image(GPath((bosh.dirs['images']).join(u'checkbox_orange_off.png')),PNG),
    'off.yellow': Image(GPath((bosh.dirs['images']).join(u'checkbox_yellow_off.png')),PNG),
    #--Off/Archive - Wizard
    'off.green.wiz':    Image(GPath((bosh.dirs['images']).join(u'checkbox_green_off_wiz.png')),PNG),
    #grey
    'off.red.wiz':      Image(GPath((bosh.dirs['images']).join(u'checkbox_red_off_wiz.png')),PNG),
    'off.white.wiz':    Image(GPath((bosh.dirs['images']).join(u'checkbox_white_off_wiz.png')),PNG),
    'off.orange.wiz':   Image(GPath((bosh.dirs['images']).join(u'checkbox_orange_off_wiz.png')),PNG),
    'off.yellow.wiz':   Image(GPath((bosh.dirs['images']).join(u'checkbox_yellow_off_wiz.png')),PNG),
    #--On/Archive
    'on.green':  Image(GPath((bosh.dirs['images']).join(u'checkbox_green_inc.png')),PNG),
    'on.grey':   Image(GPath((bosh.dirs['images']).join(u'checkbox_grey_inc.png')),PNG),
    'on.red':    Image(GPath((bosh.dirs['images']).join(u'checkbox_red_inc.png')),PNG),
    'on.white':  Image(GPath((bosh.dirs['images']).join(u'checkbox_white_inc.png')),PNG),
    'on.orange': Image(GPath((bosh.dirs['images']).join(u'checkbox_orange_inc.png')),PNG),
    'on.yellow': Image(GPath((bosh.dirs['images']).join(u'checkbox_yellow_inc.png')),PNG),
    #--On/Archive - Wizard
    'on.green.wiz':  Image(GPath((bosh.dirs['images']).join(u'checkbox_green_inc_wiz.png')),PNG),
    #grey
    'on.red.wiz':    Image(GPath((bosh.dirs['images']).join(u'checkbox_red_inc_wiz.png')),PNG),
    'on.white.wiz':  Image(GPath((bosh.dirs['images']).join(u'checkbox_white_inc_wiz.png')),PNG),
    'on.orange.wiz': Image(GPath((bosh.dirs['images']).join(u'checkbox_orange_inc_wiz.png')),PNG),
    'on.yellow.wiz': Image(GPath((bosh.dirs['images']).join(u'checkbox_yellow_inc_wiz.png')),PNG),
    #--Off/Directory
    'off.green.dir':  Image(GPath((bosh.dirs['images']).join(u'diamond_green_off.png')),PNG),
    'off.grey.dir':   Image(GPath((bosh.dirs['images']).join(u'diamond_grey_off.png')),PNG),
    'off.red.dir':    Image(GPath((bosh.dirs['images']).join(u'diamond_red_off.png')),PNG),
    'off.white.dir':  Image(GPath((bosh.dirs['images']).join(u'diamond_white_off.png')),PNG),
    'off.orange.dir': Image(GPath((bosh.dirs['images']).join(u'diamond_orange_off.png')),PNG),
    'off.yellow.dir': Image(GPath((bosh.dirs['images']).join(u'diamond_yellow_off.png')),PNG),
    #--Off/Directory - Wizard
    'off.green.dir.wiz':  Image(GPath((bosh.dirs['images']).join(u'diamond_green_off_wiz.png')),PNG),
    #grey
    'off.red.dir.wiz':    Image(GPath((bosh.dirs['images']).join(u'diamond_red_off_wiz.png')),PNG),
    'off.white.dir.wiz':  Image(GPath((bosh.dirs['images']).join(u'diamond_white_off_wiz.png')),PNG),
    'off.orange.dir.wiz': Image(GPath((bosh.dirs['images']).join(u'diamond_orange_off_wiz.png')),PNG),
    'off.yellow.dir.wiz': Image(GPath((bosh.dirs['images']).join(u'diamond_yellow_off_wiz.png')),PNG),
    #--On/Directory
    'on.green.dir':  Image(GPath((bosh.dirs['images']).join(u'diamond_green_inc.png')),PNG),
    'on.grey.dir':   Image(GPath((bosh.dirs['images']).join(u'diamond_grey_inc.png')),PNG),
    'on.red.dir':    Image(GPath((bosh.dirs['images']).join(u'diamond_red_inc.png')),PNG),
    'on.white.dir':  Image(GPath((bosh.dirs['images']).join(u'diamond_white_inc.png')),PNG),
    'on.orange.dir': Image(GPath((bosh.dirs['images']).join(u'diamond_orange_inc.png')),PNG),
    'on.yellow.dir': Image(GPath((bosh.dirs['images']).join(u'diamond_yellow_inc.png')),PNG),
    #--On/Directory - Wizard
    'on.green.dir.wiz':  Image(GPath((bosh.dirs['images']).join(u'diamond_green_inc_wiz.png')),PNG),
    #grey
    'on.red.dir.wiz':    Image(GPath((bosh.dirs['images']).join(u'diamond_red_inc_wiz.png')),PNG),
    'on.white.dir.wiz':  Image(GPath((bosh.dirs['images']).join(u'diamond_white_off_wiz.png')),PNG),
    'on.orange.dir.wiz': Image(GPath((bosh.dirs['images']).join(u'diamond_orange_inc_wiz.png')),PNG),
    'on.yellow.dir.wiz': Image(GPath((bosh.dirs['images']).join(u'diamond_yellow_inc_wiz.png')),PNG),
    #--Broken
    'corrupt':   Image(GPath((bosh.dirs['images']).join(u'red_x.png')),PNG),
    }.items())

# Gui Ids ---------------------------------------------------------------------
#------------------------------------------------------------------------------
#--Generic
ID_EDIT   = 6005
#--Label Menus
ID_GROUPS    = IdList(10100,290,'EDIT','NONE')
ID_TAGS      = IdList(10600, 90,'AUTO','COPY')
