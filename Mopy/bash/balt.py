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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2021 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Weird module that sits in-between basher and gui on the abstraction tree
now. See #190, its code should be refactored and land in basher and/or gui."""

# Imports ---------------------------------------------------------------------
from . import bass # for dirs - try to avoid
from . import bolt
from .bolt import GPath, deprint, readme_url
from .exception import AbstractError, AccessDeniedError, BoltError, \
    CancelError, SkipError, StateError
#--Python
import time
import threading
from functools import partial, wraps
from collections import OrderedDict
#--wx
import wx
import wx.adv
#--gui
from .gui import Button, CancelButton, CheckBox, HBoxedLayout, HLayout, \
    Label, LayoutOptions, OkButton, RIGHT, Stretch, TextArea, TOP, VLayout, \
    web_viewer_available, DialogWindow, WindowFrame, EventResult, ListBox, \
    Font, CheckListBox, UIListCtrl, PanelWin, Colors, DocumentViewer, \
    ImageWrapper, BusyCursor, GlobalMenu, WrappingTextMixin, HorizontalLine, \
    staticBitmap, bell, copy_files_to_clipboard, FileOpenMultiple, FileOpen, \
    FileSave
from .gui.base_components import _AComponent

# Print a notice if wx.html2 is missing
if not web_viewer_available():
    deprint(u'wx.html2.WebView is missing, features utilizing HTML will be '
            u'disabled')

class Resources(object):
    #--Icon Bundles
    bashRed = None
    bashBlue = None

def load_app_icons():
    """Called early in boot, sets up the icon bundles we use as app icons."""
    red_bundle = ImageBundle()
    red_bundle.Add(bass.dirs[u'images'].join(u'bash_32-2.ico'))
    Resources.bashRed = red_bundle.GetIconBundle()
    blue_bundle = ImageBundle()
    blue_bundle.Add(bass.dirs[u'images'].join(u'bash_blue.svg-2.ico'))
    Resources.bashBlue = blue_bundle.GetIconBundle()

# Settings --------------------------------------------------------------------
__unset = bolt.Settings(dictFile=None) # type information
_settings = __unset # must be bound to bosh.settings - smelly, see #174
sizes = {} #--Using applications should override this.

# Colors ----------------------------------------------------------------------
colors = Colors()

# Images ----------------------------------------------------------------------
images = {} #--Singleton for collection of images.

#------------------------------------------------------------------------------
class ImageBundle(object):
    """Wrapper for bundle of images.

    Allows image bundle to be specified before wx.App is initialized.""" # TODO: unneeded?
    def __init__(self):
        self._image_paths = []
        self.iconBundle = None

    def Add(self, img_path):
        self._image_paths.append(img_path)

    def GetIconBundle(self):
        if not self.iconBundle:
            self.iconBundle = wx.IconBundle()
            for img_path in self._image_paths:
                self.iconBundle.AddIcon(
                    img_path.s, ImageWrapper.typesDict[img_path.cext[1:]])
        return self.iconBundle

#------------------------------------------------------------------------------
class ImageList(object):
    """Wrapper for wx.ImageList.

    Allows ImageList to be specified before wx.App is initialized.
    Provides access to ImageList integers through imageList[key]."""
    def __init__(self,width,height):
        self.width = width
        self.height = height
        self.images = []
        self.indices = {}
        self.imageList = None

    def GetImageList(self):
        if not self.imageList:
            indices = self.indices
            imageList = self.imageList = wx.ImageList(self.width,self.height)
            for key,image in self.images:
                indices[key] = imageList.Add(image.GetBitmap())
        return self.imageList

    def get_image(self, key): return self.images[self[key]][1] # YAK !

    def __getitem__(self,key):
        self.GetImageList()
        return self.indices[key]

# Images ----------------------------------------------------------------------
class ColorChecks(ImageList):
    """ColorChecks ImageList. Used by several UIList classes."""
    def __init__(self):
        ImageList.__init__(self, 16, 16)
        for state in (u'on', u'off', u'inc', u'imp'):
            for status in (u'purple', u'blue', u'green', u'orange', u'yellow',
                           u'red'):
                shortKey = status + u'.' + state
                image_key = u'checkbox.' + shortKey
                img = bass.dirs[u'images'].join(
                    f'checkbox_{status}_{state}.png')
                image = images[image_key] = ImageWrapper(img, ImageWrapper.typesDict[u'png'])
                self.images.append((shortKey, image))

    def Get(self,status,on):
        self.GetImageList()
        if on == 3:
            if status <= -20: shortKey = u'purple.imp'
            elif status <= -10: shortKey = u'blue.imp'
            elif status <= 0: shortKey = u'green.imp'
            elif status <=10: shortKey = u'yellow.imp'
            elif status <=20: shortKey = u'orange.imp'
            else: shortKey = u'red.imp'
        elif on == 2:
            if status <= -20: shortKey = u'purple.inc'
            elif status <= -10: shortKey = u'blue.inc'
            elif status <= 0: shortKey = u'green.inc'
            elif status <=10: shortKey = u'yellow.inc'
            elif status <=20: shortKey = u'orange.inc'
            else: shortKey = u'red.inc'
        elif on:
            if status <= -20: shortKey = u'purple.on'
            elif status <= -10: shortKey = u'blue.on'
            elif status <= 0: shortKey = u'green.on'
            elif status <=10: shortKey = u'yellow.on'
            elif status <=20: shortKey = u'orange.on'
            else: shortKey = u'red.on'
        else:
            if status <= -20: shortKey = u'purple.off'
            elif status <= -10: shortKey = u'blue.off'
            elif status == 0: shortKey = u'green.off'
            elif status <=10: shortKey = u'yellow.off'
            elif status <=20: shortKey = u'orange.off'
            else: shortKey = u'red.off'
        return self.indices[shortKey]

# Modal Dialogs ---------------------------------------------------------------
#------------------------------------------------------------------------------
def askDirectory(parent,message=_(u'Choose a directory.'),defaultPath=u''):
    """Shows a modal directory dialog and return the resulting path, or None if canceled."""
    with wx.DirDialog(parent, message, defaultPath.s,
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
    if _settings.get(continueKey): return True
    #--Generate/show dialog
    checkBoxTxt = _(u"Don't show this in the future.")
    result, check = _ContinueDialog.display_dialog(
        _AComponent._resolve(parent), title=title, message=message,
        checkBoxTxt=checkBoxTxt)
    if check:
        _settings[continueKey] = 1
    return result

def askContinueShortTerm(parent, message, title=_(u'Warning')):
    """Shows a modal continue query  Returns True to continue.
    Also provides checkbox "Don't show this for rest of operation."."""
    #--Generate/show dialog
    checkBoxTxt = _(u"Don't show this for the rest of operation.")
    result, check = _ContinueDialog.display_dialog(
        _AComponent._resolve(parent), title=title, message=message,
        checkBoxTxt=checkBoxTxt)
    if result:
        if check:
            return 2
        return True
    return False

class _ContinueDialog(DialogWindow):
    _def_size = _min_size = (360, 150)

    def __init__(self, parent, message, title, checkBoxTxt):
        super(_ContinueDialog, self).__init__(parent, title, sizes_dict=sizes)
        self.gCheckBox = CheckBox(self, checkBoxTxt)
        #--Layout
        VLayout(border=6, spacing=6, item_expand=True, items=[
            (HLayout(spacing=6, items=[
                (staticBitmap(self), LayoutOptions(border=6, v_align=TOP)),
                (Label(self, message), LayoutOptions(expand=True, weight=1))]),
             LayoutOptions(weight=1)),
            Stretch(),
            HorizontalLine(self),
            HLayout(spacing=4, item_expand=True, items=[
                self.gCheckBox, Stretch(), OkButton(self), CancelButton(self),
            ]),
        ]).apply_to(self)

    def show_modal(self):
        #--Get continue key setting and return
        result = super(_ContinueDialog, self).show_modal()
        check = self.gCheckBox.is_checked
        return result, check

    @classmethod
    def display_dialog(cls, *args, **kwargs):
        #--Get continue key setting and return
        if canVista:
            result, check = vistaDialog(*args, **kwargs)
        else:
            return super(_ContinueDialog, cls).display_dialog(*args, **kwargs)
        return result, check

#------------------------------------------------------------------------------
def askText(parent, message, title=u'', default=u'', strip=True):
    """Shows a text entry dialog and returns result or None if canceled."""
    with wx.TextEntryDialog(_AComponent._resolve(parent), message, title,
                            default) as dialog:
        if dialog.ShowModal() != wx.ID_OK: return None
        txt = dialog.GetValue()
        return txt.strip() if strip else txt

#------------------------------------------------------------------------------
def askNumber(parent,message,prompt=u'',title=u'',value=0,min=0,max=10000):
    """Shows a text entry dialog and returns result or None if canceled."""
    with wx.NumberEntryDialog(_AComponent._resolve(parent), message, prompt,
                              title, value, min, max) as dialog:
        if dialog.ShowModal() != wx.ID_OK: return None
        return dialog.GetValue()

# Message Dialogs -------------------------------------------------------------
from .env import TASK_DIALOG_AVAILABLE, TaskDialog, BTN_OK, BTN_CANCEL, \
    BTN_YES, BTN_NO, GOOD_EXITS
canVista = TASK_DIALOG_AVAILABLE

def vistaDialog(parent, message, title, checkBoxTxt=None,
                buttons=None, icon=u'warning', commandLinks=True, footer=u'',
                expander=[], heading=u''):
    """Always guard with canVista == True"""
    buttons = buttons if buttons is not None else (
        (BTN_OK, u'ok'), (BTN_CANCEL, u'cancel'))
    heading = heading if heading is not None else title
    title = title if title is not None else u'Wrye Bash'
    dialog = TaskDialog(title, heading, message,
                        buttons=[x[1] for x in buttons], main_icon=icon,
                        parenthwnd=parent.GetHandle() if parent else None,
                        footer=footer)
    if expander:
        dialog.set_expander(expander,False,not footer)
    if checkBoxTxt:
        if isinstance(checkBoxTxt, bytes):
            raise RuntimeError(u'Do not pass bytes to vistaDialog!')
        elif isinstance(checkBoxTxt, str):
            dialog.set_check_box(checkBoxTxt,False)
        else:
            dialog.set_check_box(checkBoxTxt[0],checkBoxTxt[1])
    button, radio, checkbox = dialog.show(commandLinks)
    for id_, title in buttons:
        if title.startswith(u'+'): title = title[1:]
        if title == button:
            if checkBoxTxt:
                return id_ in GOOD_EXITS, checkbox
            else:
                return id_ in GOOD_EXITS, None
    return False, checkbox

def askStyled(parent, message, title, style, do_center=False):
    """Shows a modal MessageDialog.
    Use ErrorMessage, WarningMessage or InfoMessage."""
    parent = _AComponent._resolve(parent)
    if do_center: style |= wx.CENTER
    if canVista:
        vista_btn = []
        icon = None
        if style & wx.YES_NO:
            yes = u'yes'
            no = u'no'
            if style & wx.YES_DEFAULT:
                yes = u'Yes'
            elif style & wx.NO_DEFAULT:
                no = u'No'
            vista_btn.append((BTN_YES, yes))
            vista_btn.append((BTN_NO, no))
        if style & wx.OK:
            vista_btn.append((BTN_OK, u'ok'))
        if style & wx.CANCEL:
            vista_btn.append((BTN_CANCEL, u'cancel'))
        if style & (wx.ICON_EXCLAMATION|wx.ICON_INFORMATION):
            icon = u'warning'
        if style & wx.ICON_HAND:
            icon = u'error'
        result, _check = vistaDialog(parent, message=message, title=title,
                                     icon=icon, buttons=vista_btn)
    else:
        dialog = wx.MessageDialog(parent,message,title,style) # TODO de-wx!
        result = dialog.ShowModal() in (wx.ID_OK, wx.ID_YES)
        dialog.Destroy()
    return result

def askOk(parent, message, title=u''):
    """Shows a modal error message."""
    return askStyled(parent, message, title, wx.OK | wx.CANCEL)

def askYes(parent, message, title=u'', default=True, questionIcon=False):
    """Shows a modal warning or question message."""
    icon= wx.ICON_QUESTION if questionIcon else wx.ICON_EXCLAMATION
    style = wx.YES_NO|icon|(wx.YES_DEFAULT if default else wx.NO_DEFAULT)
    return askStyled(parent, message, title, style)

def askWarning(parent, message, title=_(u'Warning')):
    """Shows a modal warning message."""
    return askStyled(parent, message, title,
                     wx.OK | wx.CANCEL | wx.ICON_EXCLAMATION)

def showOk(parent, message, title=u''):
    """Shows a modal error message."""
    if isinstance(title, bolt.Path): title = title.s
    return askStyled(parent, message, title, wx.OK)

def showError(parent, message, title=_(u'Error')):
    """Shows a modal error message."""
    if isinstance(title, bolt.Path): title = title.s
    return askStyled(parent, message, title, wx.OK | wx.ICON_HAND)

def showWarning(parent, message, title=_(u'Warning'), do_center=False):
    """Shows a modal warning message."""
    return askStyled(parent, message, title, wx.OK | wx.ICON_EXCLAMATION,
                     do_center=do_center)

def showInfo(parent, message, title=_(u'Information')):
    """Shows a modal information message."""
    return askStyled(parent, message, title, wx.OK | wx.ICON_INFORMATION)

#------------------------------------------------------------------------------
class _Log(object):
    _settings_key = u'balt.LogMessage'
    def __init__(self, parent, title=u'', asDialog=True, log_icons=None):
        self.asDialog = asDialog
        #--Sizing
        key__pos_ = self._settings_key + u'.pos'
        key__size_ = self._settings_key + u'.size'
        if isinstance(title, bolt.Path): title = title.s
        #--DialogWindow or WindowFrame
        if self.asDialog:
            window = DialogWindow(parent, title, sizes_dict=_settings,
                                  icon_bundle=log_icons, size_key=key__size_,
                                  pos_key=key__pos_)
        else:
            style_ = wx.RESIZE_BORDER | wx.CAPTION | wx.SYSTEM_MENU |  \
                     wx.CLOSE_BOX | wx.CLIP_CHILDREN
            window = WindowFrame(parent, title, log_icons or Resources.bashBlue,
                                 _base_key=self._settings_key,
                                 sizes_dict=_settings, style=style_)
        window.set_min_size(200, 200)
        self.window = window

    def ShowLog(self):
        #--Show
        if self.asDialog: self.window.show_modal()
        else: self.window.show_frame()

class Log(_Log):
    def __init__(self, parent, logText, title=u'', asDialog=True,
                 fixedFont=False, log_icons=None):
        """Display text in a log window"""
        super(Log, self).__init__(parent, title, asDialog, log_icons)
        #--Bug workaround to ensure that default colour is being used - if not
        # called we get white borders instead of grey todo PY3: test if needed
        self.window.reset_background_color()
        #--Text
        txtCtrl = TextArea(self.window, init_text=logText, auto_tooltip=False)
                          # special=True) SUNKEN_BORDER and TE_RICH2
        # TODO(nycz): GUI fixed width font
        if fixedFont:
            fixedFont = wx.SystemSettings.GetFont(wx.SYS_ANSI_FIXED_FONT)
            fixedFont.SetPointSize(8)
            fixedStyle = wx.TextAttr()
            #fixedStyle.SetFlags(0x4|0x80)
            fixedStyle.SetFont(fixedFont)
            # txtCtrl.SetStyle(0,txtCtrl.GetLastPosition(),fixedStyle)
        #--Layout
        ok_button = OkButton(self.window)
        ok_button.on_clicked.subscribe(self.window.close_win)
        VLayout(border=2, items=[
            (txtCtrl, LayoutOptions(expand=True, weight=1, border=2)),
            (ok_button, LayoutOptions(h_align=RIGHT, border=2))
        ]).apply_to(self.window)
        self.ShowLog()

#------------------------------------------------------------------------------
class WryeLog(_Log):
    _settings_key = u'balt.WryeLog'
    def __init__(self, parent, logText, title=u'', asDialog=True,
                 log_icons=None):
        """Convert logText from wtxt to html and display. Optionally,
        logText can be path to an html file."""
        if isinstance(logText, bolt.Path):
            logPath = logText
        else:
            logPath = bass.dirs[u'saveBase'].join(u'WryeLogTemp.html')
            css_dir = bass.dirs[u'mopy'].join(u'Docs')
            bolt.convert_wtext_to_html(logPath, logText, css_dir)
        super(WryeLog, self).__init__(parent, title, asDialog, log_icons)
        #--Text
        self._html_ctrl = DocumentViewer(self.window)
        self._html_ctrl.try_load_html(file_path=logPath)
        #--Buttons
        gOkButton = OkButton(self.window)
        gOkButton.on_clicked.subscribe(self.window.close_win)
        if not asDialog:
            self.window.set_background_color(gOkButton.get_background_color())
        #--Layout
        VLayout(border=2, item_expand=True, items=[
            (self._html_ctrl, LayoutOptions(weight=1)),
            (HLayout(items=(self._html_ctrl.get_buttons()
                            + (Stretch(), gOkButton))),
             LayoutOptions(border=2))
        ]).apply_to(self.window)
        self.ShowLog()

def playSound(parent,sound):
    if not sound: return
    sound = wx.adv.Sound(sound)
    if sound.IsOk():
        sound.Play(wx.adv.SOUND_ASYNC)
    else:
        showError(parent,_(u'Invalid sound file %s.') % sound)

# Other Windows ---------------------------------------------------------------
#------------------------------------------------------------------------------
class ListEditorData(object):
    """Data capsule for ListEditor. [Abstract]
    DEPRECATED: nest into ListEditor"""
    def __init__(self,parent):
        self.parent = parent #--Parent window.
        self.showAdd = False
        self.showRename = False
        self.showRemove = False
        self.showSave = False
        self.showCancel = False
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
    def setInfo(self, item, info_text):
        """Sets string info on specified item."""
        raise AbstractError

    #--Save/Cancel
    def save(self):
        """Handles save button."""
        pass

#------------------------------------------------------------------------------
class ListEditor(DialogWindow):
    """Dialog for editing lists."""

    def __init__(self, parent, title, lid_data, orderedDict=None):
        """A gui list, with buttons that act on the list items.

        Added kwargs to provide extra buttons - this class is built around a
        ListEditorData instance which needlessly complicates things - mainly
        a bunch of booleans to enable buttons but also the list of data that
        corresponds to (read is duplicated by) ListEditor._list_items.
        ListEditorData should be nested here.
        :param orderedDict: orderedDict['ButtonLabel']=buttonAction
        """
        #--Data
        self._listEditorData = lid_data #--Should be subclass of ListEditorData
        self._list_items = lid_data.getItemList()
        #--GUI
        super(ListEditor, self).__init__(parent, title, sizes_dict=sizes)
        self._size_key = self._listEditorData.__class__.__name__
        #--List Box
        self.listBox = ListBox(self, choices=self._list_items)
        self.listBox.set_min_size(125, 150)
        #--Infobox
        self.gInfoBox = None # type: TextArea
        if lid_data.showInfo:
            editable = not self._listEditorData.infoReadOnly
            self.gInfoBox = TextArea(self, editable=editable)
            if editable:
                self.gInfoBox.on_text_changed.subscribe(self.OnInfoEdit)
            # TODO(nycz): GUI size=(130, -1), SUNKEN_BORDER
        #--Buttons
        buttonSet = [
            (lid_data.showAdd, _(u'Add'), self.DoAdd),
            (lid_data.showRename, _(u'Rename'), self.DoRename),
            (lid_data.showRemove, _(u'Remove'), self.DoRemove),
            (lid_data.showSave, _(u'Save'), self.DoSave),
            (lid_data.showCancel, _(u'Cancel'), self.DoCancel),
            ]
        for k, v in (orderedDict or {}).items():
            buttonSet.append((True, k, v))
        if sum(bool(x[0]) for x in buttonSet):
            def _btn(btn_label, btn_callback):
                new_button = Button(self, btn_label)
                new_button.on_clicked.subscribe(btn_callback)
                return new_button
            new_buttons = [_btn(defLabel, func) for flag, defLabel, func
                           in buttonSet if flag]
            buttons = VLayout(spacing=4, items=new_buttons)
        else:
            buttons = None
        #--Layout
        layout = VLayout(border=4, spacing=4, items=[
            (HLayout(spacing=4, item_expand=True, items=[
                (self.listBox, LayoutOptions(weight=1)),
                (self.gInfoBox, LayoutOptions(weight=self._listEditorData.infoWeight)),
                buttons
             ]), LayoutOptions(weight=1, expand=True))])
        #--Done
        if self._size_key in sizes:
            layout.apply_to(self)
            self.component_position = sizes[self._size_key]
        else:
            layout.apply_to(self, fit=True)

    def GetSelected(self): return self.listBox.lb_get_next_item(-1)

    #--List Commands
    def DoAdd(self):
        """Adds a new item."""
        newItem = self._listEditorData.add()
        if newItem and newItem not in self._list_items:
            self._list_items = self._listEditorData.getItemList()
            index = self._list_items.index(newItem)
            self.listBox.lb_insert_items([newItem], index)

    def SetItemsTo(self, items):
        if self._listEditorData.setTo(items):
            self._list_items = self._listEditorData.getItemList()
            self.listBox.lb_set_items(self._list_items)

    def DoRename(self):
        """Renames selected item."""
        selections = self.listBox.lb_get_selections()
        if not selections: return bell()
        #--Rename it
        itemDex = selections[0]
        curName = self.listBox.lb_get_str_item_at_index(itemDex)
        #--Dialog
        newName = askText(self, _(u'Rename to:'), _(u'Rename'), curName)
        if not newName or newName == curName:
            return
        elif newName in self._list_items:
            showError(self,_(u'Name must be unique.'))
        elif self._listEditorData.rename(curName,newName):
            self._list_items[itemDex] = newName
            self.listBox.lb_set_label_at_index(itemDex, newName)

    def DoRemove(self):
        """Removes selected item."""
        selections = self.listBox.lb_get_selections()
        if not selections: return bell()
        #--Data
        itemDex = selections[0]
        item = self._list_items[itemDex]
        if not self._listEditorData.remove(item): return
        #--GUI
        del self._list_items[itemDex]
        self.listBox.lb_delete_at_index(itemDex)
        if self.gInfoBox:
            self.gInfoBox.modified = False
            self.gInfoBox.text_content = u''

    #--Show Info
    def OnInfoEdit(self, new_text):
        """Info box text has been edited."""
        selections = self.listBox.lb_get_selections()
        if not selections: return bell()
        item = self._list_items[selections[0]]
        if self.gInfoBox.modified:
            self._listEditorData.setInfo(item, new_text)

    #--Save/Cancel
    def DoSave(self):
        """Handle save button."""
        self._listEditorData.save()
        sizes[self._size_key] = self.component_size
        self.accept_modal()

    def DoCancel(self):
        """Handle cancel button."""
        sizes[self._size_key] = self.component_size
        self.cancel_modal()

#------------------------------------------------------------------------------
##: Is there even a good reason for having this as a mixin? AFAICT, the only
# thing this accomplishes is causing pycharm to spit out tons of warnings
class TabDragMixin(object):
    """Mixin for the wx.Notebook class.  Enables draggable Tabs.
       Events:
         EVT_NB_TAB_DRAGGED: Called after a tab has been dragged
           event.oldIdex = old tab position (of tab that was moved
           event.newIdex = new tab position (of tab that was moved
    """
    # PY3: These slots cause a crash on wx4
    #__slots__ = ('__dragX','__dragging','__justSwapped')

    def __init__(self):
        self.__dragX = 0
        self.__dragging = wx.NOT_FOUND
        self.__justSwapped = wx.NOT_FOUND
        # TODO(inf) Test in wx3
        if wx.Platform != u'__WXGTK__': # CaptureMouse() works badly in wxGTK
            self.Bind(wx.EVT_LEFT_DOWN, self.__OnDragStart)
            self.Bind(wx.EVT_LEFT_UP, self.__OnDragEnd)
            self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.__OnDragEndForced)
            self.Bind(wx.EVT_MOTION, self.__OnDragging)

    def __OnDragStart(self, event):
        if not self.HasCapture(): # or blow up on CaptureMouse()
            pos = event.GetPosition()
            self.__dragging = self.HitTest(pos)
            if self.__dragging != wx.NOT_FOUND:
                self.__dragX = pos[0]
                self.__justSwapped = wx.NOT_FOUND
                self.CaptureMouse()
        event.Skip()

    def __OnDragEndForced(self, _event):
        self.__dragging = wx.NOT_FOUND
        self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

    def __OnDragEnd(self, event):
        if self.__dragging != wx.NOT_FOUND:
            self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
            self.__dragging = wx.NOT_FOUND
            try:
                self.ReleaseMouse()
            except AssertionError:
                # PyAssertionError: C++ assertion "GetCapture() == this"
                # failed at ..\..\src\common\wincmn.cpp(2536) in
                # wxWindowBase::ReleaseMouse(): attempt to release mouse,
                # but this window hasn't captured it
                pass
        event.Skip()

    def __OnDragging(self, event):
        if self.__dragging != wx.NOT_FOUND:
            pos = event.GetPosition()
            if abs(pos[0] - self.__dragX) > 5:
                self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
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
                self.drag_tab(newPos)
        event.Skip()

#------------------------------------------------------------------------------
class Progress(bolt.Progress):
    """Progress as progress dialog."""
    _style = wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_SMOOTH

    def __init__(self, title=_(u'Progress'), message=u' '*60, parent=None,
                 abort=False, elapsed=True, __style=_style):
        if abort: __style |= wx.PD_CAN_ABORT
        if elapsed: __style |= wx.PD_ELAPSED_TIME
        # TODO(inf) de-wx? Or maybe stop using None as parent for Progress?
        parent = _AComponent._resolve(parent) if parent else None
        self.dialog = wx.GenericProgressDialog(title, message, 100, parent,
                                               __style)
        bolt.Progress.__init__(self)
        self.message = message
        self.isDestroyed = False
        self.prevMessage = u''
        self.prevState = -1
        self.prevTime = 0

    # __enter__ and __exit__ for use with the 'with' statement
    def __exit__(self, exc_type, exc_value, exc_traceback): self.Destroy()

    def getParent(self): return self.dialog.GetParent()

    def setCancel(self, enabled=True, new_message=u''):
        # TODO(inf) Hacky, we need to rewrite this class for wx3
        new_title = self.dialog.GetTitle()
        new_parent = self.dialog.GetParent()
        new_style = self.dialog.GetWindowStyle()
        if enabled:
            new_style |= wx.PD_CAN_ABORT
        else:
            new_style &= ~wx.PD_CAN_ABORT
        self.dialog.Destroy()
        self.dialog = wx.GenericProgressDialog(new_title, new_message, 100,
                                               new_parent, new_style)

    def _do_progress(self, state, message):
        if not self.dialog:
            raise StateError(u'Dialog already destroyed.')
        elif (state == 0 or state == 1 or (state - self.prevState) > 0.05 or (
                time.time() - self.prevTime) > 0.5):
            if message != self.prevMessage:
                ret = self.dialog.Update(int(state * 100), u'\n'.join(
                    [self._ellipsize(msg) for msg in message.split(u'\n')]))
            else:
                ret = self.dialog.Update(int(state*100))
            if not ret[0]:
                raise CancelError
            self.prevMessage = message
            self.prevState = state
            self.prevTime = time.time()

    @staticmethod
    def _ellipsize(message):
        """A really ugly way to ellipsize messages that would cause the
        progress dialog to resize itself when displaying them. wx2.8's
        ProgressDialog had this built in, but wx3.0's is native, and doesn't
        have this feature, so we emulate it here. 50 characters was chosen as
        the cutoff point, since that produced a reasonably good-looking
        progress dialog at 1080p during testing.

        :param message: The message to ellipsize.
        :return: The ellipsized message."""
        if len(message) > 50:
            first = message[:24]
            second = message[-26:]
            return first + u'...' + second
        return message

    def Destroy(self):
        if self.dialog:
            # self._do_progress(self.full, _(u'Done'))
            self.dialog.Destroy()
            self.dialog = None

#------------------------------------------------------------------------------
_depth = 0
_lock = threading.Lock() # threading not needed (I just can't omit it)
def conversation(func):
    """Decorator to temporarily unbind RefreshData Link.Frame callback."""
    @wraps(func)
    def _conversation_wrapper(*args, **kwargs):
        global _depth
        try:
            with _lock: _depth += 1 # hack: allow nested conversations
            refresh_bound = Link.Frame.bind_refresh(bind=False)
            return func(*args, **kwargs)
        finally:
            with _lock: # atomic
                _depth -= 1
                if not _depth and refresh_bound:
                    Link.Frame.bind_refresh(bind=True)
    return _conversation_wrapper

class UIList(wx.Panel):
    """Offspring of basher.List and balt.Tank, ate its parents."""
    # optional menus
    column_links = None # A list of all links to show in the column menu
    context_links = None # A list of all links to show in item context menus
    # A dict mapping category names to a Links instance that will be displayed
    # when the corresponding category is clicked on in the global menu. The
    # order in which categories are added will also be the display order.
    global_links = None
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
    _singleCell = False # allow only single selections (no ctrl/shift+click)
    #--Sorting
    nonReversibleCols = {u'Load Order', u'Current Order'}
    _default_sort_col = u'File' # override as needed
    _sort_keys = {} # sort_keys[col] provides the sort key for this col
    _extra_sortings = [] #extra self.methods for fancy sortings - order matters
    # Labels, map the (permanent) order of columns to the label generating code
    labels = OrderedDict()
    #--DnD
    _dndFiles = _dndList = False
    _dndColumns = ()
    _target_ini = False # pass the target_ini settings on PopulateItem
    _copy_paths = False # enable the Ctrl+C shortcut

    def __init__(self, parent, keyPrefix, listData=None, panel=None):
        wx.Panel.__init__(self, _AComponent._resolve(parent), style=wx.WANTS_CHARS)
        self.data_store = listData # never use as local variable name !
        self.panel = panel
        #--Settings key
        self.keyPrefix = keyPrefix
        #--Columns
        self.__class__.persistent_columns = {self._default_sort_col}
        self._colDict = {} # used in setting column sort indicator
        #--gList image collection
        self.__class__.icons = ColorChecks() \
            if self.__class__.icons is self.__icons else self.__class__.icons
        #--gList
        self.__gList = UIListCtrl(self, self.__class__._editLabels,
                                  self.__class__._sunkenBorder,
                                  self.__class__._singleCell, self.dndAllow,
                                  dndFiles=self.__class__._dndFiles,
                                  dndList=self.__class__._dndList,
                                  fnDropFiles=self.OnDropFiles,
                                  fnDropIndexes=self.OnDropIndexes)
        if self.icons:
            # Image List: Column sorting order indicators
            # explorer style ^ == ascending
            checkboxesIL = self.icons.GetImageList()
            self.sm_up = checkboxesIL.Add(images[u'arrow.up'].GetBitmap())
            self.sm_dn = checkboxesIL.Add(images[u'arrow.down'].GetBitmap())
            self.__gList._native_widget.SetImageList(checkboxesIL, wx.IMAGE_LIST_SMALL)
        if self.__class__._editLabels:
            self.__gList.on_edit_label_begin.subscribe(self.OnBeginEditLabel)
            self.__gList.on_edit_label_end.subscribe(self.OnLabelEdited)
        # gList callbacks
        self.__gList.on_lst_col_rclick.subscribe(self.DoColumnMenu)
        self.__gList.on_context_menu.subscribe(self.DoItemMenu)
        self.__gList.on_lst_col_click.subscribe(self.OnColumnClick)
        self.__gList.on_key_up.subscribe(self._handle_key_up)
        self.__gList.on_key_down.subscribe(self._handle_key_down)
        #--Events: Columns
        self.__gList.on_lst_col_end_drag.subscribe(self.OnColumnResize)
        #--Events: Items
        self.__gList.on_mouse_left_dclick.subscribe(self.OnDClick)
        self.__gList.on_item_selected.subscribe(self._handle_select)
        self.__gList.on_mouse_left_down.subscribe(self._handle_left_down)
        #--Mouse movement
        self.mouse_index = None
        self.mouseTexts = {} # dictionary item->mouse text
        self.mouseTextPrev = u''
        self.__gList.on_mouse_motion.subscribe(self._handle_mouse_motion)
        self.__gList.on_mouse_leaving.subscribe(self._handle_mouse_leaving)
        #--Layout
        VLayout(item_expand=True, item_weight=1,
                items=[self.__gList]).apply_to(self)
        # Columns
        self._clean_column_settings()
        self.PopulateColumns()
        #--Items
        self._defaultTextBackground = wx.SystemSettings.GetColour(
            wx.SYS_COLOUR_WINDOW)
        self.PopulateItems()

    # Column properties
    @property
    def allCols(self): return list(self.labels)
    @property
    def colWidths(self): return _settings[self.keyPrefix + u'.colWidths']
    @property
    def colReverse(self):
        """Dictionary column->isReversed."""
        return _settings[self.keyPrefix + u'.colReverse']
    @property
    def cols(self): return _settings[self.keyPrefix + u'.cols']
    @property
    def autoColWidths(self):
        return _settings[u'bash.autoSizeListColumns']
    @autoColWidths.setter
    def autoColWidths(self, val): _settings[u'bash.autoSizeListColumns'] = val
    # the current sort column
    @property
    def sort_column(self):
        return _settings.get(self.keyPrefix + u'.sort', self._default_sort_col)
    @sort_column.setter
    def sort_column(self, val): _settings[self.keyPrefix + u'.sort'] = val

    def _handle_select(self, item_key):
        self._select(item_key)
    def _select(self, item): self.panel.SetDetails(item)

    # properties to encapsulate access to the list control
    @property
    def item_count(self): return self.__gList.lc_item_count()

    #--Items ----------------------------------------------
    def PopulateItem(self, itemDex=-1, item=None, target_ini_setts=None):
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
                itemDex = self.item_count # insert at the end
                insert = True
        else: # no way we're inserting with a None item
            item = self.GetItem(itemDex)
        for colDex, col in enumerate(self.cols):
            labelTxt = self.labels[col](self, item)
            if insert and colDex == 0:
                self.__gList.InsertListCtrlItem(itemDex, labelTxt, item)
            else:
                self.__gList._native_widget.SetItem(itemDex, colDex, labelTxt)
        self.__setUI(item, itemDex, target_ini_setts)

    class _ListItemFormat(object):
        def __init__(self):
            self.icon_key = None
            self.back_key = u'default.bkgd'
            self.text_key = u'default.text'
            self.strong = False
            self.italics = False
            self.underline = False

    def set_item_format(self, item, item_format, target_ini_setts):
        """Populate item_format attributes for text and background colors
        and set icon, font and mouse text. Responsible (applicable if the
        data_store is a FileInfo subclass) for calling getStatus (or
        tweak_status in Inis) to update respective info's status."""
        pass # screens, bsas

    def __setUI(self, fileName, itemDex, target_ini_setts):
        """Set font, status icon, background text etc."""
        gItem = self.__gList._native_widget.GetItem(itemDex)
        df = self._ListItemFormat()
        self.set_item_format(fileName, df, target_ini_setts=target_ini_setts)
        if df.icon_key and self.icons:
            if isinstance(df.icon_key, tuple):
                img = self.icons.Get(*df.icon_key)
            else: img = self.icons[df.icon_key]
            gItem.SetImage(img)
        if df.text_key:
            gItem.SetTextColour(colors[df.text_key].to_rgba_tuple())
        else:
            gItem.SetTextColour(self.__gList._native_widget.GetTextColour())
        if df.back_key:
            gItem.SetBackgroundColour(colors[df.back_key].to_rgba_tuple())
        else: gItem.SetBackgroundColour(self._defaultTextBackground)
        gItem.SetFont(Font.Style(gItem.GetFont(), bold=df.strong,
                                 slant=df.italics, underline=df.underline))
        self.__gList._native_widget.SetItem(gItem)

    def PopulateItems(self):
        """Sort items and populate entire list."""
        self.mouseTexts.clear()
        items = set(self.data_store)
        if self.__class__._target_ini:
            # hack for avoiding the syscall in get_ci_settings
            target_setts = self.data_store.ini.get_ci_settings()
        else:
            target_setts = None
        #--Update existing items.
        index = 0
        while index < self.item_count:
            item = self.GetItem(index)
            if item not in items: self.__gList.RemoveItemAt(index)
            else:
                self.PopulateItem(itemDex=index, target_ini_setts=target_setts)
                items.remove(item)
                index += 1
        #--Add remaining new items
        for item in items:
            self.PopulateItem(item=item, target_ini_setts=target_setts)
        #--Sort
        self.SortItems()
        self.autosizeColumns()

    __all = ()
    def RefreshUI(self, redraw=__all, to_del=__all, detail_item=u'SAME',
                  **kwargs):
        """Populate specified files or ALL files, sort, set status bar count.
        """
        focus_list = kwargs.pop(u'focus_list', True)
        if redraw is to_del is self.__all:
            self.PopulateItems()
        else:  #--Iterable
            for d in to_del:
                self.__gList.RemoveItemAt(self.GetIndex(d))
            for upd in redraw:
                self.PopulateItem(item=upd)
            #--Sort
            self.SortItems()
            self.autosizeColumns()
        self._refresh_details(redraw, detail_item)
        self.panel.SetStatusCount()
        if focus_list: self.Focus()

    def _refresh_details(self, redraw, detail_item):
        if detail_item is None:
            self.panel.ClearDetails()
        elif detail_item != u'SAME':
            self.SelectAndShowItem(detail_item)
        else: # if it was a single item, refresh details for it
            if len(redraw) == 1:
                self.SelectAndShowItem(next(iter(redraw)))
            else:
                self.panel.SetDetails()

    def Focus(self):
        self.__gList.set_focus()

    #--Column Menu
    def DoColumnMenu(self, evt_col):
        """Show column menu."""
        if self.column_links: self.column_links.popup_menu(self, evt_col)
        return EventResult.FINISH

    #--Item Menu
    def DoItemMenu(self):
        """Show item menu."""
        selected = self.GetSelected()
        if not selected:
            self.DoColumnMenu(0)
        elif self.context_links:
            self.context_links.popup_menu(self, selected)
        return EventResult.FINISH

    #--Callbacks --------------------------------------------------------------
    def _handle_mouse_motion(self, wrapped_evt, lb_dex_and_flags):
        """Handle mouse entered item by showing tip or similar."""
        if wrapped_evt.is_moving:
            (itemDex, mouseHitFlag) = lb_dex_and_flags
            if itemDex != self.mouse_index:
                self.mouse_index = itemDex
                if itemDex >= 0:
                    item = self.GetItem(itemDex) # get the item for this index
                    item_txt = self.mouseTexts.get(item, u'')
                    if item_txt != self.mouseTextPrev:
                        Link.Frame.set_status_info(item_txt)
                        self.mouseTextPrev = item_txt
    def _handle_mouse_leaving(self):
        if self.mouse_index is not None:
            self.mouse_index = None
            Link.Frame.set_status_info(u'')

    def _handle_key_up(self, wrapped_evt):
        """Char event: select all items, delete selected items, rename."""
        kcode = wrapped_evt.key_code
        cmd_down = wrapped_evt.is_cmd_down
        if cmd_down and kcode == ord(u'A'): # Ctrl+A
            if wrapped_evt.is_shift_down: # de-select all
                self.ClearSelected(clear_details=True)
            else: # select all
                with self.__gList.on_item_selected.pause_subscription(
                    self._handle_select):
                    # omit below to leave displayed details
                    self.panel.ClearDetails()
                    self.__gList.lc_select_item_at_index(-1) # -1 indicates 'all items'
        elif self.__class__._editLabels and kcode == wx.WXK_F2: self.Rename()
        elif kcode in _wx_delete:
            with BusyCursor(): self.DeleteItems(wrapped_evt=wrapped_evt)
        elif cmd_down and kcode == ord(u'O'): # Ctrl+O
            self.open_data_store()
        # Ctrl+C: Copy file(s) to clipboard
        elif self.__class__._copy_paths and cmd_down and kcode == ord(u'C'):
            copy_files_to_clipboard(
                [x.abs_path.s for x in self.GetSelectedInfos()])

    # Columns callbacks
    def OnColumnClick(self, evt_col):
        """Column header was left clicked on. Sort on that column."""
        self.SortItems(self.cols[evt_col],u'INVERT')

    def OnColumnResize(self, evt_col):
        """Column resized: enforce minimal width and save column size info."""
        colName = self.cols[evt_col]
        width = self.__gList.lc_get_column_width(evt_col)
        if width < self._min_column_width:
            width = self._min_column_width
            self.__gList.lc_set_column_width(evt_col, self._min_column_width)
            # if we do not veto the column will be resized anyway!
            self.__gList._native_widget.resizeLastColumn(0) # resize last column to fill
            self.colWidths[colName] = width
            return EventResult.CANCEL
        self.colWidths[colName] = width

    # gList columns autosize---------------------------------------------------
    def autosizeColumns(self):
        if self.autoColWidths:
            colCount = range(self.__gList.lc_get_columns_count())
            for i in colCount:
                self.__gList.lc_set_column_width(i, -self.autoColWidths)

    #--Events skipped
    def _handle_left_down(self, wrapped_evt, lb_dex_and_flags): pass
    def OnDClick(self, lb_dex_and_flags): pass
    def _handle_key_down(self, wrapped_evt): pass
    #--Edit labels - only registered if _editLabels != False
    def _rename_type(self):
        """Check if the operation is allowed and return the item type of the
        selected labels to be renamed."""
        to_rename = self.GetSelectedInfos()
        return (to_rename and type(to_rename[0])) or None
    def OnBeginEditLabel(self, evt_label, uilist_ctrl):
        """Start renaming: deselect the extension."""
        rename_type = self._rename_type()
        if not rename_type:
            # Nothing selected / rename mixed installer types / last marker
            return EventResult.CANCEL
        uilist_ctrl.ec_set_selection(*rename_type.rename_area_idxs(evt_label))
        uilist_ctrl.ec_set_f2_handler(self._on_f2_handler)
        return EventResult.FINISH  ##: needed?
    def OnLabelEdited(self, is_edit_cancelled, evt_label, evt_index, evt_item):
        # should only be subscribed if _editLabels==True and overridden
        raise AbstractError

    def _on_f2_handler(self, is_f2_down, ec_value, uilist_ctrl):
        """For pressing F2 on the edit box for renaming"""
        if is_f2_down:
            to_rename = self.GetSelectedInfos()
            renaming_type = type(to_rename[0])
            start, stop = uilist_ctrl.ec_get_selection()
            if start == stop: # if start==stop there is no selection
                selection_span = 0, len(ec_value)
            else:
                sel_start, _sel_stop = renaming_type.rename_area_idxs(
                    ec_value, start, stop)
                if (sel_start, _sel_stop) == (start, stop):
                    selection_span = 0, len(ec_value)  # rewind selection
                else:
                    selection_span = sel_start, _sel_stop
            uilist_ctrl.ec_set_selection(*selection_span)
            return EventResult.FINISH

    def try_rename(self, info, newFileName): # Mods/BSAs
        return self._try_rename(info, newFileName)

    # Renaming - note the @conversation, this needs to be atomic with respect
    # to refreshes and ideally atomic short
    @conversation
    def _try_rename(self, info, newFileName):
        try:
            return self.data_store.rename_operation(info, newFileName)
        except (CancelError, OSError):
            deprint(f'Renaming {info} to {newFileName} failed', traceback=True)
            # When using moveTo I would get "WindowsError:[Error 32]The process
            # cannot access ..." -  the code below was reverting the changes.
            # With shellMove I mostly get CancelError so below not needed -
            # except if a save is locked and user presses Skip - so cosaves are
            # renamed! Error handling is still a WIP
            for old, new in info.get_rename_paths(newFileName):
                if old == new: continue
                if new.exists() and not old.exists():
                    # some cosave move failed, restore files
                    new.moveTo(old)
                elif new.exists() and old.exists():
                    # move copies then deletes, so the delete part failed
                    new.remove()  # return None # break
            return None # maybe a msg if really really needed

    def _getItemClicked(self, lb_dex_and_flags, on_icon=False):
        (hitItem, hitFlag) = lb_dex_and_flags
        if hitItem < 0 or (on_icon and hitFlag != wx.LIST_HITTEST_ONITEMICON):
            return None
        return self.GetItem(hitItem)

    #--Item selection ---------------------------------------------------------
    def _get_selected(self, lam=lambda i: i, __next_all=wx.LIST_NEXT_ALL,
                      __state_selected=wx.LIST_STATE_SELECTED):
        listCtrl, selected_list = self.__gList, []
        i = listCtrl._native_widget.GetNextItem(-1, __next_all, __state_selected)
        while i != -1:
            selected_list.append(lam(i))
            i = listCtrl._native_widget.GetNextItem(i, __next_all, __state_selected)
        return selected_list

    def GetSelected(self):
        """Return list of items selected (highlighted) in the interface."""
        return self._get_selected(lam=self.GetItem)

    def GetSelectedIndexes(self):
        """Return list of indexes highlighted in the interface in display
        order."""
        return self._get_selected()

    def GetSelectedInfos(self, selected=None):
        """Return list of infos selected (highlighted) in the interface."""
        return [self.data_store[k] for k in (selected or self.GetSelected())]

    def SelectItem(self, item, deselectOthers=False):
        dex = self.GetIndex(item)
        if deselectOthers: self.ClearSelected()
        else: #we must deselect the item and then reselect for callbacks to run
            self.__gList.lc_select_item_at_index(dex, select=False)
        self.__gList.lc_select_item_at_index(dex)

    def SelectItemsNoCallback(self, items, deselectOthers=False):
        if deselectOthers: self.ClearSelected()
        with self.__gList.on_item_selected.pause_subscription(
            self._handle_select):
            for item in items: self.SelectItem(item)

    def ClearSelected(self, clear_details=False):
        """Unselect all items."""
        self.__gList.lc_select_item_at_index(-1, False) # -1 indicates 'all items'
        if clear_details: self.panel.ClearDetails()

    def SelectLast(self):
        self.__gList.lc_select_item_at_index(self.item_count - 1)

    def DeleteAll(self): self.__gList.DeleteAll()

    def EnsureVisibleItem(self, itm_name, focus=False):
        self.EnsureVisibleIndex(self.GetIndex(itm_name), focus=focus)

    def EnsureVisibleIndex(self, dex, focus=False):
        self.__gList._native_widget.Focus(dex) if focus else self.__gList._native_widget.EnsureVisible(dex)
        self.Focus()

    def SelectAndShowItem(self, item, deselectOthers=False, focus=True):
        self.SelectItem(item, deselectOthers=deselectOthers)
        self.EnsureVisibleItem(item, focus=focus)

    def OpenSelected(self, selected=None):
        """Open selected files with default program."""
        selected = self.GetSelectedInfos(selected)
        num = len(selected)
        if num > UIList.max_items_open and not askContinue(self,
            _(u'Trying to open %(num)s items - are you sure ?') % {u'num': num},
            u'bash.maxItemsOpen.continue'): return
        for sel_inf in selected:
            try:
                sel_inf.abs_path.start()
            except OSError:
                deprint(f'Failed to open {sel_inf.abs_path}', traceback=True)

    #--Sorting ----------------------------------------------------------------
    def SortItems(self, column=None, reverse=u'CURRENT'):
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
        self.__gList.ReorderDisplayed(items)
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
        curColumn = self.sort_column
        column = column or curColumn
        curReverse = self.colReverse.get(column, False)
        if column in self.nonReversibleCols: #--Disallow reverse for load
            reverse = False
        elif reverse == u'INVERT' and column == curColumn:
            reverse = not curReverse
        elif reverse in {u'INVERT',u'CURRENT'}:
            reverse = curReverse
        #--Done
        self.sort_column = column
        self.colReverse[column] = reverse
        return column, reverse, curColumn

    def _SortItems(self, col, reverse=False, items=None, sortSpecial=True):
        """Sort and return items by specified column, possibly in reverse
        order.

        If items are not specified, sort self.data_store keys and return that.
        If sortSpecial is False do not apply extra sortings."""
        def key(k): # if key is None then keep it None else provide self
            k = self._sort_keys[k]
            return bolt.natural_key() if k is None else partial(k, self)
        defaultKey = key(self._default_sort_col)
        defSort = col == self._default_sort_col
        # always apply default sort
        items = sorted(self.data_store if items is None else items,
                       key=defaultKey, reverse=defSort and reverse)
        if not defSort: items.sort(key=key(col), reverse=reverse)
        if sortSpecial:
            for lamda in self._extra_sortings: lamda(self, items)
        return items

    def _setColumnSortIndicator(self, col, oldcol, reverse):
        # set column sort image
        try:
            listCtrl = self.__gList
            try: listCtrl._native_widget.ClearColumnImage(self._colDict[oldcol])
            except KeyError:
                pass # if old column no longer is active this will fail but
                #  not a problem since it doesn't exist anyways.
            listCtrl._native_widget.SetColumnImage(self._colDict[col],
                                    self.sm_dn if reverse else self.sm_up)
        except KeyError: pass

    #--Item/Index Translation -------------------------------------------------
    def GetItem(self,index):
        """Return item (key in self.data_store) for specified list index.
        :rtype: bolt.Path | str | int
        """
        return self.__gList.FindItemAt(index)

    def GetIndex(self,item):
        """Return index for item, raise KeyError if item not present."""
        return self.__gList.FindIndexOf(item)

    #--Populate Columns -------------------------------------------------------
    def _clean_column_settings(self):
        """Removes columns that no longer exist from settings files."""
        valid_columns = set(self.allCols)
        # Clean the widths/reverse dictionaries - extracted into helper method
        def clean_dict(dict_key):
            stored_dict = _settings[self.keyPrefix + dict_key]
            invalid_columns = set(stored_dict) - valid_columns
            for c in invalid_columns:
                del stored_dict[c]
        clean_dict(u'.colWidths')
        clean_dict(u'.colReverse')
        # Clean the list of enabled columns for this UIList
        stored_cols = self.cols
        invalid_columns = set(stored_cols) - valid_columns
        for c in invalid_columns:
            while c in stored_cols:  # Just in case there's duplicates
                stored_cols.remove(c)
        # Finally, reset the sort column to the default if it's invalid now
        if self.sort_column not in valid_columns:
            self.sort_column = self._default_sort_col

    def PopulateColumns(self):
        """Create/name columns in ListCtrl."""
        cols = self.cols # this may have been updated in ColumnsMenu.Execute()
        numCols = len(cols)
        names = {_settings[u'bash.colNames'].get(key) for key in cols}
        self._colDict.clear()
        colDex, listCtrl = 0, self.__gList
        while colDex < numCols: ##: simplify!
            colKey = cols[colDex]
            colName = _settings[u'bash.colNames'].get(colKey, colKey)
            colWidth = self.colWidths.get(colKey, 30)
            if colDex >= listCtrl.lc_get_columns_count(): # Make a new column
                listCtrl.lc_insert_column(colDex, colName)
                listCtrl.lc_set_column_width(colDex, colWidth)
            else: # Update an existing column
                column = listCtrl.lc_get_column(colDex)
                col_text = column.GetText() # Py3: unicode?
                if col_text == colName:
                    # Don't change it, just make sure the width is correct
                    listCtrl.lc_set_column_width(colDex, colWidth)
                elif col_text not in names:
                    # Column that doesn't exist anymore
                    listCtrl.lc_delete_column(colDex)
                    continue # do not increment colDex or update colDict
                else: # New column
                    listCtrl.lc_insert_column(colDex, colName)
                    listCtrl.lc_set_column_width(colDex, colWidth)
            self._colDict[colKey] = colDex
            colDex += 1
        while listCtrl.lc_get_columns_count() > numCols:
            listCtrl.lc_delete_column(numCols)

    #--Drag and Drop-----------------------------------------------------------
    @conversation
    def dndAllow(self, event): # Disallow drag an drop by default
        if event: event.Veto()
        return False

    def OnDropFiles(self, x, y, filenames): raise AbstractError
    def OnDropIndexes(self, indexes, newPos): raise AbstractError

    # gList scroll position----------------------------------------------------
    def SaveScrollPosition(self, isVertical=True):
        _settings[self.keyPrefix + u'.scrollPos'] = self.__gList._native_widget.GetScrollPos(
            wx.VERTICAL if isVertical else wx.HORIZONTAL)

    def SetScrollPosition(self):
        if _settings[u'bash.restore_scroll_positions']:
            self.__gList._native_widget.ScrollLines(
                _settings.get(self.keyPrefix + u'.scrollPos', 0))

    # Data commands (WIP)------------------------------------------------------
    def Rename(self, selected=None):
        if not selected: selected = self.GetSelected()
        if selected:
            index = self.GetIndex(selected[0])
            if index != -1:
                self.__gList._native_widget.EditLabel(index)

    @conversation
    def DeleteItems(self, wrapped_evt=None, items=None,
                    dialogTitle=_(u'Delete Items'), order=True):
        recycle = (self.__class__._recycle and
        # menu items fire 'CommandEvent' - I need a workaround to detect Shift
            (True if wrapped_evt is None else not wrapped_evt.is_shift_down))
        items = self._toDelete(items)
        if not self.__class__._shellUI:
            items = self._promptDelete(items, dialogTitle, order, recycle)
        if not items: return
        if not self.__class__._shellUI: # non shellUI path used to delete as
            # many as possible, mainly to show an error on trying to delete
            # the master esm - I kept this behavior
            for i in items:
                try:
                    self.data_store.delete([i], doRefresh=False,
                                           recycle=recycle)
                except BoltError as e: showError(self, f'{e}')
                except (AccessDeniedError, CancelError, SkipError): pass
            else:
                self.data_store.delete_refresh(items, None,
                                               check_existence=True)
        else: # shellUI path tries to delete all at once
            try:
                self.data_store.delete(items, confirm=True, recycle=recycle)
            except (AccessDeniedError, CancelError, SkipError): pass
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
            if not dialog.show_modal(): return []
            return dialog.getChecked(message[0], items)

    def open_data_store(self):
        try:
            self.data_store.store_dir.start()
            return
        except OSError:
            deprint(f'Creating {self.data_store.store_dir}')
            self.data_store.store_dir.makedirs()
        self.data_store.store_dir.start()

    def hide(self, items):
        deletd = []
        for ci_key_, inf in items:
            destDir = inf.get_hide_dir()
            if destDir.join(ci_key_).exists():
                message = (_(u'A file named %s already exists in the hidden '
                             u'files directory. Overwrite it?') % ci_key_)
                if not askYes(self, message, _(u'Hide Files')): continue
            #--Do it
            with BusyCursor():
                self.data_store.move_info(ci_key_, destDir)
                deletd.append(ci_key_)
        #--Refresh stuff
        self.data_store.delete_refresh(deletd, None, check_existence=True)

    @staticmethod
    def _unhide_wildcard(): raise AbstractError
    def unhide(self):
        srcDir = self.data_store.hidden_dir
        wildcard = self._unhide_wildcard()
        destDir = self.data_store.store_dir
        srcPaths = FileOpenMultiple.display_dialog(self, _(u'Unhide files:'),
            defaultDir=srcDir, wildcard=wildcard)
        return destDir, srcDir, srcPaths

    # Global Menu -------------------------------------------------------------
    def populate_category(self, cat_label, target_category):
        for cat_link in self.global_links[cat_label]:
            cat_link.AppendToMenu(target_category, self, 0)

    def setup_global_menu(self):
        """Changes the categories displayed by the global menu to the ones for
        this tab."""
        glb_menu = Link.Frame.global_menu
        if not self.global_links:
            # If we don't have a global link menu, reset and abort
            glb_menu.set_categories([])
            return
        tab_categories = list(self.global_links)
        # Check if we have to change category names
        if not glb_menu.categories_equal(tab_categories):
            # Release and recreate the global menu to avoid GUI flicker
            glb_menu.release_bindings()
            glb_menu = GlobalMenu()
            glb_menu.set_categories(tab_categories)
            Link.Frame.set_global_menu(glb_menu)
        for curr_cat in tab_categories:
            Link.Frame.global_menu.register_category_handler(curr_cat, partial(
                self.populate_category, curr_cat))

# Links -----------------------------------------------------------------------
#------------------------------------------------------------------------------
class Links(list):
    """List of menu or button links."""
    def popup_menu(self, parent, selection):
        """Pops up a new menu from these links."""
        parent = parent or Link.Frame
        to_popup = wx.Menu() # TODO(inf) de-wx!
        for link in self:
            link.AppendToMenu(to_popup, parent, selection)
        Link.Popup = to_popup
        Link.Frame.show_popup_menu(to_popup)
        to_popup.Destroy()
        Link.Popup = None # do not leak the menu reference

#------------------------------------------------------------------------------
class Link(object):
    """Link is a command to be encapsulated in a graphic element (menu item,
    button, etc.).

    Subclasses MUST define a _text attribute (the menu label) preferably as a
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
      singleton. Use (sparingly) as the 'link' between menus and data layer."""
    # BashFrame singleton, set once and for all in BashFrame()
    Frame = None
    # Current popup menu, set in Links.popup_menu()
    Popup = None
    # Menu label (may depend on UI state when the menu is shown)
    _text = u''

    def __init__(self, _text=None): ##: is the _text param even used anymore?
        """Initialize a Link instance.

        Parameter _text underscored cause its use should be avoided - prefer to
        specify text as a class attribute (or set in it _initData())."""
        super(Link, self).__init__()
        self._text = _text or self.__class__._text # menu label

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
        the column clicked on or the first column. Set in Links.popup_menu().
        :type window: UIList | wx.Panel | gui.buttons.Button | DnDStatusBar |
            gui.misc_components.CheckListBox
        :type selection: list[Path | str | int] | int | None
        """
        self.window = window
        self.selected = selection

    def AppendToMenu(self, menu, window, selection):
        """Creates a wx menu item and appends it to :menu.

        Link implementation calls _initData and returns None.
        """
        self._initData(window, selection)

    def iselected_infos(self):
        return (self.window.data_store[x] for x in self.selected)

    def iselected_pairs(self):
        return ((x, self.window.data_store[x]) for x in self.selected)

    def _first_selected(self):
        """Return the first selected info."""
        return next(self.iselected_infos())

    # Wrappers around balt dialogs - used to single out non trivial uses of
    # self->window
    ##: avoid respecifying default params
    def _showWarning(self, message, title=_(u'Warning'), **kwdargs):
        return showWarning(self.window, message, title=title)

    def _askYes(self, message, title=u'', default=True, questionIcon=False):
        if not title: title = self._text
        return askYes(self.window, message, title=title, default=default,
                      questionIcon=questionIcon)

    def _askContinue(self, message, continueKey, title=_(u'Warning')):
        return askContinue(self.window, message, continueKey, title=title)

    def _askOpen(self, title=u'', defaultDir=u'', defaultFile=u'',
                 wildcard=u''):
        return FileOpen.display_dialog(self.window, title=title,
            defaultDir=defaultDir, defaultFile=defaultFile, wildcard=wildcard)

    def _showOk(self, message, title=u''):
        if not title: title = self._text
        return showOk(self.window, message, title)

    def _askWarning(self, message, title=_(u'Warning')):
        return askWarning(self.window, message, title)

    def _askText(self, message, title=u'', default=u'', strip=True):
        if not title: title = self._text
        return askText(self.window, message, title=title, default=default,
                       strip=strip)

    def _showError(self, message, title=_(u'Error')):
        return showError(self.window, message, title)

    def _askSave(self, title=u'', defaultDir=u'', defaultFile=u'',
                 wildcard=u''):
        return FileSave.display_dialog(self.window, title, defaultDir,
                                       defaultFile, wildcard)

    _default_icons = object()
    def _showLog(self, logText, title=u'', asDialog=False, fixedFont=False,
                 icons=_default_icons):
        if icons is self._default_icons: icons = Resources.bashBlue
        Log(self.window, logText, title, asDialog, fixedFont, log_icons=icons)

    def _showInfo(self, message, title=_(u'Information')):
        return showInfo(self.window, message, title)

    def _showWryeLog(self, logText, title=u'', asDialog=True,
                     icons=_default_icons):
        if icons is self._default_icons: icons = Resources.bashBlue
        if not title: title = self._text
        WryeLog(self.window, logText, title, asDialog, log_icons=icons)

    def _askNumber(self, message, prompt=u'', title=u'', value=0, min=0,
                   max=10000):
        return askNumber(self.window, message, prompt, title, value, min, max)

    def _askDirectory(self, message=_(u'Choose a directory.'),
                      defaultPath=u''):
        return askDirectory(self.window, message, defaultPath)

    def _askContinueShortTerm(self, message, title=_(u'Warning')):
        return askContinueShortTerm(self.window, message, title=title)

# Link subclasses -------------------------------------------------------------
class ItemLink(Link):
    """Create and append a wx menu item.

    Subclasses MUST define _text (preferably class) attribute and should
    override _help. Registers the Execute() and ShowHelp methods on menu events
    """
    kind = wx.ITEM_NORMAL # The default in wx.MenuItem(... kind=...)
    _help = u''           # The tooltip to show at the bottom of the GUI

    @property
    def link_text(self):
        """Returns the string that will be used as the display name for this
        link.

        Override this if you need to change the link name dynamically, similar
        to link_help below."""
        return self._text

    @property
    def link_help(self):
        """Returns a string that will be shown as static text at the bottom
        of the GUI.

        Override this if you need to change the help text dynamically
        depending on certain conditions (e.g. whether or not the link is
        enabled)."""
        return self._help

    def AppendToMenu(self, menu, window, selection):
        """Append self as menu item and set callbacks to be executed when
        selected."""
        super(ItemLink, self).AppendToMenu(menu, window, selection)
        # Note default id here is *not* ID_ANY but the special ID_SEPARATOR!
        menuItem = wx.MenuItem(menu, wx.ID_ANY, self.link_text, self.link_help,
                               self.__class__.kind)
        Link.Frame._native_widget.Bind(wx.EVT_MENU, self.__Execute, id=menuItem.GetId())
        Link.Frame._native_widget.Bind(wx.EVT_MENU_HIGHLIGHT_ALL, ItemLink.ShowHelp)
        menu.Append(menuItem)
        return menuItem

    # Callbacks ---------------------------------------------------------------
    # noinspection PyUnusedLocal
    def __Execute(self, __event):
        """Eat up wx event - code outside balt should not use it."""
        self.Execute()

    def Execute(self):
        """Event: link execution."""
        raise AbstractError(u'Execute not implemented')

    @staticmethod
    def ShowHelp(event): # <wx._core.MenuEvent>
        """Hover over an item, set the statusbar text"""
        if Link.Popup:
            item = Link.Popup.FindItemById(event.GetId()) # <wx._core.MenuItem>
            Link.Frame.set_status_info(item.GetHelp() if item else u'')

class MenuLink(Link):
    """Defines a submenu. Generally used for submenus of large menus."""

    def __init__(self, menu_name=None, oneDatumOnly=False):
        """Initialize. Submenu items should append themselves to self.links."""
        super(MenuLink, self).__init__()
        self._text = menu_name or self.__class__._text
        self.links = Links()
        self.oneDatumOnly = oneDatumOnly

    def append(self, link): self.links.append(link) ##: MenuLink(Link, Links) !

    def _enable(self): return not self.oneDatumOnly or len(self.selected) == 1

    def AppendToMenu(self, menu, window, selection):
        """Append self as submenu (along with submenu items) to menu."""
        super(MenuLink, self).AppendToMenu(menu, window, selection)
        subMenu = wx.Menu()
        appended_menu = menu.AppendSubMenu(subMenu, self._text)
        if not self._enable():
            appended_menu.Enable(False)
        else: # If we know we're not enabled, we can skip adding child links
            for link in self.links:
                link.AppendToMenu(subMenu, window, selection)
            appended_menu.Enable(self._enable_menu())
        return subMenu

    def _enable_menu(self):
        """Disable ourselves if none of our children are visible."""
        ##: These hasattr calls are really ugly, try to find a better way
        for l in self.links:
            if isinstance(l, AppendableLink):
                # This is an AppendableLink, skip if it's not appended
                if not l._append(self.window): continue
            if isinstance(l, MenuLink): # not elif!
                # MenuLinks have an _enable method too, avoid calling that
                if l._enable_menu(): return True
            elif isinstance(l, EnabledLink):
                # This is an EnabledLink, check if it's enabled
                if l._enable(): return True
            else:
                # This is some other type of link that's always enabled
                return True
        return False

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
        # After every 30 added items, add a break in the menu to avoid having
        # to use the annoying wx scrolling feature (mostly affects the Bash
        # Tags menu, since there are so many tags)
        i = 1 + len([x for x in self.extraItems
                     if not isinstance(x, SeparatorLink)])
        for link in (self.choiceLinkType(_text=txt) for txt in self._choices):
            if i % 30 == 0:
                menu.Break()
            link.AppendToMenu(menu, window, selection)
            i += 1
        # returns None

class ChoiceMenuLink(ChoiceLink, MenuLink):
    """Combination of ChoiceLink and MenuLink. Turns off the 'disable if no
    children are enabled' behavior of MenuLink since ChoiceLinks do not have
    a static number of children."""
    def _enable_menu(self):
        return True

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

class MultiLink(Link):
    """A link that resolves to several links when appended."""
    def _links(self):
        """Returns the list of links that this link resolves to."""
        raise AbstractError(u'_links not implemented')

    def AppendToMenu(self, menu, window, selection):
        last_ret = None
        for m_link in self._links():
            last_ret = m_link.AppendToMenu(menu, window, selection)
        return last_ret

# ItemLink subclasses ---------------------------------------------------------
class EnabledLink(ItemLink):
    """A menu item that may be disabled.

    The item is by default enabled. Override _enable() to disable/enable
    based on some condition. Subclasses MUST define self.text, preferably as
    a class attribute.
    """

    def _enable(self):
        """Override as needed to enable or disable the menu item (enabled
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
    ##: maybe edit _help to add _(u'. Select one item only')
    def _enable(self): return len(self.selected) == 1

    @property
    def _selected_item(self): return self.selected[0]
    @property
    def _selected_info(self): return self._first_selected()

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
    _text, _bl_key, _help = u'LINK TEXT', u'link.key', u'' # Override!
    opposite = False

    def _check(self):
        # check if not the same as self.opposite (so usually check if True)
        return _settings[self._bl_key] ^ self.__class__.opposite

    def Execute(self): _settings[self._bl_key] ^= True # toggle

# UIList Links ----------------------------------------------------------------
class UIList_Delete(ItemLink):
    """Delete selected item(s) from UIList."""
    _text = _(u'Delete')
    _help = _(u'Delete selected item(s)')

    def Execute(self):
        # event is a 'CommandEvent' and I can't check if shift is pressed - duh
        with BusyCursor(): self.window.DeleteItems(items=self.selected)

class UIList_Rename(ItemLink):
    """Rename selected UIList item(s)."""
    _text = _(u'Rename...')

    def Execute(self): self.window.Rename(selected=self.selected)

class UIList_OpenItems(ItemLink):
    """Open specified file(s)."""
    _text = _(u'Open...')

    @property
    def link_help(self):
        return _(u"Open '%s' with the system's default program.") % \
               self.selected[0] if len(self.selected) == 1 else _(
            u'Open the selected files.')

    def Execute(self): self.window.OpenSelected(selected=self.selected)

class UIList_OpenStore(ItemLink):
    """Opens data directory in explorer."""
    _text = _(u'Open Folder...')

    @property
    def link_help(self):
        return _(u"Open '%s'") % self.window.data_store.store_dir

    def Execute(self): self.window.open_data_store()

class UIList_Hide(ItemLink):
    """Hide the file (move it to the data store's Hidden directory)."""
    _text = _(u'Hide...')
    _help = _(u"Hide the selected file(s) by moving them to the 'Hidden' "
              u'directory.')

    @conversation
    def Execute(self):
        if not bass.inisettings[u'SkipHideConfirmation']:
            message = _(u'Hide these files? Note that hidden files are simply '
                        u'moved to the %(hdir)s directory.') % (
                          {u'hdir': self.window.data_store.hidden_dir})
            if not self._askYes(message, _(u'Hide Files')): return
        self.window.hide(self.iselected_pairs())
        self.window.RefreshUI(refreshSaves=True)

# wx Wrappers -----------------------------------------------------------------
#------------------------------------------------------------------------------
_wx_arrow_up = {wx.WXK_UP, wx.WXK_NUMPAD_UP}
wxArrowDown = {wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN}
wxArrows = _wx_arrow_up | wxArrowDown
wxReturn = {wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER}
_wx_delete = {wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE}

# ListBoxes -------------------------------------------------------------------
class _CheckList_SelectAll(ItemLink):
    """Menu item used in ListBoxes."""
    def __init__(self,select=True):
        super(_CheckList_SelectAll, self).__init__()
        self.select = select
        self._text = _(u'Select All') if select else _(u'Select None')

    def Execute(self):
        self.window.set_all_checkmarks(checked=self.select)

# TODO(inf) Needs renaming, also need to make a virtual version eventually...
class TreeCtrl(_AComponent):
    _wx_widget_type = wx.TreeCtrl

    def __init__(self, parent, title, items_dict):
        super(TreeCtrl, self).__init__(parent, size=(150, 200),
            style=wx.TR_DEFAULT_STYLE | wx.TR_FULL_ROW_HIGHLIGHT |
                  wx.TR_HIDE_ROOT)
        root = self._native_widget.AddRoot(title)
        self._native_widget.Bind(wx.EVT_MOTION, self.OnMotion)
        for item, subitems in items_dict.items():
            child = self._native_widget.AppendItem(root, item.s)
            for subitem in subitems:
                self._native_widget.AppendItem(child, subitem.s)
            self._native_widget.Expand(child)

    def OnMotion(self, event): return

class ListBoxes(WrappingTextMixin, DialogWindow):
    """A window with 1 or more lists."""
    _wrapping_offset = 64

    def __init__(self, parent, title, message, lists, liststyle=u'check',
                 style=0, bOk=_(u'OK'), bCancel=_(u'Cancel'), canCancel=True):
        """lists is in this format:
        if liststyle == u'check' or u'list'
        [title,tooltip,item1,item2,itemn],
        [title,tooltip,....],
        elif liststyle == u'tree'
        [title,tooltip,{item1:[subitem1,subitemn],item2:[subitem1,subitemn],itemn:[subitem1,subitemn]}],
        [title,tooltip,....],
        """
        super(ListBoxes, self).__init__(message, parent, title=title,
                                        icon_bundle=Resources.bashBlue,
                                        sizes_dict=sizes, style=style)
        self.itemMenu = Links()
        self.itemMenu.append(_CheckList_SelectAll())
        self.itemMenu.append(_CheckList_SelectAll(False))
        # TODO(inf) de-wx!
        minWidth = self._native_widget.ToDIP(
            self._native_widget.GetTextExtent(title)).width * 1.2 + 64
        self._panel_text.wrap(minWidth) # otherwise expands to max width
        layout = VLayout(border=5, spacing=5, items=[self._panel_text])
        self._ctrls = {}
        # Size ourselves slightly larger than the wrapped text, otherwise some
        # of it may be cut off and the buttons may become too small to read
        # TODO(ut) we should set ourselves to min(minWidth, size(btns)) - how?
        self.component_size = (minWidth + 64, -1)
        min_height = 128 + 128 * len(lists) #arbitrary just fits well currently
        if self.component_size[1] < min_height:
            self.component_size = (minWidth + 64, min_height)
        self.set_min_size(minWidth + 64, min_height)
        for item_group in lists:
            title = item_group[0] # also serves as key in self._ctrls dict
            item_tip = item_group[1]
            strings = [u'%s' % x for x in item_group[2:]] # works for Path & strings
            if not strings: continue
            if liststyle == u'check':
                checksCtrl = CheckListBox(self, choices=strings, isSingle=True,
                                          isHScroll=True)
                checksCtrl.on_context.subscribe(self._on_context)
                checksCtrl.set_all_checkmarks(checked=True)
            elif liststyle == u'list':
                checksCtrl = ListBox(self, choices=strings, isHScroll=True)
            else: # u'tree'
                checksCtrl = TreeCtrl(self, title, item_group[2])
            self._ctrls[title] = checksCtrl
            checksCtrl.tooltip = item_tip
            layout.add((HBoxedLayout(self, item_expand=True, title=title,
                                     item_weight=1, items=[checksCtrl]),
                        LayoutOptions(expand=True, weight=1)))
        btns = [OkButton(self, btn_label=bOk),
                CancelButton(self, btn_label=bCancel) if canCancel else None]
        layout.add((HLayout(spacing=5, items=btns),
                    LayoutOptions(h_align=RIGHT)))
        layout.apply_to(self)

    def _on_context(self, lb_instance):
        """Context Menu"""
        self.itemMenu.popup_menu(lb_instance, lb_instance.lb_get_selections())

    def getChecked(self, key, items, checked=True):
        """Return a sublist of 'items' containing (un)checked items.

        The control only displays the string names of items, that is why items
        needs to be passed in. If items is empty it will return an empty list.
        :param key: a key for the private _ctrls dictionary
        :param items: the items that correspond to the _ctrls[key] checksCtrl
        :param checked: keep checked items if True (default) else unchecked
        :rtype : list
        :return: the items in 'items' for (un)checked checkboxes in _ctrls[key]
        """
        if not items: return []
        select = []
        checkList = self._ctrls[key]
        if checkList:
            for i, mod in enumerate(items):
                if checkList.lb_is_checked_at_index(i) ^ (not checked):
                    select.append(mod)
        return select

# Some UAC stuff --------------------------------------------------------------
def ask_uac_restart(message, title, mopy):
    if not canVista:
        return askYes(None, message + u'\n\n' + _(
            u'Start Wrye Bash with Administrator Privileges?'), title)
    admin = _(u'Run with Administrator Privileges')
    readme = readme_url(mopy) + u'#trouble-permissions'
    return vistaDialog(None, message=message,
        buttons=[(BTN_YES, u'+' + admin), (BTN_NO, _(u'Run normally'))],
        title=title, expander=[_(u'How to avoid this message in the future'),
            _(u'Less information'),
            _(u'Use one of the following command line switches:') +
            u'\n\n' + _(u'--no-uac: always run normally') +
            u'\n' + _(u'--uac: always run with Admin Privileges') +
            u'\n\n' + _(u'See the <A href="%(readmePath)s">readme</A> '
                u'for more information.') % {u'readmePath': readme}])[0]

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

    def fit_column_to_header(self, column):
        self.SetColumnWidth(column, wx.LIST_AUTOSIZE_USEHEADER)

    def _get_selected_line(self, index): raise AbstractError

# Status bar ------------------------------------------------------------------
# TODO(inf) de_wx! Wrap wx.StatusBar
# It's currently full of _native_widget hacks to keep it functional, this one
# is the next big step
class DnDStatusBar(wx.StatusBar):
    buttons = Links()

    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent)
        self.SetFieldsCount(3)
        self.UpdateIconSizes()
        #--Bind events
        self.Bind(wx.EVT_SIZE, self.OnSize)
        #--Setup Drag-n-Drop reordering
        self.dragging = wx.NOT_FOUND
        self.dragStart = 0
        self.moved = False

    def UpdateIconSizes(self, skip_refresh=False): raise AbstractError
    def GetLink(self,uid=None,index=None,button=None): raise AbstractError

    @property
    def iconsSize(self): # +8 as each button has 4 px border on left and right
        return _settings[u'bash.statusbar.iconSize'] + 8

    def _addButton(self, link):
        gButton = link.GetBitmapButton(self)
        if gButton:
            self.buttons.append(gButton)
            # TODO(inf) Test in wx3
            # DnD events (only on windows, CaptureMouse works badly in wxGTK)
            if wx.Platform != u'__WXGTK__':
                gButton._native_widget.Bind(wx.EVT_LEFT_DOWN, self.OnDragStart)
                gButton._native_widget.Bind(wx.EVT_LEFT_UP, self.OnDragEnd)
                gButton._native_widget.Bind(wx.EVT_MOUSE_CAPTURE_LOST,
                                            self.OnDragEndForced)
                gButton._native_widget.Bind(wx.EVT_MOTION, self.OnDrag)

    def _getButtonIndex(self, mouseEvent):
        id_ = mouseEvent.GetId()
        for i, button in enumerate(self.buttons):
            if button.wx_id_() == id_:
                x = mouseEvent.GetPosition()[0]
                # position is 0 at the beginning of the button's _icon_
                # negative beyond that (on the left) and positive after
                if x < -4:
                    return max(i - 1, 0)
                elif x > self.iconsSize - 4:
                    return min(i + 1, len(self.buttons) - 1)
                return i
        return wx.NOT_FOUND

    def OnDragStart(self, event):
        self.dragging = self._getButtonIndex(event)
        if self.dragging != wx.NOT_FOUND:
            button = self.buttons[self.dragging]
            if not button._native_widget.HasCapture():
                self.dragStart = event.GetPosition()[0]
                button._native_widget.CaptureMouse()
                # Otherwise blows up on py3
                button._native_widget.Bind(wx.EVT_MOUSE_CAPTURE_LOST,
                                           lambda e: None)
        event.Skip()

    def OnDragEndForced(self, event):
        if self.dragging == wx.NOT_FOUND or not self.GetParent().IsActive():
            # The even for clicking the button sends a force capture loss
            # message.  Ignore lost capture messages if we're the active
            # window.  If we're not, that means something else forced the
            # loss of mouse capture.
            self.dragging = wx.NOT_FOUND
            self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        event.Skip()

    def OnDragEnd(self, event):
        if self.dragging != wx.NOT_FOUND:
            try:
                if self.moved:
                    for button in self.buttons:
                        if button._native_widget.HasCapture():
                            button._native_widget.ReleaseMouse()
                            break
            except:
                # deprint(u'Exception while handling mouse up on button',
                #         traceback=True)
                pass
            self.dragging = wx.NOT_FOUND
            self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
            if self.moved:
                self.moved = False
                return
        event.Skip()

    def OnDrag(self, event):
        if self.dragging != wx.NOT_FOUND:
            if abs(event.GetPosition()[0] - self.dragStart) > 4:
                self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
            over = self._getButtonIndex(event)
            if over not in (wx.NOT_FOUND, self.dragging):
                self.moved = True
                button = self.buttons[self.dragging]
                # update settings
                uid = self.GetLink(button=button).uid
                overUid = self.GetLink(index=over).uid
                overIndex = _settings[u'bash.statusbar.order'].index(overUid)
                _settings[u'bash.statusbar.order'].remove(uid)
                _settings[u'bash.statusbar.order'].insert(overIndex, uid)
                # update self.buttons
                self.buttons.remove(button)
                self.buttons.insert(over, button)
                self.dragging = over
                # Refresh button positions
                self.OnSize()
        event.Skip()

    def OnSize(self, event=None):
        rect = self.GetFieldRect(0)
        xPos, yPos = rect.x + 4, rect.y
        for button in self.buttons:
            button.component_position = (xPos, yPos)
            xPos += self.iconsSize
        if event: event.Skip()

#------------------------------------------------------------------------------
class NotebookPanel(PanelWin):
    """Parent class for notebook panels."""
    # UI settings keys prefix - used for sashPos and uiList gui settings
    keyPrefix = u'OVERRIDE'

    def __init__(self, *args, **kwargs):
        super(NotebookPanel, self).__init__(*args, **kwargs)
        # needed as some of the initialization must run after RefreshUI
        self._firstShow = True

    def RefreshUIColors(self):
        """Called to signal that UI color settings have changed."""

    def ShowPanel(self, **kwargs):
        """To be manually called when particular panel is changed to and/or
        shown for first time."""

    def ClosePanel(self, destroy=False):
        """To be manually called when containing frame is closing. Use for
        saving data, scrollpos, etc - also used in BashFrame#SaveSettings."""
