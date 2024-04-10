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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Links initialization functions. Each panel's UIList has main and items Links
attributes which are populated here. Therefore the layout of the menus is
also defined in these functions."""
import os
import shlex

from . import BSAList, INIList, InstallersList, \
    InstallersPanel, MasterList, ModList, SaveList, ScreensList
# modules below define the __all__ directive
from .app_buttons import *
from .bsa_links import *
from .constants import oblivion_tools, oblivion_java_tools, loot_bosh, \
    skyrim_tools, modeling_tools_buttons, texture_tool_buttons, audio_tools, \
    misc_tools, nifskope
from .files_links import *
from .ini_links import *
from .installer_links import *
from .installers_links import *
from .misc_links import *
from .mod_links import *
from .mods_links import *
from .saves_links import *
# Rest of internal imports
from .. import bass, bush
from ..balt import BashStatusBar, MenuLink, SeparatorLink, UIList_Delete, \
    UIList_Hide, UIList_OpenItems, UIList_OpenStore, UIList_Rename
from ..bolt import os_name
from ..env import init_app_links
from ..game import MergeabilityCheck
from ..game.patch_game import PatchGame
from ..gui import GuiImage, get_image

_is_oblivion = bush.game.fsName == 'Oblivion'
_is_skyrim = bush.game.fsName == 'Skyrim'
_j = os.path.join

#------------------------------------------------------------------------------
def InitStatusBar():
    """Initialize status bar buttons."""
    badIcons = [get_image('error_cross.16')] * 3 ##: 16, 24, 32?
    __fp = GuiImage.from_path
    def _png_list(template):
        return [__fp(template % i, iconSize=i) for i in (16, 24, 32)]
    def _svg_list(svg_fname):
        return [__fp(svg_fname, iconSize=i) for i in (16, 24, 32)]
    #--Bash Status/LinkBar
    BashStatusBar.obseButton = obse_button = ObseButton('OBSE')
    all_links = [
        obse_button,
        AutoQuitButton('AutoQuit'),
        GameButton(_png_list(f'games/{bush.game.game_icon}'))
    ]
    all_xes = dict.fromkeys( # keep order to not reorder much
        game_class.Xe.full_name for game_class in PatchGame.supported_games())
    xe_images = _png_list('tools/tes4edit%s.png')
    def _tool_args(app_key, app_path_data, clazz=AppButton, **kwargs):
        app_launcher, app_name, path_kwargs, *cli_args = app_path_data
        uid = kwargs.setdefault('uid', app_key)
        if app_key in {'Steam', 'LOOT'}:
            list_img = _svg_list(_j('tools', f'{app_key.lower()}.svg'))
        elif uid == 'TESCS':
            list_img = _png_list(f'tools/{imn}') if (
                imn := bush.game.Ck.image_name) else badIcons
        elif app_key[:-4] in all_xes: # chop off 'Path'
            list_img = xe_images
        else:
            list_img = _png_list(_j('tools', f'{app_key.lower()}%s.png'))
        if cli_args: # for tools defined in constants.py and TES4View/Trans
            kwargs['cli_args'] = (*kwargs.get('cli_args', ()), *cli_args)
        return clazz.app_button_factory(app_key, app_launcher, path_kwargs,
            list_img, app_name, **kwargs)
    all_links.append(_tool_args(None, (bush.game.Ck.exe,
            bush.game.Ck.long_name, {'root_dirs': 'app'}), clazz=TESCSButton,
        uid='TESCS', display_launcher=bool(bush.game.Ck.ck_abbrev)))
    # Launchers of tools ------------------------------------------------------
    all_links.extend(_tool_args(*tool, display_launcher=_is_oblivion) for tool
                     in oblivion_tools.items())
    all_links.extend(_tool_args(k, (*v, *shlex.split(bass.inisettings[
        f'{(u := k[:-4])}JavaArg'], posix=os_name != 'nt')), uid=u,
        display_launcher=_is_oblivion) for k, v in oblivion_java_tools.items())
    all_links.extend(_tool_args(*tool, display_launcher=_is_skyrim,
        uid=tool[0][:-4]) for tool in skyrim_tools.items())
    # xEdit -------------------------------------------------------------------
    for xe_name in all_xes:
        args = (f'{xe_name}.exe', xe_name, {'root_dirs': 'app'})
        all_links.append(_tool_args(f'{xe_name}Path', args, uid=xe_name,
            display_launcher=bush.game.Xe.full_name == xe_name,
            cli_args=(f'-{xe_name[:-4]}', '-edit'), clazz=AppXEdit))
        if xe_name == 'TES4Edit':
            # set the paths for TES4Trans/TES4View, supposing they are in the
            # same folder with TES4Edit - these are not specified in the ini
            tes4_edit_dir = all_links[-1].app_path.head
            args = 'TES4View.exe', 'TES4View', {
                'root_dirs': tes4_edit_dir}, '-TES4', '-view'
            all_links.append(_tool_args('TES4ViewPath', args, uid='TES4View',
                display_launcher=_is_oblivion, clazz=AppXEdit))
            args = 'TES4Trans.exe', 'TES4Trans', {
                'root_dirs': tes4_edit_dir}, '-TES4', '-translate'
            all_links.append(_tool_args('TES4TransPath', args, uid='TES4Trans',
                display_launcher=_is_oblivion, clazz=AppXEdit))
    all_links.append(  #Tes4LODGen
        _tool_args('Tes4LodGenPath', ('TES4LodGen.exe', 'Tes4LODGen',
            {'root_dirs': 'app'}), clazz=AppXEdit, uid='TES4LODGen',
            display_launcher=_is_oblivion, cli_args=('-TES4', '-lodgen')))
    all_links.extend(_tool_args(*tool, display_launcher=bool(dipl), clazz=cls)
        for tool, cls, dipl in zip(loot_bosh.items(), (AppLOOT, AppBOSS), (
            bush.game.loot_game_name, bush.game.boss_game_name)))
    show_model = bass.inisettings['ShowModelingToolLaunchers']
    all_links.extend(_tool_args(*mt, display_launcher=show_model) for mt in
                     modeling_tools_buttons.items())
    show_texture = bass.inisettings['ShowTextureToolLaunchers']
    all_links.append(_tool_args(*nifskope, # Nifskope
                                display_launcher=show_model or show_texture))
    all_links.extend(_tool_args(*tt, display_launcher=show_texture) for tt in
                     texture_tool_buttons.items())
    all_links.extend(_tool_args(*at, display_launcher=bass.inisettings[
        'ShowAudioToolLaunchers']) for at in audio_tools.items())
    all_links.extend(_tool_args(*mt) for mt in misc_tools.items())
    #--Custom Apps
    for pth, img_path, shortcut_desc in init_app_links(
            bass.dirs['mopy'].join('Apps')):
        if img_path is None:
            imgs = badIcons # use the 'x' icon
        else:
            imgs = [__fp(p, GuiImage.img_types['.ico'], x) for x, p in
                    zip((16, 24, 32), img_path)]
        #target.stail would keep the id on renaming the .lnk but this is unique
        app_key = pth.stail.lower()
        all_links.append(LnkButton(pth, imgs, shortcut_desc, app_key,
                                   canHide=False))
    #--Final couple
    all_links.append(DocBrowserButton('DocBrowser'))
    all_links.append(PluginCheckerButton('ModChecker'))
    all_links.append(SettingsButton('Settings', canHide=False))
    all_links.append(HelpButton('Help', canHide=False))
    all_links.append(RestartButton('Restart'))
    BashStatusBar.all_sb_links = {li.uid: li for li in all_links}

#------------------------------------------------------------------------------
def InitMasterLinks():
    """Initialize master list menus."""
    #--MasterList: Column Links
    MasterList.column_links.append_link(SortByMenu(
        sort_options=[Mods_MastersFirst(), Mods_ActiveFirst()]))
    MasterList.column_links.append_link(ColumnsMenu())
    MasterList.column_links.append_link(SeparatorLink())
    MasterList.column_links.append_link(Master_AllowEdit())
    MasterList.column_links.append_link(Master_ClearRenames())
    #--MasterList: Item Links
    MasterList.context_links.append_link(Master_ChangeTo())
    MasterList.context_links.append_link(Master_Disable())
    MasterList.context_links.append_link(SeparatorLink())
    MasterList.context_links.append_link(Master_JumpTo())

#------------------------------------------------------------------------------
def InitInstallerLinks():
    """Initialize Installers tab menus."""
    #--Column links
    # Sorting and Columns
    InstallersList.column_links.append_link(SortByMenu(
        sort_options=[Installers_InstalledFirst(), Installers_SimpleFirst(),
                      Installers_ProjectsFirst()]))
    InstallersList.column_links.append_link(ColumnsMenu())
    InstallersList.column_links.append_link(SeparatorLink())
    if True: #--Files
        files_menu = MenuLink(_('Files..'))
        files_menu.links.append_link(UIList_OpenStore())
        files_menu.links.append_link(
            Files_Unhide(_('Unhides hidden installers.')))
        files_menu.links.append_link(SeparatorLink())
        files_menu.links.append_link(Installers_CreateNewProject())
        files_menu.links.append_link(Installers_AddMarker())
        InstallersList.column_links.append_link(files_menu)
        InstallersList.column_links.append_link(SeparatorLink())
    if True: #--Data
        data_menu = MenuLink(_('Data..'))
        data_menu.links.append_link(Installers_MonitorExternalInstallation())
        data_menu.links.append_link(Installers_CleanData())
        data_menu.links.append_link(SeparatorLink())
        data_menu.links.append_link(Installers_RefreshData())
        data_menu.links.append_link(Installers_FullRefresh())
        InstallersList.column_links.append_link(data_menu)
    if True: #--Packages
        packages_menu = MenuLink(_('Packages..'))
        packages_menu.links.append_link(Installers_AnnealAll())
        packages_menu.links.append_link(Installers_UninstallAllPackages())
        packages_menu.links.append_link(Installers_ApplyEmbeddedBCFs())
        packages_menu.links.append_link(SeparatorLink())
        packages_menu.links.append_link(Installers_ListPackages())
        packages_menu.links.append_link(Installers_WizardOverlay())
        packages_menu.links.append_link(SeparatorLink())
        packages_menu.links.append_link(Installers_ExportOrder())
        packages_menu.links.append_link(Installers_ImportOrder())
        InstallersList.column_links.append_link(packages_menu)
        InstallersList.column_links.append_link(SeparatorLink())
    InstallersList.column_links.append_link(Installers_Enabled())
    InstallersList.column_links.append_link(Installers_AvoidOnStart())
    InstallersList.column_links.append_link(Installers_ValidateFomod())
    if True: #--Installation Settings
        inst_settings_menu = MenuLink(_('Installation Settings..'))
        inst_settings_menu.links.append_link(Installers_AutoAnneal())
        inst_settings_menu.links.append_link(Installers_AutoWizard())
        inst_settings_menu.links.append_link(Installers_AutoRefreshProjects())
        inst_settings_menu.links.append_link(Installers_IgnoreFomod())
        inst_settings_menu.links.append_link(SeparatorLink())
        inst_settings_menu.links.append_link(Installers_BsaRedirection())
        inst_settings_menu.links.append_link(Installers_RemoveEmptyDirs())
        InstallersList.column_links.append_link(inst_settings_menu)
    if True: #--Conflict Settings
        cflt_settings_menu = MenuLink(_('Conflict Settings..'))
        cflt_settings_menu.links.append_link(
            Installers_ShowInactiveConflicts())
        cflt_settings_menu.links.append_link(Installers_ShowLowerConflicts())
        cflt_settings_menu.links.append_link(
            Installers_ShowActiveBSAConflicts())
        InstallersList.column_links.append_link(cflt_settings_menu)
    InstallersList.column_links.append_link(SeparatorLink())
    InstallersList.column_links.append_link(Installers_SkipVanillaContent())
    InstallersList.column_links.append_link(Installers_GlobalSkips())
    InstallersList.column_links.append_link(Installers_GlobalRedirects())
    InstallersList.column_links.append_link(SeparatorLink())
    InstallersList.column_links.append_link(Misc_SaveData())
    InstallersList.column_links.append_link(Misc_SettingsDialog())
    #--Item links
    if True: #--File
        file_menu = MenuLink(_('File..'))
        file_menu.links.append_link(UIList_OpenItems())
        file_menu.links.append_link(UIList_Rename())
        file_menu.links.append_link(Installer_Duplicate())
        file_menu.links.append_link(Installer_Hide())
        file_menu.links.append_link(UIList_Delete())
        InstallersList.context_links.append_link(file_menu)
    if True: #--Open At...
        openAtMenu = MenuLink(_('Open At..'), oneDatumOnly=True)
        openAtMenu.links.append_link(Installer_OpenSearch())
        openAtMenu.links.append_link(Installer_OpenNexus())
        openAtMenu.links.append_link(Installer_OpenTESA())
        InstallersList.context_links.append_link(openAtMenu)
    #--Install, uninstall, etc.
    InstallersList.context_links.append_link(SeparatorLink())
    InstallersList.context_links.append_link(Installer_OpenReadme())
    InstallersList.context_links.append_link(Installer_Anneal())
    InstallersList.context_links.append_link(Installer_QuickRefresh())
    InstallersList.context_links.append_link(Installer_Move())
    InstallersList.context_links.append_link(Installer_SyncFromData())
    InstallersList.context_links.append_link(SeparatorLink())
    InstallersList.context_links.append_link(Installer_InstallSmart())
    if True: #--Advanced Installation
        installMenu = MenuLink(_('Advanced Installation..'))
        installMenu.links.append_link(Installer_Install())
        installMenu.links.append_link(Installer_Install('MISSING'))
        installMenu.links.append_link(Installer_Install('LAST'))
        installMenu.links.append_link(SeparatorLink())
        if True: #--FOMOD Installer
            fomod_menu = MenuLink(_('FOMOD Installer..'))
            fomod_menu.links.append_link(Installer_RunFomod())
            fomod_menu.links.append_link(Installer_CaptureFomodOutput())
            fomod_menu.links.append_link(SeparatorLink())
            fomod_menu.links.append_link(Installer_EditFomod())
            installMenu.links.append_link(fomod_menu)
        if True: #--Wizard Installer
            wizardMenu = MenuLink(_('Wizard Installer..'))
            wizardMenu.links.append_link(Installer_Wizard(auto_wizard=False))
            wizardMenu.links.append_link(Installer_Wizard(auto_wizard=True))
            wizardMenu.links.append_link(SeparatorLink())
            wizardMenu.links.append_link(Installer_EditWizard())
            installMenu.links.append_link(wizardMenu)
        InstallersList.context_links.append_link(installMenu)
    InstallersList.context_links.append_link(Installer_Uninstall())
    InstallersList.context_links.append_link(SeparatorLink())
    if True: #--Package - always visible
        package_menu = MenuLink(_('Package..'))
        package_menu.links.append_link(Installer_Refresh())
        if bush.game.has_achlist:
            package_menu.links.append_link(Installer_ExportAchlist())
        package_menu.links.append_link(Installer_ListStructure())
        package_menu.links.append_link(Installer_CopyConflicts())
        package_menu.links.append_link(SeparatorLink())
        package_menu.links.append_link(Installer_HasExtraData())
        package_menu.links.append_link(Installer_OverrideSkips())
        package_menu.links.append_link(Installer_SkipVoices())
        InstallersList.context_links.append_link(package_menu)
    if True: #--Archive - only visible for archives
        archive_menu = Installer_ArchiveMenu()
        archive_menu.links.append_link(InstallerArchive_Unpack())
        if True: #--BAIN Conversions
            conversions_menu = MenuLink(_('BAIN Conversions..'))
            conversions_menu.links.append_link(InstallerConverter_Create())
            conversions_menu.links.append_link(
                InstallerConverter_ConvertMenu())
            archive_menu.append(conversions_menu)
        InstallersList.context_links.append_link(archive_menu)
    if True: #--Project - only visible for projects
        project_menu = Installer_ProjectMenu()
        project_menu.links.append_link(InstallerProject_Pack())
        project_menu.links.append_link(InstallerProject_ReleasePack())
        project_menu.links.append_link(Installer_SkipRefresh())
        project_menu.links.append_link(InstallerProject_OmodConfig())
        InstallersList.context_links.append_link(project_menu)
    # Plugin Filter: Main Menu
    InstallersPanel.espmMenu.append_link(Installer_Espm_SelectAll())
    InstallersPanel.espmMenu.append_link(Installer_Espm_DeselectAll())
    InstallersPanel.espmMenu.append_link(Installer_Espm_List())
    InstallersPanel.espmMenu.append_link(SeparatorLink())
    # Plugin Filter: Item Menu
    InstallersPanel.espmMenu.append_link(Installer_Espm_Rename())
    InstallersPanel.espmMenu.append_link(Installer_Espm_Reset())
    InstallersPanel.espmMenu.append_link(Installer_Espm_ResetAll())
    InstallersPanel.espmMenu.append_link(SeparatorLink())
    InstallersPanel.espmMenu.append_link(Installer_Espm_JumpToMod())
    # Sub-Packages: Main Menu
    InstallersPanel.subsMenu.append_link(Installer_Subs_SelectAll())
    InstallersPanel.subsMenu.append_link(Installer_Subs_DeselectAll())
    InstallersPanel.subsMenu.append_link(Installer_Subs_ToggleSelection())
    InstallersPanel.subsMenu.append_link(SeparatorLink())
    InstallersPanel.subsMenu.append_link(Installer_Subs_ListSubPackages())
    # InstallersList: Global Links
    # File Menu
    file_menu = InstallersList.global_links[_('File')]
    file_menu.append_link(UIList_OpenStore())
    file_menu.append_link(Files_Unhide(_('Unhides hidden installers.')))
    file_menu.append_link(SeparatorLink())
    file_menu.append_link(Installers_CreateNewProject())
    file_menu.append_link(Installers_AddMarker())
    file_menu.append_link(SeparatorLink())
    file_menu.append_link(Misc_SaveData())
    # Edit Menu
    edit_menu = InstallersList.global_links[_('Edit')]
    edit_menu.append_link(Installers_MonitorExternalInstallation())
    edit_menu.append_link(Installers_CleanData())
    edit_menu.append_link(SeparatorLink())
    edit_menu.append_link(Installers_RefreshData())
    edit_menu.append_link(Installers_FullRefresh())
    edit_menu.append_link(SeparatorLink())
    edit_menu.append_link(Installers_AnnealAll())
    edit_menu.append_link(Installers_UninstallAllPackages())
    edit_menu.append_link(Installers_ApplyEmbeddedBCFs())
    edit_menu.append_link(SeparatorLink())
    edit_menu.append_link(Installers_ExportOrder())
    edit_menu.append_link(Installers_ImportOrder())
    # View Menu
    view_menu = InstallersList.global_links[_('View')]
    view_menu.append_link(SortByMenu(
        sort_options=[Installers_InstalledFirst(), Installers_SimpleFirst(),
                      Installers_ProjectsFirst()]))
    view_menu.append_link(ColumnsMenu())
    view_menu.append_link(SeparatorLink())
    view_menu.append_link(Installers_ListPackages())
    view_menu.append_link(Installers_WizardOverlay())
    # Settings Menu
    settings_menu = InstallersList.global_links[_('Settings')]
    settings_menu.append_link(Installers_Enabled())
    settings_menu.append_link(Installers_AvoidOnStart())
    settings_menu.append_link(SeparatorLink())
    settings_menu.append_link(Installers_AutoAnneal())
    settings_menu.append_link(Installers_AutoWizard())
    settings_menu.append_link(Installers_AutoRefreshProjects())
    settings_menu.append_link(Installers_IgnoreFomod())
    settings_menu.append_link(Installers_ValidateFomod())
    settings_menu.append_link(SeparatorLink())
    settings_menu.append_link(Installers_ShowActiveBSAConflicts())
    settings_menu.append_link(Installers_ShowInactiveConflicts())
    settings_menu.append_link(Installers_ShowLowerConflicts())
    settings_menu.append_link(SeparatorLink())
    settings_menu.append_link(Installers_BsaRedirection())
    settings_menu.append_link(Installers_RemoveEmptyDirs())
    settings_menu.append_link(SeparatorLink())
    settings_menu.append_link(Installers_SkipVanillaContent())
    settings_menu.append_link(Installers_GlobalSkips())
    settings_menu.append_link(Installers_GlobalRedirects())
    settings_menu.append_link(SeparatorLink())
    settings_menu.append_link(Misc_SettingsDialog())

#------------------------------------------------------------------------------
def InitINILinks():
    """Initialize INI Edits tab menus."""
    #--Column Links
    # Sorting and Columns
    INIList.column_links.append_link(SortByMenu(
        sort_options=[INI_ValidTweaksFirst()]))
    INIList.column_links.append_link(ColumnsMenu())
    INIList.column_links.append_link(SeparatorLink())
    if True: #--Files
        files_menu = MenuLink(_('Files..'))
        files_menu.links.append_link(UIList_OpenStore())
        INIList.column_links.append_link(files_menu)
    INIList.column_links.append_link(SeparatorLink())
    INIList.column_links.append_link(INI_AllowNewLines())
    INIList.column_links.append_link(INI_ListINIs())
    INIList.column_links.append_link(SeparatorLink())
    INIList.column_links.append_link(Misc_SaveData())
    INIList.column_links.append_link(Misc_SettingsDialog())
    #--Item menu
    if True: #--File
        file_menu = MenuLink(_('File..'))
        file_menu.links.append_link(UIList_OpenItems())
        file_menu.links.append_link(File_Duplicate())
        file_menu.links.append_link(UIList_Delete())
        INIList.context_links.append_link(file_menu)
    INIList.context_links.append_link(SeparatorLink())
    INIList.context_links.append_link(INI_Apply())
    INIList.context_links.append_link(INI_CreateNew())
    INIList.context_links.append_link(INI_ListErrors())
    INIList.context_links.append_link(SeparatorLink())
    INIList.context_links.append_link(File_JumpToSource())
    # INIList: Global Links
    # File Menu
    file_menu = INIList.global_links[_('File')]
    file_menu.append_link(UIList_OpenStore())
    file_menu.append_link(SeparatorLink())
    file_menu.append_link(Misc_SaveData())
    # View Menu
    view_menu = INIList.global_links[_('View')]
    view_menu.append_link(SortByMenu(sort_options=[INI_ValidTweaksFirst()]))
    view_menu.append_link(ColumnsMenu())
    view_menu.append_link(SeparatorLink())
    view_menu.append_link(INI_ListINIs())
    # Settings Menu
    settings_menu = INIList.global_links[_('Settings')]
    settings_menu.append_link(INI_AllowNewLines())
    settings_menu.append_link(SeparatorLink())
    settings_menu.append_link(Misc_SettingsDialog())

#------------------------------------------------------------------------------
def InitModLinks():
    """Initialize Mods tab menus."""
    #--ModList: Column Links
    # Sorting and Columns
    ModList.column_links.append_link(SortByMenu(
        sort_options=[Mods_MastersFirst(), Mods_ActiveFirst()]))
    ModList.column_links.append_link(ColumnsMenu())
    ModList.column_links.append_link(SeparatorLink())
    if True: #--Files
        files_menu = MenuLink(_('Files..'))
        files_menu.links.append_link(UIList_OpenStore())
        files_menu.links.append_link(
            Files_Unhide(_('Unhides hidden plugins.')))
        if bush.game.Esp.canBash:
            files_menu.links.append_link(SeparatorLink())
            files_menu.links.append_link(Mods_CreateBlank())
            files_menu.links.append_link(Mods_CreateBlankBashedPatch())
        ModList.column_links.append_link(files_menu)
    ModList.column_links.append_link(SeparatorLink())
    ModList.column_links.append_link(Mods_ActivePlugins())
    if True: #--Load Order
        lo_menu = MenuLink(_('Load Order..'))
        lo_menu.links.append_link(Mods_LOUndo())
        lo_menu.links.append_link(Mods_LORedo())
        lo_menu.links.append_link(SeparatorLink())
        lo_menu.links.append_link(Mods_LockActivePlugins())
        lo_menu.links.append_link(SeparatorLink())
        lo_menu.links.append_link(Mods_OpenLOFileMenu())
        ModList.column_links.append_link(lo_menu)
        ModList.column_links.append_link(SeparatorLink())
    ModList.column_links.append_link(Mods_LockLoadOrder())
    ModList.column_links.append_link(Mods_AutoGhost())
    if True: #--Plugins
        plugins_menu = MenuLink(_('Plugins..'))
        if bush.game.has_esl:
            plugins_menu.links.append_link(Mods_AutoESLFlagBP())
            plugins_menu.links.append_link(SeparatorLink())
        plugins_menu.links.append_link(Mods_ScanDirty())
        plugins_menu.links.append_link(Mods_IgnoreDirtyVanillaFiles())
        plugins_menu.links.append_link(SeparatorLink())
        plugins_menu.links.append_link(Mods_CrcRefresh())
        plugins_menu.links.append_link(Mods_ListMods())
        plugins_menu.links.append_link(Mods_OblivionEsmMenu())
        ModList.column_links.append_link(plugins_menu)
    if bush.game.allTags: #--Bash Tags
        bash_tags_menu = MenuLink(_('Bash Tags..'))
        bash_tags_menu.links.append_link(Mods_ListBashTags())
        bash_tags_menu.links.append_link(Mods_ExportBashTags())
        bash_tags_menu.links.append_link(Mods_ImportBashTags())
        bash_tags_menu.links.append_link(Mods_ClearManualBashTags())
        ModList.column_links.append_link(bash_tags_menu)
        ModList.column_links.append_link(SeparatorLink())
    ModList.column_links.append_link(Mods_PluginChecker())
    ModList.column_links.append_link(Mods_CleanDummyMasters())
    ModList.column_links.append_link(SeparatorLink())
    ModList.column_links.append_link(Misc_SaveData())
    ModList.column_links.append_link(Misc_SettingsDialog())
    #--ModList: Item Links
    if bass.inisettings['ShowDevTools'] and bush.game.Esp.canBash:
        dev_tools_menu = MenuLink('Dev Tools..')
        dev_tools_menu.links.append_link(Mod_FullLoad())
        dev_tools_menu.links.append_link(Mod_RecalcRecordCounts())
        dev_tools_menu.links.append_link(Mod_DumpSubrecords())
        dev_tools_menu.links.append_link(Mod_DumpRecordTypeNames())
        ModList.context_links.append_link(dev_tools_menu)
    if True: #--File
        file_menu = MenuLink(_('File..'))
        file_menu.links.append_link(Mod_Duplicate())
        file_menu.links.append_link(UIList_Hide())
        file_menu.links.append_link(Mod_Redate())
        file_menu.links.append_link(UIList_Delete())
        file_menu.links.append_link(SeparatorLink())
        file_menu.links.append_link(File_Backup())
        file_menu.links.append_link(File_RevertToBackup())
        file_menu.links.append_link(SeparatorLink())
        file_menu.links.append_link(Mod_Snapshot())
        file_menu.links.append_link(Mod_RevertToSnapshot())
        ModList.context_links.append_link(file_menu)
    ModList.context_links.append_link(SeparatorLink())
    ModList.context_links.append_link(Mod_Move())
    ModList.context_links.append_link(Mod_ShowReadme())
    ModList.context_links.append_link(File_JumpToSource())
    if True: #--Info
        info_menu = MenuLink(_('Info..'))
        if bush.game.allTags:
            info_menu.links.append_link(Mod_ListBashTags())
        info_menu.links.append_link(Mod_ListDependent())
        info_menu.links.append_link(File_ListMasters())
        if bush.game.Esp.canBash:
            info_menu.links.append_link(Mod_ListPatchConfig())
        info_menu.links.append_link(SeparatorLink())
        if bush.game.allTags:
            info_menu.links.append_link(Mod_CreateLOOTReport())
        info_menu.links.append_link(Mod_CopyModInfo())
        if bush.game.Esp.canBash:
            info_menu.links.append_link(Mod_Details())
        ModList.context_links.append_link(info_menu)
    if bush.game.Esp.canBash:
        ModList.context_links.append_link(SeparatorLink())
        ModList.context_links.append_link(Mod_CheckQualifications())
        ModList.context_links.append_link(Mod_RebuildPatch())
        ModList.context_links.append_link(SeparatorLink())
        ModList.context_links.append_link(Mod_FlipEsm())
        if MergeabilityCheck.ESL_CHECK in bush.game.mergeability_checks:
            ModList.context_links.append_link(Mod_FlipEsl())
        if MergeabilityCheck.OVERLAY_CHECK in bush.game.mergeability_checks:
            ModList.context_links.append_link(Mod_FlipOverlay())
        ModList.context_links.append_link(Mod_FlipMasters())
        ModList.context_links.append_link(Mod_CreateDummyMasters())
    ModList.context_links.append_link(SeparatorLink())
    if True: #--Plugin
        plugin_menu = MenuLink(_('Plugin..'))
        if True: #--Groups
            groupMenu = MenuLink(_('Groups..'))
            groupMenu.links.append_link(Mod_Groups())
            plugin_menu.links.append_link(groupMenu)
        if True: #--Ratings
            ratingMenu = MenuLink(_('Rating..'))
            ratingMenu.links.append_link(Mod_Ratings())
            plugin_menu.links.append_link(ratingMenu)
        plugin_menu.links.append_link(SeparatorLink())
        plugin_menu.links.append_link(Mod_AllowGhosting())
        plugin_menu.links.append_link(Mod_GhostUnghost())
        plugin_menu.links.append_link(Mod_OrderByName())
        if bush.game.Esp.canBash:
            plugin_menu.links.append_link(SeparatorLink())
            plugin_menu.links.append_link(Mod_CopyToMenu())
            if True: #--Cleaning
                cleanMenu = MenuLink(_('Cleaning..'))
                cleanMenu.links.append_link(Mod_SkipDirtyCheck())
                cleanMenu.links.append_link(SeparatorLink())
                cleanMenu.links.append_link(Mod_ScanDirty())
                cleanMenu.links.append_link(Mod_RemoveWorldOrphans())
                if _is_oblivion:
                    cleanMenu.links.append_link(Mod_FogFixer())
                plugin_menu.links.append_link(cleanMenu)
        ModList.context_links.append_link(plugin_menu)
    if bush.game.Esp.canBash: #--Advanced
        advanced_menu = MenuLink(_('Advanced..'))
        if True: #--Export
            exportMenu = MenuLink(_('Export..'))
            exportMenu.links.append_link(Mod_EditorIds_Export())
            exportMenu.links.append_link(Mod_Factions_Export())
            exportMenu.links.append_link(Mod_FactionRelations_Export())
            if bush.game.fsName in ('Enderal', 'Skyrim'):
                exportMenu.links.append_link(Mod_FullNames_Export())
                exportMenu.links.append_link(Mod_Prices_Export())
            elif bush.game.fsName in ('Fallout3', 'FalloutNV'):
                # TODO(inf) Commented out lines were only in FNV branch
                exportMenu.links.append_link(Mod_FullNames_Export())
                exportMenu.links.append_link(Mod_Prices_Export())
                # exportMenu.links.append_link(Mod_IngredientDetails_Export())
                # exportMenu.links.append_link(Mod_Scripts_Export())
                # exportMenu.links.append_link(Mod_SpellRecords_Export())
                exportMenu.links.append_link(Mod_Stats_Export())
            elif _is_oblivion:
                exportMenu.links.append_link(Mod_IngredientDetails_Export())
                exportMenu.links.append_link(Mod_FullNames_Export())
                exportMenu.links.append_link(Mod_ActorLevels_Export())
                exportMenu.links.append_link(Mod_Prices_Export())
                exportMenu.links.append_link(Mod_Scripts_Export())
                exportMenu.links.append_link(Mod_SigilStoneDetails_Export())
                exportMenu.links.append_link(Mod_SpellRecords_Export())
                exportMenu.links.append_link(Mod_Stats_Export())
            advanced_menu.links.append_link(exportMenu)
        if True: #--Import
            importMenu = MenuLink(_('Import..'))
            importMenu.links.append_link(Mod_EditorIds_Import())
            importMenu.links.append_link(Mod_Factions_Import())
            importMenu.links.append_link(Mod_FactionRelations_Import())
            if bush.game.fsName in ('Enderal', 'Skyrim'):
                importMenu.links.append_link(Mod_FullNames_Import())
                importMenu.links.append_link(Mod_Prices_Import())
            elif bush.game.fsName in ('Fallout3', 'FalloutNV'):
                # TODO(inf) Commented out lines were only in FNV branch
                importMenu.links.append_link(Mod_FullNames_Import())
                importMenu.links.append_link(Mod_Prices_Import())
                # importMenu.links.append_link(Mod_IngredientDetails_Import())
                # importMenu.links.append_link(Mod_Scripts_Import())
                importMenu.links.append_link(Mod_Stats_Import())
                # importMenu.links.append_link(SeparatorLink())
                # importMenu.links.append_link(Mod_Face_Import())
                # importMenu.links.append_link(Mod_Fids_Replace())
            elif _is_oblivion:
                importMenu.links.append_link(Mod_IngredientDetails_Import())
                importMenu.links.append_link(Mod_FullNames_Import())
                importMenu.links.append_link(Mod_ActorLevels_Import())
                importMenu.links.append_link(Mod_Prices_Import())
                importMenu.links.append_link(Mod_Scripts_Import())
                importMenu.links.append_link(Mod_SigilStoneDetails_Import())
                importMenu.links.append_link(Mod_SpellRecords_Import())
                importMenu.links.append_link(Mod_Stats_Import())
                importMenu.links.append_link(SeparatorLink())
                importMenu.links.append_link(Mod_Face_Import())
                importMenu.links.append_link(Mod_Fids_Replace())
        advanced_menu.links.append_link(importMenu)
        if _is_oblivion:
            advanced_menu.links.append_link(SeparatorLink())
            advanced_menu.links.append_link(Mod_DecompileAll())
            advanced_menu.links.append_link(Mod_SetVersion())
        ModList.context_links.append_link(advanced_menu)
    # ModList: Global Links
    # File Menu
    file_menu = ModList.global_links[_('File')]
    file_menu.append_link(UIList_OpenStore())
    file_menu.append_link(Files_Unhide(_('Unhides hidden plugins.')))
    if bush.game.Esp.canBash:
        file_menu.append_link(SeparatorLink())
        file_menu.append_link(Mods_CreateBlank())
        file_menu.append_link(Mods_CreateBlankBashedPatch())
    file_menu.append_link(SeparatorLink())
    file_menu.append_link(Misc_SaveData())
    # Edit Menu
    edit_menu = ModList.global_links[_('Edit')]
    edit_menu.append_link(Mods_ActivePlugins())
    lo_submenu = MenuLink(_('Load Order..'))
    lo_submenu.links.append_link(Mods_LOUndo())
    lo_submenu.links.append_link(Mods_LORedo())
    lo_submenu.links.append_link(SeparatorLink())
    lo_submenu.links.append_link(Mods_OpenLOFileMenu())
    edit_menu.append_link(lo_submenu)
    edit_menu.append_link(Mods_OblivionEsmMenu())
    if bush.game.allTags:
        edit_menu.append_link(SeparatorLink())
        edit_menu.append_link(Mods_ExportBashTags())
        edit_menu.append_link(Mods_ImportBashTags())
        edit_menu.append_link(Mods_ClearManualBashTags())
    edit_menu.append_link(SeparatorLink())
    edit_menu.append_link(Mods_CleanDummyMasters())
    edit_menu.append_link(Mods_CrcRefresh())
    # View Menu
    view_menu = ModList.global_links[_('View')]
    view_menu.append_link(SortByMenu(
        sort_options=[Mods_MastersFirst(), Mods_ActiveFirst()]))
    view_menu.append_link(ColumnsMenu())
    view_menu.append_link(SeparatorLink())
    view_menu.append_link(Mods_ListMods())
    if bush.game.allTags:
        view_menu.append_link(Mods_ListBashTags())
    view_menu.append_link(Mods_PluginChecker())
    # Settings Menu
    settings_menu = ModList.global_links[_('Settings')]
    settings_menu.append_link(Mods_AutoGhost())
    if bush.game.has_esl:
        settings_menu.append_link(Mods_AutoESLFlagBP())
    settings_menu.append_link(Mods_LockLoadOrder())
    settings_menu.append_link(Mods_LockActivePlugins())
    settings_menu.append_link(Mods_ScanDirty())
    settings_menu.append_link(Mods_IgnoreDirtyVanillaFiles())
    settings_menu.append_link(SeparatorLink())
    settings_menu.append_link(Misc_SettingsDialog())

#------------------------------------------------------------------------------
def InitSaveLinks():
    """Initialize save tab menus."""
    #--SaveList: Column Links
    # Sorting and Columns
    SaveList.column_links.append_link(SortByMenu())
    SaveList.column_links.append_link(ColumnsMenu())
    SaveList.column_links.append_link(SeparatorLink())
    if True: #--Files
        files_menu = MenuLink(_('Files..'))
        files_menu.links.append_link(UIList_OpenStore())
        files_menu.links.append_link(Files_Unhide(_('Unhides hidden saves.')))
    SaveList.column_links.append_link(files_menu)
    SaveList.column_links.append_link(SeparatorLink())
    if True: #--Profile
        subDirMenu = MenuLink(_('Profile..'))
        subDirMenu.links.append_link(Saves_Profiles())
        SaveList.column_links.append_link(subDirMenu)
    SaveList.column_links.append_link(Mods_OblivionEsmMenu(set_profile=True))
    SaveList.column_links.append_link(SeparatorLink())
    SaveList.column_links.append_link(Misc_SaveData())
    SaveList.column_links.append_link(Misc_SettingsDialog())
    #--SaveList: Item Links
    if True: #--File
        file_menu = MenuLink(_('File..'))
        file_menu.links.append_link(UIList_Rename())
        file_menu.links.append_link(File_Duplicate())
        file_menu.links.append_link(UIList_Hide())
        file_menu.links.append_link(UIList_Delete())
        file_menu.links.append_link(SeparatorLink())
        file_menu.links.append_link(File_Backup())
        file_menu.links.append_link(File_RevertToBackup())
        SaveList.context_links.append_link(file_menu)
    if True: #--Move To
        moveMenu = MenuLink(_('Move To..'))
        moveMenu.links.append_link(Save_Move())
        SaveList.context_links.append_link(moveMenu)
    if True: #--Copy To
        copyMenu = MenuLink(_('Copy To..'))
        copyMenu.links.append_link(Save_Move(copyMode=True))
        SaveList.context_links.append_link(copyMenu)
    SaveList.context_links.append_link(SeparatorLink())
    SaveList.context_links.append_link(Save_ActivateMasters())
    SaveList.context_links.append_link(Save_ReorderMasters())
    SaveList.context_links.append_link(File_ListMasters())
    SaveList.context_links.append_link(Save_DiffMasters())
    SaveList.context_links.append_link(SeparatorLink())
    SaveList.context_links.append_link(Save_ExportScreenshot())
    SaveList.context_links.append_link(Save_Renumber())
    if True: #--Info
        info_menu = MenuLink(_('Info..'))
        if bush.game.Ess.canEditMore:
            info_menu.links.append_link(Save_Stats())
        info_menu.links.append_link(Save_StatObse())
        info_menu.links.append_link(Save_StatPluggy())
        SaveList.context_links.append_link(info_menu)
    if bush.game.Ess.canEditMore: #--Edit & Repair
        edit_menu = MenuLink(_('Edit..'))
        edit_menu.links.append_link(Save_EditCreated(b'ALCH'))
        edit_menu.links.append_link(Save_ReweighPotions())
        edit_menu.links.append_link(SeparatorLink())
        edit_menu.links.append_link(Save_EditCreated(b'ENCH'))
        edit_menu.links.append_link(Save_EditCreatedEnchantmentCosts())
        edit_menu.links.append_link(SeparatorLink())
        edit_menu.links.append_link(Save_EditCreated(b'SPEL'))
        edit_menu.links.append_link(Save_EditPCSpells())
        edit_menu.links.append_link(SeparatorLink())
        edit_menu.links.append_link(Save_RenamePlayer())
        edit_menu.links.append_link(Save_ImportFace())
        edit_menu.links.append_link(Save_UpdateNPCLevels())
        repair_menu = MenuLink(_('Repair..'))
        repair_menu.links.append_link(Save_Unbloat())
        repair_menu.links.append_link(Save_RepairAbomb())
        repair_menu.links.append_link(Save_RepairHair())
        SaveList.context_links.append_link(SeparatorLink())
        SaveList.context_links.append_link(edit_menu)
        SaveList.context_links.append_link(repair_menu)
    # SaveList: Global Links
    # File Menu
    file_menu = SaveList.global_links[_('File')]
    file_menu.append_link(UIList_OpenStore())
    file_menu.append_link(Files_Unhide(_('Unhides hidden saves.')))
    file_menu.append_link(SeparatorLink())
    file_menu.append_link(Misc_SaveData())
    # Edit Menu
    edit_menu = SaveList.global_links[_('Edit')]
    profile_menu = MenuLink(_('Profile..'))
    profile_menu.append(Saves_Profiles())
    edit_menu.append_link(profile_menu)
    edit_menu.append_link(Mods_OblivionEsmMenu(set_profile=True))
    # View Menu
    view_menu = SaveList.global_links[_('View')]
    view_menu.append_link(SortByMenu())
    view_menu.append_link(ColumnsMenu())
    # Settings Menu
    SaveList.global_links[_('Settings')].append_link(Misc_SettingsDialog())

#------------------------------------------------------------------------------
def InitBSALinks():
    """Initialize BSA tab menus."""
    #--BSAList: Column Links
    # Sorting and Columns
    BSAList.column_links.append_link(SortByMenu())
    BSAList.column_links.append_link(ColumnsMenu())
    BSAList.column_links.append_link(SeparatorLink())
    if True: #--Files
        files_menu = MenuLink(_('Files..'))
        files_menu.links.append_link(UIList_OpenStore())
        files_menu.links.append_link(Files_Unhide(_('Unhides hidden BSAs.')))
    BSAList.column_links.append_link(files_menu)
    BSAList.column_links.append_link(SeparatorLink())
    BSAList.column_links.append_link(Misc_SaveData())
    BSAList.column_links.append_link(Misc_SettingsDialog())
    #--BSAList: Item Links
    if True: #--File
        file_menu = MenuLink(_('File..'))
        file_menu.links.append_link(File_Duplicate())
        file_menu.links.append_link(UIList_Hide())
        file_menu.links.append_link(File_Redate())
        file_menu.links.append_link(UIList_Delete())
        file_menu.links.append_link(SeparatorLink())
        file_menu.links.append_link(File_Backup())
        file_menu.links.append_link(File_RevertToBackup())
    BSAList.context_links.append_link(file_menu)
    BSAList.context_links.append_link(BSA_ExtractToProject())
    BSAList.context_links.append_link(BSA_ListContents())
    # BSAList: Global Links
    # File Menu
    file_menu = BSAList.global_links[_('File')]
    file_menu.append_link(UIList_OpenStore())
    file_menu.append_link(Files_Unhide(_('Unhides hidden BSAs.')))
    file_menu.append_link(SeparatorLink())
    file_menu.append_link(Misc_SaveData())
    # View Menu
    view_menu = BSAList.global_links[_('View')]
    view_menu.append_link(SortByMenu())
    view_menu.append_link(ColumnsMenu())
    # Settings Menu
    BSAList.global_links[_('Settings')].append_link(Misc_SettingsDialog())

#------------------------------------------------------------------------------
def InitScreenLinks():
    """Initialize screens tab menus."""
    #--ScreensList: Column Links
    # Sorting and Columns
    ScreensList.column_links.append_link(SortByMenu())
    ScreensList.column_links.append_link(ColumnsMenu())
    ScreensList.column_links.append_link(SeparatorLink())
    if True:
        files_menu = MenuLink(_('Files..'))
        files_menu.links.append_link(UIList_OpenStore())
        ScreensList.column_links.append_link(files_menu)
    ScreensList.column_links.append_link(SeparatorLink())
    ScreensList.column_links.append_link(Screens_NextScreenShot())
    if True: #--JPG Quality
        qualityMenu = MenuLink(_('JPG Quality..'))
        for i in range(100, 80, -5):
            qualityMenu.links.append_link(Screens_JpgQuality(i))
        qualityMenu.links.append_link(Screens_JpgQualityCustom())
        ScreensList.column_links.append_link(qualityMenu)
    ScreensList.column_links.append_link(SeparatorLink())
    ScreensList.column_links.append_link(Misc_SaveData())
    ScreensList.column_links.append_link(Misc_SettingsDialog())
    #--ScreensList: Item Links
    if True: #--File
        file_menu = MenuLink(_('File..'))
        file_menu.links.append_link(UIList_OpenItems())
        file_menu.links.append_link(UIList_Rename())
        file_menu.links.append_link(File_Duplicate())
        file_menu.links.append_link(UIList_Delete())
        ScreensList.context_links.append_link(file_menu)
    if True: #--Convert
        convertMenu = MenuLink(_('Convert..'))
        convertMenu.links.append_link(Screen_ConvertTo('.jpg'))
        convertMenu.links.append_link(Screen_ConvertTo('.png'))
        convertMenu.links.append_link(Screen_ConvertTo('.bmp'))
        convertMenu.links.append_link(Screen_ConvertTo('.tif'))
        ScreensList.context_links.append_link(convertMenu)
    # ScreensList: Global Links
    # File Menu
    file_menu = ScreensList.global_links[_('File')]
    file_menu.append_link(UIList_OpenStore())
    file_menu.append_link(SeparatorLink())
    file_menu.append_link(Misc_SaveData())
    # View Menu
    view_menu = ScreensList.global_links[_('View')]
    view_menu.append_link(SortByMenu())
    view_menu.append_link(ColumnsMenu())
    # Settings Menu
    settings_menu = ScreensList.global_links[_('Settings')]
    settings_menu.append_link(Screens_NextScreenShot())
    jpg_quality_menu = MenuLink(_('JPG Quality..'))
    for i in range(100, 80, -5):
        jpg_quality_menu.links.append_link(Screens_JpgQuality(i))
    jpg_quality_menu.links.append_link(Screens_JpgQualityCustom())
    settings_menu.append_link(qualityMenu)
    settings_menu.append_link(SeparatorLink())
    ScreensList.global_links[_('Settings')].append_link(Misc_SettingsDialog())

#------------------------------------------------------------------------------
def InitLinks():
    """Call other link initializers."""
    InitMasterLinks()
    InitInstallerLinks()
    InitINILinks()
    InitModLinks()
    InitSaveLinks()
    InitScreenLinks()
    # InitBSALinks()
