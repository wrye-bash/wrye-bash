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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""Menu items for the _main_ menu of the installer tab - their window attribute
points to the InstallersList singleton."""
from itertools import chain

from . import Installers_Link
from .dialogs import CreateNewProject, CleanDataEditor, \
    MonitorExternalInstallationEditor
from .. import balt, bass, bolt, bosh, bush, exception, load_order
from ..balt import AppendableLink, BoolLink, EnabledLink, ItemLink, \
    SeparatorLink
from ..gui import copy_text_to_clipboard
from ..parsers import CsvParser

__all__ = ['Installers_InstalledFirst', 'Installers_ProjectsFirst',
           u'Installers_RefreshData', u'Installers_AddMarker',
           'Installers_MonitorExternalInstallation',
           u'Installers_ListPackages', u'Installers_AnnealAll',
           u'Installers_UninstallAllPackages', 'Installers_CreateNewProject',
           'Installers_CleanData', 'Installers_AvoidOnStart',
           u'Installers_Enabled', u'Installers_AutoAnneal',
           u'Installers_AutoWizard', u'Installers_AutoRefreshProjects',
           'Installers_SkipVanillaContent',
           u'Installers_ApplyEmbeddedBCFs', u'Installers_BsaRedirection',
           u'Installers_RemoveEmptyDirs',
           u'Installers_ShowInactiveConflicts',
           u'Installers_ShowLowerConflicts',
           u'Installers_ShowActiveBSAConflicts',
           u'Installers_WizardOverlay', u'Installers_GlobalSkips',
           u'Installers_GlobalRedirects', u'Installers_FullRefresh',
           'Installers_IgnoreFomod', 'Installers_ValidateFomod',
           'Installers_SimpleFirst', 'Installers_ExportOrder',
           'Installers_ImportOrder']

#------------------------------------------------------------------------------
# Installers Links ------------------------------------------------------------
#------------------------------------------------------------------------------
class Installers_AddMarker(ItemLink):
    """Add an installer marker."""
    _text = _(u'New Marker...')
    _help = _(u'Adds a Marker, a special type of package useful for '
              u'separating and labelling your packages.')
    _keyboard_hint = 'Ctrl+Shift+N'

    def Execute(self):
        """Add a Marker."""
        self.window.addMarker()

#------------------------------------------------------------------------------
class Installers_MonitorExternalInstallation(Installers_Link):
    """Monitors Data folder for external installation."""
    _text = _dialog_title = _('Monitor External Installation...')
    _help = _('Monitors the %(data_folder)s folder to capture changes made '
              'manually or via 3rd party tools.') % {
        'data_folder': bush.game.mods_dir}

    @balt.conversation
    def Execute(self):
        msg = _('Wrye Bash will monitor your data folder for changes when '
                'installing a mod via an external application or manual '
                'install.  This will require two refreshes of the '
                '%(data_folder)s folder and may take some time. Continue?') % {
            'data_folder': bush.game.mods_dir}
        if not self._askYes(msg, _('External Installation')):
            return
        # Refresh Data
        self.iPanel.ShowPanel(canCancel=False, scan_data_dir=True)
        # Backup CRC data
        scd_before_install = self.idata.data_sizeCrcDate.copy()
        # Install and wait
        self._showOk(_(u'You may now install your mod.  When installation is '
                       u'complete, press Ok.'), _(u'External Installation'))
        # Refresh Data
        bosh.bsaInfos.refresh() # TODO: add bsas to BAIN refresh
        with load_order.Unlock():
            mods_changed = bosh.modInfos.refresh()
        inis_changed = bosh.iniInfos.refresh()
        ui_refresh = [bool(mods_changed), bool(inis_changed)]
        self.iPanel.ShowPanel(canCancel=False, scan_data_dir=True)
        # Determine changes
        curData = self.idata.data_sizeCrcDate
        newFiles = curData.keys() - scd_before_install.keys()
        delFiles = scd_before_install.keys() - curData.keys()
        sameFiles = curData.keys() & scd_before_install.keys()
        changedFiles = {file_ for file_ in sameFiles if
                        scd_before_install[file_][1] != curData[file_][1]}
        touchedFiles = {file_ for file_ in sameFiles if
                        scd_before_install[file_][2] != curData[file_][2]}
        touchedFiles -= changedFiles
        if not (newFiles or changedFiles or touchedFiles or delFiles):
            self._showOk(_('No changes were detected in the %(data_folder)s '
                           'folder.') % {'data_folder': bush.game.mods_dir},
                title=_('Monitor External Installation - No Changes'))
            return
        # Show results, select which files to include
        dialog_result = MonitorExternalInstallationEditor.display_dialog(
            self.window, new_files=sorted(newFiles),
            changed_files=sorted(changedFiles),
            touched_files=sorted(touchedFiles),
            deleted_files=sorted(delFiles))
        ed_ok, ed_new, ed_changed, ed_touched, ed_del = dialog_result
        # Ignore ed_del, we can't do anything about deleted files
        include = set(chain(ed_new, ed_changed, ed_touched))
        if not ed_ok or not include:
            return # Aborted by user or nothing left to package, cancel
        # Create Project
        projectName = self._askFilename(_('Project Name'),
            _('External Installation'), inst_type=bosh.InstallerProject,
            check_exists=False) # we will use unique_name
        if not projectName:
            return
        pr_path = bosh.InstallerProject.unique_name(projectName)
        # Copy Files
        with balt.Progress(_('Creating Project...')) as prog:
            self.idata.createFromData(pr_path, include, prog) # will order last
        # createFromData placed the new project last in install order - install
        try:
            self.idata.bain_install([pr_path], ui_refresh, override=False)
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)
        # Select new installer
        self.window.SelectLast()

#------------------------------------------------------------------------------
class Installers_ListPackages(Installers_Link):
    """Copies list of packages to clipboard."""
    _text = _(u'List Packages...')
    _help = _('Displays a list of all packages.  Also copies that list to the '
              'clipboard.  Useful for posting your package order on forums.')

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

#------------------------------------------------------------------------------
class Installers_AnnealAll(Installers_Link):
    """Anneal all packages."""
    _text = _('Anneal All')
    _help = _('Install any missing files (for active packages) and update '
              'the contents of the %(data_folder)s folder to account for all '
              'install order and configuration changes.') % {
        'data_folder': bush.game.mods_dir}

    @balt.conversation
    def Execute(self):
        """Anneal all packages."""
        ui_refresh = [False, False]
        try:
            with balt.Progress(_('Annealing...')) as progress:
                self.idata.bain_anneal(None, ui_refresh, progress=progress)
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

#------------------------------------------------------------------------------
class Installers_UninstallAllPackages(Installers_Link):
    """Uninstall all packages."""
    _text = _('Uninstall All Packages')
    _help = _('Uninstall all files from all installed packages.')

    @balt.conversation
    def Execute(self):
        """Uninstall all packages."""
        if not self._askYes(_('Really uninstall all packages?')): return
        ui_refresh = [False, False]
        try:
            with balt.Progress(_('Uninstalling...')) as progress:
                self.idata.bain_uninstall_all(ui_refresh, progress=progress)
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

#------------------------------------------------------------------------------
class _AInstallers_Refresh(AppendableLink, Installers_Link):
    """Refreshes all Installers data."""
    _full_refresh = False

    def _append(self, window): return bass.settings[u'bash.installers.enabled']

    @balt.conversation
    def Execute(self):
        self.idata.reset_refresh_flag_on_projects()
        self.iPanel.ShowPanel(fullRefresh=self._full_refresh,
                              scan_data_dir=True)

#------------------------------------------------------------------------------
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

#------------------------------------------------------------------------------
class Installers_RefreshData(_AInstallers_Refresh):
    _text = _('Refresh Data')
    _help = _('Rescan the %(data_folder)s folder and all project '
              'directories.') % {'data_folder': bush.game.mods_dir}

#------------------------------------------------------------------------------
class Installers_CleanData(Installers_Link):
    """Uninstall all files that do not come from a current package/bethesda
    files. For safety just moved to Game Mods/Bash Installers/Bash/Data
    Folder Contents (date/time)."""
    _text = _('Clean Data...')
    _help = _('Move all files that are not linked to an active installer '
              'out of the %(data_folder)s folder.') % {
        'data_folder': bush.game.mods_dir}
    _full_msg = (_('Clean %(data_folder)s folder?') % {
        'data_folder': bush.game.mods_dir} + f' {_help}\n\n' + _(
        "This includes files that were installed manually or by another "
        "program. Files will be moved to the '%(dfc_path)s' folder instead "
        "of being deleted so you can retrieve them later if necessary.") % {
        'dfc_path': bass.dirs['bainData'].join(
            f'{bush.game.mods_dir} Folder Contents <date>')} + '\n\n' + _(
        'Note that you will first be shown a list of files that this '
        'operation would remove and will have a chance to change the '
        'selection.'))

    @balt.conversation
    def Execute(self):
        if not self._askYes(self._full_msg): return
        mdir_fmt = {'data_folder': bush.game.mods_dir}
        all_unknown_files = sorted(self.idata.get_clean_data_dir_list())
        if not all_unknown_files:
            self._showOk(_('There are no untracked files in the '
                           '%(data_folder)s folder.') % mdir_fmt,
                title=_('Clean Data - %(data_folder)s is Clean') % mdir_fmt)
            return
        ed_ok, ed_unknown = CleanDataEditor.display_dialog(self.window,
            unknown_files=all_unknown_files)
        if not ed_ok or not ed_unknown:
            return # Aborted by user or nothing left to clean, cancel
        ui_refresh = [False, False]
        try:
            with balt.Progress(_('Cleaning %(data_folder)s '
                                 'contents...') % mdir_fmt, f'\n{" " * 65}'):
                self.idata.clean_data_dir(ed_unknown, ui_refresh)
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

#------------------------------------------------------------------------------
class Installers_CreateNewProject(ItemLink):
    """Open the New Project Dialog"""
    _text = _(u'New Project...')
    _help = _(u'Create a new project.')
    _keyboard_hint = 'Ctrl+N'

    @balt.conversation
    def Execute(self):
        CreateNewProject.display_dialog(self.window)

#------------------------------------------------------------------------------
class _AInstallers_Order(Installers_Link, CsvParser):
    """Base class for export/import package order links."""
    _csv_header = _('Package'), (_('Installed? (%(inst_y)s/%(inst_n)s)')
                                 % {'inst_y': 'Y', 'inst_n': 'N'})

class Installers_ExportOrder(_AInstallers_Order):
    """Export order and installation status for all packages."""
    _text = _('Export Order...')
    _help = _('Export the order and installation status of all packages.')

    def Execute(self):
        if not self._askContinue(_(
            'Note that Export Order will only export the order of all '
            'packages and whether or not they have been installed. It does '
            'not export, for example, which sub-packages you enabled. If you '
            'care about preserving such information, you may want to make a '
            'backup instead (see Settings > Global Settings... > Backups).'),
            'bash.installers.export_order.continue',
                title=_('Export Order - Note')): return
        exp_path = self._askSave(title=_('Export Order - Choose Destination'),
            defaultDir=bass.dirs['patches'], defaultFile='PackageOrder.csv',
            wildcard='*.csv')
        if not exp_path: return
        self.packages_exported = 0
        self.write_text_file(exp_path)
        self._showInfo(_('Exported order and installation status for '
                         '%(exp_num)d package(s) to %(exp_path)s.') % {
            'exp_num': self.packages_exported, 'exp_path': exp_path},
            title=_('Export Order - Done'))

    def _write_rows(self, out):
        # Order is indicated by the order in which the rows are written
        for fn_pkg, curr_pkg in self.idata.sorted_pairs():
            # Do not translate these. We want them to be human-readable, so
            # we use Y/N (see also the header), but we also need to be able to
            # import from any language later (e.g. if someone using WB in
            # Spanish shares a file with a friend who uses WB in English)
            pkg_installed = 'Y' if curr_pkg.is_active else 'N'
            out.write(f'"{fn_pkg}","{pkg_installed}"\n')
            self.packages_exported += 1

#------------------------------------------------------------------------------
class Installers_ImportOrder(_AInstallers_Order):
    """Import order and installation status for a subset of all packages from a
    previous export."""
    _text = _('Import Order...')
    _help = _('Import the order and installation status of packages from a '
              'previous export.')

    def Execute(self):
        if not self._askWarning(
            _('This will reorder and change the installation status of all '
              'packages from the chosen CSV file. It will not change the '
              'contents of the Data folder, you will have to manually install '
              'or uninstall affected packages for that. Packages that are '
              'not listed in the CSV file will not be touched.') + '\n\n' +
            _('Are you sure you want to proceed?'),
                title=_('Import Order - Warning')): return
        imp_path = self._askOpen(title=_('Import Order - Choose Source'),
            defaultDir=bass.dirs['patches'], defaultFile='PackageOrder.csv',
            wildcard='*.csv')
        if not imp_path: return
        self.first_line = True
        self.partial_package_order = []
        try:
            self.read_csv(imp_path)
        except (exception.BoltError, NotImplementedError):
            self._showError(_('The selected file is not a valid '
                              'package order CSV export.'),
                title=_('Import Order - Invalid CSV'))
            return
        reorder_err = self.idata.reorder_packages(self.partial_package_order)
        self.idata.refresh_ns()
        self.window.RefreshUI()
        if reorder_err:
            self._showError(reorder_err, title=_('Import Order - Error'))
        else:
            self._showInfo(_('Imported order and installation status for '
                             '%(total_imported)d package(s).') % {
                'total_imported': len(self.partial_package_order)},
                title=_('Import Order - Done'))

    def _parse_line(self, csv_fields):
        if self.first_line: # header validation
            self.first_line = False
            if len(csv_fields) != 2:
                raise exception.BoltError(f'Header error: {csv_fields}')
            return
        pkg_fstr, pkg_installed_yn = csv_fields
        if (pkg_fname := bolt.FName(pkg_fstr)) in self.idata:
            self.idata[pkg_fname].is_active = pkg_installed_yn == 'Y'
            self.partial_package_order.append(pkg_fname)

#------------------------------------------------------------------------------
# Installers BoolLinks --------------------------------------------------------
#------------------------------------------------------------------------------
class _Installers_BoolLink_Refresh(BoolLink):
    def Execute(self):
        super(_Installers_BoolLink_Refresh, self).Execute()
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class Installers_AutoAnneal(BoolLink):
    _text, _bl_key = _(u'Auto-Anneal'), u'bash.installers.autoAnneal'
    _help = _(u'Enable/Disable automatic annealing of packages.')

#------------------------------------------------------------------------------
class Installers_AutoWizard(BoolLink):
    _text = _(u'Auto-Anneal/Install Wizards')
    _bl_key = u'bash.installers.autoWizard'
    _help = _(u'Enable/Disable automatic installing or anneal (as applicable) '
              u'of packages after running its wizard.')

#------------------------------------------------------------------------------
class Installers_WizardOverlay(_Installers_BoolLink_Refresh):
    """Toggle using the wizard overlay icon"""
    _text  = _(u'Wizard Icon Overlay')
    _bl_key = u'bash.installers.wizardOverlay'
    _help =_(u'Enable/Disable the magic wand icon overlay for packages with '
             u'Wizards.')

#------------------------------------------------------------------------------
class Installers_AutoRefreshProjects(BoolLink):
    """Toggle autoRefreshProjects setting and update."""
    _text = _('Auto-Refresh Projects')
    _bl_key = 'bash.installers.autoRefreshProjects'
    _help = _('Toggles whether or not Wrye Bash will automatically detect '
              'changes to projects in the installers folder.')

#------------------------------------------------------------------------------
class Installers_IgnoreFomod(BoolLink):
    _text = _(u'Ignore FOMODs')
    _bl_key = u'bash.installers.ignore_fomods'
    _help = _('Ignores FOMODs when using the "Install..." option. If this is '
              'checked, FOMODs will only be used when you specifically run '
              'them via "Run FOMOD...".')

#------------------------------------------------------------------------------
class Installers_ValidateFomod(BoolLink):
    _text = _('Validate FOMODs')
    _bl_key = 'bash.installers.validate_fomods'
    _help = _('Enable/disable verification of ModuleConfig.xml files against '
              'the official schema when running an FOMOD installer.')

#------------------------------------------------------------------------------
class Installers_ApplyEmbeddedBCFs(ItemLink):
    """Automatically apply Embedded BCFs to archives that have one."""
    _text = _(u'Apply Embedded BCFs')
    _help = _(u'Automatically apply Embedded BCFs to their containing '
              u'archives.')

    @balt.conversation
    def Execute(self):
        with balt.Progress(_('Auto-Applying Embedded BCFs...')) as progress:
            destinations, converted = self._data_store.applyEmbeddedBCFs(
                progress=progress)
            if not destinations: return
        self.window.RefreshUI()
        self.window.ClearSelected(clear_details=True)
        self.window.SelectItemsNoCallback(destinations + converted)

#------------------------------------------------------------------------------
class Installers_SkipVanillaContent(BoolLink, Installers_Link):
    """Change whether or not to install vanilla content."""
    _text = _('Skip Vanilla Content')
    _bl_key = u'bash.installers.autoRefreshBethsoft'
    _help = _('If checked, do not overwrite plugins and BSAs that came with '
              'the original, unmodified game.')
    opposite = True
    _message = (_('Enable installation of vanilla content?') + '\n\n' +
                _("It is recommended to keep backups of any affected files. "
                  "Unmodified copies can be reacquired via Steam's 'Verify "
                  "integrity of game files' command.") + '\n\n' +
                _('Are you sure you want to continue?'))

    @balt.conversation
    def Execute(self):
        if not bass.settings[self._bl_key] and not self._askYes(self._message):
            return
        super().Execute()
        # Refresh Installers
        toRefresh = {iname for iname, installer in self.idata.items() if
                     installer.hasBethFiles}
        self.window.rescanInstallers(toRefresh, abort=False,
                                     update_from_data=False, shallow=True)

#------------------------------------------------------------------------------
class Installers_Enabled(BoolLink, Installers_Link):
    """Flips installer state."""
    _text, _bl_key, _help = _(u'Enabled'), u'bash.installers.enabled', _(
        u'Enable/Disable the Installers tab.')
    _dialog_title = _(u'Enable Installers')
    message = _(u'Do you want to enable Installers?') + u'\n\n\t' + _(
        u'If you do, Bash will first need to initialize some data. This can '
        u'take on the order of five minutes if there are many mods installed.')

    @balt.conversation
    def Execute(self):
        """Enable/Disable the installers tab."""
        enabled = bass.settings[self._bl_key]
        if not enabled and not self._askYes(self.message,
                                            title=self._dialog_title): return
        enabled = bass.settings[self._bl_key] = not enabled
        if enabled:
            self.window.panel.ShowPanel(scan_data_dir=True)
        else:
            self.window.DeleteAll()
            self.window.panel.ClearDetails()

#------------------------------------------------------------------------------
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
                with balt.Progress(
                        _('Enabling BSA Redirection...')) as progress:
                    bsaFile.undo_alterations(progress)
        bosh.oblivionIni.setBsaRedirection(bass.settings[self._bl_key])

#------------------------------------------------------------------------------
class Installers_ShowInactiveConflicts(_Installers_BoolLink_Refresh):
    """Toggles option to show inactive on conflicts report."""
    _text = _(u'Show Inactive Conflicts')
    _help = _(u'In the conflicts tab also display conflicts with inactive '
              u'(not installed) installers')
    _bl_key = u'bash.installers.conflictsReport.showInactive'

#------------------------------------------------------------------------------
class Installers_ShowLowerConflicts(_Installers_BoolLink_Refresh):
    """Toggles option to show lower on conflicts report."""
    _text = _(u'Show Lower Conflicts')
    _help = _(u'In the conflicts tab also display conflicts with lower order '
             u'installers (or lower loading active bsas)')
    _bl_key = u'bash.installers.conflictsReport.showLower'

#------------------------------------------------------------------------------
class Installers_ShowActiveBSAConflicts(_Installers_BoolLink_Refresh):
    """Toggles option to show files inside BSAs on conflicts report."""
    _text = _(u'Show Active BSA Conflicts')
    _help = _(u'In the conflicts tab also display same-name resources inside '
             u'installed *and* active bsas')
    _bl_key = u'bash.installers.conflictsReport.showBSAConflicts'

#------------------------------------------------------------------------------
class Installers_AvoidOnStart(BoolLink):
    """Ensures faster bash startup by preventing Installers from being startup tab."""
    _text, _bl_key, = _(u'Avoid at Startup'), u'bash.installers.fastStart'
    _help = _(u'Toggles Wrye Bash to avoid the Installers tab on startup, '
              u'avoiding unnecessary data scanning.')

#------------------------------------------------------------------------------
class Installers_RemoveEmptyDirs(BoolLink):
    """Toggles option to remove empty directories on file scan."""
    _text = _('Remove Empty Directories')
    _help = _('Toggles whether or not Wrye Bash will remove empty directories '
              'when scanning the %(data_folder)s folder.') % {
        'data_folder': bush.game.mods_dir}
    _bl_key = 'bash.installers.removeEmptyDirs'

#------------------------------------------------------------------------------
# Sorting Links ---------------------------------------------------------------
#------------------------------------------------------------------------------
class _Installer_Sort(ItemLink):
    def Execute(self):
        super(_Installer_Sort, self).Execute()
        self.window.SortItems()

#------------------------------------------------------------------------------
class Installers_InstalledFirst(_Installer_Sort, BoolLink):
    """Sort installed packages to the top."""
    _text = _('Installed First')
    _bl_key = 'bash.installers.sortActive'
    _help = _('If checked, sort installed packages to the top of the list.')

#------------------------------------------------------------------------------
class Installers_ProjectsFirst(_Installer_Sort, BoolLink):
    """Sort dirs to the top."""
    _text = _('Projects First')
    _bl_key = 'bash.installers.sortProjects'
    _help = _('If checked, sort projects to the top of the list.')

#------------------------------------------------------------------------------
class Installers_SimpleFirst(_Installer_Sort, BoolLink):
    """Sort simple packages to the top."""
    _text = _('Simple First')
    _bl_key = 'bash.installers.sortStructure'
    _help = _('If checked, sort simple packages to the top of the list.')

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
    def _pre_rescan_action(self):
        bosh.bain.Installer.init_global_skips()

#------------------------------------------------------------------------------
class _Installers_SkipOBSEPlugins(AppendableLink, _Installers_Skip):
    """Toggle allowOBSEPlugins setting and update."""
    _se_sd = (f'{bush.game.Se.se_abbrev}/{bush.game.Sd.long_name}'
              if bush.game.Sd.sd_abbrev else bush.game.Se.se_abbrev)
    _text = _('Skip %(se_sd)s Plugins') % {'se_sd': _se_sd}
    _help = _('Skips the installation of %(se_sd)s '
              'plugins.') % {'se_sd': _se_sd}
    _bl_key = 'bash.installers.allowOBSEPlugins'

    def _append(self, window):
        return bool(self._se_sd)

    def _check(self):
        return not bass.settings[self._bl_key]

#------------------------------------------------------------------------------
class _Installers_SkipScreenshots(_Installers_Skip):
    """Toggle skipScreenshots setting and update."""
    _text = _('Skip Screenshots')
    _help = _('Skips the installation of files in screenshot directories.')
    _bl_key = 'bash.installers.skipScreenshots'

#------------------------------------------------------------------------------
class _Installers_SkipScriptSources(AppendableLink, _Installers_Skip):
    """Toggle skipScriptSources setting and update."""
    _text = _('Skip Script Sources')
    _help = _('Skips the installation of script sources (%(ss_exts)s).') % {
        'ss_exts': ', '.join(bush.game.Psc.source_extensions)}
    _bl_key = 'bash.installers.skipScriptSources'

    def _append(self, window):
        return bool(bush.game.Psc.source_extensions)

#------------------------------------------------------------------------------
class _Installers_SkipImages(_Installers_Skip):
    """Toggle skipImages setting and update."""
    _text = _('Skip Images')
    _help = _('Skips the installation of images (.png, .jpg, etc.).')
    _bl_key = 'bash.installers.skipImages'

#------------------------------------------------------------------------------
class _Installers_SkipDocs(_Installers_Skip):
    """Toggle skipDocs setting and update."""
    _text = _('Skip Docs')
    _help = _('Skips the installation of documentation (.txt, .html, etc.).')
    _bl_key = 'bash.installers.skipDocs'

#------------------------------------------------------------------------------
class _Installers_SkipDistantLOD(AppendableLink, _Installers_Skip):
    """Toggle skipDistantLOD setting and update."""
    _text = _('Skip DistantLOD')
    _help = _('Skips the installation of files in the distantlod folder.')
    _bl_key = 'bash.installers.skipDistantLOD'

    def _append(self, window):
        return 'distantlod' in bush.game.Bain.data_dirs

#------------------------------------------------------------------------------
class _Installers_SkipLandscapeLODMeshes(_Installers_Skip):
    """Toggle skipLandscapeLODMeshes setting and update."""
    _text = _('Skip LOD Meshes')
    _help = _('Skips the installation of LOD meshes.')
    _bl_key = 'bash.installers.skipLandscapeLODMeshes'

#------------------------------------------------------------------------------
class _Installers_SkipLandscapeLODTextures(_Installers_Skip):
    """Toggle skipLandscapeLODTextures setting and update."""
    _text = _('Skip LOD Textures')
    _help = _('Skips the installation of LOD textures (except normals).')
    _bl_key = 'bash.installers.skipLandscapeLODTextures'

#------------------------------------------------------------------------------
class _Installers_SkipLandscapeLODNormals(_Installers_Skip):
    """Toggle skipLandscapeLODNormals setting and update."""
    _text = _('Skip LOD Normals')
    _help = _('Skips the installation of LOD normals.')
    _bl_key = 'bash.installers.skipLandscapeLODNormals'

#------------------------------------------------------------------------------
class _Installers_SkipBsl(AppendableLink, _Installers_Skip):
    """Toggle skipTESVBsl setting and update."""
    _text = _('Skip BSL Files')
    _help = _('Skips the installation of .bsl files.')
    _bl_key = 'bash.installers.skipTESVBsl'

    def _append(self, window):
        return bush.game.Bsa.has_bsl

#------------------------------------------------------------------------------
class _Installers_SkipPdb(AppendableLink, _Installers_Skip):
    """Toggle skipPDBs setting and update."""
    _text = _('Skip PDB Files')
    _help = _('Skips the installation of .pdb files.')
    _bl_key = 'bash.installers.skipPDBs'

    def _append(self, window):
        return bool(bush.game.Se.se_abbrev)

#------------------------------------------------------------------------------
class Installers_GlobalSkips(balt.MenuLink):
    """Global Skips submenu."""
    _text = _('Global Skips..')

    def __init__(self):
        super().__init__()
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
        self.append(_Installers_SkipPdb())

#------------------------------------------------------------------------------
# Redirection/Rename Links ----------------------------------------------------
#------------------------------------------------------------------------------
class _AInstallers_NoSkipDocs(EnabledLink, _Installers_RescanningLink):
    """Base class for redirect links that don't work when Skip Docs is on."""
    def _enable(self):
        return not bass.settings['bash.installers.skipDocs']

#------------------------------------------------------------------------------
class _Installers_RedirectCSVs(_Installers_RescanningLink):
    """Toggle auto-redirection of top-level CSV files."""
    _text = _('Redirect CSVs')
    _help = _('If checked, Wrye Bash will move all top-level CSV files (.csv) '
              'to the Bash Patches folder.')
    _bl_key = 'bash.installers.redirect_csvs'

#------------------------------------------------------------------------------
class _Installers_RedirectDocs(_AInstallers_NoSkipDocs):
    """Toggle auto-redirection of docs."""
    _text = _('Redirect Docs')
    _help = _('If checked, Wrye Bash will move all top-level documentation '
              "files (.txt, .html, etc.) to a Docs subfolder. 'Skip "
              "Docs' must be off.")
    _bl_key = 'bash.installers.redirect_docs'

#------------------------------------------------------------------------------
class _Installers_RedirectScriptSources(AppendableLink, EnabledLink,
                                        _Installers_RescanningLink):
    """Toggle auto-redirection of script sources."""
    _text = _('Redirect Script Sources')
    _help = _('If checked, Wrye Bash will move all script sources '
              'installed to incorrect directories (%(incorrect_dirs)s) to the '
              "correct ones. 'Skip Script Sources' must be off.") % {
        'incorrect_dirs': ', '.join(bush.game.Psc.source_redirects)}
    _bl_key = 'bash.installers.redirect_scripts'

    def _append(self, window):
        return bool(bush.game.Psc.source_redirects)

    def _enable(self):
        return not bass.settings['bash.installers.skipScriptSources']

#------------------------------------------------------------------------------
class _Installers_RenameDocs(_AInstallers_NoSkipDocs):
    """Toggle auto-renaming of docs."""
    _text = _('Rename Docs')
    _help = _('If checked, Wrye Bash will rename documentation files with '
              'common names (e.g. readme.txt) to avoid packages overwriting '
              "each other's docs.")
    _bl_key = 'bash.installers.rename_docs'

#------------------------------------------------------------------------------
class _Installers_RenameStrings(AppendableLink, _Installers_RescanningLink):
    """Toggle auto-renaming of .STRINGS files"""
    _text = _('Rename String Translation Files')
    _help = _('If checked, Wrye Bash will rename installed string files so '
              'they match your current language if none are provided for it.')
    _bl_key = 'bash.installers.renameStrings'

    def _append(self, window):
        return bool(bush.game.Esp.stringsFiles)

#------------------------------------------------------------------------------
class Installers_GlobalRedirects(balt.MenuLink):
    """Global Redirects menu."""
    _text = _('Global Redirects..')

    def __init__(self):
        super().__init__()
        self.append(_Installers_RedirectCSVs())
        self.append(_Installers_RedirectDocs())
        self.append(_Installers_RedirectScriptSources())
        self.append(SeparatorLink())
        self.append(_Installers_RenameDocs())
        self.append(_Installers_RenameStrings())
