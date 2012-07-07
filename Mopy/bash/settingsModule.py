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
#  Wrye Bash copyright (C) 2005, 2006, 2007, 2008, 2009 Wrye
#
# =============================================================================

# Imports ---------------------------------------------------------------------
import bosh
import basher

#--Python
import os
import sys
from collections import OrderedDict

#--wxPython
import wx
import wx.lib.scrolledpanel as scrolled
import wx.lib.dragscroller

def globals_gImgIdx():
    #--- Images & PopupMenu/ID Generation ---#
    global gImgDir,gImgStcDir
    gImgDir = u'%s' %bosh.dirs['images']
    gImgStcDir = u'%s' %bosh.dirs['images'].join('stc')
    gImgToolsDir = u'%s' %bosh.dirs['images'].join('tools')
    p = wx.BITMAP_TYPE_PNG

    global gChkImg
    gChkImg = wx.Bitmap(gImgStcDir + os.sep + u'check16.png',p)

    global gImgIdx
    gImgIdx = {}
    for filename in os.listdir(gImgDir):
        if filename.endswith('.png'):
            gImgIdx[u'%s'%filename] = wx.Bitmap(u'%s'%gImgDir + os.sep + u'%s'%filename,p)
        # print filename
    for filename in os.listdir(gImgStcDir):
        if filename.endswith('.png'):
            gImgIdx[u'%s'%filename] = wx.Bitmap(u'%s'%gImgStcDir + os.sep + u'%s'%filename,p)
        # print filename
    for filename in os.listdir(gImgToolsDir):
        if filename.endswith('.png'):
            gImgIdx[u'%s'%filename] = wx.Bitmap(u'%s'%gImgToolsDir + os.sep + u'%s'%filename,p)
        # print filename
    # print gImgIdx

class SettingsDialog(wx.Dialog):
    ''' widget naming convention goes as follows
    [lowercaseletter][gGlobalSetting]_[widget]
    Example: self.bAutoIndentation_CB

    CB = wx.CheckBox
    RB = wx.RadioBox
    SC = wx.SpinCtrl
    SL = wx.Slider
    ST = wx.StaticText
    BMPCOMBO = wx.combo.BitmapComboBox

    b = bool        # 0 = False, 1 = True
    i = integer     # 1,2,3,4,5,6,etc...
    f = float       # 1.23, 9.56756, etc..
    s = string      # 'Some String', 'Woooot!', 'etc...'
    '''
    def __init__(self, parent, id, title):
        wx.Dialog.__init__(self, parent, id, title='Settings', size=(600,600), style=wx.DEFAULT_DIALOG_STYLE)

        globals_gImgIdx()

        vsizer = wx.BoxSizer(wx.VERTICAL)

        self.toolbook = wx.Toolbook(self, -1, style=
                             wx.BK_DEFAULT
                             #wx.BK_TOP
                             #wx.BK_BOTTOM
                             #wx.BK_LEFT
                             #wx.BK_RIGHT
                            )

        generalsettingspanel = wx.Panel(self.toolbook, -1)
        generalsettingspanel.SetBackgroundColour('#6A6F8D')

        ############
        stcsettingspanel = wx.Panel(self.toolbook, -1)
        stcsettingspanel.SetBackgroundColour('#6A6F8D')

        ############

        # pathssettingspanel = DirectoriesPathsPanel(self.toolbook, -1)

        pathssettingspanel = wx.Panel(self.toolbook, -1)
        pathssettingspanel.SetBackgroundColour('#FFFFCC')

        toolbarsettingspanel = wx.Panel(self.toolbook, -1)
        # toolbarsettingspanel = ToolbarToolsPickerPanel(self.toolbook, -1)
        toolbarsettingspanel.SetBackgroundColour('#6A6F8D')

        vsizerpaths = wx.BoxSizer(wx.VERTICAL)
        vsizerpaths.Add(DirectoriesPathsPanel(pathssettingspanel, -1), 1, wx.EXPAND, 0)
        pathssettingspanel.SetSizer(vsizerpaths)

        ############
        devsettingspanel = wx.Panel(self.toolbook, -1)
        devsettingspanel.SetBackgroundColour('#6A6F8D')

        self.dev4CB = wx.CheckBox(devsettingspanel, -1, 'Hmmm', style=wx.BORDER)
        self.dev5CB = wx.CheckBox(devsettingspanel, -1, 'Hmmm', style=wx.BORDER)
        self.dev6CB = wx.CheckBox(devsettingspanel, -1, 'Hmmm', style=wx.BORDER)
        self.dev7CB = wx.CheckBox(devsettingspanel, -1, 'Hmmm', style=wx.BORDER)
        self.dev8CB = wx.CheckBox(devsettingspanel, -1, 'Hmmm', style=wx.BORDER)
        self.dev9CB = wx.CheckBox(devsettingspanel, -1, 'Hmmm', style=wx.BORDER)
        self.dev10CB = wx.CheckBox(devsettingspanel, -1, 'Hmmm', style=wx.BORDER)
        self.dev11CB = wx.CheckBox(devsettingspanel, -1, 'Hmmm', style=wx.BORDER)
        self.dev12CB = wx.CheckBox(devsettingspanel, -1, 'Hmmm', style=wx.BORDER)
        self.dev13CB = wx.CheckBox(devsettingspanel, -1, 'Hmmm', style=wx.BORDER)
        self.dev14CB = wx.CheckBox(devsettingspanel, -1, 'Hmmm', style=wx.BORDER)
        self.dev15CB = wx.CheckBox(devsettingspanel, -1, 'Hmmm', style=wx.BORDER)
        self.dev16CB = wx.CheckBox(devsettingspanel, -1, 'Hmmm', style=wx.BORDER)
        self.dev17CB = wx.CheckBox(devsettingspanel, -1, 'Hmmm', style=wx.BORDER)
        self.dev18CB = wx.CheckBox(devsettingspanel, -1, 'Hmmm', style=wx.BORDER)
        self.dev19CB = wx.CheckBox(devsettingspanel, -1, 'Hmmm', style=wx.BORDER)
        self.dev20CB = wx.CheckBox(devsettingspanel, -1, 'Hmmm', style=wx.BORDER)

        vsizerdev = wx.BoxSizer(wx.VERTICAL)
        vsizerdev.Add(self.dev4CB, 0, wx.ALL, 3)
        vsizerdev.Add(self.dev5CB, 0, wx.ALL, 3)
        vsizerdev.Add(self.dev6CB, 0, wx.ALL, 3)
        vsizerdev.Add(self.dev7CB, 0, wx.ALL, 3)
        vsizerdev.Add(self.dev8CB, 0, wx.ALL, 3)
        vsizerdev.Add(self.dev9CB, 0, wx.ALL, 3)
        vsizerdev.Add(self.dev10CB, 0, wx.ALL, 3)
        vsizerdev.Add(self.dev11CB, 0, wx.ALL, 3)
        vsizerdev.Add(self.dev12CB, 0, wx.ALL, 3)
        vsizerdev.Add(self.dev13CB, 0, wx.ALL, 3)
        vsizerdev.Add(self.dev14CB, 0, wx.ALL, 3)
        vsizerdev.Add(self.dev15CB, 0, wx.ALL, 3)
        vsizerdev.Add(self.dev16CB, 0, wx.ALL, 3)
        vsizerdev.Add(self.dev17CB, 0, wx.ALL, 3)
        vsizerdev.Add(self.dev18CB, 0, wx.ALL, 3)
        vsizerdev.Add(self.dev19CB, 0, wx.ALL, 3)
        vsizerdev.Add(self.dev20CB, 0, wx.ALL, 3)

        devsettingspanel.SetSizer(vsizerdev)

        il = wx.ImageList(32, 32)
        il.Add(gImgIdx['bash_32.png'])
        il.Add(gImgIdx['scintilla32.png'])
        il.Add(gImgIdx['prompt32.png'])
        il.Add(gImgIdx['scrolltools32.png'])
        il.Add(gImgIdx['devsettings32.png'])
        self.toolbook.AssignImageList(il)
        self.toolbook.AddPage(generalsettingspanel, ' General ', True, 0)
        self.toolbook.AddPage(stcsettingspanel, ' STC ', False, 1)
        self.toolbook.AddPage(pathssettingspanel, ' Paths ', False, 2)
        self.toolbook.AddPage(toolbarsettingspanel, ' Toolbar ', False, 3)
        self.toolbook.AddPage(devsettingspanel, ' DEV ', False, 4)

        vsizer.Add(self.toolbook, 1, wx.EXPAND)

        self.SetSizer(vsizer)
        # self.Fit()

        # closebutton.Bind(wx.EVT_BUTTON, self.OnDestroyCustomDialog, id=-1)
        self.Bind(wx.EVT_CLOSE, self.OnDestroyCustomDialog)

        self.SetIcon(wx.Icon(gImgDir + os.sep + u'settings16.png', wx.BITMAP_TYPE_PNG))

    def OnDestroyCustomDialog(self, event):
        self.Destroy()
        # print 'Destroyed Settings Dialog'

class DirectoriesPathsPanel(scrolled.ScrolledPanel):
    def __init__(self,parent,id):
        # wx.Panel.__init__(self, parent, -1)
        scrolled.ScrolledPanel.__init__(self, parent, -1)
        # Scroll Panel
        # self.scrollpanel = scrolled.ScrolledPanel(self, -1, style = wx.SUNKEN_BORDER)
        # self.scrollpanel.SetBackgroundColour('#FFFFCC')# readme background color

        statictextwrapsize = 400

        headerfont =  wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD)
        sectionfont = wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD)
        optionsfont = wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD)

        generalheader = wx.StaticText(self, -1, ' Directories && Paths', (-1, -1))
        generalheader.SetFont(sectionfont)
        generalheader.SetBackgroundColour('#C6C63C')
        # generalheader.SetForegroundColour('#000000')

        # OnGetFallout3Directory
        # OnGetProgramFilesDirectory
        # OnGet7ZipPath
        # OnGetBashINIPath
        # OnGetOBMMPath
        # OnGetTranscendenceGamePath
        gDirPathDict = OrderedDict([
            # bash.bashini.section.????      ,[wx.StaticText String, ToolTipString,
            #                                 CancelBitmap, Bound Function, bash.bashini.????.????]
            
            #[General]
            ('HEADER1'                      ,[u' General ']),
            
            ('sMorrowindDir'                ,[u' Morrowind Directory',u'sMorrowindDir is the path of your Morrowind directory (containing Morrowind.exe).',
                                              u'morrowind16.png', self.OnGetMorrowindDirectory, u'general']),
            ('sMorrowindBashInstallersDir'  ,[u' Morrowind Bash Installers Directory',u'sMorrowindBashInstallersDir is the path of your Morrowind bash installers directory (mods for morrowind).',
                                              u'bash_16.png', self.OnGetMorrowindDirectory, u'general']),
            ('sOblivionDir'                 ,[u' Oblivion Directory',u'sOblivionDir is the path of your Oblivion directory (containing Oblivion.exe).',
                                              u'oblivion16.png', self.OnGetOblivionDirectory, u'general']),
            ('sOblivionBashInstallersDir'   ,[u' Oblivion Bash Installers Directory',u'sOblivionBashInstallersDir is the path of your Oblivion bash installers directory (mods for oblivion).',
                                              u'bash_16.png', self.OnGetOblivionBashInstallersDirectory, u'general']),
            ('sSkyrimDir'                   ,[u' Skyrim Directory',u'sSkyrimDir is the path of your Skyrim directory (containing TESV.exe).',
                                              u'skyrim16.png', self.OnGetSkyrimDirectory, u'general']),
            ('sSkyrimBashInstallersDir'     ,[u' Skyrim Bash Installers Directory',u'sSkyrimBashInstallersDir is the path of your Skyrim bash installers directory (mods for skyrim).',
                                              u'bash_16.png', self.OnGetSkyrimBashInstallersDirectory, u'general']),

            #ESM/ESP/LOD/NIF Tool Launchers
            ('HEADER2'                      ,[u' ESM/ESP/LOD/NIF Tool Launchers ']),
            
            ('sTes4GeckoPath'               ,[u' Tes4Gecko Path',u'sTes4GeckoPath is the path to Tes4Gecko.jar.',
                                              u'tes4gecko16.png', self.OnTest, u'tooloptions']),
            ('sTes4GeckoJavaArg'            ,[u' Tes4Gecko Java Arg',u'sTes4GeckoJavaArg',
                                              u'help16.png', self.OnTest, u'tooloptions']),
            ('sTes4FilesPath'               ,[u' Tes4Files Path',u'sTes4FilesPath is the path to Tes4Files.exe.',
                                              u'tes4files16.png', self.OnTest, u'tooloptions']),
            ('sTes4EditPath'                ,[u' Tes4Edit Path',u'sTes4EditPath is the path to Tes4Edit.exe.',
                                              u'tes4edit16.png', self.OnTest, u'tooloptions']),
            ('sNifskopePath'                ,[u' Nifskope Path',u'sNifskopePath is the path to nifskope.exe.',
                                              u'nifskope16.png', self.OnTest, u'tooloptions']),
            #3D Modeling Tool Launchers
            ('HEADER3'                      ,[u' 3D Modeling Tool Launchers ']),
            
            ('sArtOfIllusionPath'           ,[u' Art Of Illusion Path',u'sArtOfIllusionPath is the path to Art of Illusion.exe.',
                                              u'artofillusion16.png', self.OnTest, u'tooloptions']),
            ('sAutoCadPath'                 ,[u' AutoCad Path',u'sAutoCadPath is the path to acad.exe.',
                                              u'autocad16.png', self.OnTest, u'tooloptions']),
            ('sBlenderPath'                 ,[u' Blender Path',u'sBlenderPath is the path to Blender.exe.',
                                              u'blender16.png', self.OnTest, u'tooloptions']),
            ('sGmaxPath'                    ,[u' Gmax Path',u'sGmaxPath is the path to gmax.exe.',
                                              u'gmax16.png', self.OnTest, u'tooloptions']),
            ('sMaxPath'                     ,[u' 3dsMax Path',u'sMaxPath is the path to 3dsmax.exe.',
                                              u'3dsmax16.png', self.OnTest, u'tooloptions']),
            ('sMayaPath'                    ,[u' Maya Path',u'sMayaPath is the path to Some.exe.',
                                              u'maya16.png', self.OnTest, u'tooloptions']),
            ('sMilkShape3DPath'             ,[u' MilkShape3D Path',u'sMilkShape3DPath is the path to ms3d.exe.',
                                              u'milkshape3d16.png', self.OnTest, u'tooloptions']),
            ('sMudboxPath'                  ,[u' Mudbox Path',u'sMudboxPath is the path to mudbox.exe.',
                                              u'mudbox16.png', self.OnTest, u'tooloptions']),
            ('sSculptrisPath'               ,[u' Sculptris Path',u'sSculptrisPath is the path to Sculptris.exe.',
                                              u'sculptris16.png', self.OnTest, u'tooloptions']),
            ('sSoftimageModToolPath'        ,[u' Softimage Mod Tool Path',u'sSoftimageModToolPath is the path to XSI.bat.',
                                              u'softimagemodtool16.png', self.OnTest, u'tooloptions']),
            ('sSpeedTreePath'               ,[u' SpeedTree Path',u'sSpeedTreePath is the path to Some.exe.',
                                              u'speedtree16.png', self.OnTest, u'tooloptions']),
            ('sTreedPath'                   ,[u' Tree[d] Path',u'sTreedPath is the path to Some.exe.',
                                              u'treed16.png', self.OnTest, u'tooloptions']),
            ('sWings3DPath'                 ,[u' Wings3D Path',u'sWings3DPath is the path to Wings3D.exe.',
                                              u'wings3d16.png', self.OnTest, u'tooloptions']),
            #Texturing/DDS Tool Launchers
            ('HEADER4'                      ,[u' Texturing/DDS Tool Launchers ']),
            
            ('sAniFXPath'                   ,[u' AniFX Path',u'sAniFXPath is the path to AniFX.exe.',
                                              u'anifx16.png', self.OnTest, u'tooloptions']),
            ('sArtweaverPath'               ,[u' Artweaver Path',u'sArtweaverPath is the path to Artweaver.exe.',
                                              u'artweaver16.png', self.OnTest, u'tooloptions']),
            ('sBricksNTilesPath'            ,[u' BricksNTiles Path',u'sBricksNTilesPath is the path to BricksNTiles.exe.',
                                              u'bricksntiles16.png', self.OnTest, u'tooloptions']),
            ('sCrazyBumpPath'               ,[u' CrazyBump Path',u'sCrazyBumpPath is the path to CrazyBump.exe.',
                                              u'crazybump16.png', self.OnTest, u'tooloptions']),
            ('sDDSConverter2Path'           ,[u' SomePath Path',u'sSomePath is the path to DDS Converter 2.exe.',
                                              u'ddsconverter16.png', self.OnTest, u'tooloptions']),
            ('sDeepPaintPath'               ,[u' DeepPaint Path',u'sDeepPaintPath is the path to DeepPaint.exe.',
                                              u'deeppaint16.png', self.OnTest, u'tooloptions']),
            ('sDogwafflePath'               ,[u' Dogwaffle Path',u'sDogwafflePath is the path to dogwaffle.exe.',
                                              u'dogwaffle16.png', self.OnTest, u'tooloptions']),
            ('sGeneticaPath'                ,[u' Genetica Path',u'sGeneticaPath is the path to Genetica.exe.',
                                              u'genetica16.png', self.OnTest, u'tooloptions']),
            ('sGeneticaViewerPath'          ,[u' Genetica Viewer Path',u'sGeneticaViewerPath is the path to Genetica Viewer 3.exe.',
                                              u'geneticaviewer16.png', self.OnTest, u'tooloptions']),
            ('sGeniuXPhotoEFXPath'          ,[u' GeniuX Photo EFX Path',u'sGeniuXPhotoEFXPath is the path to GeniuXPhotoEFX.exe.',
                                              u'geniuxphotoefx16.png', self.OnTest, u'tooloptions']),
            ('sGIMPPath'                    ,[u' GIMP Path',u'sGIMPPath is the path to gimp-2.8.exe.',
                                              u'gimp16.png', self.OnTest, u'tooloptions']),
            ('sGimpShopPath'                ,[u' GimpShop Path',u'sGimpShopPath is the path to gimp-2.2.exe.',
                                              u'gimpshop16.png', self.OnTest, u'tooloptions']),
            ('sIcoFXPath'                   ,[u' IcoFX Path',u'sIcoFXPath is the path to IcoFX.exe.',
                                              u'icofx16.png', self.OnTest, u'tooloptions']),
            ('sInkscapePath'                ,[u' Inkscape Path',u'sInkscapePath is the path to inkscape.exe.',
                                              u'inkscape16.png', self.OnTest, u'tooloptions']),
            ('sMaPZonePath'                 ,[u' MaPZone Path',u'sMaPZonePath is the path to MaPZone2.exe.',
                                              u'mapzone16.png', self.OnTest, u'tooloptions']),
            ('sMyPaintPath'                 ,[u' MyPaint Path',u'sMyPaintPath is the path to mypaint.exe.',
                                              u'mypaint16.png', self.OnTest, u'tooloptions']),
            ('sNVIDIAMelodyPath'            ,[u' NVIDIA Melody Path',u'sNVIDIAMelodyPath is the path to Melody.exe.',
                                              u'nvidiamelody16.png', self.OnTest, u'tooloptions']),
            ('sPaintNETPath'                ,[u' Paint.NET Path',u'sPaintNETPath is the path to PaintDotNet.exe.',
                                              u'paint.net16.png', self.OnTest, u'tooloptions']),
            ('sPaintShopPhotoProPath'       ,[u' PaintShop Photo Pro Path',u'sPaintShopPhotoProPath is the path to Some.exe.',
                                              u'paintshopprox316.png', self.OnTest, u'tooloptions']),
            ('sPhotobieDesignStudioPath'    ,[u' Photobie Design Studio Path',u'sPhotobieDesignStudioPath is the path to Photobie.exe.',
                                              u'photobie16.png', self.OnTest, u'tooloptions']),
            ('sPhotoFiltrePath'             ,[u' PhotoFiltre Path',u'sPhotoFiltrePath is the path to PhotoFiltre.exe.',
                                              u'photofiltre16.png', self.OnTest, u'tooloptions']),
            ('sPhotoScapePath'              ,[u' PhotoScape Path',u'sPhotoScapePath is the path to PhotoScape.exe.',
                                              u'photoscape16.png', self.OnTest, u'tooloptions']),
            ('sPhotoSEAMPath'               ,[u' PhotoSEAM Path',u'sPhotoSEAMPath is the path to PhotoSEAM.exe.',
                                              u'photoseam16.png', self.OnTest, u'tooloptions']),
            ('sPhotoshopPath'               ,[u' Photoshop Path',u'sPhotoshopPath is the path to Photoshop.exe.',
                                              u'photoshop16.png', self.OnTest, u'tooloptions']),
            ('sPixelStudioProPath'          ,[u' Pixel Studio Pro Path',u'sPixelStudioProPath is the path to Pixel.exe.',
                                              u'pixelstudiopro16.png', self.OnTest, u'tooloptions']),
            ('sPixiaPath'                   ,[u' Pixia Path',u'sPixiaPath is the path to pixia.exe.',
                                              u'pixia16.png', self.OnTest, u'tooloptions']),
            ('sTextureMakerPath'            ,[u' Texture Maker Path',u'sTextureMakerPath is the path to texturemaker.exe.',
                                              u'texturemaker16.png', self.OnTest, u'tooloptions']),
            ('sTwistedBrushPath'            ,[u' TwistedBrush Open Studio Path',u'sTwistedBrushPath is the path to tbrush_open_studio.exe.',
                                              u'twistedbrush16.png', self.OnTest, u'tooloptions']),
            ('sWTVPath'                     ,[u' Windows Texture Viewer Path',u'sWTVPath is the path to WTV.exe.',
                                              u'wtv16.png', self.OnTest, u'tooloptions']),
            ('sxNormalPath'                 ,[u' xNormal Path',u'sxNormalPath is the path to xNormal.exe.',
                                              u'xnormal16.png', self.OnTest, u'tooloptions']),
            #General/Modding Tool Launchers
            ('HEADER5'                      ,[u' General/Modding Tool Launchers ']),
            
            ('sBSACMDPath'                  ,[u' BSA Commander Path',u'sBSACMDPath is the path to bsacmd.exe.',
                                              u'bsacommander16.png', self.OnTest, u'tooloptions']),
            ('sEggTranslatorPath'           ,[u' Egg Translator Path',u'sEggTranslatorPath is the path to EggTranslator.exe.',
                                              u'eggtranslator16.png', self.OnTest, u'tooloptions']),
            ('sISOBLPath'                   ,[u' Insanity\'s Oblivion Launcher Path',u'sISOBLPath is the path to ISOBL.exe.',
                                              u'isobl16.png', self.OnTest, u'tooloptions']),
            ('sISRMGPath'                   ,[u' Insanity\'s ReadMe Generator Path',u'sISRMGPath is the path to Insanitys ReadMe Generator.exe.',
                                              u'insanity\'sreadmegenerator16.png', self.OnTest, u'tooloptions']),
            ('sISRNGPath'                   ,[u' Insanity\' Random Name Generator Path',u'sISRNGPath is the path to Random Name Generator.exe.',
                                              u'insanity\'srng16.png', self.OnTest, u'tooloptions']),
            ('sISRNPCGPath'                 ,[u' Insanity\' Random NPC Generator Path',u'sISRNPCGPath is the path to Random NPC.exe.',
                                              u'randomnpc16.png', self.OnTest, u'tooloptions']),
            ('sMAPPath'                     ,[u' Interactive Map of Cyrodiil and Shivering Isles Path',u'sMAPPath is the path to Mapa v 3.52.exe.',
                                              u'interactivemapofcyrodiil16.png', self.OnTest, u'tooloptions']),
            ('sOblivionBookCreatorPathPath' ,[u' Oblivion Book Creator Path',u'sOblivionBookCreatorPathPath is the path to OblivionBookCreator.jar.',
                                              u'oblivionbookcreator16.png', self.OnTest, u'tooloptions']),
            ('sOblivionBookCreatorJavaArg'  ,[u' Oblivion Book Creator Java Arg',u'sOblivionBookCreatorJavaArg',
                                              u'help16.png', self.OnTest, u'tooloptions']),
            ('sOBMLGPath'                   ,[u' Insanity\'s Oblivion Mod List Generator Path',u'sOBMLGPath is the path to Oblivion Mod List Generator.exe.',
                                              u'modlistgenerator16.png', self.OnTest, u'tooloptions']),
            ('sOBFELPath'                   ,[u' Oblivion Face Exchanger Lite Path',u'sOBFELPath is the path to OblivionFaceExchangeLite.exe.',
                                              u'oblivionfaceexchangerlite16.png', self.OnTest, u'tooloptions']),
            ('sRADVideoPath'                ,[u' RAD Video Tools Path',u'sRADVideoPath is the path to radvideo.exe.',
                                              u'radvideotools16.png', self.OnTest, u'tooloptions']),
            ('sTabulaPath'                  ,[u' Tabula Path',u'sTabulaPath is the path to Tabula.exe.',
                                              u'tabula16.png', self.OnTest, u'tooloptions']),
            #Screenshot/Benchmarking Tool Launchers
            ('HEADER6'                      ,[u' Screenshot/Benchmarking Tool Launchers ']),
            
            ('sFastStonePath'               ,[u' FastStone Image Viewer Path',u'sFastStonePath is the path to FSViewer.exe.',
                                              u'faststoneimageviewer16.png', self.OnTest, u'tooloptions']),
            ('sFrapsPath'                   ,[u' Fraps Path',u'sFrapsPath is the path to Fraps.exe.',
                                              u'fraps16.png', self.OnTest, u'tooloptions']),
            ('sIrfanViewPath'               ,[u' IrfanView Path',u'sIrfanViewPath is the path to i_view32.exe.',
                                              u'irfanview16.png', self.OnTest, u'tooloptions']),
            ('sWinSnapPath'                 ,[u' WinSnap Path',u'sWinSnapPath is the path to WinSnap.exe.',
                                              u'winsnap16.png', self.OnTest, u'tooloptions']),
            ('sXnViewPath'                  ,[u' XnView Path',u'sXnViewPath is the path to xnview.exe.',
                                              u'xnview16.png', self.OnTest, u'tooloptions']),
            #Sound/Audio Tool Launchers
            ('HEADER7'                      ,[u' Sound/Audio Tool Launchers ']),
            
            ('sABCAmberAudioConverterPath'  ,[u' ABC Amber Audio Converter Path',u'sABCAmberAudioConverterPath is the path to abcaudio.exe.',
                                              u'abcamberaudioconverter16.png', self.OnTest, u'tooloptions']),
            ('sAudacityPath'                ,[u' Audacity Path',u'sAudacityPath is the path to Audacity.exe.',
                                              u'audacity16.png', self.OnTest, u'tooloptions']),
            ('sMediaMonkeyPath'             ,[u' MediaMonkey Path',u'sMediaMonkeyPath is the path to MediaMonkey.exe.',
                                              u'mediamonkey16.png', self.OnTest, u'tooloptions']),
            ('sSwitchPath'                  ,[u' Switch Path',u'sSwitchPath is the path to switch.exe.',
                                              u'switch16.png', self.OnTest, u'tooloptions']),
            #Text/Development Tool Launchers
            ('HEADER8'                      ,[u' Text/Development Tool Launchers ']),
            
            ('sFreeMindPath'                ,[u' FreeMind Path',u'sFreeMindPath is the path to Freemind.exe.',
                                              u'freemind16.png', self.OnTest, u'tooloptions']),
            ('sFreeplanePath'               ,[u' Freeplane Path',u'sFreeplanePath is the path to freeplane.exe.',
                                              u'freeplane16.png', self.OnTest, u'tooloptions']),
            ('sNPPPath'                     ,[u' Notepad++ Path',u'sNPPPath is the path to notepad++.exe.',
                                              u'notepad++16.png', self.OnTest, u'tooloptions']),
            ('sWinMergePath'                ,[u' WinMerge Path',u'sWinMergePath is the path to WinMergeU.exe.',
                                              u'winmerge16.png', self.OnTest, u'tooloptions']),
            #Other/Miscellaneous Tool Launchers
            ('HEADER9'                      ,[u' Other/Miscellaneous Tool Launchers ']),
            
            ('sEVGAPrecisionPath'           ,[u' EVGA Precision Path',u'sEVGAPrecisionPath is the path to EVGAPrecision.exe.',
                                              u'evgaprecision16.png', self.OnTest, u'tooloptions']),
            ('sFileZillaPath'               ,[u' FileZilla FTP Client Path',u'sFileZillaPath is the path to filezilla.exe.',
                                              u'filezilla16.png', self.OnTest, u'tooloptions']),
            ('sLogitechKeyboardPath'        ,[u' Logitech Keyboard Profiler Path',u'sLogitechKeyboardPath is the path to LGDCore.exe(Legacy) or LCore.exe.',
                                              u'logitechkeyboard16.png', self.OnTest, u'tooloptions']),
            ('sSteamPath'                   ,[u' Steam Path',u'sSteamPath is the path to steam.exe.',
                                              u'steam16.png', self.OnTest, u'tooloptions']),
                                              
            # ('sSomePath'                    ,[u' SomePath Path',u'sSomePath is the path to Some.exe.',
                                              # u'help16.png', self.OnTest, u'tooloptions']),
            ])

        vscrollpanelsizer1 = wx.BoxSizer(wx.VERTICAL)
        vscrollpanelsizer1.Add(wx.StaticLine(self, -1, size=(-1, 1)), 0, wx.EXPAND, 0)
        vscrollpanelsizer1.Add(generalheader, 0, wx.EXPAND, 4)
        for key, value in gDirPathDict.iteritems():
            if 'HEADER' in key:
                st = wx.StaticText(self, -1, value[0], (-1, -1), style=wx.BORDER)
                st.SetFont(headerfont)
                st.SetBackgroundColour('#E6E64C')
                vscrollpanelsizer1.Add(wx.StaticLine(self, -1, size=(-1, 1)), 0, wx.EXPAND, 0)
                vscrollpanelsizer1.AddSpacer(2)
                vscrollpanelsizer1.Add(st, 0, wx.ALL, 2)
                continue
            st = wx.StaticText(self, -1, value[0], (-1, -1))
            st.SetToolTipString(value[1])
            st.SetFont(optionsfont)
            self.key = wx.SearchCtrl(self, value=basher.settings['bash.bashini.%s.%s'%(value[4],key)])
            self.key.SetDescriptiveText('<-- Search...')
            self.key.ShowSearchButton(True)
            self.key.ShowCancelButton(True)
            self.key.SetSearchBitmap(gImgIdx['zoom_on.png'])
            self.key.SetCancelBitmap(gImgIdx[value[2]])
            self.key.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, value[3])

            vscrollpanelsizer1.Add(wx.StaticLine(self, -1, size=(-1, 1)), 0, wx.EXPAND, 0)
            vscrollpanelsizer1.AddSpacer(2)

            vscrollpanelsizer1.Add(st, 0, wx.ALL, 2)
            vscrollpanelsizer1.Add(self.key, 0, wx.EXPAND | wx.ALL, 2)

        self.SetSizer(vscrollpanelsizer1)
        self.SetupScrolling()

        self.dirstring = ''
        self.pathstring = ''

        # dragscoller
        self.dragonscroll = wx.lib.dragscroller.DragScroller(self)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)

        # # sFallout3Directory
        # # sProgramFilesDirectory

        # # s7ZipPath
        # # sBashINIPath
        # # sOBMMPath
        # # sTranscendenceGamePath

    def OnTest(self, event):
        evtobj = event.GetEventObject()
        # print evtobj

    def OnRightDown(self, event):
        self.dragonscroll.Start(event.GetPosition())
        # print('OnRightDown')

    def OnRightUp(self, event):
        self.dragonscroll.Stop()
        # print('OnRightUp')

    def OnGetFile(self, event, message, wildcard):
        dialog = wx.FileDialog(
            self, message=message,
            defaultDir=os.getcwd(),
            defaultFile='',
            wildcard=wildcard,
            style=wx.OPEN | wx.CHANGE_DIR
            )

        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self.pathstring = path

        dialog.Destroy()

    def OnGetDirectory(self, event, locatestring):
        dialog = wx.DirDialog(self, locatestring,
                              style=wx.DD_DEFAULT_STYLE
                               #| wx.DD_DIR_MUST_EXIST
                               #| wx.DD_CHANGE_DIR
                               )

        if dialog.ShowModal() == wx.ID_OK:
            self.dirstring = '%s' % dialog.GetPath()
            # return(self.dirstring)
        else:
            self.dirstring = ''
        dialog.Destroy()

    def OnGetMorrowindDirectory(self, event):
        self.OnGetDirectory(event, locatestring='Locate your Morrowind Directory')
        if self.dirstring != '':
            self.sMorrowindDirectorysearchctrl.SetValue(self.dirstring)
            gGlobalsDict['MorrowindDirectory'] = str(self.dirstring)

    def OnGetOblivionDirectory(self, event):
        self.OnGetDirectory(event, locatestring='Locate your Oblivion Directory')
        if self.dirstring != '':
            self.sOblivionDirectorysearchctrl.SetValue(self.dirstring)
            gGlobalsDict['OblivionDirectory'] = str(self.dirstring)

    def OnGetOblivionDataDirectory(self, event):
        self.OnGetDirectory(event, locatestring='Locate your Oblivion Data Directory')
        if self.dirstring != '':
            self.sOblivionDataDirectorysearchctrl.SetValue(self.dirstring)
            gGlobalsDict['OblivionDataDirectory'] = str(self.dirstring)

    def OnGetOblivionMeshesDirectory(self, event):
        self.OnGetDirectory(event, locatestring='Locate your Oblivion Meshes Directory')
        if self.dirstring != '':
            self.sOblivionMeshesDirectorysearchctrl.SetValue(self.dirstring)
            gGlobalsDict['OblivionMeshesDirectory'] = str(self.dirstring)

    def OnGetOblivionTexturesDirectory(self, event):
        self.OnGetDirectory(event, locatestring='Locate your Oblivion Textures Directory')
        if self.dirstring != '':
            self.sOblivionTexturesDirectorysearchctrl.SetValue(self.dirstring)
            gGlobalsDict['OblivionTexturesDirectory'] = str(self.dirstring)

    def OnGetOblivionTexturesBookDirectory(self, event):
        self.OnGetDirectory(event, locatestring='Locate your Oblivion/Data/Textures/Menus/Book Directory')
        if self.dirstring != '':
            self.sOblivionTexturesBookDirectorysearchctrl.SetValue(self.dirstring)
            gGlobalsDict['OblivionTexturesBookDirectory'] = str(self.dirstring)

    def OnGetOblivionBashInstallersDirectory(self, event):
        self.OnGetDirectory(event, locatestring='Locate your Oblivion Bash Installers Directory')
        if self.dirstring != '':
            self.sOblivionBashInstallersDirectorysearchctrl.SetValue(self.dirstring)
            gGlobalsDict['OblivionBashInstallersDirectory'] = str(self.dirstring)

    def OnGetSkyrimDirectory(self, event):
        self.OnGetDirectory(event, locatestring='Locate your Skyrim Directory')
        if self.dirstring != '':
            self.sSkyrimDirectorysearchctrl.SetValue(self.dirstring)
            gGlobalsDict['SkyrimDirectory'] = str(self.dirstring)

    def OnGetSkyrimDirectoryReg(self, event):
        print('Needs Implemented')

    def OnGetSkyrimBashInstallersDirectory(self, event):
        self.OnGetDirectory(event, locatestring='Locate your Skyrim Bash Installers Directory')
        if self.dirstring != '':
            self.sSkyrimBashInstallersDirectorysearchctrl.SetValue(self.dirstring)
            gGlobalsDict['SkyrimBashInstallersDirectory'] = str(self.dirstring)

    def OnGetFallout3Directory(self, event):
        self.OnGetDirectory(event, locatestring='Locate your Fallout3 Directory')
        if self.dirstring != '':
            self.sFallout3Directorysearchctrl.SetValue(self.dirstring)
            gGlobalsDict['Fallout3Directory'] = str(self.dirstring)

    def OnGetProgramFilesDirectory(self, event):
        self.OnGetDirectory(event, locatestring='Locate your Program Files Directory')
        if self.dirstring != '':
            self.sProgramFilesDirectorysearchctrl.SetValue(self.dirstring)
            gGlobalsDict['ProgramFilesDirectory'] = str(self.dirstring)

    def OnGet7ZipPath(self, event):
        self.OnGetFile(event, message='Locate your OblivionModManager.exe', wildcard='All files (*.exe*)|*.exe*')
        if self.pathstring != '':
            self.sOBMMPathsearchctrl.SetValue(self.pathstring)
            gGlobalsDict['SevenZipPath'] = str(self.dirstring)

    def OnGetBashINIPath(self, event):
        self.OnGetFile(event, message='Locate your bash.ini', wildcard='All files (*.ini*)|*.ini*')
        if self.pathstring != '':
            self.sBashINIPathsearchctrl.SetValue(self.pathstring)
            gGlobalsDict['BashINIPath'] = str(self.dirstring)

    def OnGetOBMMPath(self, event):
        self.OnGetFile(event, message='Locate your OblivionModManager.exe', wildcard='All files (*.exe*)|*.exe*')
        if self.pathstring != '':
            self.sOBMMPathsearchctrl.SetValue(self.pathstring)
            gGlobalsDict['OBMMPath'] = str(self.dirstring)

    def OnGetTranscendenceGamePath(self, event):
        self.OnGetFile(event, message='Locate your Transcendence.exe', wildcard='All files (*.exe*)|*.exe*')
        if self.pathstring != '':
            self.sTranscendenceGamePathsearchctrl.SetValue(self.pathstring)
            gGlobalsDict['TranscendenceGamePath'] = str(self.dirstring)