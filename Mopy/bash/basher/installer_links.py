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

"""Installer*: Menu items for the __item__ menu of the installer tab. Their
window attribute points to the InstallersList singleton. Check before using
BashFrame.iniList - can be None (ini panel not shown).
Installer_Espm_*: Menu items for the Esp/m Filter list in the installer tab.
Their window attribute points to the InstallersPanel singleton.
Installer_Subs_*: Menu items for the Sub-Packages list in the installer tab.
Their window attribute points to the InstallersPanel singleton.
"""

import StringIO
import copy
import re
import webbrowser
from . import settingDefaults, Installers_Link, BashFrame
from .frames import InstallerProject_OmodConfigDialog
from .. import bass, bolt, bosh, bush, balt
from ..bass import Resources
from ..balt import EnabledLink, CheckLink, AppendableLink, OneItemLink, \
    UIList_Rename
from ..belt import InstallerWizard, generateTweakLines
from ..bolt import CancelError, SkipError, GPath, StateError, deprint, \
    SubProgress, LogFile, formatInteger, round_size

__all__ = ['Installer_Open', 'Installer_Duplicate', 'InstallerOpenAt_MainMenu',
           'Installer_OpenSearch', 'Installer_OpenTESA',
           'Installer_Hide', 'Installer_Rename', 'Installer_Refresh',
           'Installer_Move', 'Installer_HasExtraData',
           'Installer_OverrideSkips', 'Installer_SkipVoices',
           'Installer_SkipRefresh', 'Installer_Wizard', 'Installer_EditWizard',
           'Installer_OpenReadme', 'Installer_Anneal', 'Installer_Install',
           'Installer_Uninstall', 'InstallerConverter_MainMenu',
           'InstallerConverter_Create', 'InstallerConverter_ConvertMenu',
           'InstallerProject_Pack', 'InstallerArchive_Unpack',
           'InstallerProject_ReleasePack', 'InstallerProject_Sync',
           'Installer_CopyConflicts', 'InstallerProject_OmodConfig',
           'Installer_ListStructure', 'Installer_Espm_SelectAll',
           'Installer_Espm_DeselectAll', 'Installer_Espm_List',
           'Installer_Espm_Rename', 'Installer_Espm_Reset',
           'Installer_Espm_ResetAll', 'Installer_Subs_SelectAll',
           'Installer_Subs_DeselectAll', 'Installer_Subs_ToggleSelection',
           'Installer_Subs_ListSubPackages', 'Installer_OpenNexus']

#------------------------------------------------------------------------------
# Installer Links -------------------------------------------------------------
#------------------------------------------------------------------------------
class _InstallerLink(Installers_Link, EnabledLink):
    """Common functions for installer links..."""

    def filterInstallables(self):
        return self.idata.filterInstallables(self.selected)

    def hasMarker(self):
        if len(self.selected) > 0:
            for i in self.selected:
                if isinstance(self.idata[i],bosh.InstallerMarker):
                    return True
        return False

    def isSingleProject(self):
        """Indicates whether or not is single project."""
        if len(self.selected) != 1: return False
        else: return isinstance(self.idata[self.selected[0]],
                                bosh.InstallerProject)

    def isSingleArchive(self):
        """Indicates whether or not is single archive."""
        if len(self.selected) != 1: return False
        else: return isinstance(self.idata[self.selected[0]],
                                bosh.InstallerArchive)

    def isSelectedArchives(self):
        """Indicates whether or not selected is all archives."""
        for selected in self.selected:
            if not isinstance(self.idata[selected],
                              bosh.InstallerArchive): return False
        return True


    ##: Methods below should be in an "archives.py"
    def _promptSolidBlockSize(self, title, value=0):
        return self._askNumber(
            _(u'Use what maximum size for each solid block?') + u'\n' + _(
                u"Enter '0' to use 7z's default size."), prompt=u'MB',
            title=title, value=value, min=0, max=102400)

    def _pack(self, archive, installer, project, release=False):
        #--Archive configuration options
        blockSize = None
        if archive.cext in bolt.noSolidExts:
            isSolid = False
        else:
            if not u'-ms=' in bass.inisettings['7zExtraCompressionArguments']:
                isSolid = self._askYes(_(u'Use solid compression for %s?')
                                       % archive.s, default=False)
                if isSolid:
                    blockSize = self._promptSolidBlockSize(title=self.text)
            else:
                isSolid = True
        with balt.Progress(_(u'Packing to Archive...'),
                           u'\n' + u' ' * 60) as progress:
            #--Pack
            installer.packToArchive(project, archive, isSolid, blockSize,
                                    SubProgress(progress, 0, 0.8),
                                    release=release)
            #--Add the new archive to Bash
            if archive not in self.idata:
                self.idata[archive] = bosh.InstallerArchive(archive)
            #--Refresh UI
            iArchive = self.idata[archive]
            iArchive.blockSize = blockSize
            if iArchive.order == -1:
                self.idata.moveArchives([archive], installer.order + 1)
            #--Refresh UI
            self.idata.irefresh(what='I', pending=[archive]) # fullrefresh is unneeded
        self.window.RefreshUI()

    def _askFilename(self, message, filename):
        result = self._askText(message, title=self.dialogTitle,
                               default=filename)
        if not result: return
        archive = GPath(result).tail
        #--Error checking
        if not archive.s:
            self._showWarning(_(u'%s is not a valid archive name.') % result)
            return
        if self.idata.dir.join(archive).isdir():
            self._showWarning(_(u'%s is a directory.') % archive.s)
            return
        if archive.cext not in bolt.writeExts:
            self._showWarning(
                _(u'The %s extension is unsupported. Using %s instead.') % (
                    archive.cext, bolt.defaultExt))
            archive = GPath(archive.sroot + bolt.defaultExt).tail
        if archive in self.idata:
            if not self._askYes(_(u'%s already exists. Overwrite it?') %
                    archive.s, title=self.dialogTitle, default=False): return
        return archive

class _SingleInstallable(OneItemLink, _InstallerLink):

    def _enable(self):
        return super(_SingleInstallable, self)._enable() and bool(
            self.filterInstallables())

class _RefreshingLink(_SingleInstallable):
    _overrides_skips = False

    @balt.conversation
    def Execute(self):
        installer = self.idata[self.selected[0]]
        dest_src = installer.refreshDataSizeCrc()
        with balt.Progress(title=_(u'Override Skips')) as progress:
            if self._overrides_skips:
                self.idata.update_for_overridden_skips(set(dest_src), progress)
            self.idata.irefresh(what='NS', progress=progress)
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class Installer_EditWizard(_SingleInstallable):
    """Edit the wizard.txt associated with this project"""
    help = _(u"Edit the wizard.txt associated with this project.")

    def _initData(self, window, selection):
        super(Installer_EditWizard, self)._initData(window, selection)
        self.text = _(u'View Wizard...') if self.isSingleArchive() else _(
            u'Edit Wizard...')

    def _enable(self):
        return super(Installer_EditWizard, self)._enable() and bool(
            self.idata[self.selected[0]].hasWizard)

    def Execute(self):
        path = self.selected[0]
        if self.isSingleProject():
            # Project, open for edit
            self.idata.dir.join(path.s, self.idata[path].hasWizard).start()
        else:
            # Archive, open for viewing
            archive = self.idata[path]
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

class Installer_Wizard(OneItemLink, _InstallerLink):
    """Runs the install wizard to select subpackages and esp/m filtering"""
    parentWindow = ''
    help = _(u"Run the install wizard.")

    def __init__(self, bAuto):
        super(Installer_Wizard, self).__init__()
        self.bAuto = bAuto
        self.text = _(u'Auto Wizard') if self.bAuto else _(u'Wizard')

    def _enable(self):
        isSingle = super(Installer_Wizard, self)._enable()
        return isSingle and (self.idata[self.selected[0]]).hasWizard != False

    def Execute(self):
        with balt.BusyCursor():
            installer = self.idata[self.selected[0]]
            subs = []
            oldRemaps = copy.copy(installer.remaps)
            installer.remaps = {}
            self.iPanel.refreshCurrent(installer)
            for index in range(self.iPanel.gSubList.GetCount()):
                subs.append(self.iPanel.gSubList.GetString(index))
            saved = bosh.settings['bash.wizard.size']
            default = settingDefaults['bash.wizard.size']
            pos = bosh.settings['bash.wizard.pos']
            # Sanity checks on saved size/position
            if not isinstance(pos,tuple) or len(pos) != 2:
                deprint(_(u'Saved Wizard position (%s) was not a tuple (%s), reverting to default position.') % (pos,type(pos)))
                pos = balt.defPos
            if not isinstance(saved,tuple) or len(saved) != 2:
                deprint(_(u'Saved Wizard size (%s) was not a tuple (%s), reverting to default size.') % (saved, type(saved)))
                pageSize = tuple(default)
            else:
                pageSize = (max(saved[0],default[0]),max(saved[1],default[1]))
            try:
                wizard = InstallerWizard(self.window, self.idata,
                                         self.selected[0], self.bAuto,
                                         self.isSingleArchive(), subs,
                                         pageSize, pos)
            except CancelError:
                return
            balt.ensureDisplayed(wizard)
        ret = wizard.Run()
        # Sanity checks on returned size/position
        if not isinstance(ret.Pos, balt.wxPoint):
            deprint(_(u'Returned Wizard position (%s) was not a wx.Point (%s), reverting to default position.') % (ret.Pos, type(ret.Pos)))
            ret.Pos = balt.defPos
        if not isinstance(ret.PageSize, balt.wxSize):
            deprint(_(u'Returned Wizard size (%s) was not a wx.Size (%s), reverting to default size.') % (ret.PageSize, type(ret.PageSize)))
            ret.PageSize = tuple(default)
        bosh.settings['bash.wizard.size'] = (ret.PageSize[0],ret.PageSize[1])
        bosh.settings['bash.wizard.pos'] = (ret.Pos[0],ret.Pos[1])
        if ret.Canceled:
            installer.remaps = oldRemaps
            self.iPanel.refreshCurrent(installer)
            return
        #Check the sub-packages that were selected by the wizard
        installer.resetAllEspmNames()
        for index in xrange(self.iPanel.gSubList.GetCount()):
            select = installer.subNames[index + 1] in ret.SelectSubPackages
            self.iPanel.gSubList.Check(index, select)
            installer.subActives[index + 1] = select
        self.iPanel.refreshCurrent(installer)
        #Check the espms that were selected by the wizard
        espms = self.iPanel.gEspmList.GetStrings()
        espms = [x.replace(u'&&',u'&') for x in espms]
        installer.espmNots = set()
        for index, espm in enumerate(self.iPanel.espms):
            if espms[index] in ret.SelectEspms:
                self.iPanel.gEspmList.Check(index, True)
            else:
                self.iPanel.gEspmList.Check(index, False)
                installer.espmNots.add(espm)
        self.iPanel.refreshCurrent(installer)
        #Rename the espms that need renaming
        for oldName in ret.RenameEspms:
            installer.setEspmName(oldName, ret.RenameEspms[oldName])
        self.iPanel.refreshCurrent(installer)
        #Install if necessary
        if ret.Install:
            if self.idata[self.selected[0]].isActive: #If it's currently installed, anneal
                title, doIt = _(u'Annealing...'), self.idata.bain_anneal
            else: #Install, if it's not installed
                title, doIt = _(u'Installing...'), self.idata.bain_install
            ui_refresh = [False, False]
            try:
                with balt.Progress(title, u'\n'+u' '*60) as progress:
                    doIt(self.selected, ui_refresh, progress)
            finally:
                self.iPanel.RefreshUIMods(*ui_refresh)
        #Build any ini tweaks
        manuallyApply = []  # List of tweaks the user needs to  manually apply
        lastApplied = None
        for iniFile in ret.IniEdits:
            outFile = bass.dirs['tweaks'].join(u'%s - Wizard Tweak [%s].ini' % (installer.archive, iniFile.sbody))
            with outFile.open('w') as out:
                for line in generateTweakLines(ret.IniEdits[iniFile],iniFile):
                    out.write(line+u'\n')
            bosh.iniInfos.refresh()
            bosh.iniInfos.table.setItem(outFile.tail, 'installer', installer.archive)
            if BashFrame.iniList is not None: BashFrame.iniList.RefreshUI()
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
                    if not self._askContinue(message,
                                             'bash.iniTweaks.continue',
                                             _(u'INI Tweaks')): continue
                if BashFrame.iniList is not None:
                    BashFrame.iniList.panel.AddOrSelectIniDropDown(
                        bass.dirs['mods'].join(iniFile))
                if bosh.iniInfos[outFile.tail] == 20: continue
                bosh.iniInfos.ini.applyTweakFile(outFile)
                lastApplied = outFile.tail
            else:
                # We wont automatically apply tweaks to anything other than Oblivion.ini or an ini from
                # this installer
                manuallyApply.append((outFile,iniFile))
        #--Refresh after all the tweaks are applied
        if lastApplied is not None and BashFrame.iniList is not None:
            BashFrame.iniList.RefreshUIValid()
            BashFrame.iniList.panel.iniContents.RefreshIniContents()
            BashFrame.iniList.panel.tweakContents.RefreshTweakLineCtrl(lastApplied)
        if len(manuallyApply) > 0:
            message = balt.fill(_(u'The following INI Tweaks were not automatically applied.  Be sure to apply them after installing the package.'))
            message += u'\n\n'
            message += u'\n'.join([u' * ' + x[0].stail + u'\n   TO: ' + x[1].s for x in manuallyApply])
            self._showInfo(message)

class Installer_OpenReadme(OneItemLink, _InstallerLink):
    """Opens the installer's readme if BAIN can find one."""
    text = _(u'Open Readme')
    help = _(u"Open the installer's readme if BAIN can find one")

    def _enable(self):
        isSingle = super(Installer_OpenReadme, self)._enable()
        return isSingle and bool(self.idata[self.selected[0]].hasReadme)

    def Execute(self):
        installer = self.selected[0]
        if self.isSingleProject():
            # Project, open for edit
            self.idata.dir.join(installer.s, self.idata[installer].hasReadme).start()
        else:
            # Archive, open for viewing
            archive = self.idata[installer]
            with balt.BusyCursor():
                # This is going to leave junk temp files behind...
                archive.unpackToTemp(installer, [archive.hasReadme])
            archive.getTempDir().join(archive.hasReadme).start()

#------------------------------------------------------------------------------
class Installer_Anneal(_InstallerLink):
    """Anneal all packages."""
    text = _(u'Anneal')
    help = _(u"Anneal all packages.")

    def _enable(self): return bool(self.filterInstallables())

    def Execute(self):
        ui_refresh = [False, False]
        try:
            with balt.Progress(_(u"Annealing..."),u'\n'+u' '*60) as progress:
                self.idata.bain_anneal(self.filterInstallables(), ui_refresh,
                                       progress)
        except (CancelError,SkipError):
            pass
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

class Installer_Duplicate(OneItemLink, _InstallerLink):
    """Duplicate selected Installer."""
    text = _(u'Duplicate...')

    def _initData(self, window, selection):
        super(Installer_Duplicate, self)._initData(window, selection)
        self.help = _(u"Duplicate selected %(installername)s.") % (
            {'installername': self.selected[0]})

    def _enable(self):
        isSingle = super(Installer_Duplicate, self)._enable()
        return isSingle and not isinstance(self.idata[self.selected[0]],
                                           bosh.InstallerMarker)

    def Execute(self):
        """Duplicate selected Installer."""
        curName = self.selected[0]
        isdir = self.idata.dir.join(curName).isdir()
        if isdir: root,ext = curName,u''
        else: root,ext = curName.rootExt
        newName = self.window.new_name(root + _(u' Copy') + ext)
        result = self._askText(_(u"Duplicate %s to:") % curName.s,
                               default=newName.s)
        if not result: return
        #--Error checking
        newName = GPath(result).tail
        if not newName.s:
            self._showWarning(_(u"%s is not a valid name.") % result)
            return
        if newName in self.idata:
            self._showWarning(_(u"%s already exists.") % newName.s)
            return
        if self.idata.dir.join(curName).isfile() and curName.cext != newName.cext:
            self._showWarning(_(u"%s does not have correct extension (%s).")
                              % (newName.s,curName.ext))
            return
        #--Duplicate
        with balt.BusyCursor():
            self.idata.copy_installer(curName,newName)
            self.idata.irefresh(what='N')
            self.window.RefreshUI()

class Installer_Hide(_InstallerLink):
    """Hide selected Installers."""
    text = _(u'Hide...')
    help = _(
        u"Hide selected installer(s). No installer markers should be selected")

    def _enable(self):
        for item in self.selected:
            if isinstance(self.idata[item],bosh.InstallerMarker):
                return False
        return True

    def Execute(self):
        """Handle selection."""
        if not bass.inisettings['SkipHideConfirmation']:
            message = _(u'Hide these files? Note that hidden files are simply moved to the Bash\\Hidden subdirectory.')
            if not self._askYes(message, _(u'Hide Files')): return
        destDir = bass.dirs['modsBash'].join(u'Hidden')
        for curName in self.selected:
            newName = destDir.join(curName)
            if newName.exists():
                message = (_(u'A file named %s already exists in the hidden files directory. Overwrite it?')
                    % newName.stail)
                if not self._askYes(message, _(u'Hide Files')): return
            #Move
            with balt.BusyCursor():
                file = bass.dirs['installers'].join(curName)
                file.moveTo(newName)
        self.idata.irefresh(what='ION')
        self.window.RefreshUI()

class Installer_Rename(UIList_Rename, _InstallerLink):
    """Renames files by pattern."""
    help = _(u"Rename selected installer(s).")

    def _enable(self):
        ##Only enable if all selected items are of the same type
        firstItem = self.idata[self.selected[0]]
        if isinstance(firstItem,bosh.InstallerMarker):
            installer_type = bosh.InstallerMarker
        elif isinstance(firstItem,bosh.InstallerArchive):
            installer_type = bosh.InstallerArchive
        elif isinstance(firstItem,bosh.InstallerProject):
            installer_type = bosh.InstallerProject
        else: return False
        for item in self.selected:
            if not isinstance(self.idata[item], installer_type):
                return False
        return True

class Installer_HasExtraData(CheckLink, _RefreshingLink):
    """Toggle hasExtraData flag on installer."""
    text = _(u'Has Extra Directories')
    help = _(u"Allow installation of files in non-standard directories.")

    def _check(self): return self._enable() and (
        self.idata[self.selected[0]]).hasExtraData

    def Execute(self):
        """Toggle hasExtraData installer attribute"""
        self.idata[self.selected[0]].hasExtraData ^= True
        super(Installer_HasExtraData, self).Execute()

class Installer_OverrideSkips(CheckLink, _RefreshingLink):
    """Toggle overrideSkips flag on installer."""
    text = _(u'Override Skips')

    def _initData(self, window, selection):
        super(Installer_OverrideSkips, self)._initData(window, selection)
        self.help = _(
            u"Override global file type skipping for %(installername)s.") % (
                    {'installername': self.selected[0]}) + u'  '+ _(u'BETA!')

    def _check(self): return self._enable() and (
        self.idata[self.selected[0]]).overrideSkips

    def Execute(self):
        self.idata[self.selected[0]].overrideSkips ^= True
        self._overrides_skips = self.idata[self.selected[0]].overrideSkips
        super(Installer_OverrideSkips, self).Execute()

class Installer_SkipRefresh(CheckLink, _InstallerLink):
    """Toggle skipRefresh flag on project."""
    text = _(u"Don't Refresh")
    help = _(u"Don't automatically refresh project.")

    def _enable(self): return self.isSingleProject()

    def _check(self): return self.isSingleProject() and (
        self.idata[self.selected[0]]).skipRefresh

    def Execute(self):
        """Toggle skipRefresh project attribute and refresh the project if
        skipRefresh is set to False."""
        installer = self.idata[self.selected[0]]
        installer.skipRefresh ^= True
        if not installer.skipRefresh:
            installer.refreshBasic(
                bass.dirs['installers'].join(installer.archive), progress=None,
                recalculate_project_crc=False)
            installer.refreshStatus(self.idata)
            self.idata.irefresh(what='N')
            self.window.RefreshUI()

class Installer_Install(_InstallerLink):
    """Install selected packages."""
    mode_title = {'DEFAULT': _(u'Install'), 'LAST': _(u'Install Last'),
                  'MISSING': _(u'Install Missing')}

    def __init__(self,mode='DEFAULT'):
        super(Installer_Install, self).__init__()
        self.mode = mode
        self.text = self.mode_title[self.mode]

    def _enable(self): return len(self.filterInstallables())

    @balt.conversation
    def Execute(self):
        ui_refresh = [False, False]
        try:
            with balt.Progress(_(u'Installing...'),u'\n'+u' '*60) as progress:
                last = (self.mode == 'LAST')
                override = (self.mode != 'MISSING')
                try:
                    tweaks = self.idata.bain_install(self.filterInstallables(),
                        ui_refresh, progress, last, override)
                    ui_refresh[1] |= bool(tweaks)
                except (CancelError,SkipError):
                    pass
                except StateError as e:
                    self._showError(u'%s'%e)
                else: # no error occurred
                    if tweaks:
                        msg = _(u'The following INI Tweaks were created, '
                                u'because the existing INI was different than '
                                u'what BAIN installed:') + u'\n' + u'\n'.join(
                                [u' * %s\n' % x.stail for (x, y) in tweaks])
                        self._showInfo(msg, title=_(u'INI Tweaks'))
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

class Installer_ListStructure(OneItemLink, _InstallerLink): # Provided by Waruddar
    """Copies folder structure of installer to clipboard."""
    text = _(u"List Structure...")

    def _enable(self):
        isSingle = super(Installer_ListStructure, self)._enable()
        return isSingle and not isinstance(self.idata[self.selected[0]],
                                                  bosh.InstallerMarker)

    def Execute(self):
        archive = self.selected[0]
        installer = self.idata[archive]
        text = installer.listSource(archive)
        #--Get masters list
        balt.copyToClipboard(text)
        self._showLog(text, title=_(u'Package Structure'), fixedFont=False,
                      icons=Resources.bashBlue)

class Installer_Move(_InstallerLink):
    """Moves selected installers to desired spot."""
    text = _(u'Move To...')

    def Execute(self):
        """Handle selection."""
        curPos = min(self.idata[x].order for x in self.selected)
        message = (_(u'Move selected archives to what position?')
                   + u'\n' +
                   _(u'Enter position number.')
                   + u'\n' +
                   _(u'Last: -1; First of Last: -2; Semi-Last: -3.')
                   )
        newPos = self._askText(message, default=unicode(curPos))
        if not newPos: return
        try:
            newPos = int(newPos)
        except ValueError:
            self._showError(_(u'Position must be an integer.'))
            return
        if newPos == -3: newPos = self.idata[self.idata.lastKey].order
        elif newPos == -2: newPos = self.idata[self.idata.lastKey].order+1
        elif newPos < 0: newPos = len(self.idata.data)
        self.idata.moveArchives(self.selected,newPos)
        self.idata.irefresh(what='N')
        self.window.RefreshUI()

class Installer_Open(_InstallerLink):
    """Open selected file(s)."""
    text = _(u'Open...')

    def _initData(self, window, selection):
        super(Installer_Open, self)._initData(window, selection)
        self.help = _(u"Open '%s'") % selection[0] if len(selection) == 1 \
            else _(u"Open selected files.")
        self.selected = [x for x in self.selected if
                         not isinstance(self.idata[x], bosh.InstallerMarker)]

    def _enable(self): return bool(self.selected)

    def Execute(self): self.window.OpenSelected(selected=self.selected)

#------------------------------------------------------------------------------
class _Installer_OpenAt(_InstallerLink):
    group = 2  # the regexp group we are interested in (2 is id, 1 is modname)

    def _enable(self):
        x = self.__class__.regexp.search(self.selected[0].s)
        if not bool(self.isSingleArchive() and x): return False
        self.mod_url_id = x.group(self.__class__.group)
        return bool(self.mod_url_id)

    def _url(self): return self.__class__.baseUrl + self.mod_url_id

    def Execute(self):
        if self._askContinue(self.message, self.key, self.askTitle):
            webbrowser.open(self._url())

class Installer_OpenNexus(AppendableLink, _Installer_OpenAt):
    regexp = bosh.reTesNexus
    text = _(bush.game.nexusName)
    message = _(
        u"Attempt to open this as a mod at %(nexusName)s? This assumes that "
        u"the trailing digits in the package's name are actually the id "
        u"number of the mod at %(nexusName)s. If this assumption is wrong, "
        u"you'll just get a random mod page (or error notice) at %("
        u"nexusName)s.") % {'nexusName': bush.game.nexusName}
    key = bush.game.nexusKey
    askTitle = _(u'Open at %(nexusName)s') % {'nexusName':bush.game.nexusName}
    baseUrl = bush.game.nexusUrl + u'mods/'

    def _append(self, window): return bool(bush.game.nexusUrl)

class Installer_OpenSearch(_Installer_OpenAt):
    group = 1
    regexp = bosh.reTesNexus
    text = _(u'Google...')
    key = 'bash.installers.opensearch.continue'
    askTitle = _(u'Open a search')
    message = _(u"Open a search for this on Google?")

    def _url(self):
        return u'http://www.google.com/search?hl=en&q=' + u'+'.join(
            re.split(ur'\W+|_+', self.mod_url_id))

class Installer_OpenTESA(_Installer_OpenAt):
    regexp = bosh.reTESA
    text = _(u'TES Alliance...')
    key = 'bash.installers.openTESA.continue'
    askTitle = _(u'Open at TES Alliance')
    message = _(
        u"Attempt to open this as a mod at TES Alliance? This assumes that "
        u"the trailing digits in the package's name are actually the id "
        u"number of the mod at TES Alliance. If this assumption is wrong, "
        u"you'll just get a random mod page (or error notice) at TES "
        u"Alliance.")
    baseUrl =u'http://tesalliance.org/forums/index.php?app=downloads&showfile='

#------------------------------------------------------------------------------
class Installer_Refresh(_InstallerLink):
    """Rescans selected Installers."""
    text = _(u'Refresh')
    help = _(u'Rescan selected Installer(s)') + u'.  ' + _(
        u'Ignores skip refresh flag on projects')

    def __init__(self, calculate_projects_crc=True):
        super(Installer_Refresh, self).__init__()
        self.calculate_projects_crc = calculate_projects_crc
        if not calculate_projects_crc:
            self.text = _(u'Quick Refresh')
            self.help = _(u'Rescan selected Installer(s)') + u'.  ' + _(
                u'Ignores skip refresh flag on projects') + u'.  ' + _(
            u'Will not recalculate cached crcs of files in a project')

    def _enable(self): return bool(self.filterInstallables())

    @balt.conversation
    def Execute(self):
        toRefresh = set((x, self.idata[x]) for x in self.selected)
        self.window.rescanInstallers(toRefresh, abort=True,
                            calculate_projects_crc=self.calculate_projects_crc)

class Installer_SkipVoices(CheckLink, _RefreshingLink):
    """Toggle skipVoices flag on installer."""
    text = _(u'Skip Voices')

    def _initData(self, window, selection):
        super(Installer_SkipVoices, self)._initData(window, selection)
        self.help = _(u"Skip over any voice files in %(installername)s") % (
                    {'installername': self.selected[0]})

    def _check(self): return self._enable() and (
        self.idata[self.selected[0]]).skipVoices

    def Execute(self):
        self.idata[self.selected[0]].skipVoices ^= True
        super(Installer_SkipVoices, self).Execute()

class Installer_Uninstall(_InstallerLink):
    """Uninstall selected Installers."""
    text = _(u'Uninstall')
    help = _(u'Uninstall selected Installer(s)')

    def _enable(self): return len(self.filterInstallables())

    @balt.conversation
    def Execute(self):
        """Uninstall selected Installers."""
        ui_refresh = [False, False]
        try:
            with balt.Progress(_(u"Uninstalling..."),u'\n'+u' '*60) as progress:
                self.idata.bain_uninstall(self.filterInstallables(),
                                          ui_refresh, progress)
        except (CancelError,SkipError): # now where could this be raised from ?
            pass
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

class Installer_CopyConflicts(_SingleInstallable):
    """For Modders only - copy conflicts to a new project."""
    text = _(u'Copy Conflicts to Project')
    help = _(u'Copy all files that conflict with the selected installer into a'
             u' new project')

    def Execute(self):
        """Handle selection."""
        idata = self.idata # bosh.InstallersData instance (dict bolt.Path ->
        # InstallerArchive)
        installers_dir = idata.dir
        srcConflicts = set()
        packConflicts = []
        with balt.Progress(_(u"Copying Conflicts..."),
                           u'\n' + u' ' * 60) as progress:
            srcArchive = self.selected[0]
            srcInstaller = idata[srcArchive]
            src_sizeCrc = srcInstaller.data_sizeCrc # dictionary Path
            mismatched = set(src_sizeCrc) # just a set of bolt.Path of the src
            # installer files
            if mismatched:
                numFiles = 0
                curFile = 1
                srcOrder = srcInstaller.order
                destDir = GPath(u"%03d - Conflicts" % srcOrder)
                getArchiveOrder = lambda tup: tup[1].order
                for package, installer in sorted(idata.iteritems(),
                                                 key=getArchiveOrder):
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
                if numFiles: # there are conflicting files
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
                            installer.unpackToTemp(package, curConflicts,
                                SubProgress(progress, curFile,
                                    curFile + len(curConflicts), numFiles))
                            installer.getTempDir().moveTo(
                                installers_dir.join(destDir,GPath(
                                    u"%03d - %s" % (order,package.s))))
                            curFile += len(curConflicts)
                    project = destDir.root
                    if project not in idata:
                        idata[project] = bosh.InstallerProject(project)
                    iProject = idata[project] #bash.bosh.InstallerProject object
                    pProject = installers_dir.join(project) # bolt.Path
                    # ...\Bash Installers\030 - Conflicts
                    iProject.refreshBasic(pProject, progress=None)
                    if iProject.order == -1:
                        idata.moveArchives([project],srcInstaller.order + 1)
                    idata.irefresh(what='NS')
        self.window.RefreshUI()

#------------------------------------------------------------------------------
# InstallerDetails Espm Links -------------------------------------------------
#------------------------------------------------------------------------------
class Installer_Espm_SelectAll(EnabledLink):
    """Select All Esp/ms in installer for installation."""
    text = _(u'Select All')

    def _enable(self): return len(self.window.espms) != 0

    def Execute(self):
        """Handle selection."""
        installer = self.window.GetDetailsItem()
        installer.espmNots = set()
        for i in range(len(self.window.espms)):
            self.window.gEspmList.Check(i, True)
        self.window.refreshCurrent(installer)

class Installer_Espm_DeselectAll(EnabledLink):
    """Deselect All Esp/ms in installer for installation."""
    text = _(u'Deselect All')

    def _enable(self): return len(self.window.espms) != 0

    def Execute(self):
        """Handle selection."""
        installer = self.window.GetDetailsItem()
        espmNots = installer.espmNots = set()
        for i in range(len(self.window.espms)):
            self.window.gEspmList.Check(i, False)
            espm =GPath(self.window.gEspmList.GetString(i).replace(u'&&',u'&'))
            espmNots.add(espm)
        self.window.refreshCurrent(installer)

class Installer_Espm_Rename(EnabledLink):
    """Changes the installed name for an Esp/m."""
    text = _(u'Rename...')

    def _enable(self): return self.selected != -1

    def Execute(self):
        """Handle selection."""
        installer = self.window.GetDetailsItem()
        curName = self.window.gEspmList.GetString(self.selected).replace(u'&&',
                                                                         u'&')
        if curName[0] == u'*':
            curName = curName[1:]
        _file = GPath(curName)
        newName = self._askText(_(u"Enter new name (without the extension):"),
                                title=_(u"Rename Esp/m"), default=_file.sbody)
        if not newName: return
        if newName in self.window.espms: return
        installer.setEspmName(curName, newName + _file.cext)
        self.window.refreshCurrent(installer)

class Installer_Espm_Reset(EnabledLink):
    """Resets the installed name for an Esp/m."""
    text = _(u'Reset Name')

    def _enable(self):
        if self.selected == -1: return False
        self.installer = installer = self.window.GetDetailsItem()
        curName = self.window.gEspmList.GetString(self.selected).replace(u'&&',
                                                                         u'&')
        if curName[0] == u'*': curName = curName[1:]
        self.curName = curName
        return installer.isEspmRenamed(curName)

    def Execute(self):
        """Handle selection."""
        self.installer.resetEspmName(self.curName)
        self.window.refreshCurrent(self.installer)

class Installer_Espm_ResetAll(EnabledLink):
    """Resets all renamed Esp/ms."""
    text = _(u'Reset All Names')

    def _enable(self): return len(self.window.espms) != 0

    def Execute(self):
        """Handle selection."""
        installer = self.window.GetDetailsItem()
        installer.resetAllEspmNames()
        self.window.refreshCurrent(installer)

class Installer_Espm_List(EnabledLink):
    """Lists all Esp/ms in installer for user information/w/e."""
    text = _(u'List Esp/ms')

    def _enable(self): return len(self.window.espms) != 0

    def Execute(self):
        """Handle selection."""
        subs = _(u'Esp/m List for %s:') % self.window.GetDetailsItem(
                    ).archive + u'\n[spoiler]\n'
        espm_list = self.window.gEspmList
        for index in range(espm_list.GetCount()):
            subs += [u'   ',u'** '][espm_list.IsChecked(index)] + \
                    espm_list.GetString(index) + '\n'
        subs += u'[/spoiler]'
        balt.copyToClipboard(subs)
        self._showLog(subs, title=_(u'Esp/m List'), fixedFont=False,
                      icons=Resources.bashBlue)

#------------------------------------------------------------------------------
# InstallerDetails Subpackage Links -------------------------------------------
#------------------------------------------------------------------------------
class _Installer_Subs(EnabledLink):
    def _enable(self): return self.window.gSubList.GetCount() > 1

class Installer_Subs_SelectAll(_Installer_Subs):
    """Select All sub-packages in installer for installation."""
    text = _(u'Select All')

    def Execute(self):
        """Handle selection."""
        installer = self.window.GetDetailsItem()
        for index in xrange(self.window.gSubList.GetCount()):
            self.window.gSubList.Check(index, True)
            installer.subActives[index + 1] = True
        self.window.refreshCurrent(installer)

class Installer_Subs_DeselectAll(_Installer_Subs):
    """Deselect All sub-packages in installer for installation."""
    text = _(u'Deselect All')

    def Execute(self):
        """Handle selection."""
        installer = self.window.GetDetailsItem()
        for index in xrange(self.window.gSubList.GetCount()):
            self.window.gSubList.Check(index, False)
            installer.subActives[index + 1] = False
        self.window.refreshCurrent(installer)

class Installer_Subs_ToggleSelection(_Installer_Subs):
    """Toggles selection state of all sub-packages in installer for
    installation."""
    text = _(u'Toggle Selection')

    def Execute(self):
        """Handle selection."""
        installer = self.window.GetDetailsItem()
        for index in xrange(self.window.gSubList.GetCount()):
            check = not installer.subActives[index+1]
            self.window.gSubList.Check(index, check)
            installer.subActives[index + 1] = check
        self.window.refreshCurrent(installer)

class Installer_Subs_ListSubPackages(_Installer_Subs):
    """Lists all sub-packages in installer for user information/w/e."""
    text = _(u'List Sub-packages')

    def Execute(self):
        """Handle selection."""
        installer = self.window.GetDetailsItem()
        subs = _(u'Sub-Packages List for %s:') % installer.archive
        subs += u'\n[spoiler]\n'
        for index in xrange(self.window.gSubList.GetCount()):
            subs += [u'   ', u'** '][self.window.gSubList.IsChecked(
                index)] + self.window.gSubList.GetString(index) + u'\n'
        subs += u'[/spoiler]'
        balt.copyToClipboard(subs)
        self._showLog(subs, title=_(u'Sub-Package Lists'), fixedFont=False,
                      icons=Resources.bashBlue)

#------------------------------------------------------------------------------
# InstallerArchive Links ------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerArchive_Unpack(AppendableLink, _InstallerLink):
    """Unpack installer package(s) to Project(s)."""
    text = _(u'Unpack to Project(s)...')
    help = _(u'Unpack installer package(s) to Project(s)')

    def _append(self, window):
        self.selected = window.GetSelected() # append runs before _initData
        self.window = window # and the idata access is via self.window
        return self.isSelectedArchives()

    def Execute(self):
        #--Copy to Build
        with balt.Progress(_(u"Unpacking to Project..."),u'\n'+u' '*60) as progress:
            for archive in self.selected:
                installer = self.idata[archive]
                project = archive.root
                if self.isSingleArchive():
                    result = self._askText(_(u"Unpack %s to Project:") % archive.s,
                                           default=project.s)
                    if not result: return
                    #--Error checking
                    project = GPath(result).tail
                    if not project.s or project.cext in bolt.readExts:
                        self._showWarning(_(u"%s is not a valid project name.") % result)
                        return
                    if self.idata.dir.join(project).isfile():
                        self._showWarning(_(u"%s is a file.") % project.s)
                        return
                if project in self.idata:
                    if not self._askYes(
                        _(u"%s already exists. Overwrite it?") % project.s,
                        default=False): continue
                installer.unpackToProject(archive,project,SubProgress(progress,0,0.8))
                self._create_project(installer, progress, project)
            self.idata.irefresh(what='NS')
            self.window.RefreshUI()

    def _create_project(self, installer, progress, project):
        if project not in self.idata:
            self.idata[project] = bosh.InstallerProject(project)
        iProject = self.idata[project]
        pProject = bass.dirs['installers'].join(project)
        iProject.refreshBasic(pProject, SubProgress(progress, 0.8, 0.99))
        if iProject.order == -1:
            self.idata.moveArchives([project], installer.order + 1)

#------------------------------------------------------------------------------
# InstallerProject Links ------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerProject_OmodConfig(_InstallerLink):
    """Projects only. Allows you to read/write omod configuration info."""
    text = _(u'Omod Info...')
    help = _(u'Projects only. Allows you to read/write omod configuration info')

    def _enable(self): return self.isSingleProject()

    def Execute(self):
        project = self.selected[0]
        (InstallerProject_OmodConfigDialog(self.window, self.idata,
                                           project)).Show()

#------------------------------------------------------------------------------
class InstallerProject_Sync(_InstallerLink):
    """Synchronize the project with files from the Data directory."""
    text = _(u'Sync from Data')
    help = _(u'Synchronize the project with files from the Data directory')

    def _enable(self):
        if not self.isSingleProject(): return False
        project = self.selected[0]
        installer = self.idata[project]
        return bool(installer.missingFiles or installer.mismatchedFiles)

    def Execute(self):
        project = self.selected[0]
        installer = self.idata[project]
        missing = installer.missingFiles
        mismatched = installer.mismatchedFiles
        message = (_(u'Update %s according to data directory?') + u'\n' +
                   _(u'Files to delete:') + u'%d\n' +
                   _(u'Files to update:') + u'%d') % (
                        project.s, len(missing), len(mismatched))
        if not self._askWarning(message, title=self.text): return
        #--Sync it, baby!
        with balt.Progress(self.text, u'\n' + u' ' * 60) as progress:
            progress(0.1,_(u'Updating files.'))
            installer.syncToData(project,missing|mismatched)
            pProject = bass.dirs['installers'].join(project)
            installer.refreshBasic(pProject, SubProgress(progress, 0.1, 0.99))
            self.idata.irefresh(what='NS')
            self.window.RefreshUI()

#------------------------------------------------------------------------------
class InstallerProject_Pack(_InstallerLink):
    """Pack project to an archive."""
    text = dialogTitle = _(u'Pack to Archive...')
    help = _(u'Pack project to an archive')
    release = False

    def _enable(self): return self.isSingleProject()

    @balt.conversation
    def Execute(self):
        #--Generate default filename from the project name and the default extension
        project = self.selected[0]
        installer = self.idata[project]
        archive = GPath(project.s + bolt.defaultExt)
        #--Confirm operation
        archive = self._askFilename(
            message=_(u'Pack %s to Archive:') % project.s, filename=archive.s)
        if not archive: return
        self._pack(archive, installer, project, release=self.__class__.release)

#------------------------------------------------------------------------------
class InstallerProject_ReleasePack(InstallerProject_Pack):
    """Pack project to an archive for release. Ignores dev files/folders."""
    text = _(u'Package for Release...')
    help = _(
        u'Pack project to an archive for release. Ignores dev files/folders')
    release = True

#------------------------------------------------------------------------------
class InstallerConverter_Apply(_InstallerLink):
    """Apply a Bain Conversion File."""
    dialogTitle = _(u'Apply BCF...') # title used in dialog

    def __init__(self,converter,numAsterisks):
        super(InstallerConverter_Apply, self).__init__()
        self.converter = converter
        #--Add asterisks to indicate the number of unselected archives that the BCF uses
        self.dispName = u''.join((self.converter.fullPath.sbody,u'*' * numAsterisks))
        self.text = self.dispName

    @balt.conversation
    def Execute(self):
        #--Generate default filename from BCF filename
        defaultFilename = self.converter.fullPath.sbody[:-4] + bolt.defaultExt
        #--List source archives
        message = _(u'Using:') + u'\n* ' + u'\n* '.join(sorted(
            u'(%08X) - %s' % (x, self.idata.crc_installer[x].archive) for x in
            self.converter.srcCRCs)) + u'\n'
        #--Ask for an output filename
        destArchive = self._askFilename(message, filename=defaultFilename)
        if not destArchive: return
        with balt.Progress(_(u'Converting to Archive...'),u'\n'+u' '*60) as progress:
            #--Perform the conversion
            msg = u'%s: ' % destArchive.s + _(
                u'An error occurred while applying an Auto-BCF.')
            new_archive_order = self.idata[self.selected[-1]].order + 1
            try:
                self.idata.apply_converter(self.converter, destArchive,
                    progress, msg, show_warning=self._showWarning,
                    position=new_archive_order)
            except StateError:
                return
        self.window.RefreshUI()

#------------------------------------------------------------------------------
class InstallerConverter_ApplyEmbedded(_InstallerLink):
    text = _(u'Embedded BCF')
    dialogTitle = _(u'Apply BCF...')

    @balt.conversation
    def Execute(self):
        name = self.selected[0]
        archive = self.idata[name]
        #--Ask for an output filename
        dest = self._askFilename(_(u'Output file:'), filename=name.stail)
        if not dest: return
        with balt.Progress(_(u'Extracting BCF...'),u'\n'+u' '*60) as progress:
            destinations, converted = self.idata.applyEmbeddedBCFs(
                [archive], [dest], progress)
            if not destinations: return # destinations == [dest] if all was ok
        self.window.RefreshUI()

class InstallerConverter_Create(_InstallerLink):
    """Create BAIN conversion file."""
    dialogTitle = _(u'Create BCF...') # title used in dialog
    text = _(u'Create...')

    def Execute(self):
        #--Generate allowable targets
        readTypes = u'*%s' % u';*'.join(bolt.readExts)
        #--Select target archive
        destArchive = self._askOpen(title=_(u"Select the BAIN'ed Archive:"),
                                    defaultDir=self.idata.dir,
                                    wildcard=readTypes, mustExist=True)
        if not destArchive: return
        #--Error Checking
        BCFArchive = destArchive = destArchive.tail
        if not destArchive.s or destArchive.cext not in bolt.readExts:
            self._showWarning(_(u'%s is not a valid archive name.') % destArchive.s)
            return
        if destArchive not in self.idata:
            self._showWarning(_(u'%s must be in the Bash Installers directory.') % destArchive.s)
            return
        if BCFArchive.csbody[-4:] != u'-bcf':
            BCFArchive = GPath(BCFArchive.sbody + u'-BCF' + bolt.defaultExt).tail
        #--List source archives and target archive
        message = _(u'Convert:')
        message += u'\n* ' + u'\n* '.join(sorted(u'(%08X) - %s' % (self.idata[x].crc,x.s) for x in self.selected))
        message += (u'\n\n'+_(u'To:')+u'\n* (%08X) - %s') % (self.idata[destArchive].crc,destArchive.s) + u'\n'
        #--Confirm operation
        result = self._askText(message, title=self.dialogTitle,
                               default=BCFArchive.s)
        if not result: return
        #--Error checking
        BCFArchive = GPath(result).tail
        if not BCFArchive.s:
            self._showWarning(_(u'%s is not a valid archive name.') % result)
            return
        if BCFArchive.csbody[-4:] != u'-bcf':
            BCFArchive = GPath(BCFArchive.sbody + u'-BCF' + BCFArchive.cext).tail
        if BCFArchive.cext != bolt.defaultExt:
            self._showWarning(_(u"BCF's only support %s. The %s extension will"
                      u" be discarded.") % (bolt.defaultExt, BCFArchive.cext))
            BCFArchive = GPath(BCFArchive.sbody + bolt.defaultExt).tail
        if bass.dirs['converters'].join(BCFArchive).exists():
            if not self._askYes(_(
                    u'%s already exists. Overwrite it?') % BCFArchive.s,
                                title=self.dialogTitle, default=False): return
            #--It is safe to removeConverter, even if the converter isn't overwritten or removed
            #--It will be picked back up by the next refresh.
            self.idata.converters_data.removeConverter(BCFArchive)
        destInstaller = self.idata[destArchive]
        blockSize = None
        if destInstaller.isSolid:
            blockSize = self._promptSolidBlockSize(
                title=self.dialogTitle, value=destInstaller.blockSize or 0)
        progress = balt.Progress(_(u'Creating %s...') % BCFArchive.s,u'\n'+u' '*60)
        log = None
        try:
            #--Create the converter
            converter = bosh.converters.InstallerConverter(self.selected,
                    self.idata, destArchive, BCFArchive, blockSize, progress)
            #--Add the converter to Bash
            self.idata.converters_data.addConverter(converter)
            #--Refresh UI
            self.idata.irefresh(what='C')
            #--Generate log
            log = LogFile(StringIO.StringIO())
            log.setHeader(u'== '+_(u'Overview')+u'\n')
##            log('{{CSS:wtxt_sand_small.css}}')
            log(u'. '+_(u'Name')+u': '+BCFArchive.s)
            log(u'. '+_(u'Size')+u': %s'% round_size(converter.fullPath.size))
            log(u'. '+_(u'Remapped')+u': %s'%formatInteger(len(converter.convertedFiles))+(_(u'file'),_(u'files'))[len(converter.convertedFiles) > 1])
            log.setHeader(u'. '+_(u'Requires')+u': %s'%formatInteger(len(converter.srcCRCs))+(_(u'file'),_(u'files'))[len(converter.srcCRCs) > 1])
            log(u'  * '+u'\n  * '.join(sorted(u'(%08X) - %s' % (x, self.idata.crc_installer[x].archive) for x in converter.srcCRCs if x in self.idata.crc_installer)))
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
                self._showLog(log.out.getvalue(), title=_(u'BCF Information'))

#------------------------------------------------------------------------------
# Installer Submenus ----------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerOpenAt_MainMenu(balt.MenuLink):
    """Main Open At Menu"""
    text = _(u"Open at")
    def _enable(self):
        return super(InstallerOpenAt_MainMenu, self)._enable() and isinstance(
            self.window.data[self.selected[0]], bosh.InstallerArchive)

class InstallerConverter_ConvertMenu(balt.MenuLink):
    """Apply BCF SubMenu."""
    text = _(u"Apply")
    def _enable(self): # TODO(ut) untested for multiple selections
        """Return False to disable the converter menu, otherwise populate its
        links attribute and return True."""
        linkSet = set()
        del self.links[:]
        #--Converters are linked by CRC, not archive name
        #--So, first get all the selected archive CRCs
        selected = self.selected
        idata = self.window.data # InstallersData singleton
        selectedCRCs = set(idata[archive].crc for archive in selected)
        crcInstallers = set(idata.crc_installer)
        srcCRCs = set(idata.converters_data.srcCRC_converters)
        #--There is no point in testing each converter unless
        #--every selected archive has an associated converter
        if selectedCRCs <= srcCRCs:
            #--Test every converter for every selected archive
            #--Only add a link to the converter if it uses all selected archives,
            #--and all of its required archives are available (but not necessarily selected)
            linkSet = set( #--List comprehension is faster than unrolling the for loops, but readability suffers
                [converter for installerCRC in selectedCRCs for converter in
                 idata.converters_data.srcCRC_converters[installerCRC] if
                 selectedCRCs <= converter.srcCRCs <= crcInstallers])
##            for installerCRC in selectedCRCs:
##                for converter in window.data.srcCRC_converters[installerCRC]:
##                    if selectedCRCs <= converter.srcCRCs <= set(window.data.crc_installer): linkSet.add(converter)
        #--If the archive is a single archive with an embedded BCF, add that
        if len(selected) == 1 and idata[selected[0]].hasBCF:
            self.links.append(InstallerConverter_ApplyEmbedded())
        #--Disable the menu if there were no valid converters found
        elif not linkSet:
            return False
        #--Otherwise add each link in alphabetical order, and
        #--indicate the number of additional, unselected archives
        #--that the converter requires
        for converter in sorted(linkSet,key=lambda x: x.fullPath.stail.lower()):
            numAsterisks = len(converter.srcCRCs - selectedCRCs)
            self.links.append(InstallerConverter_Apply(converter, numAsterisks))
        return True

class InstallerConverter_MainMenu(balt.MenuLink):
    """Main BCF Menu"""
    text = _(u"Conversions")
    def _enable(self):
        for item in self.selected:
            if not isinstance(self.window.data[item], bosh.InstallerArchive):
                return False
        return True
