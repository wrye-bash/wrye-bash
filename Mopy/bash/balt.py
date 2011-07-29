# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bolt.
#
#  Wrye Bolt is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bolt is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bolt; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bolt copyright (C) 2005, 2006, 2007, 2008, 2009 Wrye
#
# =============================================================================

# Imports ---------------------------------------------------------------------
#--Localization
#..Handled by bolt, so import that.
import bolt
import bosh
from bolt import _, GPath, deprint, delist
from bolt import BoltError, AbstractError, ArgumentError, StateError, UncodedError, CancelError, SkipError

#--Python
import cPickle
import cStringIO
import StringIO
import string
import struct
import sys
import textwrap
import time
import wx
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

if bolt.bUseUnicode:
    stringBuffer = StringIO.StringIO
else:
    stringBuffer = cStringIO.StringIO

# Basics ---------------------------------------------------------------------
class IdList:
    """Provides sequences of semi-unique ids. Useful for choice menus.

    Sequence ids come in range from baseId up through (baseId + size - 1).
    Named ids will be assigned ids starting at baseId + size.

    Example:
      loadIds = IdList(10000, 90,'SAVE','EDIT','NONE')
    sequence ids are accessed by an iterator: i.e. iter(loadIds), and
    named ids accessed by name. e.g. loadIds.SAVE, loadIds.EDIT, loadIds.NONE
    """

    def __init__(self,baseId,size,*names):
        self.BASE = baseId
        self.MAX = baseId + size - 1
        #--Extra
        nextNameId = baseId + size
        for name in names:
            setattr(self,name,nextNameId)
            nextNameId += 1

    def __iter__(self):
        """Return iterator."""
        for id in range(self.BASE,self.MAX+1):
            yield id

# Constants -------------------------------------------------------------------
defId = -1
defVal = wx.DefaultValidator
defPos = wx.DefaultPosition
defSize = wx.DefaultSize

wxListAligns = [wx.LIST_FORMAT_LEFT, wx.LIST_FORMAT_RIGHT, wx.LIST_FORMAT_CENTRE]

# Settings --------------------------------------------------------------------
_settings = {} #--Using applications should override this.
sizes = {} #--Using applications should override this.

# Colors ----------------------------------------------------------------------
class Colors:
    """Colour collection and wrapper for wx.ColourDatabase.
    Provides dictionary syntax access (colors[key]) and predefined colours."""
    def __init__(self):
        self.data = {}

    def __setitem__(self,key,value):
        """Add a color to the database."""
        if not isinstance(value,str):
            self.data[key] = wx.Colour(*value)

    def __getitem__(self,key):
        """Dictionary syntax: color = colours[key]."""
        if key in self.data:
            return self.data[key]
        else:
            return wx.TheColourDatabase.Find(key)

#--Singleton
colors = Colors()

# Images ----------------------------------------------------------------------
images = {} #--Singleton for collection of images.

#------------------------------------------------------------------------------
class Image:
    """Wrapper for images, allowing access in various formats/classes.

    Allows image to be specified before wx.App is initialized."""
    def __init__(self,file,type=wx.BITMAP_TYPE_ANY,iconSize=16):
        self.file = GPath(file)
        self.type = type
        self.bitmap = None
        self.icon = None
        self.iconSize = iconSize
        if not GPath(self.file.s.split(';')[0]).exists():
            raise ArgumentError(_("Missing resource file: %s.") % (self.file,))

    def GetBitmap(self):
        if not self.bitmap:
            if self.type == wx.BITMAP_TYPE_ICO:
                self.GetIcon()
                self.bitmap = wx.EmptyBitmap(self.iconSize,self.iconSize)
                self.bitmap.CopyFromIcon(self.icon)
            else:
                self.bitmap = wx.Bitmap(self.file.s,self.type)
        return self.bitmap

    def GetIcon(self):
        if not self.icon:
            if self.type == wx.BITMAP_TYPE_ICO:
                self.icon = wx.Icon(self.file.s,wx.BITMAP_TYPE_ICO,self.iconSize,self.iconSize)
                w,h = self.icon.GetWidth(),self.icon.GetHeight()
                if (w > self.iconSize or w == 0 or
                    h > self.iconSize or h == 0):
                    self.iconSize = 16
                    self.icon = wx.Icon(self.file.s,wx.BITMAP_TYPE_ICO,self.iconSize,self.iconSize)
            else:
                self.icon = wx.EmptyIcon()
                self.icon.CopyFromBitmap(self.GetBitmap())
        return self.icon

#------------------------------------------------------------------------------
class ImageBundle:
    """Wrapper for bundle of images.

    Allows image bundle to be specified before wx.App is initialized."""
    def __init__(self):
        self.images = []
        self.iconBundle = None

    def Add(self,image):
        self.images.append(image)

    def GetIconBundle(self):
        if not self.iconBundle:
            self.iconBundle = wx.IconBundle()
            for image in self.images:
                self.iconBundle.AddIcon(image.GetIcon())
        return self.iconBundle

#------------------------------------------------------------------------------
class ImageList:
    """Wrapper for wx.ImageList.

    Allows ImageList to be specified before wx.App is initialized.
    Provides access to ImageList integers through imageList[key]."""
    def __init__(self,width,height):
        self.width = width
        self.height = height
        self.data = []
        self.indices = {}
        self.imageList = None

    def Add(self,image,key):
        self.data.append((key,image))

    def GetImageList(self):
        if not self.imageList:
            indices = self.indices
            imageList = self.imageList = wx.ImageList(self.width,self.height)
            for key,image in self.data:
                indices[key] = imageList.Add(image.GetBitmap())
        return self.imageList

    def __getitem__(self,key):
        self.GetImageList()
        return self.indices[key]

# Functions -------------------------------------------------------------------
def fill(text,width=60):
    """Wraps paragraph to width characters."""
    pars = [textwrap.fill(text,width) for text in text.split('\n')]
    return '\n'.join(pars)

def ensureDisplayed(frame,x=100,y=100):
    """Ensure that frame is displayed."""
    if wx.Display.GetFromWindow(frame) == -1:
        topLeft = wx.Display(0).GetGeometry().GetTopLeft()
        frame.MoveXY(topLeft.x+x,topLeft.y+y)

def setCheckListItems(gList,names,values):
    """Convenience method for setting a bunch of wxCheckListBox items. The main advantage
    of this is that it doesn't clear the list unless it needs to. Which is good if you want
    to preserve the scroll position of the list."""
    if not names:
        gList.Clear()
    else:
        for index,(name,value) in enumerate(zip(names,values)):
            if index >= gList.GetCount():
                gList.Append(name)
            else:
                if index == -1:
                    deprint(_("index = -1, name = %s, value = %s") % (name, value))
                    continue
                gList.SetString(index,name)
            gList.Check(index,value)
        for index in range(gList.GetCount(),len(names),-1):
            gList.Delete(index-1)

# Elements --------------------------------------------------------------------
def bell(arg=None):
    """"Rings the system bell and returns the input argument (useful for return bell(value))."""
    wx.Bell()
    return arg

def tooltip(text,wrap=50):
    """Returns tooltip with wrapped copy of text."""
    text = textwrap.fill(text,wrap)
    return wx.ToolTip(text)

class textCtrl(wx.TextCtrl):
    """wx.TextCtrl with automatic tooltip if text goes past the width of the control."""
    def __init__(self, parent, id=defId, name='', size=defSize, style=0, autotooltip=True):
        wx.TextCtrl.__init__(self,parent,id,name,size=size,style=style)
        if autotooltip:
            self.Bind(wx.EVT_TEXT, self.OnTextChange)
            self.Bind(wx.EVT_SIZE, self.OnSizeChange)

    def UpdateToolTip(self, text):
        if self.GetClientSize()[0] < self.GetTextExtent(text)[0]:
            self.SetToolTip(tooltip(text))
        else:
            self.SetToolTip(tooltip(''))

    def OnTextChange(self,event):
        self.UpdateToolTip(event.GetString())
        event.Skip()
    def OnSizeChange(self, event):
        self.UpdateToolTip(self.GetValue())
        event.Skip()

class comboBox(wx.ComboBox):
    """wx.ComboBox with automatic tooltipi if text is wider than width of control."""
    def __init__(self, *args, **kwdargs):
        autotooltip = kwdargs.get('autotooltip',True)
        if 'autotooltip' in kwdargs:
            del kwdargs['autotooltip']
        wx.ComboBox.__init__(self, *args, **kwdargs)
        if autotooltip:
            self.Bind(wx.EVT_SIZE, self.OnChange)
            self.Bind(wx.EVT_TEXT, self.OnChange)

    def OnChange(self, event):
        if self.GetClientSize()[0] < self.GetTextExtent(self.GetValue())[0]+30:
            self.SetToolTip(tooltip(self.GetValue()))
        else:
            self.SetToolTip(tooltip(''))
        event.Skip()

def bitmapButton(parent,bitmap,pos=defPos,size=defSize,style=wx.BU_AUTODRAW,val=defVal,
        name='button',id=defId,onClick=None,tip=None,onRClick=None):
    """Creates a button, binds click function, then returns bound button."""
    gButton = wx.BitmapButton(parent,id,bitmap,pos,size,style,val,name)
    if onClick: gButton.Bind(wx.EVT_BUTTON,onClick)
    if onRClick: gButton.Bind(wx.EVT_RIGHT_DOWN,onRClick)
    if tip: gButton.SetToolTip(tooltip(tip))
    return gButton

def button(parent,label='',pos=defPos,size=defSize,style=0,val=defVal,
        name='button',id=defId,onClick=None,tip=None):
    """Creates a button, binds click function, then returns bound button."""
    gButton = wx.Button(parent,id,label,pos,size,style,val,name)
    if onClick: gButton.Bind(wx.EVT_BUTTON,onClick)
    if tip: gButton.SetToolTip(tooltip(tip))
    return gButton

def toggleButton(parent,label='',pos=defPos,size=defSize,style=0,val=defVal,
        name='button',id=defId,onClick=None,tip=None):
    """Creates a toggle button, binds toggle function, then returns bound button."""
    gButton = wx.ToggleButton(parent,id,label,pos,size,style,val,name)
    if onClick: gButton.Bind(wx.EVT_TOGGLEBUTTON,onClick)
    if tip: gButton.SetToolTip(tooltip(tip))
    return gButton

def checkBox(parent,label='',pos=defPos,size=defSize,style=0,val=defVal,
        name='checkBox',id=defId,onCheck=None,tip=None):
    """Creates a checkBox, binds check function, then returns bound button."""
    gCheckBox = wx.CheckBox(parent,id,label,pos,size,style,val,name)
    if onCheck: gCheckBox.Bind(wx.EVT_CHECKBOX,onCheck)
    if tip: gCheckBox.SetToolTip(tooltip(tip))
    return gCheckBox

def staticText(parent,label='',pos=defPos,size=defSize,style=0,name="staticText",id=defId,):
    """Static text element."""
    return wx.StaticText(parent,id,label,pos,size,style,name)

def spinCtrl(parent,value='',pos=defPos,size=defSize,style=wx.SP_ARROW_KEYS,
        min=0,max=100,initial=0,name='wxSpinctrl',id=defId,onSpin=None,tip=None):
    """Spin control with event and tip setting."""
    gSpinCtrl=wx.SpinCtrl(parent,id,value,pos,size,style,min,max,initial,name)
    if onSpin: gSpinCtrl.Bind(wx.EVT_SPINCTRL,onSpin)
    if tip: gSpinCtrl.SetToolTip(tooltip(tip))
    return gSpinCtrl

# Sub-Windows -----------------------------------------------------------------
def leftSash(parent,defaultSize=(100,100),onSashDrag=None):
    """Creates a left sash window."""
    sash = wx.SashLayoutWindow(parent,style=wx.SW_3D)
    sash.SetDefaultSize(defaultSize)
    sash.SetOrientation(wx.LAYOUT_VERTICAL)
    sash.SetAlignment(wx.LAYOUT_LEFT)
    sash.SetSashVisible(wx.SASH_RIGHT, True)
    if onSashDrag:
        id = sash.GetId()
        sash.Bind(wx.EVT_SASH_DRAGGED_RANGE, onSashDrag,id=id,id2=id)
    return sash

def topSash(parent,defaultSize=(100,100),onSashDrag=None):
    """Creates a top sash window."""
    sash = wx.SashLayoutWindow(parent,style=wx.SW_3D)
    sash.SetDefaultSize(defaultSize)
    sash.SetOrientation(wx.LAYOUT_HORIZONTAL)
    sash.SetAlignment(wx.LAYOUT_TOP)
    sash.SetSashVisible(wx.SASH_BOTTOM, True)
    if onSashDrag:
        id = sash.GetId()
        sash.Bind(wx.EVT_SASH_DRAGGED_RANGE, onSashDrag,id=id,id2=id)
    return sash

# Sizers ----------------------------------------------------------------------
spacer = ((0,0),1) #--Used to space elements apart.

def aSizer(sizer,*elements):
    """Adds elements to a sizer."""
    for element in elements:
        if isinstance(element,tuple):
            if element[0] != None:
                sizer.Add(*element)
        elif element != None:
            sizer.Add(element)
    return sizer

def hSizer(*elements):
    """Horizontal sizer."""
    return aSizer(wx.BoxSizer(wx.HORIZONTAL),*elements)

def vSizer(*elements):
    """Vertical sizer and elements."""
    return aSizer(wx.BoxSizer(wx.VERTICAL),*elements)

def hsbSizer(boxArgs,*elements):
    """Horizontal static box sizer and elements."""
    return aSizer(wx.StaticBoxSizer(wx.StaticBox(*boxArgs),wx.HORIZONTAL),*elements)

def vsbSizer(boxArgs,*elements):
    """Vertical static box sizer and elements."""
    return aSizer(wx.StaticBoxSizer(wx.StaticBox(*boxArgs),wx.VERTICAL),*elements)

# Modal Dialogs ---------------------------------------------------------------
#------------------------------------------------------------------------------
def askDirectory(parent,message=_('Choose a directory.'),defaultPath=''):
    """Shows a modal directory dialog and return the resulting path, or None if canceled."""
    dialog = wx.DirDialog(parent,message,GPath(defaultPath).s,style=wx.DD_NEW_DIR_BUTTON)
    if dialog.ShowModal() != wx.ID_OK:
        dialog.Destroy()
        return None
    else:
        path = GPath(dialog.GetPath())
        dialog.Destroy()
        return path

#------------------------------------------------------------------------------
def askContinue(parent,message,continueKey,title=_('Warning')):
    """Shows a modal continue query if value of continueKey is false. Returns True to continue.
    Also provides checkbox "Don't show this in future." to set continueKey to true."""
    #--ContinueKey set?
    if _settings.get(continueKey): return wx.ID_OK
    #--Generate/show dialog
    dialog = wx.Dialog(parent,defId,title,size=(350,200),style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
    icon = wx.StaticBitmap(dialog,defId,
        wx.ArtProvider_GetBitmap(wx.ART_WARNING,wx.ART_MESSAGE_BOX, (32,32)))
    gCheckBox = checkBox(dialog,_("Don't show this in the future."))
    #--Layout
    sizer = vSizer(
        (hSizer(
            (icon,0,wx.ALL,6),
            (staticText(dialog,message,style=wx.ST_NO_AUTORESIZE),1,wx.EXPAND|wx.LEFT,6),
            ),1,wx.EXPAND|wx.ALL,6),
        (gCheckBox,0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,6),
        (hSizer( #--Save/Cancel
            spacer,
            button(dialog,id=wx.ID_OK),
            (button(dialog,id=wx.ID_CANCEL),0,wx.LEFT,4),
            ),0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,6),
        )
    dialog.SetSizer(sizer)
    #--Get continue key setting and return
    result = dialog.ShowModal()
    if gCheckBox.GetValue():
        _settings[continueKey] = 1
    return result in (wx.ID_OK,wx.ID_YES)
def askContinueShortTerm(parent,message,title=_('Warning')):
    """Shows a modal continue query  Returns True to continue.
    Also provides checkbox "Don't show this in for rest of operation."."""
    #--Generate/show dialog
    dialog = wx.Dialog(parent,defId,title,size=(350,200),style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
    icon = wx.StaticBitmap(dialog,defId,
        wx.ArtProvider_GetBitmap(wx.ART_WARNING,wx.ART_MESSAGE_BOX, (32,32)))
    gCheckBox = checkBox(dialog,_("Don't show this for rest of operation."))
    #--Layout
    sizer = vSizer(
        (hSizer(
            (icon,0,wx.ALL,6),
            (staticText(dialog,message,style=wx.ST_NO_AUTORESIZE),1,wx.EXPAND|wx.LEFT,6),
            ),1,wx.EXPAND|wx.ALL,6),
        (gCheckBox,0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,6),
        (hSizer( #--Save/Cancel
            spacer,
            button(dialog,id=wx.ID_OK),
            (button(dialog,id=wx.ID_CANCEL),0,wx.LEFT,4),
            ),0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,6),
        )
    dialog.SetSizer(sizer)
    #--Get continue key setting and return
    result = dialog.ShowModal()
    if result in (wx.ID_OK,wx.ID_YES):
        if gCheckBox.GetValue():
            return 2
        return True
    return False
#------------------------------------------------------------------------------
def askOpen(parent,title='',defaultDir='',defaultFile='',wildcard='',style=wx.OPEN,mustExist=False):
    """Show as file dialog and return selected path(s)."""
    defaultDir,defaultFile = [GPath(x).s for x in (defaultDir,defaultFile)]
    dialog = wx.FileDialog(parent,title,defaultDir,defaultFile,wildcard, style )
    if dialog.ShowModal() != wx.ID_OK:
        result = False
    elif style & wx.MULTIPLE:
        result = map(GPath,dialog.GetPaths())
        if mustExist:
            for path in result:
                if not path.exists():
                    result = False
                    break
    else:
        result = GPath(dialog.GetPath())
        if mustExist and not result.exists():
            result = False
    dialog.Destroy()
    return result

def askOpenMulti(parent,title='',defaultDir='',defaultFile='',wildcard='',style=wx.OPEN|wx.MULTIPLE):
    """Show as save dialog and return selected path(s)."""
    return askOpen(parent,title,defaultDir,defaultFile,wildcard,style )

def askSave(parent,title='',defaultDir='',defaultFile='',wildcard='',style=wx.OVERWRITE_PROMPT):
    """Show as save dialog and return selected path(s)."""
    return askOpen(parent,title,defaultDir,defaultFile,wildcard,wx.SAVE|style )

#------------------------------------------------------------------------------
def askText(parent,message,title='',default=''):
    """Shows a text entry dialog and returns result or None if canceled."""
    dialog = wx.TextEntryDialog(parent,message,title,default)
    if dialog.ShowModal() != wx.ID_OK:
        dialog.Destroy()
        return None
    else:
        value = dialog.GetValue()
        dialog.Destroy()
        return value

#------------------------------------------------------------------------------
def askNumber(parent,message,prompt='',title='',value=0,min=0,max=10000):
    """Shows a text entry dialog and returns result or None if canceled."""
    dialog = wx.NumberEntryDialog(parent,message,prompt,title,value,min,max)
    if dialog.ShowModal() != wx.ID_OK:
        dialog.Destroy()
        return None

    else:
        value = dialog.GetValue()
        dialog.Destroy()
        return value

# Message Dialogs -------------------------------------------------------------
def askStyled(parent,message,title,style):
    """Shows a modal MessageDialog.
    Use ErrorMessage, WarningMessage or InfoMessage."""
    dialog = wx.MessageDialog(parent,message,title,style)
    result = dialog.ShowModal()
    dialog.Destroy()
    return result in (wx.ID_OK,wx.ID_YES)

def askOk(parent,message,title=''):
    """Shows a modal error message."""
    return askStyled(parent,message,title,wx.OK|wx.CANCEL)

def askYes(parent,message,title='',default=True,icon=wx.ICON_EXCLAMATION):
    """Shows a modal warning or question message."""
    style = wx.YES_NO|icon|((wx.NO_DEFAULT,wx.YES_DEFAULT)[default])
    return askStyled(parent,message,title,style)

def askWarning(parent,message,title=_('Warning')):
    """Shows a modal warning message."""
    return askStyled(parent,message,title,wx.OK|wx.CANCEL|wx.ICON_EXCLAMATION)

def showOk(parent,message,title=''):
    """Shows a modal error message."""
    return askStyled(parent,message,title,wx.OK)

def showError(parent,message,title=_('Error')):
    """Shows a modal error message."""
    return askStyled(parent,message,title,wx.OK|wx.ICON_HAND)

def showWarning(parent,message,title=_('Warning')):
    """Shows a modal warning message."""
    return askStyled(parent,message,title,wx.OK|wx.ICON_EXCLAMATION)

def showInfo(parent,message,title=_('Information')):
    """Shows a modal information message."""
    return askStyled(parent,message,title,wx.OK|wx.ICON_INFORMATION)

def showList(parent,header,items,maxItems=0,title=''):
    """Formats a list of items into a message for use in a Message."""
    numItems = len(items)
    if maxItems <= 0: maxItems = numItems
    message = string.Template(header).substitute(count=numItems)
    message += '\n* '+'\n* '.join(items[:min(numItems,maxItems)])
    if numItems > maxItems:
        message += _('\n(And %d others.)') % (numItems - maxItems,)
    return askStyled(parent,message,title,wx.OK)

#------------------------------------------------------------------------------
def showLogClose(evt=None):
    """Handle log message closing."""
    window = evt.GetEventObject()
    if not window.IsIconized() and not window.IsMaximized():
        _settings['balt.LogMessage.pos'] = window.GetPositionTuple()
        _settings['balt.LogMessage.size'] = window.GetSizeTuple()
    window.Destroy()

def showQuestionLogCloseYes(Event,window):
    """Handle log message closing."""
    if window:
        if not window.IsIconized() and not window.IsMaximized():
            _settings['balt.LogMessage.pos'] = window.GetPositionTuple()
            _settings['balt.LogMessage.size'] = window.GetSizeTuple()
        window.Destroy()
    bosh.question = True

def showQuestionLogCloseNo(Event,window):
    """Handle log message closing."""
    if window:
        if not window.IsIconized() and not window.IsMaximized():
            _settings['balt.LogMessage.pos'] = window.GetPositionTuple()
            _settings['balt.LogMessage.size'] = window.GetSizeTuple()
        window.Destroy()
    bosh.question = False

def showLog(parent,logText,title='',style=0,asDialog=True,fixedFont=False,icons=None,size=True,question=False):
    """Display text in a log window"""
    #--Sizing
    pos = _settings.get('balt.LogMessage.pos',defPos)
    if size:
        size = _settings.get('balt.LogMessage.size',(400,400))
    #--Dialog or Frame
    if asDialog:
        window = wx.Dialog(parent,defId,title,pos=pos,size=size,
            style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
    else:
        window = wx.Frame(parent,defId,title,pos=pos,size=size,
            style= (wx.RESIZE_BORDER | wx.CAPTION | wx.SYSTEM_MENU | wx.CLOSE_BOX | wx.CLIP_CHILDREN))
        if icons: window.SetIcons(icons)
    window.SetSizeHints(200,200)
    window.Bind(wx.EVT_CLOSE,showLogClose)
    window.SetBackgroundColour(wx.NullColour) #--Bug workaround to ensure that default colour is being used.
    #--Text
    textCtrl = wx.TextCtrl(window,defId,logText,style=wx.TE_READONLY|wx.TE_MULTILINE|wx.TE_RICH2|wx.SUNKEN_BORDER  )
    if fixedFont:
        fixedFont = wx.SystemSettings_GetFont(wx.SYS_ANSI_FIXED_FONT )
        fixedFont.SetPointSize(8)
        fixedStyle = wx.TextAttr()
        #fixedStyle.SetFlags(0x4|0x80)
        fixedStyle.SetFont(fixedFont)
        textCtrl.SetStyle(0,textCtrl.GetLastPosition(),fixedStyle)
    if question:
        bosh.question = False
        #--Buttons
        gYesButton = button(window,id=wx.ID_YES)
        gYesButton.Bind(wx.EVT_BUTTON, lambda evt, temp=window: showQuestionLogCloseYes(evt, temp) )
        gYesButton.SetDefault()
        gNoButton = button(window,id=wx.ID_NO)
        gNoButton.Bind(wx.EVT_BUTTON, lambda evt, temp=window: showQuestionLogCloseNo(evt, temp) )
        #--Layout
        window.SetSizer(
            vSizer(
                (textCtrl,1,wx.EXPAND|wx.ALL^wx.BOTTOM,2),
                hSizer((gYesButton,0,wx.ALIGN_RIGHT|wx.ALL,4),
                    (gNoButton,0,wx.ALIGN_RIGHT|wx.ALL,4))
                )
            )
    else:
        #--Buttons
        gOkButton = button(window,id=wx.ID_OK,onClick=lambda event: window.Close())
        gOkButton.SetDefault()
        #--Layout
        window.SetSizer(
            vSizer(
                (textCtrl,1,wx.EXPAND|wx.ALL^wx.BOTTOM,2),
                (gOkButton,0,wx.ALIGN_RIGHT|wx.ALL,4),
                )
            )
    #--Show
    if asDialog:
        window.ShowModal()
        window.Destroy()
    else:
        window.Show()
    return bosh.question

#------------------------------------------------------------------------------
def showWryeLog(parent,logText,title='',style=0,asDialog=True,icons=None):
    """Convert logText from wtxt to html and display. Optionally, logText can be path to an html file."""
    try:
        import wx.lib.iewin
    except ImportError:
        # Comtypes not available most likely! so do it this way:
        import os
        if not isinstance(logText,bolt.Path):
            logPath = _settings.get('balt.WryeLog.temp', bolt.Path.getcwd().join('WryeLogTemp.html'))
            cssDir = _settings.get('balt.WryeLog.cssDir', GPath(''))
            ins = stringBuffer(logText+'\n{{CSS:wtxt_sand_small.css}}')
            out = logPath.open('w')
            bolt.WryeText.genHtml(ins,out,cssDir)
            out.close()
            logText = logPath
        os.startfile(logText.s)
        return

    #--Sizing
    pos = _settings.get('balt.WryeLog.pos',defPos)
    size = _settings.get('balt.WryeLog.size',(400,400))
    #--Dialog or Frame
    if asDialog:
        window = wx.Dialog(parent,defId,title,pos=pos,size=size,
            style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
    else:
        window = wx.Frame(parent,defId,title,pos=pos,size=size,
            style= (wx.RESIZE_BORDER | wx.CAPTION | wx.SYSTEM_MENU | wx.CLOSE_BOX | wx.CLIP_CHILDREN))
        if icons: window.SetIcons(icons)
    window.SetSizeHints(200,200)
    window.Bind(wx.EVT_CLOSE,showLogClose)
    #--Text
    textCtrl = wx.lib.iewin.IEHtmlWindow(window, defId, style = wx.NO_FULL_REPAINT_ON_RESIZE)
    if not isinstance(logText,bolt.Path):
        logPath = _settings.get('balt.WryeLog.temp', bolt.Path.getcwd().join('WryeLogTemp.html'))
        cssDir = _settings.get('balt.WryeLog.cssDir', GPath(''))
        ins = stringBuffer(logText+'\n{{CSS:wtxt_sand_small.css}}')
        out = logPath.open('w')
        bolt.WryeText.genHtml(ins,out,cssDir)
        out.close()
        logText = logPath
    textCtrl.Navigate(logText.s,0x2) #--0x2: Clear History
    #--Buttons
    bitmap = wx.ArtProvider_GetBitmap(wx.ART_GO_BACK,wx.ART_HELP_BROWSER, (16,16))
    gBackButton = bitmapButton(window,bitmap,onClick=lambda evt: textCtrl.GoBack())
    bitmap = wx.ArtProvider_GetBitmap(wx.ART_GO_FORWARD,wx.ART_HELP_BROWSER, (16,16))
    gForwardButton = bitmapButton(window,bitmap,onClick=lambda evt: textCtrl.GoForward())
    gOkButton = button(window,id=wx.ID_OK,onClick=lambda event: window.Close())
    gOkButton.SetDefault()
    if not asDialog:
        window.SetBackgroundColour(gOkButton.GetBackgroundColour())
    #--Layout
    window.SetSizer(
        vSizer(
            (textCtrl,1,wx.EXPAND|wx.ALL^wx.BOTTOM,2),
            (hSizer(
                gBackButton,
                gForwardButton,
                spacer,
                gOkButton,
                ),0,wx.ALL|wx.EXPAND,4),
            )
        )
    #--Show
    if asDialog:
        window.ShowModal()
        if window:
            _settings['balt.WryeLog.pos'] = window.GetPositionTuple()
            _settings['balt.WryeLog.size'] = window.GetSizeTuple()
            window.Destroy()
    else:
        window.Show()

def playSound(parent,sound):
    if not sound: return
    sound = wx.Sound(sound)
    if sound.IsOk():
        sound.Play(wx.SOUND_ASYNC)
    else:
        showError(parent,_("Invalid sound file %s.") % sound)

# Other Windows ---------------------------------------------------------------
#------------------------------------------------------------------------------
class ListEditorData:
    """Data capsule for ListEditor. [Abstract]"""
    def __init__(self,parent):
        """Initialize."""
        self.parent = parent #--Parent window.
        self.showAction = False
        self.showAdd = False
        self.showEdit = False
        self.showRename = False
        self.showRemove = False
        self.showSave = False
        self.showCancel = False
        self.caption = None
        #--Editable?
        self.showInfo = False
        self.infoWeight = 1 #--Controls width of info pane
        self.infoReadOnly = True #--Controls whether info pane is editable

    #--List
    def action(self,item):
        """Called when action button is used.."""
        pass
    def select(self,item):
        """Called when an item is selected."""
        pass
    def getItemList(self):
        """Returns item list in correct order."""
        raise AbstractError
        return []
    def add(self):
        """Peforms add operation. Return new item on success."""
        raise AbstractError
        return None
    def edit(self,item=None):
        """Edits specified item. Return true on success."""
        raise AbstractError
        return False
    def rename(self,oldItem,newItem):
        """Renames oldItem to newItem. Return true on success."""
        raise AbstractError
        return False
    def remove(self,item):
        """Removes item. Return true on success."""
        raise AbstractError
        return False
    def close(self):
        """Called when dialog window closes."""
        pass

    #--Info box
    def getInfo(self,item):
        """Returns string info on specified item."""
        return ''
    def setInfo(self,item,text):
        """Sets string info on specified item."""
        raise AbstractError

    #--Checklist
    def getChecks(self):
        """Returns checked state of items as array of True/False values matching Item list."""
        raise AbstractError
        return []
    def check(self,item):
        """Checks items. Return true on success."""
        raise AbstractError
        return False
    def uncheck(self,item):
        """Unchecks item. Return true on success."""
        raise AbstractError
        return False

    #--Save/Cancel
    def save(self):
        """Handles save button."""
        pass

    def cancel(self):
        """Handles cancel button."""
        pass

#------------------------------------------------------------------------------
class ListEditor(wx.Dialog):
    """Dialog for editing lists."""
    def __init__(self,parent,id,title,data,type='list'):
        #--Data
        self.data = data #--Should be subclass of ListEditorData
        self.items = data.getItemList()
        #--GUI
        wx.Dialog.__init__(self,parent,id,title,
            style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        wx.EVT_CLOSE(self, self.OnCloseWindow)
        #--Caption
        if data.caption:
            captionText = staticText(self,data.caption)
        else:
            captionText = None
        #--List Box
        if type == 'checklist':
            self.list = wx.CheckListBox(self,-1,choices=self.items,style=wx.LB_SINGLE)
            for index,checked in enumerate(self.data.getChecks()):
                self.list.Check(index,checked)
            self.Bind(wx.EVT_CHECKLISTBOX, self.DoCheck, self.list)
        else:
            self.list = wx.ListBox(self,-1,choices=self.items,style=wx.LB_SINGLE)
        self.list.SetSizeHints(125,150)
        self.list.Bind(wx.EVT_LISTBOX,self.OnSelect)
        #--Infobox
        if data.showInfo:
            self.gInfoBox = wx.TextCtrl(self,-1," ",size=(130,-1),
                style=(self.data.infoReadOnly*wx.TE_READONLY)|wx.TE_MULTILINE|wx.SUNKEN_BORDER)
            if not self.data.infoReadOnly:
                self.gInfoBox.Bind(wx.EVT_TEXT,self.OnInfoEdit)
        else:
            self.gInfoBox = None
        #--Buttons
        buttonSet = (
            (data.showAction, _('Action'), self.DoAction),
            (data.showAdd,    _('Add'),    self.DoAdd),
            (data.showEdit,   _('Edit'),   self.DoEdit),
            (data.showRename, _('Rename'), self.DoRename),
            (data.showRemove, _('Remove'), self.DoRemove),
            (data.showSave,   _('Save'),   self.DoSave),
            (data.showCancel, _('Cancel'), self.DoCancel),
            )
        if sum(bool(x[0]) for x in buttonSet):
            buttons = vSizer()
            for (flag,defLabel,func) in buttonSet:
                if not flag: continue
                label = (flag == True and defLabel) or flag
                buttons.Add(button(self,label,onClick=func),0,wx.LEFT|wx.TOP,4)
        else:
            buttons = None
        #--Layout
        sizer = vSizer(
            (captionText,0,wx.LEFT|wx.TOP,4),
            (hSizer(
                (self.list,1,wx.EXPAND|wx.TOP,4),
                (self.gInfoBox,self.data.infoWeight,wx.EXPAND|wx.TOP,4),
                (buttons,0,wx.EXPAND),
                ),1,wx.EXPAND)
            )
        #--Done
        className = data.__class__.__name__
        if className in sizes:
            self.SetSizer(sizer)
            self.SetSize(sizes[className])
        else:
            self.SetSizerAndFit(sizer)

    def GetSelected(self):
        return self.list.GetNextItem(-1,wx.LIST_NEXT_ALL,wx.LIST_STATE_SELECTED)

    #--Checklist commands
    def DoCheck(self,event):
        """Handles check/uncheck of listbox item."""
        index = event.GetSelection()
        item = self.items[index]
        if self.list.IsChecked(index):
            self.data.check(item)
        else:
            self.data.uncheck(item)
        #self.list.SetSelection(index)

    #--List Commands
    def DoAction(self,event):
        """Acts on the selected item."""
        selections = self.list.GetSelections()
        if not selections: return bell()
        itemDex = selections[0]
        item = self.items[itemDex]
        self.data.action(item)

    def DoAdd(self,event):
        """Adds a new item."""
        newItem = self.data.add()
        if newItem and newItem not in self.items:
            self.items = self.data.getItemList()
            index = self.items.index(newItem)
            self.list.InsertItems([newItem],index)

    def DoEdit(self,event):
        """Edits the selected item."""
        raise UncodedError

    def DoRename(self,event):
        """Renames selected item."""
        selections = self.list.GetSelections()
        if not selections: return bell()
        #--Rename it
        itemDex = selections[0]
        curName = self.list.GetString(itemDex)
        #--Dialog
        newName = askText(self,_('Rename to:'),_('Rename'),curName)
        if not newName or newName == curName:
            return
        elif newName in self.items:
            showError(self,_('Name must be unique.'))
        elif self.data.rename(curName,newName):
            self.items[itemDex] = newName
            self.list.SetString(itemDex,newName)

    def DoRemove(self,event):
        """Removes selected item."""
        selections = self.list.GetSelections()
        if not selections: return bell()
        #--Data
        itemDex = selections[0]
        item = self.items[itemDex]
        if not self.data.remove(item): return
        #--GUI
        del self.items[itemDex]
        self.list.Delete(itemDex)
        if self.gInfoBox:
            self.gInfoBox.DiscardEdits()
            self.gInfoBox.SetValue('')

    #--Show Info
    def OnSelect(self,event):
        """Handle show info (item select) event."""
        index = event.GetSelection()
        item = self.items[index]
        self.data.select(item)
        if self.gInfoBox:
            self.gInfoBox.DiscardEdits()
            self.gInfoBox.SetValue(self.data.getInfo(item))

    def OnInfoEdit(self,event):
        """Info box text has been edited."""
        selections = self.list.GetSelections()
        if not selections: return bell()
        item = self.items[selections[0]]
        if self.gInfoBox.IsModified():
            self.data.setInfo(item,self.gInfoBox.GetValue())

    #--Save/Cancel
    def DoSave(self,event):
        """Handle save button."""
        self.data.save()
        sizes[self.data.__class__.__name__] = self.GetSizeTuple()
        self.EndModal(wx.ID_OK)

    def DoCancel(self,event):
        """Handle save button."""
        self.data.cancel()
        sizes[self.data.__class__.__name__] = self.GetSizeTuple()
        self.EndModal(wx.ID_CANCEL)

    #--Window Closing
    def OnCloseWindow(self, event):
        """Handle window close event.
        Remember window size, position, etc."""
        self.data.close()
        sizes[self.data.__class__.__name__] = self.GetSizeTuple()
        self.Destroy()

#------------------------------------------------------------------------------
class Picture(wx.Window):
    """Picture panel."""
    def __init__(self, parent,width,height,scaling=1,style=0,background=wx.MEDIUM_GREY_BRUSH):
        """Initialize."""
        wx.Window.__init__(self, parent, defId,size=(width,height),style=style)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.bitmap = None
        if background is not None:
            self.background = background
        else:
            self.background = wx.Brush(self.GetBackgroundColour())
        #self.SetSizeHints(width,height,width,height)
        #--Events
        self.Bind(wx.EVT_PAINT,self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.OnSize()

    def SetBitmap(self,bitmap):
        """Set bitmap."""
        self.bitmap = bitmap
        self.OnSize()

    def OnSize(self,event=None):
        x, y = self.GetSize()
        if x <= 0 or y <= 0: return
        self.buffer = wx.EmptyBitmap(x,y)
        dc = wx.MemoryDC()
        dc.SelectObject(self.buffer)
        # Draw
        dc.SetBackground(self.background)
        dc.Clear()
        if self.bitmap:
            old_x,old_y = self.bitmap.GetSize()
            scale = min(float(x)/old_x, float(y)/old_y)
            new_x = old_x * scale
            new_y = old_y * scale
            pos_x = max(0,x-new_x)/2
            pos_y = max(0,y-new_y)/2
            image = self.bitmap.ConvertToImage()
            image.Rescale(new_x, new_y, wx.IMAGE_QUALITY_HIGH)
            dc.DrawBitmap(wx.BitmapFromImage(image), pos_x, pos_y)
        del dc
        self.Refresh()
        self.Update()

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self, self.buffer)

#------------------------------------------------------------------------------
class BusyCursor(object):
    """Wrapper around wx.BeginBusyCursor and wx.EndBusyCursor, to be used with
       Pythons 'with' semantics."""
    def __enter__(self):
        wx.BeginBusyCursor()
    def __exit__(self,type,value,traceback):
        wx.EndBusyCursor()

#------------------------------------------------------------------------------
class Progress(bolt.Progress):
    """Progress as progress dialog."""
    def __init__(self,title=_('Progress'),message=' '*60,parent=None,
        style=wx.PD_APP_MODAL|wx.PD_ELAPSED_TIME|wx.PD_AUTO_HIDE, abort=False, onAbort=None):
        if abort:
            style |= wx.PD_CAN_ABORT
            self.fnAbort = onAbort
        if sys.version[:3] != '2.4': style |= wx.PD_SMOOTH
        self.dialog = wx.ProgressDialog(title,bolt.Unicode(message),100,parent,style)
        self.dialog.SetFocus()
        bolt.Progress.__init__(self)
        self.message = message
        self.isDestroyed = False
        self.prevMessage = ''
        self.prevState = -1
        self.prevTime = 0

    # __enter__ and __exit__ for use with the 'with' statement
    def __enter__(self):
        return self
    def __exit__(self,type,value,traceback):
        self.Destroy()

    def setCancel(self, enabled=True):
        cancel = self.dialog.FindWindowById(wx.ID_CANCEL)
        cancel.Enable(enabled)

    def onAbort(self):
        if self.fnAbort:
            return self.fnAbort()
        return True

    def doProgress(self,state,message):
        if not self.dialog:
            raise StateError(_('Dialog already destroyed.'))
        elif (state == 0 or state == 1 or (message != self.prevMessage) or
            (state - self.prevState) > 0.05 or (time.time() - self.prevTime) > 0.5):
            self.dialog.SetFocus()
            if message != self.prevMessage:
                ret = self.dialog.Update(int(state*100),bolt.Unicode(message))
                if not ret[0]:
                    if self.onAbort():
                        raise CancelError
            else:
                ret = self.dialog.Update(int(state*100))
                if not ret[0]:
                    if self.onAbort():
                        raise CancelError
            self.prevMessage = message
            self.prevState = state
            self.prevTime = time.time()

    def Destroy(self):
        if self.dialog:
            self.dialog.Destroy()
            self.dialog = None

#------------------------------------------------------------------------------
class ListCtrl(wx.ListCtrl, ListCtrlAutoWidthMixin):
    """List control extended with the wxPython auto-width mixin class.
    Also extended to support drag-and-drop.  To define custom drag-and-drop
    functionality, you can provide callbacks for, or override the following functions:
    OnDropFiles(self, x, y, filenames) - called when files are dropped in the list control
    OnDropIndexes(self,indexes,newPos) - called to move the specified indexes to new starting position 'newPos'
    dndAllow(self) - return true to allow dnd, false otherwise

    OnDropFiles callback:   fnDropFiles
    OnDropIndexes callback: fnDropIndexes
    dndAllow callback:      fnDndAllow
    """
    class DropFileOrList(wx.DropTarget):

        def __init__(self, window, dndFiles, dndList):
            wx.PyDropTarget.__init__(self)
            self.window = window

            self.data = wx.DataObjectComposite()
            self.dataFile = wx.FileDataObject()                 # Accept files
            self.dataList = wx.CustomDataObject('ListIndexes')  # Accept indexes from a list
            if dndFiles: self.data.Add(self.dataFile)
            if dndList : self.data.Add(self.dataList)
            self.SetDataObject(self.data)

        def OnData(self, x, y, data):
            if self.GetData():
                dtype = self.data.GetReceivedFormat().GetType()
                if dtype == wx.DF_FILENAME:
                    # File(s) were dropped
                    self.window.OnDropFiles(x, y, self.dataFile.GetFilenames())
                elif dtype == self.dataList.GetFormat().GetType():
                    # ListCtrl indexes
                    data = cPickle.loads(self.dataList.GetData())
                    self.window._OnDropList(x, y, data)

        def OnDragOver(self, x, y, dragResult):
            self.window.OnDragging(x,y,dragResult)
            return wx.DropTarget.OnDragOver(self,x,y,dragResult)

    def __init__(self, parent, id, pos=defPos, size=defSize, style=0,
                 dndFiles=False, dndList=False, dndOnlyMoveContinuousGroup=True,
                 fnDropFiles=None, fnDropIndexes=None, fnDndAllow=None):
        wx.ListCtrl.__init__(self, parent, id, pos, size, style=style)
        ListCtrlAutoWidthMixin.__init__(self)
        if dndFiles or dndList:
            self.SetDropTarget(ListCtrl.DropFileOrList(self, dndFiles, dndList))
            if dndList:
                self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.OnBeginDrag)
        self.dndOnlyCont = dndOnlyMoveContinuousGroup
        self.fnDropFiles = fnDropFiles
        self.fnDropIndexes = fnDropIndexes
        self.fnDndAllow = fnDndAllow
        self.doDnD = True

    def OnDragging(self,x,y,dragResult):
        # We're dragging, see if we need to scroll the list
        index, flags = self.HitTest((x, y))
        if index == wx.NOT_FOUND:   # Didn't drop it on an item
            if self.GetItemCount() > 0:
                if y <= self.GetItemRect(0).y:
                    # Mouse is above the first item
                    self.ScrollLines(-1)
                elif y >= self.GetItemRect(self.GetItemCount() - 1).y:
                    # Mouse is after the last item
                    self.ScrollLines(1)
        else:
            # Screen position if item hovering over
            pos = index - self.GetScrollPos(wx.VERTICAL)
            if pos == 0:
                # Over the first item, see if it's over the top half
                rect = self.GetItemRect(index)
                if y < rect.y + rect.height/2:
                    self.ScrollLines(-1)
            elif pos == self.GetCountPerPage():
                # On last item/one that's not fully visible
                self.ScrollLines(1)

    def SetDnD(self, allow): self.doDnD = allow

    def OnBeginDrag(self, event):
        if not self.dndAllow(): return

        indexes = []
        start = stop = -1
        for index in range(self.GetItemCount()):
            if self.GetItemState(index, wx.LIST_STATE_SELECTED):
                if stop >= 0 and self.dndOnlyCont:
                    # Only allow moving selections if they are in a
                    # continuous block...they aren't
                    return
                if start < 0:
                    start = index
                indexes.append(index)
            else:
                if start >=0 and stop < 0:
                    stop = index - 1
        if stop < 0: stop = self.GetItemCount()

        selected = cPickle.dumps(indexes, 1)
        ldata = wx.CustomDataObject('ListIndexes')
        ldata.SetData(selected)

        data = wx.DataObjectComposite()
        data.Add(ldata)

        source = wx.DropSource(self)
        source.SetData(data)
        source.DoDragDrop(flags=wx.Drag_DefaultMove)

    def OnDropFiles(self, x, y, filenames):
        if self.fnDropFiles:
            wx.CallLater(10,self.fnDropFiles,x,y,filenames)
            #self.fnDropFiles(x, y, filenames)
            return
        # To be implemented by sub-classes
        raise AbstractError

    def _OnDropList(self, x, y, indexes):
        start = indexes[0]
        stop = indexes[-1]

        index, flags = self.HitTest((x, y))
        deprint('index:',index)
        deprint('flags:',flags)
        if index == wx.NOT_FOUND:   # Didn't drop it on an item
            deprint('index: wx.NOT_FOUND')
            if self.GetItemCount() > 0:
                if y <= self.GetItemRect(0).y:
                    # Dropped it before the first item
                    deprint('NOT_FOUND: before first item')
                    index = 0
                elif y >= self.GetItemRect(self.GetItemCount() - 1).y:
                    # Dropped it after the last item
                    deprint('NOT_FOUND: after the last item')
                    index = self.GetItemCount()
                else:
                    # Dropped it on the edge of the list, but not above or below
                    deprint('NOT_FOUND: ack!')
                    return
            else:
                deprint('NOT_FOUND: empty list?')
                # Empty list
                index = 0
        else:
            # Dropped on top of an item
            target = index
            if target >= start and target <= stop:
                deprint('target is on itself')
                # Trying to drop it back on itself
                return
            elif target < start:
                deprint('dragging upward')
                # Trying to drop it furthur up in the list
                pass
            elif target > stop:
                # Trying to drop it further down the list
                index -= 1 + (stop-start)
                deprint('dragging downward.  new index:', index)

            # If dropping on the top half of the item, insert above it,
            # otherwise insert below it
            rect = self.GetItemRect(target)
            if y > rect.y + rect.height/2:
                deprint('dragged past the bottom half of the target')
                index += 1

        # Do the moving
        deprint('sending items:', indexes)
        deprint('to index:', index)
        self.OnDropIndexes(indexes, index)

    def OnDropIndexes(self, indexes, newPos):
        if self.fnDropIndexes:
            wx.CallLater(10,self.fnDropIndexes,indexes,newPos)
            #self.fnDropIndexes(indexes, newPos)

    def dndAllow(self):
        if self.doDnD:
            if self.fnDndAllow: return self.fnDndAllow()
            return True
        return False
#------------------------------------------------------------------------------
class Tank(wx.Panel):
    """'Tank' format table. Takes the form of a wxListCtrl in Report mode, with
    multiple columns and (optionally) column and item menus."""
    #--Class-------------------------------------------------------------------
    mainMenu = None
    itemMenu = None

    #--Instance ---------------------------------------------------------------
    def __init__(self,parent,data,icons=None,mainMenu=None,itemMenu=None,
            details=None,id=-1,style=(wx.LC_REPORT | wx.LC_SINGLE_SEL),
            dndList=False,dndFiles=False,dndColumns=[]):
        wx.Panel.__init__(self,parent,id,style=wx.WANTS_CHARS)
        #--Data
        if icons == None: icons = {}
        self.data = data
        self.icons = icons #--Default to balt image collection.
        self.mainMenu = mainMenu or self.__class__.mainMenu
        self.itemMenu = itemMenu or self.__class__.itemMenu
        self.details = details
        self.dndColumns = dndColumns
        #--Item/Id mapping
        self.nextItemId = 1
        self.item_itemId = {}
        self.itemId_item = {}
        #--Layout
        sizer = vSizer()
        self.SetSizer(sizer)
        self.SetSizeHints(50,50)
        #--ListCtrl
        self.gList = gList = ListCtrl(self, -1, style=style,
                                      dndFiles=dndFiles, dndList=dndList,
                                      fnDndAllow=self.dndAllow, fnDropIndexes=self.OnDropIndexes, fnDropFiles=self.OnDropFiles)
        if self.icons:
            gList.SetImageList(icons.GetImageList(),wx.IMAGE_LIST_SMALL)
        #--State info
        self.mouseItem = None
        self.mouseTexts = {}
        self.mouseTextPrev = ''
        #--Columns
        self.UpdateColumns()
        #--Items
        self.sortDirty = False
        self.UpdateItems()
        #--Events
        self.Bind(wx.EVT_SIZE,self.OnSize)
        #--Events: Items
        gList.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        gList.Bind(wx.EVT_CONTEXT_MENU, self.DoItemMenu)
        gList.Bind(wx.EVT_LIST_ITEM_SELECTED,self.OnItemSelected)
        gList.Bind(wx.EVT_LEFT_DCLICK, self.OnDClick)
        #--Events: Columns
        gList.Bind(wx.EVT_LIST_COL_CLICK, self.OnColumnClick)
        gList.Bind(wx.EVT_LIST_COL_RIGHT_CLICK, self.DoColumnMenu)
        gList.Bind(wx.EVT_LIST_COL_END_DRAG, self.OnColumnResize)
        #--Mouse movement
        gList.Bind(wx.EVT_MOTION, self.OnMouse)
        gList.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouse)
        gList.Bind(wx.EVT_SCROLLWIN, self.OnScroll)
        #--ScrollPos
        gList.ScrollLines(data.getParam('vScrollPos',0))
        data.setParam('vScrollPos', gList.GetScrollPos(wx.VERTICAL))
        #--Hack: Default text item background color
        self.defaultTextBackground = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)

    #--Drag and Drop-----------------------------------------------------------
    def dndAllow(self):
        # Only allow drag an drop when sorting by the columns specified in dndColumns
        if self.sort not in self.dndColumns: return False
        return True

    def OnDropIndexes(self, indexes, newPos):
        # See if the column is reverse sorted first
        data = self.data
        column = self.sort
        reverse = self.colReverse.get(column,False)
        if reverse:
            newPos = self.gList.GetItemCount() - newPos - 1 - (indexes[-1]-indexes[0])
            if newPos < 0: newPos = 0

        # Move the given indexes to the new position
        self.data.moveArchives(self.GetSelected(), newPos)
        self.data.refresh(what='N')
        self.RefreshUI()

    def OnDropFiles(self, x, y, filenames):
        raise AbstractError

    #--Item/Id/Index Translation ----------------------------------------------
    def GetItem(self,index):
        """Returns item for specified list index."""
        return self.itemId_item[self.gList.GetItemData(index)]

    def GetId(self,item):
        """Returns id for specified item, creating id if necessary."""
        id = self.item_itemId.get(item)
        if id: return id
        #--Else get a new item id.
        id = self.nextItemId
        self.nextItemId += 1
        self.item_itemId[item] = id
        self.itemId_item[id] = item
        return id

    def GetIndex(self,item):
        """Returns index for specified item."""
        return self.gList.FindItemData(-1,self.GetId(item))

    def UpdateIds(self):
        """Updates item/id mappings to account for removed items."""
        removed = set(self.item_itemId.keys()) - set(self.data.keys())
        for item in removed:
            itemId = self.item_itemId[item]
            del self.item_itemId[item]
            del self.itemId_item[itemId]

    #--Updating/Sorting/Refresh -----------------------------------------------
    def PopulateColumns(self):
        """Alias for UpdateColumns, for List_Columns"""
        self.UpdateColumns()

    def UpdateColumns(self):
        """Create/name columns in ListCtrl."""
        cols = self.cols
        numCols = len(cols)
        for colDex in range(numCols):
            colKey = cols[colDex]
            colName = self.colNames.get(colKey,colKey)
            colWidth = self.colWidths.get(colKey,30)
            colAlign = wxListAligns[self.colAligns.get(colKey,0)]
            if colDex >= self.gList.GetColumnCount():
                # Make a new column
                self.gList.InsertColumn(colDex,colName,colAlign)
                self.gList.SetColumnWidth(colDex,colWidth)
            else:
                # Update an existing column
                column = self.gList.GetColumn(colDex)
                if column.GetText() == colName:
                    # Don't change it, just make sure the width is correct
                    self.gList.SetColumnWidth(colDex,colWidth)
                elif column.GetText() not in self.cols:
                    # Column that doesn't exist anymore
                    self.gList.DeleteColumn(colDex)
                    colDex -= 1
                else:
                    # New column
                    self.gList.InsertColumn(colDex,colName,colAlign)
                    self.gList.SetColumnWidth(colDex,colWidth)
        while self.gList.GetColumnCount() > numCols:
            self.gList.DeleteColumn(numCols)
        self.gList.SetColumnWidth(numCols, wx.LIST_AUTOSIZE_USEHEADER)

    def UpdateItem(self,index,item=None,selected=tuple()):
        """Populate Item for specified item."""
        if index < 0: return
        data,gList = self.data,self.gList
        item = item or self.GetItem(index)
        for iColumn,column in enumerate(self.cols):
            colDex = self.GetColumnDex(column)
            gList.SetStringItem(index,iColumn,data.getColumns(item)[colDex])
        gItem = gList.GetItem(index)
        iconKey,textKey,backKey = data.getGuiKeys(item)
        if iconKey and self.icons: gItem.SetImage(self.icons[iconKey])
        if textKey: gItem.SetTextColour(colors[textKey])
        else: gItem.SetTextColour(gList.GetTextColour())
        if backKey: gItem.SetBackgroundColour(colors[backKey])
        else: gItem.SetBackgroundColour(self.defaultTextBackground)
##        gItem.SetState((0,wx.LIST_STATE_SELECTED)[item in selected])
        gItem.SetData(self.GetId(item))
        gList.SetItem(gItem)

    def GetColumnDex(self,column):
        raise AbstractError

    def UpdateItems(self,selected='SAME'):
        """Update all items."""
        gList = self.gList
        items = set(self.data.keys())
        index = 0
        #--Items to select afterwards. (Defaults to current selection.)
        if selected == 'SAME': selected = set(self.GetSelected())
        #--Update existing items.
        while index < gList.GetItemCount():
            item = self.GetItem(index)
            if item not in items:
                gList.DeleteItem(index)
            else:
                self.UpdateItem(index,item,selected)
                items.remove(item)
                index += 1
        #--Add remaining new items
        for item in items:
            gList.InsertStringItem(index,'')
            self.UpdateItem(index,item,selected)
            index += 1
        #--Cleanup
        self.UpdateIds()
        self.SortItems()
        self.mouseTexts.clear()

    def SortItems(self,column=None,reverse='CURRENT'):
        """Sort items. Real work is done by data object, and that completed
        sort is then "cloned" list through an intermediate cmp function.

        column: column to sort. Defaults to current sort column.

        reverse:
        * True: Reverse order
        * False: Normal order
        * 'CURRENT': Same as current order for column.
        * 'INVERT': Invert if column is same as current sort column.
        """
        #--Parse column and reverse arguments.
        data = self.data
        if self.sortDirty:
            self.sortDirty = False
            (column, reverse) = (None,'CURRENT')
        curColumn = self.sort
        column = column or curColumn
        curReverse = self.colReverse.get(column,False)
        if reverse == 'INVERT' and column == curColumn:
            reverse = not curReverse
        elif reverse in ('INVERT','CURRENT'):
            reverse = curReverse
        self.SetColumnReverse(column, reverse)
        self.SetSort(column)
        #--Sort
        items = self.data.getSorted(column,reverse)
        sortDict = dict((self.item_itemId[y],x) for x,y in enumerate(items))
        self.gList.SortItems(lambda x,y: cmp(sortDict[x],sortDict[y]))
        #--Done
        self.mouseTexts.clear()

    def SetColumnReverse(colummn, reverse):
        pass
    def SetSort(self,sort):
        pass

    def RefreshData(self):
        """Refreshes underlying data."""
        self.data.refresh()

    def RefreshReport(self):
        """(Optionally) Shows a report of changes after a data refresh."""
        report = self.data.getRefreshReport()
        if report: showInfo(self,report,self.data.title)

    def RefreshUI(self,items='ALL',details='SAME'):
        """Refreshes UI for specified file."""
        selected = self.GetSelected()
        if details == 'SAME':
            details = self.GetDetailsItem()
        elif details:
            selected = tuple(details)
        if items == 'ALL':
            self.UpdateItems(selected=selected)
        elif items in self.data:
            self.UpdateItem(self.GetIndex(items),items,selected=selected)
        else: #--Iterable
            for index in range(self.gList.GetItemCount()):
                if self.GetItem(index) in set(items):
                    self.UpdateItem(index,None,selected=selected)
        self.RefreshDetails(details)

    #--Details view (if it exists)
    def GetDetailsItem(self):
        """Returns item currently being shown in details view."""
        if self.details: return self.details.GetDetailsItem()
        return None

    def RefreshDetails(self,item=None):
        """Refreshes detail view associated with data from item."""
        if self.details: return self.details.RefreshDetails(item)
        item = item or self.GetDetailsItem()
        if item not in self.data: item = None

    #--Selected items
    def GetSelected(self):
        """Return list of items selected (hilighted) in the interface."""
        gList = self.gList
        return [self.GetItem(x) for x in range(gList.GetItemCount())
            if gList.GetItemState(x,wx.LIST_STATE_SELECTED)]

    def ClearSelected(self):
        """Unselect all items."""
        gList = self.gList
        for index in range(gList.GetItemCount()):
            if gList.GetItemState(index,wx.LIST_STATE_SELECTED):
                gList.SetItemState(index, 0, wx.LIST_STATE_SELECTED)

    #--Event Handlers -------------------------------------
    def OnMouse(self,event):
        """Check mouse motion to detect right click event."""
        if event.Moving():
            (mouseItem,mouseHitFlag) = self.gList.HitTest(event.GetPosition())
            if mouseItem != self.mouseItem:
                self.mouseItem = mouseItem
                self.MouseOverItem(mouseItem)
        elif event.Leaving() and self.mouseItem != None:
            self.mouseItem = None
            self.MouseOverItem(None)
        event.Skip()

    def MouseOverItem(self,item):
        """Handle mouse over item by showing tip or similar."""
        pass

    def OnItemSelected(self,event):
        """Item Selected: Refresh details."""
        self.RefreshDetails(self.GetItem(event.m_itemIndex))

    def OnSize(self, event):
        """Panel size was changed. Change gList size to match."""
        size = self.GetClientSizeTuple()
        self.gList.SetSize(size)

    def OnScroll(self,event):
        """Event: List was scrolled. Save so can be accessed later."""
        if event.GetOrientation() == wx.VERTICAL:
            self.data.setParam('vScrollPos',event.GetPosition())
        event.Skip()

    def OnColumnResize(self,event):
        """Column resized. Save column size info."""
        colDex = event.GetColumn()
        colName = self.cols[colDex]
        width = self.gList.GetColumnWidth(colDex)
        if width < 5:
            width = 5
            self.gList.SetColumnWidth(colDex, 5)
            event.Veto()
            self.gList.resizeLastColumn(0)
        else:
            event.Skip()
        self.colWidths[colName] = width

    def OnLeftDown(self,event):
        """Left mouse button was pressed."""
        #self.hitTest = self.gList.HitTest((event.GetX(),event.GetY()))
        event.Skip()

    def OnDClick(self,event):
        """Left mouse double click."""
        event.Skip()

    def OnColumnClick(self, event):
        """Column header was left clicked on. Sort on that column."""
        self.SortItems(self.cols[event.GetColumn()],'INVERT')

    def DoColumnMenu(self,event,iColumn=None):
        """Show column menu."""
        if not self.mainMenu: return
        if iColumn is None: iColumn = event.GetColumn()
        self.mainMenu.PopupMenu(self,Link.Frame,iColumn)

    def DoItemMenu(self,event):
        """Show item menu."""
        selected = self.GetSelected()
        if not selected:
            self.DoColumnMenu(event,0)
            return
        if not self.itemMenu: return
        self.itemMenu.PopupMenu(self,Link.Frame,selected)

    #--Standard data commands -------------------------------------------------
    def DeleteSelected(self):
        """Deletes selected items."""
        items = self.GetSelected()
        if not items: return
        message = _(r'Delete these items? This operation cannot be undone.')
        message += '\n* ' + '\n* '.join([self.data.getName(x) for x in items])
        if not askYes(self,message,_('Delete Items')): return False
        for item in items:
            del self.data[item]
        self.RefreshUI()
        self.data.setChanged()

# Links -----------------------------------------------------------------------
#------------------------------------------------------------------------------
class Links(list):
    """List of menu or button links."""
    class LinksPoint:
        """Point in a link list. For inserting, removing, appending items."""
        def __init__(self,list,index):
            self._list = list
            self._index = index
        def remove(self):
            del self._list[self._index]
        def replace(self,item):
            self._list[self._index] = item
        def insert(self,item):
            self._list.insert(self._index,item)
            self._index += 1
        def append(self,item):
            self._list.insert(self._index+1,item)
            self._index += 1

    #--Access functions:
    def getClassPoint(self,classObj):
        """Returns index"""
        for index,item in enumerate(self):
            if isinstance(item,classObj):
                return Links.LinksPoint(self,index)
        else:
            return None

    #--Popup a menu from the links
    def PopupMenu(self,parent,eventWindow=None,*args):
        eventWindow = eventWindow or parent
        menu = wx.Menu()
        for link in self:
            link.AppendToMenu(menu,parent,*args)
        eventWindow.PopupMenu(menu)
        menu.Destroy()

#------------------------------------------------------------------------------
class Link:
    """Link is a command to be encapsulated in a graphic element (menu item, button, etc.)"""
    Frame = None    # Frame to update the statusbar of
    Popup = None    # Current popup menu

    def __init__(self):
        self.id = None

    def AppendToMenu(self,menu,window,data):
        """Append self to menu as menu item."""
        if isinstance(window,Tank):
            self.gTank = window
            self.window = window
            self.selected = window.GetSelected()
            self.data = window.data
            self.title = window.data.title
        else:
            self.window = window
            self.data = data
        #--Generate self.id if necessary (i.e. usually)
        if not self.id: self.id = wx.NewId()
        Link.Popup = menu
        wx.EVT_MENU(Link.Frame,self.id,self.Execute)
        wx.EVT_MENU_HIGHLIGHT_ALL(Link.Frame,Link.ShowHelp)
        wx.EVT_MENU_OPEN(Link.Frame,Link.OnMenuOpen)

    def Execute(self, event):
        """Event: link execution."""
        raise AbstractError

    @staticmethod
    def OnMenuOpen(event):
        """Hover over a submenu, clear the status bar text"""
        Link.Frame.GetStatusBar().SetText('')

    @staticmethod
    def ShowHelp(event):
        """Hover over an item, set the statusbar text"""
        if Link.Popup:
            item = Link.Popup.FindItemById(event.GetId())
            if item:
                Link.Frame.GetStatusBar().SetText(item.GetHelp())
            else:
                Link.Frame.GetStatusBar().SetText('')

#------------------------------------------------------------------------------
class SeparatorLink(Link):
    """Link that acts as a separator item in menus."""

    def AppendToMenu(self,menu,window,data):
        """Add separator to menu."""
        menu.AppendSeparator()

#------------------------------------------------------------------------------
class MenuLink(Link):
    """Defines a submenu. Generally used for submenus of large menus."""

    def __init__(self,name,oneDatumOnly=False):
        """Initialize. Submenu items should append to self.links."""
        Link.__init__(self)
        self.name = name
        self.links = Links()
        self.oneDatumOnly = oneDatumOnly

    def AppendToMenu(self,menu,window,data):
        """Add self as submenu (along with submenu items) to menu."""
        subMenu = wx.Menu()
        for link in self.links:
            link.AppendToMenu(subMenu,window,data)
        menu.AppendMenu(-1,self.name,subMenu)
        if self.oneDatumOnly and len(data) != 1:
            id = menu.FindItem(self.name)
            menu.Enable(id,False)

# Tanks Links -----------------------------------------------------------------
#------------------------------------------------------------------------------
class Tanks_Open(Link):
    """Opens data directory in explorer."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Open...'),_("Open '%s'") % self.data.dir.tail)
        menu.AppendItem(menuItem)

    def Execute(self,event):
        """Handle selection."""
        dir = self.data.dir
        dir.makedirs()
        dir.start()

# Tank Links ------------------------------------------------------------------
#------------------------------------------------------------------------------
class Tank_Delete(Link):
    """Deletes selected file from tank."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menu.AppendItem(wx.MenuItem(menu,self.id,_('Delete')))

    def Execute(self,event):
        try:
            wx.BeginBusyCursor()
            self.gTank.DeleteSelected()
        finally:
            wx.EndBusyCursor()
#------------------------------------------------------------------------------
class Tank_Open(Link):
    """Open selected file(s)."""
    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        if len(data) == 1:
            help = _("Open '%s'") % data[0]
        else:
            help = _("Open selected files.")
        menuItem = wx.MenuItem(menu,self.id,_('Open...'),help)
        menu.AppendItem(menuItem)
        menuItem.Enable(bool(self.selected))

    def Execute(self,event):
        """Handle selection."""
        dir = self.data.dir
        for file in self.selected:
            dir.join(file).start()

#------------------------------------------------------------------------------
class Tank_Duplicate(Link):
    """Create a duplicate of a tank item, assuming that tank item is a file,
    and using a SaveAs dialog."""

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_('Duplicate...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.selected) == 1)

    def Execute(self,event):
        srcDir = self.data.dir
        srcName = self.selected[0]
        (root,ext) = srcName.rootExt
        (destDir,destName,wildcard) = (srcDir, root+' Copy'+ext,'*'+ext)
        destPath = askSave(self.gTank,_('Duplicate as:'),destDir,destName,wildcard)
        if not destPath: return
        destDir,destName = destPath.headTail
        if (destDir == srcDir) and (destName == srcName):
            balt.showError(self.window,_("Files cannot be duplicated to themselves!"))
            return
        self.data.copy(srcName,destName,destDir)
        if destDir == srcDir:
            self.gTank.RefreshUI()
