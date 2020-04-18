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
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2020 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This module houses GUI classes that did not fit anywhere else. Once similar
classes accumulate in here, feel free to break them out into a module."""

__author__ = u'nycz, Infernio, Utumno'

import wx as _wx

from .base_components import _AComponent, Color, WithMouseEvents, \
    WithCharEvents, Image
from .events import EventResult
from ..bolt import deprint, Path

class Font(_wx.Font):

    @staticmethod
    def Style(font_, bold=False, slant=False, underline=False):
        if bold: font_.SetWeight(_wx.FONTWEIGHT_BOLD)
        if slant: font_.SetStyle(_wx.FONTSTYLE_SLANT)
        else: font_.SetStyle(_wx.FONTSTYLE_NORMAL)
        font_.SetUnderlined(underline)
        return font_

class CheckBox(_AComponent):
    """Represents a simple two-state checkbox.

    Events:
     - on_checked(checked: bool): Posted when this checkbox's state is changed
       by checking or unchecking it. The parameter is True if the checkbox is
       now checked and False if it is now unchecked."""
    def __init__(self, parent, label=u'', chkbx_tooltip=None, checked=False):
        """Creates a new CheckBox with the specified properties.

        :param parent: The object that this checkbox belongs to. May be a wx
                       object or a component.
        :param label: The text shown on this checkbox.
        :param chkbx_tooltip: A tooltip to show when the user hovers over this
                              checkbox.
        :param checked: The initial state of the checkbox."""
        super(CheckBox, self).__init__(_wx.CheckBox, parent, label=label)
        if chkbx_tooltip:
            self.tooltip = chkbx_tooltip
        self.is_checked = checked
        # Events
        self.on_checked = self._evt_handler(_wx.EVT_CHECKBOX,
                                            lambda event: [event.IsChecked()])

    @property
    def is_checked(self): # type: () -> bool
        """Returns True if this checkbox is checked.

        :return: True if this checkbox is checked."""
        return self._native_widget.GetValue()

    @is_checked.setter
    def is_checked(self, new_state): # type: (bool) -> None
        """Marks this checkbox as either checked or unchecked, depending on the
        value of new_state.

        :param new_state: True if this checkbox should be checked, False if it
                          should be unchecked."""
        self._native_widget.SetValue(new_state)

class DropDown(_AComponent):
    """Wraps a DropDown with automatic tooltip if text is wider than width of
    control.

    Events:
     - on_combo_select(selected_label: str): Posted when an item on the list is
     selected. The parameter is the new value of selection."""
    def __init__(self, parent, value, choices, __autotooltip=True,
                 __readonly=True):
        """Creates a new DropDown with the specified properties.

        :param parent: The object that this combobox belongs to. May be a wx
                       object or a component.
        :param value: The selected choice, also the text shown on this
                      combobox.
        :param choices: The combobox choices."""
        super(DropDown, self).__init__(_wx.ComboBox, parent, value=value,
                                       choices=choices, style=_wx.CB_READONLY)
        # Events
        self.on_combo_select = self._evt_handler(_wx.EVT_COMBOBOX,
            lambda event: [event.GetString()])
        # Internal use only - used to set the tooltip
        self._on_size_changed = self._evt_handler(_wx.EVT_SIZE)
        self._on_text_changed = self._evt_handler(_wx.EVT_TEXT)
        self._on_size_changed.subscribe(self._set_tooltip)
        self._on_text_changed.subscribe(self._set_tooltip)

    def unsubscribe_handler_(self):
        # PY3: TODO(inf) needed for wx3, check if needed in Phoenix
        self._on_size_changed.unsubscribe(self._set_tooltip)

    def _set_tooltip(self):
        """Set the tooltip"""
        cb = self._native_widget
        if cb.GetClientSize()[0] < cb.GetTextExtent(cb.GetValue())[0] + 30:
            tt = cb.GetValue()
        else: tt = u''
        self.tooltip = tt

    def set_choices(self, combo_choices):
        """Set the combobox items"""
        self._native_widget.SetItems(combo_choices)

    def set_selection(self, combo_choice):
        """Set the combobox selected item"""
        self._native_widget.SetSelection(combo_choice)

    def get_value(self):
        return self._native_widget.GetValue()

class ColorPicker(_AComponent):
    """A button with a color that launches a color picker dialog.

    Events:
     - on_color_picker_evt(selected_label: str): Posted when the button is
     clicked."""
    def __init__(self, parent, color=None):
        super(ColorPicker, self).__init__(_wx.ColourPickerCtrl, parent)
        if color is not None:
            self.set_color(color)
        self.on_color_picker_evt = self._evt_handler(
            _wx.EVT_COLOURPICKER_CHANGED)

    def get_color(self): # type: () -> Color
        return Color.from_wx(self._native_widget.GetColour())

    def set_color(self, color): # type: (Color) -> None
        self._native_widget.SetColour(color.to_rgba_tuple())

class Spinner(_AComponent):
    """Spin control with event and tip setting."""

    def __init__(self, parent, value=u'', min_val=0, max_val=100, initial=0,
                 name=u'wxSpinctrl', onSpin=None, spin_tip=None):
        super(Spinner, self).__init__(_wx.SpinCtrl, parent, value=value,
                                      style=_wx.SP_ARROW_KEYS, min=min_val,
                                      max=max_val, initial=initial, name=name)
        if onSpin:
            self._on_spin_evt = self._evt_handler(_wx.EVT_SPINCTRL)
            self._on_spin_evt.subscribe(onSpin)
        if spin_tip: self.tooltip = spin_tip

    def sp_set_value(self, sp_value): self._native_widget.SetValue(sp_value)

    def sp_get_value(self): return self._native_widget.GetValue()

class ListBox(WithMouseEvents):
    """Wrap a ListBox control.

    Events:
      - on_list_box(lb_dex: int, item_text: unicode): Posted when user selects
      an item from list. The default arg processor extracts the index of the
      event and the list item label
      - Mouse events - see gui.base_components.WithMouseEvents
     """
    # PY3: typing!
    # type _native_widget: wx.ListBox
    _wx_class = _wx.ListBox
    bind_motion = bind_rclick_down = bind_rclick_up = True

    def __init__(self, parent, choices=None, isSingle=True, isSort=False,
                 isHScroll=False, isExtended=False, onSelect=None):
        style = 0
        if isSingle: style |= _wx.LB_SINGLE
        if isSort: style |= _wx.LB_SORT
        if isHScroll: style |= _wx.LB_HSCROLL
        if isExtended: style |= _wx.LB_EXTENDED
        kwargs_ = {u'style': style}
        if choices: kwargs_[u'choices'] = choices
        super(ListBox, self).__init__(self._wx_class, parent, **kwargs_)
        if onSelect:
            self.on_list_box = self._evt_handler(_wx.EVT_LISTBOX,
                lambda event: [event.GetSelection(), event.GetString()])
            self.on_list_box.subscribe(onSelect)

    def lb_select_index(self, lb_selection_dex):
        self._native_widget.SetSelection(lb_selection_dex)

    def lb_insert(self, str_item, lb_selection_dex):
        self._native_widget.Insert(str_item, lb_selection_dex)

    def lb_insert_items(self, items, pos):
        self._native_widget.InsertItems(items, pos)

    def lb_set_items(self, items):
        """Replace all the items in the control"""
        self._native_widget.Set(items)

    def lb_set_label_at_index(self, lb_selection_dex, str_item):
        """Set the label for the given item"""
        self._native_widget.SetString(lb_selection_dex, str_item)

    def lb_delete_at_index(self, lb_selection_dex):
        """Delete the item at specified index."""
        self._native_widget.Delete(lb_selection_dex)

    def lb_scroll_lines(self, scroll): self._native_widget.ScrollLines(scroll)

    def lb_append(self, str_item): self._native_widget.Append(str_item)

    def lb_clear(self): self._native_widget.Clear()

    def lb_bold_font_at_index(self, lb_selection_dex):
        get_font = self._native_widget.GetFont()
        self._native_widget.SetItemFont(lb_selection_dex,
                                        Font.Style(get_font, bold=True))

    # Getters - we should encapsulate index access
    def lb_get_next_item(self, item, geometry=_wx.LIST_NEXT_ALL,
                         state=_wx.LIST_STATE_SELECTED):
        return self._native_widget.GetNextItem(item, geometry, state)

    def lb_get_str_item_at_index(self, lb_selection_dex):
        return self._native_widget.GetString(lb_selection_dex)

    def lb_get_str_items(self):
        return self._native_widget.GetStrings()

    def lb_get_selections(self): return self._native_widget.GetSelections()


    def lb_index_for_str_item(self, str_item):
        return self._native_widget.FindString(str_item)

    def lb_get_vertical_scroll_pos(self):
        return self._native_widget.GetScrollPos(_wx.VERTICAL)

    def lb_get_items_count(self):
        return self._native_widget.GetCount()

class CheckListBox(ListBox, WithCharEvents):
    """Wrap a CheckListBox control.

    Events:
      - on_check_list_box(index: int): Posted when user checks an item from
      list. The default arg processor extracts the index of the event.
      - on_context(evt_object: wx.Event): Posted when user checks an item
      from list. The default arg processor extracts the index of the event.
      - Mouse events see gui.base_components.WithMouseEvents.
      - Key events see gui.base_components.WithCharEvents.
      """
    # PY3: typing!
    # type _native_widget: wx.CheckListBox
    _wx_class = _wx.CheckListBox
    bind_mouse_leaving = bind_lclick_double = True

    def __init__(self, parent, choices=None, isSingle=False, isSort=False,
                 isHScroll=False, isExtended=False, onSelect=None,
                 onCheck=None): # note isSingle=False by default
        super(CheckListBox, self).__init__(parent, choices, isSingle, isSort,
                 isHScroll, isExtended, onSelect)
        if onCheck:
            self.on_check_list_box = self._evt_handler(
                _wx.EVT_CHECKLISTBOX, lambda event: [event.GetSelection()])
            self.on_check_list_box.subscribe(onCheck)
        self.on_context = self._evt_handler(_wx.EVT_CONTEXT_MENU,
                                            lambda event: [self])

    def lb_check_at_index(self, lb_selection_dex, do_check):
        self._native_widget.Check(lb_selection_dex, do_check)

    def lb_is_checked_at_index(self, lb_selection_dex):
        return self._native_widget.IsChecked(lb_selection_dex)

    def setCheckListItems(self, names, values):
        """Convenience method for setting a bunch of wxCheckListBox items. The
        main advantage of this is that it doesn't clear the list unless it
        needs to. Which is good if you want to preserve the scroll position
        of the list. """
        if not names:
            self.lb_clear()
        else:
            for index, (name, value) in enumerate(zip(names, values)):
                if index >= self.lb_get_items_count():
                    self.lb_append(name)
                else:
                    if index == -1:
                        deprint(u"index = -1, name = %s, value = %s" % (
                            name, value))
                        continue
                    self.lb_set_label_at_index(index, name)
                self.lb_check_at_index(index, value)
            for index in range(self.lb_get_items_count(), len(names), -1):
                self.lb_delete_at_index(index - 1)

    def toggle_checked_at_index(self, lb_selection_dex):
        do_check = not self.lb_is_checked_at_index(lb_selection_dex)
        self.lb_check_at_index(lb_selection_dex, do_check)

    def set_all_checkmarks(self, checked):
        """Sets all checkmarks to the specified state - checked if True,
        unchecked if False."""
        for i in xrange(self.lb_get_items_count()):
            self.lb_check_at_index(i, checked)

class Picture(_AComponent):
    """Picture panel."""
    def __init__(self, parent, width, height, scaling=1,  ##: scaling unused
                 style=_wx.BORDER_SUNKEN, background=_wx.MEDIUM_GREY_BRUSH):
        super(Picture, self).__init__(_wx.Window, parent, size=(width, height),
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
            bmp = (bmp.isfile() and Image(bmp.s).GetBitmap()) or None
        elif isinstance(bmp, tuple):
            bmp = Image.GetImage(*bmp).ConvertToBitmap()
        self.bitmap = bmp
        self._handle_resize()
        return self.bitmap

    def _handle_resize(self): ##: is all these wx.Bitmap calls needed? One right way?
        x, y = self.component_size
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
            image.Rescale(new_x, new_y, _wx.IMAGE_QUALITY_HIGH)
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
        self._native_widget.Freeze()
        img = super(PictureWithCursor, self).set_bitmap(bmp)
        self._native_widget.SetCursor(
            _wx.Cursor(_wx.CURSOR_MAGNIFIER if img else _wx.CURSOR_ARROW))
        self._native_widget.Thaw()
        return img

class _ALine(_AComponent):
    """Abstract base class for simple graphical lines."""
    _line_style = None # override in subclasses

    def __init__(self, parent):
        super(_ALine, self).__init__(_wx.StaticLine, parent,
                                     style=self._line_style)

class HorizontalLine(_ALine):
    """A simple horizontal line."""
    _line_style = _wx.LI_HORIZONTAL

class VerticalLine(_ALine):
    """A simple vertical line."""
    _line_style = _wx.LI_VERTICAL
