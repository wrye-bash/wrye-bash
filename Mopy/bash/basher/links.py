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
"""Links initialization functions. Each panel (tab) has some Links list
attributes which are populated here. Therefore the order of menu items is
also defined in these functions."""
# TODO(ut): maybe consider a links package - or a package per panel ?
# TODO(ut): remove star imports
import win32gui
from . import InstallersPanel, INIList, ModList, SaveList, BSAList, \
    ScreensList, MessageList, MasterList, bEnableWizard,  PeoplePanel, \
    BashStatusBar
from .constants import PNG, BMP, TIF, ICO
from .installer_links import *
from .mod_links import *
from .saves_links import *
from .mods_links import *
from .files_links import *
from .misc_links import List_Columns
from ..balt import Image, MenuLink

#------------------------------------------------------------------------------
from .app_buttons import Obse_Button, LAA_Button, AutoQuit_Button, \
    Oblivion_Button, TESCS_Button, App_Button, Tooldir_Button, App_Tes4View, \
    App_BOSS, App_DocBrowser, App_ModChecker, App_Settings, App_Help, \
    App_Restart, App_GenPickle

def InitStatusBar():
    """Initialize status bar links."""
    dirImages = bosh.dirs['images']
    def imageList(template):
        return [Image(dirImages.join(template % x)) for x in (16,24,32)]
    #--Bash Status/LinkBar
    BashStatusBar.obseButton = obseButton = Obse_Button(uid=u'OBSE')
    BashStatusBar.buttons.append(obseButton)
    BashStatusBar.laaButton = laaButton = LAA_Button(uid=u'LAA')
    BashStatusBar.buttons.append(laaButton)
    BashStatusBar.buttons.append(AutoQuit_Button(uid=u'AutoQuit'))
    BashStatusBar.buttons.append( # Game
        Oblivion_Button(
            bosh.dirs['app'].join(bush.game.exe),
            imageList(u'%s%%s.png' % bush.game.fsName.lower()),
            u' '.join((_(u"Launch"),bush.game.displayName)),
            u' '.join((_(u"Launch"),bush.game.displayName,u'%(version)s')),
            u'',
            uid=u'Oblivion'))
    BashStatusBar.buttons.append( #TESCS/CreationKit
        TESCS_Button(
            bosh.dirs['app'].join(bush.game.cs.exe),
            imageList(bush.game.cs.imageName),
            u' '.join((_(u"Launch"),bush.game.cs.shortName)),
            u' '.join((_(u"Launch"),bush.game.cs.shortName,u'%(version)s')),
            bush.game.cs.seArgs,
            uid=u'TESCS'))
    BashStatusBar.buttons.append( #OBMM
        App_Button(
            bosh.dirs['app'].join(u'OblivionModManager.exe'),
            imageList(u'obmm%s.png'),
            _(u"Launch OBMM"),
            uid=u'OBMM'))
    BashStatusBar.buttons.append( #ISOBL
        Tooldir_Button(
            u'ISOBL',
            imageList(u'tools/isobl%s.png'),
            _(u"Launch InsanitySorrow's Oblivion Launcher")))
    BashStatusBar.buttons.append( #ISRMG
        Tooldir_Button(
            u'ISRMG',
            imageList(u"tools/insanity'sreadmegenerator%s.png"),
            _(u"Launch InsanitySorrow's Readme Generator")))
    BashStatusBar.buttons.append( #ISRNG
        Tooldir_Button(
            u'ISRNG',
            imageList(u"tools/insanity'srng%s.png"),
            _(u"Launch InsanitySorrow's Random Name Generator")))
    BashStatusBar.buttons.append( #ISRNPCG
        Tooldir_Button(
            u'ISRNPCG',
            imageList(u'tools/randomnpc%s.png'),
            _(u"Launch InsanitySorrow's Random NPC Generator")))
    BashStatusBar.buttons.append( #OBFEL
        Tooldir_Button(
            u'OBFEL',
            imageList(u'tools/oblivionfaceexchangerlite%s.png'),
            _(u"Oblivion Face Exchange Lite")))
    BashStatusBar.buttons.append( #OBMLG
        Tooldir_Button(
            u'OBMLG',
            imageList(u'tools/modlistgenerator%s.png'),
            _(u"Oblivion Mod List Generator")))
    BashStatusBar.buttons.append( #OblivionBookCreator
        App_Button(
            (bosh.tooldirs['OblivionBookCreatorPath'],bosh.inisettings['OblivionBookCreatorJavaArg']),
            imageList(u'tools/oblivionbookcreator%s.png'),
            _(u"Launch Oblivion Book Creator"),
            uid=u'OblivionBookCreator'))
    BashStatusBar.buttons.append( #BSACommander
        Tooldir_Button(
            u'BSACMD',
            imageList(u'tools/bsacommander%s.png'),
            _(u"Launch BSA Commander")))
    BashStatusBar.buttons.append( #Tabula
        Tooldir_Button(
            u'Tabula',
            imageList(u'tools/tabula%s.png'),
            _(u"Launch Tabula")))
    BashStatusBar.buttons.append( #Tes4Files
        Tooldir_Button(
            u'Tes4FilesPath',
            imageList(u'tools/tes4files%s.png'),
            _(u"Launch TES4Files")))
    BashStatusBar.buttons.append( #Tes4Gecko
        App_Button(
            (bosh.tooldirs['Tes4GeckoPath'],bosh.inisettings['Tes4GeckoJavaArg']),
            imageList(u'tools/tes4gecko%s.png'),
            _(u"Launch Tes4Gecko"),
            uid=u'Tes4Gecko'))
    BashStatusBar.buttons.append( #Tes4View
        App_Tes4View(
            (bosh.tooldirs['Tes4ViewPath'],u'-TES4'), #no cmd argument to force view mode
            imageList(u'tools/tes4view%s.png'),
            _(u"Launch TES4View"),
            uid=u'TES4View'))
    BashStatusBar.buttons.append( #Tes4Edit
        App_Tes4View(
            (bosh.tooldirs['Tes4EditPath'],u'-TES4 -edit'),
            imageList(u'tools/tes4edit%s.png'),
            _(u"Launch TES4Edit"),
            uid=u'TES4Edit'))
    BashStatusBar.buttons.append( #Tes5Edit
        App_Tes4View(
            (bosh.tooldirs['Tes5EditPath'],u'-TES5 -edit'),
            imageList(u'tools/tes4edit%s.png'),
            _(u"Launch TES5Edit"),
            uid=u'TES5Edit'))
    BashStatusBar.buttons.append( #TesVGecko
        App_Button( (bosh.tooldirs['Tes5GeckoPath']),
            imageList(u'tools/tesvgecko%s.png'),
            _(u"Launch TesVGecko"),
            uid=u'TesVGecko'))
    BashStatusBar.buttons.append( #Tes4Trans
        App_Tes4View(
            (bosh.tooldirs['Tes4TransPath'],u'-TES4 -translate'),
            imageList(u'tools/tes4trans%s.png'),
            _(u"Launch TES4Trans"),
            uid=u'TES4Trans'))
    BashStatusBar.buttons.append( #Tes4LODGen
        App_Tes4View(
            (bosh.tooldirs['Tes4LodGenPath'],u'-TES4 -lodgen'),
            imageList(u'tools/tes4lodgen%s.png'),
            _(u"Launch Tes4LODGen"),
            uid=u'TES4LODGen'))
    BashStatusBar.buttons.append( #BOSS
        App_BOSS(
            (bosh.tooldirs['boss']),
            imageList(u'boss%s.png'),
            _(u"Launch BOSS"),
            uid=u'BOSS'))
    if bosh.inisettings['ShowModelingToolLaunchers']:
        BashStatusBar.buttons.append( #AutoCad
            Tooldir_Button(
                'AutoCad',
                imageList(u'tools/autocad%s.png'),
                _(u"Launch AutoCad")))
        BashStatusBar.buttons.append( #Blender
            Tooldir_Button(
                'BlenderPath',
                imageList(u'tools/blender%s.png'),
                _(u"Launch Blender")))
        BashStatusBar.buttons.append( #Dogwaffle
            Tooldir_Button(
                'Dogwaffle',
                imageList(u'tools/dogwaffle%s.png'),
                _(u"Launch Dogwaffle")))
        BashStatusBar.buttons.append( #GMax
            Tooldir_Button(
                'GmaxPath',
                imageList(u'tools/gmax%s.png'),
                _(u"Launch Gmax")))
        BashStatusBar.buttons.append( #Maya
            Tooldir_Button(
                'MayaPath',
                imageList(u'tools/maya%s.png'),
                _(u"Launch Maya")))
        BashStatusBar.buttons.append( #Max
            Tooldir_Button(
                'MaxPath',
                imageList(u'tools/3dsmax%s.png'),
                _(u"Launch 3dsMax")))
        BashStatusBar.buttons.append( #Milkshape3D
            Tooldir_Button(
                'Milkshape3D',
                imageList(u'tools/milkshape3d%s.png'),
                _(u"Launch Milkshape 3D")))
        BashStatusBar.buttons.append( #Mudbox
            Tooldir_Button(
                'Mudbox',
                imageList(u'tools/mudbox%s.png'),
                _(u"Launch Mudbox")))
        BashStatusBar.buttons.append( #Sculptris
            Tooldir_Button(
                'Sculptris',
                imageList(u'tools/sculptris%s.png'),
                _(u"Launch Sculptris")))
        BashStatusBar.buttons.append( #Softimage Mod Tool
            App_Button(
                (bosh.tooldirs['SoftimageModTool'],u'-mod'),
                imageList(u'tools/softimagemodtool%s.png'),
                _(u"Launch Softimage Mod Tool"),
                uid=u'SoftimageModTool'))
        BashStatusBar.buttons.append( #SpeedTree
            Tooldir_Button(
                'SpeedTree',
                imageList(u'tools/speedtree%s.png'),
                _(u"Launch SpeedTree")))
        BashStatusBar.buttons.append( #Tree[d]
            Tooldir_Button(
                'Treed',
                imageList(u'tools/treed%s.png'),
                _(u"Launch Tree\[d\]")))
        BashStatusBar.buttons.append( #Wings3D
            Tooldir_Button(
                'Wings3D',
                imageList(u'tools/wings3d%s.png'),
                _(u"Launch Wings 3D")))
    if bosh.inisettings['ShowModelingToolLaunchers'] or bosh.inisettings['ShowTextureToolLaunchers']:
        BashStatusBar.buttons.append( #Nifskope
            Tooldir_Button(
                'NifskopePath',
                imageList(u'tools/nifskope%s.png'),
                _(u"Launch Nifskope")))
    if bosh.inisettings['ShowTextureToolLaunchers']:
        BashStatusBar.buttons.append( #AniFX
            Tooldir_Button(
                'AniFX',
                imageList(u'tools/anifx%s.png'),
                _(u"Launch AniFX")))
        BashStatusBar.buttons.append( #Art Of Illusion
            Tooldir_Button(
                'ArtOfIllusion',
                imageList(u'tools/artofillusion%s.png'),
                _(u"Launch Art Of Illusion")))
        BashStatusBar.buttons.append( #Artweaver
            Tooldir_Button(
                'Artweaver',
                imageList(u'tools/artweaver%s.png'),
                _(u"Launch Artweaver")))
        BashStatusBar.buttons.append( #CrazyBump
            Tooldir_Button(
                'CrazyBump',
                imageList(u'tools/crazybump%s.png'),
                _(u"Launch CrazyBump")))
        BashStatusBar.buttons.append( #DDSConverter
            Tooldir_Button(
                'DDSConverter',
                imageList(u'tools/ddsconverter%s.png'),
                _(u"Launch DDSConverter")))
        BashStatusBar.buttons.append( #DeepPaint
            Tooldir_Button(
                'DeepPaint',
                imageList(u'tools/deeppaint%s.png'),
                _(u"Launch DeepPaint")))
        BashStatusBar.buttons.append( #FastStone Image Viewer
            Tooldir_Button(
                'FastStone',
                imageList(u'tools/faststoneimageviewer%s.png'),
                _(u"Launch FastStone Image Viewer")))
        BashStatusBar.buttons.append( #Genetica
            Tooldir_Button(
                'Genetica',
                imageList(u'tools/genetica%s.png'),
                _(u"Launch Genetica")))
        BashStatusBar.buttons.append( #Genetica Viewer
            Tooldir_Button(
                'GeneticaViewer',
                imageList(u'tools/geneticaviewer%s.png'),
                _(u"Launch Genetica Viewer")))
        BashStatusBar.buttons.append( #GIMP
            Tooldir_Button(
                'GIMP',
                imageList(u'tools/gimp%s.png'),
                _(u"Launch GIMP")))
        BashStatusBar.buttons.append( #GIMP Shop
            Tooldir_Button(
                'GimpShop',
                imageList(u'tools/gimpshop%s.png'),
                _(u"Launch GIMP Shop")))
        BashStatusBar.buttons.append( #IcoFX
            Tooldir_Button(
                'IcoFX',
                imageList(u'tools/icofx%s.png'),
                _(u"Launch IcoFX")))
        BashStatusBar.buttons.append( #Inkscape
            Tooldir_Button(
                'Inkscape',
                imageList(u'tools/inkscape%s.png'),
                _(u"Launch Inkscape")))
        BashStatusBar.buttons.append( #IrfanView
            Tooldir_Button(
                'IrfanView',
                imageList(u'tools/irfanview%s.png'),
                _(u"Launch IrfanView")))
        BashStatusBar.buttons.append( #MaPZone
            Tooldir_Button(
                'MaPZone',
                imageList(u'tools/mapzone%s.png'),
                _(u"Launch MaPZone")))
        BashStatusBar.buttons.append( #MyPaint
            Tooldir_Button(
                'MyPaint',
                imageList(u'tools/mypaint%s.png'),
                _(u"Launch MyPaint")))
        BashStatusBar.buttons.append( #NVIDIAMelody
            Tooldir_Button(
                'NVIDIAMelody',
                imageList(u'tools/nvidiamelody%s.png'),
                _(u"Launch Nvidia Melody")))
        BashStatusBar.buttons.append( #Paint.net
            Tooldir_Button(
                'PaintNET',
                imageList(u'tools/paint.net%s.png'),
                _(u"Launch Paint.NET")))
        BashStatusBar.buttons.append( #PaintShop Photo Pro
            Tooldir_Button(
                'PaintShopPhotoPro',
                imageList(u'tools/paintshopprox3%s.png'),
                _(u"Launch PaintShop Photo Pro")))
        BashStatusBar.buttons.append( #Photoshop
            Tooldir_Button(
                'PhotoshopPath',
                imageList(u'tools/photoshop%s.png'),
                _(u"Launch Photoshop")))
        BashStatusBar.buttons.append( #PhotoScape
            Tooldir_Button(
                'PhotoScape',
                imageList(u'tools/photoscape%s.png'),
                _(u"Launch PhotoScape")))
        BashStatusBar.buttons.append( #PhotoSEAM
            Tooldir_Button(
                'PhotoSEAM',
                imageList(u'tools/photoseam%s.png'),
                _(u"Launch PhotoSEAM")))
        BashStatusBar.buttons.append( #Photobie Design Studio
            Tooldir_Button(
                'Photobie',
                imageList(u'tools/photobie%s.png'),
                _(u"Launch Photobie")))
        BashStatusBar.buttons.append( #PhotoFiltre
            Tooldir_Button(
                'PhotoFiltre',
                imageList(u'tools/photofiltre%s.png'),
                _(u"Launch PhotoFiltre")))
        BashStatusBar.buttons.append( #Pixel Studio Pro
            Tooldir_Button(
                'PixelStudio',
                imageList(u'tools/pixelstudiopro%s.png'),
                _(u"Launch Pixel Studio Pro")))
        BashStatusBar.buttons.append( #Pixia
            Tooldir_Button(
                'Pixia',
                imageList(u'tools/pixia%s.png'),
                _(u"Launch Pixia")))
        BashStatusBar.buttons.append( #TextureMaker
            Tooldir_Button(
                'TextureMaker',
                imageList(u'tools/texturemaker%s.png'),
                _(u"Launch TextureMaker")))
        BashStatusBar.buttons.append( #Twisted Brush
            Tooldir_Button(
                'TwistedBrush',
                imageList(u'tools/twistedbrush%s.png'),
                _(u"Launch TwistedBrush")))
        BashStatusBar.buttons.append( #Windows Texture Viewer
            Tooldir_Button(
                'WTV',
                imageList(u'tools/wtv%s.png'),
                _(u"Launch Windows Texture Viewer")))
        BashStatusBar.buttons.append( #xNormal
            Tooldir_Button(
                'xNormal',
                imageList(u'tools/xnormal%s.png'),
                _(u"Launch xNormal")))
        BashStatusBar.buttons.append( #XnView
            Tooldir_Button(
                'XnView',
                imageList(u'tools/xnview%s.png'),
                _(u"Launch XnView")))
    if bosh.inisettings['ShowAudioToolLaunchers']:
        BashStatusBar.buttons.append( #Audacity
            Tooldir_Button(
                'Audacity',
                imageList(u'tools/audacity%s.png'),
                _(u"Launch Audacity")))
        BashStatusBar.buttons.append( #ABCAmberAudioConverter
            Tooldir_Button(
                'ABCAmberAudioConverter',
                imageList(u'tools/abcamberaudioconverter%s.png'),
                _(u"Launch ABC Amber Audio Converter")))
        BashStatusBar.buttons.append( #Switch
            Tooldir_Button(
                'Switch',
                imageList(u'tools/switch%s.png'),
                _(u"Launch Switch")))
    BashStatusBar.buttons.append( #Fraps
        Tooldir_Button(
            'Fraps',
            imageList(u'tools/fraps%s.png'),
            _(u"Launch Fraps")))
    BashStatusBar.buttons.append( #MAP
        Tooldir_Button(
            'MAP',
            imageList(u'tools/interactivemapofcyrodiil%s.png'),
            _(u"Interactive Map of Cyrodiil and Shivering Isles")))
    BashStatusBar.buttons.append( #LogitechKeyboard
        Tooldir_Button(
            'LogitechKeyboard',
            imageList(u'tools/logitechkeyboard%s.png'),
            _(u"Launch LogitechKeyboard")))
    BashStatusBar.buttons.append( #MediaMonkey
        Tooldir_Button(
            'MediaMonkey',
            imageList(u'tools/mediamonkey%s.png'),
            _(u"Launch MediaMonkey")))
    BashStatusBar.buttons.append( #NPP
        Tooldir_Button(
            'NPP',
            imageList(u'tools/notepad++%s.png'),
            _(u"Launch Notepad++")))
    BashStatusBar.buttons.append( #Steam
        Tooldir_Button(
            'Steam',
            imageList(u'steam%s.png'),
            _(u"Launch Steam")))
    BashStatusBar.buttons.append( #EVGA Precision
        Tooldir_Button(
            'EVGAPrecision',
            imageList(u'tools/evgaprecision%s.png'),
            _(u"Launch EVGA Precision")))
    BashStatusBar.buttons.append( #WinMerge
        Tooldir_Button(
            'WinMerge',
            imageList(u'tools/winmerge%s.png'),
            _(u"Launch WinMerge")))
    BashStatusBar.buttons.append( #Freemind
        Tooldir_Button(
            'FreeMind',
            imageList(u'tools/freemind%s.png'),
            _(u"Launch FreeMind")))
    BashStatusBar.buttons.append( #Freeplane
        Tooldir_Button(
            'Freeplane',
            imageList(u'tools/freeplane%s.png'),
            _(u"Launch Freeplane")))
    BashStatusBar.buttons.append( #FileZilla
        Tooldir_Button(
            'FileZilla',
            imageList(u'tools/filezilla%s.png'),
            _(u"Launch FileZilla")))
    BashStatusBar.buttons.append( #EggTranslator
        Tooldir_Button(
            'EggTranslator',
            imageList(u'tools/eggtranslator%s.png'),
            _(u"Launch Egg Translator")))
    BashStatusBar.buttons.append( #RADVideoTools
        Tooldir_Button(
            'RADVideo',
            imageList(u'tools/radvideotools%s.png'),
            _(u"Launch RAD Video Tools")))
    BashStatusBar.buttons.append( #WinSnap
        Tooldir_Button(
            'WinSnap',
            imageList(u'tools/winsnap%s.png'),
            _(u"Launch WinSnap")))
    #--Custom Apps
    dirApps = bosh.dirs['mopy'].join(u'Apps')
    bosh.initLinks(dirApps)
    folderIcon = None
    badIcons = [Image(bosh.dirs['images'].join(u'x.png'))] * 3
    for link in bosh.links:
        (target,workingdir,args,icon,description) = bosh.links[link]
        path = dirApps.join(link)
        if target.lower().find(ur'installer\{') != -1:
            target = path
        else:
            target = GPath(target)
        if target.exists():
            icon,idex = icon.split(u',')
            if icon == u'':
                if target.cext == u'.exe':
                    # Use the icon embedded in the exe
                    try:
                        win32gui.ExtractIcon(0, target.s, 0)
                        icon = target
                    except Exception as e:
                        icon = u'' # Icon will be set to a red x further down.
                else:
                    # Use the default icon for that file type
                    try:
                        import _winreg
                        if target.isdir():
                            if folderIcon is None:
                                # Special handling of the Folder icon
                                folderkey = _winreg.OpenKey(
                                    _winreg.HKEY_CLASSES_ROOT,
                                    u'Folder')
                                iconkey = _winreg.OpenKey(
                                    folderkey,
                                    u'DefaultIcon')
                                filedata = _winreg.EnumValue(
                                    iconkey,0)
                                filedata = filedata[1]
                                folderIcon = filedata
                            else:
                                filedata = folderIcon
                        else:
                            icon_path = _winreg.QueryValue(
                                _winreg.HKEY_CLASSES_ROOT,
                                target.cext)
                            pathKey = _winreg.OpenKey(
                                _winreg.HKEY_CLASSES_ROOT,
                                u'%s\\DefaultIcon' % icon_path)
                            filedata = _winreg.EnumValue(pathKey, 0)[1]
                            _winreg.CloseKey(pathKey)
                        icon,idex = filedata.split(u',')
                        icon = os.path.expandvars(icon)
                        if not os.path.isabs(icon):
                            # Get the correct path to the dll
                            for dir in os.environ['PATH'].split(u';'):
                                test = GPath(dir).join(icon)
                                if test.exists():
                                    icon = test
                                    break
                    except:
                        deprint(_(u'Error finding icon for %s:') % target.s,traceback=True)
                        icon = u'not\\a\\path'
            icon = GPath(icon)
            # First try a custom icon
            fileName = u'%s%%i.png' % path.sbody
            customIcons = [dirApps.join(fileName % x) for x in (16,24,32)]
            if customIcons[0].exists():
                icon = customIcons
            # Next try the shortcut specified icon
            else:
                if icon.exists():
                    fileName = u';'.join((icon.s,idex))
                    icon = [Image(fileName,ICO,x) for x in (16,24,32)]
            # Last, use the 'x' icon
                else:
                    icon = badIcons
            BashStatusBar.buttons.append(
                App_Button(
                    (path,()),
                    icon, description,
                    canHide=False
                    ))
    #--Final couple
    BashStatusBar.buttons.append(
        App_Button(
            (bosh.dirs['mopy'].join(u'Wrye Bash Launcher.pyw'), u'-d', u'--bashmon'),
            imageList(u'bashmon%s.png'),
            _(u"Launch BashMon"),
            uid=u'Bashmon'))
    BashStatusBar.buttons.append(App_DocBrowser(uid=u'DocBrowser'))
    BashStatusBar.buttons.append(App_ModChecker(uid=u'ModChecker'))
    BashStatusBar.buttons.append(App_Settings(uid=u'Settings',canHide=False))
    BashStatusBar.buttons.append(App_Help(uid=u'Help',canHide=False))
    if bosh.inisettings['ShowDevTools']:
        BashStatusBar.buttons.append(App_Restart(uid=u'Restart'))
        BashStatusBar.buttons.append(App_GenPickle(uid=u'Generate PKL File'))

#------------------------------------------------------------------------------
from .misc_links import Master_ChangeTo, Master_Disable

def InitMasterLinks():
    """Initialize master list menus."""
    #--MasterList: Column Links
    if True: #--Sort by
        sortMenu = MenuLink(_(u"Sort by"))
        sortMenu.links.append(Mods_EsmsFirst())
        sortMenu.links.append(SeparatorLink())
        sortMenu.links.append(Files_SortBy('File'))
        sortMenu.links.append(Files_SortBy('Author'))
        sortMenu.links.append(Files_SortBy('Group'))
        sortMenu.links.append(Files_SortBy('Installer'))
        sortMenu.links.append(Files_SortBy('Load Order'))
        sortMenu.links.append(Files_SortBy('Modified'))
        sortMenu.links.append(Files_SortBy('Save Order'))
        sortMenu.links.append(Files_SortBy('Status'))
        MasterList.mainMenu.append(sortMenu)

    #--MasterList: Item Links
    MasterList.itemMenu.append(Master_ChangeTo())
    MasterList.itemMenu.append(Master_Disable())

#------------------------------------------------------------------------------
from .installers_links import Installers_SortActive,Installers_SortProjects, \
    Installers_Refresh, Installers_AddMarker, Installers_CreateNewProject, \
    Installers_MonitorInstall, Installers_ListPackages, Installers_AnnealAll, \
    Installers_UninstallAllPackages, Installers_UninstallAllUnknownFiles, \
    Installers_AvoidOnStart, Installers_Enabled, Installers_AutoAnneal, \
    Installers_AutoWizard, Installers_AutoRefreshProjects, \
    Installers_AutoRefreshBethsoft, Installers_AutoApplyEmbeddedBCFs, \
    Installers_BsaRedirection, Installers_RemoveEmptyDirs, \
    Installers_ConflictsReportShowsInactive, \
    Installers_ConflictsReportShowsLower, \
    Installers_ConflictsReportShowBSAConflicts, Installers_WizardOverlay, \
    Installers_SkipOBSEPlugins, Installers_SkipScreenshots, \
    Installers_SkipImages, Installers_SkipDocs, Installers_SkipDistantLOD, \
    Installers_SkipLandscapeLODMeshes, Installers_SkipLandscapeLODTextures, \
    Installers_SkipLandscapeLODNormals, Installers_RenameStrings

def InitInstallerLinks():
    """Initialize Installers tab menus."""
    #--Column links
    #--Sorting
    if True:
        sortMenu = MenuLink(_(u"Sort by"))
        sortMenu.links.append(Installers_SortActive())
        sortMenu.links.append(Installers_SortProjects())
        #InstallersPanel.mainMenu.append(Installers_SortStructure())
        sortMenu.links.append(SeparatorLink())
        sortMenu.links.append(Files_SortBy('Package'))
        sortMenu.links.append(Files_SortBy('Order'))
        sortMenu.links.append(Files_SortBy('Modified'))
        sortMenu.links.append(Files_SortBy('Size'))
        sortMenu.links.append(Files_SortBy('Files'))
        InstallersPanel.mainMenu.append(sortMenu)
    #--Columns
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(List_Columns('bash.installers.cols','bash.installers.allCols',['Package']))
    #--Actions
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(balt.Tanks_Open())
    InstallersPanel.mainMenu.append(Installers_Refresh(fullRefresh=False))
    InstallersPanel.mainMenu.append(Installers_Refresh(fullRefresh=True))
    InstallersPanel.mainMenu.append(Installers_AddMarker())
    InstallersPanel.mainMenu.append(Installers_CreateNewProject())
    InstallersPanel.mainMenu.append(Installers_MonitorInstall())
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(Installers_ListPackages())
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(Installers_AnnealAll())
    InstallersPanel.mainMenu.append(Files_Unhide('installer'))
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(Installers_UninstallAllPackages())
    InstallersPanel.mainMenu.append(Installers_UninstallAllUnknownFiles())
    #--Behavior
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(Installers_AvoidOnStart())
    InstallersPanel.mainMenu.append(Installers_Enabled())
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(Installers_AutoAnneal())
    if bEnableWizard:
        InstallersPanel.mainMenu.append(Installers_AutoWizard())
    InstallersPanel.mainMenu.append(Installers_AutoRefreshProjects())
    InstallersPanel.mainMenu.append(Installers_AutoRefreshBethsoft())
    InstallersPanel.mainMenu.append(Installers_AutoApplyEmbeddedBCFs())
    InstallersPanel.mainMenu.append(Installers_BsaRedirection())
    InstallersPanel.mainMenu.append(Installers_RemoveEmptyDirs())
    InstallersPanel.mainMenu.append(Installers_ConflictsReportShowsInactive())
    InstallersPanel.mainMenu.append(Installers_ConflictsReportShowsLower())
    InstallersPanel.mainMenu.append(Installers_ConflictsReportShowBSAConflicts())
    InstallersPanel.mainMenu.append(Installers_WizardOverlay())
    InstallersPanel.mainMenu.append(SeparatorLink())
    InstallersPanel.mainMenu.append(Installers_SkipOBSEPlugins())
    InstallersPanel.mainMenu.append(Installers_SkipScreenshots())
    InstallersPanel.mainMenu.append(Installers_SkipImages())
    InstallersPanel.mainMenu.append(Installers_SkipDocs())
    InstallersPanel.mainMenu.append(Installers_SkipDistantLOD())
    InstallersPanel.mainMenu.append(Installers_SkipLandscapeLODMeshes())
    InstallersPanel.mainMenu.append(Installers_SkipLandscapeLODTextures())
    InstallersPanel.mainMenu.append(Installers_SkipLandscapeLODNormals())
    InstallersPanel.mainMenu.append(Installers_RenameStrings())

    #--Item links
    #--File
    InstallersPanel.itemMenu.append(Installer_Open())
    InstallersPanel.itemMenu.append(Installer_Duplicate())
    InstallersPanel.itemMenu.append(Installer_Delete())
    if True: #--Open At...
        openAtMenu = InstallerOpenAt_MainMenu(_(u"Open at"), oneDatumOnly=True)
        openAtMenu.links.append(Installer_OpenSearch())
        openAtMenu.links.append(Installer_OpenNexus())
        openAtMenu.links.append(Installer_OpenTESA())
        openAtMenu.links.append(Installer_OpenPES())
        InstallersPanel.itemMenu.append(openAtMenu)
    InstallersPanel.itemMenu.append(Installer_Hide())
    InstallersPanel.itemMenu.append(Installer_Rename())
    #--Install, uninstall, etc.
    InstallersPanel.itemMenu.append(SeparatorLink())
    InstallersPanel.itemMenu.append(Installer_Refresh())
    InstallersPanel.itemMenu.append(Installer_Move())
    InstallersPanel.itemMenu.append(SeparatorLink())
    InstallersPanel.itemMenu.append(Installer_HasExtraData())
    InstallersPanel.itemMenu.append(Installer_OverrideSkips())
    InstallersPanel.itemMenu.append(Installer_SkipVoices())
    InstallersPanel.itemMenu.append(Installer_SkipRefresh())
    InstallersPanel.itemMenu.append(SeparatorLink())
    if bEnableWizard:
        InstallersPanel.itemMenu.append(Installer_Wizard(False))
        InstallersPanel.itemMenu.append(Installer_Wizard(True))
        InstallersPanel.itemMenu.append(Installer_EditWizard())
        InstallersPanel.itemMenu.append(SeparatorLink())
    InstallersPanel.itemMenu.append(Installer_OpenReadme())
    InstallersPanel.itemMenu.append(Installer_Anneal())
    InstallersPanel.itemMenu.append(Installer_Install())
    InstallersPanel.itemMenu.append(Installer_Install('LAST'))
    InstallersPanel.itemMenu.append(Installer_Install('MISSING'))
    InstallersPanel.itemMenu.append(Installer_Uninstall())
    InstallersPanel.itemMenu.append(SeparatorLink())
    #--Build
    if True: #--BAIN Conversion
        conversionsMenu = InstallerConverter_MainMenu(_(u"Conversions"))
        conversionsMenu.links.append(InstallerConverter_Create())
        conversionsMenu.links.append(InstallerConverter_ConvertMenu(_(u"Apply")))
        InstallersPanel.itemMenu.append(conversionsMenu)
    InstallersPanel.itemMenu.append(InstallerProject_Pack())
    InstallersPanel.itemMenu.append(InstallerArchive_Unpack())
    InstallersPanel.itemMenu.append(InstallerProject_ReleasePack())
    InstallersPanel.itemMenu.append(InstallerProject_Sync())
    InstallersPanel.itemMenu.append(Installer_CopyConflicts())
    InstallersPanel.itemMenu.append(InstallerProject_OmodConfig())
    InstallersPanel.itemMenu.append(Installer_ListStructure())

    #--espms Main Menu
    InstallersPanel.espmMenu.append(Installer_Espm_SelectAll())
    InstallersPanel.espmMenu.append(Installer_Espm_DeselectAll())
    InstallersPanel.espmMenu.append(Installer_Espm_List())
    InstallersPanel.espmMenu.append(SeparatorLink())
    #--espms Item Menu
    InstallersPanel.espmMenu.append(Installer_Espm_Rename())
    InstallersPanel.espmMenu.append(Installer_Espm_Reset())
    InstallersPanel.espmMenu.append(SeparatorLink())
    InstallersPanel.espmMenu.append(Installer_Espm_ResetAll())

    #--Sub-Package Main Menu
    InstallersPanel.subsMenu.append(Installer_Subs_SelectAll())
    InstallersPanel.subsMenu.append(Installer_Subs_DeselectAll())
    InstallersPanel.subsMenu.append(Installer_Subs_ToggleSelection())
    InstallersPanel.subsMenu.append(SeparatorLink())
    InstallersPanel.subsMenu.append(Installer_Subs_ListSubPackages())

#------------------------------------------------------------------------------
from .ini_links import INI_SortValid, INI_AllowNewLines, INI_ListINIs, \
    INI_Apply, INI_CreateNew, INI_ListErrors, INI_FileOpenOrCopy, INI_Delete

def InitINILinks():
    """Initialize INI Edits tab menus."""
    #--Column Links
    if True: #--Sort by
        sortMenu = MenuLink(_(u"Sort by"))
        sortMenu.links.append(INI_SortValid())
        sortMenu.links.append(SeparatorLink())
        sortMenu.links.append(Files_SortBy('File'))
        sortMenu.links.append(Files_SortBy('Installer'))
    INIList.mainMenu.append(sortMenu)
    INIList.mainMenu.append(SeparatorLink())
    INIList.mainMenu.append(List_Columns('bash.ini.cols','bash.ini.allCols',['File']))
    INIList.mainMenu.append(SeparatorLink())
    INIList.mainMenu.append(INI_AllowNewLines())
    INIList.mainMenu.append(Files_Open())
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
    if True: #--Load
        loadMenu = MenuLink(_(u"Load"))
        loadMenu.links.append(Mods_LoadList())
        ModList.mainMenu.append(loadMenu)
    if True: #--Sort by
        sortMenu = MenuLink(_(u"Sort by"))
        sortMenu.links.append(Mods_EsmsFirst())
        sortMenu.links.append(Mods_SelectedFirst())
        sortMenu.links.append(SeparatorLink())
        sortMenu.links.append(Files_SortBy('File'))
        sortMenu.links.append(Files_SortBy('Author'))
        sortMenu.links.append(Files_SortBy('Group'))
        sortMenu.links.append(Files_SortBy('Installer'))
        sortMenu.links.append(Files_SortBy('Load Order'))
        sortMenu.links.append(Files_SortBy('Modified'))
        sortMenu.links.append(Files_SortBy('Rating'))
        sortMenu.links.append(Files_SortBy('Size'))
        sortMenu.links.append(Files_SortBy('Status'))
        sortMenu.links.append(Files_SortBy('CRC'))
        sortMenu.links.append(Files_SortBy('Mod Status'))
        ModList.mainMenu.append(sortMenu)
    if bush.game.fsName == u'Oblivion': #--Versions
        versionsMenu = MenuLink(u"Oblivion.esm")
        versionsMenu.links.append(Mods_OblivionVersion(u'1.1'))
        versionsMenu.links.append(Mods_OblivionVersion(u'1.1b'))
        versionsMenu.links.append(Mods_OblivionVersion(u'GOTY non-SI'))
        versionsMenu.links.append(Mods_OblivionVersion(u'SI'))
        ModList.mainMenu.append(versionsMenu)
    #--Columns ----------------------------------
    ModList.mainMenu.append(SeparatorLink())
    ModList.mainMenu.append(List_Columns('bash.mods.cols','bash.mods.allCols',['File']))
    #--------------------------------------------
    ModList.mainMenu.append(SeparatorLink())
    #--File Menu---------------------------------
    if True:
        fileMenu = MenuLink(_(u'File'))
        if bush.game.esp.canBash:
            fileMenu.links.append(Mods_CreateBlankBashedPatch())
            fileMenu.links.append(Mods_CreateBlank())
            fileMenu.links.append(SeparatorLink())
        fileMenu.links.append(Files_Open())
        fileMenu.links.append(Files_Unhide('mod'))
        ModList.mainMenu.append(fileMenu)
    ModList.mainMenu.append(SeparatorLink())
    ModList.mainMenu.append(Mods_ListMods())
    ModList.mainMenu.append(Mods_ListBashTags())
    ModList.mainMenu.append(Mods_CleanDummyMasters())
    ModList.mainMenu.append(SeparatorLink())
    ModList.mainMenu.append(Mods_AutoGhost())
    if bush.game.fsName != u'Skyrim':
        ModList.mainMenu.append(Mods_LockTimes())
    ModList.mainMenu.append(Mods_ScanDirty())

    #--ModList: Item Links
    if bosh.inisettings['ShowDevTools']:
        ModList.itemMenu.append(Mod_FullLoad())
    if True: #--File
        fileMenu = MenuLink(_(u"File"))
        if bush.game.esp.canBash:
            fileMenu.links.append(Mod_CreateDummyMasters())
            fileMenu.links.append(SeparatorLink())
        fileMenu.links.append(File_Backup())
        fileMenu.links.append(File_Duplicate())
        fileMenu.links.append(File_Snapshot())
        fileMenu.links.append(SeparatorLink())
        fileMenu.links.append(File_Delete())
        fileMenu.links.append(File_Hide())
        fileMenu.links.append(File_Redate())
        fileMenu.links.append(File_Sort())
        fileMenu.links.append(SeparatorLink())
        fileMenu.links.append(File_RevertToBackup())
        fileMenu.links.append(File_RevertToSnapshot())
        ModList.itemMenu.append(fileMenu)
    if True: #--Groups
        groupMenu = MenuLink(_(u"Group"))
        groupMenu.links.append(Mod_Groups())
        ModList.itemMenu.append(groupMenu)
    if True: #--Ratings
        ratingMenu = MenuLink(_(u"Rating"))
        ratingMenu.links.append(Mod_Ratings())
        ModList.itemMenu.append(ratingMenu)
    #--------------------------------------------
    ModList.itemMenu.append(SeparatorLink())
    if bush.game.esp.canBash:
        ModList.itemMenu.append(Mod_Details())
    ModList.itemMenu.append(File_ListMasters())
    ModList.itemMenu.append(Mod_ShowReadme())
    ModList.itemMenu.append(Mod_ListBashTags())
    ModList.itemMenu.append(Mod_CreateBOSSReport())
    ModList.itemMenu.append(Mod_CopyModInfo())
    #--------------------------------------------
    ModList.itemMenu.append(SeparatorLink())
    ModList.itemMenu.append(Mod_AllowGhosting())
    ModList.itemMenu.append(Mod_Ghost())
    if bush.game.esp.canBash:
        ModList.itemMenu.append(SeparatorLink())
        ModList.itemMenu.append(Mod_MarkMergeable(False))
        if CBash:
            ModList.itemMenu.append(Mod_MarkMergeable(True))
        ModList.itemMenu.append(Mod_Patch_Update(False))
        if CBash:
            ModList.itemMenu.append(Mod_Patch_Update(True))
        ModList.itemMenu.append(Mod_ListPatchConfig())
        ModList.itemMenu.append(Mod_ExportPatchConfig())
        #--Advanced
        ModList.itemMenu.append(SeparatorLink())
        if True: #--Export
            exportMenu = MenuLink(_(u"Export"))
            exportMenu.links.append(CBash_Mod_CellBlockInfo_Export())
            exportMenu.links.append(Mod_EditorIds_Export())
    ##        exportMenu.links.append(Mod_ItemData_Export())
            if bush.game.fsName == u'Skyrim':
                exportMenu.links.append(Mod_FullNames_Export())
                exportMenu.links.append(Mod_Prices_Export())
                exportMenu.links.append(Mod_Stats_Export())
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
    ##        importMenu.links.append(Mod_ItemData_Import())
            if bush.game.fsName == u'Skyrim':
                importMenu.links.append(Mod_FullNames_Import())
                importMenu.links.append(Mod_Prices_Import())
                importMenu.links.append(Mod_Stats_Import())
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
            cleanMenu.links.append(Mod_CleanMod())
            cleanMenu.links.append(Mod_UndeleteRefs())
            ModList.itemMenu.append(cleanMenu)
        ModList.itemMenu.append(Mod_AddMaster())
        ModList.itemMenu.append(Mod_CopyToEsmp())
        if bush.game.fsName != u'Skyrim':
            ModList.itemMenu.append(Mod_DecompileAll())
        ModList.itemMenu.append(Mod_FlipSelf())
        ModList.itemMenu.append(Mod_FlipMasters())
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
    if True: #--Sort
        sortMenu = MenuLink(_(u"Sort by"))
        sortMenu.links.append(Files_SortBy('File'))
        sortMenu.links.append(Files_SortBy('Cell'))
        sortMenu.links.append(Files_SortBy('PlayTime'))
        sortMenu.links.append(Files_SortBy('Modified'))
        sortMenu.links.append(Files_SortBy('Player'))
        sortMenu.links.append(Files_SortBy('Status'))
        SaveList.mainMenu.append(sortMenu)
    if bush.game.fsName == u'Oblivion': #--Versions
        versionsMenu = MenuLink(u"Oblivion.esm")
        versionsMenu.links.append(Mods_OblivionVersion(u'1.1',True))
        versionsMenu.links.append(Mods_OblivionVersion(u'1.1b',True))
        versionsMenu.links.append(Mods_OblivionVersion(u'GOTY non-SI',True))
        versionsMenu.links.append(Mods_OblivionVersion(u'SI',True))
        SaveList.mainMenu.append(versionsMenu)
    if True: #--Save Profiles
        subDirMenu = MenuLink(_(u"Profile"))
        subDirMenu.links.append(Saves_Profiles())
        SaveList.mainMenu.append(subDirMenu)
    #--Columns --------------------------------
    SaveList.mainMenu.append(SeparatorLink())
    SaveList.mainMenu.append(List_Columns('bash.saves.cols','bash.saves.allCols',['File']))
    #------------------------------------------
    SaveList.mainMenu.append(SeparatorLink())
    SaveList.mainMenu.append(Files_Open())
    SaveList.mainMenu.append(Files_Unhide('save'))

    #--SaveList: Item Links
    if True: #--File
        fileMenu = MenuLink(_(u"File")) #>>
        fileMenu.links.append(File_Backup())
        fileMenu.links.append(File_Duplicate())
        #fileMenu.links.append(File_Snapshot())
        fileMenu.links.append(SeparatorLink())
        fileMenu.links.append(File_Delete())
        fileMenu.links.append(File_Hide())
        fileMenu.links.append(SeparatorLink())
        fileMenu.links.append(File_RevertToBackup())
        fileMenu.links.append(Save_Rename())
        fileMenu.links.append(Save_Renumber())
        #fileMenu.links.append(File_RevertToSnapshot())
        SaveList.itemMenu.append(fileMenu)
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
    if bush.game.ess.canEditMore:
        SaveList.itemMenu.append(Save_Stats())
        SaveList.itemMenu.append(Save_StatObse())
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
    #--------------------------------------------
    if bush.game.ess.canEditMore:
        SaveList.itemMenu.append(SeparatorLink())
        SaveList.itemMenu.append(Save_Unbloat())
        SaveList.itemMenu.append(Save_RepairAbomb())
        SaveList.itemMenu.append(Save_RepairFactions())
        SaveList.itemMenu.append(Save_RepairHair())

#------------------------------------------------------------------------------
def InitBSALinks():
    """Initialize save tab menus."""
    #--BSAList: Column Links
    if True: #--Sort
        sortMenu = MenuLink(_(u"Sort by"))
        sortMenu.links.append(Files_SortBy('File'))
        sortMenu.links.append(Files_SortBy('Modified'))
        sortMenu.links.append(Files_SortBy('Size'))
        BSAList.mainMenu.append(sortMenu)
    BSAList.mainMenu.append(SeparatorLink())
    BSAList.mainMenu.append(Files_Open())
    BSAList.mainMenu.append(Files_Unhide('save'))

    #--BSAList: Item Links
    if True: #--File
        fileMenu = MenuLink(_(u"File")) #>>
        fileMenu.links.append(File_Backup())
        fileMenu.links.append(File_Duplicate())
        #fileMenu.links.append(File_Snapshot())
        fileMenu.links.append(SeparatorLink())
        fileMenu.links.append(File_Delete())
        fileMenu.links.append(File_Hide())
        fileMenu.links.append(SeparatorLink())
        fileMenu.links.append(File_RevertToBackup())
        #fileMenu.links.append(File_RevertToSnapshot())
        BSAList.itemMenu.append(fileMenu)
    #--------------------------------------------
    BSAList.itemMenu.append(SeparatorLink())
    BSAList.itemMenu.append(Save_LoadMasters())
    BSAList.itemMenu.append(File_ListMasters())
    BSAList.itemMenu.append(Save_DiffMasters())
    BSAList.itemMenu.append(Save_Stats())
    #--------------------------------------------
    BSAList.itemMenu.append(SeparatorLink())
    BSAList.itemMenu.append(Save_EditPCSpells())
    BSAList.itemMenu.append(Save_ImportFace())
    BSAList.itemMenu.append(Save_EditCreated('ENCH'))
    BSAList.itemMenu.append(Save_EditCreated('ALCH'))
    BSAList.itemMenu.append(Save_EditCreated('SPEL'))
    BSAList.itemMenu.append(Save_ReweighPotions())
    BSAList.itemMenu.append(Save_UpdateNPCLevels())
    #--------------------------------------------
    BSAList.itemMenu.append(SeparatorLink())
    BSAList.itemMenu.append(Save_Unbloat())
    BSAList.itemMenu.append(Save_RepairAbomb())
    BSAList.itemMenu.append(Save_RepairFactions())
    BSAList.itemMenu.append(Save_RepairHair())

#------------------------------------------------------------------------------
from .misc_links import Screens_NextScreenShot, Screen_JpgQuality, \
    Screen_JpgQualityCustom, Screen_Rename, Screen_ConvertTo

def InitScreenLinks():
    """Initialize screens tab menus."""
    #--SaveList: Column Links
    ScreensList.mainMenu.append(Files_Open())
    ScreensList.mainMenu.append(SeparatorLink())
    ScreensList.mainMenu.append(List_Columns('bash.screens.cols','bash.screens.allCols',['File']))
    ScreensList.mainMenu.append(SeparatorLink())
    ScreensList.mainMenu.append(Screens_NextScreenShot())
    #--JPEG Quality
    if True:
        qualityMenu = MenuLink(_(u'JPEG Quality'))
        for i in range(100,80,-5):
            qualityMenu.links.append(Screen_JpgQuality(i))
        qualityMenu.links.append(Screen_JpgQualityCustom())
        ScreensList.mainMenu.append(SeparatorLink())
        ScreensList.mainMenu.append(qualityMenu)

    #--ScreensList: Item Links
    ScreensList.itemMenu.append(File_Open())
    ScreensList.itemMenu.append(Screen_Rename())
    ScreensList.itemMenu.append(File_Delete())
    ScreensList.itemMenu.append(SeparatorLink())
    if True: #--Convert
        convertMenu = MenuLink(_(u'Convert'))
        convertMenu.links.append(Screen_ConvertTo(u'jpg',JPEG))
        convertMenu.links.append(Screen_ConvertTo(u'png',PNG))
        convertMenu.links.append(Screen_ConvertTo(u'bmp',BMP))
        convertMenu.links.append(Screen_ConvertTo(u'tif',TIF))
        ScreensList.itemMenu.append(convertMenu)

#------------------------------------------------------------------------------
from .misc_links import Messages_Archive_Import, Message_Delete

def InitMessageLinks():
    """Initialize messages tab menus."""
    #--SaveList: Column Links
    MessageList.mainMenu.append(Messages_Archive_Import())
    MessageList.mainMenu.append(SeparatorLink())
    MessageList.mainMenu.append(List_Columns('bash.messages.cols','bash.messages.allCols',['Subject']))

    #--ScreensList: Item Links
    MessageList.itemMenu.append(Message_Delete())

#------------------------------------------------------------------------------
from .misc_links import People_AddNew, People_Import, People_Karma, \
    People_Export

def InitPeopleLinks():
    """Initialize people tab menus."""
    #--Header links
    PeoplePanel.mainMenu.append(People_AddNew())
    PeoplePanel.mainMenu.append(People_Import())
    PeoplePanel.mainMenu.append(SeparatorLink())
    PeoplePanel.mainMenu.append(List_Columns('bash.people.cols','bash.people.allCols',['Name']))
    #--Item links
    PeoplePanel.itemMenu.append(People_Karma())
    PeoplePanel.itemMenu.append(SeparatorLink())
    PeoplePanel.itemMenu.append(People_AddNew())
    PeoplePanel.itemMenu.append(balt.Tank_Delete())
    PeoplePanel.itemMenu.append(People_Export())

#------------------------------------------------------------------------------
from .settings_links import Settings_BackupSettings, Settings_RestoreSettings, \
    Settings_SaveSettings, Settings_ExportDllInfo, Settings_ImportDllInfo, \
    Settings_Colors, Settings_IconSize, Settings_UnHideButtons, \
    Settings_StatusBar_ShowVersions, Settings_Languages, \
    Settings_PluginEncodings, Settings_Games, Settings_UseAltName, \
    Settings_Deprint, Settings_DumpTranslator, Settings_UAC
from .misc_links import Tab_Link

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
        tabsMenu = MenuLink(_(u'Tabs'))
        for key in bosh.settings['bash.tabs.order']:
            canDisable = bool(key != 'Mods')
            tabsMenu.links.append(Tab_Link(key,canDisable))
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
    InitMessageLinks()
    InitPeopleLinks()
    #InitBSALinks()
