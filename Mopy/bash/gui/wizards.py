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
"""High level API for implementing wizard dialogs."""

import wx as _wx

from .buttons import BackButton, CancelButton, NextButton, OkButton
from .misc_components import HorizontalLine
from .layouts import HLayout, LayoutOptions, Stretch, VLayout
from .top_level_windows import DialogWindow, PanelWin
from ..exception import AbstractError

class WizardDialog(DialogWindow):
    """A wizard dialog, which can show multiple WizardPage instances."""
    title = _(u'Wizard')

    def __init__(self, parent, **kwargs):
        super(WizardDialog, self).__init__(parent, style=_wx.MAXIMIZE_BOX,
                                           **kwargs)
        self._curr_page = self._dummy_page = WizardPage(self)
        self._sep_line = HorizontalLine(self)
        self._back_button = BackButton(self)
        self._back_button.on_clicked.subscribe(self._move_prev)
        # Create before the Next button! Otherwise it becomes the default.
        self._finish_button = OkButton(self, btn_label=_(u'Finish'))
        self._next_button = NextButton(self, default=True)
        self._next_button.on_clicked.subscribe(self._move_next)
        self._cancel_button = CancelButton(self)
        self._cancel_button.on_clicked.subscribe(self._cancel_wizard)
        self._wiz_layout = VLayout(item_expand=True, item_border=4, items=[
            (self._curr_page, LayoutOptions(weight=1)), self._sep_line,
            HLayout(item_expand=True, item_border=4, items=[
                Stretch(), self._back_button, self._next_button,
                self._finish_button, self._cancel_button,
            ]),
        ])
        self._wiz_layout.apply_to(self)

    def on_closing(self, destroy=True):
        if destroy:
            # We were closed via the dialog 'X' button, mark the wizard as
            # canceled in this case too
            self._cancel_wizard()
        super(WizardDialog, self).on_closing(destroy)

    def _refresh_buttons(self):
        """Enables or disables and hides or unhides buttons based on whether or
        not there are pages to go to in either direction. You can override this
        if you want to enable or disable buttons under other conditions."""
        self._back_button.enabled = self._has_prev_page()
        can_move_next = self._has_next_page()
        self._next_button.visible = can_move_next
        self._finish_button.visible = not can_move_next
        # If the finish button is now visible, focus it
        if not can_move_next:
            self._finish_button.set_focus()

    def _change_page(self, new_page):
        """Changes the page that the wizard is currently on to the specified
        WizardPage instance.

        :type new_page: WizardPage"""
        self._wiz_layout.replace_component(self._curr_page, new_page)
        self._curr_page.destroy_component()
        self._curr_page = new_page

    def _move_next(self):
        """Moves to the next page in the wizard."""
        if self._has_next_page():
            self._change_page(self._get_next_page())
            self._refresh_buttons()
            self.update_layout()

    def _move_prev(self):
        """Moves to the previous page in the wizard."""
        if self._has_prev_page():
            self._change_page(self._get_prev_page())
            self._refresh_buttons()
            self.update_layout()

    def _run_wizard(self):
        """Runs this wizard and block until it is done."""
        if not self._has_next_page():
            return # no pages, exit immediately
        self._move_next()
        self.show_modal()

    def get_page_size(self):
        """Returns the width and height that each page in the wizard will
        have available, in device-independent pixels (DIP)."""
        return self._curr_page.component_size

    # Abstract API
    def _has_next_page(self):
        """Returns True if there is a next page that the wizard can be moved
        to."""
        raise AbstractError(u'_has_next_page not implemented')

    def _has_prev_page(self):
        """Returns True if there is a previous page that the wizard can be
        moved to."""
        raise AbstractError(u'_has_prev_page not implemented')

    def _get_next_page(self):
        """Returns a WizardPage to move to next when moving forwards. Returns
        None if _has_next_page would return False right now, i.e. there is no
        next page to move to."""
        raise AbstractError(u'_get_next_page not implemented')

    def _get_prev_page(self):
        """Returns a WizardPage to move to next when moving backwards. Returns
        None if _has_prev_page would return False right now, i.e. there is no
        previous page to move to."""
        raise AbstractError(u'_get_prev_page not implemented')

    def _cancel_wizard(self):
        """Called when the wizard is cancelled via the Cancel button or via the
        'X' window button."""
        raise AbstractError(u'_cancel_wizard not implemented')

class WizardPage(PanelWin):
    """A single wizard page."""
