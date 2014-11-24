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
#  Wrye Bolt is distributed in the hope that it will be useful,
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

# Imports ---------------------------------------------------------------------
#--Localization
#..Handled by bolt, so import that.
import bolt
import bosh
from bolt import GPath, deprint
from bolt import BoltError, AbstractError, ArgumentError, StateError, UncodedError, CancelError, SkipError

#--Python
import cPickle
import StringIO
import string
import struct
import sys
import os
import textwrap
import time
import wx
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
from wx.lib.embeddedimage import PyEmbeddedImage
import wx.lib.newevent

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
        for id in xrange(self.BASE,self.MAX+1):
            yield id

# Constants -------------------------------------------------------------------
defId = wx.ID_ANY
defVal = wx.DefaultValidator
defPos = wx.DefaultPosition
defSize = wx.DefaultSize

wxListAligns = [wx.LIST_FORMAT_LEFT, wx.LIST_FORMAT_RIGHT, wx.LIST_FORMAT_CENTRE]

def fonts():
    font_default = wx.SystemSettings_GetFont(wx.SYS_DEFAULT_GUI_FONT)
    font_bold = wx.SystemSettings_GetFont(wx.SYS_DEFAULT_GUI_FONT)
    font_italic = wx.SystemSettings_GetFont(wx.SYS_DEFAULT_GUI_FONT)
    try:
        font_bold.SetWeight(wx.FONTWEIGHT_BOLD)
        font_italic.SetStyle(wx.FONTSTYLE_SLANT)
    except: #OLD wxpython!
        font_bold.SetWeight(wx.BOLD)
        font_italic.SetStyle(wx.SLANT)
    return (font_default, font_bold, font_italic)

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
        else:
            self.data[key] = value

    def __getitem__(self,key):
        """Dictionary syntax: color = colours[key]."""
        if key in self.data:
            key = self.data[key]
            if not isinstance(key,str):
                return key
        return wx.TheColourDatabase.Find(key)

    def __iter__(self):
        for key in self.data:
            yield key

#--Singleton
colors = Colors()

# Images ----------------------------------------------------------------------
images = {} #--Singleton for collection of images.

#----------------------------------------------------------------------
SmallUpArrow = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAADxJ"
    "REFUOI1jZGRiZqAEMFGke2gY8P/f3/9kGwDTjM8QnAaga8JlCG3CAJdt2MQxDCAUaOjyjKMp"
    "cRAYAABS2CPsss3BWQAAAABJRU5ErkJggg==")

#----------------------------------------------------------------------
SmallDnArrow = PyEmbeddedImage(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAEhJ"
    "REFUOI1jZGRiZqAEMFGke9QABgYGBgYWdIH///7+J6SJkYmZEacLkCUJacZqAD5DsInTLhDR"
    "bcPlKrwugGnCFy6Mo3mBAQChDgRlP4RC7wAAAABJRU5ErkJggg==")

#------------------------------------------------------------------------------
class Image:
    """Wrapper for images, allowing access in various formats/classes.

    Allows image to be specified before wx.App is initialized."""

    typesDict = {'png': wx.BITMAP_TYPE_PNG,
                 'jpg': wx.BITMAP_TYPE_JPEG,
                 'ico': wx.BITMAP_TYPE_ICO,
                 'bmp': wx.BITMAP_TYPE_BMP,
                 'tif': wx.BITMAP_TYPE_TIF,
                }

    def __init__(self,file,type=wx.BITMAP_TYPE_ANY,iconSize=16):
        self.file = GPath(file)
        self.type = type
        self.bitmap = None
        self.icon = None
        self.iconSize = iconSize
        if not GPath(self.file.s.split(u';')[0]).exists():
            raise ArgumentError(u"Missing resource file: %s." % self.file)

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
    pars = [textwrap.fill(text,width) for text in text.split(u'\n')]
    return u'\n'.join(pars)

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
                    deprint(u"index = -1, name = %s, value = %s" % (name, value))
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
            self.SetToolTip(tooltip(u''))

    def OnTextChange(self,event):
        self.UpdateToolTip(event.GetString())
        event.Skip()
    def OnSizeChange(self, event):
        self.UpdateToolTip(self.GetValue())
        event.Skip()

class comboBox(wx.ComboBox):
    """wx.ComboBox with automatic tooltip if text is wider than width of control."""
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
            self.SetToolTip(tooltip(u''))
        event.Skip()

def bitmapButton(parent,bitmap,pos=defPos,size=defSize,style=wx.BU_AUTODRAW,val=defVal,
        name=u'button',id=defId,onClick=None,tip=None,onRClick=None):
    """Creates a button, binds click function, then returns bound button."""
    gButton = wx.BitmapButton(parent,id,bitmap,pos,size,style,val,name)
    if onClick: gButton.Bind(wx.EVT_BUTTON,onClick)
    if onRClick: gButton.Bind(wx.EVT_CONTEXT_MENU,onRClick)
    if tip: gButton.SetToolTip(tooltip(tip))
    return gButton

def button(parent,label=u'',pos=defPos,size=defSize,style=0,val=defVal,
        name='button',id=defId,onClick=None,tip=None):
    """Creates a button, binds click function, then returns bound button."""
    gButton = wx.Button(parent,id,label,pos,size,style,val,name)
    if onClick: gButton.Bind(wx.EVT_BUTTON,onClick)
    if tip: gButton.SetToolTip(tooltip(tip))
    return gButton

def toggleButton(parent,label=u'',pos=defPos,size=defSize,style=0,val=defVal,
        name='button',id=defId,onClick=None,tip=None):
    """Creates a toggle button, binds toggle function, then returns bound button."""
    gButton = wx.ToggleButton(parent,id,label,pos,size,style,val,name)
    if onClick: gButton.Bind(wx.EVT_TOGGLEBUTTON,onClick)
    if tip: gButton.SetToolTip(tooltip(tip))
    return gButton

def checkBox(parent,label=u'',pos=defPos,size=defSize,style=0,val=defVal,
        name='checkBox',id=defId,onCheck=None,tip=None):
    """Creates a checkBox, binds check function, then returns bound button."""
    gCheckBox = wx.CheckBox(parent,id,label,pos,size,style,val,name)
    if onCheck: gCheckBox.Bind(wx.EVT_CHECKBOX,onCheck)
    if tip: gCheckBox.SetToolTip(tooltip(tip))
    return gCheckBox

def staticText(parent,label=u'',pos=defPos,size=defSize,style=0,name=u"staticText",id=defId,):
    """Static text element."""
    return wx.StaticText(parent,id,label,pos,size,style,name)

def spinCtrl(parent,value=u'',pos=defPos,size=defSize,style=wx.SP_ARROW_KEYS,
        min=0,max=100,initial=0,name=u'wxSpinctrl',id=defId,onSpin=None,tip=None):
    """Spin control with event and tip setting."""
    gSpinCtrl=wx.SpinCtrl(parent,id,value,pos,size,style,min,max,initial,name)
    if onSpin: gSpinCtrl.Bind(wx.EVT_SPINCTRL,onSpin)
    if tip: gSpinCtrl.SetToolTip(tooltip(tip))
    return gSpinCtrl

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
def askDirectory(parent,message=_(u'Choose a directory.'),defaultPath=u''):
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
def askContinue(parent,message,continueKey,title=_(u'Warning')):
    """Shows a modal continue query if value of continueKey is false. Returns True to continue.
    Also provides checkbox "Don't show this in future." to set continueKey to true."""
    #--ContinueKey set?
    if _settings.get(continueKey): return wx.ID_OK
    #--Generate/show dialog
    if canVista:
        result = vistaDialog(parent,
                             title=title,
                             message=message,
                             buttons=[(wx.ID_OK,'ok'),
                                      (wx.ID_CANCEL,'cancel'),
                                      ],
                             checkBox=_(u"Don't show this in the future."),
                             icon='warning',
                             heading=u'',
                             )
        check = result[1]
        result = result[0]
    else:
        dialog = wx.Dialog(parent,defId,title,size=(350,200),style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        icon = wx.StaticBitmap(dialog,defId,
            wx.ArtProvider_GetBitmap(wx.ART_WARNING,wx.ART_MESSAGE_BOX, (32,32)))
        gCheckBox = checkBox(dialog,_(u"Don't show this in the future."))
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
        check = gCheckBox.GetValue()
    if check:
        _settings[continueKey] = 1
    return result in (wx.ID_OK,wx.ID_YES)

def askContinueShortTerm(parent,message,title=_(u'Warning'),labels={}):
    """Shows a modal continue query  Returns True to continue.
    Also provides checkbox "Don't show this in for rest of operation."."""
    #--Generate/show dialog
    if canVista:
        buttons = []
        if wx.ID_OK in labels:
            buttons.append((wx.ID_OK,labels[wx.ID_OK]))
        for id in labels:
            if id in (wx.ID_OK,wx.ID_CANCEL):
                continue
            buttons.append((id,labels[id]))
        buttons.append((wx.ID_CANCEL,labels.get(wx.ID_CANCEL,'cancel')))
        result = vistaDialog(parent,
                             title=title,
                             message=message,
                             buttons=buttons,
                             checkBox=_(u"Don't show this for the rest of operation."),
                             icon='warning',
                             heading=u'',
                             )
        check = result[1]
        result = result[0]
    else:
        dialog = wx.Dialog(parent,defId,title,size=(350,200),style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        icon = wx.StaticBitmap(dialog,defId,
            wx.ArtProvider_GetBitmap(wx.ART_WARNING,wx.ART_MESSAGE_BOX, (32,32)))
        gCheckBox = checkBox(dialog,_(u"Don't show this for rest of operation."))
        #--Layout
        buttonSizer = hSizer(spacer)
        if wx.ID_OK in labels:
            okButton = button(dialog,id=wx.ID_OK,label=labels[wx.ID_OK])
        else:
            okButton = button(dialog,id=wx.ID_OK)
        buttonSizer.Add(okButton,0,wx.RIGHT,4)
        for id,lable in labels.itervalues():
            if id in (wx.ID_OK,wx.ID_CANCEL):
                continue
            but = button(dialog,id=id,label=lable)
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
        check = gCheckBox.GetValue()
    if result in (wx.ID_OK,wx.ID_YES):
        if check:
            return 2
        return True
    return False
#------------------------------------------------------------------------------
def askOpen(parent,title=u'',defaultDir=u'',defaultFile=u'',wildcard=u'',style=wx.FD_OPEN,mustExist=False):
    """Show as file dialog and return selected path(s)."""
    defaultDir,defaultFile = [GPath(x).s for x in (defaultDir,defaultFile)]
    dialog = wx.FileDialog(parent,title,defaultDir,defaultFile,wildcard, style)
    if dialog.ShowModal() != wx.ID_OK:
        result = False
    elif style & wx.FD_MULTIPLE:
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

def askOpenMulti(parent,title=u'',defaultDir=u'',defaultFile=u'',wildcard=u'',style=wx.FD_FILE_MUST_EXIST):
    """Show as open dialog and return selected path(s)."""
    return askOpen(parent,title,defaultDir,defaultFile,wildcard,wx.FD_OPEN|wx.FD_MULTIPLE|style)

def askSave(parent,title=u'',defaultDir=u'',defaultFile=u'',wildcard=u'',style=wx.FD_OVERWRITE_PROMPT):
    """Show as save dialog and return selected path(s)."""
    return askOpen(parent,title,defaultDir,defaultFile,wildcard,wx.FD_SAVE|style)

#------------------------------------------------------------------------------
def askText(parent,message,title=u'',default=u''):
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
def askNumber(parent,message,prompt=u'',title=u'',value=0,min=0,max=10000):
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
import win32gui
import win32api
import windows
canVista = windows.TASK_DIALOG_AVAILABLE

def getUACIcon(size='small'):
    if size == 'small':
        flag = windows.SHGSI_SMALLICON
    else:
        flag = windows.SHGSI_LARGEICON
    path,idex = windows.GetStockIconLocation(windows.SIID_SHIELD,flag)
    return path+u';%s' % idex

def setUAC(button,uac=True):
    windows.setUAC(button.GetHandle(),uac)

def _vistaDialog_Hyperlink(*args):
    file = args[1]
    windows.StartURL(file)

def vistaDialog(parent,message,title,buttons=[],checkBox=None,icon=None,commandLinks=True,footer=u'',expander=[],heading=u''):
    heading = heading if heading is not None else title
    title = title if heading is not None else u'Wrye Bash'
    dialog = windows.TaskDialog(title,heading,message,
                                buttons=[x[1] for x in buttons],
                                icon=icon,
                                parenthwnd=parent.GetHandle() if parent else None)
    dialog.bind(windows.HYPERLINK_CLICKED,_vistaDialog_Hyperlink)
    if footer:
        dialog.set_footer(footer)
    if expander:
        dialog.set_expander(expander,False,not footer)
    if checkBox:
        if isinstance(checkBox,basestring):
            dialog.set_check_box(checkBox,False)
        else:
            dialog.set_check_box(checkBox[0],checkBox[1])
    result = dialog.show(commandLinks)
    for id,title in buttons:
        if title.startswith(u'+'): title = title[1:]
        if title == result[0]:
            if checkBox:
                return (id,result[2])
            else:
                return id
    return (None,result[2])

def askStyled(parent,message,title,style,**kwdargs):
    """Shows a modal MessageDialog.
    Use ErrorMessage, WarningMessage or InfoMessage."""
    if canVista:
        buttons = []
        icon = None
        if style & wx.YES_NO:
            yes = 'yes'
            no = 'no'
            if style & wx.YES_DEFAULT:
                yes = 'Yes'
            elif style & wx.NO_DEFAULT:
                no = 'No'
            buttons.append((wx.ID_YES,yes))
            buttons.append((wx.ID_NO,no))
        if style & wx.OK:
            buttons.append((wx.ID_OK,'ok'))
        if style & wx.CANCEL:
            buttons.append((wx.ID_CANCEL,'cancel'))
        if style & (wx.ICON_EXCLAMATION|wx.ICON_INFORMATION):
            icon = 'warning'
        if style & wx.ICON_HAND:
            icon = 'error'
        result = vistaDialog(parent,
                             message=message,
                             title=title,
                             icon=icon,
                             buttons=buttons)
    else:
        dialog = wx.MessageDialog(parent,message,title,style)
        result = dialog.ShowModal()
        dialog.Destroy()
    return result in (wx.ID_OK,wx.ID_YES)

def askOk(parent,message,title=u'',**kwdargs):
    """Shows a modal error message."""
    return askStyled(parent,message,title,wx.OK|wx.CANCEL,**kwdargs)

def askYes(parent,message,title=u'',default=True,icon=wx.ICON_EXCLAMATION,**kwdargs):
    """Shows a modal warning or question message."""
    style = wx.YES_NO|icon|(wx.YES_DEFAULT if default else wx.NO_DEFAULT)
    return askStyled(parent,message,title,style,**kwdargs)

def askWarning(parent,message,title=_(u'Warning'),**kwdargs):
    """Shows a modal warning message."""
    return askStyled(parent,message,title,wx.OK|wx.CANCEL|wx.ICON_EXCLAMATION,**kwdargs)

def showOk(parent,message,title=u'',**kwdargs):
    """Shows a modal error message."""
    return askStyled(parent,message,title,wx.OK,**kwdargs)

def showError(parent,message,title=_(u'Error'),**kwdargs):
    """Shows a modal error message."""
    return askStyled(parent,message,title,wx.OK|wx.ICON_HAND,**kwdargs)

def showWarning(parent,message,title=_(u'Warning'),**kwdargs):
    """Shows a modal warning message."""
    return askStyled(parent,message,title,wx.OK|wx.ICON_EXCLAMATION,**kwdargs)

def showInfo(parent,message,title=_(u'Information'),**kwdargs):
    """Shows a modal information message."""
    return askStyled(parent,message,title,wx.OK|wx.ICON_INFORMATION,**kwdargs)

def showList(parent,header,items,maxItems=0,title=u'',**kwdargs):
    """Formats a list of items into a message for use in a Message."""
    numItems = len(items)
    if maxItems <= 0: maxItems = numItems
    message = string.Template(header).substitute(count=numItems)
    message += u'\n* '+u'\n* '.join(items[:min(numItems,maxItems)])
    if numItems > maxItems:
        message += u'\n'+_(u'(And %d others.)') % (numItems - maxItems,)
    return askStyled(parent,message,title,wx.OK,**kwdargs)

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

def showLog(parent,logText,title=u'',style=0,asDialog=True,fixedFont=False,icons=None,size=True,question=False):
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
    textCtrl = wx.TextCtrl(window,defId,logText,style=wx.TE_READONLY|wx.TE_MULTILINE|wx.TE_RICH2|wx.SUNKEN_BORDER)
    textCtrl.SetValue(logText)
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
def showWryeLog(parent,logText,title=u'',style=0,asDialog=True,icons=None):
    """Convert logText from wtxt to html and display. Optionally, logText can be path to an html file."""
    try:
        import wx.lib.iewin
    except ImportError:
        # Comtypes not available most likely! so do it this way:
        import os
        import webbrowser
        if not isinstance(logText,bolt.Path):
            logPath = _settings.get('balt.WryeLog.temp', bolt.Path.getcwd().join(u'WryeLogTemp.html'))
            cssDir = _settings.get('balt.WryeLog.cssDir', GPath(u''))
            ins = StringIO.StringIO(logText+u'\n{{CSS:wtxt_sand_small.css}}')
            with logPath.open('w',encoding='utf-8-sig') as out:
                bolt.WryeText.genHtml(ins,out,cssDir)
            ins.close()
            logText = logPath
        webbrowser.open(logText.s)
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
        logPath = _settings.get('balt.WryeLog.temp', bolt.Path.getcwd().join(u'WryeLogTemp.html'))
        cssDir = _settings.get('balt.WryeLog.cssDir', GPath(u''))
        ins = StringIO.StringIO(logText+u'\n{{CSS:wtxt_sand_small.css}}')
        with logPath.open('w',encoding='utf-8-sig') as out:
            bolt.WryeText.genHtml(ins,out,cssDir)
        ins.close()
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
        showError(parent,_(u"Invalid sound file %s.") % sound)

# Shell (OS) File Operations --------------------------------------------------
#------------------------------------------------------------------------------
try:
    from win32com.shell import shell, shellcon
    from win32com.shell.shellcon import FO_DELETE, FO_MOVE, FO_COPY, FO_RENAME

except ImportError:
    shellcon = None
    FO_DELETE = 0
    FO_MOVE = 1
    FO_COPY = 2
    FO_RENAME = 3

class FileOperationError(Exception):
    def __init__(self,errorCode):
        self.errno = errorCode
        Exception.__init__(self,u'FileOperationError: %i' % errorCode)

class AccessDeniedError(FileOperationError):
    def __init__(self):
        self.errno = 120
        Exception.__init__(self,u'FileOperationError: Access Denied')

FileOperationErrorMap = {
    120: AccessDeniedError,
    1223: CancelError,
    }

def fileOperation(operation,source,target=None,allowUndo=True,noConfirm=False,renameOnCollision=False,silent=False,parent=None):
    if not source:
        return {}

    abspath = os.path.abspath

    if isinstance(source,(bolt.Path,basestring)):
        source = GPath(abspath(GPath(source).s))
    else:
        source = [GPath(abspath(GPath(x).s)) for x in source]

    target = target if target else u''
    if isinstance(target,(bolt.Path,basestring)):
        target = GPath(abspath(GPath(target).s))
    else:
        target = [GPath(abspath(GPath(x).s)) for x in target]

    parent = parent.GetHandle() if parent else None

    if shell is not None:
        if isinstance(source,bolt.Path):
            source = source.s
        else:
            source = u'\x00'.join(x.s for x in source)

        if isinstance(target,bolt.Path):
            target = target.s
            multiDestFiles = 0
        else:
            target = u'\x00'.join(x.s for x in target)
            multiDestFiles = shellcon.FOF_MULTIDESTFILES

        flags = (shellcon.FOF_WANTMAPPINGHANDLE|
                 multiDestFiles)
        if allowUndo: flags |= shellcon.FOF_ALLOWUNDO
        if noConfirm: flags |= shellcon.FOF_NOCONFIRMATION
        if renameOnCollision: flags |= shellcon.FOF_RENAMEONCOLLISION
        if silent: flags |= shellcon.FOF_SILENT

        result,nAborted,mapping = shell.SHFileOperation(
            (parent,operation,source,target,flags,None,None))

        if result == 0:
            if nAborted:
                raise SkipError(nAborted if nAborted is not True else None)
            return dict(mapping)
        elif result == 2 and operation == FO_DELETE:
            # Delete failed because file didnt exist
            return dict(mapping)
        else:
            raise FileOperationErrorMap.get(result,FileOperationError(result))

    else:
        # Use custom dialogs and such
        # TODO: implement this
        if not isinstance(source,list):
            source = [source]
        if not isinstance(target,list):
            target = [target]

        # Delete
        if operation == FO_DELETE:
            # allowUndo - no effect, can't use recyle bin this way
            # noConfirm - ask if noConfirm is False
            # renameOnCollision - no effect, deleting files
            # silent - no real effect, since we don't show visuals when deleting this way
            if not noConfirm:
                message = _(u'Are you sure you want to permanently delete these %(count)d items?') % {'count':len(source)}
                message += u'\n\n' + '\n'.join([u' * %s' % x for x in source])
                if not askYes(parent,message,_(u'Delete Multiple Items')):
                    return {}
            # Do deletion
            for file in source:
                if not file.exists():
                    continue
                if file.isdir():
                    file.rmtree(file.stail)
                else:
                    file.remove()
            return {}
        # Only Delete is implemented so far
        raise Exception(u'Not Implemented')
        # Move
        if operation == FO_MOVE:
            # allowUndo - no effect, we're not going to track file movements manually
            # noConfirm - no real effect when moving
            # renameOnCollision - if moving collision, auto rename, otherwise ask
            # silent - no real effect, since we're not showing visuals
            collisions = []
            for fileFrom,fileTo in zip(source,target):
                if ((fileFrom.isdir() and fileTo.exists() and fileTo.isdir()) or
                    (fileFrom.isfile() and fileTo.exists() and fileTo.isfile())):
                    collisions.append(fileTo)
            if collisions:
                pass

def shellDelete(files,parent=None,askOk=True,recycle=True):
    try:
        return fileOperation(FO_DELETE,files,None,recycle,not askOk,True,False,parent)
    except CancelError:
        if askOk:
            return None
        raise

def shellMove(filesFrom,filesTo,parent=None,askOverwrite=True,allowUndo=True,autoRename=True):
    return fileOperation(FO_MOVE,filesFrom,filesTo,allowUndo,not askOverwrite,autoRename,False,parent)

def shellCopy(filesFrom,filesTo,parent=None,askOverwrite=True,allowUndo=True,autoRename=True):
    return fileOperation(FO_COPY,filesFrom,filesTo,allowUndo,not askOverwrite,autoRename,False,parent)

def shellMakeDirs(dirName,parent=None):
    if not dirName:
        return
    elif not isinstance(dirName,(list,tuple,set)):
        dirName = [dirName]
    #--Skip dirs that already exist
    dirName = [x for x in dirName if not x.exists()]
    #--Check for dirs that are impossible to create (the drive they are
    #  supposed to be on doesn't exist
    errorPaths = [dir for dir in dirName if not dir.drive().exists()]
    if errorPaths:
        raise BoltError(errorPaths)
    #--Checks complete, start working
    tempDirs = []
    tempDirsAppend = tempDirs.append
    fromDirs = []
    fromDirsAppend = fromDirs.append
    toDirs =[]
    toDirsAppend = toDirs.append
    try:
        for dir in dirName:
            # Attempt creating the directory via normal methods,
            # only, fall back to shellMove if UAC or something else
            # stopped it
            try:
                dir.makedirs()
            except:
                # Failed, try the UAC workaround
                tempDir = bolt.Path.tempDir(u'WryeBash_')
                tempDirsAppend(tempDir)
                toMake = []
                toMakeAppend = toMake.append
                while not dir.exists() and dir != dir.head:
                    # Need to test agains dir == dir.head to prevent
                    # infinite recursion if the final bit doesn't exist
                    toMakeAppend(dir.tail)
                    dir = dir.head
                if not toMake:
                    continue
                toMake.reverse()
                base = tempDir.join(toMake[0])
                toDir = dir.join(toMake[0])
                tempDir.join(*toMake).makedirs()
                fromDirsAppend(base)
                toDirsAppend(toDir)
        if fromDirs:
            # fromDirs will only get filled if dir.makedirs() failed
            shellMove(fromDirs,toDirs,parent,False,False,False)
    finally:
        for tempDir in tempDirs:
            tempDir.rmtree(safety=tempDir.stail)

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
        raise AbstractError # return []
    def add(self):
        """Peforms add operation. Return new item on success."""
        raise AbstractError # return None
    def edit(self,item=None):
        """Edits specified item. Return true on success."""
        raise AbstractError # return False
    def rename(self,oldItem,newItem):
        """Renames oldItem to newItem. Return true on success."""
        raise AbstractError # return False
    def remove(self,item):
        """Removes item. Return true on success."""
        raise AbstractError # return False
    def close(self):
        """Called when dialog window closes."""
        pass

    #--Info box
    def getInfo(self,item):
        """Returns string info on specified item."""
        return u''
    def setInfo(self,item,text):
        """Sets string info on specified item."""
        raise AbstractError

    #--Checklist
    def getChecks(self):
        """Returns checked state of items as array of True/False values matching Item list."""
        raise AbstractError # return []
    def check(self,item):
        """Checks items. Return true on success."""
        raise AbstractError # return False
    def uncheck(self,item):
        """Unchecks item. Return true on success."""
        raise AbstractError # return False

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
    def __init__(self, parent, title, data, id=wx.ID_ANY, type='list'):
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
            self.list = wx.CheckListBox(self,wx.ID_ANY,choices=self.items,style=wx.LB_SINGLE)
            for index,checked in enumerate(self.data.getChecks()):
                self.list.Check(index,checked)
            self.Bind(wx.EVT_CHECKLISTBOX, self.DoCheck, self.list)
        else:
            self.list = wx.ListBox(self,wx.ID_ANY,choices=self.items,style=wx.LB_SINGLE)
        self.list.SetSizeHints(125,150)
        self.list.Bind(wx.EVT_LISTBOX,self.OnSelect)
        #--Infobox
        if data.showInfo:
            self.gInfoBox = wx.TextCtrl(self,wx.ID_ANY,u" ",size=(130,-1),
                style=(self.data.infoReadOnly*wx.TE_READONLY)|wx.TE_MULTILINE|wx.SUNKEN_BORDER)
            if not self.data.infoReadOnly:
                self.gInfoBox.Bind(wx.EVT_TEXT,self.OnInfoEdit)
        else:
            self.gInfoBox = None
        #--Buttons
        buttonSet = (
            (data.showAction, _(u'Action'), self.DoAction),
            (data.showAdd,    _(u'Add'),    self.DoAdd),
            (data.showEdit,   _(u'Edit'),   self.DoEdit),
            (data.showRename, _(u'Rename'), self.DoRename),
            (data.showRemove, _(u'Remove'), self.DoRemove),
            (data.showSave,   _(u'Save'),   self.DoSave),
            (data.showCancel, _(u'Cancel'), self.DoCancel),
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

    # __enter__ and __exit__ for use with the 'with' statement
    def __enter__(self):
        return self
    def __exit__(self,type,value,traceback):
        self.Destroy()

    @staticmethod
    def Display(window, title, data):
        with ListEditor(window, title, data) as dialog:
            dialog.ShowModal()

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
        newName = askText(self,_(u'Rename to:'),_(u'Rename'),curName)
        if not newName or newName == curName:
            return
        elif newName in self.items:
            showError(self,_(u'Name must be unique.'))
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
            self.gInfoBox.SetValue(u'')

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
NoteBookDraggedEvent, EVT_NOTEBOOK_DRAGGED = wx.lib.newevent.NewEvent()

class TabDragMixin(object):
    """Mixin for the wx.Notebook class.  Enables draggable Tabs.
       Events:
         EVT_NB_TAB_DRAGGED: Called after a tab has been dragged
           event.oldIdex = old tab position (of tab that was moved
           event.newIdex = new tab position (of tab that was moved
    """
    __slots__=('__dragX','__dragging','__justSwapped')

    def __init__(self):
        self.__dragX = 0;
        self.__dragging = wx.NOT_FOUND
        self.__justSwapped = wx.NOT_FOUND
        self.Bind(wx.EVT_LEFT_DOWN, self.__OnDragStart)
        self.Bind(wx.EVT_LEFT_UP, self.__OnDragEnd)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.__OnDragEndForced)
        self.Bind(wx.EVT_MOTION, self.__OnDragging)

    def __OnDragStart(self, event):
        pos = event.GetPosition()
        self.__dragging = self.HitTest(pos)
        if self.__dragging != wx.NOT_FOUND:
            self.__dragX = pos[0]
            self.__justSwapped = wx.NOT_FOUND
            self.CaptureMouse()
        event.Skip()

    def __OnDragEndForced(self, event):
        self.__dragging = wx.NOT_FOUND
        self.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
        event.Skip()

    def __OnDragEnd(self, event):
        if self.__dragging != wx.NOT_FOUND:
            self.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
            self.__dragging = wx.NOT_FOUND
            try:
                self.ReleaseMouse()
            except:
                pass
        event.Skip()

    def __OnDragging(self, event):
        if self.__dragging != wx.NOT_FOUND:
            pos = event.GetPosition()
            if abs(pos[0] - self.__dragX) > 5:
                self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
            tabId = self.HitTest(pos)
            if tabId == wx.NOT_FOUND or tabId[0] in (wx.NOT_FOUND,self.__dragging[0]):
                self.__justSwapped = wx.NOT_FOUND
            else:
                if self.__justSwapped == tabId[0]:
                    return
                # We'll do the swapping by removing all pages in the way,
                # then readding them in the right place.  Do this because
                # it makes the tab we're dragging not have to refresh, whereas
                # if we just removed the current page and reinserted it in the
                # correct position, there would be refresh artifacts
                newPos = tabId[0]
                oldPos = self.__dragging[0]
                self.__justSwapped = oldPos
                self.__dragging = tabId[:]
                if newPos < oldPos:
                    left,right,step = newPos,oldPos,1
                else:
                    left,right,step = oldPos+1,newPos+1,-1
                insert = left+step
                addPages = [(self.GetPage(x),self.GetPageText(x)) for x in range(left,right)]
                addPages.reverse()
                num = right - left
                for i in range(num):
                    self.RemovePage(left)
                for page,title in addPages:
                    self.InsertPage(insert,page,title)
                evt = NoteBookDraggedEvent(fromIndex=oldPos,toIndex=newPos)
                wx.PostEvent(self,evt)
        event.Skip()

#------------------------------------------------------------------------------
class Picture(wx.Window):
    """Picture panel."""
    def __init__(self, parent,width,height,scaling=1,style=0,background=wx.MEDIUM_GREY_BRUSH):
        """Initialize."""
        wx.Window.__init__(self, parent, defId,size=(width,height),style=style)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.bitmap = None
        if background is not None:
            if isinstance(background, tuple):
                background = wx.Colour(background)
            if isinstance(background, wx.Colour):
                background = wx.Brush(background)
            self.background = background
        else:
            self.background = wx.Brush(self.GetBackgroundColour())
        #self.SetSizeHints(width,height,width,height)
        #--Events
        self.Bind(wx.EVT_PAINT,self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.OnSize()

    def SetBackground(self,background):
        if isinstance(background,tuple):
            background = wx.Colour(background)
        if isinstance(background,wx.Colour):
            background = wx.Brush(background)
        self.background = background
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
    def __init__(self,title=_(u'Progress'),message=u' '*60,parent=None,
            style=wx.PD_APP_MODAL|wx.PD_ELAPSED_TIME|wx.PD_AUTO_HIDE|wx.PD_SMOOTH,
            abort=False, onAbort=None):
        if abort:
            style |= wx.PD_CAN_ABORT
            self.fnAbort = onAbort
        self.dialog = wx.ProgressDialog(title,message,100,parent,style)
        self.dialog.SetFocus()
        bolt.Progress.__init__(self)
        self.message = message
        self.isDestroyed = False
        self.prevMessage = u''
        self.prevState = -1
        self.prevTime = 0

    # __enter__ and __exit__ for use with the 'with' statement
    def __enter__(self):
        return self
    def __exit__(self,type,value,traceback):
        self.Destroy()

    def getParent(self):
        return self.dialog.GetParent()

    def setCancel(self, enabled=True):
        cancel = self.dialog.FindWindowById(wx.ID_CANCEL)
        cancel.Enable(enabled)

    def onAbort(self):
        if self.fnAbort:
            return self.fnAbort()
        return True

    def doProgress(self,state,message):
        if not self.dialog:
            raise StateError(u'Dialog already destroyed.')
        elif (state == 0 or state == 1 or (message != self.prevMessage) or
            (state - self.prevState) > 0.05 or (time.time() - self.prevTime) > 0.5):
            self.dialog.SetFocus()
            if message != self.prevMessage:
                ret = self.dialog.Update(int(state*100),message)
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
        if index == wx.NOT_FOUND:   # Didn't drop it on an item
            if self.GetItemCount() > 0:
                if y <= self.GetItemRect(0).y:
                    # Dropped it before the first item
                    index = 0
                elif y >= self.GetItemRect(self.GetItemCount() - 1).y:
                    # Dropped it after the last item
                    index = self.GetItemCount()
                else:
                    # Dropped it on the edge of the list, but not above or below
                    return
            else:
                # Empty list
                index = 0
        else:
            # Dropped on top of an item
            target = index
            if target >= start and target <= stop:
                # Trying to drop it back on itself
                return
            elif target < start:
                # Trying to drop it furthur up in the list
                pass
            elif target > stop:
                # Trying to drop it further down the list
                index -= 1 + (stop-start)

            # If dropping on the top half of the item, insert above it,
            # otherwise insert below it
            rect = self.GetItemRect(target)
            if y > rect.y + rect.height/2:
                index += 1

        # Do the moving
        self.OnDropIndexes(indexes, index)

    def OnDropIndexes(self, indexes, newPos):
        if self.fnDropIndexes:
            wx.CallLater(10,self.fnDropIndexes,indexes,newPos)

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
            details=None,id=wx.ID_ANY,style=(wx.LC_REPORT | wx.LC_SINGLE_SEL),
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
        self.gList = gList = ListCtrl(self, wx.ID_ANY, style=style,
                                      dndFiles=dndFiles, dndList=dndList,
                                      fnDndAllow=self.dndAllow, fnDropIndexes=self.OnDropIndexes, fnDropFiles=self.OnDropFiles)
        if self.icons:
            gList.SetImageList(icons.GetImageList(),wx.IMAGE_LIST_SMALL)
        #--State info
        self.mouseItem = None
        self.mouseTexts = {}
        self.mouseTextPrev = u''
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
        self.mouseTexts[item] = data.getMouseText(iconKey,textKey,backKey)
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
        self.mouseTexts.clear()
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
            gList.InsertStringItem(index,u'')
            self.UpdateItem(index,item,selected)
            index += 1
        #--Cleanup
        self.UpdateIds()
        self.SortItems()

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

    def SetColumnReverse(self,column,reverse):
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
            for index in xrange(self.gList.GetItemCount()):
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
        return [self.GetItem(x) for x in xrange(gList.GetItemCount())
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
    def DeleteSelected(self,shellUI=False,noRecycle=False,_refresh=True):
        """Deletes selected items."""
        items = self.GetSelected()
        if not items: return
        if not shellUI:
            message = _(u'Delete these items? This operation cannot be undone.')
            message += u'\n* ' + u'\n* '.join([self.data.getName(x) for x in items])
            if not askYes(self,message,_(u'Delete Items')): return False
            for item in items:
                del self.data[item]
        else:
            try:
                self.data.delete(items,askOk=True,dontRecycle=noRecycle)
            except (CancelError,SkipError):
                pass
        if not _refresh: return  # TODO(ut): refresh below did not work for
        # BAIN - let's see with People tab (then delete _refresh parameter)
        self.RefreshUI()
        self.data.setChanged()

    def SelectItemAtIndex(self, index, _select=wx.LIST_STATE_SELECTED):
        self.gList.SetItemState(index, _select, _select)

# Links -----------------------------------------------------------------------
#------------------------------------------------------------------------------
class Links(list):
    """List of menu or button links."""
    class LinksPoint:
        """Point in a link list. For inserting, removing, appending items."""
        def __init__(self,_list,index):
            self._list = _list
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
class Link(object):
    """Link is a command to be encapsulated in a graphic element (menu item,
    button, etc.).

    Link objects are instantiated once in InitLinks() and then when the menu
    is popped up their AppendToMenu method creates a wx MenuItem or submenu.
    AppendToMenu initializes the Link instance data calling _initData
    (basically the items that are selected + some more if the window owning the
    menu is a Tank instance) to be used in the Execute method and also in some
    cases to decide if the menu item is enabled, checked etc (see subclasses).
    The only valid reason to override AppendToMenu is to prevent the menu to be
    appended.
    """ # TODO(ut): eliminate overrides of AppendToMenu
    # TODO(ut): change docs = split to +Link and MenuLink
    Frame = None    # Frame to update the statusbar of
    Popup = None    # Current popup menu

    def __init__(self):
        self.id = None
        self._dataInitialized = False  # TODO(ut): bin - only useful when we
        # override AppendToMenu and call _initData AND super.AppendToMenu
        # directly (InstallerArchive_Unpack, InstallerProject_Pack, ...?)

    def _initData(self, window, data):
        """Hack to separate data from presentation"""
        # TODO: Move to _Link subclass ? - init data and (Tank) gTank,
        # selected and data set (!) - document attributes...
        self.window = window
        if isinstance(window,Tank):
            self.gTank = window
            self.selected = window.GetSelected()
            self.data = window.data #TODO(ut)the same instance of InstallerData
        else:  # In mod list a list<Path>, in subpackage the index of the right clicked item
            self.data = data
        self._dataInitialized = True

    def AppendToMenu(self,menu,window,data):
        """Creates a wx menu item and appends it to :menu.

        Link implementation calls _initData, sets the Link.Popup (this must
        be moved to Links) generates a wx Id and returns None
        """
        if not self._dataInitialized: self._initData(window, data)
        self._dataInitialized = False # TODO(ut): turn this to a property or bin
        #--Generate self.id if necessary (i.e. usually)
        if not self.id: self.id = wx.NewId() # notice id remains the same - __init___ runs ONCE

# Link subclasses -------------------------------------------------------------
class _Link(Link): # TODO(ut): rename to ItemLink
    """TMP class to factor out duplicate code and wx dependencies.

    Subclasses MUST define text, help (preferably class) attributes OR
    override AppendToMenu().
    """
    kind = wx.ITEM_NORMAL  # the default in wx.MenuItem(... kind=...)

    def AppendToMenu(self,menu,window,data):
        """Append self as menu item and set callbacks to be executed when
        selected."""
        super(_Link, self).AppendToMenu(menu, window, data)
        # TODO(ut): is below MenuItem (_Link) specific ?
        Link.Popup = menu
        wx.EVT_MENU(Link.Frame,self.id,self.Execute)
        wx.EVT_MENU_HIGHLIGHT_ALL(Link.Frame,_Link.ShowHelp)
        menuItem = wx.MenuItem(menu, self.id, self.text, self.help,
                               self.__class__.kind)
        menu.AppendItem(menuItem)
        return menuItem

    # Callbacks ---------------------------------------------------------------
    def Execute(self, event):
        """Event: link execution."""
        raise AbstractError

    @staticmethod
    def ShowHelp(event):
        """Hover over an item, set the statusbar text"""
        if Link.Popup:
            item = Link.Popup.FindItemById(event.GetId())
            if item:
                Link.Frame.GetStatusBar().SetText(item.GetHelp())
            else:
                Link.Frame.GetStatusBar().SetText(u'')

class MenuLink(Link):
    """Defines a submenu. Generally used for submenus of large menus."""
    help = u'UNUSED'

    def __init__(self,name,oneDatumOnly=False):
        """Initialize. Submenu items should append themselves to self.links."""
        super(MenuLink, self).__init__()
        self.text = name # class attribute really (see _Link)
        self.links = Links()
        self.oneDatumOnly = oneDatumOnly

    def _enable(self): return not self.oneDatumOnly or len(self.selected) == 1

    def AppendToMenu(self,menu,window,data):
        """Append self as submenu (along with submenu items) to menu."""
        super(MenuLink, self).AppendToMenu(menu, window, data)
        wx.EVT_MENU_OPEN(Link.Frame,MenuLink.OnMenuOpen)
        subMenu = wx.Menu()
        menu.AppendMenu(self.id, self.text, subMenu)
        if not self._enable():
            menu.Enable(self.id, False)
        else: # do not append sub links unless submenu enabled
            for link in self.links: link.AppendToMenu(subMenu,window,data)

    @staticmethod
    def OnMenuOpen(event):
        """Hover over a submenu, clear the status bar text"""
        Link.Frame.GetStatusBar().SetText('')

class SeparatorLink(Link):
    """Link that acts as a separator item in menus."""

    def AppendToMenu(self,menu,window,data):
        """Add separator to menu."""
        menu.AppendSeparator()

# _Link subclasses ------------------------------------------------------------
class EnabledLink(_Link):
    """A menu item that may be disabled.

    The item is by default enabled. Override _enable() to disable\enable
    based on some condition. Subclasses MUST define self.text, preferably as
    a class attribute.
    """
    help = u''

    def _enable(self):
        """"Override as needed to enable or disable the menu item (enabled
        by default)."""
        return True

    def AppendToMenu(self, menu, window, data):
        menuItem = super(EnabledLink, self).AppendToMenu(menu, window, data)
        menuItem.Enable(self._enable())
        return menuItem

class CheckLink(_Link):
    kind = wx.ITEM_CHECK

    def _check(self): return True

    def AppendToMenu(self,menu,window,data):
        menuItem = super(CheckLink, self).AppendToMenu(menu, window, data)
        menuItem.Check(self._check())
        return menuItem

class RadioLink(CheckLink):
    kind = wx.ITEM_RADIO

class BoolLink(CheckLink):
    """Simple link that just toggles a setting."""
    text, key, help =  u'LINK TEXT', 'link.key', u'' # Override text and key !

    def __init__(self, opposite=False):
        super(BoolLink, self).__init__()
        self.opposite = opposite

    def _check(self): return bosh.settings[self.key] ^ self.opposite

    def Execute(self,event):
        bosh.settings[self.key] ^= True

# Tanks Links -----------------------------------------------------------------
#------------------------------------------------------------------------------
class Tanks_Open(_Link):
    """Opens data directory in explorer."""
    text = _(u'Open...')

    def _initData(self, window, data):
        super(Tanks_Open, self)._initData(window, data)
        self.help = _(u"Open '%s'") % self.data.dir.tail # data is Tank.data

    def Execute(self,event):
        """Handle selection."""
        dir = self.data.dir
        dir.makedirs()
        dir.start()

# Tank Links ------------------------------------------------------------------
#------------------------------------------------------------------------------
class Tank_Delete(_Link): # was used in BAIN would not refresh - used in People
    """Deletes selected file from tank."""
    text = _(u'Delete')
    help = _(u'Delete selected item(s)')

    def Execute(self,event):
        with BusyCursor():
            self.gTank.DeleteSelected()

#------------------------------------------------------------------------------
class Tank_Duplicate(Link):
    """Create a duplicate of a tank item, assuming that tank item is a file,
    and using a SaveAs dialog."""

    def AppendToMenu(self,menu,window,data):
        Link.AppendToMenu(self,menu,window,data)
        menuItem = wx.MenuItem(menu,self.id,_(u'Duplicate...'))
        menu.AppendItem(menuItem)
        menuItem.Enable(len(self.selected) == 1)

    def Execute(self,event):
        srcDir = self.data.dir
        srcName = self.selected[0]
        (root,ext) = srcName.rootExt
        (destDir,destName,wildcard) = (srcDir, root+u' Copy'+ext,u'*'+ext)
        destPath = askSave(self.gTank,_(u'Duplicate as:'),destDir,destName,wildcard)
        if not destPath: return
        destDir,destName = destPath.headTail
        if (destDir == srcDir) and (destName == srcName):
            self.showError(self.window,_(u"Files cannot be duplicated to themselves!"))
            return
        self.data.copy(srcName,destName,destDir)
        if destDir == srcDir:
            self.gTank.RefreshUI()

# wx Wrappers -----------------------------------------------------------------
#------------------------------------------------------------------------------
def copyToClipboard(text):
    if wx.TheClipboard.Open():
        wx.TheClipboard.SetData(wx.TextDataObject(text))
        wx.TheClipboard.Close()

def getKeyState(key): return wx.GetKeyState(key)
def getKeyState_Shift(): return wx.GetKeyState(wx.WXK_SHIFT)
def getKeyState_Control(): return wx.GetKeyState(wx.WXK_CONTROL)
