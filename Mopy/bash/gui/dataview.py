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
"""DataView classes for implementing a DVC. wx.dataview provides many types:

- wx.dataview.DataViewModel: abstract base for all models.
   - Implemented with _DataViewModel
   - Wrapped with ADataViewModel.  Users still need to implement
     the methods that DataViewCtrl uses to access data from the model.
- wx.dataview.DataViewCtrl:
   - Implemented with DataViewCtrl.  Only works with models derived
     from DataViewModel.
- wx.dataview.DataViewColumn: class representing a UI column of a DataViewCtrl
   - Wrapped with DataViewColumn.
- wx.dataview.DataViewItem: wx type of all items in a model.
- wx.dataview.DataViewItemArray: list-like object holding wx.DataViewItem's.
   - Mostly wrapped/unwrapped at boundaries between DataViewCtrl/ADataViewModel
     and their wrapped wx instances.
- wx.dataview.DataViewItemAttr: wx type holding UI attributes of an item
   - Currently exposed as-is.  It provides an interface for getting/setting
     various UI options, like font, color, etc.
"""
from __future__ import annotations

__author__ = 'Lojack'

from functools import wraps, cache, cached_property
from typing import Any, Callable, Iterable
from datetime import datetime
from collections.abc import Sequence
from enum import Enum, IntEnum, IntFlag
from contextlib import suppress

import wx
import wx.dataview as dv

from .base_components import _AComponent

class DataViewColumnFlags(IntFlag):
    HIDDEN = dv.DATAVIEW_COL_HIDDEN
    REORDERABLE = dv.DATAVIEW_COL_REORDERABLE
    RESIZABLE = dv.DATAVIEW_COL_RESIZABLE
    SORTABLE = dv.DATAVIEW_COL_SORTABLE

class _Forwarder:
    """Class for easier forwarding of methods/properties from
       one class to another."""
    def __init__(self,
            get_wrapper: Callable | None = None,
            set_wrapper: Callable | None = None,
            resolver: Callable | None = None) -> None:
        self._get_wrap = get_wrapper
        self._set_wrap = set_wrapper
        self._resolve = resolver or self.default_resolver

    def forward_property(self, prop: property) -> property:
        if self._get_wrap:
            def getter(component):
                return self._get_wrap(prop.fget(self._resolve(component)))
        else:
            def getter(component):
                return prop.fget(self._resolve(component))
        if self._set_wrap:
            def setter(component, value):
                prop.fset(self._resolve(component), self._set_wrap(value))
        else:
            def setter(component, value):
                prop.fset(self._resolve(component), value)
        return property(getter, setter, prop.fdel, prop.__doc__)

    def forward_method(self, func: Callable) -> Callable:
        if self._get_wrap:
            @wraps(func)
            def wrapped(component, *args, **kwargs):
                return self._get_wrap(func(self._resolve(component), *args, **kwargs))
        else:
            @wraps(func)
            def wrapped(component, *args, **kwargs):
                return func(self._resolve(component), *args, **kwargs)
        return wrapped

    @staticmethod
    def default_resolver(component: '_AComponent') -> Any:
        return getattr(component, '_native_widget', component)

    @classmethod
    @cache
    def with_return(cls, return_wrapper: Callable) -> '_Forwarder':
        return cls(return_wrapper)

    @classmethod
    @cache
    def with_input(cls, input_wrapper: Callable | None = None) -> '_Forwarder':
        input_wrapper = input_wrapper or cls.default_resolver
        return cls(None, input_wrapper)

    @classmethod
    @cache
    def wrap(cls, return_wrapper: Callable,
             input_wrapper: Callable | None = None) -> '_Forwarder':
        input_wrapper = input_wrapper or cls.default_resolver
        return cls(return_wrapper, input_wrapper)

    def __call__(self, func: Callable | property) -> Callable | property:
        """Create a instance method or property which forwards its calls to another object.
           The object forwarded to is determined by the resolver specified at creation,
           the default resolver assumes the forwarding object is `_AComponent`-like (has a
           `_native_widget` attribute.  The return type can optionally be automatically
           converted, as well as the input types for properties, as determined by conversion
           methods specified at `Forwarder` creation.

           Usage:
             forward(class.Attribute)
                - Forward the method or property with no conversion.

             forward.with_return(return_converter)(class.Attribute)
                - Forward the method or property, converting the return value.

             forward.with_input(input_converter=default_resolver)(class.Attribute)
                - Forward a property. Converting values to be set with `input_converter`.

             forward.wrap(return_converter, input_converter=default_resolver)(class.Attribute)
                - Forward the method or property, converting the return value.
                  For properties, set values are converted with `input_converter`.
           """
        if isinstance(func, property):
            return self.forward_property(func)
        else:
            return self.forward_method(func)

forward = _Forwarder()

class _DataViewModel(dv.PyDataViewModel):
    def __init__(self, parent=None) -> None:
        # parent parameter provided to work with _AComponent,
        # even though dv.PyDataViewModel doesn't derive from wx.Window
        super().__init__()

    def _set_amodel(self, model: 'ADataViewModel') -> None:
        # ADataViewModel constructs this object before its
        # Construction is complete, so we cannot set this
        # during this object's constructor
        self._model = model

    weak_refs = property(
        None,
        forward(dv.PyDataViewModel.UseWeakRefs)
    )

    # Helper methods for converting to<->from wx types
    def wrap(self, py_object: Any) -> dv.DataViewItem:
        return dv.NullDataViewItem if py_object is None else self.ObjectToItem(py_object)

    def wrap_list(self, py_objects: Iterable[Any]) -> dv.DataViewItemArray:
        array = dv.DataViewItemArray()
        for item in map(self.wrap, py_objects):
            array.append(item)
        return array

    def unwrap(self, wx_item: dv.DataViewItem) -> Any:
        return None if not wx_item else self.ItemToObject(wx_item)

    def unwrap_list(self, wx_array: dv.DataViewItemArray) -> Iterable[Any]:
        return map(self.unwrap, wx_array)

    # Methods accessed by dv.DataViewControl
    def GetChildren(self, parent: dv.DataViewItem, children: dv.DataViewItemArray) -> int:
        i = 0
        for i, child in enumerate(self._model.get_children(self.unwrap(parent)), start=1):
            children.append(self.wrap(child))
        return i

    def IsContainer(self, item: dv.DataViewItem) -> bool:
        return self._model.is_container(self.unwrap(item))

    def GetParent(self, item: dv.DataViewItem) -> dv.DataViewItem:
        return self.wrap(self._model.get_parent(self.wrap(item)))

    def HasValue(self, item: dv.DataViewItem, column: int) -> bool:
        return self._model.has_value(self.unwrap(item), column)

    def GetValue(self, item: dv.DataViewItem, column: int) -> Any:
        return self._model.get_value(self.unwrap(item), column)

    def GetAttr(self, item: dv.DataViewItem, column: int, attributes: dv.DataViewItemAttr) -> bool:
        ## TODO: wrap _dv.DataViewItemAttributes
        return self._model.get_attributes(self.unwrap(item), column, attributes)

    def SetValue(self, value: Any, item: dv.DataViewItem, column: int) -> bool:
        return self._model.set_value(self.unwrap(item), column, value)

    def GetColumnCount(self) -> int:
        return self._model.get_column_count()

    def GetColumnType(self, column: int) -> str:
        col_type = self._model.get_column_type(column)
        if isinstance(col_type, str):
            return col_type
        elif issubclass(col_type, str):
            return 'string'
        elif issubclass(col_type, int):
            return 'ulonglong'
        elif issubclass(col_type, datetime):
            return 'datetime'
        elif issubclass(col_type, bool):
            return 'bool'
        elif issubclass(col_type, float):
            return 'double'
        raise TypeError(f'DataViewModel: Unsupported column type {col_type!r}.')

class ADataViewModel(_AComponent):
    # Technically not a widget though
    _wx_widget_type = _DataViewModel
    _native_widget: _DataViewModel

    def __init__(self) -> None:
        super().__init__(None)
        self._native_widget._set_amodel(self)

    # Methods accessed by DataViewCtrl
    def get_children(self, parent: Any) -> Iterable[Any]:
        raise NotImplementedError

    def is_container(self, item: Any) -> bool:
        raise NotImplementedError

    def get_parent(self, item: Any) -> Any:
        raise NotImplementedError

    def has_value(self, item: Any, column: int) -> bool:
        raise NotImplementedError

    def get_value(self, item: Any, column: int) -> Any:
        raise NotImplementedError

    def get_attributes(self, item: Any, column: int,
                       attributes: dv.DataViewItemAttr) -> bool:
        # Default implementation: don't change any display attributes
        return False

    def set_value(self, item: Any, column: int) -> bool:
        raise NotImplementedError

    def get_column_count(self) -> int:
        raise NotImplementedError

    def get_column_type(self, column: int) -> type | str:
        raise NotImplementedError

    # Methods for notifying associated DataViewCtrl's of changes
    def notify_value_changed(self, item: Any, column: int) -> None:
        self._native_widget.NotifyValueChanged(
            self._native_widget.wrap(item),
            column
        )

    def notify_item_added(self, parent: Any, item: Any) -> None:
        self._native_widget.NotifyItemAdded(
            self._native_widget.wrap(parent),
            self._native_widget.wrap(item)
        )

    def notify_item_deleted(self, parent: Any, item: Any) -> None:
        self._native_widget.NotifyItemDeleted(
            self._native_widget.wrap(parent),
            self._native_widget.wrap(item),
        )

    def notify_item_changed(self, item: Any) -> None:
        self._native_widget.NotifyItemChanged(
            self._native_widget.wrap(item)
        )

    def notify_cleared(self) -> None:
        self._native_widget.Cleared()

    def notify_items_added(self, parent: Any, items: Iterable[Any]) -> None:
        self._native_widget.NotifyItemsAdded(
            self._native_widget.wrap(parent),
            self._native_widget.wrap_list(items)
        )

    def notify_items_deleted(self, parent: Any, items: Iterable[Any]) -> None:
        self._native_widget.NotifyItemsDeleted(
            self._native_widget.wrap(parent),
            self._native_widget.wrap_list(items)
        )

    def notify_items_changed(self, items: Iterable[Any]) -> None:
        self._native_widget.NotifyItemsChanged(
            self._native_widget.wrap_list(items)
        )

class DataViewColumn(_AComponent):
    _wx_widget_type = dv.DataViewColumn
    _native_widget: dv.DataViewColumn

    model_column = property(forward(dv.DataViewColumn.GetModelColumn))
    owner = forward(dv.DataViewColumn.Owner)
    renderer = forward(dv.DataViewColumn.Renderer)
    alignment = forward(dv.DataViewColumn.Alignment)
    bitmap = forward(dv.DataViewColumn.Bitmap)
    flags = forward(dv.DataViewColumn.Flags)
    min_width = forward(dv.DataViewColumn.MinWidth)
    sort_order = forward(dv.DataViewColumn.SortOrder)
    title = forward(dv.DataViewColumn.Title)
    width = forward(dv.DataViewColumn.Width)
    sortable = forward(dv.DataViewColumn.Sortable)
    reorderable = forward(dv.DataViewColumn.Reorderable)

class DataViewColumnType(Enum):
    BITMAP = 'Bitmap'
    DATE = 'Date'
    ICON_TEXT = 'IconText'
    PROGRESS = 'Progress'
    TEXT = 'Text'
    TOGGLE = 'Toggle'
    GENERIC = ''

class _ColumnInsert(IntEnum):
    Append = 0
    Prepend = 1

class _DataViewColumns(Sequence):
    # list-like wrapper around the UI columns present in a DataViewCtrl.
    _methods = {kind: tuple(
                    getattr(dv.DataViewCtrl, f'{where.name}{kind.value}Column')
                    for where in _ColumnInsert)
                for kind in DataViewColumnType}

    def __init__(self, widget: dv.DataViewCtrl) -> None:
        self._native_widget = widget

    # Forwarded properties
    selected = property(forward.with_return(DataViewColumn)(dv.DataViewCtrl.GetCurrentColumn))
    expander = forward.wrap(DataViewColumn)(dv.DataViewCtrl.ExpanderColumn)

    @property
    def sorter(self) -> DataViewColumn:
        return DataViewColumn(self._native_widget.GetSortingColumn(), _wrap_existing=True)

    @sorter.setter
    def sorter(self, column: DataViewColumn) -> None:
        col = self.index(column._native_widget)
        self._native_widget.ToggleSortByColumn(col)

    # Forwarded methods
    def _insert_column(self, where, *args, **kwargs) -> DataViewColumn | None:
        column_type = kwargs.pop('column_type', DataViewColumnType.GENERIC)
        method = self._methods[column_type][where]
        if column_type:
            # Specific column append/prepend method
            return DataViewColumn(method(self._native_widget, *args, **kwargs), _wrap_existing=True)
        else:
            # Generic column append/prepend method with an already existing
            # DataViewColumn object
            # Quick way to extract the 'col' arg from *args, **kwargs
            def get_column_arg(col):
                return col
            col = get_column_arg(*args, **kwargs)
            # TODO: Check if dv.DataViewColumn derives from wx.Window
            # if it doesn't, we can't use _resolve
            return col if method(self._native_widget,
                                 _AComponent._resolve(col)) else None

    def append(self, *args, **kwargs) -> DataViewColumn | None:
        return self._insert_column(_ColumnInsert.Append, *args, **kwargs)

    def prepend(self, *args, **kwargs) -> DataViewColumn | None:
        return self._insert_column(_ColumnInsert.Prepend, *args, **kwargs)

    def insert(self, position: int, column: DataViewColumn) -> bool:
        return self._native_widget.InsertColumn(position, _AComponent._resolve(column))

    clear = forward(dv.DataViewCtrl.ClearColumns)
    __delitem__ = forward(dv.DataViewCtrl.DeleteColumn)
    __getitem__ = forward.with_return(DataViewColumn)(dv.DataViewCtrl.GetColumn)
    __len__ = forward(dv.DataViewCtrl.GetColumnCount)
    index = forward.with_input()(dv.DataViewCtrl.GetColumnPosition)

class _DataViewOptions:
    """Wrapper around a DataViewCtrl's UI configuration options."""

    def __init__(self, wx_widget: dv.DataViewCtrl):
        self._native_widget = wx_widget

    # Forwarded properties
    multicolumn_sort = property(
        forward(dv.DataViewCtrl.IsMultiColumnSortAllowed),
        forward(dv.DataViewCtrl.AllowMultiColumnSort)
    )

    # Forwarded methods
    def set_drag_source_type(self, drag_type: int | None) -> None:
        drag_type = drag_type or wx.DF_INVALID
        self._native_widget.EnableDragSource(format=wx.DataFormat(drag_type))

    def set_drop_target_type(self, drop_type: int | None) -> None:
        drop_type = drop_type or wx.DF_INVALID
        self._native_widget.EnableDropTarget(format=wx.DataFormat(drop_type))

    set_alternate_row_color = forward(dv.DataViewCtrl.SetAlternateRowColour)
    set_header_attributes = forward(dv.DataViewCtrl.SetHeaderAttr)
    set_row_height = forward(dv.DataViewCtrl.SetHeaderAttr)

class _DataViewSelection(Sequence):
    # list-like wrapper around currently selected items in the DataViewControl
    ## TODO: wrap dv.DataViewItem?

    def __init__(self, wx_widget: dv.DataViewCtrl) -> None:
        self._widget = wx_widget

    # Forwarded methods
    __nonzero__ = forward(dv.DataViewCtrl.HasSelection)

    def __getitem__(self, key: int | slice) -> Any:
        if key:
            return self._widget._unwrap_item(self._widget.GetSelections()[key])
        else:
            return self._widget.unwrap_list(self._widget.GetSelection())

    def __contains__(self, item: Any) -> bool:
        return self._widget.IsSelected(self._widget._wrap_item(item))

    remove = forward(dv.DataViewCtrl.Unselect)
    __len__ = forward(dv.DataViewCtrl.GetSelectedItemsCount)
    clear = forward(dv.DataViewCtrl.UnselectAll)
    select_all = forward(dv.DataViewCtrl.SelectAll)

    def _set_selection(self, new_selection: Iterable[dv.DataViewItem] | dv.DataViewItem) -> None:
        if isinstance(new_selection, dv.DataViewItem):
            new_selection = [new_selection]
        if new_selection:
            items = dv.DataViewItemArray()
            for item in new_selection:
                items.append(item)
            self._widget.SetSelections(items)
        else:
            self._widget.UnselectAll()

    # Forwarded properties
    @property
    def focused(self) -> Any:
        return self._widget._unwrap_item(self._widget.CurrentItem)

    @focused.setter
    def focused(self, item) -> None:
        self._widget.CurrentItem = self._widget._wrap_object(item)

class DataViewCtrl(_AComponent):
    _wx_widget_type = dv.DataViewCtrl
    _native_widget: dv.DataViewCtrl

    # Forwarded properties
    default_item_attributes = property(forward(dv.DataViewCtrl.GetClassDefaultAttributes))
    visible_item_count = forward(dv.DataViewCtrl.GetCountPerPage)
    indent = forward(dv.DataViewCtrl.Indent)

    @property
    def top_item(self) -> Any:
        return self._unwrap_item(self._native_widget.TopItem)

    @top_item.setter
    def top_item(self, item: Any):
        self._native_widget.TopItem = self._wrap_object(item)

    @property
    @cache
    def columns(self) -> _DataViewColumns:
        return _DataViewColumns(self._native_widget)

    @property
    @cache
    def options(self) -> _DataViewOptions:
        return _DataViewOptions(self._native_widget)

    @property
    @cache
    def selection(self) -> _DataViewSelection:
        return _DataViewSelection(self._native_widget)

    @selection.setter
    def selection(self, new_selection: Iterable[Any]) -> None:
        new_selection = (self._wrap_object(item) for item in new_selection)
        self.selection._set_selection(new_selection)

    # Forwarded methods
    def associate_model(self, model: ADataViewModel) -> None:
        self._native_widget.AssociateModel(model._native_widget)
        with suppress(AttributeError):
            del self._model

    def collapse_item(self, item: Any) -> None:
        self._native_widget.Collapse(self._wrap_object(item))

    def edit_item(self, item: Any) -> None:
        self._native_widget.EditItem(self._wrap_object(item))

    def ensure_visible(self, item: Any) -> None:
        self._native_widget.EnsureVisible(self._wrap_object(item))

    def is_expanded(self, item: Any) -> bool:
        return self._native_widget.IsExpanded(self._wrap_object(item))

    def expand_item(self, item: Any, recursive: bool = False) -> None:
        item = self._wrap_object(item)
        if recursive:
            self._resolve(self).ExpandAncestors(item)
        else:
            self._resolve(self).Expand(item)

    # Helper methods to wrap/unwrap _dv.DataViewItem's
    @cached_property
    def _model(self) -> _DataViewModel:
        return self._resolve(self).GetModel()

    def _unwrap_item(self, item: dv.DataViewItem) -> Any:
        return self._model.unwrap(item)

    def _unwrap_list(self, items: dv.DataViewItemArray) -> Iterable[Any]:
        return self._model.unwrap_list(items)

    def _wrap_object(self, py_object: Any) -> dv.DataViewItem:
        return self._model.wrap(py_object)

    def _wrap_list(self, py_objects: Iterable[Any]) -> dv.DataViewItemArray:
        return self._model.wrap_list(py_objects)

    ## Not exposed/forwarded
    # Create
    # EnableSystemTheme
    # GetItemRect
    # GetMainWindow
    # GetModel
    # HitTest
    # ToggleSortByColumn
