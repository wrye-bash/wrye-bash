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
import settingsModule

#--Python
import os
import sys
import re
import imp #stc python macros
import random
from collections import OrderedDict

import webbrowser
import time
import subprocess

#--wxPython
import wx
import wx.stc as stc
import wx.lib.platebtn as platebtn
import wx.lib.dialogs
from wx.lib.gestures import MouseGestures
import wx.lib.imagebrowser as ib #alternate to thumbnailer
import wx.lib.scrolledpanel as scrolled
import wx.lib.agw.gradientbutton as GB
import wx.lib.platebtn as platebtn
import wx.lib.agw.flatmenu as FM
import wx.animate
try:
    import wx.lib.agw.thumbnailctrl as TC
except:
    wx.MessageBox(u'PIL Required for Thumbnailer', u'Import Error', wx.ICON_ERROR | wx.OK)
    wx.Bell()

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

useWXVER = '2.8'

ID_TEST = 32000

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

ID_TOOLBAR =             5000
ID_UNDO =                5001
ID_REDO =                5002
ID_UNDOALL =             5003
ID_REDOALL =             5004
ID_EMPTYUNDOBUFFER =     5005
ID_CUT =                 5006
ID_COPY =                5007
ID_PASTE =               5008
ID_DELETE =              5009
ID_SELECTALL =           5010
ID_COMMENT =             5011
ID_REMTRAILWHITESPACE =  5012

ID_SAVEASPROJECTWIZARD = 5100
ID_SAVEAS              = 5101
ID_SAVESELECTIONAS =     5102

ID_HELPGENERAL =         5201
ID_HELPAPIDOCSTR =       5202
ID_TIPSINSTALLERS =      5211

ID_MINIMEMO =            5301
ID_REMINDERCHECKLIST =   5302

ID_SETMYGAMEMODSDIRS =   5401

ID_GOTOLINE =            1095
ID_GOTOPOS =             1096

ID_FINDREPLACE =         1098
ID_FINDSELECTEDFORE =    1099

ID_BOOKMARK =            1101
ID_BOOKMARKPREVIOUS =    1102
ID_BOOKMARKNEXT =        1103
ID_REMOVEALLBOOKMARKS =  1104

ID_REQVEROB =                   2001
ID_REQVERSK =                   2002
ID_SELECTONE =                  2003
ID_SELECTMANY =                 2004
ID_OPTIONS =                    2005
ID_ENDSELECT =                  2006
ID_CASE =                       2007
ID_BREAK =                      2008
ID_SELECTALLKW =                2009
ID_DESELECTALL =                2010
ID_SELECTSUBPACKAGE =           2011
ID_DESELECTSUBPACKAGE =         2012
ID_SELECTESPM =                 2013
ID_DESELECTESPM =               2014
ID_SELECTALLESPMS =             2015
ID_DESELECTALLESPMS =           2016
ID_RENAMEESPM =                 2017
ID_RESETESPMNAME =              2018
ID_RESETALLESPMNAMES =          2019
ID_DEFAULTCHAR =                2020
ID_DATAFILEEXISTS =             2021
ID_IFELIFELSEENDIF =            2022
ID_WHILECONTINUEBREAKENDWHILE = 2023
ID_FORCONTINUEBREAKENDFOR =     2024
ID_FORSUBINSUBPACKAGES =        2025

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

ID_TXT2WIZSTRFILE =                      6001
ID_TXT2WIZSTRTEXT =                      6002

ID_ENLARGESELECTION =                    6003
ID_DECREASESELECTION =                   6004
ID_CONVERTQUOTES2SINGLE =                6005
ID_CONVERTQUOTES2DOUBLE =                6006
ID_CONVERTSWAPQUOTES =                   6007

ID_CONVERTESCAPESINGLEQUOTES =           6008
ID_CONVERTESCAPEDOUBLEQUOTES =           6009
ID_CONVERTESCSINGLEQUOTES2DOUBLEQUOTES = 6010


ID_CURRENTPACKAGE =     7001
ID_ACTIVEPROJECT =      7002
ID_SETACTIVEPROJECTTO = 7003
ID_CREATENEWPROJECT =   7004

ID_NEWLINEBEFORE =                  8001
ID_NEWLINEAFTER =                   8002
ID_CUTLINE =                        8003
ID_COPYLINE =                       8004
ID_DELETELINE =                     8005
ID_DELETELINECONTENTS =             8006
ID_DELETELINELEFT =                 8007
ID_DELETELINERIGHT =                8008
ID_SELECTLINENOEOL =                8009
ID_DUPLICATELINE =                  8010
ID_DUPLICATESELECTIONLINE =         8011
ID_DUPLICATELINENTIMES =            8012
ID_JOINLINES =                      8013
ID_SPLITLINES =                     8014
ID_LINETRANSPOSE =                  8015
ID_MOVELINEUP =                     8016
ID_MOVELINEDOWN =                   8017
ID_APPENDLINESSTR =                 8018
ID_REMOVESTRENDLINES =              8019
ID_REMOVESTRSTARTLINES =            8020
ID_PADWITHSPACES =                  8021

ID_REGEXDUPLINEINCFIRSTSEQNUM =     8101
ID_REGEXDUPLINEINCLASTSEQNUM =      8102
ID_REGEXDUPLINEINCFIRSTLASTSEQNUM = 8103
ID_SORT =                           8110

ID_TOGGLEREADONLY =      9000
ID_TOGGLEWHITESPACE =    9001
ID_TOGGLEINDENTGUIDES =  9002
ID_TOGGLEWORDWRAP =      9003
ID_TOGGLELINEHIGHLIGHT = 9004
ID_TOGGLEEOLVIEW =       9005
ID_BACKSPACEUNINDENTS =  9006
ID_BRACECOMPLETION =     9007
ID_AUTOINDENTATION =     9008
ID_EDGECOLUMN =          9009
ID_SCROLLPASTLASTLINE =  9010
ID_INTELLIWIZ =          9011
ID_INTELLICALLTIP =      9012

ID_USECUSTOMFONT =       9701
ID_USEMONOFONT =         9702
ID_SETCUSTOMFONT =       9703

ID_CODEFOLDERSTYLE1 =    9801
ID_CODEFOLDERSTYLE2 =    9802
ID_CODEFOLDERSTYLE3 =    9803
ID_CODEFOLDERSTYLE4 =    9804
ID_CODEFOLDERSTYLE5 =    9805
ID_CODEFOLDERSTYLE6 =    9806

ID_THEMENONE =              9901
ID_THEMEDEFAULT =           9902
ID_THEMECONSOLE =           9903
ID_THEMEOBSIDIAN =          9904
ID_THEMEZENBURN =           9905
ID_THEMEMONOKAI =           9906
ID_THEMEDEEPSPACE =         9907
ID_THEMEGREENSIDEUP =       9908
ID_THEMETWILIGHT =          9909
ID_THEMEULIPAD =            9910
ID_THEMEHELLOKITTY =        9911
ID_THEMEVIBRANTINK =        9912
ID_THEMEBIRDSOFPARIDISE =   9913
ID_THEMEBLACKLIGHT =        9914
ID_THEMENOTEBOOK =          9915
ID_TOGGLECODEFOLDERSTYLE =  9929
ID_TOGGLETHEMES =           9930

ID_OPENMACRODIR = 10001

def globals_gImgIdx():
    #--- Images & PopupMenu/ID Generation ---#
    global gImgDir,gImgStcDir
    gImgDir = u'%s' %bosh.dirs['images']
    gImgStcDir = u'%s' %bosh.dirs['images'].join('stc')
    p = wx.BITMAP_TYPE_PNG

    global gMgmImg,gRmbImg,gMmbImg,gYahImg,gChkImg
    gMgmImg = wx.Bitmap(gImgStcDir + os.sep + u'mousegesturemenu16.png',p)
    gRmbImg = wx.Bitmap(gImgStcDir + os.sep + u'mousebuttonright16.png',p)
    gMmbImg = wx.Bitmap(gImgStcDir + os.sep + u'mousebuttonmiddle16.png',p)
    gYahImg = wx.Bitmap(gImgStcDir + os.sep + u'youarehere16.png',p)
    gChkImg = wx.Bitmap(gImgStcDir + os.sep + u'check16.png',p)

    global gRmgmIDs,gRmgmDEFs,gRmgmLABELs
    gRmgmIDs = [ID_RMGM1,ID_RMGM2,ID_RMGM3,ID_RMGM4,ID_RMGM5,ID_RMGM6,ID_RMGM7,ID_RMGM8,ID_RMGM9]
    w = WizBAINStyledTextCtrl
    gRmgmDEFs = [w.OnRMouseGestureMenu1,w.OnRMouseGestureMenu2,w.OnRMouseGestureMenu3,w.OnRMouseGestureMenu4,w.OnRMouseGestureMenuNone,w.OnRMouseGestureMenu6,w.OnRMouseGestureMenu7,w.OnRMouseGestureMenu8,w.OnRMouseGestureMenu9]
    gRmgmLABELs = [u'Find/Replace/Mark\tCtrl+1',u'Wizard\tCtrl+2',u'\tCtrl+3',u'Case\tCtrl+4',u'Right Clicky!\tCtrl+5',u'Conversion\tCtrl+6',u'Project Manipulation(NOT DONE)\tCtrl+7',u'Line Operations\tCtrl+8',u'Options\tCtrl+9',]

    global gImgIdx
    gImgIdx = {}
    for filename in os.listdir(gImgStcDir):
        if filename.endswith('.png'):
            gImgIdx[u'%s'%filename] = wx.Bitmap(u'%s'%gImgStcDir + os.sep + u'%s'%filename,p)
        # print filename
    # print gImgIdx

def dprint(debugText):
    '''
    Usage: dprint(string)
    Using dprint here will cause a recusive loop and crash bash! DONT do it!
    Anywho... I work with bash at full screen and dislike not only the fact that the current standard out/err
    log window
    1. Doesn't float on the parent frame(making it less noticable and likely for a user to ignore)
    2. Standard out wasn't seperated from standard err, which causes more users posting something that isn't an error most of the time
    3. Standard err doesn't even ring a wx.Bell() to make an sound.
    4. Since the log window has to be a wx.TextCtrl, the styling sucks. I prefer White on Black standard command prompt colors. I like Tracebacks to be RED so they stand out.
    5. I don't understand why the devs didn't seperate their debug statements(stdout) from stderr in the first place. Hmmmmm.
    6. I prefer a wx.MiniFrame instead of a wx.Frame, because wx.Frame's takes up more room on the taskbar. This can easily be changed in the class DebugStdOutStdErrMiniFrame
    '''
    try:
        gDebugFrame.stdOUTStdERR.AppendText(u'\n%s' %debugText)
        gDebugFrame.Show()

        #Style Traceback a color
        # print (u'\n')
        for m in re.finditer(u'Traceback', gDebugFrame.stdOUTStdERR.GetValue()):
            gDebugFrame.stdOUTStdERR.SetStyle(m.start(), m.end(), wx.TextAttr('#FF0000', '#000000'))#RED
            # print ('%02d-%02d' % (m.start(), m.end()))
        #Uncomment next line to intentionally cause a error
        # causeTraceback
    except:#Allows users to not be bugged by the debug statements I have riddled all over the place if basher.settings['bash.installers.wizSTC.StdOutDebugWindow'] = 0
        pass

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
        target = u'\\'
        newtext = u'\\\\'
        try:
            self.window.SetTextUTF8(self.window.GetTextUTF8().replace(target, newtext))# Escape all Backslashes - Whole Doc
        except:
            self.window.SetText(self.window.GetText().replace(target, newtext))

        self.window.SelectAll()

        selectedtext = self.window.GetSelectedText()
        splitselectedtext = selectedtext.split('\n')
        length = len(splitselectedtext)

        for i in range(0,length,1):
            self.window.ReplaceSelection(u' \\n' + splitselectedtext[i] + u'\n')
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

        target = u'"'
        newtext = u"''"
        try:
            self.window.SetTextUTF8(self.window.GetTextUTF8().replace(target, newtext))# Convert " to '' - Whole Doc
        except:
            self.window.SetText(self.window.GetText().replace(target, newtext))

        self.window.SelectAll()
        selectedtext2 = self.window.GetSelectedText()

        self.window.SelectAll()
        self.window.DeleteBack()
        self.window.SetFocus()

        self.window.AddText(u'Mod_Readme = str("' + selectedtext2 + '")')
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
                target = u'\\'
                newtext = u'\\\\'
                try:
                    self.window.SetTextUTF8(self.window.GetTextUTF8().replace(target, newtext))# Escape all Backslashes - Whole Doc
                except:
                    self.window.SetText(self.window.GetText().replace(target, newtext))

                self.window.SelectAll()

                selectedtext = self.window.GetSelectedText()
                splitselectedtext = selectedtext.split('\n')
                length = len(splitselectedtext)

                for i in range(0,length,1):
                    self.window.ReplaceSelection(u' \\n' + splitselectedtext[i] + u'\n')
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

                target = u'"'
                newtext = u"''"
                try:
                    self.window.SetTextUTF8(self.window.GetTextUTF8().replace(target, newtext))# Convert " to '' - Whole Doc
                except:
                    self.window.SetText(self.window.GetText().replace(target, newtext))

                self.window.SelectAll()
                selectedtext2 = self.window.GetSelectedText()

                self.window.SelectAll()
                self.window.DeleteBack()
                self.window.SetFocus()

                #Prep wizstring basename and replace spaces with underscores for BAIN and/or UNIX compatability
                basename = os.path.basename(name)
                basename = basename[:basename.rfind('.')]
                basename = basename.replace(' ','_')
                self.window.AddText(basename + u' = str("' + selectedtext2 + u'")')
                self.window.StyleSetBackground(style=stc.STC_STYLE_DEFAULT, back='#CFFFCC')

                self.window.EndUndoAction()
                #------- Text to wizard string Conversion END -----------
            except IOError, error:
                dialog = wx.MessageDialog(None, u'Error opening file\n' + str(error))
                dialog.ShowModal()
            except UnicodeDecodeError, error:
                dialog = wx.MessageDialog(None, u'Cannot open non ascii files\n' + str(error))
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

class PlainSTC(stc.StyledTextCtrl):
    def __init__(self, parent):
        stc.StyledTextCtrl.__init__(self, parent, wx.ID_ANY)
        self.SetMarginWidth(1, 0)# This makes it look like just a simple textctrl.

class WizBAINStyledTextCtrl(stc.StyledTextCtrl):
    '''
        This class contains a custom StyledTextCtrl with custom (python based)lexer
        for the BAIN Wizard Script Language used for installing Mods on the Inatallers Tab.
        Usage of built-in functions is primarily accessed through Mouse Gesture Menus/Keyboard Shortcuts/Context Menus.
        There are many defs for manipulating text in various ways here.
        Saved Settings are found in basher.py as bash.installers.wizSTC.Setting

        Def Structure
        1. General Misc Defs
        2. wx.EVT_Defs
        3. stc.EVT_Defs
        #. For M or R MouseGestureMenu# Def:
               M or R MouseGestureMenu# Def
               ...followed by...
               Related Defs bound in M or R MouseGestureMenu# Def
    '''
    # Note to self. REMOVE gGlobalsDict stuff when settings dialog is implemented and users comfirm *Wow it works* and/or something didnt get forgotten.
    # converted most of gGlobals Dict to basher.settings['bash.installers.wizSTC.SETTING'] so far...
    # print basher.settings['bash.installers.wizSTC.ThemeOnStartup']
    # TODO:
    # 1. Implement color options also in settings dialog

    def __init__(self, parent, ID):
        stc.StyledTextCtrl.__init__(self, parent, -1)

        #--- Globals ---#
        global gWizSTC
        gWizSTC = self

        globals_gImgIdx()

        #--- DebugWindow for wxPython: stdout ---#
        if basher.settings['bash.installers.wizSTC.StdOutDebugWindow'] == 1:
            win = DebugStdOutStdErrMiniFrame(self, wx.SIMPLE_BORDER)
            win.Centre()
            win.Show(True)
            win.Hide()

        #--- Save As Wildcards ---#
        self.wildcard = u'All files (*.*)|*.*|' \
                    u'Cascade Style Sheets File (*.css*)|*.css*|' \
                    u'Hyper Text Markup Language Files (*.html;*.htm)|*.html;*.htm|' \
                    u'Python source (*.py;*.pyw)|*.py;*.pyw|' \
                    u'Text Files (*.txt;*.csv;*.log)|*.txt;*.csv;*.log|' \
                    u'BAIN Wizard WIPz Files (*.wiz*)|*.wiz*|' \
                    u'eXtensible Markup Language File (*.xml;*.xsml)|*.xml;*.xsml'

        #--- Only One Instance Open ---#
        self.OneInstanceThumbnailer = 0
        self.OneInstanceImageBrowser = 0
        self.OneInstanceToolbar = 0
        self.OneInstanceFindReplace = 0
        self.OneInstanceMiniMemo = 0
        self.OneInstanceDebugWindow = 0
        self.dragmenu2 = 0

        self.assignmentOperatorDict = OrderedDict([
            ('='   ,'Assignment (=)'),
            ('+='  ,'Compound Assignment (+=)'),
            ('-='  ,'Compound Assignment (-=)'),
            ('*='  ,'Compound Assignment (*=)'),
            ('/='  ,'Compound Assignment (/=)'),
            ('^='  ,'Compound Assignment (^=)'),
            ])

        self.mathOperatorDict = OrderedDict([
            ('+'   ,'Addition (+)'),
            ('-'   ,'Subtraction (-)'),
            ('*'   ,'Multiplication (*)'),
            ('/'   ,'Division (/)'),
            ('^'   ,'Exponentiation (^)'),
            ])

        self.booleanOperatorDict = OrderedDict([
            ('&'   ,'And (&)'),
            ('and' ,'And (and)'),
            ('|'   ,'Or (|)'),
            ('or'  ,'Or (or)'),
            ('!'   ,'Not (!)'),
            ('not' ,'Not (not)'),
            ('in'  ,'In (in)'),
            ('in:' ,'Case insensitive In (in:)'),
            ])

        self.comparisonOperatorDict = OrderedDict([
            ('==' ,'Exactly Equal (==)'),
            ('==:','Case insensitive Exactly Equal (==:)'),
            ('!=' ,'Not Equal (!=)'),
            ('!=:','Case insensitive Not Equal (!=:)'),
            ('>=' ,'Greater Than or Equal (>=)'),
            ('>=:','Case insensitive Greater Than or Equal (>=:)'),
            ('>'  ,'Greater Than (>)'),
            ('>:' ,'Case insensitive Greater Than (>:)'),
            ('<=' ,'Less Than or Equal (<=)'),
            ('<=:','Case insensitive Less Than or Equal (<=:)'),
            ('<'  ,'Less Than (<)'),
            ('<:' ,'Case insensitive Less Than (<:)'),
            ])

        self.bashDirsDict = OrderedDict([
            ('bainData'     ,'bainData'),
            ('bash'         ,'bash'),
            ('compiled'     ,'compiled'),
            ('converters'   ,'converters'),
            ('corruptBCFs'  ,'corruptBCFs'),
            ('db'           ,'db'),
            ('defaultTweaks','defaultTweaks'),
            ('dupeBCFs'     ,'dupeBCFs'),
            ('images'       ,'images'),
            ('installers'   ,'installers'),
            ('l10n'         ,'l10n'),
            ('mods'         ,'mods'),
            ('modsBash'     ,'modsBash'),
            ('mopy'         ,'mopy'),
            ('patches'      ,'patches'),
            ('saveBase'     ,'saveBase'),
            ('templates'    ,'templates'),
            ('tweaks'       ,'tweaks'),
            ('userApp'      ,'userApp'),
            ])

        #--- Lexers & Keywords & CallTipDict---#
        self.SetLexer(stc.STC_LEX_PYTHON)

        self.SetKeyWords(0, u' '.join(keywordWIZBAIN.kwlist))
        self.SetKeyWords(1, u' '.join(keywordWIZBAIN2.kwlist))

        self.allkeywords = sorted(keywordWIZBAIN.kwlist[:] + keywordWIZBAIN2.kwlist[:])

        self.gCallTipDict = OrderedDict([
                                   #---  0---|--- 10---|--- 20---|--- 30---|--- 40---|--- 50---|--- 60---|--- 70---|--- 80---|--- 90---|
                                   #123456789|123456789|123456789|123456789|123456789|123456789|123456789|123456789|123456789|123456789|
            ('!'                  ,'not'),
            ('&'                  ,'and'),
            (';#'                 ,';# Colored Comment'),
            (';'                  ,'; Comment'),
            ('Break'              ,'Break\nStops running lines in the current Case or Default block.\nWhile Loop - Signals the while loop to end execution, skipping to after the EndWhile.\nFor Loop - Signals the for loop to end execution, skipping to after the EndFor.\n\nUsage:\n Break'),
            ('Cancel'             ,'Cancel\nCancels the wizard, with an optional text to display\nin a dialog as to why the wizard was canceled.\n\nUsage:\n Cancel [text]\nArguments:\n text: a string or a variable containing a string\nExamples:\n Cancel\n Cancel "The wizard was cancelled because..."\n Cancel sCancelStr'),
            ('Case'               ,'Case\nThe lines following the Case will be run if the user\nselected option n on the dialog, until a Break or EndSelect is met.\n\nUsage:\n Case "Option"'),
            ('CompareGEVersion'   ,'CompareGEVersion\nUsed to test the installed version of the game\'s Graphics Extender against one you specify.\n\nUsage:\n CompareGEVersion(version_string)\nArguments:\n version_string: a string formatted to hold a file version number, like "1.2.3.93".\n For example OBGEv2 version 3 would be represented as "3.0.0.0",\n while the old OBGE would be "0.1.1.0"\nReturn:\n -1: Installed GE version is less than the version specified in version_string\n  0: Installed GE version is the same as the version specified in version_string\n  1: Installed GE version is higher than the version specified in version_string,\n     or there is no GE available for this game.'),
            ('CompareGameVersion' ,'CompareGameVersion\nUsed to test the installed version of the game against one you specify.\n\nUsage:\n CompareGameVersion(version_string)\nArguments:\n version_string: \n   a string formatted to hold a file version number, like "1.2.3.93". \n   For example the current Oblivion version would be represented as "1.2.0.416"\nReturn:\n -1: Installed Oblivion version is less than the version specified in version_string.\n  0: Installed Oblivion version is the same as the version specified in version_string.\n  1: Installed Oblivion version is higher than the version specified in version_string.'),
            ('CompareOBGEVersion' ,'CompareOBGEVersion\nUsed to test the installed version of OBGE against one you specify.\n\nDeprecated: Retained for backwards compatibility only. Use CompareGEVersion instead.'),
            ('CompareOBSEVersion' ,'CompareOBSEVersion\nUsed to test the installed version of OBSE against one you specify.\n\nDeprecated: Retained for backwards compatibility only. Use CompareSEVersion instead.'),
            ('CompareObVersion'   ,'CompareObVersion\nUsed to test the installed version of Oblivion against one you specify.\n\nDeprecated: Retained for backwards compatibility only. Use CompareGameVersion instead.'),
            ('CompareSEVersion'   ,'CompareSEVersion\nUsed to test the installed version of the game\'s Script Extender against one you specify.\n\nUsage:\n CompareSEVersion(version_string)\nArguments:\n version_string: a string formatted to hold a file version number, like "1.2.3.93". \n For example OBSE v18 would be represented as "0.0.18.6"\nReturn:\n -1: Installed SE version is less than the version specified in version_string.\n  0: Installed SE version is the same as the version specified in version_string.\n  1: Installed SE version is higher than the version specified in version_string,\n     or there is no SE available for this game.'),
            ('CompareWBVersion'   ,'CompareWBVersion\nUsed to test the current version of Wrye Bash agains one you specify.\n\nUsage:\n CompareWBVersion(version_number)\nArguments:\n version_number: a number representing the Wrye Bash version you want to check.\n For example Wrye Bash version 284 could be intered as either 284 or "284".\nReturn:\n -1: Installed Wrye Bash version is less than the version specified in version_number.\n  0: Installed Wrye Bash version is the same as the version specified in version_number.\n  1: Installed Wrye Bash version is higher than the version specified in version_number.'),
            ('Continue'           ,'Continue\nWhile Loop - Signals the while loop to begin over again at the While statement.\nFor Loop - Signals the for loop to begin another iteration.'),
            ('DataFileExists'     ,'DataFileExists\nTests for the existance of a file(s) in the Data directory. If the file you are \ntesting for is an ESP or ESM, this will also detected ghosted versions of the file.\n\nUsage:\n DataFileExists(file_name [, ..., file_name_n])\nArguments:\n file_name: a string or variable holding a string, specifying the path relative\n            to the Data directory to test. For example using "testesp.esp" would\n            test for "...path to oblivion...\\Data\\testesp.esp"\nReturn:\n True: All of the files exist.\n False: One or more of the files do not exist.\nExamples:\n DataFileExists("Oblivion.esm")\n DataFileExists("xulFallenleafEverglade.esp","The Lost Spires.esp")'),
            ('DeSelectAll'        ,'DeSelectAll\nCause all sub-packages, esps, and\nesms to be de-selected from installation.\n\nUsage:\n DeSelectAll'),
            ('DeSelectAllEspms'   ,'DeSelectAllEspms\nCause all esps and esms to be\nde-selected from installation.\n\nUsage:\n DeSelectAllEspms'),
            ('DeSelectEspm'       ,'DeSelectEspm\nCause the specified esp or esm to be deselected from installation. \nThis is equivilant to un-checking the esp or esm from the BAIN window.\n\nUsage:\n DeSelectEspm name\nArguments:\n name: string or variable holding the name of the esp or esm to de-select.\nExamples:\n DeSelectEspm "myPatch-Use ONLY if UniqueLandscapes_SomeXul Exists.esp"\n DeSelectEspm sEspmStrVar'),
            ('DeSelectSubPackage' ,'DeSelectSubPackage\nCause the specified sub-package to be de-selected from installation.\nThis is equivilant to un-checking the sub-package in the BAIN window.\n\nUsage:\n DeSelectSubPackage name\nArguments:\n name: string or variable holding the name of the sub-package to de-select.\nExamples:\n DeSelectSubPackage "05 Alt Blue Textures"\n DeSelectSubPackage sSubPackageStrVar'),
            ('Default'            ,'Default\nThe lines following the Default will be run,\nuntil a Break or EndSelect,\nif none of the Case options have been run.\n\nUsage:\n Default'),
            ('DisableINILine'     ,'DisableINILine\nTells Wrye Bash to modify an INI file by disabling a specific line in it.\nThis is accomplished by prepending ";-" to that line.\n\nUsage:\n DisableINILine(file_name, section, setting)\nArguments:\n file_name: The name of the ini file you wish to edit, relative to the Data directory.\n section: The section of the ini where setting resides, or "set" or "setGS" (see EditINI Examples)\n setting: The setting to disable.\nExample:\n DisableINILine("TargetINI.ini", "General","bSetting")\nExample Modified INI:\n [General]\n ;-bSetting'),
            ('EditINI'            ,'EditINI\nTells Wrye Bash to create an ini tweak file with some tweaks in it.\nIf the file that you tell Wrye Bash to apply the tweak to is from the\ncurrent installer or Oblivion.ini, then Wrye Bash will also automatically\napply the tweak, otherwise, it will just be generated for the user to apply manually.\n\nUsage:\n EditINI(file_name, section, setting, value [,comment])\nArguments:\n file_name: The name of the ini file you wish to edit, relative to the Data directory.\n section: The section in the ini where setting resides, or "set" or "setGS"\n setting: The setting you wish to change.\n value: The value to set the setting to.\n comment: Optional comment to include with this tweak.\nExample1:\n ;Setting an item in Oblivion.ini:\n EditINI("Oblivion.ini", "General", "bBorderRegionsEnabled", 0)\nExample1 Modified INI:\n [General]\n bBorderRegionsEnabled=0\nExample2:\n ;Setting an item in a script-like ini: Notice the use of set and setGS as the sections.\n EditINI("TargetINI.ini", "set", "ANVars.UseEW", 1)\n EditINI("TargetINI.ini", "setGS", "fPCBaseMagickaMult", 1)\nExample2 Modified INI:\n set ANVars.UseEW to 1\n setGS fPCBaseMagickaMult 1'),
            ('Elif'               ,'Elif statement evaluates to True, and the initial If and\nnone of the previous Elif\'s were True, then the lines following\nthis Elif will be run, until the next Elif, Else, or EndIf.\n\nUsage:\n If statement\n     linesOfCode...\n Elif statement\n     linesOfCode...\n Else\n     linesOfCode...\n EndIf'),
            ('Else'               ,'Else the initial If and none of the previous Elif\'s were True,\nthen the lines following will be run until an EndIf is met.\n\nUsage:\n If statement\n     linesOfCode...\n Elif statement\n     linesOfCode...\n Else\n     linesOfCode...\n EndIf'),
            ('EndFor'             ,'EndFor\nEnds the for loop.\n\nUsage:\n For arguments\n     linesOfCode...\n     Continue\n     linesOfCode...\n     Break\n     linesOfCode...\n EndFor\n\n For sub in SubPackages\n     For file in sub\n         linesOfCode...\n     EndFor\n EndFor'),
            ('EndIf'              ,'EndIf\nSignals the end of the If control block.\n\nUsage:\n If statement\n     linesOfCode...\n Elif statement\n     linesOfCode...\n Else\n     linesOfCode...\n EndIf'),
            ('EndSelect'          ,'EndSelect\nSignals the end of the Select control block.\n\nUsage:\n EndSelect'),
            ('EndWhile'           ,'EndWhile\nEnds the while loop. statement is re-evaluated, and if True,\nexecution begins again at the start of the While block.\n\nUsage:\n While statement\n     linesOfCode...\n     Continue\n     linesOfCode...\n     Break\n     linesOfCode...\n EndWhile'),
            ('Exec'               ,'Exec\nThis will cause the Wizard to execute lines that are passed to it. \nThis is usefull for creating dynamically generated menus.\n\nUsage:\n Exec(lines)\nArguements:\n lines: A string containing lines to execute, seperated by newline \n        characters, or a variable containing such a string.\nExample:\n\n Would be the same as:\n  SelectOne \'Do you like icecream?\', \\n      \'|Yes\', \'Select this if you like icecream!\', \'icecream.jpg\', \\n      \'No\', \'Select this if you do not like icecream\', \'ihateicecream.jpg\'\n  Case \'Yes\'\n      Note \'You like icecream!\'\n      Break\n  Case \'No\'\n      Note \'Why don\'t you like icecream?\'\n      Break\n  EndSelect\n\n Notice how the \\\' was interpreted as \' once the Exec was converted into lines. \n Remember to add two extra backslashes so the final statement has a backslash in it!'),
            ('False'              ,'False\nBuilt-in Constant\n\nValue:\n False(0)\nExample:\n bVar = False'),
            ('For'                ,'For\nBegins the for loop.\n\nUsage:\n For arguments\n     lines\n     Continue\n     lines\n     Break\n     lines\n EndFor\n\n For sub in SubPackages\n     For file in sub\n         lines\n     EndFor\n EndFor'),
            ('GetEspmStatus'      ,'GetEspmStatus\nTests the current status of an esp or espm in the Data directory.\nThis function takes esp/m ghosting into account when testing the status.\n\nUsage:\n GetEspmStatus(file_name)\nArguments:\n file_name: a string or variable holding a string, specifying the path\n            relative to the Data directory for the esp or esm to test.\nReturn:\n -1: The esp/m does not exist\n  0: The esp/m is not active, imported, or merged (Inactive)\n  1: The esp/m is not active, but has portions imported into the Bashed Patch (Imported)\n  2: The esp/m is active (Active)\n  3: The esp/m is merged into the Bashed Patch (Merged)\nExample:\n If GetEspmStatus("All Natural - Indoor Weather Filter For Mods.esp") == -1\n     ;Note "(Does Not Exist)"\n Elif GetEspmStatus("All Natural - Indoor Weather Filter For Mods.esp") == 0\n     Note "(Inactive)"\n Elif GetEspmStatus("All Natural - Indoor Weather Filter For Mods.esp") == 1\n     Note "(Imported)"\n Elif GetEspmStatus("All Natural - Indoor Weather Filter For Mods.esp") == 2\n     Note "(Active)"\n Elif GetEspmStatus("All Natural - Indoor Weather Filter For Mods.esp") == 3\n     Note "(Merged)"\n EndIf'),
            ('GetFilename'        ,'GetFilename\nFor a string that contains a path, returns the filename in that string.\n\nUsage:\n GetFilename(path_string)\nArguments:\n path_string: a string or variable of the path to work with.\nReturn:\n The filename, or an empty string if there is not a file or if path_string is not a path.\nExamples:\n GetFilename("C:\Program Files\Bethesda Softworks\Oblivion\Oblivion.exe")\n ;would return "Oblivion.exe"\n\n GetFilename("C:\Program Files\Bethesda Softworks\Oblivion")\n ;would return an empty string'),
            ('GetFolder'          ,'GetFolder\nFor a string that contains a path, returns the folder part of the string.\n\nUsage:\n GetFolder(path_string)\nArguments:\n path_string: a string or variable of the path to work with.\nReturn:\n The folder, or an empty string if there is not one, or if path_string is not a path.\nExamples:\n GetFolder("Data\mymod.esp")\n ;would return "Data"\n\n GetFolder("mymod.esp")\n ;would return an empty string'),
            ('If'                 ,'If\nBegins the control block. If statement evaluates to True, then\nthe lines following it will be run, until the next Elif, Else, or EndIf.\n\nUsage:\nIf statement\n    linesOfCode...\nElif statement\n    linesOfCode...\nElse\n    linesOfCode...\nEndIf'),
            ('Note'               ,'Note\nAdd a note to the user to be displayed at the end of the wizard,\non the finish page. The \'- \' will be added automatically.\n\nUsage:\n Note note\nArguments:\n note: string, string variable, or expression that evalutates\n       to a string, to be displayed on the finish page.\nExamples:\n Note "Write Wizards are Cool on the Finish Page :)"\n Note sNoteStrVar\n Note "I" + sNoteStrVar1 + "Notes, but I" + sNoteStrVar2 + "wizards!"'),
            ('RenameEspm'         ,'RenameEspm\nChange the installed name of an esp or esm.\n\nUsage:\n RenameEspm original_name, new_name\nArguments:\n original_name: the name of the esp or esm, as it appears in the BAIN package.\n new_name: the new name you want to have the esp or esm installed as.\nExamples:\n RenameEspm "Oscuro\'s_Oblivion_Overhaul.esp","OOO.esp"\n RenameEspm "Francesco\'s Leveled Creatures-Items Mod.esm","Frans.esm"'),
            ('RequireVersions'    ,'RequireVersions tests the users system against version requirements you specify.\nIf the requirements are not met, a warning dialog will be shown asking\nif you wish to continue anyway.\n\nUsage:\n RequireVersions game_version [, se_version, ge_version, wrye_bash_version]\nExamples:\n RequireVersions "1.2.0.416","0.0.20.6","3.0.0.0","295"\n RequireVersions PatchedOblivion,OBSEVersion,OBGEVersion,WryeBashVersion\n RequireVersions PatchedSkyrim\nArguments:\n game_version: Version of the game to test for.\n  See CompareGameVersion for the proper format of the string.\n se_version: Optional. Version of the Script Extender to test for.\n  See CompareSEVersion for the proper format of the string.\n ge_version: Optional. Version of the Graphics Extender to test for.\n  See CompareGEVersion for the proper format of the string.\n wrye_bash_version: Optional. Version of Wrye Bash to test for.\n  See CompareWBVersion for more info.'),
            ('ResetAllEspmNames'  ,'ResetAllEspmNames\nResets the names of all the esps and esms \nback to their default names.\n\nUsage:\n ResetAllEspmNames'),
            ('ResetEspmName'      ,'ResetEspmName\nResets the name of an esp or esm back to its default name.\n\nUsage:\n ResetEspmName original_name\nArguments:\n original_name: The name of the esp or esm,\n                as it appears in the BAIN package.\nExamples:\n ResetEspmName "OOO.esp"\n ;Reset esp name back to Oscuro\'s_Oblivion_Overhaul.esp\n ResetEspmName sEspmNameStrVar'),
            ('Return'             ,'Return\nSignals completion of the wizard.\nThis will jump right to the finish page.\n\nUsage:\n Return'),
            ('SelectAll'          ,'SelectAll\nCause all sub-packages, esps, and\nesms to be selected for installation.\n\nUsage:\n SelectAll'),
            ('SelectAllEspms'     ,'SelectAllEspms\nCause all esps and esms to\nbe selected for installation.\n\nUsage:\n SelectAllEspms'),
            ('SelectEspm'         ,'SelectEspm\nCause the specified esp or esm to be selected for installation. \nThis is equivilant to checking the esp or esm from the BAIN window.\n\nUsage:\n SelectEspm name\nArguments:\n name: string or variable holding the name of the esp or esm to select.\nExamples:\n SelectEspm "Oscuro\'s_Oblivion_Overhaul.esp"\n SelectEspm "Cobl.esm"\n SelectEspm sNameStrVar'),
            ('SelectMany'         ,'The SelectMany dialog gives you a list of options,\nwith the option to select one or more of them,\nor even none of them.\n\nExample:\n SelectMany "Choose many options.", \\\n     "|Option1","Description.","Wizard Images\\\\EnglishUSA.jpg",\\\n     "Option2","Description.","Wizard Images\\\\German.jpg",\\\n     "Option3","Description.","Wizard Images\\\\Italian.jpg"\n     Case "Option1"\n         ;#linesOfCode...\n         Break\n     Case "Option2"\n         ;#linesOfCode...\n         Break\n     Case "Option3"\n         ;#linesOfCode...\n         Break\n EndSelect'),
            ('SelectOne'          ,'The SelectOne dialog gives you a list of options,\nwith the option to select one of them.\n\nExample:\n SelectOne "Yes/No Question?", \\\n     "Yes","Description.","Wizard Images\\\\Yes.jpg",\\\n     "No","Description.","Wizard Images\\\\No.jpg"\n     Case "Yes"\n         ;#linesOfCode...\n         Break\n     Case "No"\n         ;#linesOfCode...\n         Break\n EndSelect'),
            ('SelectSubPackage'   ,'SelectSubPackage causes the specified sub-package to be selected for installation.\nThis is equivilant to checking the sub-package and all the esps or esms in that\nsubpackage in the BAIN window.\n\nUsage:\n SelectSubPackage name\nArguments:\n name: string or variable holding the name of the sub-package to select.\nExamples:\n SelectSubPackage "00 Core"\n sNameStrVar = str("01 Patch")\n SelectSubPackage sNameStrVar'),
            ('True'               ,'True\nBuilt-in Constant\n\nValue:\n True(1)\nExample:\n bVar = True'),
            ('While'              ,'While\nBegins the while loop. If statement evaluates to True, execution of the lines begins, otherwise execution skips to after the EndWhile.\n\nUsage:\n While statement\n     linesOfCode...\n     Continue\n     linesOfCode...\n     Break\n     linesOfCode...\n EndWhile'),
            ('\\"'                ,'Escape sequences are special sequences of character\nyou can put in a string to get a different character\nout when used in the wizard.\n\nUsage:\n\\"'),
            ('\\'                 ,'Escape sequences are special sequences of character\nyou can put in a string to get a different character\nout when used in the wizard.\n\nUsage:\n\\\\'),
            ('\\\''               ,'Escape sequences are special sequences of character\nyou can put in a string to get a different character\nout when used in the wizard.\n\nUsage:\n\\\''),
            ('\\n'                ,'Escape sequences are special sequences of character\nyou can put in a string to get a different character\nout when used in the wizard.\n\nUsage:\n\\t'),
            ('\\t'                ,'Escape sequences are special sequences of character\nyou can put in a string to get a different character\nout when used in the wizard.\n\nUsage:\n\\n'),
            ('and'                ,'and\n'),
            ('endswith'           ,'endswith\nTest what a string ends with.\n\nUsage:\n endswith(string, ending_1 [, ..., ending_n])\nArguments:\n string: a string, variable or constant.\n ending_1 through ending_n: a string, variable or constant.\nReturn:\n True if the string ends in any of the endings specified.\n False if the string does not end in any of the endings specified.\nExamples:\n myString = "What does this string end with"\n If endswith(myString,"with?","")\n     Note "It endswith \'with?\'"\n Else\n     Note "Nope"\n EndIf'),
            ('find'               ,'find\nReturn index of first occurrance of a substring\n\nUsage:\n find(string, substring [, start, stop])\nArguments:\n string: a string or variable to search in.\n substring: a string or variable to search for.\n start: Index at which to start searching in string. \n        (Optional. If not specified, searching will start at the beggining of string)\n stop: Index at which to stop searching. \n       (Optional. If not specified, searching will stop at the end of string)\nReturn:\n The index of the first occurance of substring in string\n -1 if substring could not be found\nExamples:\n string = "How much wood would a woodchuck chuck if a woodchuck could chuck wood?"\n substring = "wood"\n Note find(string, substring) ;Returns the 9 position in the string.'),
            ('float'              ,'float\nUsed to convert a value to decimal, for example\nconverting a value held in a string to a decimal value.\n\nUsage:\n float(value)\nArguments:\n value: any value. An integer, decimal, variable, constant, or string.\nReturn:\n Decimal value of value, if possible. For example, float(\'2.4\') would return 2.4.\n 0.0 if decimal conversion is not possible.'),
            ('in'                 ,'in\n'),
            ('in:'                ,'in:\n'),
            ('int'                ,'int\nUsed to convert a value to an integer, for example\nconverting a value held in a string to a integer value.\n\nUsage:\n int(value)\nArguments:\n value: any value. An integer, decimal, variable, constant, or string.\nReturn:\n Integer value of value, if possible. For example int(\'65\') would return 65.\n 0 if integer conversion is not possible.'),
            ('len'                ,'len\nUsed to find the length of a string.\n\nUsage:\n len(string)\nArguments:\n string: a string, variable, or constant.\nReturn:\n Length of the string if possible.\n 0 if length calculation was not possible.'),
            ('lower'              ,'lower\nConvert a string to lower case.\n\nUsage:\n lower(string)\nArguments:\n string: a string or variable.\nReturn:\n string converted to lower case, or\n The original string if an error occured. For example if you\n tried to call lower on a non-string type.'),
            ('not'                ,'not\n'),
            ('or'                 ,'or\n'),
            ('rfind'              ,'rfind\nReturn index of last occurrance of a substring\n\nUsage:\n rfind(string, substring [, start, stop])\nArguments:\n string: a string or variable to search in.\n substring: a string or variable to search for.\n start: Index to start searching in string.\n        (Optional. If not specified, searching will start at the beggining of string)\n stop: Index to start searching.\n       (Optional. If not specified, searching will stop at the end of string)\nReturn:\n The index of the last occurance of substring in string\n -1 if substring could not be found'),
            ('startswith'         ,'startswith\nTest what a string starts with.\n\nUsage:\n startswith(string, prefix_1 [, ..., prefix_n])\nArguments:\n string: a string, variable or constant.\n prefix_1 through ending_n: a string, variable or constant.\nReturn:\n True if the string begins with any of the prefixes specified.\n False if the string does not begin with any of the prefixes specified.\nExamples:\n myString = "What does this string start with?"\n If startswith(myString,"What","does this","HUH?","ribbit","")\n     Note "It startswith \'What\'"\n Else\n     Note "Nope"\n EndIf'),
            ('str'                ,'str\nUsed to convert a value into a string, for example\nwhen trying to concantenate a integer or decimal to a string.\n\nUsage:\n str(value)\nArguments:\n value: any value. An integer, decimal, variable, constant, or another string.\nReturn:\n String representation of value. For example, str(5) would return "5".'),
            ('|'                  ,'|\nDefault Character or the or operator. Place a pipe character as the first character in\nSelectOne/Many dialog options to select that option as default.\n\nExamples:\n "|Selected As A Default Option","","",\\\n "Not Selected As A Default Option","","",\\\n ...MoreOptionsLines..\n "LastOption","",""'),
            ])

        # # testformissingCallTiplist = []
        # # for word in self.allkeywords:
            # # try:
                # # print self.gCallTipDict[word]
            # # except:#snake missing calltips
                # # testformissingCallTiplist.append(str(word))
        # # print('========================================================================')
        # # print(testformissingCallTiplist)

        #Easter Egg CallTips for various non wizard script words. A little comic relief from porting all this...
        w = 'The wizard.txt install script located in\nthe head of the Package(archive/project).'
        self.gEasterEggCallTipDict = OrderedDict([
            ('Wrye'      ,'Wrye is the Monkey GOD of Modding!'),
            ('Bash'      ,'Wrye Bash! The Ultimate Mod Utility.\nWhat else where you thinking of...'),
            ('Metallicow','Shiny Graphics and WizBAIN Editor author.\n\nMooo.'),
            ('BAIN'      ,'BAsh INstaller'),
            ('WizBAIN'   ,'WIZard BAsh INstaller'),('WIZBAIN','WIZard BAsh INstaller'),
            ('Wizard'    ,w),('wizard',w),('WIZARD',w),
            ('RTFM'      ,'Read The Fine Manual.'),
            ('IIRC'      ,'If I Remember Correctly.....ummm'),
            ])

        #--- Misc or Todo(maybe) ---#
        self.SetEOLMode(stc.STC_EOL_LF) # UNIX
        self.SetBufferedDraw(basher.settings['bash.installers.wizSTC.UseBufferedDraw']) # If drawing is buffered then each line of text is drawn into a bitmap buffer before drawing it to the screen to avoid flicker.
        self.SetOvertype(basher.settings['bash.installers.wizSTC.OvertypeOnOff']) # Set to overtype (true) or insert mode.
        self.SetEndAtLastLine(basher.settings['bash.installers.wizSTC.ScrollingPastLastLine'])
        self.SetReadOnly(basher.settings['bash.installers.wizSTC.ReadOnly'])

        # Being there is no wx.MenuBar dont use CmdKeyAssigns otherwise things wont work right. These are all acounted for with functions in the KeyDownEvent.
        ## self.CmdKeyAssign(ord('C'), stc.STC_SCMOD_CTRL, stc.STC_CMD_UNDO) # Set a acellerator key to do something (Ctrl+Key)

        #--- Caret Options ---#
        self.SetCaretPeriod(basher.settings['bash.installers.wizSTC.CaretSpeed'])                  # Set the time in milliseconds that the caret is on and off. 0 = steady on.
        self.SetCaretForeground(basher.settings['bash.installers.wizSTC.CaretForegroundColor'])    # The color of the caret ; 'blue' or '#0000FF'
        self.SetCaretLineVisible(basher.settings['bash.installers.wizSTC.CaretLineVisible'])       # Default color should... be the same as the background unless SetCaretLineBackground is called to change its color. # Display the background of the line containing the caret in a different colour.
        self.SetCaretLineBackground(basher.settings['bash.installers.wizSTC.CaretLineBackground']) # Set the color of the background of the line containing the caret.(Currently selected line)
        ## self.SetCaretLineBackAlpha(basher.settings['bash.installers.wizSTC.CaretLineBackgroundAlpha']) # Set background alpha of the caret line. 0-255
        self.SetCaretWidth(basher.settings['bash.installers.wizSTC.CaretPixelWidth'])              # Set the width of the insert mode caret. 0 - 3 seems to be the max
        self.EnsureCaretVisible() # Ensure the caret is visible.

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
        self.MarkerDefineBitmap(0, gImgIdx['caretlinebm16.png'])
        self.MarkerDefineBitmap(1, gImgIdx['bookmark16.png'])

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

        #--- Brace Completion stuff ---#
        self.brace_dict={40:')',
                         91:']',
                         123:'}',
                         39:"'",
                         34:'"'}

        #--- Bind Events ---#
        # wx.EVTs
        self.Bind(wx.EVT_CONTEXT_MENU,          self.OnContextMenu)
        self.Bind(wx.EVT_KEY_DOWN,              self.OnKeyDown)
        self.Bind(wx.EVT_KEY_UP,                self.OnKeyUp)
        self.Bind(wx.EVT_LEFT_DOWN,             self.OnLeftDown)
        ## self.Bind(wx.EVT_LEFT_UP,               self.OnLeftUp)
        ## self.Bind(wx.EVT_RIGHT_DOWN,            self.OnRightDown)
        ## self.Bind(wx.EVT_RIGHT_UP,              self.OnRightUp)
        self.Bind(wx.EVT_SET_FOCUS,             self.OnSTCGainFocus)
        self.Bind(wx.EVT_KILL_FOCUS,            self.OnSTCLoseFocus)
        # wx.stc.EVTs
        self.Bind(stc.EVT_STC_UPDATEUI,         self.OnUpdateUI)
        self.Bind(stc.EVT_STC_MARGINCLICK,      self.OnMarginClick)
        self.Bind(stc.EVT_STC_CHARADDED,        self.OnCharAdded) # Brace Completion
        ## self.Bind(stc.EVT_STC_ZOOM,               self.OnSTCZoom)
        self.Bind(stc.EVT_STC_HOTSPOT_DCLICK,     self.OnHotSpotDClick)
        self.Bind(stc.EVT_STC_CALLTIP_CLICK,      self.OnCallTipClick)
        self.Bind(stc.EVT_STC_AUTOCOMP_SELECTION, self.OnAutoCompSelection)
        self.Bind(stc.EVT_STC_ROMODIFYATTEMPT,    self.OnReadOnlyModifyAttempt)
        ## self.Bind(stc.EVT_STC_DWELLSTART,         self.OnMouseDwellStart)
        ## self.Bind(stc.EVT_STC_DWELLEND,           self.OnMouseDwellEnd)
        ## self.Bind(stc.EVT_STC_MACRORECORD,        self.OnRecordingTheMacro)

        #--- Flags ---#
        self.autocompflag = 0 #Off by default
        self.autocompstartpos = 0

        #--- Macro Recording ---#
        self.macrorecordingflag = 0 #Off by default
        ## self.macrostring = []

        txtfile = u'%s' %bosh.dirs['mopy'].join('macro').join('LineList.txt')
        if os.path.exists(txtfile):
            self.mylineslist = []
            filein = open(txtfile, 'r')
            templist = filein.readlines()
            for line in templist:
                 rstripedLine = line.rstrip('\n')
                 self.mylineslist.append(rstripedLine)
            filein.close()
        else:
            self.mylineslist = [u'WARNING!',u'%s'%txtfile,u'Wasn\'t Found.',u'Create a new one...Dummy',]

        #--- Register AutoComplete Images ---#
        self.RegisterImage(5, gImgIdx['wizardhat16.png'])

        #--- Mouse Gestures ---#
        ''' Mouse Gestures...Visualize your numpad and start drawing from 5 to an outside number. 9 possible events
        # [7][8][9]
        # [4][5][6]
        # [1][2][3] '''
        # rmouse
        self.rmousegesture = MouseGestures(self, Auto=True, MouseButton=wx.MOUSE_BTN_RIGHT)#wx.MOUSE_BTN_LEFT,wx.MOUSE_BTN_RIGHT
        self.rmousegesture.AddGesture(u'L', self.OnRMouseGestureMenu4, u'You moved left')
        self.rmousegesture.AddGesture(u'R', self.OnRMouseGestureMenu6, u'You moved right')
        self.rmousegesture.AddGesture(u'U', self.OnRMouseGestureMenu8, u'You moved up')
        self.rmousegesture.AddGesture(u'D', self.OnRMouseGestureMenu2, u'You moved down')
        # The diag gestures
        self.rmousegesture.AddGesture(u'1', self.OnRMouseGestureMenu1, u'You moved left/down  diag1')
        self.rmousegesture.AddGesture(u'3', self.OnRMouseGestureMenu3, u'You moved right/down diag3')
        self.rmousegesture.AddGesture(u'7', self.OnRMouseGestureMenu7, u'You moved left/up    diag7')
        self.rmousegesture.AddGesture(u'9', self.OnRMouseGestureMenu9, u'You moved right/up   diag9')
        self.rmousegesture.AddGesture(u'' , self.OnRMouseGestureMenuNone, u'Context Key/Right Mouse Context Menu')

        self.rmousegesture.SetGesturesVisible(True)
        self.rmousegesture.SetGesturePen(wx.Colour(230, 230, 76), 5)#(color, linepixelwidth)
        self.rmousegesture.SetWobbleTolerance(basher.settings['bash.installers.wizSTC.MouseGestureWobbleTolerance'])

        # mmouse
        self.mmousegesture = MouseGestures(self, Auto=True, MouseButton=wx.MOUSE_BTN_MIDDLE)
        self.mmousegesture.AddGesture('' , self.OnMMouseGestureMenuNone, u'Middle Mouse Context Menu')
        self.mmousegesture.SetGesturesVisible(True)
        self.mmousegesture.SetGesturePen(wx.Colour(255, 156, 0), 5)#Orange
        self.mmousegesture.SetWobbleTolerance(basher.settings['bash.installers.wizSTC.MouseGestureWobbleTolerance'])

        #--- Rectangular Selection ---#
        self.rect_selection_clipboard_flag = False #Set to false initially so that if upon open user tries to paste, it won't throw an error.

        #--- Set Theme ---#
        self.OnSetTheme(self)

        #--- Folder Margin Style ---#
        self.OnSetFolderMarginStyle(self)#Hmmmm. This might have problems working on startup. I think it is fixed.

    def OnPass(self, event): pass

    def OnSelectNone(self, event):
        ''' Select nothing in the document. (DeSelect) '''
        p = self.GetCurrentPos()
        self.SetSelection(p,p)

    def OnContextMenu(self, event):
        ''' wx.EVT_CONTEXT_MENU
        This handles making the context key still work and a none mouse gesture pull up
        the context without poping up again after a different mouse gesture menu. '''
        pass
        # print ('This is handled by OnRMouseGestureMenuNone')

    def OnLeftDown(self, event):
        ''' wx.EVT_LEFT_DOWN '''
        # print('OnLeftDown')
        event.Skip()

        if self.OneInstanceFindReplace == 1:
            #losing focus trancparency handles these wigets[self.findwhatcomboctrl,self.findallfulllist,self.replacewithcomboctrl]
            if gFindReplaceMiniFrame.transparencyradiobox.GetSelection() == 0:#only on losing focus
                gFindReplaceMiniFrame.SetTransparent(basher.settings['bash.installers.wizSTC.SetFindReplaceTransparency'])

        # pass

    def OnLeftUp(self, event):
        ''' wx.EVT_LEFT_UP '''
        print('OnLeftUp')
        pass

    def OnRightDown(self, event):
        ''' wx.EVT_RIGHT_DOWN '''
        print('OnRightDown')
        pass

    def OnRightUp(self, event):
        ''' wx.EVT_RIGHT_UP '''
        print('OnRightUp')
        pass

    def OnKeyUp(self, event):
        ''' wx.EVT_KEY_UP '''
        key = event.GetKeyCode()

        #--- The Auto-indentation Feature. ---#
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
        ''' wx.EVT_KEY_DOWN '''
        key = event.GetKeyCode()
        # print (key)

        if self.CallTipActive():
            self.CallTipCancel()
        if self.autocompflag == 1:
            self.autocompflag = 0

        event.Skip()#Removing this line will cause the keyboard to NOT function properly!

        # Handle the Non-STC Standard Keyboard Accelerators Here since wtf, there is no wx.Menu.
        if key == 27: self.OnSelectNone(event) #Escape doesn't like accelerators on MS-Windows for some reason...

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

        if event.ControlDown() and event.ShiftDown() and key == 66:#Ctrl+B
            self.OnHopPreviousBookmark(event)
        elif event.ControlDown() and event.AltDown() and key == 66:#Ctrl+B
            self.OnHopNextBookmark(event)
        elif event.ControlDown() and key == 66:#Ctrl+B
            self.OnToggleBookmark(event)

        if event.ControlDown() and key == 67:#Ctrl+C
            self.OnCopy(event)

        if event.ControlDown() and key == 70:#Ctrl+F
            self.OnFindReplaceOneInstanceChecker(event)

        if event.ControlDown() and key == 71:#Ctrl+G
            self.OnGoToLine(event)

        if event.ControlDown() and key == 77:#Ctrl+M
            if self.OneInstanceMiniMemo == 0:
                self.OnMiniMemo(event)
            else:
                gMiniMemo.OnDestroyMemo(event)

        if event.ControlDown() and key == 81:#Ctrl+Q
            self.OnToggleComment(event)

        if event.ControlDown() and key == 86:#Ctrl+V
            if self.rect_selection_clipboard_flag:
                self.OnColumnPasteFromKeyboardShortcut(event)
            else:
                self.OnPasteFromKeyboardShortcut(event)

        if event.ControlDown() and key == 87:#Ctrl+W
            self.OnShowWordCompleteBox(event)

        if event.ControlDown() and event.ShiftDown() and key == 315:#Ctrl+Shift+Up
            self.OnMoveLineUp(event)

        if event.ControlDown() and event.ShiftDown() and key == 317:#Ctrl+Shift+Down
            self.OnMoveLineDown(event)

        # if key == 340:#F1
            # pass

        # if key == 341:#F2
            # pass

        # if key == 342:#F3
            # pass

        if key == 343:#F4
            self.OnFindSelectedForwards(event)

        # if key == 344:#F5
            # pass

        # if key == 345:#F6
            # pass

        if key == 346:#F7
            self.OnDuplicateLineIncrementFirstSeqNumbers(event)

        if key == 347:#F8
            self.OnDuplicateLineIncrementLastSeqNumbers(event)

        if key == 348:#F9
            self.OnDuplicateLineIncrementFirstAndLastSeqNumbers(event)

        # if key == 349:#F10
            # pass

        if key == 350:#F11
            self.OnToggleFolderMarginStyle(event)

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
        ''' stc.EVT_STC_UPDATEUI
        If the text, the styling, or the selection has been changed, This is bound by stc.EVT_STC_UPDATEUI above.
        Used to update any GUI elements that should change as a result. Also for other tasks that can be performed using background processing. '''

        #Responsible for the bad brace check feature.
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

        # Update the find replace line pos col numbers if dialog is open
        if self.OneInstanceFindReplace == 1:
            gFindReplaceMiniFrame.spinnerctrl1.SetRange(1, self.GetLineCount())
            gFindReplaceMiniFrame.staticlinecount.SetLabel(u'Max %s' %self.GetLineCount())

            gFindReplaceMiniFrame.spinnerctrl3.SetRange(0,self.GetLength())
            gFindReplaceMiniFrame.staticpos.SetLabel(u'Max %s' %self.GetLength())

            currentline = self.GetCurrentLine()
            linelen = self.GetLineEndPosition(currentline) - self.PositionFromLine(currentline)
            gFindReplaceMiniFrame.spinnerctrl2.SetRange(0,linelen)
            gFindReplaceMiniFrame.staticcol.SetLabel(u'Max %s' %linelen)

            if self.GetSelectionStart() == self.GetSelectionEnd(): gFindReplaceMiniFrame.checkboxinselection.Enable(False)
            else: gFindReplaceMiniFrame.checkboxinselection.Enable(True)

            #losing focus trancparency handles these wigets[self.findwhatcomboctrl,self.findallfulllist,self.replacewithcomboctrl]
            if gFindReplaceMiniFrame.transparencyradiobox.GetSelection() == 0:#only on losing focus
                gFindReplaceMiniFrame.SetTransparent(basher.settings['bash.installers.wizSTC.SetFindReplaceTransparency'])

    def OnMarginClick(self, event):
        ''' stc.EVT_STC_MARGINCLICK
        Event occurs when the bookmark, line or code fold margins are clicked. '''
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
            linenum = self.LineFromPosition(event.GetPosition())
            # print self.MarkerGet(self.GetCurrentLine())
            if self.MarkerGet(linenum) == 1:
                self.MarkerAdd(linenum, 1)
            elif self.MarkerGet(linenum) == 3:
                self.MarkerDelete(linenum, 1)#Mark with user bookmark
            else:
                if self.MarkerGet(linenum) != 2:
                    self.MarkerAdd(linenum, 1)
                else:
                    self.MarkerDelete(linenum, 1)

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
        ''' stc.EVT_STC_CHARADDED
        Brace Completion. If the feature is enabled, it adds a closing brace at the current caret/cursor position.
        Intelliwiz for AutoComplete. Handles AutoCompetion AutoComplete if charadded is last char to add to find a correct case keyword'''
        key = event.GetKey()
        # print key
        #--- Brace Completion ---#
        if basher.settings['bash.installers.wizSTC.BraceCompletion'] == 1:
            if key in [40,91,123,39,34]: #These numbers are the keycodes of the braces defined above: ( [ { ' " (the first half of them)
                self.AddText(self.brace_dict[key])
                self.CharLeft()

        #--- Intelliwiz for AutoComplete ---#
        #Everytime new keywords are added to the wizard script language, this code should be re-evaluated for correctness.
        #Char Keyword Startswith, Number of chars to figure out what the user is typing...
        #B  1               'Break',
        #Ca? 3              'Cancel',
        #Ca? 3              'Case',
        #CompareG? 9        'CompareGEVersion',
        #CompareG? 9        'CompareGameVersion',
        #CompareOB? 10      'CompareOBGEVersion',
        #CompareOB? 10      'CompareOBSEVersion',
        #CompareO? 9        'CompareObVersion',
        #Compare? 8         'CompareSEVersion',
        #Compare? 8         'CompareWBVersion',
        #Co? 3              'Continue',
        #D? 2               'DataFileExists',
        #De? 3              'Default',
        #NULL               'DeSelectAll',
        #DeSelectAll? 12    'DeSelectAllEspms',
        #DeSelect? 9        'DeSelectEspm',
        #DeSelect? 9        'DeSelectSubPackage',
        #D? 2               'DisableINILine',
        #E? 2               'EditINI',
        #El? 3              'Elif',
        #El? 3              'Else',
        #End? 4             'EndFor',
        #End? 4             'EndIf',
        #End? 4             'EndWhile',
        #End? 4             'EndSelect',
        #E? 2               'Exec',
        #F? 2               'False',
        #F? 2               'For',
        #Get? 4             'GetEspmStatus',
        #GetF? 5            'GetFilename',
        #GetF? 5            'GetFolder',
        #I 1                'If',
        #N 1                'Note',
        #Re? 3              'RenameEspm',
        #Re? 3              'RequireVersions',
        #Reset? 6           'ResetAllEspmNames',
        #Reset? 6           'ResetEspmName',
        #Re? 3              'Return',
        #NULL               'SelectAll',
        #SelectAll? 10      'SelectAllEspms',
        #Select? 7          'SelectEspm',
        #Select? 7          'SelectMany',
        #Select? 7          'SelectOne',
        #Select? 7          'SelectSubPackage',
        #T 1                'True',
        #W 1                'While',

        #e 1                'endswith',
        #f? 2               'find',
        #f? 2               'float',
        #i 1                'int',
        #l? 2               'len',
        #l? 2               'lower',
        #r 1                'rfind',
        #st? 3              'startswith',
        #NULL               'str',

        if self.AutoCompActive():
            if basher.settings['bash.installers.wizSTC.IntelliWiz'] == 1:
                autocompstartpos = self.AutoCompPosStart()
                #Get Text from position range everytime a character is added.
                #Longest known words at present time is 18 chars. WB298
                #For example, if AutoComplete is open and the user types the char "B", since "Break" is
                # the only word that startswith "B", then it will automatically complete the word intelligently.
                #Eventually I will look into generating the needed code here with a startswith function loop from all keywords or something...
                pos = self.GetCurrentPos()
                howFarAmI = pos - autocompstartpos
                maybeusertypod = 0
                # print howFarAmI
                if howFarAmI == 1:    onechar     = self.GetTextRange(pos-1,pos)
                elif howFarAmI == 2:  twochars    = self.GetTextRange(pos-2,pos)
                elif howFarAmI == 3:  threechars  = self.GetTextRange(pos-3,pos)
                elif howFarAmI == 4:  fourchars   = self.GetTextRange(pos-4,pos)
                elif howFarAmI == 5:  fivechars   = self.GetTextRange(pos-5,pos)
                elif howFarAmI == 6:  sixchars    = self.GetTextRange(pos-6,pos)
                elif howFarAmI == 7:  sevenchars  = self.GetTextRange(pos-7,pos)
                elif howFarAmI == 8:  eightchars  = self.GetTextRange(pos-8,pos)
                elif howFarAmI == 9:  ninechars   = self.GetTextRange(pos-9,pos)
                elif howFarAmI == 10: tenchars    = self.GetTextRange(pos-10,pos)
                elif howFarAmI == 11: elevenchars = self.GetTextRange(pos-11,pos)
                elif howFarAmI == 12: twelvechars = self.GetTextRange(pos-12,pos)

                if howFarAmI == 1:
                    if onechar in ['B']:#Break
                        self.AutoCompSelect(onechar)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                    elif onechar in ['I']:#If
                        self.AutoCompSelect(onechar)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                    elif onechar in ['N']:#Note ""
                        self.AutoCompSelect(onechar)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText(' ""')
                        self.CharLeft()
                    elif onechar in ['T']:#True
                        self.AutoCompSelect(onechar)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                    elif onechar in ['W']:#While
                        self.AutoCompSelect(onechar)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                    elif onechar in ['e']:#endswith("","")
                        self.AutoCompSelect(onechar)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText('("","")')
                        for i in range(0,5):
                            self.CharLeft()
                    elif onechar in ['i']:#int("")
                        self.AutoCompSelect(onechar)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText('("")')
                        self.CharLeft()
                        self.CharLeft()
                    elif onechar in ['r']:#rfind("","")
                        self.AutoCompSelect(onechar)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText('("","")')
                        for i in range(0,5):
                            self.CharLeft()
                elif howFarAmI == 2:
                    if twochars in ['le']:#len(sSomestring) or whereas len('sSomestring') might be caught by brace completion above.
                        self.AutoCompSelect(twochars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText('()')
                        self.CharLeft()
                        # TODO Maybe: Optionally send a event to add another autocompletion box that grabs all strings variables, etc...
                    elif twochars in ['lo']:#lower(sSomestring) or whereas len('sSomestring') might be caught by brace completion above.
                        self.AutoCompSelect(twochars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText('()')
                        self.CharLeft()
                    elif twochars in ['Di']:#DisableINILine("TargetINI.ini","General","bSetting")
                        self.AutoCompSelect(twochars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText('("","","")')
                        for i in range(0,8):
                            self.CharLeft()
                    elif twochars in ['Ed']:#EditINI("","","", ,"")
                        self.AutoCompSelect(twochars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText('("","","", ,"")')
                        for i in range(0,13):
                            self.CharLeft()
                    elif twochars in ['Da','Ex','fl']:#DataFileExists(""),Exec(""),float("")
                        self.AutoCompSelect(twochars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText('("")')
                        self.CharLeft()
                        self.CharLeft()
                    elif twochars in ['Fa']:#False
                        self.AutoCompSelect(twochars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                    elif twochars in ['Fo']:#For
                        self.AutoCompSelect(twochars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                    elif twochars in ['fi']:#find("","")
                        self.AutoCompSelect(twochars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText('("","")')
                        for i in range(0,5):
                            self.CharLeft()
                elif howFarAmI == 3:
                    # print(threechars)
                    if threechars in ['Can']:#Cancel ""
                        self.AutoCompSelect(threechars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText(' ""')
                        self.CharLeft()
                    elif threechars in ['Cas']:#Case ""
                        self.AutoCompSelect(threechars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText(' ""')
                        self.CharLeft()
                    elif threechars in ['Con']:#Continue
                        self.AutoCompSelect(threechars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                    elif threechars in ['Def']:#Default
                        self.AutoCompSelect(threechars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                    elif threechars in ['Eli']:#Elif
                        self.AutoCompSelect(threechars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                    elif threechars in ['Els']:#Else
                        self.AutoCompSelect(threechars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                    elif threechars in ['Req']:#RequireVersions "","","",""
                        self.AutoCompSelect(threechars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText(' "","","",""')
                        for i in range(0,10):
                            self.CharLeft()
                    elif threechars in ['Ren']:#RenameEspm "",""
                        self.AutoCompSelect(threechars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText(' "",""')
                        for i in range(0,4):
                            self.CharLeft()
                    elif threechars in ['Ret']:#Return
                        self.AutoCompSelect(threechars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                    elif threechars in ['str']:#str("")
                        self.AutoCompSelect(threechars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText('("")')
                        self.CharLeft()
                        self.CharLeft()
                    elif threechars in ['sta']:#startswith("","")
                        self.AutoCompSelect(threechars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText('("","")')
                        for i in range(0,5):
                            self.CharLeft()
                elif howFarAmI == 4:
                    if fourchars in ['EndF']:#EndFor
                        self.AutoCompSelect(fourchars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                    elif fourchars in ['EndI']:#EndIf
                        self.AutoCompSelect(fourchars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                    elif fourchars in ['EndS']:#EndSelect
                        self.AutoCompSelect(fourchars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                    elif fourchars in ['EndW']:#EndWhile
                        self.AutoCompSelect(fourchars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                    elif fourchars in ['GetE']:#GetEspmStatus("")
                        self.AutoCompSelect(fourchars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText('("")')
                        self.CharLeft()
                        self.CharLeft()
                elif howFarAmI == 5:
                    if fivechars in ['GetFi']:#GetFilename("")
                        self.AutoCompSelect(fivechars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText('("")')
                        self.CharLeft()
                        self.CharLeft()
                    elif fivechars in ['GetFo']:#GetFolder("")
                        self.AutoCompSelect(fivechars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText('("")')
                        self.CharLeft()
                        self.CharLeft()
                elif howFarAmI == 6:
                    if sixchars in ['ResetA']:#ResetAllEspmNames
                        self.AutoCompSelect(sixchars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                    elif sixchars in ['ResetE']:#ResetEspmName ""
                        self.AutoCompSelect(sixchars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText(' ""')
                        self.CharLeft()
                elif howFarAmI == 7:
                    if sevenchars in ['SelectE']:#SelectEspm ""
                        self.AutoCompSelect(sevenchars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText(' ""')
                        self.CharLeft()
                    elif sevenchars in ['SelectM']:#SelectMany "", \
                        self.AutoCompSelect(sevenchars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText(' "", \\')
                        for i in range(0,4):
                            self.CharLeft()
                    elif sevenchars in ['SelectO']:#SelectOne "", \
                        self.AutoCompSelect(sevenchars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText(' "", \\')
                        for i in range(0,4):
                            self.CharLeft()
                    elif sevenchars in ['SelectS']:#SelectSubPackage ""
                        self.AutoCompSelect(sevenchars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText(' ""')
                        self.CharLeft()
                elif howFarAmI == 8:
                    if eightchars in ['CompareS','CompareW']:#CompareSEVersion(""),CompareWBVersion("")
                        self.AutoCompSelect(eightchars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText('("")')
                        self.CharLeft()
                        self.CharLeft()
                elif howFarAmI == 9:
                    if ninechars in ['CompareGE','CompareGa','CompareOb']:#CompareGEVersion(""),CompareGameVersion(""),CompareObVersion("")
                        self.AutoCompSelect(ninechars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText('("")')
                        self.CharLeft()
                        self.CharLeft()
                    elif ninechars in ['DeSelectE','DeSelectS']:#DeSelectEspm "",DeSelectSubPackage ""
                        self.AutoCompSelect(ninechars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText(' ""')
                        self.CharLeft()
                elif howFarAmI == 10:
                    if tenchars in ['CompareOBG','CompareOBS']:#CompareOBGEVersion(""),CompareOBSEVersion("")
                        self.AutoCompSelect(tenchars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                        self.AddText('("")')
                        self.CharLeft()
                        self.CharLeft()
                    elif tenchars in ['SelectAllE']:#SelectAllEspms
                        self.AutoCompSelect(tenchars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                elif howFarAmI == 11:
                    pass #None yet
                    ##if elevenchars in ['SomeNewKeyw']:#SomeNewKeyword
                        ##doSomething
                elif howFarAmI == 12:
                    if twelvechars in ['DeSelectAllE']:#DeSelectAllEspms
                        self.AutoCompSelect(twelvechars)
                        kwpos = self.AutoCompGetCurrent()
                        self.AutoCompComplete()
                        autocompendpos = self.GetCurrentPos()
                else:#Dont throw an error if howFarAmI exceeds #. Also don't try to show a unknown Calltip.
                    kwpos = self.AutoCompGetCurrent()
                    autocompendpos = self.GetCurrentPos()
                    maybeusertypod = 1

                    autocompletedkeywordis = self.GetTextRange(autocompstartpos,autocompendpos)
                    # print self.GetTextRange(autocompstartpos,autocompendpos)

                    if maybeusertypod == 1:
                        pass
                    else:
                        if basher.settings['bash.installers.wizSTC.IntelliCallTip'] == 1:
                            try:
                                self.CallTipSetBackground('#D7DEEB')
                                self.CallTipSetForeground('#666666')
                                self.CallTipShow(pos, self.gCallTipDict[u'%s'%autocompletedkeywordis])
                                #try to highlight the keyword
                                try:
                                    match = re.search(u'%s' %autocompletedkeywordis, self.gCallTipDict[u'%s' %autocompletedkeywordis])
                                    foundpostions = (match.span())
                                    self.CallTipSetHighlight(foundpostions[0], foundpostions[1])
                                    self.CallTipSetForegroundHighlight('#FF0000')
                                except:
                                    pass#NoneType
                            except:
                                self.CallTipSetBackground('#F6F68C')
                                self.CallTipSetForeground('#666666')
                                self.CallTipShow(pos,'Hmmm. No CallTip for that...')

    def OnCallTipClick(self, event):
        ''' stc.EVT_STC_CALLTIP_CLICK
        Binding this will cancel the CallTip when clicked on, instead of default behaivior which is nothing. '''
        # self.CallTipSetHighlight(2,15)#Can only use this once for positions, not multiple
        # self.CallTipSetForegroundHighlight('#00AA00')
        # self.CallTipSetForeground('#AA0000')
        # self.CallTipSetBackground('#0000AA')
        ## self.CallTipUseStyle(2)
        # print self.CallTipPosAtStart()
        # print self.CallTipActive()
        self.CallTipCancel()

    def OnMMouseGestureMenuNone(self, event):
        ''' Middle Clicky! Call the Middle Mouse Gesture Menu.
        NUMPAD:5
        [7][8][9]
        [4][@][6]
        [1][2][3]
        '''
        # dprint ('MMouse None')
        middleclickmenu = wx.Menu()

        p = wx.BITMAP_TYPE_PNG

        mcheader1 = wx.MenuItem(middleclickmenu, 0000, u'M MGM 5 Macro', u'ContextMenu5')
        mcheader1.SetBackgroundColour('#FF8800')
        middleclickmenu.AppendItem(mcheader1)
        mcheader1.SetDisabledBitmap(gImgIdx[u'mousebuttonmiddle16.png'])
        mcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            mgm = wx.MenuItem(middleclickmenu, gRmgmIDs[i-1], u'&R MGM %s %s'%(str(i),gRmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
            mgm.SetBitmap(gMgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(middleclickmenu, ID_MMGM5, u'&M MGM 5 You Are Here!\tCtrl+0', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(gYahImg)
        mgm.SetBackgroundColour('#F4FAB4')
        mgm.Enable(False)
        submenu.AppendItem(mgm)
        middleclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        openmacrodir = wx.MenuItem(middleclickmenu, ID_OPENMACRODIR, u'&Open Macro Directory...', u' Open Macro Directory...')
        openmacrodir.SetBitmap(gImgIdx['macro16.png'])
        middleclickmenu.AppendItem(openmacrodir)

        middleclickmenu.AppendSeparator()

        macroTxtDir = bosh.dirs[u'mopy'].join(u'macro').join(u'txt')
        macroPyDir = bosh.dirs[u'mopy'].join(u'macro').join(u'py')

        submenu = wx.Menu()

        for line in self.mylineslist:
            if line == u'':
                continue
            else:
                newid = wx.NewId()
                addtextlinelist = wx.MenuItem(middleclickmenu, newid, u'%s'%line, u' %s'%line)
                addtextlinelist.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, '%(mono)s'%faces))
                if self.mylineslist[0] == u'WARNING!':
                    addtextlinelist.SetBitmap(wx.Bitmap(gImgDir + os.sep + u'errormarker24.png',p))
                submenu.AppendItem(addtextlinelist)
                wx.EVT_MENU(middleclickmenu, newid, self.OnAddTextMenuLabel)
        middleclickmenu.AppendMenu(wx.NewId(), u'Add Text: Line Macro', submenu)

        middleclickmenu.AppendSeparator()

        for filename in os.listdir(u'%s' %macroTxtDir):
            if filename.endswith(u'.txt'):
                # dprint (filename)
                newid = wx.NewId()
                txtmacro = wx.MenuItem(middleclickmenu, newid, u'%s' %filename, u' Txt Macro')
                txtmacro.SetBitmap(gImgIdx['file_txt16.png'])
                middleclickmenu.AppendItem(txtmacro)
                wx.EVT_MENU(middleclickmenu, newid, self.OnWriteUserTxtMacro)

        middleclickmenu.AppendSeparator()

        for filename in os.listdir(u'%s' %macroPyDir):
            if filename.endswith(u'.py'):
                # dprint (filename)
                if filename == u'__init__.py':
                    pass
                else:
                    newid = wx.NewId()
                    pymacro = wx.MenuItem(middleclickmenu, newid, u'%s' %filename, u' Py Macro')
                    pymacro.SetBitmap(gImgIdx['file_py16.png'])
                    middleclickmenu.AppendItem(pymacro)
                    wx.EVT_MENU(middleclickmenu, newid, self.OnPythonMacro)

        # events
        for i in range(0,len(gRmgmIDs)):
            wx.EVT_MENU(middleclickmenu, gRmgmIDs[i], gRmgmDEFs[i])
        wx.EVT_MENU(middleclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        wx.EVT_MENU(middleclickmenu, ID_OPENMACRODIR, self.OnOpenMacroDir)

        self.PopupMenu(middleclickmenu)
        middleclickmenu.Destroy()

    def OnOpenMacroDir(slef, event):
        macrodir = bosh.dirs[u'mopy'].join(u'macro')
        try:
            subprocess.Popen(u'explorer "%s"' %macrodir)
            # dprint('SubProcess')
        except:
            webbrowser.open(u'%s' %macrodir)
            # dprint('WebBrowser')

    def OnWriteUserTxtMacro(self, event):
        ''' Read the text file in and add it into the document at the caret. '''
        id =  event.GetId()
        # dprint (event.GetId())
        # dprint (event.GetEventObject())
        evtobj = event.GetEventObject()
        menuitem = evtobj.FindItemById(id)
        # dprint (menuitem.GetItemLabel())

        usertxtmacro = bosh.dirs[u'mopy'].join(u'macro').join(u'txt').join(u'%s' %menuitem.GetItemLabel())

        macrotextfile = open(u'%s' %usertxtmacro, 'r')
        macro = macrotextfile.read()
        macrotextfile.close()
        self.AddText(macro + u'\n')

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
        # rightclickmenu = FM.FlatMenu()

        p = wx.BITMAP_TYPE_PNG

        rcheader1 = wx.MenuItem(rightclickmenu, 0000, u'R MGM 5 Right Clicky!', u'ContextMenu5')
        rcheader1.SetBackgroundColour('#000000')
        rightclickmenu.AppendItem(rcheader1)
        rcheader1.SetDisabledBitmap(gRmbImg)
        rcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            if i == 5:#The currently open menu
                mgm = wx.MenuItem(rightclickmenu, gRmgmIDs[i-1], u'&R MGM %s You Are Here!\tCtrl+5'%str(i), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(gYahImg)
                mgm.SetBackgroundColour('#F4FAB4')
                mgm.Enable(False)
            else:
                mgm = wx.MenuItem(rightclickmenu, gRmgmIDs[i-1], u'&R MGM %s %s'%(str(i),gRmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(gMgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(rightclickmenu, ID_MMGM5, u'&M MGM 5 Macro\tCtrl+0', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(gMgmImg)
        submenu.AppendItem(mgm)
        rightclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        floatingtoolbar = wx.MenuItem(rightclickmenu, ID_TOOLBAR, u'&Use Floating Toolbar', u' Use Floating Toolbar')
        floatingtoolbar.SetBitmap(gImgIdx['star16.png'])
        rightclickmenu.AppendItem(floatingtoolbar)
        if self.OneInstanceToolbar == 1:
            floatingtoolbar.Enable(False)

        rightclickmenu.AppendSeparator()

        undo = wx.MenuItem(rightclickmenu, ID_UNDO, u'&Undo\tCtrl+Z', u' Undo last modifications')
        undo.SetBitmap(gImgIdx['undo16.png'])
        rightclickmenu.AppendItem(undo)
        if self.CanUndo() == 0:   undo.Enable(False)#trying to disable a menu item before it's appended to the menu doesn't work.
        elif self.CanUndo() == 1: undo.Enable(True)
        redo = wx.MenuItem(rightclickmenu, ID_REDO, u'&Redo\tCtrl+Y', u' Redo last modifications')
        redo.SetBitmap(gImgIdx['redo16.png'])
        rightclickmenu.AppendItem(redo)
        if self.CanRedo() == 0:   redo.Enable(False)
        elif self.CanRedo() == 1: redo.Enable(True)

        submenu = wx.Menu()
        undoall = wx.MenuItem(rightclickmenu, ID_UNDOALL, '&Undo All', ' Undo all actions in the Undo Buffer')
        undoall.SetBitmap(gImgIdx['undo16.png'])
        submenu.AppendItem(undoall)
        if self.CanUndo() == 0:   undoall.Enable(False)
        elif self.CanUndo() == 1: undoall.Enable(True)
        redoall = wx.MenuItem(rightclickmenu, ID_REDOALL, '&Redo All', ' Redo all actions in the Undo Buffer')
        redoall.SetBitmap(gImgIdx['redo16.png'])
        submenu.AppendItem(redoall)
        if self.CanRedo() == 0:   redoall.Enable(False)
        elif self.CanRedo() == 1: redoall.Enable(True)
        emptyundobuffer = wx.MenuItem(rightclickmenu, ID_EMPTYUNDOBUFFER, '&Empty Undo Buffer (be sure to save)', ' Empty Undo Buffer')
        emptyundobuffer.SetBitmap(gImgIdx['emptyundobuffer16.png'])
        submenu.AppendItem(emptyundobuffer)
        rightclickmenu.AppendMenu(wx.NewId(), 'Undo/Redo Specials', submenu)

        rightclickmenu.AppendSeparator()
        cut = wx.MenuItem(rightclickmenu, ID_CUT, u'&Cut\tCtrl+X', u' Cut selected text')
        cut.SetBitmap(gImgIdx['cut16.png'])
        rightclickmenu.AppendItem(cut)
        copy = wx.MenuItem(rightclickmenu, ID_COPY, u'&Copy\tCtrl+C', u' Copy selected text')
        copy.SetBitmap(gImgIdx['copy16.png'])
        rightclickmenu.AppendItem(copy)
        paste = wx.MenuItem(rightclickmenu, ID_PASTE, u'&Paste\tCtrl+V', u' Paste from clipboard')
        paste.SetBitmap(gImgIdx['paste16.png'])
        rightclickmenu.AppendItem(paste)
        if self.CanPaste() == 0:   paste.Enable(False)
        elif self.CanPaste() == 1: paste.Enable(True)
        delete = wx.MenuItem(rightclickmenu, ID_DELETE, u'&Delete', u' Delete selected text')
        delete.SetBitmap(gImgIdx['delete16.png'])
        rightclickmenu.AppendItem(delete)
        rightclickmenu.AppendSeparator()
        selectall = wx.MenuItem(rightclickmenu, ID_SELECTALL, u'&Select All\tCtrl+A', u' Select All Text in Document')
        selectall.SetBitmap(gImgIdx['selectall2416.png'])
        rightclickmenu.AppendItem(selectall)

        rightclickmenu.AppendSeparator()

        togglecomment = wx.MenuItem(rightclickmenu, ID_COMMENT, u'&Toggle Comment\tCtrl+Q', u' Toggle Commenting on the selected line(s)')
        togglecomment.SetBitmap(gImgIdx['togglecomment16.png'])
        rightclickmenu.AppendItem(togglecomment)

        removetrailingwhitespace = wx.MenuItem(rightclickmenu, ID_REMTRAILWHITESPACE, u'&Remove Trailing Whitespace', u' Remove trailing whitespace from end of lines in the document')
        removetrailingwhitespace.SetBitmap(gImgIdx['removetrailingspaces16.png'])
        rightclickmenu.AppendItem(removetrailingwhitespace)

        rightclickmenu.AppendSeparator()

        submenu = wx.Menu()
        saveasprojectwizard = wx.MenuItem(rightclickmenu, ID_SAVEASPROJECTWIZARD, u'&Save as this project\'s wizard', u' Save as Project\'s wizard.txt')
        saveasprojectwizard.SetBitmap(gImgIdx['saveaswiz16.png'])
        submenu.AppendItem(saveasprojectwizard)

        saveas = wx.MenuItem(rightclickmenu, ID_SAVEAS, u'&Save as...', u' Save as...')
        saveas.SetBitmap(gImgIdx['save16.png'])
        submenu.AppendItem(saveas)

        saveselectionas = wx.MenuItem(rightclickmenu, ID_SAVESELECTIONAS, u'&Save selection as...', u' Save selection as...')
        saveselectionas.SetBitmap(gImgIdx['save16.png'])
        submenu.AppendItem(saveselectionas)
        if self.GetSelectionStart() == self.GetSelectionEnd(): saveselectionas.Enable(False)

        rightclickmenu.AppendMenu(wx.NewId(), u'File', submenu)

        submenu = wx.Menu()
        minimemo = wx.MenuItem(rightclickmenu, ID_MINIMEMO, u'&Mini Memo\tCtrl+M', u' Mini Memo')
        minimemo.SetBitmap(gImgIdx['memo16.png'])
        submenu.AppendItem(minimemo)

        reminderchecklist = wx.MenuItem(rightclickmenu, ID_REMINDERCHECKLIST, u'&Reminder Checklist...', u' Reminder Checklist for mod authors.')
        reminderchecklist.SetBitmap(gImgIdx['check16.png'])
        submenu.AppendItem(reminderchecklist)

        modCatagoriesList =[u'Abodes - Player homes',u'Animals, creatures, mounts & horses',u'Animation',u'Armour',u'Audio, sound and music',u'Bug fixes',u'Castles, palaces, mansions and estates',u'Cheats and god items',u'Cities, towns, villages and hamlets',u'Clothing',u'Collectables, treasure hunts and puzzles',u'Combat',u'Companion creatures',u'Companions - Other',u'Dungeons - New',u'Dungeons - Vanilla',u'Environmental',u'Gameplay effects and changes',u'Guilds/Factions',u'Hair and face models',u'Immersion',u'Items and Objects - Player',u'Items and Objects - World',u'Landscape changes',u'Locations - New',u'Locations - Vanilla',u'Magic - Alchemy, potions, poisons and ingreds',u'Magic - Gameplay',u'Magic - Spells & enchantments',u'Mercantiles (shops, stores, inns, taverns, etc)',u'Miscellaneous',u'Modders resources and tutorials',u'Models and textures',u'New lands',u'New structures',u'NPC',u'Overhauls',u'Patches',u'Quests and adventures',u'Races, classes and birthsigns',u'Ruins, forts and abandoned structures',u'Saved games',u'Skills and leveling',u'Stealth',u'User interfaces',u'Utilities',u'Videos and trailers',u'Visuals and graphics',u'Weapon and armour',u'Weapons']
        subsubmenu = wx.Menu()
        for modCatagory in modCatagoriesList:
            newid = wx.NewId()
            modcatagory = wx.MenuItem(rightclickmenu, newid, u'%s' %modCatagory, u' Open %s' %modCatagory)
            modcatagory.SetBitmap(gImgIdx['black16.png'])
            subsubmenu.AppendItem(modcatagory)
            wx.EVT_MENU(rightclickmenu, newid, self.OnAddTextMenuLabel)
        submenu.AppendMenu(wx.NewId(), u'AddText: Mod Catagories', subsubmenu)
        # rightclickmenu.AppendMenu(wx.NewId(), u'AddText: Mod Catagories', submenu)

        rightclickmenu.AppendMenu(wx.NewId(), u'Misc', submenu)

        submenu = wx.Menu()
        helpwizbaineditorgeneral = wx.MenuItem(rightclickmenu, ID_HELPGENERAL, u'&WizBAIN Editor General', u' Help explaining general features')
        helpwizbaineditorgeneral.SetBitmap(wx.Bitmap(gImgDir + os.sep + u'help16.png',p))
        submenu.AppendItem(helpwizbaineditorgeneral)

        helpwizbaineditorgeneral = wx.MenuItem(rightclickmenu, ID_HELPAPIDOCSTR, u'&WizBAIN Editor API Doc Strings', u' Help explaining the function performed upon execution')
        helpwizbaineditorgeneral.SetBitmap(gImgIdx['python16.png'])
        submenu.AppendItem(helpwizbaineditorgeneral)

        installerstabtips = wx.MenuItem(rightclickmenu, ID_TIPSINSTALLERS, u'&Installers Tab Tips', u' Tnstallers Tab Tips')
        installerstabtips.SetBitmap(gImgIdx['lightbulb16.png'])
        submenu.AppendItem(installerstabtips)

        rightclickmenu.AppendMenu(wx.NewId(), u'Help', submenu)

        submenu = wx.Menu()
        for key, value in self.bashDirsDict.iteritems():
            newid = wx.NewId()
            openthisdirectory = wx.MenuItem(rightclickmenu, newid, u'%s' %bosh.dirs[key], u' Open %s' %bosh.dirs[key])
            openthisdirectory.SetBitmap(gImgIdx['open16.png'])
            submenu.AppendItem(openthisdirectory)
            wx.EVT_MENU(rightclickmenu, newid, self.OnOpenDirectory)

        submenu.AppendSeparator()

        setmymodsdirs = wx.MenuItem(rightclickmenu, ID_SETMYGAMEMODSDIRS, u'&Set My *Game* Mods Directory Paths', u' Set My *Game* Mods Directory Paths')
        setmymodsdirs.SetBitmap(wx.Bitmap(gImgDir + os.sep + u'settings16.png',p))
        submenu.AppendItem(setmymodsdirs)

        myModDirsList = [basher.settings['bash.bashini.mymodsdirs.MySkyrimModsDir'],
                         basher.settings['bash.bashini.mymodsdirs.MyOblivionModsDir'],
                         basher.settings['bash.bashini.mymodsdirs.MyMorrowindModsDir'],
                         basher.settings['bash.bashini.mymodsdirs.MyFallout3ModsDir'],
                         basher.settings['bash.bashini.mymodsdirs.MyFalloutNVModsDir'],
                         ]
        for dir in myModDirsList:
            newid = wx.NewId()
            openthisdirectory = wx.MenuItem(rightclickmenu, newid, u'%s' %dir, u' Open %s' %dir)
            openthisdirectory.SetBitmap(gImgIdx['open16.png'])
            submenu.AppendItem(openthisdirectory)
            wx.EVT_MENU(rightclickmenu, newid, self.OnOpenDirectory)

        rightclickmenu.AppendMenu(wx.NewId(), u'Open Dir...', submenu)


        # testnewid = wx.NewId()
        # test = wx.MenuItem(rightclickmenu, testnewid, u'&Test wx.NewId()', u' For Testing Purposes')
        # test.SetBitmap(wx.Image(gImgStcDir + os.sep + u'test16.png',p).ConvertToBitmap())
        # wx.EVT_MENU(rightclickmenu, testnewid, self.OnTestNewId)
        # rightclickmenu.AppendItem(test)

        test = wx.MenuItem(rightclickmenu, ID_TEST, u'&Test permanent defined ID: ID_TEST', u' For Testing Purposes')
        test.SetBitmap(gImgIdx['test16.png'])
        rightclickmenu.AppendItem(test)

        #events
        wx.EVT_MENU(rightclickmenu, ID_TEST, self.OnTest)

        wx.EVT_MENU(rightclickmenu, ID_TOOLBAR, self.OnShowFloatingToolbar)

        wx.EVT_MENU(rightclickmenu, ID_SAVEASPROJECTWIZARD, self.OnSaveAsProjectsWizard)
        wx.EVT_MENU(rightclickmenu, ID_SAVEAS, self.OnSaveAs)
        wx.EVT_MENU(rightclickmenu, ID_SAVESELECTIONAS, self.OnSaveSelectionAs)

        wx.EVT_MENU(rightclickmenu, ID_MINIMEMO, self.OnMiniMemo)
        wx.EVT_MENU(rightclickmenu, ID_REMINDERCHECKLIST, self.OnShowReminderChecklist)

        wx.EVT_MENU(rightclickmenu, ID_HELPGENERAL, self.OnHelpWizBAINEditorGeneral)
        wx.EVT_MENU(rightclickmenu, ID_HELPAPIDOCSTR, self.OnHelpWizBAINEditorAPIDocStrings)
        wx.EVT_MENU(rightclickmenu, ID_TIPSINSTALLERS, self.OnShowInstallersTabTipsDialog)

        wx.EVT_MENU(rightclickmenu, ID_SETMYGAMEMODSDIRS, self.OnSetMyGameModsPaths)

        wx.EVT_MENU(rightclickmenu, ID_UNDO, self.OnUndo)
        wx.EVT_MENU(rightclickmenu, ID_REDO, self.OnRedo)
        wx.EVT_MENU(rightclickmenu, ID_UNDOALL, self.OnUndoAll)
        wx.EVT_MENU(rightclickmenu, ID_REDOALL, self.OnRedoAll)
        wx.EVT_MENU(rightclickmenu, ID_EMPTYUNDOBUFFER, self.OnEmptyUndoBuffer)

        wx.EVT_MENU(rightclickmenu, ID_CUT, self.OnCut)
        wx.EVT_MENU(rightclickmenu, ID_COPY, self.OnCopy)
        if self.rect_selection_clipboard_flag:
            wx.EVT_MENU(rightclickmenu, ID_PASTE, self.OnColumnPasteFromContextMenu)
        else:
            wx.EVT_MENU(rightclickmenu, ID_PASTE, self.OnPasteFromContextMenu)
        wx.EVT_MENU(rightclickmenu, ID_DELETE, self.OnDelete)
        wx.EVT_MENU(rightclickmenu, ID_SELECTALL, self.OnSelectAll)
        wx.EVT_MENU(rightclickmenu, ID_COMMENT, self.OnToggleComment)
        wx.EVT_MENU(rightclickmenu, ID_REMTRAILWHITESPACE, self.OnRemoveTrailingWhitespace)

        for i in range(0,len(gRmgmIDs)):
            wx.EVT_MENU(rightclickmenu, gRmgmIDs[i], gRmgmDEFs[i])
        wx.EVT_MENU(rightclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        self.PopupMenu(rightclickmenu)
        rightclickmenu.Destroy()

    def OnTestNewId(self, event):
        dprint (u'OnTestNewId - Everytime the menu is opened.')
        dprint (event.GetId())

    def OnTest(self, event):
        print ('OnTest')
        print ('ID_TEST')
        print (event.GetId())

        # self.OnSaveAs(event)

        # for keyword in self.allkeywords:
            # self.AddText(keyword + '\n')

        # dprint('mwahaha')

        # if self.OneInstanceDebugWindow == 0:
            # win = DebugStdOutStdErrMiniFrame(self, wx.SIMPLE_BORDER)
            # win.Centre()
            # win.Show(True)
            # self.OneInstanceDebugWindow = 1
            # causeTraceback #seee... I told ya so... It was a intentional error. This window now only accepts stderr Tracebacks, not stdout, print or dprint(u'%s' %str) messages! Oh, and the other is cooler because it has stylish black rims and red Tracebacks if you want mooo!
        # else:
            # gDebugFrame.Show()

            
        win = settingsModule.SettingsDialog(self, -1, 'Settings')
        win.Centre()
        win.Show(True)


    def causeTraceback(self, event):
        causeTraceback

    def OnUndo(self,event):
        ''' Undo one action in the undo history. '''
        if self.CanUndo() == 1:
            self.Undo()

    def OnRedo(self,event):
        ''' Redoes the next action on the undo history. '''
        if self.CanRedo() == 1:
            self.Redo()

    def OnUndoAll(self, event):
        ''' Undo all actions in the undo history. '''
        while self.CanUndo() == 1: self.Undo()
        # print ('UndoAll')

    def OnRedoAll(self, event):
        ''' Redo all actions in the undo history. '''
        while self.CanRedo() == 1: self.Redo()
        # print ('RedoAll')

    def OnEmptyUndoBuffer(self, event):
        ''' Delete the undo history. '''
        dialog = wx.MessageDialog(self,
            'This cannot be undone!\n'
            'Would you like to continue?',
            'Empty Undo Buffer', wx.OK|wx.CANCEL|wx.ICON_EXCLAMATION)
        dialog.Destroy()

        if dialog.ShowModal() == wx.ID_OK:
            self.EmptyUndoBuffer()
            # print ('EmptyUndoBuffer()')
        else:
            pass
            # print('Canceled Empty Undo Buffer')

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
            self.Copy()
            # print ('rect_selection_clipboard_flag = True')
        else:
            self.rect_selection_clipboard_flag = False
            self.Copy()
            # print ('rect_selection_clipboard_flag = False')
        # print ('OnCopy')

    def OnCopyAll(self, event):
        ''' Copy all of the text in the document to the clipboard. '''
        self.SelectAll()
        self.Copy()

    def OnPasteFromContextMenu(self, event):
        ''' Paste the contents of the clipboard into the document replacing the selection.
        or Override CmdKeyExecute if the rect_selection_clipboard_flag is set. '''
        if self.CanPaste() == 1: #Will a paste succeed? 1 For Yes, 0 for No.
            if self.rect_selection_clipboard_flag:
                self.OnColumnPasteFromContextMenu(event)
            else:
                self.Paste()
        elif self.CanPaste() == 0:
            wx.Bell()
            # print ('This Paste can\'t succeed.')

    def OnPasteFromKeyboardShortcut(self, event):
        ''' HACK Def: Paste the contents of the clipboard into the document replacing the selection.
        or Override CmdKeyExecute if the rect_selection_clipboard_flag is set. '''
        if self.CanPaste() == 1: #Will a paste succeed? 1 For Yes, 0 for No.
            if self.rect_selection_clipboard_flag:
                self.OnColumnPasteFromKeyboardShortcut(event)
            else:
                self.Paste()
                wx.CallAfter(self.Undo)#Wrye Bash Port HACK: Because... No wx.Menu RectSelection HACK , Don't paste twice;rectangular then regular, just rectangular
        elif self.CanPaste() == 0:
            wx.Bell()
            # print ('This Paste can\'t succeed.')

    def OnColumnPasteFromContextMenu(self, event):
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
        # print('OnColumnPasteFromContextMenu')

    def OnColumnPasteFromKeyboardShortcut(self, event):
        ''' HACK Def: Paste text into the document in a rectangular or columnar fashion. '''
        if self.rect_selection_clipboard_flag:
            self.OnColumnPasteFromContextMenu(event)
            wx.CallAfter(self.Undo)#Wrye Bash Port HACK: Because... No wx.Menu RectSelection HACK , Don't paste twice;rectangular then regular, just rectangular
        # print('OnColumnPasteFromKeyboardShortcut')

    def OnDelete(self, event):
        ''' Clear the selection. '''
        self.Clear()

    def OnSelectAll(self, event):
        ''' Select all of the text in the document. '''
        self.SelectAll()

    def OnToggleComment(self, event):
        ''' Toggle commenting on current or selected line(s) ==> ;# ini/pythonic colored comment.
        Commenting = semicolon(;) followed by a number sign/pound/hash(#) followed by a single whitespace( ).'''
        self.BeginUndoAction()
        selstart = self.GetSelectionStart()
        selend = self.GetSelectionEnd()
        line = self.LineFromPosition(self.GetCurrentPos())
        # print ('char1: ' + str(self.GetCharAt(self.GetLineIndentPosition(line))))

        if selstart == selend:
            # dprint('Nothing Selected - Toggle Comment Single Line')
            retainposafterwards = self.GetCurrentPos()
            if self.GetCharAt(self.GetLineIndentPosition(line)) == 10:
                pass
                # dprint ('line:' + str(line+1) + ' is blank LF') # char is LF EOL.
            elif self.GetCharAt(self.GetLineIndentPosition(line)) == 13:
                pass
                # dprint ('line:' + str(line+1) + ' is blank CR') # char is CR EOL.
            elif self.GetCharAt(self.GetLineIndentPosition(line)) == 0:
                pass
                # dprint ('line:' + str(line+1) + ' is blank nothing') # char is nothing. end of doc
            elif basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
                if self.GetCharAt(self.GetLineIndentPosition(line)) == 59: # char is ;
                    if self.GetCharAt(self.GetLineIndentPosition(line) + 1) == 35: # char is #
                        if self.GetCharAt(self.GetLineIndentPosition(line) + 2) == 32: # char is space
                            # dprint ('wizbain commented line')
                            self.GotoPos(self.GetLineIndentPosition(line) + 3)
                            for i in range(0,3):
                                self.DeleteBackNotLine()
                            self.GotoPos(retainposafterwards - 3)
                else:
                    self.GotoPos(self.GetLineIndentPosition(line))
                    self.AddText(u';# ')
                    self.GotoPos(retainposafterwards + 3)
        else:
            # dprint('Toggle Comment On Selected Lines')
            startline = self.LineFromPosition(selstart)
            endline = self.LineFromPosition(selend)
            for i in range(startline, endline + 1):
                # dprint ('line:' + str(i + 1) + ' ' + str(self.GetLine(i)))

                if self.GetCharAt(self.GetLineIndentPosition(i)) == 10:
                    pass
                    # dprint ('line:' + str(i+1) + ' is blank LF') # char is LF EOL.
                elif self.GetCharAt(self.GetLineIndentPosition(i)) == 13:
                    pass
                    # dprint ('line:' + str(i+1) + ' is blank CR') # char is CR EOL.
                elif self.GetCharAt(self.GetLineIndentPosition(i)) == 0:
                    pass
                    # dprint ('line:' + str(i+1) + ' is blank nothing') # char is nothing. end of doc
                elif basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
                    if self.GetCharAt(self.GetLineIndentPosition(i)) == 59: # char is ;
                        if self.GetCharAt(self.GetLineIndentPosition(i) + 1) == 35: # char is #
                            if self.GetCharAt(self.GetLineIndentPosition(i) + 2) == 32: # char is space
                                # dprint ('wizbain commented line')
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
                    print (u'Huh')
        self.EndUndoAction()
        # dprint ('OnToggleComment might need some more work.')

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
            if os.path.exists(u'%s%s%s%s%s' %(dir, os.sep, packagename, os.sep, u'Data')):
                # print('Data Dir Found')
                wizpath = u'%s%s%s%s%s%swizard.txt' %(dir, os.sep, packagename, os.sep, u'Data', os.sep)
            elif os.path.exists(u'%s%s%s%s%s' %(dir, os.sep, packagename, os.sep, u'data')):
                # print('data Dir Found')
                wizpath = u'%s%s%s%s%s%swizard.txt' %(dir, os.sep, packagename, os.sep, u'data', os.sep)
            else:
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

    def OnSaveAs(self, event):
        ''' File|SaveAs event - Prompt for File Name. '''
        dialog = wx.FileDialog(self, u'Save As...', u'%s' %bosh.dirs['installers'], u'', self.wildcard, wx.SAVE | wx.OVERWRITE_PROMPT)
        if (dialog.ShowModal() == wx.ID_OK):
            self.filename = dialog.GetFilename()
            self.dirname = dialog.GetDirectory()
            self.path = dialog.GetPath()
            # - Use the OnSave to save the fil
            try:
                # print self.dirname
                # print self.filename
                somefile = open(os.path.join(self.dirname, self.filename), 'w')
                # print('somefile',somefile)
                somefile.write(self.GetTextUTF8())
                # print ('Write File Close - Save')
                somefile.close()
                # self.SetSavePoint() #Don't use this here. If user immediately clicks on another package afterwards, infos won't get saved as this resets the Modify Flag.
                # print('OnSaveAs')
            except:
                wx.MessageBox(u'Error in saving file.', u'ERROR', wx.ICON_ERROR | wx.OK)
                wx.Bell()
        dialog.Destroy()

    def OnSaveSelectionAs(self, event):
        ''' File|SaveSelectionAs event - Prompt for File Name. '''
        if self.GetSelectionStart() == self.GetSelectionEnd():
            wx.Bell()
            self.SetStatusText('No Text Selected!')
        else:
            dialog = wx.FileDialog(self, u'Save Selection As...', u'%s' %bosh.dirs['installers'], u'', self.wildcard, wx.SAVE | wx.OVERWRITE_PROMPT)
            if (dialog.ShowModal() == wx.ID_OK):
                self.filename = dialog.GetFilename()
                self.dirname = dialog.GetDirectory()
                self.path = dialog.GetPath()
                try:
                    somefile = file(os.path.join(self.dirname, self.filename), 'w')
                    somefile.write(self.GetSelectedTextUTF8())
                    somefile.close()
                    # print('Saved Selection.')
                except:
                    wx.MessageBox(u'Error in saving file.', u'ERROR', wx.ICON_ERROR | wx.OK)
                    wx.Bell()
            dialog.Destroy()

    def OnMiniMemo(self, event):
        if self.OneInstanceMiniMemo == 0:
            win = MemoMiniFrame(self, wx.SIMPLE_BORDER)
            win.Centre()
            win.Show(True)
            self.OneInstanceMiniMemo = 1

    def OnShowReminderChecklist(self, event):
        win = ChecklistBeforePackageingYourMod(self, wx.SIMPLE_BORDER)
        win.Centre()
        win.Show()

    def OnShowInstallersTabTipsDialog(self, event):
        customframe = InstallersTabTips(self, -1, u'Installers Tab Tips')
        customframe.Show()

    def OnHelpWizBAINEditorGeneral(self, event):
        ''' Call the WizBAINEditorHelpGeneralDialog '''
        customdialog = WizBAINEditorHelpGeneralDialog(None,-1)
        customdialog.ShowModal()
        customdialog.Destroy()

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

        functionlist = [self.OnHelpWizBAINEditorAPIDocStrings,self.OnSelectNone,self.OnKeyDown,self.OnUpdateUI,self.OnMarginClick,self.OnFoldAll,self.OnExpand,self.OnCharAdded,self.OnSelectAll,self.OnUndo,self.OnRedo,self.OnCut,self.OnCopy,self.OnCopyAll,self.OnPasteFromContextMenu,self.OnColumnPasteFromContextMenu,self.OnPasteFromKeyboardShortcut,self.OnColumnPasteFromKeyboardShortcut,self.OnDelete,self.OnRemoveTrailingWhitespace,self.OnSaveAsProjectsWizard,self.OnTextToWizardStringFileDropMiniFrame,self.OnTextToWizardStringTextDropMiniFrame,self.OnContextMenu,self.OnHelpWizBAINEditorGeneral,self.OnToggleComment,self.OnUPPERCASE,self.Onlowercase,self.OnInvertCase,self.OnCapitalCase,self.OnMMouseGestureMenuNone,self.OnWriteUserTxtMacro,self.OnLoadModule,self.OnPythonMacro,self.OnRMouseGestureMenuNone,self.OnTestNewId,self.OnTest,self.OnRMouseGestureMenu1,self.OnSort,self.OnFindSelectedForwards,self.OnRMouseGestureMenu2,self.OnUseOnTopDraggableRMouseGestureMenu2,self.OnDefaultCharacterSelectedOptions,self.OnThumbnailerPackageWizardImages,self.OnThumbnailContextMenu,self.OnThumbnailWizImage,self.OnDialogDestroy,self.OnImageBrowserPackageWizardImages,self.OnWriteImageDirectoryIMAGE,self.OnWriteKeywordSUBNAMEorESPMNAME,self.OnWriteListSubPackages,self.OnWriteListEspms,self.OnDeleteIfSelectedText,self.OnRequireVersionsOblivion,self.OnRequireVersionsSkyrim,self.OnSelectOne,self.OnSelectMany,self.OnChoicesX02,self.OnEndSelect,self.OnCase,self.OnBreak,self.OnSelectAllKeyword,self.OnDeSelectAll,self.OnSelectSubPackage,self.OnDeSelectSubPackage,self.OnSelectEspm,self.OnSelectAllEspms,self.OnDeSelectEspm,self.OnDeSelectAllEspms,self.OnRenameEspm,self.OnResetEspmName,self.OnResetAllEspmNames,self.OnWizardImages,self.OnRMouseGestureMenu3,self.OnShowSelectedTextCallTip,self.OnShowWordCompleteBox,self.OnShowAutoCompleteBox,self.OnRMouseGestureMenu4,self.OnRMouseGestureMenu6,self.OnRMouseGestureMenu7,self.OnRMouseGestureMenu8,self.OnNewLineBefore,self.OnNewLineAfter,self.OnLineCut,self.OnLineCopy,self.OnLineDelete,self.OnDeleteLineContents,self.OnLineSelect,self.OnLineDuplicate,self.OnLineDuplicateNTimes,self.OnDuplicateSelectionLine,self.OnLinesJoin,self.OnLinesSplit,self.OnLineTranspose,self.OnMoveLineUp,self.OnMoveLineDown,self.OnAppendSelectedLinesWithAString,self.OnRemoveStringFromEndOfSelectedLines,self.OnRemoveStringFromStartOfSelectedLines,self.OnPadWithSpacesSelectedLines,self.OnRMouseGestureMenu9,self.OnViewWhitespace,self.OnShowIndentationGuides,self.OnWordwrap,self.OnHighlightSelectedLine,self.OnShowEOL,self.OnSetFolderMarginStyle,self.OnFolderMarginStyle1,self.OnFolderMarginStyle2,self.OnFolderMarginStyle3,self.OnFolderMarginStyle4,self.OnFolderMarginStyle5,self.OnFolderMarginStyle6,self.OnSetTheme,self.OnToggleEditorThemes,self.OnNoTheme,self.OnDefaultTheme,self.OnConsoleTheme,self.OnObsidianTheme,self.OnZenburnTheme,self.OnMonokaiTheme,self.OnDeepSpaceTheme,self.OnGreenSideUpTheme,self.OnTwilightTheme,self.OnUliPadTheme,self.OnHelloKittyTheme,self.OnVibrantInkTheme,self.OnBirdsOfParidiseTheme,self.OnBlackLightTheme,self.OnNotebookTheme,]

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
        dialog.SetIcon(wx.Icon(gImgDir + os.sep + u'help16.png', wx.BITMAP_TYPE_PNG))
        dialog.ShowModal()
        dialog.Destroy()


    def OnSetMyGameModsPaths(self, event):
        # win = SetMyGameModsPaths(self, wx.SIMPLE_BORDER)
        # win.Centre()
        # win.Show()
        print('OnSetMyGameModsPaths')

    def OnOpenDirectory(self, event):
        id =  event.GetId()
        evtobj = event.GetEventObject()
        menuitem = evtobj.FindItemById(id)
        if os.path.exists(u'%s' %menuitem.GetItemLabel()):
            # dprint('exists')
            try:
                try:
                    subprocess.Popen(u'explorer "%s"' %menuitem.GetItemLabel())
                    # dprint('SubProcess')
                except:
                    webbrowser.open(u'%s' %menuitem.GetItemLabel())
                    # dprint('WebBrowser')
            except:
                wx.MessageBox(u'def OnOpenDirectory Error in wizSTC.py', u'ERROR', wx.ICON_ERROR | wx.OK)
        else:
            wx.MessageBox(u'The path:\n%s\ndoesn\'t exist or could not be found.' %menuitem.GetItemLabel(), u'ERROR', wx.ICON_ERROR | wx.OK)
        # dprint (menuitem.GetItemLabel())

    def OnShowFloatingToolbar(self, event):
        if self.OneInstanceToolbar == 0:
            customtoolbar = FloatingToolbar(self, -1)
            customtoolbar.Show()
            self.OneInstanceToolbar = 1

    def OnRMouseGestureMenu1(self, event):
        ''' Call the Right Mouse Gesture Menu.
        NUMPAD:1
        [7][8][9]
        [4][5][6]
        [@][2][3]
        '''
        rightclickmenu = wx.Menu()

        rcheader1 = wx.MenuItem(rightclickmenu, 0000, u'R MGM 1 Find/Replace/Mark', u'ContextMenu1')
        rcheader1.SetBackgroundColour('#000000')
        rightclickmenu.AppendItem(rcheader1)
        rcheader1.SetDisabledBitmap(gRmbImg)
        rcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            if i == 1:#The currently open menu
                mgm = wx.MenuItem(rightclickmenu, gRmgmIDs[i-1], u'&R MGM %s You Are Here!\tCtrl+1'%str(i), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(gYahImg)
                mgm.SetBackgroundColour('#F4FAB4')
                mgm.Enable(False)
            else:
                mgm = wx.MenuItem(rightclickmenu, gRmgmIDs[i-1], u'&R MGM %s %s'%(str(i),gRmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(gMgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(rightclickmenu, ID_MMGM5, u'&M MGM 5 Macro\tCtrl+0', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(gMgmImg)
        submenu.AppendItem(mgm)
        rightclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        rightclickmenu.AppendSeparator()

        gotolinenumber = wx.MenuItem(rightclickmenu, ID_GOTOLINE, u'&Go to line number\tCtrl+G', u' Advance to the given line in the currently open document')
        gotolinenumber.SetBitmap(gImgIdx['gotoline16.png'])
        rightclickmenu.AppendItem(gotolinenumber)

        gotoposition = wx.MenuItem(rightclickmenu, ID_GOTOPOS, u'&Go to position', u' Advance to the given position in the currently open document')
        gotoposition.SetBitmap(gImgIdx['gotoposition16.png'])
        rightclickmenu.AppendItem(gotoposition)

        findreplace = wx.MenuItem(rightclickmenu, ID_FINDREPLACE, u'&Find && Replace...\tCtrl+F', u' Find & Replace miniframe')
        findreplace.SetBitmap(gImgIdx['findreplace16.png'])
        rightclickmenu.AppendItem(findreplace)

        findselectedforwards = wx.MenuItem(rightclickmenu, ID_FINDSELECTEDFORE, u'&Find Selected Forwards\tF4', u' Find selected text forwards')
        findselectedforwards.SetBitmap(gImgIdx['arrowdownbw16.png'])
        rightclickmenu.AppendItem(findselectedforwards)

        togglebookmark = wx.MenuItem(rightclickmenu, ID_BOOKMARK, u'&Bookmark Line\tCtrl+B', u' Add/Remove bookmark for the current line')
        togglebookmark.SetBitmap(gImgIdx['bookmark16.png'])
        rightclickmenu.AppendItem(togglebookmark)

        previousbookmark = wx.MenuItem(rightclickmenu, ID_BOOKMARKPREVIOUS, u'&Previous Bookmark\tCtrl+Shift+B', u' Hop to the previous bookmark in this document')
        previousbookmark.SetBitmap(gImgIdx['bookmarkfindprevious16.png'])
        rightclickmenu.AppendItem(previousbookmark)

        nextbookmark = wx.MenuItem(rightclickmenu, ID_BOOKMARKNEXT, u'&Next Bookmark\tCtrl+Alt+B', u' Hop to the next bookmark in this document')
        nextbookmark.SetBitmap(gImgIdx['bookmarkfindnext16.png'])
        rightclickmenu.AppendItem(nextbookmark)

        removeallbookmarks = wx.MenuItem(rightclickmenu, ID_REMOVEALLBOOKMARKS, u'&Remove All Bookmarks', u' Remove all bookmarks from document')
        removeallbookmarks.SetBitmap(gImgIdx['removeallbookmarks16.png'])
        rightclickmenu.AppendItem(removeallbookmarks)

        #events
        wx.EVT_MENU(rightclickmenu, ID_GOTOLINE, self.OnGoToLine)
        wx.EVT_MENU(rightclickmenu, ID_GOTOPOS, self.OnGoToPosition)
        wx.EVT_MENU(rightclickmenu, ID_FINDREPLACE, self.OnFindReplaceOneInstanceChecker)
        wx.EVT_MENU(rightclickmenu, ID_FINDSELECTEDFORE, self.OnFindSelectedForwards)

        wx.EVT_MENU(rightclickmenu, ID_BOOKMARK, self.OnToggleBookmark)
        wx.EVT_MENU(rightclickmenu, ID_BOOKMARKPREVIOUS, self.OnHopPreviousBookmark)
        wx.EVT_MENU(rightclickmenu, ID_BOOKMARKNEXT, self.OnHopNextBookmark)
        wx.EVT_MENU(rightclickmenu, ID_REMOVEALLBOOKMARKS, self.OnRemoveAllBookmarks)

        for i in range(0,len(gRmgmIDs)):
            wx.EVT_MENU(rightclickmenu, gRmgmIDs[i], gRmgmDEFs[i])
        wx.EVT_MENU(rightclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        self.PopupMenu(rightclickmenu)
        rightclickmenu.Destroy()

    def OnGoToLine(self, event):
        ''' Move caret/view to user specified line in document. '''
        dialog = wx.TextEntryDialog(self, u'Enter line number (1- %s)' % self.GetLineCount() + u'\nYou are here: %s' %(self.GetCurrentLine() + 1), u'Go to line', u'')
        line = ''
        if dialog.ShowModal() == wx.ID_OK:
            line = int(dialog.GetValue()) - 1
        dialog.Destroy()
        if line != '':
            self.GotoLine(line)
        self.SetFocus()
        # dprint('GoToLine ' + str(self.GetCurrentLine() +1))

    def OnGoToPosition(self, event):
        ''' Move caret/view to position in the document. '''
        pos = self.GetLength()  #Returns the number of characters in the document.
        dialog = wx.TextEntryDialog(self, u'Enter position (offset) number (0- %s)' % pos + u'\nYou are here: %s' %(self.GetCurrentPos()), u'Go to position', u'')

        if dialog.ShowModal() == wx.ID_OK:
            pos = int(dialog.GetValue())
        else:
            pos = ''
            # dprint ('Cancel')
        dialog.Destroy()
        if pos != '':
            self.GotoPos(pos)   #Set caret to a position and ensure it is visible.
        self.SetFocus()
        # dprint('OnGoToPosition. Your current pos is: ' + str(self.GetCurrentPos()))

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

    def OnToggleBookmark(self,event):
        '''Add or remove a bookmark from the current line int the bookmark margin.'''
        linenum = self.GetCurrentLine()
        if self.MarkerGet(linenum):
            if self.MarkerGet(linenum) == 3:
                self.MarkerDelete(linenum, 1)
            elif self.MarkerGet(linenum) == 1 :
                self.MarkerAdd(linenum, 1)
        else:
            self.MarkerAdd(linenum, 1)

    def OnHopPreviousBookmark(self, event):
        '''Move caret to the previous bookmarked line in the file.'''
        currentline = self.GetCurrentLine()
        linecount = self.GetLineCount()
        marker = self.MarkerGet(currentline)
        dprint (marker)
        if marker == 0 or marker == 1 or marker == 3:
            currentline -= 1
        findbookmark = self.MarkerPrevious(currentline, 2)
        if findbookmark > -1:
            self.GotoLine(findbookmark)
        else:
            findbookmark = self.MarkerPrevious(linecount, 2)
            if findbookmark > -1:
                self.GotoLine(findbookmark)

    def OnHopNextBookmark(self, event):
        '''Move caret to the next bookmarked line in the file.'''
        currentline = self.GetCurrentLine()
        marker = self.MarkerGet(currentline)
        if marker == 0 or marker == 1 or marker == 3:
            currentline += 1
        findbookmark = self.MarkerNext(currentline, 2)
        if findbookmark > -1:
            self.GotoLine(findbookmark)
        else:
            findbookmark = self.MarkerNext(0, 2)
            if findbookmark > -1:
                self.GotoLine(findbookmark)

    def OnRemoveAllBookmarks(self, event):
        '''Remove all bookmarks from everyline in the document in the bookmark margin.'''
        for i in range(0,3):
            self.MarkerDeleteAll(i)

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
        rcheader1.SetDisabledBitmap(gRmbImg)
        rcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            if i == 2:#The currently open menu
                mgm = wx.MenuItem(rightclickmenu, gRmgmIDs[i-1], u'&R MGM %s You Are Here!\tCtrl+2'%str(i), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(gYahImg)
                mgm.SetBackgroundColour('#F4FAB4')
                mgm.Enable(False)
            else:
                mgm = wx.MenuItem(rightclickmenu, gRmgmIDs[i-1], u'&R MGM %s %s'%(str(i),gRmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(gMgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(rightclickmenu, ID_MMGM5, u'&M MGM 5 Macro\tCtrl+0', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(gMgmImg)
        submenu.AppendItem(mgm)
        rightclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        ontopdragmenu = wx.MenuItem(rightclickmenu, ID_RMGM2DRAG, u'&Use OnTop Draggable Menu', u' Use OnTop Draggable Menu')
        ontopdragmenu.SetBitmap(gImgIdx['star16.png'])
        rightclickmenu.AppendItem(ontopdragmenu)
        if self.dragmenu2 == 1: ontopdragmenu.Enable(False)

        rightclickmenu.AppendSeparator()

        mSubListCount = basher.gInstallers.gSubList.GetCount()
        mEspmListCount = basher.gInstallers.gEspmList.GetCount()

        reqversky = wx.MenuItem(rightclickmenu, ID_REQVEROB, u'&RequireVersions Oblivion', u' RequireVersions "1.2.0.416","0.0.20.6","3.0.0.0","295"')
        reqversky.SetBitmap(wx.Bitmap(gImgDir + os.sep + (u'oblivion16.png'),p))
        rightclickmenu.AppendItem(reqversky)
        reqverob = wx.MenuItem(rightclickmenu, ID_REQVERSK, u'&RequireVersions Skyrim', u' RequireVersions "1.1.21.0","","","295"')
        reqverob.SetBitmap(wx.Bitmap(gImgDir + os.sep + (u'skyrim16.png'),p))
        rightclickmenu.AppendItem(reqverob)

        submenu = wx.Menu()
        menuItem = wx.MenuItem(submenu, wx.NewId(), u'&DataFileExists ("[modName]")')
        datafileexists = wx.MenuItem(rightclickmenu, ID_DATAFILEEXISTS, u'&DataFileExists ("")', u' DataFileExists ("")')
        submenu.AppendItem(datafileexists)
        for filename in os.listdir(u'%s' %bosh.dirs['mods']):
            newid = wx.NewId()
            if u'Bashed Patch' in filename:
                # print filename
                datafileexists = wx.MenuItem(rightclickmenu, newid, u'DataFileExists ("%s")' %filename, u' DataFileExists ("[modName]")')
                datafileexists.SetBitmap(wx.Bitmap(gImgDir + os.sep + (u'wryemonkey16.png'),p))
                submenu.AppendItem(datafileexists)
                wx.EVT_MENU(rightclickmenu, newid, self.OnWriteKeywordSUBNAMEorESPMNAME)
            elif filename.endswith(u'.esp'):
                # print filename
                datafileexists = wx.MenuItem(rightclickmenu, newid, u'DataFileExists ("%s")' %filename, u' DataFileExists ("[modName]")')
                datafileexists.SetBitmap(gImgIdx['esp16.png'])
                submenu.AppendItem(datafileexists)
                wx.EVT_MENU(rightclickmenu, newid, self.OnWriteKeywordSUBNAMEorESPMNAME)
            elif filename.endswith(u'.esm'):
                # print filename
                datafileexists = wx.MenuItem(rightclickmenu, newid, u'DataFileExists ("%s")' %filename, u' DataFileExists ("[modName]")')
                datafileexists.SetBitmap(gImgIdx['esm16.png'])
                submenu.AppendItem(datafileexists)
                wx.EVT_MENU(rightclickmenu, newid, self.OnWriteKeywordSUBNAMEorESPMNAME)
        menuItem.SetBitmap(gImgIdx['list16.png'])
        menuItem.SetBackgroundColour(u'#FFF7EE')
        menuItem.SetSubMenu(submenu)
        rightclickmenu.AppendItem(menuItem)

        selectone = wx.MenuItem(rightclickmenu, ID_SELECTONE, u'&SelectOne "Dialog...", \\', u' SelectOne "Dialog...", \\')
        selectone.SetBitmap(gImgIdx['dialog16.png'])
        rightclickmenu.AppendItem(selectone)
        selectmany = wx.MenuItem(rightclickmenu, ID_SELECTMANY, u'&SelectMany "Dialog...", \\', u' SelectMany "Dialog...", \\')
        selectmany.SetBitmap(gImgIdx['dialog16.png'])
        rightclickmenu.AppendItem(selectmany)

        ifelifelseendif = wx.MenuItem(rightclickmenu, ID_IFELIFELSEENDIF, u'&If-Elif-Else-EndIf')
        rightclickmenu.AppendItem(ifelifelseendif)

        submenu = wx.Menu()
        whilecontinuebreakendwhileloop = wx.MenuItem(rightclickmenu, ID_WHILECONTINUEBREAKENDWHILE, u'&While-Continue-Break-EndWhile Loop', u' While-Continue-Break-EndWhile Loop')
        submenu.AppendItem(whilecontinuebreakendwhileloop)

        forcontinuebreakendforloop = wx.MenuItem(rightclickmenu, ID_FORCONTINUEBREAKENDFOR, u'&For-Continue-Break-EndFot Loop', u' For-Continue-Break-EndFor Loop')
        submenu.AppendItem(forcontinuebreakendforloop)

        forsubinsubpackagesloop = wx.MenuItem(rightclickmenu, ID_FORSUBINSUBPACKAGES, u'&For sub in SubPackages Loop', u' For sub in SubPackages Loop')
        submenu.AppendItem(forsubinsubpackagesloop)
        rightclickmenu.AppendMenu(wx.NewId(), u'While/For Loops...', submenu)

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
            menuItem.SetBitmap(gImgIdx['list16.png'])
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
            menuItem.SetBitmap(gImgIdx['list16.png'])
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
                    selectespmsubmenuitem.SetBitmap(gImgIdx['esp16.png'])
                elif filename.endswith(u'.esm'):
                    selectespmsubmenuitem = wx.MenuItem(rightclickmenu, newid, u'SelectEspm "' + u'%s' %filename + u'"', u' SelectEspm "[espmName]"')
                    selectespmsubmenuitem.SetBitmap(gImgIdx['esm16.png'])
                submenu.AppendItem(selectespmsubmenuitem)
                wx.EVT_MENU(rightclickmenu, newid, self.OnWriteKeywordSUBNAMEorESPMNAME)
            menuItem.SetBitmap(gImgIdx['list16.png'])
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
                    deselectespmsubmenuitem.SetBitmap(gImgIdx['esp16.png'])
                elif filename.endswith(u'.esm'):
                    deselectespmsubmenuitem = wx.MenuItem(rightclickmenu, newid, u'DeSelectEspm "' + u'%s' %filename + u'"', u' DeSelectEspm "[espmName]"')
                    deselectespmsubmenuitem.SetBitmap(gImgIdx['esm16.png'])
                submenu.AppendItem(deselectespmsubmenuitem)
                wx.EVT_MENU(rightclickmenu, newid, self.OnWriteKeywordSUBNAMEorESPMNAME)
            menuItem.SetBitmap(gImgIdx['list16.png'])
            menuItem.SetBackgroundColour(u'#FFF7EE')
            menuItem.SetSubMenu(submenu)
            rightclickmenu.AppendItem(menuItem)

        selectallespms = wx.MenuItem(rightclickmenu, ID_SELECTALLESPMS, u'&SelectAllEspms', u' SelectAllEspms')
        rightclickmenu.AppendItem(selectallespms)

        deselectallespms = wx.MenuItem(rightclickmenu, ID_DESELECTALLESPMS, u'&DeSelectAllEspms', u' DeSelectAllEspms')
        rightclickmenu.AppendItem(deselectallespms)

        if mEspmListCount == 0:
            renameespm = wx.MenuItem(rightclickmenu, ID_RENAMEESPM, u'RenameEspm "",""', u' RenameEspm "",""')
            rightclickmenu.AppendItem(renameespm)
        else:
            submenu = wx.Menu()
            menuItem = wx.MenuItem(submenu, wx.NewId(), u'RenameEspm "[espmName]",""')
            renameespm = wx.MenuItem(rightclickmenu, ID_RENAMEESPM, u'RenameEspm "",""', u' RenameEspm "",""')
            submenu.AppendItem(renameespm)
            for index in xrange(mEspmListCount):
                newid = wx.NewId()
                filename = u'%s' %basher.gInstallers.gEspmList.GetString(index)
                if filename.endswith(u'.esp'):
                    renameespmsubmenuitem = wx.MenuItem(rightclickmenu, newid, u'RenameEspm "' + u'%s' %filename + u'",""', u' RenameEspm "[espmName]",""')
                    renameespmsubmenuitem.SetBitmap(gImgIdx['esp16.png'])
                elif filename.endswith(u'.esm'):
                    renameespmsubmenuitem = wx.MenuItem(rightclickmenu, newid, u'RenameEspm "' + u'%s' %filename + u'",""', u' RenameEspm "[espmName]",""')
                    renameespmsubmenuitem.SetBitmap(gImgIdx['esm16.png'])
                submenu.AppendItem(renameespmsubmenuitem)
                wx.EVT_MENU(rightclickmenu, newid, self.OnWriteKeywordSUBNAMEorESPMNAME)
            menuItem.SetBitmap(gImgIdx['list16.png'])
            menuItem.SetBackgroundColour(u'#FFF7EE')
            menuItem.SetSubMenu(submenu)
            rightclickmenu.AppendItem(menuItem)

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
                    resetespmnamesubmenuitem.SetBitmap(gImgIdx['esp16.png'])
                elif filename.endswith(u'.esm'):
                    resetespmnamesubmenuitem = wx.MenuItem(rightclickmenu, newid, u'ResetEspmName "' + u'%s' %filename + u'"', u' ResetEspmName "[espmName]"')
                    resetespmnamesubmenuitem.SetBitmap(gImgIdx['esm16.png'])
                submenu.AppendItem(resetespmnamesubmenuitem)
                wx.EVT_MENU(rightclickmenu, newid, self.OnWriteKeywordSUBNAMEorESPMNAME)
            menuItem.SetBitmap(gImgIdx['list16.png'])
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
            packagename.SetBitmap(wx.Bitmap(gImgDir + os.sep + u'diamond_white_off_wiz.png',p))
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
                        submenuitem.SetBitmap(gImgIdx['file_image16.png'])
                    elif ext == u'.png':
                        submenuitem.SetBitmap(gImgIdx['file_png16.png'])
                    else:
                        submenuitem.SetBitmap(gImgIdx['black16.png'])
                    submenu.AppendItem(submenuitem)
                    wx.EVT_MENU(rightclickmenu, newid, self.OnWriteImageDirectoryIMAGE)
            menuItem.SetBitmap(gImgIdx['list16.png'])
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
            packagename.SetBitmap(wx.Bitmap(gImgDir + os.sep + u'diamond_white_off_wiz.png',p))
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
                        submenuitem.SetBitmap(gImgIdx['file_image16.png'])
                    elif ext == u'.png':
                        submenuitem.SetBitmap(gImgIdx['file_png16.png'])
                    else:
                        submenuitem.SetBitmap(gImgIdx['black16.png'])
                    submenu.AppendItem(submenuitem)
                    wx.EVT_MENU(rightclickmenu, newid, self.OnWriteImageDirectoryIMAGE)
            menuItem.SetBitmap(gImgIdx['list16.png'])
            menuItem.SetBackgroundColour(u'#FFF7EE')
            menuItem.SetSubMenu(submenu)
            rightclickmenu.AppendItem(menuItem)
        else:
            screenshotsimages = wx.MenuItem(rightclickmenu, ID_SCREENSHOTS, u'Screenshots\\\\', u' Screenshots\\\\')
            rightclickmenu.AppendItem(screenshotsimages)

        #--- Built-in Help Start ---#
        builtinhelpSubmenu = wx.Menu()

        subsubmenu = wx.Menu()
        deprecatedwords = ['CompareObVersion','CompareOBSEVersion','CompareOBGEVersion']
        for keyword in self.allkeywords:
            newid = wx.NewId()
            menuItem = wx.MenuItem(rightclickmenu, newid, u'%s'%keyword, u' %s'%keyword)
            if keyword in deprecatedwords:
                menuItem.SetBitmap(gImgIdx['wizardhatred16.png'])
            else:
                menuItem.SetBitmap(gImgIdx['wizardhat16.png'])
            subsubmenu.AppendItem(menuItem)
            wx.EVT_MENU(rightclickmenu, newid, self.OnShowCallTipMenuLabel)
        builtinhelpSubmenu.AppendMenu(wx.NewId(), u'All Wizard Language Words(ShowCallTip)', subsubmenu)

        subsubmenu = wx.Menu()
        for dialogword in ['SelectOne','SelectMany','RequireVersions','Cancel']:
            newid = wx.NewId()
            menuItem = wx.MenuItem(rightclickmenu, newid, u'%s'%dialogword, u' %s'%dialogword)
            subsubmenu.AppendItem(menuItem)
            wx.EVT_MENU(rightclickmenu, newid, self.OnAddTextMenuLabel)
        builtinhelpSubmenu.AppendMenu(wx.NewId(), u'Dialog Words', subsubmenu)

        subsubmenu = wx.Menu()
        for functionword in ['CompareObVersion','CompareGameVersion','CompareOBSEVersion','CompareSEVersion','CompareOBGEVersion','CompareGEVersion','CompareWBVersion','DataFileExists','GetEspmStatus','EditINI','DisableINILine','Exec','str','int','float','len','endswith','startswith','lower','find','rfind','GetFilename','GetFolder']:
            newid = wx.NewId()
            menuItem = wx.MenuItem(rightclickmenu, newid, u'%s'%functionword, u' %s'%functionword)
            subsubmenu.AppendItem(menuItem)
            wx.EVT_MENU(rightclickmenu, newid, self.OnAddTextMenuLabel)
        builtinhelpSubmenu.AppendMenu(wx.NewId(), u'Function Words', subsubmenu)

        subsubmenu = wx.Menu()
        for keyword in ['SelectSubPackage','DeSelectSubPackage','SelectEspm','DeSelectEspm','SelectAll','DeSelectAll','SelectAllEspms','DeSelectAllEspms','RenameEspm','ResetEspmName','ResetAllEspmNames','Note','If','Elif','Else','EndIf','While','Continue','Break','EndWhile','For','Continue','Break','EndFor','SelectOne','Case','Default','Break','EndSelect','SelectMany','Return','Cancel','RequireVersions']:
            newid = wx.NewId()
            menuItem = wx.MenuItem(rightclickmenu, newid, u'%s'%keyword, u' %s'%keyword)
            subsubmenu.AppendItem(menuItem)
            wx.EVT_MENU(rightclickmenu, newid, self.OnAddTextMenuLabel)
        builtinhelpSubmenu.AppendMenu(wx.NewId(), u'Keywords', subsubmenu)

        subsubmenu = wx.Menu()
        for key, value in self.assignmentOperatorDict.iteritems():
            newid = wx.NewId()
            menuItem = wx.MenuItem(rightclickmenu, newid, u'&%s'%value, u' %s'%value)
            subsubmenu.AppendItem(menuItem)
            wx.EVT_MENU(rightclickmenu, newid, self.OnAssignmentMathBooleanComparisonOperators)
        builtinhelpSubmenu.AppendMenu(wx.NewId(), u'Assignment Operators', subsubmenu)

        subsubmenu = wx.Menu()
        for key, value in self.mathOperatorDict.iteritems():
            newid = wx.NewId()
            menuItem = wx.MenuItem(rightclickmenu, newid, u'&%s'%value, u' %s'%value)
            subsubmenu.AppendItem(menuItem)
            wx.EVT_MENU(rightclickmenu, newid, self.OnAssignmentMathBooleanComparisonOperators)
        builtinhelpSubmenu.AppendMenu(wx.NewId(), u'Math Operators', subsubmenu)

        subsubmenu = wx.Menu()
        for key, value in self.booleanOperatorDict.iteritems():
            newid = wx.NewId()
            if key == '&':#ampersand needs two to show in a wx.menu. this is acounted for in the function also.
                menuItem = wx.MenuItem(rightclickmenu, newid, u'&And (&&)', u' And (&&)')
            else:
                menuItem = wx.MenuItem(rightclickmenu, newid, u'&%s'%value, u' %s'%value)
            subsubmenu.AppendItem(menuItem)
            wx.EVT_MENU(rightclickmenu, newid, self.OnAssignmentMathBooleanComparisonOperators)
        builtinhelpSubmenu.AppendMenu(wx.NewId(), u'Boolean Operators', subsubmenu)

        subsubmenu = wx.Menu()
        for key, value in self.comparisonOperatorDict.iteritems():
            newid = wx.NewId()
            menuItem = wx.MenuItem(rightclickmenu, newid, u'&%s'%value, u' %s'%value)
            subsubmenu.AppendItem(menuItem)
            wx.EVT_MENU(rightclickmenu, newid, self.OnAssignmentMathBooleanComparisonOperators)
        builtinhelpSubmenu.AppendMenu(wx.NewId(), u'Comparison Operators', subsubmenu)

        subsubmenu = wx.Menu()
        for builtinconstant in ['True','False']:
            newid = wx.NewId()
            menuItem = wx.MenuItem(rightclickmenu, newid, u'%s'%builtinconstant, u' %s'%builtinconstant)
            subsubmenu.AppendItem(menuItem)
            wx.EVT_MENU(rightclickmenu, newid, self.OnAddTextMenuLabel)
        builtinhelpSubmenu.AppendMenu(wx.NewId(), u'Built-in Constants', subsubmenu)

        subsubmenu = wx.Menu()
        for escapesequence in ['\\"','\\\'','\\t','\\n','\\\\']:
            newid = wx.NewId()
            menuItem = wx.MenuItem(rightclickmenu, newid, u'%s'%escapesequence, u' %s'%escapesequence)
            subsubmenu.AppendItem(menuItem)
            wx.EVT_MENU(rightclickmenu, newid, self.OnAddTextMenuLabel)
        builtinhelpSubmenu.AppendMenu(wx.NewId(), u'Escape Sequences', subsubmenu)

        rightclickmenu.AppendMenu(wx.NewId(), u'Built-In Help/CheatSheet', builtinhelpSubmenu)

        #--- Built-in Help End ---#

        rightclickmenu.AppendSeparator()

        submenu = wx.Menu()
        listactivesubpackages = wx.MenuItem(rightclickmenu, ID_LISTSUBPACKAGES, u'&List SubPackages... (De)/SelectSubPackages', u' List SubPackages...')
        listactivesubpackages.SetBitmap(gImgIdx['list16.png'])
        submenu.AppendItem(listactivesubpackages)

        listactiveespms = wx.MenuItem(rightclickmenu, ID_LISTESPMS, u'&List Espms... (De)/SelectEspm', u' List Espms...')
        listactiveespms.SetBitmap(gImgIdx['list16.png'])
        submenu.AppendItem(listactiveespms)

        rightclickmenu.AppendMenu(wx.NewId(), u'List...', submenu)

        imagebrowserpackagewizardimages = wx.MenuItem(rightclickmenu, ID_IMAGEBROWSER, u'&ImageBrowser [packageName\\Wizard Images]')
        imagebrowserpackagewizardimages.SetBitmap(gImgIdx['file_image16.png'])
        rightclickmenu.AppendItem(imagebrowserpackagewizardimages)

        thumbnailerpackagewizardimages = wx.MenuItem(rightclickmenu, ID_THUMBNAILER, u'&Thumbnailer [packageName\\Wizard Images]')
        thumbnailerpackagewizardimages.SetBitmap(gImgIdx['python16.png'])
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

        wx.EVT_MENU(rightclickmenu, ID_WHILECONTINUEBREAKENDWHILE, self.OnWhileContinueBreakEndWhile)
        wx.EVT_MENU(rightclickmenu, ID_FORCONTINUEBREAKENDFOR, self.OnForContinueBreakEndFor)
        wx.EVT_MENU(rightclickmenu, ID_FORSUBINSUBPACKAGES, self.OnForSubInSubPackages)

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

        for i in range(0,len(gRmgmIDs)):
            wx.EVT_MENU(rightclickmenu, gRmgmIDs[i], gRmgmDEFs[i])
        wx.EVT_MENU(rightclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        wx.EVT_MENU(rightclickmenu, ID_RMGM2DRAG, self.OnUseOnTopDraggableRMouseGestureMenu2)

        self.PopupMenu(rightclickmenu)
        rightclickmenu.Destroy()

    def OnShowCallTipMenuLabel(self, event):
        ''' This function adds text to the document from the dynamically generated menuitems by getting the menuitems's label. '''
        id =  event.GetId()
        evtobj = event.GetEventObject()
        menuitem = evtobj.FindItemById(id)
        pos = self.GetCurrentPos()
        try:
            self.CallTipSetBackground('#D7DEEB')
            self.CallTipSetForeground('#666666')
            self.CallTipShow(pos,self.gCallTipDict[u'%s' %menuitem.GetItemLabel()])
            #try to highlight the keyword
            try:
                match = re.search(u'%s' %menuitem.GetItemLabel(), self.gCallTipDict[u'%s' %menuitem.GetItemLabel()])
                foundpostions = (match.span())
                self.CallTipSetHighlight(foundpostions[0], foundpostions[1])
                self.CallTipSetForegroundHighlight('#FF0000')
            except:
                pass#NoneType
        except:
            self.CallTipSetBackground('#F6F68C')
            self.CallTipSetForeground('#666666')
            self.CallTipShow(pos,'Hmmm. No CallTip for that...')

    def OnAddTextMenuLabel(self, event):
        ''' This function adds text to the document from the dynamically generated menuitems by getting the menuitems's label. '''
        id =  event.GetId()
        # print event.GetId()
        # print event.GetEventObject()
        evtobj = event.GetEventObject()
        menuitem = evtobj.FindItemById(id)
        # print menuitem.GetItemLabel()
        self.AddText(u'%s' %menuitem.GetItemLabel())

    def OnIfElifElseEndIf(self, event):
        indentSz = basher.settings['bash.installers.wizSTC.IndentSize']
        self.AddText(u'If\n' +
                     u' '*indentSz + u';#\n' +
                     u'Elif\n' +
                     u' '*indentSz + u';#\n' +
                     u'Else\n' +
                     u' '*indentSz + u';#\n' +
                     u'EndIf\n')

    def OnWhileContinueBreakEndWhile(self, event):
        indentSz = basher.settings['bash.installers.wizSTC.IndentSize']
        self.AddText(u'While\n' +
                     u' '*indentSz + u';#\n' +
                     u' '*indentSz + u'Continue\n' +
                     u' '*indentSz + u';#\n' +
                     u' '*indentSz + u'Break\n' +
                     u' '*indentSz + u';#\n' +
                     u'EndWhile\n')

    def OnForContinueBreakEndFor(self, event):
        indentSz = basher.settings['bash.installers.wizSTC.IndentSize']
        self.AddText(u'For\n' +
                     u' '*indentSz + u';#\n' +
                     u' '*indentSz + u'Continue\n' +
                     u' '*indentSz + u';#\n' +
                     u' '*indentSz + u'Break\n' +
                     u' '*indentSz + u';#\n' +
                     u'EndFor\n')

    def OnForSubInSubPackages(self, event):
        indentSz = basher.settings['bash.installers.wizSTC.IndentSize']
        self.AddText(u'For sub in SubPackages\n' +
                     u' '*indentSz + u'For file in sub\n' +
                     u' '*indentSz*2 + u';#lines\n' +
                     u' '*indentSz + u'EndFor\n' +
                     u'EndFor\n')

    def OnUseOnTopDraggableRMouseGestureMenu2(self, event):
        ''' Call the Floating-Draggable Version of the menu. '''
        if self.dragmenu2 == 0:
            # win = DraggableRMouseGestureMenu2(self, wx.SIMPLE_BORDER)
            win = DraggableScrolledPanel(self, wx.SIMPLE_BORDER)
            win.Centre()
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
                if os.path.exists(packagenamewizardimagesDir):
                    self.dialog = wx.Dialog(self, -1, title=u'%s' %basher.gInstallers.gPackage.GetValue() + os.sep + u'Wizard Images',
                                            size=(545, 425), style=wx.DEFAULT_DIALOG_STYLE)
                    self.dialog.SetBackgroundColour('#000000') # Set the Frame Background Color

                    
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
                else:
                    wx.MessageBox(u'%s\nNot found!'%packagenamewizardimagesDir, u'WARNING', wx.ICON_EXCLAMATION | wx.OK)

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

    def OnAssignmentMathBooleanComparisonOperators(self, event):
        ''' This function adds text(Assignment, Math, Boolean, or Comparison Operators) to the document from the dynamically generated menuitems by getting the comparison operator from menuitems's label. '''
        id =  event.GetId()
        # print event.GetId()
        # print event.GetEventObject()
        evtobj = event.GetEventObject()
        menuitem = evtobj.FindItemById(id)
        # print menuitem.GetItemLabel()
        menulabel = menuitem.GetItemLabel()
        operatorinbraces = menulabel[menulabel.rfind('(')+1:menulabel.rfind(')')]
        if operatorinbraces == '&&':#account for ampersand behavior in wx.menu
            self.AddText(u'&')
        else:
            self.AddText(u'%s' %operatorinbraces)

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
        ''' Write DataFileExists ("") to the editor. '''
        self.OnDeleteIfSelectedText(event)
        self.AddText('DataFileExists ("")')
        self.CharLeft()
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
        dialog.SetIcon(wx.Icon(gImgStcDir + os.sep + u'wizardhat16.png', wx.BITMAP_TYPE_PNG))
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
        dialog.SetIcon(wx.Icon(gImgStcDir + os.sep + u'wizardhat16.png', wx.BITMAP_TYPE_PNG))
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

        rcheader1 = wx.MenuItem(rightclickmenu, 0000, u'&R MGM 3', u'ContextMenu3')
        rcheader1.SetBackgroundColour('#000000')
        rightclickmenu.AppendItem(rcheader1)
        rcheader1.SetDisabledBitmap(gRmbImg)
        rcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            if i == 3:#The currently open menu
                mgm = wx.MenuItem(rightclickmenu, gRmgmIDs[i-1], u'&R MGM %s You Are Here!\tCtrl+3'%str(i), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(gYahImg)
                mgm.SetBackgroundColour('#F4FAB4')
                mgm.Enable(False)
            else:
                mgm = wx.MenuItem(rightclickmenu, gRmgmIDs[i-1], u'&R MGM %s %s'%(str(i),gRmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(gMgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(rightclickmenu, ID_MMGM5, u'&M MGM 5 Macro\tCtrl+0', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(gMgmImg)
        submenu.AppendItem(mgm)
        rightclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        rightclickmenu.AppendSeparator()

        showcalltip = wx.MenuItem(rightclickmenu, ID_CALLTIP, u'&Show CallTip\tCtrl+Shift+Space', u' Show a calltip for the currently selected word.')
        showcalltip.SetBitmap(gImgIdx['showcalltip24.png'])
        rightclickmenu.AppendItem(showcalltip)

        wordcomplete = wx.MenuItem(rightclickmenu, ID_WORDCOMPLETE, u'&WordComplete Box\tCtrl+W', u' Ctrl+W opens the WordComplete box')
        wordcomplete.SetBitmap(gImgIdx['wordcomplete24.png'])
        rightclickmenu.AppendItem(wordcomplete)

        autocomplete = wx.MenuItem(rightclickmenu, ID_AUTOCOMPLETE, u'&AutoComplete Box\tCtrl+Space', u' Ctrl+Space opens the AutoComplete box')
        autocomplete.SetBitmap(gImgIdx['autocomplete24.png'])
        rightclickmenu.AppendItem(autocomplete)

        #events
        for i in range(0,len(gRmgmIDs)):
            wx.EVT_MENU(rightclickmenu, gRmgmIDs[i], gRmgmDEFs[i])
        wx.EVT_MENU(rightclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        wx.EVT_MENU(rightclickmenu, ID_CALLTIP, self.OnShowSelectedTextCallTip)
        wx.EVT_MENU(rightclickmenu, ID_WORDCOMPLETE, self.OnShowWordCompleteBox)
        wx.EVT_MENU(rightclickmenu, ID_AUTOCOMPLETE, self.OnShowAutoCompleteBox)

        self.PopupMenu(rightclickmenu)
        rightclickmenu.Destroy()

    def OnShowSelectedTextCallTip(self, event):
        ''' Show a CallTip for the currently selected wizard script keyword. '''
        pos = self.GetCurrentPos()
        someword = self.GetSelectedText()

        self.CallTipSetHighlight(2, 5)                  #Highlight a segment of the definition.(int start, int end)
        self.CallTipSetForegroundHighlight('#FF0000')   #Set the foreground colour for the highlighted part of the call tip.
        self.CallTipSetForeground('#666666')            #Set the foreground colour for the call tip.
        self.CallTipSetBackground('#D7DEEB')            #Set the background colour for the call tip.
        # self.CallTipPosAtStart()    #Retrieve the position where the caret was before displaying the call tip.
        # self.CallTipUseStyle(48)    #Enable use of STYLE_CALLTIP and set call tip tab size in pixels.
        # self.CallTipActive()        #Is there an active call tip? -> bool
        # self.CallTipCancel()        #Remove the call tip from the screen.
        # self.CallTipPosAtStart()    #Retrieve the position where the caret was before displaying the call tip.

        try:
            self.CallTipShow(pos,self.gCallTipDict[someword])
            #try to highlight the keyword
            try:
                match = re.search(u'%s' %someword, self.gCallTipDict[someword])
                foundpostions = (match.span())
                self.CallTipSetHighlight(foundpostions[0], foundpostions[1])
                self.CallTipSetForegroundHighlight('#FF0000')
            except:
                pass#NoneType
        except:
            try:
                self.CallTipShow(pos,self.gEasterEggCallTipDict[someword])
            except:
                self.CallTipSetBackground('#F6F68C')#Traditional Wrye Readme Yellow
                self.CallTipSetForeground('#666666')
                self.CallTipShow(pos,'Hmmm. No CallTip for that...')


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

    def OnHotSpotDClick(self, event):
        if basher.settings['bash.installers.wizSTC.IntelliCallTip'] == 1:
            pos = self.GetCurrentPos()
            autocompletedkeywordis = self.GetSelectedText()
            try:
                self.CallTipSetBackground('#D7DEEB')
                self.CallTipSetForeground('#666666')
                self.CallTipShow(pos, self.gCallTipDict[u'%s'%autocompletedkeywordis])
                # try to highlight the keyword
                try:
                    match = re.search(u'%s' %autocompletedkeywordis, self.gCallTipDict[u'%s' %autocompletedkeywordis])
                    foundpostions = (match.span())
                    self.CallTipSetHighlight(foundpostions[0], foundpostions[1])
                    self.CallTipSetForegroundHighlight('#FF0000')
                except:
                    pass#NoneType
            except:
                self.CallTipSetBackground('#F6F68C')
                self.CallTipSetForeground('#666666')
                self.CallTipShow(pos,'Hmmm. No CallTip for that...')



    def OnShowAutoCompleteBox(self, event):
        '''Shows the Auto-Complete Box in the editor filled with wizard script keywords.'''
        if basher.settings['bash.installers.wizSTC.LoadSTCLexer'] == 'wizbainlexer':
            kw = keywordWIZBAIN.kwlist[:] + keywordWIZBAIN2.kwlist[:]
            # Optionally add more ...
            ## kw.append('__U__SePeRaToR__l__?')#Adding extra words screws with IntelliCallTip
            # Python sorts are case sensitive
            kw.sort()
            # So this needs to match
            self.AutoCompSetIgnoreCase(False)
            self.AutoCompSetChooseSingle(True) #Should a single item auto-completion list automatically choose the item.

            self.AutoCompSetCancelAtStart(False)#Should the auto-completion list be cancelled if the user backspaces to a position before where the box was created. Ex False:Call Autocomplete and type "C", then backspace "C"... Notice the box doesn't cancel until you backspace the second time.
            self.AutoCompSetAutoHide(False)#Set whether or not autocompletion is hidden automatically when nothing matches.

            # self.AutoCompSetDropRestOfWord(False)#Set whether or not autocompletion deletes any word characters after the inserted text upon completion.

            # # print self.AutoCompGetMaxWidth()
            # self.AutoCompSetMaxWidth(0)
            # # print self.AutoCompGetMaxHeight()
            # self.AutoCompSetMaxHeight(9)

            # # self.AutoCompSetFillUps('L')

            ## self.AutoCompSetTypeSeparator(int separatorCharacter)#Change the type-separator character in the string setting up an auto-completion list. Default is '?' but can be changed if items contain '?'.
            # Registered images are specified with appended '?type'
            for i in range(len(kw)):
                if kw[i] in keywordWIZBAIN.kwlist or keywordWIZBAIN2.kwlist:
                    kw[i] = kw[i] + '?5'
            self.AutoCompShow(0, ' '.join(kw))

            self.autocompstartpos = self.AutoCompPosStart()


    def OnRMouseGestureMenu4(self, event):
        ''' Call the Right Mouse Gesture Menu.
        NUMPAD:4
        [7][8][9]
        [@][5][6]
        [1][2][3]
        '''
        rightclickmenu = wx.Menu()

        rcheader1 = wx.MenuItem(rightclickmenu, 0000, u'&R MGM 4 Case', u'ContextMenu4')
        rcheader1.SetBackgroundColour('#000000')
        rightclickmenu.AppendItem(rcheader1)
        rcheader1.SetDisabledBitmap(gRmbImg)
        rcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            if i == 4:#The currently open menu
                mgm = wx.MenuItem(rightclickmenu, gRmgmIDs[i-1], u'&R MGM %s You Are Here!\tCtrl+4'%str(i), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(gYahImg)
                mgm.SetBackgroundColour('#F4FAB4')
                mgm.Enable(False)
            else:
                mgm = wx.MenuItem(rightclickmenu, gRmgmIDs[i-1], u'&R MGM %s %s'%(str(i),gRmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(gMgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(rightclickmenu, ID_MMGM5, u'&M MGM 5 Macro\tCtrl+0', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(gMgmImg)
        submenu.AppendItem(mgm)
        rightclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        rightclickmenu.AppendSeparator()

        uppercase = wx.MenuItem(rightclickmenu, ID_UPPERCASE, '&UPPER CASE\tCtrl+Shift+U', ' Change Selected text to all UPPER CASE')
        uppercase.SetBitmap(gImgIdx['uppercase16.png'])
        rightclickmenu.AppendItem(uppercase)
        lowercase = wx.MenuItem(rightclickmenu, ID_LOWERCASE, '&lower case\tCtrl+U', ' Change Selected text to all lower case')
        lowercase.SetBitmap(gImgIdx['lowercase16.png'])
        rightclickmenu.AppendItem(lowercase)
        invertcase = wx.MenuItem(rightclickmenu, ID_INVERTCASE, '&iNVERT cASE', ' Invert Case of Selected text')
        invertcase.SetBitmap(gImgIdx['invertcase2416.png'])
        rightclickmenu.AppendItem(invertcase)
        capitalcase = wx.MenuItem(rightclickmenu, ID_CAPITALCASE, '&Capital Case', ' Change Selected text to all Capital Case(words)')
        capitalcase.SetBitmap(gImgIdx['capitalcase16.png'])
        rightclickmenu.AppendItem(capitalcase)

        #events
        wx.EVT_MENU(rightclickmenu, ID_UPPERCASE, self.OnUPPERCASE)
        wx.EVT_MENU(rightclickmenu, ID_LOWERCASE, self.Onlowercase)
        wx.EVT_MENU(rightclickmenu, ID_INVERTCASE, self.OnInvertCase)
        wx.EVT_MENU(rightclickmenu, ID_CAPITALCASE, self.OnCapitalCase)

        for i in range(0,len(gRmgmIDs)):
            wx.EVT_MENU(rightclickmenu, gRmgmIDs[i], gRmgmDEFs[i])
        wx.EVT_MENU(rightclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        self.PopupMenu(rightclickmenu)
        rightclickmenu.Destroy()

    def OnUPPERCASE(self, event):
        '''Converts selection to UPPERCASE.'''
        self.UpperCase()
        # dprint ('OnUPPERCASE')

    def Onlowercase(self, event):
        '''Converts selection to lowercase.'''
        self.LowerCase()
        # dprint ('Onlowercase')

    def OnInvertCase(self, event):
        '''Inverts the case of the selected text.'''
        getsel = self.GetSelection()
        selectedtext = self.GetSelectedText()
        if len(selectedtext):
            self.BeginUndoAction()
            self.ReplaceSelection(selectedtext.swapcase())
            self.SetSelection(getsel[1],getsel[0])#Keep the text selected afterwards retaining caret pos
            self.EndUndoAction()
        # dprint ('OnInvertCase')

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
                if u'a' <= character.lower() <= u'z':
                    if word == False:
                        character = character.upper()
                        word = True
                else:
                    if word == True:
                        word = False
                s.append(character)
            text = u''.join(s)
            self.BeginUndoAction()
            self.ReplaceSelection(text)
            self.SetSelection(getsel[1],getsel[0])#Keep the text selected afterwards retaining caret pos
            self.EndUndoAction()
        self.EndUndoAction()
        # dprint ('OnCapitalCase')

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
        rcheader1.SetDisabledBitmap(gRmbImg)
        rcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            if i == 6:#The currently open menu
                mgm = wx.MenuItem(rightclickmenu, gRmgmIDs[i-1], u'&R MGM %s You Are Here!\tCtrl+6'%str(i), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(gYahImg)
                mgm.SetBackgroundColour('#F4FAB4')
                mgm.Enable(False)
            else:
                mgm = wx.MenuItem(rightclickmenu, gRmgmIDs[i-1], u'&R MGM %s %s'%(str(i),gRmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(gMgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(rightclickmenu, ID_MMGM5, u'&M MGM 5 Macro\tCtrl+0', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(gMgmImg)
        submenu.AppendItem(mgm)
        rightclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        rightclickmenu.AppendSeparator()

        txt2wizstrfiledrop = wx.MenuItem(rightclickmenu, ID_TXT2WIZSTRFILE, u'& Txt2WizStr\t(FileDrop)', u' Txt2WizStr (FileDrop)')
        txt2wizstrfiledrop.SetBitmap(wx.Bitmap(gImgDir + os.sep + u'wizard.png',p))
        rightclickmenu.AppendItem(txt2wizstrfiledrop)

        txt2wizstrtextdrop = wx.MenuItem(rightclickmenu, ID_TXT2WIZSTRTEXT, u'& Txt2WizStr\t(TextDrop)', u' Txt2WizStr (TextDrop)')
        txt2wizstrtextdrop.SetBitmap(wx.Bitmap(gImgDir + os.sep + u'wizard.png',p))
        rightclickmenu.AppendItem(txt2wizstrtextdrop)

        enlargeselection = wx.MenuItem(rightclickmenu, ID_ENLARGESELECTION, '&Enlarge Selection', ' Enlarge the selection by 1 on both ends(starting and ending).')
        enlargeselection.SetBitmap(gImgIdx['black16.png'])
        rightclickmenu.AppendItem(enlargeselection)

        decreaseselection = wx.MenuItem(rightclickmenu, ID_DECREASESELECTION, '&Decrease Selection', ' Decrease the selection by 1 on both ends(starting and ending).')
        decreaseselection.SetBitmap(gImgIdx['black16.png'])
        rightclickmenu.AppendItem(decreaseselection)

        convertquotestosinglequotes = wx.MenuItem(rightclickmenu, ID_CONVERTQUOTES2SINGLE, '&Convert quotes to \' s\t(Sel Text)', ' Convert quotes to \' s.')
        convertquotestosinglequotes.SetBitmap(gImgIdx['singlequote16.png'])
        rightclickmenu.AppendItem(convertquotestosinglequotes)

        convertquotestodoublequotes = wx.MenuItem(rightclickmenu, ID_CONVERTQUOTES2DOUBLE, '&Convert quotes to " s\t(Sel Text)', ' Convert quotes to " s.')
        convertquotestodoublequotes.SetBitmap(gImgIdx['doublequote16.png'])
        rightclickmenu.AppendItem(convertquotestodoublequotes)

        swapquotes = wx.MenuItem(rightclickmenu, ID_CONVERTSWAPQUOTES, '&Swap Quotes "<->\'\t(Sel Text)', ' Swap Quotes "<->\'')
        swapquotes.SetBitmap(gImgIdx['swapquotes16.png'])
        rightclickmenu.AppendItem(swapquotes)

        escapesinglequotes = wx.MenuItem(rightclickmenu, ID_CONVERTESCAPESINGLEQUOTES, '&Escape single quotes to \\\' s\t(Sel Text)', ' Escape single quotes to \\\' s.')
        escapesinglequotes.SetBitmap(gImgIdx['singlequote16.png'])
        rightclickmenu.AppendItem(escapesinglequotes)

        escapedoublequotes = wx.MenuItem(rightclickmenu, ID_CONVERTESCAPEDOUBLEQUOTES, '&Escape double quotes to \\\" s\t(Sel Text)', ' Escape double quotes to \\\" s.')
        escapedoublequotes.SetBitmap(gImgIdx['doublequote16.png'])
        rightclickmenu.AppendItem(escapedoublequotes)

        escapesingletodoublequotes = wx.MenuItem(rightclickmenu, ID_CONVERTESCSINGLEQUOTES2DOUBLEQUOTES, '&Escape single quotes to \\\" s\t(Sel Text)', ' Escape single quotes to \\\" s.')
        escapesingletodoublequotes.SetBitmap(gImgIdx['singlequote16.png'])
        rightclickmenu.AppendItem(escapesingletodoublequotes)

        #events
        wx.EVT_MENU(rightclickmenu, ID_TXT2WIZSTRFILE, self.OnTextToWizardStringFileDropMiniFrame)
        wx.EVT_MENU(rightclickmenu, ID_TXT2WIZSTRTEXT, self.OnTextToWizardStringTextDropMiniFrame)

        wx.EVT_MENU(rightclickmenu, ID_ENLARGESELECTION, self.OnEnlargeSelection)
        wx.EVT_MENU(rightclickmenu, ID_DECREASESELECTION, self.OnDecreaseSelection)
        wx.EVT_MENU(rightclickmenu, ID_CONVERTQUOTES2SINGLE, self.OnConvertQuotesToSingle)
        wx.EVT_MENU(rightclickmenu, ID_CONVERTQUOTES2DOUBLE, self.OnConvertQuotesToDouble)
        wx.EVT_MENU(rightclickmenu, ID_CONVERTSWAPQUOTES, self.OnConvertSwapQuotes)

        wx.EVT_MENU(rightclickmenu, ID_CONVERTESCAPESINGLEQUOTES, self.OnEscapeSingleQuotes)
        wx.EVT_MENU(rightclickmenu, ID_CONVERTESCAPEDOUBLEQUOTES, self.OnEscapeDoubleQuotes)
        wx.EVT_MENU(rightclickmenu, ID_CONVERTESCSINGLEQUOTES2DOUBLEQUOTES, self.OnEscapeSingleQoutesToDoubleQuotes)


        for i in range(0,len(gRmgmIDs)):
            wx.EVT_MENU(rightclickmenu, gRmgmIDs[i], gRmgmDEFs[i])
        wx.EVT_MENU(rightclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        self.PopupMenu(rightclickmenu)
        rightclickmenu.Destroy()

    def OnTextToWizardStringFileDropMiniFrame(self, event):
        ''' Call the TextToWizardString(FileDrop) convertor floating miniframe. '''
        texttowizardstringminiframe = wx.MiniFrame(self, -1, u'Text To Wizard String (File Drop)', style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT, size=(300, 150))

        texttowizardstringminiframe.SetSizeHints(200,150)

        texttowizardstringminiframe.textctrl1 = TextToWizardStringSTC(texttowizardstringminiframe)
        msg = u'Drag & Drop the textfile into this miniframe. \nIt will automatically be converted to a wizard string! \nYou can then SelectAll, Cut, Paste it into the Editor. \nThis is useful for readmes, etc...'
        try:
            texttowizardstringminiframe.textctrl1.SetTextUTF8(msg)
        except:
            texttowizardstringminiframe.textctrl1.SetText(msg)
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
            texttowizardstringtextdropminiframe.textctrl1.SetTextUTF8(msg)
        except:
            texttowizardstringtextdropminiframe.textctrl1.SetText(msg)
        texttowizardstringtextdropminiframe.textctrl1.EmptyUndoBuffer()

        #Drag and Drop - Text Drop
        textdroptarget = TextDropTargetForTextToWizardString(texttowizardstringtextdropminiframe.textctrl1)
        texttowizardstringtextdropminiframe.textctrl1.SetDropTarget(textdroptarget)

        texttowizardstringtextdropminiframe.Centre()
        texttowizardstringtextdropminiframe.Show()

    def OnEnlargeSelection(self, event):
        '''Enlarge the selection by 1 space on both ends(starting and ending)'''
        getsel = self.GetSelection()
        # print getsel
        if getsel[1] < getsel[0]:
            self.SetSelection(getsel[1]-1,getsel[0]+1)
        else:
            self.SetSelection(getsel[1]+1,getsel[0]-1)
        # print('EnlargeSelection')

    def OnDecreaseSelection(self, event):
        '''Decrease the selection by 1 space on both ends(starting and ending)'''
        getsel = self.GetSelection()
        if getsel[1] < getsel[0]:
            self.SetSelection(getsel[1]+1,getsel[0]-1)
        else:
            self.SetSelection(getsel[1]-1,getsel[0]+1)
        # print('DecreaseSelection')

    def OnConvertQuotesToSingle(self, event):
        self.OnConvertSelectionTargetToNewText(target = '"',
                                               newtext = "\'",
                                               message = 'You don\'t have anything selected!\nWould you like to convert all quotes in the whole document?',
                                               title = 'Convert Quotes To \'')

    def OnConvertQuotesToDouble(self, event):
        self.OnConvertSelectionTargetToNewText(target = '\'',
                                               newtext = '"',
                                               message = 'You don\'t have anything selected!\nWould you like to convert all quotes in the whole document?',
                                               title = 'Convert Quotes To "')

    def OnConvertSwapQuotes(self, event):
        '''
        Swap 'Qoute"s' <-> Swap "Qoute's"
        on selected text.
        '''
        if self.GetSelectionStart() == self.GetSelectionEnd():
            dialog = wx.MessageDialog(self, 'You don\'t have anything selected!\nWould you like to swap all qoutes in the whole document?',
                                      'Swap \'Qoute"s\' <-> Swap "Qoute\'s"', wx.YES_NO|wx.NO_DEFAULT|wx.ICON_EXCLAMATION)
            if dialog.ShowModal() == wx.ID_YES:
                self.BeginUndoAction()
                curline = self.GetCurrentLine()
                self.SelectAll()
                text = self.GetTextUTF8()
                newtext = ''
                for char in text:
                    if char == '\'':
                        newtext += '"'
                    elif char == '"':
                        newtext += '\''
                    else:
                        newtext += str(char)
                self.Clear()
                self.SetTextUTF8(newtext)
                self.GotoLine(curline)
                self.EndUndoAction()
            dialog.Destroy()
        else:
            text = self.GetSelectedText()
            newtext = ''
            for char in text:
                if char == '\'':
                    newtext += '"'
                elif char == '"':
                    newtext += '\''
                else:
                    newtext += str(char)
            self.Clear()
            self.AddText(newtext)
            self.EndUndoAction()
        # print newtext

    def OnEscapeSingleQuotes(self, event):
        self.OnConvertSelectionTargetToNewText(target = "\'",
                                               newtext = "\\'",
                                               message = 'You don\'t have anything selected!\nWould you like to escape all single quotes in the whole document?',
                                               title = 'Escape Single Quotes To \\\'')

    def OnEscapeDoubleQuotes(self, event):
        self.OnConvertSelectionTargetToNewText(target = '\"',
                                               newtext = '\\"',
                                               message = 'You don\'t have anything selected!\nWould you like to escape all double quotes in the whole document?',
                                               title = 'Escape Double Quotes To \\\'')

    def OnEscapeSingleQoutesToDoubleQuotes(self, event):
        self.OnConvertSelectionTargetToNewText(target = "\'",
                                               newtext = '\\"',
                                               message = 'You don\'t have anything selected!\nWould you like to escape all single qoutes to double quotes in the whole document?',
                                               title = 'Escape Single Quotes To \\\"')

    def OnConvertSelectionTargetToNewText(self, target, newtext, message, title):
        # target = 'a'
        # newtext = 'z'
        # message = 'bla bla'
        # title = 'The title'
        if self.GetSelectionStart() == self.GetSelectionEnd():
            dialog = wx.MessageDialog(self, message, title, wx.YES_NO|wx.NO_DEFAULT|wx.ICON_EXCLAMATION)
            if dialog.ShowModal() == wx.ID_YES:
                self.BeginUndoAction()
                curpos = self.GetCurrentPos()
                self.SetText(self.GetText().replace(target, newtext))  #Whole Doc
                self.GotoPos(curpos)
                self.EndUndoAction()
            dialog.Destroy()
        else:
            self.BeginUndoAction()
            selectedtext = self.GetSelectedText()
            newselectedtext = selectedtext.replace(target, newtext)
            self.Clear()
            self.AddText(newselectedtext)
            self.EndUndoAction()


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
        rcheader1.SetDisabledBitmap(gRmbImg)
        rcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            if i == 7:#The currently open menu
                mgm = wx.MenuItem(rightclickmenu, gRmgmIDs[i-1], u'&R MGM %s You Are Here!\tCtrl+7'%str(i), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(gYahImg)
                mgm.SetBackgroundColour('#F4FAB4')
                mgm.Enable(False)
            else:
                mgm = wx.MenuItem(rightclickmenu, gRmgmIDs[i-1], u'&R MGM %s %s'%(str(i),gRmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(gMgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(rightclickmenu, ID_MMGM5, u'&M MGM 5 Macro\tCtrl+0', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(gMgmImg)
        submenu.AppendItem(mgm)
        rightclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        rightclickmenu.AppendSeparator()

        currentpackagename = u'%s' %basher.gInstallers.gPackage.GetValue()

        # > Can't be a directory or filename character...at least on windows...so
        currentpackage = wx.MenuItem(rightclickmenu, ID_CURRENTPACKAGE, u'&Current Package>>> %s' %currentpackagename, u' Current Package Name')
        # currentpackage.SetBitmap(gImgIdx['test16.png'])
        rightclickmenu.AppendItem(currentpackage)
        currentpackage.Enable(False)

        activeproject = wx.MenuItem(rightclickmenu, ID_ACTIVEPROJECT, u'&Active Project>>> %s' %basher.settings['bash.installers.wizSTC.ActiveProject'], u' Active Project')
        # activeproject.SetBitmap(gImgIdx['test16.png'])
        rightclickmenu.AppendItem(activeproject)
        activeproject.Enable(False)

        submenu = wx.Menu()
        setactiveproject = wx.MenuItem(rightclickmenu, ID_SETACTIVEPROJECTTO, u'None', u' Set Active Project To None')
        setactiveproject.SetBitmap(gImgIdx['test16.png'])
        submenu.AppendItem(setactiveproject)
        wx.EVT_MENU(rightclickmenu, ID_SETACTIVEPROJECTTO, self.OnSetActiveProjectTo)

        srcdir = u'%s'%bosh.dirs['installers']
        directories = [dirname for dirname in os.listdir(srcdir) if os.path.isdir(os.path.join(srcdir, dirname))]
        for dir in directories:
            if os.path.basename(dir) not in ['Bash','Bain Converters']:
                newid = wx.NewId()
                setactiveproject = wx.MenuItem(rightclickmenu, newid, u'%s'%dir, u' Set Active Project To %s'%dir)
                setactiveproject.SetBitmap(gImgIdx['test16.png'])
                submenu.AppendItem(setactiveproject)
                wx.EVT_MENU(rightclickmenu, newid, self.OnSetActiveProjectTo)
                # print dir
        rightclickmenu.AppendMenu(wx.NewId(), u'Set Active Project To...', submenu)

        createnewproject = wx.MenuItem(rightclickmenu, ID_CREATENEWPROJECT, u'&Create New Project...', u' Create New Project...')
        createnewproject.SetBitmap(wx.Bitmap(gImgDir + os.sep + (u'diamond_white_off_wiz.png'),p))
        rightclickmenu.AppendItem(createnewproject)

        rightclickmenu.AppendSeparator()

        # hmmm = wx.MenuItem(rightclickmenu, 9999, u'&Copy SubPackage to Active Project...Needs Label && ID', u' StatusText Description Here')
        # hmmm.SetBitmap(gImgIdx['black16.png'])
        # rightclickmenu.AppendItem(hmmm)

        # hmmm = wx.MenuItem(rightclickmenu, 9999, u'&Copy Espm to Active Project...Needs Label && ID', u' StatusText Description Here')
        # hmmm.SetBitmap(gImgIdx['black16.png'])
        # rightclickmenu.AppendItem(hmmm)

        # hmmm = wx.MenuItem(rightclickmenu, 9999, u'&Copy All to Active Project(exc. wizard)...Needs Label && ID', u' StatusText Description Here')
        # hmmm.SetBitmap(gImgIdx['black16.png'])
        # rightclickmenu.AppendItem(hmmm)

        # hmmm = wx.MenuItem(rightclickmenu, 9999, u'&Append Current Package\'s wizard.txt to Active Project\'s wipz.wiz Needs Label && ID', u' Mergify wiz')
        # hmmm.SetBitmap(gImgIdx['black16.png'])
        # rightclickmenu.AppendItem(hmmm)

        hmmm = wx.MenuItem(rightclickmenu, 9999, u'&Needs Label && ID', u' StatusText Description Here')
        hmmm.SetBitmap(gImgIdx['black16.png'])
        rightclickmenu.AppendItem(hmmm)

        #events
        for i in range(0,len(gRmgmIDs)):
            wx.EVT_MENU(rightclickmenu, gRmgmIDs[i], gRmgmDEFs[i])
        wx.EVT_MENU(rightclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        # wx.EVT_MENU(rightclickmenu, ID_CURRENTPACKAGE, self.OnPass)
        # wx.EVT_MENU(rightclickmenu, ID_ACTIVEPROJECT, self.OnPass)

        wx.EVT_MENU(rightclickmenu, ID_CREATENEWPROJECT, self.OnCreateNewProject)

        self.PopupMenu(rightclickmenu)
        rightclickmenu.Destroy()

    def OnSetActiveProjectTo(self, event):
        id =  event.GetId()
        evtobj = event.GetEventObject()
        menuitem = evtobj.FindItemById(id)
        print u'%s' %menuitem.GetItemLabel()
        basher.settings['bash.installers.wizSTC.ActiveProject'] = u'%s' %menuitem.GetItemLabel()
        basher.settings.setChanged('bash.installers.wizSTC.ActiveProject')

    def OnCreateNewProject(self, event):
        dialog = basher.CreateNewProject(None,-1,u'Create New Project')
        dialog.ShowModal()
        dialog.Destroy()

    def OnRMouseGestureMenu8(self, event):
        ''' Call the Right Mouse Gesture Menu.
        NUMPAD:8
        [7][@][9]
        [4][5][6]
        [1][2][3]
        '''
        rightclickmenu = wx.Menu()

        rcheader1 = wx.MenuItem(rightclickmenu, 0000, u'&R MGM 8 Line Operations', u'ContextMenu8')
        rcheader1.SetBackgroundColour('#000000')
        rightclickmenu.AppendItem(rcheader1)
        rcheader1.SetDisabledBitmap(gRmbImg)
        rcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            if i == 8:#The currently open menu
                mgm = wx.MenuItem(rightclickmenu, gRmgmIDs[i-1], u'&R MGM %s You Are Here!\tCtrl+8'%str(i), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(gYahImg)
                mgm.SetBackgroundColour('#F4FAB4')
                mgm.Enable(False)
            else:
                mgm = wx.MenuItem(rightclickmenu, gRmgmIDs[i-1], u'&R MGM %s %s'%(str(i),gRmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(gMgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(rightclickmenu, ID_MMGM5, u'&M MGM 5 Macro\tCtrl+0', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(gMgmImg)
        submenu.AppendItem(mgm)
        rightclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        rightclickmenu.AppendSeparator()

        newlinebefore = wx.MenuItem(rightclickmenu, ID_NEWLINEBEFORE, u'&New Line Before', u' Insert a new line before the current line.')
        newlinebefore.SetBitmap(gImgIdx['newlinebefore16.png'])
        rightclickmenu.AppendItem(newlinebefore)

        newlineafter = wx.MenuItem(rightclickmenu, ID_NEWLINEAFTER, u'&New Line After', u' Insert a new line after the current line.')
        newlineafter.SetBitmap(gImgIdx['newlineafter16.png'])
        rightclickmenu.AppendItem(newlineafter)

        cutline = wx.MenuItem(rightclickmenu, ID_CUTLINE, u'&Cut Line\tCtrl+L', u' Cut the current line to the clipboard.')
        cutline.SetBitmap(gImgIdx['cutline16.png'])
        rightclickmenu.AppendItem(cutline)

        copyline = wx.MenuItem(rightclickmenu, ID_COPYLINE, u'&Copy Line', u' Copy the current line to the clipboard.')
        copyline.SetBitmap(gImgIdx['copyline16.png'])
        rightclickmenu.AppendItem(copyline)

        deleteline = wx.MenuItem(rightclickmenu, ID_DELETELINE, u'&Delete Line\tCtrl+Shift+L', u' Delete the current line.')
        deleteline.SetBitmap(gImgIdx['deleteline16.png'])
        rightclickmenu.AppendItem(deleteline)

        deletelinecontents = wx.MenuItem(rightclickmenu, ID_DELETELINECONTENTS, u'&Delete Line Contents', u' Delete the contents of the current line.')
        deletelinecontents.SetBitmap(gImgIdx['deleteline16.png'])
        rightclickmenu.AppendItem(deletelinecontents)

        deletelineleft = wx.MenuItem(rightclickmenu, ID_DELETELINELEFT, u'&Delete Line Left\tCtrl+Shift+Back', u' Delete back from the current position to the start of the line.')
        deletelineleft.SetBitmap(gImgIdx['deletelineleft16.png'])
        rightclickmenu.AppendItem(deletelineleft)

        deletelineright = wx.MenuItem(rightclickmenu, ID_DELETELINERIGHT, u'&Delete Line Right\tCtrl+Shift+Del', u' Delete forwards from the current position to the end of the line.')
        deletelineright.SetBitmap(gImgIdx['deletelineright16.png'])
        rightclickmenu.AppendItem(deletelineright)

        selectline = wx.MenuItem(rightclickmenu, ID_SELECTLINENOEOL, u'&Select Line(without EOL)', u' Select the contents of the caret line without EOL chars.')
        selectline.SetBitmap(gImgIdx['selectline16.png'])
        rightclickmenu.AppendItem(selectline)

        duplicateline = wx.MenuItem(rightclickmenu, ID_DUPLICATELINE, u'&Duplicate Line', u' Duplicate the current line.')
        duplicateline.SetBitmap(gImgIdx['duplicateline16.png'])
        rightclickmenu.AppendItem(duplicateline)

        duplicateselectionline = wx.MenuItem(rightclickmenu, ID_DUPLICATESELECTIONLINE, u'&Duplicate Selection/Line\tCtrl+D', u' Duplicate the selection. If the selection is empty, it duplicates the line containing the caret.')
        duplicateselectionline.SetBitmap(gImgIdx['duplicateselectionline16.png'])
        rightclickmenu.AppendItem(duplicateselectionline)

        duplicatelinentimes = wx.MenuItem(rightclickmenu, ID_DUPLICATELINENTIMES, u'&Duplicate Line n Times...', u' Duplicate the current line n times.')
        duplicatelinentimes.SetBitmap(gImgIdx['duplicateselectionline16.png'])
        rightclickmenu.AppendItem(duplicatelinentimes)

        joinlines = wx.MenuItem(rightclickmenu, ID_JOINLINES, u'&Join Lines', u' Join the currently selected lines.')
        joinlines.SetBitmap(gImgIdx['joinlines16.png'])
        rightclickmenu.AppendItem(joinlines)

        splitlines = wx.MenuItem(rightclickmenu, ID_SPLITLINES, u'&Split Lines', u' Split the lines in the target into lines that are less wide than pixelWidth where possible.')
        splitlines.SetBitmap(gImgIdx['splitlines16.png'])
        rightclickmenu.AppendItem(splitlines)

        switcheroolinetranspose = wx.MenuItem(rightclickmenu, ID_LINETRANSPOSE, u'&Line Transpose\tCtrl+T', u' Switcheroo the current line with the previous.')
        switcheroolinetranspose.SetBitmap(gImgIdx['linetranspose16.png'])
        rightclickmenu.AppendItem(switcheroolinetranspose)

        movelineup = wx.MenuItem(rightclickmenu, ID_MOVELINEUP, u'&Move Line Up\tCtrl+Shift+Up', u' Move the current line up.')
        movelineup.SetBitmap(gImgIdx['arrowupbw16.png'])
        rightclickmenu.AppendItem(movelineup)

        movelinedown = wx.MenuItem(rightclickmenu, ID_MOVELINEDOWN, u'&Move Line Down\tCtrl+Shift+Down', u' Move the current line down.')
        movelinedown.SetBitmap(gImgIdx['arrowdownbw16.png'])
        rightclickmenu.AppendItem(movelinedown)

        appendselectedlineswithastring = wx.MenuItem(rightclickmenu, ID_APPENDLINESSTR, u'&Append Selected Line(s) with a string...', u' Append Selected Line(s) with a string.')
        appendselectedlineswithastring.SetBitmap(gImgIdx['append16.png'])
        rightclickmenu.AppendItem(appendselectedlineswithastring)

        removestringfromendoflines = wx.MenuItem(rightclickmenu, ID_REMOVESTRENDLINES, u'&Remove string from end of selected lines...', u' Remove a user-defined string from the end of selected lines.')
        removestringfromendoflines.SetBitmap(gImgIdx['remove16.png'])
        rightclickmenu.AppendItem(removestringfromendoflines)

        removestringfromstartoflines = wx.MenuItem(rightclickmenu, ID_REMOVESTRSTARTLINES, u'&Remove string from start of lines...', u' Remove a user-defined string from the start of selected lines.')
        removestringfromstartoflines.SetBitmap(gImgIdx['remove16.png'])
        rightclickmenu.AppendItem(removestringfromstartoflines)

        padwithspaces = wx.MenuItem(rightclickmenu, ID_PADWITHSPACES, u'&Pad With Spaces(selected lines)', u' Pad selected lines with spaces to the longest column width')
        padwithspaces.SetBitmap(gImgIdx['padwithspaces16.png'])
        rightclickmenu.AppendItem(padwithspaces)

        duplicatelineincrementfirstseqnumbers = wx.MenuItem(rightclickmenu, ID_REGEXDUPLINEINCFIRSTSEQNUM, '&Duplicate Line Increment First Seq Numbers\tF7', ' If a line contains a sequence of numbers, increment the first sequence of numbers by one. Else, duplicate the line normally.')
        duplicatelineincrementfirstseqnumbers.SetBitmap(gImgIdx['regex16.png'])
        rightclickmenu.AppendItem(duplicatelineincrementfirstseqnumbers)

        duplicatelineincrementlastseqnumbers = wx.MenuItem(rightclickmenu, ID_REGEXDUPLINEINCLASTSEQNUM, '&Duplicate Line Increment Last Seq Numbers\tF8', ' If a line contains a sequence of numbers, increment the last sequence of numbers by one. Else, duplicate the line normally.')
        duplicatelineincrementlastseqnumbers.SetBitmap(gImgIdx['regex16.png'])
        rightclickmenu.AppendItem(duplicatelineincrementlastseqnumbers)

        duplicatelineincrementfirstandlastseqnumbers = wx.MenuItem(rightclickmenu, ID_REGEXDUPLINEINCFIRSTLASTSEQNUM, '&Duplicate Line Increment First && Last Seqs Numbers\tF9', ' If a line contains a sequence of numbers, increment the first & last sequences of numbers by one. Else, duplicate the line normally.')
        duplicatelineincrementfirstandlastseqnumbers.SetBitmap(gImgIdx['regex16.png'])
        rightclickmenu.AppendItem(duplicatelineincrementfirstandlastseqnumbers)

        sort = wx.MenuItem(rightclickmenu, ID_SORT, u'&Sort Selected Lines...', u' Sort selected lines in the active document')
        sort.SetBitmap(gImgIdx['sort16.png'])
        rightclickmenu.AppendItem(sort)

        #events
        wx.EVT_MENU(rightclickmenu, ID_NEWLINEBEFORE, self.OnNewLineBefore)
        wx.EVT_MENU(rightclickmenu, ID_NEWLINEAFTER, self.OnNewLineAfter)
        wx.EVT_MENU(rightclickmenu, ID_CUTLINE, self.OnLineCut)
        wx.EVT_MENU(rightclickmenu, ID_COPYLINE, self.OnLineCopy)
        wx.EVT_MENU(rightclickmenu, ID_DELETELINE, self.OnLineDelete)
        wx.EVT_MENU(rightclickmenu, ID_DELETELINECONTENTS, self.OnDeleteLineContents)
        wx.EVT_MENU(rightclickmenu, ID_DELETELINELEFT, self.OnDeleteLineLeft)
        wx.EVT_MENU(rightclickmenu, ID_DELETELINERIGHT, self.OnDeleteLineRight)
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

        wx.EVT_MENU(rightclickmenu, ID_REGEXDUPLINEINCFIRSTSEQNUM, self.OnDuplicateLineIncrementFirstSeqNumbers)
        wx.EVT_MENU(rightclickmenu, ID_REGEXDUPLINEINCLASTSEQNUM, self.OnDuplicateLineIncrementLastSeqNumbers)
        wx.EVT_MENU(rightclickmenu, ID_REGEXDUPLINEINCFIRSTLASTSEQNUM, self.OnDuplicateLineIncrementFirstAndLastSeqNumbers)

        wx.EVT_MENU(rightclickmenu, ID_SORT, self.OnSort)

        for i in range(0,len(gRmgmIDs)):
            wx.EVT_MENU(rightclickmenu, gRmgmIDs[i], gRmgmDEFs[i])
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

    def OnDeleteLineLeft(self, event):
        ''' Delete back from the current position to the start of the line. '''
        self.DelLineLeft()

    def OnDeleteLineRight(self, event):
        ''' Delete forwards from the current position to the end of the line. '''
        self.DelLineRight()

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

    def OnDuplicateLineIncrementFirstSeqNumbers(self, event):
        ''' If a line contains a sequence of numbers, increment the first sequence of numbers by one. Else, duplicate the line normally. '''
        firstNum = re.compile(r'[0-9]+')

        string = self.GetLine(self.GetCurrentLine())
        bainsubpackagenum = firstNum.search(string)
        if bainsubpackagenum:
            next = str(int(bainsubpackagenum.group(0))+1)
            startpos, endpos = bainsubpackagenum.span(0)
            string = string[:max(endpos-len(next), startpos)] + next + string[endpos:]

        self.GotoPos(self.GetLineEndPosition(self.GetCurrentLine()))
        self.NewLine()
        self.AddText(string.rstrip())#rstrip the eol char off so the editor doesn't jump to the next line.
        self.SetFocus()
        # print next,'\n',startpos,'\n',endpos,'\n',string

    def OnDuplicateLineIncrementLastSeqNumbers(self, event):
        ''' If a line contains a sequence of numbers, increment the last sequence of numbers by one. Else, duplicate the line normally. '''
        lastNum = re.compile(r'(?:[^\d]*(\d+)[^\d]*)+')

        string = self.GetLine(self.GetCurrentLine())
        bainnexusnum = lastNum.search(string)
        if bainnexusnum:
            next = str(int(bainnexusnum.group(1))+1)
            startpos, endpos = bainnexusnum.span(1)
            string = string[:max(endpos-len(next), startpos)] + next + string[endpos:]

        self.GotoPos(self.GetLineEndPosition(self.GetCurrentLine()))
        self.NewLine()
        self.AddText(string.rstrip())#rstrip the eol char off so the editor doesn't jump to the next line.
        self.SetFocus()
        # print next,'\n',startpos,'\n',endpos,'\n',string

    def OnDuplicateLineIncrementFirstAndLastSeqNumbers(self, event):
        ''' If a line contains a sequence of numbers, increment the first and last sequences of numbers by one. Else, duplicate the line normally. '''
        firstNum = re.compile(r'[0-9]+')

        string = self.GetLine(self.GetCurrentLine())
        bainsubpackagenum = firstNum.search(string)
        if bainsubpackagenum:
            next = str(int(bainsubpackagenum.group(0))+1)
            startpos, endpos = bainsubpackagenum.span(0)
            string = string[:max(endpos-len(next), startpos)] + next + string[endpos:]

        lastNum = re.compile(r'(?:[^\d]*(\d+)[^\d]*)+')

        bainnexusnum = lastNum.search(string)
        if bainnexusnum:
            next = str(int(bainnexusnum.group(1))+1)
            startpos, endpos = bainnexusnum.span(1)
            string = string[:max(endpos-len(next), startpos)] + next + string[endpos:]

        self.GotoPos(self.GetLineEndPosition(self.GetCurrentLine()))
        self.NewLine()
        self.AddText(string.rstrip())#rstrip the eol char off so the editor doesn't jump to the next line.
        self.SetFocus()
        # print next,'\n',startpos,'\n',endpos,'\n',string

    def OnSort(self, event):
        ''' Call a dialog with various options to sort the selected text lines. '''
        self.BeginUndoAction()
        linestring = str(self.GetSelectedText())
        linestringlist = linestring.split('\n')
        length = len(linestringlist)

        if self.GetSelectionStart() == self.GetSelectionEnd():
            wx.MessageBox(u'No Text Selected!', u'Sort Error', wx.OK|wx.ICON_ERROR)
        else:
            dialog = wx.SingleChoiceDialog(self, u'How do you want to sort the selection?', u'Sort...',
                    [u'Ascending Case Sensitive', u'Ascending Case insensitive', u'Descending Case Sensitive', u'Descending Case insensitive', u'Randomly'],
                    wx.CHOICEDLG_STYLE)

            if dialog.ShowModal() == wx.ID_OK:
                getsel = self.GetSelection()
                if dialog.GetStringSelection() == u'Ascending Case Sensitive':
                    linestringlist.sort()
                    for i in range(0,length-1):
                        self.ReplaceSelection(linestringlist[i] + u'\n')
                    self.ReplaceSelection(linestringlist[length-1])
                elif dialog.GetStringSelection() == u'Ascending Case insensitive':
                    linestringlist.sort(key=str.lower)
                    for i in range(0,length-1):
                        self.ReplaceSelection(linestringlist[i] + u'\n')
                    self.ReplaceSelection(linestringlist[length-1])
                elif dialog.GetStringSelection() == u'Descending Case Sensitive':
                    linestringlist.sort()
                    linestringlist.reverse()
                    for i in range(0,length-1):
                        self.ReplaceSelection(linestringlist[i] + u'\n')
                    self.ReplaceSelection(linestringlist[length-1])
                elif dialog.GetStringSelection() == u'Descending Case insensitive':
                    linestringlist.sort(key=str.lower)
                    linestringlist.reverse()
                    for i in range(0,length-1):
                        self.ReplaceSelection(linestringlist[i] + u'\n')
                    self.ReplaceSelection(linestringlist[length-1])
                elif dialog.GetStringSelection() == u'Randomly':
                    r = []
                    for i in range(self.LineFromPosition(self.GetSelectionStart()),self.LineFromPosition(self.GetSelectionEnd()) + 1):
                        r.append(self.GetLine(i).rstrip())
                    random.shuffle(r)
                    self.DeleteBack()
                    for line in r:
                        self.AddText(line + u'\n')
                    self.DeleteBack()
                self.SetSelection(getsel[1],getsel[0])#Keep the text selected afterwards retaining caret pos

            dialog.Destroy()
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
        rcheader1.SetDisabledBitmap(gRmbImg)
        rcheader1.Enable(False)

        submenu = wx.Menu()
        for i in range(1,10):
            if i == 9:#The currently open menu
                mgm = wx.MenuItem(rightclickmenu, gRmgmIDs[i-1], u'&R MGM %s You Are Here!\tCtrl+9'%str(i), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(gYahImg)
                mgm.SetBackgroundColour('#F4FAB4')
                mgm.Enable(False)
            else:
                mgm = wx.MenuItem(rightclickmenu, gRmgmIDs[i-1], u'&R MGM %s %s'%(str(i),gRmgmLABELs[i-1]), u' Call Mouse Gesture Menu %s'%str(i))
                mgm.SetBitmap(gMgmImg)
            submenu.AppendItem(mgm)
        submenu.AppendSeparator()
        mgm = wx.MenuItem(rightclickmenu, ID_MMGM5, u'&M MGM 5 Macro\tCtrl+0', u' Call M Mouse Gesture Menu 5')
        mgm.SetBitmap(gMgmImg)
        submenu.AppendItem(mgm)
        rightclickmenu.AppendMenu(wx.NewId(), u'Mouse Gesture Menus', submenu)

        rightclickmenu.AppendSeparator()

        if basher.settings['bash.installers.wizSTC.ReadOnly'] == 1: IO = u'Off'
        else: IO = u'On'
        togglereadonly = wx.MenuItem(rightclickmenu, ID_TOGGLEREADONLY, u'&Toggle Read Only Mode\t%s'%IO, u' Toggle Read Only Mode')
        if basher.settings['bash.installers.wizSTC.ReadOnly'] == 1:
            togglereadonly.SetBitmap(gImgIdx['readonlymodeon16.png'])
        else:
            togglereadonly.SetBitmap(gImgIdx['readonlymodeoff16.png'])
        rightclickmenu.AppendItem(togglereadonly)

        if basher.settings['bash.installers.wizSTC.ViewWhiteSpace'] == 1: IO = u'On*'
        elif basher.settings['bash.installers.wizSTC.ViewWhiteSpace'] == 2: IO = u'Off'
        else: IO = u'On'
        togglewhitespace = wx.MenuItem(rightclickmenu, ID_TOGGLEWHITESPACE, u'&Toggle Whitespace\t%s'%IO, u' Toggle Whitespace')
        togglewhitespace.SetBitmap(gImgIdx['showwhitespace16.png'])
        rightclickmenu.AppendItem(togglewhitespace)

        if basher.settings['bash.installers.wizSTC.IndentationGuides'] == 1: IO = u'Off'
        else: IO = u'On'
        toggleindentguides = wx.MenuItem(rightclickmenu, ID_TOGGLEINDENTGUIDES, u'&Toggle Indent Guides\t%s'%IO, u' Toggle Indent Guides On/Off')
        toggleindentguides.SetBitmap(gImgIdx['showindentationguide16.png'])
        rightclickmenu.AppendItem(toggleindentguides)

        if basher.settings['bash.installers.wizSTC.WordWrap'] == 1: IO = u'Off'
        else: IO = u'On'
        togglewordwrap = wx.MenuItem(rightclickmenu, ID_TOGGLEWORDWRAP, u'&Toggle Wordwrap\t%s'%IO, u' Toggle Wordwrap On/Off')
        togglewordwrap.SetBitmap(gImgIdx['wordwrap16.png'])
        rightclickmenu.AppendItem(togglewordwrap)

        if basher.settings['bash.installers.wizSTC.CaretLineVisible'] == 1: IO = u'Off'
        else: IO = u'On'
        togglehighlightselectedline = wx.MenuItem(rightclickmenu, ID_TOGGLELINEHIGHLIGHT, u'&Toggle Highlight Selected Line\t%s'%IO, u' Toggle Highlight Selected Line')
        togglehighlightselectedline.SetBitmap(gImgIdx['highlightcurrentline16.png'])
        rightclickmenu.AppendItem(togglehighlightselectedline)

        if basher.settings['bash.installers.wizSTC.ViewEOL'] == 1: IO = u'Off'
        else: IO = u'On'
        toggleeolview = wx.MenuItem(rightclickmenu, ID_TOGGLEEOLVIEW, u'&Toggle EOL View\t%s'%IO, u' Toggle Show/Hide End of line characters ')
        toggleeolview.SetBitmap(gImgIdx['eollf16.png'])
        rightclickmenu.AppendItem(toggleeolview)

        if basher.settings['bash.installers.wizSTC.BackSpaceUnIndents'] == 1: IO = u'Off'
        else: IO = u'On'
        togglebackspaceunindents = wx.MenuItem(rightclickmenu, ID_BACKSPACEUNINDENTS, u'&Toggle BackSpace Unindents\t%s'%IO, u' Toggle BackSpace Unindents')
        togglebackspaceunindents.SetBitmap(gImgIdx['backspaceunindents16.png'])
        rightclickmenu.AppendItem(togglebackspaceunindents)

        if basher.settings['bash.installers.wizSTC.BraceCompletion'] == 1: IO = u'Off'
        else: IO = u'On'
        togglebracecompletion = wx.MenuItem(rightclickmenu, ID_BRACECOMPLETION, u'&Toggle Brace Completion \'"({[]})"\'\t%s'%IO, u' Toggle Brace Completion \'"({[]})"\'')
        togglebracecompletion.SetBitmap(gImgIdx['bracecompletion16.png'])
        rightclickmenu.AppendItem(togglebracecompletion)

        if basher.settings['bash.installers.wizSTC.AutoIndentation'] == 1: IO = u'Off'
        else: IO = u'On'
        toggleautoindentation = wx.MenuItem(rightclickmenu, ID_AUTOINDENTATION, u'&Toggle Auto-Indentation\t%s'%IO, u' Toggle Auto-Indentation')
        toggleautoindentation.SetBitmap(gImgIdx['autoindentation16.png'])
        rightclickmenu.AppendItem(toggleautoindentation)

        if basher.settings['bash.installers.wizSTC.LongLineEdgeMode'] == 1: IO = u'=On'
        elif basher.settings['bash.installers.wizSTC.LongLineEdgeMode'] == 2: IO = u'Off'
        else: IO = u'|On'
        toggleedgecolumn = wx.MenuItem(rightclickmenu, ID_EDGECOLUMN, u'&Toggle Edge Column\t%s'%IO, u' Toggle Edge Column')
        toggleedgecolumn.SetBitmap(gImgIdx['edgecolumn16.png'])
        rightclickmenu.AppendItem(toggleedgecolumn)
        
        submenu_longlineedge = wx.Menu()
        lle = basher.settings['bash.installers.wizSTC.LongLineEdge']
        for i in range(0,121):
            newid = wx.NewId()
            setlonglineedge = wx.MenuItem(rightclickmenu, newid, u'%s'%i, u' Set Long Line Edge To %s'%i)
            if lle == i:
                setlonglineedge.SetBitmap(gChkImg)
            submenu_longlineedge.AppendItem(setlonglineedge)
            wx.EVT_MENU(rightclickmenu, newid, self.OnLongLineEdge)
        rightclickmenu.AppendMenu(wx.NewId(), u'Set Long Line Edge\t%s'%lle, submenu_longlineedge)
        
        if basher.settings['bash.installers.wizSTC.ScrollingPastLastLine'] == 1: IO = u'On'
        else: IO = u'Off'
        togglescrollpastlastline = wx.MenuItem(rightclickmenu, ID_SCROLLPASTLASTLINE, u'&Toggle Scroll Past Last Line\t%s'%IO, u' Toggle Scroll Past Last Line')
        togglescrollpastlastline.SetBitmap(gImgIdx['scrollpastlastline16.png'])
        rightclickmenu.AppendItem(togglescrollpastlastline)
        
        if basher.settings['bash.installers.wizSTC.IntelliWiz'] == 1: IO = u'Off'
        else: IO = u'On'
        toggleintelliwiz = wx.MenuItem(rightclickmenu, ID_INTELLIWIZ, u'&Toggle IntelliWiz\t%s'%IO, u' Toggle IntelliWiz')
        toggleintelliwiz.SetBitmap(gImgIdx['yingyang16.png'])
        rightclickmenu.AppendItem(toggleintelliwiz)

        if basher.settings['bash.installers.wizSTC.IntelliCallTip'] == 1: IO = u'Off'
        else: IO = u'On'
        toggleintellicalltip = wx.MenuItem(rightclickmenu, ID_INTELLICALLTIP, u'&Toggle IntelliCallTip\t%s'%IO, u' Toggle IntelliCallTip')
        toggleintellicalltip.SetBitmap(gImgIdx['yingyang16.png'])
        rightclickmenu.AppendItem(toggleintellicalltip)

        rightclickmenu.AppendSeparator()

        submenu_font = wx.Menu()

        usecustomfont = wx.MenuItem(rightclickmenu, ID_USECUSTOMFONT, u'&Use Custom Font', u' Use Custom Font', kind = wx.ITEM_CHECK)
        usecustomfont.SetBitmap(gChkImg)
        submenu_font.AppendItem(usecustomfont)
        if basher.settings['bash.installers.wizSTC.UseCustomFont'] == 1: usecustomfont.Check(True)

        usemonofont = wx.MenuItem(rightclickmenu, ID_USEMONOFONT, u'&Use Mono Font (%(mono)s)'%faces, u' Use Mono Font', kind = wx.ITEM_CHECK)
        usemonofont.SetBitmap(gChkImg)
        submenu_font.AppendItem(usemonofont)
        if basher.settings['bash.installers.wizSTC.UseCustomFont'] == 0: usemonofont.Check(True)

        submenu_font.AppendSeparator()
        usercustomfontface = basher.settings['bash.installers.wizSTC.UserCustomFontFace']
        usercustomfont = wx.MenuItem(rightclickmenu, wx.NewId(), u'&%s'%usercustomfontface, u' User Custom Font')
        # font = usercustomfont.GetFont()
        # usercustomfont.SetItemLabel(u'%s'%usercustomfontface)
        # usercustomfont.SetFont(font)
        usercustomfont.SetFont(wx.Font(12, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, u'%s'%usercustomfontface))
        usercustomfont.SetBitmap(gImgIdx['font16.png'])
        submenu_font.AppendItem(usercustomfont)
        usercustomfont.Enable(False)

        setcustomfont = wx.MenuItem(rightclickmenu, ID_SETCUSTOMFONT, u'&Set Custom Font...', u' Set Custom Font')
        setcustomfont.SetBitmap(gImgIdx['font24.png'])
        submenu_font.AppendItem(setcustomfont)
        rightclickmenu.AppendMenu(wx.NewId(), u'Font', submenu_font)


        submenu_codefolder = wx.Menu()
        self.folderIDs = [ID_CODEFOLDERSTYLE1,ID_CODEFOLDERSTYLE2,ID_CODEFOLDERSTYLE3,ID_CODEFOLDERSTYLE4,ID_CODEFOLDERSTYLE5,ID_CODEFOLDERSTYLE6]
        self.folderLABELs = ['Folder Margin Style 1','Folder Margin Style 2','Folder Margin Style 3','Folder Margin Style 4','Folder Margin Style 5','Folder Margin Style 6']
        for i in range(1,len(self.folderIDs)+1):
            folder = wx.MenuItem(rightclickmenu, self.folderIDs[i-1], u'&%s'%self.folderLABELs[i-1], u' %s'%self.folderLABELs[i-1], kind = wx.ITEM_CHECK)
            folder.SetBitmap(gChkImg)
            submenu_codefolder.AppendItem(folder)
            if basher.settings['bash.installers.wizSTC.FolderMarginStyle'] == i: folder.Check(True)
        submenu_codefolder.AppendSeparator()
        togglecodefoldstyle = wx.MenuItem(rightclickmenu, ID_TOGGLECODEFOLDERSTYLE, u'&Toggle Folder Margin Style\tF11', u' Toggle Folder Margin Style')

        foldImgList = [u'foldermarginstyle_arrows_24.png',u'foldermarginstyle_plusminus_24.png',u'foldermarginstyle_circletree_24.png',u'foldermarginstyle_boxtree_24.png',u'foldermarginstyle_indentdots_24.png',u'foldermarginstyle_shortarrowcircle_24.png']
        fms = basher.settings['bash.installers.wizSTC.FolderMarginStyle']
        if fms == len(foldImgList):
            togglecodefoldstyle.SetBitmap(wx.Bitmap(gImgStcDir + os.sep + foldImgList[0],p))
        else:
            togglecodefoldstyle.SetBitmap(wx.Bitmap(gImgStcDir + os.sep + foldImgList[fms],p))
        submenu_codefolder.AppendItem(togglecodefoldstyle)
        rightclickmenu.AppendMenu(wx.NewId(), u'Folder Margin Style', submenu_codefolder)

        submenu_themes = wx.Menu()
        self.themeIDs = [ID_THEMENONE,ID_THEMEDEFAULT,ID_THEMECONSOLE,ID_THEMEOBSIDIAN,ID_THEMEZENBURN,ID_THEMEMONOKAI,ID_THEMEDEEPSPACE,ID_THEMEGREENSIDEUP,ID_THEMETWILIGHT,ID_THEMEULIPAD,ID_THEMEHELLOKITTY,ID_THEMEVIBRANTINK,ID_THEMEBIRDSOFPARIDISE,ID_THEMEBLACKLIGHT,ID_THEMENOTEBOOK]
        self.themeLABELs = ['No Theme','Default','Console','Obsidian','Zenburn','Monokai','Deep Space','Green Side Up','Twilight','UliPad','Hello Kitty','Vibrant Ink','Birds Of Paridise','BlackLight','Notebook']
        for i in range(1,len(self.themeIDs)+1):
            theme = wx.MenuItem(rightclickmenu, self.themeIDs[i-1], u'&%s'%self.themeLABELs[i-1], u' %s Theme'%self.themeLABELs[i-1], kind = wx.ITEM_CHECK)
            theme.SetBitmap(gChkImg)
            submenu_themes.AppendItem(theme)
            if basher.settings['bash.installers.wizSTC.ThemeOnStartup'] == u'%s' %self.themeLABELs[i-1]: theme.Check(True)
        submenu_themes.AppendSeparator()
        togglethemes = wx.MenuItem(rightclickmenu, ID_TOGGLETHEMES, u'&Toggle Editor Themes\tF12', u' Toggle Editor Themes')
        togglethemes.SetBitmap(gImgIdx['toggletheme24.png'])
        submenu_themes.AppendItem(togglethemes)
        rightclickmenu.AppendMenu(wx.NewId(), u'Themes', submenu_themes)

        #events
        wx.EVT_MENU(rightclickmenu, ID_CODEFOLDERSTYLE1, self.OnFolderStyleSetting1)
        wx.EVT_MENU(rightclickmenu, ID_CODEFOLDERSTYLE2, self.OnFolderStyleSetting2)
        wx.EVT_MENU(rightclickmenu, ID_CODEFOLDERSTYLE3, self.OnFolderStyleSetting3)
        wx.EVT_MENU(rightclickmenu, ID_CODEFOLDERSTYLE4, self.OnFolderStyleSetting4)
        wx.EVT_MENU(rightclickmenu, ID_CODEFOLDERSTYLE5, self.OnFolderStyleSetting5)
        wx.EVT_MENU(rightclickmenu, ID_CODEFOLDERSTYLE6, self.OnFolderStyleSetting6)



        wx.EVT_MENU(rightclickmenu, ID_TOGGLECODEFOLDERSTYLE, self.OnToggleFolderMarginStyle)


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

        wx.EVT_MENU(rightclickmenu, ID_TOGGLEREADONLY, self.OnReadOnly)
        wx.EVT_MENU(rightclickmenu, ID_TOGGLEWHITESPACE, self.OnViewWhitespace)
        wx.EVT_MENU(rightclickmenu, ID_TOGGLEINDENTGUIDES, self.OnShowIndentationGuides)
        wx.EVT_MENU(rightclickmenu, ID_TOGGLEWORDWRAP, self.OnWordwrap)
        wx.EVT_MENU(rightclickmenu, ID_TOGGLELINEHIGHLIGHT, self.OnHighlightSelectedLine)
        wx.EVT_MENU(rightclickmenu, ID_TOGGLEEOLVIEW, self.OnShowEOL)
        wx.EVT_MENU(rightclickmenu, ID_BACKSPACEUNINDENTS, self.OnBackSpaceUnindents)
        wx.EVT_MENU(rightclickmenu, ID_BRACECOMPLETION, self.OnBraceCompletion)
        wx.EVT_MENU(rightclickmenu, ID_AUTOINDENTATION, self.OnAutoIndentation)
        wx.EVT_MENU(rightclickmenu, ID_EDGECOLUMN, self.OnEdgeColumn)
        wx.EVT_MENU(rightclickmenu, ID_SCROLLPASTLASTLINE, self.OnScrollPastLastLine)
        wx.EVT_MENU(rightclickmenu, ID_INTELLIWIZ, self.OnIntelliWiz)
        wx.EVT_MENU(rightclickmenu, ID_INTELLICALLTIP, self.OnIntelliCallTip)

        for i in range(0,len(gRmgmIDs)):
            wx.EVT_MENU(rightclickmenu, gRmgmIDs[i], gRmgmDEFs[i])
        wx.EVT_MENU(rightclickmenu, ID_MMGM5, self.OnMMouseGestureMenuNone)

        self.PopupMenu(rightclickmenu)
        rightclickmenu.Destroy()

    def OnReadOnly(self, event):
        '''Toggle Read-Only Mode On/Off for the current document. '''
        if self.GetReadOnly() == 1: #In read-only mode? 1 For Yes, 0 for No.
            self.SetReadOnly(False) #Set to read write.
            basher.settings['bash.installers.wizSTC.ReadOnly'] = 0
        elif self.GetReadOnly() == 0:
            self.SetReadOnly(True)  #Set to read only.
            basher.settings['bash.installers.wizSTC.ReadOnly'] = 1
        basher.settings.setChanged('bash.installers.wizSTC.ReadOnly')

    def OnReadOnlyModifyAttempt(self, event):
        ''' Ring the bell to notify the user that the document is in Read-Only Mode '''
        wx.Bell()
        # print ('Read-Only Mode: On!')

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
        ''' Toggle the indentation guides in the editor On/Off '''
        if self.GetIndentationGuides() == True:
            self.SetIndentationGuides(False)
            basher.settings['bash.installers.wizSTC.IndentationGuides'] = 0
        else:
            self.SetIndentationGuides(True)
            basher.settings['bash.installers.wizSTC.IndentationGuides'] = 1
        basher.settings.setChanged('bash.installers.wizSTC.IndentationGuides')

    def OnWordwrap(self, event):
        ''' Toggle Wordwrapping of the document in the editor On/Off '''
        if self.GetWrapMode() == True:
            self.SetWrapMode(False)
            basher.settings['bash.installers.wizSTC.WordWrap'] = 0
        else:
            self.SetWrapMode(True)
            basher.settings['bash.installers.wizSTC.WordWrap'] = 1
        basher.settings.setChanged('bash.installers.wizSTC.WordWrap')

    def OnHighlightSelectedLine(self, event):
        ''' Toggle highlighting the currently selected line(the one with the caret) in the editor On/Off '''
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

    def OnLongLineEdge(self, event):
        ''' Set the long line edge column number. '''
        id =  event.GetId()
        evtobj = event.GetEventObject()
        menuitem = evtobj.FindItemById(id)
        self.SetEdgeColumn(int(menuitem.GetItemLabel()))
        basher.settings['bash.installers.wizSTC.LongLineEdge'] = int(menuitem.GetItemLabel())
        basher.settings.setChanged('bash.installers.wizSTC.LongLineEdge')

    def OnScrollPastLastLine(self, event):
        ''' Toggle scrolling past last line on and off. '''
        sl = basher.settings['bash.installers.wizSTC.ScrollingPastLastLine']
        if sl == 1:
            self.SetEndAtLastLine(0)
            basher.settings['bash.installers.wizSTC.ScrollingPastLastLine'] = 0
        elif sl == 0:
            self.SetEndAtLastLine(1)
            basher.settings['bash.installers.wizSTC.ScrollingPastLastLine'] = 1
        basher.settings.setChanged('bash.installers.wizSTC.ScrollingPastLastLine')
            
    def OnIntelliWiz(self, event):
        ''' Toggle auto-completion IntelliWiz on and off. '''
        iw = basher.settings['bash.installers.wizSTC.IntelliWiz']
        if iw == 1:
            basher.settings['bash.installers.wizSTC.IntelliWiz'] = 0
        elif iw == 0:
            basher.settings['bash.installers.wizSTC.IntelliWiz'] = 1
        basher.settings.setChanged('bash.installers.wizSTC.IntelliWiz')

    def OnIntelliCallTip(self, event):
        ''' Toggle auto-completion IntelliCallTip on and off. '''
        ic = basher.settings['bash.installers.wizSTC.IntelliCallTip']
        if ic == 1:
            basher.settings['bash.installers.wizSTC.IntelliCallTip'] = 0
        elif ic == 0:
            basher.settings['bash.installers.wizSTC.IntelliCallTip'] = 1
        basher.settings.setChanged('bash.installers.wizSTC.IntelliCallTip')

    def OnChooseFont(self, event):
        # wx.FONTENCODING_SYSTEM        system default
        # wx.FONTENCODING_DEFAULT       current default encoding
        # wx.FONTENCODING_ISO8859_1     West European (Latin1)
        # wx.FONTENCODING_ISO8859_2     Central and East European (Latin2)
        # wx.FONTENCODING_ISO8859_3     Esperanto (Latin3)
        # wx.FONTENCODING_ISO8859_4     Baltic (old) (Latin4)
        # wx.FONTENCODING_ISO8859_5     Cyrillic
        # wx.FONTENCODING_ISO8859_6     Arabic
        # wx.FONTENCODING_ISO8859_7     Greek
        # wx.FONTENCODING_ISO8859_8     Hebrew
        # wx.FONTENCODING_ISO8859_9     Turkish (Latin5)
        # wx.FONTENCODING_ISO8859_10    Variation of Latin4 (Latin6)
        # wx.FONTENCODING_ISO8859_11    Thai
        # wx.FONTENCODING_ISO8859_12    doesn't exist currently, but put it here anyhow to make all ISO8859 consecutive numbers
        # wx.FONTENCODING_ISO8859_13    Baltic (Latin7)
        # wx.FONTENCODING_ISO8859_14    Latin8
        # wx.FONTENCODING_ISO8859_15    Latin9 (a.k.a. Latin0, includes euro)
        # wx.FONTENCODING_KOI8          Cyrillic charset
        # wx.FONTENCODING_ALTERNATIVE   same as MS-DOS CP866
        # wx.FONTENCODING_BULGARIAN     used under Linux in Bulgaria
        # wx.FONTENCODING_CP437         original MS-DOS codepage
        # wx.FONTENCODING_CP850         CP437 merged with Latin1
        # wx.FONTENCODING_CP852         CP437 merged with Latin2
        # wx.FONTENCODING_CP855         another cyrillic encoding
        # wx.FONTENCODING_CP866         and another one
        # wx.FONTENCODING_CP874         WinThai
        # wx.FONTENCODING_CP1250        WinLatin2
        # wx.FONTENCODING_CP1251        WinCyrillic
        # wx.FONTENCODING_CP1252        WinLatin1
        # wx.FONTENCODING_CP1253        WinGreek (8859-7)
        # wx.FONTENCODING_CP1254        WinTurkish
        # wx.FONTENCODING_CP1255        WinHebrew
        # wx.FONTENCODING_CP1256        WinArabic
        # wx.FONTENCODING_CP1257        WinBaltic (same as Latin 7)
        # wx.FONTENCODING_UTF7          UTF-7 Unicode encoding
        # wx.FONTENCODING_UTF8          UTF-8 Unicode encoding
                                           #pointSize,   family,   style,    weight, underline, face, encoding)
        default_font = wx.Font(int('%(size)d' %faces), wx.SWISS, wx.NORMAL, wx.NORMAL, False, '%(mono)s' %faces, wx.FONTENCODING_DEFAULT)
        fontdata = wx.FontData()
        if sys.platform == 'win32':
            fontdata.EnableEffects(True)
        fontdata.SetAllowSymbols(True)
        fontdata.SetInitialFont(default_font)
        fontdata.SetRange(8, 72)
        fontdata.SetShowHelp(True)
        fontdata.SetColour('Black')#WorksXP:Black, Gray, Green=Lime, Red, Blue, Yellow
        #DontWorkXP:Olive,Navy,Purple,Teal,Silver,Lime,Fuchsia,Aqua

        dialog = wx.FontDialog(None, fontdata)
        dialog.Centre()
        dialog.GetFontData().SetInitialFont(default_font)

        if dialog.ShowModal() == wx.ID_OK:
            data = dialog.GetFontData()
            if sys.platform == 'win32':
                data.EnableEffects(True)
            font = data.GetChosenFont()
            self.SetForegroundColour(data.GetColour())
            self.SetFont(font)
            # optional info ...
            s1 = '\n colour     --> ' + str(data.GetColour().Get())
            s2 = '\n pointsize  --> ' + str(font.GetPointSize())
            s3 = '\n family     --> ' + font.GetFamilyString()
            s4 = '\n style      --> ' + font.GetStyleString()
            s5 = '\n weight     --> ' + font.GetWeightString()
            s6 = '\n face       --> ' + font.GetFaceName()
            s7 = '\n underlined --> ' + str(font.GetUnderlined())
            s8 = '\n encoding   --> ' + str(font.GetEncoding())
            s9 = '\n isfixedwidth --> ' + str(font.IsFixedWidth())
            s = s1+s2+s3+s4+s5+s6+s7+s8+s9
            print s
            # self.label.SetLabel(s)
            # self.SetLabel(s)
            # self.StyleSetFont(-1, s)#int styleNum, Font font



            self.StyleSetFaceName(stc.STC_STYLE_DEFAULT, font.GetFaceName()) # Set the font of a style.(int style, String fontName)
            # self.StyleSetFaceName(stc.STC_STYLE_LINENUMBER, font.GetFaceName())

            for stylespec in (stc.STC_P_DEFAULT,      stc.STC_P_COMMENTLINE, stc.STC_P_NUMBER,   stc.STC_P_STRING,
                              stc.STC_P_CHARACTER,    stc.STC_P_WORD,        stc.STC_P_TRIPLE,   stc.STC_P_TRIPLEDOUBLE,
                              stc.STC_P_CLASSNAME,    stc.STC_P_DEFNAME,     stc.STC_P_OPERATOR, stc.STC_P_IDENTIFIER,
                              stc.STC_P_COMMENTBLOCK, stc.STC_P_STRINGEOL):
                self.StyleSetFaceName(   stylespec, font.GetFaceName())
                self.StyleSetSize(       stylespec, font.GetPointSize())
                if font.GetStyleString() == 'wxITALIC':
                    self.StyleSetItalic( stylespec, True)
                else:
                    self.StyleSetItalic( stylespec, False)
                if font.GetWeightString() == 'wxBOLD':
                    self.StyleSetBold(   stylespec, True)
                else:
                    self.StyleSetBold(   stylespec, False)
                # self.StyleSetForeground( stylespec, data.GetColour().Get())
                # self.StyleSetForeground( stylespec, '#FFAA00')
                # self.StyleSetBackground( stylespec, data.GetColour().Get())
                self.StyleSetEOLFilled( stylespec, True)
                self.StyleSetUnderline( stylespec, font.GetUnderlined())
                # self.StyleResetDefault()


            # self.StyleSetFaceName(stc.STC_P_WORD, 'Daedric')    # Set the font of a style.(int style, String fontName)

        dialog.Destroy()

        # print ('OnFont - This needs work with the STC version...')


    def OnSetFolderMarginStyle(self, event):#Called after STC is initialised MainWindow Initial Startup. Not sure why but calling it here in the class causes the fold symbols to not work quite properly at startup...
        ''' Setup of fold margin colors and styles before calling on of the OnFolderMarginStyle# functions. '''
        tos = basher.settings['bash.installers.wizSTC.ThemeOnStartup']
        fms = basher.settings['bash.installers.wizSTC.FolderMarginStyle']
        if fms in [1,2,5,6]:
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

            if   fms == 1: self.OnFolderMarginStyle1(event, Color1, Color2)
            elif fms == 2: self.OnFolderMarginStyle2(event, Color1, Color2)
            elif fms == 5: self.OnFolderMarginStyle5(event, Color1, Color2)
            elif fms == 6: self.OnFolderMarginStyle6(event, Color1, Color2)

        elif fms in [3,4]:
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

    def OnFolderStyleSetting1(self, event):
        basher.settings['bash.installers.wizSTC.FolderMarginStyle'] = 1
        basher.settings.setChanged('bash.installers.wizSTC.FolderMarginStyle')
        self.OnSetFolderMarginStyle(self)
    def OnFolderStyleSetting2(self, event):
        basher.settings['bash.installers.wizSTC.FolderMarginStyle'] = 2
        basher.settings.setChanged('bash.installers.wizSTC.FolderMarginStyle')
        self.OnSetFolderMarginStyle(self)
    def OnFolderStyleSetting3(self, event):
        basher.settings['bash.installers.wizSTC.FolderMarginStyle'] = 3
        basher.settings.setChanged('bash.installers.wizSTC.FolderMarginStyle')
        self.OnSetFolderMarginStyle(self)
    def OnFolderStyleSetting4(self, event):
        basher.settings['bash.installers.wizSTC.FolderMarginStyle'] = 4
        basher.settings.setChanged('bash.installers.wizSTC.FolderMarginStyle')
        self.OnSetFolderMarginStyle(self)
    def OnFolderStyleSetting5(self, event):
        basher.settings['bash.installers.wizSTC.FolderMarginStyle'] = 5
        basher.settings.setChanged('bash.installers.wizSTC.FolderMarginStyle')
        self.OnSetFolderMarginStyle(self)
    def OnFolderStyleSetting6(self, event):
        basher.settings['bash.installers.wizSTC.FolderMarginStyle'] = 6
        basher.settings.setChanged('bash.installers.wizSTC.FolderMarginStyle')
        self.OnSetFolderMarginStyle(self)
    def OnFolderMarginStyle1(self, event, Color1, Color2):
        ''' Arrow pointing right for contracted folders, arrow pointing down for expanded. '''
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_ARROWDOWN, Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_ARROW,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_EMPTY,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_EMPTY,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_EMPTY,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_EMPTY,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_EMPTY,     Color1 , Color2)
    def OnFolderMarginStyle2(self, event, Color1, Color2):
        ''' Plus for contracted folders, minus for expanded. '''
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_MINUS, Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_PLUS,  Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_EMPTY, Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_EMPTY, Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_EMPTY, Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_EMPTY, Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_EMPTY, Color1 , Color2)
    def OnFolderMarginStyle3(self, event, Color1, Color2):
        ''' Like a flattened tree control using circular headers and curved joins. '''
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_CIRCLEMINUS,          Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_CIRCLEPLUS,           Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_VLINE,                Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_LCORNERCURVE,         Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_CIRCLEPLUSCONNECTED,  Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_CIRCLEMINUSCONNECTED, Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNERCURVE,         Color1, Color2)
    def OnFolderMarginStyle4(self, event, Color1, Color2):
        ''' Like a flattened tree control using square headers. '''
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_BOXMINUS,          Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_BOXPLUS,           Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_VLINE,             Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_LCORNER,           Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_BOXPLUSCONNECTED,  Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_BOXMINUSCONNECTED, Color1, Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNER,           Color1, Color2)
    def OnFolderMarginStyle5(self, event, Color1, Color2):
        ''' Arrows >>> pointing right for contracted folders, dotdotdot ... for expanded. '''
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_ARROWS,    Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_DOTDOTDOT, Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_EMPTY,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_EMPTY,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_EMPTY,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_EMPTY,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_EMPTY,     Color1 , Color2)
    def OnFolderMarginStyle6(self, event, Color1, Color2):
        ''' Short arrow -> pointing right for contracted folders, circle ... for expanded. '''
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_SHORTARROW, Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_CIRCLE,     Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_EMPTY,      Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_EMPTY,      Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_EMPTY,      Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_EMPTY,      Color1 , Color2)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_EMPTY,      Color1 , Color2)
    def OnToggleFolderMarginStyle(self, event):
        ''' '''
        fms = basher.settings['bash.installers.wizSTC.FolderMarginStyle']
        if   fms == 1: self.OnFolderStyleSetting2(event)
        elif fms == 2: self.OnFolderStyleSetting3(event)
        elif fms == 3: self.OnFolderStyleSetting4(event)
        elif fms == 4: self.OnFolderStyleSetting5(event)
        elif fms == 5: self.OnFolderStyleSetting6(event)
        elif fms == 6: self.OnFolderStyleSetting1(event)

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
        self.MarkerDefineBitmap(1, gImgIdx['bookmark16.png'])
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
        self.MarkerDefineBitmap(1, gImgIdx['bookmark16.png'])
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
        self.MarkerDefineBitmap(1, gImgIdx['bookmark16.png'])
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
        self.MarkerDefineBitmap(1, gImgIdx['bookmark16.png'])
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
        self.MarkerDefineBitmap(1, gImgIdx['bookmark16.png'])
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
        self.MarkerDefineBitmap(1, gImgIdx['bookmark16.png'])
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
        self.MarkerDefineBitmap(1, gImgIdx['bookmark16.png'])
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
        self.MarkerDefineBitmap(1, gImgIdx['bookmark16.png'])
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
        self.MarkerDefineBitmap(1, gImgIdx['bookmark16.png'])
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
        self.MarkerDefineBitmap(1, gImgIdx['bookmark16.png'])
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
        self.MarkerDefineBitmap(1, gImgIdx['bookmark16.png'])
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
        self.MarkerDefineBitmap(1, gImgIdx['bookmark16.png'])
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
        self.MarkerDefineBitmap(1, gImgIdx['bookmark16.png'])
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
        self.MarkerDefineBitmap(1, gImgIdx['bookmarkblacklight16.png'])
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
        self.MarkerDefineBitmap(1, gImgIdx['bookmark16.png'])
        for i in range(0,stc.STC_INDIC_MAX + 1): self.IndicatorSetForeground(i,'#FF0000')
        if self.GetMarginWidth(3) == 0: self.SetMarginWidth(3, 16)
        # print('Notebook Theme')


    def OnFindReplaceOneInstanceChecker(self, event):
        if self.OneInstanceFindReplace == 0:
            win = FindReplaceMiniFrame(self, wx.SIMPLE_BORDER)
            win.Centre()
            win.Show(True)
        else:
            gFindReplaceMiniFrame.findwhatcomboctrl.SetValue(self.GetSelectedText())
            gFindReplaceMiniFrame.OnFindComboBoxTextChange(event)

class MemoMiniFrame(wx.MiniFrame):
    ''' Find/Replace Floating MiniFrame for Comments/WizBAIN Editor. '''
    def __init__(self, parent, id):
        wx.MiniFrame.__init__(self, parent, -1, title=u'Memo', style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT)

        global gMiniMemo
        gMiniMemo = self

        self.SetSizeHints(75,75)

        self.memo = stc.StyledTextCtrl(self, wx.ID_ANY)
        self.memo.Bind(wx.EVT_KEY_DOWN, self.OnMiniMemoKeyDown)
        self.memo.SetMarginWidth(1, 0)
        self.memo.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'fore:#000000,back:#FFFFBF,face:%(mono)s,size:%(size)d' % faces)
        self.memo.ClearDocumentStyle()
        self.memo.StyleClearAll()
        self.memo.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'fore:#000000,back:#FFFFBF,face:%(mono)s,size:%(size)d' % faces)
        try:
            self.memo.SetText(u'%s'%basher.settings['bash.installers.wizSTC.MiniMemoText'])
        except:
            self.memo.SetTextUTF8(u'%s'%basher.settings['bash.installers.wizSTC.MiniMemoText'])
        self.memo.EmptyUndoBuffer()
        self.memo.SetWhitespaceForeground(True,'#FFFFBF')
        self.memo.SetWhitespaceBackground(True,'#FFFFBF')
        self.memo.SetWrapMode(1)
        self.memo.SetFocus()

        self.Centre()
        self.Show()

        self.SetSize(basher.settings['bash.installers.wizSTC.MiniMemoSavedSize'])

        self.Bind(wx.EVT_CLOSE, self.OnDestroyMemo)

    def OnMiniMemoKeyDown(self, event):
        ''' Event occurs when a key is pressed down. '''
        key = event.GetKeyCode()
        event.Skip()
        if event.ControlDown() and key == 77:#Ctrl+M
            self.OnDestroyMemo(event)

    def OnDestroyMemo(self, event):
        basher.settings['bash.installers.wizSTC.MiniMemoSavedSize'] = self.GetSize()
        basher.settings['bash.installers.wizSTC.MiniMemoText'] = self.memo.GetTextUTF8()
        basher.settings.setChanged('bash.installers.wizSTC.MiniMemoText')
        self.Destroy()
        gWizSTC.OneInstanceMiniMemo = 0
        gWizSTC.SetFocus()
        # print ('Destroyed Memo MiniFrame')

class FindReplaceMiniFrame(wx.MiniFrame):
    ''' Find/Replace Floating MiniFrame for Comments/WizBAIN Editor. '''
    def __init__(self, parent, id):
        wx.MiniFrame.__init__(self, parent, -1, title=u'Find & Replace', size=(560, 330), style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT)

        global gFindReplaceMiniFrame
        gFindReplaceMiniFrame = self

        gWizSTC.OneInstanceFindReplace = 1

        # self.SetDoubleBuffered(True)#Hmmm need to look into overlapping issues with the staticboxes and the inviso slider

        self.SetSizeHints(560,330,560,560)

        self.SetBackgroundColour('#E0DFE3')    # Set the Frame Background Color

        self.statictextfindwhat =    wx.StaticText(self, -1, u'Find what?',    pos=( 10,  8))
        self.statictextreplacewith = wx.StaticText(self, -1, u'Replace with?', pos=( 10, 93))
        self.statictextcountfound =  wx.StaticText(self, -1, u'Count Found:',  pos=(260, 65))

        self.staticboxbookmarkline = wx.StaticBox(self, -1, u'',          pos=(260,  25), size=(288, 32))
        self.staticboxinselection =  wx.StaticBox(self, -1, u'',          pos=(305, 109), size=(242, 32))
        self.staticboxbookmarks =    wx.StaticBox(self, -1, u'Bookmarks', pos=(185, 220), size=(190, 80))

        self.checkboxwholeword =    wx.CheckBox(self, -1, u'Match whole word only', pos=( 10, 137), style=wx.NO_BORDER)
        if basher.settings['bash.installers.wizSTC.FindReplaceWholeWordCB'] == 1:
            self.checkboxwholeword.SetValue(True)
        self.checkboxmatchcase =    wx.CheckBox(self, -1, u'Match Case',            pos=( 10, 157), style=wx.NO_BORDER)
        if basher.settings['bash.installers.wizSTC.FindReplaceMatchCaseCB'] == 1:
            self.checkboxmatchcase.SetValue(True)
        self.checkboxwraparound =   wx.CheckBox(self, -1, u'Wrap around',           pos=( 10, 177), style=wx.NO_BORDER)
        if basher.settings['bash.installers.wizSTC.FindReplaceWrapAroundCB'] == 1:
            self.checkboxwraparound.SetValue(True)

        self.checkboxinselection =  wx.CheckBox(self, -1, u'In Selection',          pos=(325, 118), style=wx.NO_BORDER)
        if gWizSTC.GetSelectionStart() == gWizSTC.GetSelectionEnd():
            self.checkboxinselection.Enable(False)
        else:
            self.checkboxinselection.SetValue(True)
        self.checkboxbookmarkline = wx.CheckBox(self, -1, u'Bookmark Line',         pos=(275, 35), style=wx.NO_BORDER)

        self.standardbookmarkbmpbtn = wx.BitmapButton(self,     -1, gImgIdx['bookmark16.png'], (265, 265))
        self.findpreviousbookmarkbmpbtn = wx.BitmapButton(self, -1, gImgIdx['bookmarkfindprevious16.png'], (290, 265))
        self.findnextbookmarkbmpbtn = wx.BitmapButton(self,     -1, gImgIdx['bookmarkfindnext16.png'], (315, 265))

        self.removeallbookmarksbmpbtn = wx.BitmapButton(self,   -1, gImgIdx['removeallbookmarks16.png'], (340, 265))

        self.appenditemfindlistbmpbtn = wx.BitmapButton(self,       -1, gImgIdx['listappend16.png'], (364, 4))
        self.appenditemfindlistbmpbtn.SetToolTipString(u'Append To Find List')
        self.deleteitemfindlistbmpbtn = wx.BitmapButton(self,        -1, gImgIdx['listerase16.png'], (390, 4))
        self.deleteitemfindlistbmpbtn.SetToolTipString(u'Delete from Find List')
        self.appenditemreplacelistbmpbtn = wx.BitmapButton(self,    -1, gImgIdx['listappend16.png'], (364, 88))
        self.appenditemreplacelistbmpbtn.SetToolTipString(u'Append To Replace List')
        self.deleteitemreplacelistbmpbtn = wx.BitmapButton(self,     -1, gImgIdx['listerase16.png'], (390, 88))
        self.deleteitemreplacelistbmpbtn.SetToolTipString(u'Delete from Replace List')

        self.findallfulllist = wx.TextCtrl(self, -1, u'Find All Full List', (10, 310), (400,215), style=wx.VSCROLL | wx.HSCROLL | wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_READONLY)

        self.searchmoderadiobox = wx.RadioBox(self, -1, u'Search Mode', choices=[u'Normal'], majorDimension=3, style=wx.RA_SPECIFY_ROWS, pos=(10, 220),  size=(170, 80))
        # self.searchmoderadiobox = wx.RadioBox(self, -1, u'Search Mode(Normal ONLY)', choices=[u'Normal',u'Extended (\\n, \\r, \\t, \\0, \\x...)', u'Regular Expression'], majorDimension=3, style=wx.RA_SPECIFY_ROWS, pos=(10, 220),  size=(170, 80))
        self.transparencyradiobox = wx.RadioBox(self, -1, u'Transparency', choices=['On losing focus','Always'], majorDimension=2, style=wx.RA_SPECIFY_ROWS, pos=(380, 220), size=(120, 80))

        self.transparencyslider = wx.Slider(self, 100, basher.settings['bash.installers.wizSTC.SetFindReplaceTransparency'], 30, 255, (382, 280), (90, 18), wx.SL_BOTH )
        # Slider initial position is set to 255. The min value is 30, max value is 255
        #wx.SL_HORIZONTAL | wx.SL_VERTICAL | wx.SL_BOTH | wx.SL_AUTOTICKS | wx.SL_LABELS | wx.SL_LEFT | wx.SL_RIGHT | wx.SL_TOP | wx.SL_BOTTOM | wx.SL_INVERSE
        self.transparencyslider.SetTickFreq(5, 1)
        self.transparencysliderstatictext = wx.StaticText(self, -1, '%s' %self.transparencyslider.GetValue(),    pos=(476, 280))

        self.gFindlist = basher.settings['bash.installers.wizSTC.FindList']
        self.gReplacelist = basher.settings['bash.installers.wizSTC.ReplaceList']

        if basher.settings['bash.installers.wizSTC.FindReplaceComboBoxsAutoSort'] == 1: #Auto Sort
            self.findwhatcomboctrl = wx.ComboBox(self, id=-1, value=gWizSTC.GetSelectedText(), pos=(100, 5), size=(260, -1), choices=self.gFindlist, style=wx.CB_SORT)#| wx.CB_SIMPLE | wx.CB_DROPDOWN | wx.CB_READONLY
            self.replacewithcomboctrl = wx.ComboBox(self, id=-1, pos=(100, 90), size=(260, -1), choices=self.gReplacelist, style=wx.CB_SORT)
        elif basher.settings['bash.installers.wizSTC.FindReplaceComboBoxsAutoSort'] == 0:
            self.findwhatcomboctrl = wx.ComboBox(self, id=-1, value=gWizSTC.GetSelectedText(), pos=(100, 5), size=(260, -1), choices=self.gFindlist)
            self.replacewithcomboctrl = wx.ComboBox(self, id=-1, pos=(100, 90), size=(260, -1), choices=self.gReplacelist)

        #Upon opening the dialog for the first time or until the user deletes the default list item or adds one, place this in the box as a tip.
        if self.gFindlist == ['Add/Delete from list with the buttons ==>']: self.findwhatcomboctrl.SetValue('Add/Delete from list with the buttons ==>')
        if self.gReplacelist == ['Add/Delete from list with the buttons ==>']: self.findwhatcomboctrl.SetValue('Add/Delete from list with the buttons ==>')

        self.findcomboctrlstaticbmp = wx.StaticBitmap(self, -1, gImgIdx['findtextctrlwhite2120.png'], pos=(79,5), size=(22,21), style=wx.BORDER)#, style=wx.NO_BORDER
        self.findreplacecomboctrlstaticbmp = wx.StaticBitmap(self, -1, gImgIdx['findreplacetextctrlwhite2120.png'], pos=(79,90), size=(22,21), style=wx.BORDER)

        self.findcaretbutton =   wx.Button(self, -1, u'Find Caret',   pos=( 10,  32), size=( 60, 24))
        self.findprevbutton =    wx.Button(self, -1, u'Find Prev',    pos=(420,   4), size=( 60, 24))
        self.findnextbutton =    wx.Button(self, -1, u'Find Next',    pos=(485,   4), size=( 60, 24))
        self.findallbutton =     wx.Button(self, -1, u'Find All',     pos=(420,  32), size=(125, 24))
        self.setbookmarkbutton = wx.Button(self, -1, u'Set Bookmark', pos=(190, 265), size=( 75, 24))
        self.countbutton =       wx.Button(self, -1, u'Count',        pos=(420,  60), size=(124, 24))
        self.replacebutton =     wx.Button(self, -1, u'Replace',      pos=(420,  88), size=(124, 24))
        self.replaceallbutton =  wx.Button(self, -1, u'Replace All',  pos=(420, 116), size=(124, 24))
        self.closebutton =       wx.Button(self, -1, u'Close',        pos=(420, 144), size=(124, 24))
        self.gotolinebutton =    wx.Button(self, -1, u'Go To Line',   pos=(485, 315), size=( 60, 24))
        self.gotocolumnbutton =  wx.Button(self, -1, u'Go To Col',    pos=(485, 360), size=( 60, 24))
        self.gotoposbutton =     wx.Button(self, -1, u'Go To Pos',    pos=(485, 405), size=( 60, 24))

        self.minimizefindreplacebmpbtn = wx.BitmapButton(self, -1, gImgIdx['minimizefindreplace5030.png'], (485, 490))

        self.staticline = wx.StaticLine(self, -1, pos = (5, 305), size = (545, 2), style = wx.LI_HORIZONTAL, name = u'static line')

        self.spinnerctrl1 = wx.SpinCtrl(self, -1, '', (420, 315), (60, -1))
        self.spinnerctrl1.SetRange(1, gWizSTC.GetLineCount())
        self.spinnerctrl1.SetValue(1)
        self.staticlinecount = wx.StaticText(self, -1, u'Max %s' %gWizSTC.GetLineCount(),    pos=(420, 340))

        self.spinnerctrl2 = wx.SpinCtrl(self, -1, '', (420, 360), (60, -1))
        currentline = gWizSTC.GetCurrentLine()
        linelen = gWizSTC.GetLineEndPosition(currentline) - gWizSTC.PositionFromLine(currentline)
        self.spinnerctrl2.SetRange(0,linelen)
        self.spinnerctrl2.SetValue(0)
        self.staticcol = wx.StaticText(self, -1, u'Max %s' %linelen,    pos=(420, 385))

        self.spinnerctrl3 = wx.SpinCtrl(self, -1, '', (420, 405), (60, -1))
        self.spinnerctrl3.SetRange(0,gWizSTC.GetLength())
        self.spinnerctrl3.SetValue(0)
        self.staticpos = wx.StaticText(self, -1, u'Max %s' %gWizSTC.GetLength(),    pos=(420, 430))

        # http://www.bluebison.net/: The cute chameleon & python images comes from here.
        self.bluebisonpythonstaticbmp =      wx.StaticBitmap(self, -1, gImgIdx['bluebisonpythonwithpencil.png'],      pos=(140,115), size=(150,103), style=wx.NO_BORDER)
        self.bluebisonpythonawakestaticbmp = wx.StaticBitmap(self, -1, gImgIdx['bluebisonpythonwithpencilawake.png'], pos=(140,115), size=(150,103), style=wx.NO_BORDER)
        self.bluebisonpythonawakestaticbmp.Hide()

        self.bluebisonsneakypadstaticbmp = wx.StaticBitmap(self, -1, gImgIdx['wizpad++3954.png'], pos=(514,220), size=(39,54), style=wx.NO_BORDER)

        self.contexthelpbmpbtn = wx.BitmapButton(self, -1, gImgIdx['contexthelp24.png'], (510, 268))
        self.contexthelpbmpbtn.SetToolTipString(u'View help for\nthis dialog')
        self.contexthelpbmpbtn.SetCursor(wx.StockCursor(wx.CURSOR_QUESTION_ARROW))

        ''' Find/Replace Bindings '''
        self.findcaretbutton.Bind( wx.EVT_BUTTON, self.OnFindCaret,                id=-1)
        self.findprevbutton.Bind(  wx.EVT_BUTTON, self.OnFindPrev,                 id=-1)
        self.findnextbutton.Bind(  wx.EVT_BUTTON, self.OnFindNext,                 id=-1)
        self.findallbutton.Bind(   wx.EVT_BUTTON, self.OnFindAll,                  id=-1)
        self.countbutton.Bind(     wx.EVT_BUTTON, self.OnFindCount,                id=-1)
        self.closebutton.Bind(     wx.EVT_BUTTON, self.OnDestroyFindReplaceDialog, id=-1)
        self.replacebutton.Bind(   wx.EVT_BUTTON, self.OnReplaceSelection,         id=-1)
        self.replaceallbutton.Bind(wx.EVT_BUTTON, self.OnReplaceAllInDoc,          id=-1)

        self.standardbookmarkbmpbtn.Bind(    wx.EVT_BUTTON, self.OnToggleBookmark,           id=-1)
        self.findpreviousbookmarkbmpbtn.Bind(wx.EVT_BUTTON, self.OnHopPreviousBookmark,      id=-1)
        self.findnextbookmarkbmpbtn.Bind(    wx.EVT_BUTTON, self.OnHopNextBookmark,          id=-1)
        self.removeallbookmarksbmpbtn.Bind(  wx.EVT_BUTTON, self.OnRemoveAllBookmarks,       id=-1)

        self.appenditemfindlistbmpbtn.Bind(   wx.EVT_BUTTON, self.OnAppendFindListItem,               id=-1)
        self.deleteitemfindlistbmpbtn.Bind(    wx.EVT_BUTTON, self.OnDeleteFindListItem,              id=-1)
        self.appenditemreplacelistbmpbtn.Bind(wx.EVT_BUTTON, self.OnAppendReplaceListItem,            id=-1)
        self.deleteitemreplacelistbmpbtn.Bind( wx.EVT_BUTTON, self.OnDeleteReplaceListItem,           id=-1)
        self.contexthelpbmpbtn.Bind(      wx.EVT_BUTTON, self.OnShowFindReplaceHelpDialog, id=-1)

        self.checkboxwholeword.Bind(wx.EVT_CHECKBOX, self.OnSaveCheckBoxSetting)
        self.checkboxmatchcase.Bind(wx.EVT_CHECKBOX, self.OnSaveCheckBoxSetting)
        self.checkboxwraparound.Bind(wx.EVT_CHECKBOX, self.OnSaveCheckBoxSetting)

        self.findcomboctrlstaticbmp.Bind(wx.EVT_LEFT_UP,         self.OnSetSelectedToFindCombo,        id=-1)
        self.findcomboctrlstaticbmp.Bind(wx.EVT_RIGHT_UP,        self.OnBlankFindCombo,                id=-1)
        self.findreplacecomboctrlstaticbmp.Bind(wx.EVT_LEFT_UP,  self.OnSetSelectedToFindReplaceCombo, id=-1)
        self.findreplacecomboctrlstaticbmp.Bind(wx.EVT_RIGHT_UP, self.OnBlankFindReplaceCombo,         id=-1)

        self.findwhatcomboctrl.Bind(wx.EVT_TEXT,            self.OnFindComboBoxTextChange,        id=-1)

        self.minimizefindreplacebmpbtn.Bind(wx.EVT_BUTTON,       self.OnFindReplaceResizeFrameToMinimum, id=-1)

        self.bluebisonpythonstaticbmp.Bind(wx.EVT_ENTER_WINDOW,      self.OnPythonThoughtBubble,        id=-1)
        self.bluebisonpythonawakestaticbmp.Bind(wx.EVT_LEAVE_WINDOW, self.OnPythonThoughtBubbleHide,    id=-1)

        self.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        widgetList = [self.bluebisonpythonstaticbmp,self.bluebisonpythonawakestaticbmp,self.findcaretbutton,self.findprevbutton,self.findnextbutton,self.findallbutton,self.countbutton,self.closebutton,self.replacebutton,self.replaceallbutton,self.setbookmarkbutton,self.standardbookmarkbmpbtn,self.findpreviousbookmarkbmpbtn,self.findnextbookmarkbmpbtn,self.removeallbookmarksbmpbtn,self.appenditemfindlistbmpbtn,self.deleteitemfindlistbmpbtn,self.appenditemreplacelistbmpbtn,self.deleteitemreplacelistbmpbtn,self.contexthelpbmpbtn,self.findcomboctrlstaticbmp,self.findreplacecomboctrlstaticbmp,self.checkboxwholeword,self.checkboxmatchcase,self.checkboxwraparound,self.checkboxbookmarkline,self.checkboxinselection,self.transparencyslider,self.transparencysliderstatictext,self.transparencyradiobox,self.searchmoderadiobox]
        for widget in widgetList:
            widget.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
            widget.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        #the losing focus part of these widgets are handled in gWizSTC.OnUpdateUI def
        # for widget in [self.findwhatcomboctrl,self.findallfulllist,self.replacewithcomboctrl]:
            #### widget.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)#BUGGY. Doesnt work right graphically, use wx.EVT_LEFT_DOWN for combo boxes and textctrls
            # widget.Bind(wx.EVT_LEFT_DOWN, self.OnSetFocus)
            # widget.Bind(wx.EVT_ENTER_WINDOW, self.OnSetFocus)
            # widget.Bind(wx.EVT_LEAVE_WINDOW, self.OnKillFocus)
            # widget.Bind(wx.EVT_LEAVE_WINDOW, self.OnComboBoxTextCtrlLeaveWindow)
            # widget.Bind(wx.EVT_TEXT, self.OnSetFocus)
            # widget.Bind(wx.EVT_UPDATE_UI, self.OnSetFocus)
            # widget.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        # self.Bind(wx.EVT_LEAVE_WINDOW, self.OnKillFocus)


        self.transparencyradiobox.Bind(wx.EVT_RADIOBOX, self.OnEvtTransparencyRadioBox, id=-1)
        self.transparencyslider.Bind(wx.EVT_SLIDER, self.OnAdjustFindReplaceTransparency, id=-1)

        self.gotolinebutton.Bind(wx.EVT_BUTTON, self.OnFRGoToLine, id=-1)
        self.gotocolumnbutton.Bind(wx.EVT_BUTTON, self.OnFRGoToColumn, id=-1)
        self.gotoposbutton.Bind(wx.EVT_BUTTON, self.OnFRGoToPos, id=-1)

        self.Bind(wx.EVT_CLOSE, self.OnDestroyFindReplaceDialog)

        self.OnFindComboBoxTextChange(self)

        self.SetTransparent(basher.settings['bash.installers.wizSTC.SetFindReplaceTransparency'])
        self.Centre()
        self.Show()

        self.Bind(wx.EVT_KEY_DOWN, self.OnFRKeyDown)

    def OnFRKeyDown(self, event):
        pass
        #TODO inmplement F3/F4 search here
        # print('FR KEY DOWN')

    def OnFindComboBoxTextChange(self, event):
        if self.findwhatcomboctrl.GetValue() == u'':
            self.findprevbutton.Disable()
            self.findnextbutton.Disable()
            self.findallbutton.Disable()
            self.countbutton.Disable()
            self.replacebutton.Disable()
            self.replaceallbutton.Disable()
        else:
            self.findprevbutton.Enable()
            self.findnextbutton.Enable()
            self.countbutton.Enable()
            self.findallbutton.Enable()
            self.replacebutton.Enable()
            self.replaceallbutton.Enable()

    def OnBlankFindCombo(self, event):
        self.findwhatcomboctrl.SetValue(u'')
        self.OnFindComboBoxTextChange(event)
    def OnSetSelectedToFindCombo(self, event):
        self.findwhatcomboctrl.SetValue(gWizSTC.GetSelectedText())
        self.OnFindComboBoxTextChange(event)
    def OnBlankFindReplaceCombo(self, event):
        self.replacewithcomboctrl.SetValue(u'')
    def OnSetSelectedToFindReplaceCombo(self, event):
        self.replacewithcomboctrl.SetValue(gWizSTC.GetSelectedText())

    def OnPythonThoughtBubble(self, event):
        self.bluebisonpythonawakestaticbmp.Show()
        self.bluebisonpythonstaticbmp.Hide()
    def OnPythonThoughtBubbleHide(self, event):
        # print ('Ugh eyelids gettting heavy...Must study Python harder....')
        self.bluebisonpythonstaticbmp.Show()
        self.bluebisonpythonawakestaticbmp.Hide()

    def OnFRGoToLine(self, event):
        gWizSTC.GotoLine(self.spinnerctrl1.GetValue()-1)
        # gWizSTC.SetFocus()

    def OnFRGoToColumn(self, event):
        currentline = gWizSTC.GetCurrentLine()             #Returns the line number of the line with the caret.
        linestart = gWizSTC.PositionFromLine(currentline)  #Retrieve the position at the start of a line.
        gWizSTC.GotoPos(linestart + self.spinnerctrl2.GetValue())
        # gWizSTC.SetFocus()

    def OnFRGoToPos(self, event):
        gWizSTC.GotoPos(self.spinnerctrl3.GetValue())
        # gWizSTC.SetFocus()

    # # def OnComboBoxTextCtrlLeaveWindow(self, event):
        # # if event.GetEventObject() == self.findwhatcomboctrl or event.GetEventObject() == self.replacewithcomboctrl:
            # # if self.transparencyradiobox.GetSelection() == 0:#only on losing focus
                # # self.SetTransparent(basher.settings['bash.installers.wizSTC.SetFindReplaceTransparency'])

    def OnSetFocus(self, event):
        if self.transparencyradiobox.GetSelection() == 0:#only on losing focus
            self.SetTransparent(255)
        # print('OnSetFocus')

    def OnKillFocus(self, event):
        # print event.GetWindow()
        # print event.GetEventObject()
        if event.GetWindow() == None:
        # if self.findwhatcomboctrl.GetWindow():
            event.Skip()

        elif event.GetEventObject() == self.findallfulllist:
            if self.transparencyradiobox.GetSelection() == 0:#only on losing focus
                self.SetTransparent(basher.settings['bash.installers.wizSTC.SetFindReplaceTransparency'])
        elif self.transparencyradiobox.GetSelection() == 0:#only on losing focus
            self.SetTransparent(basher.settings['bash.installers.wizSTC.SetFindReplaceTransparency'])
        # print('OnKillFocus')

    def OnEvtTransparencyRadioBox(self, event):
        # print ('EvtRadioBox: %d\n' % event.GetInt())
        if event.GetInt() == 0:#only on losing focus
            self.SetTransparent(255)
        else:#Always
            self.SetTransparent(basher.settings['bash.installers.wizSTC.SetFindReplaceTransparency'])
        basher.settings.setChanged('bash.installers.wizSTC.SetFindReplaceTransparency')

    def OnAdjustFindReplaceTransparency(self, event):
        value = self.transparencyslider.GetValue()
        self.SetTransparent(value)
        self.transparencysliderstatictext.SetLabel(str(value))

        basher.settings['bash.installers.wizSTC.SetFindReplaceTransparency'] = value
        basher.settings.setChanged('bash.installers.wizSTC.SetFindReplaceTransparency')

    def OnFindCount(self, event):
        self.OnSetSearchFlags(event)
        searchflags = gWizSTC.GetSearchFlags()
        startofdoc = 1
        endofdoc = gWizSTC.GetLength() #Returns the number of characters in the document.
        # gWizSTC.FindText(startofdoc,endofdoc,self.findwhatcomboctrl.GetValue(),gWizSTC.GetSearchFlags())#(minPos,maxPos,text,flags)
        found = 0
        if gWizSTC.FindText(startofdoc,endofdoc,self.findwhatcomboctrl.GetValue(), searchflags) == -1:
            pass
            # print ('None Found')
        elif self.findwhatcomboctrl.GetValue() == '':
            pass
            # print ('saved again from a recursive loop')
        else:
            while gWizSTC.FindText(startofdoc,endofdoc,self.findwhatcomboctrl.GetValue(), searchflags) > -1:
                gWizSTC.FindText(startofdoc,endofdoc,self.findwhatcomboctrl.GetValue(), searchflags)
                # print gWizSTC.FindText(startofdoc,endofdoc,self.findwhatcomboctrl.GetValue(), searchflags)
                startofdoc = len(self.findwhatcomboctrl.GetValue()) + gWizSTC.FindText(startofdoc,endofdoc,self.findwhatcomboctrl.GetValue(), searchflags)
                found = found + 1
        self.statictextcountfound.SetLabel('Count Found: %s' %found)
        # print ('FindCount: ' + str(found))

    def OnSetSearchFlags(self, event):
        global searchflags
        self.OnGetSearchFlags(event)
        gWizSTC.SetSearchFlags(searchflags)
        # print('OnSetSearchFlags')
        # print ('searchflags:', searchflags)

    def OnSaveCheckBoxSetting(self, event):
        if self.checkboxwholeword.GetValue() == True:
            basher.settings['bash.installers.wizSTC.FindReplaceWholeWordCB'] = 1
        else:
            basher.settings['bash.installers.wizSTC.FindReplaceWholeWordCB'] = 0
        basher.settings.setChanged('bash.installers.wizSTC.FindReplaceWholeWordCB')
        if self.checkboxmatchcase.GetValue() == True:
            basher.settings['bash.installers.wizSTC.FindReplaceMatchCaseCB'] = 1
        else:
            basher.settings['bash.installers.wizSTC.FindReplaceMatchCaseCB'] = 0
        basher.settings.setChanged('bash.installers.wizSTC.FindReplaceMatchCaseCB')
        if self.checkboxwraparound.GetValue() == True:
            basher.settings['bash.installers.wizSTC.FindReplaceWrapAroundCB'] = 1
        else:
            basher.settings['bash.installers.wizSTC.FindReplaceWrapAroundCB'] = 0
        basher.settings.setChanged('bash.installers.wizSTC.FindReplaceWrapAroundCB')
        # print('OnSaveCheckBoxSetting')

    def OnGetSearchFlags(self, event):
        global searchflags
        searchflags = 0
        if self.checkboxwholeword.IsChecked() == True:
            searchflags |= wx.stc.STC_FIND_WHOLEWORD
            # print ('wx.stc.STC_FIND_WHOLEWORD')
        if self.checkboxmatchcase.IsChecked() == True:
            searchflags |= wx.stc.STC_FIND_MATCHCASE
            # print ('wx.stc.STC_FIND_MATCHCASE')
        # if self.regex.IsChecked() == True:
            # searchflags |= wx.stc.STC_FIND_REGEXP
            # print ('wx.stc.STC_FIND_REGEXP')
        # if self.regular:
            # searchflags |= wx.stc.STC_FIND_REGEXP

        return searchflags

    def OnFindCaret(self, event):
        gWizSTC.EnsureCaretVisible()
        gWizSTC.SetFocus()

    def OnFindPrev(self, event):
        self.OnSetSearchFlags(event)
        gWizSTC.SearchAnchor()
        #Flags are stc.STC_FIND_WHOLEWORD, stc.STC_FIND_MATCHCASE, stc.STC_FIND_WORDSTART, stc.STC_FIND_REGEXP
        # gWizSTC.SearchPrev(stc.STC_FIND_MATCHCASE , self.findwhatcomboctrl.GetValue())
        if gWizSTC.SearchPrev(gWizSTC.GetSearchFlags(), self.findwhatcomboctrl.GetValue()) == -1:
            if self.checkboxwraparound.IsChecked() == True:
                # print ('insertwraparound code here')
                val = self.findwhatcomboctrl.GetValue()

                curpos = gWizSTC.GetCurrentPos()
                findstring = gWizSTC.FindText(gWizSTC.GetLength(), curpos, val, flags=self.OnGetSearchFlags(event))

                if findstring != -1:
                    gWizSTC.GotoPos(findstring)
                    gWizSTC.SetSelection(findstring, findstring + len(val))
                    if self.checkboxbookmarkline.IsChecked() == True:
                        linenum = gWizSTC.GetCurrentLine()
                        gWizSTC.MarkerAdd(linenum, 1)#Mark with user bookmark
                else:
                    # print ('String wasnt found!')
                    wx.Bell()
            else:
                # print ('String wasnt found!')
                wx.Bell()
        else:
            if self.checkboxbookmarkline.IsChecked() == True:
                linenum = gWizSTC.GetCurrentLine()
                gWizSTC.MarkerAdd(linenum, 1)#Mark with user bookmark

        # gWizSTC.SetFocus()
        gWizSTC.EnsureCaretVisible()   #Ensure the caret is visible.

        # print ('Find Prev')

    def OnFindNext(self, event):
        ''' Find the next occurance of a string in the document. '''
        if self.findwhatcomboctrl.GetValue() == '':
            # print ('Nothing In the Find ComboBox!')
            wx.Bell()
            gWizSTC.SetFocus()
        else:
            # print ('Value:', self.findwhatcomboctrl.GetValue())
            self.OnSetSearchFlags(event)
            lengthofword = len(self.findwhatcomboctrl.GetValue())
            # print ('Length', lengthofword)
            start1 = gWizSTC.GetSelectionStart()    #Returns the position at the start of the selection.
            end1 = gWizSTC.GetSelectionEnd()      #Returns the position at the end of the selection.
            gWizSTC.GotoPos(end1)
            gWizSTC.SearchAnchor()         #Sets the current caret position to be the search anchor.

            if gWizSTC.SearchNext(gWizSTC.GetSearchFlags(), self.findwhatcomboctrl.GetValue()) == -1:
                if self.checkboxwraparound.IsChecked() == True:
                    # print ('insertwraparound code here')
                    val = self.findwhatcomboctrl.GetValue()

                    curpos = gWizSTC.GetCurrentPos() #Hmmmm.. when run as .py gives a global error, but not when run as .pyw???
                    findstring = gWizSTC.FindText(0, curpos, val, flags=self.OnGetSearchFlags(event))

                    if findstring != -1:
                        gWizSTC.GotoPos(findstring)
                        gWizSTC.SetSelection(findstring, findstring + len(val))
                        if self.checkboxbookmarkline.IsChecked() == True:
                            linenum = gWizSTC.GetCurrentLine()
                            gWizSTC.MarkerAdd(linenum, 1)#Mark with user bookmark
                    else:
                        # print ('String wasnt found!')
                        wx.Bell()
                        gWizSTC.SetSelection(end1,start1)
                else:
                    # print ('String wasnt found!')
                    wx.Bell()
                    gWizSTC.SetSelection(end1,start1)
            else:
                start2 = gWizSTC.GetSelectionStart()   #Returns the position at the start of the selection.
                end2 = gWizSTC.GetSelectionEnd()       #Returns the position at the end of the selection.
                gWizSTC.SetSelection(start2,end2)

            # gWizSTC.GetAnchor()                    #Int ==> Returns the position of the opposite end of the selection to the caret.
            # gWizSTC.SetAnchor(end2)                #Set the selection anchor to a position. The anchor is the opposite end of the selection from the caret.

                if self.checkboxbookmarkline.IsChecked() == True:
                    linenum = gWizSTC.GetCurrentLine()
                    gWizSTC.MarkerAdd(linenum, 1)#Mark with user bookmark

            # gWizSTC.SetFocus()
            # gWizSTC.GetSTCFocus()          #Get internal focus flag. --> bool
            # gWizSTC.SetSTCFocus(True)      #Change internal focus flag. --> bool
            gWizSTC.EnsureCaretVisible()   #Ensure the caret is visible.

        # print ('Find Next-This NEEDS more work.')

    def OnFindAll(self, event):
        self.OnSetSearchFlags(event)
        searchflags = gWizSTC.GetSearchFlags()
        startofdoc = 0
        endofdoc = gWizSTC.GetLength() #Returns the number of characters in the document.
        # gWizSTC.FindText(startofdoc,endofdoc,self.findwhatcomboctrl.GetValue(),gWizSTC.GetSearchFlags())#(minPos,maxPos,text,flags)
        found = 0
        points = self.findallfulllist.GetFont().GetPointSize()  # get the current size
        bold = wx.Font(points+5, wx.ROMAN, wx.NORMAL, wx.BOLD, True)#, wx.ITALIC
        boldnum = wx.Font(points+1, wx.ROMAN, wx.NORMAL, wx.BOLD, False)

        if gWizSTC.FindText(startofdoc,endofdoc,self.findwhatcomboctrl.GetValue(), searchflags) == -1:
            self.findallfulllist.SetValue(u'Nothing Was Found :( ?')
            self.findallfulllist.SetStyle(0, 22, wx.TextAttr(wx.NullColour, wx.NullColour, bold))
            self.findallfulllist.SetStyle(0, 22, wx.TextAttr('BLUE', 'YELLOW'))
            # print ('None Found')
        elif self.findwhatcomboctrl.GetValue() == '':
            self.findallfulllist.SetValue(u'Saved again from a recursive loop! :)')
            self.findallfulllist.SetStyle(0, 37, wx.TextAttr(wx.NullColour, wx.NullColour, bold))
            self.findallfulllist.SetStyle(0, 37, wx.TextAttr('BLACK', 'RED'))
            # print ('Saved again from a recursive loop! :)')
            wx.Bell()
        else:
            self.findallfulllist.SetValue(u'Find All Found List\n' + u'SearchString :' + str(self.findwhatcomboctrl.GetValue()) + u'\n' + u'SearchFlags :' + str(searchflags) + u'\n' + u'%s' %basher.gInstallers.gPackage.GetValue() + u'\n\n')
            # Make the headers bold & underlined
            self.findallfulllist.SetStyle(0, 19, wx.TextAttr(wx.NullColour, wx.NullColour, bold))
            self.findallfulllist.SetStyle(0, 19, wx.TextAttr('BLACK', '#CBFF9E'))
            while gWizSTC.FindText(startofdoc,endofdoc,self.findwhatcomboctrl.GetValue(), searchflags) > -1:
                gWizSTC.FindText(startofdoc,endofdoc,self.findwhatcomboctrl.GetValue(), searchflags)
                # print gWizSTC.FindText(startofdoc,endofdoc,self.findwhatcomboctrl.GetValue(), searchflags)
                linenum = gWizSTC.LineFromPosition(gWizSTC.FindText(startofdoc,endofdoc,self.findwhatcomboctrl.GetValue(), searchflags))
                posnum = gWizSTC.FindText(startofdoc,endofdoc,self.findwhatcomboctrl.GetValue(), searchflags)
                column = gWizSTC.GetColumn(posnum)#- len(self.findwhatcomboctrl.GetValue()
                if self.checkboxbookmarkline.IsChecked() == True:
                    gWizSTC.MarkerAdd(linenum, 1)#Mark with user bookmark
                found = found + 1
                foundoccurancecolorstart = self.findallfulllist.GetLastPosition()
                self.findallfulllist.AppendText(str(found) + u'.  Line ' + str(linenum + 1) + u' | Column ' + str(column) + u' | Position ' + str(posnum) + u'\n' + str(gWizSTC.GetLine(linenum)) + u'\n')
                # Make the found occurances bold & colored
                self.findallfulllist.SetStyle(foundoccurancecolorstart, foundoccurancecolorstart+len(str(found))+1, wx.TextAttr(wx.NullColour, wx.NullColour, boldnum))
                self.findallfulllist.SetStyle(foundoccurancecolorstart, foundoccurancecolorstart+len(str(found))+1, wx.TextAttr('BLACK', '#CBFF9E'))
                startofdoc = len(self.findwhatcomboctrl.GetValue()) + gWizSTC.FindText(startofdoc,endofdoc,self.findwhatcomboctrl.GetValue(), searchflags)

        self.findallfulllist.SetInsertionPoint(0)
        # print self.GetSize()
        self.SetSize(wx.Size(560,560))
        self.statictextcountfound.SetLabel(u'Count Found: %s' %found)
        # print ('FindCount: ' + str(found))
        # print found

        # print ('Find All-This probably more Work.')

    def OnReplaceSelection(self, event):

        selstart = gWizSTC.GetSelectionStart()
        # gWizSTC.SetSelectionStart(selstart)
        selend = gWizSTC.GetSelectionEnd()
        # gWizSTC.SetSelectionEnd(selend)

        # gWizSTC.GetSelection()
        # gWizSTC.SetSelection(selstart,selend)

        # gWizSTC.SetTargetStart(selstart)
        # gWizSTC.SetTargetEnd(selend)
        # print gWizSTC.TargetFromSelection()

        # print gWizSTC.GetSelection()

        if selstart == selend:
            # print ('Nothing Selected')
            wx.Bell()
        else:
            if self.findwhatcomboctrl.GetValue() == '':
                # print ('Nothing In the Find ComboBox!')
                wx.Bell()
            # elif self.replacewithcomboctrl.GetValue() == '':
                # print ('Nothing In the Replace ComboBox! This will replace the selection with nothing.')
            else:
                gWizSTC.TargetFromSelection()
                gWizSTC.ReplaceTarget(self.replacewithcomboctrl.GetValue())
                self.OnFindNext(event)

        # print ('Replace - This probably needs more work.')

    def OnReplaceAllInDoc(self, event):
        if gWizSTC.GetSelectionStart() != gWizSTC.GetSelectionEnd():
            if self.checkboxinselection.IsChecked():
                selstring = gWizSTC.GetSelectedText()
                selstring = selstring.replace(self.findwhatcomboctrl.GetValue(), self.replacewithcomboctrl.GetValue())
                gWizSTC.ReplaceSelection(selstring)
                gWizSTC.SetFocus()
            else:
                startingpos = gWizSTC.GetCurrentPos()
                startingline = gWizSTC.GetCurrentLine()
                startingposofstartingline = gWizSTC.PositionFromLine(startingline)  #Retrieve the position at the start of a line.
                # print (gWizSTC.LineFromPosition(gWizSTC.GetCurrentPos()) + 1) #Retrieve the line containing a position.

                target = self.findwhatcomboctrl.GetValue()
                newtext = self.replacewithcomboctrl.GetValue()

                gWizSTC.SetText(gWizSTC.GetText().replace(target, newtext))  #Whole Doc
                gWizSTC.GotoLine(startingline)
                # gWizSTC.GotoPos(startingpos - startingposofstartingline)
                gWizSTC.SetFocus()
        else:
            startingpos = gWizSTC.GetCurrentPos()
            startingline = gWizSTC.GetCurrentLine()
            startingposofstartingline = gWizSTC.PositionFromLine(startingline)  #Retrieve the position at the start of a line.
            # print (gWizSTC.LineFromPosition(gWizSTC.GetCurrentPos()) + 1) #Retrieve the line containing a position.

            target = self.findwhatcomboctrl.GetValue()
            newtext = self.replacewithcomboctrl.GetValue()

            gWizSTC.SetText(gWizSTC.GetText().replace(target, newtext))  #Whole Doc
            gWizSTC.GotoLine(startingline)
            # gWizSTC.GotoPos(startingpos - startingposofstartingline)
            gWizSTC.SetFocus()

            # print ('ReplaceAll - This NEEDS more work. InSelection needs done')

    def OnToggleBookmark(self,event):
        '''Add or remove a bookmark from the current line int the bookmark margin.'''
        linenum = gWizSTC.GetCurrentLine()
        # print gWizSTC.MarkerGet(linenum)
        if gWizSTC.MarkerGet(linenum):
            # print gWizSTC.MarkerGet(gWizSTC.GetCurrentLine())
            if gWizSTC.MarkerGet(linenum) == 3:
                gWizSTC.MarkerDelete(linenum, 1)#Mark with user bookmark
            elif gWizSTC.MarkerGet(linenum) == 1 :
                gWizSTC.MarkerAdd(linenum, 1)
        else:
            gWizSTC.MarkerAdd(linenum, 1)#Mark with user bookmark
        # gWizSTC.SetFocus()
        # dprint ('Toggle Bookmark')

    def OnRemoveAllBookmarks(self, event):
        '''Remove all bookmarks from everyline in the document in the bookmark margin.'''
        for i in range(0,3):
            gWizSTC.MarkerDeleteAll(i)
        # dprint ('Remove All Bookmarks')

    def OnHopPreviousBookmark(self, event):
        '''Move caret to the previous bookmarked line in the file.'''
        currentline = gWizSTC.GetCurrentLine()
        linecount = gWizSTC.GetLineCount()
        marker = gWizSTC.MarkerGet(currentline)
        dprint (marker)
        if marker == 0 or marker == 1 or marker == 3:
            currentline -= 1
        findbookmark = gWizSTC.MarkerPrevious(currentline, 2)
        if findbookmark > -1:
            gWizSTC.GotoLine(findbookmark)
        else:
            findbookmark = gWizSTC.MarkerPrevious(linecount, 2)
            if findbookmark > -1:
                gWizSTC.GotoLine(findbookmark)
        # gWizSTC.SetFocus()
        # dprint ('OnHopPreviousBookmark')

    def OnHopNextBookmark(self, event):
        '''Move caret to the next bookmarked line in the file.'''
        currentline = gWizSTC.GetCurrentLine()
        marker = gWizSTC.MarkerGet(currentline)
        if marker == 0 or marker == 1 or marker == 3:
            currentline += 1
        findbookmark = gWizSTC.MarkerNext(currentline, 2)
        if findbookmark > -1:
            gWizSTC.GotoLine(findbookmark)
        else:
            findbookmark = gWizSTC.MarkerNext(0, 2)
            if findbookmark > -1:
                gWizSTC.GotoLine(findbookmark)
        # gWizSTC.SetFocus()
        # dprint ('OnHopNextBookmark')

    def OnSetDefaultBookmarkNumber(self, event):
        '''Set a number for the default bookmark'''
        dialog = wx.TextEntryDialog(self, 'Enter marker number (1-30)', 'Set Default Bookmark Number', '2')
        num = ''
        if dialog.ShowModal() == wx.ID_OK:
            num = int(dialog.GetValue())
        dialog.Destroy()
        if num != '':
            if num <= int(9):
                gWizSTC.MarkerDefineBitmap( 1, gImgIdx['bookmark16.png'] %num)
            elif num <= int(30):
                gWizSTC.MarkerDefineBitmap( 1, gImgIdx['bookmark0%s.png'] %num)
        # gWizSTC.SetFocus()

        # print ('Set Default Bookmark to ' + str(num))

    def OnAppendFindListItem(self, event):
        value = '%s'%self.findwhatcomboctrl.GetValue()
        if value not in basher.settings['bash.installers.wizSTC.FindList']:
            self.gFindlist.append('%s'%self.findwhatcomboctrl.GetValue())
            basher.settings.setChanged('bash.installers.wizSTC.FindList')
        # print basher.settings['bash.installers.wizSTC.FindList']
        #Refresh the combobox list
        self.findwhatcomboctrl.SetItems(basher.settings['bash.installers.wizSTC.FindList'])
        self.findwhatcomboctrl.SetValue(value)

    def OnAppendReplaceListItem(self, event):
        value = '%s'%self.replacewithcomboctrl.GetValue()
        if value not in basher.settings['bash.installers.wizSTC.ReplaceList']:
            self.gReplacelist.append('%s'%self.replacewithcomboctrl.GetValue())
            basher.settings.setChanged('bash.installers.wizSTC.ReplaceList')
        # print basher.settings['bash.installers.wizSTC.ReplaceList']
        #Refresh the combobox list
        self.replacewithcomboctrl.SetItems(basher.settings['bash.installers.wizSTC.ReplaceList'])
        self.replacewithcomboctrl.SetValue(value)

    def OnShowFindReplaceHelpDialog(self, event):
        customdialog = FindReplaceHelpDialog(None, -1, 'Find/Replace Dialog Help')
        customdialog.ShowModal()
        customdialog.Destroy()

    def OnDeleteFindListItem(self, event):
        value = '%s'%self.findwhatcomboctrl.GetValue()
        if value in basher.settings['bash.installers.wizSTC.FindList']:
            self.gFindlist.remove('%s'%self.findwhatcomboctrl.GetValue())
            basher.settings.setChanged('bash.installers.wizSTC.FindList')
        # print basher.settings['bash.installers.wizSTC.FindList']
        try:
            itempos = self.findwhatcomboctrl.FindString(value)
            self.findwhatcomboctrl.Delete(itempos)#Remove item from the combobox list
        except:#No item named that
            pass

    def OnDeleteReplaceListItem(self, event):
        value = '%s'%self.replacewithcomboctrl.GetValue()
        if value in basher.settings['bash.installers.wizSTC.ReplaceList']:
            self.gReplacelist.remove('%s'%self.replacewithcomboctrl.GetValue())
            basher.settings.setChanged('bash.installers.wizSTC.ReplaceList')
        # print basher.settings['bash.installers.wizSTC.ReplaceList']
        try:
            itempos = self.replacewithcomboctrl.FindString(value)
            self.replacewithcomboctrl.Delete(itempos)#Remove item from the combobox list
        except:#No item named that
            pass

    def OnFindReplaceResizeFrameToMinimum(self, event):
        self.SetSize(wx.Size(560,330))

    def OnDestroyFindReplaceDialog(self, event):
        self.Destroy()
        gWizSTC.OneInstanceFindReplace = 0
        gWizSTC.SetFocus()
        # print 'Destroyed FindReplaceDialog'


class FindReplaceHelpDialog(wx.Dialog):
    def __init__(self, parent, id, title):
        wx.Dialog.__init__(self, parent, id, title=u'Find & Replace Dialog Help', size=(400, 410), style=wx.DEFAULT_DIALOG_STYLE)

        HelpMessage = """=== COMBOBOXES ===

These are the main attraction for this dialog and have a few options.
They are drop down Comboboxes and each both read from a saved bash setting list to make up the list of options to display when choosing an option from the dropdown menu.

- Find what? -
The Find what? combobox string(word(s)/text) is what you will be searching for in the document.

- Replace with? -
The Replace with? combobox string(word(s)/text) is what you will be replacing the selection(selected text) in the document with.

- Combobox Options -
Both Find and Replace Comboboxes have two small buttons directly to the right of them.
One for appending the current string to the global Find/Replace Lists.
Another for deleting the current string from the global Find/Replace Lists.
The respective find replace icon to the left of the comboboxes can be left clicked to update the selection from the currently selected text in the editor(this works well as double clicking a word in the editor selects it.) or right clicked to either erase the selection in the combobox. Select some text in the editor and alternate left-right click on the icons to try this out.

With Microsoft Windows, pressing F4 expands a wx.Choice or wx.ComboBox so that the user can use the up/down arrows to make a selection.
Also after the lists become long enough(about 30), the combobox dropdown list will show horizontal scrollers if your platform supports it.

=== BUTTONS ===

- Find Caret button -
Finds the caret in document, insuring it is visible.

- Find Prev button -
Attempts to find the user specified text in the Find what? combobox in the current document. Direction Up/Previous.

- Find Next button -
Attempts to find the user specified text in the Find what? combobox in the current document. Direction Down/Next.

- Find All button -
Attempts to find all occurernces of the user specified text in the Find what? combobox in the current document. Additionally if the Bookmark Line checkbox is checked it will place a bookmark on each line the text is found.

- Replace button -
Replace the selected text in the editor with the user specified text from the Replace with? combobox.

- Replace All button -
Replaces all occurernces of the user specified text in the Find what? combobox in the current document with the user specified text from the Replace with? combobox.

- Close button -
Closes & Destroys the Find/Replace MiniFrame.


=== RADIO BUTTONS ===

---Search Mode Options---
- Normal -

- Extended -
NOT IMPLEMENTED YET!

-Regular Expression -
NOT IMPLEMENTED YET!

---Bookmarks Options---
The bottom row of bookmark buttons are duplicates from the regular bookmark options.
The Set bookmark opens up a dialog to set a particular bookmark you would like to use as the default.
The next button to the right of that is the default bookmark.
The next two buttons are 'hop to previous' & 'hop to next' bookmark in the current document.
The last button removes all Bookmarks from the document.

---Transparency Options---
Change the transparency of the Find/Replace Dialog. This is adjusted with the slider. The miniframes current aplha transparency is displayed to the right of the slider. 30 for near invisibility to 255 for opaque.
- On losing Focus -
The MiniFrame will only be transparent when it doesn't have focus.
- Always -
The MiniFrame will always be transparent when it regardless of focus.


=== CHECK BOXES ===

- Match Whole Word Only -
A match will only occur if the characters before and after the match are not word characters.

- Match Case -
A match will only occur if the case of the search string(Find what?) and the candidate string match. For example if you are searching for 'Yes', then it would pass up ('YES', 'yes', 'YeS', anything NOT exactly the same as etc...) while performing the search.

- Wrap Around -
If you have hit the end or the begining of the document(depending on which way you are searching), this will allow the search to continue from the opposite end of the document.

- Bookmark Line -
If the 'Bookmark Line' checkbox is checked it will place a bookmark on each line the text is found. This is used in conjunction with the Find All button

- In Selection -
If the 'In Selection' checkbox ischecked, this will only replace the used specified text from the Find what? combobox with the user specified text from the Replace with? in the currently selected text(your selection) in the editor.
"""

        panel = wx.Panel(self, -1)
        panel.SetBackgroundColour('#222222')

        staticbox = wx.StaticBox(panel, -1, u'Help! I lost... What do I do?', pos=(5, 5), size=(380, 320))
        staticbox.SetForegroundColour('#FFFFFF')

        self.helpCtrl = wx.TextCtrl(panel, -1, u'%s'%HelpMessage, (15, 25), (360,290), style=wx.VSCROLL | wx.TE_MULTILINE | wx.TE_WORDWRAP | wx.TE_RICH2 | wx.TE_READONLY)

        self.helpCtrl.SetForegroundColour('#000000')
        self.helpCtrl.SetBackgroundColour('#CBFF9E')

        points = self.helpCtrl.GetFont().GetPointSize()  # get the current size
        bold = wx.Font(points+7, wx.ROMAN, wx.NORMAL, wx.BOLD, True)#, wx.ITALIC
        # self.helpCtrl.SetStyle(44, 55, wx.TextAttr("RED", "YELLOW"))
        # Make the headers bold & underlined

        headerList = [u'=== COMBOBOXES ===',u'=== BUTTONS ===',u'=== RADIO BUTTONS ===',u'=== CHECK BOXES ===']
        for header in headerList:
            match = re.search(header, HelpMessage)
            foundpostions = (match.span())
            self.helpCtrl.SetStyle(foundpostions[0], foundpostions[1], wx.TextAttr(wx.NullColour, wx.NullColour, bold))

        standardblackwhitebitmapbutton = wx.BitmapButton(panel, -1, gImgIdx['ffffff-000000.png'])
        consolecolorbitmapbutton = wx.BitmapButton(panel, -1, gImgIdx['000000-ffffff.png'])

        lightbluecolorbitmapbutton = wx.BitmapButton(panel, -1, gImgIdx['ffffff-bfd4ff.png'])
        lighttancolorbitmapbutton = wx.BitmapButton(panel, -1, gImgIdx['ffffff-ffeabf.png'])

        self.closebutton = GB.GradientButton(panel, label=u'Close', pos=(310, 330), size=(70,30))#, style=wx.BORDER
        self.closebutton.SetForegroundColour('#000000')
        self.closebutton.SetBackgroundColour('#000000')
        self.closebutton.SetTopStartColour(wx.Colour(255, 255, 255, 255)) # wx.Colour(R, G, B, A)
        self.closebutton.SetTopEndColour(wx.Colour(202, 247, 185, 255))
        self.closebutton.SetBottomStartColour(wx.Colour(202, 247, 185, 255))
        # self.closebutton.SetBottomEndColour(wx.Colour(183, 241, 176, 255))
        self.closebutton.SetBottomEndColour(wx.Colour(0, 0, 0, 255))
        self.closebutton.SetPressedTopColour(wx.Colour(183, 241, 176, 255))
        self.closebutton.SetPressedBottomColour('#FFFFFF')

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(panel, 1, wx.EXPAND)

        sboxsizer = wx.StaticBoxSizer(staticbox, wx.VERTICAL)
        sboxsizer.Add(self.helpCtrl, 1, wx.EXPAND | wx.ALL, 5 )

        pvsizer = wx.BoxSizer(wx.VERTICAL)
        phsizer = wx.BoxSizer(wx.HORIZONTAL)

        pvsizer.Add(sboxsizer, 1, wx.EXPAND | wx.ALL, 8)

        phsizer.Add(standardblackwhitebitmapbutton, 0, wx.ALL, 8)
        phsizer.Add(consolecolorbitmapbutton      , 0, wx.ALL, 8)
        phsizer.Add(lightbluecolorbitmapbutton    , 0, wx.ALL, 8)
        phsizer.Add(lighttancolorbitmapbutton     , 0, wx.ALL, 8)

        pvsizer.Add(phsizer)
        pvsizer.Add(self.closebutton     , 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        panel.SetSizer(pvsizer)

        self.SetSizer(vsizer)

        standardblackwhitebitmapbutton.Bind(wx.EVT_BUTTON, self.OnStandardStyleColor, id=-1)
        consolecolorbitmapbutton.Bind(wx.EVT_BUTTON, self.OnConsoleStyleColor, id=-1)
        lightbluecolorbitmapbutton.Bind(wx.EVT_BUTTON, self.OnLightBlueStyleColor, id=-1)
        lighttancolorbitmapbutton.Bind(wx.EVT_BUTTON, self.OnLightTanStyleColor, id=-1)
        self.closebutton.Bind(wx.EVT_BUTTON, self.OnDestroyCustomDialog, id=-1)
        self.Bind(wx.EVT_CLOSE, self.OnDestroyCustomDialog)

        self.SetIcon(wx.Icon(gImgDir + os.sep + 'help16.png', wx.BITMAP_TYPE_PNG))

    def OnStandardStyleColor(self, event):
        self.helpCtrl.SetForegroundColour('#000000')
        self.helpCtrl.SetBackgroundColour('#FFFFFF')

        self.closebutton.SetTopStartColour(wx.Colour(255, 255, 255, 255))
        self.closebutton.SetTopEndColour(wx.Colour(128, 128, 128, 255))
        self.closebutton.SetBottomStartColour(wx.Colour(128, 128, 128, 255))
        self.closebutton.SetBottomEndColour(wx.Colour(0, 0, 0, 255))

    def OnConsoleStyleColor(self, event):
        #Console Style: White on Black
        self.helpCtrl.SetForegroundColour('#FFFFFF')
        self.helpCtrl.SetBackgroundColour('#000000')

    def OnLightBlueStyleColor(self, event):
        self.helpCtrl.SetForegroundColour('#000000')
        self.helpCtrl.SetBackgroundColour('#BFD4FF')

    def OnLightTanStyleColor(self, event):
        self.helpCtrl.SetForegroundColour('#000000')
        self.helpCtrl.SetBackgroundColour('#FFEABF')

        self.closebutton.SetTopStartColour(wx.Colour(255, 221, 151, 255))
        self.closebutton.SetTopEndColour(wx.Colour(138, 119, 80, 255))
        self.closebutton.SetBottomStartColour(wx.Colour(138, 119, 80, 255))
        self.closebutton.SetBottomEndColour(wx.Colour(0, 0, 0, 255))

    def OnDestroyCustomDialog(self, event):
        self.Destroy()
        # print 'Destroyed FindReplaceHelpDialog Class'

class DebugStdOutStdErrMiniFrame(wx.Frame):
    ''' General Floating Toolbar. '''
    def __init__(self, parent, id):
        wx.Frame.__init__(self, parent, -1, title=u'wxPython: stdout', size=(-1, -1), style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT)

        global gDebugFrame
        gDebugFrame = self

        # self.stdOUTStdERR = stc.StyledTextCtrl(self, -1)#Doesn't work here!
        self.stdOUTStdERR = wx.TextCtrl(self, -1, '', style=wx.VSCROLL | wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_READONLY | wx.TE_WORDWRAP | wx.TE_NOHIDESEL)#| wx.HSCROLL

        openingMessage = u'MCow Debug Print Console (c) 2011-2012\n'
        redirectMessage = u'Redirecting wx.Python: stdout...\n'

        self.stdOUTStdERR.WriteText(openingMessage)
        self.stdOUTStdERR.WriteText(redirectMessage)

        dprint('Usage:\n dprint(string)')
        dprint('Arguments:\n string: a string or variable containing one.')
        dprint('Example:\n dprint(\'Write Something to this Console!\')\n\n')

        self.stdOUTStdERR.SetFont(wx.Font(10, wx.SWISS , wx.NORMAL, wx.NORMAL, False, u'%(mono)s' %faces))
        points = self.stdOUTStdERR.GetFont().GetPointSize()  # get the current size
        # Make the header bold & underlined
        bold = wx.Font(points+6, wx.ROMAN, wx.NORMAL, wx.BOLD, True)#, wx.ITALIC

        self.stdOUTStdERR.SetBackgroundColour('#000000')
        self.stdOUTStdERR.SetForegroundColour('#FFFFFF')

        self.stdOUTStdERR.SetStyle(0, len(openingMessage), wx.TextAttr(wx.NullColour, wx.NullColour, bold))

        sys.stdout = self.stdOUTStdERR    #Writes standard output the stc. #Example: print ('this')
        # sys.stderr = self.stdOUTStdERR    #Writes standard errors the stc. #Example: Traceback (most recent call last)

        self.stdOUTStdERR.WriteText(u'Traceback (most recent call last):\n  File "C:\\Program Files\\Steam\\steamapps\\common\\skyrim\\Mopy\\bash\\wizSTC.py", line -wb299, in OnTest\n    causeTraceback\nHahaGotchaError: global name \'causeTraceback\' is still defined in \'itsNormalPlace\' :)\n')

        print ('\nimport this\n')
        import this

        self.stdOUTStdERR.SetSelection(0,0)#Set the view to 0(start of text) at first view.

        for m in re.finditer(u'Traceback', self.stdOUTStdERR.GetValue()):
            self.stdOUTStdERR.SetStyle(m.start(), m.end(), wx.TextAttr('#FF0000', '#000000'))#RED
            # print '%02d-%02d' % (m.start(), m.end())

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        hsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        hsizer1.Add(self.stdOUTStdERR, 1, wx.EXPAND | wx.ALL, 0)
        self.SetSizer(hsizer1)
        self.Fit()

        self.SetClientSize(hsizer1.GetSize())
        self.SetMinSize((600,300))
        self.Centre()

        gImgStcDir = (u'%s' %bosh.dirs['images'].join(u'stc'))
        self.SetIcon(wx.Icon(gImgStcDir + os.sep + u'debug16.png', wx.BITMAP_TYPE_PNG))

    def OnClose(self, event):
        self.Hide()

class FloatingToolbar(wx.MiniFrame):
    ''' General Floating Toolbar. '''
    def __init__(self, parent, id):
        wx.MiniFrame.__init__(self, parent, -1, title='Toolbar', size=(-1, -1), style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT)

        undotool = wx.BitmapButton(self, ID_UNDO, gImgIdx['undo16.png'])
        undotool.SetToolTipString(u'Undo')
        undotool.Bind(wx.EVT_BUTTON, gWizSTC.OnUndo)
        redotool = wx.BitmapButton(self, ID_REDO, gImgIdx['redo16.png'])
        redotool.SetToolTipString(u'Redo')
        redotool.Bind(wx.EVT_BUTTON, gWizSTC.OnRedo)
        cuttool = wx.BitmapButton(self, ID_CUT, gImgIdx['cut16.png'])
        cuttool.SetToolTipString(u'Cut')
        cuttool.Bind(wx.EVT_BUTTON, gWizSTC.OnCut)
        copytool = wx.BitmapButton(self, ID_COPY, gImgIdx['copy16.png'])
        copytool.SetToolTipString(u'Copy')
        copytool.Bind(wx.EVT_BUTTON, gWizSTC.OnCopy)
        pastetool = wx.BitmapButton(self, ID_PASTE, gImgIdx['paste16.png'])
        pastetool.SetToolTipString(u'Paste')
        if gWizSTC.rect_selection_clipboard_flag:
            pastetool.Bind(wx.EVT_BUTTON, gWizSTC.OnColumnPasteFromContextMenu)
        else:
            pastetool.Bind(wx.EVT_BUTTON, gWizSTC.OnPasteFromContextMenu)
        selectalltool = wx.BitmapButton(self, ID_SELECTALL, gImgIdx['selectall16.png'])
        selectalltool.SetToolTipString(u'Select All')
        selectalltool.Bind(wx.EVT_BUTTON, gWizSTC.OnSelectAll)
        togglecommenttool = wx.BitmapButton(self, ID_COMMENT, gImgIdx['togglecomment16.png'])
        togglecommenttool.SetToolTipString(u'Toggle Comment')
        togglecommenttool.Bind(wx.EVT_BUTTON, gWizSTC.OnToggleComment)
        removetrailingwhitespacetool = wx.BitmapButton(self, ID_REMTRAILWHITESPACE, gImgIdx['removetrailingspaces16.png'])
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
        gWizSTC.SetFocus()
        self.Destroy()


class ChecklistBeforePackageingYourMod(wx.Frame):
    ''' Reminder checklist for mod authors of things they should do before packaging a mod for release(RELz). '''
    def __init__(self, parent, id):
        wx.Frame.__init__(self, parent, -1, title=u'Reminder Checklist', size=(400, 400), style=wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT)

        s1 = u' Reminder checklist before packaging your mod for release(RELz).\n Have you...'
        s2 = u'Written a Readme(MyModName_Readme.txt)?'
        s3 = u'Written a Install Wizard(wizard.txt)?'
        s4 = u'Checked for missing Resources(Meshes/Textures/Icons/etc...)?'
        s5 = u'Optimised Textures?'
        s6 = u'Cleaned your esp/m of UDR and ITM records?'
        s7 = u'Made sure your version number is correct(espm/descrition field/readmes/etc...)?'
        s8 = u'Placed correct Bash Tags and reported your mod to BOSS?'
        s9 = u'Brushed you teeth today? :)'
        self.strList = [s1,s2,s3,s4,s5,s6,s7,s8,s9]
        # s10 = u''

        self.SetBackgroundColour('#F6F68C')
        vsizer1 = wx.BoxSizer(wx.VERTICAL)
        self.cbList = []
        for i in range(0,len(self.strList)):
            if i == 0:
                st = wx.StaticText(self, -1, self.strList[i], style=wx.BORDER)
                st.SetBackgroundColour('#E6E64C')
                vsizer1.Add(st, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
            else:
                cb = 'self.cb%d' %i
                cb = wx.CheckBox(self, -1, self.strList[i], style=wx.BORDER)
                vsizer1.Add(cb, 0, wx.EXPAND | wx.ALL, 3)
                self.cbList.append(cb)
        # print self.cbList

        staticline = wx.StaticLine(self, -1, (-1, -1), (-1, -1), wx.LI_HORIZONTAL)

        self.addtextchecklistbutton = wx.Button(self, wx.NewId(), 'Add Text CheckList', (-1, -1), wx.DefaultSize)
        self.closebutton = wx.Button(self, wx.NewId(), 'Close', (-1, -1), wx.DefaultSize)

        hsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        hsizer1.AddStretchSpacer()
        hsizer1.Add(self.addtextchecklistbutton, 0, wx.ALIGN_RIGHT | wx.LEFT, 10)
        hsizer1.Add(self.closebutton, 0, wx.ALIGN_RIGHT | wx.LEFT, 10)

        vsizer1.Add(staticline, 0, wx.GROW | wx.ALL , 8)
        vsizer1.Add(hsizer1, 0, wx.EXPAND | wx.ALL, 8)
        self.SetMinSize((450, 285))
        self.SetSizer(vsizer1)
        self.Fit()

        self.Centre()
        self.Bind(wx.EVT_BUTTON, self.OnAddTextCheckList)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.closebutton.Bind(wx.EVT_BUTTON, self.OnClose)
        self.SetIcon(wx.Icon(gImgStcDir + os.sep + u'check16.png',wx.BITMAP_TYPE_PNG))

    def OnAddTextCheckList(self, event):
        for i in range(0,len(self.strList)):
            if i == 0:
                gWizSTC.AddText(self.strList[i] + u'\n')
            else:
                if self.cbList[i-1].IsChecked():
                    gWizSTC.AddText(u'[X] ' + self.strList[i] + u'\n')
                else:
                    gWizSTC.AddText(u'[ ] ' + self.strList[i] + u'\n')

    def OnClose(self, event):
        self.Destroy()

class InstallersTabTips(wx.Frame):
    ''' The tip of the day dialog. '''
    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, -1, title='Installers Tab Tips', size=(400, 400), style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)#| wx.FRAME_FLOAT_ON_PARENT

        # Read this data file in as a list
        tipsin = open(u'%s' %bosh.dirs['bash'].join(u'installerstabtips.txt'), 'r' )
        self.tips_list = tipsin.readlines()
        tipsin.close()

        self.tipnum = random.randint(0, len(self.tips_list)) #Set tipnum to start on a random tip
        if self.tipnum == len(self.tips_list): self.tipnum = self.tipnum - 1#Avoid random index out of range error

        self.tipbox = wx.TextCtrl(self, wx.NewId(), str(self.tips_list[self.tipnum]), (-1, -1), (-1, 200), style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_NOHIDESEL)

        staticline = wx.StaticLine(self, -1, (-1, -1), (-1, -1), wx.LI_HORIZONTAL)

        self.nexttipbutton = wx.Button(self, wx.NewId(), 'Next Tip', (-1, -1), wx.DefaultSize)
        self.closebutton = wx.Button(self, wx.NewId(), 'Close', (-1, -1), wx.DefaultSize)

        # The seamless tiling background image.
        self.backgroundbitmap = gImgIdx['seamlessbackgroundtile256.png']

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

        self.SetIcon(wx.Icon(gImgStcDir + os.sep + u'lightbulb16.png', wx.BITMAP_TYPE_PNG))

    def OnNextTip(self, event):
        # test = random.randint(0, len(self.tips_list))
        # dprint (len(self.tips_list))
        # dprint (test)
        # dprint (str(self.tips_list[test]))

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

        while x < sz.width:
            y = 0
            while y < sz.height:
                dc.DrawBitmap(self.backgroundbitmap, x, y)
                y = y + h
            dc.DrawBitmap(self.backgroundbitmap, x, y)
            x = x + w
        # print('TiledBackground')

    def OnClose(self, event):
        self.Destroy()

class DraggableRMouseGestureMenu2(wx.MiniFrame):
    '''The goal here was to make a easily generated draggable menu in a class that can be
    easily copied and adjusted in the code. Made with good ol fashoned absolute positioning,
    a 20 pixel image width and 20 pixel button height. The buttons names and bound functions
    are generated from the Ordered Dictionary. Native OS Colors. REQz by Alt3rn1ty '''
    #AllTests: 1920x1080 resolution with one single column disabled draggable header and...
    #                                                            Option1       , Option2
    #TestOption1: ...and 38 single column buttons ==           len(Dict) = 79, if i in []
    #TestOption2: ...and 78 double column buttons ==           len(Dict) = 79, if i in [1]
    #TestOption3: ...and 11 Single/52 double column buttons == len(Dict) = 66, if i in [12]
    def __init__(self, parent, style):
        wx.MiniFrame.__init__(self, parent, style=wx.FRAME_FLOAT_ON_PARENT | wx.FRAME_NO_TASKBAR)
        self.menucolor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENU)
        self.menubarcolor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUBAR)
        # self.menuhilightcolor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUHILIGHT)
        # self.menutextcolor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUTEXT)
        # self.buttonfacecolor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)

        self.SetBackgroundColour(self.menucolor)

        gImgDir = u'%s' %bosh.dirs['images']
        gImgStcDir = u'%s' %bosh.dirs['images'].join(u'stc')

        # 1st entry is the disabled header, the rest are...
        # String buttonNames : functionToBind = to numOfButns
        buttonNames = OrderedDict([
            ('R MGM 2 Wizard' , gWizSTC.OnPass),
            ('RequireVersions' , gWizSTC.OnRequireVersionsSkyrim),
            ('SelectSubPackage' , gWizSTC.OnSelectSubPackage),
            ('DeSelectSubPackage' , gWizSTC.OnDeSelectSubPackage),
            ('SelectAll' , gWizSTC.OnSelectAllKeyword),
            ('DeSelectAll' , gWizSTC.OnDeSelectAll),
            ('SelectEspm' , gWizSTC.OnSelectEspm),
            ('DeSelectEspm' , gWizSTC.OnDeSelectEspm),
            ('SelectOne' , gWizSTC.OnSelectOne),
            ('SelectMany' , gWizSTC.OnSelectMany),
            ('"","","",\\' , gWizSTC.OnChoicesX02),
            ('Case ""' , gWizSTC.OnCase),
            ('Break' , gWizSTC.OnBreak),
            ('EndSelect' , gWizSTC.OnEndSelect),
            # ('b15' , gWizSTC.OnPass),
            # ('b16' , gWizSTC.OnPass),
            # ('b17' , gWizSTC.OnPass),
            # ('b18' , gWizSTC.OnPass),
            # ('b19' , gWizSTC.OnPass),
            # ('b20' , gWizSTC.OnPass),
            # ('b21' , gWizSTC.OnPass),
            # ('b22' , gWizSTC.OnPass),
            # ('b23' , gWizSTC.OnPass),
            # ('b24' , gWizSTC.OnPass),
            # ('b25' , gWizSTC.OnPass),
            ])

        i = 0
        btnsz = (240, 20)#Adjustable Width ONLY. Fixed height of 20px
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
            #if i in [] = one column of buttons
            #if i in [1] = one header/all doubled column buttons afterwards
            #if i in [1<#] = Any every num bigger than 1 generates a header and #-1 amount of single column buttons, then the rest are doubled column afterwards
            if i in [1]:#Only use one int in the list.
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

        self.SetSize((btnsz[0]+border*2+26, menuheight))

        dragpic = wx.StaticBitmap(self, -1, gImgIdx['wizbain20x100.png'], pos=(btnsz[0]+border*2, border))
        dragpic.SetBackgroundColour(self.menucolor)

        self.closebutton = wx.StaticBitmap(self, -1, gImgIdx['stopsign20.png'], pos=(btnsz[0]+border*2, menuheight-border*2-20))
        self.closebutton.SetBackgroundColour(self.menucolor)

        for draggableobject in [self, dragpic]:
            draggableobject.Bind(wx.EVT_LEFT_DOWN, self.OnMouseLeftDown)
            draggableobject.Bind(wx.EVT_MOTION, self.OnMouseMotion)
            draggableobject.Bind(wx.EVT_LEFT_UP, self.OnMouseLeftUp)
            # draggableobject.Bind(wx.EVT_RIGHT_UP, self.OnDestroyMenu)

        self.closebutton.Bind(wx.EVT_LEFT_DOWN, self.OnDestroyMenu)

        wx.CallAfter(self.Refresh)

    def OnMouseLeftDown(self, event):
        try:
            self.Refresh()
            self.ldPos = event.GetEventObject().ClientToScreen(event.GetPosition())
            self.wPos = self.ClientToScreen((0,0))
            self.CaptureMouse()
        except:#DCLICK error
            pass
        gWizSTC.SetFocus()

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
        gWizSTC.SetFocus()

    def OnDestroyMenu(self, event):
        self.Show(False)
        self.Destroy()
        gWizSTC.dragmenu2 = 0


class WizBAINEditorHelpGeneralDialog(wx.Dialog):
    ''' Whoha and general propaganda from the TES4WizBAIN author who originally made this fine editor:
    Mooo, Metallicow, Metalio Bovinus. '''
    def __init__(self, parent, id):
        wx.Dialog.__init__(self, parent, id, title=u'WizBAIN Editor Help-General', size=(695, 550), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.THICK_FRAME)

        HelpMessage = (
        u'The WizBAIN Editor is for mod authors and players to write fancy install scripts for their packages(called wizards),'\
        u'thus easing headaches and confusion during installation by all users. The Editor is primarily mouse gesture/context '\
        u'menu based and may not be obvious to a casual or first time user.\nThe mouse gesture menus are based off of a NUMPad, '\
        u'such as are on many keyboards. NUMPad 5 would be the default right or middle click context. To access the other menus '\
        u'just mouse gesture outward from 5 to another number. An example of how to open the right click mouse gesture 8 menu(R MGM 8) '\
        u'would be to first right click and hold the mouse button down and move your mouse forward/up and release.\n'\
        u'The WizBAIN Editor is currently a PORT/WIPz\n'\
        u'\n'\
        u'[7][8][9]\n'\
        u'[4][5][6]\n'\
        u'[1][2][3]\n'\
        u'\n'\
        u'Enjoy\n    ~Metallicow, TES4WizBAIN Dev\n'
        )

        self.SetBackgroundColour('#4E4E4E')

        staticbox = wx.StaticBox(self, -1, u'Help! I lost... What do I do?', pos=(5, 5), size=(380, 320))
        staticbox.SetForegroundColour('#FFFFFF')

        self.helpCtrl = WizBAINStyledTextCtrl(self, wx.ID_ANY)
        try:
            self.helpCtrl.SetTextUTF8(u'%s'%HelpMessage)
        except:
            self.helpCtrl.SetText(u'%s'%HelpMessage)
        self.helpCtrl.SetReadOnly(True)
        self.helpCtrl.SetWrapMode(True)

        numpad = wx.StaticBitmap(self, -1, wx.Bitmap(gImgDir + os.sep + u'readme' + os.sep + u'numpad.png', wx.BITMAP_TYPE_PNG))
        numpad.SetToolTipString('Visualize standard Right Click is numpad 5')
        
        gif = wx.animate.Animation(u'%s' %gImgDir + os.sep + u'readme' + os.sep + u'mouse_gesture_animation.gif')
        self.aniCtrl = wx.animate.AnimationCtrl(self, -1, gif)
        self.aniCtrl.SetUseWindowBackgroundColour()
        self.aniCtrl.Play()
        self.aniCtrl.SetToolTipString('Example of Right Mouse Gesture Menu 9')

        self.randombutton = platebtn.PlateButton(self, wx.ID_ANY, '', wx.Bitmap(gImgDir + os.sep + 'mcowavi32.png'), style=platebtn.PB_STYLE_GRADIENT)
        self.randombutton.SetToolTipString('Click on me\nfor a\nRandom\nMooo\nThought bubble!')
        # self.randombutton.SetBackgroundColour('#4E4E4E')
        self.randombutton.Bind(wx.EVT_BUTTON, self.OnRandomFlatMenu)
        
        self.closebutton = GB.GradientButton(self, -1, gImgIdx['stopsign20.png'], label=u' Close', pos=(310, 330), size=(70,30))#, style=wx.BORDER
        self.closebutton.SetForegroundColour('#FFFFFF')
        self.closebutton.SetBackgroundColour('#E0E0E0')
        self.closebutton.SetTopStartColour(wx.Colour(149, 0, 0, 35)) # wx.Colour(R, G, B, A)
        self.closebutton.SetTopEndColour(wx.Colour(104, 0, 0, 118))
        self.closebutton.SetBottomStartColour(wx.Colour(72, 0, 0, 161))
        self.closebutton.SetBottomEndColour(wx.Colour(37, 0, 0, 194))
        self.closebutton.SetPressedTopColour(wx.Colour(224, 224, 224, 255))
        self.closebutton.SetPressedBottomColour('#505050')
        self.closebutton.SetToolTipString('Close')

        vsizer = wx.BoxSizer(wx.VERTICAL)

        sboxsizer = wx.StaticBoxSizer(staticbox, wx.VERTICAL)
        sboxsizer.Add(self.helpCtrl, 1, wx.EXPAND | wx.ALL, 5 )

        vsizer1 = wx.BoxSizer(wx.VERTICAL)
        vsizer2 = wx.BoxSizer(wx.VERTICAL)
        hsizer1 = wx.BoxSizer(wx.HORIZONTAL)

        vsizer1.Add(sboxsizer, 1, wx.EXPAND | wx.ALL, 8)

        hsizer1.Add(numpad      , 0, wx.ALIGN_CENTRE | wx.ALL, 8)
        hsizer1.Add(self.aniCtrl      , 0, wx.EXPAND | wx.ALL, 8)

        vsizer1.Add(hsizer1)
        vsizer2.Add(self.randombutton     , 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        vsizer2.Add(self.closebutton     , 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        
        hsizer1.AddStretchSpacer(20)
        # hsizer1.AddSpacer(20)
        hsizer1.Add(vsizer2, 0, wx.ALIGN_CENTRE | wx.ALL)

        # self.SetSizer(vsizer1)
        vsizer.Add(vsizer1, 1, wx.EXPAND | wx.ALL)

        self.SetSizer(vsizer)

        self.closebutton.Bind(wx.EVT_BUTTON, self.OnDestroyCustomDialog, id=-1)
        self.Bind(wx.EVT_CLOSE, self.OnDestroyCustomDialog)

        self.backgroundbitmap = gImgIdx['gridart217x90.png']
        if useWXVER == '2.8':
            self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        elif useWXVER == '2.9':
            self.SetBackgroundStyle(wx.BG_STYLE_ERASE)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnDrawBackground)
        
        self.SetIcon(wx.Icon(gImgDir + os.sep + 'help16.png', wx.BITMAP_TYPE_PNG))

    def OnRandomFlatMenu(self, event):
        flatmenu = FM.FlatMenu()
        
        randcols = random.randint(1,3)
        flatmenu.SetNumberColumns(randcols)

        randmenuitems = random.randint(7,50)

        for i in range(0,randmenuitems):
            randbmp = random.randint(0,6)
            if   randbmp == 0: bmp = gImgIdx['null16.png']
            elif randbmp == 1: bmp = gImgIdx['star16.png']
            elif randbmp == 2: bmp = gImgIdx['cheese16.png']
            elif randbmp == 3: bmp = gImgIdx['python16.png']
            elif randbmp == 4: bmp = gImgIdx['yingyang16.png']
            elif randbmp == 5: bmp = gImgIdx['wizardhat16.png']
            elif randbmp == 6: bmp = gImgIdx['black16.png']

            if randcols == 1 and i in [4,random.randint(8,25),random.randint(20,35),random.randint(35,49)]:
                flatmenu.AppendSeparator()
                continue

            if randbmp == 3 and i != 1:
                newid = wx.NewId()
                menuItem = FM.FlatMenuItem(flatmenu, newid, u'Menu Item %s'%i, '', wx.ITEM_NORMAL, None, bmp)
                if random.randint(0,1) == 1:
                    menuItem.SetHotBitmap(gImgIdx['python_red16.png'])
            elif randbmp == 5 and i != 1:
                newid = wx.NewId()
                menuItem = FM.FlatMenuItem(flatmenu, newid, u'Menu Item %s'%i, '', wx.ITEM_NORMAL, None, bmp)
                if random.randint(0,1) == 1:
                    menuItem.SetHotBitmap(gImgIdx['wizardhatred16.png'])
            elif randbmp == 6 and i != 1:
                newid = wx.NewId()
                menuItem = FM.FlatMenuItem(flatmenu, newid, u'Menu Item %s'%i, '', wx.ITEM_NORMAL, None, bmp)
                if random.randint(0,1) == 1:
                    menuItem.SetHotBitmap(gImgIdx['test16.png'])
            else:
                newid = wx.NewId()
                menuItem = FM.FlatMenuItem(flatmenu, newid, u'Menu Item %s'%i, '', wx.ITEM_NORMAL, None, bmp)
            if i == 1:
                menuItem.SetNormalBitmap(gRmbImg)
                menuItem.SetText(u'Context Item %s'%i)
                context_menu = FM.FlatMenu()# Create a context menu
                contextMenuItem = FM.FlatMenuItem(context_menu, wx.ID_ANY, u'Bla Bla Blaa '*5, '', wx.ITEM_NORMAL, None, gImgIdx['contexthelp24.png'])
                context_menu.AppendItem(contextMenuItem)
                menuItem.SetContextMenu(context_menu)
                
            randtextchance = random.randint(0,4)
            randtext = ['Buggy','Enhancement','Random','Error']
            if randtextchance == 1 and i != 1:
                randtextchance = randtext[random.randint(0,3)]
                if randtextchance == 'Error':
                    menuItem.SetNormalBitmap(wx.Bitmap(gImgDir + os.sep + 'errormarker16.png', wx.BITMAP_TYPE_PNG))
                menuItem.SetText(u'%s Item %s'%(randtextchance,i))

            randdisablechance = random.randint(0,6)
            if randdisablechance == 6 and i != 1:
                menuItem.SetText(u'Disabled Item %s'%i)
                menuItem.Enable(False)
                
            flatmenu.AppendItem(menuItem)

        pos = wx.GetMousePosition()
        flatmenu.Popup(wx.Point(pos[0]-8, pos[1]-8), self)

    def OnDrawBackground(self, event):
        dc = wx.ClientDC(self)

        sz = self.GetClientSize()
        w = self.backgroundbitmap.GetWidth()
        h = self.backgroundbitmap.GetHeight()
        x = 0
        y = 0

        while x < sz.width:
            y = 0
            while y < sz.height:
                dc.DrawBitmap(self.backgroundbitmap, x, y)
                y = y + h
            dc.DrawBitmap(self.backgroundbitmap, x, y)
            x = x + w

        self.randombutton.Refresh()
        # print('TiledBackground')

    def OnDestroyCustomDialog(self, event):
        self.Destroy()
        # print 'Destroyed Help Class'

class DraggableScrolledPanel(wx.MiniFrame):
    '''The goal here was to make a easily generated draggable menu in a class that can be
    easily copied and adjusted in the code. Made with good ol fashoned absolute positioning,
    a 20 pixel image width and 20 pixel button height. The buttons names and bound functions
    are generated from the Ordered Dictionary. Native OS Colors.  '''

    def __init__(self, parent, style):
        wx.MiniFrame.__init__(self, parent, style=wx.FRAME_FLOAT_ON_PARENT | wx.FRAME_NO_TASKBAR)
        self.menucolor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENU)
        self.menubarcolor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUBAR)

        self.SetBackgroundColour(self.menucolor)
        mfsize = (200,450)
        dragonscroll_vsizer = wx.BoxSizer(wx.VERTICAL)

        self.dragonscrollpanel = scrolled.ScrolledPanel(self, -1, size=(mfsize[0],mfsize[1]), style = wx.SUNKEN_BORDER)
        self.dragonscrollpanel.SetBackgroundColour(self.menucolor)

        gImgDir = u'%s' %bosh.dirs['images']
        gImgStcDir = u'%s' %bosh.dirs['images'].join(u'stc')

        # 1st entry is the disabled header, the rest are...
        # String buttonNames : functionToBind = to numOfButns
        buttonNames = OrderedDict([
            ('R MGM 2 Wizard' , gWizSTC.OnPass),
            ('RequireVersions' , gWizSTC.OnRequireVersionsSkyrim),
            ('SelectSubPackage' , gWizSTC.OnSelectSubPackage),
            ('DeSelectSubPackage' , gWizSTC.OnDeSelectSubPackage),
            ('SelectAll' , gWizSTC.OnSelectAllKeyword),
            ('DeSelectAll' , gWizSTC.OnDeSelectAll),
            ('SelectEspm' , gWizSTC.OnSelectEspm),
            ('DeSelectEspm' , gWizSTC.OnDeSelectEspm),
            ('SelectOne' , gWizSTC.OnSelectOne),
            ('SelectMany' , gWizSTC.OnSelectMany),
            ('"","","",\\' , gWizSTC.OnChoicesX02),
            ('Case ""' , gWizSTC.OnCase),
            ('Break' , gWizSTC.OnBreak),
            ('EndSelect' , gWizSTC.OnEndSelect),
            ('b15' , gWizSTC.OnPass),
            ('b16' , gWizSTC.OnPass),
            ('b17' , gWizSTC.OnPass),
            ('b18' , gWizSTC.OnPass),
            ('b19' , gWizSTC.OnPass),
            ('b20' , gWizSTC.OnPass),
            ('b21' , gWizSTC.OnPass),
            ('b22' , gWizSTC.OnPass),
            ('b23' , gWizSTC.OnPass),
            ('b24' , gWizSTC.OnPass),
            ('b25' , gWizSTC.OnPass),
            ('b26' , gWizSTC.OnPass),
            ('b27' , gWizSTC.OnPass),
            ('b28' , gWizSTC.OnPass),
            ('b29' , gWizSTC.OnPass),
            ('b30' , gWizSTC.OnPass),
            ('b31' , gWizSTC.OnPass),
            ('b32' , gWizSTC.OnPass),
            ('b33' , gWizSTC.OnPass),
            ('b34' , gWizSTC.OnPass),
            ('b35' , gWizSTC.OnPass),
            ('b36' , gWizSTC.OnPass),
            ('b37' , gWizSTC.OnPass),
            ('b38' , gWizSTC.OnPass),
            ('b39' , gWizSTC.OnPass),
            ('b40' , gWizSTC.OnPass),
            ('b41' , gWizSTC.OnPass),
            ('b42' , gWizSTC.OnPass),
            ('b43' , gWizSTC.OnPass),
            ('b44' , gWizSTC.OnPass),
            ('b45' , gWizSTC.OnPass),
            ('b46' , gWizSTC.OnPass),
            ('b47' , gWizSTC.OnPass),
            ('b48' , gWizSTC.OnPass),
            ('b49' , gWizSTC.OnPass),
            ('b50' , gWizSTC.OnPass),
            ('b51' , gWizSTC.OnPass),
            ('b52' , gWizSTC.OnPass),
            ('b53' , gWizSTC.OnPass),
            ('b54' , gWizSTC.OnPass),
            ('b55' , gWizSTC.OnPass),
            ('b56' , gWizSTC.OnPass),
            ('b57' , gWizSTC.OnPass),
            ('b58' , gWizSTC.OnPass),
            ('b59' , gWizSTC.OnPass),
            ('b60' , gWizSTC.OnPass),
            ('b61' , gWizSTC.OnPass),
            ])

        border = 4
        disableheader = 0
        for key, value in buttonNames.iteritems():
            if disableheader == 0:
                key = wx.Button(self.dragonscrollpanel, -1, u' %s' %str(key))
                key.SetBackgroundColour(self.menubarcolor)
                dragonscroll_vsizer.Add(key,0,wx.EXPAND)
                key.Enable(False)
                disableheader = 1
            else:
                key = wx.Button(self.dragonscrollpanel, -1, u' %s' %str(key), style=wx.BU_LEFT)
                dragonscroll_vsizer.Add(key,0,wx.EXPAND)
                key.Bind(wx.EVT_BUTTON, value)

        dragpic = wx.StaticBitmap(self, -1, gImgIdx['wizbain20x100.png'], pos=(mfsize[0]+border, border))
        dragpic.SetBackgroundColour(self.menucolor)

        self.closebutton = wx.StaticBitmap(self, -1, gImgIdx['stopsign20.png'], pos=(mfsize[0]+border, mfsize[1]-24))
        self.closebutton.SetBackgroundColour(self.menucolor)

        for draggableobject in [self, dragpic]:
            draggableobject.Bind(wx.EVT_LEFT_DOWN, self.OnMouseLeftDown)
            draggableobject.Bind(wx.EVT_MOTION, self.OnMouseMotion)
            draggableobject.Bind(wx.EVT_LEFT_UP, self.OnMouseLeftUp)
            # draggableobject.Bind(wx.EVT_RIGHT_UP, self.OnDestroyMenu)

        self.closebutton.Bind(wx.EVT_LEFT_DOWN, self.OnDestroyMenu)

        self.dragonscrollpanel.SetSizer(dragonscroll_vsizer)
        self.dragonscrollpanel.SetupScrolling()
        # self.dragonscrollpanel.Fit()

        vsizer1 = wx.BoxSizer(wx.VERTICAL)
        vsizer1.Add(self.dragonscrollpanel, 1, wx.EXPAND | wx.RIGHT, 24 + border)
        self.SetSizer(vsizer1)
        self.Fit()

        wx.CallAfter(self.Refresh)

    def OnMouseLeftDown(self, event):
        try:
            self.Refresh()
            self.ldPos = event.GetEventObject().ClientToScreen(event.GetPosition())
            self.wPos = self.ClientToScreen((0,0))
            self.CaptureMouse()
        except:#DCLICK error
            pass
        gWizSTC.SetFocus()

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
        gWizSTC.SetFocus()

    def OnDestroyMenu(self, event):
        self.Show(False)
        self.Destroy()
        gWizSTC.dragmenu2 = 0
