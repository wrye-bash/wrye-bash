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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
"""A popup is a small dialog that asks the user for a single piece of
information, e.g. a string, a number or just confirmation."""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from functools import partial
from typing import Any

import wx as _wx

from .base_components import Color, _AComponent
from .buttons import Button, CancelButton, DeselectAllButton, ImageButton, \
    OkButton, PureImageButton, SelectAllButton
from .checkables import CheckBox
from .layouts import CENTER, HLayout, LayoutOptions, Stretch, VBoxedLayout, \
    VLayout
from .misc_components import DatePicker, HorizontalLine, TimePicker
from .multi_choices import CheckListBox
from .text_components import Label, SearchBar, TextAlignment, TextField, \
    WrappingLabel
from .top_level_windows import DialogWindow
##: Remove GPath, it's for file dialogs
from ..bolt import GPath, dict_sort
from ..exception import AbstractError

class CopyOrMovePopup(DialogWindow):
    """A popup that allows the user to choose between moving or copying a file
    and also includes a checkbox for remembering the choice in the future."""
    title = _(u'Move or Copy?')
    _def_size = _min_size = (450, 175)

    def __init__(self, parent, message, *, sizes_dict, icon_bundle):
        super().__init__(parent, sizes_dict=sizes_dict,
            icon_bundle=icon_bundle)
        ##: yuck, decouple!
        from ..balt import staticBitmap
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

    def show_modal(self) -> tuple[bool | str, bool]:
        """Return the choice the user made (either the string 'MOVE' or the
        string 'COPY') and whether that choice should be remembered."""
        result = super().show_modal()
        return result and self._ret_action, self._gCheckBox.is_checked

class _TransientPopup(_AComponent):
    """Base class for transient popups, i.e. popups that disappear as soon as
    they lose focus."""
    _native_widget: _wx.PopupTransientWindow

    def __init__(self, parent):
        # Note: the style (second parameter) may not be passed as a keyword
        # argument to this wx class for whatever reason
        super().__init__(parent, _wx.BORDER_SIMPLE | _wx.PU_CONTAINS_CONTROLS)

    def show_popup(self, popup_pos: tuple[int, int]):
        """Shows this popup at the specified position on the screen."""
        self._native_widget.Position(popup_pos, (0, 0))
        self._native_widget.Popup()

class MultiChoicePopup(_TransientPopup):
    """A transient popup that shows a list of checkboxes with a search bar. To
    implement special behavior when an item is checked or unchecked, you have
    to override the on_item_checked and on_mass_select methods."""
    def __init__(self, parent, *, all_choices: dict[str, bool], help_text='',
            aa_btn_tooltip='', ra_btn_tooltip=''):
        """Creates a new MultiChoicePopup with the specified parameters.

        :param parent: The object that this popup belongs to. May be a wx
            object or a component.
        :param all_choices: A dict mapping item names to booleans indicating
            whether or not that item is currently checked.
        :param help_text: A static help text to show at the top of the popup
            (optional).
        :param aa_btn_tooltip: A tooltip to show when hovering over the 'Add
            All' button (optional).
        :param ra_btn_tooltip: A tooltip to show when hovering over the 'Remove
            All' button (optional)."""
        super().__init__(parent)
        self._all_choices = dict(dict_sort(all_choices))
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
        self._mass_select_shared(choices_checked=True)

    def _deselect_all_choices(self):
        """Internal callback for the Deselect All button."""
        self._mass_select_shared(choices_checked=False)

    def _mass_select_shared(self, *, choices_checked: bool):
        """Shared code of _select_all_choices and _deselect_all_choices."""
        self._choice_box.set_all_checkmarks(checked=choices_checked)
        curr_choice_strs = self._choice_box.lb_get_str_items()
        # Remember this for when we update the choice box contents via search
        for choice_str in curr_choice_strs:
            self._all_choices[choice_str] = choices_checked
        self.on_mass_select(curr_choices=curr_choice_strs,
                            choices_checked=choices_checked)

    def _search_choices(self, search_str):
        """Internal callback for searching via the search bar."""
        search_lower = search_str.strip().lower()
        choices_dict = {k: v for k, v in self._all_choices.items() if
                        search_lower in k.lower()}
        self._choice_box.set_all_items(choices_dict)

    def _handle_item_checked(self, choice_index):
        """Internal callback for checking or unchecking an item, forwards to
        the abstract on_item_checked method."""
        choice_name = self._choice_box.lb_get_str_item_at_index(choice_index)
        choice_checked = self._choice_box.lb_is_checked_at_index(choice_index)
        # Remember this for when we update the choice box contents via search
        self._all_choices[choice_name] = choice_checked
        self.on_item_checked(choice_name, choice_checked)

    def on_item_checked(self, choice_name: str, choice_checked: bool):
        """Called when a single item has been checked or unchecked."""
        raise AbstractError('on_item_checked not implemented')

    def on_mass_select(self, curr_choices: list[str], choices_checked: bool):
        """Called when multiple items have been checked or unchecked."""
        raise AbstractError('on_mass_select not implemented')

# File Dialogs ----------------------------------------------------------------
class _FileDialog(_AComponent):
    """Ask user for a filesystem path using the system dialogs."""
    _native_widget: _wx.FileDialog
    _dialog_style = _wx.FD_OPEN | _wx.FD_FILE_MUST_EXIST

    def __init__(self, parent, title='', defaultDir='', defaultFile='',
                 wildcard='', allow_create=False):
        defaultDir, defaultFile = map(str, (defaultDir, defaultFile))
        style_ = self.__class__._dialog_style
        if allow_create and style_ & _wx.FD_FILE_MUST_EXIST:
            style_ ^= _wx.FD_FILE_MUST_EXIST
        super().__init__(parent, title, defaultDir, defaultFile, wildcard,
                         style=style_)

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

    def __init__(self, parent, title='', defaultDir='', defaultFile='',
                 wildcard=''): ##:mustExist seems True given the FD_FILE_MUST_EXIST?
        super().__init__(parent, title, defaultDir, defaultFile, wildcard)

    def _validate_input(self):
        return [GPath(p) for p in self._native_widget.GetPaths()]

class FileSave(_FileDialog):
    """'Save as' dialog."""
    _dialog_style = _wx.FD_SAVE | _wx.FD_OVERWRITE_PROMPT

class DirOpen(_FileDialog):
    """'Open directory' dialog."""
    _native_widget: _wx.DirDialog
    _dialog_style = _wx.DD_DEFAULT_STYLE | _wx.DD_SHOW_HIDDEN

    def __init__(self, parent, title='', defaultPath='', create_dir=False):
        st = self.__class__._dialog_style
        st |= _wx.DD_NEW_DIR_BUTTON if create_dir else _wx.DD_DIR_MUST_EXIST
        # we call _FileDialog parent in mro so we need to stringify defaultPath
        super(_FileDialog, self).__init__(parent, title, '%s' % defaultPath,
                                          style=st)

# Deletion --------------------------------------------------------------------
class DeletionDialog(DialogWindow):
    """A popup for choosing what to delete from a list of items. Allows the
    user to uncheck items and choose whether or not to recycle them."""
    _def_size = (290, 250)
    _min_size = (290, 150)

    def __init__(self, parent, *, title: str,
            items_to_delete: list[str], default_recycle: bool,
            sizes_dict, icon_bundle, trash_icon):
        """Initializes a new DeletionDialog.

        :param items_to_delete: A list of strings representing the items that
            can be deleted.
        :param default_recycle: Whether the 'Recycle' checkbox should be
            checked by default or not."""
        super().__init__(parent, sizes_dict=sizes_dict, title=title,
            icon_bundle=icon_bundle)
        ##: yuck, decouple!
        from ..balt import staticBitmap
        self._deletable_items = CheckListBox(self, choices=items_to_delete)
        self._deletable_items.set_all_checkmarks(checked=True)
        self._recycle_checkbox = CheckBox(self, _('Recycle'),
            checked=default_recycle, chkbx_tooltip=_(
                'Whether to move deleted items to the recycling bin or '
                'permanently delete them.'))
        self._recycle_checkbox.on_checked.subscribe(self._on_recycle_checked)
        self._question_label = WrappingLabel(self, self._get_question_msg())
        uncheck_label = WrappingLabel(self, _('Uncheck items to skip deleting '
                                              'them if desired.'))
        self._delete_button = OkButton(self, self._get_button_text())
        VLayout(border=6, spacing=4, item_expand=True, items=[
            HLayout(spacing=4, item_expand=True, items=[
                staticBitmap(self, trash_icon),
                (VLayout(spacing=4, item_expand=True, items=[
                    self._question_label,
                    HorizontalLine(self),
                    uncheck_label,
                ]), LayoutOptions(weight=1)),
            ]),
            (self._deletable_items, LayoutOptions(weight=1)),
            HLayout(item_expand=True, items=[
                self._recycle_checkbox,
                Stretch(),
                self._delete_button,
                CancelButton(self),
            ]),
        ]).apply_to(self)
        # Wrap our WrappingLabels afterwards and update the layout to match
        uncheck_label.auto_wrap()
        self._question_label.auto_wrap()
        self.update_layout()

    def _get_question_msg(self):
        """Helper method to get the right question message to show at the top
        of the dialog."""
        return (_('Delete these items to the recycling bin?')
                if self._recycle_checkbox.is_checked else
                _('Permanently delete these items? This operation cannot be '
                  'undone!'))

    def _get_button_text(self):
        """Helper method to get the right text to show on the OK button."""
        return (_('Delete') if self._recycle_checkbox.is_checked else
                _('Delete Permanently'))

    def _on_recycle_checked(self, _checked):
        """Internal callback for updating the dialog contents whenever the
        recycling checkbox is changed."""
        self._question_label.label_text = self._get_question_msg()
        self._delete_button.button_label = self._get_button_text()
        self.update_layout()

    def show_modal(self) -> tuple[bool, tuple[str, ...], bool]:
        """Return whether the OK button or Cancel button was pressed, the
        items to be deleted as a tuple of strings and whether the recycling
        checkbox was ticked or not."""
        result = super().show_modal()
        chosen_strings = self._deletable_items.get_checked_strings()
        chosen_recycle = self._recycle_checkbox.is_checked
        return result, chosen_strings, chosen_recycle

# Date and Time ---------------------------------------------------------------
class DateAndTimeDialog(DialogWindow):
    """Dialog for choosing a date and time."""
    title = _('Choose a date and time')
    _def_size = (270, 360)

    def __init__(self, parent, *, warning_color: Color, icon_bundle):
        super().__init__(parent, icon_bundle=icon_bundle)
        self._warning_color = warning_color
        self._date_picker = DatePicker(self)
        # We need to turn this into a POSIX timestamp later
        self._date_picker.set_posix_range()
        self._date_picker.on_picker_changed.subscribe(self._handle_picker)
        self._time_picker = TimePicker(self)
        self._time_picker.on_picker_changed.subscribe(self._handle_picker)
        self._manual_entry = TextField(self)
        self._manual_entry.on_text_changed.subscribe(self._handle_manual)
        # Call this once to set the initial text in the manual entry field
        self._handle_picker()
        self._manual_layout = VBoxedLayout(self, _('Manual (valid)'),
            item_expand=True, items=[self._manual_entry])
        self._ok_button = OkButton(self)
        VLayout(border=6, spacing=4, item_expand=True, items=[
            VBoxedLayout(self, _('Date'), items=[
                (self._date_picker, LayoutOptions(h_align=CENTER)),
            ]),
            VBoxedLayout(self, _('Time'), items=[
                (self._time_picker, LayoutOptions(h_align=CENTER)),
            ]),
            self._manual_layout,
            Stretch(),
            HorizontalLine(self),
            HLayout(item_expand=True, items=[
                Stretch(),
                self._ok_button,
                CancelButton(self),
            ]),
        ]).apply_to(self)

    def _handle_picker(self):
        """Internal callback that updates the manual entry field whenever a
        picker is used."""
        with self._manual_entry.on_text_changed.pause_subscription(
                self._handle_manual): # Avoid getting into a loop
            picker_datetime = datetime.datetime.combine(
                self._date_picker.get_date(), self._time_picker.get_time())
            self._manual_entry.text_content = picker_datetime.strftime('%c')

    def _handle_manual(self, new_manual_dt_str):
        """Internal callback that updates the pickers whenever the manual entry
        field has been edited to contain a valid date and time."""
        try:
            # This will raise ValueError if the format does not match
            new_datetime = datetime.datetime.strptime(new_manual_dt_str, '%c')
            # This will raise OSError if the datetime cannot be turned into a
            # POSIX timestamp
            new_datetime.timestamp()
        except (OSError, ValueError):
            # User entered an incorrect date and time, let them know and
            # prevent accepting the dialog
            self._manual_layout.set_title(_('Manual (invalid)'))
            self._manual_layout.set_title_color(self._warning_color)
            self._ok_button.enabled = False
            return
        # User entered a correct date and time, allow accepting the dialog
        # again
        self._manual_layout.set_title(_('Manual (valid)'))
        self._manual_layout.reset_title_color()
        self._ok_button.enabled = True
        # Pausing picker subscription here is not currently necessary, but may
        # become necessary in the future, so stay sharp
        self._date_picker.set_date(new_datetime.date())
        self._time_picker.set_time(new_datetime.time())

    def show_modal(self) -> tuple[bool, datetime.datetime]:
        """Return whether the OK button or Cancel button was pressed and the
        final chosen date and time as a datetime.datetime object."""
        result = super().show_modal()
        manual_datetime = datetime.datetime.strptime(
            self._manual_entry.text_content, '%c')
        return result, manual_datetime

# Misc ------------------------------------------------------------------------
@dataclass(slots=True)
class MLEList:
    """Represents a single list shown in a multi-list editor."""
    # The title of the list. Shown above the description and items.
    mlel_title: str
    # A description of what this list represents or advice regarding what to do
    # with this list. Shown above the items.
    mlel_desc: str
    # A list of items in the list. Will be shown in the order they are passed
    # in, so you may want to sort them first.
    mlel_items: list[str]

class AMultiListEditor(DialogWindow):
    """Base class for a multi-list editor. Useful if you want to show a user
    one or more lists, where they may check or uncheck items in those lists.
    You have to subclass this and pass in appropriate arguments (see __init__
    below). That way we also get a unique __class__.__name__ for the settings
    key."""
    _min_size = (300, 400)

    def __init__(self, parent, *, data_desc: str, list_data: list[MLEList],
            check_uncheck_bitmaps, sizes_dict, icon_bundle, start_checked=True,
            ok_label=_('OK'), cancel_label=_('Cancel')):
        """Initializes a new AMultiListEditor.

        :param data_desc: A description that will be shown at the top of the
            resulting dialog.
        :param list_data: A list specifying the lists that can be edited via
            this dialog. See MLEList for more information.
        :param check_uncheck_bitmaps: A tuple of _wx.Bitmaps for the
            check/uncheck buttons. Order is checked, unchecked.
        :param start_checked: Optional. If True, start with all items checked.
            If False, start with all items unchecked. True by default.
        :param ok_label: Optional. The label to show on the OK button. 'OK' by
            default.
        :param cancel_label: Optional. The label to show on the Cancel button.
            'Cancel' by default."""
        super().__init__(parent, sizes_dict=sizes_dict,
            icon_bundle=icon_bundle)
        # Stores the state of the edited data in each list
        self._wip_list_data = [{i: True for i in m.mlel_items}
                               for m in list_data]
        self._editor_clbs = []
        clb_items = []
        all_wrapping_labels = []
        for i, mle_list in enumerate(list_data):
            # Skip showing any list editors for lists without items. However,
            # we do still want to return them in show_modal for ease of use
            if not mle_list.mlel_items:
                # To keep indices identical between _editor_clbs and
                # _wip_list_data
                self._editor_clbs.append(None)
                continue
            mle_clb = CheckListBox(self, choices=mle_list.mlel_items)
            mle_clb.set_all_checkmarks(checked=start_checked)
            mle_clb.on_box_checked.subscribe(partial(
                self._handle_box_checked, i))
            self._editor_clbs.append(mle_clb)
            title_label = WrappingLabel(self, mle_list.mlel_title)
            clb_items.append(title_label)
            all_wrapping_labels.append(title_label)
            desc_label = WrappingLabel(self, mle_list.mlel_desc)
            clb_items.append(desc_label)
            all_wrapping_labels.append(desc_label)
            # Put the check/uncheck buttons right before the search bar
            search_layout = HLayout(item_expand=True, spacing=4)
            check_all_btn = PureImageButton(self, check_uncheck_bitmaps[0],
                btn_tooltip=_('Check all currently visible items.'))
            check_all_btn.on_clicked.subscribe(partial(
                self._handle_mass_check, i, True))
            search_layout.add(check_all_btn)
            uncheck_all_btn = PureImageButton(self, check_uncheck_bitmaps[1],
                btn_tooltip=_('Uncheck all currently visible items.'))
            uncheck_all_btn.on_clicked.subscribe(partial(
                self._handle_mass_check, i, False))
            search_layout.add(uncheck_all_btn)
            mle_sb = SearchBar(self)
            mle_sb.on_text_changed.subscribe(partial(
                self._handle_editor_search, i))
            # The search bar should take up all remaining horizontal space
            search_layout.add((mle_sb, LayoutOptions(weight=1)))
            clb_items.append(search_layout)
            # And last goes the CheckListBox, which should tkae up all
            # remaining vertical space
            clb_items.append((mle_clb, LayoutOptions(weight=1)))
        data_desc_label = WrappingLabel(self, data_desc)
        all_wrapping_labels.append(data_desc_label)
        VLayout(border=6, spacing=4, item_expand=True, items=[
            data_desc_label,
            HorizontalLine(self),
            *clb_items,
            HLayout(spacing=4, item_expand=True, items=[
                Stretch(),
                OkButton(self, ok_label),
                CancelButton(self, cancel_label),
            ]),
        ]).apply_to(self)
        for wl in all_wrapping_labels:
            wl.auto_wrap()
        self.update_layout()

    def _handle_box_checked(self, list_data_index: int, box_index: int):
        """Internal callback, called whenever a checkbox is checked or
        unchecked. Updates the internal state tracking dict to keep track of
        checking/unchecking."""
        curr_clb = self._editor_clbs[list_data_index]
        now_checked = curr_clb.lb_is_checked_at_index(box_index)
        checked_item = curr_clb.lb_get_str_item_at_index(box_index)
        self._wip_list_data[list_data_index][checked_item] = now_checked

    def _handle_editor_search(self, list_data_index: int, search_str: str):
        """Internal callback, called whenever text is entered into a seach bar.
        Updates the contents of the affected CheckListBox to match."""
        lower_search_str = search_str.strip().lower()
        mle_item_state = self._wip_list_data[list_data_index]
        searched_items = {i: mle_item_state[i] for i in mle_item_state
                          if lower_search_str in i.lower()}
        self._editor_clbs[list_data_index].set_all_items(searched_items)

    def _handle_mass_check(self, list_data_index: int, checked_state: bool):
        """Internal callback, called whenever a Check All or Uncheck All button
        is pressed. Checks or unchecks all currently visible items."""
        curr_clb = self._editor_clbs[list_data_index]
        # This does not end up calling _handle_box_checked, so no need to
        # pause that subscription
        curr_clb.set_all_checkmarks(checked=checked_state)
        curr_wip_data = self._wip_list_data[list_data_index]
        for wip_item in curr_clb.lb_get_str_items():
            curr_wip_data[wip_item] = checked_state

    ##: Return type should be tuple[bool, list[str], ...] (I think), but
    # PyCharm complains about that
    def show_modal(self) -> tuple[bool, Any]:
        """Return whether the OK button or Cancel button was pressed and one or
        more lists of strings, where each list of strings corresponds to the
        selected items from the nth list in the editor."""
        result = super().show_modal()
        # Compile only the checked items into the resulting lists
        final_lists = [
            [mli for mli, mli_checked in mle_list_data.items() if mli_checked]
            for mle_list_data in self._wip_list_data]
        return result, *final_lists
