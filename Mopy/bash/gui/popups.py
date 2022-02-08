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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2022 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""A popup is a small dialog that asks the user for a single piece of
information, e.g. a string, a number or just confirmation."""

import wx as _wx

from .base_components import _AComponent
from .buttons import Button, CancelButton, DeselectAllButton, SelectAllButton
from .checkables import CheckBox
from .functions import staticBitmap # yuck
from .layouts import CENTER, HLayout, LayoutOptions, Stretch, VLayout
from .misc_components import HorizontalLine
from .multi_choices import CheckListBox
from .text_components import Label, SearchBar, TextAlignment
from .top_level_windows import DialogWindow
from ..bolt import dict_sort
from ..bolt import GPath ##: remove this it's for file dialogs
from ..exception import AbstractError

class CopyOrMovePopup(DialogWindow): ##: wx.PopupWindow?
    """A popup that allows the user to choose between moving or copying a file
    and also includes a checkbox for remembering the choice in the future."""
    title = _(u'Move or Copy?')
    _def_size = _min_size = (450, 175)

    def __init__(self, parent, message, sizes_dict):
        super(CopyOrMovePopup, self).__init__(parent, sizes_dict=sizes_dict)
        self._ret_action = u''
        self._gCheckBox = CheckBox(self, _(u"Don't show this in the future."))
        move_button = Button(self, btn_label=_(u'Move'))
        move_button.on_clicked.subscribe(lambda: self._return_action(u'MOVE'))
        copy_button = Button(self, btn_label=_(u'Copy'), default=True)
        copy_button.on_clicked.subscribe(lambda: self._return_action(u'COPY'))
        VLayout(border=6, spacing=6, item_expand=True, items=[
            HLayout(spacing=6, item_border=6, items=[
                (staticBitmap(self), LayoutOptions(v_align=CENTER)),
                (Label(self, message), LayoutOptions(expand=True))
            ]),
            Stretch(),
            HorizontalLine(self),
            HLayout(spacing=4, item_expand=True, items=[
                self._gCheckBox, Stretch(), move_button, copy_button,
                CancelButton(self),
            ]),
        ]).apply_to(self)

    def _return_action(self, new_ret):
        """Callback for the move/copy buttons."""
        self._ret_action = new_ret
        self.accept_modal()

    def show_modal(self):
        """Return the choice the user made (either the string 'MOVE' or the
        string 'COPY') and whether that choice should be remembered."""
        result = super(CopyOrMovePopup, self).show_modal()
        return result and self._ret_action, self._gCheckBox.is_checked

class _TransientPopup(_AComponent):
    """Base class for transient popups, i.e. popups that disappear as soon as
    they lose focus."""
    _wx_widget_type = _wx.PopupTransientWindow

    def __init__(self, parent):
        # Note: the style (second parameter) may not be passed as a keyword
        # argument to this wx class for whatever reason
        super(_TransientPopup, self).__init__(
            parent, _wx.BORDER_SIMPLE | _wx.PU_CONTAINS_CONTROLS)

    def show_popup(self, popup_pos): # type: (tuple) -> None
        """Shows this popup at the specified position on the screen."""
        self._native_widget.Position(popup_pos, (0, 0))
        self._native_widget.Popup()

class MultiChoicePopup(_TransientPopup):
    """A transient popup that shows a list of checkboxes with a search bar. To
    implement special behavior when an item is checked or unchecked, you have
    to override the on_item_checked and on_mass_select methods."""
    def __init__(self, parent, all_choices, help_text=u'', aa_btn_tooltip=u'',
                 ra_btn_tooltip=u''):
        """Creates a new MultiChoicePopup with the specified parameters.

        :param parent: The object that this popup belongs to. May be a wx
            object or a component.
        :param all_choices: A dict mapping item names to booleans indicating
            whether or not that item is currently checked.
        :type all_choices: dict[str, bool]
        :param help_text: A static help text to show at the top of the popup
            (optional).
        :param aa_btn_tooltip: A tooltip to show when hovering over the 'Add
            All' button (optional).
        :param ra_btn_tooltip: A tooltip to show when hovering over the 'Remove
            All' button (optional)."""
        super(MultiChoicePopup, self).__init__(parent)
        self._all_choices = list(dict_sort(all_choices))
        choice_search = SearchBar(self)
        choice_search.on_text_changed.subscribe(self._search_choices)
        choice_search.set_focus()
        self._choice_box = CheckListBox(self)
        self._choice_box.on_box_checked.subscribe(self._handle_item_checked)
        select_all_btn = SelectAllButton(self, _(u'Add All'),
                                         btn_tooltip=aa_btn_tooltip)
        select_all_btn.on_clicked.subscribe(self._select_all_choices)
        deselect_all_btn = DeselectAllButton(self, _(u'Remove All'),
                                             btn_tooltip=ra_btn_tooltip)
        deselect_all_btn.on_clicked.subscribe(self._deselect_all_choices)
        # Start with everything shown -> empty search string
        self._search_choices(search_str=u'')
        help_label = Label(self, help_text, alignment=TextAlignment.CENTER)
        VLayout(border=6, spacing=4, item_expand=True, items=[
            help_label if help_text else None, choice_search, self._choice_box,
            HLayout(spacing=4, item_expand=True, items=[
                Stretch(), select_all_btn, deselect_all_btn, Stretch(),
            ]),
        ]).apply_to(self, fit=True)

    def _select_all_choices(self):
        """Internal callback for the Select All button."""
        self._choice_box.set_all_checkmarks(checked=True)
        self.on_mass_select(curr_choices=self._choice_box.lb_get_str_items(),
                            choices_checked=True)

    def _deselect_all_choices(self):
        """Internal callback for the Deselect All button."""
        self._choice_box.set_all_checkmarks(checked=False)
        self.on_mass_select(curr_choices=self._choice_box.lb_get_str_items(),
                            choices_checked=False)

    def _search_choices(self, search_str):
        """Internal callback for searching via the search bar."""
        search_lower = search_str.strip().lower()
        choices_dict = {k: v for k, v in self._all_choices if
                        search_lower in k.lower()}
        self._choice_box.set_all_items(choices_dict)

    def _handle_item_checked(self, choice_index):
        """Internal callback for checking or unchecking an item, forwards to
        the abstract on_item_checked method."""
        choice_name = self._choice_box.lb_get_str_item_at_index(choice_index)
        choice_checked = self._choice_box.lb_is_checked_at_index(choice_index)
        self.on_item_checked(choice_name, choice_checked)

    def on_item_checked(self, choice_name, choice_checked):
        # type: (str, bool) -> None
        """Called when a single item has been checked or unchecked."""
        raise AbstractError(u'on_item_checked not implemented')

    def on_mass_select(self, curr_choices, choices_checked):
        # type: (list, bool) -> None
        """Called when multiple items have been checked or unchecked."""
        raise AbstractError(u'on_mass_select not implemented')

# File Dialogs ----------------------------------------------------------------
class _FileDialog(_AComponent):
    """Ask user for a filesystem path using the system dialogs."""
    _wx_widget_type = _wx.FileDialog
    _dialog_style = _wx.FD_OPEN | _wx.FD_FILE_MUST_EXIST

    def __init__(self, parent, title=u'', defaultDir=u'', defaultFile=u'',
                 wildcard=u'', allow_create=False):
        defaultDir,defaultFile = [GPath(x).s for x in (defaultDir,defaultFile)]
        style_ = self.__class__._dialog_style
        if allow_create and style_ & _wx.FD_FILE_MUST_EXIST:
            style_ ^= _wx.FD_FILE_MUST_EXIST
        super(_FileDialog, self).__init__(parent, title, defaultDir,
                                          defaultFile, wildcard, style=style_)

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): self.destroy_component()

    @classmethod
    def display_dialog(cls, *args, **kwargs):
        """Instantiate a dialog, display it and return the ShowModal result."""
        with cls(*args, **kwargs) as dialog:
            if dialog._native_widget.ShowModal() != _wx.ID_OK:
                return False
            return dialog._validate_input()

    def _validate_input(self):
        return GPath(self._native_widget.GetPath())

class FileOpen(_FileDialog):
    """'Open file' dialog."""

class FileOpenMultiple(_FileDialog):
    """'Open files' dialog that returns a *list* of files to open."""
    _dialog_style = _wx.FD_OPEN | _wx.FD_MULTIPLE | _wx.FD_FILE_MUST_EXIST

    def __init__(self, parent, title=u'', defaultDir=u'', defaultFile=u'',
                 wildcard=u''): ##:mustExist seems True given the FD_FILE_MUST_EXIST?
        super(FileOpenMultiple, self).__init__(parent, title, defaultDir,
                                               defaultFile, wildcard)

    def _validate_input(self):
        return [GPath(p) for p in self._native_widget.GetPaths()]

class FileSave(_FileDialog):
    """'Save as' dialog."""
    _dialog_style = _wx.FD_SAVE | _wx.FD_OVERWRITE_PROMPT

class DirOpen(_FileDialog):
    """'Open directory' dialog."""
    _wx_widget_type = _wx.DirDialog
    _dialog_style = _wx.DD_DEFAULT_STYLE | _wx.DD_SHOW_HIDDEN

    def __init__(self, parent, title=u'', defaultPath=u'', create_dir=False):
        st = self.__class__._dialog_style
        st |= _wx.DD_NEW_DIR_BUTTON if create_dir else _wx.DD_DIR_MUST_EXIST
        super(_FileDialog, self).__init__(parent, title, '%s' % defaultPath,
                                          style=st)
