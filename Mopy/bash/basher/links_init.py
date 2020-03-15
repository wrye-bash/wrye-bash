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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""Links initialization functions. Each panel's UIList has main and items Links
attributes which are populated here. Therefore the layout of the menus is
also defined in these functions."""
from . import InstallersPanel, InstallersList, INIList, ModList, SaveList, \
    BSAList, ScreensList, MasterList, bEnableWizard, PeopleList, \
    BashStatusBar, BashNotebook
from .. import bass, balt, bush
from ..cint import CBashApi
from ..balt import MenuLink, SeparatorLink, UIList_OpenItems, \
    UIList_OpenStore, UIList_Hide
from ..env import init_app_links
from ..gui import Image
# modules below define the __all__ directive
from .app_buttons import *
from .mods_links import *
from .files_links import *
from .installers_links import *
from .installer_links import *
from .saves_links import *
from .settings_links import *
from .misc_links import *
from .ini_links import *
from .mod_links import *
from .bsa_links import *

#------------------------------------------------------------------------------
def InitStatusBar():
    """Initialize status bar links."""
    def imageList(template):
        return [Image(bass.dirs['images'].join(template % i)) for i in
                (16, 24, 32)]
    def _init_tool_buttons(): # tooldirs must have been initialized
        return (((bass.tooldirs['OblivionBookCreatorPath'],
                  bass.inisettings['OblivionBookCreatorJavaArg']),
                 imageList(u'tools/oblivionbookcreator%s.png'),
                 _(u"Launch Oblivion Book Creator"),
                 {'uid': u'OblivionBookCreator'}),
                ((bass.tooldirs['Tes4GeckoPath'],
                  bass.inisettings['Tes4GeckoJavaArg']),
                 imageList(u'tools/tes4gecko%s.png'),
                 _(u"Launch Tes4Gecko"), {'uid': u'Tes4Gecko'}),
                ((bass.tooldirs['Tes5GeckoPath']),
                imageList(u'tools/tesvgecko%s.png'),
                _(u"Launch TesVGecko"), {'uid': u'TesVGecko'}),
        )
    #--Bash Status/LinkBar
    BashStatusBar.obseButton = obseButton = Obse_Button(uid=u'OBSE')
    BashStatusBar.buttons.append(obseButton)
    BashStatusBar.laaButton = laaButton = LAA_Button(uid=u'LAA')
    BashStatusBar.buttons.append(laaButton)
    BashStatusBar.buttons.append(AutoQuit_Button(uid=u'AutoQuit'))
    BashStatusBar.buttons.append( # Game
        Game_Button(
            bass.dirs['app'].join(bush.game.launch_exe),
            bass.dirs['app'].join(*bush.game.version_detect_file),
            imageList(u'%s%%s.png' % bush.game.fsName.lower()),
            u' '.join((_(u"Launch"),bush.game.displayName)),
            u' '.join((_(u"Launch"),bush.game.displayName,u'%(version)s'))))
    BashStatusBar.buttons.append( #TESCS/CreationKit
        TESCS_Button(
            bass.dirs['app'].join(bush.game.ck.exe),
            imageList(bush.game.ck.image_name),
            u' '.join((_(u"Launch"),bush.game.ck.ck_abbrev)),
            u' '.join((_(u"Launch"),bush.game.ck.ck_abbrev,u'%(version)s')),
            bush.game.ck.se_args))
    BashStatusBar.buttons.append( #OBMM
        app_button_factory(bass.dirs['app'].join(u'OblivionModManager.exe'),
                           imageList(u'obmm%s.png'), _(u"Launch OBMM"),
                           uid=u'OBMM'))
    from .constants import toolbar_buttons
    # Just an _App_Button whose path is in bass.tooldirs
    Tooldir_Button = lambda *args: app_button_factory(bass.tooldirs[args[0]],
                                                      *args[1:])
    for tb in toolbar_buttons:
        BashStatusBar.buttons.append(Tooldir_Button(*tb))
    for tb2 in _init_tool_buttons():
        BashStatusBar.buttons.append(app_button_factory(*tb2[:-1], **tb2[-1]))
    BashStatusBar.buttons.append( #Tes4View
        App_Tes4View(
            (bass.tooldirs['Tes4ViewPath'], u'-TES4'), #no cmd argument to force view mode
            imageList(u'tools/tes4view%s.png'),
            _(u"Launch TES4View"),
            uid=u'TES4View'))
    # TODO(inf) Refactor this! I made bush.game.xe a class precisely for stuff
    #  like this - so add stuff like xe.command_line_arg and drop these 30+
    #  braindead lines
    BashStatusBar.buttons.append( #Tes4Edit
        App_Tes4View((bass.tooldirs['Tes4EditPath'], u'-TES4 -edit'),
                     imageList(u'tools/tes4edit%s.png'),
                     _(u"Launch TES4Edit"),
                     uid=u'TES4Edit'))
    BashStatusBar.buttons.append( #Tes5Edit
        App_Tes4View((bass.tooldirs['Tes5EditPath'], u'-TES5 -edit'),
                     imageList(u'tools/tes4edit%s.png'),
                     _(u"Launch TES5Edit"),
                     uid=u'TES5Edit'))
    BashStatusBar.buttons.append( #EnderalEdit
        App_Tes4View((bass.tooldirs['EnderalEditPath'], u'-Enderal -edit'),
                     imageList(u'tools/tes4edit%s.png'),
                     _(u"Launch EnderalEdit"),
                     uid=u'EnderalEdit'))
    BashStatusBar.buttons.append(  #SSEEdit
        App_Tes4View((bass.tooldirs['SSEEditPath'], u'-SSE -edit'),
                     imageList(u'tools/tes4edit%s.png'), _(u"Launch SSEEdit"),
                     uid=u'SSEEdit'))
    BashStatusBar.buttons.append(  #Fo4Edit
        App_Tes4View((bass.tooldirs['Fo4EditPath'], u'-FO4 -edit'),
                     imageList(u'tools/tes4edit%s.png'), _(u"Launch FO4Edit"),
                     uid=u'FO4Edit'))
    BashStatusBar.buttons.append(  #Fo3Edit
        App_Tes4View((bass.tooldirs['Fo3EditPath'], u'-FO3 -edit'),
                     imageList(u'tools/tes4edit%s.png'), _(u"Launch FO3Edit"),
                     uid=u'FO3Edit'))
    BashStatusBar.buttons.append(  #FnvEdit
        App_Tes4View((bass.tooldirs['FnvEditPath'], u'-FNV -edit'),
                     imageList(u'tools/tes4edit%s.png'), _(u"Launch FNVEdit"),
                     uid=u'FNVEdit'))
    BashStatusBar.buttons.append(  #TesVGecko
        app_button_factory((bass.tooldirs['Tes5GeckoPath']),
                           imageList(u'tools/tesvgecko%s.png'),
                           _(u"Launch TesVGecko"), uid=u'TesVGecko'))
    BashStatusBar.buttons.append(  #Tes4Trans
        App_Tes4View((bass.tooldirs['Tes4TransPath'], u'-TES4 -translate'),
                     imageList(u'tools/tes4trans%s.png'),
                     _(u"Launch TES4Trans"), uid=u'TES4Trans'))
    BashStatusBar.buttons.append(  #Tes4LODGen
        App_Tes4View((bass.tooldirs['Tes4LodGenPath'], u'-TES4 -lodgen'),
                     imageList(u'tools/tes4lodgen%s.png'),
                     _(u"Launch Tes4LODGen"), uid=u'TES4LODGen'))
    BashStatusBar.buttons.append( #BOSS
        App_BOSS((bass.tooldirs['boss']),
                imageList(u'boss%s.png'),
                _(u"Launch BOSS"),
                uid=u'BOSS'))
    if bass.inisettings['ShowModelingToolLaunchers']:
        from .constants import modeling_tools_buttons
        for mb in modeling_tools_buttons:
            BashStatusBar.buttons.append(Tooldir_Button(*mb))
        BashStatusBar.buttons.append( #Softimage Mod Tool
            app_button_factory((bass.tooldirs['SoftimageModTool'], u'-mod'),
                               imageList(u'tools/softimagemodtool%s.png'),
                               _(u"Launch Softimage Mod Tool"),
                               uid=u'SoftimageModTool'))
    if bass.inisettings['ShowModelingToolLaunchers'] \
            or bass.inisettings['ShowTextureToolLaunchers']:
        BashStatusBar.buttons.append( #Nifskope
            Tooldir_Button('NifskopePath', imageList(u'tools/nifskope%s.png'),
                _(u"Launch Nifskope")))
    if bass.inisettings['ShowTextureToolLaunchers']:
        from .constants import texture_tool_buttons
        for tt in texture_tool_buttons:
            BashStatusBar.buttons.append(Tooldir_Button(*tt))
    if bass.inisettings['ShowAudioToolLaunchers']:
        from .constants import audio_tools
        for at in audio_tools:
            BashStatusBar.buttons.append(Tooldir_Button(*at))
    from .constants import misc_tools
    for mt in misc_tools: BashStatusBar.buttons.append(Tooldir_Button(*mt))
    #--Custom Apps
    dirApps = bass.dirs['mopy'].join(u'Apps')
    badIcons = [Image(bass.dirs['images'].join(u'error_cross_16.png'))] * 3
    def iconList(fileName):
        return [Image(fileName, Image.typesDict[u'ico'], x) for x in
                (16, 24, 32)]
    for pth, icon, description in init_app_links(dirApps, badIcons, iconList):
            BashStatusBar.buttons.append(
                app_button_factory((pth,()), icon, description, canHide=False))
    #--Final couple
    BashStatusBar.buttons.append(App_DocBrowser(uid=u'DocBrowser'))
    BashStatusBar.buttons.append(App_ModChecker(uid=u'ModChecker'))
    BashStatusBar.buttons.append(App_Settings(uid=u'Settings',canHide=False))
    BashStatusBar.buttons.append(App_Help(uid=u'Help',canHide=False))
    if bass.inisettings['ShowDevTools']:
        BashStatusBar.buttons.append(App_Restart(uid=u'Restart'))
        BashStatusBar.buttons.append(App_GenPickle(uid=u'Generate PKL File'))

#------------------------------------------------------------------------------
def InitMasterLinks():
    """Initialize master list menus."""
    #--MasterList: Column Links
    MasterList.mainMenu.append(SortByMenu(
        sort_options=[Mods_EsmsFirst(), Mods_SelectedFirst()]))
    MasterList.mainMenu.append(Master_AllowEdit())
    MasterList.mainMenu.append(Master_ClearRenames())
    #--MasterList: Item Links
    MasterList.itemMenu.append(Master_ChangeTo())
    MasterList.itemMenu.append(Master_Disable())

#------------------------------------------------------------------------------
def InitInstallerLinks():
    """Initialize Installers tab menus."""
    #--Column links
    # Sorting and Columns
    InstallersList.mainMenu.append(SortByMenu(
        sort_options=[Installers_SortActive(), # Installers_SortStructure(),
                      Installers_SortProjects()]))
    InstallersList.mainMenu.append(ColumnsMenu())
    InstallersList.mainMenu.append(SeparatorLink())
    # Files Menu
    if True:
        files_menu = MenuLink(_(u'Files..'))
        files_menu.links.append(UIList_OpenStore())
        files_menu.links.append(Files_Unhide(u'installer'))
        files_menu.links.append(SeparatorLink())
        files_menu.links.append(Installers_CreateNewProject())
        InstallersList.mainMenu.append(files_menu)
    InstallersList.mainMenu.append(SeparatorLink())
    #--Actions
    InstallersList.mainMenu.append(Installers_Refresh())
    InstallersList.mainMenu.append(Installers_Refresh(full_refresh=True))
    InstallersList.mainMenu.append(Installers_AddMarker())
    InstallersList.mainMenu.append(Installers_MonitorInstall())
    InstallersList.mainMenu.append(SeparatorLink())
    InstallersList.mainMenu.append(Installers_ListPackages())
    InstallersList.mainMenu.append(SeparatorLink())
    InstallersList.mainMenu.append(Installers_AnnealAll())
    InstallersList.mainMenu.append(SeparatorLink())
    InstallersList.mainMenu.append(Installers_UninstallAllPackages())
    InstallersList.mainMenu.append(Installers_UninstallAllUnknownFiles())
    InstallersList.mainMenu.append(Installers_AutoApplyEmbeddedBCFs())
    #--Behavior
    InstallersList.mainMenu.append(SeparatorLink())
    InstallersList.mainMenu.append(Installers_AvoidOnStart())
    InstallersList.mainMenu.append(Installers_Enabled())
    InstallersList.mainMenu.append(SeparatorLink())
    InstallersList.mainMenu.append(Installers_AutoAnneal())
    if bEnableWizard:
        InstallersList.mainMenu.append(Installers_AutoWizard())
    InstallersList.mainMenu.append(Installers_AutoRefreshProjects())
    InstallersList.mainMenu.append(Installers_AutoRefreshBethsoft())
    InstallersList.mainMenu.append(Installers_BsaRedirection())
    InstallersList.mainMenu.append(Installers_RemoveEmptyDirs())
    InstallersList.mainMenu.append(Installers_ConflictsReportShowsInactive())
    InstallersList.mainMenu.append(Installers_ConflictsReportShowsLower())
    InstallersList.mainMenu.append(
        Installers_ConflictsReportShowBSAConflicts())
    InstallersList.mainMenu.append(Installers_WizardOverlay())
    InstallersList.mainMenu.append(SeparatorLink())
    InstallersList.mainMenu.append(Installers_GlobalSkips())
    InstallersList.mainMenu.append(Installers_RenameStrings())
    #--Item links
    if True: #--File Menu
        file_menu = MenuLink(_(u'File..'))
        file_menu.links.append(Installer_Open())
        file_menu.links.append(Installer_Rename())
        file_menu.links.append(Installer_Duplicate())
        file_menu.links.append(Installer_Hide())
        file_menu.links.append(File_Redate())
        file_menu.links.append(balt.UIList_Delete())
        InstallersList.itemMenu.append(file_menu)
    if True: #--Open At...
        openAtMenu = InstallerOpenAt_MainMenu(oneDatumOnly=True)
        openAtMenu.links.append(Installer_OpenSearch())
        openAtMenu.links.append(Installer_OpenNexus())
        openAtMenu.links.append(Installer_OpenTESA())
        InstallersList.itemMenu.append(openAtMenu)
    #--Install, uninstall, etc.
    InstallersList.itemMenu.append(Installer_OpenReadme())
    InstallersList.itemMenu.append(Installer_Anneal())
    InstallersList.itemMenu.append(
        Installer_Refresh(calculate_projects_crc=False))
    InstallersList.itemMenu.append(Installer_Move())
    InstallersList.itemMenu.append(SeparatorLink())
    if True:  # Install Menu
        installMenu = MenuLink(_(u'Install..'))
        installMenu.links.append(Installer_Install())
        installMenu.links.append(Installer_Install('MISSING'))
        installMenu.links.append(Installer_Install('LAST'))
        if bEnableWizard:
            wizardMenu = MenuLink(_(u'Wizard Installer..'))
            wizardMenu.links.append(Installer_Wizard(False))
            wizardMenu.links.append(Installer_Wizard(True))
            wizardMenu.links.append(Installer_EditWizard())
            installMenu.links.append(wizardMenu)
        InstallersList.itemMenu.append(installMenu)
    InstallersList.itemMenu.append(Installer_Uninstall())
    InstallersList.itemMenu.append(SeparatorLink())
    if True:  # Package Menu
        packageMenu = MenuLink(_(u'Package..'))
        packageMenu.links.append(Installer_Refresh())
        packageMenu.links.append(SeparatorLink())
        if bush.game.has_achlist:
            packageMenu.links.append(Installer_ExportAchlist())
        packageMenu.links.append(InstallerProject_Pack())
        packageMenu.links.append(InstallerProject_ReleasePack())
        packageMenu.links.append(SeparatorLink())
        packageMenu.links.append(Installer_ListStructure())
        packageMenu.links.append(InstallerProject_Sync())
        packageMenu.links.append(InstallerArchive_Unpack())
        packageMenu.links.append(Installer_CopyConflicts())
        InstallersList.itemMenu.append(packageMenu)
    #--Build
    if True: #--BAIN Conversion
        conversionsMenu = InstallerConverter_MainMenu()
        conversionsMenu.links.append(InstallerConverter_Create())
        conversionsMenu.links.append(InstallerConverter_ConvertMenu())
        InstallersList.itemMenu.append(conversionsMenu)
    InstallersList.itemMenu.append(SeparatorLink())
    InstallersList.itemMenu.append(Installer_HasExtraData())
    InstallersList.itemMenu.append(Installer_OverrideSkips())
    InstallersList.itemMenu.append(Installer_SkipVoices())
    InstallersList.itemMenu.append(Installer_SkipRefresh())
    InstallersList.itemMenu.append(SeparatorLink())
    InstallersList.itemMenu.append(InstallerProject_OmodConfig())
    # Plugin Filter Main Menu
    InstallersPanel.espmMenu.append(Installer_Espm_SelectAll())
    InstallersPanel.espmMenu.append(Installer_Espm_DeselectAll())
    InstallersPanel.espmMenu.append(Installer_Espm_List())
    InstallersPanel.espmMenu.append(SeparatorLink())
    # Plugin Filter Item Menu
    InstallersPanel.espmMenu.append(Installer_Espm_Rename())
    InstallersPanel.espmMenu.append(Installer_Espm_Reset())
    InstallersPanel.espmMenu.append(Installer_Espm_ResetAll())
    InstallersPanel.espmMenu.append(SeparatorLink())
    InstallersPanel.espmMenu.append(Installer_Espm_JumpToMod())
    #--Sub-Package Main Menu
    InstallersPanel.subsMenu.append(Installer_Subs_SelectAll())
    InstallersPanel.subsMenu.append(Installer_Subs_DeselectAll())
    InstallersPanel.subsMenu.append(Installer_Subs_ToggleSelection())
    InstallersPanel.subsMenu.append(SeparatorLink())
    InstallersPanel.subsMenu.append(Installer_Subs_ListSubPackages())

#------------------------------------------------------------------------------
def InitINILinks():
    """Initialize INI Edits tab menus."""
    #--Column Links
    # Sorting and Columns
    INIList.mainMenu.append(SortByMenu(sort_options=[INI_SortValid()]))
    INIList.mainMenu.append(ColumnsMenu())
    INIList.mainMenu.append(SeparatorLink())
    # Files Menu
    if True:
        files_menu = MenuLink(_(u'Files..'))
        files_menu.links.append(UIList_OpenStore())
        INIList.mainMenu.append(files_menu)
    INIList.mainMenu.append(SeparatorLink())
    INIList.mainMenu.append(INI_AllowNewLines())
    INIList.mainMenu.append(INI_ListINIs())
    #--Item menu
    INIList.itemMenu.append(INI_Apply())
    INIList.itemMenu.append(INI_CreateNew())
    INIList.itemMenu.append(INI_ListErrors())
    INIList.itemMenu.append(SeparatorLink())
    INIList.itemMenu.append(INI_FileOpenOrCopy())
    INIList.itemMenu.append(INI_Delete())

#------------------------------------------------------------------------------
def InitModLinks():
    """Initialize Mods tab menus."""
    #--ModList: Column Links
    # Sorting and Columns
    ModList.mainMenu.append(SortByMenu(
        sort_options=[Mods_EsmsFirst(), Mods_SelectedFirst()]))
    ModList.mainMenu.append(ColumnsMenu())
    ModList.mainMenu.append(SeparatorLink())
    # Files Menu
    if True:
        files_menu = MenuLink(_(u'Files..'))
        files_menu.links.append(UIList_OpenStore())
        files_menu.links.append(Files_Unhide(u'mod'))
        if bush.game.Esp.canBash:
            files_menu.links.append(SeparatorLink())
            files_menu.links.append(Mods_CreateBlankBashedPatch())
            files_menu.links.append(Mods_CreateBlank())
            files_menu.links.append(Mods_CreateBlank(masterless=True))
        ModList.mainMenu.append(files_menu)
    ModList.mainMenu.append(SeparatorLink())
    if True: #--Load
        loadMenu = MenuLink(_(u'Load Order'))
        loadMenu.links.append(Mods_LoadList())
        ModList.mainMenu.append(loadMenu)
    ModList.mainMenu.append(SeparatorLink())
    if bush.game.fsName == u'Oblivion': #--Versions
        versionsMenu = MenuLink(u"Oblivion.esm")
        versionsMenu.links.append(Mods_OblivionVersion(u'1.1'))
        versionsMenu.links.append(Mods_OblivionVersion(u'1.1b'))
        versionsMenu.links.append(Mods_OblivionVersion(u'GOTY non-SI'))
        versionsMenu.links.append(Mods_OblivionVersion(u'SI'))
        ModList.mainMenu.append(versionsMenu)
        ModList.mainMenu.append(SeparatorLink())
    ModList.mainMenu.append(Mods_ListMods())
    ModList.mainMenu.append(Mods_ListBashTags())
    ModList.mainMenu.append(Mods_CleanDummyMasters())
    ModList.mainMenu.append(SeparatorLink())
    ModList.mainMenu.append(Mods_AutoGhost())
    if bush.game.has_esl:
        ModList.mainMenu.append(Mods_AutoESLFlagBP())
    ModList.mainMenu.append(Mods_LockLoadOrder())
    ModList.mainMenu.append(Mods_ScanDirty())
    ModList.mainMenu.append(SeparatorLink())
    ModList.mainMenu.append(Mods_CrcRefresh())
    #--ModList: Item Links
    if bass.inisettings['ShowDevTools'] and bush.game.Esp.canBash:
        ModList.itemMenu.append(Mod_FullLoad())
    if True: #--File
        file_menu = MenuLink(_(u'File..'))
        file_menu.links.append(File_Duplicate())
        file_menu.links.append(UIList_Hide())
        file_menu.links.append(Mod_Redate())
        file_menu.links.append(balt.UIList_Delete())
        file_menu.links.append(SeparatorLink())
        file_menu.links.append(File_Backup())
        file_menu.links.append(File_RevertToBackup())
        file_menu.links.append(SeparatorLink())
        file_menu.links.append(File_Snapshot())
        file_menu.links.append(File_RevertToSnapshot())
        ModList.itemMenu.append(file_menu)
    if True: #--Groups
        groupMenu = MenuLink(_(u"Groups"))
        groupMenu.links.append(Mod_Groups())
        ModList.itemMenu.append(groupMenu)
    if True: #--Ratings
        ratingMenu = MenuLink(_(u"Rating"))
        ratingMenu.links.append(Mod_Ratings())
        ModList.itemMenu.append(ratingMenu)
    #--------------------------------------------
    ModList.itemMenu.append(SeparatorLink())
    ModList.itemMenu.append(Mod_Move())
    ModList.itemMenu.append(Mod_OrderByName())
    ModList.itemMenu.append(SeparatorLink())
    if bush.game.Esp.canBash:
        ModList.itemMenu.append(Mod_Details())
    ModList.itemMenu.append(File_ListMasters())
    ModList.itemMenu.append(Mod_ShowReadme())
    ModList.itemMenu.append(Mod_ListBashTags())
    ModList.itemMenu.append(Mod_CreateBOSSReport())
    ModList.itemMenu.append(Mod_CopyModInfo())
    ModList.itemMenu.append(Mod_ListDependent())
    ModList.itemMenu.append(Mod_JumpToInstaller())
    #--------------------------------------------
    ModList.itemMenu.append(SeparatorLink())
    ModList.itemMenu.append(Mod_AllowGhosting())
    ModList.itemMenu.append(Mod_Ghost())
    if bush.game.Esp.canBash:
        ModList.itemMenu.append(SeparatorLink())
        ModList.itemMenu.append(Mod_MarkMergeable())
        if CBashApi.Enabled:
            ModList.itemMenu.append(Mod_MarkMergeable(doCBash=True))
        ModList.itemMenu.append(Mod_Patch_Update())
        if CBashApi.Enabled:
            ModList.itemMenu.append(Mod_Patch_Update(doCBash=True))
        ModList.itemMenu.append(Mod_ListPatchConfig())
        ModList.itemMenu.append(Mod_ExportPatchConfig())
        #--Advanced
        ModList.itemMenu.append(SeparatorLink())
        if True: #--Export
            exportMenu = MenuLink(_(u"Export"))
            if CBashApi.Enabled:
                exportMenu.links.append(CBash_Mod_CellBlockInfo_Export())
            exportMenu.links.append(Mod_EditorIds_Export())
            ## exportMenu.links.append(Mod_ItemData_Export())
            if bush.game.fsName in (u'Enderal', u'Skyrim'):
                exportMenu.links.append(Mod_FullNames_Export())
                exportMenu.links.append(Mod_Prices_Export())
                exportMenu.links.append(Mod_Stats_Export())
            elif bush.game.fsName == u'FalloutNV':
                # exportMenu.links.append(Mod_Factions_Export())
                exportMenu.links.append(Mod_FullNames_Export())
                exportMenu.links.append(Mod_Prices_Export())
                exportMenu.links.append(Mod_FactionRelations_Export())
                # exportMenu.links.append(Mod_IngredientDetails_Export())
                # exportMenu.links.append(Mod_Scripts_Export())
                # exportMenu.links.append(Mod_SpellRecords_Export())
                exportMenu.links.append(Mod_Stats_Export())
            elif bush.game.fsName == u'Fallout3':
                exportMenu.links.append(Mod_FullNames_Export())
                exportMenu.links.append(Mod_Prices_Export())
                exportMenu.links.append(Mod_Stats_Export())
                exportMenu.links.append(Mod_FactionRelations_Export())
            elif bush.game.fsName == u'Oblivion':
                exportMenu.links.append(Mod_Factions_Export())
                exportMenu.links.append(Mod_FullNames_Export())
                exportMenu.links.append(Mod_ActorLevels_Export())
                exportMenu.links.append(CBash_Mod_MapMarkers_Export())
                exportMenu.links.append(Mod_Prices_Export())
                exportMenu.links.append(Mod_FactionRelations_Export())
                exportMenu.links.append(Mod_IngredientDetails_Export())
                exportMenu.links.append(Mod_Scripts_Export())
                exportMenu.links.append(Mod_SigilStoneDetails_Export())
                exportMenu.links.append(Mod_SpellRecords_Export())
                exportMenu.links.append(Mod_Stats_Export())
            ModList.itemMenu.append(exportMenu)
        if True: #--Import
            importMenu = MenuLink(_(u"Import"))
            importMenu.links.append(Mod_EditorIds_Import())
            ## importMenu.links.append(Mod_ItemData_Import())
            if bush.game.fsName in (u'Enderal', u'Skyrim'):
                importMenu.links.append(Mod_FullNames_Import())
                importMenu.links.append(Mod_Prices_Import())
                importMenu.links.append(Mod_Stats_Import())
            elif bush.game.fsName == u'FalloutNV':
                importMenu.links.append(Mod_FullNames_Import())
                importMenu.links.append(Mod_Prices_Import())
                importMenu.links.append(Mod_FactionRelations_Import())
                # importMenu.links.append(Mod_IngredientDetails_Import())
                # importMenu.links.append(Mod_Scripts_Import())
                importMenu.links.append(Mod_Stats_Import())
                # importMenu.links.append(SeparatorLink())
                # importMenu.links.append(Mod_Face_Import())
                # importMenu.links.append(Mod_Fids_Replace())
            elif bush.game.fsName == u'Fallout3':
                importMenu.links.append(Mod_FullNames_Import())
                importMenu.links.append(Mod_Prices_Import())
                importMenu.links.append(Mod_Stats_Import())
                importMenu.links.append(Mod_FactionRelations_Import())
            elif bush.game.fsName == u'Oblivion':
                importMenu.links.append(Mod_Factions_Import())
                importMenu.links.append(Mod_FullNames_Import())
                importMenu.links.append(Mod_ActorLevels_Import())
                importMenu.links.append(CBash_Mod_MapMarkers_Import())
                importMenu.links.append(Mod_Prices_Import())
                importMenu.links.append(Mod_FactionRelations_Import())
                importMenu.links.append(Mod_IngredientDetails_Import())
                importMenu.links.append(Mod_Scripts_Import())
                importMenu.links.append(Mod_SigilStoneDetails_Import())
                importMenu.links.append(Mod_SpellRecords_Import())
                importMenu.links.append(Mod_Stats_Import())
                importMenu.links.append(SeparatorLink())
                importMenu.links.append(Mod_Face_Import())
                importMenu.links.append(Mod_Fids_Replace())
            ModList.itemMenu.append(importMenu)
        if True: #--Cleaning
            cleanMenu = MenuLink(_(u"Mod Cleaning"))
            cleanMenu.links.append(Mod_SkipDirtyCheck())
            cleanMenu.links.append(SeparatorLink())
            cleanMenu.links.append(Mod_ScanDirty())
            cleanMenu.links.append(Mod_RemoveWorldOrphans())
            cleanMenu.links.append(Mod_FogFixer())
            cleanMenu.links.append(Mod_UndeleteRefs())
            ModList.itemMenu.append(cleanMenu)
        # Disabled since it's dangerous - it doesn't update FormIDs, breaking
        # every record in the file.
        # ModList.itemMenu.append(Mod_AddMaster())
        ModList.itemMenu.append(Mod_CopyToEsmp())
        if bush.game.fsName == u'Oblivion':
            ModList.itemMenu.append(Mod_DecompileAll())
        ModList.itemMenu.append(Mod_FlipEsm())
        if bush.game.check_esl:
            ModList.itemMenu.append(Mod_FlipEsl())
        ModList.itemMenu.append(Mod_FlipMasters())
        if bush.game.Esp.canBash:
            ModList.itemMenu.append(Mod_CreateDummyMasters())
        if bush.game.fsName == u'Oblivion':
            ModList.itemMenu.append(Mod_SetVersion())
#    if bosh.inisettings['showadvanced'] == 1:
#        advmenu = MenuLink(_(u"Advanced Scripts"))
#        advmenu.links.append(Mod_DiffScripts())
        #advmenu.links.append(())

#------------------------------------------------------------------------------
def InitSaveLinks():
    """Initialize save tab menus."""
    #--SaveList: Column Links
    # Sorting and Columns
    SaveList.mainMenu.append(SortByMenu())
    SaveList.mainMenu.append(ColumnsMenu())
    SaveList.mainMenu.append(SeparatorLink())
    # Files Menu
    if True:
        files_menu = MenuLink(_(u'Files..'))
        files_menu.links.append(UIList_OpenStore())
        files_menu.links.append(Files_Unhide(u'save'))
    SaveList.mainMenu.append(files_menu)
    SaveList.mainMenu.append(SeparatorLink())
    if True: #--Save Profiles
        subDirMenu = MenuLink(_(u"Profile"))
        subDirMenu.links.append(Saves_Profiles())
        SaveList.mainMenu.append(subDirMenu)
    if bush.game.fsName == u'Oblivion': #--Versions
        SaveList.mainMenu.append(SeparatorLink())
        versionsMenu = MenuLink(u"Oblivion.esm")
        versionsMenu.links.append(Mods_OblivionVersion(u'1.1',setProfile=True))
        versionsMenu.links.append(Mods_OblivionVersion(u'1.1b',setProfile=True))
        versionsMenu.links.append(Mods_OblivionVersion(u'GOTY non-SI',setProfile=True))
        versionsMenu.links.append(Mods_OblivionVersion(u'SI',setProfile=True))
        SaveList.mainMenu.append(versionsMenu)
    #--SaveList: Item Links
    if True: #--File
        file_menu = MenuLink(_(u'File..'))
        file_menu.links.append(Save_Rename())
        file_menu.links.append(File_Duplicate())
        file_menu.links.append(UIList_Hide())
        file_menu.links.append(balt.UIList_Delete())
        file_menu.links.append(SeparatorLink())
        file_menu.links.append(File_Backup())
        file_menu.links.append(File_RevertToBackup())
        SaveList.itemMenu.append(file_menu)
    if True: #--Move to Profile
        moveMenu = MenuLink(_(u"Move To"))
        moveMenu.links.append(Save_Move())
        SaveList.itemMenu.append(moveMenu)
    if True: #--Copy to Profile
        copyMenu = MenuLink(_(u"Copy To"))
        copyMenu.links.append(Save_Move(True))
        SaveList.itemMenu.append(copyMenu)
    #--------------------------------------------
    SaveList.itemMenu.append(SeparatorLink())
    SaveList.itemMenu.append(Save_LoadMasters())
    SaveList.itemMenu.append(File_ListMasters())
    SaveList.itemMenu.append(Save_DiffMasters())
    if bush.game.Ess.canEditMore:
        SaveList.itemMenu.append(Save_Stats())
    SaveList.itemMenu.append(Save_StatObse())
    SaveList.itemMenu.append(Save_StatPluggy())
    if bush.game.Ess.canEditMore:
        #--------------------------------------------
        SaveList.itemMenu.append(SeparatorLink())
        SaveList.itemMenu.append(Save_EditPCSpells())
        SaveList.itemMenu.append(Save_RenamePlayer())
        SaveList.itemMenu.append(Save_EditCreatedEnchantmentCosts())
        SaveList.itemMenu.append(Save_ImportFace())
        SaveList.itemMenu.append(Save_EditCreated('ENCH'))
        SaveList.itemMenu.append(Save_EditCreated('ALCH'))
        SaveList.itemMenu.append(Save_EditCreated('SPEL'))
        SaveList.itemMenu.append(Save_ReweighPotions())
        SaveList.itemMenu.append(Save_UpdateNPCLevels())
    #--------------------------------------------
    SaveList.itemMenu.append(SeparatorLink())
    SaveList.itemMenu.append(Save_ExportScreenshot())
    SaveList.itemMenu.append(Save_Renumber())
    #--------------------------------------------
    if bush.game.Ess.canEditMore:
        SaveList.itemMenu.append(SeparatorLink())
        SaveList.itemMenu.append(Save_Unbloat())
        SaveList.itemMenu.append(Save_RepairAbomb())
        SaveList.itemMenu.append(Save_RepairHair())

#------------------------------------------------------------------------------
def InitBSALinks():
    """Initialize BSA tab menus."""
    #--BSAList: Column Links
    # Sorting and Columns
    BSAList.mainMenu.append(SortByMenu())
    BSAList.mainMenu.append(ColumnsMenu())
    BSAList.mainMenu.append(SeparatorLink())
    # Files Menu
    if True:
        files_menu = MenuLink(_(u'Files..'))
        files_menu.links.append(UIList_OpenStore())
        files_menu.links.append(Files_Unhide(u'BSA'))
    BSAList.mainMenu.append(files_menu)
    BSAList.mainMenu.append(SeparatorLink())
    #--BSAList: Item Links
    if True: #--File
        file_menu = MenuLink(_(u'File..'))
        file_menu.links.append(File_Duplicate())
        file_menu.links.append(UIList_Hide())
        file_menu.links.append(File_Redate())
        file_menu.links.append(balt.UIList_Delete())
        file_menu.links.append(SeparatorLink())
        file_menu.links.append(File_Backup())
        file_menu.links.append(File_RevertToBackup())
    BSAList.itemMenu.append(file_menu)
    BSAList.itemMenu.append(BSA_ExtractToProject())
    BSAList.itemMenu.append(BSA_ListContents())

#------------------------------------------------------------------------------
def InitScreenLinks():
    """Initialize screens tab menus."""
    #--ScreensList: Column Links
    # Sorting and Columns
    ScreensList.mainMenu.append(SortByMenu())
    ScreensList.mainMenu.append(ColumnsMenu())
    ScreensList.mainMenu.append(SeparatorLink())
    if True:
        files_menu = MenuLink(_(u'Files..'))
        files_menu.links.append(UIList_OpenStore())
        ScreensList.mainMenu.append(files_menu)
    ScreensList.mainMenu.append(SeparatorLink())
    ScreensList.mainMenu.append(Screens_NextScreenShot())
    #--JPEG Quality
    if True:
        qualityMenu = MenuLink(_(u'JPEG Quality'))
        for i in range(100, 80, -5):
            qualityMenu.links.append(Screens_JpgQuality(i))
        qualityMenu.links.append(Screens_JpgQualityCustom())
        ScreensList.mainMenu.append(SeparatorLink())
        ScreensList.mainMenu.append(qualityMenu)
    #--ScreensList: Item Links
    if True: #--File
        file_menu = MenuLink(_(u'File..'))
        file_menu.links.append(UIList_OpenItems())
        file_menu.links.append(Screen_Rename())
        file_menu.links.append(File_Duplicate())
        file_menu.links.append(balt.UIList_Delete())
        ScreensList.itemMenu.append(file_menu)
    if True: #--Convert
        convertMenu = MenuLink(_(u'Convert'))
        image_type = Image.typesDict
        convertMenu.links.append(Screen_ConvertTo(u'jpg', image_type['jpg']))
        convertMenu.links.append(Screen_ConvertTo(u'png', image_type['png']))
        convertMenu.links.append(Screen_ConvertTo(u'bmp', image_type['bmp']))
        convertMenu.links.append(Screen_ConvertTo(u'tif', image_type['tif']))
        ScreensList.itemMenu.append(convertMenu)

#------------------------------------------------------------------------------
def InitPeopleLinks():
    """Initialize people tab menus."""
    #--Header links
    # Sorting and Columns
    PeopleList.mainMenu.append(SortByMenu())
    PeopleList.mainMenu.append(ColumnsMenu())
    PeopleList.mainMenu.append(SeparatorLink())
    PeopleList.mainMenu.append(People_AddNew())
    PeopleList.mainMenu.append(People_Import())
    #--Item links
    PeopleList.itemMenu.append(People_Karma())
    PeopleList.itemMenu.append(SeparatorLink())
    PeopleList.itemMenu.append(People_AddNew())
    PeopleList.itemMenu.append(balt.UIList_Delete())
    PeopleList.itemMenu.append(People_Export())

#------------------------------------------------------------------------------
def InitSettingsLinks():
    """Initialize settings menu."""
    SettingsMenu = BashStatusBar.SettingsMenu
    #--User settings
    SettingsMenu.append(Settings_BackupSettings())
    SettingsMenu.append(Settings_RestoreSettings())
    SettingsMenu.append(Settings_SaveSettings())
    #--OBSE Dll info
    SettingsMenu.append(SeparatorLink())
    SettingsMenu.append(Settings_ExportDllInfo())
    SettingsMenu.append(Settings_ImportDllInfo())
    #--Color config
    SettingsMenu.append(SeparatorLink())
    SettingsMenu.append(Settings_Colors())
    if True:
        tabsMenu = BashNotebook.tabLinks(MenuLink(_(u'Tabs')))
        SettingsMenu.append(tabsMenu)
    #--StatusBar
    if True:
        sbMenu = MenuLink(_(u'Status bar'))
        #--Icon size
        if True:
            sizeMenu = MenuLink(_(u'Icon size'))
            for size in (16,24,32):
                sizeMenu.links.append(Settings_IconSize(size))
            sbMenu.links.append(sizeMenu)
        sbMenu.links.append(Settings_UnHideButtons())
        sbMenu.links.append(Settings_StatusBar_ShowVersions())
        SettingsMenu.append(sbMenu)
    SettingsMenu.append(Settings_Languages())
    SettingsMenu.append(Settings_PluginEncodings())
    SettingsMenu.append(Settings_Games())
    SettingsMenu.append(SeparatorLink())
    SettingsMenu.append(Settings_UseAltName())
    SettingsMenu.append(Settings_Deprint())
    SettingsMenu.append(Settings_DumpTranslator())
    SettingsMenu.append(Settings_UAC())

def InitLinks():
    """Call other link initializers."""
    InitStatusBar()
    InitSettingsLinks()
    InitMasterLinks()
    InitInstallerLinks()
    InitINILinks()
    InitModLinks()
    InitSaveLinks()
    InitScreenLinks()
    InitPeopleLinks()
    # InitBSALinks()
