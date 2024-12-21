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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2024 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""Weird module that sits in-between basher and gui on the abstraction tree
now. See #190, its code should be refactored and land in basher and/or gui."""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from functools import partial, wraps
from itertools import islice
from typing import final

import wx
import wx.adv

from . import bass, wrye_text  # bass for dirs - track
from . import bolt
from .bass import Store
from .bolt import FName, Path, RefrIn, deprint, readme_url, \
    fast_cached_property, RefrData
from .env import BTN_NO, BTN_YES, TASK_DIALOG_AVAILABLE
from .exception import CancelError, SkipError, StateError
from .gui import BusyCursor, Button, CheckListBox, Color, DialogWindow, \
    DirOpen, EventResult, FileOpen, FileOpenMultiple, FileSave, Font, \
    GlobalMenu, HLayout, LayoutOptions, ListBox, Links, LogDialog, LogFrame, \
    PanelWin, TextArea, UIListCtrl, VLayout, bell, copy_files_to_clipboard, \
    DeletionDialog, web_viewer_available, AutoSize, get_shift_down, \
    ContinueDialog, askText, askNumber, askYes, askWarning, showOk, showError, \
    showWarning, showInfo, TreeNodeFormat, DnDStatusBar, get_image, \
    get_color_checks, ImageList
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
    def _get_bundle(img_path):
        bundle = wx.IconBundle()
        # early boot get_image_dir not ready
        bundle.AddIcon(bass.dirs['images'].join(img_path).s)
        return bundle
    Resources.bashRed = _get_bundle('bash_icons_red.ico')
    Resources.bashBlue = _get_bundle('bash_icons_blue.ico')

# Settings --------------------------------------------------------------------
_settings: bolt.Settings = None # must be bound to bass.settings - smelly, #178

# Colors ----------------------------------------------------------------------
colors: dict[str, Color] = {}

# Images ----------------------------------------------------------------------
class ColorChecks(ImageList):
    """ColorChecks ImageList. Used by several UIList classes."""
    _int_to_state = {0: 'off', 1: 'on', 2: 'inc', 3: 'imp'}
    _statuses = ('purple', 'blue', 'green', 'orange', 'yellow', 'red')

    def __init__(self, icons_dict):
        super().__init__(16, 16)
        self._images = list(icons_dict.items())

    def img_dex(self, *args):
        if len(args) == 1:
            return super().img_dex(args[0])
        status, on = args
        if status <= -20: color_key = 'purple'
        elif status <= -10: color_key = 'blue'
        elif status <= 0: color_key = 'green'
        elif status <= 10: color_key = 'yellow'
        elif status <= 20: color_key = 'orange'
        else: color_key = 'red'
        return self._indices[f'{self._int_to_state[on]}.{color_key}']

def get_dv_bitmaps():
    """Returns the bitmaps needed for DocumentViewer."""
    return tuple(map(get_image, ('back.16', 'forward.16', 'reload.16')))

# Modal Dialogs ---------------------------------------------------------------
#------------------------------------------------------------------------------
def askContinue(parent, message, continueKey=None, title=_('Warning'),
                show_cancel=True):
    """Show a modal continue query if continueKey is provided and the value of
    the corresponding setting is False. Return True to continue.
    Also provides checkbox "Don't show this in the future." to set continueKey
    to True. continueKey must end in '.continue' - should be enforced. If
    continueKey is None however, it provides a "Don't show this for the rest of
    operation." checkbox instead."""
    #--ContinueKey set?
    if continueKey and _settings.get(continueKey):
        return True
    #--Generate/show dialog
    checkBoxTxt = _("Don't show this in the future.") if continueKey else _(
        "Don't show this for the rest of operation.")
    result, check = ContinueDialog.display_dialog(parent, message, title,
        checkBoxTxt, show_cancel=show_cancel, sizes_dict=_settings)
    if continueKey and result and check: # Don't store setting if user canceled
        _settings[continueKey] = 1
    return result if continueKey else ( # 2: checked 1: OK
        (result + bool(check)) if result else False)

#------------------------------------------------------------------------------
def show_log(parent, logText: str | Path, title: str | Path, wrye_log=False,
             asDialog=False):
    """Display text in a log window."""
    kw = {}
    if wrye_log:
        kw['dv_bitmaps'] = get_dv_bitmaps() #tell _LogWin we want a wryelog
        if not isinstance(logText, Path): # we only pass a Path in the BP log
            # convert logText from wtxt to html, pass the path to the html file
            ##: shouldn't we create a tmp file below?
            logPath = bass.dirs['saveBase'].join('WryeLogTemp.html')
            css_dir = bass.dirs['mopy'].join('Docs')
            wrye_text.convert_wtext_to_html(logPath, logText, css_dir)
            logText = logPath
    if asDialog:
        LogDialog.display_dialog(parent, f'{title}', Resources.bashBlue,
                                 _settings, logText=logText, **kw)
    else:
        LogFrame(parent, f'{title}', Resources.bashBlue, _settings,
                 logText=logText, **kw).show_frame()

def playSound(parent,sound):
    if not sound: return
    sound = wx.adv.Sound(sound)
    if sound.IsOk():
        sound.Play(wx.adv.SOUND_ASYNC)
    else:
        showError(parent, _('Invalid sound file %(sound_file)s.') % {
            'sound_file': sound})

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
        raise NotImplementedError # return []
    def add(self):
        """Performs add operation. Return new item on success."""
        raise NotImplementedError # return None
    def rename(self,oldItem,newItem):
        """Renames oldItem to newItem. Return true on success."""
        raise NotImplementedError # return False
    def remove(self,item):
        """Removes item. Return true on success."""
        raise NotImplementedError # return False

    #--Info box
    def getInfo(self,item):
        """Returns string info on specified item."""
        return u''
    def setInfo(self, item, info_text):
        """Sets string info on specified item."""
        raise NotImplementedError

    #--Save/Cancel
    def save(self):
        """Handles save button."""

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
        self._listEditorData: ListEditorData = lid_data
        self._list_items = lid_data.getItemList()
        #--GUI
        self._size_key = self._listEditorData.__class__.__name__
        super().__init__(parent, title, sizes_dict=_settings)
        #--List Box
        self.listBox = ListBox(self, choices=self._list_items,
                               onSelect=self.OnSelect)
        self.listBox.set_min_size(125, 150)
        #--Infobox
        self.gInfoBox: TextArea | None = None
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
            new_buttons = [_btn(defLabel, func) for def_flag, defLabel, func
                           in buttonSet if def_flag]
            le_buttons = VLayout(spacing=4, items=new_buttons)
        else:
            le_buttons = None
        #--Layout
        layout = VLayout(border=4, spacing=4, items=[
            (HLayout(spacing=4, item_expand=True, items=[
                (self.listBox, LayoutOptions(weight=1)),
                (self.gInfoBox, LayoutOptions(weight=self._listEditorData.infoWeight)),
                le_buttons
             ]), LayoutOptions(weight=1, expand=True))])
        #--Done
        if self._size_key in _settings['bash.window.sizes']:
            layout.apply_to(self)
            self.component_position = _settings['bash.window.sizes'][
                self._size_key]
        else:
            layout.apply_to(self, fit=True)

    #--List Commands
    def DoAdd(self):
        """Adds a new item."""
        newItem = self._listEditorData.add()
        if newItem and newItem not in self._list_items:
            self._list_items = self._listEditorData.getItemList()
            index = self._list_items.index(newItem)
            self.listBox.lb_insert(newItem, index)

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
            showError(self, _('Name must be unique.'))
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
    def OnSelect(self, _lb_selection_dex, lb_selection_str):
        """Handle show info (item select) event."""
        # self._listEditorData.select(lb_selection_str)
        if self.gInfoBox:
             # self.gInfoBox.DiscardEdits()
             self.gInfoBox.text_content = self._listEditorData.getInfo(
                 lb_selection_str)

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
        _settings['bash.window.sizes'][self._size_key] = self.component_size
        self.accept_modal()

    def DoCancel(self):
        """Handle cancel button."""
        _settings['bash.window.sizes'][self._size_key] = self.component_size
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
        if wx.Platform == '__WXMSW__': # CaptureMouse works badly in wxGTK/OSX
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

    def __init__(self, title=_('Progress'), message=f'\n{" " * 60}',
                 parent=None, abort=False, elapsed=True, __style=_style):
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
            return f'{first}…{second}'
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

#------------------------------------------------------------------------------
@dataclass(slots=True)
class _ListItemFormat:
    _parent_uil: UIList
    icon_key: tuple[str | None, ...] = (None,)
    bold: bool = False
    italics: bool = False
    underline: bool = False
    _text_key: str = 'default.text'
    _back_key: str = 'default.bkgd'

    def to_tree_node_format(self):
        """Convert this list item format to an equivalent tree node format,
        relative to the specified parent UIList."""
        return TreeNodeFormat(
            icon_idx=self._parent_uil.icons.img_dex(*self.icon_key),
            back_color=self._parent_uil.lookup_back_key(self.back_key),
            text_color=self._parent_uil.lookup_text_key(self.text_key),
            bold=self.bold, italics=self.italics, underline=self.underline)

    @property
    def back_key(self) -> str:
        return self._back_key

    @back_key.setter
    def back_key(self, val: str):
        self._back_key = max(val, self._back_key,
            key=self._parent_uil.back_key_priority.__getitem__)

    @property
    def text_key(self) -> str:
        return self._text_key

    @text_key.setter
    def text_key(self, val: str):
        self._text_key = max(val, self._text_key,
            key=self._parent_uil.text_key_priority.__getitem__)

DecoratedTreeDict = dict[FName, tuple[TreeNodeFormat | None,
    list[tuple[FName, TreeNodeFormat | None]]]]

class UIList(PanelWin):
    """Offspring of basher.List and balt.Tank, ate its parents."""
    # optional menus
    column_links = None # A list of all links to show in the column menu
    context_links = None # A list of all links to show in item context menus
    # A dict mapping category names to a Links instance that will be displayed
    # when the corresponding category is clicked on in the global menu. The
    # order in which categories are added will also be the display order.
    global_links = None
    # If set to True, ignore the bash.global_menu setting when determining
    # whether to show a column menu or not
    _bypass_gm_setting = False
    max_items_open = 7 # max number of items one can open without prompt
    #--Cols
    _min_column_width = 24
    # Set of columns that exist, but will never be visible and can't be
    # interacted with
    banned_columns = set()
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
    labels = {}
    #--DnD
    _dndFiles = _dndList = False
    _dndColumns = ()
    _target_ini = False # pass the target_ini settings on PopulateItem
    _copy_paths = False # enable the Ctrl+C shortcut

    def __init__(self, parent, keyPrefix, listData=None, panel=None):
        super().__init__(parent, wants_chars=True, no_border=False)
        self.data_store = listData # never use as local variable name !
        try:
            Link.Frame.all_uilists[self.data_store.unique_store_key] = self
        except AttributeError:
            pass # not one of the singleton DataStores
        self.panel = panel
        #--Settings key
        self.keyPrefix = keyPrefix
        #--Columns
        self.__class__.persistent_columns = {self._default_sort_col}
        self._col_index = {} # used in setting column sort indicator
        #--gList
        self.__gList = UIListCtrl(self, self.__class__._editLabels,
                                  self.__class__._sunkenBorder,
                                  self.__class__._singleCell, self.dndAllow,
                                  dndFiles=self.__class__._dndFiles,
                                  dndList=self.__class__._dndList,
                                  fnDropFiles=self.OnDropFiles,
                                  fnDropIndexes=self.OnDropIndexes)
        # Image List: Column sorting order indicators
        # explorer style ^ == ascending
        self.icons.native_init(recreate=False)
        self.sm_up = self.icons.img_dex('arrow.up.16')
        self.sm_dn = self.icons.img_dex('arrow.down.16')
        self.__gList.set_image_list(self.icons)
        if self.__class__._editLabels:
            self.__gList.on_edit_label_begin.subscribe(self.OnBeginEditLabel)
            self.__gList.on_edit_label_end.subscribe(self.OnLabelEdited)
        # gList callbacks
        self.__gList.on_lst_col_rclick.subscribe(self.DoColumnMenu)
        self.__gList.on_context_menu.subscribe(self.DoItemMenu)
        self.__gList.on_lst_col_click.subscribe(self._on_column_click)
        self.__gList.on_key_up.subscribe(self._handle_key_up)
        self.__gList.on_key_down.subscribe(self._handle_key_down)
        #--Events: Columns
        self.__gList.on_lst_col_end_drag.subscribe(self._on_column_resize)
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
        self._defaultTextBackground = Color.from_wx(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
        self.populate_items()

    @fast_cached_property
    def icons(self):
        return ColorChecks(get_color_checks())

    # Column properties
    @property
    def allCols(self): return list(self.labels)
    @property
    def all_allowed_cols(self):
        return [c for c in self.allCols if c not in self.banned_columns]
    @property
    def colWidths(self): return _settings[f'{self.keyPrefix}.colWidths']
    @property
    def colReverse(self):
        """Dictionary column->isReversed."""
        return _settings[f'{self.keyPrefix}.colReverse']
    @property
    def cols(self): return _settings[f'{self.keyPrefix}.cols']
    @property
    def allowed_cols(self):
        """Version of cols that filters out banned_columns."""
        return [c for c in self.cols if c not in self.banned_columns]
    @property
    def auto_col_widths(self):
        return _settings.get(f'{self.keyPrefix}.auto_size_columns',
            AutoSize.FIT_MANUAL)
    @auto_col_widths.setter
    def auto_col_widths(self, val):
        _settings[f'{self.keyPrefix}.auto_size_columns'] = val
    # the current sort column
    @property
    def sort_column(self):
        return _settings.get(f'{self.keyPrefix}.sort', self._default_sort_col)
    @sort_column.setter
    def sort_column(self, val): _settings[f'{self.keyPrefix}.sort'] = val

    @property
    def data_store_key(self) -> str:
        """The unique string key that establishes a correspondence between this
        UIList and its data store. Used when information is passed along
        between the backend and the GUI (e.g. for refreshing)."""
        return self.data_store.unique_store_key

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
        :param item: an FName or an int (Masters), the key in self.data
        :param target_ini_setts: Cached information about the INI settings.
            Used on the INI Edits tab"""
        insert = False
        allow_cols = self.allowed_cols # property, calculate once
        if not allow_cols:
            return # No visible columns, nothing to do
        if item is not None:
            try:
                itemDex = self._get_uil_index(item)
            except KeyError: # item is not present, so inserting
                itemDex = self.item_count # insert at the end
                insert = True
        else: # no way we're inserting with a None item
            item = self.GetItem(itemDex)
        str_label = self.labels[allow_cols[0]](self, item)
        if insert:
            # We're inserting a new item, so we need special handling for the
            # first SetItem call - see InsertListCtrlItem
            self.__gList.InsertListCtrlItem(
                itemDex, str_label, item,
                decorate_cb=partial(self.__setUI, item, target_ini_setts))
        else:
            # The item is already in the UIList, so we only need to redecorate
            # and set text for all labels
            gItem = self.__gList.get_item_data(itemDex)
            self.__setUI(item, target_ini_setts, gItem)
            # Piggyback off the SetItem call we need for __setUI to also set
            # the first column's text
            gItem.SetText(str_label)
            self.__gList.set_item_data(gItem)
        for col_dex, col in enumerate(allow_cols[1:], start=1):
            self.__gList.set_item_data(itemDex, col_dex,
                                       self.labels[col](self, item))

    def populate_items(self):
        """Sort items and populate entire list."""
        # Make sure to freeze/thaw, all the InsertListCtrlItem calls make the
        # GUI lag
        with self.pause_drawing():
            self.mouseTexts.clear()
            items = set(self.data_store)
            if self.__class__._target_ini:
                # hack for avoiding the syscall in get_ci_settings
                t_setts = self.data_store.ini.get_ci_settings()
            else:
                t_setts = None
            #--Update existing items.
            index = 0
            while index < self.item_count:
                item = self.GetItem(index)
                if item not in items: self.__gList.RemoveItemAt(index)
                else:
                    self.PopulateItem(itemDex=index, target_ini_setts=t_setts)
                    items.remove(item)
                    index += 1
            #--Add remaining new items
            for item in items:
                self.PopulateItem(item=item, target_ini_setts=t_setts)
            #--Sort
            self.SortItems()
            self.autosizeColumns()

    _same_item = object()
    @final
    def RefreshUI(self, rdata=None, *, detail_item=_same_item,
                  focus_list=True):
        """Populate specified files or ALL files, sort, set status bar count,
        etc. See parameter docs below.

        :param rdata: If passed, refresh/add the UIList items specified in
            rdata.redraw and delete the items in rdata.to_del. Else,
            entirely repopulate this UIList.
        :param focus_list: If True, focus this UIList."""
        if rdata is None:
            self.populate_items()
            updated = ()
        else: # a RefrData instance
            # Make sure to freeze/thaw, all the InsertListCtrlItem calls make
            # the GUI lag
            with self.pause_drawing():
                for d in rdata.to_del:
                    self.__gList.RemoveItemAt(self._get_uil_index(d))
                for upd in (updated := rdata.redraw | rdata.to_add):
                    self.PopulateItem(item=upd)
                #--Sort
                self.SortItems()
                self.autosizeColumns()
        self._refresh_details(updated, detail_item)
        if Link.Frame.notebook.currentPage is self.panel:
            # we need to check if our Panel is currently shown because we may
            # call Refresh UI of other tabs too - this results for instance in
            # mods count flickering when deleting a save in saves tab
            Link.Frame.set_status_info(self.panel.sb_count_str(), 2)
        if focus_list: self.Focus()

    def propagate_refresh(self, refresh_others: defaultdict[str, bool | dict],
                          **kwargs):
        """Refresh this UIList and propagate the refresh to other tabs.
        :param refresh_others: A dict mapping unique data store keys (see
            bass.Store) to RefreshUI kwargs."""
        kwargs.setdefault('focus_list', True)
        refresh_others[self.data_store_key] = kwargs
        Link.Frame.distribute_ui_refresh(refresh_others)

    def _refresh_details(self, to_redraw, detail_item):
        if detail_item is None:
            self.panel.ClearDetails()
        elif detail_item is not self._same_item:
            self.SelectAndShowItem(detail_item)
        else: # if it was a single item, refresh details for it
            if len(to_redraw) == 1:
                self.SelectAndShowItem(next(iter(to_redraw)))
            else:
                self.panel.SetDetails()

    def Focus(self):
        self.__gList.set_focus()

    #--Decorating -------------------------------------------------------------
    @fast_cached_property
    def back_key_priority(self):
        return {k: j for j, k in enumerate([
            # Plugins ---------------------------------------------------------
            'default.bkgd', 'mods.bkgd.size_mismatch', 'mods.bkgd.ghosted',
            'mods.bkgd.doubleTime.exists', 'mods.bkgd.doubleTime.load',
            # INIs ------------------------------------------------------------
            'ini.bkgd.invalid',
            # Installers ------------------------------------------------------
            'installers.bkgd.skipped', 'installers.bkgd.outOfOrder',
            'installers.bkgd.dirty'])}

    @fast_cached_property
    def text_key_priority(self):
        from . import bush
        return {k: j for j, k in enumerate([
            # Plugins ---------------------------------------------------------
            'default.text', *dict.fromkeys(bush.game.mod_keys.values()),
            # Installers ------------------------------------------------------
            'installers.text.invalid', 'installers.text.marker',
            'installers.text.complex',
        ])}

    def set_item_format(self, item, item_format, target_ini_setts):
        """Populate item_format attributes for text and background colors
        and set icon, font and mouse text. Responsible (applicable if the
        data_store is a FileInfo subclass) for calling getStatus (or
        tweak_status in Inis) to update respective info's status."""
        pass # screens, bsas

    def __setUI(self, fileName, target_ini_setts, gItem):
        """Set font, status icon, background text etc."""
        df = _ListItemFormat(self)
        self.set_item_format(fileName, df, target_ini_setts=target_ini_setts)
        icon_index = self.icons.img_dex(*df.icon_key)
        if icon_index is not None:
            gItem.SetImage(icon_index)
        gItem.SetTextColour(self.lookup_text_key(df.text_key).to_rgba_tuple())
        gItem.SetBackgroundColour(
            self.lookup_back_key(df.back_key).to_rgba_tuple())
        gItem.SetFont(Font.Style(gItem.GetFont(), strong=df.bold,
                                 slant=df.italics, underline=df.underline))

    def lookup_text_key(self, target_text_color: str):
        """Helper method to look up a text color from a list item format."""
        if target_text_color:
            return colors[target_text_color]
        else:
            return self.__gList.get_text_color()

    def lookup_back_key(self, target_back_color: str):
        """Helper method to look up a background color from a list item
        format."""
        if target_back_color:
            return colors[target_back_color]
        else:
            return self._defaultTextBackground

    def decorate_tree_dict(self, tree_dict: dict[FName, list[FName]],
            target_ini_setts=None) -> DecoratedTreeDict:
        """Add appropriate TreeNodeFormat instances to the specified dict
        mapping items in this UIList to lists of items in this UIList."""
        def _decorate(i):
            lif = _ListItemFormat(self)
            # Only run set_item_format when the item is actually present,
            # otherwise just use the default settings (we do still have to use
            # those since the default text/background colors may have been
            # changed from the OS default)
            if i in self.data_store:
                self.set_item_format(i, lif, target_ini_setts=target_ini_setts)
            return lif.to_tree_node_format()
        return {i: (_decorate(i), [(c, _decorate(c)) for c in i_children])
                for i, i_children in tree_dict.items()}

    #--Right Click Menus ------------------------------------------------------
    def DoColumnMenu(self, evt_col: int):
        """Show column menu.

        :param evt_col: The index of the column that the user clicked on."""
        if self._pop_menu():
            self.column_links.popup_menu(self, evt_col)
        return EventResult.FINISH

    def _pop_menu(self):
        """Decide if we should pop the columns menu - must be set for one."""
        return (self.column_links and not # column menu must be set
            self.__gList.ec_rename_prompt_opened() and # See DoItemMenu below
            # bash.global_menu == 1 -> Global Menu Only
            (self._bypass_gm_setting or _settings['bash.global_menu'] != 1))

    def DoItemMenu(self):
        """Show item menu."""
        # Don't allow this if we are in the process of renaming because
        # various operations in the menus would make the rename prompt lose
        # focus, which would leave WB's data stores out of sync with the file
        # system, resulting in errors when we go to access the file
        if not self.__gList.ec_rename_prompt_opened():
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
        if cmd_down and kcode == ord(u'A'): # Ctrl+A - (de)select all
            if wrapped_evt.is_shift_down: # deselect all
                self.ClearSelected(clear_details=True)
            else: # select all
                with self.__gList.on_item_selected.pause_subscription(
                    self._handle_select):
                    # omit below to leave displayed details
                    self.panel.ClearDetails()
                    self.__gList.lc_select_item_at_index(-1) # -1 indicates 'all items'
        elif self.__class__._editLabels and kcode == wx.WXK_F2: # F2 - rename
            self.Rename()
        elif kcode in _wx_delete: # Del - delete selected file(s)
            with BusyCursor(): self.DeleteItems(wrapped_evt=wrapped_evt)
        elif cmd_down and kcode == ord(u'O'): # Ctrl+O - open data folder
            self.open_data_store()
        elif cmd_down and kcode == ord('S'): # Ctrl+S - save data
            with BusyCursor():
                Link.Frame.SaveSettings()
        # Ctrl+Num + - auto-size columns to fit contents
        elif cmd_down and kcode == wx.WXK_NUMPAD_ADD:
            self.auto_col_widths = AutoSize.FIT_CONTENTS
            # On Windows, this happens automatically (due to the native widget
            # handling it), so all we have to do there is update our internal
            # state to match. On all (?, only tested on wxGTK) other platforms
            # we have to implement it ourselves
            if wx.Platform != '__WXMSW__':
                self.autosizeColumns()
        # Ctrl+C - copy file(s) to clipboard
        elif self.__class__._copy_paths and cmd_down and kcode == ord(u'C'):
            copy_files_to_clipboard(
                [x.abs_path.s for x in self.GetSelectedInfos()])
        else:
            return EventResult.CONTINUE
        return EventResult.FINISH

    # Columns callbacks
    def _on_column_click(self, evt_col):
        """Column header was left-clicked on. Sort on that column."""
        self.SortItems(self.cols[evt_col], 'INVERT')

    def _on_column_resize(self, evt_col):
        """Column resized: enforce minimal width and save column size info."""
        colName = self.cols[evt_col]
        width = self.__gList.lc_get_column_width(evt_col)
        if width < self._min_column_width:
            width = self._min_column_width
            self.__gList.lc_set_column_width(evt_col, self._min_column_width)
            # if we do not veto the column will be resized anyway!
            self.__gList.resize_last_col() # resize last column to fill
            self.colWidths[colName] = width
            return EventResult.CANCEL
        self.colWidths[colName] = width

    # gList columns autosize---------------------------------------------------
    def autosizeColumns(self):
        if self.auto_col_widths != AutoSize.FIT_MANUAL:
            colCount = range(self.__gList.lc_get_columns_count())
            for i in colCount:
                self.__gList.lc_set_auto_column_width(i, self.auto_col_widths)

    #--Events skipped
    def _handle_left_down(self, wrapped_evt, lb_dex_and_flags): pass
    def OnDClick(self, lb_dex_and_flags): pass
    def _handle_key_down(self, wrapped_evt):
        if wrapped_evt.is_cmd_down and wrapped_evt.key_code == wx.WXK_TAB:
            if wx.Platform == '__WXMSW__':
                # Handled natively on MSW ##: what about macOS?
                return EventResult.CONTINUE
            # Ctrl+Tab - cycle tabs to the right
            # Ctrl+Shift+Tab - cycle tabs to the left
            Link.Frame.notebook.AdvanceSelection(not wrapped_evt.is_shift_down)
        else:
            return EventResult.CONTINUE
        return EventResult.FINISH
    #--Edit labels - only registered if _editLabels != False
    def _check_rename_requirements(self):
        """Check if the renaming operation is allowed and return the item type
        of the selected labels to be renamed as well as an error to show the
        user."""
        if not (sel_original := self.GetSelected()):
            # I don't see how this would be possible, but just in case...
            return None, _('No items selected for renaming.')
        sel_filtered = self.data_store.filter_essential(sel_original)
        if not sel_filtered:
            # None of the selected items may be renamed, so this whole renaming
            # attempt is a nonstarter
            return None, _('The selected items cannot be renamed.')
        if next(iter(sel_filtered)) != sel_original[0]:
            # The currently selected/detail item cannot be renamed, so we can't
            # edit labels, which means we have to abort the renaming attempt
            return None, _('Renaming %(first_item)s is not allowed.') % {
                'first_item': sel_original[0]}
        return type(next(iter(sel_filtered.values()))), ''

    def could_rename(self):
        """Returns True if the currently selected item(s) would allow
        renaming."""
        return self._check_rename_requirements()[0] is not None

    def OnBeginEditLabel(self, evt_label, uilist_ctrl):
        """Start renaming: deselect the extension."""
        rename_type, rename_err = self._check_rename_requirements()
        if not rename_type:
            # We can't rename for some reason, let the user know
            showError(self, rename_err)
            return EventResult.CANCEL
        uilist_ctrl.ec_set_selection(*rename_type.rename_area_idxs(evt_label))
        uilist_ctrl.ec_set_f2_handler(self._on_f2_handler)
        return EventResult.FINISH  ##: needed?

    def OnLabelEdited(self, is_edit_cancelled, evt_label, evt_index, evt_item):
        # should only be subscribed if _editLabels==True and overridden
        raise NotImplementedError

    def _on_f2_handler(self, is_f2_down, ec_value, uilist_ctrl):
        """For pressing F2 on the edit box for renaming"""
        if is_f2_down:
            to_rename = self.GetSelectedInfos()
            renaming_type = type(to_rename[0])
            start, stop = uilist_ctrl.ec_get_selection()
            if start == stop: # if start==stop there is no selection ##: we may need to return?
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

    # Renaming - note the @conversation, this needs to be atomic with respect
    # to refreshes and ideally atomic short - store_refr is Installers only
    @conversation
    def try_rename(self, info, newName, rdata_ren, store_refr=None):
        """Mods/BSAs - Inis won't be added and Screens/Installers/Saves
        override - reduce this."""
        try:
            return self.data_store.rename_operation(info, newName, rdata_ren,
                store_refr=store_refr) # a RefrData instance
        except (CancelError, OSError):
            deprint(f'Renaming {info} to {newName} failed', traceback=True)
            # When using moveTo I would get "WindowsError:[Error 32]The process
            # cannot access ..." -  the code below was reverting the changes.
            # With shellMove I mostly get CancelError so below not needed -
            # except if a save is locked and user presses Skip - so cosaves are
            # renamed! Error handling is still a WIP
            for old, new in info.get_rename_paths(newName):
                if old == new: continue
                if (nex := new.exists()) and not (oex := old.exists()):
                    # some cosave move failed, restore files
                    new.moveTo(old, check_exist=False) # we just checked
                elif nex and oex:
                    # move copies then deletes, so the delete part failed
                    new.remove()  # return None # break
            return None # maybe a msg if really really needed

    def _getItemClicked(self, lb_dex_and_flags, *, on_icon=False):
        (hitItem, hitFlag) = lb_dex_and_flags
        if hitItem < 0 or (on_icon and hitFlag != wx.LIST_HITTEST_ONITEMICON):
            return None
        return self.GetItem(hitItem)

    def _get_info_clicked(self, lb_dex_and_flags, *, on_icon=False):
        item_key = self._getItemClicked(lb_dex_and_flags, on_icon=on_icon)
        return self.data_store[item_key] if item_key else item_key

    #--Item selection ---------------------------------------------------------
    def _get_selected(self, items=False):
        """Return the list of indexes highlighted in the interface in
        display order - if items is True return the list of items instead."""
        listCtrl, selected_list = self.__gList, []
        i = listCtrl.get_selected_index()
        while i != -1:
            selected_list.append(i)
            i = listCtrl.get_selected_index(i)
        return [*map(self.GetItem, selected_list)] if items else selected_list

    def GetSelected(self):
        """Return list of items selected (highlighted) in the interface."""
        return self._get_selected(items=True)

    def GetSelectedInfos(self, selected=None):
        """Return list of infos selected (highlighted) in the interface."""
        return [self.data_store[k] for k in (selected or self.GetSelected())]

    def get_selected_infos_filtered(self, selected=None):
        """Version of GetSelectedInfos that filters out essential infos."""
        return [*self.data_store.filter_essential(
            selected or self.GetSelected()).values()]

    def SelectItem(self, item, deselectOthers=False):
        dex = self._get_uil_index(item)
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

    def EnsureVisibleIndex(self, dex, focus=False):
        if focus:
            self.__gList.focus_index(dex)
        else:
            self.__gList.ensure_visible_index(dex)
        self.Focus()

    def SelectAndShowItem(self, item, deselectOthers=False, focus=True):
        self.SelectItem(item, deselectOthers=deselectOthers)
        self.EnsureVisibleIndex(self._get_uil_index(item), focus=focus)

    def OpenSelected(self, selected=None):
        """Open selected files with default program."""
        sel_openable = self.data_store.filter_unopenable(
            selected or self.GetSelected())
        if not sel_openable:
            showWarning(self, _('The selected items cannot be opened.'))
            return
        num = len(sel_openable)
        if num > UIList.max_items_open and not askContinue(self,
            _(u'Trying to open %(num)s items - are you sure ?') % {u'num': num},
            u'bash.maxItemsOpen.continue'): return
        for sel_inf in sel_openable.values():
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
        column, reverse, oldcol = self._get_sort_settings(column, reverse)
        items = self._SortItems(column, reverse)
        self.__gList.ReorderDisplayed(items)
        # check if old column is present then clear the sort indicator - not
        # needed if column stays the same (set_col_image will replace the icon)
        if column != oldcol and oldcol in self._col_index:
            self.__gList.clear_col_image(self._col_index[oldcol])
        # set column sort image - runs also on disabling columns
        if column in self._col_index: # check if the column was not just hidden
            self.__gList.set_col_image(self._col_index[column],
                                       self.sm_dn if reverse else self.sm_up)

    def _get_sort_settings(self, column, reverse):
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
        def _mk_key(k): # if key is None then keep it None else provide self
            k = self._sort_keys[k]
            return bolt.natural_key() if k is None else partial(k, self)
        defaultKey = _mk_key(self._default_sort_col)
        defSort = col == self._default_sort_col
        # always apply default sort
        items = sorted(self.data_store if items is None else items,
                       key=defaultKey, reverse=defSort and reverse)
        if not defSort: items.sort(key=_mk_key(col), reverse=reverse)
        if sortSpecial:
            for lamda in self._extra_sortings: lamda(self, items)
        return items

    #--Item/Index Translation -------------------------------------------------
    def GetItem(self, index) -> FName | int:
        """Return item (key in self.data_store) for specified list index."""
        return self.__gList.FindItemAt(index)

    def _get_uil_index(self, item):
        """Return index for item, raise KeyError if item not present."""
        return self.__gList.FindIndexOf(item)

    #--Populate Columns -------------------------------------------------------
    def _clean_column_settings(self):
        """Removes columns that no longer exist from settings files."""
        valid_columns = set(self.allCols)
        # Clean the widths/reverse dictionaries
        for dict_key in ('.colWidths', '.colReverse'):
            stored_dict = _settings[f'{self.keyPrefix}{dict_key}']
            invalid_columns = set(stored_dict) - valid_columns
            for c in invalid_columns:
                del stored_dict[c]
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
        # this may have been updated in ColumnsMenu.Execute()
        allow_cols = self.allowed_cols
        numCols = len(allow_cols)
        names = {_settings[u'bash.colNames'].get(key) for key in allow_cols}
        self._col_index.clear()
        colDex, listCtrl = 0, self.__gList
        while colDex < numCols: ##: simplify!
            colKey = allow_cols[colDex]
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
            self._col_index[colKey] = colDex
            colDex += 1
        while listCtrl.lc_get_columns_count() > numCols:
            listCtrl.lc_delete_column(numCols)

    #--Drag and Drop-----------------------------------------------------------
    @conversation
    def dndAllow(self, event): # Disallow drag and drop by default
        if event: event.Veto()
        return False

    def OnDropFiles(self, x, y, filenames): raise NotImplementedError
    def OnDropIndexes(self, indexes, newPos): raise NotImplementedError

    # gList scroll position----------------------------------------------------
    def SaveScrollPosition(self, isVertical=True):
        _settings[f'{self.keyPrefix}.scrollPos'] = self.__gList.get_scroll_pos(
            isVertical)

    def SetScrollPosition(self):
        if _settings['bash.restore_scroll_positions']:
            with self.__gList.pause_drawing():
                self.__gList.set_scroll_pos(
                    _settings.get(f'{self.keyPrefix}.scrollPos', 0))

    # Data commands (WIP)------------------------------------------------------
    def Rename(self, selected=None):
        if not selected: selected = self.GetSelected()
        if selected:
            index = self._get_uil_index(selected[0])
            if index != -1:
                self.__gList.edit_label(index)

    @conversation
    def DeleteItems(self, wrapped_evt=None, items=None,
                    dialogTitle=_(u'Delete Items'), order=True):
        items = items if items is not None else self.GetSelected()
        if not items:
            # Sometimes we get a double Del key event on GTK, but with no
            # selection present for the second one - just skip that
            return
        # We need a copy of the original items for the error below
        orig_items = items
        if wrapped_evt is None: # Called from menu item
            recycle = not get_shift_down()
        else:
            recycle = not wrapped_evt.is_shift_down
        items = list(self.data_store.filter_essential(items))
        if not items and orig_items:
            # Only undeletable items selected, inform the user
            showError(self, _('The selected items cannot be deleted.'))
            return
        if order: items.sort()
        # Let the user adjust deleted items and recycling state via GUI
        dd_ok, dd_items, dd_recycle = DeletionDialog.display_dialog(self,
            title=dialogTitle, items_to_delete=items, default_recycle=recycle,
            sizes_dict=_settings, icon_bundle=Resources.bashBlue,
            trash_icon=get_image('trash_can.32'))
        if not dd_ok or not dd_items: return
        try:
            self.data_store.delete(dd_items, recycle=dd_recycle)
        except (PermissionError, CancelError, SkipError): pass
        # Also cleans _gList internal dicts
        self.propagate_refresh(Store.SAVES.DO())

    def open_data_store(self):
        try:
            (sd := self.data_store.store_dir).start()
            return
        except OSError:
            deprint(f'Creating {sd}')
            sd.makedirs()
        sd.start()

    def hide(self, items: dict[FName, ...]):
        """Hides the items in the specified iterable."""
        moved_infos = set()
        for fnkey, inf in items.items():
            destDir = inf.get_hide_dir()
            if destDir.join(fnkey).exists():
                message = (_('A file named %(target_file_name)s already '
                             'exists in the hidden files directory. Overwrite '
                             'it?') % {'target_file_name': fnkey})
                if not askYes(self, message, _('Hide Files')): continue
            #--Do it
            with BusyCursor():
                inf.move_info(destDir)
                moved_infos.add(inf)
        # no need to check existence, we just moved them
        self.data_store.refresh(RefrIn(del_infos=moved_infos))

    @staticmethod
    def _unhide_wildcard(): raise NotImplementedError
    def unhide(self):
        srcDir = self.data_store.hide_dir
        # Otherwise the unhide command will open some random directory
        srcDir.makedirs()
        wildcard = self._unhide_wildcard()
        destDir = self.data_store.store_dir
        srcPaths = FileOpenMultiple.display_dialog(self, _(u'Unhide files:'),
            defaultDir=srcDir, wildcard=wildcard)
        return destDir, srcDir, srcPaths

    def jump_to_source(self, uil_item: FName) -> bool:
        """Jumps to the installer associated with the specified UIList item."""
        fn_package = self.get_source(uil_item)
        if fn_package is None:
            return False
        try:
            Link.Frame.notebook.SelectPage('Installers', fn_package)
        except KeyError:
            # The package does not exist anymore
            ##: This points to deeper bugs in our ownership handling/updating
            # that should be fixed
            return False
        return True

    def get_source(self, uil_item: FName) -> FName | None:
        """Returns the package associated with the specified UIList item, or
        None if the Installers tab is not enabled or the Installers tab is
        enabled but not constructed (i.e. hidden) or the item does not have an
        associated package."""
        if (not Link.Frame.iPanel or
                not _settings['bash.installers.enabled']):
            return None # Installers disabled or not initialized
        return FName(self.data_store[uil_item].get_table_prop('installer'))

    # Global Menu -------------------------------------------------------------
    def _populate_category(self, cat_label, target_category):
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
                self._populate_category, curr_cat))

# Links -----------------------------------------------------------------------
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
    # Menu label (may depend on UI state when the menu is shown)
    _text = u''

    def __init__(self, _text=None):
        """Initialize a Link instance.

        Parameter _text underscored cause its use should be avoided - prefer to
        specify text as a class attribute (or set it via link_text). Used by
        ChoiceLink however, so it *is* still used."""
        super(Link, self).__init__()
        self._text = _text or self.__class__._text # menu label

    def _initData(self, window: UIList | wx.Panel | Button | CheckListBox,
            selection: list[FName | int] | int | None):
        """Initialize the Link instance data based on UI state when the
        menu is Popped up.

        Called from AppendToMenu - DO NOT call directly. If you need to use the
        initialized data in setting instance attributes (such as text) override
        and always _call super_ when overriding.

        :param window: the element the menu is being popped from (usually a
            UIList subclass)
        :param selection: the selected items when the menu is appended or None.
            In modlist/installers it's a list<Path> while in sub-package it's
            the index of the right-clicked item. In main (column header) menus
            it's the column clicked on or the first column. Set in
            Links.popup_menu()."""
        self.window = window
        self.selected = selection

    def AppendToMenu(self, menu, window, selection):
        """Creates a wx menu item and appends it to :menu.

        Link implementation calls _initData and returns None.
        """
        self._initData(window, selection)

    def iselected_infos(self):
        return (self._data_store[x] for x in self.selected)

    @property
    def _data_store(self):
        return self.window.data_store

    def iselected_pairs(self):
        return ((x, self._data_store[x]) for x in self.selected)

    def _first_selected(self):
        """Return the first selected info."""
        return next(self.iselected_infos())

    def refresh_sel(self, to_refr=None, **kwargs):
        """Refresh selected items (or items in to_refr) in the UIList."""
        to_refr = self.selected if to_refr is None else to_refr
        self.window.RefreshUI(RefrData(set(to_refr)), **kwargs)

    # Wrappers around balt dialogs - used to single out non trivial uses of
    # self->window
    ##: avoid respecifying default params
    def _showWarning(self, message, title=_('Warning')):
        return showWarning(self.window, message, title=title)

    def _askYes(self, message, title='', default_is_yes=True,
                questionIcon=False):
        return askYes(self.window, message, title=title or self._text,
            default_is_yes=default_is_yes, question_icon=questionIcon)

    def _askContinue(self, message, continueKey, title=_('Warning'),
            show_cancel=True):
        return askContinue(self.window, message, continueKey, title=title,
            show_cancel=show_cancel)

    def _askContinueShortTerm(self, message, title=_('Warning')):
        return askContinue(self.window, message, continueKey=None, title=title)

    def _showOk(self, message, title=u''):
        return showOk(self.window, message, title or self._text)

    def _askWarning(self, message, title=_(u'Warning')):
        return askWarning(self.window, message, title)

    def _askText(self, message, title=u'', default=u'', strip=True):
        return askText(self.window, message, title=title or self._text,
                       default_txt=default, strip=strip)

    def _showError(self, message, title=_(u'Error')):
        return showError(self.window, message, title)

    def _showLog(self, logText, title='', *, asDialog=False):
        show_log(self.window, logText, title, asDialog=asDialog)

    def _showInfo(self, message, title=_(u'Information')):
        return showInfo(self.window, message, title)

    def _showWryeLog(self, logText, title='', *, asDialog=True):
        show_log(self.window, logText, title or self._text, wrye_log=True,
                 asDialog=asDialog)

    def _askNumber(self, message, prompt='', title='', initial_num=0,
            min_num=0, max_num=10000):
        return askNumber(self.window, message, prompt, title,
            initial_num=initial_num, min_num=min_num, max_num=max_num)

    # De-wx'd File/dir dialogs
    def _askOpen(self, title='', defaultDir='', defaultFile='', wildcard=''):
        return FileOpen.display_dialog(self.window, title, defaultDir,
                                       defaultFile, wildcard)

    def _askSave(self, title='', defaultDir='', defaultFile='', wildcard=''):
        return FileSave.display_dialog(self.window, title, defaultDir,
                                       defaultFile, wildcard)

    def _askDirectory(self, message=_('Choose a directory.'), defaultPath=''):
        """Show a modal directory dialog and return the resulting path,
        or None if canceled."""
        return DirOpen.display_dialog(self.window, message, defaultPath,
                                      create_dir=True)

# Link subclasses -------------------------------------------------------------
class ItemLink(Link):
    """Create and append a wx menu item.

    Subclasses MUST define _text (preferably class) attribute and should
    override _help. Registers the Execute() and ShowHelp methods on menu events
    """
    kind = wx.ITEM_NORMAL # The default in wx.MenuItem(... kind=...)
    _help = u''           # The tooltip to show at the bottom of the GUI
    _keyboard_hint = ''   # The keyboard shortcut hint to show, if any

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
        full_link_text = _AComponent._escape(self.link_text)
        if self._keyboard_hint:
            full_link_text += f'\t{self._keyboard_hint}'
        # Note default id here is *not* ID_ANY but the special ID_SEPARATOR!
        menuItem = wx.MenuItem(menu, wx.ID_ANY, full_link_text, self.link_help,
                               self.__class__.kind)
        # If the menu comes with a parent window (i.e. from the global menu),
        # then use that for binding. Otherwise, use the parent window we got
        # passed in (i.e. for column links, context menus, etc.)
        if not (bind_parent := menu.GetWindow()):
            bind_parent = _AComponent._resolve(window)
        bind_parent.Bind(wx.EVT_MENU, self.__Execute, id=menuItem.GetId())
        Link.Frame._native_widget.Bind(wx.EVT_MENU_HIGHLIGHT_ALL, ItemLink.ShowHelp)
        menu.Append(menuItem)
        return menuItem

    # Callbacks ---------------------------------------------------------------
    # noinspection PyUnusedLocal
    def __Execute(self, __event):
        """Eat up wx event - code outside balt should not use it."""
        self.Execute()
        return EventResult.FINISH

    def Execute(self):
        """Event: link execution."""
        raise NotImplementedError

    @staticmethod
    def ShowHelp(event): # <wx._core.MenuEvent>
        """Hover over an item, set the statusbar text"""
        if Links.Popup:
            item = Links.Popup.FindItemById(event.GetId()) # <wx._core.MenuItem>
            Link.Frame.set_status_info(item.GetHelp() if item else u'')

class MenuLink(Link):
    """Defines a submenu. Generally used for submenus of large menus."""

    def __init__(self, menu_name=None, oneDatumOnly=False):
        """Initialize. Submenu items should append themselves to self.links."""
        super().__init__()
        self._text = menu_name or self.__class__._text
        self.links = Links()
        self.oneDatumOnly = oneDatumOnly

    def append(self, link):
        self.links.append_link(link) ##: MenuLink(Link, Links) !

    def _enable(self): return not self.oneDatumOnly or len(self.selected) == 1

    def AppendToMenu(self, menu, window, selection):
        """Append self as submenu (along with submenu items) to menu."""
        super().AppendToMenu(menu, window, selection)
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
        """Disable ourselves if none of our children are usable."""
        return self._any_link_usable(self.links)

    def _any_link_usable(self, candidate_links):
        """Helper method that returns True if at least one of the candidate links
        can be interacted with by the user."""
        for l in candidate_links:
            if isinstance(l, SeparatorLink):
                # SeparatorLinks are not interactable links, so there is no
                # need to worry about their enabled status
                continue
            if isinstance(l, AppendableLink):
                # This is an AppendableLink, skip if it's not appended
                if not l._append(self.window): continue
            if isinstance(l, MenuLink): # not elif!
                # MenuLinks have an _enable method too, avoid calling that
                if l._enable_menu(): return True
            elif isinstance(l, EnabledLink):
                # This is an EnabledLink, check if it's enabled
                if l._enable(): return True
                if isinstance(l, MultiLink): # not elif!
                    # This is a MultiLink (appended and enabled), check if any
                    # of its child links are usable
                    if self._any_link_usable(l._links()): return True
            elif isinstance(l, MultiLink):
                # This is a MultiLink (appended and not an EnabledLink), check
                # if any of its child links are usable
                if self._any_link_usable(l._links()): return True
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
        raise NotImplementedError

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
        raise NotImplementedError

    def AppendToMenu(self, menu, window, selection):
        if not self._append(window): return
        return super(AppendableLink, self).AppendToMenu(menu, window,
                                                        selection)

class MultiLink(Link):
    """A link that resolves to several links when appended."""
    def _links(self):
        """Returns the list of links that this link resolves to."""
        raise NotImplementedError

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
    def _enable(self): return len(self.selected) == 1

    @property
    def _selected_item(self): return self.selected[0]
    @property
    def _selected_info(self): return self._first_selected()

class CheckLink(ItemLink):
    kind = wx.ITEM_CHECK

    def _check(self): raise NotImplementedError

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
class UIList_Delete(EnabledLink):
    """Delete selected item(s) from UIList."""
    _text = _('Delete')
    _keyboard_hint = 'Del'

    def _filter_undeletable(self, to_delete_items):
        """Filters out undeletable items from the specified iterable."""
        return self._data_store.filter_essential(to_delete_items)

    def _enable(self):
        # Only enable if at least one deletable file is selected
        return bool(self._filter_undeletable(self.selected))

    @property
    def link_help(self):
        sel_filtered = list(self._filter_undeletable(self.selected))
        if sel_filtered == self.selected:
            if len(sel_filtered) == 1:
                return _("Delete '%(filename)s'.") % {
                    'filename': sel_filtered[0]}
            return _('Delete the selected items.')
        else:
            if sel_filtered:
                return _('Delete the selected items (some of the selected '
                         'items cannot be deleted and will be skipped).')
            return _('The selected items cannot be deleted.')

    def Execute(self):
        # event is a 'CommandEvent' and I can't check if shift is pressed - duh
        with BusyCursor():
            self.window.DeleteItems(items=self.selected)

class UIList_Rename(EnabledLink):
    """Rename selected UIList item(s)."""
    _text = _('Rename…')
    _keyboard_hint = 'F2'

    @property
    def link_help(self):
        if self.window.could_rename():
            sel_filtered = [*self._data_store.filter_essential(self.selected)]
            if len(sel_filtered) == 1:
                return _('Renames the selected item.')
            elif sel_filtered == self.selected:
                return _('Renames the selected items.')
            else:
                return _('Renames the selected items (some of the selected '
                         'items cannot be renamed and will be skipped).')
        return _('The selected items cannot be renamed.')

    def _enable(self):
        return self.window.could_rename()

    def Execute(self):
        self.window.Rename(selected=self.selected)

class UIList_OpenItems(EnabledLink):
    """Open specified file(s)."""
    _text = _('Open…')
    _keyboard_hint = 'Enter'

    @property
    def link_help(self):
        sel_filtered = list(self._data_store.filter_unopenable(self.selected))
        if sel_filtered == self.selected:
            if len(sel_filtered) == 1:
                return _("Open '%(item_to_open)s' with the system's default "
                         "program.") % {'item_to_open': sel_filtered[0]}
            return _("Open the selected items with the system's default "
                     "program.")
        else:
            if sel_filtered:
                return _("Open the selected items with the system's default "
                         "program (some of the selected items cannot be "
                         "opened and will be skipped).")
            return _("The selected items cannot be opened with the system's "
                     "default program.")

    def _enable(self):
        return bool(self._data_store.filter_unopenable(self.selected))

    def Execute(self):
        # OpenSelected will do the filtering, no need for us to do it too
        self.window.OpenSelected(self.selected)

class UIList_OpenStore(ItemLink):
    """Opens data directory in explorer."""
    _text = _('Open Folder…')
    _keyboard_hint = 'Ctrl+O'

    @property
    def link_help(self):
        return _("Open '%(data_store_path)s'.") % {
            'data_store_path': self._data_store.store_dir}

    def Execute(self): self.window.open_data_store()

class UIList_Hide(EnabledLink):
    """Hide the file (move it to the data store's Hidden directory)."""
    _text = _('Hide…')

    def _filter_unhideable(self, to_hide_items):
        """Filters out unhideable items from the specified iterable."""
        return self._data_store.filter_essential(to_hide_items)

    def _enable(self):
        # Only enable if at least one hideable file is selected
        return bool(self._filter_unhideable(self.selected))

    @property
    def link_help(self):
        sel_filtered = list(self._filter_unhideable(self.selected))
        if sel_filtered == self.selected:
            if len(sel_filtered) == 1:
                return _("Hide '%(filename)s' by moving it to the 'Hidden' "
                         "directory.") % {'filename': sel_filtered[0]}
            return _("Hide the selected items by moving them to the 'Hidden' "
                     "directory.")
        else:
            if sel_filtered:
                return _("Hide the selected items by moving them to the "
                         "'Hidden' directory (some of the selected items "
                         "cannot be hidden and will be skipped).")
            return _('The selected items cannot be hidden.')

    @conversation
    def Execute(self):
        if not bass.inisettings['SkipHideConfirmation']:
            message = _(u'Hide these files? Note that hidden files are simply '
                        u'moved to the %(hdir)s directory.') % (
                          {'hdir': self._data_store.hide_dir})
            if not self._askYes(message, _(u'Hide Files')): return
        self.window.hide(self._filter_unhideable(self.selected))
        self.window.propagate_refresh(Store.SAVES.DO())

class Installer_Op(ItemLink):
    """Common refresh logic for BAIN operations."""
    _prog_args = ()

    @conversation
    def Execute(self):
        ui_refresh = defaultdict(bool)
        try:
            with (Progress(*self._prog_args) if self._prog_args else
                  bolt.Progress() as progress):
                return self._perform_action(ui_refresh, progress)
        except (CancelError, SkipError):
            return None
        finally:
            self.window.propagate_refresh(ui_refresh)
            Link.Frame.distribute_warnings(ui_refresh)

    def _perform_action(self, ui_refresh_, progress):
        raise NotImplementedError

# wx Wrappers -----------------------------------------------------------------
#------------------------------------------------------------------------------
_wx_arrow_up = {wx.WXK_UP, wx.WXK_NUMPAD_UP}
wxArrowDown = {wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN}
wxArrows = _wx_arrow_up | wxArrowDown
wxReturn = {wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER}
_wx_delete = {wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE}

# Some UAC stuff --------------------------------------------------------------
def ask_uac_restart(message, mopy):
    if not TASK_DIALOG_AVAILABLE:
        message += '\n\n' + _('Start Wrye Bash with Administrator Privileges?')
        btns = ex = None
    else:
        admin = _('Run with Administrator Privileges')
        readme = readme_url(mopy) + '#trouble-permissions'
        btns = [(BTN_YES, f'+{admin}'), (BTN_NO, _('Run normally'))]
        switches = [_('Use one of the following command line switches:'), '',
                    _('%(cli_no_uac)s: always run normally'),
                    _('%(cli_uac)s: always run with Admin Privileges'), '',
                    _('See the %(readme)s for more information.')]
        ex = [_('How to avoid this message in the future'),
              _('Less information'), '\n'.join(switches) % {
                'cli_no_uac': '--no-uac', 'cli_uac': '--uac',
                'readme': f'<A href="{readme}">readme</A>'}]
    return askYes(None, message, title=_('UAC Protection'),
        vista_buttons=btns, expander=ex)

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
            self._contents.Freeze()
            try:
                # First calculate what we need to scroll to get to the top of
                # the window, then add the amount we'd have to scroll to get to
                # our target line to that
                top_scroll = -self._contents.GetScrollPos(wx.VERTICAL)
                self._contents.ScrollLines(top_scroll + iniLine)
            finally:
                self._contents.Thaw()
        event.Skip()

    def fit_column_to_header(self, column):
        self.SetColumnWidth(column, wx.LIST_AUTOSIZE_USEHEADER)

    def _get_selected_line(self, index): raise NotImplementedError

# Status bar ------------------------------------------------------------------
class BashStatusBar(DnDStatusBar):
    all_sb_links: dict = {} # all possible status bar links - visible or not
    obseButton = None # the OBSE button singleton
    icon_size = 8 # the size of the status bar icons - 8 is a special value

    def __init__(self, parent):
        super().__init__(parent)
        # we can't hotswitch the icon size, so we need to store it
        # +8 as each button has 4 px border on left and right
        self.__class__.icon_size = _settings['bash.statusbar.iconSize'] + 8
        self._native_widget.SetFieldsCount(3)
        self.buttons = {}  # populated with SBLinks whose gButtons is not None
        # when bash is run for the first time those are empty - set here
        order = _settings['bash.statusbar.order']
        hide = _settings['bash.statusbar.hide']
        # filter for non-existent ids and reorder the dict according to order
        hidden = {lid for lid in hide if lid in self.all_sb_links}
        hide.clear()
        hide.update(hidden)
        saved_order = {lid: li for lid in order if
                       (li := self.all_sb_links.get(lid))}
        # append new buttons and reorder BashStatusBar.all_sb_links
        self.all_sb_links = saved_order | self.all_sb_links
        order[:] = list(self.all_sb_links)  # set bash.statusbar.order
        # Add buttons in order that is saved
        for link_uid, link in self.all_sb_links.items():
            # Hidden?
            if link_uid in hide: continue
            # Add it, if allow_create allows it
            if link.native_init(self, on_drag_start=self._on_drag_start,
                on_drag_end=self._on_drag_end, on_drag=self._on_drag,
                on_drag_end_forced=self._on_drag_end_forced):
                self.buttons[link.uid] = link
        self._set_fields_size()
        ##: Why - 10? I just tried values until it looked good, why does
        # this one work best?
        self._native_widget.SetMinHeight(self._native_widget.FromDIP(
            self.icon_size - 10))
        self._draw_buttons()
        #--Setup Drag-n-Drop reordering
        self._reset_drag(False)
        self.moved = False

    def set_sb_text(self, status_text, field_dex, *, show_panel=False):
        super().set_sb_text(status_text, field_dex)
        if show_panel:
            self._set_fields_size()

    # Buttons drag and drop ---------------------------------------------------
    def _getButtonIndex(self, mouseEvent):
        native_button = mouseEvent.event_object_
        for i, button_link in enumerate(self.buttons.values()):
            if button_link._native_widget == native_button:
                x = mouseEvent.evt_pos[0]
                # position is 0 at the beginning of the button's _icon_
                # negative beyond that (on the left) and positive after
                if x < -4:
                    return max(i - 1, 0), button_link
                elif x > self.icon_size - 4:
                    return min(i + 1, len(self.buttons) - 1), button_link
                return i, button_link
        return wx.NOT_FOUND, None

    def _on_drag_start(self, mouse_evnt, _lb_dex_and_flags):
        self.dragging, button_link = self._getButtonIndex(mouse_evnt)
        if wx.Platform == '__WXMSW__':
            button_link._native_widget.CaptureMouse()
        return EventResult.FINISH # we don't skip blocks EVT_MOTION somehow

    def _on_drag_end_forced(self):
        self._reset_drag()
        # NOTE: Don't Skip, otherwise wxPython treats this event as unhandled,
        # and raises an exception.
        return EventResult.FINISH

    def _on_drag_end(self, mouse_evnt):
        __, button_link = self._getButtonIndex(mouse_evnt)
        if button_link._native_widget.HasCapture():
            button_link._native_widget.ReleaseMouse()
        if self.dragging != wx.NOT_FOUND:
            self._reset_drag()
            if self.moved:
                self.moved = False
                return EventResult.FINISH
            else:
                button_link.sb_click()

    def _reset_drag(self, set_cursor=True):
        self.dragStart = 0
        self.dragging = wx.NOT_FOUND
        if set_cursor: self.set_cursor()

    def _on_drag(self, mouse_evnt, _hittest0):
        if self.dragging != wx.NOT_FOUND:
            if abs(mouse_evnt.evt_pos[0] - self.dragStart) > 4:
                self.moved = True # just lost your chance to click the button
                self.set_cursor(hand=True)
            over, _ = self._getButtonIndex(mouse_evnt)
            button_link = next(islice(self.buttons.values(), self.dragging, None), None)
            if over not in (wx.NOT_FOUND, self.dragging):
                self.moved = True
                # update settings
                uid = button_link.uid
                overUid = self.buttons[[*self.buttons][over]].uid
                uid_order = _settings['bash.statusbar.order']
                overIndex = uid_order.index(overUid)
                uid_order.remove(uid)
                uid_order.insert(overIndex, uid)
                # resort self.buttons
                self._sort_buttons(uid_order)
                self.dragging = over
                # Refresh button positions
                self._draw_buttons()

    def _sort_buttons(self, uid_order):
        uid_order = {k: j for j, k in enumerate(uid_order)}
        self.buttons = {k: self.buttons[k] for k in
                        sorted(self.buttons, key=uid_order.get)}

    def _draw_buttons(self):
        rect = self._native_widget.GetFieldRect(0)
        xPos, yPos = rect.x + self._native_widget.FromDIP(4), rect.y
        button_spacing = self._native_widget.FromDIP(self.icon_size)
        for button_link in self.buttons.values():
            button_link.component_position = (xPos, yPos)
            xPos += button_spacing

    def toggle_buttons_visible(self, hide_ids=(), unhide_ids=()):
        """Toggle the visibility of the specified buttons."""
        hidden_buttons = _settings['bash.statusbar.hide']
        order = _settings['bash.statusbar.order']
        sort_buttons = False
        for link_uid in unhide_ids:
            hidden_buttons.discard(link_uid)
            link = self.all_sb_links[link_uid]
            if not link.native_init(self, recreate=False,
                    on_drag_start=self._on_drag_start,
                    on_drag_end=self._on_drag_end, on_drag=self._on_drag,
                    on_drag_end_forced=self._on_drag_end_forced):
                if not link.allow_create():
                    deprint(f'requested to create non existent button {link}')
                    continue
                link.visible = True  # button was already created and hidden
            self.buttons[link_uid] = link
            # Find the position to insert it at
            if link_uid not in order:
                # Not specified, put it at the end
                order.append(link_uid)
            else:
                sort_buttons = True
        if sort_buttons: self._sort_buttons(order)
        for link_uid in hide_ids:
            try:
                self.buttons[link_uid].visible = False
                del self.buttons[link_uid]
                hidden_buttons.add(link_uid)
            except KeyError: pass # should not happen
        self._set_fields_size()
        self._draw_buttons()

    def _set_fields_size(self):
        text_length_px = self._native_widget.GetTextExtent(
            self._native_widget.GetStatusText(2)).width
        # +10 is necessary to make the entire text fit without it getting
        # ellipsized on GTK/OSX, but not on MSW
        if wx.Platform != '__WXMSW__':
            text_length_px += 10
        self._native_widget.SetStatusWidths(
            [self._native_widget.FromDIP(self.icon_size) * len(self.buttons),
             -1, text_length_px])

    @classmethod
    def set_tooltips(cls):
        """Reset the tooltips of all *created* items, even hidden ones."""
        for button in cls.all_sb_links.values():
            button.tooltip = button.sb_button_tip

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
