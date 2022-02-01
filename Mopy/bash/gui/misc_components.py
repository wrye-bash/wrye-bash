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
"""This module houses GUI classes that did not fit anywhere else. Once similar
classes accumulate in here, feel free to break them out into a module."""

__author__ = u'nycz, Infernio, Utumno'

import re
import wx as _wx
from wx.grid import Grid
from collections import defaultdict
from itertools import chain

from .base_components import _AComponent, Color, WithMouseEvents, \
    ImageWrapper, WithCharEvents
from .events import EventResult
from .functions import copy_text_to_clipboard, read_from_clipboard
from ..bolt import Path, dict_sort

class Font(_wx.Font):
    @staticmethod
    def Style(font_: _wx.Font, bold=False, slant=False, underline=False):
        if bold: font_.SetWeight(_wx.FONTWEIGHT_BOLD)
        else: font_.SetWeight(_wx.FONTWEIGHT_NORMAL)
        if slant: font_.SetStyle(_wx.FONTSTYLE_SLANT)
        else: font_.SetStyle(_wx.FONTSTYLE_NORMAL)
        font_.SetUnderlined(underline)
        return font_

# Pictures --------------------------------------------------------------------
class Picture(_AComponent):
    """Picture panel."""
    _wx_widget_type = _wx.Window

    def __init__(self, parent, width, height, scaling=1,  ##: scaling unused
                 style=_wx.BORDER_SUNKEN, background=_wx.MEDIUM_GREY_BRUSH):
        super(Picture, self).__init__(parent, size=(width, height),
                                      style=style)
        self._native_widget.SetBackgroundStyle(_wx.BG_STYLE_CUSTOM)
        self.bitmap = None
        self.background = self._get_brush(
            background or self._native_widget.GetBackgroundColour())
        #self.SetSizeHints(width,height,width,height)
        #--Events
        self._on_paint = self._evt_handler(_wx.EVT_PAINT)
        self._on_paint.subscribe(self._handle_paint)
        self._on_size = self._evt_handler(_wx.EVT_SIZE)
        self._on_size.subscribe(self._handle_resize)
        self._handle_resize()

    def SetBackground(self, background):
        self.background = self._get_brush(background)
        self._handle_resize()

    @staticmethod
    def _get_brush(background):
        if isinstance(background, Color):
            background = background.to_rgba_tuple()
        if isinstance(background, tuple):
            background = _wx.Colour(*background)
        if isinstance(background, _wx.Colour):
            background = _wx.Brush(background)
        return background

    def set_bitmap(self, bmp):
        """Set the bitmap on the native_widget and return the wx object for
        caching"""
        if isinstance(bmp, Path):
            bmp = (bmp.is_file() and ImageWrapper(bmp).get_bitmap()) or None
        self.bitmap = bmp
        self._handle_resize()
        return self.bitmap

    def _handle_resize(self): ##: is all these wx.Bitmap calls needed? One right way?
        x, y = self.scaled_size()
        if x <= 0 or y <= 0: return
        self.buffer = _wx.Bitmap(x,y)
        dc = _wx.MemoryDC()
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
            image.Rescale(int(new_x), int(new_y), _wx.IMAGE_QUALITY_HIGH)
            dc.DrawBitmap(_wx.Bitmap(image), pos_x, pos_y)
        del dc
        self._native_widget.Refresh()
        self._native_widget.Update()

    def _handle_paint(self):
        dc = _wx.BufferedPaintDC(self._native_widget, self.buffer)
        return EventResult.FINISH

class PictureWithCursor(Picture, WithMouseEvents):
    bind_lclick_double = bind_middle_up = True

    def set_bitmap(self, bmp):
        # Don't want the bitmap to resize until we call self.Layout()
        with self.pause_drawing():
            img = super(PictureWithCursor, self).set_bitmap(bmp)
            self._native_widget.SetCursor(
                _wx.Cursor(_wx.CURSOR_MAGNIFIER if img else _wx.CURSOR_ARROW))
        return img

# Lines -----------------------------------------------------------------------
class _ALine(_AComponent):
    """Abstract base class for simple graphical lines."""
    _line_style = None # override in subclasses
    _wx_widget_type = _wx.StaticLine

    def __init__(self, parent):
        super(_ALine, self).__init__(parent, style=self._line_style)

class HorizontalLine(_ALine):
    """A simple horizontal line."""
    _line_style = _wx.LI_HORIZONTAL

class VerticalLine(_ALine):
    """A simple vertical line."""
    _line_style = _wx.LI_VERTICAL

# Tables ----------------------------------------------------------------------
class Table(WithCharEvents):
    """A component that displays data in a tabular manner, with useful
    extensions like Ctrl+C/Ctrl+V support built in. Note that it was not built
    to allow customizing the row labels, one of its central assumptions is that
    they are always ints."""
    _wx_widget_type = Grid

    def __init__(self, parent, table_data, editable=True):
        """Creates a new Table with the specified parent and table data.

        :param parent: The object that this table belongs to. May be a wx
            object or a component.
        :param table_data: The data to show in the table. Maps column names to
            the data displayed in the column.
        :type table_data: dict[str, list[str]]
        :param editable: True if the user may edit the contents of the
            table."""
        super(Table, self).__init__(parent)
        # Verify that all columns are identically sized
        column_len = len(next(iter(table_data.values())))
        if any(len(column_data) != column_len for column_data
               in table_data.values()):
            raise SyntaxError(u'Table columns must all have the same size')
        if not all(table_data):
            raise SyntaxError(u'Table rows must be nonempty strings')
        # Create the Grid, then populate it from table_data
        # Note order here and below - row, col is correct for wx
        self._native_widget.CreateGrid(column_len, len(table_data))
        self._native_widget.EnableEditing(editable)
        self._label_to_col_index = {}
        for c, column_label in enumerate(table_data):
            self._label_to_col_index[column_label] = c
            self._native_widget.SetColLabelValue(c, column_label)
            for r, cell_label in enumerate(table_data[column_label]):
                self._native_widget.SetCellValue(r, c, cell_label)
        self._native_widget.AutoSize()
        self.on_key_up.subscribe(self._on_table_key_up)

    def _on_table_key_up(self, wrapped_evt):
        """Internal handler, implements copy and paste, select all, etc."""
        if wrapped_evt.is_cmd_down:
            kcode = wrapped_evt.key_code
            if kcode == ord(u'A'):
                if wrapped_evt.is_shift_down:
                    # Ctrl+Shift+A - unselect all cells
                    self._native_widget.ClearSelection()
                else:
                    # Ctrl+A - select all cells
                    for c in range(self._native_widget.GetNumberCols()):
                        self._native_widget.SelectCol(c, True)
            elif kcode == ord(u'C'):
                # Ctrl+C - copy contents of selected cells
                copy_text_to_clipboard(self._format_selected_cells(
                    self.get_selected_cells()))
            elif kcode == ord(u'V'):
                # Ctrl+V - paste contents of selected cells
                if not self._native_widget.IsEditable(): return
                parsed_clipboard = self._parse_clipboard_contents(
                    read_from_clipboard())
                if not parsed_clipboard:
                    from .. import balt # TODO(inf) de-wx! move this to gui
                    balt.showWarning(self, _(u'Could not parse the pasted '
                                             u'contents as a valid table.'))
                    return
                self.edit_cells(parsed_clipboard)
                self._native_widget.AutoSize()

    def _format_selected_cells(self, sel_cells):
        """Formats the output of get_selected_cells into a human-readable
        format."""
        if not sel_cells:
            # None selected, just return the currently focused cell's value
            return self.get_focused_cell()
        elif len(sel_cells) == 1:
            # Selection is limited to a single column, format as a
            # newline-separated list
            sorted_cells = dict_sort(next(iter(sel_cells.values())),
                                     key_f=lambda k: int(k))
            return u'\n'.join(t[1] for t in sorted_cells)
        else:
            # Here is where it gets ugly - we need to format a full table with
            # row/column separators, proper spacing and labels
            clip_text = []
            row_labels = set(chain.from_iterable(
                r for r in sel_cells.values()))
            col_labels = list(sel_cells) ##: do we need the list here?
            # First calculate the maximum label lengths we'll have to pad to
            max_row_length = max(map(len, row_labels))
            max_col_lengths = {}
            for col_label, col_cells in sel_cells.items():
                max_col_lengths[col_label] = max(
                    map(len, col_cells.values()))
            # We now have enough info to format the header, so do that
            first_header_line = u' ' * max_row_length + u' | '
            first_header_line += u' | '.join(l.ljust(max_col_lengths[l])
                                             for l in col_labels)
            second_header_line = u'-' * (max_row_length + 1) + u'+'
            second_header_line += u'+'.join(u'-' * (max_col_lengths[l] + 2)
                                            for l in col_labels)
            # Bit hacky - the last one doesn't have a trailing space
            second_header_line = second_header_line[:-1]
            clip_text.append(first_header_line)
            clip_text.append(second_header_line)
            # Finish off by formatting each row
            for row_label in sorted(row_labels, key=int):
                curr_line = row_label.ljust(max_row_length) + u' | '
                cell_vals = []
                for col_label, col_cells in sel_cells.items():
                    cell_vals.append(col_cells.get(row_label, u'').ljust(
                        max_col_lengths[col_label]))
                curr_line += u' | '.join(cell_vals)
                clip_text.append(curr_line)
            return u'\n'.join(l.rstrip() for l in clip_text)

    _complex_start = re.compile(r' +\|')
    def _parse_clipboard_contents(self, clipboard_contents):
        """Parses the specified clipboard contents into a dictionary
        containing instructions for how to edit the table."""
        # Note that we'll return {} whenever we detect a format error
        if not clipboard_contents: return {}
        ret_dict = defaultdict(dict)
        all_lines = clipboard_contents.splitlines()
        if self._complex_start.match(all_lines[0]):
            if len(all_lines) < 3: return {}
            # Still the most complex case, but much simpler than copying. We
            # need to parse the ASCII table, which will give us absolute
            # instructions on how to edit the real table
            col_labels = [x.strip() for x in all_lines[0].split(u'|')][1:]
            # Iterate over all rows, but skip the second line - only there for
            # human readability
            for row_line in all_lines[2:]:
                line_contents = [x.strip() for x in row_line.split(u'|')]
                if len(line_contents) < len(col_labels) + 1: return {}
                row_label = line_contents[0]
                # Iterate over each cell in the current row, but check if
                # there's a value in the cell before storing it (we don't want
                # to override cells the user didn't originally select)
                for i, cell_value in enumerate(line_contents[1:]):
                    cell_value = cell_value
                    if cell_value:
                        ret_dict[col_labels[i]][row_label] = cell_value
        else:
            # Pasting a list is always relative to the focused cell
            ##: As a 'fun' project: take the current selection into account
            focused_col = self.get_focused_column()
            focused_row = self._native_widget.GetGridCursorRow() + 1
            for r, cell_value in enumerate(all_lines):
                ret_dict[focused_col][str(focused_row + r)] = cell_value
        return ret_dict

    def get_cell_value(self, col_label, row_label):
        """Returns the value of the cell at the specified row and column."""
        return self._native_widget.GetCellValue(
            int(row_label) - 1, self._label_to_col_index[col_label])

    def set_cell_value(self, col_label, row_label, cell_value):
        """Sets the value of the cell at the specified row and column to the
        specified value."""
        self._native_widget.SetCellValue(
            int(row_label) - 1, self._label_to_col_index[col_label],
            cell_value)

    def get_focused_cell(self):
        """Returns the value of the focused cell."""
        return self._native_widget.GetCellValue(
            self._native_widget.GetGridCursorRow(),
            self._native_widget.GetGridCursorCol())

    def get_focused_column(self):
        """Returns the label of the focused column."""
        return self._native_widget.GetColLabelValue(
            self._native_widget.GetGridCursorCol())

    def get_selected_cells(self):
        """Returns a dict of dicts, mapping column labels to row labels to cell
        values for all cells that have been selected by the user."""
        # May seem inefficient, but the alternative is incredibly complex; plus
        # this takes < 1/2s for a table with several thousand entries
        sel_dict = defaultdict(dict)
        for c in range(self._native_widget.GetNumberCols()):
            col_label = self._native_widget.GetColLabelValue(c)
            for r in range(self._native_widget.GetNumberRows()):
                if self._native_widget.IsInSelection(r, c):
                    sel_dict[col_label][str(r + 1)] = (
                        self._native_widget.GetCellValue(r, c))
        return sel_dict

    def edit_cells(self, cell_edits):
        """Applies a series of as described by the specified dict mapping
        column labels to row labels to cell values."""
        for col_label, target_cells in cell_edits.items():
            for row_label, target_val in target_cells.items():
                # Skip any that would go out of bounds
                if int(row_label) - 1 < self._native_widget.GetNumberRows():
                    self.set_cell_value(col_label, row_label, target_val)

# Other -----------------------------------------------------------------------
class GlobalMenu(_AComponent):
    """A global menu bar that populates JIT by repopulating its contents right
    before the menu is opened by the user. The menus are called 'categories' to
    differentiate them from regular context menus."""
    _wx_widget_type = _wx.MenuBar

    class _GMCategory(_wx.Menu):
        """wx-derived class used to differentiate between events on regular
        menus and categories and to provide the category label at runtime."""
        def __init__(self, cat_lbl):
            super(GlobalMenu._GMCategory, self).__init__()
            self.category_label = cat_lbl

    def __init__(self):
        self._native_widget = self._wx_widget_type() # no parent
        self._category_handlers = {}
        # We need to do this once and only once, because wxPython does not
        # support binding multiple methods to one event source. Also, it *has*
        # to be on Link.Frame, even if that looks weird.
        from ..balt import Link ##: de-wx! move links to gui
        menu_processor = lambda event: [event.GetMenu()]
        self._on_menu_opened = Link.Frame._evt_handler(_wx.EVT_MENU_OPEN,
            menu_processor)
        self._on_menu_closed = Link.Frame._evt_handler(_wx.EVT_MENU_CLOSE,
            menu_processor)
        self._on_menu_opened.subscribe(self._handle_menu_opened)
        self._on_menu_closed.subscribe(self._handle_menu_closed)

    def categories_equal(self, new_categories):
        """Checks if the categories currently shown in the GUI match the
        specified ones."""
        return new_categories == [x[1] for x in self._native_widget.GetMenus()]

    def register_category_handler(self, cat_label, cat_handler):
        """Registers the specified handler for the specified category. The
        handler should be a callback that will be given a _GMCategory instance,
        which it should populate with links."""
        self._category_handlers[cat_label] = cat_handler

    def release_bindings(self):
        """Releases the 'on menu' bindings used by this class. You *must* call
        this if you want to replace the global menu at runtime."""
        self._on_menu_opened.unsubscribe(self._handle_menu_opened)
        self._on_menu_closed.unsubscribe(self._handle_menu_closed)

    def set_categories(self, all_categories):
        """Creates dropdowns for all specified categories, discarding existing
        ones in the process. It has to be done like this to avoid changing the
        GUI's layout while categories are added to/removed from it."""
        self._native_widget.SetMenus([(self._GMCategory(c), c)
                                      for c in all_categories])

    def _handle_menu_opened(self, wx_menu):
        """Internal callback, does the heavy lifting. Also handles status bar
        text resetting, because wxPython does not permit more than one event
        handler."""
        from ..balt import Link ##: de-wx! move links to gui
        Link.Frame.set_status_info(u'')
        if not isinstance(wx_menu, self._GMCategory):
            return # skip all regular context menus that were opened
        # If we don't pause here, the GUI will flicker like crazy
        with self.pause_drawing():
            # Clear the menu and repopulate it. Have to do this JIT, since the
            # checked/enabled/appended state of links will depend on the
            # current state of WB itself.
            for old_menu_item in wx_menu.GetMenuItems():
                wx_menu.DestroyItem(old_menu_item)
            # Need to set this, otherwise help text won't be shown
            Link.Popup = wx_menu
            try:
                self._category_handlers[wx_menu.category_label](wx_menu)
            except KeyError:
                raise RuntimeError(u"A GlobalMenu handler is missing for "
                                   u"category '%s'." % wx_menu.category_label)

    def _handle_menu_closed(self, wx_menu):
        """Internal callback, needed to correctly handle help text."""
        if isinstance(wx_menu, self._GMCategory):
            from ..balt import Link ##: de-wx! move links to gui
            Link.Popup = None
