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
import copy
from .. import bosh, balt, bush
from ..balt import fill, _Link, BoolLink, AppendableLink, Link
from . import ListBoxes, CreateNewProject
from ..bolt import GPath, SubProgress

gInstallers = None

#------------------------------------------------------------------------------
# Installers Links ------------------------------------------------------------
#------------------------------------------------------------------------------
class Installers_AddMarker(_Link):
    """Add an installer marker."""
    text = _(u'Add Marker...')
    help = _(u'Adds a Marker, a special type of package useful for separating'
             u' and labelling your packages.')

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
            self.gTank.SelectItemAtIndex(index)
            self.gTank.gList.EditLabel(index)

class Installers_MonitorInstall(_Link):
    """Monitors Data folder for external installation."""
    text = _(u'Monitor External Installation...')
    help = _(u'Monitors the Data folder during installation via manual install'
             u' or 3rd party tools.')

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
        changedFiles = set(file_ for file_ in sameFiles if data[file_][1] != curData[file_][1])
        touchedFiles = set(file_ for file_ in sameFiles if data[file_][2] != curData[file_][2])
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
                           checklists,changedlabels={ListBoxes.ID_OK:_(u'Create Project')})
        choice = dialog.ShowModal()
        if choice == ListBoxes.ID_CANCEL:
            dialog.Destroy()
            return
        include = set()
        for (lst,key) in [(newFiles,newFilesKey),
                           (changedFiles,changedFilesKey),
                           (touchedFiles,touchedFilesKey),
                           ]:
            if lst:
                id_ = dialog.ids[key]
                checks = dialog.FindWindowById(id_)
                if checks:
                    for i,file_ in enumerate(lst):
                        if checks.IsChecked(i):
                            include.add(file_)
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
        self.gTank.SelectItemAtIndex(self.gTank.gList.GetItemCount()-1)

class Installers_AnnealAll(_Link):
    """Anneal all packages."""
    text = _(u'Anneal All')
    help = _(u'This will install any missing files (for active installers)'
             u' and correct all install order and reconfiguration errors.')

    def Execute(self,event):
        """Handle selection."""
        try:
            with balt.Progress(_(u"Annealing..."),u'\n'+u' '*60) as progress:
                self.data.anneal(progress=progress)
        finally:
            self.data.refresh(what='NS')
            gInstallers.RefreshUIMods()
            Link.Frame.RefreshData()

class Installers_UninstallAllPackages(_Link):
    """Uninstall all packages."""
    text = _(u'Uninstall All Packages')
    help = _(u'This will uninstall all packages.')

    def Execute(self,event):
        """Handle selection."""
        if not balt.askYes(self.gTank,fill(_(u"Really uninstall All Packages?"),70),self.text): return
        try:
            with balt.Progress(_(u"Uninstalling..."),u'\n'+u' '*60) as progress:
                self.data.uninstall(unArchives='ALL',progress=progress)
        finally:
            self.data.refresh(what='NS')
            gInstallers.RefreshUIMods()
            Link.Frame.RefreshData()

class Installers_Refresh(AppendableLink, _Link):
    """Refreshes all Installers data."""
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
        """Handle selection."""
        if self.fullRefresh:
            message = balt.fill(_(u"Refresh ALL data from scratch? This may take five to ten minutes (or more) depending on the number of mods you have installed."))
            if not balt.askWarning(self.gTank,fill(message,80),self.text): return
        gInstallers.refreshed = False
        gInstallers.fullRefresh = self.fullRefresh
        gInstallers.OnShow()

class Installers_UninstallAllUnknownFiles(_Link):
    """Uninstall all files that do not come from a current package/bethesda
    files. For safety just moved to Oblivion Mods\Bash Installers\Bash\Data
    Folder Contents (date/time)\."""
    text = _(u'Clean Data')
    help = _(u'This will remove all mod files that are not linked to an'
             u' active installer out of the Data folder.')

    def Execute(self,event):
        """Handle selection."""
        fullMessage = _(
            u"Clean Data directory?") + u"  " + self.help + u"  " + _(
            u'This includes files that were installed manually or by another '
            u'program.  Files will be moved to the "%s" directory instead of '
            u'being deleted so you can retrieve them later if necessary.  '
            u'Note that if you use TES4LODGen, this will also clean out the '
            u'DistantLOD folder, so on completion please run TES4LodGen '
            u'again.') % u'Oblivion Mods\\Bash Installers\\Bash\\Data Folder Contents <date>'
        if balt.askYes(self.gTank,fill(fullMessage,70),self.text):
            try:
                with balt.Progress(_(u"Cleaning Data Files..."),
                                   u'\n' + u' ' * 65) as progress:
                    self.data.clean(progress=progress)
            finally:
                self.data.refresh(what='NS')
                gInstallers.RefreshUIMods()
                Link.Frame.RefreshData()

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
        BoolLink.Execute(self,event)
        gInstallers.gList.RefreshUI()

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
        BoolLink.Execute(self,event)
        gInstallers.OnShow()

class Installers_AutoRefreshBethsoft(BoolLink):
    """Toggle refreshVanilla setting and update."""
    text = _(u'Skip Bethsoft Content')
    key = 'bash.installers.autoRefreshBethsoft'
    help = _(u'Skip installing Bethesda ESMs, ESPs, and BSAs')

    def __init__(self):
        super(Installers_AutoRefreshBethsoft, self).__init__(True)

    def Execute(self,event):
        if not bosh.settings[self.key]:
            message = balt.fill(_(u"Enable installation of Bethsoft Content?") + u'\n\n' +
                                _(u"In order to support this, Bethesda ESPs, ESMs, and BSAs need to have their CRCs calculated.  This will be accomplished by a full refresh of BAIN data an may take quite some time.  Are you sure you want to continue?")
                                )
            if not balt.askYes(self.gTank,fill(message,80),self.text): return
        BoolLink.Execute(self,event)
        if bosh.settings[self.key]:
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

class Installers_Enabled(BoolLink):
    """Flips installer state."""
    text, key, help = _(u'Enabled'), 'bash.installers.enabled', _(
        u'Enable/Disable the Installers tab.')
    dialogTitle = _('Enable Installers')

    def Execute(self,event):
        """Handle selection."""
        enabled = bosh.settings[self.key]
        message = (_(u"Do you want to enable Installers?")
                   + u'\n\n\t' +
                   _(u"If you do, Bash will first need to initialize some data. This can take on the order of five minutes if there are many mods installed.")
                   )
        if not enabled and not balt.askYes(self.gTank,fill(message,80),self.dialogTitle):
            return
        enabled = bosh.settings[self.key] = not enabled
        if enabled:
            gInstallers.refreshed = False
            gInstallers.OnShow()
            gInstallers.gList.RefreshUI()
        else:
            gInstallers.gList.gList.DeleteAllItems()
            gInstallers.RefreshDetails(None)

class Installers_BsaRedirection(AppendableLink, BoolLink):
    """Toggle BSA Redirection."""
    text, key = _(u'BSA Redirection'),'bash.bsaRedirection',

    def _append(self, window):
        section,key = bush.game.ini.bsaRedirection
        return True if section and key else False

    def Execute(self,event):
        """Handle selection."""
        BoolLink.Execute(self,event)
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
    text, key = _(u'Show Lower Conflicts'), \
                'bash.installers.conflictsReport.showLower'

class Installers_ConflictsReportShowBSAConflicts(_Installers_BoolLink_Refresh):
    """Toggles option to show files inside BSAs on conflicts report."""
    text, key = _(u'Show BSA Conflicts'), \
                'bash.installers.conflictsReport.showBSAConflicts'

class Installers_AvoidOnStart(BoolLink):
    """Ensures faster bash startup by preventing Installers from being startup tab."""
    text, key, help = _(u'Avoid at Startup'), 'bash.installers.fastStart', _(
        u"Toggles Wrye Bash to avoid the Installers tab on startup,"
        u" avoiding unnecessary data scanning.")

class Installers_RemoveEmptyDirs(BoolLink):
    """Toggles option to remove empty directories on file scan."""
    text, key = _(u'Clean Data Directory'), 'bash.installers.removeEmptyDirs'

class Installers_SortActive(BoolLink):
    """Sort by type."""
    text, key, help = _(u'Sort by Active'), 'bash.installers.sortActive', _(
        u'If selected, active installers will be sorted to the top of the list.')

    def Execute(self,event):
        BoolLink.Execute(self,event)
        self.gTank.SortItems()

class Installers_SortProjects(BoolLink):
    """Sort dirs to the top."""
    text, key, help = _(u'Projects First'), 'bash.installers.sortProjects', _(
        u'If selected, projects will be sorted to the top of the list.')

    def Execute(self,event):
        BoolLink.Execute(self,event)
        self.gTank.SortItems()

class Installers_SortStructure(BoolLink):
    """Sort by type."""
    text, key = _(u'Sort by Structure'), 'bash.installers.sortStructure'

    def Execute(self,event):
        BoolLink.Execute(self,event)
        self.gTank.SortItems()

#------------------------------------------------------------------------------
# Installers_Skip Links -------------------------------------------------------
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
    """Toggle skipDistantLOD setting and update."""
    text, key = _(u'Skip LOD Textures'), \
                'bash.installers.skipLandscapeLODTextures',

class Installers_SkipLandscapeLODNormals(Installers_Skip):
    """Toggle skipDistantLOD setting and update."""
    text, key = _(u'Skip LOD Normals'), \
                'bash.installers.skipLandscapeLODNormals',

class Installers_SkipOBSEPlugins(Installers_Skip):
    """Toggle allowOBSEPlugins setting and update."""

    text, key = _(u'Skip %s Plugins') % bush.game.se_sd, \
                          'bash.installers.allowOBSEPlugins'

    def AppendToMenu(self,menu,window,data):
        if not bush.game.se_sd: return
        menuItem = BoolLink.AppendToMenu(self,menu,window,data)
        menuItem.Check(not bosh.settings[self.key])
        bosh.installersWindow = self.gTank

class Installers_RenameStrings(AppendableLink, Installers_Skip):
    """Toggle auto-renaming of .STRINGS files"""
    text, key = _(u'Auto-name String Translation Files'), \
                'bash.installers.renameStrings'

    def _append(self, window): return bool(bush.game.esp.stringsFiles)

class Installers_CreateNewProject(_Link):
    """Open the Create New Project Dialog"""
    text = _(u'Create New Project...')
    help = _(u'Create a new project...')

    def Execute(self, event):
        dialog = CreateNewProject()
        dialog.ShowModal()
        dialog.Destroy()

