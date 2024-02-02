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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module contains some constants ripped out of basher.py"""
from .. import bush
from ..bolt import GPath
from ..game import MergeabilityCheck
from ..gui import DEFAULT_POSITION

# Color Descriptions ----------------------------------------------------------
colorInfo = {
    'default.text': (_('Default Text'),
        _('This is the text color used for list items when no other is '
          'specified. For example, an ESP that is not mergeable or ghosted, '
          'and has no other problems.'),
    ),
    'default.bkgd': (_('Default Background'),
        _('This is the text background color used for list items when no '
          'other is specified. For example, an ESM that is not ghosted.'),
    ),
    'default.warn': (_('Default Warning'),
        _('This is the color used for text that is communicating some sort '
          'of warning or error.'),
    ),
    'mods.text.esm': ('ESM',
        _('Tabs: Mods, Saves') + '\n\n' +
        _('This is the text color used for ESMs on the Mods Tab, and in the '
          'Masters info on both the Mods Tab and Saves Tab.'),
    ),
    'mods.bkgd.ghosted': (_('Ghosted Plugin'),
        _('Tabs: Mods') + '\n\n' +
        _('This is the background color used for a ghosted plugin.'),
    ),
    'ini.bkgd.invalid': (_('Invalid INI Tweak'),
        _('Tabs: INI Edits') + '\n\n' +
        _('This is the background color used for a tweak file that is invalid'
          ' for the currently selected target INI.'),
    ),
    'tweak.bkgd.invalid': (_('Invalid Tweak Line'),
        _('Tabs: INI Edits') + '\n\n' +
        _('This is the background color used for a line in a tweak file that '
          'is invalid for the currently selected target INI.'),
    ),
    'tweak.bkgd.mismatched': (_('Mismatched Tweak Line'),
        _('Tabs: INI Edits') + '\n\n' +
        _('This is the background color used for a line in a tweak file that '
          'does not match what is set in the target INI.'),
    ),
    'tweak.bkgd.matched': (_('Matched Tweak Line'),
        _('Tabs: INI Edits') + '\n\n' +
        _('This is the background color used for a line in a tweak file that '
          'matches what is set in the target INI.'),
    ),
    'installers.text.complex': (_('Complex Installer'),
        _('Tabs: Installers') + '\n\n' +
        _('This is the text color used for a complex BAIN package.'),
    ),
    'installers.text.invalid': (_('Invalid'),
        _('Tabs: Installers') + '\n\n' +
        _('This is the text color used for invalid packages.'),
    ),
    'installers.text.marker': (_('Marker'),
        _('Tabs: Installers') + '\n\n' +
        _('This is the text color used for Markers.'),
    ),
    'installers.bkgd.skipped': (_('Skipped Files'),
        _('Tabs: Installers') + '\n\n' +
        _('This is the background color used for a package with files that '
          'will not be installed by BAIN. This means some files are selected '
          'to be installed, but due to your current Skip settings (for '
          'example, Skip DistantLOD), will not be installed.'),
    ),
    'installers.bkgd.outOfOrder': (_('Installer Out of Order'),
        _('Tabs: Installers') + '\n\n' +
        _('This is the background color used for an installer with files '
          'installed, that should be overridden by a package with a higher '
          'install order. It can be repaired with an Anneal or Anneal All.'),
    ),
    'installers.bkgd.dirty': (_('Dirty Installer'),
        _('Tabs: Installers') + '\n\n' +
        _('This is the background color used for an installer that is '
          'configured in a "dirty" manner. This means changes have been made '
          'to its configuration, and an Anneal or Install needs to be '
          'performed to make the install match what is configured.'),
    ),
    'screens.bkgd.image': (_('Screenshot Background'),
        _('Tabs: Saves, Screenshots') + '\n\n' +
        _('This is the background color used for images.'),
    ),
}

# Only show color options when the game actually supports them
# Do masters have working DATA subrecords? ------------------------------------
if bush.game.Esp.check_master_sizes:
    colorInfo['mods.bkgd.size_mismatch'] = (_('Size Mismatch'),
        _('Tabs: Mods') + '\n\n' +
        _('This is the background color used for plugin masters that have a '
          'stored size not matching the one of the plugin on disk, and for '
          'plugins that have at least one such master.'),
    )

# Does the LO use timestamps? -------------------------------------------------
##: Is this condition OK? We can't really call load_order to check...
if not bush.game.using_txt_file:
    colorInfo['mods.bkgd.doubleTime.exists'] = (_('Inactive Time Conflict'),
        _('Tabs: Mods') + '\n\n' +
        _('This is the background color used for a plugin with an inactive '
          'time conflict. This means that two or more plugins have the same '
          'timestamp, but only one (or none) of them is active.'),
    )
    colorInfo['mods.bkgd.doubleTime.load'] = (_('Active Time Conflict'),
        _('Tabs: Mods') + '\n\n' +
        _('This is the background color used for a plugin with an active '
          'time conflict. This means that two or more plugins with the same '
          'timestamp are active.'),
    )

# Can we create a BP? ---------------------------------------------------------
if bush.game.Esp.canBash:
    colorInfo['mods.text.bashedPatch'] = ('Bashed Patch',
        _('Tabs: Mods') + '\n\n' +
        _('This is the text color used for Bashed Patches.'),
    )

# Are ESLs supported? ---------------------------------------------------------
if bush.game.has_esl:
    colorInfo['mods.text.esl'] = ('ESL',
        _('Tabs: Mods, Saves') + '\n\n' +
        _('This is the text color used for ESLs on the Mods Tab, and in the '
          'Masters info on both the Mods Tab and Saves Tab.'),
    )
    colorInfo['mods.text.eslm'] = ('ESLM',
        _('Tabs: Mods, Saves') + '\n\n' +
        _('This is the text color used for ESLs with a master flag on the '
          'Mods Tab, and in the Masters info on both the Mods Tab and Saves '
          'Tab.'),
    )

# Are Overlay plugins supported? ----------------------------------------------
if bush.game.has_overlay_plugins:
    colorInfo['mods.text.eso'] = (_('Overlay Plugin'),
        _('Tabs: Mods') + '\n\n' +
        _('This is the text color used for Overlay plugins on the Mods Tab.'),
    )
    colorInfo['mods.text.esom'] = (_('Overlay Master'),
        _('Tabs: Mods') + '\n\n' +
        _('This is the text color used for Overlay plugins with a master flag '
          'on the Mods Tab.'),
    )

# What do we check w.r.t. mergeability? ---------------------------------------
if MergeabilityCheck.OVERLAY_CHECK in bush.game.mergeability_checks:
    if MergeabilityCheck.ESL_CHECK in bush.game.mergeability_checks:
        if MergeabilityCheck.MERGE in bush.game.mergeability_checks:
            mc_title = _('Mergeable, ESL-Capable or Overlay-Capable Plugin')
            mc_desc = _('This is the text color used for plugins that could '
                        'be merged into the Bashed Patch, ESL-flagged or '
                        'Overlay-flagged.')
        else: # -> no mergeables
            mc_title = _('ESL-Capable or Overlay-Capable Plugin')
            mc_desc = _('This is the text color used for plugins that could '
                        'be ESL-flagged or Overlay-flagged.')
    else: # -> no ESLs
        if MergeabilityCheck.MERGE in bush.game.mergeability_checks:
            mc_title = _('Mergeable or Overlay-Capable Plugin')
            mc_desc = _('This is the text color used for plugins that could '
                        'be merged into the Bashed Patch or Overlay-flagged.')
        else: # -> no ESLs or mergeables
            mc_title = _('Overlay-Capable Plugin')
            mc_desc = _('This is the text color used for plugins that could '
                        'be Overlay-flagged.')
else: # -> no overlays
    if MergeabilityCheck.ESL_CHECK in bush.game.mergeability_checks:
        if MergeabilityCheck.MERGE in bush.game.mergeability_checks:
            mc_title = _('Mergeable or ESL-Capable')
            mc_desc = _('This is the text color used for plugins that could '
                        'be merged into the Bashed Patch or ESL-flagged.')
        else: # -> no mergeables
            mc_title = _('ESL-Capable')
            mc_desc = _('This is the text color used for plugins that could '
                        'be ESL-flagged.')
    else: # -> no ESLs
        if MergeabilityCheck.MERGE in bush.game.mergeability_checks:
            mc_title = _('Mergeable')
            mc_desc = _('This is the text color used for plugins that could '
                        'be merged into the Bashed Patch.')
        else:
            mc_title = mc_desc = None
if mc_title is not None and mc_desc is not None:
    colorInfo['mods.text.mergeable'] = (mc_title,
        _('Tabs: Mods') + '\n\n' +
        mc_desc,
    )

# Does NoMerge exist? ---------------------------------------------------------
if MergeabilityCheck.MERGE in bush.game.mergeability_checks:
    colorInfo['mods.text.noMerge'] = (_("'NoMerge' Plugin"),
        _('Tabs: Mods') + '\n\n' +
        _('This is the text color used for a mergeable plugin that is '
          "tagged 'NoMerge'."),
    )

#--Load config/defaults
settingDefaults = { # keep current naming format till refactored
    #--Basics
    'bash.version': 0,
    'bash.backupPath': None,
    'bash.frameMax': False, # True if maximized
    'bash.page': 1,
    'bash.global_menu': 0,
    'bash.pluginEncoding': 'cp1252',    # Western European
    'bash.restore_scroll_positions': True,
    'bash.show_internal_keys': False,
    'bash.temp_dir': '',
    'bash.window.sizes': {},
    #--Update Check on Boot
    'bash.update_check.enabled': True,
    'bash.update_check.cooldown': 1,
    'bash.update_check.last_checked': 0,
    #--Appearance
    'bash.useAltName': True,
    'bash.use_reverse_icons': False,
    #--Colors
    'bash.colors': {
        #--Common Colors
        'default.text':                 (0,   0,   0),   # 'BLACK'
        'default.bkgd':                 (255, 255, 255), # 'WHITE'
        'default.warn':                 (255, 0,   0),
        #--Mods Tab
        'mods.text.esm':                (0,   0,   255), # 'BLUE'
        'mods.text.mergeable':          (0,   153, 0),
        'mods.text.noMerge':            (150, 130, 0),
        'mods.bkgd.doubleTime.exists':  (255, 220, 220),
        'mods.bkgd.doubleTime.load':    (255, 149, 149),
        'mods.bkgd.ghosted':            (232, 232, 232),
        'mods.bkgd.size_mismatch':      (255, 238, 217),
        'mods.text.esl':                (226, 54,  197),
        'mods.text.eslm':               (123, 29,  223),
        'mods.text.eso':                (235, 119, 44),
        'mods.text.esom':               (234, 49, 9),
        'mods.text.bashedPatch':        (30,  157, 251),
        #--INI Edits Tab
        'ini.bkgd.invalid':             (223, 223, 223),
        'tweak.bkgd.invalid':           (255, 213, 170),
        'tweak.bkgd.mismatched':        (255, 255, 191),
        'tweak.bkgd.matched':           (193, 255, 193),
        #--Installers Tab
        'installers.text.complex':      (35,  35,  142), # 'NAVY'
        'installers.text.invalid':      (128, 128, 128), # 'GREY'
        'installers.text.marker':       (230, 97,  89),
        'installers.bkgd.skipped':      (224, 224, 224),
        'installers.bkgd.outOfOrder':   (255, 255, 0),
        'installers.bkgd.dirty':        (255, 187, 51),
        #--Screenshots Tab
        'screens.bkgd.image':           (100, 100, 100),
    },
    #--BSA Redirection
    'bash.bsaRedirection': True,
    # Wrye Bash: Localization
    'bash.l10n.editor.param_fmt': '%s',
    'bash.l10n.editor.path': '',
    # Wrye Bash: Load Order
    'bash.load_order.lock_active_plugins': True,
    #--Wrye Bash: StatusBar
    'bash.statusbar.iconSize': 16,
    'bash.statusbar.hide': set(),
    'bash.statusbar.order': [],
    'bash.statusbar.showversion': False,
    #--Wrye Bash: Group and Rating
    'bash.mods.groups': [
        'Root',
        'Library',
        'Cosmetic',
        'Clothing',
        'Weapon',
        'Tweak',
        'Overhaul',
        'Misc.',
        'Magic',
        'NPC',
        'Home',
        'Place',
        'Quest',
        'Last',
    ],
    'bash.mods.ratings': ['+', '1', '2', '3', '4', '5', '=', '~'],
    #--Wrye Bash: Col (Sort) Names
    'bash.colNames': {
        'Mod Status': _('Plugin Status'),
        'Author': _('Author'),
        'Cell': _('Location'),
        'CRC': _('CRC'),
        'Current Index': _('Current Index'),
        'Current Order': _('Current LO'),
        'File': _('File'),
        'Files': _('Files'),
        'Group': _('Group'),
        'Indices': _('Index'),
        'Installer': _('Source'),
        'Load Order': _('Load Order'),
        'Modified': _('Modified'),
        'Num': _('MI'),
        'Order': _('Order'),
        'Package': _('Package'),
        'PlayTime': _('Hours'),
        'Player': _('Player'),
        'Rating': _('Rating'),
        'Size': _('Size'),
        'Status': _('Status'),
    },
    #--Wrye Bash: Masters
    'bash.masters.cols': ['File', 'Num', 'Current Order'],
    'bash.masters.esmsFirst': False,
    'bash.masters.selectedFirst': False,
    'bash.masters.sort': 'Num',
    'bash.masters.colReverse': {},
    'bash.masters.colWidths': {
        'File': 80,
        'Num': 30,
        'Current Order': 60,
        'Indices': 50,
        'Current Index': 50,
    },
    #--Wrye Bash: Mod Docs
    'bash.modDocs.dir': None,
    #--Installers
    'bash.installers.cols': ['Package', 'Order', 'Modified', 'Size', 'Files'],
    'bash.installers.colReverse': {},
    'bash.installers.sort': 'Order',
    'bash.installers.colWidths': {
        'Package': 230,
        'Order': 25,
        'Modified': 135,
        'Size': 75,
        'Files': 55,
    },
    'bash.installers.page': 0,
    'bash.installers.isFirstRun': True,
    'bash.installers.enabled': True,
    'bash.installers.autoAnneal': True,
    'bash.installers.autoWizard': True,
    'bash.installers.wizardOverlay': True,
    'bash.installers.fastStart': True,
    'bash.installers.autoRefreshBethsoft': False,
    'bash.installers.autoRefreshProjects': True,
    'bash.installers.ignore_fomods': False,
    'bash.installers.validate_fomods': True,
    'bash.installers.removeEmptyDirs': True,
    'bash.installers.skipScreenshots': False,
    'bash.installers.skipScriptSources': False,
    'bash.installers.skipImages': False,
    'bash.installers.skipDocs': False,
    'bash.installers.skipDistantLOD': False,
    'bash.installers.skipLandscapeLODMeshes': False,
    'bash.installers.skipLandscapeLODTextures': False,
    'bash.installers.skipLandscapeLODNormals': False,
    'bash.installers.skipTESVBsl': True,
    'bash.installers.skipPDBs': False,
    'bash.installers.allowOBSEPlugins': True,
    'bash.installers.rename_docs': True,
    'bash.installers.renameStrings': True,
    'bash.installers.redirect_csvs': True,
    'bash.installers.redirect_docs': True,
    'bash.installers.redirect_scripts': True,
    'bash.installers.sortProjects': False,
    'bash.installers.sortActive': False,
    'bash.installers.sortStructure': False,
    'bash.installers.conflictsReport.showLower': True,
    'bash.installers.conflictsReport.showInactive': False,
    'bash.installers.conflictsReport.showBSAConflicts': True,
    'bash.installers.goodDlls': {},
    'bash.installers.badDlls': {},
    'bash.installers.onDropFiles.action': None,
    'bash.installers.commentsSplitterSashPos': 0,
    'bash.installers.import_order.create_markers': True,
    'bash.installers.import_order.what': 'imp_all',
    #--Wrye Bash: Wizards
    'bash.fomod.size': (600, 500),
    'bash.fomod.pos': DEFAULT_POSITION,
    'bash.fomod.use_table': False,
    'bash.wizard.size': (600, 500),
    'bash.wizard.pos': DEFAULT_POSITION,
    #--Wrye Bash: INI Tweaks
    'bash.ini.cols': ['File', 'Installer'],
    'bash.ini.sort': 'File',
    'bash.ini.colReverse': {},
    'bash.ini.sortValid': True,
    'bash.ini.colWidths': {
        'File': 300,
        'Installer': 100,
    },
    'bash.ini.choices': {},
    'bash.ini.choice': 0,
    'bash.ini.allowNewLines': bush.game.Ini.allow_new_lines,
    #--Wrye Bash: Mods
    'bash.mods.autoGhost': False,
    'bash.mods.auto_flag_esl': True,
    'bash.mods.cols': ['File', 'Load Order', 'Installer', 'Modified', 'Size',
                       'Author', 'CRC'],
    'bash.mods.esmsFirst': False,
    'bash.mods.selectedFirst': False,
    'bash.mods.sort': 'Load Order',
    'bash.mods.colReverse': {},
    'bash.mods.colWidths': {
        'Author': 100,
        'File': 200,
        'Group': 10,
        'Installer': 100,
        'Load Order': 25,
        'Indices': 50,
        'Modified': 135,
        'Rating': 10,
        'Size': 75,
        'CRC': 60,
        'Mod Status': 50,
    },
    'bash.mods.details.colWidths': {},
    'bash.mods.details.colReverse': {},
    'bash.mods.renames': {},
    'bash.mods.scanDirty': True,
    'bash.mods.ignore_dirty_vanilla_files': True,
    'bash.mods.export.skip': '',
    'bash.mods.export.deprefix': '',
    'bash.mods.export.skipcomments': False,
    #--Wrye Bash: Saves
    'bash.saves.cols': ['File', 'Modified', 'Size', 'PlayTime', 'Player',
                        'Cell'],
    'bash.saves.sort': 'Modified',
    'bash.saves.colReverse': {
        'Modified': True,
    },
    'bash.saves.colWidths': {
        'File': 375,
        'Modified': 135,
        'Size': 65,
        'PlayTime': 50,
        'Player': 70,
        'Cell': 80,
    },
    'bash.saves.details.colWidths': {},
    'bash.saves.details.colReverse': {},
    #--Wrye Bash: BSAs
    'bash.BSAs.cols': ['File', 'Modified', 'Size'],
    'bash.BSAs.sort': 'File',
    'bash.BSAs.colReverse': {
        'Modified': True,
    },
    'bash.BSAs.colWidths': {
        'File': 150,
        'Modified': 150,
        'Size': 75,
    },
    #--Wrye Bash: Screenshots
    'bash.screens.cols': ['File', 'Modified', 'Size'],
    'bash.screens.sort': 'File',
    'bash.screens.colReverse': {
        'Modified': True,
    },
    'bash.screens.colWidths': {
        'File': 100,
        'Modified': 150,
        'Size': 75,
    },
    'bash.screens.jpgQuality': 95,
    'bash.screens.jpgCustomQuality': 75,
    #--BOSS/LOOT:
    'BOSS.ClearLockTimes': True,
    'BOSS.UseGUI': False,
    'LOOT.AutoSort': False,
    # No need to store defaults for all the xEdits for all games
    f'{bush.game.Xe.xe_key_prefix}.iKnowWhatImDoing': False,
    f'{bush.game.Xe.xe_key_prefix}.skip_bsas': False,
}

# Enable Index columns by default for ESL and Overlay games
if bush.game.has_esl or bush.game.has_overlay_plugins:
    settingDefaults['bash.mods.cols'].insert(2, 'Indices')
    settingDefaults['bash.masters.cols'].extend(['Indices', 'Current Index'])

# Specify various launchers in the format (tool_key: tool) - each one has a
# (3) matching image file(s) in `images/tools` - image filename starts with
# tool_key.lower() and ends in '.svg' (or '[16|24|32].png')

oblivion_tools = {
    'OBMM': ('OblivionModManager.exe', 'OBMM', {
        'root_dirs': 'app'}),
    'ISOBL': ('ISOBL.exe', "InsanitySorrow's Oblivion Launcher", {
        'root_dirs': 'app'}),
    'ISRMG': ('Insanitys ReadMe Generator.exe', "InsanitySorrow's Readme Generator", {
        'root_dirs': 'app'}),
    'ISRNG': ('Random Name Generator.exe', "InsanitySorrow's Random Name Generator", {
        'root_dirs': 'app'}),
    'ISRNPCG': ('Random NPC.exe', "InsanitySorrow's Random NPC Generator", {
        'root_dirs': 'app'}),
    'OBFEL': ('OblivionFaceExchangeLite.exe', 'Oblivion Face Exchange Lite', {
        'subfolders': 'Oblivion Face Exchange Lite'}),
    'OBMLG': ('Oblivion Mod List Generator.exe', 'Oblivion Mod List Generator', {
        'root_dirs': 'app', 'subfolders': ('Modding Tools', 'Oblivion Mod List Generator')}),
    'BSACMD': ('bsacmd.exe', 'BSA Commander', {
        'subfolders': 'BSACommander'}),
    'Tabula': ('Tabula.exe', 'Tabula', {
        'root_dirs': 'app', 'subfolders': ('Modding Tools', 'Tabula')}),
    'Tes4FilesPath': ('TES4Files.exe', 'TES4Files', {
        'root_dirs': 'app', 'subfolders': 'Tools'}),
}

oblivion_java_tools = {
    'Tes4GeckoPath': ('Tes4Gecko.jar', 'Tes4Gecko', {
        'root_dirs': 'app'}),
    'OblivionBookCreatorPath': ('OblivionBookCreator.jar', 'Oblivion Book Creator', {
        'root_dirs': 'mods'}),
}

skyrim_tools = {
    'Tes5GeckoPath': ('TESVGecko.exe', 'TesVGecko', {
        'subfolders': ('Dark Creations', 'TESVGecko')}),
}

modeling_tools_buttons = {
    'AutoCad': ('acad.exe', 'AutoCad', {
        'subfolders': 'Autodesk Architectural Desktop 3'}),
    'BlenderPath': ('blender.exe', 'Blender', {
        'subfolders': ('Blender Foundation', 'Blender')}),
    'Dogwaffle': ('dogwaffle.exe', 'Dogwaffle', {
        'subfolders': 'project dogwaffle'}),
    'GmaxPath': ('gmax.exe', 'Gmax', {
        'root_dirs': [GPath(r'C:\GMAX')]}),
    'MayaPath': (None, 'Maya', {}),
    'MaxPath': ('3dsmax.exe', '3dsMax', {
        'subfolders': ('Autodesk', '3ds Max 2010')}),
    'Milkshape3D': ('ms3d.exe', 'Milkshape 3D', {
        'subfolders': 'MilkShape 3D 1.8.4'}),
    'Mudbox': ('mudbox.exe', 'Mudbox', {
        'subfolders': ('Autodesk', 'Mudbox2011')}),
    'Sculptris': ('Sculptris.exe', 'Sculptris', {
        'subfolders': 'sculptris'}),
    'SpeedTree': (None, 'SpeedTree', {}),
    'Treed': ('tree[d].exe', 'Tree[d]', {
        'subfolders': ('gile[s]', 'plugins', 'tree[d]')}),
    'Wings3D': ('Wings3D.exe', 'Wings 3D', {
        'subfolders': 'wings3d_1.2'}),
    'SoftimageModTool': ('XSI.bat', 'Softimage Mod Tool', {
            'root_dirs': [GPath(r'C:\Softimage')],
            'subfolders': ('Softimage_Mod_Tool_7.5', 'Application', 'bin')
        }, '-mod')
}

texture_tool_buttons = {
    'AniFX': ('AniFX.exe', 'AniFX', {
        'subfolders': 'AniFX 1.0'}),
    'ArtOfIllusion': ('Art of Illusion.exe', 'Art Of Illusion', {
        'subfolders': 'ArtOfIllusion'}),
    'Artweaver': ('Artweaver.exe', 'Artweaver', {
        'subfolders': 'Artweaver 1.0'}),
    'CrazyBump': ('CrazyBump.exe', 'CrazyBump', {
        'subfolders': 'Crazybump'}),
    'DDSConverter': ('DDS Converter 2.exe', 'DDSConverter', {
        'subfolders': 'DDS Converter 2'}),
    'DeepPaint': ('DeepPaint.exe', 'DeepPaint', {
        'subfolders': ('Right Hemisphere', 'Deep Paint')}),
    'FastStone': ('FSViewer.exe', 'FastStone Image Viewer', {
        'subfolders': 'FastStone Image Viewer'}),
    'Genetica': ('Genetica.exe', 'Genetica', {
        'subfolders': ('Spiral Graphics', 'Genetica 3.5')}),
    'GeneticaViewer': ('Genetica Viewer 3.exe', 'Genetica Viewer', {
        'subfolders': ('Spiral Graphics', 'Genetica Viewer 3')}),
    'GIMP': ('gimp-2.6.exe', 'GIMP', {
        'subfolders': ('GIMP-2.0', 'bin')}),
    'IcoFX': ('IcoFX.exe', 'IcoFX', {
        'subfolders': 'IcoFX 1.6'}),
    'Inkscape': ('inkscape.exe', 'Inkscape', {
        'subfolders': [('Inkscape', 'bin'), ('Inkscape',)]}),
    'IrfanView': ('i_view32.exe', 'IrfanView', {
        'subfolders': 'IrfanView'}),
    'Krita': ('krita.exe', 'Krita', {
        'subfolders': ('Krita (x86)', 'bin')}),
    'MaPZone': ('MaPZone2.exe', 'MaPZone', {
        'subfolders': ('Allegorithmic', 'MaPZone 2.6')}),
    'MyPaint': ('mypaint.exe', 'MyPaint', {
        'subfolders': 'MyPaint'}),
    'NVIDIAMelody': ('Melody.exe', 'Nvidia Melody', {
        'subfolders': ('NVIDIA Corporation', 'Melody')}),
    'PaintNET': ('PaintDotNet.exe', 'Paint.NET', {
        'subfolders': 'Paint.NET'}),
    'PaintShopPhotoPro': ('Corel Paint Shop Pro Photo.exe',
                          'PaintShop Photo Pro', {
        'subfolders': (
            'Corel', 'Corel PaintShop Photo Pro', 'X3', 'PSPClassic')
    }),
    'PhotoshopPath': ('Photoshop.exe', 'Photoshop', {
        'subfolders': [('Adobe', 'Adobe Photoshop CS6 (64 Bit)'),
                       ('Adobe', 'Adobe Photoshop CS3')]
    }),
    'PhotoScape': ('PhotoScape.exe', 'PhotoScape', {
        'subfolders': 'PhotoScape'}),
    'PhotoSEAM': ('PhotoSEAM.exe', 'PhotoSEAM', {
        'subfolders': 'PhotoSEAM'}),
    'Photobie': ('Photobie.exe', 'Photobie', {
        'subfolders': 'Photobie'}),
    'PhotoFiltre': ('PhotoFiltre.exe', 'PhotoFiltre', {
        'subfolders': 'PhotoFiltre'}),
    'PixelStudio': ('Pixel.exe', 'Pixel Studio Pro', {
        'subfolders': 'Pixel'}),
    'Pixia': ('pixia.exe', 'Pixia', {
        'subfolders': 'Pixia'}),
    'TextureMaker': ('texturemaker.exe', 'TextureMaker', {
        'subfolders': 'Texture Maker'}),
    'TwistedBrush': ('tbrush_open_studio.exe', 'TwistedBrush', {
        'subfolders': ('Pixarra', 'TwistedBrush Open Studio')}),
    'WTV': ('WTV.exe', 'Windows Texture Viewer', {
        'subfolders': 'WindowsTextureViewer'}),
    'xNormal': ('xNormal.exe', 'xNormal', {
        'subfolders': ('Santiago Orgaz', 'xNormal', '3.17.3', 'x86')}),
    'XnView': ('xnview.exe', 'XnView', {
        'subfolders': 'XnView'})
}

nifskope = ('NifskopePath', ('Nifskope.exe', 'Nifskope', {
    'subfolders': ('NifTools', 'NifSkope')}))

audio_tools = {
    'Audacity': ('Audacity.exe', 'Audacity', {
        'subfolders': 'Audacity'}),
    'ABCAmberAudioConverter': ('abcaudio.exe',
        'ABC Amber Audio Converter', {
        'subfolders': 'ABC Amber Audio Converter'}),
    'Switch': ('switch.exe', 'Switch', {
        'subfolders': ('NCH Swift Sound', 'Switch')})
}

misc_tools = {
    'Fraps': ('Fraps.exe', 'Fraps', {
        'root_dirs': [GPath(r'C:\Fraps')]}),
    'MAP': ('Mapa v 3.52.exe',
            'Interactive Map of Cyrodiil and Shivering Isles', {
                'root_dirs': 'app', 'subfolders': ('Modding Tools',
                    'Interactive Map of Cyrodiil and Shivering Isles 3.52')}),
    'LogitechKeyboard': ('LGDCore.exe', 'LogitechKeyboard', {
        'subfolders': ('Logitech', 'GamePanel Software', 'G-series Software')}
                         ),
    'MediaMonkey': ('MediaMonkey.exe', 'MediaMonkey', {
        'subfolders': 'MediaMonkey'}),
    'NPP': ('notepad++.exe', 'Notepad++', {
        'subfolders': ('Notepad++',)}),
    'Steam': ('steam.exe', 'Steam', {
        'subfolders': 'Steam'}),
    'EVGAPrecision': ('EVGAPrecision.exe', 'EVGA Precision', {
        'subfolders': 'EVGA Precision'}),
    'WinMerge': ('WinMergeU.exe', 'WinMerge', {
        'subfolders': 'WinMerge'}),
    'FreeMind': ('Freemind.exe', 'FreeMind', {
        'subfolders': 'FreeMind'}),
    'Freeplane': ('freeplane.exe', 'Freeplane', {
        'subfolders': 'Freeplane'}),
    'FileZilla': ('filezilla.exe', 'FileZilla', {
        'subfolders': 'FileZilla FTP Client'}),
    'EggTranslator': ('EggTranslator.exe', 'Egg Translator', {
        'subfolders': 'Egg Translator'}),
    'RADVideo': ('radvideo.exe', 'RAD Video Tools', {
        'subfolders': 'RADVideo'}),
    'WinSnap': ('WinSnap.exe', 'WinSnap', {
        'subfolders': 'WinSnap'})
}

loot_bosh = {
    'LOOT': ('LOOT.exe', 'LOOT', {'subfolders': 'LOOT'}),
    'BOSS': ('BOSS.exe', 'BOSS', {'subfolders': 'BOSS'})
}
