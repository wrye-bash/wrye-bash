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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""Menu items for the _main_ menu of the installer tab - their window attribute
points to the InstallersList singleton."""

from . import Installers_Link
from .dialogs import CreateNewProject
from .. import bass, bosh, balt, bush, load_order
from ..balt import BoolLink, AppendableLink, ItemLink, ListBoxes, \
    EnabledLink
from ..gui import copy_text_to_clipboard

__all__ = [u'Installers_SortActive', u'Installers_SortProjects',
           u'Installers_RefreshData', u'Installers_AddMarker',
           u'Installers_CreateNewProject', u'Installers_MonitorInstall',
           u'Installers_ListPackages', u'Installers_AnnealAll',
           u'Installers_UninstallAllPackages',
           u'Installers_UninstallAllUnknownFiles', u'Installers_AvoidOnStart',
           u'Installers_Enabled', u'Installers_AutoAnneal',
           u'Installers_AutoWizard', u'Installers_AutoRefreshProjects',
           u'Installers_AutoRefreshBethsoft',
           u'Installers_ApplyEmbeddedBCFs', u'Installers_BsaRedirection',
           u'Installers_RemoveEmptyDirs',
           u'Installers_ConflictsReportShowsInactive',
           u'Installers_ConflictsReportShowsLower',
           u'Installers_ConflictsReportShowBSAConflicts',
           u'Installers_WizardOverlay', u'Installers_GlobalSkips',
           u'Installers_GlobalRedirects', u'Installers_FullRefresh',
           u'Installers_IgnoreFomod']

#------------------------------------------------------------------------------
# Installers Links ------------------------------------------------------------
#------------------------------------------------------------------------------
class Installers_AddMarker(ItemLink):
    """Add an installer marker."""
    _text = _(u'New Marker...')
    _help = _(u'Adds a Marker, a special type of package useful for '
              u'separating and labelling your packages.')

    def Execute(self):
        """Add a Marker."""
        self.window.addMarker()

class Installers_MonitorInstall(Installers_Link):
    """Monitors Data folder for external installation."""
    _text = _(u'Monitor External Installation...')
    _help = _(u'Monitors the %s folder during installation via manual install '
              u'or 3rd party tools.') % bush.game.mods_dir

    @balt.conversation
    def Execute(self):
        msg = _(u'Wrye Bash will monitor your data folder for changes when '
                u'installing a mod via an external application or manual '
                u'install.  This will require two refreshes of the %s folder '
                u'and may take some time.') % bush.game.mods_dir
        if not balt.askOk(self.window, msg, _(u'External Installation')):
            return
        # Refresh Data
        self.iPanel.ShowPanel(canCancel=False, scan_data_dir=True)
        # Backup CRC data
        data_sizeCrcDate = self.idata.data_sizeCrcDate.copy()
        # Install and wait
        self._showOk(_(u'You may now install your mod.  When installation is '
                       u'complete, press Ok.'), _(u'External Installation'))
        # Refresh Data
        bosh.bsaInfos.refresh() # TODO: add bsas to BAIN refresh
        with load_order.Unlock():
            mods_changed = bosh.modInfos.refresh()
        inis_changed = bosh.iniInfos.refresh()
        ui_refresh = (bool(mods_changed), bool(inis_changed))
        self.iPanel.ShowPanel(canCancel=False, scan_data_dir=True)
        # Determine changes
        curData = self.idata.data_sizeCrcDate
        oldFiles = set(data_sizeCrcDate)
        curFiles = set(curData)
        newFiles = curFiles - oldFiles
        delFiles = oldFiles - curFiles
        sameFiles = curFiles & oldFiles
        changedFiles = {file_ for file_ in sameFiles if
                        data_sizeCrcDate[file_][1] != curData[file_][1]}
        touchedFiles = {file_ for file_ in sameFiles if
                        data_sizeCrcDate[file_][2] != curData[file_][2]}
        touchedFiles -= changedFiles

        if not newFiles and not changedFiles and not touchedFiles:
            self._showOk(_(u'No changes were detected in the %s '
                           u'directory.') % bush.game.mods_dir,
                         _(u'External Installation'))
            return
        newFiles = sorted(newFiles) # sorts case insensitive as those are CIStr
        changedFiles = sorted(changedFiles)
        touchedFiles = sorted(touchedFiles)
        # Show results, select which files to include
        checklists = []
        newFilesKey = _(u'New Files: %(count)i') % {u'count':len(newFiles)}
        changedFilesKey = _(u'Changed Files: %(count)i') % {u'count':len(changedFiles)}
        touchedFilesKey = _(u'Touched Files: %(count)i') % {u'count':len(touchedFiles)}
        delFilesKey = _(u'Deleted Files')
        if newFiles:
            group = [newFilesKey, _(u'These files are newly added to the %s '
                                    u'directory.') % bush.game.mods_dir]
            group.extend(newFiles)
            checklists.append(group)
        if changedFiles:
            group = [changedFilesKey, _(u'These files were modified.'), ]
            group.extend(changedFiles)
            checklists.append(group)
        if touchedFiles:
            group = [touchedFilesKey, _(
                u'These files were not changed, but had their modification '
                u'time altered.  Most likely, these files are included in '
                u'the external installation, but were the same version as '
                u'already existed.'), ]
            group.extend(touchedFiles)
            checklists.append(group)
        if delFiles:
            group = [delFilesKey, _(
                u'These files were deleted.  BAIN does not have the '
                u'capability to remove files when installing.'), ]
            group.extend(sorted(delFiles))
        with ListBoxes(self.window, _(u'External Installation'),
                       _(u'The following changes were detected in the %s '
                         u'directory.') % bush.game.mods_dir,
                       checklists, bOk=_(u'Create Project')) as dialog:
            if not dialog.show_modal(): return
            include = set()
            for (lst, key) in [(newFiles, newFilesKey),
                               (changedFiles, changedFilesKey),
                               (touchedFiles, touchedFilesKey), ]:
                include |= set(dialog.getChecked(key, lst))
            if not include: return
        # Create Project
        projectName = self._askText(_(u'Project Name'),
                                    _(u'External Installation'))
        if not projectName:
            return
        pr_path = bosh.InstallerProject.unique_name(projectName)
        # Copy Files
        with balt.Progress(_(u'Creating Project...'), u'\n' + u' '*60) as prog:
            self.idata.createFromData(pr_path, include, prog) # will order last
        # createFromData placed the new project last in install order - install
        try:
            self.idata.bain_install([pr_path], ui_refresh, override=False)
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)
        # Select new installer
        self.window.SelectLast()

class Installers_ListPackages(Installers_Link):
    """Copies list of Bain files to clipboard."""
    _text = _(u'List Packages...')
    _help = _(u'Displays a list of all packages.  Also copies that list to '
        u'the clipboard.  Useful for posting your package order on forums.')

    @balt.conversation
    def Execute(self):
        #--Get masters list
        message = _(u'Only show Installed Packages?') + u'\n' + _(
            u'(Else shows all packages)')
        installed_only = self._askYes(message, _(u'Only Show Installed?'))
        package_list = self.idata.getPackageList(
            showInactive=not installed_only)
        copy_text_to_clipboard(package_list)
        self._showLog(package_list, title=_(u'BAIN Packages'), fixedFont=False)

class Installers_AnnealAll(Installers_Link):
    """Anneal all packages."""
    _text = _(u'Anneal All')
    _help = _(u'Install any missing files (for active packages) and update '
              u'the contents of the %s folder to account for all install '
              u'order and configuration changes.') % bush.game.mods_dir

    @balt.conversation
    def Execute(self):
        """Anneal all packages."""
        ui_refresh = [False, False]
        try:
            with balt.Progress(_(u'Annealing...'),u'\n'+u' '*60) as progress:
                self.idata.bain_anneal(None, ui_refresh, progress=progress)
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

class Installers_UninstallAllPackages(Installers_Link):
    """Uninstall all packages."""
    _text = _(u'Uninstall All Packages')
    _help = _(u'This will uninstall all packages.')

    @balt.conversation
    def Execute(self):
        """Uninstall all packages."""
        if not self._askYes(_(u'Really uninstall All Packages?')): return
        ui_refresh = [False, False]
        try:
            with balt.Progress(_(u'Uninstalling...'),u'\n'+u' '*60) as progress:
                self.idata.bain_uninstall(u'ALL', ui_refresh, progress=progress)
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

class _AInstallers_Refresh(AppendableLink, Installers_Link):
    """Refreshes all Installers data."""
    _full_refresh = False

    def _append(self, window): return bass.settings[u'bash.installers.enabled']

    @balt.conversation
    def Execute(self):
        self.idata.reset_refresh_flag_on_projects()
        self.iPanel.ShowPanel(fullRefresh=self._full_refresh,
                              scan_data_dir=True)

class Installers_FullRefresh(_AInstallers_Refresh):
    _text = _(u'Full Refresh')
    _help = _(u'Perform a full refresh of all data files, recalculating all '
              u'CRCs. This can take 5-15 minutes.')
    _fr_msg = _(u'Refresh ALL data from scratch? This may take five to ten '
                u'minutes (or more) depending on the number of mods you have '
                u'installed.')
    _full_refresh = True

    def Execute(self):
        if not self._askWarning(self._fr_msg, self._text): return
        super(Installers_FullRefresh, self).Execute()

class Installers_RefreshData(_AInstallers_Refresh):
    _text = _(u'Refresh Data')
    _help = _(u'Rescan the %s directory and all project '
              u'directories.') % bush.game.mods_dir

class Installers_UninstallAllUnknownFiles(Installers_Link):
    """Uninstall all files that do not come from a current package/bethesda
    files. For safety just moved to Game Mods/Bash Installers/Bash/Data
    Folder Contents (date/time)."""
    _text = _(u'Clean Data')
    _help = _(u'This will remove all mod files that are not linked to an '
             u'active installer out of the %s folder.') % bush.game.mods_dir
    fullMessage = (_(u'Clean %s directory?') % bush.game.mods_dir + u' ' +
                   _help + u'\n\n' + _(
                u'This includes files that were installed manually or by '
                u'another program. Files will be moved to the "%s" directory '
                u'instead of being deleted so you can retrieve them later if '
                u'necessary.') % bass.dirs[u'bainData'].join(
                u'%s Folder Contents <date>' % bush.game.mods_dir) + u'\n\n' +
                   _(u'Note that you will first be shown a list of files that '
                     u'this operation would remove and will have a chance to '
                     u'change the selection.'))

    @balt.conversation
    def Execute(self):
        if not self._askYes(self.fullMessage): return
        ui_refresh = [False, False]
        try:
            all_unknown_files = self.idata.get_clean_data_dir_list()
            if not all_unknown_files:
                self._showOk(
                    _(u'There are no untracked files in the %s '
                      u'folder.') % bush.game.mods_dir,
                    _(u'%s folder is clean') % bush.game.mods_dir)
                return
            message = [u'',       # adding a tool tip
                       _(u'Uncheck files to keep them in the %s '
                         u'folder.') % bush.game.mods_dir]
            all_unknown_files.sort()
            message.extend(all_unknown_files)
            with ListBoxes(self.window,
                  _(u'Move files out of the %s folder.') % bush.game.mods_dir,
                  _(u'Uncheck any files you want to keep in the %s '
                    u'folder.') % bush.game.mods_dir,
                  [message]) as dialog:
                selected_unknown_files = dialog.show_modal() and \
                    dialog.getChecked(message[0], all_unknown_files)
            if selected_unknown_files:
                with balt.Progress(
                        _(u'Cleaning %s contents...') % bush.game.mods_dir,
                        u'\n' + u' ' * 65):
                    self.idata.clean_data_dir(selected_unknown_files,
                                              ui_refresh)
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

#------------------------------------------------------------------------------
# Installers BoolLinks --------------------------------------------------------
#------------------------------------------------------------------------------
class Installers_AutoAnneal(BoolLink):
    _text, _bl_key = _(u'Auto-Anneal'), u'bash.installers.autoAnneal'
    _help = _(u'Enable/Disable automatic annealing of packages.')

class Installers_AutoWizard(BoolLink):
    _text = _(u'Auto-Anneal/Install Wizards')
    _bl_key = u'bash.installers.autoWizard'
    _help = _(u'Enable/Disable automatic installing or anneal (as applicable) '
              u'of packages after running its wizard.')

class _Installers_BoolLink_Refresh(BoolLink):
    def Execute(self):
        super(_Installers_BoolLink_Refresh, self).Execute()
        self.window.RefreshUI()

class Installers_WizardOverlay(_Installers_BoolLink_Refresh):
    """Toggle using the wizard overlay icon"""
    _text  = _(u'Wizard Icon Overlay')
    _bl_key = u'bash.installers.wizardOverlay'
    _help =_(u'Enable/Disable the magic wand icon overlay for packages with '
             u'Wizards.')

class Installers_AutoRefreshProjects(BoolLink):
    """Toggle autoRefreshProjects setting and update."""
    _text = _(u'Auto-Refresh Projects')
    _bl_key = u'bash.installers.autoRefreshProjects'
    _help = _(u'Toggles whether or not Wrye Bash will automatically detect '
              u'changes to projects in the installers directory.')

class Installers_IgnoreFomod(BoolLink):
    _text = _(u'Ignore FOMODs')
    _bl_key = u'bash.installers.ignore_fomods'
    _help = _(u'Ignores FOMODs when using the "Install..." option. If this is '
              u'checked, FOMODs will only be used when you specifically run '
              u'them via "FOMOD Installer...".')

class Installers_ApplyEmbeddedBCFs(ItemLink):
    """Automatically apply Embedded BCFs to archives that have one."""
    _text = _(u'Apply Embedded BCFs')
    _help = _(u'Automatically apply Embedded BCFs to their containing '
              u'archives.')

    @balt.conversation
    def Execute(self):
        with balt.Progress(_(u'Auto-Applying Embedded BCFs...'),
                           message=u'\n' + u' ' * 60) as progress:
            destinations, converted = self.window.data_store.applyEmbeddedBCFs(
                progress=progress)
            if not destinations: return
        self.window.RefreshUI()
        self.window.ClearSelected(clear_details=True)
        self.window.SelectItemsNoCallback(destinations + converted)

class Installers_AutoRefreshBethsoft(BoolLink, Installers_Link):
    """Toggle refreshVanilla setting and update."""
    _text = _(u'Skip Bethsoft Content')
    _bl_key = u'bash.installers.autoRefreshBethsoft'
    _help = _(u'Skip installing Bethesda ESMs, ESPs, and BSAs')
    opposite = True
    message = _(u'Enable installation of Bethsoft Content?') + u'\n\n' + _(
        u'In order to support this, Bethesda ESPs, ESMs, and BSAs need to '
        u'have their CRCs calculated.  Moreover Bethesda ESPs, ESMs will have '
        u'their crc recalculated every time on booting BAIN.  Are you sure '
        u'you want to continue?')

    @balt.conversation
    def Execute(self):
        if not bass.settings[self._bl_key] and not self._askYes(self.message):
            return
        super(Installers_AutoRefreshBethsoft, self).Execute()
        if bass.settings[self._bl_key]:
            # Refresh Data - only if we are now including Bethsoft files
            with balt.Progress(title=_(u'Refreshing Bethsoft Content'),
                               message=u'\n' + u' ' * 60) as progress:
                self.idata.update_for_overridden_skips(bush.game.bethDataFiles,
                                                       progress)
        # Refresh Installers
        toRefresh = {iname for iname, installer in self.idata.items() if
                     installer.hasBethFiles}
        self.window.rescanInstallers(toRefresh, abort=False,
                                     update_from_data=False, shallow=True)

class Installers_Enabled(BoolLink):
    """Flips installer state."""
    _text, _bl_key, _help = _(u'Enabled'), u'bash.installers.enabled', _(
        u'Enable/Disable the Installers tab.')
    dialogTitle = _(u'Enable Installers')
    message = _(u'Do you want to enable Installers?') + u'\n\n\t' + _(
        u'If you do, Bash will first need to initialize some data. This can '
        u'take on the order of five minutes if there are many mods installed.')

    @balt.conversation
    def Execute(self):
        """Enable/Disable the installers tab."""
        enabled = bass.settings[self._bl_key]
        if not enabled and not self._askYes(self.message,
                                            title=self.dialogTitle): return
        enabled = bass.settings[self._bl_key] = not enabled
        if enabled:
            self.window.panel.ShowPanel(scan_data_dir=True)
        else:
            self.window.DeleteAll()
            self.window.panel.ClearDetails()

class Installers_BsaRedirection(AppendableLink, BoolLink, EnabledLink):
    """Toggle BSA Redirection."""
    _text, _bl_key = _(u'BSA Redirection'), u'bash.bsaRedirection'
    _help = _(u"Use Quarn's BSA redirection technique.")

    @property
    def link_help(self):
        if not self._enable():
            return self._help + u'  ' + _(u'%(ini)s must exist') % {
                u'ini': bush.game.Ini.dropdown_inis[0]}
        else: return self._help

    def _append(self, window):
        br_section, br_key = bush.game.Ini.bsa_redirection_key
        return bool(br_section) and bool(br_key)

    def _enable(self): return bosh.oblivionIni.abs_path.exists()

    def Execute(self):
        super(Installers_BsaRedirection, self).Execute()
        if bass.settings[self._bl_key]:
            # Delete ArchiveInvalidation.txt, if it exists
            bosh.bsaInfos.remove_invalidation_file()
            if bush.game.displayName == u'Oblivion':
                # For Oblivion, undo any alterations done to the textures BSA
                # and reset the mtimes of vanilla BSAs ##: port to FO3/FNV?
                bsaPath = bosh.modInfos.store_dir.join(
                        bass.inisettings[u'OblivionTexturesBSAName'])
                bsaFile = bosh.bsa_files.OblivionBsa(bsaPath, load_cache=True,
                                                     names_only=False)
                with balt.Progress(_(u'Enabling BSA Redirection...'),
                                   message=u'\n' + u' ' * 60) as progress:
                    bsaFile.undo_alterations(progress)
        bosh.oblivionIni.setBsaRedirection(bass.settings[self._bl_key])

class Installers_ConflictsReportShowsInactive(_Installers_BoolLink_Refresh):
    """Toggles option to show inactive on conflicts report."""
    _text = _(u'Show Inactive Conflicts')
    _help = _(u'In the conflicts tab also display conflicts with inactive '
              u'(not installed) installers')
    _bl_key = u'bash.installers.conflictsReport.showInactive'

class Installers_ConflictsReportShowsLower(_Installers_BoolLink_Refresh):
    """Toggles option to show lower on conflicts report."""
    _text = _(u'Show Lower Conflicts')
    _help = _(u'In the conflicts tab also display conflicts with lower order '
             u'installers (or lower loading active bsas)')
    _bl_key = u'bash.installers.conflictsReport.showLower'

class Installers_ConflictsReportShowBSAConflicts(_Installers_BoolLink_Refresh):
    """Toggles option to show files inside BSAs on conflicts report."""
    _text = _(u'Show Active BSA Conflicts')
    _help = _(u'In the conflicts tab also display same-name resources inside '
             u'installed *and* active bsas')
    _bl_key = u'bash.installers.conflictsReport.showBSAConflicts'

class Installers_AvoidOnStart(BoolLink):
    """Ensures faster bash startup by preventing Installers from being startup tab."""
    _text, _bl_key, = _(u'Avoid at Startup'), u'bash.installers.fastStart'
    _help = _(u'Toggles Wrye Bash to avoid the Installers tab on startup, '
              u'avoiding unnecessary data scanning.')

class Installers_RemoveEmptyDirs(BoolLink):
    """Toggles option to remove empty directories on file scan."""
    _text = _(u'Remove Empty Directories')
    _help = _(u'Toggles whether or not Wrye Bash will remove empty '
              u'directories when scanning the %s folder.') % bush.game.mods_dir
    _bl_key = u'bash.installers.removeEmptyDirs'

# Sorting Links
class _Installer_Sort(ItemLink):
    def Execute(self):
        super(_Installer_Sort, self).Execute()
        self.window.SortItems()

class Installers_SortActive(_Installer_Sort, BoolLink):
    """Sort by type."""
    _text = _(u'Sort by Active')
    _bl_key = u'bash.installers.sortActive'
    _help = _(u'If selected, active installers will be sorted to the top of '
              u'the list.')

class Installers_SortProjects(_Installer_Sort, BoolLink):
    """Sort dirs to the top."""
    _text = _(u'Projects First')
    _bl_key = u'bash.installers.sortProjects'
    _help = _(u'If selected, projects will be sorted to the top of the list.')

class Installers_SortStructure(_Installer_Sort, BoolLink):
    """Sort by type."""
    _text, _bl_key = _(u'Sort by Structure'), u'bash.installers.sortStructure'

#------------------------------------------------------------------------------
# Installers_Skip Links -------------------------------------------------------
#------------------------------------------------------------------------------
class _Installers_RescanningLink(Installers_Link, BoolLink):
    """An Installers link that rescans installers upon being toggled."""
    def Execute(self):
        super(_Installers_RescanningLink, self).Execute()
        self._pre_rescan_action()
        self._do_installers_rescan()

    def _pre_rescan_action(self):
        """A method to call after executing the link but before rescanning.
        Does nothing by default."""

    def _do_installers_rescan(self):
        """Performs the rescan of installers after toggling the link."""
        self.window.rescanInstallers(self.idata, abort=False, # iterate idata
            update_from_data=False,##:update data too when turning skips off ??
            shallow=True)

class _Installers_Skip(_Installers_RescanningLink):
    """Toggle global skip settings and update."""
    @property
    def link_help(self):
        # Slice off the starting 'Skip '
        return _(u'Skips the installation of %(skip_files)s.') % {
            u'skip_files': self._text[5:].lower()}

    def _pre_rescan_action(self):
        bosh.bain.Installer.init_global_skips()

class _Installers_SkipOBSEPlugins(AppendableLink, _Installers_Skip):
    """Toggle allowOBSEPlugins setting and update."""
    _se_sd = bush.game.Se.se_abbrev + (
            u'/' + bush.game.Sd.long_name) if bush.game.Sd.sd_abbrev else u''
    _text = _(u'Skip %s Plugins') % _se_sd
    _bl_key = u'bash.installers.allowOBSEPlugins'
    def _append(self, window): return bool(self._se_sd)
    def _check(self): return not bass.settings[self._bl_key]

class _Installers_SkipScreenshots(_Installers_Skip):
    """Toggle skipScreenshots setting and update."""
    _text, _bl_key = _(u'Skip Screenshots'), u'bash.installers.skipScreenshots'

class _Installers_SkipScriptSources(AppendableLink, _Installers_Skip):
    """Toggle skipScriptSources setting and update."""
    _text, _bl_key = _(u'Skip Script Sources'), u'bash.installers.skipScriptSources'
    def _append(self, window): return bool(bush.game.Psc.source_extensions)

class _Installers_SkipImages(_Installers_Skip):
    """Toggle skipImages setting and update."""
    _text, _bl_key = _(u'Skip Images'), u'bash.installers.skipImages'

class _Installers_SkipDocs(_Installers_Skip):
    """Toggle skipDocs setting and update."""
    _text, _bl_key = _(u'Skip Docs'), u'bash.installers.skipDocs'

class _Installers_SkipDistantLOD(_Installers_Skip):
    """Toggle skipDistantLOD setting and update."""
    _text, _bl_key = _(u'Skip DistantLOD'), u'bash.installers.skipDistantLOD'

class _Installers_SkipLandscapeLODMeshes(_Installers_Skip):
    """Toggle skipLandscapeLODMeshes setting and update."""
    _text = _(u'Skip LOD Meshes')
    _bl_key = u'bash.installers.skipLandscapeLODMeshes'

class _Installers_SkipLandscapeLODTextures(_Installers_Skip):
    """Toggle skipLandscapeLODTextures setting and update."""
    _text = _(u'Skip LOD Textures')
    _bl_key = u'bash.installers.skipLandscapeLODTextures'

class _Installers_SkipLandscapeLODNormals(_Installers_Skip):
    """Toggle skipLandscapeLODNormals setting and update."""
    _text = _(u'Skip LOD Normals')
    _bl_key = u'bash.installers.skipLandscapeLODNormals'

class _Installers_SkipBsl(AppendableLink, _Installers_Skip):
    """Toggle skipTESVBsl setting and update."""
    _text, _bl_key = _(u'Skip BSL Files'), u'bash.installers.skipTESVBsl'
    def _append(self, window): return bush.game.Bsa.has_bsl

class Installers_GlobalSkips(balt.MenuLink):
    """Global Skips submenu."""
    _text = _(u'Global Skips')

    def __init__(self):
        super(Installers_GlobalSkips, self).__init__()
        self.append(_Installers_SkipOBSEPlugins())
        self.append(_Installers_SkipScreenshots())
        self.append(_Installers_SkipScriptSources())
        self.append(_Installers_SkipImages())
        self.append(_Installers_SkipDocs())
        self.append(_Installers_SkipDistantLOD())
        self.append(_Installers_SkipLandscapeLODMeshes())
        self.append(_Installers_SkipLandscapeLODTextures())
        self.append(_Installers_SkipLandscapeLODNormals())
        self.append(_Installers_SkipBsl())

#------------------------------------------------------------------------------
# Redirection/Rename Links ----------------------------------------------------
#------------------------------------------------------------------------------
class _Installers_RenameStrings(AppendableLink, _Installers_RescanningLink):
    """Toggle auto-renaming of .STRINGS files"""
    _text = _(u'Rename String Translation Files')
    _help = _(u'If checked, Wrye Bash will rename all installed string files '
              u'so they match your current language.')
    _bl_key = u'bash.installers.renameStrings'
    def _append(self, window): return bool(bush.game.Esp.stringsFiles)

class _Installers_RedirectScriptSources(AppendableLink, EnabledLink,
                                        _Installers_RescanningLink):
    """Toggle auto-redirection of script sources."""
    _text = _(u'Redirect Script Sources')
    _help = _(u'If checked, Wrye Bash will move all script sources '
              u'installed to incorrect directories (%s) to the correct ones. '
              u"'Skip Script Sources' must be "
              u'off.') % u', '.join(bush.game.Psc.source_redirects)
    _bl_key = u'bash.installers.redirect_scripts'

    def _append(self, window): return bool(bush.game.Psc.source_redirects)
    def _enable(self): return not bass.settings[
        u'bash.installers.skipScriptSources']

class Installers_GlobalRedirects(AppendableLink, balt.MenuLink):
    """Global Redirects menu."""
    _text = _(u'Global Redirects')

    def __init__(self):
        super(Installers_GlobalRedirects, self).__init__()
        self.append(_Installers_RenameStrings())
        self.append(_Installers_RedirectScriptSources())

    def _append(self, window):
        # Otherwise this menu would be empty for e.g. Oblivion
        return any(l._append(window) for l in self.links)

#--New project dialog ---------------------------------------------------------
class Installers_CreateNewProject(ItemLink):
    """Open the New Project Dialog"""
    _text = _(u'New Project...')
    _help = _(u'Create a new project.')

    @balt.conversation
    def Execute(self): CreateNewProject.display_dialog(self.window)
