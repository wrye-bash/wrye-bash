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
from collections import defaultdict

from . import settingDefaults, Installers_Link, BashFrame, INIList
from .frames import InstallerProject_OmodConfigDialog
from .. import bass, bolt, bosh, bush, balt, archives
from ..balt import EnabledLink, CheckLink, AppendableLink, OneItemLink, \
    UIList_Rename, UIList_Hide
from ..belt import InstallerWizard, generateTweakLines
from ..bolt import GPath, deprint, SubProgress, LogFile, formatInteger, \
    round_size
from ..exception import CancelError, SkipError, StateError

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

    def isSingleArchive(self):
        """Indicates whether or not is single archive."""
        if len(self.selected) != 1: return False
        else: return isinstance(next(self.iselected_infos()),
                                bosh.InstallerArchive)

    ##: Methods below should be in an "archives.py"
    def _promptSolidBlockSize(self, title, value=0):
        return self._askNumber(
            _(u'Use what maximum size for each solid block?') + u'\n' + _(
                u"Enter '0' to use 7z's default size."), prompt=u'MB',
            title=title, value=value, min=0, max=102400)

    def _pack(self, archive_path, installer, project, release=False):
        #--Archive configuration options
        blockSize = None
        if archive_path.cext in archives.noSolidExts:
            isSolid = False
        else:
            if not u'-ms=' in bass.inisettings['7zExtraCompressionArguments']:
                isSolid = self._askYes(_(u'Use solid compression for %s?')
                                       % archive_path.s, default=False)
                if isSolid:
                    blockSize = self._promptSolidBlockSize(title=self._text)
            else:
                isSolid = True
        with balt.Progress(_(u'Packing to Archive...'),
                           u'\n' + u' ' * 60) as progress:
            #--Pack
            installer.packToArchive(project, archive_path, isSolid, blockSize,
                                    SubProgress(progress, 0, 0.8),
                                    release=release)
            #--Add the new archive to Bash
            iArchive = self.idata.refresh_installer(archive_path,
                is_project=False, progress=progress,
                install_order=installer.order + 1, do_refresh=True)
            iArchive.blockSize = blockSize
        self.window.RefreshUI(detail_item=archive_path)

    def _askFilename(self, message, filename):
        """:rtype: bolt.Path"""
        result = self._askText(message, title=self.dialogTitle,
                               default=filename)
        if not result: return
        archive_path = GPath(result).tail
        #--Error checking
        if not archive_path.s:
            self._showWarning(_(u'%s is not a valid archive name.') % result)
            return
        if self.idata.store_dir.join(archive_path).isdir():
            self._showWarning(_(u'%s is a directory.') % archive_path.s)
            return
        if archive_path.cext not in archives.writeExts:
            self._showWarning(
                _(u'The %s extension is unsupported. Using %s instead.') % (
                    archive_path.cext, archives.defaultExt))
            archive_path = GPath(archive_path.sroot + archives.defaultExt).tail
        if archive_path in self.idata:
            if not self._askYes(_(u'%s already exists. Overwrite it?') %
                    archive_path.s, title=self.dialogTitle, default=False): return
        return archive_path

class _SingleInstallable(OneItemLink, _InstallerLink):

    def _enable(self):
        return super(_SingleInstallable, self)._enable() and bool(
            self.idata.filterInstallables(self.selected))

class _SingleProject(OneItemLink, _InstallerLink):

    def _enable(self):
        return super(_SingleProject, self)._enable() and isinstance(
            self._selected_info, bosh.InstallerProject)

class _RefreshingLink(_SingleInstallable):
    _overrides_skips = False

    @balt.conversation
    def Execute(self):
        dest_src = self._selected_info.refreshDataSizeCrc()
        with balt.Progress(title=_(u'Override Skips')) as progress:
            if self._overrides_skips:
                self.idata.update_for_overridden_skips(set(dest_src), progress)
            self.idata.irefresh(what='NS', progress=progress)
        self.window.RefreshUI()

class _InstallLink(_InstallerLink):

    def _enable(self):
        self._installables = self.idata.filterInstallables(self.selected)
        return bool(self._installables)

#------------------------------------------------------------------------------
class Installer_EditWizard(_SingleInstallable):
    """Edit the wizard.txt associated with this project"""
    help = _(u"Edit the wizard.txt associated with this project.")

    def _initData(self, window, selection):
        super(Installer_EditWizard, self)._initData(window, selection)
        self._text = _(u'View Wizard...') if self.isSingleArchive() else _(
            u'Edit Wizard...')

    def _enable(self):
        return super(Installer_EditWizard, self)._enable() and bool(
            self._selected_info.hasWizard)

    def Execute(self): self._selected_info.open_wizard()

class Installer_Wizard(OneItemLink, _InstallerLink):
    """Runs the install wizard to select subpackages and esp/m filtering"""
    parentWindow = ''
    help = _(u"Run the install wizard.")

    def __init__(self, bAuto):
        super(Installer_Wizard, self).__init__()
        self.bAuto = bAuto
        self._text = _(u'Auto Wizard') if self.bAuto else _(u'Wizard')

    def _enable(self):
        isSingle = super(Installer_Wizard, self)._enable()
        return isSingle and self._selected_info.hasWizard != False

    @balt.conversation
    def Execute(self):
        with balt.BusyCursor():
            installer = self._selected_info
            subs = []
            oldRemaps = copy.copy(installer.remaps)
            installer.remaps = {} # FIXME(ut): only clear if not cancelled ?
            idetails = self.iPanel.detailsPanel
            idetails.refreshCurrent(installer)
            for index in xrange(idetails.gSubList.GetCount()):
                subs.append(idetails.gSubList.GetString(index))
            default, pageSize, pos = self._get_size_and_pos()
            try:
                wizard = InstallerWizard(self.window, self._selected_info,
                                         self.bAuto, subs, pageSize, pos)
            except CancelError:
                return
            balt.ensureDisplayed(wizard)
        ret = wizard.Run()
        self._save_size_pos(default, ret)
        if ret.Canceled:
            installer.remaps = oldRemaps
            idetails.refreshCurrent(installer)
            return
        #Check the sub-packages that were selected by the wizard
        installer.resetAllEspmNames()
        for index in xrange(idetails.gSubList.GetCount()):
            select = installer.subNames[index + 1] in ret.SelectSubPackages
            idetails.gSubList.Check(index, select)
            installer.subActives[index + 1] = select
        idetails.refreshCurrent(installer)
        #Check the espms that were selected by the wizard
        espms = idetails.gEspmList.GetStrings()
        espms = [x.replace(u'&&',u'&') for x in espms]
        installer.espmNots = set()
        for index, espm in enumerate(idetails.espms):
            if espms[index] in ret.SelectEspms:
                idetails.gEspmList.Check(index, True)
            else:
                idetails.gEspmList.Check(index, False)
                installer.espmNots.add(espm)
        idetails.refreshCurrent(installer)
        #Rename the espms that need renaming
        for oldName in ret.RenameEspms:
            installer.setEspmName(oldName, ret.RenameEspms[oldName])
        idetails.refreshCurrent(installer)
        #Install if necessary
        ui_refresh = [False, False]
        try:
            if ret.Install:
                if self._selected_info.isActive: #If it's currently installed, anneal
                    title, doIt = _(u'Annealing...'), self.idata.bain_anneal
                else: #Install, if it's not installed
                    title, doIt = _(u'Installing...'), self.idata.bain_install
                with balt.Progress(title, u'\n'+u' '*60) as progress:
                    doIt(self.selected, ui_refresh, progress)
            self._apply_tweaks(installer, ret, ui_refresh)
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

    def _apply_tweaks(self, installer, ret, ui_refresh):
        #Build any ini tweaks
        manuallyApply = []  # List of tweaks the user needs to  manually apply
        lastApplied = None
        new_targets = {}
        for iniFile, wizardEdits in ret.IniEdits.iteritems():
            outFile = bass.dirs['tweaks'].join(u'%s - Wizard Tweak [%s].ini' %
                (installer.archive, iniFile.sbody))
            with outFile.open('w') as out:
                for line in generateTweakLines(wizardEdits, iniFile):
                    out.write(line + u'\n')
            bosh.iniInfos.add_info(outFile.tail) # add it to the iniInfos
            bosh.iniInfos.table.setItem(outFile.tail, 'installer',
                                        installer.archive)
            # trigger refresh UI
            ui_refresh[1] = True
            # We wont automatically apply tweaks to anything other than
            # Oblivion.ini or an ini from this installer
            game_ini = bosh.get_game_ini(iniFile, is_abs=False)
            if game_ini:
                target_path = game_ini.abs_path
                target_ini_file = game_ini
            else: # suppose that the target ini file is in the Data/ dir
                target_path = bass.dirs['mods'].join(iniFile)
                new_targets[target_path.stail] = target_path
                if not (iniFile.s in installer.ci_dest_sizeCrc and ret.Install):
                    # Can only automatically apply ini tweaks if the ini was
                    # actually installed.  Since BAIN is setup to not auto
                    # install after the wizard, we'll show a message telling
                    # the User what tweaks to apply manually.
                    manuallyApply.append((outFile, iniFile))
                    continue
                target_ini_file = bosh.BestIniFile(target_path)
            if INIList.apply_tweaks((bosh.iniInfos[outFile.tail],),
                                    target_ini_file):
                lastApplied = outFile.tail
        #--Refresh after all the tweaks are applied
        if lastApplied is not None:
            target_updated = bosh.INIInfos.update_targets(new_targets)
            if BashFrame.iniList is not None:
                BashFrame.iniList.panel.detailsPanel.set_choice(
                    target_path.stail, reset_choices=target_updated)
                BashFrame.iniList.panel.ShowPanel(refresh_target=True,
                    focus_list=False, detail_item=lastApplied)
            ui_refresh[1] = False
        if len(manuallyApply) > 0:
            message = balt.fill(_(
                u'The following INI Tweaks were not automatically applied.  '
                u'Be sure to apply them after installing the package.'))
            message += u'\n\n'
            message += u'\n'.join([u' * ' + x[0].stail + u'\n   TO: ' + x[1].s
                                   for x in manuallyApply])
            self._showInfo(message)

    @staticmethod
    def _save_size_pos(default, ret):
        # Sanity checks on returned size/position
        if not isinstance(ret.Pos, balt.wxPoint):
            deprint(_(
                u'Returned Wizard position (%s) was not a wx.Point (%s), '
                u'reverting to default position.') % (ret.Pos, type(ret.Pos)))
            ret.Pos = balt.defPos
        if not isinstance(ret.PageSize, balt.wxSize):
            deprint(_(u'Returned Wizard size (%s) was not a wx.Size (%s), '
                      u'reverting to default size.') % (
                        ret.PageSize, type(ret.PageSize)))
            ret.PageSize = tuple(default)
        bass.settings['bash.wizard.size'] = (ret.PageSize[0], ret.PageSize[1])
        bass.settings['bash.wizard.pos'] = (ret.Pos[0], ret.Pos[1])

    @staticmethod
    def _get_size_and_pos():
        saved = bass.settings['bash.wizard.size']
        default = settingDefaults['bash.wizard.size']
        pos = bass.settings['bash.wizard.pos']
        # Sanity checks on saved size/position
        if not isinstance(pos, tuple) or len(pos) != 2:
            deprint(_(u'Saved Wizard position (%s) was not a tuple (%s), '
                      u'reverting to default position.') % (pos, type(pos)))
            pos = balt.defPos
        if not isinstance(saved, tuple) or len(saved) != 2:
            deprint(_(u'Saved Wizard size (%s) was not a tuple (%s), '
                      u'reverting to default size.') % (saved, type(saved)))
            pageSize = tuple(default)
        else:
            pageSize = (max(saved[0], default[0]), max(saved[1], default[1]))
        return default, pageSize, pos

class Installer_OpenReadme(OneItemLink, _InstallerLink):
    """Opens the installer's readme if BAIN can find one."""
    _text = _(u'Open Readme')
    help = _(u"Open the installer's readme if BAIN can find one")

    def _enable(self):
        isSingle = super(Installer_OpenReadme, self)._enable()
        return isSingle and bool(self._selected_info.hasReadme)

    def Execute(self): self._selected_info.open_readme()

#------------------------------------------------------------------------------
class Installer_Anneal(_InstallLink):
    """Anneal all packages."""
    _text = _(u'Anneal')
    help = _(u"Anneal all packages.")

    def Execute(self):
        ui_refresh = [False, False]
        try:
            with balt.Progress(_(u"Annealing..."),u'\n'+u' '*60) as progress:
                self.idata.bain_anneal(self._installables, ui_refresh,
                                       progress)
        except (CancelError,SkipError):
            pass
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

class Installer_Duplicate(OneItemLink, _InstallerLink):
    """Duplicate selected Installer."""
    _text = _(u'Duplicate...')

    def _initData(self, window, selection):
        super(Installer_Duplicate, self)._initData(window, selection)
        self.help = _(u"Duplicate selected %(installername)s.") % (
            {'installername': self._selected_item})

    def _enable(self):
        isSingle = super(Installer_Duplicate, self)._enable()
        return isSingle and not isinstance(self._selected_info,
                                           bosh.InstallerMarker)

    @balt.conversation
    def Execute(self):
        """Duplicate selected Installer."""
        curName = self._selected_item
        isdir = self.idata.store_dir.join(curName).isdir()
        if isdir: root,ext = curName,u''
        else: root,ext = curName.root, curName.ext
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
        if self.idata.store_dir.join(curName).isfile() and curName.cext != newName.cext:
            self._showWarning(_(u"%s does not have correct extension (%s).")
                              % (newName.s,curName.ext))
            return
        #--Duplicate
        with balt.BusyCursor():
            self.idata.copy_installer(curName,newName)
            self.idata.irefresh(what='N')
        self.window.RefreshUI(detail_item=newName)

class Installer_Hide(_InstallerLink, UIList_Hide):
    """Hide selected Installers."""
    _text = _(u'Hide...')
    help = _(
        u"Hide selected installer(s). No installer markers should be selected")

    def _enable(self):
        return not any(map(lambda inf: isinstance(inf, bosh.InstallerMarker),
                       self.iselected_infos()))

class Installer_Rename(UIList_Rename, _InstallerLink):
    """Renames files by pattern."""
    help = _(u"Rename selected installer(s).") + u'  ' + _(
        u'All selected installers must be of the same type')

    def _enable(self):
        ##Only enable if all selected items are of the same type
        firstItem = next(self.iselected_infos())
        return all(map(lambda inf: isinstance(inf, type(firstItem)),
                       self.iselected_infos()))

class Installer_HasExtraData(CheckLink, _RefreshingLink):
    """Toggle hasExtraData flag on installer."""
    _text = _(u'Has Extra Directories')
    help = _(u"Allow installation of files in non-standard directories.")

    def _check(self):
        return self._enable() and self._selected_info.hasExtraData

    def Execute(self):
        """Toggle hasExtraData installer attribute"""
        self._selected_info.hasExtraData ^= True
        super(Installer_HasExtraData, self).Execute()

class Installer_OverrideSkips(CheckLink, _RefreshingLink):
    """Toggle overrideSkips flag on installer."""
    _text = _(u'Override Skips')

    def _initData(self, window, selection):
        super(Installer_OverrideSkips, self)._initData(window, selection)
        self.help = _(
            u"Override global file type skipping for %(installername)s.") % (
                {'installername': self._selected_item}) + u'  '+ _(u'BETA!')

    def _check(self):
        return self._enable() and self._selected_info.overrideSkips

    def Execute(self):
        self._selected_info.overrideSkips ^= True
        self._overrides_skips = self._selected_info.overrideSkips
        super(Installer_OverrideSkips, self).Execute()

class Installer_SkipRefresh(CheckLink, _SingleProject):
    """Toggle skipRefresh flag on project."""
    _text = _(u"Don't Refresh")
    help = _(u"Don't automatically refresh project.")

    def _check(self): return self._enable() and self._selected_info.skipRefresh

    def Execute(self):
        """Toggle skipRefresh project attribute and refresh the project if
        skipRefresh is set to False."""
        installer = self._selected_info
        installer.skipRefresh ^= True
        if not installer.skipRefresh:
            installer.refreshBasic(progress=None,
                                   recalculate_project_crc=False)
            installer.refreshStatus(self.idata)
            self.idata.irefresh(what='N')
            self.window.RefreshUI()

class Installer_Install(_InstallLink):
    """Install selected packages."""
    mode_title = {'DEFAULT': _(u'Install'), 'LAST': _(u'Install Last'),
                  'MISSING': _(u'Install Missing')}

    def __init__(self,mode='DEFAULT'):
        super(Installer_Install, self).__init__()
        self.mode = mode
        self._text = self.mode_title[self.mode]

    @balt.conversation
    def Execute(self):
        ui_refresh = [False, False]
        try:
            with balt.Progress(_(u'Installing...'),u'\n'+u' '*60) as progress:
                last = (self.mode == 'LAST')
                override = (self.mode != 'MISSING')
                try:
                    tweaks = self.idata.bain_install(self._installables,
                        ui_refresh, progress, last, override)
                except (CancelError,SkipError):
                    pass
                except StateError as e:
                    self._showError(u'%s'%e)
                else: # no error occurred
                    self._warn_mismatched_ini_tweaks_created(tweaks)
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

    def _warn_mismatched_ini_tweaks_created(self, tweaks):
        if tweaks:
            msg = _(u'The following INI Tweaks were created, because the '
                u'existing INI was different than what BAIN installed:') + \
                u'\n' + u'\n'.join([u' * %s\n' % x.stail for (x, y) in tweaks])
            self._showInfo(msg, title=_(u'INI Tweaks'))

class Installer_ListStructure(OneItemLink, _InstallerLink): # Provided by Waruddar
    """Copies folder structure of installer to clipboard."""
    _text = _(u"List Structure...")

    def _enable(self):
        isSingle = super(Installer_ListStructure, self)._enable()
        return isSingle and not isinstance(self._selected_info,
                                           bosh.InstallerMarker)

    @balt.conversation ##: no use ! _showLog returns immediately
    def Execute(self):
        source_list_txt = self._selected_info.listSource()
        #--Get masters list
        balt.copyToClipboard(source_list_txt)
        self._showLog(source_list_txt, title=_(u'Package Structure'),
                      fixedFont=False)

class Installer_Move(_InstallerLink):
    """Moves selected installers to desired spot."""
    _text = _(u'Move To...')

    @balt.conversation
    def Execute(self):
        curPos = min(inf.order for inf in self.iselected_infos())
        message = (_(u'Move selected archives to what position?') + u'\n' +
                   _(u'Enter position number.') + u'\n' +
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
        elif newPos < 0: newPos = len(self.idata)
        self.idata.moveArchives(self.selected,newPos)
        self.idata.irefresh(what='N')
        self.window.RefreshUI(
            detail_item=self.iPanel.detailsPanel.displayed_item)

class Installer_Open(balt.UIList_OpenItems, _InstallerLink):
    """Open selected file(s)."""

    def _initData(self, window, selection):
        super(Installer_Open, self)._initData(window, selection)
        self.selected = [k for k, v in self.iselected_pairs() if
                         not isinstance(v, bosh.InstallerMarker)]

    def _enable(self): return bool(self.selected)

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
    _text = _(bush.game.nexusName)
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
    _text = _(u'Google...')
    key = 'bash.installers.opensearch.continue'
    askTitle = _(u'Open a search')
    message = _(u"Open a search for this on Google?")

    def _url(self):
        return u'http://www.google.com/search?hl=en&q=' + u'+'.join(
            re.split(ur'\W+|_+', self.mod_url_id))

class Installer_OpenTESA(_Installer_OpenAt):
    regexp = bosh.reTESA
    _text = _(u'TES Alliance...')
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
    _text = _(u'Refresh')
    help = _(u'Rescan selected Installer(s)') + u'.  ' + _(
        u'Ignores skip refresh flag on projects')

    def __init__(self, calculate_projects_crc=True):
        super(Installer_Refresh, self).__init__()
        self.calculate_projects_crc = calculate_projects_crc
        if not calculate_projects_crc:
            self._text = _(u'Quick Refresh')
            self.help = Installer_Refresh.help + u'.  ' + _(
                u'Will not recalculate cached crcs of files in a project')

    def _enable(self): return bool(self.idata.filterPackages(self.selected))

    @balt.conversation
    def Execute(self):
        self.window.rescanInstallers(self.selected, abort=True,
                            calculate_projects_crc=self.calculate_projects_crc)

class Installer_SkipVoices(CheckLink, _RefreshingLink):
    """Toggle skipVoices flag on installer."""
    _text = _(u'Skip Voices')

    def _initData(self, window, selection):
        super(Installer_SkipVoices, self)._initData(window, selection)
        self.help = _(u"Skip over any voice files in %(installername)s") % (
                    {'installername': self._selected_item})

    def _check(self): return self._enable() and self._selected_info.skipVoices

    def Execute(self):
        self._selected_info.skipVoices ^= True
        super(Installer_SkipVoices, self).Execute()

class Installer_Uninstall(_InstallLink):
    """Uninstall selected Installers."""
    _text = _(u'Uninstall')
    help = _(u'Uninstall selected Installer(s)')

    @balt.conversation
    def Execute(self):
        """Uninstall selected Installers."""
        ui_refresh = [False, False]
        try:
            with balt.Progress(_(u"Uninstalling..."),u'\n'+u' '*60) as progress:
                self.idata.bain_uninstall(self._installables, ui_refresh,
                                          progress)
        except (CancelError,SkipError): # now where could this be raised from ?
            pass
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

class Installer_CopyConflicts(_SingleInstallable):
    """For Modders only - copy conflicts to a new project."""
    _text = _(u'Copy Conflicts to Project')
    help = _(u'Copy all files that conflict with the selected installer into a'
             u' new project') + u'.  ' + _(
        u'Conflicts with inactive installers are included')

    @balt.conversation
    def Execute(self):
        """Copy files that conflict with this installer from all other
        installers to a project."""
        srcConflicts = set()
        packConflicts = []
        src_sizeCrc = self._selected_info.ci_dest_sizeCrc # CIstr -> (int, int)
        def _ok(msg): self._showOk(msg % self._selected_item)
        if not src_sizeCrc:
            return _ok(_(u'No files to install for %s'))
        src_order = self._selected_info.order
        with balt.Progress(_(u"Scanning Packages..."),
                           u'\n' + u' ' * 60) as progress:
            progress.setFull(len(self.idata))
            numFiles = 0
            destDir = GPath(u"Conflicts - %03d" % src_order)
            for i,(package, installer) in enumerate(self.idata.sorted_pairs()):
                curConflicts = set()
                progress(i, _(u"Scanning Packages...") + u'\n' + package.s)
                for z, y in installer.refreshDataSizeCrc().iteritems():
                    if z in src_sizeCrc and installer.ci_dest_sizeCrc[z] != \
                            src_sizeCrc[z]:
                        curConflicts.add(y)
                        srcConflicts.add(src_sizeCrc[z])
                numFiles += len(curConflicts)
                if curConflicts: packConflicts.append(
                    (installer.order, package, curConflicts))
            srcConflicts = set( # we need the paths rel to the archive not Data
                src for src, size, crc in self._selected_info.fileSizeCrcs if
                (size,crc) in srcConflicts)
            numFiles += len(srcConflicts)
        if not numFiles:
            return _ok(_(u'No conflicts detected for %s'))
        ijoin = self.idata.store_dir.join
        def _copy_conflicts(curFile):
            inst = self.idata[package]
            if isinstance(inst, bosh.InstallerProject):
                for src in curConflicts:
                    srcFull = ijoin(package, src)
                    destFull = ijoin(destDir, g_path, src)
                    if srcFull.exists():
                        progress(curFile, self._selected_item.s + u'\n' + _(
                            u'Copying files...') + u'\n' + src)
                        srcFull.copyTo(destFull)
                        curFile += 1
            else:
                unpack_dir = inst.unpackToTemp(curConflicts,
                    SubProgress(progress, curFile, curFile + len(curConflicts),
                                len(curConflicts)))
                unpack_dir.moveTo(ijoin(destDir, g_path))
                curFile += len(curConflicts)
            return curFile
        with balt.Progress(_(u"Copying Conflicts..."),
                           u'\n' + u' ' * 60) as progress:
            progress.setFull(numFiles)
            curFile = 0
            g_path = package = self._selected_item
            curConflicts = srcConflicts
            curFile = _copy_conflicts(curFile)
            for order,package,curConflicts in packConflicts:
                g_path = GPath(u"%03d - %s" % (
                    order if order < src_order else order + 1, package.s))
                curFile = _copy_conflicts(curFile)
        self.idata.refresh_installer(destDir, is_project=True, progress=None,
                                     install_order=src_order + 1,
                                     do_refresh=True)
        self.window.RefreshUI(detail_item=destDir)

#------------------------------------------------------------------------------
# InstallerDetails Espm Links -------------------------------------------------
#------------------------------------------------------------------------------
class _Installer_Details_Link(EnabledLink):

    def _enable(self): return len(self.window.espms) != 0

    def _initData(self, window, selection):
        """:type window: bosh.InstallersDetails
        :type selection: int"""
        super(_Installer_Details_Link, self)._initData(window, selection)
        self._installer = self.window.file_info

class Installer_Espm_SelectAll(_Installer_Details_Link):
    """Select All Esp/ms in installer for installation."""
    _text = _(u'Select All')

    def Execute(self):
        self._installer.espmNots = set()
        for i in range(len(self.window.espms)):
            self.window.gEspmList.Check(i, True)
        self.window.refreshCurrent(self._installer)

class Installer_Espm_DeselectAll(_Installer_Details_Link):
    """Deselect All Esp/ms in installer for installation."""
    _text = _(u'Deselect All')

    def Execute(self):
        espmNots = self._installer.espmNots = set()
        for i in range(len(self.window.espms)):
            self.window.gEspmList.Check(i, False)
            espm =GPath(self.window.gEspmList.GetString(i).replace(u'&&',u'&'))
            espmNots.add(espm)
        self.window.refreshCurrent(self._installer)

class Installer_Espm_Rename(_Installer_Details_Link):
    """Changes the installed name for an Esp/m."""
    _text = _(u'Rename...')

    def _enable(self): return self.selected != -1

    def Execute(self):
        curName = self.window.gEspmList.GetString(self.selected).replace(u'&&',
                                                                         u'&')
        if curName[0] == u'*':
            curName = curName[1:]
        _file = GPath(curName)
        newName = self._askText(_(u"Enter new name (without the extension):"),
                                title=_(u"Rename Esp/m"), default=_file.sbody)
        if not newName: return
        if newName in self.window.espms: return
        self._installer.setEspmName(curName, newName + _file.cext)
        self.window.refreshCurrent(self._installer)

class Installer_Espm_Reset(_Installer_Details_Link):
    """Resets the installed name for an Esp/m."""
    _text = _(u'Reset Name')

    def _enable(self):
        if self.selected == -1: return False
        curName = self.window.gEspmList.GetString(self.selected).replace(u'&&',
                                                                         u'&')
        if curName[0] == u'*': curName = curName[1:]
        self.curName = curName
        return self._installer.isEspmRenamed(curName)

    def Execute(self):
        self._installer.resetEspmName(self.curName)
        self.window.refreshCurrent(self._installer)

class Installer_Espm_ResetAll(_Installer_Details_Link):
    """Resets all renamed Esp/ms."""
    _text = _(u'Reset All Names')

    def Execute(self):
        self._installer.resetAllEspmNames()
        self.window.refreshCurrent(self._installer)

class Installer_Espm_List(_Installer_Details_Link):
    """Lists all Esp/ms in installer for user information/w/e."""
    _text = _(u'List Esp/ms')

    def Execute(self):
        subs = (_(u'Esp/m List for %s:') % self._installer.archive +
                u'\n[spoiler]\n')
        espm_list = self.window.gEspmList
        for index in range(espm_list.GetCount()):
            subs += [u'   ',u'** '][espm_list.IsChecked(index)] + \
                    espm_list.GetString(index) + '\n'
        subs += u'[/spoiler]'
        balt.copyToClipboard(subs)
        self._showLog(subs, title=_(u'Esp/m List'), fixedFont=False)

#------------------------------------------------------------------------------
# InstallerDetails Subpackage Links -------------------------------------------
#------------------------------------------------------------------------------
class _Installer_Subs(_Installer_Details_Link):
    def _enable(self): return self.window.gSubList.GetCount() > 1

class Installer_Subs_SelectAll(_Installer_Subs):
    """Select All sub-packages in installer for installation."""
    _text = _(u'Select All')

    def Execute(self):
        for index in xrange(self.window.gSubList.GetCount()):
            self.window.gSubList.Check(index, True)
            self._installer.subActives[index + 1] = True
        self.window.refreshCurrent(self._installer)

class Installer_Subs_DeselectAll(_Installer_Subs):
    """Deselect All sub-packages in installer for installation."""
    _text = _(u'Deselect All')

    def Execute(self):
        for index in xrange(self.window.gSubList.GetCount()):
            self.window.gSubList.Check(index, False)
            self._installer.subActives[index + 1] = False
        self.window.refreshCurrent(self._installer)

class Installer_Subs_ToggleSelection(_Installer_Subs):
    """Toggles selection state of all sub-packages in installer for
    installation."""
    _text = _(u'Toggle Selection')

    def Execute(self):
        for index in xrange(self.window.gSubList.GetCount()):
            check = not self._installer.subActives[index+1]
            self.window.gSubList.Check(index, check)
            self._installer.subActives[index + 1] = check
        self.window.refreshCurrent(self._installer)

class Installer_Subs_ListSubPackages(_Installer_Subs):
    """Lists all sub-packages in installer for user information/w/e."""
    _text = _(u'List Sub-packages')

    def Execute(self):
        subs = _(u'Sub-Packages List for %s:') % self._installer.archive
        subs += u'\n[spoiler]\n'
        for index in xrange(self.window.gSubList.GetCount()):
            subs += [u'   ', u'** '][self.window.gSubList.IsChecked(
                index)] + self.window.gSubList.GetString(index) + u'\n'
        subs += u'[/spoiler]'
        balt.copyToClipboard(subs)
        self._showLog(subs, title=_(u'Sub-Package Lists'), fixedFont=False)

#------------------------------------------------------------------------------
# InstallerArchive Links ------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerArchive_Unpack(AppendableLink, _InstallerLink):
    """Unpack installer package(s) to Project(s)."""
    _text = _(u'Unpack to Project(s)...')
    help = _(u'Unpack installer package(s) to Project(s)')

    def _append(self, window):
        self.selected = window.GetSelected() # append runs before _initData
        self.window = window # and the idata access is via self.window
        return all(map(lambda inf: isinstance(inf, bosh.InstallerArchive),
                       self.iselected_infos()))

    @balt.conversation
    def Execute(self):
        #--Copy to Build
        with balt.Progress(_(u"Unpacking to Project..."),u'\n'+u' '*60) as progress:
            projects = []
            for archive, installer in self.idata.sorted_pairs(self.selected):
                project = archive.root
                if self.isSingleArchive():
                    result = self._askText(_(u"Unpack %s to Project:") % archive.s,
                                           default=project.s)
                    if not result: return
                    #--Error checking
                    project = GPath(result).tail
                    if not project.s or project.cext in archives.readExts:
                        self._showWarning(_(u"%s is not a valid project name.") % result)
                        return
                    if self.idata.store_dir.join(project).isfile():
                        self._showWarning(_(u"%s is a file.") % project.s)
                        return
                if project in self.idata:
                    if not self._askYes(
                        _(u"%s already exists. Overwrite it?") % project.s,
                        default=False): continue
                installer.unpackToProject(project,SubProgress(progress,0,0.8))
                self.idata.refresh_installer(project, is_project=True,
                    progress=SubProgress(progress, 0.8, 0.99),
                    install_order=installer.order + 1, do_refresh=False)
                projects.append(project)
            if not projects: return
            self.idata.irefresh(what='NS')
            self.window.RefreshUI(detail_item=projects[-1]) # all files ? can status of others change ?
            self.window.SelectItemsNoCallback(projects)

#------------------------------------------------------------------------------
# InstallerProject Links ------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerProject_OmodConfig(_SingleProject):
    """Projects only. Allows you to read/write omod configuration info."""
    _text = _(u'Omod Info...')
    help = _(u'Projects only. Allows you to read/write omod configuration info')

    def Execute(self):
        (InstallerProject_OmodConfigDialog(self.window, self.idata,
                                           self._selected_item)).Show()

#------------------------------------------------------------------------------
class InstallerProject_Sync(_SingleProject):
    """Synchronize the project with files from the Data directory."""
    _text = _(u'Sync from Data')
    help = _(u'Synchronize the project with files from the Data directory') + \
        u'.  ' + _(u'Currently only for projects (not archives)')

    def _enable(self):
        if not super(InstallerProject_Sync, self)._enable(): return False
        return bool(self._selected_info.missingFiles or
                    self._selected_info.mismatchedFiles)

    def Execute(self):
        missing = self._selected_info.missingFiles
        mismatched = self._selected_info.mismatchedFiles
        message = (_(u'Update %s according to data directory?') + u'\n' + _(
            u'Files to delete:') + u'%d\n' + _(
            u'Files to update:') + u'%d') % (
                      self._selected_item.s, len(missing), len(mismatched))
        if not self._askWarning(message, title=self._text): return
        #--Sync it, baby!
        with balt.Progress(self._text, u'\n' + u' ' * 60) as progress:
            progress(0.1,_(u'Updating files.'))
            self._selected_info.syncToData(missing | mismatched)
            self._selected_info.refreshBasic(SubProgress(progress, 0.1, 0.99))
            self.idata.irefresh(what='NS')
            self.window.RefreshUI()

#------------------------------------------------------------------------------
class InstallerProject_Pack(_SingleProject):
    """Pack project to an archive."""
    _text = dialogTitle = _(u'Pack to Archive...')
    help = _(u'Pack project to an archive')
    release = False

    @balt.conversation
    def Execute(self):
        #--Generate default filename from the project name and the default extension
        archive = GPath(self._selected_item.s + archives.defaultExt)
        #--Confirm operation
        archive = self._askFilename(
            message=_(u'Pack %s to Archive:') % self._selected_item.s,
            filename=archive.s)
        if not archive: return
        self._pack(archive, self._selected_info, self._selected_item,
                   release=self.__class__.release)

#------------------------------------------------------------------------------
class InstallerProject_ReleasePack(InstallerProject_Pack):
    """Pack project to an archive for release. Ignores dev files/folders."""
    _text = _(u'Package for Release...')
    help = _(
        u'Pack project to an archive for release. Ignores dev files/folders')
    release = True

#------------------------------------------------------------------------------
class _InstallerConverter_Link(_InstallerLink):

    @balt.conversation
    def _check_identical_content(self, message):
        # check that no installers with identical content are selected, this
        # leads to undefined behavior
        crcs_dict = defaultdict(set)
        for inst in self.iselected_infos():
            crcs_dict[inst.crc].add(inst)
        duplicates = []
        for crc_, installers in crcs_dict.iteritems():
            if len(installers) > 1:
                duplicates.append((crc_, u'  \n* ' + u'  \n* '.join(
                    sorted(x.archive for x in installers))))
        if duplicates:
            msg = _(u'Installers with identical content selected:') + u'\n'
            msg += u'\n'.join(
                sorted(u'CRC: %08X%s' % (k, v) for k, v in duplicates))
            if message: msg += u'\n' + message
            self._showError(msg, _(u'Identical installers content'))
            return True
        return False

class InstallerConverter_Apply(_InstallerConverter_Link):
    """Apply a Bain Conversion File."""
    dialogTitle = _(u'Apply BCF...') # title used in dialog

    def __init__(self,converter,selected):
        super(InstallerConverter_Apply, self).__init__()
        self.converter = converter
        #--Add asterisks to indicate the number of unselected archives that the BCF uses
        self.dispName = self.converter.fullPath.sbody
        self._text = self.dispName
        self._selected = selected

    @balt.conversation
    def Execute(self):
        if self._check_identical_content(
                _(u'Please only select the installers this converter was made '
                  u'for.')):
            return
        # all installers that this converter needs are present and unique
        crc_installer = dict((x.crc, x) for x in self.iselected_infos())
        #--Generate default filename from BCF filename
        defaultFilename = self.converter.fullPath.sbody[:-4] + archives\
            .defaultExt
        #--List source archives
        message = _(u'Using:') + u'\n* ' + u'\n* '.join(sorted(
            u'(%08X) - %s' % (x, crc_installer[x].archive) for x in
            self.converter.srcCRCs)) + u'\n'
        #--Ask for an output filename
        destArchive = self._askFilename(message, filename=defaultFilename)
        if not destArchive: return
        with balt.Progress(_(u'Converting to Archive...'),u'\n'+u' '*60) as progress:
            #--Perform the conversion
            msg = u'%s: ' % destArchive.s + _(
                u'An error occurred while applying an Auto-BCF.')
            msg += _(u'Maybe the BCF was packed for another installer ?')
            new_archive_order = self.idata[self.selected[-1]].order + 1
            try:
                self.idata.apply_converter(self.converter, destArchive,
                    progress, msg, show_warning=self._showWarning,
                    position=new_archive_order, crc_installer=crc_installer)
            except StateError:
                return
        self.window.RefreshUI(detail_item=destArchive)

#------------------------------------------------------------------------------
class InstallerConverter_ApplyEmbedded(_InstallerLink):
    _text = _(u'Embedded BCF')
    dialogTitle = _(u'Apply BCF...')

    @balt.conversation
    def Execute(self):
        name, archive = next(self.iselected_pairs()) # first selected pair
        #--Ask for an output filename
        dest = self._askFilename(_(u'Output file:'), filename=name.stail)
        if not dest: return
        with balt.Progress(_(u'Extracting BCF...'),u'\n'+u' '*60) as progress:
            destinations, converted = self.idata.applyEmbeddedBCFs(
                [archive], [dest], progress)
            if not destinations: return # destinations == [dest] if all was ok
        self.window.RefreshUI(detail_item=dest)

class InstallerConverter_Create(_InstallerConverter_Link):
    """Create BAIN conversion file."""
    dialogTitle = _(u'Create BCF...') # title used in dialog
    _text = _(u'Create...')

    def Execute(self):
        if self._check_identical_content(
                _(u'Please only select installers that are needed.')):
            return
        # all installers that this converter needs are unique
        crc_installer = dict((x.crc, x) for x in self.iselected_infos())
        #--Generate allowable targets
        readTypes = u'*%s' % u';*'.join(archives.readExts)
        #--Select target archive
        destArchive = self._askOpen(title=_(u"Select the BAIN'ed Archive:"),
                                    defaultDir=self.idata.store_dir,
                                    wildcard=readTypes, mustExist=True)
        if not destArchive: return
        #--Error Checking
        BCFArchive = destArchive = destArchive.tail
        if not destArchive.s or destArchive.cext not in archives.readExts:
            self._showWarning(_(u'%s is not a valid archive name.') % destArchive.s)
            return
        if destArchive not in self.idata:
            self._showWarning(_(u'%s must be in the Bash Installers directory.') % destArchive.s)
            return
        if BCFArchive.csbody[-4:] != u'-bcf':
            BCFArchive = GPath(BCFArchive.sbody + u'-BCF' + archives.defaultExt).tail
        #--List source archives and target archive
        message = _(u'Convert:')
        message += u'\n* ' + u'\n* '.join(sorted(
            u'(%08X) - %s' % (v.crc, k.s) for k, v in self.iselected_pairs()))
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
        if BCFArchive.cext != archives.defaultExt:
            self._showWarning(_(u"BCF's only support %s. The %s extension will"
                      u" be discarded.") % (
                              archives.defaultExt, BCFArchive.cext))
            BCFArchive = GPath(BCFArchive.sbody + archives.defaultExt).tail
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
        with balt.Progress(_(u'Creating %s...') % BCFArchive.s,u'\n'+u' '*60) as progress:
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
            log(u'  * '+u'\n  * '.join(sorted(u'(%08X) - %s' % (x, crc_installer[x].archive) for x in converter.srcCRCs if x in crc_installer)))
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
            len_missing = len(converter.bcf_missing_files)
            log.setHeader(
                u'. ' + _(u'Contains') + u': %s' % formatInteger(len_missing) +
                (_(u'file'), _(u'files'))[len_missing > 1])
            log(u'  * ' +u'\n  * '.join(sorted(u'%s' % x for x in converter
                                               .bcf_missing_files)))
        if log:
            self._showLog(log.out.getvalue(), title=_(u'BCF Information'))

#------------------------------------------------------------------------------
# Installer Submenus ----------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerOpenAt_MainMenu(balt.MenuLink):
    """Main Open At Menu"""
    _text = _(u"Open at")
    def _enable(self):
        return super(InstallerOpenAt_MainMenu, self)._enable() and isinstance(
            self.window.data_store[self.selected[0]], bosh.InstallerArchive)

class InstallerConverter_ConvertMenu(balt.MenuLink):
    """Apply BCF SubMenu."""
    _text = _(u"Apply")
    def _enable(self):
        """Return False to disable the converter menu, otherwise populate its
        links attribute and return True."""
        linkSet = set()
        del self.links[:]
        #--Converters are linked by CRC, not archive name
        #--So, first get all the selected archive CRCs
        selected = self.selected
        idata = self.window.data_store # InstallersData singleton
        selectedCRCs = set(idata[archive].crc for archive in selected)
        srcCRCs = set(idata.converters_data.srcCRC_converters)
        #--There is no point in testing each converter unless
        #--every selected archive has an associated converter
        if selectedCRCs <= srcCRCs:
            #--Test every converter for every selected archive
            # Only add a link to the converter if all of its required archives
            # are selected
            linkSet = set()
            for installerCRC in selectedCRCs:
               for converter in idata.converters_data.srcCRC_converters[installerCRC]:
                   if converter.srcCRCs <= selectedCRCs:
                       linkSet.add(converter)
        #--If the archive is a single archive with an embedded BCF, add that
        if len(selected) == 1 and idata[selected[0]].hasBCF:
            self.links.append(InstallerConverter_ApplyEmbedded())
        #--Disable the menu if there were no valid converters found
        elif not linkSet:
            return False
        #--Otherwise add each link in alphabetical order, and
        #--indicate the number of additional, unselected archives
        #--that the converter requires
        for converter in sorted(linkSet,key=lambda x:x.fullPath.stail.lower()):
            self.links.append(InstallerConverter_Apply(converter, selected))
        return True

class InstallerConverter_MainMenu(balt.MenuLink):
    """Main BCF Menu"""
    _text = _(u"Conversions")
    def _enable(self):
        for item in self.selected:
            if not isinstance(self.window.data_store[item], bosh.InstallerArchive):
                return False
        return True
