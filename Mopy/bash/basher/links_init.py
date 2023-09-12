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

"""Links initialization functions. Each panel's UIList has main and items Links
attributes which are populated here. Therefore the layout of the menus is
also defined in these functions."""

from . import BashStatusBar, BSAList, INIList, InstallersList, \
    InstallersPanel, MasterList, ModList, SaveList, ScreensList
# modules below define the __all__ directive
from .app_buttons import *
from .bsa_links import *
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
from ..balt import MenuLink, SeparatorLink, UIList_Delete, UIList_Hide, \
    UIList_OpenItems, UIList_OpenStore, UIList_Rename, images
from ..env import init_app_links
from ..game.patch_game import PatchGame
from ..gui import ImageWrapper

_is_oblivion = bush.game.fsName == 'Oblivion'

#------------------------------------------------------------------------------
def InitStatusBar():
    """Initialize status bar links."""
    def _png_list(template):
        return [ImageWrapper(bass.dirs[u'images'].join(template % i)) for i in
                (16, 24, 32)]
    def _svg_list(svg_fname):
        return [ImageWrapper(bass.dirs['images'].join(svg_fname), iconSize=i)
                for i in (16, 24, 32)]
    def _init_tool_buttons(): # tooldirs must have been initialized
        return (((bass.tooldirs[u'OblivionBookCreatorPath'],
                  bass.inisettings[u'OblivionBookCreatorJavaArg']),
                 _png_list('tools/oblivionbookcreator%s.png'),
                 _(u'Launch Oblivion Book Creator'),
                 {'uid': u'OblivionBookCreator'}),
                ((bass.tooldirs[u'Tes4GeckoPath'],
                  bass.inisettings[u'Tes4GeckoJavaArg']),
                 _png_list('tools/tes4gecko%s.png'),
                 _(u'Launch Tes4Gecko'), {'uid': u'Tes4Gecko'}),
                ((bass.tooldirs[u'Tes5GeckoPath']),
                _png_list('tools/tesvgecko%s.png'),
                _(u'Launch TesVGecko'), {'uid': u'TesVGecko'}),
        )
    #--Bash Status/LinkBar
    BashStatusBar.obseButton = obseButton = Obse_Button(uid=u'OBSE')
    all_links = [
        obseButton,
        AutoQuit_Button(uid='AutoQuit'),
        Game_Button(
            bass.dirs['app'].join(bush.game.launch_exe),
            bass.dirs['app'].join(bush.game.version_detect_file),
            _png_list(f'games/{bush.game.game_icon}'),
            _('Launch %(game_name)s') % {'game_name': bush.game.displayName},
            _('Launch %(game_name)s %(app_version)s')),
    ]
    if bush.game.Ck.ck_abbrev:
        all_links.append(TESCS_Button( # Construction Set / Creation Kit
            bass.dirs['app'].join(bush.game.Ck.exe),
            _png_list(f'tools/{bush.game.Ck.image_name}'),
            _('Launch %(ck_name)s') % {'ck_name': bush.game.Ck.long_name},
            _('Launch %(ck_name)s %(app_version)s'),
            bush.game.Ck.se_args))
    # OBMM
    all_links.append(app_button_factory(
        bass.dirs['app'].join('OblivionModManager.exe'),
        _png_list('tools/obmm%s.png'), _('Launch OBMM'),
        uid='OBMM'))
    # Just an _App_Button whose path is in bass.tooldirs
    Tooldir_Button = lambda *args: app_button_factory(bass.tooldirs[args[0]],
                                                      *args[1:])
    from .constants import toolbar_buttons
    for tb in toolbar_buttons:
        all_links.append(Tooldir_Button(*tb))
    for tb2 in _init_tool_buttons():
        all_links.append(app_button_factory(*tb2[:-1], **tb2[-1]))
    all_links.append( #Tes4View
        App_xEdit((bass.tooldirs['Tes4ViewPath'], '-TES4 -view'),
            _png_list('tools/tes4view%s.png'), _('Launch TES4View'),
            uid='TES4View'))
    for game_class in PatchGame.supported_games(): # TODO(ut): don't save those for all games!
        xe_name = game_class.Xe.full_name
        all_links.append(App_xEdit((bass.tooldirs[f'{xe_name}Path'],
             '-%s -edit' % xe_name[:-4]), # chop off edit
            _png_list('tools/tes4edit%s.png'), _(u'Launch %s') % xe_name,
            uid=xe_name))
    all_links.append(  #TesVGecko
        app_button_factory((bass.tooldirs[u'Tes5GeckoPath']),
                           _png_list('tools/tesvgecko%s.png'),
                           _(u"Launch TesVGecko"), uid=u'TesVGecko'))
    all_links.append(  #Tes4Trans
        App_xEdit((bass.tooldirs['Tes4TransPath'], '-TES4 -translate'),
            _png_list('tools/tes4trans%s.png'), _('Launch TES4Trans'),
            uid='TES4Trans'))
    all_links.append(  #Tes4LODGen
        App_xEdit((bass.tooldirs['Tes4LodGenPath'], '-TES4 -lodgen'),
            _png_list('tools/tes4lodgen%s.png'), _('Launch Tes4LODGen'),
            uid='TES4LODGen'))
    if bush.game.boss_game_name:
        all_links.append( #BOSS
            App_BOSS(bass.tooldirs['boss'], _png_list('tools/boss%s.png'),
                _('Launch BOSS'), uid='BOSS'))
    if bush.game.loot_game_name:
        all_links.append( #LOOT
            App_LOOT(bass.tooldirs['LOOT'], _svg_list('tools/loot.svg'),
                _('Launch LOOT'), uid='LOOT'))
    if bass.inisettings[u'ShowModelingToolLaunchers']:
        from .constants import modeling_tools_buttons
        for mb in modeling_tools_buttons:
            all_links.append(Tooldir_Button(*mb))
        all_links.append( #Softimage Mod Tool
            app_button_factory((bass.tooldirs[u'SoftimageModTool'], u'-mod'),
                               _png_list('tools/softimagemodtool%s.png'),
                               _(u"Launch Softimage Mod Tool"),
                               uid=u'SoftimageModTool'))
    if bass.inisettings[u'ShowModelingToolLaunchers'] \
            or bass.inisettings[u'ShowTextureToolLaunchers']:
        all_links.append( #Nifskope
            Tooldir_Button(u'NifskopePath', _png_list('tools/nifskope%s.png'),
                _(u'Launch Nifskope')))
    if bass.inisettings[u'ShowTextureToolLaunchers']:
        from .constants import texture_tool_buttons
        for tt in texture_tool_buttons:
            all_links.append(Tooldir_Button(*tt))
    if bass.inisettings[u'ShowAudioToolLaunchers']:
        from .constants import audio_tools
        for at in audio_tools:
            all_links.append(Tooldir_Button(*at))
    from .constants import misc_tools
    for mt in misc_tools: all_links.append(Tooldir_Button(*mt))
    #--Custom Apps
    dirApps = bass.dirs[u'mopy'].join(u'Apps')
    badIcons = [images['error_cross.16'].get_bitmap()] * 3
    def iconList(fileName):
        return [ImageWrapper(fileName, ImageWrapper.img_types['.ico'], x) for x
                in (16, 24, 32)]
    for pth, icon, shortcut_descr in init_app_links(dirApps, badIcons, iconList):
            all_links.append(
                app_button_factory((pth,()), icon, shortcut_descr, canHide=False))
    #--Final couple
    all_links.append(App_DocBrowser(uid='DocBrowser'))
    all_links.append(App_PluginChecker(uid='ModChecker'))
    all_links.append(App_Settings(uid='Settings', canHide=False))
    all_links.append(App_Help(uid='Help', canHide=False))
    if bass.inisettings['ShowDevTools']:
        all_links.append(App_Restart(uid='Restart'))
    BashStatusBar.all_sb_links = {li.uid: li for li in all_links}

#------------------------------------------------------------------------------
def InitMasterLinks():
    """Initialize master list menus."""
    #--MasterList: Column Links
    MasterList.column_links.append(SortByMenu(
        sort_options=[Mods_MastersFirst(), Mods_ActiveFirst()]))
    MasterList.column_links.append(ColumnsMenu())
    MasterList.column_links.append(SeparatorLink())
    MasterList.column_links.append(Master_AllowEdit())
    MasterList.column_links.append(Master_ClearRenames())
    #--MasterList: Item Links
    MasterList.context_links.append(Master_ChangeTo())
    MasterList.context_links.append(Master_Disable())
    MasterList.context_links.append(SeparatorLink())
    MasterList.context_links.append(Master_JumpTo())

#------------------------------------------------------------------------------
def InitInstallerLinks():
    """Initialize Installers tab menus."""
    #--Column links
    # Sorting and Columns
    InstallersList.column_links.append(SortByMenu(
        sort_options=[Installers_InstalledFirst(), Installers_SimpleFirst(),
                      Installers_ProjectsFirst()]))
    InstallersList.column_links.append(ColumnsMenu())
    InstallersList.column_links.append(SeparatorLink())
    if True: #--Files
        files_menu = MenuLink(_('Files..'))
        files_menu.links.append(UIList_OpenStore())
        files_menu.links.append(Files_Unhide(_('Unhides hidden installers.')))
        files_menu.links.append(SeparatorLink())
        files_menu.links.append(Installers_CreateNewProject())
        files_menu.links.append(Installers_AddMarker())
        InstallersList.column_links.append(files_menu)
        InstallersList.column_links.append(SeparatorLink())
    if True: #--Data
        data_menu = MenuLink(_('Data..'))
        data_menu.links.append(Installers_MonitorExternalInstallation())
        data_menu.links.append(Installers_CleanData())
        data_menu.links.append(SeparatorLink())
        data_menu.links.append(Installers_RefreshData())
        data_menu.links.append(Installers_FullRefresh())
        InstallersList.column_links.append(data_menu)
    if True: #--Packages
        packages_menu = MenuLink(_('Packages..'))
        packages_menu.links.append(Installers_AnnealAll())
        packages_menu.links.append(Installers_UninstallAllPackages())
        packages_menu.links.append(Installers_ApplyEmbeddedBCFs())
        packages_menu.links.append(SeparatorLink())
        packages_menu.links.append(Installers_ListPackages())
        packages_menu.links.append(Installers_WizardOverlay())
        packages_menu.links.append(SeparatorLink())
        packages_menu.links.append(Installers_ExportOrder())
        packages_menu.links.append(Installers_ImportOrder())
        InstallersList.column_links.append(packages_menu)
        InstallersList.column_links.append(SeparatorLink())
    InstallersList.column_links.append(Installers_Enabled())
    InstallersList.column_links.append(Installers_AvoidOnStart())
    InstallersList.column_links.append(Installers_ValidateFomod())
    if True: #--Installation Settings
        inst_settings_menu = MenuLink(_('Installation Settings..'))
        inst_settings_menu.links.append(Installers_AutoAnneal())
        inst_settings_menu.links.append(Installers_AutoWizard())
        inst_settings_menu.links.append(Installers_AutoRefreshProjects())
        inst_settings_menu.links.append(Installers_IgnoreFomod())
        inst_settings_menu.links.append(SeparatorLink())
        inst_settings_menu.links.append(Installers_BsaRedirection())
        inst_settings_menu.links.append(Installers_RemoveEmptyDirs())
        InstallersList.column_links.append(inst_settings_menu)
    if True: #--Conflict Settings
        cflt_settings_menu = MenuLink(_('Conflict Settings..'))
        cflt_settings_menu.links.append(Installers_ShowInactiveConflicts())
        cflt_settings_menu.links.append(Installers_ShowLowerConflicts())
        cflt_settings_menu.links.append(Installers_ShowActiveBSAConflicts())
        InstallersList.column_links.append(cflt_settings_menu)
    InstallersList.column_links.append(SeparatorLink())
    InstallersList.column_links.append(Installers_SkipVanillaContent())
    InstallersList.column_links.append(Installers_GlobalSkips())
    InstallersList.column_links.append(Installers_GlobalRedirects())
    InstallersList.column_links.append(SeparatorLink())
    InstallersList.column_links.append(Misc_SaveData())
    InstallersList.column_links.append(Misc_SettingsDialog())
    #--Item links
    if True: #--File
        file_menu = MenuLink(_('File..'))
        file_menu.links.append(Installer_Open())
        file_menu.links.append(UIList_Rename())
        file_menu.links.append(Installer_Duplicate())
        file_menu.links.append(Installer_Hide())
        file_menu.links.append(UIList_Delete())
        InstallersList.context_links.append(file_menu)
    if True: #--Open At...
        openAtMenu = MenuLink(_('Open At..'), oneDatumOnly=True)
        openAtMenu.links.append(Installer_OpenSearch())
        openAtMenu.links.append(Installer_OpenNexus())
        openAtMenu.links.append(Installer_OpenTESA())
        InstallersList.context_links.append(openAtMenu)
    #--Install, uninstall, etc.
    InstallersList.context_links.append(SeparatorLink())
    InstallersList.context_links.append(Installer_OpenReadme())
    InstallersList.context_links.append(Installer_Anneal())
    InstallersList.context_links.append(
        Installer_Refresh(calculate_projects_crc=False))
    InstallersList.context_links.append(Installer_Move())
    InstallersList.context_links.append(Installer_SyncFromData())
    InstallersList.context_links.append(SeparatorLink())
    InstallersList.context_links.append(Installer_InstallSmart())
    if True: #--Advanced Installation
        installMenu = MenuLink(_('Advanced Installation..'))
        installMenu.links.append(Installer_Install())
        installMenu.links.append(Installer_Install('MISSING'))
        installMenu.links.append(Installer_Install('LAST'))
        installMenu.links.append(SeparatorLink())
        if True: #--FOMOD Installer
            fomod_menu = MenuLink(_('FOMOD Installer..'))
            fomod_menu.links.append(Installer_RunFomod())
            fomod_menu.links.append(Installer_CaptureFomodOutput())
            fomod_menu.links.append(SeparatorLink())
            fomod_menu.links.append(Installer_EditFomod())
            installMenu.links.append(fomod_menu)
        if True: #--Wizard Installer
            wizardMenu = MenuLink(_('Wizard Installer..'))
            wizardMenu.links.append(Installer_Wizard(auto_wizard=False))
            wizardMenu.links.append(Installer_Wizard(auto_wizard=True))
            wizardMenu.links.append(SeparatorLink())
            wizardMenu.links.append(Installer_EditWizard())
            installMenu.links.append(wizardMenu)
        InstallersList.context_links.append(installMenu)
    InstallersList.context_links.append(Installer_Uninstall())
    InstallersList.context_links.append(SeparatorLink())
    if True: #--Package - always visible
        package_menu = MenuLink(_('Package..'))
        package_menu.links.append(Installer_Refresh())
        if bush.game.has_achlist:
            package_menu.links.append(Installer_ExportAchlist())
        package_menu.links.append(Installer_ListStructure())
        package_menu.links.append(Installer_CopyConflicts())
        package_menu.links.append(SeparatorLink())
        package_menu.links.append(Installer_HasExtraData())
        package_menu.links.append(Installer_OverrideSkips())
        package_menu.links.append(Installer_SkipVoices())
        InstallersList.context_links.append(package_menu)
    if True: #--Archive - only visible for archives
        archive_menu = Installer_ArchiveMenu()
        archive_menu.links.append(InstallerArchive_Unpack())
        if True: #--BAIN Conversions
            conversions_menu = MenuLink(_('BAIN Conversions..'))
            conversions_menu.links.append(InstallerConverter_Create())
            conversions_menu.links.append(InstallerConverter_ConvertMenu())
            archive_menu.append(conversions_menu)
        InstallersList.context_links.append(archive_menu)
    if True: #--Project - only visible for projects
        project_menu = Installer_ProjectMenu()
        project_menu.links.append(InstallerProject_Pack())
        project_menu.links.append(InstallerProject_ReleasePack())
        project_menu.links.append(Installer_SkipRefresh())
        project_menu.links.append(InstallerProject_OmodConfig())
        InstallersList.context_links.append(project_menu)
    # Plugin Filter: Main Menu
    InstallersPanel.espmMenu.append(Installer_Espm_SelectAll())
    InstallersPanel.espmMenu.append(Installer_Espm_DeselectAll())
    InstallersPanel.espmMenu.append(Installer_Espm_List())
    InstallersPanel.espmMenu.append(SeparatorLink())
    # Plugin Filter: Item Menu
    InstallersPanel.espmMenu.append(Installer_Espm_Rename())
    InstallersPanel.espmMenu.append(Installer_Espm_Reset())
    InstallersPanel.espmMenu.append(Installer_Espm_ResetAll())
    InstallersPanel.espmMenu.append(SeparatorLink())
    InstallersPanel.espmMenu.append(Installer_Espm_JumpToMod())
    # Sub-Packages: Main Menu
    InstallersPanel.subsMenu.append(Installer_Subs_SelectAll())
    InstallersPanel.subsMenu.append(Installer_Subs_DeselectAll())
    InstallersPanel.subsMenu.append(Installer_Subs_ToggleSelection())
    InstallersPanel.subsMenu.append(SeparatorLink())
    InstallersPanel.subsMenu.append(Installer_Subs_ListSubPackages())
    # InstallersList: Global Links
    # File Menu
    file_menu = InstallersList.global_links[_('File')]
    file_menu.append(UIList_OpenStore())
    file_menu.append(Files_Unhide(_('Unhides hidden installers.')))
    file_menu.append(SeparatorLink())
    file_menu.append(Installers_CreateNewProject())
    file_menu.append(Installers_AddMarker())
    file_menu.append(SeparatorLink())
    file_menu.append(Misc_SaveData())
    # Edit Menu
    edit_menu = InstallersList.global_links[_('Edit')]
    edit_menu.append(Installers_MonitorExternalInstallation())
    edit_menu.append(Installers_CleanData())
    edit_menu.append(SeparatorLink())
    edit_menu.append(Installers_RefreshData())
    edit_menu.append(Installers_FullRefresh())
    edit_menu.append(SeparatorLink())
    edit_menu.append(Installers_AnnealAll())
    edit_menu.append(Installers_UninstallAllPackages())
    edit_menu.append(Installers_ApplyEmbeddedBCFs())
    edit_menu.append(SeparatorLink())
    edit_menu.append(Installers_ExportOrder())
    edit_menu.append(Installers_ImportOrder())
    # View Menu
    view_menu = InstallersList.global_links[_('View')]
    view_menu.append(SortByMenu(
        sort_options=[Installers_InstalledFirst(), Installers_SimpleFirst(),
                      Installers_ProjectsFirst()]))
    view_menu.append(ColumnsMenu())
    view_menu.append(SeparatorLink())
    view_menu.append(Installers_ListPackages())
    view_menu.append(Installers_WizardOverlay())
    # Settings Menu
    settings_menu = InstallersList.global_links[_('Settings')]
    settings_menu.append(Installers_Enabled())
    settings_menu.append(Installers_AvoidOnStart())
    settings_menu.append(SeparatorLink())
    settings_menu.append(Installers_AutoAnneal())
    settings_menu.append(Installers_AutoWizard())
    settings_menu.append(Installers_AutoRefreshProjects())
    settings_menu.append(Installers_IgnoreFomod())
    settings_menu.append(Installers_ValidateFomod())
    settings_menu.append(SeparatorLink())
    settings_menu.append(Installers_ShowActiveBSAConflicts())
    settings_menu.append(Installers_ShowInactiveConflicts())
    settings_menu.append(Installers_ShowLowerConflicts())
    settings_menu.append(SeparatorLink())
    settings_menu.append(Installers_BsaRedirection())
    settings_menu.append(Installers_RemoveEmptyDirs())
    settings_menu.append(SeparatorLink())
    settings_menu.append(Installers_SkipVanillaContent())
    settings_menu.append(Installers_GlobalSkips())
    settings_menu.append(Installers_GlobalRedirects())
    settings_menu.append(SeparatorLink())
    settings_menu.append(Misc_SettingsDialog())

#------------------------------------------------------------------------------
def InitINILinks():
    """Initialize INI Edits tab menus."""
    #--Column Links
    # Sorting and Columns
    INIList.column_links.append(SortByMenu(
        sort_options=[INI_ValidTweaksFirst()]))
    INIList.column_links.append(ColumnsMenu())
    INIList.column_links.append(SeparatorLink())
    if True: #--Files
        files_menu = MenuLink(_('Files..'))
        files_menu.links.append(UIList_OpenStore())
        INIList.column_links.append(files_menu)
    INIList.column_links.append(SeparatorLink())
    INIList.column_links.append(INI_AllowNewLines())
    INIList.column_links.append(INI_ListINIs())
    INIList.column_links.append(SeparatorLink())
    INIList.column_links.append(Misc_SaveData())
    INIList.column_links.append(Misc_SettingsDialog())
    #--Item menu
    if True: #--File
        file_menu = MenuLink(_('File..'))
        file_menu.links.append(INI_Open())
        file_menu.links.append(File_Duplicate())
        file_menu.links.append(UIList_Delete())
        INIList.context_links.append(file_menu)
    INIList.context_links.append(SeparatorLink())
    INIList.context_links.append(INI_Apply())
    INIList.context_links.append(INI_CreateNew())
    INIList.context_links.append(INI_ListErrors())
    INIList.context_links.append(SeparatorLink())
    INIList.context_links.append(File_JumpToSource())
    # INIList: Global Links
    # File Menu
    file_menu = INIList.global_links[_('File')]
    file_menu.append(UIList_OpenStore())
    file_menu.append(SeparatorLink())
    file_menu.append(Misc_SaveData())
    # View Menu
    view_menu = INIList.global_links[_('View')]
    view_menu.append(SortByMenu(sort_options=[INI_ValidTweaksFirst()]))
    view_menu.append(ColumnsMenu())
    view_menu.append(SeparatorLink())
    view_menu.append(INI_ListINIs())
    # Settings Menu
    settings_menu = INIList.global_links[_('Settings')]
    settings_menu.append(INI_AllowNewLines())
    settings_menu.append(SeparatorLink())
    settings_menu.append(Misc_SettingsDialog())

#------------------------------------------------------------------------------
def InitModLinks():
    """Initialize Mods tab menus."""
    #--ModList: Column Links
    # Sorting and Columns
    ModList.column_links.append(SortByMenu(
        sort_options=[Mods_MastersFirst(), Mods_ActiveFirst()]))
    ModList.column_links.append(ColumnsMenu())
    ModList.column_links.append(SeparatorLink())
    if True: #--Files
        files_menu = MenuLink(_('Files..'))
        files_menu.links.append(UIList_OpenStore())
        files_menu.links.append(Files_Unhide(_('Unhides hidden plugins.')))
        if bush.game.Esp.canBash:
            files_menu.links.append(SeparatorLink())
            files_menu.links.append(Mods_CreateBlank())
            files_menu.links.append(Mods_CreateBlankBashedPatch())
        ModList.column_links.append(files_menu)
    ModList.column_links.append(SeparatorLink())
    ModList.column_links.append(Mods_ActivePlugins())
    if True: #--Load Order
        lo_menu = MenuLink(_('Load Order..'))
        lo_menu.links.append(Mods_LOUndo())
        lo_menu.links.append(Mods_LORedo())
        lo_menu.links.append(SeparatorLink())
        lo_menu.links.append(Mods_LockActivePlugins())
        lo_menu.links.append(SeparatorLink())
        lo_menu.links.append(Mods_OpenLOFileMenu())
        ModList.column_links.append(lo_menu)
        ModList.column_links.append(SeparatorLink())
    ModList.column_links.append(Mods_LockLoadOrder())
    ModList.column_links.append(Mods_AutoGhost())
    if True: #--Plugins
        plugins_menu = MenuLink(_('Plugins..'))
        if bush.game.has_esl:
            plugins_menu.links.append(Mods_AutoESLFlagBP())
            plugins_menu.links.append(SeparatorLink())
        plugins_menu.links.append(Mods_ScanDirty())
        plugins_menu.links.append(Mods_IgnoreDirtyVanillaFiles())
        plugins_menu.links.append(SeparatorLink())
        plugins_menu.links.append(Mods_CrcRefresh())
        plugins_menu.links.append(Mods_ListMods())
        plugins_menu.links.append(Mods_OblivionEsmMenu())
        ModList.column_links.append(plugins_menu)
    if bush.game.allTags: #--Bash Tags
        bash_tags_menu = MenuLink(_('Bash Tags..'))
        bash_tags_menu.links.append(Mods_ListBashTags())
        bash_tags_menu.links.append(Mods_ExportBashTags())
        bash_tags_menu.links.append(Mods_ImportBashTags())
        bash_tags_menu.links.append(Mods_ClearManualBashTags())
        ModList.column_links.append(bash_tags_menu)
        ModList.column_links.append(SeparatorLink())
    ModList.column_links.append(Mods_PluginChecker())
    ModList.column_links.append(Mods_CleanDummyMasters())
    ModList.column_links.append(SeparatorLink())
    ModList.column_links.append(Misc_SaveData())
    ModList.column_links.append(Misc_SettingsDialog())
    #--ModList: Item Links
    if bass.inisettings['ShowDevTools'] and bush.game.Esp.canBash:
        dev_tools_menu = MenuLink('Dev Tools..')
        dev_tools_menu.links.append(Mod_FullLoad())
        dev_tools_menu.links.append(Mod_RecalcRecordCounts())
        dev_tools_menu.links.append(Mod_DumpSubrecords())
        ModList.context_links.append(dev_tools_menu)
    if True: #--File
        file_menu = MenuLink(_('File..'))
        file_menu.links.append(Mod_Duplicate())
        file_menu.links.append(UIList_Hide())
        file_menu.links.append(Mod_Redate())
        file_menu.links.append(UIList_Delete())
        file_menu.links.append(SeparatorLink())
        file_menu.links.append(File_Backup())
        file_menu.links.append(File_RevertToBackup())
        file_menu.links.append(SeparatorLink())
        file_menu.links.append(File_Snapshot())
        file_menu.links.append(File_RevertToSnapshot())
        ModList.context_links.append(file_menu)
    ModList.context_links.append(SeparatorLink())
    ModList.context_links.append(Mod_Move())
    ModList.context_links.append(Mod_ShowReadme())
    ModList.context_links.append(File_JumpToSource())
    if True: #--Info
        info_menu = MenuLink(_('Info..'))
        if bush.game.allTags:
            info_menu.links.append(Mod_ListBashTags())
        info_menu.links.append(Mod_ListDependent())
        info_menu.links.append(File_ListMasters())
        if bush.game.Esp.canBash:
            info_menu.links.append(Mod_ListPatchConfig())
        info_menu.links.append(SeparatorLink())
        if bush.game.allTags:
            info_menu.links.append(Mod_CreateLOOTReport())
        info_menu.links.append(Mod_CopyModInfo())
        if bush.game.Esp.canBash:
            info_menu.links.append(Mod_Details())
        ModList.context_links.append(info_menu)
    if bush.game.Esp.canBash:
        ModList.context_links.append(SeparatorLink())
        ModList.context_links.append(Mod_MarkMergeable())
        ModList.context_links.append(Mod_RebuildPatch())
        ModList.context_links.append(SeparatorLink())
        ModList.context_links.append(Mod_FlipEsm())
        if bush.game.has_esl:
            ModList.context_links.append(Mod_FlipEsl())
        ModList.context_links.append(Mod_FlipMasters())
        ModList.context_links.append(Mod_CreateDummyMasters())
    ModList.context_links.append(SeparatorLink())
    if True: #--Plugin
        plugin_menu = MenuLink(_('Plugin..'))
        if True: #--Groups
            groupMenu = MenuLink(_('Groups..'))
            groupMenu.links.append(Mod_Groups())
            plugin_menu.links.append(groupMenu)
        if True: #--Ratings
            ratingMenu = MenuLink(_('Rating..'))
            ratingMenu.links.append(Mod_Ratings())
            plugin_menu.links.append(ratingMenu)
        plugin_menu.links.append(SeparatorLink())
        plugin_menu.links.append(Mod_AllowGhosting())
        plugin_menu.links.append(Mod_GhostUnghost())
        plugin_menu.links.append(Mod_OrderByName())
        if bush.game.Esp.canBash:
            plugin_menu.links.append(SeparatorLink())
            plugin_menu.links.append(Mod_CopyToMenu())
            if True: #--Cleaning
                cleanMenu = MenuLink(_('Cleaning..'))
                cleanMenu.links.append(Mod_SkipDirtyCheck())
                cleanMenu.links.append(SeparatorLink())
                cleanMenu.links.append(Mod_ScanDirty())
                cleanMenu.links.append(Mod_RemoveWorldOrphans())
                if _is_oblivion:
                    cleanMenu.links.append(Mod_FogFixer())
                plugin_menu.links.append(cleanMenu)
        ModList.context_links.append(plugin_menu)
    if bush.game.Esp.canBash: #--Advanced
        advanced_menu = MenuLink(_('Advanced..'))
        if True: #--Export
            exportMenu = MenuLink(_('Export..'))
            exportMenu.links.append(Mod_EditorIds_Export())
            exportMenu.links.append(Mod_Factions_Export())
            exportMenu.links.append(Mod_FactionRelations_Export())
            if bush.game.fsName in ('Enderal', 'Skyrim'):
                exportMenu.links.append(Mod_FullNames_Export())
                exportMenu.links.append(Mod_Prices_Export())
            elif bush.game.fsName in ('Fallout3', 'FalloutNV'):
                # TODO(inf) Commented out lines were only in FNV branch
                exportMenu.links.append(Mod_FullNames_Export())
                exportMenu.links.append(Mod_Prices_Export())
                # exportMenu.links.append(Mod_IngredientDetails_Export())
                # exportMenu.links.append(Mod_Scripts_Export())
                # exportMenu.links.append(Mod_SpellRecords_Export())
                exportMenu.links.append(Mod_Stats_Export())
            elif _is_oblivion:
                exportMenu.links.append(Mod_IngredientDetails_Export())
                exportMenu.links.append(Mod_FullNames_Export())
                exportMenu.links.append(Mod_ActorLevels_Export())
                exportMenu.links.append(Mod_Prices_Export())
                exportMenu.links.append(Mod_Scripts_Export())
                exportMenu.links.append(Mod_SigilStoneDetails_Export())
                exportMenu.links.append(Mod_SpellRecords_Export())
                exportMenu.links.append(Mod_Stats_Export())
            advanced_menu.links.append(exportMenu)
        if True: #--Import
            importMenu = MenuLink(_('Import..'))
            importMenu.links.append(Mod_EditorIds_Import())
            importMenu.links.append(Mod_Factions_Import())
            importMenu.links.append(Mod_FactionRelations_Import())
            if bush.game.fsName in ('Enderal', 'Skyrim'):
                importMenu.links.append(Mod_FullNames_Import())
                importMenu.links.append(Mod_Prices_Import())
            elif bush.game.fsName in ('Fallout3', 'FalloutNV'):
                # TODO(inf) Commented out lines were only in FNV branch
                importMenu.links.append(Mod_FullNames_Import())
                importMenu.links.append(Mod_Prices_Import())
                # importMenu.links.append(Mod_IngredientDetails_Import())
                # importMenu.links.append(Mod_Scripts_Import())
                importMenu.links.append(Mod_Stats_Import())
                # importMenu.links.append(SeparatorLink())
                # importMenu.links.append(Mod_Face_Import())
                # importMenu.links.append(Mod_Fids_Replace())
            elif _is_oblivion:
                importMenu.links.append(Mod_IngredientDetails_Import())
                importMenu.links.append(Mod_FullNames_Import())
                importMenu.links.append(Mod_ActorLevels_Import())
                importMenu.links.append(Mod_Prices_Import())
                importMenu.links.append(Mod_Scripts_Import())
                importMenu.links.append(Mod_SigilStoneDetails_Import())
                importMenu.links.append(Mod_SpellRecords_Import())
                importMenu.links.append(Mod_Stats_Import())
                importMenu.links.append(SeparatorLink())
                importMenu.links.append(Mod_Face_Import())
                importMenu.links.append(Mod_Fids_Replace())
        advanced_menu.links.append(importMenu)
        if _is_oblivion:
            advanced_menu.links.append(SeparatorLink())
            advanced_menu.links.append(Mod_DecompileAll())
            advanced_menu.links.append(Mod_SetVersion())
        ModList.context_links.append(advanced_menu)
    # ModList: Global Links
    # File Menu
    file_menu = ModList.global_links[_('File')]
    file_menu.append(UIList_OpenStore())
    file_menu.append(Files_Unhide(_('Unhides hidden plugins.')))
    if bush.game.Esp.canBash:
        file_menu.append(SeparatorLink())
        file_menu.append(Mods_CreateBlank())
        file_menu.append(Mods_CreateBlankBashedPatch())
    file_menu.append(SeparatorLink())
    file_menu.append(Misc_SaveData())
    # Edit Menu
    edit_menu = ModList.global_links[_('Edit')]
    edit_menu.append(Mods_ActivePlugins())
    lo_submenu = MenuLink(_('Load Order..'))
    lo_submenu.links.append(Mods_LOUndo())
    lo_submenu.links.append(Mods_LORedo())
    lo_submenu.links.append(SeparatorLink())
    lo_submenu.links.append(Mods_OpenLOFileMenu())
    edit_menu.append(lo_submenu)
    edit_menu.append(Mods_OblivionEsmMenu())
    if bush.game.allTags:
        edit_menu.append(SeparatorLink())
        edit_menu.append(Mods_ExportBashTags())
        edit_menu.append(Mods_ImportBashTags())
        edit_menu.append(Mods_ClearManualBashTags())
    edit_menu.append(SeparatorLink())
    edit_menu.append(Mods_CleanDummyMasters())
    edit_menu.append(Mods_CrcRefresh())
    # View Menu
    view_menu = ModList.global_links[_('View')]
    view_menu.append(SortByMenu(
        sort_options=[Mods_MastersFirst(), Mods_ActiveFirst()]))
    view_menu.append(ColumnsMenu())
    view_menu.append(SeparatorLink())
    view_menu.append(Mods_ListMods())
    if bush.game.allTags:
        view_menu.append(Mods_ListBashTags())
    view_menu.append(Mods_PluginChecker())
    # Settings Menu
    settings_menu = ModList.global_links[_('Settings')]
    settings_menu.append(Mods_AutoGhost())
    if bush.game.has_esl:
        settings_menu.append(Mods_AutoESLFlagBP())
    settings_menu.append(Mods_LockLoadOrder())
    settings_menu.append(Mods_LockActivePlugins())
    settings_menu.append(Mods_ScanDirty())
    settings_menu.append(Mods_IgnoreDirtyVanillaFiles())
    settings_menu.append(SeparatorLink())
    settings_menu.append(Misc_SettingsDialog())

#------------------------------------------------------------------------------
def InitSaveLinks():
    """Initialize save tab menus."""
    #--SaveList: Column Links
    # Sorting and Columns
    SaveList.column_links.append(SortByMenu())
    SaveList.column_links.append(ColumnsMenu())
    SaveList.column_links.append(SeparatorLink())
    if True: #--Files
        files_menu = MenuLink(_('Files..'))
        files_menu.links.append(UIList_OpenStore())
        files_menu.links.append(Files_Unhide(_('Unhides hidden saves.')))
    SaveList.column_links.append(files_menu)
    SaveList.column_links.append(SeparatorLink())
    if True: #--Profile
        subDirMenu = MenuLink(_('Profile..'))
        subDirMenu.links.append(Saves_Profiles())
        SaveList.column_links.append(subDirMenu)
    SaveList.column_links.append(Mods_OblivionEsmMenu(set_profile=True))
    SaveList.column_links.append(SeparatorLink())
    SaveList.column_links.append(Misc_SaveData())
    SaveList.column_links.append(Misc_SettingsDialog())
    #--SaveList: Item Links
    if True: #--File
        file_menu = MenuLink(_('File..'))
        file_menu.links.append(UIList_Rename())
        file_menu.links.append(File_Duplicate())
        file_menu.links.append(UIList_Hide())
        file_menu.links.append(UIList_Delete())
        file_menu.links.append(SeparatorLink())
        file_menu.links.append(File_Backup())
        file_menu.links.append(File_RevertToBackup())
        SaveList.context_links.append(file_menu)
    if True: #--Move To
        moveMenu = MenuLink(_('Move To..'))
        moveMenu.links.append(Save_Move())
        SaveList.context_links.append(moveMenu)
    if True: #--Copy To
        copyMenu = MenuLink(_('Copy To..'))
        copyMenu.links.append(Save_Move(copyMode=True))
        SaveList.context_links.append(copyMenu)
    SaveList.context_links.append(SeparatorLink())
    SaveList.context_links.append(Save_ActivateMasters())
    SaveList.context_links.append(Save_ReorderMasters())
    SaveList.context_links.append(File_ListMasters())
    SaveList.context_links.append(Save_DiffMasters())
    SaveList.context_links.append(SeparatorLink())
    SaveList.context_links.append(Save_ExportScreenshot())
    SaveList.context_links.append(Save_Renumber())
    if True: #--Info
        info_menu = MenuLink(_('Info..'))
        if bush.game.Ess.canEditMore:
            info_menu.links.append(Save_Stats())
        info_menu.links.append(Save_StatObse())
        info_menu.links.append(Save_StatPluggy())
        SaveList.context_links.append(info_menu)
    if bush.game.Ess.canEditMore: #--Edit & Repair
        edit_menu = MenuLink(_('Edit..'))
        edit_menu.links.append(Save_EditCreated(b'ALCH'))
        edit_menu.links.append(Save_ReweighPotions())
        edit_menu.links.append(SeparatorLink())
        edit_menu.links.append(Save_EditCreated(b'ENCH'))
        edit_menu.links.append(Save_EditCreatedEnchantmentCosts())
        edit_menu.links.append(SeparatorLink())
        edit_menu.links.append(Save_EditCreated(b'SPEL'))
        edit_menu.links.append(Save_EditPCSpells())
        edit_menu.links.append(SeparatorLink())
        edit_menu.links.append(Save_RenamePlayer())
        edit_menu.links.append(Save_ImportFace())
        edit_menu.links.append(Save_UpdateNPCLevels())
        repair_menu = MenuLink(_('Repair..'))
        repair_menu.links.append(Save_Unbloat())
        repair_menu.links.append(Save_RepairAbomb())
        repair_menu.links.append(Save_RepairHair())
        SaveList.context_links.append(SeparatorLink())
        SaveList.context_links.append(edit_menu)
        SaveList.context_links.append(repair_menu)
    # SaveList: Global Links
    # File Menu
    file_menu = SaveList.global_links[_('File')]
    file_menu.append(UIList_OpenStore())
    file_menu.append(Files_Unhide(_('Unhides hidden saves.')))
    file_menu.append(SeparatorLink())
    file_menu.append(Misc_SaveData())
    # Edit Menu
    edit_menu = SaveList.global_links[_('Edit')]
    profile_menu = MenuLink(_('Profile..'))
    profile_menu.append(Saves_Profiles())
    edit_menu.append(profile_menu)
    edit_menu.append(Mods_OblivionEsmMenu(set_profile=True))
    # View Menu
    view_menu = SaveList.global_links[_('View')]
    view_menu.append(SortByMenu())
    view_menu.append(ColumnsMenu())
    # Settings Menu
    SaveList.global_links[_('Settings')].append(Misc_SettingsDialog())

#------------------------------------------------------------------------------
def InitBSALinks():
    """Initialize BSA tab menus."""
    #--BSAList: Column Links
    # Sorting and Columns
    BSAList.column_links.append(SortByMenu())
    BSAList.column_links.append(ColumnsMenu())
    BSAList.column_links.append(SeparatorLink())
    if True: #--Files
        files_menu = MenuLink(_('Files..'))
        files_menu.links.append(UIList_OpenStore())
        files_menu.links.append(Files_Unhide(_('Unhides hidden BSAs.')))
    BSAList.column_links.append(files_menu)
    BSAList.column_links.append(SeparatorLink())
    BSAList.column_links.append(Misc_SaveData())
    BSAList.column_links.append(Misc_SettingsDialog())
    #--BSAList: Item Links
    if True: #--File
        file_menu = MenuLink(_('File..'))
        file_menu.links.append(File_Duplicate())
        file_menu.links.append(UIList_Hide())
        file_menu.links.append(File_Redate())
        file_menu.links.append(UIList_Delete())
        file_menu.links.append(SeparatorLink())
        file_menu.links.append(File_Backup())
        file_menu.links.append(File_RevertToBackup())
    BSAList.context_links.append(file_menu)
    BSAList.context_links.append(BSA_ExtractToProject())
    BSAList.context_links.append(BSA_ListContents())
    # BSAList: Global Links
    # File Menu
    file_menu = BSAList.global_links[_('File')]
    file_menu.append(UIList_OpenStore())
    file_menu.append(Files_Unhide(_('Unhides hidden BSAs.')))
    file_menu.append(SeparatorLink())
    file_menu.append(Misc_SaveData())
    # View Menu
    view_menu = BSAList.global_links[_('View')]
    view_menu.append(SortByMenu())
    view_menu.append(ColumnsMenu())
    # Settings Menu
    BSAList.global_links[_('Settings')].append(Misc_SettingsDialog())

#------------------------------------------------------------------------------
def InitScreenLinks():
    """Initialize screens tab menus."""
    #--ScreensList: Column Links
    # Sorting and Columns
    ScreensList.column_links.append(SortByMenu())
    ScreensList.column_links.append(ColumnsMenu())
    ScreensList.column_links.append(SeparatorLink())
    if True:
        files_menu = MenuLink(_('Files..'))
        files_menu.links.append(UIList_OpenStore())
        ScreensList.column_links.append(files_menu)
    ScreensList.column_links.append(SeparatorLink())
    ScreensList.column_links.append(Screens_NextScreenShot())
    if True: #--JPEG Quality
        qualityMenu = MenuLink(_('JPEG Quality..'))
        for i in range(100, 80, -5):
            qualityMenu.links.append(Screens_JpgQuality(i))
        qualityMenu.links.append(Screens_JpgQualityCustom())
        ScreensList.column_links.append(qualityMenu)
    ScreensList.column_links.append(SeparatorLink())
    ScreensList.column_links.append(Misc_SaveData())
    ScreensList.column_links.append(Misc_SettingsDialog())
    #--ScreensList: Item Links
    if True: #--File
        file_menu = MenuLink(_('File..'))
        file_menu.links.append(UIList_OpenItems())
        file_menu.links.append(UIList_Rename())
        file_menu.links.append(File_Duplicate())
        file_menu.links.append(UIList_Delete())
        ScreensList.context_links.append(file_menu)
    if True: #--Convert
        convertMenu = MenuLink(_('Convert..'))
        convertMenu.links.append(Screen_ConvertTo('.jpg'))
        convertMenu.links.append(Screen_ConvertTo('.png'))
        convertMenu.links.append(Screen_ConvertTo('.bmp'))
        convertMenu.links.append(Screen_ConvertTo('.tif'))
        ScreensList.context_links.append(convertMenu)
    # ScreensList: Global Links
    # File Menu
    file_menu = ScreensList.global_links[_('File')]
    file_menu.append(UIList_OpenStore())
    file_menu.append(SeparatorLink())
    file_menu.append(Misc_SaveData())
    # View Menu
    view_menu = ScreensList.global_links[_('View')]
    view_menu.append(SortByMenu())
    view_menu.append(ColumnsMenu())
    # Settings Menu
    settings_menu = ScreensList.global_links[_('Settings')]
    settings_menu.append(Screens_NextScreenShot())
    jpeg_quality_menu = MenuLink(_('JPEG Quality..'))
    for i in range(100, 80, -5):
        jpeg_quality_menu.links.append(Screens_JpgQuality(i))
    jpeg_quality_menu.links.append(Screens_JpgQualityCustom())
    settings_menu.append(qualityMenu)
    settings_menu.append(SeparatorLink())
    ScreensList.global_links[_('Settings')].append(Misc_SettingsDialog())

#------------------------------------------------------------------------------
def InitLinks():
    """Call other link initializers."""
    InitStatusBar()
    InitMasterLinks()
    InitInstallerLinks()
    InitINILinks()
    InitModLinks()
    InitSaveLinks()
    InitScreenLinks()
    # InitBSALinks()
