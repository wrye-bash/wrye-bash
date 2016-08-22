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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2015 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

# Imports ---------------------------------------------------------------------
import re

import bass # for dirs - try to avoid
#--Localization
#..Handled by bolt, so import that.
import bolt
from env import AccessDeniedError ##:same as above, env and balt should not mix
from bolt import GPath, deprint, BoltError, AbstractError, ArgumentError, \
    StateError, CancelError, SkipError
from bass import Resources
#--Python
import cPickle
import string
import textwrap
import time
import threading
from functools import partial, wraps
from collections import OrderedDict, namedtuple
#--wx
import wx
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
from wx.lib.embeddedimage import PyEmbeddedImage
import wx.lib.newevent

# Constants -------------------------------------------------------------------
defId = wx.ID_ANY
defVal = wx.DefaultValidator
defPos = wx.DefaultPosition
defSize = wx.DefaultSize

splitterStyle = wx.BORDER_NONE|wx.SP_LIVE_UPDATE#|wx.FULL_REPAINT_ON_RESIZE - doesn't seem to need this to work properly

# wx Types
wxPoint = wx.Point
wxSize = wx.Size

def fonts():
    font_default = wx.SystemSettings_GetFont(wx.SYS_DEFAULT_GUI_FONT)
    font_bold = wx.SystemSettings_GetFont(wx.SYS_DEFAULT_GUI_FONT)
    font_italic = wx.SystemSettings_GetFont(wx.SYS_DEFAULT_GUI_FONT)
    font_bold.SetWeight(wx.FONTWEIGHT_BOLD)
    font_italic.SetStyle(wx.FONTSTYLE_SLANT)
    Fonts = namedtuple('Fonts', ['default', 'bold', 'italic'])
    return Fonts(font_default, font_bold, font_italic)

# Settings --------------------------------------------------------------------
__unset = bolt.Settings(dictFile=None) # type information
_settings = __unset # must be bound to bosh.settings - smelly, see #174
sizes = {} #--Using applications should override this.

# Colors ----------------------------------------------------------------------
class Colors:
    """Colour collection and wrapper for wx.ColourDatabase.
    Provides dictionary syntax access (colors[key]) and predefined colours."""
    def __init__(self):
        self._colors = {}

    def __setitem__(self,key,value):
        """Add a color to the database."""
        if not isinstance(value,str):
            self._colors[key] = wx.Colour(*value)
        else:
            self._colors[key] = value

    def __getitem__(self,key):
        """Dictionary syntax: color = colours[key]."""
        if key in self._colors:
            key = self._colors[key]
            if not isinstance(key,str):
                return key
        return wx.TheColourDatabase.Find(key)

    def __iter__(self):
        for key in self._colors:
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

    def __init__(self, filename, imageType=wx.BITMAP_TYPE_ANY, iconSize=16):
        self.file = GPath(filename)
        self.type = imageType
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

    @staticmethod
    def GetImage(data, height, width):
        """Hasty wrapper around wx.EmptyImage - absorb to GetBitmap."""
        image = wx.EmptyImage(width, height)
        image.SetData(data)
        return image

    @staticmethod
    def Load(srcPath, quality):
        """Hasty wrapper around wx.Image - loads srcPath with specified
        quality if a jpeg."""
        bitmap = wx.Image(srcPath.s)
        # This only has an effect on jpegs, so it's ok to do it on every kind
        bitmap.SetOptionInt(wx.IMAGE_OPTION_QUALITY, quality)
        return bitmap

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
        self.images = []
        self.indices = {}
        self.imageList = None

    def Add(self,image,key):
        self.images.append((key,image))

    def GetImageList(self):
        if not self.imageList:
            indices = self.indices
            imageList = self.imageList = wx.ImageList(self.width,self.height)
            for key,image in self.images:
                indices[key] = imageList.Add(image.GetBitmap())
        return self.imageList

    def __getitem__(self,key):
        self.GetImageList()
        return self.indices[key]

# Images ----------------------------------------------------------------------
class ColorChecks(ImageList):
    """ColorChecks ImageList. Used by several List classes."""
    def __init__(self):
        ImageList.__init__(self, 16, 16)
        for state in (u'on', u'off', u'inc', u'imp'):
            for status in (u'purple', u'blue', u'green', u'orange', u'yellow',
                           u'red'):
                shortKey = status + u'.' + state
                imageKey = u'checkbox.' + shortKey
                file = GPath(bass.dirs['images'].join(
                    u'checkbox_' + status + u'_' + state + u'.png'))
                image = images[imageKey] = Image(file, Image.typesDict['png'])
                self.Add(image, shortKey)

    def Get(self,status,on):
        self.GetImageList()
        if on == 3:
            if status <= -20: shortKey = 'purple.imp'
            elif status <= -10: shortKey = 'blue.imp'
            elif status <= 0: shortKey = 'green.imp'
            elif status <=10: shortKey = 'yellow.imp'
            elif status <=20: shortKey = 'orange.imp'
            else: shortKey = 'red.imp'
        elif on == 2:
            if status <= -20: shortKey = 'purple.inc'
            elif status <= -10: shortKey = 'blue.inc'
            elif status <= 0: shortKey = 'green.inc'
            elif status <=10: shortKey = 'yellow.inc'
            elif status <=20: shortKey = 'orange.inc'
            else: shortKey = 'red.inc'
        elif on:
            if status <= -20: shortKey = 'purple.on'
            elif status <= -10: shortKey = 'blue.on'
            elif status <= 0: shortKey = 'green.on'
            elif status <=10: shortKey = 'yellow.on'
            elif status <=20: shortKey = 'orange.on'
            else: shortKey = 'red.on'
        else:
            if status <= -20: shortKey = 'purple.off'
            elif status <= -10: shortKey = 'blue.off'
            elif status == 0: shortKey = 'green.off'
            elif status <=10: shortKey = 'yellow.off'
            elif status <=20: shortKey = 'orange.off'
            else: shortKey = 'red.off'
        return self.indices[shortKey]

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

def setCheckListItems(checkListBox, names, values):
    """Convenience method for setting a bunch of wxCheckListBox items. The
    main advantage of this is that it doesn't clear the list unless it needs
    to. Which is good if you want to preserve the scroll position of the list.
    """
    if not names:
        checkListBox.Clear()
    else:
        for index, (name, value) in enumerate(zip(names, values)):
            if index >= checkListBox.GetCount():
                checkListBox.Append(name)
            else:
                if index == -1:
                    deprint(
                        u"index = -1, name = %s, value = %s" % (name, value))
                    continue
                checkListBox.SetString(index, name)
            checkListBox.Check(index, value)
        for index in range(checkListBox.GetCount(), len(names), -1):
            checkListBox.Delete(index - 1)

# Elements --------------------------------------------------------------------
def bell(arg=None):
    """"Rings the system bell and returns the input argument (useful for return bell(value))."""
    wx.Bell()
    return arg

def tooltip(text,wrap=50):
    """Returns tooltip with wrapped copy of text."""
    text = textwrap.fill(text,wrap)
    return wx.ToolTip(text)

class TextCtrl(wx.TextCtrl):
    """wx.TextCtrl with automatic tooltip if text goes past the width of the
    control."""

    def __init__(self, parent, value=u'', size=defSize, style=0,
                 multiline=False, autotooltip=True, name=wx.TextCtrlNameStr,
                 maxChars=None, onKillFocus=None, onText=None):
        if multiline: style |= wx.TE_MULTILINE ##: would it harm to have them all multiline ?
        wx.TextCtrl.__init__(self, parent, defId, value, size=size, style=style,
                             name=name)
        if maxChars: self.SetMaxLength(maxChars)
        if autotooltip:
            self.Bind(wx.EVT_TEXT, self.OnTextChange)
            self.Bind(wx.EVT_SIZE, self.OnSizeChange)
        # event handlers must call event.Skip()
        if onKillFocus:
            self.Bind(wx.EVT_KILL_FOCUS, lambda __event: onKillFocus())
        if onText: self.Bind(wx.EVT_TEXT, onText)

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

class RoTextCtrl(TextCtrl):
    """Set some styles to a read only textCtrl.

    Name intentionally ugly - tmp class to accommodate current code - do not
    use - do not imitate my fishing in kwargs."""
    def __init__(self, *args, **kwargs):
        """"To accommodate for common text boxes in Bash code - borderline"""
        # set some styles
        style = kwargs.get('style', 0)
        style |= wx.TE_READONLY
        special = kwargs.pop('special', False) # used in places
        if special: style |= wx.TE_RICH2 | wx.SUNKEN_BORDER
        if kwargs.pop('noborder', False): style |= wx.NO_BORDER
        if kwargs.pop('hscroll', False): style |= wx.HSCROLL
        kwargs['style'] = style
        # override default 'multiline' parameter value, 'False', with 'True'
        kwargs['multiline'] = kwargs.pop('multiline', True)
        super(RoTextCtrl, self).__init__(*args, **kwargs)

class ComboBox(wx.ComboBox):
    """wx.ComboBox with automatic tooltip if text is wider than width of control."""
    def __init__(self, *args, **kwdargs):
        autotooltip = kwdargs.pop('autotooltip', True)
        if kwdargs.pop('readonly', True):
            kwdargs['style'] = kwdargs.get('style', 0) | wx.CB_READONLY
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

def bitmapButton(parent, bitmap, tip=None, pos=defPos, size=defSize,
                 style=wx.BU_AUTODRAW, val=defVal, name=u'button',
                 onBBClick=None, onRClick=None):
    """Creates a button, binds click function, then returns bound button."""
    gButton = wx.BitmapButton(parent,defId,bitmap,pos,size,style,val,name)
    if onBBClick: gButton.Bind(wx.EVT_BUTTON, lambda __event: onBBClick())
    if onRClick: gButton.Bind(wx.EVT_CONTEXT_MENU,onRClick)
    if tip: gButton.SetToolTip(tooltip(tip))
    return gButton

class Button(wx.Button):
    _id = defId
    label = u''

    def __init__(self, parent, label=u'', pos=defPos, size=defSize, style=0,
                 val=defVal, name='button', onButClick=None,
                 onButClickEventful=None, tip=None, default=False):
        """Create a button and bind its click function.
        :param onButClick: a no args function to execute on button click
        :param onButClickEventful: a function accepting as parameter the
        EVT_BUTTON - messing with events outside balt is discouraged
        """
        if  not label and self.__class__.label: label = self.__class__.label
        wx.Button.__init__(self, parent, self.__class__._id,
                           label, pos, size, style, val, name)
        if onButClick and onButClickEventful:
            raise BoltError('Both onButClick and onButClickEventful specified')
        if onButClick: self.Bind(wx.EVT_BUTTON, lambda __event: onButClick())
        if onButClickEventful: self.Bind(wx.EVT_BUTTON, onButClickEventful)
        if tip: self.SetToolTip(tooltip(tip))
        if default: self.SetDefault()

class OkButton(Button): _id = wx.ID_OK
class CancelButton(Button):
    _id = wx.ID_CANCEL
    label = _(u'Cancel')

def ok_and_cancel_sizer(parent, okButton=None):
    siz = wx.StdDialogButtonSizer()
    okButton = okButton or OkButton(parent)
    okButton.SetDefault()
    siz.Add(okButton)
    siz.Add(CancelButton(parent))
    siz.Realize()
    return hSizer(hspacer, siz), 0, wx.EXPAND | wx.ALL ^ wx.TOP, 6

class SaveButton(Button):
    _id = wx.ID_SAVE
    label = _(u'Save')

class SaveAsButton(Button): _id = wx.ID_SAVEAS
class RevertButton(Button): _id = wx.ID_SAVE
class RevertToSavedButton(Button): _id = wx.ID_REVERT_TO_SAVED
class OpenButton(Button): _id = wx.ID_OPEN
class SelectAllButton(Button): _id = wx.ID_SELECTALL
class ApplyButton(Button): _id = wx.ID_APPLY

def toggleButton(parent, label=u'', pos=defPos, size=defSize, style=0,
                 val=defVal, name='button', onClickToggle=None, tip=None):
    """Creates a toggle button, binds toggle function, then returns bound
    button."""
    gButton = wx.ToggleButton(parent, defId, label, pos, size, style, val,
                              name)
    if onClickToggle: gButton.Bind(wx.EVT_TOGGLEBUTTON,
                                   lambda __event: onClickToggle())
    if tip: gButton.SetToolTip(tooltip(tip))
    return gButton

def checkBox(parent, label=u'', pos=defPos, size=defSize, style=0, val=defVal,
             name='checkBox', onCheck=None, tip=None, checked=False):
    """Creates a checkBox, binds check function, then returns bound button."""
    gCheckBox = wx.CheckBox(parent, defId, label, pos, size, style, val, name)
    if onCheck: gCheckBox.Bind(wx.EVT_CHECKBOX, lambda __event: onCheck())
    if tip: gCheckBox.SetToolTip(tooltip(tip))
    gCheckBox.SetValue(checked)
    return gCheckBox

class StaticText(wx.StaticText):
    """Static text element."""

    def __init__(self, parent, label=u'', pos=defPos, size=defSize, style=0,
                 noAutoResize=False, name=u"staticText"):
        if noAutoResize: style |= wx.ST_NO_AUTORESIZE
        wx.StaticText.__init__(self, parent, defId, label, pos, size, style,
                               name)
        self._label = label # save the unwrapped text
        self.Rewrap()

    def Rewrap(self, width=None):
        self.Freeze()
        self.SetLabel(self._label)
        self.Wrap(width or self.GetSize().width)
        self.Thaw()

def spinCtrl(parent, value=u'', pos=defPos, size=defSize,
             style=wx.SP_ARROW_KEYS, min=0, max=100, initial=0,
             name=u'wxSpinctrl', onSpin=None, tip=None):
    """Spin control with event and tip setting."""
    gSpinCtrl = wx.SpinCtrl(parent, defId, value, pos, size, style, min, max,
                            initial, name)
    if onSpin: gSpinCtrl.Bind(wx.EVT_SPINCTRL, lambda __event: onSpin())
    if tip: gSpinCtrl.SetToolTip(tooltip(tip))
    return gSpinCtrl

def listBox(parent, choices=None, **kwargs):
    kind = kwargs.pop('kind', 'list')
    # cater for existing CheckListBox and ListBox style variations
    style = 0
    if kwargs.pop('isSingle', kind == 'list'): style |= wx.LB_SINGLE
    if kwargs.pop('isSort', False): style |= wx.LB_SORT
    if kwargs.pop('isHScroll', False): style |= wx.LB_HSCROLL
    if kwargs.pop('isExtended', False): style |= wx.LB_EXTENDED
    cls = wx.ListBox if kind=='list' else wx.CheckListBox
    gListBox = cls(parent, choices=choices, style=style) if choices else cls(
        parent, style=style)
    callback = kwargs.pop('onSelect', None)
    if callback: gListBox.Bind(wx.EVT_LISTBOX, callback)
    return gListBox

def staticBitmap(parent, bitmap=None, size=(32, 32), special='warn'):
    """Tailored to current usages - IAW: do not use."""
    if bitmap is None:
        bmp = wx.ArtProvider_GetBitmap
        if special == 'warn':
            bitmap = bmp(wx.ART_WARNING,wx.ART_MESSAGE_BOX, size)
        elif special == 'undo':
            return bmp(wx.ART_UNDO,wx.ART_TOOLBAR,size)
        else: raise ArgumentError(u'special must be either warn or undo: ' +
                                  unicode(special, "utf-8") + u' given')
    return wx.StaticBitmap(parent, defId, bitmap)

# Sizers ----------------------------------------------------------------------
hspacer = ((0, 0), 1) #--Used to space elements apart.
def hspace(pixels=4):
    return (pixels, 0),

def vspace(pixels=4):
    return (0, pixels),

def _aSizer(sizer, *elements):
    """Adds elements to a sizer."""
    for element in elements:
        if isinstance(element,tuple):
            if element[0] is not None:
                sizer.Add(*element)
        elif element is not None:
            sizer.Add(element)
    return sizer

def hSizer(*elements):
    """Horizontal sizer."""
    return _aSizer(wx.BoxSizer(wx.HORIZONTAL), *elements)

def vSizer(*elements):
    """Vertical sizer and elements."""
    return _aSizer(wx.BoxSizer(wx.VERTICAL), *elements)

def hsbSizer(parent, box_label=u'', *elements):
    """A horizontal box sizer, but surrounded by a static box."""
    return _aSizer(wx.StaticBoxSizer(wx.StaticBox(parent, label=box_label),
                                     wx.HORIZONTAL), *elements)

# Modal Dialogs ---------------------------------------------------------------
#------------------------------------------------------------------------------
def askDirectory(parent,message=_(u'Choose a directory.'),defaultPath=u''):
    """Shows a modal directory dialog and return the resulting path, or None if canceled."""
    with wx.DirDialog(parent, message, GPath(defaultPath).s,
                      style=wx.DD_NEW_DIR_BUTTON) as dialog:
        if dialog.ShowModal() != wx.ID_OK: return None
        return GPath(dialog.GetPath())

#------------------------------------------------------------------------------
def askContinue(parent, message, continueKey, title=_(u'Warning')):
    """Show a modal continue query if value of continueKey is false. Return
    True to continue.
    Also provides checkbox "Don't show this in future." to set continueKey
    to true. continueKey must end in '.continue' - should be enforced
    """
    #--ContinueKey set?
    if _settings.get(continueKey): return wx.ID_OK
    #--Generate/show dialog
    if canVista:
        result = vistaDialog(parent,
                             title=title,
                             message=message,
                             buttons=[(wx.ID_OK, 'ok'),
                                      (wx.ID_CANCEL, 'cancel')],
                             checkBoxTxt=_(u"Don't show this in the future."),
                             icon='warning',
                             heading=u'',
                             )
        check = result[1]
        result = result[0]
    else:
        result, check = _continueDialog(parent, message, title,
                                        _(u"Don't show this in the future."))
    if check:
        _settings[continueKey] = 1
    return result in (wx.ID_OK,wx.ID_YES)

def askContinueShortTerm(parent, message, title=_(u'Warning')):
    """Shows a modal continue query  Returns True to continue.
    Also provides checkbox "Don't show this in for rest of operation."."""
    #--Generate/show dialog
    if canVista:
        buttons=[(wx.ID_OK, 'ok'), (wx.ID_CANCEL, 'cancel')]
        result = vistaDialog(parent,
                             title=title,
                             message=message,
                             buttons=buttons,
                             checkBoxTxt=_(u"Don't show this for the rest of operation."),
                             icon='warning',
                             heading=u'',
                             )
        check = result[1]
        result = result[0]
    else:
        result, check = _continueDialog(parent, message, title, _(
            u"Don't show this for rest of operation."))
    if result in (wx.ID_OK, wx.ID_YES):
        if check:
            return 2
        return True
    return False

def _continueDialog(parent, message, title, checkBoxText):
    with Dialog(parent, title, size=(350, 200)) as dialog:
        icon = staticBitmap(dialog)
        gCheckBox = checkBox(dialog, checkBoxText)
        #--Layout
        sizer = vSizer(
            (hSizer((icon, 0, wx.ALL, 6), hspace(6),
                    (StaticText(dialog, message, noAutoResize=True), 1,
                     wx.EXPAND)
                    ), 1, wx.EXPAND | wx.ALL, 6),
            (gCheckBox, 0, wx.EXPAND | wx.ALL ^ wx.TOP, 6),
            ok_and_cancel_sizer(dialog),
            )
        dialog.SetSizer(sizer)
        #--Get continue key setting and return
        result = dialog.ShowModal()
        check = gCheckBox.GetValue()
        return result, check

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
def askText(parent, message, title=u'', default=u'', strip=True):
    """Shows a text entry dialog and returns result or None if canceled."""
    with wx.TextEntryDialog(parent, message, title, default) as dialog:
        if dialog.ShowModal() != wx.ID_OK: return None
        txt = dialog.GetValue()
        return txt.strip() if strip else txt

#------------------------------------------------------------------------------
def askNumber(parent,message,prompt=u'',title=u'',value=0,min=0,max=10000):
    """Shows a text entry dialog and returns result or None if canceled."""
    with wx.NumberEntryDialog(parent, message, prompt, title, value, min,
                              max) as dialog:
        if dialog.ShowModal() != wx.ID_OK: return None
        return dialog.GetValue()

# Message Dialogs -------------------------------------------------------------
try:
    import windows as _win # only import here !
    canVista = _win.TASK_DIALOG_AVAILABLE
except ImportError: # bare linux (in wine it's imported but malfunctions)
    deprint('Importing windows.py failed', traceback=True)
    _win = None
    canVista = False

def vistaDialog(parent, message, title, buttons=[], checkBoxTxt=None,
                icon=None, commandLinks=True, footer=u'', expander=[],
                heading=u''):
    """Always guard with canVista == True"""
    heading = heading if heading is not None else title
    title = title if heading is not None else u'Wrye Bash'
    dialog = _win.TaskDialog(title, heading, message,
                             buttons=[x[1] for x in buttons],
                             main_icon=icon,
                             parenthwnd=parent.GetHandle() if parent else None,
                             footer=footer)
    dialog.bindHyperlink()
    if expander:
        dialog.set_expander(expander,False,not footer)
    if checkBoxTxt:
        if isinstance(checkBoxTxt,basestring):
            dialog.set_check_box(checkBoxTxt,False)
        else:
            dialog.set_check_box(checkBoxTxt[0],checkBoxTxt[1])
    button, radio, checkbox = dialog.show(commandLinks)
    for id_, title in buttons:
        if title.startswith(u'+'): title = title[1:]
        if title == button:
            if checkBoxTxt:
                return id_,checkbox
            else:
                return id_
    return None, checkbox

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

def askYes(parent, message, title=u'', default=True, questionIcon=False,
           **kwdargs):
    """Shows a modal warning or question message."""
    icon= wx.ICON_QUESTION if questionIcon else wx.ICON_EXCLAMATION
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
def _showLogClose(evt=None):
    """Handle log message closing."""
    window = evt.GetEventObject()
    if not window.IsIconized() and not window.IsMaximized():
        _settings['balt.LogMessage.pos'] = tuple(window.GetPosition())
        _settings['balt.LogMessage.size'] = tuple(window.GetSize())
    window.Destroy()

def showLog(parent, logText, title=u'', asDialog=True, fixedFont=False,
            icons=None, size=True):
    """Display text in a log window"""
    #--Sizing
    pos = _settings.get('balt.LogMessage.pos',defPos)
    if size:
        size = _settings.get('balt.LogMessage.size',(400,400))
    #--Dialog or Frame
    if asDialog:
        window = Dialog(parent, title, pos=pos, size=size)
    else:
        window = wx.Frame(parent,defId,title,pos=pos,size=size,
            style= (wx.RESIZE_BORDER | wx.CAPTION | wx.SYSTEM_MENU | wx.CLOSE_BOX | wx.CLIP_CHILDREN))
        if icons: window.SetIcons(icons)
    window.SetSizeHints(200,200)
    window.Bind(wx.EVT_CLOSE,_showLogClose)
    window.SetBackgroundColour(wx.NullColour) #--Bug workaround to ensure that default colour is being used.
    #--Text
    txtCtrl = RoTextCtrl(window, logText, special=True, autotooltip=False)
    txtCtrl.SetValue(logText)
    if fixedFont:
        fixedFont = wx.SystemSettings_GetFont(wx.SYS_ANSI_FIXED_FONT )
        fixedFont.SetPointSize(8)
        fixedStyle = wx.TextAttr()
        #fixedStyle.SetFlags(0x4|0x80)
        fixedStyle.SetFont(fixedFont)
        txtCtrl.SetStyle(0,txtCtrl.GetLastPosition(),fixedStyle)
    #--Buttons
    gOkButton = OkButton(window, onButClick=window.Close, default=True)
    #--Layout
    window.SetSizer(
        vSizer((txtCtrl,1,wx.EXPAND|wx.ALL^wx.BOTTOM,2),
               (gOkButton,0,wx.ALIGN_RIGHT|wx.ALL,4),
        ))
    #--Show
    if asDialog:
        with window: window.ShowModal()
    else: window.Show()

#------------------------------------------------------------------------------
def showWryeLog(parent, logText, title=u'', asDialog=True, icons=None):
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
            with logPath.open('w',encoding='utf-8-sig') as out, \
                 bolt.sio(logText+u'\n{{CSS:wtxt_sand_small.css}}') as ins:
                bolt.WryeText.genHtml(ins,out,cssDir)
            logText = logPath
        webbrowser.open(logText.s)
        return

    #--Sizing
    pos = _settings.get('balt.WryeLog.pos',defPos)
    size = _settings.get('balt.WryeLog.size',(400,400))
    #--Dialog or Frame
    if asDialog:
        window = Dialog(parent, title, pos=pos, size=size)
    else:
        window = wx.Frame(parent,defId,title,pos=pos,size=size,
            style= (wx.RESIZE_BORDER | wx.CAPTION | wx.SYSTEM_MENU | wx.CLOSE_BOX | wx.CLIP_CHILDREN))
        if icons: window.SetIcons(icons)
    window.SetSizeHints(200,200)
    window.Bind(wx.EVT_CLOSE,_showLogClose)
    #--Text
    textCtrl_ = wx.lib.iewin.IEHtmlWindow(window, defId, style = wx.NO_FULL_REPAINT_ON_RESIZE)
    if not isinstance(logText,bolt.Path):
        logPath = _settings.get('balt.WryeLog.temp', bolt.Path.getcwd().join(u'WryeLogTemp.html'))
        cssDir = _settings.get('balt.WryeLog.cssDir', GPath(u''))
        with logPath.open('w',encoding='utf-8-sig') as out, \
             bolt.sio(logText + u'\n{{CSS:wtxt_sand_small.css}}') as ins:
            bolt.WryeText.genHtml(ins,out,cssDir)
        logText = logPath
    textCtrl_.Navigate(logText.s,0x2) #--0x2: Clear History
    #--Buttons
    bitmap = wx.ArtProvider_GetBitmap(wx.ART_GO_BACK,wx.ART_HELP_BROWSER, (16,16))
    gBackButton = bitmapButton(window,bitmap, onBBClick=textCtrl_.GoBack)
    bitmap = wx.ArtProvider_GetBitmap(wx.ART_GO_FORWARD,wx.ART_HELP_BROWSER, (16,16))
    gForwardButton = bitmapButton(window,bitmap, onBBClick=textCtrl_.GoForward)
    gOkButton = OkButton(window, onButClick=window.Close, default=True)
    if not asDialog:
        window.SetBackgroundColour(gOkButton.GetBackgroundColour())
    #--Layout
    window.SetSizer(
        vSizer(
            (textCtrl_,1,wx.EXPAND|wx.ALL^wx.BOTTOM,2),
            (hSizer(
                gBackButton,
                gForwardButton,
                hspacer,
                gOkButton,
                ),0,wx.ALL|wx.EXPAND,4),
            )
        )
    #--Show
    if asDialog:
        window.ShowModal()
        if window:
            _settings['balt.WryeLog.pos'] = tuple(window.GetPosition())
            _settings['balt.WryeLog.size'] = tuple(window.GetSize())
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

# Other Windows ---------------------------------------------------------------
#------------------------------------------------------------------------------
class ListEditorData:
    """Data capsule for ListEditor. [Abstract]
    DEPRECATED: nest into ListEditor"""
    def __init__(self,parent):
        self.parent = parent #--Parent window.
        self.showAdd = False
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
    def getItemList(self):
        """Returns item list in correct order."""
        raise AbstractError # return []
    def add(self):
        """Performs add operation. Return new item on success."""
        raise AbstractError # return None
    def rename(self,oldItem,newItem):
        """Renames oldItem to newItem. Return true on success."""
        raise AbstractError # return False
    def remove(self,item):
        """Removes item. Return true on success."""
        raise AbstractError # return False

    #--Info box
    def getInfo(self,item):
        """Returns string info on specified item."""
        return u''
    def setInfo(self,item,text):
        """Sets string info on specified item."""
        raise AbstractError

    #--Save/Cancel
    def save(self):
        """Handles save button."""
        pass

#------------------------------------------------------------------------------
class Dialog(wx.Dialog):
    title = u'OVERRIDE'

    def __init__(self, parent=None, title=None, size=defSize, pos=defPos,
                 style=0, resize=True, caption=False):
        ##: drop parent/resize parameters(parent=Link.Frame (test),resize=True)
        self.sizesKey = self.__class__.__name__
        self.title = title or self.__class__.title
        style |= wx.DEFAULT_DIALOG_STYLE
        self.resizable = resize
        if resize: style |= wx.RESIZE_BORDER
        if caption: style |= wx.CAPTION
        super(Dialog, self).__init__(parent, title=self.title, size=size,
                                     pos=pos, style=style)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow) # used in ImportFaceDialog and ListEditor

    def OnCloseWindow(self, event):
        """Handle window close event.
        Remember window size, position, etc."""
        if self.resizable: sizes[self.sizesKey] = tuple(self.GetSize())
        event.Skip()

    @classmethod
    def Display(cls, *args, **kwargs):
        """Instantiate a dialog, display it and return the ShowModal result."""
        with cls(*args, **kwargs) as dialog:
            return dialog.ShowModal()

    def EndModalOK(self): self.EndModal(wx.ID_OK)

class ListEditor(Dialog):
    """Dialog for editing lists."""

    def __init__(self, parent, title, data, orderedDict=None):
        """A gui list, with buttons that act on the list items.

        Added kwargs to provide extra buttons - this class is built around a
        ListEditorData instance which needlessly complicates things - mainly
        a bunch of booleans to enable buttons but also the list of data that
        corresponds to (read is duplicated by) ListEditor._list_items.
        ListEditorData should be nested here.
        :param orderedDict: orderedDict['ButtonLabel']=buttonAction
        """
        #--Data
        self._listEditorData = data #--Should be subclass of ListEditorData
        self._list_items = data.getItemList()
        #--GUI
        super(ListEditor, self).__init__(parent, title)
        # overrides Dialog.sizesKey
        self.sizesKey = self._listEditorData.__class__.__name__
        #--Caption
        if data.caption:
            captionText = StaticText(self,data.caption)
        else:
            captionText = None
        #--List Box
        self.listBox = listBox(self, choices=self._list_items)
        self.listBox.SetSizeHints(125,150)
        #--Infobox
        if data.showInfo:
            self.gInfoBox = TextCtrl(self,size=(130,-1),
                style=(self._listEditorData.infoReadOnly*wx.TE_READONLY) |
                      wx.TE_MULTILINE | wx.SUNKEN_BORDER)
            if not self._listEditorData.infoReadOnly:
                self.gInfoBox.Bind(wx.EVT_TEXT,
                                   lambda __event: self.OnInfoEdit())
        else:
            self.gInfoBox = None
        #--Buttons
        buttonSet = [
            (data.showAdd,    _(u'Add'),    self.DoAdd),
            (data.showRename, _(u'Rename'), self.DoRename),
            (data.showRemove, _(u'Remove'), self.DoRemove),
            (data.showSave,   _(u'Save'),   self.DoSave),
            (data.showCancel, _(u'Cancel'), self.DoCancel),
            ]
        for k,v in (orderedDict or {}).items():
            buttonSet.append((True, k, v))
        if sum(bool(x[0]) for x in buttonSet):
            buttons = vSizer()
            for (flag,defLabel,func) in buttonSet:
                if not flag: continue
                label = (flag == True and defLabel) or flag
                buttons.Add(Button(self, label, onButClick=func),
                            0, wx.LEFT | wx.TOP, 4)
        else:
            buttons = None
        #--Layout
        sizer = vSizer(
            (captionText,0,wx.LEFT|wx.TOP,4),
            (hSizer(
                (self.listBox,1,wx.EXPAND|wx.TOP,4),
                (self.gInfoBox,self._listEditorData.infoWeight,wx.EXPAND|wx.TOP,4),
                (buttons,0,wx.EXPAND),
                ),1,wx.EXPAND)
            )
        #--Done
        if self.sizesKey in sizes:
            self.SetSizer(sizer)
            self.SetSize(sizes[self.sizesKey])
        else:
            self.SetSizerAndFit(sizer)

    def GetSelected(self):
        return self.listBox.GetNextItem(-1,wx.LIST_NEXT_ALL,wx.LIST_STATE_SELECTED)

    #--List Commands
    def DoAdd(self):
        """Adds a new item."""
        newItem = self._listEditorData.add()
        if newItem and newItem not in self._list_items:
            self._list_items = self._listEditorData.getItemList()
            index = self._list_items.index(newItem)
            self.listBox.InsertItems([newItem],index)

    def SetItemsTo(self, items):
        if self._listEditorData.setTo(items):
            self._list_items = self._listEditorData.getItemList()
            self.listBox.Set(self._list_items)

    def DoRename(self):
        """Renames selected item."""
        selections = self.listBox.GetSelections()
        if not selections: return bell()
        #--Rename it
        itemDex = selections[0]
        curName = self.listBox.GetString(itemDex)
        #--Dialog
        newName = askText(self, _(u'Rename to:'), _(u'Rename'), curName)
        if not newName or newName == curName:
            return
        elif newName in self._list_items:
            showError(self,_(u'Name must be unique.'))
        elif self._listEditorData.rename(curName,newName):
            self._list_items[itemDex] = newName
            self.listBox.SetString(itemDex,newName)

    def DoRemove(self):
        """Removes selected item."""
        selections = self.listBox.GetSelections()
        if not selections: return bell()
        #--Data
        itemDex = selections[0]
        item = self._list_items[itemDex]
        if not self._listEditorData.remove(item): return
        #--GUI
        del self._list_items[itemDex]
        self.listBox.Delete(itemDex)
        if self.gInfoBox:
            self.gInfoBox.DiscardEdits()
            self.gInfoBox.SetValue(u'')

    #--Show Info
    def OnInfoEdit(self):
        """Info box text has been edited."""
        selections = self.listBox.GetSelections()
        if not selections: return bell()
        item = self._list_items[selections[0]]
        if self.gInfoBox.IsModified():
            self._listEditorData.setInfo(item,self.gInfoBox.GetValue())

    #--Save/Cancel
    def DoSave(self):
        """Handle save button."""
        self._listEditorData.save()
        sizes[self.sizesKey] = tuple(self.GetSize())
        self.EndModal(wx.ID_OK)

    def DoCancel(self):
        """Handle cancel button."""
        sizes[self.sizesKey] = tuple(self.GetSize())
        self.EndModal(wx.ID_CANCEL)

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
        self.__dragX = 0
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

    def __OnDragEnd(self, event):
        if self.__dragging != wx.NOT_FOUND:
            self.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
            self.__dragging = wx.NOT_FOUND
            try:
                self.ReleaseMouse()
            except AssertionError:
                """PyAssertionError: C++ assertion "GetCapture() == this"
                failed at ..\..\src\common\wincmn.cpp(2536) in
                wxWindowBase::ReleaseMouse(): attempt to release mouse,
                but this window hasn't captured it""" # assertion error...
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
    def __exit__(self, exc_type, exc_value, exc_traceback):
        wx.EndBusyCursor()

#------------------------------------------------------------------------------
class Progress(bolt.Progress):
    """Progress as progress dialog."""
    _style = wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_SMOOTH

    def __init__(self, title=_(u'Progress'), message=u' '*60, parent=None,
                 abort=False, elapsed=True, __style=_style):
        if abort: __style |= wx.PD_CAN_ABORT
        self._elapsed = elapsed
        if elapsed: __style |= wx.PD_ELAPSED_TIME
        self.dialog = wx.ProgressDialog(title, message, 100, parent, __style)
        bolt.Progress.__init__(self)
        self.message = message
        self.isDestroyed = False
        self.prevMessage = u''
        self.prevState = -1
        self.prevTime = 0

    # __enter__ and __exit__ for use with the 'with' statement
    def __exit__(self, exc_type, exc_value, exc_traceback): self.Destroy()

    def getParent(self): return self.dialog.GetParent()

    def setCancel(self, enabled=True):
        cancel = self.dialog.FindWindowById(wx.ID_CANCEL)
        cancel.Enable(enabled)

    def _do_progress(self, state, message):
        if not self.dialog:
            raise StateError(u'Dialog already destroyed.')
        elif (state == 0 or state == 1 or (message != self.prevMessage) or (
                    state - self.prevState) > 0.05 or (
                    self._elapsed and (time.time() - self.prevTime) > 0.5)):
            if message != self.prevMessage:
                ret = self.dialog.Update(int(state*100),message)
            else:
                ret = self.dialog.Update(int(state*100))
            if not ret[0]:
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

    ALWAYS add new items via InsertListCtrlItem() and delete them via
    RemoveItemAt().
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

            self.data_object = wx.DataObjectComposite()
            self.dataFile = wx.FileDataObject()                 # Accept files
            self.dataList = wx.CustomDataObject('ListIndexes')  # Accept indexes from a list
            if dndFiles: self.data_object.Add(self.dataFile)
            if dndList : self.data_object.Add(self.dataList)
            self.SetDataObject(self.data_object)

        def OnData(self, x, y, data):
            if self.GetData():
                dtype = self.data_object.GetReceivedFormat().GetType()
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

    def __init__(self, parent, pos=defPos, size=defSize, style=0,
                 dndFiles=False, dndList=False, dndOnlyMoveContinuousGroup=True,
                 fnDropFiles=None, fnDropIndexes=None, fnDndAllow=None):
        wx.ListCtrl.__init__(self, parent, pos=pos, size=size, style=style)
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
        #--Item/Id mapping
        self._item_itemId = {}
        self._itemId_item = {}

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
                if start >=0 > stop:
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
            if start <= target <= stop:
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
        return self.doDnD and (not self.fnDndAllow or self.fnDndAllow())

    # API (alpha) -------------------------------------------------------------

    # Internal id <-> item mappings used in SortItems for now
    # Ripped from Tank - _Monkey patch_ - we need a proper ListCtrl subclass

    def __id(self, item):
        i = long(wx.NewId())
        self._item_itemId[item] = i
        self._itemId_item[i] = item
        return i

    def InsertListCtrlItem(self, index, value, item):
        """Insert an item to the list control giving it an internal id."""
        i = self.__id(item)
        some_long = self.InsertStringItem(index, value) # index ?
        gItem = self.GetItem(index) # that's what Tank did
        gItem.SetData(i)  # Associate our id with that row.
        self.SetItem(gItem) # this is needed too - yak
        return some_long

    def RemoveItemAt(self, index):
        """Remove item at specified list index."""
        itemId = self.GetItemData(index)
        item = self._itemId_item[itemId]
        del self._item_itemId[item]
        del self._itemId_item[itemId]
        self.DeleteItem(index)

    def DeleteAll(self):
        self._item_itemId.clear()
        self._itemId_item.clear()
        self.DeleteAllItems()

    def FindIndexOf(self, item):
        """Return index of specified item."""
        return self.FindItemData(-1, self._item_itemId[item])

    def FindItemAt(self, index):
        """Return item for specified list index."""
        return self._itemId_item[self.GetItemData(index)]

    def ReorderDisplayed(self, inorder):
        """Reorder the list control displayed items to match inorder."""
        sortDict = dict((self._item_itemId[y], x) for x, y in enumerate(inorder))
        self.SortItems(lambda x, y: cmp(sortDict[x], sortDict[y]))

#------------------------------------------------------------------------------
_depth = 0
_lock = threading.Lock() # threading not needed (I just can't omit it)
def conversation(func):
    """Decorator to temporarily unbind RefreshData Link.Frame callback."""
    @wraps(func)
    def _conversation_wrapper(*args, **kwargs):
        global _depth
        try:
            with _lock: _depth += 1 # hack: allow sequences of conversations
            Link.Frame.BindRefresh(bind=False)
            return func(*args, **kwargs)
        finally:
            with _lock: # atomic
                _depth -= 1
                if not _depth: Link.Frame.BindRefresh(bind=True)
    return _conversation_wrapper

class UIList(wx.Panel):
    """Offspring of basher.List and balt.Tank, ate its parents."""
    # optional menus
    mainMenu = None
    itemMenu = None
    #--gList image collection
    __icons = ImageList(16, 16) # sentinel value due to bass.dirs not being
    # yet initialized when balt is imported, so I can't use ColorChecks here
    icons = __icons
    _shellUI = False # only True in Screens/INIList/Installers
    _recycle = True # False on tabs that recycle makes no sense (People)
    max_items_open = 7 # max number of items one can open without prompt
    #--Cols
    _min_column_width = 24
    #--Style params
    _editLabels = False # allow editing the labels - also enables F2 shortcut
    _sunkenBorder = True
    _singleCell = False
    #--Sorting
    nonReversibleCols = {'Load Order', 'Current Order'}
    _default_sort_col = 'File' # override as needed
    _sort_keys = {} # sort_keys[col] provides the sort key for this col
    _extra_sortings = [] #extra self.methods for fancy sortings - order matters
    # Labels, map the (permanent) order of columns to the label generating code
    labels = OrderedDict()
    #--DnD
    _dndFiles = _dndList = False
    _dndColumns = ()

    def __init__(self, parent, keyPrefix, listData=None, panel=None):
        wx.Panel.__init__(self, parent, style=wx.WANTS_CHARS)
        self.data_store = listData # never use as local variable name !
        self.panel = panel
        #--Layout
        sizer = vSizer()
        self.SetSizer(sizer)
        #--Settings key
        self.keyPrefix = keyPrefix
        #--Columns
        self.__class__.persistent_columns = {self._default_sort_col}
        self._colDict = {} # used in setting column sort indicator
        #--gList image collection
        self.__class__.icons = ColorChecks() \
            if self.__class__.icons is self.__icons else self.__class__.icons
        #--gList
        ctrlStyle = wx.LC_REPORT
        if self.__class__._editLabels: ctrlStyle |= wx.LC_EDIT_LABELS
        if self.__class__._sunkenBorder: ctrlStyle |= wx.SUNKEN_BORDER
        if self.__class__._singleCell: ctrlStyle |= wx.LC_SINGLE_SEL
        self._gList = ListCtrl(self, style=ctrlStyle,
                               dndFiles=self.__class__._dndFiles,
                               dndList=self.__class__._dndList,
                               fnDndAllow=self.dndAllow,
                               fnDropFiles=self.OnDropFiles,
                               fnDropIndexes=self.OnDropIndexes)
        if self.icons:
            # Image List: Column sorting order indicators
            # explorer style ^ == ascending
            checkboxesIL = self.icons.GetImageList()
            self.sm_up = checkboxesIL.Add(SmallUpArrow.GetBitmap())
            self.sm_dn = checkboxesIL.Add(SmallDnArrow.GetBitmap())
            self._gList.SetImageList(checkboxesIL, wx.IMAGE_LIST_SMALL)
        if self.__class__._editLabels:
            self._gList.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnLabelEdited)
            self._gList.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginEditLabel)
        # gList callbacks
        self._gList.Bind(wx.EVT_LIST_COL_RIGHT_CLICK, self.DoColumnMenu)
        self._gList.Bind(wx.EVT_CONTEXT_MENU, self.DoItemMenu)
        self._gList.Bind(wx.EVT_LIST_COL_CLICK, self.OnColumnClick)
        self._gList.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self._gList.Bind(wx.EVT_CHAR, self.OnChar)
        #--Events: Columns
        self._gList.Bind(wx.EVT_LIST_COL_END_DRAG, self.OnColumnResize)
        #--Events: Items
        self._gList.Bind(wx.EVT_LEFT_DCLICK, self.OnDClick)
        self._gList.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
        self._gList.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        #--Mouse movement
        self.mouse_index = None
        self.mouseTexts = {} # dictionary item->mouse text
        self.mouseTextPrev = u''
        self._gList.Bind(wx.EVT_MOTION, self.OnMouse)
        self._gList.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouse)
        # Panel callbacks
        self.Bind(wx.EVT_SIZE,self.OnSize)
        # Columns
        self.PopulateColumns()
        #--Items
        self._defaultTextBackground = wx.SystemSettings.GetColour(
            wx.SYS_COLOUR_WINDOW)
        self.PopulateItems()

    # Column properties
    @property
    def allCols(self): return self.labels.keys()
    @property
    def colWidths(self):
        return _settings.getChanged(self.keyPrefix + '.colWidths', {})
    @property
    def colReverse(self): # not sure why it gets it changed but no harm either
        """Dictionary column->isReversed."""
        return _settings.getChanged(self.keyPrefix + '.colReverse', {})
    @property
    def cols(self): return _settings.getChanged(self.keyPrefix + '.cols')
    @property
    def autoColWidths(self):
        return _settings.get('bash.autoSizeListColumns', 0)
    @autoColWidths.setter
    def autoColWidths(self, val): _settings['bash.autoSizeListColumns'] = val
    # the current sort column
    @property
    def sort(self):
        return _settings.get(self.keyPrefix + '.sort', self._default_sort_col)
    @sort.setter
    def sort(self, val): _settings[self.keyPrefix + '.sort'] = val

    def OnItemSelected(self, event):
        modName = self.GetItem(event.m_itemIndex)
        self._select(modName)
    def _select(self, item): self.panel.SetDetails(item)

    #--Items ----------------------------------------------
    def PopulateItem(self, itemDex=-1, item=None):
        """Populate ListCtrl for specified item. Either item or itemDex must be
        specified.
        :param itemDex: the index of the item in the list - must be given if
        item is None
        :param item: a bolt.Path or an int (Masters) or a string (People),
        the key in self.data
        """
        insert = False
        if item is not None:
            try:
                itemDex = self.GetIndex(item)
            except KeyError: # item is not present, so inserting
                itemDex = self._gList.GetItemCount() # insert at the end
                insert = True
        else: # no way we're inserting with a None item
            item = self.GetItem(itemDex)
        cols = self.cols
        for colDex in range(len(cols)):
            col = cols[colDex]
            labelTxt = self.labels[col](self, item)
            if insert and colDex == 0:
                self._gList.InsertListCtrlItem(itemDex, labelTxt, item)
            else:
                self._gList.SetStringItem(itemDex, colDex, labelTxt)
        self.__setUI(item, itemDex)

    class _ListItemFormat(object):
        def __init__(self):
            self.icon_key = None
            self.back_key = 'default.bkgd'
            self.text_key = 'default.text'
            self.font = Resources.fonts.default
            self.underline = False

    def set_item_format(self, item, item_format):
        """Populate item_format attributes for text and background colors
        and set icon, font and mouse text. Responsible (applicable if the
        data_store is a FileInfo subclass) for calling getStatus (or
        tweak_status in Inis) to update respective info's status."""
        pass # screens, bsas

    def __setUI(self, fileName, itemDex):
        """Set font, status icon, background text etc."""
        gItem = self._gList.GetItem(itemDex)
        df = self._ListItemFormat()
        self.set_item_format(fileName, df)
        if df.icon_key and self.icons:
            if isinstance(df.icon_key, tuple):
                img = self.icons.Get(*df.icon_key)
            else: img = self.icons[df.icon_key]
            gItem.SetImage(img)
        if df.text_key: gItem.SetTextColour(colors[df.text_key])
        else: gItem.SetTextColour(self._gList.GetTextColour())
        if df.back_key: gItem.SetBackgroundColour(colors[df.back_key])
        else: gItem.SetBackgroundColour(self._defaultTextBackground)
        font = gItem.GetFont()
        font.SetUnderlined(df.underline)
        gItem.SetFont(font)
        self._gList.SetItem(gItem)

    def PopulateItems(self):
        """Sort items and populate entire list."""
        self.mouseTexts.clear()
        items = set(self.GetItems())
        #--Update existing items.
        index = 0
        while index < self._gList.GetItemCount():
            item = self.GetItem(index)
            if item not in items: self._gList.RemoveItemAt(index)
            else:
                self.PopulateItem(index)
                items.remove(item)
                index += 1
        #--Add remaining new items
        for item in items: self.PopulateItem(item=item)
        #--Sort
        self.SortItems()
        self.autosizeColumns()

    __all = ()
    def RefreshUI(self, **kwargs):
        """Populate specified files or ALL files, set status bar count.

        If there are any deleted (applies also to renamed) items leave files
        parameter alone.
        """
        # TODO(ut) needs work: A) deleted, new and files->modified **kwargs
        # parameters and get rid of ModList override(move part to PopulateItem)
        # Refresh UI uses must be optimized - pass in ONLY the items we need
        # refreshed - most of the time Refresh UI calls PopulateItems on ALL
        # items - a nono. Refresh UI has 106 uses...
        # B) Rework details: add 'select' tuple parameter (ex 'detail', duh) to
        # allow specifying detail item - for now use heuristics (len(files))
        files = kwargs.pop('files', self.__all)
        if files is self.__all:
            self.PopulateItems()
        else:  #--Iterable
            for file_ in files:
                self.PopulateItem(item=file_)
            #--Sort
            self.SortItems()
            self.autosizeColumns()
        # Details HACK: if it was a single item then refresh details for it:
        if len(files) == 1: self.SelectItem(files[0])
        else: self.panel.RefreshDetails()
        self.panel.SetStatusCount()

    #--Column Menu
    def DoColumnMenu(self, event, column=None):
        """Show column menu."""
        if not self.mainMenu: return
        if column is None: column = event.GetColumn()
        self.mainMenu.PopupMenu(self, Link.Frame, column)

    #--Item Menu
    def DoItemMenu(self,event):
        """Show item menu."""
        selected = self.GetSelected()
        if not selected:
            self.DoColumnMenu(event,0)
            return
        if not self.itemMenu: return
        self.itemMenu.PopupMenu(self,Link.Frame,selected)

    #-- Callbacks -------------------------------------------------------------
    def OnSize(self, event):
        """Panel size was changed. Change gList size to match."""
        size = tuple(self.GetClientSize())
        self._gList.SetSize(size)

    def OnMouse(self,event):
        """Handle mouse entered item by showing tip or similar."""
        if event.Moving():
            (itemDex, mouseHitFlag) = self._gList.HitTest(event.GetPosition())
            if itemDex != self.mouse_index:
                self.mouse_index = itemDex
                if itemDex >= 0:
                    item = self.GetItem(itemDex) # get the item for this index
                    text = self.mouseTexts.get(item, u'')
                    if text != self.mouseTextPrev:
                        Link.Frame.SetStatusInfo(text)
                        self.mouseTextPrev = text
        elif event.Leaving() and self.mouse_index is not None:
            self.mouse_index = None
            Link.Frame.SetStatusInfo(u'')
        event.Skip()

    def OnKeyUp(self, event):
        """Char event: select all items, delete selected items, rename."""
        code = event.GetKeyCode()
        if event.CmdDown() and code == ord('A'): # Ctrl+A
            try:
                self._gList.Unbind(wx.EVT_LIST_ITEM_SELECTED)
                self.panel.ClearDetails() #omit this to leave displayed details
                self._SelectAll()
            finally:
                self._gList.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
        elif self.__class__._editLabels and code == wx.WXK_F2: self.Rename()
        elif code in wxDelete:
            with BusyCursor(): self.DeleteItems(event=event)
        event.Skip()

    ##: Columns callbacks - belong to a ListCtrl mixin
    def OnColumnClick(self, event):
        """Column header was left clicked on. Sort on that column."""
        self.SortItems(self.cols[event.GetColumn()],'INVERT')

    def OnColumnResize(self, event):
        """Column resized: enforce minimal width and save column size info."""
        colDex = event.GetColumn()
        colName = self.cols[colDex]
        width = self._gList.GetColumnWidth(colDex)
        if width < self._min_column_width:
            width = self._min_column_width
            self._gList.SetColumnWidth(colDex, self._min_column_width)
            event.Veto() # if we do not veto the column will be resized anyway!
            self._gList.resizeLastColumn(0) # resize last column to fill
        else:
            event.Skip()
        self.colWidths[colName] = width

    # gList columns autosize---------------------------------------------------
    def autosizeColumns(self):
        if self.autoColWidths:
            colCount = xrange(self._gList.GetColumnCount())
            for i in colCount:
                self._gList.SetColumnWidth(i, -self.autoColWidths)

    #--Events skipped##:de-register callbacks? register only if hasattr(OnXXX)?
    def OnLeftDown(self,event): event.Skip()
    def OnDClick(self,event): event.Skip()
    def OnChar(self,event): event.Skip()
    #--Edit labels - only registered if _editLabels != False
    def OnBeginEditLabel(self, event):
        """Start renaming: deselect the extension."""
        to = len(GPath(event.GetLabel()).sbody)
        (self._gList.GetEditControl()).SetSelection(0, to)
    def OnLabelEdited(self,event): event.Skip()

    def _getItemClicked(self, event, on_icon=False):
        (hitItem, hitFlag) = self._gList.HitTest(event.GetPosition())
        if hitItem < 0 or (on_icon and hitFlag != wx.LIST_HITTEST_ONITEMICON):
            return None
        return self.GetItem(hitItem)

    #-- Item selection --------------------------------------------------------
    def GetItems(self): return self.data_store.keys()

    def _get_selected(self, lam=lambda i: i, __next_all=wx.LIST_NEXT_ALL,
                      __state_selected=wx.LIST_STATE_SELECTED):
        listCtrl, selected_list = self._gList, []
        i = listCtrl.GetNextItem(-1, __next_all, __state_selected)
        while i != -1:
            selected_list.append(lam(i))
            i = listCtrl.GetNextItem(i, __next_all, __state_selected)
        return selected_list

    def GetSelected(self):
        """Return list of items selected (highlighted) in the interface."""
        return self._get_selected(lam=self.GetItem)

    def GetSelectedIndexes(self):
        """Return list of indexes highlighted in the interface in display
        order."""
        return self._get_selected()

    def SelectItemAtIndex(self, index, select=True,
                          __select=wx.LIST_STATE_SELECTED):
        self._gList.SetItemState(index, select * __select, __select)

    def SelectItem(self, item, deselectOthers=False):
        dex = self.GetIndex(item)
        if deselectOthers: self.ClearSelected()
        else: #we must deselect the item and then reselect for callbacks to run
            self.SelectItemAtIndex(dex, select=False)
        self.SelectItemAtIndex(dex)

    def SelectItemsNoCallback(self, items, deselectOthers=False):
        if deselectOthers: self.ClearSelected()
        try:
            self._gList.Unbind(wx.EVT_LIST_ITEM_SELECTED)
            for item in items: self.SelectItem(item)
        finally:
            self._gList.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)

    def ClearSelected(self, clear_details=False):
        """Unselect all items."""
        self.SelectItemAtIndex(-1, False) # -1 indicates 'all items'
        if clear_details: self.panel.ClearDetails()

    def _SelectAll(self): # only called after unbinding EVT_LIST_ITEM_SELECTED
        self.SelectItemAtIndex(-1) # -1 indicates 'all items'

    def SelectLast(self):
        self.SelectItemAtIndex(self._gList.GetItemCount() - 1)

    def DeleteAll(self): self._gList.DeleteAll()

    def EnsureVisibleItem(self, name, focus=False):
        self.EnsureVisibleIndex(self.GetIndex(name), focus=focus)

    def EnsureVisibleIndex(self, dex, focus=False):
        self._gList.Focus(dex) if focus else self._gList.EnsureVisible(dex)
        self._gList.SetFocus()

    def SelectAndShowItem(self, item, deselectOthers=False, focus=True):
        self.SelectItem(item, deselectOthers=deselectOthers)
        self.EnsureVisibleItem(item, focus=focus)

    def OpenSelected(self, selected=None):
        """Open selected files with default program."""
        dataDir = self.data_store.dir
        selected = selected if selected else self.GetSelected()
        num = len(selected)
        if num > UIList.max_items_open and not askContinue(self,
            _(u'Trying to open %(num)s items - are you sure ?') % {'num': num},
            'bash.maxItemsOpen.continue'): return
        for file_ in selected:
            file_ = dataDir.join(file_)
            if file_.exists(): file_.start()

    #--Sorting ----------------------------------------------------------------
    def SortItems(self, column=None, reverse='CURRENT'):
        """Sort items. Real work is done by _SortItems, and that completed
        sort is then "cloned" to the list control.

        :param column: column to sort. Defaults to current sort column.
        :param reverse:
        * True: Reverse order
        * False: Normal order
        * 'CURRENT': Same as current order for column.
        * 'INVERT': Invert if column is same as current sort column.
        """
        column, reverse, oldcol = self._GetSortSettings(column, reverse)
        items = self._SortItems(column, reverse)
        self._gList.ReorderDisplayed(items)
        self._setColumnSortIndicator(column, oldcol, reverse)

    def _GetSortSettings(self, column, reverse):
        """Return parsed col, reverse arguments. Used by SortItems.
        col: sort variable.
          Defaults to last sort. (self.sort)
        reverse: sort order
          True: Descending order
          False: Ascending order
         'CURRENT': Use current reverse setting for sort variable.
         'INVERT': Use current reverse settings for sort variable, unless
             last sort was on same sort variable -- in which case,
             reverse the sort order.
        """
        curColumn = self.sort
        column = column or curColumn
        curReverse = self.colReverse.get(column, False)
        if column in self.nonReversibleCols: #--Disallow reverse for load
            reverse = False
        elif reverse == 'INVERT' and column == curColumn:
            reverse = not curReverse
        elif reverse in {'INVERT','CURRENT'}:
            reverse = curReverse
        #--Done
        self.sort = column
        self.colReverse[column] = reverse
        return column, reverse, curColumn

    def _SortItems(self, col, reverse=False, items=None, sortSpecial=True):
        """Sort and return items by specified column, possibly in reverse
        order.

        If items are not specified, sort what is returned by GetItems() and
        return that. If sortSpecial is False do not apply extra sortings."""
        items = items if items is not None else self.GetItems()
        def key(k): # if key is None then keep it None else provide self
            k = self._sort_keys[k]
            return k if k is None else partial(k, self)
        defaultKey = key(self._default_sort_col)
        defSort = col == self._default_sort_col
        # always apply default sort
        items.sort(key=defaultKey, reverse=defSort and reverse)
        if not defSort: items.sort(key=key(col), reverse=reverse)
        if sortSpecial:
            for lamda in self._extra_sortings: lamda(self, items)
        return items

    def _setColumnSortIndicator(self, col, oldcol, reverse):
        # set column sort image
        try:
            listCtrl = self._gList
            try: listCtrl.ClearColumnImage(self._colDict[oldcol])
            except KeyError:
                pass # if old column no longer is active this will fail but
                #  not a problem since it doesn't exist anyways.
            listCtrl.SetColumnImage(self._colDict[col],
                                    self.sm_dn if reverse else self.sm_up)
        except KeyError: pass

    #--Item/Index Translation -------------------------------------------------
    def GetItem(self,index):
        """Returns item for specified list index."""
        return self._gList.FindItemAt(index)

    def GetIndex(self,item):
        """Return index for item, raise KeyError if item not present."""
        return self._gList.FindIndexOf(item)

    #--Populate Columns -------------------------------------------------------
    def PopulateColumns(self):
        """Create/name columns in ListCtrl."""
        cols = self.cols # this may have been updated in ColumnsMenu.Execute()
        numCols = len(cols)
        names = set(_settings['bash.colNames'].get(key) for key in cols)
        self._colDict.clear()
        colDex, listCtrl = 0, self._gList
        while colDex < numCols: ##: simplify!
            colKey = cols[colDex]
            colName = _settings['bash.colNames'].get(colKey, colKey)
            colWidth = self.colWidths.get(colKey, 30)
            if colDex >= listCtrl.GetColumnCount(): # Make a new column
                listCtrl.InsertColumn(colDex, colName)
                listCtrl.SetColumnWidth(colDex, colWidth)
            else: # Update an existing column
                column = listCtrl.GetColumn(colDex)
                text = column.GetText()
                if text == colName:
                    # Don't change it, just make sure the width is correct
                    listCtrl.SetColumnWidth(colDex, colWidth)
                elif text not in names:
                    # Column that doesn't exist anymore
                    listCtrl.DeleteColumn(colDex)
                    continue # do not increment colDex or update colDict
                else: # New column
                    listCtrl.InsertColumn(colDex, colName)
                    listCtrl.SetColumnWidth(colDex, colWidth)
            self._colDict[colKey] = colDex
            colDex += 1
        while listCtrl.GetColumnCount() > numCols:
            listCtrl.DeleteColumn(numCols)

    #--Drag and Drop-----------------------------------------------------------
    def dndAllow(self):
        # Only allow drag an drop when sorting by the columns specified in dndColumns
        return self.sort in self._dndColumns

    def OnDropFiles(self, x, y, filenames): raise AbstractError
    def OnDropIndexes(self, indexes, newPos): raise AbstractError

    # gList scroll position----------------------------------------------------
    def SaveScrollPosition(self, isVertical=True):
        _settings[self.keyPrefix + '.scrollPos'] = self._gList.GetScrollPos(
            wx.VERTICAL if isVertical else wx.HORIZONTAL)

    def SetScrollPosition(self):
        self._gList.ScrollLines(
            _settings.get(self.keyPrefix + '.scrollPos', 0))

    # Data commands (WIP)------------------------------------------------------
    def Rename(self, selected=None):
        if not selected: selected = self.GetSelected()
        if selected:
            index = self.GetIndex(selected[0])
            if index != -1:
                self._gList.EditLabel(index)

    def validate_filename(self, event, has_digits=False, ext=u'', add_ext=u''):
        if event.IsEditCancelled(): return None, None
        newName = event.GetLabel()
        if add_ext and not newName.lower().endswith(add_ext):
            newName += add_ext
        regex = u'^([^/\\:*?"<>|]+?)'
        if has_digits: regex += u'(\d*)'
        regex += ext + u'$'
        rePattern = re.compile(regex, re.I | re.U)
        maPattern = rePattern.match(newName)
        if not maPattern:
            showError(self, _(u'Bad extension or file root: ') + newName)
            event.Veto()
        return maPattern, newName

    @conversation
    def DeleteItems(self, event=None, items=None,
                    dialogTitle=_(u'Delete Items'), order=True):
        recycle = (self.__class__._recycle and
        # menu items fire 'CommandEvent' - I need a workaround to detect Shift
            (True if event is None else not event.ShiftDown()))
        items = self._toDelete(items)
        if not self.__class__._shellUI:
            items = self._promptDelete(items, dialogTitle, order, recycle)
        if not items: return
        for i in items: ##: simplify and make sure delete_Refresh() runs !
            try:
                if not self.__class__._shellUI: # non shellUI path used to
                    # delete as many as possible, I kept this behavior
                    self.data_store.delete(i, doRefresh=False, recycle=recycle)
                else: # shellUI path tries to delete all at once
                    self.data_store.delete(items, confirm=True, recycle=recycle)
            except bolt.BoltError as e: showError(self, u'%r' % e)
            except (AccessDeniedError, CancelError, SkipError): pass
            finally:
                if self.__class__._shellUI: break # could delete fail mid-way ?
        else:
            self.data_store.delete_Refresh(items, check_existence=True)
        self.RefreshUI(refreshSaves=True) # also cleans _gList internal dicts

    def _toDelete(self, items):
        return items if items is not None else self.GetSelected()

    def _promptDelete(self, items, dialogTitle, order, recycle):
        if not items: return items
        message = [u'', _(u'Uncheck items to skip deleting them if desired.')]
        if order: items.sort()
        message.extend(items)
        msg = _(u'Delete these items to the recycling bin ?') if recycle else \
            _(u'Delete these items?  This operation cannot be undone.')
        with ListBoxes(self, dialogTitle, msg, [message]) as dialog:
            if not dialog.askOkModal(): return []
            return dialog.getChecked(message[0], items)

    # Generate unique filenames when duplicating files etc
    @staticmethod
    def _new_name(new_name, count):
        count += 1
        new_name = GPath(new_name.root + (u' (%d)' % count) + new_name.ext)
        return new_name, count

    def new_name(self, new_name):
        base_name, count = new_name, 0
        while new_name in self.data_store:
            new_name, count = self._new_name(base_name, count)
        return new_name

    @staticmethod
    def new_path(new_name, dest_dir):
        base_name, count = new_name, 0
        while dest_dir.join(new_name).exists() and count < 1000:
            new_name, count = UIList._new_name(base_name, count)
        return new_name

# Links -----------------------------------------------------------------------
#------------------------------------------------------------------------------
class Links(list):
    """List of menu or button links."""

    #--Popup a menu from the links
    def PopupMenu(self, parent=None, eventWindow=None, *args):
        parent = parent or Link.Frame
        eventWindow = eventWindow or parent
        menu = wx.Menu()
        Link.Popup = menu
        for link in self:
            link.AppendToMenu(menu,parent,*args)
        eventWindow.PopupMenu(menu)
        menu.Destroy()
        Link.Popup = None # do not leak the menu reference

#------------------------------------------------------------------------------
class Link(object):
    """Link is a command to be encapsulated in a graphic element (menu item,
    button, etc.).

    Subclasses MUST define a text attribute (the menu label) preferably as a
    class attribute, or if it depends on current state by overriding
    _initData().
    Link objects are _not_ menu items. They are instantiated _once_ in
    InitLinks(). Their AppendToMenu() is responsible for creating a wx MenuItem
    or wx submenu and append this to the currently popped up wx menu.
    Contract:
    - Link.__init__() is called _once_, _before the Bash app is initialized_,
    except for "local" Link subclasses used in ChoiceLink related code.
    - Link.AppendToMenu() overrides stay confined in balt.
    - Link.Frame is set once and for all to the (ex) basher.bashFrame
      singleton. Use (sparingly) as the 'link' between menus and data layer.
    """
    Frame = None   # BashFrame singleton, set once and for all in BashFrame()
    Popup = None   # Current popup menu, set in Links.PopupMenu()
    text = u''     # Menu label (may depend on UI state when the menu is shown)

    def __init__(self, _text=None):
        """Assign a wx Id.

        Parameter _text underscored cause its use should be avoided - prefer to
        specify text as a class attribute (or set in it _initData()).
        """
        super(Link, self).__init__()
        self._id = wx.NewId() # register wx callbacks in AppendToMenu overrides
        self.text = _text or self.__class__.text # menu label

    def _initData(self, window, selection):
        """Initialize the Link instance data based on UI state when the
        menu is Popped up.

        Called from AppendToMenu - DO NOT call directly. If you need to use the
        initialized data in setting instance attributes (such as text) override
        and always _call super_ when overriding.
        :param window: the element the menu is being popped from (usually a
        UIList subclass)
        :param selection: the selected items when the menu is appended or None.
        In modlist/installers it's a list<Path> while in subpackage it's the
        index of the right-clicked item. In main (column header) menus it's
        the column clicked on or the first column. Set in Links.PopupMenu().
        :type window: UIList | wx.Panel | wx.Button | basher.BashStatusbar
        :type selection: list[Path | unicode | int] | int
        """
        self.window = window
        self.selected = selection

    def AppendToMenu(self, menu, window, selection):
        """Creates a wx menu item and appends it to :menu.

        Link implementation calls _initData and returns None.
        """
        self._initData(window, selection)

    # Wrappers around balt dialogs - used to single out non trivial uses of
    # self->window
    ##: avoid respecifying default params
    def _showWarning(self, message, title=_(u'Warning'), **kwdargs):
        return showWarning(self.window, message, title=title, **kwdargs)

    def _askYes(self, message, title=u'', default=True, questionIcon=False):
        if not title: title = self.text
        return askYes(self.window, message, title=title, default=default,
                      questionIcon=questionIcon)

    def _askContinue(self, message, continueKey, title=_(u'Warning')):
        return askContinue(self.window, message, continueKey, title=title)

    def _askOpen(self, title=u'', defaultDir=u'', defaultFile=u'',
                 wildcard=u'', mustExist=False):
        return askOpen(self.window, title=title, defaultDir=defaultDir,
                       defaultFile=defaultFile, wildcard=wildcard,
                       mustExist=mustExist)

    def _askOk(self, message, title=u''):
        if not title: title = self.text
        return askOk(self.window, message, title)

    def _showOk(self, message, title=u'', **kwdargs):
        if not title: title = self.text
        return showOk(self.window, message, title, **kwdargs)

    def _askWarning(self, message, title=_(u'Warning'), **kwdargs):
        return askWarning(self.window, message, title, **kwdargs)

    def _askText(self, message, title=u'', default=u'', strip=True):
        if not title: title = self.text
        return askText(self.window, message, title=title, default=default,
                       strip=strip)

    def _showError(self, message, title=_(u'Error'), **kwdargs):
        return showError(self.window, message, title, **kwdargs)

    def _askSave(self, title=u'', defaultDir=u'', defaultFile=u'',
                 wildcard=u'', style=wx.FD_OVERWRITE_PROMPT):
        return askSave(self.window, title, defaultDir, defaultFile, wildcard,
                       style)

    def _showLog(self, logText, title=u'', asDialog=False, fixedFont=False,
                 icons=None, size=True):
        showLog(self.window, logText, title, asDialog, fixedFont, icons,
                size)

    def _showInfo(self, message, title=_(u'Information'), **kwdargs):
        return showInfo(self.window, message, title, **kwdargs)

    def _showWryeLog(self, logText, title=u'', asDialog=True, icons=None):
        return showWryeLog(self.window, logText, title, asDialog, icons)

    def _askNumber(self, message, prompt=u'', title=u'', value=0, min=0,
                   max=10000):
        return askNumber(self.window, message, prompt, title, value, min, max)

    def _askOpenMulti(self, title=u'', defaultDir=u'', defaultFile=u'',
                      wildcard=u''):
        return askOpenMulti(self.window, title, defaultDir, defaultFile,
                            wildcard)

    def _askDirectory(self, message=_(u'Choose a directory.'),
                      defaultPath=u''):
        return askDirectory(self.window, message, defaultPath)

    def _askContinueShortTerm(self, message, title=_(u'Warning')):
        return askContinueShortTerm(self.window, message, title=title)

# Link subclasses -------------------------------------------------------------
class ItemLink(Link):
    """Create and append a wx menu item.

    Subclasses MUST define text (preferably class) attribute and should
    override help. Registers the Execute() and ShowHelp methods on menu events.
    """
    kind = wx.ITEM_NORMAL  # the default in wx.MenuItem(... kind=...)
    help = None

    def AppendToMenu(self, menu, window, selection):
        """Append self as menu item and set callbacks to be executed when
        selected."""
        super(ItemLink, self).AppendToMenu(menu, window, selection)
        Link.Frame.Bind(wx.EVT_MENU, self.__Execute, id=self._id)
        Link.Frame.Bind(wx.EVT_MENU_HIGHLIGHT_ALL, ItemLink.ShowHelp)
        menuItem = wx.MenuItem(menu, self._id, self.text, self.help or u'',
                               self.__class__.kind)
        menu.AppendItem(menuItem)
        return menuItem

    # Callbacks ---------------------------------------------------------------
    # noinspection PyUnusedLocal
    def __Execute(self, __event):
        """Eat up wx event - code outside balt should not use it."""
        self.Execute()

    def Execute(self):
        """Event: link execution."""
        raise AbstractError

    @staticmethod
    def ShowHelp(event): # <wx._core.MenuEvent>
        """Hover over an item, set the statusbar text"""
        if Link.Popup:
            item = Link.Popup.FindItemById(event.GetId()) # <wx._core.MenuItem>
            Link.Frame.SetStatusInfo(item.GetHelp() if item else u'')

class MenuLink(Link):
    """Defines a submenu. Generally used for submenus of large menus."""
    help = u'UNUSED'

    def __init__(self, name=None, oneDatumOnly=False):
        """Initialize. Submenu items should append themselves to self.links."""
        super(MenuLink, self).__init__()
        self.text = name or self.__class__.text
        self.links = Links()
        self.oneDatumOnly = oneDatumOnly

    def append(self, link): self.links.append(link) ##: MenuLink(Link, Links) !

    def _enable(self): return not self.oneDatumOnly or len(self.selected) == 1

    def AppendToMenu(self, menu, window, selection):
        """Append self as submenu (along with submenu items) to menu."""
        super(MenuLink, self).AppendToMenu(menu, window, selection)
        Link.Frame.Bind(wx.EVT_MENU_OPEN, MenuLink.OnMenuOpen)
        subMenu = wx.Menu()
        menu.AppendMenu(self._id, self.text, subMenu)
        if not self._enable():
            menu.Enable(self._id, False)
        else: # do not append sub links unless submenu enabled
            for link in self.links: link.AppendToMenu(subMenu, window,
                                                      selection)
        return subMenu

    @staticmethod
    def OnMenuOpen(event):
        """Hover over a submenu, clear the status bar text"""
        Link.Frame.SetStatusInfo(u'')

class ChoiceLink(Link):
    """List of Choices with optional menu items to edit etc those choices."""
    extraItems = [] # list<Link>
    choiceLinkType = ItemLink # the class type of the individual choices' links

    @property
    def _choices(self):
        """List of text labels for the individual choices links."""
        return []

    def AppendToMenu(self, menu, window, selection):
        """Append Link items."""
        submenu = super(ChoiceLink, self).AppendToMenu(menu, window, selection)
        if isinstance(submenu, wx.Menu): # we inherit a Menu, append to it
            menu = submenu
        for link in self.extraItems:
            link.AppendToMenu(menu, window, selection)
        for link in (self.choiceLinkType(_text=txt) for txt in self._choices):
            link.AppendToMenu(menu, window, selection)
        # returns None

class TransLink(Link):
    """Transcendental link, can't quite make up its mind."""
    # No state

    def _decide(self, window, selection):
        """Return a Link subclass instance to call AppendToMenu on."""
        raise AbstractError

    def AppendToMenu(self, menu, window, selection):
        return self._decide(window, selection).AppendToMenu(menu, window,
                                                            selection)

class SeparatorLink(Link):
    """Link that acts as a separator item in menus."""

    def AppendToMenu(self, menu, window, selection):
        """Add separator to menu."""
        menu.AppendSeparator()

# Link Mixin ------------------------------------------------------------------
class AppendableLink(Link):
    """A menu item or submenu that may be appended to a Menu or not.

    Mixin to be used with Link subclasses that override Link.AppendToMenu.
    Could use a metaclass in Link and replace AppendToMenu with one that
    returns if _append() == False.
    """

    def _append(self, window):
        """"Override as needed to append or not the menu item."""
        raise AbstractError

    def AppendToMenu(self, menu, window, selection):
        if not self._append(window): return
        return super(AppendableLink, self).AppendToMenu(menu, window,
                                                        selection)

# ItemLink subclasses ---------------------------------------------------------
class EnabledLink(ItemLink):
    """A menu item that may be disabled.

    The item is by default enabled. Override _enable() to disable\enable
    based on some condition. Subclasses MUST define self.text, preferably as
    a class attribute.
    """

    def _enable(self):
        """"Override as needed to enable or disable the menu item (enabled
        by default)."""
        return True

    def AppendToMenu(self, menu, window, selection):
        menuItem = super(EnabledLink, self).AppendToMenu(menu, window,
                                                         selection)
        menuItem.Enable(self._enable())
        return menuItem

class OneItemLink(EnabledLink):
    """Link enabled only when there is one and only one selected item.

    To be used in Link subclasses where self.selected is a list instance.
    """
    ##: maybe edit help to add _(u'. Select one item only')
    def _enable(self): return len(self.selected) == 1

class CheckLink(ItemLink):
    kind = wx.ITEM_CHECK

    def _check(self): raise AbstractError

    def AppendToMenu(self, menu, window, selection):
        menuItem = super(CheckLink, self).AppendToMenu(menu, window, selection)
        menuItem.Check(self._check())
        return menuItem

class RadioLink(CheckLink):
    kind = wx.ITEM_RADIO

class BoolLink(CheckLink):
    """Simple link that just toggles a setting."""
    text, key, help =  u'LINK TEXT', 'link.key', u'' # Override text and key !
    opposite = False

    def _check(self):
        # check if not the same as self.opposite (so usually check if True)
        return _settings[self.key] ^ self.__class__.opposite

    def Execute(self): _settings[self.key] ^= True # toggle

# UIList Links ----------------------------------------------------------------
class UIList_Delete(ItemLink):
    """Delete selected item(s) from UIList."""
    text = _(u'Delete')
    help = _(u'Delete selected item(s)')

    def Execute(self):
        # event is a 'CommandEvent' and I can't check if shift is pressed - duh
        with BusyCursor(): self.window.DeleteItems(items=self.selected)

class UIList_Rename(ItemLink):
    """Rename selected UIList item(s)."""
    text = _(u'Rename...')

    def Execute(self): self.window.Rename(selected=self.selected)

# wx Wrappers -----------------------------------------------------------------
#------------------------------------------------------------------------------
def copyToClipboard(text):
    if wx.TheClipboard.Open():
        wx.TheClipboard.SetData(wx.TextDataObject(text))
        wx.TheClipboard.Close()

def copyListToClipboard(selected):
    if selected and not wx.TheClipboard.IsOpened():
        wx.TheClipboard.Open()
        clipData = wx.FileDataObject()
        for abspath in selected: clipData.AddFile(abspath)
        wx.TheClipboard.SetData(clipData)
        wx.TheClipboard.Close()

def clipboardDropFiles(millis, callable_):
    if wx.TheClipboard.Open():
        if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_FILENAME)):
            obj = wx.FileDataObject()
            wx.TheClipboard.GetData(obj)
            wx.CallLater(millis, callable_, 0, 0, obj.GetFilenames())
        wx.TheClipboard.Close()

def getKeyState(key): return wx.GetKeyState(key)
def getKeyState_Shift(): return wx.GetKeyState(wx.WXK_SHIFT)
def getKeyState_Control(): return wx.GetKeyState(wx.WXK_CONTROL)

wxArrowUp = {wx.WXK_UP, wx.WXK_NUMPAD_UP}
wxArrowDown = {wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN}
wxArrows = wxArrowUp | wxArrowDown
wxReturn = {wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER}
wxDelete = {wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE}

# ListBoxes -------------------------------------------------------------------
class _CheckList_SelectAll(ItemLink):
    """Menu item used in ListBoxes."""
    def __init__(self,select=True):
        super(_CheckList_SelectAll, self).__init__()
        self.select = select
        self.text = _(u'Select All') if select else _(u'Select None')

    def Execute(self):
        for i in xrange(self.window.GetCount()):
            self.window.Check(i,self.select)

class ListBoxes(Dialog):
    """A window with 1 or more lists."""

    def __init__(self, parent, title, message, lists, liststyle='check',
                 style=0, bOk=_(u'OK'), bCancel=_(u'Cancel'), canCancel=True):
        """lists is in this format:
        if liststyle == 'check' or 'list'
        [title,tooltip,item1,item2,itemn],
        [title,tooltip,....],
        elif liststyle == 'tree'
        [title,tooltip,{item1:[subitem1,subitemn],item2:[subitem1,subitemn],itemn:[subitem1,subitemn]}],
        [title,tooltip,....],
        """
        super(ListBoxes, self).__init__(parent, title=title, style=style,
                                        resize=True)
        self.itemMenu = Links()
        self.itemMenu.append(_CheckList_SelectAll())
        self.itemMenu.append(_CheckList_SelectAll(False))
        self.SetIcons(Resources.bashBlue)
        minWidth = self.GetTextExtent(title)[0] * 1.2 + 64
        sizer = wx.FlexGridSizer(len(lists) + 2, 1)
        self.text = StaticText(self, message)
        self.text.Rewrap(minWidth) # otherwise self.text expands to max width
        sizer.AddGrowableRow(0) # needed so text fits - glitch on resize
        sizer.Add(self.text, 0, wx.EXPAND)
        self._ids = {}
        labels = {wx.ID_CANCEL: bCancel, wx.ID_OK: bOk}
        self.SetSize(wxSize(minWidth, -1))
        for i,group in enumerate(lists):
            title = group[0] # also serves as key in self._ids dict
            tip = group[1]
            strings = [u'%s' % x for x in group[2:]] # works for Path & strings
            if len(strings) == 0: continue
            subsizer = hsbSizer(self, title)
            if liststyle == 'check':
                checksCtrl = listBox(self, choices=strings, isSingle=True,
                                     isHScroll=True, kind='checklist')
                checksCtrl.Bind(wx.EVT_KEY_UP,self.OnKeyUp)
                checksCtrl.Bind(wx.EVT_CONTEXT_MENU,self.OnContext)
                # check all - for range and set see wx._controls.CheckListBox
                checksCtrl.SetChecked(set(range(len(strings))))
            elif liststyle == 'list':
                checksCtrl = listBox(self, choices=strings, isHScroll=True)
            else:
                checksCtrl = wx.TreeCtrl(self, size=(150, 200),
                                         style=wx.TR_DEFAULT_STYLE |
                                               wx.TR_FULL_ROW_HIGHLIGHT |
                                               wx.TR_HIDE_ROOT)
                root = checksCtrl.AddRoot(title)
                checksCtrl.Bind(wx.EVT_MOTION, self.OnMotion)
                for item, subitems in group[2].iteritems():
                    child = checksCtrl.AppendItem(root,item.s)
                    for subitem in subitems:
                        checksCtrl.AppendItem(child,subitem.s)
            self._ids[title] = checksCtrl.GetId()
            checksCtrl.SetToolTip(tooltip(tip))
            subsizer.Add(checksCtrl,1,wx.EXPAND|wx.ALL,2)
            sizer.Add(subsizer,0,wx.EXPAND|wx.ALL,5)
            sizer.AddGrowableRow(i + 1)
        okButton = OkButton(self, label=labels[wx.ID_OK], default=True)
        buttonSizer = hSizer(hspacer,
                             (okButton,0,wx.ALIGN_RIGHT),
                             )
        if canCancel:
            buttonSizer.Add(CancelButton(self, label=labels[wx.ID_CANCEL]),0,wx.ALIGN_RIGHT|wx.LEFT,2)
        sizer.Add(buttonSizer, 1, wx.EXPAND | wx.ALL ^ wx.TOP, 5)
        sizer.AddGrowableCol(0)
        sizer.SetSizeHints(self)
        self.SetSizer(sizer)
        #make sure that minimum size is at least the size of title
        if self.GetSize()[0] < minWidth:
            self.SetSize(wxSize(minWidth,-1))
        self.text.Rewrap(self.GetSize().width)
        self.Bind(wx.EVT_SIZE, self.OnSize)

    def OnMotion(self, event): return

    def OnSize(self, event):
        self.text.Rewrap(self.GetSize().width)
        event.Skip()

    def OnKeyUp(self,event):
        """Char events"""
        ##Ctrl-A - check all
        obj = event.GetEventObject()
        if event.CmdDown() and event.GetKeyCode() == ord('A'):
            check = not event.ShiftDown()
            for i in xrange(len(obj.GetStrings())):
                    obj.Check(i,check)
        else:
            event.Skip()

    def OnContext(self,event):
        """Context Menu"""
        self.itemMenu.PopupMenu(event.GetEventObject(), Link.Frame,
                                event.GetEventObject().GetSelections())
        event.Skip()

    def OnClick(self,event):
        id_ = event.GetId()
        if id_ not in (wx.ID_OK,wx.ID_CANCEL):
            self.EndModal(id_)
        else:
            event.Skip()

    def askOkModal(self): return self.ShowModal() != wx.ID_CANCEL

    def getChecked(self, key, items, checked=True):
        """Return a sublist of 'items' containing (un)checked items.

        The control only displays the string names of items, that is why items
        needs to be passed in. If items is empty it will return an empty list.
        :param key: a key for the private _ids dictionary
        :param items: the items that correspond to the _ids[key] checksCtrl
        :param checked: keep checked items if True (default) else unchecked
        :rtype : list
        :return: the items in 'items' for (un)checked checkboxes in _ids[key]
        """
        if not items: return []
        select = []
        checkList = self.FindWindowById(self._ids[key])
        if checkList:
            for i, mod in enumerate(items):
                if checkList.IsChecked(i) ^ (not checked): select.append(mod)
        return select

# Some UAC stuff --------------------------------------------------------------
def ask_uac_restart(message, title, mopy):
    if not canVista:
        return askYes(None, message + u'\n\n' + _(
                u'Start Wrye Bash with Administrator Privileges?'), title)
    admin = _(u'Run with Administrator Privileges')
    readme = readme_url(mopy)
    readme += '#trouble-permissions'
    return vistaDialog(None, message=message,
        buttons=[(True, u'+' + admin), (False, _(u'Run normally')), ],
        title=title, expander=[_(u'How to avoid this message in the future'),
            _(u'Less information'),
            _(u'Use one of the following command line switches:') +
            u'\n\n' + _(u'--no-uac: always run normally') +
            u'\n' + _(u'--uac: always run with Admin Privileges') +
            u'\n\n' + _(u'See the <A href="%(readmePath)s">readme</A> '
                u'for more information.') % {'readmePath': readme}])

def readme_url(mopy, advanced=False):
    readme = mopy.join(u'Docs',
                       u'Wrye Bash Advanced Readme.html' if advanced else
                       u'Wrye Bash General Readme.html')
    if readme.exists():
        readme = u'file:///' + readme.s.replace(u'\\', u'/').replace(u' ',
                                                                     u'%20')
    else:
        # Fallback to Git repository
        readme = u"http://wrye-bash.github.io/docs/Wrye%20Bash" \
                 u"%20General%20Readme.html"
    return readme

class INIListCtrl(wx.ListCtrl):

    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnSelect)
        self.InsertColumn(0, u'')

    def OnSelect(self, event):
        index = event.GetIndex()
        self.SetItemState(index, 0, wx.LIST_STATE_SELECTED)
        iniLine = self._get_selected_line(index)
        if iniLine != -1:
            self._contents.EnsureVisible(iniLine)
            scroll = iniLine - self._contents.GetScrollPos(wx.VERTICAL) - index
            self._contents.ScrollLines(scroll)
        event.Skip()

    def _get_selected_line(self, index): raise AbstractError
