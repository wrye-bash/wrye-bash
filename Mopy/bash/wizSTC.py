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

"""This module provides the majority of StyledTextCtrl(stc) stuff for the
Comments/WizBAIN Editor located in the Bash Installers(BAIN) Tab.

The module contains various functions for manipulating text such as many text
editors do. Most of the functions are aimed specifically toward the custom
wizard script language that was developed initially by LoJack for the
purpose of making mod installations easy.

This code originally was developed as a completely seperate application
(TES4WizBAIN (C) 2011, 2012) and is ported(WIPz)/authored mainly by Metallicow.

Time Line
1st Era - Wrye Developed BAIN
2nd Era - LoJack Developed The Wizard Scripting Language
3rd Era - Metallicow Developed The WizBAIN Editor
"""

# Imports ---------------------------------------------------------------------
#--Localization
#..Handled by bosh, so import that.
import bosh
import basher
import keywordWIZBAIN  # Keywords for BAIN Wizard stc
import keywordWIZBAIN2 # Keywords2 for BAIN Wizard stc

#--Python
import os
import re
import imp #stc python macros
import random
from collections import OrderedDict

#--wxPython
import wx
import wx.stc as stc
import wx.lib.platebtn as platebtn
import wx.lib.dialogs
from wx.lib.gestures import MouseGestures
import wx.lib.imagebrowser as ib #alternate to thumbnailer

#--User Macros(located outside of the bash dir)
from macro.py import *

# Font Stuff - defaults, etc
if wx.Platform == '__WXMSW__':
    # For Windows OS
    faces = {
            'times': 'Times New Roman',
            'mono' : 'Courier New',
            'helv' : 'Arial',
            'other': 'Comic Sans MS',
            'size' : 10,
            'size2': 8,
            }
elif wx.Platform == '__WXMAC__':
    # For Macintosh Apple OS
    faces = {
            'times': 'Times New Roman',
            'mono' : 'Monaco',
            'helv' : 'Arial',
            'other': 'Comic Sans MS',
            'size' : 10,
            'size2': 8,
            }
else:
    # For Whatever else OS. Changed per myk reqz
    faces = {
            'times': 'serif',       # 'times': 'Times',
            'mono' : 'monospace',   # 'mono' : 'Courier',
            'helv' : 'monospace',   # 'helv' : 'Helvetica',
            'other': 'sans',        # 'other': 'new century schoolbook',
            'size' : 10,
            'size2': 8,
             }

#--IDs
# When working with code, often the programmer uses numbers for ids.
# Typically this is fine if you have a small application, but as an
# application grows bigger and more badass it becomes a hassle to track
# down all these numbers, especially if there are multiple spots in the
# code using/calling these numbers for whatever reason.
# By defining all the IDs in one spot, this makes it easy to see where
# both the menu items ids and bindings are. This also helps keep the programmer
# from accidentily using the same ID twice, which if is the case, of course
# some poor user might report a BUG causing bugfixing duties on your part.
# Plus ID_SOMEWRYEBASHID is more readable and understandable than 18746 is for example.
# Also for whatever reasons, numbers here can be changed easily for orginization or
# other debugging purposes because a defined number is easier to track down than
# a randomly generated wx.NewId() which could potentially change every instance the app is run.

    # typicalexample = wx.MenuItem(rightclickmenu, 1234, u'&What the Heck is 1234', u' Can become apaininthearse')
    # menu.AppendItem(typicalexample)

    # ID_COOLFUNC = 1234
    # goodexample = wx.MenuItem(rightclickmenu, ID_COOLFUNC, u'&Do something cool!', u' ID_COOLFUNC... ummm. Oh yeah, now I remember what this does! :)')
    # menu.AppendItem(goodexample)

# TES4WizBAIN actually has a wx.menubar unlike Wrye Bash.
# Anywho here are my learned findings on the matter as a basic reference here also.
#-----------------------------------------
# Max ID number seems to be 65535 on wx2.8
# Max ID number seems to be 32766 on wx2.9.3.1 #seems to be cut in half
# 16-24 size icons for menuitems is fine. Anything larger will require hacking, espcially with radio/check and wx2.9
# ####x16 size icon for menuitem titlebar screws with the width of all menus. Again resort to hacking here. Worse to fix.
#-----------------------------------------

# ID_TEST = 0909

ID_RMGM1 = 3001
ID_RMGM2 = 3002
ID_RMGM3 = 3003
ID_RMGM4 = 3004
ID_RMGM5 = 3005
ID_RMGM6 = 3006
ID_RMGM7 = 3007
ID_RMGM8 = 3008
ID_RMGM9 = 3009

ID_RMGM2DRAG = 3012

ID_MMGM5 = 3025

ID_TOOLBAR =   5000
ID_UNDO =      5001
ID_REDO =      5002
ID_CUT =       5003
ID_COPY =      5004
ID_PASTE =     5005
ID_DELETE =    5006
ID_SELECTALL = 5007
ID_COMMENT =   5008
ID_REMTRAILWHITESPACE =  5009

ID_SAVEASPROJECTWIZARD = 5100

ID_HELPGENERAL =         5201
ID_HELPAPIDOCSTR =       5202
ID_TIPSINSTALLERS =      5211

ID_SORT =                1097
ID_FINDSELECTEDFORE =    1099

ID_REQVEROB =           2001
ID_REQVERSK =           2002
ID_SELECTONE =          2003
ID_SELECTMANY =         2004
ID_OPTIONS =            2005
ID_ENDSELECT =          2006
ID_CASE =               2007
ID_BREAK =              2008
ID_SELECTALLKW =        2009
ID_DESELECTALL =        2010
ID_SELECTSUBPACKAGE =   2011
ID_DESELECTSUBPACKAGE = 2012
ID_SELECTESPM =         2013
ID_DESELECTESPM =       2014
ID_SELECTALLESPMS =     2015
ID_DESELECTALLESPMS =   2016
ID_RENAMEESPM =         2017
ID_RESETESPMNAME =      2018
ID_RESETALLESPMNAMES =  2019
ID_DEFAULTCHAR =        2020
ID_DATAFILEEXISTS =     2021
ID_IFELIFELSEENDIF =    2022

ID_WIZARDIMAGES =       2090
ID_SCREENSHOTS =        2091
ID_LISTSUBPACKAGES =    2101
ID_LISTESPMS =          2102
ID_THUMBNAILER =        2191
ID_IMAGEBROWSER =       2192

ID_CALLTIP =      3097
ID_WORDCOMPLETE = 3098
ID_AUTOCOMPLETE = 3099

ID_UPPERCASE =   4001
ID_LOWERCASE =   4002
ID_INVERTCASE =  4003
ID_CAPITALCASE = 4004

ID_TXT2WIZSTRFILE = 6001
ID_TXT2WIZSTRTEXT = 6002

ID_NEWLINEBEFORE =          8001
ID_NEWLINEAFTER =           8002
ID_CUTLINE =                8003
ID_COPYLINE =               8004
ID_DELETELINE =             8005
ID_DELETELINECONTENTS =     8006
ID_SELECTLINENOEOL =        8007
ID_DUPLICATELINE =          8008
ID_DUPLICATESELECTIONLINE = 8009
ID_DUPLICATELINENTIMES =    8010
ID_JOINLINES =              8011
ID_SPLITLINES =             8012
ID_LINETRANSPOSE =          8013
ID_MOVELINEUP =             8014
ID_MOVELINEDOWN =           8015
ID_APPENDLINESSTR =         8016
ID_REMOVESTRENDLINES =      8017
ID_REMOVESTRSTARTLINES =    8018
ID_PADWITHSPACES =          8019

ID_TOGGLEWHITESPACE =    9001
ID_TOGGLEINDENTGUIDES =  9002
ID_TOGGLEWORDWRAP =      9003
ID_TOGGLELINEHIGHLIGHT = 9004
ID_TOGGLEEOLVIEW =       9005
ID_BACKSPACEUNINDENTS =  9006
ID_BRACECOMPLETION =     9007
ID_AUTOINDENTATION =     9008
ID_EDGECOLUMN =          9009

ID_THEMENONE =            9901
ID_THEMEDEFAULT =         9902
ID_THEMECONSOLE =         9903
ID_THEMEOBSIDIAN =        9904
ID_THEMEZENBURN =         9905
ID_THEMEMONOKAI =         9906
ID_THEMEDEEPSPACE =       9907
ID_THEMEGREENSIDEUP =     9908
ID_THEMETWILIGHT =        9909
ID_THEMEULIPAD =          9910
ID_THEMEHELLOKITTY =      9911
ID_THEMEVIBRANTINK =      9912
ID_THEMEBIRDSOFPARIDISE = 9913
ID_THEMEBLACKLIGHT =      9914
ID_THEMENOTEBOOK =        9915
ID_TOGGLETHEMES =         9930

class TextDropTargetForTextToWizardString(wx.TextDropTarget):
    ''' This object implements Drop Target functionality for Text '''
    def __init__(self, window):
        # Initialize the Drop Target, passing in the Object Reference to indicate what should receive the dropped text
        wx.TextDropTarget.__init__(self)
        # Store the Object Reference for dropped text
        self.window = window

    def OnDropText(self, x, y, text):
        ''' Implement Text Drop & Convert to a Wizard String '''
        # When text is dropped, write it into the object specified
        self.window.BeginUndoAction()

        self.window.ClearAll()# Delete the drag and drop into this window initial message or anything else.

        self.window.AddText(text)

        #------- Text to wizard string Conversion START ---------
        target = '\\'
        newtext = '\\\\'
        try:
            self.window.SetText(self.window.GetText().replace(target, newtext))  # Escape all Backslashes - Whole Doc
        except:
            self.window.SetTextUTF8(self.window.GetTextUTF8().replace(target, newtext))

        self.window.SelectAll()

        selectedtext = self.window.GetSelectedText()
        splitselectedtext = selectedtext.split('\n')
        length = len(splitselectedtext)

        for i in range(0,length,1):
            self.window.ReplaceSelection(' \\n' + splitselectedtext[i] + '\n')
        self.window.DeleteBack()

        totalnumlines = self.window.GetLineCount()

        for i in range(0,totalnumlines,1):
            self.window.GotoLine(i)
            self.window.Home()
            # self.window.AddText(' \\n')

            self.window.Home()
            self.window.DeleteBack()

        self.window.GotoLine(1)
        self.window.Home()
        self.window.GotoPos(3)
        for i in range(0,3): self.window.DeleteBack()

        target = '"'
        newtext = "''"
        try:
            self.window.SetText(self.window.GetText().replace(target, newtext))  # Convert " to '' - Whole Doc
        except:
            self.window.SetTextUTF8(self.window.GetTextUTF8().replace(target, newtext))

        self.window.SelectAll()
        selectedtext2 = self.window.GetSelectedText()

        self.window.SelectAll()
        self.window.DeleteBack()
        self.window.SetFocus()

        self.window.AddText('Mod_Readme = str("' + selectedtext2 + '")')
        self.window.StyleSetBackground(style=stc.STC_STYLE_DEFAULT, back='#CFFFCC')

        self.window.EndUndoAction()
        #------- Text to wizard string Conversion END -----------

class FileDropTargetForTextToWizardString(wx.FileDropTarget):
    ''' This object implements Drop Target functionality for Files '''
    def __init__(self, window):
        ''' Initialize the Drop Target, passing in the Object Reference to indicate what should receive the dropped file '''
        wx.FileDropTarget.__init__(self)
        self.window = window

    def OnDropFiles(self, x, y, filenames):
        ''' Implement File Drop & Convert to a Wizard String '''
        for name in filenames:
            try:
                self.window.BeginUndoAction()

                self.window.ClearAll()# Delete the drag and drop into this window initial message or anything else.

                textfile = open(name, 'r')
                text = textfile.read()
                self.window.AddText(text)
                textfile.close()
                #------- Text to wizard string Conversion START ---------
                target = '\\'
                newtext = '\\\\'
                try:
                    self.window.SetText(self.window.GetText().replace(target, newtext))  # Escape all Backslashes - Whole Doc
                except:
                    self.window.SetTextUTF8(self.window.GetTextUTF8().replace(target, newtext))

                self.window.SelectAll()

                selectedtext = self.window.GetSelectedText()
                splitselectedtext = selectedtext.split('\n')
                length = len(splitselectedtext)

                for i in range(0,length,1):
                    self.window.ReplaceSelection(' \\n' + splitselectedtext[i] + '\n')
                self.window.DeleteBack()

                totalnumlines = self.window.GetLineCount()

                for i in range(0,totalnumlines,1):
                    self.window.GotoLine(i)
                    self.window.Home()

                    self.window.Home()
                    self.window.DeleteBack()

                self.window.GotoLine(1)
                self.window.Home()
                self.window.GotoPos(3)
                for i in range(0,3): self.window.DeleteBack()

                target = '"'
                newtext = "''"
                try:
                    self.window.SetText(self.window.GetText().replace(target, newtext))  # Convert " to '' - Whole Doc
                except:
                    self.window.SetTextUTF8(self.window.GetTextUTF8().replace(target, newtext))

                self.window.SelectAll()
                selectedtext2 = self.window.GetSelectedText()

                self.window.SelectAll()
                self.window.DeleteBack()
                self.window.SetFocus()

                #Prep wizstring basename and replace spaces with underscores for BAIN and/or UNIX compatability
                basename = os.path.basename(name)
                basename = basename[:basename.rfind('.')]
                basename = basename.replace(' ','_')
                self.window.AddText(basename + ' = str("' + selectedtext2 + '")')
                self.window.StyleSetBackground(style=stc.STC_STYLE_DEFAULT, back='#CFFFCC')

                self.window.EndUndoAction()
                #------- Text to wizard string Conversion END -----------
            except IOError, error:
                dialog = wx.MessageDialog(None, 'Error opening file\n' + str(error))
                dialog.ShowModal()
            except UnicodeDecodeError, error:
                dialog = wx.MessageDialog(None, 'Cannot open non ascii files\n' + str(error))
                dialog.ShowModal()

class TextToWizardStringSTC(stc.StyledTextCtrl):
    def __init__(self, parent):
        stc.StyledTextCtrl.__init__(self, parent, wx.ID_ANY)
        self.SetMarginWidth(1, 0)# This makes it look like just a simple textctrl.

        self.Bind(stc.EVT_STC_DO_DROP, self.OnDoDrop)
        self.Bind(stc.EVT_STC_DRAG_OVER, self.OnDragOver)

    def OnDragOver(self, event):
        event.SetDragResult(wx.DragNone)# Prevent dropping at the beginning of the buffer.

    def OnDoDrop(self, event):
        event.SetDragText(event.GetDragText())# Can change text if needed.


class WizBAINStyledTextCtrl(stc.StyledTextCtrl):
    def __init__(self, parent, ID):
        stc.StyledTextCtrl.__init__(self, parent, -1)

        global gWizSTC
        gWizSTC = self

        #--- Global STC Settings To Save ---#
        # Note to self. REMOVE gGlobalsDict stuff when settings dialog is implemented and users comfirm *Wow it works* and/or something didnt get forgotten.
        # converted most of gGlobals Dict to basher.settings['bash.installers.wizSTC.SETTING'] so far...
        # TODO:
        # 1. Implement color options also in settings dialog
        # BUGGISH ON STARTUP
        # 1. Review TES4WizBAIN Code to see how I fixed the startup folder marker code. IIRC there needed to be a call to change it after calling __init__ in basher.py. Not sure why it has to be this way...

        # global gGlobalsDict
        # gGlobalsDict = OrderedDict([
            # ('LoadSTCLexer' , 'wizbainlexer'),
            # ('ThemeOnStartup' , 'No Theme'),
            # ('FolderMarginStyle', 1),
            # ('ShowLineNumbersMargin', 1),
            # ('AutoAdjustLineMargin', 1),
            # ('CaretSpeed' , 0),
            # ('CaretPixelWidth' , 2),
            # ('CaretForegroundColor' , '#0000FF'),
            # ('CaretLineBackgroundAlpha', 100),
            # ('CaretLineVisible', 1),
            # ('WordWrap', 0),
            # ('TabsOrSpaces', 0),
            # ('IndentSize', 4),
            # ('TabWidth', 4),
            # ('IndentationGuides' , 1),
            # ('ViewWhiteSpace' , 1),
            # ('TabIndents' , 1),
            # ('BackSpaceUnIndents' , 0),
            # ('BraceCompletion' , 0),
            # ('AutoIndentation' , 0),
            # ('ReadOnly' , 0),
            # ('UseAntiAliasing' , 1),
            # ('UseBufferedDraw' , 1),
            # ('OvertypeOnOff' , 0),
            # ('ViewEOL' , 0),
            # ('LongLineEdge' , 80),
            # ('LineEdgeModeAsColumnMarker' , 0),
            # ('VertEditMode' , 0),
            # ('ScrollingPastLastLine' , 1),
            # ('SetLeftRightBlankMargins' , 0),
            # ('MouseGestureWobbleTolerance' , 500), #Hmmm need to figure out how this affects usage as in low/high number
            # ('UserCustomFontFace' , 'Magic Cards'),
            # ('ModdersHandle' , 'Metallicow'),
            # ])

        # print basher.settings['bash.installers.wizSTC.LoadSTCLexer']
        # print basher.settings['bash.installers.wizSTC.ThemeOnStartup']

        #--- Only One Instance Open ---#
        self.OneInstanceThumbnailer = 0
        self.OneInstanceImageBrowser = 0
        self.OneInstanceToolbar = 0
        self.dragmenu2 = 0

        #--- Images & Menu/ID Generation ---#
        self.imgDir = u'%s' %bosh.dirs['images']
        self.imgstcDir = u'%s' %bosh.dirs['images'].join('stc')
        p = wx.BITMAP_TYPE_PNG
        self.mgmImg = wx.Image(self.imgstcDir + os.sep + u'mousegesturemenu16.png',p).ConvertToBitmap()
        self.rmbImg = wx.Image(self.imgstcDir + os.sep + u'mousebuttonright16.png',p).ConvertToBitmap()
        self.mmbImg = wx.Image(self.imgstcDir + os.sep + u'mousebuttonmiddle16.png',p).ConvertToBitmap()
        self.yahImg = wx.Image(self.imgstcDir + os.sep + u'youarehere16.png',p).ConvertToBitmap()
        self.chkImg = wx.Image(self.imgstcDir + os.sep + u'check16.png',p).ConvertToBitmap()

        self.rmgmIDs = [ID_RMGM1,ID_RMGM2,ID_RMGM3,ID_RMGM4,ID_RMGM5,ID_RMGM6,ID_RMGM7,ID_RMGM8,ID_RMGM9]
        self.rmgmLABELs = [u'',u'Wizard',u'',u'Case',u'Right Clicky!',u'Conversion',u'Project Manipulation(NOT DONE)',u'Line Operations',u'Options',]

        #--- Lexers & Keywords ---#
        self.SetLexer(stc.STC_LEX_PYTHON)

        self.SetKeyWords(0, u' '.join(keywordWIZBAIN.kwlist))
        self.SetKeyWords(1, u' '.join(keywordWIZBAIN2.kwlist))

        #--- Misc or Todo(maybe) ---#
        self.SetEOLMode(stc.STC_EOL_LF) # UNIX
        self.SetBufferedDraw(basher.settings['bash.installers.wizSTC.UseBufferedDraw']) # If drawing is buffered then each line of text is drawn into a bitmap buffer before drawing it to the screen to avoid flicker.
        self.SetOvertype(basher.settings['bash.installers.wizSTC.OvertypeOnOff']) # Set to overtype (true) or insert mode.
        self.SetEndAtLastLine(basher.settings['bash.installers.wizSTC.ScrollingPastLastLine'])
        # #Todo# self.CmdKeyAssign(ord('C'), stc.STC_SCMOD_CTRL, stc.STC_CMD_UNDO) # Set a acellerator key to do something (Ctrl+Key)

        #--- Caret Options ---#
        self.SetCaretPeriod(basher.settings['bash.installers.wizSTC.CaretSpeed'])                  # Set the time in milliseconds that the caret is on and off. 0 = steady on.
        self.SetCaretForeground(basher.settings['bash.installers.wizSTC.CaretForegroundColor'])    # The color of the caret ; 'blue' or '#0000FF'
        self.SetCaretLineVisible(basher.settings['bash.installers.wizSTC.CaretLineVisible'])       # Default color should... be the same as the background unless SetCaretLineBackground is called to change its color. # Display the background of the line containing the caret in a different colour.
        self.SetCaretLineBackground(basher.settings['bash.installers.wizSTC.CaretLineBackground']) # Set the color of the background of the line containing the caret.(Currently selected line)
        ## self.SetCaretLineBackAlpha(basher.settings['bash.installers.wizSTC.CaretLineBackgroundAlpha']) # Set background alpha of the caret line. 0-255
        self.SetCaretWidth(basher.settings['bash.installers.wizSTC.CaretPixelWidth'])              # Set the width of the insert mode caret. 0 - 3 seems to be the max
        self.EnsureCaretVisible()                                            # Ensure the caret is visible.

        #--- Whitespace, Indentation, TAB, Properties, Indicator stuff ---#
        self.SetViewWhiteSpace(basher.settings['bash.installers.wizSTC.ViewWhiteSpace']) # Set to 0,1,or 2

        self.SetIndent(basher.settings['bash.installers.wizSTC.IndentSize'])                   # Proscribed indent size for wx
        self.SetIndentationGuides(basher.settings['bash.installers.wizSTC.IndentationGuides']) # To help beginners, show indent guides

        self.SetTabIndents(basher.settings['bash.installers.wizSTC.TabIndents']) # Tab key indents. Sets whether a tab pressed when caret is within indentation indents.
        self.SetBackSpaceUnIndents(basher.settings['bash.installers.wizSTC.BackSpaceUnIndents']) # Backspace unindents rather than delete 1 space. Sets whether a backspace pressed when caret is within indentation unindents.
        self.SetTabWidth(basher.settings['bash.installers.wizSTC.TabWidth'])    # Prescribed tab size for wx
        self.SetUseTabs(basher.settings['bash.installers.wizSTC.TabsOrSpaces']) # Use spaces rather than tabs, or TabTimmy will complain!

        self.SetProperty('fold', '1')
        self.SetProperty('tab.timmy.whinge.level', '1')
        self.SetProperty('fold.quotes.python', '1')
        self.SetProperty('fold.comment.python', '1')

        self.IndicatorSetStyle(1,1)
        self.IndicatorSetForeground(1,'#FF0000')

        self.SetEdgeColumn(basher.settings['bash.installers.wizSTC.LongLineEdge'])#Set the column number of the edge. If text goes past the edge then it is highlighted.
        self.SetEdgeMode(basher.settings['bash.installers.wizSTC.LongLineEdgeMode'])

        self.SetViewEOL(basher.settings['bash.installers.wizSTC.ViewEOL'])

        #--- Setup a margin to hold bookmarks ---#
        self.SetMarginType(1, stc.STC_MARGIN_SYMBOL)
        self.SetMarginSensitive(1, True)
        self.SetMarginWidth(1, 16)

        #--- Define the bookmark images ---#
        self.MarkerDefineBitmap(0, wx.Image(self.imgstcDir + os.sep + 'caretlinebm16.png', wx.BITMAP_TYPE_PNG).ConvertToBitmap())
        self.MarkerDefineBitmap(1, wx.Image(self.imgstcDir + os.sep + 'bookmark16.png', wx.BITMAP_TYPE_PNG).ConvertToBitmap())

        #--- Setup a margin to hold line numbers ---#
        self.SetMarginType(2, stc.STC_MARGIN_NUMBER)
        self.SetMarginWidth(2, 40)  #5 digits using a small mono font (40 pixels). Good up to 9999

        #--- Setup a margin to hold fold markers ---#
        ## self.SetFoldFlags(16)  ###  WHAT IS THIS VALUE?  WHAT ARE THE OTHER FLAGS?  DOES IT MATTER?
        self.SetMarginType(3, stc.STC_MARGIN_SYMBOL)
        self.SetMarginMask(3, stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(3, True)
        self.SetMarginWidth(3, 16)

        #--- Wordwrap ---#
        self.SetWrapMode(basher.settings['bash.installers.wizSTC.WordWrap'])
        self.SetWrapVisualFlags(1) #0 = off. 1 = wraparrow at right. 2 = wraparrow at left. 3 = wraparrow at left and right.
        self.SetWrapVisualFlagsLocation(stc.STC_WRAPVISUALFLAGLOC_DEFAULT) #Set the location of visual flags for wrapped lines. 0&2 = far right. 1&3 = EOL char at where the wrap starts on the right.

        #--- Set Global Styles ---#
        self.StyleClearAll()

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#000000,back:#FFFFFF,face:%(mono)s,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE, 'fore:#33FF33,back:#FF0000')
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,  'fore:#000000,back:#99AA99,face:%(mono)s,size:%(size2)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, 'fore:#000000,back:#FFFFFF,face:%(other)s' % faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,  'fore:#FF0000,back:#0000FF,bold')
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,    'fore:#000000,back:#FF0000,bold')

        #--- Set Python Styles ---#
        # default
        self.StyleSetSpec(stc.STC_P_DEFAULT,        'fore:#000000,back:#FFFFFF,face:%(mono)s,size:%(size)d' % faces)
        # comments
        self.StyleSetSpec(stc.STC_P_COMMENTLINE,    'fore:#007F00,back:#EAFFE9,face:%(mono)s,size:%(size)d' % faces)
        # number
        self.StyleSetSpec(stc.STC_P_NUMBER,         'fore:#FF0000,back:#FFFFFF,size:%(size)d' % faces)
        # string
        self.StyleSetSpec(stc.STC_P_STRING,         'fore:#FF8000,back:#FFFFFF,face:%(mono)s,size:%(size)d' % faces)
        # single quoted string
        self.StyleSetSpec(stc.STC_P_CHARACTER,      'fore:#FF8000,back:#FFFFFF,face:%(mono)s,size:%(size)d' % faces)
        # keyword
        self.StyleSetSpec(stc.STC_P_WORD,           'fore:#FF0000,back:#FFFFFF,face:%(mono)s,size:%(size)d' % faces)
        # keyword2
        self.StyleSetSpec(stc.STC_P_WORD2,          'fore:#6000FF,back:#FFFFFF,face:%(mono)s,size:%(size)d' % faces)
        # triple quotes
        self.StyleSetSpec(stc.STC_P_TRIPLE,         'fore:#000000,back:#FFF7EE,size:%(size)d' % faces)
        # triple double quotes
        self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,   'fore:#FF8000,back:#FFF7EE,size:%(size)d' % faces)
        # class name definition
        self.StyleSetSpec(stc.STC_P_CLASSNAME,      'fore:#0000FF,back:#FFFFFF,bold,underline,size:%(size)d' % faces)
        # function or method name definition
        self.StyleSetSpec(stc.STC_P_DEFNAME,        'fore:#007F7F,back:#FFFFFF,bold,size:%(size)d' % faces)
        # operators
        self.StyleSetSpec(stc.STC_P_OPERATOR,       'fore:#000000,back:#FFFFFF,bold,size:%(size)d' % faces)
        # identifiers
        self.StyleSetSpec(stc.STC_P_IDENTIFIER,     'fore:#000000,back:#FFFFFF,face:%(mono)s,size:%(size)d' % faces)
        # comment-blocks
        self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,   'fore:#7F7F7F,back:#F8FFF8,size:%(size)d' % faces)
        # end of line where string is not closed
        self.StyleSetSpec(stc.STC_P_STRINGEOL,      'fore:#000000,back:#E0C0E0,face:%(mono)s,eol,size:%(size)d' % faces)

        #--- Bind Events ---#
        self.Bind(stc.EVT_STC_MARGINCLICK,      self.OnMarginClick)
        self.Bind(wx.EVT_CONTEXT_MENU,          self.OnContextMenu)
        self.Bind(stc.EVT_STC_UPDATEUI,         self.OnUpdateUI)
        self.Bind(wx.EVT_KEY_DOWN,              self.OnKeyDown)
        self.Bind(wx.EVT_KEY_UP,                self.OnKeyUp)
        ## self.Bind(stc.EVT_STC_ZOOM,            self.OnSTCZoom)
        ## self.Bind(stc.EVT_STC_HOTSPOT_DCLICK,  self.OnHotSpotDClick)
        self.Bind(stc.EVT_STC_AUTOCOMP_SELECTION,  self.OnAutoCompSelection)

        # self.Bind(stc.EVT_STC_ROMODIFYATTEMPT,  self.OnReadOnlyModifyAttempt)
        self.Bind(wx.EVT_SET_FOCUS,             self.OnSTCGainFocus)
        self.Bind(wx.EVT_KILL_FOCUS,            self.OnSTCLoseFocus)
        # self.Bind(stc.EVT_STC_DWELLSTART,       self.OnMouseDwellStart)
        # self.Bind(stc.EVT_STC_DWELLEND,         self.OnMouseDwellEnd)

        #--- Brace Completion stuff ---#
        self.brace_dict={40:')',
                         91:']',
                         123:'}',
                         39:"'",
                         34:'"'}

        self.Bind(wx.stc.EVT_STC_CHARADDED, self.OnCharAdded) # When a character is added to the stc

        #--- Flags ---#
        self.autocompflag = 0 #Off by default

        #--- Macro Recording ---#
        ## self.Bind(stc.EVT_STC_MACRORECORD,  self.OnRecordingTheMacro)
        self.macrorecordingflag = 0 #Off by default
        ## self.macrostring = []

        #--- Register AutoComplete Images ---#
        self.RegisterImage(5, wx.Image(self.imgstcDir + os.sep + 'wizardhat16.png', wx.BITMAP_TYPE_PNG).ConvertToBitmap())

        #--- Mouse Gestures ---#
        ''' Mouse Gestures...Visualize your numpad and start drawing from 5 to an outside number. 9 possible events
        # [7][8][9]
        # [4][5][6]
        # [1][2][3] '''
        # rmouse
        self.rmousegesture = MouseGestures(self, Auto=True, MouseButton=wx.MOUSE_BTN_RIGHT)#wx.MOUSE_BTN_LEFT,wx.MOUSE_BTN_RIGHT
        self.rmousegesture.AddGesture('L', self.OnRMouseGestureMenu4, 'You moved left')
        self.rmousegesture.AddGesture('R', self.OnRMouseGestureMenu6, 'You moved right')
        self.rmousegesture.AddGesture('U', self.OnRMouseGestureMenu8, 'You moved up')
        self.rmousegesture.AddGesture('D', self.OnRMouseGestureMenu2, 'You moved down')
        # The diag gestures
        self.rmousegesture.AddGesture('1', self.OnRMouseGestureMenu1, 'You moved left/down  diag1')
        self.rmousegesture.AddGesture('3', self.OnRMouseGestureMenu3, 'You moved right/down diag3')
        self.rmousegesture.AddGesture('7', self.OnRMouseGestureMenu7, 'You moved left/up    diag7')
        self.rmousegesture.AddGesture('9', self.OnRMouseGestureMenu9, 'You moved right/up   diag9')
        self.rmousegesture.AddGesture('' , self.OnRMouseGestureMenuNone, 'Context Key/Right Mouse Context Menu')

        self.rmousegesture.SetGesturesVisible(True)
        self.rmousegesture.SetGesturePen(wx.Colour(230, 230, 76), 5)#(color, linepixelwidth)
        self.rmousegesture.SetWobbleTolerance(basher.settings['bash.installers.wizSTC.MouseGestureWobbleTolerance'])

        # mmouse
        self.mmousegesture = MouseGestures(self, Auto=True, MouseButton=wx.MOUSE_BTN_MIDDLE)
        self.mmousegesture.AddGesture('' , self.OnMMouseGestureMenuNone, 'Middle Mouse Context Menu')
        self.mmousegesture.SetGesturesVisible(True)
        self.mmousegesture.SetGesturePen(wx.Colour(255, 156, 0), 5)#Orange
        self.mmousegesture.SetWobbleTolerance(basher.settings['bash.installers.wizSTC.MouseGestureWobbleTolerance'])

        #--- Rectangular Selection ---#
        self.rect_selection_clipboard_flag = False #Set to false initially so that if upon open user tries to paste, it won't throw an error.

        #--- Set Theme ---#
        self.OnSetTheme(self)



        #--- NEEDS WORK ---#
        self.OnFolderMarginStyle4(self, '#FFFFFF', '#000000')#Hmmmm This is having problems changing correctly on startup again...
        self.OnSetFolderMarginStyle(self)#Hmmmm

    def OnSelectNone(self, event):
        ''' Select nothing in the document. (DeSelect) '''
        p = self.GetCurrentPos()
        self.SetSelection(p,p)

    def OnKeyUp(self, event):
        ''' The Auto-indentation Feature. '''
        key = event.GetKeyCode()
        if self.autocompflag == 1:
            self.autocompflag = 0
            pass #Word Completion or AutoCompletion is open
        elif event.ControlDown() and key == 87 or event.ControlDown() and key == wx.WXK_RETURN:#87 = W
        # # if self.AutoCompActive():
            pass #pre Word Completion
        elif key == wx.WXK_NUMPAD_ENTER or key == wx.WXK_RETURN:
            if self.macrorecordingflag == 1:
                pass
            elif basher.settings['bash.installers.wizSTC.AutoIndentation'] == 1:
                try:
                    self.BeginUndoAction()
                    line = self.GetCurrentLine()
                    linecontents = self.GetLine(self.GetCurrentLine())
                    # print ('AutoIndentNoSelection: Line:' + str(line) + '\n' + 'PrevLineIndent:' + str(self.GetLineIndentation(line - 1)))
                    if line != '':
                        if self.GetCharAt(self.GetLineIndentPosition(line - 1)) == 10 or 13:
                            self.SetLineIndentation(line, self.GetLineIndentation(line - 1))
                        # print('LineContents:' + str(self.GetLine(self.GetCurrentLine())))
                        # print('LF or CR This Line Is Not Empty. Do not SetLineIndentation')
                    else:
                        self.SetLineIndentation(line, self.GetLineIndentation(line - 1))

                    if basher.settings['bash.installers.wizSTC.TabsOrSpaces'] == 0: self.GotoPos(self.GetCurrentPos() + self.GetLineIndentation(line - 1)) #Spaces
                    elif basher.settings['bash.installers.wizSTC.TabsOrSpaces'] == 1: self.GotoPos(self.GetCurrentPos() + self.GetLineIndentation(line - 1)/self.GetIndent()) #TABS
                    self.EndUndoAction()
                except: pass

    def OnKeyDown(self, event):
        ''' Event occurs when a key is pressed down. '''
        if self.CallTipActive():
            self.CallTipCancel()
        if self.autocompflag == 1:
            self.autocompflag = 0
        key = event.GetKeyCode()
        # print (key)
        event.Skip()#Removing this line will cause the keyboard to NOT function properly!

        # Handle the Non-STC Standard Keyboard Accelerators Here since wtf, there is no wx.Menu.
        if key == 27: self.OnSelectNone(event) #Escape doesn't like accelerators on windows for some reason...

        if event.ControlDown() and key == 32:
            if event.ShiftDown():#Ctrl+Shift+Space
                self.OnShowSelectedTextCallTip(event)
            else:#Ctrl+Space
                self.OnShowAutoCompleteBox(event)

        if   event.ControlDown() and key == 48 or key == 324:#Ctrl+0 or NUMPad0
            self.OnMMouseGestureMenuNone(event)
        elif event.ControlDown() and key == 49 or key == 325:#Ctrl+1 or NUMPad1
            self.OnRMouseGestureMenu1(event)
        elif event.ControlDown() and key == 50 or key == 326:#Ctrl+2 or NUMPad2
            self.OnRMouseGestureMenu2(event)
        elif event.ControlDown() and key == 51 or key == 327:#Ctrl+3 or NUMPad3
            self.OnRMouseGestureMenu3(event)
        elif event.ControlDown() and key == 52 or key == 328:#Ctrl+4 or NUMPad4
            self.OnRMouseGestureMenu4(event)
        elif event.ControlDown() and key == 53 or key == 329:#Ctrl+5 or NUMPad5
            self.OnRMouseGestureMenuNone(event)
        elif event.ControlDown() and key == 54 or key == 330:#Ctrl+6 or NUMPad6
            self.OnRMouseGestureMenu6(event)
        elif event.ControlDown() and key == 55 or key == 331:#Ctrl+7 or NUMPad7
            self.OnRMouseGestureMenu7(event)
        elif event.ControlDown() and key == 56 or key == 332:#Ctrl+8 or NUMPad8
            self.OnRMouseGestureMenu8(event)
        elif event.ControlDown() and key == 57 or key == 333:#Ctrl+9 or NUMPad9
            self.OnRMouseGestureMenu9(event)

        if event.ControlDown() and key == 67:#Ctrl+C
            self.OnCopy(event)

        if event.ControlDown() and key == 81:#Ctrl+Q
            self.OnToggleComment(event)

        if event.ControlDown() and key == 86:#Ctrl+V
            self.OnPaste(event)

        if event.ControlDown() and key == 87:#Ctrl+W
            self.OnShowWordCompleteBox(event)

        if event.ControlDown() and event.ShiftDown() and key == 315:#Ctrl+Shift+Up
            self.OnMoveLineUp(event)

        if event.ControlDown() and event.ShiftDown() and key == 317:#Ctrl+Shift+Down
            self.OnMoveLineDown(event)

        if key == 343:#F4
            self.OnFindSelectedForwards(event)

        if key == 351:#F12
            self.OnToggleEditorThemes(event)

        #--- Auto-Adjust linenumber margin width ---#
        if basher.settings['bash.installers.wizSTC.ShowLineNumbersMargin'] == 1:
            if basher.settings['bash.installers.wizSTC.AutoAdjustLineMargin'] == 1:
                totallines = self.GetLineCount()
                if totallines < 99:
                    self.SetMarginWidth(2, 22) #3 digits using a small mono font (22 pixels). Good up to 99
                elif totallines < 999:
                    self.SetMarginWidth(2, 30) #4 digits using a small mono font (30 pixels). Good up to 999
                elif totallines < 9999:
                    self.SetMarginWidth(2, 40) #5 digits using a small mono font (40 pixels). Good up to 9999

    def OnUpdateUI(self, event):
        ''' If the text, the styling, or the selection has been changed, This is bound by stc.EVT_STC_UPDATEUI above.
            Used to update any GUI elements that should change as a result. Also for other tasks that can be performed using background processing. '''

        ''' Responsible for the bad brace check feature. '''
        #--- Check for matching braces ---#
        braceatcaret = -1
        braceopposite = -1
        charbefore = None
        caretpos = self.GetCurrentPos()
        if caretpos > 0:
            charbefore = self.GetCharAt(caretpos - 1)
            styleBefore = self.GetStyleAt(caretpos - 1)
        # Check before
        if charbefore and chr(charbefore) in '[]{}()'\
                and styleBefore == stc.STC_P_OPERATOR:
            braceatcaret = caretpos - 1
        # Check after
        if braceatcaret < 0:
            charafter = self.GetCharAt(caretpos)
            styleafter = self.GetStyleAt(caretpos)

            if charafter and chr(charafter) in '[]{}()'\
                    and styleafter == stc.STC_P_OPERATOR:
                braceatcaret = caretpos
        if braceatcaret >= 0:
            braceopposite = self.BraceMatch(braceatcaret)
        if braceatcaret != -1  and braceopposite == -1:
            self.BraceBadLight(braceatcaret)
        else:
            self.BraceHighlight(braceatcaret, braceopposite)

        #--- Caret Line Margin ---#
        lineclicked = self.LineFromPosition(event.GetPosition())
        linecount = self.GetLineCount()
        for i in range(0,linecount+1):
            self.MarkerDelete(i, 0)
        self.MarkerAdd(self.GetCurrentLine(), 0)

    def OnMarginClick(self, event):
        ''' Event occurs when the bookmark, line or code fold margins are clicked. '''
        #-- Fold and unfold as needed --#
        if event.GetMargin() == 3:
            if event.GetShift() and event.GetControl():
                self.OnFoldAll()
            else:
                lineClicked = self.LineFromPosition(event.GetPosition())
                if self.GetFoldLevel(lineClicked) &\
                        stc.STC_FOLDLEVELHEADERFLAG:
                    if event.GetShift():
                        self.SetFoldexpanded(lineClicked, True)
                        self.OnExpand(lineClicked, True, True, 1)
                    elif event.GetControl():
                        if self.GetFoldexpanded(lineClicked):
                            self.SetFoldexpanded(lineClicked, False)
                            self.OnExpand(lineClicked, False, True, 0)
                        else:
                            self.SetFoldexpanded(lineClicked, True)
                            self.OnExpand(lineClicked, True, True, 100)
                    else:
                        self.ToggleFold(lineClicked)
        #--- Bookmark Margin ---#
        if event.GetMargin() == 1:
            lineClicked = self.LineFromPosition(event.GetPosition())
            if self.MarkerGet(lineClicked):
                self.MarkerDelete(lineClicked, 1)
            else:
                self.MarkerAdd(lineClicked, 1)

    def OnFoldAll(self):
        ''' Folding folds, marker - to + '''
        lineCount = self.GetLineCount()
        expanding = True
        # Find out if folding or unfolding
        for lineNum in range(lineCount):
            if self.GetFoldLevel(lineNum) &\
                    stc.STC_FOLDLEVELHEADERFLAG:
                expanding = not self.GetFoldExpanded(lineNum)
                break;
        lineNum = 0
        while lineNum < lineCount:
            level = self.GetFoldLevel(lineNum)
            if level & stc.STC_FOLDLEVELHEADERFLAG and \
               (level & stc.STC_FOLDLEVELNUMBERMASK) ==\
                    stc.STC_FOLDLEVELBASE:
                if expanding:
                    self.SetFoldExpanded(lineNum, True)
                    lineNum = self.OnExpand(lineNum, True)
                    lineNum = lineNum - 1
                else:
                    lastChild = self.GetLastChild(lineNum, -1)
                    self.SetFoldExpanded(lineNum, False)
                    if lastChild > lineNum:
                        self.HideLines(lineNum+1, lastChild)
            lineNum = lineNum + 1

    def OnExpand(self, line, doexpand, force=False, visLevels=0, level=-1):
        ''' Expanding folds, marker + to - '''
        lastChild = self.GetLastChild(line, level)
        line = line + 1
        while line <= lastChild:
            if force:
                if visLevels > 0:
                    self.ShowLines(line, line)
                else:
                    self.HideLines(line, line)
            else:
                if doexpand:
                    self.ShowLines(line, line)
            if level == -1:
                level = self.GetFoldLevel(line)
            if level & stc.STC_FOLDLEVELHEADERFLAG:
                if force:
                    if visLevels > 1:
                        self.SetFoldexpanded(line, True)
                    else:
                        self.SetFoldexpanded(line, False)
                    line = self.OnExpand(line, doexpand, force, visLevels-1)
                else:
                    if doexpand and self.GetFoldexpanded(line):
                        line = self.OnExpand(line, True, force, visLevels-1)
                    else:
                        line = self.OnExpand(line, False, force, visLevels-1)
            else:
                line = line + 1;
        return line

    def OnCharAdded(self, event):
        ''' Brace Completion. If the feature is enabled, it adds a closing brace at the current caret/cursor position. '''
        key = event.GetKey()
        # print key
        if basher.settings['bash.installers.wizSTC.BraceCompletion'] == 1:
            if key in [40,91,123,39,34]: #These numbers are the keycodes of the braces defined above: ( [ { ' " (the first half of them)
                self.AddText(self.brace_dict[key])
                self.CharLeft()

    def OnSelectAll(self, event):
        ''' Select all of the text in the document. '''
        self.SelectAll()

    def OnUndo(self,event):
        ''' Undo one action in the undo history. '''
        if self.CanUndo() == 1:
            self.Undo()

    def OnRedo(self,event):
        ''' Redoes the next action on the undo history. '''
        if self.CanRedo() == 1:
            self.Redo()

    def OnCut(self, event):
        ''' Cut the selection to the clipboard and explicitly set the rect_selection_clipboard_flag for each pass. '''
        if self.SelectionIsRectangle():
            self.rect_selection_clipboard_flag = True
            # print ('rect_selection_clipboard_flag = True')
        else:
            self.rect_selection_clipboard_flag = False
            # print ('rect_selection_clipboard_flag = False')
        self.Cut()

    def OnCopy(self, event):
        ''' Copy the selection to the clipboard and explicitly set the rect_selection_clipboard_flag for each pass. '''
        if self.SelectionIsRectangle():
            self.rect_selection_clipboard_flag = True
            # print ('rect_selection_clipboard_flag = True')
        else:
            self.rect_selection_clipboard_flag = False
            # print ('rect_selection_clipboard_flag = False')
        self.Copy()
        # print ('OnCopy')

    def OnCopyAll(self, event):
        ''' Copy all of the text in the document to the clipboard. '''
        self.SelectAll()
        self.Copy()

    def OnPaste(self, event):
        ''' Paste the contents of the clipboard into the document replacing the selection.
        or Override CmdKeyExecute if the rect_selection_clipboard_flag is set. '''
        if self.CanPaste() == 1: #Will a paste succeed? 1 For Yes, 0 for No.
            if self.rect_selection_clipboard_flag:
                self.OnColumnPaste(event)
            else:
                self.Paste() # or self.CmdKeyExecute(stc.STC_CMD_PASTE)
                wx.CallAfter(self.Undo)#Wrye Bash Port HACK: Because... No wx.Menu RectSelection HACK , Don't paste twice;rectangular then regular, just rectangular
        elif self.CanPaste() == 0:
            wx.Bell()
            # print ('This Paste can\'t succeed.')

    def OnColumnPaste(self, event):
        ''' Paste text into the document in a rectangular or columnar fashion. '''
        if self.rect_selection_clipboard_flag:
            self.BeginUndoAction()
            data_obj = wx.TextDataObject() # Create the data object we'll use to store the clipboard data.
            wx.TheClipboard.Open()
            if wx.TheClipboard.GetData(data_obj): # Continue only if there's data in the clipboard...
                if self.SelectionIsRectangle():
                    self.DeleteBackNotLine() # Delete what is selected before rectangular/column pasting.
                text = data_obj.GetText() # Get the text from the clipboard.
                ind = 0
                pos = self.GetCurrentPos()
                oldpos = pos
                line = self.GetCurrentLine()
                col = self.GetColumn(self.GetCurrentPos())
                while text.find('\n', ind) != -1:
                        newind = text.find('\n', ind)
                        self.AddText(text[ind:newind - 1])
                        self.GotoPos(pos)
                        self.LineDown() #or self.CmdKeyExecute (wx.stc.STC_CMD_LINEDOWN)
                        pos = self.GetCurrentPos()
                        line += 1
                        ind = newind + 1
                self.GotoPos(oldpos) # Move the caret back to original start pos.
            wx.TheClipboard.Close()
            self.EndUndoAction()
        wx.CallAfter(self.Undo)#Wrye Bash Port HACK: Because... No wx.Menu RectSelection HACK , Don't paste twice;rectangular then regular, just rectangular
        # print('OnColumnPaste')

    def OnDelete(self, event):
        ''' Clear the selection. '''
        self.Clear()

    def OnRemoveTrailingWhitespace(self, event):
        '''Eliminates/Removes all trailing/extra whitespace characters from the end of each line in the whole document.'''
        self.BeginUndoAction()
        curline = self.GetCurrentLine()
        firstvisline = self.GetFirstVisibleLine()
        endofdoc = self.GetLength()

        stripedlist = []
        for line in range(0, self.GetLineCount()):
            linetext = self.GetLine(line)
            striped = linetext.rstrip()
            stripedlist.append(striped)

        self.ClearAll()
        totallines = len(stripedlist)
        count = 0
        for stripedline in stripedlist:
            count += 1
            if count == totallines:#lastline don't add extra newline
                self.AppendText(stripedline)
            elif stripedline == '':
                self.AppendText('\n')
            else:
                self.AppendText(stripedline + '\n')

        self.GotoLine(curline)
        secondvisline = self.GetFirstVisibleLine()
        # Retain the topline & line of the doc before striping
        for i in range(0, (firstvisline - secondvisline)):
            self.LineScrollDown()
        self.EndUndoAction()

    def OnSaveAsProjectsWizard(self, event):
        ''' Save the current document text to the current project's directory as its wizard script. '''
        self.ConvertEOLs(2)#Unix. LF. Fix for Mixed EOL problem
        try:
            dir = basher.gInstallers.data.dir
            packagename = basher.gInstallers.gPackage.GetValue()
            # print dir
            # print packagename

            projectpath = u'%s%s%s' %(dir, os.sep, packagename)
            wizpath = u'%s%s%s%swizard.txt' %(dir, os.sep, packagename, os.sep)
            # print wizpath

            if packagename == '':#Don't save the wizard in the Bash Installers dir
                wx.MessageBox(u'Select a package first!', u'ERROR', wx.ICON_ERROR | wx.OK)
                wx.Bell()
            elif packagename.startswith(u'==') and packagename.endswith(u'=='):
                if not os.path.exists(projectpath):
                    wx.MessageBox(u'You can\'t save a wizard to a marker', u'ERROR', wx.ICON_ERROR | wx.OK)
                    wx.Bell()
                else:
                    somefile = open(wizpath, 'w')
                    somefile.write(self.GetTextUTF8())
                    # print ('Saved Document.')
                    somefile.close()
                    # self.SetSavePoint() #Don't use this here. If user immediately clicks on another package afterwards, infos won't get saved as this resets the Modify Flag.
            elif os.path.exists(projectpath):
                somefile = open(wizpath, 'w')
                somefile.write(self.GetTextUTF8())
                # print ('Saved Document.')
                somefile.close()
                # self.SetSavePoint() #Don't use this here. If user immediately clicks on another package afterwards, infos won't get saved as this resets the Modify Flag.
        except:
            wx.MessageBox(u'Error in saving file.', u'ERROR', wx.ICON_ERROR | wx.OK)
            wx.Bell()

    def OnTextToWizardStringFileDropMiniFrame(self, event):
        ''' Call the TextToWizardString(FileDrop) convertor floating miniframe. '''
        texttowizardstringminiframe = wx.MiniFrame(self, -1, u'Text To Wizard String (File Drop)', style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT, size=(300, 150))

        texttowizardstringminiframe.SetSizeHints(200,150)

        texttowizardstringminiframe.textctrl1 = TextToWizardStringSTC(texttowizardstringminiframe)
        msg = u'Drag & Drop the textfile into this miniframe. \nIt will automatically be converted to a wizard string! \nYou can then SelectAll, Cut, Paste it into the Editor. \nThis is useful for readmes, etc...'
        try:
            texttowizardstringminiframe.textctrl1.SetText(msg)
        except:
            texttowizardstringminiframe.textctrl1.SetTextUTF8(msg)
        texttowizardstringminiframe.textctrl1.EmptyUndoBuffer()

        #Drag and Drop - File Drop
        filedroptarget = FileDropTargetForTextToWizardString(texttowizardstringminiframe.textctrl1)
        texttowizardstringminiframe.textctrl1.SetDropTarget(filedroptarget)

        texttowizardstringminiframe.Centre()
        texttowizardstringminiframe.Show()

    def OnTextToWizardStringTextDropMiniFrame(self, event):
        ''' Call the TextToWizardString(TextDrop) convertor floating miniframe. '''
        texttowizardstringtextdropminiframe = wx.MiniFrame(self, -1, u'Text To Wizard String (Text Drop)', style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT, size=(300, 150))

        texttowizardstringtextdropminiframe.SetSizeHints(200,150)

        texttowizardstringtextdropminiframe.textctrl1 = TextToWizardStringSTC(texttowizardstringtextdropminiframe)
        msg = u'Drag & Drop some text into this miniframe. \nIt will automatically be converted to a wizard string! \nYou can then SelectAll, Cut, Paste it into the Editor. \nThis is useful for text from a web page, some of the editor text, etc...'
        try:
            texttowizardstringtextdropminiframe.textctrl1.SetText(msg)
        except:
            texttowizardstringtextdropminiframe.textctrl1.SetTextUTF8(msg)
        texttowizardstringtextdropminiframe.textctrl1.EmptyUndoBuffer()

        #Drag and Drop - Text Drop
        textdroptarget = TextDropTargetForTextToWizardString(texttowizardstringtextdropminiframe.textctrl1)
        texttowizardstringtextdropminiframe.textctrl1.SetDropTarget(textdroptarget)

        texttowizardstringtextdropminiframe.Centre()
        texttowizardstringtextdropminiframe.Show()

    def OnContextMenu(self, event):
        ''' This handles making the context key still work and a none mouse gesture pull up the context without poping up again after a different mouse gesture menu. '''
        pass
        # print ('This is handled by OnRMouseGestureMenuNone')

    def OnHelpWizBAINEditorGeneral(self, event):
        ''' Whoha and general propaganda from the TES4WizBAIN author who originally made this fine editor:
        Mooo, Metallicow, Metalio Bovinus. '''
        message = (
        u'The WizBAIN Editor is for mod authors and players to write fancy install scripts for their packages(called wizards),'\
        u'thus easing headaches and confusion during installation by all users. The Editor is primarily mouse gesture/context '\
        u'menu based and may not be obvious to a casual or first time user.\nThe mouse gesture menus are based off of a NUMPad, '\
        u'such as are on many keyboards. NUMPad 5 would be the default right or middle click context. To access the other menus '\
        u'just mouse gesture outward from 5 to another number. An example of how to open the right click mouse gesture 8 menu(R MGM 8) '\
        u'would be to first right click and hold the mouse button down and move your mouse forward/up and release.\n'\
        u'The WizBAIN Editor is currently a WIPz\n'\
        u'\n'\
        u'[7][8][9]\n'\
        u'[4][5][6]\n'\
        u'[1][2][3]\n'\
        u'\n'\
        u'\n'\
        u'Enjoy ~Metallicow, TES4WizBAIN Dev\n'
        )

        dialog = wx.lib.dialogs.ScrolledMessageDialog(self, message, u'WizBAIN Editor Help-General', size=(500, 350))
        dialog.SetIcon(wx.Icon(self.imgstcDir + os.sep + '..' + os.sep + 'help16.png', wx.BITMAP_TYPE_PNG))
        dialog.ShowModal()
        dialog.Destroy()

    def OnHelpWizBAINEditorAPIDocStrings(self, event):
        ''' Print the doctrings of the WizBAIN Editor functions for help. '''
        #Testing ATM - Python Version

        # text_file = open(u'%s' %bosh.dirs['bash'].join(u'wizSTC.py'), 'r')
        # str = text_file.read()
        # text_file.close()

        # findall = re.findall(r'def\s.*\(.*\):', str)

        # if findall:
            # print (findall)
        # else:
            # print ('did not find')

        functionlist = [self.OnHelpWizBAINEditorAPIDocStrings,self.OnSelectNone,self.OnKeyDown,self.OnUpdateUI,self.OnMarginClick,self.OnFoldAll,self.OnExpand,self.OnCharAdded,self.OnSelectAll,self.OnUndo,self.OnRedo,self.OnCut,self.OnCopy,self.OnCopyAll,self.OnPaste,self.OnColumnPaste,self.OnDelete,self.OnRemoveTrailingWhitespace,self.OnSaveAsProjectsWizard,self.OnTextToWizardStringFileDropMiniFrame,self.OnTextToWizardStringTextDropMiniFrame,self.OnContextMenu,self.OnHelpWizBAINEditorGeneral,self.OnToggleComment,self.OnUPPERCASE,self.Onlowercase,self.OnInvertCase,self.OnCapitalCase,self.OnMMouseGestureMenuNone,self.OnWriteUserTxtMacro,self.OnLoadModule,self.OnPythonMacro,self.OnRMouseGestureMenuNone,self.OnTestNewId,self.OnTest,self.OnRMouseGestureMenu1,self.OnSort,self.OnFindSelectedForwards,self.OnRMouseGestureMenu2,self.OnUseOnTopDraggableRMouseGestureMenu2,self.OnDefaultCharacterSelectedOptions,self.OnThumbnailerPackageWizardImages,self.OnThumbnailContextMenu,self.OnThumbnailWizImage,self.OnDialogDestroy,self.OnImageBrowserPackageWizardImages,self.OnWriteImageDirectoryIMAGE,self.OnWriteKeywordSUBNAMEorESPMNAME,self.OnWriteKeywordMODNAME,self.OnWriteListSubPackages,self.OnWriteListEspms,self.OnDeleteIfSelectedText,self.OnRequireVersionsOblivion,self.OnRequireVersionsSkyrim,self.OnSelectOne,self.OnSelectMany,self.OnChoicesX02,self.OnEndSelect,self.OnCase,self.OnBreak,self.OnSelectAllKeyword,self.OnDeSelectAll,self.OnSelectSubPackage,self.OnDeSelectSubPackage,self.OnSelectEspm,self.OnSelectAllEspms,self.OnDeSelectEspm,self.OnDeSelectAllEspms,self.OnRenameEspm,self.OnResetEspmName,self.OnResetAllEspmNames,self.OnWizardImages,self.OnRMouseGestureMenu3,self.OnShowSelectedTextCallTip,self.OnShowWordCompleteBox,self.OnShowAutoCompleteBox,self.OnRMouseGestureMenu4,self.OnRMouseGestureMenu6,self.OnRMouseGestureMenu7,self.OnRMouseGestureMenu8,self.OnNewLineBefore,self.OnNewLineAfter,self.OnLineCut,self.OnLineCopy,self.OnLineDelete,self.OnDeleteLineContents,self.OnLineSelect,self.OnLineDuplicate,self.OnLineDuplicateNTimes,self.OnDuplicateSelectionLine,self.OnLinesJoin,self.OnLinesSplit,self.OnLineTranspose,self.OnMoveLineUp,self.OnMoveLineDown,self.OnAppendSelectedLinesWithAString,self.OnRemoveStringFromEndOfSelectedLines,self.OnRemoveStringFromStartOfSelectedLines,self.OnPadWithSpacesSelectedLines,self.OnRMouseGestureMenu9,self.OnViewWhitespace,self.OnShowIndentationGuides,self.OnWordwrap,self.OnHighlightSelectedLine,self.OnShowEOL,self.OnSetFolderMarginStyle,self.OnFolderMarginStyle1,self.OnFolderMarginStyle2,self.OnFolderMarginStyle3,self.OnFolderMarginStyle4,self.OnFolderMarginStyle5,self.OnFolderMarginStyle6,self.OnSetTheme,self.OnToggleEditorThemes,self.OnNoTheme,self.OnDefaultTheme,self.OnConsoleTheme,self.OnObsidianTheme,self.OnZenburnTheme,self.OnMonokaiTheme,self.OnDeepSpaceTheme,self.OnGreenSideUpTheme,self.OnTwilightTheme,self.OnUliPadTheme,self.OnHelloKittyTheme,self.OnVibrantInkTheme,self.OnBirdsOfParidiseTheme,self.OnBlackLightTheme,self.OnNotebookTheme,]

        message = u''
        for function in functionlist:
            message += u'%s' %function.__name__ # ''' bla bla bla docstring '''
            message += u'\n'
            message += u'%s' %function.__doc__ # ''' bla bla bla docstring '''
            message += u'\n'
            message += u'\n'

        # import wizSTC
        # message += u'%s' %help(wizSTC)
        # message += u'%s' %dir(wizSTC)
        # message += u'%s' %dir('wizSTC')

        dialog = wx.lib.dialogs.ScrolledMessageDialog(self, u'%s' %message, u'WizBAIN Editor API Doc Strings', size=(500, 400))
        # dialog.SetFont(wx.Font(12, wx.DECORATIVE, wx.NORMAL, wx.NORMAL, False, u'%(mono)s' % faces))
        dialog.SetIcon(wx.Icon(self.imgstcDir + os.sep + '..' + os.sep + u'help16.png', wx.BITMAP_TYPE_PNG))
        dialog.ShowModal()
        dialog.Destroy()

    def OnToggleComment(self, event):
        ''' Toggle commenting on current or selected line(s) ==> ;# ini/pythonic colored comment.
        Commenting = semicolon(;) followed by a number sign/pound/hash(#) followed by a single whitespace( ).'''
        self.BeginUndoAction()
        selstart = self.GetSelectionStart()
        selend = self.GetSelectionEnd()
        line = self.LineFromPosition(self.GetCurrentPos())
        # print ('char1: ' + str(self.GetCharAt(self.GetLineIndentPosition(line))))

        if selstart == selend:
            # print('Nothing Selected - Toggle Comment Single Line')
            retainposafterwards = self.GetCurrentPos()
            if self.GetCharAt(self.GetLineIndentPosition(line)) == 10:
                pass
                # print ('line:' + str(line+1) + ' is blank LF') # char is LF EOL.
            elif self.GetCharAt(self.GetLineIndentPosition(line)) == 13:
                pass
                # print ('line:' + str(line+1) + ' is blank CR') # char is CR EOL.
            elif self.GetCharAt(self.GetLineIndentPosition(line)) == 0:
                pass
                # print ('line:' + str(line+1) + ' is blank nothing') # char is nothing. end of doc
            elif basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
                if self.GetCharAt(self.GetLineIndentPosition(line)) == 59: # char is ;
                    if self.GetCharAt(self.GetLineIndentPosition(line) + 1) == 35: # char is #
                        if self.GetCharAt(self.GetLineIndentPosition(line) + 2) == 32: # char is space
                            # print ('wizbain commented line')
                            self.GotoPos(self.GetLineIndentPosition(line) + 3)
                            for i in range(0,3):
                                self.DeleteBackNotLine()
                            self.GotoPos(retainposafterwards - 3)
                else:
                    self.GotoPos(self.GetLineIndentPosition(line))
                    self.AddText(u';# ')
                    self.GotoPos(retainposafterwards + 3)
        else:
            # print('Toggle Comment On Selected Lines')
            startline = self.LineFromPosition(selstart)
            endline = self.LineFromPosition(selend)
            for i in range(startline, endline + 1):
                # print ('line:' + str(i + 1) + ' ' + str(self.GetLine(i)))

                if self.GetCharAt(self.GetLineIndentPosition(i)) == 10:
                    pass
                    # print ('line:' + str(i+1) + ' is blank LF') # char is LF EOL.
                elif self.GetCharAt(self.GetLineIndentPosition(i)) == 13:
                    pass
                    # print ('line:' + str(i+1) + ' is blank CR') # char is CR EOL.
                elif self.GetCharAt(self.GetLineIndentPosition(i)) == 0:
                    pass
                    # print ('line:' + str(i+1) + ' is blank nothing') # char is nothing. end of doc
                elif basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
                    if self.GetCharAt(self.GetLineIndentPosition(i)) == 59: # char is ;
                        if self.GetCharAt(self.GetLineIndentPosition(i) + 1) == 35: # char is #
                            if self.GetCharAt(self.GetLineIndentPosition(i) + 2) == 32: # char is space
                                # print ('wizbain commented line')
                                self.GotoPos(self.GetLineIndentPosition(i) + 3)
                                for i in range(0,3):
                                    self.DeleteBackNotLine()
                                currentline = self.GetCurrentLine()
                                self.SetSelection(self.GetLineEndPosition(currentline),selstart)
                    else:
                        self.GotoPos(self.GetLineIndentPosition(i))
                        self.AddText(u';# ')

                        self.SetSelection(self.GetLineEndPosition(self.LineFromPosition(self.GetCurrentPos())),selstart)
                else:
                    print ('Huh')
        self.EndUndoAction()
        #print ('OnToggleComment might need some more work.')

    def OnUPPERCASE(self, event):
        '''Converts selection to UPPERCASE.'''
        self.UpperCase()
        #print ('OnUPPERCASE')

    def Onlowercase(self, event):
        '''Converts selection to lowercase.'''
        self.LowerCase()
        #print ('Onlowercase')

    def OnInvertCase(self, event):
        '''Inverts the case of the selected text.'''
        getsel = self.GetSelection()
        selectedtext = self.GetSelectedText()
        if len(selectedtext):
            self.BeginUndoAction()
            self.ReplaceSelection(selectedtext.swapcase())
            self.SetSelection(getsel[1],getsel[0])#Keep the text selected afterwards retaining caret pos
            self.EndUndoAction()
        #print ('OnInvertCase')

    def OnCapitalCase(self, event):
        '''Capitalizes the first letter of each word of the selected text.'''
        self.BeginUndoAction()
        self.Onlowercase(event)
        getsel = self.GetSelection()
        text = self.GetSelectedText()
        if len(text) > 0:
            s=[]
            word = False
            for character in text:
                if 'a' <= character.lower() <= 'z':
                    if word == False:
                        character = character.upper()
                        word = True
                else:
                    if word == True:
                        word = False
                s.append(character)
            text = ''.join(s)
            self.BeginUndoAction()
            self.ReplaceSelection(text)
            self.SetSelection(getsel[1],getsel[0])#Keep the text selected afterwards retaining caret pos
            self.EndUndoAction()
        self.EndUndoAction()
        #print ('OnCapitalCase')

    def OnMMouseGestureMenuNone(self, event):
        ''' Middle Clicky! Call the Middle Mouse Gesture Menu.
        NUMPAD:5
        [7][8][9]
        [4][@][6]
        [1][2][3]
        '''
        # print ('MMouse None')
        middleclickmenu = wx.Menu()

        p = wx.BITMAP_TYPE_PNG

        mcheader1 = wx.MenuItem(middleclickmenu, 0000, u'M MGM 5 Macro', u'ContextMenu5')
        mcheader1.SetBackgroundColour('#FF8800')
        middleclickmenu.AppendItem(mcheader1)
        mcheader1.SetDisabledBitmap(wx.Image(self.imgstcDir + os.sep + (u'mousebuttonmiddle16.png'),p).ConvertToBitmap())
        mcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            mgm = wx.MenuItem(middleclickmenu, self.rmgmIDs[i-1], u'&R MGM %s %s'%(str(i),self.rmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
            mgm.SetBitmap(self.mgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(middleclickmenu, ID_MMGM5, u'&M MGM 5 You Are Here!', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(self.yahImg)
        mgm.SetBackgroundColour('#F4FAB4')
        mgm.Enable(False)
        submenu.AppendItem(mgm)
        middleclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        middleclickmenu.AppendSeparator()

        macroTxtDir = bosh.dirs[u'mopy'].join(u'macro').join(u'txt')
        macroPyDir = bosh.dirs[u'mopy'].join(u'macro').join(u'py')

        for filename in os.listdir(u'%s' %macroTxtDir):
            if filename.endswith(u'.txt'):
                # print filename
                newid = wx.NewId()
                txtmacro = wx.MenuItem(middleclickmenu, newid, u'%s' %filename, u' Txt Macro')
                txtmacro.SetBitmap(wx.Image(self.imgstcDir + os.sep + ('file_txt16.png'),p).ConvertToBitmap())
                middleclickmenu.AppendItem(txtmacro)
                wx.EVT_MENU(middleclickmenu, newid, self.OnWriteUserTxtMacro)

        middleclickmenu.AppendSeparator()

        for filename in os.listdir(u'%s' %macroPyDir):
            if filename.endswith(u'.py'):
                # print filename
                if filename == '__init__.py':
                    pass
                else:
                    newid = wx.NewId()
                    pymacro = wx.MenuItem(middleclickmenu, newid, u'%s' %filename, u' Py Macro')
                    pymacro.SetBitmap(wx.Image(self.imgstcDir + os.sep + ('file_py16.png'),p).ConvertToBitmap())
                    middleclickmenu.AppendItem(pymacro)
                    wx.EVT_MENU(middleclickmenu, newid, self.OnPythonMacro)

        # events
        wx.EVT_MENU(middleclickmenu, ID_RMGM1, self.OnRMouseGestureMenu1)
        wx.EVT_MENU(middleclickmenu, ID_RMGM2, self.OnRMouseGestureMenu2)
        wx.EVT_MENU(middleclickmenu, ID_RMGM3, self.OnRMouseGestureMenu3)
        wx.EVT_MENU(middleclickmenu, ID_RMGM4, self.OnRMouseGestureMenu4)
        wx.EVT_MENU(middleclickmenu, ID_RMGM5, self.OnRMouseGestureMenuNone)
        wx.EVT_MENU(middleclickmenu, ID_RMGM6, self.OnRMouseGestureMenu6)
        wx.EVT_MENU(middleclickmenu, ID_RMGM7, self.OnRMouseGestureMenu7)
        wx.EVT_MENU(middleclickmenu, ID_RMGM8, self.OnRMouseGestureMenu8)
        wx.EVT_MENU(middleclickmenu, ID_RMGM9, self.OnRMouseGestureMenu9)

        wx.EVT_MENU(middleclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        self.PopupMenu(middleclickmenu)
        middleclickmenu.Destroy()

    def OnWriteUserTxtMacro(self, event):
        ''' Read the text file in and add it into the document at the caret. '''
        id =  event.GetId()
        # print event.GetId()
        # print event.GetEventObject()
        evtobj = event.GetEventObject()
        menuitem = evtobj.FindItemById(id)
        # print menuitem.GetItemLabel()

        usertxtmacro = bosh.dirs[u'mopy'].join(u'macro').join(u'txt').join(u'%s' %menuitem.GetItemLabel())

        macrotextfile = open(u'%s' %usertxtmacro, 'r')
        macro = macrotextfile.read()
        macrotextfile.close()
        self.AddText(macro + '\n')

    def OnLoadModule(self, name, filename):
        ''' Load a user python macro located in the 'mopy/macro/py' directory and return it as a new module. '''
        x = imp.new_module(filename)
        x.__file__ = filename
        x.__name__ = name
        x.__builtins__ = __builtins__
        execfile(filename, x.__dict__)
        return x

    def OnPythonMacro(self, event):
        ''' Execute the user python macro. Located in the 'mopy/macro/py' directory. '''
        id =  event.GetId()
        # print event.GetId()
        # print event.GetEventObject()
        evtobj = event.GetEventObject()
        menuitem = evtobj.FindItemById(id)
        # print menuitem.GetItemLabel()
        menulabel = menuitem.GetItemLabel()
        userpymacro = menulabel.rstrip(u'.py')

        filepath = bosh.dirs[u'mopy'].join(u'macro').join(u'py').join(u'%s' %menulabel)
        x = self.OnLoadModule(userpymacro, u'%s' %filepath)
        x.macro(self)

    def OnRMouseGestureMenuNone(self, event):
        ''' Right Clicky! Call the Right Mouse Gesture Menu.
        NUMPAD:5
        [7][8][9]
        [4][@][6]
        [1][2][3]
        '''
        rightclickmenu = wx.Menu()

        p = wx.BITMAP_TYPE_PNG

        rcheader1 = wx.MenuItem(rightclickmenu, 0000, u'R MGM 5', u'ContextMenu5')
        rcheader1.SetBackgroundColour('#000000')
        rightclickmenu.AppendItem(rcheader1)
        rcheader1.SetDisabledBitmap(self.rmbImg)
        rcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            if i == 5:#The currently open menu
                mgm = wx.MenuItem(rightclickmenu, self.rmgmIDs[i-1], u'&R MGM %s You Are Here!'%str(i), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(self.yahImg)
                mgm.SetBackgroundColour('#F4FAB4')
                mgm.Enable(False)
            else:
                mgm = wx.MenuItem(rightclickmenu, self.rmgmIDs[i-1], u'&R MGM %s %s'%(str(i),self.rmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(self.mgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(rightclickmenu, ID_MMGM5, u'&M MGM 5 Macro', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(self.mgmImg)
        submenu.AppendItem(mgm)
        rightclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        floatingtoolbar = wx.MenuItem(rightclickmenu, ID_TOOLBAR, u'&Use Floating Toolbar', u' Use Floating Toolbar')
        floatingtoolbar.SetBitmap(wx.Image(self.imgstcDir + os.sep + ('star16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(floatingtoolbar)
        if self.OneInstanceToolbar == 1:
            floatingtoolbar.Enable(False)

        rightclickmenu.AppendSeparator()

        undo = wx.MenuItem(rightclickmenu, ID_UNDO, u'&Undo\tCtrl+Z', u' Undo last modifications')
        undo.SetBitmap(wx.Image(self.imgstcDir + os.sep + ('undo16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(undo)
        if self.CanUndo() == 0:   undo.Enable(False)#trying to disable a menu item before it's appended to the menu doesn't work.
        elif self.CanUndo() == 1: undo.Enable(True)
        redo = wx.MenuItem(rightclickmenu, ID_REDO, u'&Redo\tCtrl+Y', u' Redo last modifications')
        redo.SetBitmap(wx.Image(self.imgstcDir + os.sep + ('redo16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(redo)
        if self.CanRedo() == 0:   redo.Enable(False)
        elif self.CanRedo() == 1: redo.Enable(True)
        rightclickmenu.AppendSeparator()
        cut = wx.MenuItem(rightclickmenu, ID_CUT, u'&Cut\tCtrl+X', u' Cut selected text')
        cut.SetBitmap(wx.Image(self.imgstcDir + os.sep + ('cut16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(cut)
        copy = wx.MenuItem(rightclickmenu, ID_COPY, u'&Copy\tCtrl+C', u' Copy selected text')
        copy.SetBitmap(wx.Image(self.imgstcDir + os.sep + ('copy16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(copy)
        paste = wx.MenuItem(rightclickmenu, ID_PASTE, u'&Paste\tCtrl+V', u' Paste from clipboard')
        paste.SetBitmap(wx.Image(self.imgstcDir + os.sep + ('paste16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(paste)
        if self.CanPaste() == 0:   paste.Enable(False)
        elif self.CanPaste() == 1: paste.Enable(True)
        delete = wx.MenuItem(rightclickmenu, ID_DELETE, u'&Delete', u' Delete selected text')
        delete.SetBitmap(wx.Image(self.imgstcDir + os.sep + ('delete16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(delete)
        rightclickmenu.AppendSeparator()
        selectall = wx.MenuItem(rightclickmenu, ID_SELECTALL, u'&Select All\tCtrl+A', u' Select All Text in Document')
        selectall.SetBitmap(wx.Image(self.imgstcDir + os.sep + ('selectall2416.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(selectall)

        rightclickmenu.AppendSeparator()

        togglecomment = wx.MenuItem(rightclickmenu, ID_COMMENT, u'&Toggle Comment\tCtrl+Q', u' Toggle Commenting on the selected line(s)')
        togglecomment.SetBitmap(wx.Image(self.imgstcDir + os.sep + ('togglecomment16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(togglecomment)

        removetrailingwhitespace = wx.MenuItem(rightclickmenu, ID_REMTRAILWHITESPACE, u'&Remove Trailing Whitespace', u' Remove trailing whitespace from end of lines in the document')
        removetrailingwhitespace.SetBitmap(wx.Image(self.imgstcDir + os.sep + ('removetrailingspaces16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(removetrailingwhitespace)

        rightclickmenu.AppendSeparator()

        submenu = wx.Menu()
        saveasprojectwizard = wx.MenuItem(rightclickmenu, ID_SAVEASPROJECTWIZARD, u'&Save as this project\'s wizard', u' Save as Project\'s wizard.txt')
        saveasprojectwizard.SetBitmap(wx.Image(self.imgstcDir + os.sep + ('save16.png'),p).ConvertToBitmap())
        submenu.AppendItem(saveasprojectwizard)
        rightclickmenu.AppendMenu(wx.NewId(), u'File', submenu)

        submenu = wx.Menu()
        helpwizbaineditorgeneral = wx.MenuItem(rightclickmenu, ID_HELPGENERAL, u'&WizBAIN Editor General', u' Help explaining general features')
        helpwizbaineditorgeneral.SetBitmap(wx.Image(self.imgDir + os.sep + (u'help16.png'),p).ConvertToBitmap())
        submenu.AppendItem(helpwizbaineditorgeneral)

        helpwizbaineditorgeneral = wx.MenuItem(rightclickmenu, ID_HELPAPIDOCSTR, u'&WizBAIN Editor API Doc Strings', u' Help explaining the function performed upon execution')
        helpwizbaineditorgeneral.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'python16.png'),p).ConvertToBitmap())
        submenu.AppendItem(helpwizbaineditorgeneral)

        installerstabtips = wx.MenuItem(rightclickmenu, ID_TIPSINSTALLERS, u'&Installers Tab Tips', u' Tnstallers Tab Tips')
        installerstabtips.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'lightbulb16.png'),p).ConvertToBitmap())
        submenu.AppendItem(installerstabtips)



        rightclickmenu.AppendMenu(wx.NewId(), u'Help', submenu)


        # testnewid = wx.NewId()
        # test = wx.MenuItem(rightclickmenu, testnewid, u'&Test wx.NewId()', u' For Testing Purposes')
        # test.SetBitmap(wx.Image(self.imgstcDir + os.sep + ('test16.png'),p).ConvertToBitmap())
        # wx.EVT_MENU(rightclickmenu, testnewid, self.OnTestNewId)
        # rightclickmenu.AppendItem(test)

        # test = wx.MenuItem(rightclickmenu, ID_TEST, u'&Test permanent defined ID: ID_TEST', u' For Testing Purposes')
        # test.SetBitmap(wx.Image(self.imgstcDir + os.sep + ('test16.png'),p).ConvertToBitmap())
        # rightclickmenu.AppendItem(test)

        #events
        # wx.EVT_MENU(rightclickmenu, ID_TEST, self.OnTest)

        wx.EVT_MENU(rightclickmenu, ID_TOOLBAR, self.OnShowFloatingToolbar)

        wx.EVT_MENU(rightclickmenu, ID_SAVEASPROJECTWIZARD, self.OnSaveAsProjectsWizard)

        wx.EVT_MENU(rightclickmenu, ID_HELPGENERAL, self.OnHelpWizBAINEditorGeneral)
        wx.EVT_MENU(rightclickmenu, ID_HELPAPIDOCSTR, self.OnHelpWizBAINEditorAPIDocStrings)
        wx.EVT_MENU(rightclickmenu, ID_TIPSINSTALLERS, self.OnShowInstallersTabTipsDialog)

        wx.EVT_MENU(rightclickmenu, ID_UNDO, self.OnUndo)
        wx.EVT_MENU(rightclickmenu, ID_REDO, self.OnRedo)
        wx.EVT_MENU(rightclickmenu, ID_CUT, self.OnCut)
        wx.EVT_MENU(rightclickmenu, ID_COPY, self.OnCopy)
        wx.EVT_MENU(rightclickmenu, ID_PASTE, self.OnPaste)
        wx.EVT_MENU(rightclickmenu, ID_DELETE, self.OnDelete)
        wx.EVT_MENU(rightclickmenu, ID_SELECTALL, self.OnSelectAll)
        wx.EVT_MENU(rightclickmenu, ID_COMMENT, self.OnToggleComment)
        wx.EVT_MENU(rightclickmenu, ID_REMTRAILWHITESPACE, self.OnRemoveTrailingWhitespace)

        wx.EVT_MENU(rightclickmenu, ID_RMGM1, self.OnRMouseGestureMenu1)
        wx.EVT_MENU(rightclickmenu, ID_RMGM2, self.OnRMouseGestureMenu2)
        wx.EVT_MENU(rightclickmenu, ID_RMGM3, self.OnRMouseGestureMenu3)
        wx.EVT_MENU(rightclickmenu, ID_RMGM4, self.OnRMouseGestureMenu4)
        wx.EVT_MENU(rightclickmenu, ID_RMGM5, self.OnRMouseGestureMenuNone)
        wx.EVT_MENU(rightclickmenu, ID_RMGM6, self.OnRMouseGestureMenu6)
        wx.EVT_MENU(rightclickmenu, ID_RMGM7, self.OnRMouseGestureMenu7)
        wx.EVT_MENU(rightclickmenu, ID_RMGM8, self.OnRMouseGestureMenu8)
        wx.EVT_MENU(rightclickmenu, ID_RMGM9, self.OnRMouseGestureMenu9)

        wx.EVT_MENU(rightclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        self.PopupMenu(rightclickmenu)
        rightclickmenu.Destroy()

    def OnTestNewId(self, event):
        print ('OnTestNewId - Everytime the menu is opened.')
        print (event.GetId())

    def OnTest(self, event):
        print ('OnTest')
        print ('ID_TEST')
        print (event.GetId())

    def OnShowFloatingToolbar(self, event):
        if self.OneInstanceToolbar == 0:
            customtoolbar = FloatingToolbar(self, -1)
            customtoolbar.Show()
            self.OneInstanceToolbar = 1

    def OnShowInstallersTabTipsDialog(self, event):
        customframe = InstallersTabTips(self, -1, 'Installers Tab Tips')
        customframe.Show()

    def OnRMouseGestureMenu1(self, event):
        ''' Call the Right Mouse Gesture Menu.
        NUMPAD:1
        [7][8][9]
        [4][5][6]
        [@][2][3]
        '''
        rightclickmenu = wx.Menu()

        p = wx.BITMAP_TYPE_PNG

        rcheader1 = wx.MenuItem(rightclickmenu, 0000, u'R MGM 1', u'ContextMenu1')
        rcheader1.SetBackgroundColour('#000000')
        rightclickmenu.AppendItem(rcheader1)
        rcheader1.SetDisabledBitmap(self.rmbImg)
        rcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            if i == 1:#The currently open menu
                mgm = wx.MenuItem(rightclickmenu, self.rmgmIDs[i-1], u'&R MGM %s You Are Here!'%str(i), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(self.yahImg)
                mgm.SetBackgroundColour('#F4FAB4')
                mgm.Enable(False)
            else:
                mgm = wx.MenuItem(rightclickmenu, self.rmgmIDs[i-1], u'&R MGM %s %s'%(str(i),self.rmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(self.mgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(rightclickmenu, ID_MMGM5, u'&M MGM 5 Macro', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(self.mgmImg)
        submenu.AppendItem(mgm)
        rightclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        rightclickmenu.AppendSeparator()

        sort = wx.MenuItem(rightclickmenu, ID_SORT, u'&Sort...', u' Sort selected lines in the active document')
        sort.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'sort16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(sort)

        findselectedforwards = wx.MenuItem(rightclickmenu, ID_FINDSELECTEDFORE, u'&Find Selected Forwards\tF4', u' Find selected text forwards')
        findselectedforwards.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'arrowdownbw16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(findselectedforwards)

        #events
        wx.EVT_MENU(rightclickmenu, ID_SORT, self.OnSort)
        wx.EVT_MENU(rightclickmenu, ID_FINDSELECTEDFORE, self.OnFindSelectedForwards)

        wx.EVT_MENU(rightclickmenu, ID_RMGM1, self.OnRMouseGestureMenu1)
        wx.EVT_MENU(rightclickmenu, ID_RMGM2, self.OnRMouseGestureMenu2)
        wx.EVT_MENU(rightclickmenu, ID_RMGM3, self.OnRMouseGestureMenu3)
        wx.EVT_MENU(rightclickmenu, ID_RMGM4, self.OnRMouseGestureMenu4)
        wx.EVT_MENU(rightclickmenu, ID_RMGM5, self.OnRMouseGestureMenuNone)
        wx.EVT_MENU(rightclickmenu, ID_RMGM6, self.OnRMouseGestureMenu6)
        wx.EVT_MENU(rightclickmenu, ID_RMGM7, self.OnRMouseGestureMenu7)
        wx.EVT_MENU(rightclickmenu, ID_RMGM8, self.OnRMouseGestureMenu8)
        wx.EVT_MENU(rightclickmenu, ID_RMGM9, self.OnRMouseGestureMenu9)

        wx.EVT_MENU(rightclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        self.PopupMenu(rightclickmenu)
        rightclickmenu.Destroy()

    def OnSort(self, event):
        ''' Call a dialog with various options to sort the selected text. '''
        self.BeginUndoAction()
        linestring = str(self.GetSelectedText())
        linestringlist = linestring.split('\n')
        length = len(linestringlist)

        if self.GetSelectionStart() == self.GetSelectionEnd():
            wx.MessageBox('No Text Selected!', 'Sort Error', wx.OK|wx.ICON_ERROR)
        else:
            dialog = wx.SingleChoiceDialog(self, "How do you want to sort the selection?", 'Sort...',
                    ['Ascending Case Sensitive', 'Ascending Case insensitive', 'Descending Case Sensitive', 'Descending Case insensitive', 'Randomly'],
                    wx.CHOICEDLG_STYLE)

            if dialog.ShowModal() == wx.ID_OK:
                getsel = self.GetSelection()
                if dialog.GetStringSelection() == 'Ascending Case Sensitive':
                    linestringlist.sort()
                    for i in range(0,length-1):
                        self.ReplaceSelection(linestringlist[i] + '\n')
                    self.ReplaceSelection(linestringlist[length-1])
                elif dialog.GetStringSelection() == 'Ascending Case insensitive':
                    linestringlist.sort(key=str.lower)
                    for i in range(0,length-1):
                        self.ReplaceSelection(linestringlist[i] + '\n')
                    self.ReplaceSelection(linestringlist[length-1])
                elif dialog.GetStringSelection() == 'Descending Case Sensitive':
                    linestringlist.sort()
                    linestringlist.reverse()
                    for i in range(0,length-1):
                        self.ReplaceSelection(linestringlist[i] + '\n')
                    self.ReplaceSelection(linestringlist[length-1])
                elif dialog.GetStringSelection() == 'Descending Case insensitive':
                    linestringlist.sort(key=str.lower)
                    linestringlist.reverse()
                    for i in range(0,length-1):
                        self.ReplaceSelection(linestringlist[i] + '\n')
                    self.ReplaceSelection(linestringlist[length-1])
                elif dialog.GetStringSelection() == 'Randomly':
                    r = []
                    for i in range(self.LineFromPosition(self.GetSelectionStart()),self.LineFromPosition(self.GetSelectionEnd()) + 1):
                        r.append(self.GetLine(i).rstrip())
                    random.shuffle(r)
                    self.DeleteBack()
                    for line in r:
                        self.AddText(line + '\n')
                    self.DeleteBack()
                self.SetSelection(getsel[1],getsel[0])#Keep the text selected afterwards retaining caret pos

            dialog.Destroy()
        self.EndUndoAction()

    def OnFindSelectedForwards(self, event):
        ''' Attempt to find the selected text further along in the document. Wraparound '''
        if self.GetSelectionStart() == self.GetSelectionEnd():
            pass
        else:
            try:
                val = self.GetSelectedText()
            except:
                val = self.GetSelectedTextUTF8()

            curpos = self.GetCurrentPos()
            findstring = self.FindText(curpos, self.GetLength(), val, flags=1)
            # print ('QF findstring = ' + str(findstring))

            if findstring != -1:
                self.GotoPos(findstring)
                self.SetSelection(findstring, findstring + len(val))
            else:
                try:
                    findstring = self.FindText(0, self.GetLength(), val, flags=1)
                    if findstring != -1:
                        self.GotoPos(findstring)
                        self.SetSelection(findstring, findstring + len(val))
                    else: wx.Bell()
                except:
                    pass#print ('Quick Find String Not Found')


    def OnRMouseGestureMenu2(self, event):
        ''' Call the Right Mouse Gesture Menu.
        NUMPAD:2
        [7][8][9]
        [4][5][6]
        [1][@][3]
        '''
        rightclickmenu = wx.Menu()

        p = wx.BITMAP_TYPE_PNG

        rcheader1 = wx.MenuItem(rightclickmenu, 0000, u'R MGM 2 Wizard', u'ContextMenu2')
        rcheader1.SetBackgroundColour('#000000')
        rightclickmenu.AppendItem(rcheader1)
        rcheader1.SetDisabledBitmap(self.rmbImg)
        rcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            if i == 2:#The currently open menu
                mgm = wx.MenuItem(rightclickmenu, self.rmgmIDs[i-1], u'&R MGM %s You Are Here!'%str(i), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(self.yahImg)
                mgm.SetBackgroundColour('#F4FAB4')
                mgm.Enable(False)
            else:
                mgm = wx.MenuItem(rightclickmenu, self.rmgmIDs[i-1], u'&R MGM %s %s'%(str(i),self.rmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(self.mgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(rightclickmenu, ID_MMGM5, u'&M MGM 5 Macro', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(self.mgmImg)
        submenu.AppendItem(mgm)
        rightclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        ontopdragmenu = wx.MenuItem(rightclickmenu, ID_RMGM2DRAG, u'&Use OnTop Draggable Menu', u' Use OnTop Draggable Menu')
        ontopdragmenu.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'star16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(ontopdragmenu)
        if self.dragmenu2 == 1: ontopdragmenu.Enable(False)

        rightclickmenu.AppendSeparator()

        mSubListCount = basher.gInstallers.gSubList.GetCount()
        mEspmListCount = basher.gInstallers.gEspmList.GetCount()

        reqversky = wx.MenuItem(rightclickmenu, ID_REQVEROB, u'&RequireVersions Oblivion', u' RequireVersions "1.2.0.416","0.0.20.6","3.0.0.0","295"')
        reqversky.SetBitmap(wx.Image(self.imgDir + os.sep + (u'oblivion16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(reqversky)
        reqverob = wx.MenuItem(rightclickmenu, ID_REQVERSK, u'&RequireVersions Skyrim', u' RequireVersions "1.1.21.0","","","295"')
        reqverob.SetBitmap(wx.Image(self.imgDir + os.sep + (u'skyrim16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(reqverob)

        submenu = wx.Menu()
        menuItem = wx.MenuItem(submenu, wx.NewId(), u'&DataFileExists ("[modName]")')
        datafileexists = wx.MenuItem(rightclickmenu, ID_DATAFILEEXISTS, u'&DataFileExists ""', u' DataFileExists ""')
        submenu.AppendItem(datafileexists)
        for filename in os.listdir(u'%s' %bosh.dirs['mods']):
            newid = wx.NewId()
            if u'Bashed Patch' in filename:
                # print filename
                datafileexists = wx.MenuItem(rightclickmenu, newid, u'DataFileExists ("%s")' %filename, u' DataFileExists ("[modName]")')
                datafileexists.SetBitmap(wx.Image(self.imgDir + os.sep + (u'wryemonkey16.png'),p).ConvertToBitmap())
                submenu.AppendItem(datafileexists)
                wx.EVT_MENU(rightclickmenu, newid, self.OnWriteKeywordSUBNAMEorESPMNAME)
            elif filename.endswith(u'.esp'):
                # print filename
                datafileexists = wx.MenuItem(rightclickmenu, newid, u'DataFileExists ("%s")' %filename, u' DataFileExists ("[modName]")')
                datafileexists.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'esp16.png'),p).ConvertToBitmap())
                submenu.AppendItem(datafileexists)
                wx.EVT_MENU(rightclickmenu, newid, self.OnWriteKeywordSUBNAMEorESPMNAME)
            elif filename.endswith(u'.esm'):
                # print filename
                datafileexists = wx.MenuItem(rightclickmenu, newid, u'DataFileExists ("%s")' %filename, u' DataFileExists ("[modName]")')
                datafileexists.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'esm16.png'),p).ConvertToBitmap())
                submenu.AppendItem(datafileexists)
                wx.EVT_MENU(rightclickmenu, newid, self.OnWriteKeywordSUBNAMEorESPMNAME)
        menuItem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'list16.png'),p).ConvertToBitmap())
        menuItem.SetBackgroundColour(u'#FFF7EE')
        menuItem.SetSubMenu(submenu)
        rightclickmenu.AppendItem(menuItem)

        selectone = wx.MenuItem(rightclickmenu, ID_SELECTONE, u'&SelectOne "Dialog...", \\', u' SelectOne "Dialog...", \\')
        selectone.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'dialog16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(selectone)
        selectmany = wx.MenuItem(rightclickmenu, ID_SELECTMANY, u'&SelectMany "Dialog...", \\', u' SelectMany "Dialog...", \\')
        selectmany.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'dialog16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(selectmany)

        ifelifelseendif = wx.MenuItem(rightclickmenu, ID_IFELIFELSEENDIF, u'&If-Elif-Else-EndIf')
        rightclickmenu.AppendItem(ifelifelseendif)

        choicesx2 = wx.MenuItem(rightclickmenu, ID_OPTIONS, u'&"","","",\\ X2', u' "","","",\\ X2')
        rightclickmenu.AppendItem(choicesx2)
        endselect = wx.MenuItem(rightclickmenu, ID_ENDSELECT, u'&EndSelect', u' EndSelect')
        rightclickmenu.AppendItem(endselect)
        case = wx.MenuItem(rightclickmenu, ID_CASE, u'&Case', u' Case')
        rightclickmenu.AppendItem(case)
        bbreak = wx.MenuItem(rightclickmenu, ID_BREAK, u'&Break', u' Break')
        rightclickmenu.AppendItem(bbreak)
        selectall = wx.MenuItem(rightclickmenu, ID_SELECTALLKW, u'&SelectAll', u' SelectAll')
        rightclickmenu.AppendItem(selectall)
        deselectall = wx.MenuItem(rightclickmenu, ID_DESELECTALL, u'&DeSelectAll', u' DeSelectAll')
        rightclickmenu.AppendItem(deselectall)

        if mSubListCount == 0:
            selectsubpackage = wx.MenuItem(rightclickmenu, ID_SELECTSUBPACKAGE, u'&SelectSubPackage', u' SelectSubPackage')
            rightclickmenu.AppendItem(selectsubpackage)
        else:
            submenu = wx.Menu()
            menuItem = wx.MenuItem(submenu, wx.NewId(), u'SelectSubPackage "[subName]"')
            selectsubpackage = wx.MenuItem(rightclickmenu, ID_SELECTSUBPACKAGE, u'&SelectSubPackage ""', u' SelectSubPackage ""')
            submenu.AppendItem(selectsubpackage)
            for index in xrange(mSubListCount):
                newid = wx.NewId()
                selectsubpackagesubmenuitem = wx.MenuItem(rightclickmenu, newid, u'SelectSubPackage "' + u'%s' %basher.gInstallers.gSubList.GetString(index) + u'"', u' SelectSubPackage "[subName]"')
                submenu.AppendItem(selectsubpackagesubmenuitem)
                wx.EVT_MENU(rightclickmenu, newid, self.OnWriteKeywordSUBNAMEorESPMNAME)
            menuItem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'list16.png'),p).ConvertToBitmap())
            menuItem.SetBackgroundColour(u'#FFF7EE')
            menuItem.SetSubMenu(submenu)
            rightclickmenu.AppendItem(menuItem)

        if mSubListCount == 0:
            deselectsubpackage = wx.MenuItem(rightclickmenu, ID_DESELECTSUBPACKAGE, u'&DeSelectSubPackage', u' DeSelectSubPackage')
            rightclickmenu.AppendItem(deselectsubpackage)
        else:
            submenu = wx.Menu()
            menuItem = wx.MenuItem(submenu, wx.NewId(), u'DeSelectSubPackage "[subName]"')
            deselectsubpackage = wx.MenuItem(rightclickmenu, ID_DESELECTSUBPACKAGE, u'&DeSelectSubPackage ""', u' DeSelectSubPackage ""')
            submenu.AppendItem(deselectsubpackage)
            for index in xrange(mSubListCount):
                newid = wx.NewId()
                deselectsubpackagesubmenuitem = wx.MenuItem(rightclickmenu, newid, u'DeSelectSubPackage "' + u'%s' %basher.gInstallers.gSubList.GetString(index) + u'"', u' DeSelectSubPackage "[subName]"')
                submenu.AppendItem(deselectsubpackagesubmenuitem)
                wx.EVT_MENU(rightclickmenu, newid, self.OnWriteKeywordSUBNAMEorESPMNAME)
            menuItem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'list16.png'),p).ConvertToBitmap())
            menuItem.SetBackgroundColour(u'#FFF7EE')
            menuItem.SetSubMenu(submenu)
            rightclickmenu.AppendItem(menuItem)

        if mEspmListCount == 0:
            selectespm = wx.MenuItem(rightclickmenu, ID_SELECTESPM, u'&SelectEspm', u' SelectEspm')
            rightclickmenu.AppendItem(selectespm)
        else:
            submenu = wx.Menu()
            menuItem = wx.MenuItem(submenu, wx.NewId(), u'SelectEspm "[espmName]"')
            selectespm = wx.MenuItem(rightclickmenu, ID_SELECTESPM, u'&SelectEspm ""', u' SelectEspm ""')
            submenu.AppendItem(selectespm)
            for index in xrange(mEspmListCount):
                newid = wx.NewId()
                filename = u'%s' %basher.gInstallers.gEspmList.GetString(index)
                if filename.endswith(u'.esp'):
                    selectespmsubmenuitem = wx.MenuItem(rightclickmenu, newid, u'SelectEspm "' + u'%s' %filename + u'"', u' SelectEspm "[espmName]"')
                    selectespmsubmenuitem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'esp16.png'),p).ConvertToBitmap())
                elif filename.endswith(u'.esm'):
                    selectespmsubmenuitem = wx.MenuItem(rightclickmenu, newid, u'SelectEspm "' + u'%s' %filename + u'"', u' SelectEspm "[espmName]"')
                    selectespmsubmenuitem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'esm16.png'),p).ConvertToBitmap())
                submenu.AppendItem(selectespmsubmenuitem)
                wx.EVT_MENU(rightclickmenu, newid, self.OnWriteKeywordSUBNAMEorESPMNAME)
            menuItem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'list16.png'),p).ConvertToBitmap())
            menuItem.SetBackgroundColour(u'#FFF7EE')
            menuItem.SetSubMenu(submenu)
            rightclickmenu.AppendItem(menuItem)

        if mEspmListCount == 0:
            deselectespm = wx.MenuItem(rightclickmenu, ID_DESELECTESPM, u'&DeSelectEspm', u' DeSelectEspm')
            rightclickmenu.AppendItem(deselectespm)
        else:
            submenu = wx.Menu()
            menuItem = wx.MenuItem(submenu, wx.NewId(), u'DeSelectEspm "[espmName]"')
            deselectespm = wx.MenuItem(rightclickmenu, ID_DESELECTESPM, u'&DeSelectEspm ""', u' DeSelectEspm ""')
            submenu.AppendItem(deselectespm)
            for index in xrange(mEspmListCount):
                newid = wx.NewId()
                filename = u'%s' %basher.gInstallers.gEspmList.GetString(index)
                if filename.endswith(u'.esp'):
                    deselectespmsubmenuitem = wx.MenuItem(rightclickmenu, newid, u'DeSelectEspm "' + u'%s' %filename + u'"', u' DeSelectEspm "[espmName]"')
                    deselectespmsubmenuitem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'esp16.png'),p).ConvertToBitmap())
                elif filename.endswith(u'.esm'):
                    deselectespmsubmenuitem = wx.MenuItem(rightclickmenu, newid, u'DeSelectEspm "' + u'%s' %filename + u'"', u' DeSelectEspm "[espmName]"')
                    deselectespmsubmenuitem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'esm16.png'),p).ConvertToBitmap())
                submenu.AppendItem(deselectespmsubmenuitem)
                wx.EVT_MENU(rightclickmenu, newid, self.OnWriteKeywordSUBNAMEorESPMNAME)
            menuItem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'list16.png'),p).ConvertToBitmap())
            menuItem.SetBackgroundColour(u'#FFF7EE')
            menuItem.SetSubMenu(submenu)
            rightclickmenu.AppendItem(menuItem)

        selectallespms = wx.MenuItem(rightclickmenu, ID_SELECTALLESPMS, u'&SelectAllEspms', u' SelectAllEspms')
        rightclickmenu.AppendItem(selectallespms)

        deselectallespms = wx.MenuItem(rightclickmenu, ID_DESELECTALLESPMS, u'&DeSelectAllEspms', u' DeSelectAllEspms')
        rightclickmenu.AppendItem(deselectallespms)

        renameespm = wx.MenuItem(rightclickmenu, ID_RENAMEESPM, u'&RenameEspm', u' RenameEspm')
        rightclickmenu.AppendItem(renameespm)

        if mEspmListCount == 0:
            resetespmname = wx.MenuItem(rightclickmenu, ID_RESETESPMNAME, u'&ResetEspmName', u' ResetEspmName')
            rightclickmenu.AppendItem(resetespmname)
        else:
            submenu = wx.Menu()
            menuItem = wx.MenuItem(submenu, wx.NewId(), u'ResetEspmName "[espmName]"')
            resetespmname = wx.MenuItem(rightclickmenu, ID_RESETESPMNAME, u'&ResetEspmName ""', u' ResetEspmName ""')
            submenu.AppendItem(resetespmname)
            for index in xrange(mEspmListCount):
                newid = wx.NewId()
                filename = u'%s' %basher.gInstallers.gEspmList.GetString(index)
                if filename.endswith(u'.esp'):
                    resetespmnamesubmenuitem = wx.MenuItem(rightclickmenu, newid, u'ResetEspmName "' + u'%s' %filename + u'"', u' ResetEspmName "[espmName]"')
                    resetespmnamesubmenuitem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'esp16.png'),p).ConvertToBitmap())
                elif filename.endswith(u'.esm'):
                    resetespmnamesubmenuitem = wx.MenuItem(rightclickmenu, newid, u'ResetEspmName "' + u'%s' %filename + u'"', u' ResetEspmName "[espmName]"')
                    resetespmnamesubmenuitem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'esm16.png'),p).ConvertToBitmap())
                submenu.AppendItem(resetespmnamesubmenuitem)
                wx.EVT_MENU(rightclickmenu, newid, self.OnWriteKeywordSUBNAMEorESPMNAME)
            menuItem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'list16.png'),p).ConvertToBitmap())
            menuItem.SetBackgroundColour(u'#FFF7EE')
            menuItem.SetSubMenu(submenu)
            rightclickmenu.AppendItem(menuItem)

        resetallespmnames = wx.MenuItem(rightclickmenu, ID_RESETALLESPMNAMES, u'&ResetAllEspmNames', u' ResetAllEspmNames')
        rightclickmenu.AppendItem(resetallespmnames)

        defaultcharselectedoptions = wx.MenuItem(rightclickmenu, ID_DEFAULTCHAR, u'&"|Default Char","Selected Options","Line(s)", \\')
        rightclickmenu.AppendItem(defaultcharselectedoptions)

        packagenamewizardimagesDir = (u'%s' %bosh.dirs[u'installers'].join(u'%s' %basher.gInstallers.gPackage.GetValue()).join(u'Wizard Images'))
        if os.path.isdir(packagenamewizardimagesDir):
            submenu = wx.Menu()
            menuItem = wx.MenuItem(submenu, wx.NewId(), u'Wizard Images\\\\[packageImg.ext]')
            packagename = wx.MenuItem(rightclickmenu, wx.NewId(), u'%s' %basher.gInstallers.gPackage.GetValue(), u' packageName')
            packagename.SetBitmap(wx.Image(self.imgDir + os.sep + u'diamond_white_off_wiz.png',p).ConvertToBitmap())
            submenu.AppendItem(packagename)
            packagename.Enable(False)
            wizardimages = wx.MenuItem(rightclickmenu, ID_WIZARDIMAGES, u'Wizard Images\\\\', u' Wizard Images\\\\')
            submenu.AppendItem(wizardimages)
            packagenameWizardImagesList = os.listdir(packagenamewizardimagesDir)
            # print (packagenameWizardImagesList)
            # print (u'Wizard Images Dir Exists')
            for wizardimage in packagenameWizardImagesList:
                ext = wizardimage[wizardimage.rfind('.'):].lower()
                # print (ext)
                if ext in [u'.jpg',u'.jpeg',u'.png',u'.gif',u'.ico']:
                    newid = wx.NewId()
                    submenuitem = wx.MenuItem(rightclickmenu, newid, u'Wizard Images\\\\' + u'%s' %wizardimage, u' Wizard Images\\\\')
                    if ext == u'.jpg' or ext == u'.jpeg':
                        submenuitem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'file_image16.png'),p).ConvertToBitmap())
                    elif ext == u'.png':
                        submenuitem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'file_png16.png'),p).ConvertToBitmap())
                    else:
                        submenuitem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'black16.png'),p).ConvertToBitmap())
                    submenu.AppendItem(submenuitem)
                    wx.EVT_MENU(rightclickmenu, newid, self.OnWriteImageDirectoryIMAGE)
            menuItem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'list16.png'),p).ConvertToBitmap())
            menuItem.SetBackgroundColour(u'#FFF7EE')
            menuItem.SetSubMenu(submenu)
            rightclickmenu.AppendItem(menuItem)
        else:
            wizardimages = wx.MenuItem(rightclickmenu, ID_WIZARDIMAGES, u'Wizard Images\\\\', u' Wizard Images\\\\')
            rightclickmenu.AppendItem(wizardimages)

        ####################################

        packagenamewizardimagesDir = (u'%s' %bosh.dirs[u'installers'].join(u'%s' %basher.gInstallers.gPackage.GetValue()).join(u'Screenshots'))
        if os.path.isdir(packagenamewizardimagesDir):
            submenu = wx.Menu()
            menuItem = wx.MenuItem(submenu, wx.NewId(), u'Screenshots\\\\[packageImg.ext]')
            packagename = wx.MenuItem(rightclickmenu, wx.NewId(), u'%s' %basher.gInstallers.gPackage.GetValue(), u' packageName')
            packagename.SetBitmap(wx.Image(self.imgDir + os.sep + u'diamond_white_off_wiz.png',p).ConvertToBitmap())
            submenu.AppendItem(packagename)
            packagename.Enable(False)
            screenshotsimages = wx.MenuItem(rightclickmenu, ID_SCREENSHOTS, u'Screenshots\\\\', u' Screenshots\\\\')
            submenu.AppendItem(screenshotsimages)
            packagenameWizardImagesList = os.listdir(packagenamewizardimagesDir)
            # print (packagenameWizardImagesList)
            # print (u'Wizard Images Dir Exists')
            for wizardimage in packagenameWizardImagesList:
                ext = wizardimage[wizardimage.rfind('.'):].lower()
                # print (ext)
                if ext in [u'.jpg',u'.jpeg',u'.png',u'.gif',u'.ico']:
                    newid = wx.NewId()
                    submenuitem = wx.MenuItem(rightclickmenu, newid, u'Screenshots\\\\' + u'%s' %wizardimage, u' Screenshots\\\\')
                    if ext == u'.jpg' or ext == u'.jpeg':
                        submenuitem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'file_image16.png'),p).ConvertToBitmap())
                    elif ext == u'.png':
                        submenuitem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'file_png16.png'),p).ConvertToBitmap())
                    else:
                        submenuitem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'black16.png'),p).ConvertToBitmap())
                    submenu.AppendItem(submenuitem)
                    wx.EVT_MENU(rightclickmenu, newid, self.OnWriteImageDirectoryIMAGE)
            menuItem.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'list16.png'),p).ConvertToBitmap())
            menuItem.SetBackgroundColour(u'#FFF7EE')
            menuItem.SetSubMenu(submenu)
            rightclickmenu.AppendItem(menuItem)
        else:
            screenshotsimages = wx.MenuItem(rightclickmenu, ID_SCREENSHOTS, u'Screenshots\\\\', u' Screenshots\\\\')
            rightclickmenu.AppendItem(screenshotsimages)

        rightclickmenu.AppendSeparator()

        submenu = wx.Menu()
        listactivesubpackages = wx.MenuItem(rightclickmenu, ID_LISTSUBPACKAGES, u'&List SubPackages... (De)/SelectSubPackages', u' List SubPackages...')
        listactivesubpackages.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'list16.png'),p).ConvertToBitmap())
        submenu.AppendItem(listactivesubpackages)

        listactiveespms = wx.MenuItem(rightclickmenu, ID_LISTESPMS, u'&List Espms... (De)/SelectEspm', u' List Espms...')
        listactiveespms.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'list16.png'),p).ConvertToBitmap())
        submenu.AppendItem(listactiveespms)

        rightclickmenu.AppendMenu(wx.NewId(), u'List...', submenu)

        imagebrowserpackagewizardimages = wx.MenuItem(rightclickmenu, ID_IMAGEBROWSER, u'&ImageBrowser [packageName\\Wizard Images]')
        imagebrowserpackagewizardimages.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'file_image16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(imagebrowserpackagewizardimages)

        thumbnailerpackagewizardimages = wx.MenuItem(rightclickmenu, ID_THUMBNAILER, u'&Thumbnailer [packageName\\Wizard Images]')
        thumbnailerpackagewizardimages.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'python16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(thumbnailerpackagewizardimages)

        # submenu = wx.Menu()
        # for i in range(0,256):
            # testmanysubmenuitems = wx.MenuItem(rightclickmenu, wx.NewId(), u'Test "' + u'%s' %i + u'"', u' Test')
            # submenu.AppendItem(testmanysubmenuitems)
        # rightclickmenu.AppendMenu(wx.NewId(), u'Test many submenu items(256)...', submenu)

        #events
        wx.EVT_MENU(rightclickmenu, ID_REQVEROB, self.OnRequireVersionsOblivion)
        wx.EVT_MENU(rightclickmenu, ID_REQVERSK, self.OnRequireVersionsSkyrim)

        wx.EVT_MENU(rightclickmenu, ID_DATAFILEEXISTS, self.OnDataFileExists)


        wx.EVT_MENU(rightclickmenu, ID_SELECTONE, self.OnSelectOne)
        wx.EVT_MENU(rightclickmenu, ID_SELECTMANY, self.OnSelectMany)
        wx.EVT_MENU(rightclickmenu, ID_OPTIONS, self.OnChoicesX02)
        wx.EVT_MENU(rightclickmenu, ID_ENDSELECT, self.OnEndSelect)
        wx.EVT_MENU(rightclickmenu, ID_CASE, self.OnCase)
        wx.EVT_MENU(rightclickmenu, ID_BREAK, self.OnBreak)

        wx.EVT_MENU(rightclickmenu, ID_IFELIFELSEENDIF, self.OnIfElifElseEndIf)

        wx.EVT_MENU(rightclickmenu, ID_SELECTALLKW, self.OnSelectAllKeyword)
        wx.EVT_MENU(rightclickmenu, ID_DESELECTALL, self.OnDeSelectAll)
        wx.EVT_MENU(rightclickmenu, ID_SELECTSUBPACKAGE, self.OnSelectSubPackage)
        wx.EVT_MENU(rightclickmenu, ID_DESELECTSUBPACKAGE, self.OnDeSelectSubPackage)
        wx.EVT_MENU(rightclickmenu, ID_SELECTESPM, self.OnSelectEspm)
        wx.EVT_MENU(rightclickmenu, ID_DESELECTESPM, self.OnDeSelectEspm)
        wx.EVT_MENU(rightclickmenu, ID_SELECTALLESPMS, self.OnSelectAllEspms)
        wx.EVT_MENU(rightclickmenu, ID_DESELECTALLESPMS, self.OnDeSelectAllEspms)
        wx.EVT_MENU(rightclickmenu, ID_RENAMEESPM, self.OnRenameEspm)
        wx.EVT_MENU(rightclickmenu, ID_RESETESPMNAME, self.OnResetEspmName)
        wx.EVT_MENU(rightclickmenu, ID_RESETALLESPMNAMES, self.OnResetAllEspmNames)
        wx.EVT_MENU(rightclickmenu, ID_DEFAULTCHAR, self.OnDefaultCharacterSelectedOptions)

        wx.EVT_MENU(rightclickmenu, ID_WIZARDIMAGES, self.OnWizardImages)
        wx.EVT_MENU(rightclickmenu, ID_THUMBNAILER, self.OnThumbnailerPackageWizardImages)
        wx.EVT_MENU(rightclickmenu, ID_IMAGEBROWSER, self.OnImageBrowserPackageWizardImages)

        wx.EVT_MENU(rightclickmenu, ID_LISTSUBPACKAGES, self.OnWriteListSubPackages)
        wx.EVT_MENU(rightclickmenu, ID_LISTESPMS, self.OnWriteListEspms)

        wx.EVT_MENU(rightclickmenu, ID_RMGM1, self.OnRMouseGestureMenu1)
        wx.EVT_MENU(rightclickmenu, ID_RMGM2, self.OnRMouseGestureMenu2)
        wx.EVT_MENU(rightclickmenu, ID_RMGM3, self.OnRMouseGestureMenu3)
        wx.EVT_MENU(rightclickmenu, ID_RMGM4, self.OnRMouseGestureMenu4)
        wx.EVT_MENU(rightclickmenu, ID_RMGM5, self.OnRMouseGestureMenuNone)
        wx.EVT_MENU(rightclickmenu, ID_RMGM6, self.OnRMouseGestureMenu6)
        wx.EVT_MENU(rightclickmenu, ID_RMGM7, self.OnRMouseGestureMenu7)
        wx.EVT_MENU(rightclickmenu, ID_RMGM8, self.OnRMouseGestureMenu8)
        wx.EVT_MENU(rightclickmenu, ID_RMGM9, self.OnRMouseGestureMenu9)

        wx.EVT_MENU(rightclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        wx.EVT_MENU(rightclickmenu, ID_RMGM2DRAG, self.OnUseOnTopDraggableRMouseGestureMenu2)

        self.PopupMenu(rightclickmenu)
        rightclickmenu.Destroy()

    def OnIfElifElseEndIf(self, event):
        indentSz = basher.settings['bash.installers.wizSTC.IndentSize']
        self.AddText(u'If\n' +
                     u' '*indentSz + ';#\n'
                     u'Elif\n' +
                     u' '*indentSz + ';#\n'
                     u'Else\n' +
                     u' '*indentSz + ';#\n'
                     u'EndIf\n')

    def OnUseOnTopDraggableRMouseGestureMenu2(self, event):
        ''' Call the Always-OnTop-Draggable Version of the menu. '''
        if self.dragmenu2 == 0:
            win = DraggableRMouseGestureMenu2(self, wx.SIMPLE_BORDER)
            pos = gWizSTC.ClientToScreen(self.GetPosition())
            # print pos
            win.Position((pos[0],pos[1]),(0, 0))
            win.Show(True)
            self.dragmenu2 = 1

    def OnDefaultCharacterSelectedOptions(self, event):
        ''' Add the Default Character(|) to Option Lines. Can be single or multiple lines.
            "|Option1","","",\  ;Selected
            "|Option2","","",\  ;Selected
            "|Option3","","",\  ;Selected
            "Option4","",""     ;Not Selected
        '''
        selstart = self.GetSelectionStart()
        selend = self.GetSelectionEnd()
        startline = self.LineFromPosition(selstart)
        endline = self.LineFromPosition(selend)
        if selstart == selend:#Nothing selected
            indentpos = self.GetLineIndentPosition(startline)
            if self.GetCharAt(indentpos) == 34 or self.GetCharAt(indentpos) == 39:
                self.InsertText(indentpos + 1, '|')
        elif startline == endline:#Some selection on the same line
            indentpos = self.GetLineIndentPosition(startline)
            if self.GetCharAt(indentpos) == 34 or self.GetCharAt(indentpos) == 39:
                self.InsertText(indentpos + 1, '|')
        elif startline != endline:#More than one line selected
            self.BeginUndoAction()
            if startline > endline:#Ex 20,3
                for i in range(endline,startline + 1):
                    indentpos = self.GetLineIndentPosition(i)
                    if self.GetCharAt(indentpos) == 34 or self.GetCharAt(indentpos) == 39:
                        self.InsertText(indentpos + 1, '|')
                        # print i
            else:
                for i in range(startline,endline + 1):
                    indentpos = self.GetLineIndentPosition(i)
                    if self.GetCharAt(indentpos) == 34 or self.GetCharAt(indentpos) == 39:
                        self.InsertText(indentpos + 1, '|')
                        # print i
            self.EndUndoAction()
        self.SetFocus()

    def OnThumbnailerPackageWizardImages(self, event):
        ''' Call a floating frame with viewable wizard images from the currently active projects 'Wizard Images' directory. '''
        if self.OneInstanceThumbnailer == 1:
            wx.MessageBox(u'Only One Instance Allowed Open', u'WARNING', wx.ICON_EXCLAMATION | wx.OK)
        else:
            package = u'%s' %bosh.dirs[u'installers'].join(u'%s' %basher.gInstallers.gPackage.GetValue())
            if not os.path.isdir(package):
                wx.MessageBox(u'The Thumbnailer is for projects ONLY,\nNOT archives. Extract to a project first!', u'WARNING', wx.ICON_EXCLAMATION | wx.OK)
            else:
                packagenamewizardimagesDir = (u'%s' %bosh.dirs[u'installers'].join(u'%s' %basher.gInstallers.gPackage.GetValue()).join(u'Wizard Images'))
                self.dialog = wx.Dialog(self, -1, title=u'%s' %basher.gInstallers.gPackage.GetValue() + os.sep + u'Wizard Images',
                                        size=(545, 425), style=wx.DEFAULT_DIALOG_STYLE)
                self.dialog.SetBackgroundColour('#000000') # Set the Frame Background Color

                import wx.lib.agw.thumbnailctrl as TC
                self.thumbnailer = TC.ThumbnailCtrl(self.dialog, wx.NewId(), imagehandler=TC.NativeImageHandler, thumbfilter=TC.THUMB_FILTER_IMAGES)
                self.thumbnailer.ShowDir(packagenamewizardimagesDir)# Show this images dir
                self.thumbnailer.SetThumbOutline(TC.THUMB_OUTLINE_FULL)
                self.thumbnailer.SetZoomFactor(1.4)
                # self.thumbnailer.Bind(TC.EVT_THUMBNAILS_POINTED, self.OnThumbnailPointed)
                # self.thumbnailer.SetHighlightPointed(True)
                self.thumbnailer.ShowComboBox(True)
                self.thumbnailer.EnableToolTips(True)
                self.thumbnailer.ShowFileNames(True)
                self.thumbnailer.EnableDragging(True)
                # thumbnailcontextmenu = self.OnThumbnailContextMenu()
                # self.thumbnailer.SetPopupMenu(thumbnailcontextmenu)
                # self.thumbnailer.Bind(TC.EVT_THUMBNAILS_SEL_CHANGED, self.OnThumbnailSelChanged)
                self.thumbnailer.Bind(wx.EVT_CONTEXT_MENU, self.OnThumbnailContextMenu)
                # self.thumbnailer.Bind(wx.EVT_RIGHT_UP, self.OnThumbnailContextMenu)
                # self.thumbnailer.Bind(wx.EVT_RIGHT_DOWN, self.OnThumbnailSelChanged)
                self.thumbnailer.Bind(TC.EVT_THUMBNAILS_DCLICK, self.OnThumbnailWizImage)
                self.dialog.Bind(wx.EVT_CLOSE, self.OnDialogDestroy)

                tnsizer = wx.BoxSizer(wx.VERTICAL)
                tnsizer.Add(self.thumbnailer, 1, wx.EXPAND | wx.ALL, 3)
                self.dialog.SetSizer(tnsizer)
                tnsizer.Layout()

                self.dialog.Centre()
                self.dialog.Show()
                self.OneInstanceThumbnailer = 1
                # self.dialog.ShowModal()
                # self.dialog.Destroy()

    def OnThumbnailContextMenu(self, event):
        ''' Brings up a Thumbnailer context menu with various options: Ex Open Selected Thumbnail(Image) in Photoshop. '''
        print('THUMBNAIL CONTEXT')

    def OnThumbnailWizImage(self, event):
        ''' Adds text 'Wizard Images\\\\image.ext' a the caret. '''
        # id =  event.GetId()
        # evtobj = event.GetEventObject()
        # print id
        # print evtobj

        imgpath = self.thumbnailer.GetOriginalImage(self.thumbnailer.GetSelection())
        imgnamewithext = os.path.basename(imgpath) #Returns the final component of a pathname
        self.AddText(u'Wizard Images\\\\%s'%str(imgnamewithext))
        # return self.dialog.Destroy()

    def OnDialogDestroy(self, event):
        ''' Destroys the thumbnailer dialog. Needed because of the Only One Instance Open check '''
        # print ('KILL.BURN.DESTROY.')
        self.OneInstanceThumbnailer = 0
        return self.dialog.Destroy()

    def OnImageBrowserPackageWizardImages(self, event):
        ''' Call a floating frame with viewable wizard images from the currently active projects 'Wizard Images' directory. '''
        if self.OneInstanceImageBrowser == 1:
            wx.MessageBox(u'Only One Instance Allowed Open', u'WARNING', wx.ICON_EXCLAMATION | wx.OK)
        else:
            package = u'%s' %bosh.dirs[u'installers'].join(u'%s' %basher.gInstallers.gPackage.GetValue())
            if not os.path.isdir(package):
                wx.MessageBox(u'The Image Browser is for projects ONLY,\nNOT archives. Extract to a project first!', u'WARNING', wx.ICON_EXCLAMATION | wx.OK)
            else:
                packagenamewizardimagesDir = (u'%s' %bosh.dirs[u'installers'].join(u'%s' %basher.gInstallers.gPackage.GetValue()).join(u'Wizard Images'))
                dialog = ib.ImageDialog(self, packagenamewizardimagesDir)
                dialog.Centre()
                if dialog.ShowModal() == wx.ID_OK:
                    basename = os.path.basename(dialog.GetFile())
                    self.AddText(u'Wizard Images\\\\%s' %basename)
                else:
                    pass
                dialog.Destroy()

    def OnWriteImageDirectoryIMAGE(self, event):
        ''' This function adds text to the document from the dynamically generated menuitems by getting the menuitems's label. '''
        id =  event.GetId()
        # print event.GetId()
        # print event.GetEventObject()
        evtobj = event.GetEventObject()
        menuitem = evtobj.FindItemById(id)
        # print menuitem.GetItemLabel()
        self.AddText(u'%s' %menuitem.GetItemLabel())

    def OnWriteKeywordSUBNAMEorESPMNAME(self, event):
        ''' This function adds text to the document from the dynamically generated menuitems by getting the menuitems's label. '''
        id =  event.GetId()
        # print event.GetId()
        # print event.GetEventObject()
        evtobj = event.GetEventObject()
        menuitem = evtobj.FindItemById(id)
        # print menuitem.GetItemLabel()
        self.AddText(u'%s' %menuitem.GetItemLabel() + u'\n')

    # def OnWriteKeywordMODNAME(self, event):#NOT DONE
        # ''' This function adds text to the document from the dynamically generated menuitems by getting the menuitems's label. '''
        # # print bosh.modInfos.getModList(showCRC=False,showVersion=False,fileInfo=None,wtxt=True)
        # # dataDir = bosh.dirs['mods']

        # for filename in os.listdir(u'%s' %bosh.dirs['mods']):
            # if filename.endswith(u'.esp') or filename.endswith(u'.esm'):
                # print filename

    def OnDataFileExists(self, event):
        ''' Write DataFileExists "" to the editor. '''
        self.OnDeleteIfSelectedText(event)
        self.AddText('DataFileExists ""')
        self.CharLeft()
        self.SetFocus()

    def OnWriteListSubPackages(self, event):
        ''' Write (De)/SelectSubPackage "[subName]" for currently unselected/selected SubPackages. '''
        subs = _(u'')
        for index in xrange(basher.gInstallers.gSubList.GetCount()):
            subs += [u'DeSelectSubPackage "',u'SelectSubPackage "'][basher.gInstallers.gSubList.IsChecked(index)] + basher.gInstallers.gSubList.GetString(index) + u'"\n'
        self.AddText(subs)

    def OnWriteListEspms(self, event):
        ''' Write (De)/SelectEspm "[espmName]" for currently unselected/selected Espms. '''
        espms = _(u'')
        for index in xrange(basher.gInstallers.gEspmList.GetCount()):
            espms += [u'DeSelectEspm "',u'SelectEspm "'][basher.gInstallers.gEspmList.IsChecked(index)] + basher.gInstallers.gEspmList.GetString(index) + u'"\n'
        self.AddText(espms)

    def OnDeleteIfSelectedText(self, event):
        ''' This function deletes any selected text. Usually called from another function. '''
        if self.GetSelectionStart() == self.GetSelectionEnd():
            pass
        else:
            self.DeleteBack()

    def OnRequireVersionsOblivion(self, event):
        ''' Adds text RequireVersions "GameVersion","ScriptExtenderVersion","GraphicsExtenderVersion","WryeBashVersion" '''
        self.AddText(u'RequireVersions "1.2.0.416","0.0.20.6","3.0.0.0","295"')
    def OnRequireVersionsSkyrim(self, event):
        ''' Adds text RequireVersions "GameVersion","ScriptExtenderVersion","GraphicsExtenderVersion","WryeBashVersion" '''
        self.AddText(u'RequireVersions "1.1.21.0","","","295"')
    def OnSelectOne(self, event):
        ''' Adds text for a SelectOne dialog to the editor. '''
        # self.AddText(u'SelectOne "", \\')
        # for i in range(0,4): self.CharLeft()

        dialog = wx.TextEntryDialog(self, 'SelectOne "How Many Options?", \\\n'
                                          '    "Option1","Description1","Wizard Images\\\\SomePic1.png",\\\n'
                                          '    "Option2","Description2","Wizard Images\\\\SomePic2.png",\\\n'
                                          '    Case "Option1"\n'
                                          '        ;#Do Something\n'
                                          '        Break\n'
                                          '    Case "Option2"\n'
                                          '        ;#Do Something\n'
                                          '        Break\n'
                                          'EndSelect\n'
                                          '\n'
                                          'Enter desired number of options (2 or above)', 'Add SelectOne Dialog Code', '2')
        dialog.SetIcon(wx.Icon(self.imgstcDir + os.sep + u'wizardhat16.png', wx.BITMAP_TYPE_PNG))
        number = ''
        if dialog.ShowModal() == wx.ID_OK:
            number = int(dialog.GetValue())
            numberminusone = int(dialog.GetValue()) - 1
        dialog.Destroy()

        if number != '':
            self.AddText(u'SelectOne "", \\\n')
            self.AddText((' '*basher.settings['bash.installers.wizSTC.IndentSize'] + '"", "", "",\\\n')*(numberminusone) +
                          ' '*basher.settings['bash.installers.wizSTC.IndentSize'] + '"", "", ""\n')
            self.AddText((' '*basher.settings['bash.installers.wizSTC.IndentSize'] + 'Case ""\n' +
                          ' '*basher.settings['bash.installers.wizSTC.IndentSize']*2 + ';#\n' +
                          ' '*basher.settings['bash.installers.wizSTC.IndentSize']*2 + 'Break\n')*(number))
            self.SetFocus()
            self.AddText(u'EndSelect')

    def OnSelectMany(self, event):
        ''' Adds text for a SelectMany dialog to the editor. '''
        # self.AddText(u'SelectMany "", \\')
        # for i in range(0,4): self.CharLeft()

        dialog = wx.TextEntryDialog(self, 'SelectMany "How Many Options?", \\\n'
                                          '    "Option1","Description1","Wizard Images\\\\SomePic1.png",\\\n'
                                          '    "Option2","Description2","Wizard Images\\\\SomePic2.png",\\\n'
                                          '    "Option3","Description3","Wizard Images\\\\SomePic3.png",\\\n'
                                          '    Case "Option1"\n'
                                          '        ;#Do Something\n'
                                          '        Break\n'
                                          '    Case "Option2"\n'
                                          '        ;#Do Something\n'
                                          '        Break\n'
                                          '    Case "Option3"\n'
                                          '        ;#Do Something\n'
                                          '        Break\n'
                                          'EndSelect\n'
                                          '\n'
                                          'Enter desired number of options (2 or above)', 'Add SelectMany Dialog Code', '2')
        dialog.SetIcon(wx.Icon(self.imgstcDir + os.sep + u'wizardhat16.png', wx.BITMAP_TYPE_PNG))
        number = ''
        if dialog.ShowModal() == wx.ID_OK:
            number = int(dialog.GetValue())
            numberminusone = int(dialog.GetValue()) - 1
        dialog.Destroy()

        if number != '':
            self.AddText(u'SelectMany "", \\\n')
            self.AddText((' '*basher.settings['bash.installers.wizSTC.IndentSize'] + '"", "", "",\\\n')*(numberminusone) +
                          ' '*basher.settings['bash.installers.wizSTC.IndentSize'] + '"", "", ""\n')
            self.AddText((' '*basher.settings['bash.installers.wizSTC.IndentSize'] + 'Case ""\n' +
                          ' '*basher.settings['bash.installers.wizSTC.IndentSize']*2 + ';#\n' +
                          ' '*basher.settings['bash.installers.wizSTC.IndentSize']*2 + 'Break\n')*(number))
            self.SetFocus()
            self.AddText(u'EndSelect')



    def OnChoicesX02(self, event): # "", "", "" x2
        ''' Adds (indented)text for some SelectOne/Many dialog options to the editor. '''
        if basher.settings['bash.installers.wizSTC.TabsOrSpaces'] == 1:#TABS
            self.AddText('\t"", "Description.", "Wizard Images\\\\NeedPic.jpg",\\\n'
                         '\t"", "Description.", "Wizard Images\\\\NeedPic.jpg"\n')
        elif basher.settings['bash.installers.wizSTC.TabsOrSpaces'] == 0:#Spaces
            indent1 = ' '*(basher.settings['bash.installers.wizSTC.IndentSize'])
            self.AddText('%s"", "Description.", "Wizard Images\\\\NeedPic.jpg",\\\n' % indent1 +
                         '%s"", "Description.", "Wizard Images\\\\NeedPic.jpg"\n' % indent1)
        self.SetFocus()
    def OnEndSelect(self, event):
        ''' Adds text EndSelect to the editor. '''
        self.AddText('EndSelect\n')
        self.SetFocus()
    def OnCase(self, event):
        ''' Adds (indented)text Case to the editor. '''
        if basher.settings['bash.installers.wizSTC.TabsOrSpaces'] == 1:#TABS
            self.AddText('\tCase ""\n')
        elif basher.settings['bash.installers.wizSTC.TabsOrSpaces'] == 0:#Spaces
            indent1 = ' '*(basher.settings['bash.installers.wizSTC.IndentSize'])
            self.AddText('%sCase ""\n' %indent1)
        self.SetFocus()
    def OnBreak(self, event):
        ''' Adds (indented)text Break to the editor. '''
        if basher.settings['bash.installers.wizSTC.TabsOrSpaces'] == 1:#TABS
            self.AddText('\tBreak\n')
        elif basher.settings['bash.installers.wizSTC.TabsOrSpaces'] == 0:#Spaces
            indent1 = ' '*(basher.settings['bash.installers.wizSTC.IndentSize'])
            self.AddText('%sBreak\n' %indent1)
        self.SetFocus()
    def OnSelectAllKeyword(self, event):
        ''' Adds text SelectAll to the editor. '''
        self.AddText('SelectAll')
        self.SetFocus()
    def OnDeSelectAll(self, event):
        ''' Adds text DeSelectAll to the editor. '''
        self.AddText('DeSelectAll')
        self.SetFocus()
    def OnSelectSubPackage(self, event):
        ''' Adds text SelectSubPackage "" to the editor. '''
        self.OnDeleteIfSelectedText(event)
        self.AddText('SelectSubPackage ""')
        self.CharLeft()
        self.SetFocus()
    def OnDeSelectSubPackage(self, event):
        ''' Adds text DeSelectSubPackage "" to the editor. '''
        self.OnDeleteIfSelectedText(event)
        self.AddText('DeSelectSubPackage ""')
        self.CharLeft()
        self.SetFocus()
    def OnSelectEspm(self, event):
        ''' Adds text SelectEspm "" to the editor. '''
        self.OnDeleteIfSelectedText(event)
        self.AddText('SelectEspm ""')
        self.CharLeft()
        self.SetFocus()
    def OnSelectAllEspms(self, event):
        ''' Adds text SelectAllEspms to the editor. '''
        self.AddText('SelectAllEspms')
        self.SetFocus()
    def OnDeSelectEspm(self, event):
        ''' Adds text DeSelectEspm "" to the editor. '''
        self.OnDeleteIfSelectedText(event)
        self.AddText('DeSelectEspm ""')
        self.CharLeft()
        self.SetFocus()
    def OnDeSelectAllEspms(self, event):
        ''' Adds text DeSelectAllEspms to the editor. '''
        self.AddText('DeSelectAllEspms')
        self.SetFocus()
    def OnRenameEspm(self, event):
        ''' Adds text RenameEspm "" to the editor. '''
        self.OnDeleteIfSelectedText(event)
        self.AddText('RenameEspm ""')
        self.CharLeft()
        self.SetFocus()
    def OnResetEspmName(self, event):
        ''' Adds text ResetEspmName "" to the editor. '''
        self.OnDeleteIfSelectedText(event)
        self.AddText('ResetEspmName ""')
        self.CharLeft()
        self.SetFocus()
    def OnResetAllEspmNames(self, event):
        ''' Adds text ResetAllEspmNames to the editor. '''
        self.AddText('ResetAllEspmNames')
        self.SetFocus()

    def OnWizardImages(self, event):
        ''' Adds text Wizard Images\\\\ to the editor. '''
        self.AddText('Wizard Images\\\\')
        self.SetFocus()


    def OnRMouseGestureMenu3(self, event):
        ''' Call the Right Mouse Gesture Menu.
        NUMPAD:3
        [7][8][9]
        [4][5][6]
        [1][2][@]
        '''
        rightclickmenu = wx.Menu()

        p = wx.BITMAP_TYPE_PNG

        rcheader1 = wx.MenuItem(rightclickmenu, 0000, u'&R MGM 3', u'ContextMenu3')
        rcheader1.SetBackgroundColour('#000000')
        rightclickmenu.AppendItem(rcheader1)
        rcheader1.SetDisabledBitmap(self.rmbImg)
        rcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            if i == 3:#The currently open menu
                mgm = wx.MenuItem(rightclickmenu, self.rmgmIDs[i-1], u'&R MGM %s You Are Here!'%str(i), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(self.yahImg)
                mgm.SetBackgroundColour('#F4FAB4')
                mgm.Enable(False)
            else:
                mgm = wx.MenuItem(rightclickmenu, self.rmgmIDs[i-1], u'&R MGM %s %s'%(str(i),self.rmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(self.mgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(rightclickmenu, ID_MMGM5, u'&M MGM 5 Macro', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(self.mgmImg)
        submenu.AppendItem(mgm)
        rightclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        rightclickmenu.AppendSeparator()

        showcalltip = wx.MenuItem(rightclickmenu, ID_CALLTIP, u'&Show CallTip\tCtrl+Shift+Space', u' Show a calltip for the currently selected word.')
        showcalltip.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'showcalltip24.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(showcalltip)

        wordcomplete = wx.MenuItem(rightclickmenu, ID_WORDCOMPLETE, u'&WordComplete Box\tCtrl+W', u' Ctrl+W opens the WordComplete box')
        wordcomplete.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'wordcomplete24.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(wordcomplete)

        autocomplete = wx.MenuItem(rightclickmenu, ID_AUTOCOMPLETE, u'&AutoComplete Box\tCtrl+Space', u' Ctrl+Space opens the AutoComplete box')
        autocomplete.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'autocomplete24.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(autocomplete)

        #events
        wx.EVT_MENU(rightclickmenu, ID_RMGM1, self.OnRMouseGestureMenu1)
        wx.EVT_MENU(rightclickmenu, ID_RMGM2, self.OnRMouseGestureMenu2)
        wx.EVT_MENU(rightclickmenu, ID_RMGM3, self.OnRMouseGestureMenu3)
        wx.EVT_MENU(rightclickmenu, ID_RMGM4, self.OnRMouseGestureMenu4)
        wx.EVT_MENU(rightclickmenu, ID_RMGM5, self.OnRMouseGestureMenuNone)
        wx.EVT_MENU(rightclickmenu, ID_RMGM6, self.OnRMouseGestureMenu6)
        wx.EVT_MENU(rightclickmenu, ID_RMGM7, self.OnRMouseGestureMenu7)
        wx.EVT_MENU(rightclickmenu, ID_RMGM8, self.OnRMouseGestureMenu8)
        wx.EVT_MENU(rightclickmenu, ID_RMGM9, self.OnRMouseGestureMenu9)

        wx.EVT_MENU(rightclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        wx.EVT_MENU(rightclickmenu, ID_CALLTIP, self.OnShowSelectedTextCallTip)
        wx.EVT_MENU(rightclickmenu, ID_WORDCOMPLETE, self.OnShowWordCompleteBox)
        wx.EVT_MENU(rightclickmenu, ID_AUTOCOMPLETE, self.OnShowAutoCompleteBox)

        self.PopupMenu(rightclickmenu)
        rightclickmenu.Destroy()

    def OnShowSelectedTextCallTip(self, event):
        ''' Show a CallTip for the currently selected wizard script keyword. '''
        pos = self.GetCurrentPos()

        self.CallTipSetBackground('yellow')             #Set the background colour for the call tip.
        self.CallTipSetForeground('#666666')            #Set the foreground colour for the call tip.
        self.CallTipSetHighlight(2, 5)                  #Highlight a segment of the definition.(int start, int end)
        self.CallTipSetForegroundHighlight('#FF0000')   #Set the foreground colour for the highlighted part of the call tip.
        # self.CallTipPosAtStart()    #Retrieve the position where the caret was before displaying the call tip.
        # self.CallTipUseStyle(48)    #Enable use of STYLE_CALLTIP and set call tip tab size in pixels.
        # self.CallTipActive()        #Is there an active call tip? -> bool
        # self.CallTipCancel()        #Remove the call tip from the screen.
        # self.CallTipPosAtStart()    #Retrieve the position where the caret was before displaying the call tip.

        if basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
            self.CallTipSetBackground('#D7DEEB')        #Set the background colour for the call tip.
            self.CallTipSetForeground('#666666')        #Set the foreground colour for the call tip.

            if   self.GetSelectedText() == 'SelectOne':         self.CallTipShow(pos, 'The SelectOne dialog gives you a list of options,\nwith the option to select one of them.')
            elif self.GetSelectedText() == 'SelectMany':        self.CallTipShow(pos, 'The SelectMany dialog gives you a list of options,\nwith the option to select one or more of them,\nor even none of them.')
            elif self.GetSelectedText() == 'EndSelect':         self.CallTipShow(pos, 'EndSelect')
            elif self.GetSelectedText() == 'SelectAll':         self.CallTipShow(pos, 'Cause all sub-packages, esps, and\nesms to be selected for installation.')
            elif self.GetSelectedText() == 'DeSelectAll':       self.CallTipShow(pos, 'Cause all sub-packages, esps, and\nesms to be de-selected from installation.')
            elif self.GetSelectedText() == 'SelectSubPackage':  self.CallTipShow(pos, 'Cause the specified sub-package\nto be selected for installation')
            elif self.GetSelectedText() == 'DeSelectSubPackage':self.CallTipShow(pos, 'Cause the specified sub-package\nto be de-selected from installation.')
            elif self.GetSelectedText() == 'If':                self.CallTipShow(pos, 'Begins the control block.')
            elif self.GetSelectedText() == 'Elif':              self.CallTipShow(pos, 'Elif')
            elif self.GetSelectedText() == 'Else':              self.CallTipShow(pos, 'Else')
            elif self.GetSelectedText() == 'EndIf':             self.CallTipShow(pos, 'Signals the end of the If control block.')
            elif self.GetSelectedText() == 'False':             self.CallTipShow(pos, 'False')
            elif self.GetSelectedText() == 'True':              self.CallTipShow(pos, 'True')
            elif self.GetSelectedText() == '|Default Character':self.CallTipShow(pos, '|Default Character')
            elif self.GetSelectedText() == '; Comment':         self.CallTipShow(pos, '; Comment')
            elif self.GetSelectedText() == 'DataFileExists':    self.CallTipShow(pos, 'Tests for the existance of a file in the Data directory.')
            elif self.GetSelectedText() == 'SelectEspm':        self.CallTipShow(pos, 'Cause the specified esp or esm\nto be selected for installation.')
            elif self.GetSelectedText() == 'SelectAllEspms':    self.CallTipShow(pos, 'Cause all esps and esms to\nbe selected for installation.')
            elif self.GetSelectedText() == 'DeSelectEspm':      self.CallTipShow(pos, 'Cause the specified esp or esm\nto be deselected from installation.')
            elif self.GetSelectedText() == 'DeSelectAllEspms':  self.CallTipShow(pos, 'Cause all esps and esms to be\nde-selected from installation.')
            elif self.GetSelectedText() == 'RenameEspm':        self.CallTipShow(pos, 'Change the installed name of an esp or esm.')
            elif self.GetSelectedText() == 'ResetEspmName':     self.CallTipShow(pos, 'Resets the name of an esp or esm\nback to its default name.')
            elif self.GetSelectedText() == 'ResetAllEspmNames': self.CallTipShow(pos, 'Resets the names of all the esps and\nesms back to their default names. ')
            elif self.GetSelectedText() == 'RequireVersions':   self.CallTipShow(pos, 'The RequireVersions dialog will show up if the wizard \nspecified minimum version requirements, and your \nsystem doesn\'t meet those requirements.')
            elif self.GetSelectedText() == 'Cancel':            self.CallTipShow(pos, 'The Cancel dialog will be shown if the wizard\ncancels execution for some reason.\nIf a reason is given, it will be displayed.')
            elif self.GetSelectedText() == 'Note':              self.CallTipShow(pos, 'Add a note to the user to be displayed\nat the end of the wizard, on the finish page.')
            elif self.GetSelectedText() == 'Return':            self.CallTipShow(pos, 'Signals completion of the wizard.\nThis will jump right to the finish page. ')
            elif self.GetSelectedText() == 'CompareObVersion':  self.CallTipShow(pos, 'CompareObVersion')
            elif self.GetSelectedText() == 'CompareOBSEVersion':self.CallTipShow(pos, 'CompareOBSEVersion')
            elif self.GetSelectedText() == 'CompareOBGEVersion':self.CallTipShow(pos, 'CompareOBGEVersion')
            elif self.GetSelectedText() == 'CompareWBVersion':  self.CallTipShow(pos, 'CompareWBVersion')
            elif self.GetSelectedText() == 'str':               self.CallTipShow(pos, 'Used to convert a value into a string,\nfor example when trying to concantenate\na integer or decimal to a string.')
            elif self.GetSelectedText() == 'int':               self.CallTipShow(pos, 'Used to convert a value to an integer,\nfor example converting a value held in a\nstring to a integer value. ')
            elif self.GetSelectedText() == 'float':             self.CallTipShow(pos, 'Used to convert a value to decimal, for\nexample converting a value held in a\nstring to a decimal value. ')
            elif self.GetSelectedText() == 'len':               self.CallTipShow(pos, 'Used to find the length of a string.')
            elif self.GetSelectedText() == 'lower':             self.CallTipShow(pos, 'lower')
            elif self.GetSelectedText() == 'For':               self.CallTipShow(pos, 'For')
            elif self.GetSelectedText() == 'EndFor':            self.CallTipShow(pos, 'EndFor')
            elif self.GetSelectedText() == 'While':             self.CallTipShow(pos, 'While')
            elif self.GetSelectedText() == 'EndWhile':          self.CallTipShow(pos, 'EndWhile')
            elif self.GetSelectedText() == 'Continue':          self.CallTipShow(pos, 'Continue')
            elif self.GetSelectedText() == 'GetEspmStatus':     self.CallTipShow(pos, 'Tests the current status of an esp or espm\nin the Data directory. This function takes esp/m\nghosting into account when testing the status.')
            else:
                pass

    def OnSTCGainFocus(self, event):
        self.SetSTCFocus(True)
        # print ('GetSTCFocus = ' + str(self.GetSTCFocus()))

    def OnSTCLoseFocus(self, event):
        ''' Cancel any modes such as call tip or auto-completion list display.
        This Closes the calltips and auto completion boxes from always staying on
        top if switching to another application window OutofApp(such as photoshop, etc).
        Also works for other dialogs InApp. '''
        self.SetSTCFocus(False)
        # print ('GetSTCFocus = ' + str(self.GetSTCFocus()))
        self.Cancel()

    def OnShowWordCompleteBox(self, event):
        ''' Show a Auto-Completeion box with all the words in the document. '''
        text = self.GetText()
        replaceThisList = ['.','!','?',',',':',';',
                           '\'','"',
                           '/','\\',
                           '[',']','<','>','(',')','{','}',
                           '=','+','-',
                           '_','@','#','$','%','^','&','*','|','`','~',
                           '\n','\t']
        for char in replaceThisList:
            text = text.replace(char, ' ')
        words = list(set(text.split(' ')))

        # print words

        kw = words
        kw.sort()

        # # print self.AutoCompGetMaxWidth()
        # self.AutoCompSetMaxWidth(0)
        # # print self.AutoCompGetMaxHeight()
        # self.AutoCompSetMaxHeight(9)

        # No need to seperate lowercase words from capitalcase or uppercase words
        self.AutoCompSetIgnoreCase(False)
        self.AutoCompShow(0, ' '.join(kw))

    def OnAutoCompSelection(self, event):
        self.autocompflag = 1
        # print ('OnAutoCompSelection')

    def OnShowAutoCompleteBox(self, event):
        '''Shows the Auto-Complete Box in the editor filled with wizard script keywords.'''
        if basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
            kw = keywordWIZBAIN.kwlist[:] + keywordWIZBAIN2.kwlist[:]
            # Optionally add more ...
            kw.append('__U__SePeRaToR__l__?')
            # Python sorts are case sensitive
            kw.sort()
            # So this needs to match
            self.AutoCompSetIgnoreCase(False)
            self.AutoCompSetChooseSingle(True) #Should a single item auto-completion list automatically choose the item.

            # # print self.AutoCompGetMaxWidth()
            # self.AutoCompSetMaxWidth(0)
            # # print self.AutoCompGetMaxHeight()
            # self.AutoCompSetMaxHeight(9)

            # Registered images are specified with appended '?type'
            for i in range(len(kw)):
                if kw[i] in keywordWIZBAIN.kwlist or keywordWIZBAIN2.kwlist:
                    kw[i] = kw[i] + '?5'
            self.AutoCompShow(0, ' '.join(kw))

    def OnRMouseGestureMenu4(self, event):
        ''' Call the Right Mouse Gesture Menu.
        NUMPAD:4
        [7][8][9]
        [@][5][6]
        [1][2][3]
        '''
        rightclickmenu = wx.Menu()

        p = wx.BITMAP_TYPE_PNG

        rcheader1 = wx.MenuItem(rightclickmenu, 0000, u'&R MGM 4 Case', u'ContextMenu4')
        rcheader1.SetBackgroundColour('#000000')
        rightclickmenu.AppendItem(rcheader1)
        rcheader1.SetDisabledBitmap(self.rmbImg)
        rcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            if i == 4:#The currently open menu
                mgm = wx.MenuItem(rightclickmenu, self.rmgmIDs[i-1], u'&R MGM %s You Are Here!'%str(i), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(self.yahImg)
                mgm.SetBackgroundColour('#F4FAB4')
                mgm.Enable(False)
            else:
                mgm = wx.MenuItem(rightclickmenu, self.rmgmIDs[i-1], u'&R MGM %s %s'%(str(i),self.rmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(self.mgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(rightclickmenu, ID_MMGM5, u'&M MGM 5 Macro', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(self.mgmImg)
        submenu.AppendItem(mgm)
        rightclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        rightclickmenu.AppendSeparator()

        uppercase = wx.MenuItem(rightclickmenu, ID_UPPERCASE, '&UPPER CASE', ' Change Selected text to all UPPER CASE')
        uppercase.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'uppercase16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(uppercase)
        lowercase = wx.MenuItem(rightclickmenu, ID_LOWERCASE, '&lower case', ' Change Selected text to all lower case')
        lowercase.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'lowercase16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(lowercase)
        invertcase = wx.MenuItem(rightclickmenu, ID_INVERTCASE, '&iNVERT cASE', ' Invert Case of Selected text')
        invertcase.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'invertcase2416.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(invertcase)
        capitalcase = wx.MenuItem(rightclickmenu, ID_CAPITALCASE, '&Capital Case', ' Change Selected text to all Capital Case(words)')
        capitalcase.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'capitalcase16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(capitalcase)

        #events
        wx.EVT_MENU(rightclickmenu, ID_UPPERCASE, self.OnUPPERCASE)
        wx.EVT_MENU(rightclickmenu, ID_LOWERCASE, self.Onlowercase)
        wx.EVT_MENU(rightclickmenu, ID_INVERTCASE, self.OnInvertCase)
        wx.EVT_MENU(rightclickmenu, ID_CAPITALCASE, self.OnCapitalCase)

        wx.EVT_MENU(rightclickmenu, ID_RMGM1, self.OnRMouseGestureMenu1)
        wx.EVT_MENU(rightclickmenu, ID_RMGM2, self.OnRMouseGestureMenu2)
        wx.EVT_MENU(rightclickmenu, ID_RMGM3, self.OnRMouseGestureMenu3)
        wx.EVT_MENU(rightclickmenu, ID_RMGM4, self.OnRMouseGestureMenu4)
        wx.EVT_MENU(rightclickmenu, ID_RMGM5, self.OnRMouseGestureMenuNone)
        wx.EVT_MENU(rightclickmenu, ID_RMGM6, self.OnRMouseGestureMenu6)
        wx.EVT_MENU(rightclickmenu, ID_RMGM7, self.OnRMouseGestureMenu7)
        wx.EVT_MENU(rightclickmenu, ID_RMGM8, self.OnRMouseGestureMenu8)
        wx.EVT_MENU(rightclickmenu, ID_RMGM9, self.OnRMouseGestureMenu9)

        wx.EVT_MENU(rightclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        self.PopupMenu(rightclickmenu)
        rightclickmenu.Destroy()

    def OnRMouseGestureMenu6(self, event):
        ''' Call the Right Mouse Gesture Menu.
        NUMPAD:6
        [7][8][9]
        [4][5][@]
        [1][2][3]
        '''
        rightclickmenu = wx.Menu()

        p = wx.BITMAP_TYPE_PNG

        rcheader1 = wx.MenuItem(rightclickmenu, 0000, u'&R MGM 6 Conversion', u'ContextMenu6')
        rcheader1.SetBackgroundColour('#000000')
        rightclickmenu.AppendItem(rcheader1)
        rcheader1.SetDisabledBitmap(self.rmbImg)
        rcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            if i == 6:#The currently open menu
                mgm = wx.MenuItem(rightclickmenu, self.rmgmIDs[i-1], u'&R MGM %s You Are Here!'%str(i), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(self.yahImg)
                mgm.SetBackgroundColour('#F4FAB4')
                mgm.Enable(False)
            else:
                mgm = wx.MenuItem(rightclickmenu, self.rmgmIDs[i-1], u'&R MGM %s %s'%(str(i),self.rmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(self.mgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(rightclickmenu, ID_MMGM5, u'&M MGM 5 Macro', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(self.mgmImg)
        submenu.AppendItem(mgm)
        rightclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        rightclickmenu.AppendSeparator()

        txt2wizstrfiledrop = wx.MenuItem(rightclickmenu, ID_TXT2WIZSTRFILE, u'& Txt2WizStr (FileDrop)', u' Txt2WizStr (FileDrop)')
        txt2wizstrfiledrop.SetBitmap(wx.Image(self.imgDir + os.sep + 'wizard.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(txt2wizstrfiledrop)

        txt2wizstrtextdrop = wx.MenuItem(rightclickmenu, ID_TXT2WIZSTRTEXT, u'& Txt2WizStr (TextDrop)', u' Txt2WizStr (TextDrop)')
        txt2wizstrtextdrop.SetBitmap(wx.Image(self.imgDir + os.sep + 'wizard.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(txt2wizstrtextdrop)

        ## hmmm = wx.MenuItem(rightclickmenu, 9999, u'&Needs Label && ID', u' StatusText Description Here')
        ## hmmm.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'black16.png'),p).ConvertToBitmap())
        ## rightclickmenu.AppendItem(hmmm)

        ## hmmm = wx.MenuItem(rightclickmenu, 9999, u'&Needs Label && ID', u' StatusText Description Here')
        ## hmmm.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'black16.png'),p).ConvertToBitmap())
        ## rightclickmenu.AppendItem(hmmm)

        #events
        wx.EVT_MENU(rightclickmenu, ID_TXT2WIZSTRFILE, self.OnTextToWizardStringFileDropMiniFrame)
        wx.EVT_MENU(rightclickmenu, ID_TXT2WIZSTRTEXT, self.OnTextToWizardStringTextDropMiniFrame)

        wx.EVT_MENU(rightclickmenu, ID_RMGM1, self.OnRMouseGestureMenu1)
        wx.EVT_MENU(rightclickmenu, ID_RMGM2, self.OnRMouseGestureMenu2)
        wx.EVT_MENU(rightclickmenu, ID_RMGM3, self.OnRMouseGestureMenu3)
        wx.EVT_MENU(rightclickmenu, ID_RMGM4, self.OnRMouseGestureMenu4)
        wx.EVT_MENU(rightclickmenu, ID_RMGM5, self.OnRMouseGestureMenuNone)
        wx.EVT_MENU(rightclickmenu, ID_RMGM6, self.OnRMouseGestureMenu6)
        wx.EVT_MENU(rightclickmenu, ID_RMGM7, self.OnRMouseGestureMenu7)
        wx.EVT_MENU(rightclickmenu, ID_RMGM8, self.OnRMouseGestureMenu8)
        wx.EVT_MENU(rightclickmenu, ID_RMGM9, self.OnRMouseGestureMenu9)

        wx.EVT_MENU(rightclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        self.PopupMenu(rightclickmenu)
        rightclickmenu.Destroy()

    def OnRMouseGestureMenu7(self, event):
        ''' Call the Right Mouse Gesture Menu.
        NUMPAD:7
        [@][8][9]
        [4][5][6]
        [1][2][3]
        '''
        rightclickmenu = wx.Menu()

        p = wx.BITMAP_TYPE_PNG

        rcheader1 = wx.MenuItem(rightclickmenu, 0000, u'&R MGM 7 Project Manipulation (NOT DONE)', u'ContextMenu7')
        rcheader1.SetBackgroundColour('#000000')
        rightclickmenu.AppendItem(rcheader1)
        rcheader1.SetDisabledBitmap(self.rmbImg)
        rcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            if i == 7:#The currently open menu
                mgm = wx.MenuItem(rightclickmenu, self.rmgmIDs[i-1], u'&R MGM %s You Are Here!'%str(i), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(self.yahImg)
                mgm.SetBackgroundColour('#F4FAB4')
                mgm.Enable(False)
            else:
                mgm = wx.MenuItem(rightclickmenu, self.rmgmIDs[i-1], u'&R MGM %s %s'%(str(i),self.rmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(self.mgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(rightclickmenu, ID_MMGM5, u'&M MGM 5 Macro', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(self.mgmImg)
        submenu.AppendItem(mgm)
        rightclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        rightclickmenu.AppendSeparator()

        currentpackagename = u'%s' %basher.gInstallers.gPackage.GetValue()

        # > Can't be a directory or filename character...at least on windows...so
        currentpackage = wx.MenuItem(rightclickmenu, wx.NewId(), u'&Current Package>>> %s' %currentpackagename, u' Current Package Name')
        currentpackage.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'test16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(currentpackage)
        currentpackage.Enable(False)

        activeproject = wx.MenuItem(rightclickmenu, 9999, u'&Active Project>>> %s' %basher.settings['bash.installers.wizSTC.ActiveProject'], u' Active Project')
        activeproject.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'test16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(activeproject)
        activeproject.Enable(False)

        submenu = wx.Menu()
        setactiveproject = wx.MenuItem(rightclickmenu, 9999, u'&None Needs Label && ID', u' Set Active Project To None')
        setactiveproject.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'test16.png'),p).ConvertToBitmap())
        submenu.AppendItem(setactiveproject)
        rightclickmenu.AppendMenu(wx.NewId(), u'Set Active Project To... Needs Label && ID', submenu)

        createnewproject = wx.MenuItem(rightclickmenu, 9999, u'&Create New Project...Needs Label && ID', u' StatusText Description Here')
        createnewproject.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'test16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(createnewproject)

        rightclickmenu.AppendSeparator()

        hmmm = wx.MenuItem(rightclickmenu, 9999, u'&Copy SubPackage to Active Project...Needs Label && ID', u' StatusText Description Here')
        hmmm.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'black16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(hmmm)

        hmmm = wx.MenuItem(rightclickmenu, 9999, u'&Copy Espm to Active Project...Needs Label && ID', u' StatusText Description Here')
        hmmm.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'black16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(hmmm)

        hmmm = wx.MenuItem(rightclickmenu, 9999, u'&Copy All to Active Project(exc. wizard)...Needs Label && ID', u' StatusText Description Here')
        hmmm.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'black16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(hmmm)

        hmmm = wx.MenuItem(rightclickmenu, 9999, u'&Append Current Package\'s wizard.txt to Active Project\'s blizzard.wiz Needs Label && ID', u' Mergify wiz/blizz')
        hmmm.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'black16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(hmmm)

        hmmm = wx.MenuItem(rightclickmenu, 9999, u'&Needs Label && ID', u' StatusText Description Here')
        hmmm.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'black16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(hmmm)


        #events
        wx.EVT_MENU(rightclickmenu, ID_RMGM1, self.OnRMouseGestureMenu1)
        wx.EVT_MENU(rightclickmenu, ID_RMGM2, self.OnRMouseGestureMenu2)
        wx.EVT_MENU(rightclickmenu, ID_RMGM3, self.OnRMouseGestureMenu3)
        wx.EVT_MENU(rightclickmenu, ID_RMGM4, self.OnRMouseGestureMenu4)
        wx.EVT_MENU(rightclickmenu, ID_RMGM5, self.OnRMouseGestureMenuNone)
        wx.EVT_MENU(rightclickmenu, ID_RMGM6, self.OnRMouseGestureMenu6)
        wx.EVT_MENU(rightclickmenu, ID_RMGM7, self.OnRMouseGestureMenu7)
        wx.EVT_MENU(rightclickmenu, ID_RMGM8, self.OnRMouseGestureMenu8)
        wx.EVT_MENU(rightclickmenu, ID_RMGM9, self.OnRMouseGestureMenu9)

        wx.EVT_MENU(rightclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        self.PopupMenu(rightclickmenu)
        rightclickmenu.Destroy()

    def OnRMouseGestureMenu8(self, event):
        ''' Call the Right Mouse Gesture Menu.
        NUMPAD:8
        [7][@][9]
        [4][5][6]
        [1][2][3]
        '''
        rightclickmenu = wx.Menu()

        p = wx.BITMAP_TYPE_PNG

        rcheader1 = wx.MenuItem(rightclickmenu, 0000, u'&R MGM 8 Line Operations', u'ContextMenu8')
        rcheader1.SetBackgroundColour('#000000')
        rightclickmenu.AppendItem(rcheader1)
        rcheader1.SetDisabledBitmap(self.rmbImg)
        rcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            if i == 8:#The currently open menu
                mgm = wx.MenuItem(rightclickmenu, self.rmgmIDs[i-1], u'&R MGM %s You Are Here!'%str(i), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(self.yahImg)
                mgm.SetBackgroundColour('#F4FAB4')
                mgm.Enable(False)
            else:
                mgm = wx.MenuItem(rightclickmenu, self.rmgmIDs[i-1], u'&R MGM %s %s'%(str(i),self.rmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(self.mgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(rightclickmenu, ID_MMGM5, u'&M MGM 5 Macro', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(self.mgmImg)
        submenu.AppendItem(mgm)
        rightclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        rightclickmenu.AppendSeparator()

        newlinebefore = wx.MenuItem(rightclickmenu, ID_NEWLINEBEFORE, u'&New Line Before', u' Insert a new line before the current line.')
        newlinebefore.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'newlinebefore16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(newlinebefore)

        newlineafter = wx.MenuItem(rightclickmenu, ID_NEWLINEAFTER, u'&New Line After', u' Insert a new line after the current line.')
        newlineafter.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'newlineafter16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(newlineafter)

        cutline = wx.MenuItem(rightclickmenu, ID_CUTLINE, u'&Cut Line', u' Cut the current line to the clipboard.')
        cutline.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'cutline16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(cutline)

        copyline = wx.MenuItem(rightclickmenu, ID_COPYLINE, u'&Copy Line', u' Copy the current line to the clipboard.')
        copyline.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'copyline16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(copyline)

        deleteline = wx.MenuItem(rightclickmenu, ID_DELETELINE, u'&Delete Line\tCtrl+L', u' Delete the current line.')
        deleteline.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'deleteline16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(deleteline)

        deletelinecontents = wx.MenuItem(rightclickmenu, ID_DELETELINECONTENTS, u'&Delete Line Contents', u' Delete the contents of the current line.')
        deletelinecontents.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'deleteline16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(deletelinecontents)

        selectline = wx.MenuItem(rightclickmenu, ID_SELECTLINENOEOL, u'&Select Line(without EOL)', u' Select the contents of the caret line without EOL chars.')
        selectline.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'selectline16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(selectline)

        duplicateline = wx.MenuItem(rightclickmenu, ID_DUPLICATELINE, u'&Duplicate Line', u' Duplicate the current line.')
        duplicateline.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'duplicateline16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(duplicateline)

        duplicateselectionline = wx.MenuItem(rightclickmenu, ID_DUPLICATESELECTIONLINE, u'&Duplicate Selection/Line\tCtrl+D', u' Duplicate the selection. If the selection is empty, it duplicates the line containing the caret.')
        duplicateselectionline.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'duplicateselectionline16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(duplicateselectionline)

        duplicatelinentimes = wx.MenuItem(rightclickmenu, ID_DUPLICATELINENTIMES, u'&Duplicate Line n Times', u' Duplicate the current line n times.')
        duplicatelinentimes.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'duplicateselectionline16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(duplicatelinentimes)

        joinlines = wx.MenuItem(rightclickmenu, ID_JOINLINES, u'&Join Lines', u' Join the currently selected lines.')
        joinlines.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'joinlines16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(joinlines)

        splitlines = wx.MenuItem(rightclickmenu, ID_SPLITLINES, u'&Split Lines', u' Split the lines in the target into lines that are less wide than pixelWidth where possible.')
        splitlines.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'splitlines16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(splitlines)

        switcheroolinetranspose = wx.MenuItem(rightclickmenu, ID_LINETRANSPOSE, u'&Line Transpose\tCtrl+T', u' Switcheroo the current line with the previous.')
        switcheroolinetranspose.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'linetranspose16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(switcheroolinetranspose)

        movelineup = wx.MenuItem(rightclickmenu, ID_MOVELINEUP, u'&Move Line Up\tCtrl+Shift+Up', u' Move the current line up.')
        movelineup.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'arrowupbw16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(movelineup)

        movelinedown = wx.MenuItem(rightclickmenu, ID_MOVELINEDOWN, u'&Move Line Down\tCtrl+Shift+Down', u' Move the current line down.')
        movelinedown.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'arrowdownbw16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(movelinedown)

        appendselectedlineswithastring = wx.MenuItem(rightclickmenu, ID_APPENDLINESSTR, u'&Append Selected Line(s) with a string', u' Append Selected Line(s) with a string.')
        appendselectedlineswithastring.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'append16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(appendselectedlineswithastring)

        removestringfromendoflines = wx.MenuItem(rightclickmenu, ID_REMOVESTRENDLINES, u'&Remove string from end of selected lines', u' Remove a user-defined string from the end of selected lines.')
        removestringfromendoflines.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'remove16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(removestringfromendoflines)

        removestringfromstartoflines = wx.MenuItem(rightclickmenu, ID_REMOVESTRSTARTLINES, u'&Remove string from start of lines', u' Remove a user-defined string from the start of selected lines.')
        removestringfromstartoflines.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'remove16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(removestringfromstartoflines)

        padwithspaces = wx.MenuItem(rightclickmenu, ID_PADWITHSPACES, u'&Pad With Spaces(selected lines)', u' Pad selected lines with spaces to the longest column width')
        padwithspaces.SetBitmap(wx.Image(self.imgstcDir + os.sep + u'padwithspaces16.png',p).ConvertToBitmap())
        rightclickmenu.AppendItem(padwithspaces)



        #events
        wx.EVT_MENU(rightclickmenu, ID_NEWLINEBEFORE, self.OnNewLineBefore)
        wx.EVT_MENU(rightclickmenu, ID_NEWLINEAFTER, self.OnNewLineAfter)
        wx.EVT_MENU(rightclickmenu, ID_CUTLINE, self.OnLineCut)
        wx.EVT_MENU(rightclickmenu, ID_COPYLINE, self.OnLineCopy)
        wx.EVT_MENU(rightclickmenu, ID_DELETELINE, self.OnLineDelete)
        wx.EVT_MENU(rightclickmenu, ID_DELETELINECONTENTS, self.OnDeleteLineContents)
        wx.EVT_MENU(rightclickmenu, ID_SELECTLINENOEOL, self.OnLineSelect)
        wx.EVT_MENU(rightclickmenu, ID_DUPLICATELINE, self.OnLineDuplicate)
        wx.EVT_MENU(rightclickmenu, ID_DUPLICATESELECTIONLINE, self.OnDuplicateSelectionLine)
        wx.EVT_MENU(rightclickmenu, ID_DUPLICATELINENTIMES, self.OnLineDuplicateNTimes)
        wx.EVT_MENU(rightclickmenu, ID_JOINLINES, self.OnLinesJoin)
        wx.EVT_MENU(rightclickmenu, ID_SPLITLINES, self.OnLinesSplit)
        wx.EVT_MENU(rightclickmenu, ID_LINETRANSPOSE, self.OnLineTranspose)
        wx.EVT_MENU(rightclickmenu, ID_MOVELINEUP, self.OnMoveLineUp)
        wx.EVT_MENU(rightclickmenu, ID_MOVELINEDOWN, self.OnMoveLineDown)
        wx.EVT_MENU(rightclickmenu, ID_APPENDLINESSTR, self.OnAppendSelectedLinesWithAString)
        wx.EVT_MENU(rightclickmenu, ID_REMOVESTRENDLINES, self.OnRemoveStringFromEndOfSelectedLines)
        wx.EVT_MENU(rightclickmenu, ID_REMOVESTRSTARTLINES, self.OnRemoveStringFromStartOfSelectedLines)

        wx.EVT_MENU(rightclickmenu, ID_PADWITHSPACES, self.OnPadWithSpacesSelectedLines)

        wx.EVT_MENU(rightclickmenu, ID_RMGM1, self.OnRMouseGestureMenu1)
        wx.EVT_MENU(rightclickmenu, ID_RMGM2, self.OnRMouseGestureMenu2)
        wx.EVT_MENU(rightclickmenu, ID_RMGM3, self.OnRMouseGestureMenu3)
        wx.EVT_MENU(rightclickmenu, ID_RMGM4, self.OnRMouseGestureMenu4)
        wx.EVT_MENU(rightclickmenu, ID_RMGM5, self.OnRMouseGestureMenuNone)
        wx.EVT_MENU(rightclickmenu, ID_RMGM6, self.OnRMouseGestureMenu6)
        wx.EVT_MENU(rightclickmenu, ID_RMGM7, self.OnRMouseGestureMenu7)
        wx.EVT_MENU(rightclickmenu, ID_RMGM8, self.OnRMouseGestureMenu8)
        wx.EVT_MENU(rightclickmenu, ID_RMGM9, self.OnRMouseGestureMenu9)

        wx.EVT_MENU(rightclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        self.PopupMenu(rightclickmenu)
        rightclickmenu.Destroy()


    def OnNewLineBefore(self, event):
        ''' Insert a new line before the current line. '''
        self.HomeDisplay()
        self.CharLeft()
        self.NewLine()
        self.SetFocus()

    def OnNewLineAfter(self, event):
        ''' Insert a new line after the current line. '''
        self.LineEndDisplay()
        self.NewLine()
        self.SetFocus()

    def OnLineCut(self, event):
        ''' Cut the line containing the caret. '''
        self.LineCut()

    def OnLineCopy(self, event):
        ''' Copy the line containing the caret. '''
        self.LineCopy()

    def OnLineDelete(self, event, nTimes=1):
        ''' Delete the line containing the caret. '''
        for i in range(0,nTimes):
            self.LineDelete()

    def OnDeleteLineContents(self, event):
        ''' Delete the contents of the line containing the caret, but not the line itself.'''
        self.OnLineSelect(event)
        self.DeleteBackNotLine()

    def OnLineSelect(self, event):
        ''' Select the contents of the caret line, but without the EOL char(s). '''
        linefrompos = self.LineFromPosition(self.GetCurrentPos())
        firstposcurline = self.PositionFromLine(linefrompos)
        lengthline = len(self.GetLine(linefrompos))
        if self.GetEOLMode() == 0: self.SetSelection(firstposcurline,firstposcurline+lengthline-2)#Minus 2 for Dos/Windows CRLF chars
        else: self.SetSelection(firstposcurline,firstposcurline+lengthline-1)#Minus 1 for CR or LF EOL char

    def OnLineDuplicate(self, event):
        ''' Duplicate the current line. '''
        self.LineDuplicate()

    def OnLineDuplicateNTimes(self, event):
        ''' Duplicate the current line n times. '''
        dialog = wx.TextEntryDialog(self, u'Example:\n\nDuplicate this line\nDuplicate this line\nDuplicate this line\netc...\n\nEnter the number of times you want to duplicate the current line.', u'Duplicate Line n Times', u'')
        if dialog.ShowModal() == wx.ID_OK:
            try:
                self.BeginUndoAction()
                n = dialog.GetValue()
                for i in range(0,int(n)):
                    self.LineDuplicate()
                self.EndUndoAction()
            except:
                wx.Bell()
                self.OnLineDuplicateNTimes(event)

    def OnDuplicateSelectionLine(self, event):
        ''' Duplicate the selection. If selection empty duplicate the line containing the caret. '''
        self.SelectionDuplicate()

    def OnLinesJoin(self, event):
        targettojoin = self.TargetFromSelection()
        self.LinesJoin()

    def OnLinesSplit(self, event):
        ''' Split the lines in the target into lines that are less wide than pixelWidth where possible. '''
        self.TargetFromSelection()
        self.LinesSplit(-1)

    def OnLineTranspose(self, event):
        ''' Switch the current line with the previous. '''
        self.BeginUndoAction()
        self.LineTranspose()
        self.EndUndoAction()

    def OnMoveLineUp(self, event):
        ''' Move the current line up. '''
        linenum = self.GetCurrentLine()
        if linenum > 0 :
            self.BeginUndoAction()
            self.LineTranspose()
            self.LineUp()
            self.EndUndoAction()

    def OnMoveLineDown(self, event):
        ''' Move the current line down. '''
        linenum = self.GetCurrentLine()
        if linenum < self.GetLineCount() - 1:
            self.BeginUndoAction()
            self.LineDown()
            self.LineTranspose()
            self.EndUndoAction()

    def OnAppendSelectedLinesWithAString(self, event):
        ''' Call a dialog asking the user for a string to append to the end of selected line(s) '''
        dialog = wx.TextEntryDialog(self, u'line1 Append A String\nline2 Append A String\nline3 Append A String\netc...', u'Append (selected lines) with a string', u' Append A String')
        if dialog.ShowModal() == wx.ID_OK:
            self.BeginUndoAction()
            appendselstring = dialog.GetValue()

            selstart = self.GetSelectionStart()
            selend = self.GetSelectionEnd()
            startline = self.LineFromPosition(selstart)
            endline = self.LineFromPosition(selend)
            for i in range(startline, endline+1):
                self.GotoPos(self.GetLineEndPosition(i))
                self.AddText(appendselstring)
            self.EndUndoAction()
        dialog.Destroy()

    def OnRemoveStringFromEndOfSelectedLines(self, event):
        ''' Call a dialog asking the user for a string to remove from the end of selected line(s) '''
        dialog = wx.TextEntryDialog(self, u'ExampleString to remove:ing\n\nline(s) Remove A String\nbecomes\nline(s) Remove A Str\netc...\n\nNote: Does not strip trailing whitespace!', u'Remove String from end of Selected Lines', u' Remove End String')
        if dialog.ShowModal() == wx.ID_OK:
            self.BeginUndoAction()
            removeendselstring = dialog.GetValue()

            selstart = self.GetSelectionStart()
            selend = self.GetSelectionEnd()
            startline = self.LineFromPosition(selstart)
            endline = self.LineFromPosition(selend)
            for i in range(startline, endline+1):
                self.GotoPos(self.GetLineEndPosition(i))
                linestring = self.GetLine(i).rstrip('\n')
                if linestring.endswith(removeendselstring):
                    for i in range(0, len(removeendselstring)):
                        self.DeleteBack()
            self.EndUndoAction()
        dialog.Destroy()

    def OnRemoveStringFromStartOfSelectedLines(self, event):
        ''' Call a dialog asking the user for a string to remove from the beginning of selected line(s) '''
        dialog = wx.TextEntryDialog(self, u'ExampleString to remove:Rem\n\nline(s) Remove A String\nbecomes\nline(s) ove A String\netc...\n\nNote: Leading indentation/whitespace is ignored!', u'Remove String from end of Selected Lines', u' Remove End String')
        if dialog.ShowModal() == wx.ID_OK:
            self.BeginUndoAction()
            removestartselstring = dialog.GetValue()

            selstart = self.GetSelectionStart()
            selend = self.GetSelectionEnd()
            startline = self.LineFromPosition(selstart)
            endline = self.LineFromPosition(selend)
            for i in range(startline, endline+1):
                self.GotoPos(self.GetLineIndentPosition(i))
                linestring = self.GetLine(i).lstrip()
                if linestring.startswith(removestartselstring):
                    for i in range(0, len(removestartselstring)):
                        self.CmdKeyExecute(wx.stc.STC_CMD_CLEAR)
            self.EndUndoAction()
        dialog.Destroy()

    def OnPadWithSpacesSelectedLines(self, event):
        ''' Pad selected lines with spaces to the longest column width. '''
        selstart = self.GetSelectionStart()
        selend = self.GetSelectionEnd()
        startline = self.LineFromPosition(selstart)
        endline = self.LineFromPosition(selend)

        longestcolumnsonaline = 0
        for i in range(startline, endline+1):
            lineendpos = self.GetLineEndPosition(i)
            columnsonline = self.GetColumn(lineendpos)
            if columnsonline > longestcolumnsonaline:
                longestcolumnsonaline = columnsonline

        self.BeginUndoAction()
        for i in range(startline, endline+1):
            lineendpos = self.GetLineEndPosition(i)
            self.GotoPos(lineendpos)
            while self.GetColumn(self.GetCurrentPos()) < longestcolumnsonaline:
                self.AddText(u' ')
        self.EndUndoAction()

    def OnRMouseGestureMenu9(self, event):
        ''' Call the Right Mouse Gesture Menu.
        NUMPAD:9
        [7][8][@]
        [4][5][6]
        [1][2][3]
        '''
        rightclickmenu = wx.Menu()

        p = wx.BITMAP_TYPE_PNG

        rcheader1 = wx.MenuItem(rightclickmenu, 0000, u'&R MGM 9 Options', u'ContextMenu9')
        rcheader1.SetBackgroundColour('#000000')
        rightclickmenu.AppendItem(rcheader1)
        rcheader1.SetDisabledBitmap(self.rmbImg)
        rcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            if i == 9:#The currently open menu
                mgm = wx.MenuItem(rightclickmenu, self.rmgmIDs[i-1], u'&R MGM %s You Are Here!'%str(i), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(self.yahImg)
                mgm.SetBackgroundColour('#F4FAB4')
                mgm.Enable(False)
            else:
                mgm = wx.MenuItem(rightclickmenu, self.rmgmIDs[i-1], u'&R MGM %s %s'%(str(i),self.rmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(self.mgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(rightclickmenu, ID_MMGM5, u'&M MGM 5 Macro', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(self.mgmImg)
        submenu.AppendItem(mgm)
        rightclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        rightclickmenu.AppendSeparator()

        if basher.settings['bash.installers.wizSTC.ViewWhiteSpace'] == 1: IO = u'On*'
        elif basher.settings['bash.installers.wizSTC.ViewWhiteSpace'] == 2: IO = u'Off'
        else: IO = u'On'
        togglewhitespace = wx.MenuItem(rightclickmenu, ID_TOGGLEWHITESPACE, u'&Toggle Whitespace\t%s'%IO, u' Toggle Whitespace')
        togglewhitespace.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'showwhitespace16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(togglewhitespace)

        if basher.settings['bash.installers.wizSTC.IndentationGuides'] == 1: IO = u'Off'
        else: IO = u'On'
        toggleindentguides = wx.MenuItem(rightclickmenu, ID_TOGGLEINDENTGUIDES, u'&Toggle Indent Guides\t%s'%IO, u' Toggle Indent Guides On/Off')
        toggleindentguides.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'showindentationguide16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(toggleindentguides)

        if basher.settings['bash.installers.wizSTC.WordWrap'] == 1: IO = u'Off'
        else: IO = u'On'
        togglewordwrap = wx.MenuItem(rightclickmenu, ID_TOGGLEWORDWRAP, u'&Toggle Wordwrap\t%s'%IO, u' Toggle Wordwrap On/Off')
        togglewordwrap.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'wordwrap16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(togglewordwrap)

        if basher.settings['bash.installers.wizSTC.CaretLineVisible'] == 1: IO = u'Off'
        else: IO = u'On'
        togglehighlightselectedline = wx.MenuItem(rightclickmenu, ID_TOGGLELINEHIGHLIGHT, u'&Toggle Highlight Selected Line\t%s'%IO, u' Toggle Highlight Selected Line')
        togglehighlightselectedline.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'highlightcurrentline16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(togglehighlightselectedline)

        if basher.settings['bash.installers.wizSTC.ViewEOL'] == 1: IO = u'Off'
        else: IO = u'On'
        toggleeolview = wx.MenuItem(rightclickmenu, ID_TOGGLEEOLVIEW, u'&Toggle EOL View\t%s'%IO, u' Toggle Show/Hide End of line characters ')
        toggleeolview.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'eollf16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(toggleeolview)

        if basher.settings['bash.installers.wizSTC.BackSpaceUnIndents'] == 1: IO = u'Off'
        else: IO = u'On'
        togglebackspaceunindents = wx.MenuItem(rightclickmenu, ID_BACKSPACEUNINDENTS, u'&Toggle BackSpace Unindents\t%s'%IO, u' Toggle BackSpace Unindents')
        togglebackspaceunindents.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'backspaceunindents16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(togglebackspaceunindents)

        if basher.settings['bash.installers.wizSTC.BraceCompletion'] == 1: IO = u'Off'
        else: IO = u'On'
        togglebracecompletion = wx.MenuItem(rightclickmenu, ID_BRACECOMPLETION, u'&Toggle Brace Completion \'"({[]})"\'\t%s'%IO, u' Toggle Brace Completion \'"({[]})"\'')
        togglebracecompletion.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'bracecompletion16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(togglebracecompletion)

        if basher.settings['bash.installers.wizSTC.AutoIndentation'] == 1: IO = u'Off'
        else: IO = u'On'
        toggleautoindentation = wx.MenuItem(rightclickmenu, ID_AUTOINDENTATION, u'&Toggle Auto-Indentation\t%s'%IO, u' Toggle Auto-Indentation')
        toggleautoindentation.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'autoindentation16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(toggleautoindentation)

        if basher.settings['bash.installers.wizSTC.LongLineEdgeMode'] == 1: IO = u'=On'
        elif basher.settings['bash.installers.wizSTC.LongLineEdgeMode'] == 2: IO = u'Off'
        else: IO = u'|On'
        toggleedgecolumn = wx.MenuItem(rightclickmenu, ID_EDGECOLUMN, u'&Toggle Edge Column\t%s'%IO, u' Toggle Edge Column')
        toggleedgecolumn.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'edgecolumn16.png'),p).ConvertToBitmap())
        rightclickmenu.AppendItem(toggleedgecolumn)

        ## hmmm = wx.MenuItem(rightclickmenu, 9999, u'&Needs Label,Func && ID', u' StatusText Description Here')
        ## hmmm.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'showlinenumbers16.png'),p).ConvertToBitmap())
        ## rightclickmenu.AppendItem(hmmm)

        rightclickmenu.AppendSeparator()

        submenu_themes = wx.Menu()
        self.themeIDs = [ID_THEMENONE,ID_THEMEDEFAULT,ID_THEMECONSOLE,ID_THEMEOBSIDIAN,ID_THEMEZENBURN,ID_THEMEMONOKAI,ID_THEMEDEEPSPACE,ID_THEMEGREENSIDEUP,ID_THEMETWILIGHT,ID_THEMEULIPAD,ID_THEMEHELLOKITTY,ID_THEMEVIBRANTINK,ID_THEMEBIRDSOFPARIDISE,ID_THEMEBLACKLIGHT,ID_THEMENOTEBOOK]
        self.themeLABELs = ['No Theme','Default','Console','Obsidian','Zenburn','Monokai','Deep Space','Green Side Up','Twilight','UliPad','Hello Kitty','Vibrant Ink','Birds Of Paridise','BlackLight','Notebook']
        for i in range(1,len(self.themeIDs)+1):
            theme = wx.MenuItem(rightclickmenu, self.themeIDs[i-1], u'&%s'%self.themeLABELs[i-1], u' %s Theme'%self.themeLABELs[i-1], kind = wx.ITEM_CHECK)
            theme.SetBitmap(self.chkImg)
            submenu_themes.AppendItem(theme)
            if basher.settings['bash.installers.wizSTC.ThemeOnStartup'] == u'%s' %self.themeLABELs[i-1]: theme.Check(True)
        submenu_themes.AppendSeparator()
        togglethemes = wx.MenuItem(rightclickmenu, ID_TOGGLETHEMES, u'&Toggle Editor Themes\tF12', u' Toggle Editor Themes')
        togglethemes.SetBitmap(wx.Image(self.imgstcDir + os.sep + (u'toggletheme24.png'),p).ConvertToBitmap())
        submenu_themes.AppendItem(togglethemes)
        rightclickmenu.AppendMenu(7900, u'Themes', submenu_themes)

        #events
        wx.EVT_MENU(rightclickmenu, ID_THEMENONE, self.OnNoTheme)
        wx.EVT_MENU(rightclickmenu, ID_THEMEDEFAULT, self.OnDefaultTheme)
        wx.EVT_MENU(rightclickmenu, ID_THEMECONSOLE, self.OnConsoleTheme)
        wx.EVT_MENU(rightclickmenu, ID_THEMEOBSIDIAN, self.OnObsidianTheme)
        wx.EVT_MENU(rightclickmenu, ID_THEMEZENBURN, self.OnZenburnTheme)
        wx.EVT_MENU(rightclickmenu, ID_THEMEMONOKAI, self.OnMonokaiTheme)
        wx.EVT_MENU(rightclickmenu, ID_THEMEDEEPSPACE, self.OnDeepSpaceTheme)
        wx.EVT_MENU(rightclickmenu, ID_THEMEGREENSIDEUP, self.OnGreenSideUpTheme)
        wx.EVT_MENU(rightclickmenu, ID_THEMETWILIGHT, self.OnTwilightTheme)
        wx.EVT_MENU(rightclickmenu, ID_THEMEULIPAD, self.OnUliPadTheme)
        wx.EVT_MENU(rightclickmenu, ID_THEMEHELLOKITTY, self.OnHelloKittyTheme)
        wx.EVT_MENU(rightclickmenu, ID_THEMEVIBRANTINK, self.OnVibrantInkTheme)
        wx.EVT_MENU(rightclickmenu, ID_THEMEBIRDSOFPARIDISE, self.OnBirdsOfParidiseTheme)
        wx.EVT_MENU(rightclickmenu, ID_THEMEBLACKLIGHT, self.OnBlackLightTheme)
        wx.EVT_MENU(rightclickmenu, ID_THEMENOTEBOOK, self.OnNotebookTheme)
        wx.EVT_MENU(rightclickmenu, ID_TOGGLETHEMES, self.OnToggleEditorThemes)

        wx.EVT_MENU(rightclickmenu, ID_TOGGLEWHITESPACE, self.OnViewWhitespace)
        wx.EVT_MENU(rightclickmenu, ID_TOGGLEINDENTGUIDES, self.OnShowIndentationGuides)
        wx.EVT_MENU(rightclickmenu, ID_TOGGLEWORDWRAP, self.OnWordwrap)
        wx.EVT_MENU(rightclickmenu, ID_TOGGLELINEHIGHLIGHT, self.OnHighlightSelectedLine)
        wx.EVT_MENU(rightclickmenu, ID_TOGGLEEOLVIEW, self.OnShowEOL)
        wx.EVT_MENU(rightclickmenu, ID_BACKSPACEUNINDENTS, self.OnBackSpaceUnindents)
        wx.EVT_MENU(rightclickmenu, ID_BRACECOMPLETION, self.OnBraceCompletion)
        wx.EVT_MENU(rightclickmenu, ID_AUTOINDENTATION, self.OnAutoIndentation)
        wx.EVT_MENU(rightclickmenu, ID_EDGECOLUMN, self.OnEdgeColumn)

        wx.EVT_MENU(rightclickmenu, ID_RMGM1, self.OnRMouseGestureMenu1)
        wx.EVT_MENU(rightclickmenu, ID_RMGM2, self.OnRMouseGestureMenu2)
        wx.EVT_MENU(rightclickmenu, ID_RMGM3, self.OnRMouseGestureMenu3)
        wx.EVT_MENU(rightclickmenu, ID_RMGM4, self.OnRMouseGestureMenu4)
        wx.EVT_MENU(rightclickmenu, ID_RMGM5, self.OnRMouseGestureMenuNone)
        wx.EVT_MENU(rightclickmenu, ID_RMGM6, self.OnRMouseGestureMenu6)
        wx.EVT_MENU(rightclickmenu, ID_RMGM7, self.OnRMouseGestureMenu7)
        wx.EVT_MENU(rightclickmenu, ID_RMGM8, self.OnRMouseGestureMenu8)
        wx.EVT_MENU(rightclickmenu, ID_RMGM9, self.OnRMouseGestureMenu9)

        wx.EVT_MENU(rightclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        self.PopupMenu(rightclickmenu)
        rightclickmenu.Destroy()

    def OnViewWhitespace(self, event):
        ''' Toggle whitespace inbetween three modes: Off,On, and On within Indentation. '''
        if   self.GetViewWhiteSpace() == 0:
            self.SetViewWhiteSpace(1)#0,1,or, 2
            basher.settings['bash.installers.wizSTC.ViewWhiteSpace'] = 1
        elif self.GetViewWhiteSpace() == 1:
            self.SetViewWhiteSpace(2)
            basher.settings['bash.installers.wizSTC.ViewWhiteSpace'] = 2
        elif self.GetViewWhiteSpace() == 2:
            self.SetViewWhiteSpace(0)
            basher.settings['bash.installers.wizSTC.ViewWhiteSpace'] = 0
        basher.settings.setChanged('bash.installers.wizSTC.ViewWhiteSpace')

    def OnShowIndentationGuides(self, event):
        '''Toggle the indentation guides in the editor On/Off'''
        if self.GetIndentationGuides() == True:
            self.SetIndentationGuides(False)
            basher.settings['bash.installers.wizSTC.IndentationGuides'] = 0
        else:
            self.SetIndentationGuides(True)
            basher.settings['bash.installers.wizSTC.IndentationGuides'] = 1
        basher.settings.setChanged('bash.installers.wizSTC.IndentationGuides')

    def OnWordwrap(self, event):
        '''Toggle Wordwrapping of the document in the editor On/Off'''
        if self.GetWrapMode() == True:
            self.SetWrapMode(False)
            basher.settings['bash.installers.wizSTC.WordWrap'] = 0
        else:
            self.SetWrapMode(True)
            basher.settings['bash.installers.wizSTC.WordWrap'] = 1
        basher.settings.setChanged('bash.installers.wizSTC.WordWrap')

    def OnHighlightSelectedLine(self, event):
        '''Toggle highlighting the currently selected line(the one with the caret) in the editor On/Off'''
        if self.GetCaretLineVisible() == True:
            self.SetCaretLineVisible(False)
            basher.settings['bash.installers.wizSTC.CaretLineVisible'] = 0
        else:
            self.SetCaretLineVisible(True)
            basher.settings['bash.installers.wizSTC.CaretLineVisible'] = 1
        basher.settings.setChanged('bash.installers.wizSTC.CaretLineVisible')

    def OnShowEOL(self, event):
        ''' Toggle Show/Hide End of line characters '''
        if self.GetViewEOL() == 1:
            self.SetViewEOL(False)
            basher.settings['bash.installers.wizSTC.ViewEOL'] = 0
        elif self.GetViewEOL() == 0:
            self.SetViewEOL(True)
            basher.settings['bash.installers.wizSTC.ViewEOL'] = 1
        basher.settings.setChanged('bash.installers.wizSTC.ViewEOL')

    def OnBackSpaceUnindents(self, event):
        ''' Toggle option that sets whether a backspace pressed when caret is within indentation unindents. '''
        if self.GetBackSpaceUnIndents() == 1:
            self.SetBackSpaceUnIndents(False)
            basher.settings['bash.installers.wizSTC.BackSpaceUnIndents'] = 0
        elif self.GetBackSpaceUnIndents() == 0:
            self.SetBackSpaceUnIndents(True)
            basher.settings['bash.installers.wizSTC.BackSpaceUnIndents'] = 1
        basher.settings.setChanged('bash.installers.wizSTC.BackSpaceUnIndents')

    def OnBraceCompletion(self, event):
        ''' Toggle brace completion on and off. Baces: '"{([])}"' '''
        bc = basher.settings['bash.installers.wizSTC.BraceCompletion']
        if bc == 1:
            basher.settings['bash.installers.wizSTC.BraceCompletion'] = 0
        elif bc == 0:
            basher.settings['bash.installers.wizSTC.BraceCompletion'] = 1
        basher.settings.setChanged('bash.installers.wizSTC.BraceCompletion')

    def OnAutoIndentation(self, event):
        ''' Toggle auto-indentation on and off. '''
        ai = basher.settings['bash.installers.wizSTC.AutoIndentation']
        if ai == 1:
            basher.settings['bash.installers.wizSTC.AutoIndentation'] = 0
        elif ai == 0:
            basher.settings['bash.installers.wizSTC.AutoIndentation'] = 1
        basher.settings.setChanged('bash.installers.wizSTC.AutoIndentation')

    def OnEdgeColumn(self, event):
        ''' Toggle the long line edge column in the editor On/Off through the three different modes.
        The edge may be displayed by a line (EDGE_LINE) or by highlighting text that goes beyond
        it (EDGE_BACKGROUND) or not displayed at all (EDGE_NONE).'''
        if basher.settings['bash.installers.wizSTC.LineEdgeModeAsColumnMarker'] == 1: pass
        else:
            self.SetEdgeColumn(basher.settings['bash.installers.wizSTC.LongLineEdge'])

            if self.GetEdgeMode() == 0:   #stc.STC_EDGE_NONE
                self.SetEdgeMode(stc.STC_EDGE_LINE)
                basher.settings['bash.installers.wizSTC.LongLineEdgeMode'] = stc.STC_EDGE_LINE
            elif self.GetEdgeMode() == 1: #stc.STC_EDGE_LINE
                self.SetEdgeMode(stc.STC_EDGE_BACKGROUND)
                basher.settings['bash.installers.wizSTC.LongLineEdgeMode'] = stc.STC_EDGE_BACKGROUND
            elif self.GetEdgeMode() == 2: #stc.STC_EDGE_BACKGROUND
                self.SetEdgeMode(stc.STC_EDGE_NONE)
                basher.settings['bash.installers.wizSTC.LongLineEdgeMode'] = stc.STC_EDGE_NONE
            basher.settings.setChanged('bash.installers.wizSTC.LongLineEdgeMode')

    def OnSetFolderMarginStyle(self, event):#Called after STC is initialised MainWindow Initial Startup. Not sure why but calling it here in the class causes the fold symbols to not work quite properly at startup...
        ''' Setup of fold margin colors and styles before calling on of the OnFolderMarginStyle# functions. '''
        tos = basher.settings['bash.installers.wizSTC.ThemeOnStartup']
        fms = basher.settings['bash.installers.wizSTC.FolderMarginStyle']
        if   tos == 'No Theme':          Color1 = '#000000'; Color2 = '#FFFFFF'
        elif tos == 'Default':           Color1 = '#000000'; Color2 = '#32CC99'#medium aquamarine
        elif tos == 'Console':           Color1 = '#BBBBBB'; Color2 = '#000000'
        elif tos == 'Obsidian':          Color1 = '#293134'; Color2 = '#66747B'
        elif tos == 'Zenburn':           Color1 = '#DCDCCC'; Color2 = '#3F3F3F'
        elif tos == 'Monokai':           Color1 = '#272822'; Color2 = '#75715E'
        elif tos == 'Deep Space':        Color1 = '#0D0D0D'; Color2 = '#483C45'
        elif tos == 'Green Side Up':     Color1 = '#12362B'; Color2 = '#FFFFFF'
        elif tos == 'Twilight':          Color1 = '#2E3436'; Color2 = '#F9EE98'
        elif tos == 'UliPad':            Color1 = '#FFFFFF'; Color2 = '#F0804F'
        elif tos == 'Hello Kitty':       Color1 = '#FF0000'; Color2 = '#FFFFFF'
        elif tos == 'Vibrant Ink':       Color1 = '#333333'; Color2 = '#999999'
        elif tos == 'Birds Of Paridise': Color1 = '#423230'; Color2 = '#D9D458'
        elif tos == 'BlackLight':        Color1 = '#FF7800'; Color2 = '#535AE9'
        elif tos == 'Notebook':          Color1 = '#000000'; Color2 = '#A0D6E2'

        elif fms == 1: self.OnFolderMarginStyle1(event, Color1, Color2)
        elif fms == 2: self.OnFolderMarginStyle2(event, Color1, Color2)
        elif fms == 5: self.OnFolderMarginStyle5(event, Color1, Color2)
        elif fms == 6: self.OnFolderMarginStyle6(event, Color1, Color2)

        if   tos == 'No Theme':          Color1 = '#FFFFFF'; Color2 = '#000000'
        elif tos == 'Default':           Color1 = '#32CC99'; Color2 = '#000000'
        elif tos == 'Console':           Color1 = '#000000'; Color2 = '#BBBBBB'
        elif tos == 'Obsidian':          Color1 = '#293134'; Color2 = '#66747B'
        elif tos == 'Zenburn':           Color1 = '#DCDCCC'; Color2 = '#3F3F3F'
        elif tos == 'Monokai':           Color1 = '#75715E'; Color2 = '#272822'
        elif tos == 'Deep Space':        Color1 = '#483C45'; Color2 = '#0D0D0D'
        elif tos == 'Green Side Up':     Color1 = '#FFFFFF'; Color2 = '#12362B'
        elif tos == 'Twilight':          Color1 = '#F9EE98'; Color2 = '#2E3436'
        elif tos == 'UliPad':            Color1 = '#F0804F'; Color2 = '#FFFFFF'
        elif tos == 'Hello Kitty':       Color1 = '#FFFFFF'; Color2 = '#FF0000'
        elif tos == 'Vibrant Ink':       Color1 = '#999999'; Color2 = '#333333'
        elif tos == 'Birds Of Paridise': Color1 = '#D9D458'; Color2 = '#423230'
        elif tos == 'BlackLight':        Color1 = '#535AE9'; Color2 = '#FF7800'
        elif tos == 'Notebook':          Color1 = '#A0D6E2'; Color2 = '#000000'

        if   fms == 3: self.OnFolderMarginStyle3(event, Color1, Color2)
        elif fms == 4: self.OnFolderMarginStyle4(event, Color1, Color2)

    def OnFolderMarginStyle1(self, event, Color1, Color2):
        ''' Arrow pointing right for contracted folders, arrow pointing down for expanded. '''
        basher.settings['bash.installers.wizSTC.FolderMarginStyle'] = 1
        basher.settings.setChanged('bash.installers.wizSTC.FolderMarginStyle')
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_ARROWDOWN, Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_ARROW,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_EMPTY,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_EMPTY,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_EMPTY,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_EMPTY,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_EMPTY,     Color1 , Color2)
    def OnFolderMarginStyle2(self, event, Color1, Color2):
        ''' Plus for contracted folders, minus for expanded. '''
        basher.settings['bash.installers.wizSTC.FolderMarginStyle'] = 2
        basher.settings.setChanged('bash.installers.wizSTC.FolderMarginStyle')
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_MINUS, Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_PLUS,  Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_EMPTY, Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_EMPTY, Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_EMPTY, Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_EMPTY, Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_EMPTY, Color1 , Color2)
    def OnFolderMarginStyle3(self, event, Color1, Color2):
        ''' Like a flattened tree control using circular headers and curved joins. '''
        basher.settings['bash.installers.wizSTC.FolderMarginStyle'] = 3
        basher.settings.setChanged('bash.installers.wizSTC.FolderMarginStyle')
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_CIRCLEMINUS,          Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_CIRCLEPLUS,           Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_VLINE,                Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_LCORNERCURVE,         Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_CIRCLEPLUSCONNECTED,  Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_CIRCLEMINUSCONNECTED, Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNERCURVE,         Color1, Color2)
    def OnFolderMarginStyle4(self, event, Color1, Color2):
        ''' Like a flattened tree control using square headers. '''
        basher.settings['bash.installers.wizSTC.FolderMarginStyle'] = 4
        basher.settings.setChanged('bash.installers.wizSTC.FolderMarginStyle')
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_BOXMINUS,          Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_BOXPLUS,           Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_VLINE,             Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_LCORNER,           Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_BOXPLUSCONNECTED,  Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_BOXMINUSCONNECTED, Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNER,           Color1, Color2)
    def OnFolderMarginStyle5(self, event, Color1, Color2):
        ''' Arrows >>> pointing right for contracted folders, dotdotdot ... for expanded. '''
        basher.settings['bash.installers.wizSTC.FolderMarginStyle'] = 5
        basher.settings.setChanged('bash.installers.wizSTC.FolderMarginStyle')
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_ARROWS,    Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_DOTDOTDOT, Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_EMPTY,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_EMPTY,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_EMPTY,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_EMPTY,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_EMPTY,     Color1 , Color2)
    def OnFolderMarginStyle6(self, event, Color1, Color2):
        ''' Short arrow -> pointing right for contracted folders, circle ... for expanded. '''
        basher.settings['bash.installers.wizSTC.FolderMarginStyle'] = 6
        basher.settings.setChanged('bash.installers.wizSTC.FolderMarginStyle')
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_SHORTARROW, Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_CIRCLE,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_EMPTY,      Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_EMPTY,      Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_EMPTY,      Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_EMPTY,      Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_EMPTY,      Color1 , Color2)

    def OnSetTheme(self, event):
        ''' Called on initialization to set the users saved theme setting. '''
        tos = basher.settings['bash.installers.wizSTC.ThemeOnStartup']
        if   tos == 'No Theme':          self.OnNoTheme(event)
        elif tos == 'Default':           self.OnDefaultTheme(event)
        elif tos == 'Console':           self.OnConsoleTheme(event)
        elif tos == 'Obsidian':          self.OnObsidianTheme(event)
        elif tos == 'Zenburn':           self.OnZenburnTheme(event)
        elif tos == 'Monokai':           self.OnMonokaiTheme(event)
        elif tos == 'Deep Space':        self.OnDeepSpaceTheme(event)
        elif tos == 'Green Side Up':     self.OnGreenSideUpTheme(event)
        elif tos == 'Twilight':          self.OnTwilightTheme(event)
        elif tos == 'UliPad':            self.OnUliPadTheme(event)
        elif tos == 'Hello Kitty':       self.OnHelloKittyTheme(event)
        elif tos == 'Vibrant Ink':       self.OnVibrantInkTheme(event)
        elif tos == 'Birds Of Paridise': self.OnBirdsOfParidiseTheme(event)
        elif tos == 'BlackLight':        self.OnBlackLightTheme(event)
        elif tos == 'Notebook':          self.OnNotebookTheme(event)
        else:
            print ('ThemeOnStartup ERROR!!!!!!!!!!!!\nOnSetTheme')

    def OnToggleEditorThemes(self, event):
        ''' Toggles through the various built-in themes. Default keyboard shortcut: F12. '''
        tos = basher.settings['bash.installers.wizSTC.ThemeOnStartup']
        if   tos == 'No Theme':          self.OnDefaultTheme(event)
        elif tos == 'Default':           self.OnConsoleTheme(event)
        elif tos == 'Console':           self.OnObsidianTheme(event)
        elif tos == 'Obsidian':          self.OnZenburnTheme(event)
        elif tos == 'Zenburn':           self.OnMonokaiTheme(event)
        elif tos == 'Monokai':           self.OnDeepSpaceTheme(event)
        elif tos == 'Deep Space':        self.OnGreenSideUpTheme(event)
        elif tos == 'Green Side Up':     self.OnTwilightTheme(event)
        elif tos == 'Twilight':          self.OnUliPadTheme(event)
        elif tos == 'UliPad':            self.OnHelloKittyTheme(event)
        elif tos == 'Hello Kitty':       self.OnVibrantInkTheme(event)
        elif tos == 'Vibrant Ink':       self.OnBirdsOfParidiseTheme(event)
        elif tos == 'Birds Of Paridise': self.OnBlackLightTheme(event)
        elif tos == 'BlackLight':        self.OnNotebookTheme(event)
        elif tos == 'Notebook':          self.OnNoTheme(event)

    def OnNoTheme(self, event):
        ''' A black and white only theme. Use this theme if you don't want syntax highlighting. '''
        basher.settings['bash.installers.wizSTC.ThemeOnStartup'] = 'No Theme'
        basher.settings.setChanged('bash.installers.wizSTC.ThemeOnStartup')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#000000,back:#FFFFFF,face:%(mono)s,size:%(size)d' % faces)
        self.ClearDocumentStyle()
        self.StyleClearAll()
        self.SetCaretLineBackground('#DDDDDD')
        self.SetCaretForeground('#000000')

        self.rmousegesture.SetGesturePen('Black', 5)

        self.SetFoldMarginHiColour(True, '#FFFFFF')
        self.SetFoldMarginColour(True, '#000000')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#000000,back:#FFFFFF,face:%(mono)s,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE, 'fore:#000000,back:#FFFFFF')
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,  'fore:#FFFFFF,back:#000000,face:%(mono)s,size:%(size2)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, 'fore:#000000,back:#FFFFFF')
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,  'fore:#000000,back:#FFFFFF')
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,    'fore:#000000,back:#FFFFFF')

        self.SetWhitespaceForeground(True, '#000000')
        self.SetWhitespaceBackground(False,'#FFFFFF')

        self.SetSelForeground(False, '#000000')
        self.SetSelBackground(True,  '#999999')

        if basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'pythonlexer' or basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
            # Make the Python styles ...
            self.StyleSetSpec(stc.STC_P_DEFAULT,        'fore:#000000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_COMMENTLINE,    'fore:#000000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_NUMBER,         'fore:#000000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_STRING,         'fore:#000000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_CHARACTER,      'fore:#000000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_WORD,           'fore:#000000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_WORD2,          'fore:#000000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_TRIPLE,         'fore:#000000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,   'fore:#000000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_CLASSNAME,      'fore:#000000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_DEFNAME,        'fore:#000000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_OPERATOR,       'fore:#000000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_IDENTIFIER,     'fore:#000000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,   'fore:#000000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_STRINGEOL,      'fore:#000000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_DECORATOR,      'fore:#000000,back:#FFFFFF')

            self.StyleSetHotSpot(stc.STC_P_WORD, True)
            self.StyleSetHotSpot(stc.STC_P_WORD2, True)

        self.Colourise(0, self.GetLength())
        self.OnSetFolderMarginStyle(event)
        for i in range(0,stc.STC_INDIC_MAX + 1): self.IndicatorSetForeground(i,'#000000')

        self.SetMarginWidth(3, 0)
        # print('No Theme')

    def OnDefaultTheme(self, event):
        ''' This is the default theme made originally for TES4WizBAIN. Colors are based off utumno's Notepad++ BAIN Wizard syntax highlighting theme. '''
        basher.settings['bash.installers.wizSTC.ThemeOnStartup'] = 'Default'
        basher.settings.setChanged('bash.installers.wizSTC.ThemeOnStartup')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#000000,back:#FFFFFF,face:%(mono)s,size:%(size)d' % faces)#Always call this twice. before and after StyleClearAll()
        self.ClearDocumentStyle()
        self.StyleClearAll()
        self.SetCaretLineBackground('#D7DEEB')
        self.SetCaretForeground('#0000FF')

        self.rmousegesture.SetGesturePen('Black', 5)

        self.SetFoldMarginHiColour(True, '#FFFFFF')
        self.SetFoldMarginColour(True, '#E0E0E0')  #Set the colours used as a chequerboard pattern in the fold margin #Sometimes Visually, this is glitchy looking when moving the window with colors other than default.

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#000000,back:#FFFFFF,face:%(mono)s,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE, 'fore:#33FF33,back:#FF0000')
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,  'fore:#000000,back:#99AA99,face:%(mono)s,size:%(size2)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, 'fore:#000000,back:#FFFFFF')
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,  'fore:#FF0000,back:#ACACFF,bold')
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,    'fore:#000000,back:#FF0000,bold')

        self.SetWhitespaceForeground(True, '#000000')
        self.SetWhitespaceBackground(False,'#FFFFFF')

        self.SetSelForeground(False, '#000000')
        self.SetSelBackground(True,  '#C0C0C0')

        if basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'pythonlexer' or basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
            # Make the Python styles ...
            self.StyleSetSpec(stc.STC_P_DEFAULT,        'fore:#000000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_COMMENTLINE,    'fore:#007F00,back:#EAFFE9')
            self.StyleSetSpec(stc.STC_P_NUMBER,         'fore:#FF0000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_STRING,         'fore:#FF8000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_CHARACTER,      'fore:#FF8000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_WORD,           'fore:#FF0000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_WORD2,          'fore:#6000FF,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_TRIPLE,         'fore:#000000,back:#FFF7EE')
            self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,   'fore:#FF8000,back:#FFF7EE')
            self.StyleSetSpec(stc.STC_P_CLASSNAME,      'fore:#0000FF,back:#FFFFFF,bold,underline')
            self.StyleSetSpec(stc.STC_P_DEFNAME,        'fore:#007F7F,back:#FFFFFF,bold')
            self.StyleSetSpec(stc.STC_P_OPERATOR,       'fore:#000000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_IDENTIFIER,     'fore:#000000,back:#FFFFFF')
            self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,   'fore:#7F7F7F,back:#F8FFF8')
            self.StyleSetSpec(stc.STC_P_STRINGEOL,      'fore:#000000,back:#E0C0E0,eol')
            self.StyleSetSpec(stc.STC_P_DECORATOR,      'fore:#000000,back:#FFFFFF')

            self.StyleSetHotSpot(stc.STC_P_WORD, True) #This keeps the hotspots active when moused over
            self.StyleSetHotSpot(stc.STC_P_WORD2, True)

        self.Colourise(0, self.GetLength())
        self.OnSetFolderMarginStyle(event)
        for i in range(0,stc.STC_INDIC_MAX + 1): self.IndicatorSetForeground(i,'#FF0000')
        if self.GetMarginWidth(3) == 0: self.SetMarginWidth(3, 16)
        # print('Default Theme')

    def OnConsoleTheme(self, event):
        ''' A dark version of the Default theme. '''
        basher.settings['bash.installers.wizSTC.ThemeOnStartup'] = 'Console'
        basher.settings.setChanged('bash.installers.wizSTC.ThemeOnStartup')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#BBBBBB,back:#000000,face:%(mono)s,size:%(size)d' % faces)
        self.ClearDocumentStyle()
        self.StyleClearAll()
        self.SetCaretLineBackground('#333333')
        self.SetCaretForeground('#AAB716')

        self.rmousegesture.SetGesturePen('White', 5)

        self.SetFoldMarginHiColour(True, '#000000')
        self.SetFoldMarginColour(True, '#222222')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#BBBBBB,back:#000000,face:%(mono)s,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE, 'fore:#AAAAAA,back:#000000')
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,  'fore:#BBBBBB,back:#222222,bold,face:%(mono)s,size:%(size2)d' % faces)
        # self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, 'fore:#000000,back:#FFFFFF,face:%(mono)s' % faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,  'fore:#FF0000,back:#0000FF,bold')
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,    'fore:#000000,back:#FF0000,bold')

        self.SetWhitespaceForeground(True, '#BBBBBB')
        self.SetWhitespaceBackground(False,'#FFFFFF')

        self.SetSelForeground(False, '#43BBE2')
        self.SetSelBackground(True,  '#444444')

        if basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'pythonlexer' or basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
            # Python styles
            self.StyleSetSpec(stc.STC_P_DEFAULT,        'fore:#BBBBBB,back:#000000')
            self.StyleSetSpec(stc.STC_P_COMMENTLINE,    'fore:#007F00,back:#000000')
            self.StyleSetSpec(stc.STC_P_NUMBER,         'fore:#FF0000,back:#000000')
            self.StyleSetSpec(stc.STC_P_STRING,         'fore:#FF8000,back:#000000')
            self.StyleSetSpec(stc.STC_P_CHARACTER,      'fore:#FF8000,back:#000000')
            self.StyleSetSpec(stc.STC_P_WORD,           'fore:#FF0000,back:#000000')
            self.StyleSetSpec(stc.STC_P_WORD2,          'fore:#6000FF,back:#000000')
            self.StyleSetSpec(stc.STC_P_TRIPLE,         'fore:#FFBB19,back:#332505')
            self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,   'fore:#FFBB19,back:#000000')
            self.StyleSetSpec(stc.STC_P_CLASSNAME,      'fore:#0000FF,back:#000000,bold,underline')
            self.StyleSetSpec(stc.STC_P_DEFNAME,        'fore:#007F7F,back:#000000,bold')
            self.StyleSetSpec(stc.STC_P_OPERATOR,       'fore:#BBBBBB,back:#000000,bold')
            self.StyleSetSpec(stc.STC_P_IDENTIFIER,     'fore:#BBBBBB,back:#000000')
            self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,   'fore:#7F7F7F,back:#000000')
            self.StyleSetSpec(stc.STC_P_STRINGEOL,      'fore:#BBBBBB,back:#000000,eol')
            self.StyleSetSpec(stc.STC_P_DECORATOR,      'fore:#BBBBBB,back:#000000')

            self.StyleSetHotSpot(stc.STC_P_WORD, True)
            self.StyleSetHotSpot(stc.STC_P_WORD2, True)

        self.Colourise(0, self.GetLength())
        self.OnSetFolderMarginStyle(event)
        for i in range(0,stc.STC_INDIC_MAX + 1): self.IndicatorSetForeground(i,'#FF0000')
        if self.GetMarginWidth(3) == 0: self.SetMarginWidth(3, 16)
        # print('Console Theme')

    def OnObsidianTheme(self, event):
        ''' A popular theme found in various code editors. '''
        basher.settings['bash.installers.wizSTC.ThemeOnStartup'] = 'Obsidian'
        basher.settings.setChanged('bash.installers.wizSTC.ThemeOnStartup')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,       'fore:#E0E2E4,back:#293134,face:%(mono)s,size:%(size)d' % faces)
        self.ClearDocumentStyle()
        self.StyleClearAll()
        self.SetCaretLineBackground('#2F393C')
        self.SetCaretForeground('#C1CBD2')

        self.rmousegesture.SetGesturePen('Black', 5)

        self.SetFoldMarginHiColour(True, '#3F4B4E')
        self.SetFoldMarginColour(True, '#293134')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,       'fore:#E0E2E4,back:#293134,face:%(mono)s,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE,   'fore:#394448,back:#293134')
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,    'fore:#81969A,back:#3F4B4E,bold,face:%(mono)s,size:%(size2)d' % faces)
        # self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, 'fore:#000000,back:#FFFFFF,face:%(mono)s' % faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,    'fore:#F3DB2E,back:#293134,bold')
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,      'fore:#FB0000,back:#293134,bold')

        self.SetWhitespaceForeground(True, '#343F43')
        self.SetWhitespaceBackground(False,'#293134')

        self.SetSelForeground(False, '#C00000')
        self.SetSelBackground(True,  '#404E51')

        if basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'pythonlexer' or basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
            # Python styles
            self.StyleSetSpec(stc.STC_P_DEFAULT,        'fore:#E0E2E4,back:#293134')
            self.StyleSetSpec(stc.STC_P_COMMENTLINE,    'fore:#66747B,back:#293134')
            self.StyleSetSpec(stc.STC_P_NUMBER,         'fore:#FFCD22,back:#293134')
            self.StyleSetSpec(stc.STC_P_STRING,         'fore:#EC7600,back:#293134')
            self.StyleSetSpec(stc.STC_P_CHARACTER,      'fore:#FF8409,back:#293134')
            self.StyleSetSpec(stc.STC_P_WORD,           'fore:#C7BA63,back:#293134')
            self.StyleSetSpec(stc.STC_P_WORD2,          'fore:#93C763,back:#293134')
            self.StyleSetSpec(stc.STC_P_TRIPLE,         'fore:#66747B,back:#293134')
            self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,   'fore:#66747B,back:#293134')
            self.StyleSetSpec(stc.STC_P_CLASSNAME,      'fore:#A082BD,back:#293134,bold,underline')
            self.StyleSetSpec(stc.STC_P_DEFNAME,        'fore:#678CB1,back:#293134,bold')
            self.StyleSetSpec(stc.STC_P_OPERATOR,       'fore:#E8E2B7,back:#293134,bold')
            self.StyleSetSpec(stc.STC_P_IDENTIFIER,     'fore:#E0E2E4,back:#293134')
            self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,   'fore:#66747B,back:#293134')
            self.StyleSetSpec(stc.STC_P_STRINGEOL,      'fore:#E0E2E4,back:#293134,eol')
            self.StyleSetSpec(stc.STC_P_DECORATOR,      'fore:#BBBBBB,back:#000000')

            self.StyleSetHotSpot(stc.STC_P_WORD, True)
            self.StyleSetHotSpot(stc.STC_P_WORD2, True)

        self.Colourise(0, self.GetLength())
        self.OnSetFolderMarginStyle(event)
        for i in range(0,stc.STC_INDIC_MAX + 1): self.IndicatorSetForeground(i,'#FF0000')
        if self.GetMarginWidth(3) == 0: self.SetMarginWidth(3, 16)
        # print('Obsidian Theme')

    def OnZenburnTheme(self, event):
        ''' A popular theme found in various code editors. '''
        basher.settings['bash.installers.wizSTC.ThemeOnStartup'] = 'Zenburn'
        basher.settings.setChanged('bash.installers.wizSTC.ThemeOnStartup')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,       'fore:#DCDCCC,back:#3F3F3F,face:%(mono)s,size:%(size)d' % faces)
        self.ClearDocumentStyle()
        self.StyleClearAll()
        self.SetCaretLineBackground('#101010')
        self.SetCaretForeground('#8FAF9F')

        self.rmousegesture.SetGesturePen('Black', 5)

        self.SetFoldMarginHiColour(True, '#3F3F3F')
        self.SetFoldMarginColour(True, '#8A8A8A')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,       'fore:#DCDCCC,back:#3F3F3F,face:%(mono)s,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE,   'fore:#4F5F5F,back:#3F3F3F')
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,    'fore:#8A8A8A,back:#535353,bold,face:%(mono)s,size:%(size2)d' % faces)
        # self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, 'fore:#000000,back:#FFFFFF,face:%(mono)s' % faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,    'fore:#F0F9F9,back:#3F3F3F,bold')
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,      'fore:#F09F9F,back:#3F3F3F,bold')

        self.SetWhitespaceForeground(True, '#5F5F5F')
        self.SetWhitespaceBackground(False,'#3F3F3F')

        self.SetSelForeground(False, '#C00000')
        self.SetSelBackground(True,  '#585858')

        if basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'pythonlexer' or basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
            # Python styles
            self.StyleSetSpec(stc.STC_P_DEFAULT,        'fore:#DCDCCC,back:#3F3F3F')
            self.StyleSetSpec(stc.STC_P_COMMENTLINE,    'fore:#7F9F7F,back:#3F3F3F')
            self.StyleSetSpec(stc.STC_P_NUMBER,         'fore:#8CD0D3,back:#3F3F3F')
            self.StyleSetSpec(stc.STC_P_STRING,         'fore:#CC9393,back:#3F3F3F')
            self.StyleSetSpec(stc.STC_P_CHARACTER,      'fore:#DCA3A3,back:#3F3F3F')
            self.StyleSetSpec(stc.STC_P_WORD,           'fore:#DFC47D,back:#3F3F3F')
            self.StyleSetSpec(stc.STC_P_WORD2,          'fore:#DFC47D,back:#3F3F3F')
            self.StyleSetSpec(stc.STC_P_TRIPLE,         'fore:#7F9F7F,back:#3F3F3F')
            self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,   'fore:#7F9F7F,back:#3F3F3F')
            self.StyleSetSpec(stc.STC_P_CLASSNAME,      'fore:#DCDCCC,back:#3F3F3F,bold,underline')
            self.StyleSetSpec(stc.STC_P_DEFNAME,        'fore:#CEDF99,back:#3F3F3F,bold')
            self.StyleSetSpec(stc.STC_P_OPERATOR,       'fore:#9F9D6D,back:#3F3F3F,bold')
            self.StyleSetSpec(stc.STC_P_IDENTIFIER,     'fore:#DCDCCC,back:#3F3F3F')
            self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,   'fore:#7F9F7F,back:#3F3F3F')
            self.StyleSetSpec(stc.STC_P_STRINGEOL,      'fore:#CC9393,back:#3F3F3F,eol')
            self.StyleSetSpec(stc.STC_P_DECORATOR,      'fore:#BBBBBB,back:#000000')

            self.StyleSetHotSpot(stc.STC_P_WORD, True)
            self.StyleSetHotSpot(stc.STC_P_WORD2, True)

        self.Colourise(0, self.GetLength())
        self.OnSetFolderMarginStyle(event)
        for i in range(0,stc.STC_INDIC_MAX + 1): self.IndicatorSetForeground(i,'#FF0000')
        if self.GetMarginWidth(3) == 0: self.SetMarginWidth(3, 16)
        # print('Zenburn Theme')

    def OnMonokaiTheme(self, event):
        ''' A popular theme found in various code editors. '''
        basher.settings['bash.installers.wizSTC.ThemeOnStartup'] = 'Monokai'
        basher.settings.setChanged('bash.installers.wizSTC.ThemeOnStartup')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,       'fore:#F8F8F2,back:#272822,face:%(mono)s,size:%(size)d' % faces)
        self.ClearDocumentStyle()
        self.StyleClearAll()
        self.SetCaretLineBackground('#101010')
        self.SetCaretForeground('#8FAF9F')

        self.rmousegesture.SetGesturePen('Black', 5)

        self.SetFoldMarginHiColour(True, '#E6DB74')
        self.SetFoldMarginColour(True, '#888888')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,       'fore:#F8F8F2,back:#272822,face:%(mono)s,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE,   'fore:#888A85,back:#272822')
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,    'fore:#EEEEEC,back:#2D2E27,bold,face:%(mono)s,size:%(size2)d' % faces)
        # self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, 'fore:#000000,back:#FFFFFF,face:%(mono)s' % faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,    'fore:#FCE94F,back:#272822,bold')
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,      'fore:#EF2929,back:#272822,bold')

        self.SetWhitespaceForeground(True, '#75715E')
        self.SetWhitespaceBackground(False,'#272822')

        self.SetSelForeground(False, '#8000FF')
        self.SetSelBackground(True,  '#49483E')

        if basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'pythonlexer' or basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
            # Python styles
            self.StyleSetSpec(stc.STC_P_DEFAULT,        'fore:#F8F8F2,back:#272822')
            self.StyleSetSpec(stc.STC_P_COMMENTLINE,    'fore:#75715E,back:#272822')
            self.StyleSetSpec(stc.STC_P_NUMBER,         'fore:#AE81FF,back:#272822,size:%(size)d' % faces)
            self.StyleSetSpec(stc.STC_P_STRING,         'fore:#E6DB74,back:#272822')
            self.StyleSetSpec(stc.STC_P_CHARACTER,      'fore:#E6DB74,back:#272822')
            self.StyleSetSpec(stc.STC_P_WORD,           'fore:#66D9EF,back:#272822')
            self.StyleSetSpec(stc.STC_P_WORD2,          'fore:#F92672,back:#272822')
            self.StyleSetSpec(stc.STC_P_TRIPLE,         'fore:#E6DB74,back:#272822')
            self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,   'fore:#E6DB74,back:#272822')
            self.StyleSetSpec(stc.STC_P_CLASSNAME,      'fore:#F8F8F2,back:#272822,bold,underline')
            self.StyleSetSpec(stc.STC_P_DEFNAME,        'fore:#A6E22E,back:#272822,bold')
            self.StyleSetSpec(stc.STC_P_OPERATOR,       'fore:#FD7620,back:#272822,bold')
            self.StyleSetSpec(stc.STC_P_IDENTIFIER,     'fore:#FFFFFF,back:#272822')
            self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,   'fore:#75715E,back:#272822')
            self.StyleSetSpec(stc.STC_P_STRINGEOL,      'fore:#E6DB74,back:#F92672,eol')
            self.StyleSetSpec(stc.STC_P_DECORATOR,      'fore:#BBBBBB,back:#000000')

            self.StyleSetHotSpot(stc.STC_P_WORD, True)
            self.StyleSetHotSpot(stc.STC_P_WORD2, True)

        self.Colourise(0, self.GetLength())
        self.OnSetFolderMarginStyle(event)
        for i in range(0,stc.STC_INDIC_MAX + 1): self.IndicatorSetForeground(i,'#FF0000')
        if self.GetMarginWidth(3) == 0: self.SetMarginWidth(3, 16)
        # print('Monokai Theme')

    def OnDeepSpaceTheme(self, event):
        ''' A dark theme inspired by Transcendence, a cool little totally random & moddable space shooter RPG by George Morisomoto. '''
        basher.settings['bash.installers.wizSTC.ThemeOnStartup'] = 'Deep Space'
        basher.settings.setChanged('bash.installers.wizSTC.ThemeOnStartup')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,       'fore:#FFFFFF,back:#000000,face:%(mono)s,size:%(size)d' % faces)
        self.ClearDocumentStyle()
        self.StyleClearAll()
        self.SetCaretLineBackground('#101010')
        self.SetCaretForeground('#8FAF9F')

        self.rmousegesture.SetGesturePen('White', 5)

        self.SetFoldMarginHiColour(True, '#805978')
        self.SetFoldMarginColour(True, '#888888')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,       'fore:#FFFFFF,back:#0D0D0D,face:%(mono)s,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE,   'fore:#888A85,back:#0D0D0D')
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,    'fore:#75796E,back:#0D0D0D,bold,face:%(mono)s,size:%(size2)d' % faces)
        # self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR,   'fore:#1EFF00,back:#1EFF00,face:%(mono)s' % faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,    'fore:#6EA65A,back:#0D0D0D,bold')
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,      'fore:#EF2929,back:#0D0D0D,bold')

        self.SetWhitespaceForeground(True, '#805978')
        self.SetWhitespaceBackground(False,'#0D0D0D')

        self.SetSelForeground(False, '#8000FF')
        self.SetSelBackground(True,  '#26061E')

        if basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'pythonlexer' or basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
            # Python styles
            self.StyleSetSpec(stc.STC_P_DEFAULT,        'fore:#F8F8F2,back:#0D0D0D')
            self.StyleSetSpec(stc.STC_P_COMMENTLINE,    'fore:#483C45,back:#0D0D0D')
            self.StyleSetSpec(stc.STC_P_NUMBER,         'fore:#A8885A,back:#0D0D0D')
            self.StyleSetSpec(stc.STC_P_STRING,         'fore:#805978,back:#0D0D0D')
            self.StyleSetSpec(stc.STC_P_CHARACTER,      'fore:#805978,back:#0D0D0D')
            self.StyleSetSpec(stc.STC_P_WORD,           'fore:#9EBF60,back:#0D0D0D')
            self.StyleSetSpec(stc.STC_P_WORD2,          'fore:#566F39,back:#0D0D0D')
            self.StyleSetSpec(stc.STC_P_TRIPLE,         'fore:#805978,back:#0D0D0D')
            self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,   'fore:#805978,back:#0D0D0D')
            self.StyleSetSpec(stc.STC_P_CLASSNAME,      'fore:#6078BF,back:#0D0D0D,bold,underline')
            self.StyleSetSpec(stc.STC_P_DEFNAME,        'fore:#6078BF,back:#0D0D0D,bold')
            self.StyleSetSpec(stc.STC_P_OPERATOR,       'fore:#596380,back:#0D0D0D,bold')
            self.StyleSetSpec(stc.STC_P_IDENTIFIER,     'fore:#BBBBBB,back:#0D0D0D')
            self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,   'fore:#483C45,back:#0D0D0D')
            self.StyleSetSpec(stc.STC_P_STRINGEOL,      'fore:#FF00FF,back:#5F0047,eol')
            self.StyleSetSpec(stc.STC_P_DECORATOR,      'fore:#BBBBBB,back:#0D0D0D')

            self.StyleSetHotSpot(stc.STC_P_WORD, True)
            self.StyleSetHotSpot(stc.STC_P_WORD2, True)

        self.Colourise(0, self.GetLength())
        self.OnSetFolderMarginStyle(event)
        for i in range(0,stc.STC_INDIC_MAX + 1): self.IndicatorSetForeground(i,'#FF00FF')
        if self.GetMarginWidth(3) == 0: self.SetMarginWidth(3, 16)
        # print('Deep Space Theme')

    def OnGreenSideUpTheme(self, event):
        ''' A strangely greenish/purplish theme developed by an alien I met once. '''
        basher.settings['bash.installers.wizSTC.ThemeOnStartup'] = 'Green Side Up'
        basher.settings.setChanged('bash.installers.wizSTC.ThemeOnStartup')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,       'fore:#00FF00,back:#000000,face:%(mono)s,size:%(size)d' % faces)
        self.ClearDocumentStyle()
        self.StyleClearAll()
        self.SetCaretLineBackground('#657868')
        self.SetCaretForeground('#8FAF9F')

        self.rmousegesture.SetGesturePen('#8000FF', 5)

        self.SetFoldMarginHiColour(True, '#00FF00')
        self.SetFoldMarginColour(True, '#888888')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,       'fore:#00FF00,back:#000000,face:%(mono)s,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE,   'fore:#548045,back:#000000')
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,    'fore:#00FF0A,back:#111111,bold,face:%(mono)s,size:%(size2)d' % faces)
        # self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR,   'fore:#1EFF00,back:#1EFF00,face:%(mono)s' % faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,    'fore:#6EA65A,back:#000000,bold')
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,      'fore:#EF2929,back:#000000,bold')

        self.SetWhitespaceForeground(True, '#8AC392')
        self.SetWhitespaceBackground(False,'#000000')

        self.SetSelForeground(True, '#8000FF')
        self.SetSelBackground(True, '#333333')

        if basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'pythonlexer' or basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
            # Python styles
            self.StyleSetSpec(stc.STC_P_DEFAULT,        'fore:#BBBBBB,back:#000000')
            self.StyleSetSpec(stc.STC_P_COMMENTLINE,    'fore:#00AA00,back:#3B5930')
            self.StyleSetSpec(stc.STC_P_NUMBER,         'fore:#479D1C,back:#000000')
            self.StyleSetSpec(stc.STC_P_STRING,         'fore:#50E064,back:#000000')
            self.StyleSetSpec(stc.STC_P_CHARACTER,      'fore:#50E064,back:#000000')
            self.StyleSetSpec(stc.STC_P_WORD,           'fore:#3B5930,back:#000000,bold')
            self.StyleSetSpec(stc.STC_P_WORD2,          'fore:#3B5930,back:#000000,bold')
            self.StyleSetSpec(stc.STC_P_TRIPLE,         'fore:#50E064,back:#000000')
            self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,   'fore:#50E064,back:#000000')
            self.StyleSetSpec(stc.STC_P_CLASSNAME,      'fore:#0B6518,back:#000000,bold,underline')
            self.StyleSetSpec(stc.STC_P_DEFNAME,        'fore:#0B6518,back:#000000,bold')
            self.StyleSetSpec(stc.STC_P_OPERATOR,       'fore:#5BBF69,back:#000000,bold')
            self.StyleSetSpec(stc.STC_P_IDENTIFIER,     'fore:#00FF00,back:#000000')
            self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,   'fore:#00AA00,back:#3B5930' % faces)
            self.StyleSetSpec(stc.STC_P_STRINGEOL,      'fore:#000000,back:#00FF00,eol' % faces)#
            self.StyleSetSpec(stc.STC_P_DECORATOR,      'fore:#BBBBBB,back:#000000' % faces)

            self.StyleSetHotSpot(stc.STC_P_WORD, True)
            self.StyleSetHotSpot(stc.STC_P_WORD2, True)

        self.Colourise(0, self.GetLength())
        self.OnSetFolderMarginStyle(event)
        for i in range(0,stc.STC_INDIC_MAX + 1): self.IndicatorSetForeground(i,'#8000FF')
        if self.GetMarginWidth(3) == 0: self.SetMarginWidth(3, 16)
        # print('Green Side Up Theme')

    def OnTwilightTheme(self, event):
        ''' A popular theme found in various code editors. '''
        basher.settings['bash.installers.wizSTC.ThemeOnStartup'] = 'Twilight'
        basher.settings.setChanged('bash.installers.wizSTC.ThemeOnStartup')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,       'fore:#FFFFFF,back:#141414,face:%(mono)s,size:%(size)d' % faces)
        self.ClearDocumentStyle()
        self.StyleClearAll()
        self.SetCaretLineBackground('#292929')
        self.SetCaretForeground('#A7A7A7')

        self.rmousegesture.SetGesturePen('White', 5)

        self.SetFoldMarginHiColour(True, '#8F9D6A')
        self.SetFoldMarginColour(True, '#888888')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,       'fore:#FFFFFF,back:#141414,face:%(mono)s,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE,   'fore:#888A85,back:#141414')
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,    'fore:#EEEEEC,back:#2E3436,bold,face:%(mono)s,size:%(size2)d' % faces)
        # self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR,   'fore:#1EFF00,back:#1EFF00,face:%(mono)s' % faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,    'fore:#6EA65A,back:#141414,bold')
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,      'fore:#EF2929,back:#141414,bold')

        self.SetWhitespaceForeground(True, '#FCAF3E')
        self.SetWhitespaceBackground(False,'#141414')

        self.SetSelForeground(False, '#8000FF')
        self.SetSelBackground(True,  '#3E3E3E')

        if basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'pythonlexer' or basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
            # Python styles
            self.StyleSetSpec(stc.STC_P_DEFAULT,        'fore:#F8F8F8,back:#141414')
            self.StyleSetSpec(stc.STC_P_COMMENTLINE,    'fore:#5F5A60,back:#141414')
            self.StyleSetSpec(stc.STC_P_NUMBER,         'fore:#7587A6,back:#141414')
            self.StyleSetSpec(stc.STC_P_STRING,         'fore:#8F9D6A,back:#141414')
            self.StyleSetSpec(stc.STC_P_CHARACTER,      'fore:#8F9D6A,back:#141414')
            self.StyleSetSpec(stc.STC_P_WORD,           'fore:#F9EE98,back:#141414')
            self.StyleSetSpec(stc.STC_P_WORD2,          'fore:#CDA869,back:#141414')
            self.StyleSetSpec(stc.STC_P_TRIPLE,         'fore:#8F9D6A,back:#141414')
            self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,   'fore:#8F9D6A,back:#141414')
            self.StyleSetSpec(stc.STC_P_CLASSNAME,      'fore:#9B703F,back:#141414,bold,underline')
            self.StyleSetSpec(stc.STC_P_DEFNAME,        'fore:#9B703F,back:#141414,bold')
            self.StyleSetSpec(stc.STC_P_OPERATOR,       'fore:#CDA869,back:#141414,bold')
            self.StyleSetSpec(stc.STC_P_IDENTIFIER,     'fore:#F8F8F8,back:#141414')
            self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,   'fore:#5F5A60,back:#141414')
            self.StyleSetSpec(stc.STC_P_STRINGEOL,      'fore:#8F9D6A,back:#452645,eol')
            self.StyleSetSpec(stc.STC_P_DECORATOR,      'fore:#BBBBBB,back:#141414')

            self.StyleSetHotSpot(stc.STC_P_WORD, True)
            self.StyleSetHotSpot(stc.STC_P_WORD2, True)

        self.Colourise(0, self.GetLength())
        self.OnSetFolderMarginStyle(event)
        for i in range(0,stc.STC_INDIC_MAX + 1): self.IndicatorSetForeground(i,'#4526DD')
        if self.GetMarginWidth(3) == 0: self.SetMarginWidth(3, 16)
        # print('Twilight Theme')

    def OnUliPadTheme(self, event):
        ''' The default UliPad code editor theme. '''
        basher.settings['bash.installers.wizSTC.ThemeOnStartup'] = 'UliPad'
        basher.settings.setChanged('bash.installers.wizSTC.ThemeOnStartup')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,       'fore:#FFFFFF,back:#112435,face:%(mono)s,size:%(size)d' % faces)
        self.ClearDocumentStyle()
        self.StyleClearAll()
        self.SetCaretLineBackground('#413FFF')
        self.SetCaretForeground('#FF0000')

        self.rmousegesture.SetGesturePen('Black', 5)

        self.SetFoldMarginHiColour(True, '#3476A3')
        self.SetFoldMarginColour(True, '#FFFFFF')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,       'fore:#FFFFFF,back:#112435,face:%(mono)s,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE,   'fore:#888A85,back:#112435')
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,    'fore:#FFFFFF,back:#1F4661,bold,face:%(mono)s,size:%(size2)d' % faces)
        # self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR,   'fore:#1EFF00,back:#1EFF00,face:%(mono)s' % faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,    'fore:#FF0000,back:#112435,bold')
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,      'fore:#FFFFFF,back:#112435,bold')

        self.SetWhitespaceForeground(True, '#8DB0D3')
        self.SetWhitespaceBackground(False,'#112435')

        self.SetSelForeground(False, '#8000FF')
        self.SetSelBackground(True,  '#2E9F27')

        if basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'pythonlexer' or basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
            # Python styles
            self.StyleSetSpec(stc.STC_P_DEFAULT,        'fore:#8DB0D3,back:#112435')
            self.StyleSetSpec(stc.STC_P_COMMENTLINE,    'fore:#00CFCB,back:#112435')
            self.StyleSetSpec(stc.STC_P_NUMBER,         'fore:#FF00FF,back:#112435')
            self.StyleSetSpec(stc.STC_P_STRING,         'fore:#00FF80,back:#112435')
            self.StyleSetSpec(stc.STC_P_CHARACTER,      'fore:#E19618,back:#112435')
            self.StyleSetSpec(stc.STC_P_WORD,           'fore:#FFFF00,back:#112435')
            self.StyleSetSpec(stc.STC_P_WORD2,          'fore:#FFFF00,back:#112435')
            self.StyleSetSpec(stc.STC_P_TRIPLE,         'fore:#00FF80,back:#112435')
            self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,   'fore:#00FF80,back:#112435')
            self.StyleSetSpec(stc.STC_P_CLASSNAME,      'fore:#BBFF4F,back:#112435,bold,underline')
            self.StyleSetSpec(stc.STC_P_DEFNAME,        'fore:#8DAF57,back:#112435,bold')
            self.StyleSetSpec(stc.STC_P_OPERATOR,       'fore:#F0804F,back:#112435,bold')
            self.StyleSetSpec(stc.STC_P_IDENTIFIER,     'fore:#8DB0D3,back:#112435')
            self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,   'fore:#00CFCB,back:#112435')
            self.StyleSetSpec(stc.STC_P_STRINGEOL,      'fore:#FF6F82,back:#E0C0E0,eol')
            self.StyleSetSpec(stc.STC_P_DECORATOR,      'fore:#BBBBBB,back:#112435')

            self.StyleSetHotSpot(stc.STC_P_WORD, True)
            self.StyleSetHotSpot(stc.STC_P_WORD2, True)

        self.Colourise(0, self.GetLength())
        self.OnSetFolderMarginStyle(event)
        for i in range(0,stc.STC_INDIC_MAX + 1): self.IndicatorSetForeground(i,'#FF0000')
        if self.GetMarginWidth(3) == 0: self.SetMarginWidth(3, 16)
        # print('UliPad Theme')

    def OnHelloKittyTheme(self, event):
        ''' A theme for all the lady coders out there. '''
        basher.settings['bash.installers.wizSTC.ThemeOnStartup'] = 'Hello Kitty'
        basher.settings.setChanged('bash.installers.wizSTC.ThemeOnStartup')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#000000,back:#FFB0FF,face:%(mono)s,size:%(size)d' % faces)
        self.ClearDocumentStyle()
        self.StyleClearAll()
        self.SetCaretLineBackground('#FF80C0')
        self.SetCaretForeground('#372017')

        self.rmousegesture.SetGesturePen('Black', 5)

        self.SetFoldMarginHiColour(True, '#FF80C0')
        self.SetFoldMarginColour(True, '#FF80C0')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#000000,back:#FFB0FF,face:%(mono)s,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE, 'fore:#C0C0C0,back:#FFB0FF')
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,  'fore:#FFFFFF,back:#FF80FF,face:%(mono)s,size:%(size2)d' % faces)
        # self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, 'fore:#000000,back:#FFFFFF')
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,  'fore:#FF0000,back:#FFB0FF,bold')
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,    'fore:#800000,back:#FFB0FF,bold')

        self.SetWhitespaceForeground(True, '#FFB56A')
        self.SetWhitespaceBackground(False,'#FFFFFF')

        self.SetSelForeground(False, '#FFD5FF')
        self.SetSelBackground(True,  '#FFD5FF')

        if basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'pythonlexer' or basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
            #Python Styles
            self.StyleSetSpec(stc.STC_P_DEFAULT,        'fore:#000000,back:#FFB0FF')
            self.StyleSetSpec(stc.STC_P_COMMENTLINE,    'fore:#008000,back:#FFB0FF')
            self.StyleSetSpec(stc.STC_P_NUMBER,         'fore:#FF0000,back:#FFB0FF')
            self.StyleSetSpec(stc.STC_P_STRING,         'fore:#808080,back:#FFB0FF')
            self.StyleSetSpec(stc.STC_P_CHARACTER,      'fore:#808080,back:#FFB0FF')
            self.StyleSetSpec(stc.STC_P_WORD,           'fore:#0000FF,back:#FFB0FF,bold')
            self.StyleSetSpec(stc.STC_P_WORD2,          'fore:#0000FF,back:#FFB0FF,bold')
            self.StyleSetSpec(stc.STC_P_TRIPLE,         'fore:#FF8000,back:#FFB0FF')
            self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,   'fore:#000000,back:#FFB0FF')
            self.StyleSetSpec(stc.STC_P_CLASSNAME,      'fore:#000000,back:#FFB0FF,bold,underline')
            self.StyleSetSpec(stc.STC_P_DEFNAME,        'fore:#FF00FF,back:#FFB0FF,bold')
            self.StyleSetSpec(stc.STC_P_OPERATOR,       'fore:#000080,back:#FFB0FF,bold')
            self.StyleSetSpec(stc.STC_P_IDENTIFIER,     'fore:#000000,back:#FFB0FF')
            self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,   'fore:#008000,back:#FFB0FF')
            self.StyleSetSpec(stc.STC_P_STRINGEOL,      'fore:#FFFF00,back:#E0C0E0,eol')
            self.StyleSetSpec(stc.STC_P_DECORATOR,      'fore:#000000,back:#FFB0FF')

            self.StyleSetHotSpot(stc.STC_P_WORD, True)
            self.StyleSetHotSpot(stc.STC_P_WORD2, True)

        self.Colourise(0, self.GetLength())
        self.OnSetFolderMarginStyle(event)
        for i in range(0,stc.STC_INDIC_MAX + 1): self.IndicatorSetForeground(i,'#FF0000')
        if self.GetMarginWidth(3) == 0: self.SetMarginWidth(3, 16)
        # print('Hello Kitty Theme')

    def OnVibrantInkTheme(self, event):
        ''' A popular theme found in various code editors. '''
        basher.settings['bash.installers.wizSTC.ThemeOnStartup'] = 'Vibrant Ink'
        basher.settings.setChanged('bash.installers.wizSTC.ThemeOnStartup')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#FFFFFF,back:#000000,face:%(mono)s,size:%(size)d' % faces)
        self.ClearDocumentStyle()
        self.StyleClearAll()
        self.SetCaretLineBackground('#333333')
        self.SetCaretForeground('#FFFFFF')

        self.rmousegesture.SetGesturePen('White', 5)

        self.SetFoldMarginHiColour(True, '#111111')
        self.SetFoldMarginColour(True, '#222222')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#FFFFFF,back:#000000,face:%(mono)s,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE, 'fore:#C0C0C0,back:#000000')
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,  'fore:#E4E4E4,back:#333333,face:%(mono)s,size:%(size2)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, 'fore:#FFFFFF,back:#000000')
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,  'fore:#99CC99,back:#000000,bold')
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,    'fore:#CCFF33,back:#000000,bold')

        self.SetWhitespaceForeground(True, '#FF8080')
        self.SetWhitespaceBackground(False,'#000000')

        self.SetSelForeground(False, '#8000FF')
        self.SetSelBackground(True,  '#6699CC')

        if basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'pythonlexer' or basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
            #Python Styles
            self.StyleSetSpec(stc.STC_P_DEFAULT,        'fore:#FFFFFF,back:#000000')
            self.StyleSetSpec(stc.STC_P_COMMENTLINE,    'fore:#9933CC,back:#000000')
            self.StyleSetSpec(stc.STC_P_NUMBER,         'fore:#99CC99,back:#000000')
            self.StyleSetSpec(stc.STC_P_STRING,         'fore:#66FF00,back:#000000')
            self.StyleSetSpec(stc.STC_P_CHARACTER,      'fore:#66FF00,back:#000000')
            self.StyleSetSpec(stc.STC_P_WORD,           'fore:#FF6600,back:#000000,bold')
            self.StyleSetSpec(stc.STC_P_WORD2,          'fore:#FF6600,back:#000000,bold')
            self.StyleSetSpec(stc.STC_P_TRIPLE,         'fore:#FF8000,back:#000000')
            self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,   'fore:#FFFFFF,back:#000000')
            self.StyleSetSpec(stc.STC_P_CLASSNAME,      'fore:#FFFFFF,back:#000000,bold,underline')
            self.StyleSetSpec(stc.STC_P_DEFNAME,        'fore:#FF00FF,back:#000000,bold')
            self.StyleSetSpec(stc.STC_P_OPERATOR,       'fore:#FFCC00,back:#000000,bold')
            self.StyleSetSpec(stc.STC_P_IDENTIFIER,     'fore:#FFFFFF,back:#000000')
            self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,   'fore:#9933CC,back:#000000')
            self.StyleSetSpec(stc.STC_P_STRINGEOL,      'fore:#FFFF00,back:#000000,eol')
            self.StyleSetSpec(stc.STC_P_DECORATOR,      'fore:#FFFFFF,back:#000000')

            self.StyleSetHotSpot(stc.STC_P_WORD, True)
            self.StyleSetHotSpot(stc.STC_P_WORD2, True)

        self.Colourise(0, self.GetLength())
        self.OnSetFolderMarginStyle(event)
        for i in range(0,stc.STC_INDIC_MAX + 1): self.IndicatorSetForeground(i,'#FF0000')
        if self.GetMarginWidth(3) == 0: self.SetMarginWidth(3, 16)
        # print('Vibrant Ink Theme')

    def OnBirdsOfParidiseTheme(self, event):
        ''' A similarly colored/unique theme found floating around the net somewhere. '''
        basher.settings['bash.installers.wizSTC.ThemeOnStartup'] = 'Birds Of Paridise'
        basher.settings.setChanged('bash.installers.wizSTC.ThemeOnStartup')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#E6E1C4,back:#423230,face:%(mono)s,size:%(size)d' % faces)
        self.ClearDocumentStyle()
        self.StyleClearAll()
        self.SetCaretLineBackground('#292119')
        self.SetCaretForeground('#FFFFFF')

        self.rmousegesture.SetGesturePen('Black', 5)

        self.SetFoldMarginHiColour(True, '#FFFFFF')
        self.SetFoldMarginColour(True, '#E6E1C4')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#E6E1C4,back:#423230,face:%(mono)s,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE, 'fore:#C0C0C0,back:#423230')
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,  'fore:#E6E1C4,back:#4A3937,face:%(mono)s,size:%(size2)d' % faces)
        # self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, 'fore:#FFFFFF,back:#423230')
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,  'fore:#99CC99,back:#423230,bold')
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,    'fore:#FF0000,back:#FFFFFF,bold')

        self.SetWhitespaceForeground(True, '#5E4A31')
        self.SetWhitespaceBackground(False,'#000000')

        self.SetSelForeground(False, '#8000FF')
        self.SetSelBackground(True,  '#393126')

        if basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'pythonlexer' or basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
            #Python Styles
            self.StyleSetSpec(stc.STC_P_DEFAULT,        'fore:#E6E1C4,back:#423230')
            self.StyleSetSpec(stc.STC_P_COMMENTLINE,    'fore:#6B4A31,back:#423230,bold,italic')
            self.StyleSetSpec(stc.STC_P_NUMBER,         'fore:#6A99BB,back:#423230')
            self.StyleSetSpec(stc.STC_P_STRING,         'fore:#D9D458,back:#423230')
            self.StyleSetSpec(stc.STC_P_CHARACTER,      'fore:#D9D458,back:#423230')
            self.StyleSetSpec(stc.STC_P_WORD,           'fore:#EF5A31,back:#423230,bold')
            self.StyleSetSpec(stc.STC_P_WORD2,          'fore:#EF5A31,back:#423230,bold')
            self.StyleSetSpec(stc.STC_P_TRIPLE,         'fore:#E6E1C4,back:#423230')
            self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,   'fore:#E6E1C4,back:#423230')
            self.StyleSetSpec(stc.STC_P_CLASSNAME,      'fore:#EFA431,back:#423230,bold')
            self.StyleSetSpec(stc.STC_P_DEFNAME,        'fore:#78AC9C,back:#423230,bold')
            self.StyleSetSpec(stc.STC_P_OPERATOR,       'fore:#E6E1C4,back:#423230,bold')
            self.StyleSetSpec(stc.STC_P_IDENTIFIER,     'fore:#E6E1C4,back:#423230')
            self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,   'fore:#6B4A31,back:#423230,bold,italic')
            self.StyleSetSpec(stc.STC_P_STRINGEOL,      'fore:#D94C30,back:#EFA431,bold,eol')
            self.StyleSetSpec(stc.STC_P_DECORATOR,      'fore:#FFFFFF,back:#423230')

            self.StyleSetHotSpot(stc.STC_P_WORD, True)
            self.StyleSetHotSpot(stc.STC_P_WORD2, True)

        self.Colourise(0, self.GetLength())
        self.OnSetFolderMarginStyle(event)
        for i in range(0,stc.STC_INDIC_MAX + 1): self.IndicatorSetForeground(i,'#FF0000')
        if self.GetMarginWidth(3) == 0: self.SetMarginWidth(3, 16)
        # print('Birds of Paridise Theme')

    def OnBlackLightTheme(self, event):
        ''' Metallicow's personal version of a blacklight looking theme '''
        basher.settings['bash.installers.wizSTC.ThemeOnStartup'] = 'BlackLight'
        basher.settings.setChanged('bash.installers.wizSTC.ThemeOnStartup')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#DDDDDD,back:#000000,face:%(mono)s,size:%(size)d' % faces)
        self.ClearDocumentStyle()
        self.StyleClearAll()
        self.SetCaretLineBackground('#131D2E')
        self.SetCaretForeground('#FFFFFF')

        self.rmousegesture.SetGesturePen('#24276E', 5)

        self.SetFoldMarginHiColour(True, '#535AE9')
        self.SetFoldMarginColour(True, '#24276E')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#DDDDDD,back:#000000,face:%(mono)s,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE, 'fore:#3F5456,back:#000000')
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,  'fore:#296050,back:#000000,bold,face:%(mono)s,size:%(size2)d' % faces)
        # self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, 'fore:#FFFFFF,back:#000000')
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,  'fore:#99CC99,back:#000000,bold')
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,    'fore:#FF0000,back:#000000,bold')

        self.SetWhitespaceForeground(True, '#3F5456')
        self.SetWhitespaceBackground(False,'#000000')

        self.SetSelForeground(True,  '#535AE9')
        self.SetSelBackground(True,  '#24276E')

        if basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'pythonlexer' or basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
            #Python Styles
            self.StyleSetSpec(stc.STC_P_DEFAULT,        'fore:#E6E1C4,back:#000000')
            self.StyleSetSpec(stc.STC_P_COMMENTLINE,    'fore:#3F5456,back:#000000,bold,italic')
            self.StyleSetSpec(stc.STC_P_NUMBER,         'fore:#6A99BB,back:#000000')
            self.StyleSetSpec(stc.STC_P_STRING,         'fore:#81D9A6,back:#296050')
            self.StyleSetSpec(stc.STC_P_CHARACTER,      'fore:#81D9A6,back:#296050')
            self.StyleSetSpec(stc.STC_P_WORD,           'fore:#EB4D8E,back:#000000,bold')
            self.StyleSetSpec(stc.STC_P_WORD2,          'fore:#B8DB6F,back:#000000,bold')
            self.StyleSetSpec(stc.STC_P_TRIPLE,         'fore:#535AE9,back:#000000')
            self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,   'fore:#535AE9,back:#000000')
            self.StyleSetSpec(stc.STC_P_CLASSNAME,      'fore:#3F99AA,back:#000000,bold')
            self.StyleSetSpec(stc.STC_P_DEFNAME,        'fore:#3F99AA,back:#000000,bold')
            self.StyleSetSpec(stc.STC_P_OPERATOR,       'fore:#787767,back:#000000,bold')
            self.StyleSetSpec(stc.STC_P_IDENTIFIER,     'fore:#DDDDDD,back:#000000')
            self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,   'fore:#3F5456,back:#000000,bold,italic')
            self.StyleSetSpec(stc.STC_P_STRINGEOL,      'fore:#5E4DFF,back:#BAFF4D,bold,eol')
            self.StyleSetSpec(stc.STC_P_DECORATOR,      'fore:#594851,back:#000000')

            self.StyleSetHotSpot(stc.STC_P_WORD, True)
            self.StyleSetHotSpot(stc.STC_P_WORD2, True)

        self.Colourise(0, self.GetLength())
        self.OnSetFolderMarginStyle(event)
        for i in range(0,stc.STC_INDIC_MAX + 1): self.IndicatorSetForeground(i,'#535AE9')
        if self.GetMarginWidth(3) == 0: self.SetMarginWidth(3, 16)
        # print('BlackLight Theme')

    def OnNotebookTheme(self, event):
        ''' A similarly colored/whimsical theme found floating around the net somewhere based off actual notebook and highlighter markers colors. '''
        basher.settings['bash.installers.wizSTC.ThemeOnStartup'] = 'Notebook'
        basher.settings.setChanged('bash.installers.wizSTC.ThemeOnStartup')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#000000,back:#CAC2AD,face:%(mono)s,size:%(size)d' % faces)
        self.ClearDocumentStyle()
        self.StyleClearAll()
        self.SetCaretLineBackground('#BBB09C')
        self.SetCaretLineBackAlpha(basher.settings['bash.installers.wizSTC.CaretLineBackgroundAlpha'])
        self.SetCaretForeground('#7C7563')

        self.rmousegesture.SetGesturePen('Black', 5)

        self.SetFoldMarginHiColour(True, '#BBB39E')
        self.SetFoldMarginColour(True, '#CAC2AD')

        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#000000,back:#CAC2AD,face:%(mono)s,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE, 'fore:#7C7563,back:#CAC2AD')
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,  'fore:#000000,back:#CAC2AD,face:%(mono)s,size:%(size2)d' % faces)
        # self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, 'fore:#0000FF,back:#CAC2AD')
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,  'fore:#265729,back:#99CC99,bold')
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,    'fore:#FF0000,back:#CAC2AD,bold')

        self.SetWhitespaceForeground(True, '#7C7563')
        self.SetWhitespaceBackground(False,'#000000')

        self.SetSelForeground(True, '#000000')
        self.SetSelBackground(True,  '#9A9384')

        if basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'pythonlexer' or basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
            #Python Styles
            self.StyleSetSpec(stc.STC_P_DEFAULT,        'fore:#E6E1C4,back:#CAC2AD')
            self.StyleSetSpec(stc.STC_P_COMMENTLINE,    'fore:#000000,back:#B0EE65,bold')
            self.StyleSetSpec(stc.STC_P_NUMBER,         'fore:#000000,back:#B1A0E2')
            self.StyleSetSpec(stc.STC_P_STRING,         'fore:#000000,back:#E2D855')
            self.StyleSetSpec(stc.STC_P_CHARACTER,      'fore:#000000,back:#E2D855')
            self.StyleSetSpec(stc.STC_P_WORD,           'fore:#000000,back:#BBB09C,bold')
            self.StyleSetSpec(stc.STC_P_WORD2,          'fore:#000000,back:#E2C4A0,bold')
            self.StyleSetSpec(stc.STC_P_TRIPLE,         'fore:#7C7563,back:#CAC2AD')
            self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,   'fore:#7C7563,back:#CAC2AD')
            self.StyleSetSpec(stc.STC_P_CLASSNAME,      'fore:#000000,back:#DFA0AB,bold,underline')
            self.StyleSetSpec(stc.STC_P_DEFNAME,        'fore:#000000,back:#A0D6E2')
            self.StyleSetSpec(stc.STC_P_OPERATOR,       'fore:#7C7563,back:#CAC2AD,bold')
            self.StyleSetSpec(stc.STC_P_IDENTIFIER,     'fore:#000000,back:#CAC2AD')
            self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,   'fore:#000000,back:#B0EE65,bold')
            self.StyleSetSpec(stc.STC_P_STRINGEOL,      'fore:#E2A0A0,back:#D94C30,bold,eol')
            self.StyleSetSpec(stc.STC_P_DECORATOR,      'fore:#000000,back:#888888')

            self.StyleSetHotSpot(stc.STC_P_WORD, True)
            self.StyleSetHotSpot(stc.STC_P_WORD2, True)

        self.Colourise(0, self.GetLength())
        self.OnSetFolderMarginStyle(event)
        for i in range(0,stc.STC_INDIC_MAX + 1): self.IndicatorSetForeground(i,'#FF0000')
        if self.GetMarginWidth(3) == 0: self.SetMarginWidth(3, 16)
        # print('Notebook Theme')



class FloatingToolbar(wx.MiniFrame):
    ''' General Floating Toolbar. '''
    def __init__(self, parent, id):
        wx.MiniFrame.__init__(self, parent, -1, title='Toolbar', size=(-1, -1), style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT)

        p = wx.BITMAP_TYPE_PNG

        undotool = wx.BitmapButton(self, ID_UNDO, wx.Image(gWizSTC.imgstcDir + os.sep + u'undo16.png',p).ConvertToBitmap())
        undotool.SetToolTipString(u'Undo')
        undotool.Bind(wx.EVT_BUTTON, gWizSTC.OnUndo)
        redotool = wx.BitmapButton(self, ID_REDO, wx.Image(gWizSTC.imgstcDir + os.sep + u'redo16.png',p).ConvertToBitmap())
        redotool.SetToolTipString(u'Redo')
        redotool.Bind(wx.EVT_BUTTON, gWizSTC.OnRedo)
        cuttool = wx.BitmapButton(self, ID_CUT, wx.Image(gWizSTC.imgstcDir + os.sep + u'cut16.png',p).ConvertToBitmap())
        cuttool.SetToolTipString(u'Cut')
        cuttool.Bind(wx.EVT_BUTTON, gWizSTC.OnCut)
        copytool = wx.BitmapButton(self, ID_COPY, wx.Image(gWizSTC.imgstcDir + os.sep + u'copy16.png',p).ConvertToBitmap())
        copytool.SetToolTipString(u'Copy')
        copytool.Bind(wx.EVT_BUTTON, gWizSTC.OnCopy)
        pastetool = wx.BitmapButton(self, ID_PASTE, wx.Image(gWizSTC.imgstcDir + os.sep + u'paste16.png',p).ConvertToBitmap())
        pastetool.SetToolTipString(u'Paste')
        pastetool.Bind(wx.EVT_BUTTON, gWizSTC.OnPaste)
        selectalltool = wx.BitmapButton(self, ID_SELECTALL, wx.Image(gWizSTC.imgstcDir + os.sep + u'selectall16.png',p).ConvertToBitmap())
        selectalltool.SetToolTipString(u'Select All')
        selectalltool.Bind(wx.EVT_BUTTON, gWizSTC.OnSelectAll)
        togglecommenttool = wx.BitmapButton(self, ID_COMMENT, wx.Image(gWizSTC.imgstcDir + os.sep + u'togglecomment16.png',p).ConvertToBitmap())
        togglecommenttool.SetToolTipString(u'Toggle Comment')
        togglecommenttool.Bind(wx.EVT_BUTTON, gWizSTC.OnToggleComment)
        removetrailingwhitespacetool = wx.BitmapButton(self, ID_REMTRAILWHITESPACE, wx.Image(gWizSTC.imgstcDir + os.sep + u'removetrailingspaces16.png',p).ConvertToBitmap())
        removetrailingwhitespacetool.SetToolTipString(u'Remove Trailing Whitespace')
        removetrailingwhitespacetool.Bind(wx.EVT_BUTTON, gWizSTC.OnRemoveTrailingWhitespace)

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        hsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        hsizer1.Add(undotool, 0)
        hsizer1.Add(redotool, 0)
        hsizer1.Add(cuttool, 0)
        hsizer1.Add(copytool, 0)
        hsizer1.Add(pastetool, 0)
        hsizer1.Add(selectalltool, 0)
        hsizer1.Add(togglecommenttool, 0)
        hsizer1.Add(removetrailingwhitespacetool, 0)
        self.SetSizer(hsizer1)
        self.Fit()

        self.SetClientSize(hsizer1.GetSize())
        self.SetMinSize(self.GetSize())
        self.SetMaxSize(self.GetSize())
        self.Centre()

    def OnClose(self, event):
        gWizSTC.OneInstanceToolbar = 0
        self.Destroy()

class InstallersTabTips(wx.Frame):
    ''' The tip of the day dialog. '''
    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, -1, title='Installers Tab Tips', size=(400, 400), style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT)

        useWXVER = '2.8'

        p = wx.BITMAP_TYPE_PNG

        # Read this data file in as a list
        tipsin = open(u'%s' %bosh.dirs['bash'].join(u'installerstabtips.txt'), 'r' )
        self.tips_list = tipsin.readlines()
        tipsin.close()

        self.tipnum = random.randint(0, len(self.tips_list)) #Set tipnum to start on a random tip

        self.tipbox = wx.TextCtrl(self, wx.NewId(), str(self.tips_list[self.tipnum]), (-1, -1), (-1, 200), style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_NOHIDESEL)

        staticline = wx.StaticLine(self, -1, (-1, -1), (-1, -1), wx.LI_HORIZONTAL)

        self.nexttipbutton = wx.Button(self, wx.NewId(), 'Next Tip', (-1, -1), wx.DefaultSize)
        self.closebutton = wx.Button(self, wx.NewId(), 'Close', (-1, -1), wx.DefaultSize)

        # The seamless tiling background image.
        self.backgroundbitmap = wx.Bitmap(gWizSTC.imgstcDir + os.sep + u'seamlessbackgroundtile256.png',p)

        hsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        hsizer1.AddStretchSpacer()
        hsizer1.Add(self.nexttipbutton, 0, wx.ALIGN_RIGHT | wx.LEFT, 5)
        hsizer1.Add(self.closebutton, 0, wx.ALIGN_RIGHT | wx.LEFT, 10)

        vsizer1 = wx.BoxSizer(wx.VERTICAL)
        vsizer1.Add(self.tipbox, 1, wx.EXPAND | wx.ALL, 8)
        vsizer1.Add(staticline, 0, wx.GROW | wx.ALL , 8)
        vsizer1.Add(hsizer1, 0, wx.EXPAND | wx.ALL, 8)
        vsizer1.SetMinSize((350, -1))
        self.SetSizerAndFit(vsizer1)

        self.SetClientSize(vsizer1.GetSize())
        self.SetMinSize(self.GetSize())
        self.Centre()

        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.nexttipbutton.Bind(wx.EVT_BUTTON, self.OnNextTip)
        self.closebutton.Bind(wx.EVT_BUTTON, self.OnClose)
        if useWXVER == '2.8':
            self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        elif useWXVER == '2.9':
            self.SetBackgroundStyle(wx.BG_STYLE_ERASE)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnDrawBackground)

        self.SetIcon(wx.Icon(gWizSTC.imgstcDir + os.sep + u'lightbulb16.png',p))

    def OnNextTip(self, event):
        self.tipnum = self.tipnum + 1
        if self.tipnum == len(self.tips_list):
            self.tipnum = 0
            self.tipbox.SetValue(str(self.tips_list[0]))
        else:
            self.tipbox.SetValue(str(self.tips_list[self.tipnum]))
        # print self.tipnum

    def OnDrawBackground(self, event):
        dc = wx.ClientDC(self)

        sz = self.GetClientSize()
        w = self.backgroundbitmap.GetWidth()
        h = self.backgroundbitmap.GetHeight()
        x = 0
        y = 0

        while x < sz.width:#sz.width
            y = 0
            while y < sz.height:#sz.height
                dc.DrawBitmap(self.backgroundbitmap, x, y)
                y = y + h
            dc.DrawBitmap(self.backgroundbitmap, x, y)
            x = x + w
        # print('TiledBackground')

    def OnClose(self, event):
        self.Destroy()

class DraggableRMouseGestureMenu2(wx.PopupTransientWindow):
    ''' Since this was intended for text and also sizers don't work here...
        gonna have to revert to good ol fashoned absolute positioning.
        The goal here is to make a draggable menu that can be moved.
        Look into fixing... Side effect - Always OnTop instead of floating ontop in app.
        Maybe will alter a miniframe for this or make it into a user macro.'''
    def __init__(self, parent, style):
        wx.PopupTransientWindow.__init__(self, parent, style)
        self.menucolor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENU)
        self.menubarcolor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUBAR)
        self.menuhilightcolor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUHILIGHT)
        self.menutextcolor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUTEXT)
        self.buttonfacecolor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)

        self.SetBackgroundColour(self.menucolor)

        self.imgDir = u'%s' %bosh.dirs['images']
        self.imgstcDir = u'%s' %bosh.dirs['images'].join(u'stc')

        # 1st entry is the disabled header, the rest are...
        # String buttonNames : functionToBind = to numOfButns
        buttonNames = OrderedDict([
            ('R MGM 2 Wizard' , self.OnPass),
            ('RequireVersions' , gWizSTC.OnRequireVersionsSkyrim),
            ('SelectSubPackage' , gWizSTC.OnSelectSubPackage),#d1
            ('DeSelectSubPackage' , gWizSTC.OnDeSelectSubPackage),#d1
            ('SelectAll' , gWizSTC.OnSelectAllKeyword),#d2
            ('DeSelectAll' , gWizSTC.OnDeSelectAll),#d2
            ('SelectEspm' , gWizSTC.OnSelectEspm),#d3
            ('DeSelectEspm' , gWizSTC.OnDeSelectEspm),#d3
            ('SelectOne' , gWizSTC.OnSelectOne),#d4
            ('SelectMany' , gWizSTC.OnSelectMany),#d4
            ('"","","",\\' , gWizSTC.OnChoicesX02),
            ('Case ""' , gWizSTC.OnCase),
            ('Break' , gWizSTC.OnBreak),
            ('EndSelect' , gWizSTC.OnEndSelect),
            # ('b15' , self.OnPass),
            # ('b16' , self.OnPass),
            # ('b17' , self.OnPass),
            # ('b18' , self.OnPass),
            # ('b19' , self.OnPass),
            # ('b20' , self.OnPass),
            # ('b21' , self.OnPass),
            # ('b22' , self.OnPass),
            # ('b23' , self.OnPass),
            # ('b24' , self.OnPass),
            # ('b25' , self.OnPass),
            ])

        i = 0
        btnsz = (240, 20)
        numOfButns = 1
        border = 4
        pxInbetween = 4
        disableMenuTitle = 0
        cont2b = -1
        for key, value in buttonNames.iteritems():
            if cont2b == 1:
                key = wx.Button(self, -1, u' %s' %str(key), pos=(btnsz[0]/2 + border, pxInbetween), size=(btnsz[0]/2,btnsz[1]), style=wx.BU_LEFT)
                key.Bind(wx.EVT_BUTTON, value)
                pxInbetween += 24
                cont2b = 0
                continue
            if i in [1,2,3,4,5,6,7,8,9]:#grouped opposites/doubles
                key = wx.Button(self, -1, u' %s' %str(key), pos=(4, pxInbetween), size=(btnsz[0]/2-border/2,btnsz[1]), style=wx.BU_LEFT)
                cont2b = 1
            else:
                key = wx.Button(self, -1, u' %s' %str(key), pos=(4, pxInbetween), size=btnsz, style=wx.BU_LEFT)
            key.Bind(wx.EVT_BUTTON, value)
            numOfButns += 1
            if cont2b == 1:
                continue
            pxInbetween += 24
            if disableMenuTitle == 0:
                key.SetBackgroundColour(self.menubarcolor)
                key.Enable(False)
                disableMenuTitle = 1
            i += 1

        menuheight = (numOfButns*(border+btnsz[1])-btnsz[1]+(border/2))
        # print menuheight

        self.SetSize((btnsz[0]+border*4+20, menuheight))
        self.SetPosition((20,20))

        dragpic = wx.StaticBitmap(self, -1, wx.Bitmap(self.imgstcDir + os.sep + u'wizbain20x100.png', wx.BITMAP_TYPE_PNG), pos=(btnsz[0]+border*2, border))
        dragpic.SetBackgroundColour(self.menucolor)

        self.closebutton = wx.StaticBitmap(self, -1, wx.Bitmap(self.imgstcDir + os.sep + u'stopsign20.png', wx.BITMAP_TYPE_PNG), pos=(btnsz[0]+border*2, menuheight-border*2-20))
        self.closebutton.SetBackgroundColour(self.menucolor)

        for draggableobject in [self, dragpic]:
            draggableobject.Bind(wx.EVT_LEFT_DOWN, self.OnMouseLeftDown)
            draggableobject.Bind(wx.EVT_MOTION, self.OnMouseMotion)
            draggableobject.Bind(wx.EVT_LEFT_UP, self.OnMouseLeftUp)
            # draggableobject.Bind(wx.EVT_RIGHT_UP, self.OnDestroyMenu)

        self.closebutton.Bind(wx.EVT_LEFT_DOWN, self.OnDestroyMenu)

        wx.CallAfter(self.Refresh)

    def OnPass(self, event): pass

    def OnMouseLeftDown(self, event):
        try:
            self.Refresh()
            self.ldPos = event.GetEventObject().ClientToScreen(event.GetPosition())
            self.wPos = self.ClientToScreen((0,0))
            self.CaptureMouse()
        except:#DCLICK error
            pass

    def OnMouseMotion(self, event):
        try:
            if event.Dragging() and event.LeftIsDown():
                dPos = event.GetEventObject().ClientToScreen(event.GetPosition())
                nPos = (self.wPos.x + (dPos.x - self.ldPos.x),
                        self.wPos.y + (dPos.y - self.ldPos.y))
                self.Move(nPos)
        except:#DCLICK error
            pass

    def OnMouseLeftUp(self, event):
        try:
            self.ReleaseMouse()
        except:#DCLICK error
            pass

    def OnDestroyMenu(self, event):
        self.Show(False)
        self.Destroy()
        gWizSTC.dragmenu2 = 0
