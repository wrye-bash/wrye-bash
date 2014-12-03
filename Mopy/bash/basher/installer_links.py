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
import StringIO
import copy
import re
import webbrowser
import wx
from . import settingDefaults, InstallerProject_OmodConfigDialog, Resources, \
    Installers_Link
from .. import bosh, bush, balt
from ..balt import EnabledLink, CheckLink, AppendableLink, Link
from ..belt import InstallerWizard, generateTweakLines
from ..bolt import CancelError, SkipError, GPath, StateError, deprint, \
    SubProgress, UncodedError, LogFile
from ..bosh import formatInteger
# FIXME(ut): globals
iniList = None
gInstallers = None

#------------------------------------------------------------------------------
# Installer Links -------------------------------------------------------------
#------------------------------------------------------------------------------
class _InstallerLink(Installers_Link, EnabledLink):
    """Common functions for installer links..."""

    def isSingleInstallable(self):
        if len(self.selected) == 1:
            installer = self.idata[self.selected[0]]
            if not isinstance(installer,
                              (bosh.InstallerProject, bosh.InstallerArchive)):
                return False
            elif installer.type not in (1,2):
                return False
            return True
        return False

    def filterInstallables(self): return filter(lambda x: # TODO(ut) - simplify - type in (1, 2) ??
        x in self.idata and self.idata[x].type in (1, 2) and isinstance(
        self.idata[x], (bosh.InstallerArchive, bosh.InstallerProject)),
                                                self.selected)

    def hasMarker(self):
        if len(self.selected) > 0:
            for i in self.selected:
                if isinstance(self.idata[i],bosh.InstallerMarker):
                    return True
        return False

    def isSingle(self):
        """Indicates whether or not is single installer."""
        return len(self.selected) == 1

    def isSingleMarker(self):
        """Indicates whether or not is single installer marker."""
        if len(self.selected) != 1: return False
        else: return isinstance(self.idata[self.selected[0]],
                              bosh.InstallerMarker)

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

    def getProjectPath(self):
        """Returns whether build directory exists."""
        archive = self.selected[0]
        return bosh.dirs['builds'].join(archive.sroot)

    def projectExists(self):
        if not len(self.selected) == 1: return False
        return self.getProjectPath().exists()

#------------------------------------------------------------------------------
class Installer_EditWizard(_InstallerLink):
    """Edit the wizard.txt associated with this project"""
    help = _(u"Edit the wizard.txt associated with this project.")

    def _initData(self, window, data):
        super(Installer_EditWizard, self)._initData(window, data)
        self.text = _(u'View Wizard...') if self.isSingleArchive() else _(
            u'Edit Wizard...')

    def _enable(self):
        return self.isSingleInstallable() and bool(
            self.idata[self.selected[0]].hasWizard)

    def Execute(self, event):
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

class Installer_Wizard(_InstallerLink):
    """Runs the install wizard to select subpackages and esp/m filtering"""
    parentWindow = ''
    help = _(u"Run the install wizard.")

    def __init__(self, bAuto):
        super(Installer_Wizard, self).__init__()
        self.bAuto = bAuto
        self.text = _(u'Auto Wizard') if self.bAuto else _(u'Wizard')

    def _enable(self):
        return self.isSingle() and (self.idata[
                                        self.selected[0]]).hasWizard != False

    def Execute(self, event):
        with balt.BusyCursor():
            installer = self.idata[self.selected[0]]
            subs = []
            oldRemaps = copy.copy(installer.remaps)
            installer.remaps = {}
            gInstallers.refreshCurrent(installer)
            for index in range(gInstallers.gSubList.GetCount()):
                subs.append(gInstallers.gSubList.GetString(index))
            saved = bosh.settings['bash.wizard.size']
            default = settingDefaults['bash.wizard.size']
            pos = bosh.settings['bash.wizard.pos']
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
                wizard = InstallerWizard(self, subs, pageSize, pos)
            except CancelError:
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
        bosh.settings['bash.wizard.size'] = (ret.PageSize[0],ret.PageSize[1])
        bosh.settings['bash.wizard.pos'] = (ret.Pos[0],ret.Pos[1])
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
            if self.idata[self.selected[0]].isActive:
                #Anneal
                try:
                    with balt.Progress(_(u'Annealing...'), u'\n'+u' '*60) as progress:
                        self.idata.anneal(self.selected, progress)
                finally:
                    self.idata.refresh(what='NS')
                    gInstallers.RefreshUIMods()
            else:
                #Install, if it's not installed
                try:
                    with balt.Progress(_(u'Installing...'),u'\n'+u' '*60) as progress:
                        self.idata.install(self.selected, progress)
                finally:
                    self.idata.refresh(what='N')
                    gInstallers.RefreshUIMods()
            Link.Frame.RefreshData()
        #Build any ini tweaks
        manuallyApply = []  # List of tweaks the user needs to  manually apply
        lastApplied = None
        #       iniList-> left    -> splitter ->INIPanel
        panel = iniList.GetParent().GetParent().GetParent()
        for iniFile in ret.IniEdits:
            outFile = bosh.dirs['tweaks'].join(u'%s - Wizard Tweak [%s].ini' % (installer.archive, iniFile.sbody))
            with outFile.open('w') as out:
                for line in generateTweakLines(ret.IniEdits[iniFile],iniFile):
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

class Installer_OpenReadme(_InstallerLink):
    """Opens the installer's readme if BAIN can find one"""
    text = _(u'Open Readme')
    help = _(u"Opens the installer's readme.")

    def _enable(self):
        return self.isSingle() and bool(self.idata[self.selected[0]].hasReadme)

    def Execute(self, event):
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

    def _enable(self):
        return len(self.filterInstallables())

    def Execute(self,event):
        """Handle selection."""
        try:
            with balt.Progress(_(u"Annealing..."),u'\n'+u' '*60) as progress:
                self.idata.anneal(self.filterInstallables(),progress)
        except (CancelError,SkipError):
            pass
        finally:
            self.idata.refresh(what='NS')
            gInstallers.RefreshUIMods()
            Link.Frame.RefreshData()

class Installer_Delete(_InstallerLink):
    text = _(u'Delete')
    help = _(u'Delete selected item(s)')

    def Execute(self, event): self.gTank.DeleteSelected(shellUI=False,
                                                        noRecycle=False)

class Installer_Duplicate(_InstallerLink):
    """Duplicate selected Installer."""
    text = _(u'Duplicate...')

    def _initData(self,window,data):
        super(Installer_Duplicate, self)._initData(window, data)
        self.help = _(u"Duplicate selected %(installername)s.") % (
            {'installername': self.selected[0]})

    def _enable(self): return self.isSingle() and not self.isSingleMarker()

    def Execute(self,event):
        """Handle selection."""
        curName = self.selected[0]
        isdir = self.idata.dir.join(curName).isdir()
        if isdir: root,ext = curName,u''
        else: root,ext = curName.rootExt
        newName = root+_(u' Copy')+ext
        index = 0
        while newName in self.idata:
            newName = root + (_(u' Copy (%d)') % index) + ext
            index += 1
        result = balt.askText(self.gTank,_(u"Duplicate %s to:") % curName.s,
            self.text,newName.s)
        result = (result or u'').strip()
        if not result: return
        #--Error checking
        newName = GPath(result).tail
        if not newName.s:
            balt.showWarning(self.gTank,_(u"%s is not a valid name.") % result)
            return
        if newName in self.idata:
            balt.showWarning(self.gTank,_(u"%s already exists.") % newName.s)
            return
        if self.idata.dir.join(curName).isfile() and curName.cext != newName.cext:
            balt.showWarning(self.gTank,
                _(u"%s does not have correct extension (%s).") % (newName.s,curName.ext))
            return
        #--Duplicate
        with balt.BusyCursor():
            self.idata.copy(curName,newName)
            self.idata.refresh(what='N')
            self.gTank.RefreshUI()

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
        self.idata.refresh(what='ION')
        self.gTank.RefreshUI()

class Installer_Rename(_InstallerLink):
    """Renames files by pattern."""
    text = _(u'Rename...')
    help = _(u"Rename selected installer(s).")

    def _enable(self):
        ##Only enable if all selected items are of the same type
        window = self.window
        firstItem = window.data[window.GetSelected()[0]]
        if isinstance(firstItem,bosh.InstallerMarker):
            self.InstallerType = bosh.InstallerMarker
        elif isinstance(firstItem,bosh.InstallerArchive):
            self.InstallerType = bosh.InstallerArchive
        elif isinstance(firstItem,bosh.InstallerProject):
            self.InstallerType = bosh.InstallerProject
        else: self.InstallerType = None
        if self.InstallerType:
            for item in window.GetSelected():
                if not isinstance(window.data[item],self.InstallerType):
                    return False
        return True

    def Execute(self,event):
        if len(self.selected) > 0:
            index = self.gTank.GetIndex(self.selected[0])
            if index != -1:
                self.gTank.gList.EditLabel(index)

class Installer_HasExtraData(CheckLink, _InstallerLink):
    """Toggle hasExtraData flag on installer."""
    text = _(u'Has Extra Directories')
    help = _(u"Allow installation of files in non-standard directories.")

    def _enable(self): return self.isSingleInstallable()

    def _check(self): return self.isSingleInstallable() and (
        self.idata[self.selected[0]]).hasExtraData

    def Execute(self,event):
        """Handle selection."""
        installer = self.idata[self.selected[0]]
        installer.hasExtraData ^= True
        installer.refreshDataSizeCrc()
        installer.refreshStatus(self.idata)
        self.idata.refresh(what='N')
        self.gTank.RefreshUI()

class Installer_OverrideSkips(CheckLink, _InstallerLink):
    """Toggle overrideSkips flag on installer."""
    text = _(u'Override Skips')
    help = _(u"Allow installation of files in non-standard directories.")

    def _initData(self, window, data):
        super(Installer_OverrideSkips, self)._initData(window, data)
        self.help = _(
            u"Override global file type skipping for %(installername)s.") % (
                    {'installername': self.selected[0]})

    def _enable(self): return self.isSingleInstallable()

    def _check(self): return self.isSingleInstallable() and (
        self.idata[self.selected[0]]).overrideSkips

    def Execute(self,event):
        """Handle selection."""
        installer = self.idata[self.selected[0]]
        installer.overrideSkips ^= True
        installer.refreshDataSizeCrc()
        installer.refreshStatus(self.idata)
        self.idata.refresh(what='N')
        self.gTank.RefreshUI()

class Installer_SkipRefresh(CheckLink, _InstallerLink):
    """Toggle skipRefresh flag on installer."""
    text = _(u"Don't Refresh")
    help = _(u"Don't automatically refresh project.")

    def _enable(self): return self.isSingleProject()

    def _check(self): return self.isSingleProject() and (
        self.idata[self.selected[0]]).skipRefresh

    def Execute(self,event):
        """Handle selection."""
        installer = self.idata[self.selected[0]]
        installer.skipRefresh ^= True
        if not installer.skipRefresh:
            # Check to see if we need to refresh this Project
            file = bosh.dirs['installers'].join(installer.archive)
            if (installer.size,installer.modified) != (file.size,file.getmtime(True)):
                installer.refreshDataSizeCrc()
                installer.refreshBasic(file)
                installer.refreshStatus(self.idata)
                self.idata.refresh(what='N')
                self.gTank.RefreshUI()

class Installer_Install(_InstallerLink):
    """Install selected packages."""
    mode_title = {'DEFAULT': _(u'Install'), 'LAST': _(u'Install Last'),
                  'MISSING': _(u'Install Missing')}

    def __init__(self,mode='DEFAULT'):
        super(Installer_Install, self).__init__()
        self.mode = mode
        self.text = self.mode_title[self.mode]

    def _enable(self): return len(self.filterInstallables())

    def Execute(self,event):
        """Handle selection."""
        try:
            with balt.Progress(_(u'Installing...'),u'\n'+u' '*60) as progress:
                last = (self.mode == 'LAST')
                override = (self.mode != 'MISSING')
                try:
                    tweaks = self.idata.install(self.filterInstallables(),progress,last,override)
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
            self.idata.refresh(what='N')
            gInstallers.RefreshUIMods()
            Link.Frame.RefreshData()

class Installer_ListStructure(_InstallerLink):   # Provided by Waruddar
    """Copies folder structure of installer to clipboard."""
    text = _(u"List Structure...")

    def _enable(self):
        return self.isSingle() and not isinstance(self.idata[self.selected[0]],
                                                  bosh.InstallerMarker)

    def Execute(self,event):
        archive = self.selected[0]
        installer = self.idata[archive]
        text = installer.listSource(archive)
        #--Get masters list
        balt.copyToClipboard(text)
        balt.showLog(self.gTank,text,_(u'Package Structure'),asDialog=False,fixedFont=False,icons=Resources.bashBlue)

class Installer_Move(_InstallerLink):
    """Moves selected installers to desired spot."""
    text = _(u'Move To...')

    def Execute(self,event):
        """Handle selection."""
        curPos = min(self.idata[x].order for x in self.selected)
        message = (_(u'Move selected archives to what position?')
                   + u'\n' +
                   _(u'Enter position number.')
                   + u'\n' +
                   _(u'Last: -1; First of Last: -2; Semi-Last: -3.')
                   )
        newPos = balt.askText(self.gTank,message,self.text,unicode(curPos))
        if not newPos: return
        newPos = newPos.strip()
        try:
            newPos = int(newPos)
        except:
            balt.showError(self.gTank,_(u'Position must be an integer.'))
            return
        if newPos == -3: newPos = self.idata[self.idata.lastKey].order
        elif newPos == -2: newPos = self.idata[self.idata.lastKey].order+1
        elif newPos < 0: newPos = len(self.idata.data)
        self.idata.moveArchives(self.selected,newPos)
        self.idata.refresh(what='N')
        self.gTank.RefreshUI()

class Installer_Open(_InstallerLink):
    """Open selected file(s)."""
    text = _(u'Open...')

    def _initData(self, window, data):
        super(Installer_Open, self)._initData(window, data)
        self.help = _(u"Open '%s'") % data[0] if len(data) == 1 else _(
            u"Open selected files.")
        self.selected = [x for x in self.selected if
                         not isinstance(self.idata.data[x],
                                        bosh.InstallerMarker)]

    def _enable(self): return bool(self.selected)

    def Execute(self,event):
        """Handle selection."""
        dir_ = self.idata.dir
        for file_ in self.selected:
            dir_.join(file_).start()

#------------------------------------------------------------------------------
class _Installer_OpenAt(_InstallerLink):
    group = 2  # the regexp group we are interested in - 2 is id, 1 is modname

    def _enable(self):
        x = self.__class__.regexp.search(self.selected[0].s)
        if not bool(self.isSingleArchive() and x): return False
        self._id = x.group(self.__class__.group)
        return bool(self._id)

    def _url(self): return self.__class__.baseUrl + self._id

    def Execute(self, event):
        if balt.askContinue(self.gTank, self.message, self.key, self.askTitle):
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
    key = 'bash.installers.opensearch'
    askTitle = _(u'Open a search')
    message = _(u"Open a search for this on Google?")

    def _url(self):
        return u'http://www.google.com/search?hl=en&q=' + u'+'.join(
            re.split(ur'\W+|_+', self._id))

class Installer_OpenTESA(_Installer_OpenAt):
    regexp = bosh.reTESA
    text = _(u'TES Alliance...')
    key = 'bash.installers.openTESA'
    askTitle = _(u'Open at TES Alliance')
    message = _(
        u"Attempt to open this as a mod at TES Alliance? This assumes that "
        u"the trailing digits in the package's name are actually the id "
        u"number of the mod at TES Alliance. If this assumption is wrong, "
        u"you'll just get a random mod page (or error notice) at TES "
        u"Alliance.")
    baseUrl =u'http://tesalliance.org/forums/index.php?app=downloads&showfile='

class Installer_OpenPES(_Installer_OpenAt):
    regexp = bosh.reTESA
    text = _(u'Planet Elderscrolls...')
    key = 'bash.installers.openPES'
    askTitle = _(u'Open at Planet Elderscrolls')
    message = _(
        u"Attempt to open this as a mod at Planet Elderscrolls? This assumes "
        u"that the trailing digits in the package's name are actually the id "
        u"number of the mod at Planet Elderscrolls. If this assumption is "
        u"wrong, you'll just get a random mod page (or error notice) at "
        u"Planet Elderscrolls.")
    baseUrl = u'http://planetelderscrolls.gamespy.com/View.php' \
               u'?view=OblivionMods.Detail&id='

#------------------------------------------------------------------------------
class Installer_Refresh(_InstallerLink):
    """Rescans selected Installers."""
    text = _(u'Refresh')

    def _enable(self):
        return not len(self.selected) == 1 or self.isSingleInstallable()

    def Execute(self,event):
        """Handle selection."""
        try:
            with balt.Progress(_(u'Refreshing Packages...'),u'\n'+u' '*60, abort=True) as progress:
                progress.setFull(len(self.selected))
                for index,archive in enumerate(self.selected):
                    progress(index,_(u'Refreshing Packages...')+u'\n'+archive.s)
                    installer = self.idata[archive]
                    apath = bosh.dirs['installers'].join(archive)
                    installer.refreshBasic(apath,SubProgress(progress,index,index+1),True)
                    self.idata.hasChanged = True
        except CancelError:
            # User canceled the refresh
            pass
        self.idata.refresh(what='NSC')
        self.gTank.RefreshUI()

class Installer_SkipVoices(CheckLink, _InstallerLink):
    """Toggle skipVoices flag on installer."""
    text = _(u'Skip Voices')

    def _enable(self): return self.isSingleInstallable()

    def _check(self): return self.isSingleInstallable() and (
        self.idata[self.selected[0]]).skipVoices

    def Execute(self,event):
        """Handle selection."""
        installer = self.idata[self.selected[0]]
        installer.skipVoices ^= True
        installer.refreshDataSizeCrc()
        self.idata.refresh(what='NS')
        self.gTank.RefreshUI()

class Installer_Uninstall(_InstallerLink):
    """Uninstall selected Installers."""
    text = _(u'Uninstall')

    def _enable(self): return len(self.filterInstallables())

    def Execute(self,event):
        """Handle selection."""
        try:
            with balt.Progress(_(u"Uninstalling..."),u'\n'+u' '*60) as progress:
                self.idata.uninstall(self.filterInstallables(),progress)
        except (CancelError,SkipError):
            pass
        finally:
            self.idata.refresh(what='NS')
            bosh.modInfos.plugins.saveLoadOrder()
            gInstallers.RefreshUIMods()
            Link.Frame.RefreshData()

class Installer_CopyConflicts(_InstallerLink):
    """For Modders only - copy conflicts to a new project."""
    text = _(u'Copy Conflicts to Project')

    def _enable(self): return self.isSingleInstallable()

    def Execute(self,event):
        """Handle selection."""
        data = self.idata # bosh.InstallersData instance (dict bolt.Path ->
        # InstallerArchive)
        installers_dir = data.dir
        srcConflicts = set()
        packConflicts = []
        with balt.Progress(_(u"Copying Conflicts..."),
                           u'\n' + u' ' * 60) as progress:
            srcArchive = self.selected[0]
            srcInstaller = data[srcArchive]
            src_sizeCrc = srcInstaller.data_sizeCrc # dictionary Path
            mismatched = set(src_sizeCrc) # just a set of bolt.Path of the src
            # installer files
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
                    iProject = data[project] #bash.bosh.InstallerProject object
                    pProject = installers_dir.join(project) # bolt.Path
                    # ...\Bash Installers\030 - Conflicts
                    iProject.refreshed = False
                    iProject.refreshBasic(pProject,None,True)
                    if iProject.order == -1:
                        data.moveArchives([project],srcInstaller.order + 1)
                    data.refresh(what='I') # InstallersData.refresh()
                    self.gTank.RefreshUI()

#------------------------------------------------------------------------------
# InstallerDetails Espm Links -------------------------------------------------
#------------------------------------------------------------------------------
class Installer_Espm_SelectAll(EnabledLink):
    """Select All Esp/ms in installer for installation."""
    text = _(u'Select All')

    def _enable(self): return len(gInstallers.espms) != 0

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        installer.espmNots = set()
        for i in range(len(gInstallers.espms)):
            gInstallers.gEspmList.Check(i, True)
        gInstallers.refreshCurrent(installer)

class Installer_Espm_DeselectAll(EnabledLink):
    """Deselect All Esp/ms in installer for installation."""
    text = _(u'Deselect All')

    def _enable(self): return len(gInstallers.espms) != 0

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        espmNots = installer.espmNots = set()
        for i in range(len(gInstallers.espms)):
            gInstallers.gEspmList.Check(i, False)
            espm =GPath(gInstallers.gEspmList.GetString(i).replace(u'&&',u'&'))
            espmNots.add(espm)
        gInstallers.refreshCurrent(installer)

class Installer_Espm_Rename(EnabledLink):
    """Changes the installed name for an Esp/m."""
    text = _(u'Rename...')

    def _enable(self): return self.data != -1

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        curName =gInstallers.gEspmList.GetString(self.data).replace(u'&&',u'&')
        if curName[0] == u'*':
            curName = curName[1:]
        _file = GPath(curName)
        newName = balt.askText(self.window,
                               _(u"Enter new name (without the extension):"),
                               _(u"Rename Esp/m"), _file.sbody)
        if not newName: return
        if newName in gInstallers.espms: return
        installer.setEspmName(curName, newName + _file.cext)
        gInstallers.refreshCurrent(installer)

class Installer_Espm_Reset(EnabledLink):
    """Resets the installed name for an Esp/m."""
    text = _(u'Reset Name')

    def _enable(self):
        if self.data == -1: return False  # FIXME ?
        self.installer = installer = gInstallers.data[gInstallers.detailsItem]
        curName =gInstallers.gEspmList.GetString(self.data).replace(u'&&',u'&')
        if curName[0] == u'*': curName = curName[1:]
        self.curName = curName
        return installer.isEspmRenamed(curName)

    def Execute(self,event):
        """Handle selection."""
        self.installer.resetEspmName(self.curName)
        gInstallers.refreshCurrent(self.installer)

class Installer_Espm_ResetAll(EnabledLink):
    """Resets all renamed Esp/ms."""
    text = _(u'Reset All Names')

    def _enable(self): return len(gInstallers.espms) != 0

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        installer.resetAllEspmNames()
        gInstallers.refreshCurrent(installer)

class Installer_Espm_List(EnabledLink):
    """Lists all Esp/ms in installer for user information/w/e."""
    text = _(u'List Esp/ms')

    def _enable(self): return len(gInstallers.espms) != 0

    def Execute(self,event):
        """Handle selection."""
        subs = _(u'Esp/m List for %s:') % gInstallers.data[
            gInstallers.detailsItem].archive + u'\n[spoiler]\n'
        espm_list = gInstallers.gEspmList
        for index in range(espm_list.GetCount()):
            subs += [u'   ',u'** '][espm_list.IsChecked(index)] + \
                    espm_list.GetString(index) + '\n'
        subs += u'[/spoiler]'
        balt.copyToClipboard(subs)
        balt.showLog(self.window, subs, _(u'Esp/m List'), asDialog=False,
                     fixedFont=False, icons=Resources.bashBlue)

#------------------------------------------------------------------------------
# InstallerDetails Subpackage Links -------------------------------------------
#------------------------------------------------------------------------------
class _Installer_Subs(EnabledLink):
    def _enable(self): return gInstallers.gSubList.GetCount() > 1

class Installer_Subs_SelectAll(_Installer_Subs):
    """Select All sub-packages in installer for installation."""
    text = _(u'Select All')

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        for index in xrange(gInstallers.gSubList.GetCount()):
            gInstallers.gSubList.Check(index, True)
            installer.subActives[index + 1] = True
        gInstallers.refreshCurrent(installer)

class Installer_Subs_DeselectAll(_Installer_Subs):
    """Deselect All sub-packages in installer for installation."""
    text = _(u'Deselect All')

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        for index in xrange(gInstallers.gSubList.GetCount()):
            gInstallers.gSubList.Check(index, False)
            installer.subActives[index + 1] = False
        gInstallers.refreshCurrent(installer)

class Installer_Subs_ToggleSelection(_Installer_Subs):
    """Toggles selection state of all sub-packages in installer for
    installation."""
    text = _(u'Toggle Selection')

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        for index in xrange(gInstallers.gSubList.GetCount()):
            check = not installer.subActives[index+1]
            gInstallers.gSubList.Check(index, check)
            installer.subActives[index + 1] = check
        gInstallers.refreshCurrent(installer)

class Installer_Subs_ListSubPackages(_Installer_Subs):
    """Lists all sub-packages in installer for user information/w/e."""
    text = _(u'List Sub-packages')

    def Execute(self,event):
        """Handle selection."""
        installer = gInstallers.data[gInstallers.detailsItem]
        subs = _(u'Sub-Packages List for %s:') % installer.archive
        subs += u'\n[spoiler]\n'
        for index in xrange(gInstallers.gSubList.GetCount()):
            subs += [u'   ', u'** '][gInstallers.gSubList.IsChecked(
                index)] + gInstallers.gSubList.GetString(index) + u'\n'
        subs += u'[/spoiler]'
        balt.copyToClipboard(subs)
        balt.showLog(self.window, subs, _(u'Sub-Package Lists'),
                     asDialog=False, fixedFont=False, icons=Resources.bashBlue)

#------------------------------------------------------------------------------
# InstallerArchive Links ------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerArchive_Unpack(AppendableLink, _InstallerLink):
    """Install selected packages."""
    text = _(u'Unpack to Project(s)...')

    def _append(self, window):
        self.selected = window.GetSelected()
        return self.isSelectedArchives()

    def Execute(self,event):
        if self.isSingleArchive():
            archive = self.selected[0]
            installer = self.idata[archive]
            project = archive.root
            result = balt.askText(self.gTank,_(u"Unpack %s to Project:") % archive.s,
                self.text,project.s)
            result = (result or u'').strip()
            if not result: return
            #--Error checking
            project = GPath(result).tail
            if not project.s or project.cext in bosh.readExts:
                balt.showWarning(self.gTank,_(u"%s is not a valid project name.") % result)
                return
            if self.idata.dir.join(project).isfile():
                balt.showWarning(self.gTank,_(u"%s is a file.") % project.s)
                return
            if project in self.idata:
                if not balt.askYes(self.gTank,_(u"%s already exists. Overwrite it?") % project.s,self.text,False):
                    return
        #--Copy to Build
        with balt.Progress(_(u"Unpacking to Project..."),u'\n'+u' '*60) as progress:
            if self.isSingleArchive():
                installer.unpackToProject(archive,project,SubProgress(progress,0,0.8))
                if project not in self.idata:
                    self.idata[project] = bosh.InstallerProject(project)
                iProject = self.idata[project]
                pProject = bosh.dirs['installers'].join(project)
                iProject.refreshed = False
                iProject.refreshBasic(pProject,SubProgress(progress,0.8,0.99),True)
                if iProject.order == -1:
                    self.idata.moveArchives([project],installer.order+1)
                self.idata.refresh(what='NS')
                self.gTank.RefreshUI()
                #pProject.start()
            else:
                for archive in self.selected:
                    project = archive.root
                    installer = self.idata[archive]
                    if project in self.idata:
                        if not balt.askYes(self.gTank,_(u"%s already exists. Overwrite it?") % project.s,self.text,False):
                            continue
                    installer.unpackToProject(archive,project,SubProgress(progress,0,0.8))
                    if project not in self.idata:
                        self.idata[project] = bosh.InstallerProject(project)
                    iProject = self.idata[project]
                    pProject = bosh.dirs['installers'].join(project)
                    iProject.refreshed = False
                    iProject.refreshBasic(pProject,SubProgress(progress,0.8,0.99),True)
                    if iProject.order == -1:
                        self.idata.moveArchives([project],installer.order+1)
                self.idata.refresh(what='NS')
                self.gTank.RefreshUI()

#------------------------------------------------------------------------------
# InstallerProject Links ------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerProject_OmodConfig(_InstallerLink):
    """Install selected packages.""" # TODO(ut): docs
    text = _(u'Omod Info...')

    def _enable(self): return self.isSingleProject()

    def Execute(self,event):
        project = self.selected[0]
        dialog =InstallerProject_OmodConfigDialog(self.gTank,self.idata,project)
        dialog.Show()

#------------------------------------------------------------------------------
class InstallerProject_Sync(_InstallerLink):
    """Install selected packages.""" # TODO(ut): docs
    text = _(u'Sync from Data')

    def _enable(self):
        if not self.isSingleProject(): return False
        project = self.selected[0]
        installer = self.idata[project]
        return bool(installer.missingFiles or installer.mismatchedFiles)

    def Execute(self,event):
        project = self.selected[0]
        installer = self.idata[project]
        missing = installer.missingFiles
        mismatched = installer.mismatchedFiles
        message = (_(u'Update %s according to data directory?')
                   + u'\n' +
                   _(u'Files to delete:')
                   + u'%d\n' +
                   _(u'Files to update:')
                   + u'%d') % (project.s,len(missing),len(mismatched))
        if not balt.askWarning(self.gTank,message,self.text): return
        #--Sync it, baby!
        with balt.Progress(self.text, u'\n' + u' ' * 60) as progress:
            progress(0.1,_(u'Updating files.'))
            installer.syncToData(project,missing|mismatched)
            pProject = bosh.dirs['installers'].join(project)
            installer.refreshed = False
            installer.refreshBasic(pProject,SubProgress(progress,0.1,0.99),True)
            self.idata.refresh(what='NS')
            self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class InstallerProject_SyncPack(_InstallerLink):
    """Install selected packages.""" # TODO(ut): docs
    text = _(u'Sync and Pack')

    def _enable(self): return self.projectExists()

    def Execute(self,event):
        raise UncodedError

#------------------------------------------------------------------------------
class InstallerProject_Pack(AppendableLink, _InstallerLink):
    """Pack project to an archive."""
    text = _(u'Pack to Archive...')

    def _append(self, window):
        self.selected = window.GetSelected()
        return self.isSingleProject()

    def Execute(self,event):
        #--Generate default filename from the project name and the default extension
        project = self.selected[0]
        installer = self.idata[project]
        archive = bosh.GPath(project.s + bosh.defaultExt)
        #--Confirm operation
        result = balt.askText(self.gTank,_(u'Pack %s to Archive:') % project.s,
            self.text,archive.s)
        result = (result or u'').strip()
        if not result: return
        #--Error checking
        archive = GPath(result).tail
        if not archive.s:
            balt.showWarning(self.gTank,_(u'%s is not a valid archive name.') % result)
            return
        if self.idata.dir.join(archive).isdir():
            balt.showWarning(self.gTank,_(u'%s is a directory.') % archive.s)
            return
        if archive.cext not in bosh.writeExts:
            balt.showWarning(self.gTank,_(u'The %s extension is unsupported. Using %s instead.') % (archive.cext, bosh.defaultExt))
            archive = GPath(archive.sroot + bosh.defaultExt).tail
        if archive in self.idata:
            if not balt.askYes(self.gTank,_(u'%s already exists. Overwrite it?') % archive.s,self.text,False): return
        #--Archive configuration options
        blockSize = None
        if archive.cext in bosh.noSolidExts:
            isSolid = False
        else:
            if not u'-ms=' in bosh.inisettings['7zExtraCompressionArguments']:
                isSolid = balt.askYes(self.gTank,_(u'Use solid compression for %s?') % archive.s,self.text,False)
                if isSolid:
                    blockSize = balt.askNumber(self.gTank,
                        _(u'Use what maximum size for each solid block?')
                        + u'\n' +
                        _(u"Enter '0' to use 7z's default size.")
                        ,u'MB',self.text,0,0,102400)
            else: isSolid = True
        with balt.Progress(_(u'Packing to Archive...'),u'\n'+u' '*60) as progress:
            #--Pack
            installer.packToArchive(project,archive,isSolid,blockSize,SubProgress(progress,0,0.8))
            #--Add the new archive to Bash
            if archive not in self.idata:
                self.idata[archive] = bosh.InstallerArchive(archive)
            #--Refresh UI
            iArchive = self.idata[archive]
            pArchive = bosh.dirs['installers'].join(archive)
            iArchive.blockSize = blockSize
            iArchive.refreshed = False
            iArchive.refreshBasic(pArchive,SubProgress(progress,0.8,0.99),True)
            if iArchive.order == -1:
                self.idata.moveArchives([archive],installer.order+1)
            #--Refresh UI
            self.idata.refresh(what='I')
            self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class InstallerProject_ReleasePack(_InstallerLink):
    """Pack project to an archive for release. Ignores dev files/folders."""
    text = _(u'Package for Release...')

    def _enable(self): return self.isSingleProject()

    def Execute(self,event):
        #--Generate default filename from the project name and the default extension
        project = self.selected[0]
        installer = self.idata[project]
        archive = bosh.GPath(project.s + bosh.defaultExt)
        #--Confirm operation
        result = balt.askText(self.gTank,_(u"Pack %s to Archive:") % project.s,
            self.text,archive.s)
        result = (result or u'').strip()
        if not result: return
        #--Error checking
        archive = GPath(result).tail
        if not archive.s:
            balt.showWarning(self.gTank,_(u"%s is not a valid archive name.") % result)
            return
        if self.idata.dir.join(archive).isdir():
            balt.showWarning(self.gTank,_(u"%s is a directory.") % archive.s)
            return
        if archive.cext not in bosh.writeExts:
            balt.showWarning(self.gTank,_(u"The %s extension is unsupported. Using %s instead.") % (archive.cext, bosh.defaultExt))
            archive = GPath(archive.sroot + bosh.defaultExt).tail
        if archive in self.idata:
            if not balt.askYes(self.gTank,_(u"%s already exists. Overwrite it?") % archive.s,self.text,False): return
        #--Archive configuration options
        blockSize = None
        if archive.cext in bosh.noSolidExts:
            isSolid = False
        else:
            if not u'-ms=' in bosh.inisettings['7zExtraCompressionArguments']:
                isSolid = balt.askYes(self.gTank,_(u"Use solid compression for %s?") % archive.s,self.text,False)
                if isSolid:
                    blockSize = balt.askNumber(self.gTank,
                        _(u'Use what maximum size for each solid block?')
                        + u'\n' +
                        _(u"Enter '0' to use 7z's default size."),'MB',self.text,0,0,102400)
            else: isSolid = True
        with balt.Progress(_(u"Packing to Archive..."),u'\n'+u' '*60) as progress:
            #--Pack
            installer.packToArchive(project,archive,isSolid,blockSize,SubProgress(progress,0,0.8),release=True)
            #--Add the new archive to Bash
            if archive not in self.idata:
                self.idata[archive] = bosh.InstallerArchive(archive)
            #--Refresh UI
            iArchive = self.idata[archive]
            pArchive = bosh.dirs['installers'].join(archive)
            iArchive.blockSize = blockSize
            iArchive.refreshed = False
            iArchive.refreshBasic(pArchive,SubProgress(progress,0.8,0.99),True)
            if iArchive.order == -1:
                self.idata.moveArchives([archive],installer.order+1)
            #--Refresh UI
            self.idata.refresh(what='I')
            self.gTank.RefreshUI()

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

    def Execute(self,event):
        #--Generate default filename from BCF filename
        result = self.converter.fullPath.sbody[:-4]
        #--List source archives
        message = _(u'Using:')+u'\n* '
        message += u'\n* '.join(sorted(u'(%08X) - %s' % (x,self.idata.crc_installer[x].archive) for x in self.converter.srcCRCs)) + u'\n'
        #--Confirm operation
        result = balt.askText(self.gTank,message,self.dialogTitle,result + bosh.defaultExt)
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
        if destArchive in self.idata:
            if not balt.askYes(self.gTank,_(u'%s already exists. Overwrite it?') % destArchive.s,self.dialogTitle,False): return
        with balt.Progress(_(u'Converting to Archive...'),u'\n'+u' '*60) as progress:
            #--Perform the conversion
            self.converter.apply(destArchive,self.idata.crc_installer,SubProgress(progress,0.0,0.99))
            if hasattr(self.converter, 'hasBCF') and not self.converter.hasBCF:
                deprint(u'An error occurred while attempting to apply an Auto-BCF:',traceback=True)
                balt.showWarning(self.gTank,
                    _(u'%s: An error occurred while applying an Auto-BCF.' % destArchive.s))
                # hasBCF will be set to False if there is an error while
                # rearranging files
                return
            #--Add the new archive to Bash
            if destArchive not in self.idata:
                self.idata[destArchive] = bosh.InstallerArchive(destArchive)
            #--Apply settings from the BCF to the new InstallerArchive
            iArchive = self.idata[destArchive]
            self.converter.applySettings(iArchive)
            #--Refresh UI
            pArchive = bosh.dirs['installers'].join(destArchive)
            iArchive.refreshed = False
            iArchive.refreshBasic(pArchive,SubProgress(progress,0.99,1.0),True)
            if iArchive.order == -1:
                lastInstaller = self.idata[self.selected[-1]]
                self.idata.moveArchives([destArchive],lastInstaller.order+1)
            self.idata.refresh(what='I')
            self.gTank.RefreshUI()

#------------------------------------------------------------------------------
class InstallerConverter_ApplyEmbedded(_InstallerLink):
    text = _(u'Embedded BCF')

    def Execute(self,event):
        name = self.selected[0]
        archive = self.idata[name]
        #--Ask for an output filename
        destArchive = balt.askText(self.gTank, _(u'Output file:'),
                                   _(u'Apply BCF...'), name.stail)
        destArchive = (destArchive if destArchive else u'').strip()
        if not destArchive: return
        destArchive = GPath(destArchive)
        #--Error checking
        if not destArchive.s:
            balt.showWarning(self.gTank, _(
                u'%s is not a valid archive name.') % destArchive.s)
            return
        if destArchive.cext not in bosh.writeExts:
            balt.showWarning(self.gTank, _(
                u'The %s extension is unsupported. Using %s instead.') % (
                                 destArchive.cext, bosh.defaultExt))
            destArchive = GPath(destArchive.sroot + bosh.defaultExt).tail
        if destArchive in self.idata:
            if not balt.askYes(self.gTank, _(
                    u'%s already exists. Overwrite it?') % destArchive.s,
                               _(u'Apply BCF...'), False):
                return
        with balt.Progress(_(u'Extracting BCF...'),u'\n'+u' '*60) as progress:
            self.idata.applyEmbeddedBCFs([archive],[destArchive],progress)
            iArchive = self.idata[destArchive]
            if iArchive.order == -1:
                lastInstaller = self.idata[self.selected[-1]]
                self.idata.moveArchives([destArchive],lastInstaller.order+1)
            self.idata.refresh(what='I')
            self.gTank.RefreshUI()

class InstallerConverter_Create(_InstallerLink):
    """Create BAIN conversion file."""
    dialogTitle = _(u'Create BCF...') # title used in dialog
    text = _(u'Create...')

    def Execute(self,event):
        #--Generate allowable targets
        readTypes = u'*%s' % u';*'.join(bosh.readExts)
        #--Select target archive
        destArchive = balt.askOpen(self.gTank,_(u"Select the BAIN'ed Archive:"),
                                   self.idata.dir,u'', readTypes,mustExist=True)
        if not destArchive: return
        #--Error Checking
        BCFArchive = destArchive = destArchive.tail
        if not destArchive.s or destArchive.cext not in bosh.readExts:
            balt.showWarning(self.gTank,_(u'%s is not a valid archive name.') % destArchive.s)
            return
        if destArchive not in self.idata:
            balt.showWarning(self.gTank,_(u'%s must be in the Bash Installers directory.') % destArchive.s)
            return
        if BCFArchive.csbody[-4:] != u'-bcf':
            BCFArchive = GPath(BCFArchive.sbody + u'-BCF' + bosh.defaultExt).tail
        #--List source archives and target archive
        message = _(u'Convert:')
        message += u'\n* ' + u'\n* '.join(sorted(u'(%08X) - %s' % (self.idata[x].crc,x.s) for x in self.selected))
        message += (u'\n\n'+_(u'To:')+u'\n* (%08X) - %s') % (self.idata[destArchive].crc,destArchive.s) + u'\n'
        #--Confirm operation
        result = balt.askText(self.gTank,message,self.dialogTitle,BCFArchive.s)
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
            if not balt.askYes(self.gTank,_(u'%s already exists. Overwrite it?') % BCFArchive.s,self.dialogTitle,False): return
            #--It is safe to removeConverter, even if the converter isn't overwritten or removed
            #--It will be picked back up by the next refresh.
            self.idata.removeConverter(BCFArchive)
        destInstaller = self.idata[destArchive]
        blockSize = None
        if destInstaller.isSolid:
            blockSize = balt.askNumber(self.gTank,u'mb',
                _(u'Use what maximum size for each solid block?')
                + u'\n' +
                _(u"Enter '0' to use 7z's default size."),
                self.dialogTitle,destInstaller.blockSize or 0,0,102400)
        progress = balt.Progress(_(u'Creating %s...') % BCFArchive.s,u'\n'+u' '*60)
        log = None
        try:
            #--Create the converter
            converter = bosh.InstallerConverter(self.selected, self.idata, destArchive, BCFArchive, blockSize, progress)
            #--Add the converter to Bash
            self.idata.addConverter(converter)
            #--Refresh UI
            self.idata.refresh(what='C')
            #--Generate log
            log = LogFile(StringIO.StringIO())
            log.setHeader(u'== '+_(u'Overview')+u'\n')
##            log('{{CSS:wtxt_sand_small.css}}')
            log(u'. '+_(u'Name')+u': '+BCFArchive.s)
            log(u'. '+_(u'Size')+u': %s KB'% formatInteger(max(converter.fullPath.size,1024)/1024 if converter.fullPath.size else 0))
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
                balt.showLog(self.gTank, log.out.getvalue(), _(u'BCF Information'))

#------------------------------------------------------------------------------
# Installer Submenus ----------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerOpenAt_MainMenu(balt.MenuLink):
    """Main Open At Menu"""
    def _enable(self):
        if not super(InstallerOpenAt_MainMenu, self)._enable(): return False # one  selected only
        return isinstance(self.data[self.selected[0]],bosh.InstallerArchive)

class InstallerConverter_ConvertMenu(balt.MenuLink):
    """Apply BCF SubMenu."""
    def _enable(self): # TODO(ut) untested for multiple selections
        """Return False to disable the converter menu otherwise populate its links attribute and return True."""
        linkSet = set()
        #--Converters are linked by CRC, not archive name
        #--So, first get all the selected archive CRCs
        selected = self.selected # window.GetSelected()
        instData = self.data # window.data, InstallersData singleton
        selectedCRCs = set(instData[archive].crc for archive in selected)
        crcInstallers = set(instData.crc_installer)
        srcCRCs = set(instData.srcCRC_converters)
        #--There is no point in testing each converter unless
        #--every selected archive has an associated converter
        if selectedCRCs <= srcCRCs:
            #--Test every converter for every selected archive
            #--Only add a link to the converter if it uses all selected archives,
            #--and all of its required archives are available (but not necessarily selected)
            linkSet = set( #--List comprehension is faster than unrolling the for loops, but readability suffers
                [converter for installerCRC in selectedCRCs for converter in
                 instData.srcCRC_converters[installerCRC] if
                 selectedCRCs <= converter.srcCRCs <= crcInstallers])
##            for installerCRC in selectedCRCs:
##                for converter in window.data.srcCRC_converters[installerCRC]:
##                    if selectedCRCs <= converter.srcCRCs <= set(window.data.crc_installer): linkSet.add(converter)
        #--If the archive is a single archive with an embedded BCF, add that
        if len(selected) == 1 and instData[selected[0]].hasBCF:
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
    def _enable(self):
        for item in self.selected:
            if not isinstance(self.data[item],bosh.InstallerArchive):
                return False
        return True
