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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module defines layout components that define how components will fit
together to create a GUI. In doing so, it is also responsible for making the
rest of the gui modules work by chaining the _AComponent-based high-level
components into actual wx calls."""

__author__ = 'nycz'

import wx as _wx

from .base_components import _AComponent

CENTER, LEFT, RIGHT, TOP, BOTTOM = 'center', 'left', 'right', 'top', 'bottom'
_H_ALIGNS = {None: _wx.ALIGN_LEFT,
             CENTER: _wx.ALIGN_CENTER_HORIZONTAL,
             LEFT: _wx.ALIGN_LEFT,
             RIGHT: _wx.ALIGN_RIGHT}
_V_ALIGNS = {None: _wx.ALIGN_CENTER_VERTICAL,
             CENTER: _wx.ALIGN_CENTER_VERTICAL,
             TOP: _wx.ALIGN_TOP,
             BOTTOM: _wx.ALIGN_BOTTOM}

class Spacer(object):
    """A fixed-size space in a layout."""
    def __init__(self, size=0):
        self.size = size

class Stretch(object):
    """A space that will take up as much space as possible in a layout."""
    def __init__(self, weight=1):
        self.weight = weight

class LayoutOptions(object):
    """Container for all layouts' options. Note that some options may only
    work with certain kinds of layouts (eg. col_span and row_span).

    border (int)
        The width (in pixels) of the empty space around an item.
    fill (bool)
        Whether the items should fill the entire space the layout has
        allocated for it or not.
    weight (int)
        The relative amount an item will grow beyond the space the
        layout has allocated for it. If in one layout there is only one item
        with weight > 0, it will take up all remaining space. If multiple
        items all have equal weight > 0, they will share the space equally.
        If one item has twice the weight of another, it will take up twice
        the space, etc.
    h_align (LEFT/CENTER/RIGHT), v_align (TOP/CENTER/BOTTOM)
        The horizontal and vertical alignment for an item
        within the space the layout has allocated for it, specified with the
        enums LEFT/CENTER/RIGHT for h_align and TOP/CENTER/BOTTOM for v_align.
        Note that these options do nothing if fill is true, since the item
        then takes up all of the space and has no room to move.
    col_span, row_span (int)
        The number of columns or rows this items should take up.
    """
    def __init__(self, border=None, fill=None, weight=None,
                 h_align=None, v_align=None, col_span=None, row_span=None):
        self.border = border
        self.fill = fill
        self.weight = weight
        self.h_align = h_align
        self.v_align = v_align
        self.col_span = col_span
        self.row_span = row_span

class _ALayout(object):
    """Abstract base class for all layouts."""
    def __init__(self, sizer, border=0, default_border=0, default_fill=False,
                 default_h_align=None, default_v_align=None):
        self._sizer = sizer
        if border > 0:
            self._border_wrapper = _wx.BoxSizer(_wx.VERTICAL)
            self._border_wrapper.AddSizer(self._sizer, proportion=1,
                                          flag=_wx.ALL | _wx.EXPAND,
                                          border=border)
        else:
            self._border_wrapper = None
        self.default_border = default_border
        self.default_fill = default_fill
        self.default_h_align = default_h_align
        self.default_v_align = default_v_align
        self._parent = None

    def apply_to(self, parent, fit=False):
        """Apply this layout to to the parent."""
        self._parent = parent
        sizer = self._border_wrapper or self._sizer
        if fit:
            parent.SetSizerAndFit(sizer)
        else:
            parent.SetSizer(sizer)

    def _get_item_options(self, item):
        """Internal helper function to get possible options from the item."""
        options = None
        if isinstance(item, tuple):
            item, options = item
        if item is None: return None, None, None, None
        elif isinstance(item, _ALayout):
            item = item._sizer
        else:
            item = _AComponent._resolve(item)
        border = self.default_border
        fill_ = self.default_fill
        h_align = self.default_h_align
        v_align = self.default_v_align
        if options:
            if options.border is not None: border = options.border
            if options.fill is not None: fill_ = options.fill
            if options.h_align is not None: h_align = options.h_align
            if options.v_align is not None: v_align = options.v_align
        flags = _wx.ALL | _H_ALIGNS[h_align] | _V_ALIGNS[v_align]
        if fill_: flags |= _wx.EXPAND
        return item, options, border, flags

class _ALineLayout(_ALayout):
    """Abstract base class for one-dimensional layouts."""
    def __init__(self, sizer, border=0, spacing=0,
                 default_border=0, default_fill=False, default_weight=0,
                 default_h_align=None, default_v_align=None, items=()):
        """Initiate the layout.
        The default_* arguments are for when those options are not provided
        when adding an item. See LayoutOptions for more information.
        :param sizer: The sizer this layout will wrap around.
        :param border: Size in pixels of an empty border around the layout.
                       NOTE: this is around the layout, not individual items.
        :param spacing: Size in pixels of spacing between each item.
        :param items: Items or (item, options) pairs to add directly.
        """
        self.spacing = spacing
        self.default_weight = default_weight
        super(_ALineLayout, self).__init__(sizer, border=border,
                                           default_border=default_border,
                                           default_fill=default_fill,
                                           default_h_align=default_h_align,
                                           default_v_align=default_v_align)
        if items: self.add_many(*items)

    def add(self, item):
        """Add one item to the layout.
        The argument may be a (item, options) pair."""
        if isinstance(item, Stretch):
            self._add_stretch(item.weight)
        elif isinstance(item, Spacer):
            self._add_spacer(item.size)
        else:
            item, options, border, flags = self._get_item_options(item)
            if item is None: return
            weight = (options.weight if options and options.weight is not None
                      else self.default_weight)
            if self.spacing > 0 and not self._sizer.IsEmpty():
                self._sizer.AddSpacer(self.spacing)
            self._sizer.Add(item, proportion=weight, flag=flags, border=border)
            self._sizer.SetItemMinSize(item, -1, -1)

    def add_many(self, *items):
        """Add multiple items to the layout.
        The items may be (item, options) pairs, Stretch- or Spacer objects."""
        for item in items:
            self.add(item)

    def _add_spacer(self, length=4):
        """Add a fixed space to the layout."""
        self._sizer.AddSpacer(length)

    def _add_stretch(self, weight=1):
        """Add a growing space to the layout."""
        self._sizer.AddStretchSpacer(prop=weight)

class HBoxedLayout(_ALineLayout):
    """A horizontal layout with a border around it and an optional title."""
    def __init__(self, parent, title=u'', **kwargs):
        sizer = _wx.StaticBoxSizer(_wx.StaticBox(parent, label=title),
                                   _wx.HORIZONTAL)
        super(HBoxedLayout, self).__init__(sizer, **kwargs)

class HLayout(_ALineLayout):
    """A simple horizontal layout."""
    def __init__(self, *args, **kwargs):
        super(HLayout, self).__init__(_wx.BoxSizer(_wx.HORIZONTAL),
                                      *args, **kwargs)

class VLayout(_ALineLayout):
    """A simple vertical layout."""
    def __init__(self, *args, **kwargs):
        super(VLayout, self).__init__(_wx.BoxSizer(_wx.VERTICAL),
                                      *args, **kwargs)

class GridLayout(_ALayout):
    """A flexible grid layout.
    It has no fixed or set number of rows or columns, but will instead grow to
    fit its content. The weight of items are handled on a per-row and -col
    basis, specified with stretch_cols/stretch_rows or set_stretch()."""
    def __init__(self, border=0, h_spacing=0, v_spacing=0,
                 stretch_cols=(), stretch_rows=(),
                 default_fill=False, default_border=0,
                 default_h_align=None, default_v_align=None, items=()):
        """
        Initiate the grid layout.

        :param h_spacing: the width (in pixels) of space between columns
        :param v_spacing: the height (in pixels) of space between rows
        :param stretch_cols: the columns (as a list of ints) that should
            grow and fill available space
        :param stretch_rows: the rows (as a list of ints) that should
            grow and fill available space
        :param items: Items or (item, options) pairs to add directly.
        """
        super(GridLayout, self).__init__(_wx.GridBagSizer(hgap=h_spacing,
                                                          vgap=v_spacing),
                                         border=border,
                                         default_border=default_border,
                                         default_fill=default_fill,
                                         default_h_align=default_h_align,
                                         default_v_align=default_v_align)
        if items:
            self.append_rows(items)
        for col in stretch_cols:
            self.set_stretch(col=col)
        for row in stretch_rows:
            self.set_stretch(row=row)

    def add(self, col, row, item):
        """Add an item to the specified place in the layout.
        If there is an item there already, it will be replaced.
        If item is None, nothing will be added."""
        item, options, border, flags = self._get_item_options(item)
        if item is None: return
        col_span, row_span = 1, 1
        if options:
            if options.col_span is not None: col_span = options.col_span
            if options.row_span is not None: row_span = options.row_span
        self._sizer.Add(item, (row, col), span=(row_span, col_span),
                        flag=flags, border=border)
        self._sizer.SetItemMinSize(item, -1, -1)

    def append_row(self, items):
        """Add a row of items to the bottom of the layout."""
        row = self._sizer.GetRows()
        for col, item in enumerate(items):
            if item is not None:
                self.add(col, row, item)

    def append_rows(self, item_rows):
        """Add multiple rows of items to the bottom of the layout."""
        row_num = self._sizer.GetRows()
        for row, items in enumerate(item_rows, row_num):
            for col, item in enumerate(items):
                if item is not None:
                    self.add(col, row, item)

    def col_count(self):
        """Return the number of columns in the layout."""
        return self._sizer.GetCols()

    def row_count(self):
        """Return the number of rows in the layout."""
        return self._sizer.GetRows()

    def set_stretch(self, col=None, row=None, weight=0):
        """Set the relative weight of a column or a row."""
        # The sizer blows up if you try to set a column or row to grow if
        # there isn't something in it, so we add a space if that happens
        if row is not None:
            if self._sizer.IsRowGrowable(row): # can't set growable...
                self._sizer.RemoveGrowableRow(row) # ...if it's already set
            try:
                self._sizer.AddGrowableRow(row, proportion=weight)
            except _wx.PyAssertionError: # the sizer blows up
                self._sizer.Add((0, 0), (row, 0)) # add space to the first col
                self._sizer.AddGrowableRow(row, proportion=weight)
        if col is not None:
            if self._sizer.IsColGrowable(col):
                self._sizer.RemoveGrowableCol(col)
            try:
                self._sizer.AddGrowableCol(col, proportion=weight)
            except _wx.PyAssertionError:
                self._sizer.Add((0, 0), (0, col))
                self._sizer.AddGrowableCol(col, proportion=weight)

