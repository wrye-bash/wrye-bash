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
"""A popup is a small dialog that asks the user for a single piece of
information, e.g. a string, a number or just confirmation."""

from .buttons import Button, CancelButton
from .checkables import CheckBox
from .layouts import CENTER, HLayout, LayoutOptions, Stretch, VLayout
from .misc_components import HorizontalLine, staticBitmap # yuck
from .text_components import Label
from .top_level_windows import DialogWindow

class CopyOrMovePopup(DialogWindow):
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

    def get_action(self):
        """Returns the choice the user made. Either the string 'MOVE' or the
        string 'COPY'."""
        return self._ret_action

    def should_remember(self):
        """Returns True if the choice the user made should be remembered."""
        return self._gCheckBox.is_checked
