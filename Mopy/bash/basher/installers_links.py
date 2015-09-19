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

"""Menu items for the _main_ menu of the installer tab - their window attribute
points to the InstallersList singleton."""

import copy
from . import Installers_Link
from .dialogs import CreateNewProject
from .. import bosh, balt, bush
from ..balt import BoolLink, AppendableLink, ItemLink, ListBoxes
from ..bass import Resources

__all__ = ['Installers_SortActive', 'Installers_SortProjects',
           'Installers_Refresh', 'Installers_AddMarker',
           'Installers_CreateNewProject', 'Installers_MonitorInstall',
           'Installers_ListPackages', 'Installers_AnnealAll',
           'Installers_UninstallAllPackages',
           'Installers_UninstallAllUnknownFiles', 'Installers_AvoidOnStart',
           'Installers_Enabled', 'Installers_AutoAnneal',
           'Installers_AutoWizard', 'Installers_AutoRefreshProjects',
           'Installers_AutoRefreshBethsoft',
           'Installers_AutoApplyEmbeddedBCFs', 'Installers_BsaRedirection',
           'Installers_RemoveEmptyDirs',
           'Installers_ConflictsReportShowsInactive',
           'Installers_ConflictsReportShowsLower',
           'Installers_ConflictsReportShowBSAConflicts',
           'Installers_WizardOverlay', 'Installers_SkipOBSEPlugins',
           'Installers_SkipScreenshots', 'Installers_SkipImages',
           'Installers_SkipDocs', 'Installers_SkipDistantLOD',
           'Installers_SkipLandscapeLODMeshes',
           'Installers_SkipLandscapeLODTextures',
           'Installers_SkipLandscapeLODNormals', 'Installers_SkipBsl',
           'Installers_RenameStrings']

#------------------------------------------------------------------------------
# Installers Links ------------------------------------------------------------
#------------------------------------------------------------------------------
class Installers_AddMarker(ItemLink):
    """Add an installer marker."""
    text = _(u'Add Marker...')
    help = _(u'Adds a Marker, a special type of package useful for separating'
             u' and labelling your packages.')

    def Execute(self,event):
        """Add a Marker."""
        self.window.addMarker()

class Installers_MonitorInstall(Installers_Link):
    """Monitors Data folder for external installation."""
    text = _(u'Monitor External Installation...')
    help = _(u'Monitors the Data folder during installation via manual install'
             u' or 3rd party tools.')

    def Execute(self,event):
        """Handle Selection."""
        msg = _(u'Wrye Bash will monitor your data folder for changes when '
                u'installing a mod via an external application or manual '
                u'install.  This will require two refreshes of the Data folder'
                u' and may take some time.')
        if not self._askOk(msg, _(u'External Installation')): return
        # Refresh Data
        self.iPanel.refreshed = False
        self.iPanel.fullRefresh = False
        self.iPanel.ShowPanel(canCancel=False)
        # Backup CRC data
        data = copy.copy(self.iPanel.data.data_sizeCrcDate)
        # Install and wait
        self._showOk(_(u'You may now install your mod.  When installation is '
                       u'complete, press Ok.'),
                     _(u'External Installation'))
        # Refresh Data
        self.iPanel.refreshed = False
        self.iPanel.fullRefresh = False
        self.iPanel.ShowPanel(canCancel=False)
        # Determine changes
        curData = self.iPanel.data.data_sizeCrcDate
        oldFiles = set(data)
        curFiles = set(curData)
        newFiles = curFiles - oldFiles
        delFiles = oldFiles - curFiles
        sameFiles = curFiles & oldFiles
        changedFiles = set(file_ for file_ in sameFiles if data[file_][1] != curData[file_][1])
        touchedFiles = set(file_ for file_ in sameFiles if data[file_][2] != curData[file_][2])
        touchedFiles -= changedFiles

        if not newFiles and not changedFiles and not touchedFiles:
            self._showOk(_(u'No changes were detected in the Data directory.'),
                         _(u'External Installation'))
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
        dialog = ListBoxes(self.window,_(u'External Installation'),
                           _(u'The following changes were detected in the Data directory'),
                           checklists, bOk=_(u'Create Project'))
        if not dialog.askOkModal():
            dialog.Destroy()
            return
        include = set()
        for (lst, key) in [(newFiles, newFilesKey),
                           (changedFiles, changedFilesKey),
                           (touchedFiles, touchedFilesKey), ]:
            include |= set(dialog.getChecked(key, lst))
        dialog.Destroy()
        # Create Project
        if not include:
            return
        projectName = self._askText(_(u'Project Name'),
                                    _(u'External Installation'))
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
        self.iPanel.ShowPanel()
        # Update the status of the installer (as installer last)
        path = path.relpath(bosh.dirs['installers'])
        self.idata.install([path],None,True,False)
        # Refresh UI
        self.iPanel.RefreshUIMods()
        # Select new installer
        self.window.SelectLast()

class Installers_ListPackages(Installers_Link):
    """Copies list of Bain files to clipboard."""
    text = _(u'List Packages...')
    help = _(u'Displays a list of all packages.  Also copies that list to the '
        u'clipboard.  Useful for posting your package order on forums.')

    def Execute(self,event):
        #--Get masters list
        message = (_(u'Only show Installed Packages?')
                   + u'\n' +
                   _(u'(Else shows all packages)')
                   )
        if self._askYes(message,_(u'Only Show Installed?')):
            text = self.idata.getPackageList(False)
        else: text = self.idata.getPackageList()
        balt.copyToClipboard(text)
        self._showLog(text, title=_(u'BAIN Packages'), fixedFont=False,
                      icons=Resources.bashBlue)

class Installers_AnnealAll(Installers_Link):
    """Anneal all packages."""
    text = _(u'Anneal All')
    help = _(u'This will install any missing files (for active installers)'
             u' and correct all install order and reconfiguration errors.')

    def Execute(self,event):
        """Anneal all packages."""
        try:
            with balt.Progress(_(u"Annealing..."),u'\n'+u' '*60) as progress:
                self.idata.anneal(progress=progress)
        finally:
            self.iPanel.RefreshUIMods(_refreshData=True)

class Installers_UninstallAllPackages(Installers_Link):
    """Uninstall all packages."""
    text = _(u'Uninstall All Packages')
    help = _(u'This will uninstall all packages.')

    def Execute(self,event):
        """Uninstall all packages."""
        if not self._askYes(_(u"Really uninstall All Packages?")): return
        try:
            with balt.Progress(_(u"Uninstalling..."),u'\n'+u' '*60) as progress:
                self.idata.uninstall(unArchives='ALL',progress=progress)
        finally:
            self.iPanel.RefreshUIMods(_refreshData=True)

class Installers_Refresh(AppendableLink, Installers_Link):
    """Refreshes all Installers data."""
    msg = _(u"Refresh ALL data from scratch? This may take five to ten minutes"
            u" (or more) depending on the number of mods you have installed.")

    def __init__(self, fullRefresh=False):
        super(Installers_Refresh, self).__init__()
        self.fullRefresh = fullRefresh
        self.text = (_(u'Refresh Data'),_(u'Full Refresh'))[self.fullRefresh]
        self.help = _(
            u"Perform a full refresh of all data files, recalculating all "
            u"CRCs.  This can take 5-15 minutes.") if self.fullRefresh else _(
            u"Rescan the Data directory and all project directories.")

    def _append(self, window): return bosh.settings['bash.installers.enabled']
    def Execute(self,event):
        """Refreshes all Installers data"""
        if self.fullRefresh and not self._askWarning(self.msg, self.text):
            return
        self.iPanel.refreshed = False
        self.iPanel.fullRefresh = self.fullRefresh
        self.iPanel.ShowPanel()

class Installers_UninstallAllUnknownFiles(Installers_Link):
    """Uninstall all files that do not come from a current package/bethesda
    files. For safety just moved to Oblivion Mods\Bash Installers\Bash\Data
    Folder Contents (date/time)\."""
    text = _(u'Clean Data')
    help = _(u'This will remove all mod files that are not linked to an'
             u' active installer out of the Data folder.')
    fullMessage = _(u"Clean Data directory?") + u"  " + help + u"  " + _(
        u'This includes files that were installed manually or by another '
        u'program.  Files will be moved to the "%s" directory instead of '
        u'being deleted so you can retrieve them later if necessary.  '
        u'Note that if you use TES4LODGen, this will also clean out the '
        u'DistantLOD folder, so on completion please run TES4LodGen again.'
        ) % ur'Oblivion Mods\Bash Installers\Bash\Data Folder Contents <date>'

    def Execute(self,event):
        if self._askYes(self.fullMessage):
            try:
                with balt.Progress(_(u"Cleaning Data Files..."),
                                   u'\n' + u' ' * 65) as progress:
                    self.idata.clean(progress=progress)
            finally:
                self.idata.irefresh(what='NS')
                self.iPanel.RefreshUIMods(_refreshData=True)

#------------------------------------------------------------------------------
# Installers BoolLinks --------------------------------------------------------
#------------------------------------------------------------------------------
class Installers_AutoAnneal(BoolLink):
    text, key, help = _(u'Auto-Anneal'), 'bash.installers.autoAnneal', _(
        u"Enable/Disable automatic annealing of packages.")

class Installers_AutoWizard(BoolLink):
    text = _(u'Auto-Anneal/Install Wizards')
    key = 'bash.installers.autoWizard'
    help = _(u"Enable/Disable automatic installing or anneal (as applicable)"
             u" of packages after running its wizard.")

class _Installers_BoolLink_Refresh(BoolLink):
    def Execute(self,event):
        super(_Installers_BoolLink_Refresh, self).Execute(event)
        self.window.RefreshUI()

class Installers_WizardOverlay(_Installers_BoolLink_Refresh):
    """Toggle using the wizard overlay icon"""
    text  = _(u'Wizard Icon Overlay')
    key = 'bash.installers.wizardOverlay'
    help =_(u"Enable/Disable the magic wand icon overlay for packages with"
            u" Wizards.")

class Installers_AutoRefreshProjects(BoolLink):
    """Toggle autoRefreshProjects setting and update."""
    text = _(u'Auto-Refresh Projects')
    key = 'bash.installers.autoRefreshProjects'

class Installers_AutoApplyEmbeddedBCFs(BoolLink):
    """Toggle autoApplyEmbeddedBCFs setting and update."""
    text = _(u'Auto-Apply Embedded BCFs')
    key = 'bash.installers.autoApplyEmbeddedBCFs'
    help = _(u'If enabled, embedded BCFs will automatically be applied to '
        u'archives.')

    def Execute(self,event):
        super(Installers_AutoApplyEmbeddedBCFs, self).Execute(event)
        self.window.panel.ShowPanel()

class Installers_AutoRefreshBethsoft(BoolLink, Installers_Link):
    """Toggle refreshVanilla setting and update."""
    text = _(u'Skip Bethsoft Content')
    key = 'bash.installers.autoRefreshBethsoft'
    help = _(u'Skip installing Bethesda ESMs, ESPs, and BSAs')
    opposite = True
    message = _(u"Enable installation of Bethsoft Content?") + u'\n\n' + _(
        u"In order to support this, Bethesda ESPs, ESMs, and BSAs need to "
        u"have their CRCs calculated.  This will be accomplished by a full "
        u"refresh of BAIN data an may take quite some time.  Are you sure "
        u"you want to continue?")

    def Execute(self,event):
        if not bosh.settings[self.key] and not self._askYes(self.message):
            return
        super(Installers_AutoRefreshBethsoft, self).Execute(event)
        if bosh.settings[self.key]:
            # Refresh Data - only if we are now including Bethsoft files
            self.iPanel.refreshed = False
            self.iPanel.fullRefresh = False
            self.iPanel.ShowPanel()
        # Refresh Installers
        toRefresh = set()
        for name, installer in self.idata.iteritems():
            if installer.hasBethFiles: toRefresh.add((name,installer))
        self.window.rescanInstallers(toRefresh, abort=False)

class Installers_Enabled(BoolLink):
    """Flips installer state."""
    text, key, help = _(u'Enabled'), 'bash.installers.enabled', _(
        u'Enable/Disable the Installers tab.')
    dialogTitle = _(u'Enable Installers')
    message = _(u"Do you want to enable Installers?") + u'\n\n\t' + _(
        u"If you do, Bash will first need to initialize some data. This can "
        u"take on the order of five minutes if there are many mods installed.")

    def Execute(self,event):
        """Enable/Disable the installers tab."""
        enabled = bosh.settings[self.key]
        if not enabled and not self._askYes(self.message,
                                            title=self.dialogTitle): return
        enabled = bosh.settings[self.key] = not enabled
        if enabled:
            self.window.panel.refreshed = False
            self.window.panel.ShowPanel()
            self.window.RefreshUI()
        else:
            self.window.DeleteAll() ##: crude
            self.window.panel.ClearDetails()

class Installers_BsaRedirection(AppendableLink, BoolLink):
    """Toggle BSA Redirection."""
    text, key = _(u'BSA Redirection'),'bash.bsaRedirection'
    help = _(u"Use Quarn's BSA redirection technique.")

    def _append(self, window):
        section,key = bush.game.ini.bsaRedirection
        return bool(section) and bool(key)

    def Execute(self,event):
        """Handle selection."""
        super(Installers_BsaRedirection, self).Execute(event)
        if bosh.settings[self.key]:
            bsaPath = bosh.modInfos.dir.join(bosh.inisettings['OblivionTexturesBSAName'])
            bsaFile = bosh.BsaFile(bsaPath)
            bsaFile.scan()
            resetCount = bsaFile.reset()
            #balt.showOk(self,_(u"BSA Hashes reset: %d") % (resetCount,))
        bosh.oblivionIni.setBsaRedirection(bosh.settings[self.key])

class Installers_ConflictsReportShowsInactive(_Installers_BoolLink_Refresh):
    """Toggles option to show inactive on conflicts report."""
    text = _(u'Show Inactive Conflicts')
    key = 'bash.installers.conflictsReport.showInactive'

class Installers_ConflictsReportShowsLower(_Installers_BoolLink_Refresh):
    """Toggles option to show lower on conflicts report."""
    text = _(u'Show Lower Conflicts')
    key = 'bash.installers.conflictsReport.showLower'

class Installers_ConflictsReportShowBSAConflicts(_Installers_BoolLink_Refresh):
    """Toggles option to show files inside BSAs on conflicts report."""
    text = _(u'Show BSA Conflicts')
    key = 'bash.installers.conflictsReport.showBSAConflicts'

class Installers_AvoidOnStart(BoolLink):
    """Ensures faster bash startup by preventing Installers from being startup tab."""
    text, key, help = _(u'Avoid at Startup'), 'bash.installers.fastStart', _(
        u"Toggles Wrye Bash to avoid the Installers tab on startup,"
        u" avoiding unnecessary data scanning.")

class Installers_RemoveEmptyDirs(BoolLink):
    """Toggles option to remove empty directories on file scan."""
    text, key = _(u'Clean Data Directory'), 'bash.installers.removeEmptyDirs'

# Sorting Links
class _Installer_Sort(ItemLink):
    def Execute(self,event):
        super(_Installer_Sort, self).Execute(event)
        self.window.SortItems()

class Installers_SortActive(_Installer_Sort, BoolLink):
    """Sort by type."""
    text, key, help = _(u'Sort by Active'), 'bash.installers.sortActive', _(
        u'If selected, active installers will be sorted to the top of the list.')

class Installers_SortProjects(_Installer_Sort, BoolLink):
    """Sort dirs to the top."""
    text, key, help = _(u'Projects First'), 'bash.installers.sortProjects', _(
        u'If selected, projects will be sorted to the top of the list.')

class Installers_SortStructure(_Installer_Sort, BoolLink):
    """Sort by type."""
    text, key = _(u'Sort by Structure'), 'bash.installers.sortStructure'

#------------------------------------------------------------------------------
# Installers_Skip Links -------------------------------------------------------
#------------------------------------------------------------------------------
class Installers_Skip(Installers_Link, BoolLink):
    """Toggle various skip settings and update."""
    def Execute(self,event):
        super(Installers_Skip, self).Execute(event)
        with balt.Progress(_(u'Refreshing Packages...'),u'\n'+u' '*60, abort=False) as progress:
            progress.setFull(len(self.idata))
            for index,dataItem in enumerate(self.idata.iteritems()):
                progress(index,_(u'Refreshing Packages...')+u'\n'+dataItem[0].s)
                dataItem[1].refreshDataSizeCrc()
        self.idata.irefresh(what='NS')
        self.window.RefreshUI()

class Installers_SkipScreenshots(Installers_Skip):
    """Toggle skipScreenshots setting and update."""
    text, key = _(u'Skip Screenshots'), 'bash.installers.skipScreenshots'

class Installers_SkipImages(Installers_Skip):
    """Toggle skipImages setting and update."""
    text, key = _(u'Skip Images'), 'bash.installers.skipImages'

class Installers_SkipDocs(Installers_Skip):
    """Toggle skipDocs setting and update."""
    text, key = _(u'Skip Docs'), 'bash.installers.skipDocs'

class Installers_SkipDistantLOD(Installers_Skip):
    """Toggle skipDistantLOD setting and update."""
    text, key = _(u'Skip DistantLOD'), 'bash.installers.skipDistantLOD'

class Installers_SkipLandscapeLODMeshes(Installers_Skip):
    """Toggle skipLandscapeLODMeshes setting and update."""
    text, key = _(u'Skip LOD Meshes'), 'bash.installers.skipLandscapeLODMeshes'

class Installers_SkipLandscapeLODTextures(Installers_Skip):
    """Toggle skipLandscapeLODTextures setting and update."""
    text = _(u'Skip LOD Textures')
    key = 'bash.installers.skipLandscapeLODTextures'

class Installers_SkipLandscapeLODNormals(Installers_Skip):
    """Toggle skipLandscapeLODNormals setting and update."""
    text = _(u'Skip LOD Normals')
    key = 'bash.installers.skipLandscapeLODNormals'

class Installers_SkipBsl(AppendableLink, Installers_Skip):
    """Toggle skipTESVBsl setting and update."""
    text, key = _(u'Skip bsl Files'), 'bash.installers.skipTESVBsl'
    def _append(self, window): return bush.game.fsName == 'Skyrim'

class Installers_SkipOBSEPlugins(AppendableLink, Installers_Skip):
    """Toggle allowOBSEPlugins setting and update."""
    text = _(u'Skip %s Plugins') % bush.game.se_sd
    key = 'bash.installers.allowOBSEPlugins'

    def _append(self, window): return bool(bush.game.se_sd)
    def _check(self): return not bosh.settings[self.key]

class Installers_RenameStrings(AppendableLink, Installers_Skip):
    """Toggle auto-renaming of .STRINGS files"""
    text = _(u'Auto-name String Translation Files')
    key = 'bash.installers.renameStrings'

    def _append(self, window): return bool(bush.game.esp.stringsFiles)

class Installers_CreateNewProject(ItemLink):
    """Open the Create New Project Dialog"""
    text = _(u'Create New Project...')
    help = _(u'Create a new project...')

    def Execute(self, event): CreateNewProject.Display()
