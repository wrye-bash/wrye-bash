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
from functools import wraps
from itertools import chain

from . import BashFrame, INIList, Installers_Link, InstallersDetails
from .dialogs import SyncFromDataEditor
from .frames import InstallerProject_OmodConfigDialog
from .gui_fomod import InstallerFomod
from .. import archives, balt, bass, bolt, bosh, bush, env
from ..balt import AppendableLink, CheckLink, EnabledLink, OneItemLink, \
    UIList_Hide
from ..belt import InstallerWizard, generateTweakLines
from ..bolt import FName, LogFile, SubProgress, deprint, round_size
from ..bosh import InstallerConverter, converters
from ..exception import CancelError, SkipError, StateError, XMLParsingError
from ..gui import BusyCursor, copy_text_to_clipboard
from ..wbtemp import cleanup_temp_dir

__all__ = [u'Installer_Open', u'Installer_Duplicate',
           'Installer_OpenSearch', 'Installer_CaptureFomodOutput',
           'Installer_OpenTESA', 'Installer_Hide',
           u'Installer_Refresh', u'Installer_Move', u'Installer_HasExtraData',
           u'Installer_OverrideSkips', u'Installer_SkipVoices',
           u'Installer_SkipRefresh', u'Installer_Wizard',
           u'Installer_EditWizard', u'Installer_OpenReadme',
           u'Installer_Anneal', u'Installer_Install', u'Installer_Uninstall',
           'Installer_ArchiveMenu', 'InstallerConverter_Create',
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
           'Installer_RunFomod', 'Installer_InstallSmart',
           'Installer_EditFomod', 'Installer_ProjectMenu']

#------------------------------------------------------------------------------
# Installer Links -------------------------------------------------------------
#------------------------------------------------------------------------------
class _InstallerLink(Installers_Link, EnabledLink):
    """Common methods for installer links."""

    def _promptSolidBlockSize(self, title, default_size=0):
        return self._askNumber(
            _('Use what maximum size for each solid block?') + '\n' + _(
                "Enter '0' to use 7z's default size."), prompt='MB',
            title=title, initial_num=default_size, min_num=0, max_num=102400)

def _with_busy_cursor(func):
    @wraps(func)
    def _busy(*args, **kwargs):
        with BusyCursor():
            func(*args, **kwargs)
    return _busy

class _SingleInstallable(OneItemLink, _InstallerLink):

    def _enable(self):
        return super()._enable() and not self._selected_info.is_marker

class _SingleProject(OneItemLink, _InstallerLink):

    def _enable(self):
        return super()._enable() and self._selected_info.is_project

class _ArchiveOnly(_InstallerLink):
    """_InstallerLink that is only enabled for archives."""
    def _enable(self):
        return all(inf.is_archive for inf in self.iselected_infos())

class _RefreshingLink(_SingleInstallable):
    _overrides_skips = False

    @balt.conversation
    def Execute(self):
        dest_src = self._selected_info.refreshDataSizeCrc()
        with balt.Progress(title=_(u'Override Skips')) as progress:
            if self._overrides_skips:
                self.idata.update_for_overridden_skips(set(dest_src), progress)
            self.idata.refresh_ns(progress=progress)
        self.window.RefreshUI()

class _NoMarkerLink(_InstallerLink):
    """Installer link that does not accept any markers."""
    def _enable(self):
        self._installables = self.idata.filterInstallables(self.selected)
        return bool(self._installables) and super()._enable()

#------------------------------------------------------------------------------
class _Installer_AWizardLink(_NoMarkerLink):
    """Base class for wizard links."""
    def _perform_install(self, sel_package, ui_refresh):
        if sel_package.is_active: # If it's currently installed, anneal
            title = _(u'Annealing...')
            do_it = self.idata.bain_anneal
        else: # Install if it's not installed
            title = _(u'Installing...')
            do_it = self.idata.bain_install
        with balt.Progress(title) as progress:
            do_it([sel_package.fn_key], ui_refresh, progress)

class _Installer_AViewOrEditFile(_SingleInstallable):
    """Base class for View/Edit wizard/FOMOD links."""
    def _run_on_archive(self):
        """Returns True if the single installable we've got selected is an
        archive."""
        return next(self.iselected_infos()).is_archive

class _Installer_AFomod(_InstallerLink):
    """Base class for FOMOD links."""
    def _enable(self):
        return super()._enable() and all(
            i.has_fomod_conf for i in self.iselected_infos())

class Installer_EditFomod(_Installer_AFomod, _Installer_AViewOrEditFile):
    """View or edit the ModuleConfig.xml associated with this package."""
    @property
    def link_text(self):
        return (_('View ModuleConfig...') if self._run_on_archive() else
                _('Edit ModuleConfig...'))

    @property
    def link_help(self):
        return (_('View the ModuleConfig.xml associated with this archive.')
                if self._run_on_archive() else
                _('Edit the ModuleConfig.xml associated with this project.'))

    @_with_busy_cursor
    def Execute(self): self._selected_info.open_fomod_conf()

class _Installer_ARunFomod(_Installer_AFomod):
    """Base class for FOMOD links that need to run the FOMOD wizard."""
    _wants_install_checkbox: bool

    @balt.conversation
    def Execute(self):
        ui_refresh = [False, False]
        # Use list() since we're going to deselect packages
        try:
            for sel_package in list(self.iselected_infos()):
                try:
                    with BusyCursor():
                        # Select the package we want to install - posts events
                        # to set details and update GUI
                        self.window.SelectItem(sel_package.fn_key)
                        if sel_package.is_archive: ##: yak identical code in Installer_Wizard
                            progress = balt.Progress(_('Extracting images...'),
                                                     abort=True)
                        else:
                            progress = None
                        try:
                            fm_wizard = InstallerFomod(self.window,
                                sel_package, self._wants_install_checkbox,
                                progress)
                        except CancelError:
                            continue
                        if not fm_wizard.validate_fomod():
                            # Validation failed and the user chose not to continue
                            return
                        fm_wizard.ensureDisplayed()
                    ret = fm_wizard.run_fomod()
                    if ret.canceled:
                        continue
                    # Now we're ready to execute the link's specific action
                    self._execute_action(sel_package, ret, ui_refresh)
                except XMLParsingError:
                    deprint('Invalid FOMOD XML syntax:', traceback=True)
                    self._showError(
                        _("The ModuleConfig.xml file that comes with "
                          "%(package_name)s has invalid syntax. Please report "
                          "this to the mod author so it can be fixed "
                          "properly. The BashBugDump.log in Wrye Bash's Mopy "
                          "folder contains additional details, please include "
                          "it in your report.") % {
                            'package_name': sel_package.fn_key
                        }, title=_('Invalid FOMOD XML Syntax'))
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

    def _execute_action(self, sel_package, ret, ui_refresh):
        raise NotImplementedError

class Installer_RunFomod(_Installer_AWizardLink, _Installer_ARunFomod):
    """Runs the FOMOD installer and installs the output via BAIN."""
    _text = _('Run FOMOD...')
    _help = _('Run the FOMOD installer and install the output.')
    _wants_install_checkbox = True

    def _execute_action(self, sel_package, ret, ui_refresh):
        # Switch the GUI to FOMOD mode and pass selected files to BAIN
        idetails = self.iPanel.detailsPanel
        idetails.set_fomod_mode(fomod_enabled=True)
        sel_package.extras_dict['fomod_dict'] = ret.install_files
        idetails.refreshCurrent(sel_package)
        if ret.should_install:
            self._perform_install(sel_package, ui_refresh)

class Installer_CaptureFomodOutput(_Installer_ARunFomod):
    _text = _dialog_title = _('Capture FOMOD Output...')
    _help = _('Run the FOMOD installer and create a new project from the '
              'output.')
    # There's no point in showing the 'Install this package' checkbox - it
    # would have the same behavior as hitting 'Cancel' for this link
    _wants_install_checkbox = False

    def _execute_action(self, sel_package, ret, ui_refresh):
        working_on_archive = sel_package.is_archive
        proj_default = (sel_package.abs_path.sbody if working_on_archive
                        else sel_package.fn_key)
        proj_name = self._askFilename(_('Project Name'), proj_default,
            inst_type=bosh.InstallerProject, check_exists=False)
        if not proj_name:
            return
        pr_path = bosh.InstallerProject.unique_name(proj_name)
        if working_on_archive:
            # This is an archive, so we have to use unpackToTemp first
            with balt.Progress(_('Unpacking Archive...')) as prog:
                src_folder = sel_package.unpackToTemp(
                    list(ret.install_files), prog)
        else:
            # This is a project, so we can directly copy the wanted
            # files
            src_folder = sel_package.abs_path
        dst_folder = bass.dirs['installers'].join(pr_path)
        dst_folder.makedirs()
        srcs_dsts = {
            src_folder.join(s): dst_folder.join(d)
            for s, d in ret.install_files.items()
        }
        env.shellCopy(srcs_dsts, parent=self.window)
        if working_on_archive:
            # We no longer need the temp directory since we copied everything
            # to the final project, so clean it up
            cleanup_temp_dir(src_folder)
        with balt.Progress(_('Creating Project...')) as prog:
            self.idata.new_info(pr_path, prog,
                                install_order=sel_package.order + 1)

class Installer_EditWizard(_Installer_AViewOrEditFile):
    """View or edit the wizard.txt associated with this package."""
    @property
    def link_text(self):
        return (_('View Wizard...') if self._run_on_archive() else
                _('Edit Wizard...'))

    @property
    def link_help(self):
        return (_('View the wizard.txt associated with this archive.')
                if self._run_on_archive() else
                _('Edit the wizard.txt associated with this project.'))

    def _enable(self):
        return super()._enable() and bool(self._selected_info.hasWizard)

    @_with_busy_cursor
    def Execute(self): self._selected_info.open_wizard()

class Installer_Wizard(_Installer_AWizardLink):
    """Runs the install wizard to select sub-packages and filter plugins."""
    def __init__(self, *, auto_wizard):
        super(Installer_Wizard, self).__init__()
        self.bAuto = auto_wizard
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
        # Installer_RunFomod has just one!
        ui_refresh = [False, False]
        idetails = self.iPanel.detailsPanel
        try:
            # Use list() since we're going to deselect packages
            for sel_package in list(self.iselected_infos()):
                with BusyCursor():
                    # Select the package we want to install - posts events to
                    # set details and update GUI
                    self.window.SelectItem(sel_package.fn_key)
                    # Switch away from FOMOD mode, the wizard may need plugin
                    # data from BAIN
                    idetails.set_fomod_mode(fomod_enabled=False)
                    idetails.refreshCurrent(sel_package)
                    try:
                        if sel_package.is_archive: ##: yak identical code in Installer_RunFomod
                            progress = balt.Progress(_('Extracting images...'),
                                                     abort=True)
                        else:
                            progress = None
                        wizard = InstallerWizard(self.window, sel_package,
                                                 self.bAuto, progress)
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
                espm_strs = idetails.gEspmList.lb_get_str_items()
                sel_package.espmNots = set()
                for index, espm in enumerate(idetails.espm_checklist_fns):
                    do_check = espm_strs[index] in ret.select_plugins or bool(
                        sel_package.espmNots.add(espm)) # bool(None) == False
                    idetails.gEspmList.lb_check_at_index(index, do_check)
                idetails.refreshCurrent(sel_package)
                #Rename the espms that need renaming
                for oldName, renamed in ret.rename_plugins.items():
                    sel_package.setEspmName(oldName, renamed)
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
                f'{installer} - Wizard Tweak [{basen}].ini')
            # Use UTF-8 since this came from a wizard.txt which could have
            # characters in it that are unencodable in cp1252 - plus this is
            # just a tweak, won't be read by the game
            with outFile.open(u'w', encoding=u'utf-8') as out:
                out.write(u'\n'.join(generateTweakLines(wizardEdits, iniFile)))
                out.write(u'\n')
            bosh.iniInfos.new_info(outFile.stail, owner=installer.fn_key)
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
            if INIList.apply_tweaks((bosh.iniInfos[outFile.stail],),
                                    target_ini_file):
                lastApplied = FName(outFile.stail)
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
            message = _('The following INI Tweaks were not automatically '
                        'applied. Be sure to apply them after installing the '
                        'package.')
            message += u'\n\n'
            message += u'\n'.join([u' * %s\n   TO: %s' % (x[0].stail, x[1])
                                   for x in manuallyApply])
            self._showInfo(message)

class Installer_OpenReadme(_SingleInstallable):
    """Opens the installer's readme if BAIN can find one."""
    _text = _(u'Open Readme')
    _help = _(u"Open the installer's readme if BAIN can find one")

    def _enable(self):
        return super()._enable() and bool(self._selected_info.hasReadme)

    @_with_busy_cursor
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
            with balt.Progress(_('Annealing...')) as progress:
                self.idata.bain_anneal(self._installables, ui_refresh,
                                       progress)
        except (CancelError,SkipError):
            pass
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)

class Installer_Duplicate(_SingleInstallable):
    """Duplicate selected Installer."""
    _text = _dialog_title = _(u'Duplicate...')

    @property
    def link_help(self):
        return _(u'Duplicate selected %(installername)s.') % (
            {u'installername': self._selected_item})

    @balt.conversation
    def Execute(self):
        """Duplicate selected Installer."""
        is_arch = self._selected_info.is_archive
        fn_inst = self._selected_item
        r, e = (fn_inst.fn_body, fn_inst.fn_ext) if is_arch else (fn_inst, '')
        newName = self._selected_info.unique_key(r, e, add_copy=True)
        allowed_exts = {e} if is_arch else set()
        result = self._askFilename(
            _(u'Duplicate %s to:') % fn_inst, newName,
            inst_type=type(self._selected_info),
            disallow_overwrite=True, no_dir=False, ##: no_dir=False?
            allowed_exts=allowed_exts, use_default_ext=False)
        if not result: return
        #--Duplicate
        with BusyCursor():
            self.idata.copy_installer(self._selected_info, result)
        self.window.RefreshUI(detail_item=result)

class Installer_Hide(_InstallerLink, UIList_Hide):
    """Installers tab version of the Hide command."""
    def _filter_unhideable(self, to_hide_items):
        # Can't hide markers, so filter those out
        return (h for h in super()._filter_unhideable(to_hide_items)
                if not self.idata[h].is_marker)

class Installer_HasExtraData(CheckLink, _RefreshingLink):
    """Toggle hasExtraData flag on installer."""
    _text = _(u'Has Extra Directories')
    _help = _(u'Allow installation of files in non-standard directories.')

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
        return _('Override global file type skipping for '
                 '%(installername)s.') % {'installername': self._selected_item}

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
        if installer.do_update(): # will return False if skipRefresh == True
            installer.refreshStatus(self.idata)
            self.idata.refresh_n()
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
            with balt.Progress(_('Installing...')) as progress:
                last = (self.mode == 'LAST')
                override = (self.mode != 'MISSING')
                try:
                    new_tweaks = self.idata.bain_install(self._installables,
                        ui_refresh, progress, last, override)
                except (CancelError, SkipError):
                    return
                except StateError as e:
                    self._showError(f'{e}')
                    return
        finally:
            self.iPanel.RefreshUIMods(*ui_refresh)
        # No error occurred and we didn't cancel or skip, but let RefreshUIMods
        # run first so it can update checkbox colors
        self._warn_nothing_installed()
        self._warn_mismatched_ini_tweaks_created(new_tweaks)

    def _warn_mismatched_ini_tweaks_created(self, new_tweaks):
        if not new_tweaks: return
        msg = _(u'The following INI Tweaks were created, because the '
            u'existing INI was different than what BAIN installed:') + \
            u'\n' + u'\n'.join([u' * %s\n' % x.stail for (x, y) in new_tweaks])
        self._showInfo(msg, title=_(u'INI Tweaks'))

    def _warn_nothing_installed(self):
        inst_packages = [self.idata[i] for i in self._installables]
        # See set_subpackage_checkmarks for the off-by-one explanation
        # Note also we have to skip active FOMODs, otherwise install commands
        # will break on them since they often have sub-packages but will pretty
        # much never have any active ones.
        unconf_packages = [p for p in inst_packages
                           if p.type == 2 and not any(p.subActives[1:]) and
                           not p.extras_dict.get('fomod_active', False)]
        if unconf_packages:
            up_title = _('Installed unconfigured packages')
            up_msg2 = _(
                'To remedy this, use the "Sub-Packages" and "Plugin '
                'Filter" boxes to select game data to install for the '
                'affected packages, then use "Anneal" to update the '
                'installation. You can also identify this problem by the '
                'white package checkbox.')
            if len(unconf_packages) == len(inst_packages):
                if len(unconf_packages) == 1:
                    up_msg1 = _(
                        'The package you installed (%(sel_pkg)s) is complex, '
                        'which means it has sub-packages. However, you did '
                        'not activate any sub-packages for it, which is '
                        'probably a mistake since it means no game data has '
                        'been installed for it.') % {
                        'sel_pkg': unconf_packages[0]}
                    up_msg2 = _(
                        'To remedy this, use the "Sub-Packages" and "Plugin '
                        'Filter" boxes to select game data to install for the '
                        'affected package, then use "Anneal" to update the '
                        'installation. You can also identify this problem by '
                        'the white package checkbox.')
                    up_title = _('Installed unconfigured package')
                else:
                    up_msg1 = _(
                        'The packages you installed are complex, which means '
                        'they have sub-packages. However, you did not '
                        'activate any sub-packages for them, which is '
                        'probably a mistake since it means no game data has '
                        'been installed for them.')
            else:
                up_msg1 = _(
                    'One or more of the packages you installed are complex, '
                    'which means they have sub-packages. However, you did not '
                    'activate any sub-packages for them, which is probably a '
                    'mistake since it means no game data has been installed '
                    'for them.')
            self._askContinue(f'{up_msg1}\n\n{up_msg2}',
                'bash.installers.nothing_installed.continue',
                title=up_title, show_cancel=False)

class Installer_InstallSmart(_NoMarkerLink):
    """A 'smart' installer for new users. Uses wizards and FOMODs if present,
    then falls back to regular install if that isn't possible."""
    _text = _(u'Install...')
    _help = _(u'Installs selected installer(s), preferring a visual method if '
              u'available.')

    def _try_installer(self, sel_package, link_instance):
        """Checks if the specified installer link is enabled and, if so, runs
        it.

        :type link_instance: EnabledLink"""
        link_instance._initData(self.window, [sel_package.fn_key])
        if link_instance._enable():
            link_instance.Execute()
            return True
        return False

    def Execute(self):
        ##: Not the best implementation, pretty readable and obvious though
        inst_wiz = Installer_Wizard(auto_wizard=False)
        inst_fomod = Installer_RunFomod()
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

class Installer_ListStructure(_SingleInstallable):
    """Copies folder structure of installer to clipboard."""
    _text = _(u'List Structure...')
    _help = _(u'Displays the folder structure of the selected installer (and '
              u'copies it to the system clipboard).')

    @balt.conversation ##: no use ! _showLog returns immediately
    def Execute(self):
        source_list_txt = self._selected_info.listSource()
        #--Get masters list
        copy_text_to_clipboard(source_list_txt)
        self._showLog(source_list_txt, title=_(u'Package Structure'),
                      fixedFont=False)

class Installer_ExportAchlist(_SingleInstallable):
    """Write an achlist file with all the destinations files for this
    installer in this configuration."""
    _text = _(u'Export Achlist')
    _mode_info_dir = u'Mod Info Exports'
    _help = (_(u'Create achlist file for use by the %s.') %
             bush.game.Ck.long_name)

    def Execute(self):
        out_dir = bass.dirs['app'].join(self.__class__._mode_info_dir)
        achlist = out_dir.join(f'{self._selected_info.fn_key}.achlist')
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
    _text = _('Move To...')
    _help = _('Move the selected installer(s) to a position of your choice.')

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
        self.idata.refresh_n()
        self.window.RefreshUI(
            detail_item=self.iPanel.detailsPanel.displayed_item)

class Installer_Open(Installers_Link, balt.UIList_OpenItems):
    """Open selected installer(s). Selected markers are skipped."""
    def _filter_unopenable(self, to_open_items):
        return (p for p in to_open_items if not self.idata[p].is_marker)

#------------------------------------------------------------------------------
class _Installer_OpenAt(_InstallerLink):
    _open_at_key: str
    _open_at_message: str
    _open_at_title: str

    def _url(self):
        raise NotImplementedError

    def Execute(self):
        if self._askContinue(self._open_at_message, self._open_at_key,
                             self._open_at_title):
            webbrowser.open(self._url())

class _Installer_OpenAt_Regex(_Installer_OpenAt):
    _regex_pattern: re.Pattern
    _regex_group: int
    _base_url: str

    def _enable(self):
        # The menu won't even be enabled if >1 plugin is selected
        x = self.__class__._regex_pattern.search(self.selected[0])
        self._mod_url_id = x and x.group(self.__class__._regex_group)
        return bool(self._mod_url_id)

    def _url(self):
        return self.__class__._base_url + self._mod_url_id

class Installer_OpenNexus(AppendableLink, _Installer_OpenAt_Regex):
    _text = f'{bush.game.nexusName}...'
    _help = _("Opens this mod's page at the %(nexusName)s.") % {
        'nexusName': bush.game.nexusName}
    _open_at_key = bush.game.nexusKey
    _open_at_message = _(
        u'Attempt to open this as a mod at %(nexusName)s? This assumes that '
        u"the trailing digits in the package's name are actually the id "
        u'number of the mod at %(nexusName)s. If this assumption is wrong, '
        u"you'll just get a random mod page (or error notice) at %("
        u'nexusName)s.') % {u'nexusName': bush.game.nexusName}
    _open_at_title = _('Open at %(nexusName)s') % {
        'nexusName': bush.game.nexusName}
    _regex_pattern = bosh.reTesNexus
    _regex_group = 2
    _base_url = bush.game.nexusUrl + 'mods/'

    def _append(self, window): return bool(bush.game.nexusUrl)

class Installer_OpenSearch(_Installer_OpenAt):
    _text = u'Google...'
    _help = _(u"Searches for this mod's title on Google.")
    _open_at_key = 'bash.installers.opensearch.continue'
    _open_at_message = _('Open a search for this on Google?')
    _open_at_title = _('Open at Google')

    def _url(self):
        def _mk_google_param(m):
            """Helper method to create a google search query for the specified
            mod name."""
            return '+'.join(re.split(r'\W+|_+', m))
        search_base = 'https://www.google.com/search?q='
        sel_inst_name = self.selected[0]
        # First, try extracting the mod name via the Nexus regex
        ma_nexus = bosh.reTesNexus.search(sel_inst_name)
        if ma_nexus and ma_nexus.group(1):
            return search_base + _mk_google_param(ma_nexus.group(1))
        # If that fails, try extracting the mod name via the TESAlliance regex
        ma_tesa = bosh.reTESA.search(sel_inst_name)
        if ma_tesa and ma_tesa.group(1):
            return search_base + _mk_google_param(ma_tesa.group(1))
        # If even that fails, just use the whole string (except the file
        # extension)
        return search_base + sel_inst_name.fn_body

class Installer_OpenTESA(_Installer_OpenAt_Regex):
    _text = u'TES Alliance...'
    _help = _(u"Opens this mod's page at TES Alliance.")
    _open_at_key = 'bash.installers.openTESA.continue'
    _open_at_message = _(
        u'Attempt to open this as a mod at TES Alliance? This assumes that '
        u"the trailing digits in the package's name are actually the id "
        u'number of the mod at TES Alliance. If this assumption is wrong, '
        u"you'll just get a random mod page (or error notice) at TES "
        u'Alliance.')
    _open_at_title = _('Open at TES Alliance')
    _regex_pattern = bosh.reTESA
    _regex_group = 2
    _base_url = 'http://tesalliance.org/forums/index.php?app=downloads&showfile='

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
            with balt.Progress(_('Uninstalling...')) as progress:
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
        with balt.Progress(_('Scanning Packages...')) as progress:
            progress.setFull(len(self.idata))
            numFiles = 0
            fn_conflicts_dir = FName(f'Conflicts - {src_order:03d}')
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
            if inst.is_project:
                for src in curConflicts:
                    srcFull = ijoin(package, src)
                    destFull = ijoin(fn_conflicts_dir, g_path, src)
                    if srcFull.exists():
                        progress(curFile, f'{self._selected_item}\n' + _(
                            u'Copying files...') + u'\n' + src)
                        srcFull.copyTo(destFull)
                        curFile += 1
            else:
                unpack_dir = inst.unpackToTemp(curConflicts,
                    SubProgress(progress, curFile, curFile + len(curConflicts),
                                len(curConflicts)))
                unpack_dir.moveTo(ijoin(fn_conflicts_dir, g_path))
                cleanup_temp_dir(unpack_dir) # Mark as cleaned up internally
                curFile += len(curConflicts)
            return curFile
        with balt.Progress(_('Copying Conflicts...')) as progress:
            progress.setFull(numFiles)
            curFile = 0
            g_path = package = self._selected_item
            curConflicts = srcConflicts
            curFile = _copy_conflicts(curFile)
            for order,package,curConflicts in packConflicts:
                g_path = f'{order if order < src_order else order + 1:03d} ' \
                         f'- {package}'
                curFile = _copy_conflicts(curFile)
        self.idata.new_info(fn_conflicts_dir, install_order=src_order + 1)
        self.window.RefreshUI(detail_item=fn_conflicts_dir)

#------------------------------------------------------------------------------
# InstallerDetails Plugin Filter Links ----------------------------------------
#------------------------------------------------------------------------------
class _Installer_Details_Link(EnabledLink):
    window: InstallersDetails

    def _enable(self): return len(self.window.espm_checklist_fns) != 0

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
        self._installer.espmNots = set(self.window.espm_checklist_fns)
        self.window.gEspmList.set_all_checkmarks(checked=False)
        self.window.refreshCurrent(self._installer)

class Installer_Espm_Rename(_Installer_Details_Link):
    """Changes the installed name for a plugin."""
    _text = _(u'Rename...')
    _help = _(u'Changes the name under which this plugin will be installed.')

    def _enable(self): return self.selected != -1

    def Execute(self):
        curName = self.window.get_espm(self.selected)
        newName = self._askText(_(u'Enter new name (without the extension):'),
                                title=_(u'Rename Plugin'), default=curName.fn_body)
        if not newName: return
        if (newName := newName + curName.fn_ext) in \
                self.window.espm_checklist_fns:
            return
        self._installer.setEspmName(curName, newName)
        self.window.refreshCurrent(self._installer)

class Installer_Espm_Reset(_Installer_Details_Link):
    """Resets the installed name for a plugin."""
    _text = _(u'Reset Name')
    _help = _(u'Resets the name under which this plugin will be installed '
              u'back to its default name.')

    def _enable(self):
        if self.selected == -1: return False
        self.curName = self.window.get_espm(self.selected)
        return self._installer.isEspmRenamed(self.curName)

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
        for i in range(espm_list.lb_get_items_count()):
            sub_prefix = ['   ', '** '][espm_list.lb_is_checked_at_index(i)]
            subs += f'{sub_prefix}{self.window.get_espm(i)}\n'
        subs += u'[/spoiler]'
        copy_text_to_clipboard(subs)
        self._showLog(subs, title=_(u'Plugin List'), fixedFont=False)

class Installer_Espm_JumpToMod(_Installer_Details_Link):
    """Jumps to a plugin in the Mods tab, if it is installed."""
    _text = _('Jump to Plugin')
    _help = _('Jumps to this plugin on the Mods tab. You can double-click on '
              'this plugin to the same effect.')

    def _enable(self):
        if self.selected == -1: return False
        self.target_plugin = self.window.get_espm(self.selected)
        return self.target_plugin in bosh.modInfos

    def Execute(self):
        balt.Link.Frame.notebook.SelectPage(u'Mods', self.target_plugin)

#------------------------------------------------------------------------------
# InstallerDetails Sub-package Links ------------------------------------------
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
        sp_list = self.window.gSubList
        for i in range(sp_list.lb_get_items_count()):
            subs += ['   ', '** '][sp_list.lb_is_checked_at_index(i)]
            subs += sp_list.lb_get_str_item_at_index(i) + '\n'
        subs += u'[/spoiler]'
        copy_text_to_clipboard(subs)
        self._showLog(subs, title=_(u'Sub-Package Lists'), fixedFont=False)

#------------------------------------------------------------------------------
# InstallerArchive Links ------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerArchive_Unpack(_ArchiveOnly):
    """Unpack installer package(s) to Project(s)."""
    _text = _dialog_title = _(u'Unpack to Project(s)...')
    _help = _(u'Unpack installer package(s) to Project(s)')

    @balt.conversation
    def Execute(self):
        # Ask the user first to avoid the progress dialog shoving itself over
        # any dialogs we pop up
        to_unpack = []
        for iname, installer in self.idata.sorted_pairs(self.selected):
            project = iname.fn_body
            if len(self.selected) == 1:
                project = self._askFilename(_('Unpack %(target_archive)s to '
                                              'Project:') % {
                    'target_archive': iname}, project,
                    inst_type=bosh.InstallerProject, no_file=True)
                if not project: return
            elif project in self.idata and not self._askYes( #only needed check
                    _(u'%s already exists. Overwrite it?') % project,
                    default_is_yes=False):
                continue
            # All check passed, we can unpack this
            to_unpack.append((installer, project))
        # We're safe to show the progress dialog now
        with balt.Progress(_('Unpacking to Project...')) as progress:
            projects = []
            for installer, project in to_unpack:
                count_unpacked = installer.unpackToProject(project,
                    SubProgress(progress, 0, 0.8))
                if not count_unpacked:
                    continue # no files were unpacked - stat would fail below
                self.idata.new_info(project, SubProgress(progress, 0.8, 0.99),
                    install_order=installer.order + 1, do_refresh=False)
                projects.append(project)
            if not projects: return
            self.idata.refresh_ns()
            self.window.RefreshUI(detail_item=projects[-1]) # all files ? can status of others change ?
            self.window.SelectItemsNoCallback(projects)

#------------------------------------------------------------------------------
# InstallerProject Links ------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerProject_OmodConfig(_SingleProject):
    """Projects only. Allows you to read/write omod configuration info."""
    _text = _('OMOD Info...')
    _help = _('Projects only. Allows you to read/write OMOD configuration '
              'info.')

    def Execute(self):
        InstallerProject_OmodConfigDialog(self.window,
                                          self._selected_item).show_frame()
#------------------------------------------------------------------------------
class Installer_SyncFromData(_SingleInstallable):
    """Synchronize an archive or project with files from the Data directory."""
    _text = _('Sync From Data...')
    _help = _(u'Synchronize an installer with files from the %s '
              u'directory.') % bush.game.mods_dir

    def _enable(self):
        return super()._enable() and bool(self._selected_info.missingFiles or
            self._selected_info.mismatchedFiles)

    def Execute(self):
        was_rar = self._selected_item.fn_ext == '.rar'
        if was_rar and not self._askYes('\n\n'.join([
                _('.rar files cannot be modified. Wrye Bash can however '
                  'repack them to .7z files, which can then be modified.'),
                _('Note that doing this will leave the old .rar file behind, '
                  'so you may want to manually delete it afterwards.'),
                _("Click 'Yes' to repack, or 'No' to abort the sync.")])):
            return # user clicked 'No'
        missing = sorted(self._selected_info.missingFiles)
        mismatched = sorted(self._selected_info.mismatchedFiles)
        ed_ok, ed_missing, ed_mismatched = SyncFromDataEditor.display_dialog(
            self.window, pkg_missing=missing, pkg_mismatched=mismatched,
            pkg_name=self._selected_item)
        if not ed_ok or (not ed_missing and not ed_mismatched):
            return # Aborted by user or nothing left to sync, cancel
        #--Sync it, baby!
        with balt.Progress(self._text) as progress:
            progress(0.1, _('Updating files.'))
            actual_upd, actual_del = self._selected_info.sync_from_data(
                set(ed_missing) | set(ed_mismatched),
                progress=SubProgress(progress, 0.1, 0.7))
            if (actual_del != len(ed_missing)
                    or actual_upd != len(ed_mismatched)):
                msg = '\n'.join([
                    _('Something went wrong when updating '
                      '%(target_package)s.'),
                    _('Deleted %(act_deleted)d files, expected to delete '
                      '%(exp_deleted)d files.'),
                    _('Updated %(act_updated)d files, expected to update '
                      '%(exp_updated)d files.'),
                    _('Check the integrity of %(target_package)s.')])
                self._showWarning(msg % {
                    'target_package': self._selected_item,
                    'act_deleted': actual_del, 'exp_deleted': len(ed_missing),
                    'act_updated': actual_upd,
                    'exp_updated': len(ed_mismatched)})
            self._selected_info.do_update(force_update=True,
                recalculate_project_crc=True,
                progress=SubProgress(progress, 0.7, 0.8))
            if was_rar:
                final_package = self._selected_info.writable_archive_name()
                # Move the new archive directly underneath the old archive
                self.idata.new_info(final_package, progress, is_proj=False,
                    do_refresh=False, _index=0.8,
                    install_order=self._selected_info.order + 1)
                created_package = self.idata[final_package]
                created_package.is_active = self._selected_info.is_active
            self.idata.refresh_ns(progress=SubProgress(progress, 0.9, 0.99))
            self.window.RefreshUI()

#------------------------------------------------------------------------------
class InstallerProject_Pack(_SingleProject):
    """Pack project to an archive."""
    _text = _dialog_title = _(u'Pack to Archive...')
    _help = _(u'Pack project to an archive')
    release = False

    @balt.conversation
    def Execute(self):
        #--Generate default filename from the project name and the default extension
        archive_name = self._selected_item + archives.defaultExt
        #--Confirm operation
        archive_name = self._askFilename(
            _(u'Pack %s to Archive:') % self._selected_item, archive_name)
        if not archive_name: return
        installer = self._selected_info
        #--Archive configuration options
        blockSize = None
        if archive_name.fn_ext in archives.noSolidExts:
            isSolid = False
        else:
            if not u'-ms=' in bass.inisettings['7zExtraCompressionArguments']:
                isSolid = self._askYes(_('Use solid compression for %s?')
                                       % archive_name, default_is_yes=False)
                if isSolid:
                    blockSize = self._promptSolidBlockSize(title=self._text)
            else:
                isSolid = True
        with balt.Progress(_('Packing to Archive...')) as progress:
            #--Pack
            installer.packToArchive(self._selected_item, archive_name, isSolid,
                                    blockSize, SubProgress(progress, 0, 0.8),
                                    release=self.__class__.release)
            #--Add the new archive to Bash
            iArchive = self.idata.new_info(archive_name, progress,
                is_proj=False, install_order=installer.order + 1)
            iArchive.blockSize = blockSize
        self.window.RefreshUI(detail_item=archive_name)

#------------------------------------------------------------------------------
class InstallerProject_ReleasePack(InstallerProject_Pack):
    """Pack project to an archive for release. Ignores dev files/folders."""
    _text = _(u'Package for Release...')
    _help = _(
        u'Pack project to an archive for release. Ignores dev files/folders')
    release = True

#------------------------------------------------------------------------------
class _InstallerConverter_Link(_ArchiveOnly):

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
                    sorted(x.fn_key for x in installers))))
        if duplicates:
            msg = _(u'Installers with identical content selected:') + u'\n'
            msg += '\n'.join(sorted(f'CRC: {k:08X}{v}' for k, v in duplicates))
            if message: msg += u'\n' + message
            self._showError(msg, _(u'Identical installers content'))
            return True
        return False

class InstallerConverter_Apply(_InstallerConverter_Link):
    """Apply a BAIN Conversion File."""
    _dialog_title = _(u'Apply BCF...')

    def __init__(self,converter,selected):
        super(InstallerConverter_Apply, self).__init__()
        self.converter = converter
        #--Add asterisks to indicate the number of unselected archives that the BCF uses
        self.dispName = self.converter.fullPath.sbody
        self._selected = selected

    @property
    def link_text(self):
        return self.dispName

    @property
    def link_help(self):
        return _(u'Applies %(bcf)s to the selected installer(s).') % {
            u'bcf': self.dispName}

    @balt.conversation
    def Execute(self):
        if self._check_identical_content(_(
                'Please only select the packages this BCF was made for.')):
            return
        # all installers that this converter needs are present and unique
        crc_installer = {x.crc: x for x in self.iselected_infos()}
        #--Generate default filename from BCF filename
        defaultFilename = self.converter.fullPath.sbody[:-4] + archives\
            .defaultExt
        #--List source archives
        message = _('Using:') + '\n* ' + '\n* '.join(sorted(
            f'({x:08X}) - {crc_installer[x]}' for x in
            self.converter.srcCRCs)) + '\n'
        #--Ask for an output filename
        destArchive = self._askFilename(message, filename=defaultFilename)
        if not destArchive: return
        with balt.Progress(_('Converting to Archive...')) as progress:
            #--Perform the conversion
            msg = _('%(dest_archive)s: An error occurred while applying a '
                    'BCF. This can occur if the BCF is applied to an already '
                    'BCF-converted archive. More details about the error '
                    'follow:') % {'dest_archive': destArchive}
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
    _help = _('Applies the BAIN conversion files (BCFs) embedded in the '
              'selected package(s).')
    _dialog_title = _(u'Apply BCF...')

    @balt.conversation
    def Execute(self):
        iname, inst = next(self.iselected_pairs()) # first selected pair
        #--Ask for an output filename
        dest = self._askFilename(_('Output file:'), filename=iname)
        if not dest: return
        with balt.Progress(_('Extracting BCF...')) as progress:
            destinations, converted = self.idata.applyEmbeddedBCFs(
                [inst], [dest], progress)
            if not destinations: return # destinations == [dest] if all was ok
        self.window.RefreshUI(detail_item=dest)

class InstallerConverter_Create(_InstallerConverter_Link):
    """Create BAIN conversion file."""
    _text = _(u'Create...')
    _help = _(u'Creates a new BAIN conversion file (BCF).')
    _dialog_title = _(u'Create BCF...')

    def Execute(self):
        if self._check_identical_content(
                _(u'Please only select installers that are needed.')):
            return
        # all installers that this converter needs are unique
        crc_installer = {x.crc: x for x in self.iselected_infos()}
        #--Generate allowable targets
        readTypes = f'*{";*".join(archives.readExts)}'
        #--Select target archive
        destArchive = self._askOpen(title=_("Select the BAIN'ed Archive:"),
            defaultDir=self.idata.store_dir, wildcard=readTypes)
        if not destArchive: return
        #--Error Checking
        bcf_fname = destArchive = FName(destArchive.stail)
        if not destArchive or destArchive.fn_ext not in archives.readExts:
            self._showWarning(_('%(arcname)s is not a valid archive name.') % {
                'arcname': destArchive})
            return
        if destArchive not in self.idata:
            self._showWarning(_('%(arcname)s must be in the Bash Installers '
                                'directory.') % {'arcname': destArchive})
            return
        if bcf_fname.fn_body[-4:].lower() != '-bcf':
            bcf_fname = FName(f'{bcf_fname.fn_body}-BCF{archives.defaultExt}')
        #--List source archives and target archive
        msg = _('Convert:') + '\n* '
        msg += '\n* '.join(sorted(f'({v.crc:08X}) - {k}' for k, v in
                                  self.iselected_pairs())) + '\n\n' + _('To:')
        msg += f'\n* ({self.idata[destArchive].crc:08X}) - {destArchive}\n'
        #--Confirm operation
        bcf_fname = self._askFilename(msg, bcf_fname,
                                      base_dir=converters.converters_dir,
                                      allowed_exts={archives.defaultExt})
        if not bcf_fname: return
        #--Error checking
        if bcf_fname.fn_body[-4:].lower() != '-bcf':
            bcf_fname = FName(f'{bcf_fname.fn_body}-BCF{archives.defaultExt}')
        if (conv_path := converters.converters_dir.join(bcf_fname)).exists():
            #--It is safe to removeConverter, even if the converter isn't overwritten or removed
            #--It will be picked back up by the next refresh.
            self.idata.converters_data.removeConverter(conv_path)
        destInstaller = self.idata[destArchive]
        blockSize = None
        if destInstaller.isSolid:
            blockSize = self._promptSolidBlockSize(
                title=self._dialog_title, default_size=destInstaller.blockSize or 0)
        with balt.Progress(_('Creating %(bcf_name)s...') % {
            'bcf_name': bcf_fname}) as progress:
            #--Create the converter
            conv = InstallerConverter.from_scratch(self.selected, self.idata,
                destArchive, bcf_fname, blockSize, progress)
            #--Add the converter to Bash
            self.idata.converters_data.addConverter(conv)
        #--Refresh UI
        with balt.Progress(_('Refreshing Converters...')) as progress:
            self.idata.irefresh(progress, what='C')
        #--Generate log
        log = LogFile(io.StringIO())
        log.setHeader(f'== {_("Overview")}\n')
        # log('{{CSS:wtxt_sand_small.css}}')
        log(f'. {_("Name")}: {bcf_fname}')
        log(f'. {_("Size")}: {round_size(conv.fullPath.psize)}')
        log(f'. {_("Remapped: %u file(s)") % len(conv.convertedFiles)}')
        log.setHeader('. ' + _('Requires: %u file(s)') % len(conv.srcCRCs))
        log('  * ' + '\n  * '.join(sorted(
            f'({x:08X}) - {crc_installer[x]}' for x in conv.srcCRCs
            if x in crc_installer)))
        log.setHeader('. ' + _('Options:'))
        log(f'  *  {_("Skip Voices")} = {bool(conv.skipVoices)}')
        log(f'  *  {_("Solid Archive")} = {bool(conv.isSolid)}')
        if conv.isSolid:
            if conv.blockSize:
                log(f'    *  {_("Solid Block Size")} = {conv.blockSize:d}')
            else:
                log(f'    *  {_("Solid Block Size")} = 7z default')
        log(f'  *  {_("Has Comments")} = {bool(conv.comments)}')
        log(f'  *  {_("Has Extra Directories")} = {bool(conv.hasExtraData)}')
        log(f'  *  {_("Has Plugins Unselected")} = {bool(conv.espmNots)}')
        log(f'  *  {_("Has Packages Selected")} = {bool(conv.subActives)}')
        log.setHeader('. ' + _('Contains: %u file(s)') % len(
            conv.bcf_missing_files))
        log('  * ' + '\n  * '.join(sorted(map(str, conv.bcf_missing_files))))
        if log:
            self._showLog(log.out.getvalue(), title=_('BCF Information'))

#------------------------------------------------------------------------------
# Installer Submenus ----------------------------------------------------------
#------------------------------------------------------------------------------
class InstallerConverter_ConvertMenu(balt.MenuLink):
    """Apply BCF SubMenu."""
    _text = _('Apply..')

    def _enable(self):
        """Return False to disable the converter menu, otherwise populate its
        links attribute and return True."""
        linkSet = set()
        del self.links[:]
        #--Converters are linked by CRC, not archive name
        #--So, first get all the selected archive CRCs
        selected = self.selected
        idata = self._data_store # InstallersData singleton
        selectedCRCs = set(inst.crc for inst in self.iselected_infos())
        srcCRCs = set( # crcs of all installers referenced by some converter
            inst_crc_converters := idata.converters_data.srcCRC_converters)
        #--There is no point in testing each converter unless
        #--every selected archive has an associated converter
        if selectedCRCs <= srcCRCs:
            #--Test every converter for every selected archive
            bcfs = {*chain( # converters referencing selected installers
                *(inst_crc_converters[inst_crc] for inst_crc in selectedCRCs))}
            # Only add a link to the converter if all of its required archives
            # are selected
            linkSet = {conv for conv in bcfs if conv.srcCRCs <= selectedCRCs}
        #--If the archive is a single archive with an embedded BCF, add that
        if len(selected) == 1 and self._first_selected().hasBCF:
            self.links.append(InstallerConverter_ApplyEmbedded())
        #--Disable the menu if there were no valid converters found
        elif not linkSet:
            return False
        #--Otherwise add each link in alphabetical order, and
        #--indicate the number of additional, unselected archives
        #--that the converter requires
        for converter in sorted(linkSet, key=lambda x: x.fullPath.tail):
            self.links.append(InstallerConverter_Apply(converter, selected))
        return True

class _Installer_TypeOnlyMenu(AppendableLink, balt.MenuLink):
    """Base class for archive/project-only menus."""
    _wants_archive: bool

    def _append(self, window):
        self.selected = window.GetSelected() # append runs before _initData
        self.window = window # and the idata access is via self.window
        return all(inst.is_archive == self._wants_archive
                   for inst in self.iselected_infos())

class Installer_ArchiveMenu(_Installer_TypeOnlyMenu):
    """Archive-specific menu."""
    _text = _('Archive..')
    _wants_archive = True

class Installer_ProjectMenu(_Installer_TypeOnlyMenu):
    """Project-specific menu."""
    _text = _('Project..')
    _wants_archive = False
