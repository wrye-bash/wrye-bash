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

"""This module contains some constants ripped out of basher.py"""
from .. import bass, bush
from ..balt import ImageList
from ..gui import ImageWrapper, DEFAULT_POSITION

# Color Descriptions ----------------------------------------------------------
colorInfo = {
    u'default.text': (_(u'Default Text'),
        _(u'This is the text color used for list items when no other is '
          u'specified.  For example, an ESP that is not mergeable or ghosted, '
          u'and has no other problems.'),
    ),
    u'default.bkgd': (_(u'Default Background'),
        _(u'This is the text background color used for list items when no '
          u'other is specified.  For example, an ESM that is not ghosted.'),
    ),
    u'default.warn': (_(u'Default Warning'),
        _(u'This is the color used for text that is communicating some sort '
          u'of warning or error.'),
    ),
    u'mods.text.esm': (_(u'ESM'),
        _(u'Tabs: Mods, Saves') + u'\n\n' +
        _(u'This is the text color used for ESMs in the Mods Tab, and in the '
          u'Masters info on both the Mods Tab and Saves Tab.'),),
    u'mods.text.esl': (_(u'ESL'),
        _(u'Tabs: Mods, Saves') + u'\n\n' +
        _(u'This is the text color used for ESLs in the Mods Tab, and in the '
          u'Masters info on both the Mods Tab and Saves Tab.'),),
    u'mods.text.eslm': (_(u'ESLM'),
        _(u'Tabs: Mods, Saves') + u'\n\n' +
        _(u'This is the text color used for ESLs with a master flag in the '
          u'Mods Tab, and in the Masters info on both the Mods Tab and Saves '
          u'Tab.'),),
    u'mods.text.noMerge': (_(u"'NoMerge' Plugin"),
        _(u'Tabs: Mods') + u'\n\n' +
        _(u'This is the text color used for a mergeable plugin that is '
          u"tagged 'NoMerge'."),
    ),
    u'mods.text.bashedPatch': (_(u'Bashed Patch'),
        _(u'Tabs: Mods') + u'\n\n' +
        _(u'This is the text color used for Bashed Patches.'),
    ),
    u'mods.bkgd.doubleTime.exists': (_(u'Inactive Time Conflict'),
        _(u'Tabs: Mods') + u'\n\n' +
        _(u'This is the background color used for a plugin with an inactive '
          u'time conflict.  This means that two or more plugins have the same '
          u'timestamp, but only one (or none) of them is active.'),
    ),
    u'mods.bkgd.doubleTime.load': (_(u'Active Time Conflict'),
        _(u'Tabs: Mods') + u'\n\n' +
        _(u'This is the background color used for a plugin with an active '
          u'time conflict.  This means that two or more plugins with the same '
          u'timestamp are active.'),
    ),
    u'mods.bkgd.deactivate': (_(u"'Deactivate' Plugin"),
        _(u'Tabs: Mods') + u'\n\n' +
        _(u'This is the background color used for an active plugin that is '
          u"tagged 'Deactivate'."),
    ),
    u'mods.bkgd.ghosted': (_(u'Ghosted Plugin'),
        _(u'Tabs: Mods') + u'\n\n' +
        _(u'This is the background color used for a ghosted plugin.'),
    ),
    u'ini.bkgd.invalid': (_(u'Invalid INI Tweak'),
        _(u'Tabs: INI Edits') + u'\n\n' +
        _(u'This is the background color used for a tweak file that is invalid'
          u' for the currently selected target INI.'),
    ),
    u'tweak.bkgd.invalid': (_(u'Invalid Tweak Line'),
        _(u'Tabs: INI Edits') + u'\n\n' +
        _(u'This is the background color used for a line in a tweak file that '
          u'is invalid for the currently selected target INI.'),
    ),
    u'tweak.bkgd.mismatched': (_(u'Mismatched Tweak Line'),
        _(u'Tabs: INI Edits') + u'\n\n' +
        _(u'This is the background color used for a line in a tweak file that '
          u'does not match what is set in the target INI.'),
    ),
    u'tweak.bkgd.matched': (_(u'Matched Tweak Line'),
        _(u'Tabs: INI Edits') + u'\n\n' +
        _(u'This is the background color used for a line in a tweak file that '
          u'matches what is set in the target INI.'),
    ),
    u'installers.text.complex': (_(u'Complex Installer'),
        _(u'Tabs: Installers') + u'\n\n' +
        _(u'This is the text color used for a complex BAIN package.'),
    ),
    u'installers.text.invalid': (_(u'Invalid'),
        _(u'Tabs: Installers') + u'\n\n' +
        _(u'This is the text color used for invalid packages.'),
    ),
    u'installers.text.marker': (_(u'Marker'),
        _(u'Tabs: Installers') + u'\n\n' +
        _(u'This is the text color used for Markers.'),
    ),
    u'installers.bkgd.skipped': (_(u'Skipped Files'),
        _(u'Tabs: Installers') + u'\n\n' +
        _(u'This is the background color used for a package with files that '
          u'will not be installed by BAIN.  This means some files are selected'
          u' to be installed, but due to your current Skip settings (for '
          u'example, Skip DistantLOD), will not be installed.'),
    ),
    u'installers.bkgd.outOfOrder': (_(u'Installer Out of Order'),
        _(u'Tabs: Installers') + u'\n\n' +
        _(u'This is the background color used for an installer with files '
          u'installed, that should be overridden by a package with a higher '
          u'install order.  It can be repaired with an Anneal or Anneal All.'),
    ),
    u'installers.bkgd.dirty': (_(u'Dirty Installer'),
        _(u'Tabs: Installers') + u'\n\n' +
        _(u'This is the background color used for an installer that is '
          u'configured in a "dirty" manner.  This means changes have been made'
          u' to its configuration, and an Anneal or Install needs to be '
          u'performed to make the install match what is configured.'),
    ),
    u'screens.bkgd.image': (_(u'Screenshot Background'),
        _(u'Tabs: Saves, Screens') + u'\n\n' +
        _(u'This is the background color used for images.'),
    ),
}
if bush.game.check_esl:
    colorInfo[u'mods.text.mergeable'] = (_(u'ESL Capable plugin'),
            _(u'Tabs: Mods') + u'\n\n' +
            _(u'This is the text color used for ESL Capable plugins.'),
        )
else:
    colorInfo[u'mods.text.mergeable'] = (_(u'Mergeable Plugin'),
            _(u'Tabs: Mods') + u'\n\n' +
            _(u'This is the text color used for mergeable plugins.'),
        )

if bush.game.Esp.check_master_sizes:
    colorInfo[u'mods.bkgd.size_mismatch'] = (_(u'Size Mismatch'),
        _(u'Tabs: Mods') + u'\n\n' +
        _(u'This is the background color used for plugin masters that have a '
          u'stored size not matching the one of the plugin on disk, and for '
          u'plugins that have at least one such master.')
    )

#--Load config/defaults
settingDefaults = { # keep current naming format till refactored
    #--Basics
    u'bash.version': 0,
    u'bash.backupPath': None,
    u'bash.frameMax': False, # True if maximized
    u'bash.page': 1,
    u'bash.useAltName': True,
    u'bash.show_global_menu': True,
    u'bash.pluginEncoding': u'cp1252',    # Western European
    u'bash.show_internal_keys': False,
    u'bash.restore_scroll_positions': False,
    u'bash.autoSizeListColumns': 0,
    #--Colors
    u'bash.colors': {
        #--Common Colors
        u'default.text':                 (0,   0,   0),   # 'BLACK'
        u'default.bkgd':                 (255, 255, 255), # 'WHITE'
        u'default.warn':                 (255, 0,   0),
        #--Mods Tab
        u'mods.text.esm':                (0,   0,   255), # 'BLUE'
        u'mods.text.mergeable':          (0,   153, 0),
        u'mods.text.noMerge':            (150, 130, 0),
        u'mods.bkgd.doubleTime.exists':  (255, 220, 220),
        u'mods.bkgd.doubleTime.load':    (255, 100, 100),
        u'mods.bkgd.deactivate':         (255, 100, 100),
        u'mods.bkgd.ghosted':            (232, 232, 232),
        u'mods.text.eslm':               (123, 29,  223),
        u'mods.text.esl':                (226, 54,  197),
        u'mods.text.bashedPatch':        (30,  157, 251),
        #--INI Edits Tab
        u'ini.bkgd.invalid':             (223, 223, 223),
        u'tweak.bkgd.invalid':           (255, 213, 170),
        u'tweak.bkgd.mismatched':        (255, 255, 191),
        u'tweak.bkgd.matched':           (193, 255, 193),
        #--Installers Tab
        u'installers.text.complex':      (35,  35,  142), # 'NAVY'
        u'installers.text.invalid':      (128, 128, 128), # 'GREY'
        u'installers.text.marker':       (230, 97,  89),
        u'installers.bkgd.skipped':      (224, 224, 224),
        u'installers.bkgd.outOfOrder':   (255, 255, 0),
        u'installers.bkgd.dirty':        (255, 187, 51),
        #--Screens Tab
        u'screens.bkgd.image':           (100, 100, 100),
    },
    #--BSA Redirection
    u'bash.bsaRedirection': True,
    # Wrye Bash: Localization
    u'bash.l10n.editor.param_fmt': u'%s',
    u'bash.l10n.editor.path': u'',
    # Wrye Bash: Load Order
    u'bash.load_order.lock_active_plugins': True,
    #--Wrye Bash: StatusBar
    u'bash.statusbar.iconSize': 16,
    u'bash.statusbar.hide': set(),
    u'bash.statusbar.order': [],
    u'bash.statusbar.showversion': False,
    #--Wrye Bash: Group and Rating
    u'bash.mods.groups': [
        u'Root',
        u'Library',
        u'Cosmetic',
        u'Clothing',
        u'Weapon',
        u'Tweak',
        u'Overhaul',
        u'Misc.',
        u'Magic',
        u'NPC',
        u'Home',
        u'Place',
        u'Quest',
        u'Last',
    ],
    u'bash.mods.ratings': [u'+', u'1', u'2', u'3', u'4', u'5', u'=', u'~'],
    #--Wrye Bash: Col (Sort) Names
    u'bash.colNames': {
        u'Mod Status': _(u'Mod Status'),
        u'Author': _(u'Author'),
        u'Cell': _(u'Cell'),
        u'CRC': _(u'CRC'),
        u'Current Order': _(u'Current LO'),
        u'File': _(u'File'),
        u'Files': _(u'Files'),
        u'Group': _(u'Group'),
        u'Indices': _(u'Index'),
        u'Installer': _(u'Installer'),
        u'Load Order': _(u'Load Order'),
        u'Modified': _(u'Modified'),
        u'Num': _(u'MI'),
        u'Order': _(u'Order'),
        u'Package': _(u'Package'),
        u'PlayTime': _(u'Hours'),
        u'Player': _(u'Player'),
        u'Rating': _(u'Rating'),
        u'Size': _(u'Size'),
        u'Status': _(u'Status'),
    },
    #--Wrye Bash: Masters
    u'bash.masters.cols': [u'File', u'Num', u'Current Order'],
    u'bash.masters.esmsFirst': False,
    u'bash.masters.selectedFirst': False,
    u'bash.masters.sort': u'Num',
    u'bash.masters.colReverse': {},
    u'bash.masters.colWidths': {
        u'File': 80,
        u'Num': 30,
        u'Current Order': 60,
        'Indices': 50,
    },
    #--Wrye Bash: Mod Docs
    u'bash.modDocs.show': False,
    u'bash.modDocs.dir': None,
    #--Installers
    u'bash.installers.cols': [u'Package', u'Order', u'Modified', u'Size',
                              u'Files'],
    u'bash.installers.colReverse': {},
    u'bash.installers.sort': u'Order',
    u'bash.installers.colWidths': {
        u'Package': 230,
        u'Order': 25,
        u'Modified': 135,
        u'Size': 75,
        u'Files': 55,
    },
    u'bash.installers.page': 0,
    u'bash.installers.isFirstRun': True,
    u'bash.installers.enabled': True,
    u'bash.installers.autoAnneal': True,
    u'bash.installers.autoWizard': True,
    u'bash.installers.wizardOverlay': True,
    u'bash.installers.fastStart': True,
    u'bash.installers.autoRefreshBethsoft': False,
    u'bash.installers.autoRefreshProjects': True,
    u'bash.installers.ignore_fomods': False,
    u'bash.installers.removeEmptyDirs': True,
    u'bash.installers.skipScreenshots': False,
    u'bash.installers.skipScriptSources': False,
    u'bash.installers.skipImages': False,
    u'bash.installers.skipDocs': False,
    u'bash.installers.skipDistantLOD': False,
    u'bash.installers.skipLandscapeLODMeshes': False,
    u'bash.installers.skipLandscapeLODTextures': False,
    u'bash.installers.skipLandscapeLODNormals': False,
    u'bash.installers.skipTESVBsl': True,
    u'bash.installers.allowOBSEPlugins': True,
    u'bash.installers.renameStrings': True,
    u'bash.installers.redirect_scripts': True,
    u'bash.installers.sortProjects': False,
    u'bash.installers.sortActive': False,
    u'bash.installers.sortStructure': False,
    u'bash.installers.conflictsReport.showLower': True,
    u'bash.installers.conflictsReport.showInactive': False,
    u'bash.installers.conflictsReport.showBSAConflicts': True,
    u'bash.installers.goodDlls': {},
    u'bash.installers.badDlls': {},
    u'bash.installers.onDropFiles.action': None,
    u'bash.installers.commentsSplitterSashPos': 0,
    #--Wrye Bash: Wizards
    u'bash.fomod.size': (600, 500),
    u'bash.fomod.pos': DEFAULT_POSITION,
    u'bash.fomod.use_table': False,
    u'bash.wizard.size': (600, 500),
    u'bash.wizard.pos': DEFAULT_POSITION,
    #--Wrye Bash: INI Tweaks
    u'bash.ini.cols': [u'File', u'Installer'],
    u'bash.ini.sort': u'File',
    u'bash.ini.colReverse': {},
    u'bash.ini.sortValid': True,
    u'bash.ini.colWidths': {
        u'File': 300,
        u'Installer': 100,
    },
    u'bash.ini.choices': {},
    u'bash.ini.choice': 0,
    u'bash.ini.allowNewLines': bush.game.Ini.allow_new_lines,
    #--Wrye Bash: Mods
    u'bash.mods.autoGhost': False,
    u'bash.mods.auto_flag_esl': True,
    u'bash.mods.cols': [u'File', u'Load Order', u'Installer', u'Modified',
                        u'Size', u'Author', u'CRC'],
    u'bash.mods.esmsFirst': False,
    u'bash.mods.selectedFirst': False,
    u'bash.mods.sort': u'Load Order',
    u'bash.mods.colReverse': {},
    u'bash.mods.colWidths': {
        u'Author': 100,
        u'File': 200,
        u'Group': 10,
        u'Installer': 100,
        u'Load Order': 25,
        u'Indices': 50,
        u'Modified': 135,
        u'Rating': 10,
        u'Size': 75,
        u'CRC': 60,
        u'Mod Status': 50,
    },
    u'bash.mods.details.colWidths': {},
    u'bash.mods.details.colReverse': {},
    u'bash.mods.renames': {},
    u'bash.mods.scanDirty': True,
    u'bash.mods.export.skip': u'',
    u'bash.mods.export.deprefix': u'',
    u'bash.mods.export.skipcomments': False,
    #--Wrye Bash: Saves
    u'bash.saves.cols': [u'File', u'Modified', u'Size', u'PlayTime', u'Player',
                         u'Cell'],
    u'bash.saves.sort': u'Modified',
    u'bash.saves.colReverse': {
        u'Modified': True,
    },
    u'bash.saves.colWidths': {
        u'File': 375,
        u'Modified': 135,
        u'Size': 65,
        u'PlayTime': 50,
        u'Player': 70,
        u'Cell': 80,
    },
    u'bash.saves.details.colWidths': {},
    u'bash.saves.details.colReverse': {},
    #--Wrye Bash: BSAs
    u'bash.BSAs.cols': [u'File', u'Modified', u'Size'],
    u'bash.BSAs.sort': u'File',
    u'bash.BSAs.colReverse': {
        u'Modified': True,
    },
    u'bash.BSAs.colWidths': {
        u'File': 150,
        u'Modified': 150,
        u'Size': 75,
    },
    #--Wrye Bash: Screens
    u'bash.screens.cols': [u'File', u'Modified', u'Size'],
    u'bash.screens.sort': u'File',
    u'bash.screens.colReverse': {
        u'Modified': True,
    },
    u'bash.screens.colWidths': {
        u'File': 100,
        u'Modified': 150,
        u'Size': 75,
    },
    u'bash.screens.jpgQuality': 95,
    u'bash.screens.jpgCustomQuality': 75,
    #--BOSS:
    u'BOSS.ClearLockTimes': True,
    u'BOSS.AlwaysUpdate': True,
    u'BOSS.UseGUI': False,
}

# No need to store defaults for all the xEdits for all games
settingDefaults[bush.game.Xe.xe_key_prefix + u'.iKnowWhatImDoing'] = False
settingDefaults[bush.game.Xe.xe_key_prefix + u'.skip_bsas'] = False

if bush.game.Esp.check_master_sizes:
    settingDefaults[u'bash.colors'][u'mods.bkgd.size_mismatch'] = (255, 238,
                                                                   217)

if bush.game.has_esl: # Enable Index column by default for ESL games
    settingDefaults[u'bash.mods.cols'].insert(2, u'Indices')
    settingDefaults['bash.masters.cols'].insert(1, 'Indices')

# Images ----------------------------------------------------------------------
#------------------------------------------------------------------------------
imDirJn = bass.dirs[u'images'].join
def _png(fname): return ImageWrapper(imDirJn(fname))

#--Image lists
installercons = ImageList(16,16)
installercons.images.extend({
    #--Off/Archive
    u'off.green':  _png(u'checkbox_green_off.png'),
    u'off.grey':   _png(u'checkbox_grey_off.png'),
    u'off.red':    _png(u'checkbox_red_off.png'),
    u'off.white':  _png(u'checkbox_white_off.png'),
    u'off.orange': _png(u'checkbox_orange_off.png'),
    u'off.yellow': _png(u'checkbox_yellow_off.png'),
    #--Off/Archive - Wizard
    u'off.green.wiz':    _png(u'checkbox_green_off_wiz.png'),
    #grey
    u'off.red.wiz':      _png(u'checkbox_red_off_wiz.png'),
    u'off.white.wiz':    _png(u'checkbox_white_off_wiz.png'),
    u'off.orange.wiz':   _png(u'checkbox_orange_off_wiz.png'),
    u'off.yellow.wiz':   _png(u'checkbox_yellow_off_wiz.png'),
    #--On/Archive
    u'on.green':  _png(u'checkbox_green_inc.png'),
    u'on.grey':   _png(u'checkbox_grey_inc.png'),
    u'on.red':    _png(u'checkbox_red_inc.png'),
    u'on.white':  _png(u'checkbox_white_inc.png'),
    u'on.orange': _png(u'checkbox_orange_inc.png'),
    u'on.yellow': _png(u'checkbox_yellow_inc.png'),
    #--On/Archive - Wizard
    u'on.green.wiz':  _png(u'checkbox_green_inc_wiz.png'),
    #grey
    u'on.red.wiz':    _png(u'checkbox_red_inc_wiz.png'),
    u'on.white.wiz':  _png(u'checkbox_white_inc_wiz.png'),
    u'on.orange.wiz': _png(u'checkbox_orange_inc_wiz.png'),
    u'on.yellow.wiz': _png(u'checkbox_yellow_inc_wiz.png'),
    #--Off/Directory
    u'off.green.dir':  _png(u'diamond_green_off.png'),
    u'off.grey.dir':   _png(u'diamond_grey_off.png'),
    u'off.red.dir':    _png(u'diamond_red_off.png'),
    u'off.white.dir':  _png(u'diamond_white_off.png'),
    u'off.orange.dir': _png(u'diamond_orange_off.png'),
    u'off.yellow.dir': _png(u'diamond_yellow_off.png'),
    #--Off/Directory - Wizard
    u'off.green.dir.wiz':  _png(u'diamond_green_off_wiz.png'),
    #grey
    u'off.red.dir.wiz':    _png(u'diamond_red_off_wiz.png'),
    u'off.white.dir.wiz':  _png(u'diamond_white_off_wiz.png'),
    u'off.orange.dir.wiz': _png(u'diamond_orange_off_wiz.png'),
    u'off.yellow.dir.wiz': _png(u'diamond_yellow_off_wiz.png'),
    #--On/Directory
    u'on.green.dir':  _png(u'diamond_green_inc.png'),
    u'on.grey.dir':   _png(u'diamond_grey_inc.png'),
    u'on.red.dir':    _png(u'diamond_red_inc.png'),
    u'on.white.dir':  _png(u'diamond_white_inc.png'),
    u'on.orange.dir': _png(u'diamond_orange_inc.png'),
    u'on.yellow.dir': _png(u'diamond_yellow_inc.png'),
    #--On/Directory - Wizard
    u'on.green.dir.wiz':  _png(u'diamond_green_inc_wiz.png'),
    #grey
    u'on.red.dir.wiz':    _png(u'diamond_red_inc_wiz.png'),
    u'on.white.dir.wiz':  _png(u'diamond_white_off_wiz.png'),
    u'on.orange.dir.wiz': _png(u'diamond_orange_inc_wiz.png'),
    u'on.yellow.dir.wiz': _png(u'diamond_yellow_inc_wiz.png'),
    #--Broken
    u'corrupt':   _png(u'red_x.png'),
}.items())

#--Buttons
def imageList(template):
    return [ImageWrapper(imDirJn(template % x)) for x in (16, 24, 32)]

# TODO(65): game handling refactoring - some of the buttons are game specific
toolbar_buttons = (
    (u'ISOBL', imageList(u'tools/isobl%s.png'),
    _(u"Launch InsanitySorrow's Oblivion Launcher")),
    (u'ISRMG', imageList(u"tools/insanity'sreadmegenerator%s.png"),
    _(u"Launch InsanitySorrow's Readme Generator")),
    (u'ISRNG', imageList(u"tools/insanity'srng%s.png"),
    _(u"Launch InsanitySorrow's Random Name Generator")),
    (u'ISRNPCG', imageList(u'tools/randomnpc%s.png'),
    _(u"Launch InsanitySorrow's Random NPC Generator")),
    (u'OBFEL', imageList(u'tools/oblivionfaceexchangerlite%s.png'),
    _(u'Oblivion Face Exchange Lite')),
    (u'OBMLG', imageList(u'tools/modlistgenerator%s.png'),
    _(u'Oblivion Mod List Generator')),
    (u'BSACMD', imageList(u'tools/bsacommander%s.png'),
    _(u'Launch BSA Commander')),
    (u'Tabula', imageList(u'tools/tabula%s.png'),
     _(u'Launch Tabula')),
    (u'Tes4FilesPath', imageList(u'tools/tes4files%s.png'),
    _(u'Launch TES4Files')),
)

modeling_tools_buttons = (
    (u'AutoCad', imageList(u'tools/autocad%s.png'), _(u'Launch AutoCad')),
    (u'BlenderPath', imageList(u'tools/blender%s.png'), _(u'Launch Blender')),
    (u'Dogwaffle', imageList(u'tools/dogwaffle%s.png'),
     _(u'Launch Dogwaffle')),
    (u'GmaxPath', imageList(u'tools/gmax%s.png'), _(u'Launch Gmax')),
    (u'MayaPath', imageList(u'tools/maya%s.png'), _(u'Launch Maya')),
    (u'MaxPath', imageList(u'tools/3dsmax%s.png'), _(u'Launch 3dsMax')),
    (u'Milkshape3D', imageList(u'tools/milkshape3d%s.png'),
     _(u'Launch Milkshape 3D')),
    (u'Mudbox', imageList(u'tools/mudbox%s.png'), _(u'Launch Mudbox')),
    (u'Sculptris', imageList(u'tools/sculptris%s.png'),
     _(u'Launch Sculptris')),
    (u'SpeedTree', imageList(u'tools/speedtree%s.png'),
     _(u'Launch SpeedTree')),
    (u'Treed', imageList(u'tools/treed%s.png'), _(u'Launch Tree\[d\]')),
    (u'Wings3D', imageList(u'tools/wings3d%s.png'), _(u'Launch Wings 3D')),
)

texture_tool_buttons = (
    (u'AniFX', imageList(u'tools/anifx%s.png'), _(u'Launch AniFX')),
    (u'ArtOfIllusion', imageList(u'tools/artofillusion%s.png'),
     _(u'Launch Art Of Illusion')),
    (u'Artweaver', imageList(u'tools/artweaver%s.png'),
     _(u'Launch Artweaver')),
    (u'CrazyBump', imageList(u'tools/crazybump%s.png'),
     _(u'Launch CrazyBump')),
    (u'DDSConverter', imageList(u'tools/ddsconverter%s.png'),
     _(u'Launch DDSConverter')),
    (u'DeepPaint', imageList(u'tools/deeppaint%s.png'),
     _(u'Launch DeepPaint')),
    (u'FastStone', imageList(u'tools/faststoneimageviewer%s.png'),
     _(u'Launch FastStone Image Viewer')),
    (u'Genetica', imageList(u'tools/genetica%s.png'), _(u'Launch Genetica')),
    (u'GeneticaViewer', imageList(u'tools/geneticaviewer%s.png'),
     _(u'Launch Genetica Viewer')),
    (u'GIMP', imageList(u'tools/gimp%s.png'), _(u'Launch GIMP')),
    (u'IcoFX', imageList(u'tools/icofx%s.png'), _(u'Launch IcoFX')),
    (u'Inkscape', imageList(u'tools/inkscape%s.png'), _(u'Launch Inkscape')),
    (u'IrfanView', imageList(u'tools/irfanview%s.png'),
     _(u'Launch IrfanView')),
    (u'Krita', imageList(u'tools/krita%s.png'), _(u'Launch Krita')),
    (u'MaPZone', imageList(u'tools/mapzone%s.png'), _(u'Launch MaPZone')),
    (u'MyPaint', imageList(u'tools/mypaint%s.png'), _(u'Launch MyPaint')),
    (u'NVIDIAMelody', imageList(u'tools/nvidiamelody%s.png'),
     _(u'Launch Nvidia Melody')),
    (u'PaintNET', imageList(u'tools/paint.net%s.png'), _(u'Launch Paint.NET')),
    (u'PaintShopPhotoPro', imageList(u'tools/paintshopprox3%s.png'),
     _(u'Launch PaintShop Photo Pro')),
    (u'PhotoshopPath', imageList(u'tools/photoshop%s.png'),
     _(u'Launch Photoshop')),
    (u'PhotoScape', imageList(u'tools/photoscape%s.png'),
     _(u'Launch PhotoScape')),
    (u'PhotoSEAM', imageList(u'tools/photoseam%s.png'),
     _(u'Launch PhotoSEAM')),
    (u'Photobie', imageList(u'tools/photobie%s.png'), _(u'Launch Photobie')),
    (u'PhotoFiltre', imageList(u'tools/photofiltre%s.png'),
     _(u'Launch PhotoFiltre')),
    (u'PixelStudio', imageList(u'tools/pixelstudiopro%s.png'),
     _(u'Launch Pixel Studio Pro')),
    (u'Pixia', imageList(u'tools/pixia%s.png'), _(u'Launch Pixia')),
    (u'TextureMaker', imageList(u'tools/texturemaker%s.png'),
     _(u'Launch TextureMaker')),
    (u'TwistedBrush', imageList(u'tools/twistedbrush%s.png'),
     _(u'Launch TwistedBrush')),
    (u'WTV', imageList(u'tools/wtv%s.png'),
     _(u'Launch Windows Texture Viewer')),
    (u'xNormal', imageList(u'tools/xnormal%s.png'), _(u'Launch xNormal')),
    (u'XnView', imageList(u'tools/xnview%s.png'), _(u'Launch XnView')),
)

audio_tools = (
    (u'Audacity', imageList(u'tools/audacity%s.png'), _(u'Launch Audacity')),
    (u'ABCAmberAudioConverter',
     imageList(u'tools/abcamberaudioconverter%s.png'),
    _(u'Launch ABC Amber Audio Converter')),
    (u'Switch', imageList(u'tools/switch%s.png'), _(u'Launch Switch')),
)

misc_tools = (
    (u'Fraps', imageList(u'tools/fraps%s.png'), _(u'Launch Fraps')),
    (u'MAP', imageList(u'tools/interactivemapofcyrodiil%s.png'),
        _(u'Interactive Map of Cyrodiil and Shivering Isles')),
    (u'LogitechKeyboard', imageList(u'tools/logitechkeyboard%s.png'),
        _(u'Launch LogitechKeyboard')),
    (u'MediaMonkey', imageList(u'tools/mediamonkey%s.png'),
        _(u'Launch MediaMonkey')),
    (u'NPP', imageList(u'tools/notepad++%s.png'), _(u'Launch Notepad++')),
    (u'Steam', imageList(u'steam%s.png'), _(u'Launch Steam')),
    (u'EVGAPrecision', imageList(u'tools/evgaprecision%s.png'),
        _(u'Launch EVGA Precision')),
    (u'WinMerge', imageList(u'tools/winmerge%s.png'), _(u'Launch WinMerge')),
    (u'FreeMind', imageList(u'tools/freemind%s.png'), _(u'Launch FreeMind')),
    (u'Freeplane', imageList(u'tools/freeplane%s.png'),
     _(u'Launch Freeplane')),
    (u'FileZilla', imageList(u'tools/filezilla%s.png'),
     _(u'Launch FileZilla')),
    (u'EggTranslator', imageList(u'tools/eggtranslator%s.png'),
        _(u'Launch Egg Translator')),
    (u'RADVideo', imageList(u'tools/radvideotools%s.png'),
        _(u'Launch RAD Video Tools')),
    (u'WinSnap', imageList(u'tools/winsnap%s.png'), _(u'Launch WinSnap')),
)
