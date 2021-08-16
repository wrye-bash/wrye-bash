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

"""Installer*: Menu items for the __item__ menu of the installer tab. Their
window attribute points to the InstallersList singleton. Check before using
BashFrame.iniList - can be None (ini panel not shown).
Installer_Espm_*: Menu items for the Plugin Filter list in the installer tab.
Their window attribute points to the InstallersPanel singleton.
Installer_Subs_*: Menu items for the Sub-Packages list in the installer tab.
Their window attribute points to the InstallersPanel singleton.
"""

import io
import os
import re
import webbrowser
from collections import defaultdict

from . import Installers_Link, BashFrame, INIList
from .frames import InstallerProject_OmodConfigDialog
from .gui_fomod import InstallerFomod
from .. import bass, bolt, bosh, bush, balt, archives
from ..balt import EnabledLink, CheckLink, AppendableLink, OneItemLink, \
    UIList_Rename, UIList_Hide
from ..belt import InstallerWizard, generateTweakLines
from ..bolt import GPath, SubProgress, LogFile, round_size, text_wrap
from ..bosh import InstallerArchive, InstallerProject
from ..exception import CancelError, SkipError, StateError
from ..gui import BusyCursor, copy_text_to_clipboard

__all__ = [u'Installer_Open', u'Installer_Duplicate',
           u'Installer_OpenSearch',
           u'Installer_OpenTESA', u'Installer_Hide', u'Installer_Rename',
           u'Installer_Refresh', u'Installer_Move', u'Installer_HasExtraData',
           u'Installer_OverrideSkips', u'Installer_SkipVoices',
           u'Installer_SkipRefresh', u'Installer_Wizard',
           u'Installer_EditWizard', u'Installer_OpenReadme',
           u'Installer_Anneal', u'Installer_Install', u'Installer_Uninstall',
           u'InstallerConverter_MainMenu', u'InstallerConverter_Create',
           u'InstallerConverter_ConvertMenu', u'InstallerProject_Pack',
           u'InstallerArchive_Unpack', u'InstallerProject_ReleasePack',
           u'Installer_CopyConflicts', u'Installer_SyncFromData' ,
           u'InstallerProject_OmodConfig', u'Installer_ListStructure',
           u'Installer_Espm_SelectAll', u'Installer_Espm_DeselectAll',
           u'Installer_Espm_List', u'Installer_Espm_Rename',
           u'Installer_Espm_Reset', u'Installer_Espm_ResetAll',
           u'Installer_Subs_SelectAll', u'Installer_Subs_DeselectAll',
           u'Installer_Subs_ToggleSelection',
           u'Installer_Subs_ListSubPackages', u'Installer_OpenNexus',
           u'Installer_ExportAchlist', u'Installer_Espm_JumpToMod',
           u'Installer_Fomod', u'Installer_InstallSmart']

#------------------------------------------------------------------------------
# Installer Links -------------------------------------------------------------
#------------------------------------------------------------------------------
class _InstallerLink(Installers_Link, EnabledLink):
    """Common functions for installer links..."""

    def isSingleArchive(self):
        """Indicates whether or not is single archive."""
        return len(self.selected) == 1 and next(
            self.iselected_infos()).is_archive()

    ##: Methods below should be in archives.py
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
            if not u'-ms=' in bass.inisettings[u'7zExtraCompressionArguments']:
                isSolid = self._askYes(_(u'Use solid compression for %s?')
                                       % archive_path, default=False)
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
            iArchive = InstallerArchive.refresh_installer(
                archive_path, self.idata, progress=progress,
                install_order=installer.order + 1, do_refresh=True)
            iArchive.blockSize = blockSize
        self.window.RefreshUI(detail_item=archive_path)

    def _askFilename(self, message, filename, inst_type=bosh.InstallerArchive,
                     disallow_overwrite=False, no_dir=True,
                     allowed_exts=archives.writeExts, use_default_ext=True):
        """:rtype: bolt.Path"""
        result = self._askText(message, title=self.dialogTitle,
                               default=filename)
        if not result: return
        #--Error checking
        archive_path, msg = inst_type.validate_filename_str(result,
            allowed_exts=allowed_exts, use_default_ext=use_default_ext)
        if msg is None:
            self._showError(archive_path) # it's an error message in this case
            return
        if isinstance(msg, tuple):
            _root, msg = msg
            self._showWarning(msg) # warn on extension change
        if no_dir and self.idata.store_dir.join(archive_path).isdir():
            self._showError(_(u'%s is a directory.') % archive_path)
            return
        if archive_path in self.idata:
            if disallow_overwrite:
                self._showError(_(u'%s already exists.') % archive_path)
                return
            if not self._askYes(
                    _(u'%s already exists. Overwrite it?') % archive_path,
                    title=self.dialogTitle, default=False): return
        return archive_path

class _SingleInstallable(OneItemLink, _InstallerLink):

    def _enable(self):
        return super(_SingleInstallable, self)._enable() and bool(
            self.idata.filterInstallables(self.selected))

class _SingleProject(OneItemLink, _InstallerLink):

    def _enable(self):
        return super(_SingleProject, self)._enable() and \
               self._selected_info.is_project()

class _RefreshingLink(_SingleInstallable):
    _overrides_skips = False

    @balt.conversation
    def Execute(self):
        dest_src = self._selected_info.refreshDataSizeCrc()
        with balt.Progress(title=_(u'Override Skips')) as progress:
            if self._overrides_skips:
                self.idata.update_for_overridden_skips(set(dest_src), progress)
            self.idata.irefresh(what=u'NS', progress=progress)
        self.window.RefreshUI()

class _NoMarkerLink(_InstallerLink):
    """Installer link that does not accept any markers."""
    def _enable(self):
        self._installables = self.idata.filterInstallables(self.selected)
        return bool(self._installables) and super(_NoMarkerLink, self)._enable()

#------------------------------------------------------------------------------
class _Installer_AWizardLink(_InstallerLink):
    """Base class for wizard links."""
    def _perform_install(self, sel_package, ui_refresh):
        if sel_package.is_active: # If it's currently installed, anneal
            title = _(u'Annealing...')
            do_it = self.window.data_store.bain_anneal
        else: # Install if it's not installed
            title = _(u'Installing...')
            do_it = self.window.data_store.bain_install
        with balt.Progress(title, u'\n'+u' '*60) as progress:
            do_it([GPath(sel_package.archive)], ui_refresh, progress)

class Installer_Fomod(_Installer_AWizardLink):
    """Runs the FOMOD installer"""
    _text = _(u'FOMOD Installer...')
    _help = _(u'Run the FOMOD installer.')

    def _enable(self):
        return super(Installer_Fomod, self)._enable() and all(
            i.has_fomod_conf for i in self.iselected_infos())

    @balt.conversation
    def Execute(self):
        ui_refresh = [False, False]
        idetails = self.iPanel.detailsPanel
        try:
            # Use list() since we're going to deselect packages
            for sel_package in list(self.iselected_infos()):
                with BusyCursor():
                    # Select the package we want to install - posts events to
                    # set details and update GUI
                    self.window.SelectItem(GPath(sel_package.archive))
                    try:
                        fm_wizard = InstallerFomod(self.window, sel_package)
                    except CancelError:
                        continue
                    fm_wizard.ensureDisplayed()
                # Run the FOMOD installer
                ret = fm_wizard.run_fomod()
                if ret.canceled:
                    continue
                # Switch the GUI to FOMOD mode and pass selected files to BAIN
                idetails.set_fomod_mode(fomod_enabled=True)
                sel_package.extras_dict[u'fomod_dict'] = ret.install_files
                idetails.refreshCurrent(sel_package)
                if ret.should_install:
                    self._perform_install(sel_package, ui_refresh)
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

class Installer_EditWizard(_SingleInstallable):
    """Edit the wizard.txt associated with this project"""
    _help = _(u'Edit the wizard.txt associated with this project.')

    @property
    def link_text(self):
        return _(u'View Wizard...') if self.isSingleArchive() else _(
            u'Edit Wizard...')

    def _enable(self):
        return super(Installer_EditWizard, self)._enable() and bool(
            self._selected_info.hasWizard)

    def Execute(self): self._selected_info.open_wizard()

class Installer_Wizard(_Installer_AWizardLink):
    """Runs the install wizard to select subpackages and plugin filtering"""
    def __init__(self, bAuto):
        super(Installer_Wizard, self).__init__()
        self.bAuto = bAuto
        self._text = (_(u'Auto Wizard...') if self.bAuto
                      else _(u'Manual Wizard...'))
        self._help = (
            _(u'Run the install wizard, selecting the default options.')
            if self.bAuto else _(u'Run the install wizard.'))

    def _enable(self):
        return super(Installer_Wizard, self)._enable() and all(
            i.hasWizard for i in self.iselected_infos())

    @balt.conversation
    def Execute(self):
        ##: Investigate why we have so many refreshCurrents in here.
        # Installer_Fomod has just one!
        ui_refresh = [False, False]
        idetails = self.iPanel.detailsPanel
        try:
            # Use list() since we're going to deselect packages
            for sel_package in list(self.iselected_infos()):
                with BusyCursor():
                    # Select the package we want to install - posts events to
                    # set details and update GUI
                    self.window.SelectItem(GPath(sel_package.archive))
                    # Switch away from FOMOD mode, the wizard may need plugin
                    # data from BAIN
                    idetails.set_fomod_mode(fomod_enabled=False)
                    idetails.refreshCurrent(sel_package)
                    try:
                        wizard = InstallerWizard(self.window, sel_package,
                                                 self.bAuto)
                    except CancelError:
                        return
                    wizard.ensureDisplayed()
                ret = wizard.Run()
                if ret.canceled:
                    if isinstance(ret.canceled, str):
                        self._showWarning(ret.canceled)
                    idetails.refreshCurrent(sel_package)
                    continue
                sel_package.resetAllEspmNames()
                for index in range(len(sel_package.subNames[1:])):
                    select = (sel_package.subNames[index + 1] in
                              ret.select_sub_packages)
                    idetails.gSubList.lb_check_at_index(index, select)
                    sel_package.subActives[index + 1] = select
                idetails.refreshCurrent(sel_package)
                # Check the plugins that were selected by the wizard
                espms = idetails.gEspmList.lb_get_str_items()
                espms = [x.replace(u'&&',u'&') for x in espms]
                sel_package.espmNots = set()
                for index, espm in enumerate(idetails.espms):
                    if espms[index] in ret.select_plugins:
                        idetails.gEspmList.lb_check_at_index(index, True)
                    else:
                        idetails.gEspmList.lb_check_at_index(index, False)
                        sel_package.espmNots.add(espm)
                idetails.refreshCurrent(sel_package)
                #Rename the espms that need renaming
                for oldName in ret.rename_plugins:
                    sel_package.setEspmName(oldName,
                                            ret.rename_plugins[oldName])
                idetails.refreshCurrent(sel_package)
                #Install if necessary
                if ret.should_install:
                    self._perform_install(sel_package, ui_refresh)
                self._apply_tweaks(sel_package, ret, ui_refresh)
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

    def _apply_tweaks(self, installer, ret, ui_refresh):
        #Build any ini tweaks
        manuallyApply = []  # List of tweaks the user needs to  manually apply
        lastApplied = None
        new_targets = {}
        for iniFile, wizardEdits in ret.ini_edits.items():
            basen = os.path.basename(os.path.splitext(iniFile)[0])
            outFile = bass.dirs[u'ini_tweaks'].join(
                u'%s - Wizard Tweak [%s].ini' % (installer, basen))
            # Use UTF-8 since this came from a wizard.txt which could have
            # characters in it that are unencodable in cp1252 - plus this is
            # just a tweak, won't be read by the game
            with outFile.open(u'w', encoding=u'utf-8') as out:
                out.write(u'\n'.join(generateTweakLines(wizardEdits, iniFile)))
                out.write(u'\n')
            bosh.iniInfos.new_info(outFile.tail, owner=installer.archive)
            # trigger refresh UI
            ui_refresh[1] = True
            # We wont automatically apply tweaks to anything other than
            # Oblivion.ini or an ini from this installer
            game_ini = bosh.get_game_ini(iniFile, is_abs=False)
            if game_ini:
                target_path = game_ini.abs_path
                target_ini_file = game_ini
            else: # suppose that the target ini file is in the Data/ dir
                target_path = bass.dirs[u'mods'].join(iniFile)
                new_targets[target_path.stail] = target_path
                if not (iniFile in installer.ci_dest_sizeCrc and
                        ret.should_install):
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
                BashFrame.iniList.panel.ShowPanel(focus_list=False,
                                                  detail_item=lastApplied)
            ui_refresh[1] = False
        if len(manuallyApply) > 0:
            message = text_wrap(_(u'The following INI Tweaks were not '
                                  u'automatically applied.  Be sure to apply '
                                  u'them after installing the package.'))
            message += u'\n\n'
            message += u'\n'.join([u' * %s\n   TO: %s' % (x[0].stail, x[1])
                                   for x in manuallyApply])
            self._showInfo(message)

class Installer_OpenReadme(OneItemLink, _InstallerLink):
    """Opens the installer's readme if BAIN can find one."""
    _text = _(u'Open Readme')
    _help = _(u"Open the installer's readme if BAIN can find one")

    def _enable(self):
        single_item = super(Installer_OpenReadme, self)._enable()
        return single_item and bool(self._selected_info.hasReadme)

    def Execute(self): self._selected_info.open_readme()

#------------------------------------------------------------------------------
class Installer_Anneal(_NoMarkerLink):
    """Anneal all packages."""
    _text = _(u'Anneal')
    _help = _(u'Install any missing files (for active packages) and update '
              u'the contents of the %s folder to account for install order '
              u'and configuration changes in the selected '
              u'package(s).') % bush.game.mods_dir

    def Execute(self):
        ui_refresh = [False, False]
        try:
            with balt.Progress(_(u'Annealing...'),u'\n'+u' '*60) as progress:
                self.idata.bain_anneal(self._installables, ui_refresh,
                                       progress)
        except (CancelError,SkipError):
            pass
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

class Installer_Duplicate(OneItemLink, _InstallerLink):
    """Duplicate selected Installer."""
    _text = _(u'Duplicate...')
    dialogTitle = _text

    @property
    def link_help(self):
        return _(u'Duplicate selected %(installername)s.') % (
            {u'installername': self._selected_item})

    def _enable(self):
        single_item = super(Installer_Duplicate, self)._enable()
        return single_item and not self._selected_info.is_marker()

    @balt.conversation
    def Execute(self):
        """Duplicate selected Installer."""
        newName = self._selected_info.unique_key(self._selected_item.root,
                                                 add_copy=True)
        allowed_exts = {} if not self._selected_info.is_archive() else {
            self._selected_item.ext}
        result = self._askFilename(
            _(u'Duplicate %s to:') % self._selected_item, newName.s,
            inst_type=type(self._selected_info),
            disallow_overwrite=True, no_dir=False, ##: no_dir=False?
            allowed_exts=allowed_exts, use_default_ext=False)
        if not result: return
        #--Duplicate
        with BusyCursor():
            self.idata.copy_installer(self._selected_item, result)
            self.idata.irefresh(what=u'N')
        self.window.RefreshUI(detail_item=result)

class Installer_Hide(_InstallerLink, UIList_Hide):
    """Hide selected Installers."""
    _help = UIList_Hide._help + _(u' Not available if any markers have been '
                                  u'selected.')

    def _enable(self):
        return not any(inf.is_marker() for inf in self.iselected_infos())

class Installer_Rename(UIList_Rename, _InstallerLink):
    """Renames files by pattern."""
    _help = _(u'Rename selected installer(s).') + u'  ' + _(
        u'All selected installers must be of the same type')

    def _enable(self):
        ##Only enable if all selected items are of the same type
        firstItem = next(self.iselected_infos())
        for info in self.iselected_infos():
            if not isinstance(info, type(firstItem)):
                return False
        return True

class Installer_HasExtraData(CheckLink, _RefreshingLink):
    """Toggle hasExtraData flag on installer."""
    _text = _(u'Has Extra Directories')
    _help = _(u'Allow installation of files in non-standard directories.')

    def _enable(self):
        return len(self.selected) == 1 and not self._selected_info.is_marker()

    def _check(self):
        return self._enable() and self._selected_info.hasExtraData

    def Execute(self):
        """Toggle hasExtraData installer attribute"""
        self._selected_info.hasExtraData ^= True
        super(Installer_HasExtraData, self).Execute()

class Installer_OverrideSkips(CheckLink, _RefreshingLink):
    """Toggle overrideSkips flag on installer."""
    _text = _(u'Override Skips')

    @property
    def link_help(self):
        return _(
            u'Override global file type skipping for %(installername)s.') % (
                {u'installername': self._selected_item}) + u'  '+ _(u'BETA!')

    def _check(self):
        return self._enable() and self._selected_info.overrideSkips

    def Execute(self):
        self._selected_info.overrideSkips ^= True
        self._overrides_skips = self._selected_info.overrideSkips
        super(Installer_OverrideSkips, self).Execute()

class Installer_SkipRefresh(CheckLink, _SingleProject):
    """Toggle skipRefresh flag on project."""
    _text = _(u"Don't Refresh")
    _help = _(u"Don't automatically refresh project.")

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
            self.idata.irefresh(what=u'N')
            self.window.RefreshUI()

class Installer_Install(_NoMarkerLink):
    """Install selected packages."""
    mode_title = {u'DEFAULT': _(u'Install Configured'),
                  u'LAST': _(u'Install Last'),
                  u'MISSING': _(u'Install Missing Files')}
    mode_help = {u'DEFAULT': _(u'Install all configured files from selected '
                               u'installer(s), overwriting mismatched files.'),
                 u'LAST': _(u'Install all configured files from selected '
                            u'installer(s) at the last position, overwriting '
                            u'mismatched files.'),
                 u'MISSING': _(u'Install all missing files from the selected '
                               u'installer(s).')}

    def __init__(self,mode=u'DEFAULT'):
        super(Installer_Install, self).__init__()
        self.mode = mode
        self._text = self.mode_title[self.mode]
        self._help = self.mode_help[self.mode]

    @balt.conversation
    def Execute(self):
        ui_refresh = [False, False]
        try:
            with balt.Progress(_(u'Installing...'),u'\n'+u' '*60) as progress:
                last = (self.mode == u'LAST')
                override = (self.mode != u'MISSING')
                try:
                    new_tweaks = self.idata.bain_install(self._installables,
                        ui_refresh, progress, last, override)
                except (CancelError,SkipError):
                    pass
                except StateError as e:
                    self._showError(u'%s'%e)
                else: # no error occurred
                    self._warn_mismatched_ini_tweaks_created(new_tweaks)
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

    def _warn_mismatched_ini_tweaks_created(self, new_tweaks):
        if not new_tweaks: return
        msg = _(u'The following INI Tweaks were created, because the '
            u'existing INI was different than what BAIN installed:') + \
            u'\n' + u'\n'.join([u' * %s\n' % x.stail for (x, y) in new_tweaks])
        self._showInfo(msg, title=_(u'INI Tweaks'))

class Installer_InstallSmart(_NoMarkerLink):
    """A 'smart' installer for new users. Uses wizards and FOMODs if present,
    then falls back to regular install if that isn't possible."""
    _text = _(u'Install...')
    _help = _(u'Installs selected installer(s), preferring a visual method if '
              u'available.')

    def _try_installer(self, sel_package, inst_instance):
        """Checks if the specified installer link is enabled and, if so, runs
        it.

        :type inst_instance: EnabledLink"""
        inst_instance._initData(self.window, [GPath(sel_package.archive)])
        if inst_instance._enable():
            inst_instance.Execute()
            return True
        return False

    def Execute(self):
        ##: Not the best implementation, pretty readable and obvious though
        inst_wiz = Installer_Wizard(bAuto=False)
        inst_fomod = Installer_Fomod()
        inst_regular = Installer_Install()
        # Use list() since the interactive installers can change selection
        for sel_package in list(self.iselected_infos()):
            # Look for a BAIN wizard first, best integration with BAIN (duh)
            if self._try_installer(sel_package, inst_wiz): continue
            # Skip FOMODs here if the Ignore FOMODs option is checked
            if not bass.settings[u'bash.installers.ignore_fomods']:
                # Next, look for an FOMOD wizard - not quite as good, but at
                # least it's visual
                if self._try_installer(sel_package, inst_fomod): continue
            # Finally, fall back to the regular 'Install Configured' method
            self._try_installer(sel_package, inst_regular)

class Installer_ListStructure(OneItemLink, _InstallerLink):
    """Copies folder structure of installer to clipboard."""
    _text = _(u'List Structure...')
    _help = _(u'Displays the folder structure of the selected installer (and '
              u'copies it to the system clipboard).')

    def _enable(self):
        single_item = super(Installer_ListStructure, self)._enable()
        return single_item and not self._selected_info.is_marker()

    @balt.conversation ##: no use ! _showLog returns immediately
    def Execute(self):
        source_list_txt = self._selected_info.listSource()
        #--Get masters list
        copy_text_to_clipboard(source_list_txt)
        self._showLog(source_list_txt, title=_(u'Package Structure'),
                      fixedFont=False)

class Installer_ExportAchlist(OneItemLink, _InstallerLink):
    """Write an achlist file with all the destinations files for this
    installer in this configuration."""
    _text = _(u'Export Achlist')
    _mode_info_dir = u'Mod Info Exports'
    _help = (_(u'Create achlist file for use by the %s.') %
             bush.game.Ck.long_name)

    def _enable(self):
        single_item = super(Installer_ExportAchlist, self)._enable()
        return single_item and not self._selected_info.is_marker()

    def Execute(self):
        info_dir = bass.dirs[u'app'].join(self.__class__._mode_info_dir)
        info_dir.makedirs()
        achlist = info_dir.join(self._selected_info.archive + u'.achlist')
        ##: Windows-1252 is a guess. The CK is able to decode non-ASCII
        # characters encoded with it correctly, at the very least (UTF-8/UTF-16
        # both fail), but the encoding might depend on the game language?
        with BusyCursor(), achlist.open(u'w', encoding=u'cp1252') as out:
            out.write(u'[\n\t"')
            lines = u'",\n\t"'.join(
                u'\\'.join((bush.game.mods_dir, d)).replace(u'\\', u'\\\\')
                for d in bolt.sortFiles(self._selected_info.ci_dest_sizeCrc)
                # exclude top level files and docs - last one monkey patched
                if os.path.split(d)[0] and not d.lower().startswith(u'docs'))
            out.write(lines)
            out.write(u'"\n]')

class Installer_Move(_InstallerLink):
    """Moves selected installers to desired spot."""
    _text = _(u'Move To...')
    _help = _(u'Move the selected installer(s) to a position of your choice.')

    @balt.conversation
    def Execute(self):
        curPos = min(inf.order for inf in self.iselected_infos())
        message = (_(u'Move selected archives to what position?') + u'\n' +
                   _(u'Enter position number.') + u'\n' +
                   _(u'Last: -1; First of Last: -2; Semi-Last: -3.')
                   )
        newPos = self._askText(message, default=str(curPos))
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
        self.idata.irefresh(what=u'N')
        self.window.RefreshUI(
            detail_item=self.iPanel.detailsPanel.displayed_item)

class Installer_Open(balt.UIList_OpenItems, EnabledLink):
    """Open selected installer(s). Selected markers are skipped."""

    def _enable(self):
        # Can't use _NoMarkerLink since it will skip unrecognized packages
        return not any(p.is_marker() for p in self.iselected_infos())

    def Execute(self):
        self.window.OpenSelected(selected=self.selected)

#------------------------------------------------------------------------------
class _Installer_OpenAt(_InstallerLink):
    group = 2  # the regexp group we are interested in (2 is id, 1 is modname)
    _open_at_continue = u'OVERRIDE'

    def _enable(self):
        # The menu won't even be enabled if >1 plugin is selected
        x = self.__class__.regexp.search(self.selected[0].s)
        if not x: return False
        self.mod_url_id = x.group(self.__class__.group)
        return bool(self.mod_url_id)

    def _url(self): return self.__class__.baseUrl + self.mod_url_id

    def Execute(self):
        if self._askContinue(self.message, self._open_at_continue,
                             self.askTitle):
            webbrowser.open(self._url())

class Installer_OpenNexus(AppendableLink, _Installer_OpenAt):
    regexp = bosh.reTesNexus
    _text = u'%s...' % bush.game.nexusName
    _help = _(u"Opens this mod's page at the %(nexusName)s.") % \
            {u'nexusName': bush.game.nexusName}
    message = _(
        u'Attempt to open this as a mod at %(nexusName)s? This assumes that '
        u"the trailing digits in the package's name are actually the id "
        u'number of the mod at %(nexusName)s. If this assumption is wrong, '
        u"you'll just get a random mod page (or error notice) at %("
        u'nexusName)s.') % {u'nexusName': bush.game.nexusName}
    _open_at_continue = bush.game.nexusKey
    askTitle = _(u'Open at %(nexusName)s') % {u'nexusName':bush.game.nexusName}
    baseUrl = bush.game.nexusUrl + u'mods/'

    def _append(self, window): return bool(bush.game.nexusUrl)

class Installer_OpenSearch(_Installer_OpenAt):
    group = 1
    regexp = bosh.reTesNexus
    _text = u'Google...'
    _help = _(u"Searches for this mod's title on Google.")
    _open_at_continue = u'bash.installers.opensearch.continue'
    askTitle = _(u'Open a search')
    message = _(u'Open a search for this on Google?')

    def _url(self):
        return u'http://www.google.com/search?hl=en&q=' + u'+'.join(
            re.split(r'\W+|_+', self.mod_url_id))

class Installer_OpenTESA(_Installer_OpenAt):
    regexp = bosh.reTESA
    _text = u'TES Alliance...'
    _help = _(u"Opens this mod's page at TES Alliance.")
    _open_at_continue = u'bash.installers.openTESA.continue'
    askTitle = _(u'Open at TES Alliance')
    message = _(
        u'Attempt to open this as a mod at TES Alliance? This assumes that '
        u"the trailing digits in the package's name are actually the id "
        u'number of the mod at TES Alliance. If this assumption is wrong, '
        u"you'll just get a random mod page (or error notice) at TES "
        u'Alliance.')
    baseUrl =u'http://tesalliance.org/forums/index.php?app=downloads&showfile='

#------------------------------------------------------------------------------
class Installer_Refresh(_InstallerLink):
    """Rescans selected Installers."""
    _text = _(u'Refresh')
    _help = _(u'Rescan selected Installer(s)') + u'.  ' + _(
        u'Ignores skip refresh flag on projects')

    def __init__(self, calculate_projects_crc=True):
        super(Installer_Refresh, self).__init__()
        self.calculate_projects_crc = calculate_projects_crc
        if not calculate_projects_crc:
            self._text = _(u'Quick Refresh')
            self._help = Installer_Refresh._help + u'.  ' + _(
                u'Will not recalculate cached crcs of files in a project')

    def _enable(self):
        return bool(list(self.idata.ipackages(self.selected)))

    @balt.conversation
    def Execute(self):
        self.window.rescanInstallers(self.selected, abort=True,
            calculate_projects_crc=self.calculate_projects_crc)

class Installer_SkipVoices(CheckLink, _RefreshingLink):
    """Toggle skipVoices flag on installer."""
    _text = _(u'Skip Voices')

    @property
    def link_help(self):
        return _(u'Skip over any voice files in %(installername)s') % (
                    {u'installername': self._selected_item})

    def _check(self): return self._enable() and self._selected_info.skipVoices

    def Execute(self):
        self._selected_info.skipVoices ^= True
        super(Installer_SkipVoices, self).Execute()

class Installer_Uninstall(_NoMarkerLink):
    """Uninstall selected Installers."""
    _text = _(u'Uninstall')
    _help = _(u'Uninstall selected Installer(s)')

    @balt.conversation
    def Execute(self):
        """Uninstall selected Installers."""
        ui_refresh = [False, False]
        try:
            with balt.Progress(_(u'Uninstalling...'),u'\n'+u' '*60) as progress:
                self.idata.bain_uninstall(self._installables, ui_refresh,
                                          progress)
        except (CancelError,SkipError): # now where could this be raised from ?
            pass
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

class Installer_CopyConflicts(_SingleInstallable):
    """For Modders only - copy conflicts to a new project."""
    _text = _(u'Copy Conflicts to Project')
    _help = _(u'Copy all files that conflict with the selected installer into a'
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
        with balt.Progress(_(u'Scanning Packages...'),
                           u'\n' + u' ' * 60) as progress:
            progress.setFull(len(self.idata))
            numFiles = 0
            destDir = GPath(u'Conflicts - %03d' % src_order)
            for i,(package, installer) in enumerate(self.idata.sorted_pairs()):
                curConflicts = set()
                progress(i, _(u'Scanning Packages...') + u'\n%s' % package)
                for z, y in installer.refreshDataSizeCrc().items():
                    if z in src_sizeCrc and installer.ci_dest_sizeCrc[z] != \
                            src_sizeCrc[z]:
                        curConflicts.add(y)
                        srcConflicts.add(src_sizeCrc[z])
                numFiles += len(curConflicts)
                if curConflicts: packConflicts.append(
                    (installer.order, package, curConflicts))
            srcConflicts = { # we need the paths rel to the archive not Data
                src for src, siz, crc in self._selected_info.fileSizeCrcs if
                (siz, crc) in srcConflicts}
            numFiles += len(srcConflicts)
        if not numFiles:
            return _ok(_(u'No conflicts detected for %s'))
        ijoin = self.idata.store_dir.join
        def _copy_conflicts(curFile):
            inst = self.idata[package]
            if inst.is_project():
                for src in curConflicts:
                    srcFull = ijoin(package, src)
                    destFull = ijoin(destDir, g_path, src)
                    if srcFull.exists():
                        progress(curFile, u'%s\n' % self._selected_item + _(
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
        with balt.Progress(_(u'Copying Conflicts...'),
                           u'\n' + u' ' * 60) as progress:
            progress.setFull(numFiles)
            curFile = 0
            g_path = package = self._selected_item
            curConflicts = srcConflicts
            curFile = _copy_conflicts(curFile)
            for order,package,curConflicts in packConflicts:
                g_path = GPath(u'%03d - %s' % (
                    order if order < src_order else order + 1, package.s))
                curFile = _copy_conflicts(curFile)
        InstallerProject.refresh_installer(destDir, self.idata, progress=None,
            install_order=src_order + 1, do_refresh=True)
        self.window.RefreshUI(detail_item=destDir)

#------------------------------------------------------------------------------
# InstallerDetails Plugin Filter Links ----------------------------------------
#------------------------------------------------------------------------------
class _Installer_Details_Link(EnabledLink):

    def _enable(self): return len(self.window.espms) != 0

    def _initData(self, window, selection):
        """:type window: bosh.InstallersDetails
        :type selection: int"""
        super(_Installer_Details_Link, self)._initData(window, selection)
        self._installer = self.window.file_info

class Installer_Espm_SelectAll(_Installer_Details_Link):
    """Select all plugins in installer for installation."""
    _text = _(u'Select All')
    _help = _(u'Selects all plugin files in the selected sub-packages.')

    def Execute(self):
        self._installer.espmNots = set()
        self.window.gEspmList.set_all_checkmarks(checked=True)
        self.window.refreshCurrent(self._installer)

class Installer_Espm_DeselectAll(_Installer_Details_Link):
    """Deselect all plugins in installer for installation."""
    _text = _(u'Deselect All')
    _help = _(u'Deselects all plugin files in the selected sub-packages.')

    def Execute(self):
        self._installer.espmNots = set(self.window.espms)
        self.window.gEspmList.set_all_checkmarks(checked=False)
        self.window.refreshCurrent(self._installer)

class Installer_Espm_Rename(_Installer_Details_Link):
    """Changes the installed name for a plugin."""
    _text = _(u'Rename...')
    _help = _(u'Changes the name under which this plugin will be installed.')

    def _enable(self): return self.selected != -1

    def Execute(self):
        curName = self.window.gEspmList.lb_get_str_item_at_index(self.selected).replace(u'&&',
                                                                         u'&')
        if curName[0] == u'*':
            curName = curName[1:]
        _file = GPath(curName)
        newName = self._askText(_(u'Enter new name (without the extension):'),
                                title=_(u'Rename Plugin'), default=_file.sbody)
        if not newName: return
        if newName in self.window.espms: return
        self._installer.setEspmName(curName, newName + _file.cext)
        self.window.refreshCurrent(self._installer)

class Installer_Espm_Reset(_Installer_Details_Link):
    """Resets the installed name for a plugin."""
    _text = _(u'Reset Name')
    _help = _(u'Resets the name under which this plugin will be installed '
              u'back to its default name.')

    def _enable(self):
        if self.selected == -1: return False
        curName = self.window.gEspmList.lb_get_str_item_at_index(self.selected).replace(u'&&',
                                                                         u'&')
        if curName[0] == u'*': curName = curName[1:]
        self.curName = curName
        return self._installer.isEspmRenamed(curName)

    def Execute(self):
        self._installer.resetEspmName(self.curName)
        self.window.refreshCurrent(self._installer)

class Installer_Espm_ResetAll(_Installer_Details_Link):
    """Resets all renamed plugins."""
    _text = _(u'Reset All Names')
    _help = _(u'Resets all plugins with changed names back to their default '
              u'ones.')

    def Execute(self):
        self._installer.resetAllEspmNames()
        self.window.refreshCurrent(self._installer)

class Installer_Espm_List(_Installer_Details_Link):
    """Lists all plugins in installer for user information."""
    _text = _(u'List Plugins')
    _help = _(u'Displays a list of all plugin files in the selected '
              u'sub-packages (and copies it to the system clipboard).')

    def Execute(self):
        subs = _(u'Plugin List for %s:') % self._installer + u'\n[spoiler]\n'
        espm_list = self.window.gEspmList
        for index in range(espm_list.lb_get_items_count()):
            subs += [u'   ',u'** '][espm_list.lb_is_checked_at_index(index)] + \
                    espm_list.lb_get_str_item_at_index(index) + u'\n'
        subs += u'[/spoiler]'
        copy_text_to_clipboard(subs)
        self._showLog(subs, title=_(u'Plugin List'), fixedFont=False)

class Installer_Espm_JumpToMod(_Installer_Details_Link):
    """Jumps to a plugin in the Mods tab, if it is installed."""
    _text = _(u'Jump to Mod')
    _help = _(u'Jumps to this plugin in the Mods tab. You can double-click on '
              u'the plugin to the same effect.')

    def _enable(self):
        if self.selected == -1: return False
        ##: Maybe refactor all this plugin logic (especially the renamed plugin
        # (asterisk) handling) to a property inside a base class?
        selected_plugin = self.window.gEspmList.lb_get_str_item_at_index(
            self.selected).replace(u'&&', u'&')
        if selected_plugin[0] == u'*': selected_plugin = selected_plugin[1:]
        self.target_plugin = GPath(selected_plugin)
        return self.target_plugin in bosh.modInfos

    def Execute(self):
        balt.Link.Frame.notebook.SelectPage(u'Mods', self.target_plugin)

#------------------------------------------------------------------------------
# InstallerDetails Subpackage Links -------------------------------------------
#------------------------------------------------------------------------------
class _Installer_Subs(_Installer_Details_Link):
    def _enable(self): return self.window.gSubList.lb_get_items_count() > 1

class _Installer_Subs_MassSelect(_Installer_Subs):
    """Base class for the (de)select all links."""
    _should_check = False

    def Execute(self):
        self.window.set_subpackage_checkmarks(checked=self._should_check)
        self.window.refreshCurrent(self._installer)

class Installer_Subs_SelectAll(_Installer_Subs_MassSelect):
    """Select All sub-packages in installer for installation."""
    _text = _(u'Select All')
    _help = _(u'Selects all sub-packages in this installer.')
    _should_check = True

class Installer_Subs_DeselectAll(_Installer_Subs_MassSelect):
    """Deselect All sub-packages in installer for installation."""
    _text = _(u'Deselect All')
    _help = _(u'Deselects all sub-packages in this installer.')

class Installer_Subs_ToggleSelection(_Installer_Subs):
    """Toggles selection state of all sub-packages in installer for
    installation."""
    _text = _(u'Toggle Selection')
    _help = _(u'Deselects all selected sub-packages and vice versa.')

    def Execute(self):
        for index in range(self.window.gSubList.lb_get_items_count()):
            # + 1 due to empty string included in subActives by BAIN
            check = not self._installer.subActives[index + 1]
            self.window.gSubList.lb_check_at_index(index, check)
            self._installer.subActives[index + 1] = check
        self.window.refreshCurrent(self._installer)

class Installer_Subs_ListSubPackages(_Installer_Subs):
    """Lists all sub-packages in installer for user information/w/e."""
    _text = _(u'List Sub-Packages')
    _help = _(u'Displays a list of all sub-packages in this installer (and '
              u'copies it to the system clipboard).')

    def Execute(self):
        subs = _(u'Sub-Packages List for %s:') % self._installer
        subs += u'\n[spoiler]\n'
        for index in range(self.window.gSubList.lb_get_items_count()):
            subs += [u'   ', u'** '][self.window.gSubList.lb_is_checked_at_index(
                index)] + self.window.gSubList.lb_get_str_item_at_index(index) + u'\n'
        subs += u'[/spoiler]'
        copy_text_to_clipboard(subs)
        self._showLog(subs, title=_(u'Sub-Package Lists'), fixedFont=False)

#------------------------------------------------------------------------------
# InstallerArchive Links ------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerArchive_Unpack(AppendableLink, _InstallerLink):
    """Unpack installer package(s) to Project(s)."""
    _text = _(u'Unpack to Project(s)...')
    _help = _(u'Unpack installer package(s) to Project(s)')

    def _append(self, window):
        self.selected = window.GetSelected() # append runs before _initData
        self.window = window # and the idata access is via self.window
        return all(inf.is_archive() for inf in self.iselected_infos())

    @balt.conversation
    def Execute(self):
        # Ask the user first to avoid the progress dialog shoving itself over
        # any dialogs we pop up
        to_unpack = []
        for iname, installer in self.idata.sorted_pairs(self.selected):
            project = iname.root
            if self.isSingleArchive():
                result = self._askText(_(u'Unpack %s to Project:') % iname,
                                       default=project.s)
                if not result: return
                # Error checking
                project = GPath(result).tail
                if not project.s or project.cext in archives.readExts:
                    self._showWarning(_(u'%s is not a valid project name.') %
                                      result)
                    return
                if self.idata.store_dir.join(project).isfile():
                    self._showWarning(_(u'%s is a file.') % project)
                    return
            if project in self.idata and not self._askYes(
                    _(u'%s already exists. Overwrite it?') % project,
                    default=False):
                continue
            # All check passed, we can unpack this
            to_unpack.append((installer, project))
        # We're safe to show the progress dialog now
        with balt.Progress(_(u'Unpacking to Project...'),u'\n'+u' '*60) \
                as progress:
            projects = []
            for installer, project in to_unpack:
                installer.unpackToProject(project,SubProgress(progress,0,0.8))
                InstallerProject.refresh_installer(project, self.idata,
                    progress=SubProgress(progress, 0.8, 0.99),
                    install_order=installer.order + 1, do_refresh=False)
                projects.append(project)
            if not projects: return
            self.idata.irefresh(what=u'NS')
            self.window.RefreshUI(detail_item=projects[-1]) # all files ? can status of others change ?
            self.window.SelectItemsNoCallback(projects)

#------------------------------------------------------------------------------
# InstallerProject Links ------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerProject_OmodConfig(_SingleProject):
    """Projects only. Allows you to read/write omod configuration info."""
    _text = _(u'Omod Info...')
    _help = _(u'Projects only. Allows you to read/write omod configuration info')

    def Execute(self):
        InstallerProject_OmodConfigDialog(self.window,
                                          self._selected_item).show_frame()
#------------------------------------------------------------------------------
class Installer_SyncFromData(_SingleInstallable):
    """Synchronize an archive or project with files from the Data directory."""
    _text = _(u'Sync from Data')
    _help = _(u'Synchronize an installer with files from the %s '
              u'directory.') % bush.game.mods_dir

    def _enable(self):
        if not super(Installer_SyncFromData, self)._enable(): return False
        return bool(self._selected_info.missingFiles or
                    self._selected_info.mismatchedFiles)

    def Execute(self):
        was_rar = self._selected_item.cext == u'.rar'
        if was_rar:
            if not self._askYes(
                    _(u'.rar files cannot be modified. Wrye Bash can however '
                      u'repack them to .7z files, which can then be '
                      u'modified.') + u'\n\n' +
                    _(u'Note that doing this will leave the old .rar file '
                      u'behind, so you may want to manually delete it '
                      u'afterwards.') + u'\n\n' +
                    _(u"Click 'Yes' to repack, or 'No' to abort the sync.")):
                return # user clicked 'No'
        missing = sorted(self._selected_info.missingFiles)
        mismatched = sorted(self._selected_info.mismatchedFiles)
        msg_del = [_(u'Files to delete (%u):') % len(missing),
                   _(u'Uncheck files to keep them in the package.')]
        msg_del.extend(missing)
        msg_upd = [_(u'Files to update (%u):') % len(mismatched),
                   _(u'Uncheck files to keep them unchanged in the package.')]
        msg_upd.extend(mismatched)
        sel_missing, sel_mismatched = [], []
        with balt.ListBoxes(self.window, self._text,
                            _(u'Update %s according to %s directory?')
                            % (self._selected_item, bush.game.mods_dir)
                            + u'\n' +
                            _(u'Uncheck any files you want to keep '
                              u'unchanged.'), [msg_del, msg_upd]) as dialog:
            if dialog.show_modal():
                sel_missing = set(dialog.getChecked(msg_del[0], missing))
                sel_mismatched = set(dialog.getChecked(msg_upd[0], mismatched))
        if not sel_missing and not sel_mismatched:
            return # Nothing left to sync, cancel
        #--Sync it, baby!
        with balt.Progress(self._text, u'\n' + u' ' * 60) as progress:
            progress(0.1,_(u'Updating files.'))
            actual_upd, actual_del = self._selected_info.sync_from_data(
                sel_missing | sel_mismatched,
                progress=SubProgress(progress, 0.1, 0.7))
            if (actual_del != len(sel_missing)
                    or actual_upd != len(sel_mismatched)):
                msg = u'\n'.join([
                    _(u'Something went wrong when updating "%s" installer.'
                      ) % self._selected_info,
                    _(u'Deleted %s. Expected to delete %s file(s).') % (
                        actual_del, len(sel_missing)),
                    _(u'Updated %s. Expected to update %s file(s).') % (
                        actual_upd, len(sel_mismatched)),
                    _(u'Check the integrity of the installer.')])
                self._showWarning(msg)
            self._selected_info.refreshBasic(SubProgress(progress, 0.7, 0.8))
            if was_rar:
                final_package = self._selected_info.writable_archive_name()
                # Move the new archive directly underneath the old archive
                InstallerArchive.refresh_installer(
                    final_package, self.idata, do_refresh=False,
                    progress=SubProgress(progress, 0.8, 0.9),
                    install_order=self._selected_info.order + 1)
                self.idata[final_package].is_active = True
            self.idata.irefresh(progress=SubProgress(progress, 0.9, 0.99),
                                what=u'NS')
            self.window.RefreshUI()

#------------------------------------------------------------------------------
class InstallerProject_Pack(_SingleProject):
    """Pack project to an archive."""
    _text = dialogTitle = _(u'Pack to Archive...')
    _help = _(u'Pack project to an archive')
    release = False

    @balt.conversation
    def Execute(self):
        #--Generate default filename from the project name and the default extension
        archive_name = GPath(self._selected_item.s + archives.defaultExt)
        #--Confirm operation
        archive_name = self._askFilename(
            _(u'Pack %s to Archive:') % self._selected_item, archive_name.s)
        if not archive_name: return
        self._pack(archive_name, self._selected_info, self._selected_item,
                   release=self.__class__.release)

#------------------------------------------------------------------------------
class InstallerProject_ReleasePack(InstallerProject_Pack):
    """Pack project to an archive for release. Ignores dev files/folders."""
    _text = _(u'Package for Release...')
    _help = _(
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
        for crc_, installers in crcs_dict.items():
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

    @property
    def link_help(self):
        return _(u'Applies %(bcf)s to the selected installer(s).') % {
            u'bcf': self.dispName}

    @balt.conversation
    def Execute(self):
        if self._check_identical_content(
                _(u'Please only select the installers this converter was made '
                  u'for.')):
            return
        # all installers that this converter needs are present and unique
        crc_installer = {x.crc: x for x in self.iselected_infos()}
        #--Generate default filename from BCF filename
        defaultFilename = self.converter.fullPath.sbody[:-4] + archives\
            .defaultExt
        #--List source archives
        message = _(u'Using:') + u'\n* ' + u'\n* '.join(sorted(
            u'(%08X) - %s' % (x, crc_installer[x]) for x in
            self.converter.srcCRCs)) + u'\n'
        #--Ask for an output filename
        destArchive = self._askFilename(message, filename=defaultFilename)
        if not destArchive: return
        with balt.Progress(_(u'Converting to Archive...'),u'\n'+u' '*60) as progress:
            #--Perform the conversion
            msg = u'%s: ' % destArchive + _(
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
    _help = _(u'Applies the BAIN converter files (BCFs) embedded in the '
              u'selected installer(s).')
    dialogTitle = _(u'Apply BCF...')

    @balt.conversation
    def Execute(self):
        iname, inst = next(self.iselected_pairs()) # first selected pair
        #--Ask for an output filename
        dest = self._askFilename(_(u'Output file:'), filename=iname.stail)
        if not dest: return
        with balt.Progress(_(u'Extracting BCF...'),u'\n'+u' '*60) as progress:
            destinations, converted = self.idata.applyEmbeddedBCFs(
                [inst], [dest], progress)
            if not destinations: return # destinations == [dest] if all was ok
        self.window.RefreshUI(detail_item=dest)

class InstallerConverter_Create(_InstallerConverter_Link):
    """Create BAIN conversion file."""
    dialogTitle = _(u'Create BCF...') # title used in dialog
    _text = _(u'Create...')
    _help = _(u'Creates a new BAIN conversion file (BCF).')

    def Execute(self):
        if self._check_identical_content(
                _(u'Please only select installers that are needed.')):
            return
        # all installers that this converter needs are unique
        crc_installer = {x.crc: x for x in self.iselected_infos()}
        #--Generate allowable targets
        readTypes = u'*%s' % u';*'.join(archives.readExts)
        #--Select target archive
        destArchive = self._askOpen(title=_(u"Select the BAIN'ed Archive:"),
            defaultDir=self.idata.store_dir, wildcard=readTypes)
        if not destArchive: return
        #--Error Checking
        BCFArchive = destArchive = destArchive.tail
        if not destArchive.s or destArchive.cext not in archives.readExts:
            self._showWarning(_(u'%s is not a valid archive name.') % destArchive)
            return
        if destArchive not in self.idata:
            self._showWarning(_(u'%s must be in the Bash Installers directory.') % destArchive)
            return
        if BCFArchive.csbody[-4:] != u'-bcf':
            BCFArchive = GPath(BCFArchive.sbody + u'-BCF' + archives.defaultExt).tail
        #--List source archives and target archive
        message = _(u'Convert:')
        message += u'\n* ' + u'\n* '.join(sorted(
            u'(%08X) - %s' % (v.crc, k.s) for k, v in self.iselected_pairs()))
        message += (u'\n\n'+_(u'To:')+u'\n* (%08X) - %s') % (self.idata[destArchive].crc,destArchive) + u'\n'
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
                      u' be discarded.') % (
                              archives.defaultExt, BCFArchive.cext))
            BCFArchive = GPath(BCFArchive.sbody + archives.defaultExt).tail
        if bass.dirs[u'converters'].join(BCFArchive).exists():
            if not self._askYes(_(
                    u'%s already exists. Overwrite it?') % BCFArchive,
                                title=self.dialogTitle, default=False): return
            #--It is safe to removeConverter, even if the converter isn't overwritten or removed
            #--It will be picked back up by the next refresh.
            self.idata.converters_data.removeConverter(BCFArchive)
        destInstaller = self.idata[destArchive]
        blockSize = None
        if destInstaller.isSolid:
            blockSize = self._promptSolidBlockSize(
                title=self.dialogTitle, value=destInstaller.blockSize or 0)
        with balt.Progress(_(u'Creating %s...') % BCFArchive,u'\n'+u' '*60) as progress:
            #--Create the converter
            converter = bosh.converters.InstallerConverter(self.selected,
                    self.idata, destArchive, BCFArchive, blockSize, progress)
            #--Add the converter to Bash
            self.idata.converters_data.addConverter(converter)
            #--Refresh UI
            self.idata.irefresh(what=u'C')
            #--Generate log
            log = LogFile(io.StringIO())
            log.setHeader(u'== '+_(u'Overview')+u'\n')
##            log('{{CSS:wtxt_sand_small.css}}')
            log(u'. '+_(u'Name')+u': %s'%BCFArchive)
            log(u'. ' + _(u'Size') +u': %s' % round_size(converter.fullPath.psize))
            log(u'. ' + _(u'Remapped: %u file(s)') %
                len(converter.convertedFiles))
            log.setHeader(u'. ' + _(u'Requires: %u file(s)') %
                          len(converter.srcCRCs))
            log(u'  * '+u'\n  * '.join(sorted(u'(%08X) - %s' % (x, crc_installer[x]) for x in converter.srcCRCs if x in crc_installer)))
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
            log.setHeader(u'. ' + _(u'Contains: %u file(s)') %
                          len(converter.bcf_missing_files))
            log(u'  * ' +u'\n  * '.join(sorted(u'%s' % x for x in converter
                                               .bcf_missing_files)))
        if log:
            self._showLog(log.out.getvalue(), title=_(u'BCF Information'))

#------------------------------------------------------------------------------
# Installer Submenus ----------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerConverter_ConvertMenu(balt.MenuLink):
    """Apply BCF SubMenu."""
    _text = _(u'Apply')
    def _enable(self):
        """Return False to disable the converter menu, otherwise populate its
        links attribute and return True."""
        linkSet = set()
        del self.links[:]
        #--Converters are linked by CRC, not archive name
        #--So, first get all the selected archive CRCs
        selected = self.selected
        idata = self.window.data_store # InstallersData singleton
        selectedCRCs = set(inst.crc for inst in self.iselected_infos())
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
        if len(selected) == 1 and self._first_selected().hasBCF:
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
    _text = _(u'BAIN Conversions')
    def _enable(self):
        return all(inst.is_archive() for inst in self.iselected_infos())
