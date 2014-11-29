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
import re
import webbrowser
import wx
from . import _Link, settingDefaults, bashBlue, refreshData
from .. import bosh, bush, balt
from ..belt import InstallerWizard, generateTweakLines
from ..bolt import CancelError, SkipError, GPath, StateError, deprint
# FIXME(ut): globals
iniList = None
gInstallers = None

#------------------------------------------------------------------------------
# Installer Links -------------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerLink(_Link):
    """Common functions for installer links..."""
    help = u''

    def _enable(self):
        """"Override as needed to enable or disable the menu item (enabled
        by default)."""
        return True

    def AppendToMenu(self, menu, window, data):
        menuItem = _Link.AppendToMenu(self, menu, window, data)
        menuItem.Enable(self._enable())
        return menuItem

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
        """Indicates whether or not is single installer marker."""
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
    help = _(u"Edit the wizard.txt associated with this project.")

    def _enable(self):
        return self.isSingleInstallable() and bool(
            self.data[self.selected[0]].hasWizard)

    def AppendToMenu(self, menu, window, data):
        self._initData(window, data)
        self.text = _(u'View Wizard...') if self.isSingleArchive() else _(
            u'Edit Wizard...')
        InstallerLink.AppendToMenu(self, menu, window, data)

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
    help = _(u"Run the install wizard.")

    def _enable(self):
        return self.isSingle() and (self.data[
                                        self.selected[0]]).hasWizard != False

    def __init__(self, bAuto):
        InstallerLink.__init__(self)
        self.bAuto = bAuto
        self.text = _(u'Auto Wizard') if self.bAuto else _(u'Wizard')

    def Execute(self, event):
        with balt.BusyCursor():
            installer = self.data[self.selected[0]]
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
            refreshData()
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

class Installer_OpenReadme(InstallerLink):
    """Opens the installer's readme if BAIN can find one"""
    text = _(u'Open Readme')
    help = _(u"Opens the installer's readme.")

    def _enable(self):
        return self.isSingle() and bool(self.data[self.selected[0]].hasReadme)

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
    text = _(u'Anneal')
    help = _(u"Anneal all packages.")

    def _enable(self):
        return len(self.filterInstallables())

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
            refreshData()

class Installer_Duplicate(InstallerLink):
    """Duplicate selected Installer."""
    text = _(u'Duplicate...')

    def AppendToMenu(self,menu,window,data):
        self._initData(window, data)
        self.help = _(u"Duplicate selected %(installername)s.") % ({'installername':self.selected[0]})
        menuItem = _Link.AppendToMenu(self,menu,window,data)
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
            self.text,newName.s)
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

class Installer_Hide(InstallerLink):
    """Hide selected Installers."""
    text = _(u'Hide...')
    help = _(u"Hide selected installer(s).")

    def _enable(self):
        for item in self.window.GetSelected():
            if isinstance(self.window.data[item],bosh.InstallerMarker):
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
        self.data.refresh(what='ION')
        self.gTank.RefreshUI()

class Installer_Rename(InstallerLink):
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

class Installer_HasExtraData(InstallerLink):
    """Toggle hasExtraData flag on installer."""
    text = _(u'Has Extra Directories')
    help = _(u"Allow installation of files in non-standard directories.")
    kind = wx.ITEM_CHECK

    def AppendToMenu(self,menu,window,data):
        menuItem = _Link.AppendToMenu(self,menu,window,data)
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

class Installer_OverrideSkips(InstallerLink):
    """Toggle overrideSkips flag on installer."""
    text = _(u'Override Skips')
    help = _(u"Allow installation of files in non-standard directories.")
    kind = wx.ITEM_CHECK

    def AppendToMenu(self,menu,window,data):
        self._initData(window, data)
        self.help = _(
            u"Override global file type skipping for %(installername)s.") % (
                    {'installername': self.selected[0]})
        menuItem = _Link.AppendToMenu(self,menu,window,data)
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

class Installer_SkipRefresh(InstallerLink):
    """Toggle skipRefresh flag on installer."""
    text = _(u"Don't Refresh")
    help = _(u"Don't automatically refresh project.")
    kind = wx.ITEM_CHECK

    def AppendToMenu(self,menu,window,data):
        menuItem = _Link.AppendToMenu(self,menu,window,data)
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

class Installer_Install(InstallerLink):
    """Install selected packages."""
    mode_title = {'DEFAULT':_(u'Install'),'LAST':_(u'Install Last'),'MISSING':_(u'Install Missing')}

    def __init__(self,mode='DEFAULT'):
        _Link.__init__(self)
        self.mode = mode

    def AppendToMenu(self,menu,window,data):
        self.text = self.mode_title[self.mode]
        menuItem = _Link.AppendToMenu(self,menu,window,data)
        menuItem.Enable(len(self.filterInstallables()))

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
            refreshData()

class Installer_ListPackages(InstallerLink):
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
        if balt.askYes(self.gTank,message,_(u'Only Show Installed?')):
            text = self.data.getPackageList(False)
        else: text = self.data.getPackageList()
        balt.copyToClipboard(text)
        balt.showLog(self.gTank,text,_(u'BAIN Packages'),asDialog=False,fixedFont=False,icons=bashBlue)

class Installer_ListStructure(InstallerLink):   # Provided by Waruddar
    """Copies folder structure of installer to clipboard."""
    text = _(u"List Structure...")

    def _enable(self):
        return self.isSingle() and not isinstance(self.data[self.selected[0]],
                                                  bosh.InstallerMarker)

    def Execute(self,event):
        archive = self.selected[0]
        installer = self.data[archive]
        text = installer.listSource(archive)
        #--Get masters list
        balt.copyToClipboard(text)
        balt.showLog(self.gTank,text,_(u'Package Structure'),asDialog=False,fixedFont=False,icons=bashBlue)

class Installer_Move(InstallerLink):
    """Moves selected installers to desired spot."""
    text = _(u'Move To...')

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

class Installer_Open(_Link):
    """Open selected file(s)."""
    text = _(u'Open...')

    def AppendToMenu(self,menu,window,data):
        self.help = _(u"Open '%s'") % data[0] if len(data) == 1 else _(
            u"Open selected files.")
        menuItem = _Link.AppendToMenu(self,menu,window,data)
        self.selected = [x for x in self.selected if not isinstance(self.data.data[x],bosh.InstallerMarker)]
        menuItem.Enable(bool(self.selected))

    def Execute(self,event):
        """Handle selection."""
        dir = self.data.dir
        for file in self.selected:
            dir.join(file).start()

#------------------------------------------------------------------------------
class _Installer_OpenAt(InstallerLink):
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

class Installer_OpenNexus(_Installer_OpenAt):
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

    def AppendToMenu(self,menu,window,data):
        if not bush.game.nexusUrl: return
        _Installer_OpenAt.AppendToMenu(self, menu, window, data)

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
