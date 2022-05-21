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
"""DataView classes for implmenting a DVC."""
from __future__ import annotations

__author__ = u'Lojack'

from functools import wraps, cache, cached_property
from typing import Any, Callable, get_origin, get_args, Optional, Union
from datetime import datetime
from collections.abc import Sequence, Iterable
from enum import Enum, IntEnum, IntFlag
from contextlib import suppress

import wx
import wx.dataview as dv

try:
    from types import UnionType
except ImportError:
    # Only available on py 3.10+
    UnionType = Union

from .base_components import _AComponent, Color


## wx.dataview provides many types:
#
# wx.dataview.DataViewModel: abstract base for all models.
#  - Implemented with _DataViewModel
#  - Wrapped with ADataViewModel.  Users still need to implement
#    the methods that DataViewCtrl uses to access data from the model.
# wx.dataview.DataViewCtrl:
#  - Implemented with DataViewCtrl.  Only works with models derived
#    from DataViewModel.
# wx.dataview.DataViewColumn: class representing a UI column of a DataViewCtrl
#  - Wrapped with DataViewColumn.
# wx.dataview.DataViewItem: wx type of all items in a model.
#  - Wrapped/unwrapped at wx boundaries internally.
# wx.dataview.DataViewItemArray: list-like object holding wx.DataViewItem's.
#  - Wrapped/unwrapped at wx boundaries internally.
# wx.dataview.DataViewItemAttr: wx type holding UI attributes of an item
#  - Wrapped with DataViewItemAttr
#  - Note, wx.Font items are not wrapped however (DataViewItemAttr.font)


__all__ = [
    'ADataViewModel',
    'DataViewCtrl',
    'DataViewColumnType',
    'DataViewColumn',
    'DataViewColumnFlags',
    'DataViewItemAttr',
    'forward',
    'default_resolver',
]


RGBA = tuple[int, int, int, int]


class DataViewColumnFlags(IntFlag):
    HIDDEN = dv.DATAVIEW_COL_HIDDEN
    REORDERABLE = dv.DATAVIEW_COL_REORDERABLE
    RESIZABLE = dv.DATAVIEW_COL_RESIZABLE
    SORTABLE = dv.DATAVIEW_COL_SORTABLE


def get_optional_type(annotation) -> Any:
    """Get the optional type of an `Optional[type]`, `Union[type, None]`, or
    `type | None` type annotation.

    :param annotation: a type annotation
    :return: the optional type, or None if `annotation` is not an Optional
        type annotation or accepts more than one none-None type.
    """
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        # UnionType is the type | None annotation type.
        type_args = get_args(annotation)
        if len(type_args) == 2:
            t1, t2 = type_args
            if t1 is type(None):
                return t2
            return t1
    return None


def default_resolver(component: _AComponent) -> Any:
    """A resolver to use with `Forwarder` instances, forwarding to objects
    storing the forwarded instance in a `_native_widget` attribute, ie:
    `_AComponent` instances.
    """
    return getattr(component, '_native_widget', component)


class Forwarder:
    """Class for easier forwarding of methods/properties from one class to
    another.
    """
    def __init__(self,
            return_wrapper: Callable | None = None,
            input_wrapper: Callable | None = None,
            resolver: Callable | None = None) -> None:
        """Create a new forwarder instance for wrapping methods.
        
        :param return_wrapper: A callable taking a single object. When this
            forwarder wraps a property or method, its return value is passed
            through `get_wrapper` to convert it.
        :param set_wrapper: A callable taking a single object. When this
            forwarder wraps a property, the setter for the property has values
            to be set passed through `set_wrapper` to convert it.
        :param resolver: A callable taking the instance of the forwarding
            class, returning the target object to forward to.
        """
        self._get_wrap = return_wrapper
        self._set_wrap = input_wrapper
        self._resolve = resolver or default_resolver

    def forward_property(self, prop: property) -> property:
        """Create a property which forwards to the property on the target
        class.

        :param prop: The property instance on the target class.
        :return: A new property object forwarding to the given property.
        """
        if self._get_wrap:
            if (return_type := get_optional_type(self._get_wrap)):
                def getter(component):
                    return_value = prop.fget(self._resolve(component))
                    if return_value is None:
                        return return_type(return_value)
                    return None
            else:
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
        def deller(component):
            prop.fdel(self._resolve(component))
        return property(getter, setter, deller, prop.__doc__)

    def forward_method(self, func: Callable) -> Callable:
        """Create a instance method which forwards to a method on the target
        class.

        :param func: The method on the target class.
        :return: A new method, forwarding to the given method.
        """
        if self._get_wrap:
            @wraps(func)
            def wrapped(component, *args, **kwargs):
                return self._get_wrap(
                    func(self._resolve(component), *args, **kwargs))
        else:
            @wraps(func)
            def wrapped(component, *args, **kwargs):
                return func(self._resolve(component), *args, **kwargs)
        return wrapped

    def with_return(self, return_wrapper: Callable) -> 'Forwarder':
        """Create a copy of this `Forwarder` instance, using the specified
        return wrapper. Equivalent to 
        `Forwarder.with_wrappers(return_wrapper, None, None)`.
        
        :param return_wrapper: The return wrapper the new instance will use.
        :return: A new `Forwarder` instance with the given wrapper.
        """
        return self.with_wrappers(return_wrapper=return_wrapper)

    def with_input(self, input_wrapper: Callable | None = None) -> 'Forwarder':
        """Create a copy of this `Forwarder` instance, using the specified
        input wrapper.  Equivalent to either
        `Forwarder.with_wrappers(None, input_wrapper, None)` or
        `Forwarder.with_wrappers(None, default_resolver, None)`.
        
        :param input_wrapper: The input wrapper the new instance will use. If
            not specified, the default resolver will be used.
        :return: A new `Forwarder` instance with the given wrapper.
        """
        input_wrapper = input_wrapper or default_resolver
        return self.with_wrappers(input_wrapper=input_wrapper)

    @cache
    def with_wrappers(
            self,
            return_wrapper: Callable | None = None,
            input_wrapper: Callable | None = None,
            resolver: Callable | None = None
        ) -> 'Forwarder':
        """Create a copy of this `Forwarder` instance, with the specified
        wrappers, and resolver.

        :param return_wrapper: If provided, the new instance will use this as
            the return wrapper.
        :param input_wrapper: If provided, the new instance will use this as
            the input wrapper.
        :param resolver: If provided, the new instance will use this as the
            resolver.
        :return: A new `Forwarder` instance with the given wrappers and
            resolver.
        """
        return_wrapper = return_wrapper or self._get_wrap
        input_wrapper = input_wrapper or self._set_wrap
        resolver = resolver or self._resolve
        return type(self)(return_wrapper, input_wrapper, resolver)
    
    def __call__(self, func: Callable | property) -> Callable | property:
        """Wrap a method or property as a new method or property. Using the
        resolver, input wrapper, and return wrappers specified at `Forwarder`
        creation:
        - The target instance is found using the resolver.
        - Input values to properties are converted using the input wrapper.
        - The return value is converted using the return wrapper.

        :param func: The method or property to forward to.
        :return: A new method or property, forwarding to `func`.
        """
        if isinstance(func, property):
            return self.forward_property(func)
        else:
            return self.forward_method(func)
forward = Forwarder()


class DataViewItemAttr(_AComponent):
    # Never instantiated by users, only wrapped
    _wx_widget_type: dv.DataViewItemAttr
    _native_widget: dv.DataViewItemAttr

    @staticmethod
    def color_to_rgba(color: RGBA | Color) -> RGBA:
        if isinstance(color, Color):
            return color.to_rgba_tuple()
        # Already an RGBA tuple
        return color

    # Item attributes
    bold = forward(dv.DataViewItemAttr.Bold)
    color = forward.with_wrappers(Color.from_wx, color_to_rgba)(
        dv.DataViewItemAttr.Colour)
    italic = forward(dv.DataViewItemAttr.Italic)
    background_color = forward.with_wrappers(Color.from_wx, color_to_rgba)(
        dv.DataViewItemAttr.BackgroundColour)
    strikethrough = forward(
        property(None, dv.DataViewItemAttr.SetStrikethrough))
    font = forward(property(dv.DataViewItemAttr.GetEffectiveFont))

    # Test if default attributes have been changed from defaults.
    is_default = forward(property(dv.DataViewItemAttr.IsDefault))
    has_color = forward(property(dv.DataViewItemAttr.HasColour))
    has_background_color = forward(
        property(dv.DataViewItemAttr.HasBackgroundColour))
    has_font = forward(property(dv.DataViewItemAttr.HasFont))


class _DataViewModel(dv.PyDataViewModel):
    def __init__(self, parent=None) -> None:
        # parent parameter provided to work with _AComponent, even though
        # dv.PyDataViewModel doesn't derive from wx.Window.
        super().__init__()

    def _set_amodel(self, model: 'ADataViewModel') -> None:
        # ADataViewModel constructs this object before its construction is
        # complete, so we cannot set this during this object's constructor.
        self._model = model

    weak_refs = property(
        None,
        forward(dv.PyDataViewModel.UseWeakRefs)
    )

    # Helper methods for converting to<->from wx types
    def wrap(self, py_object: Any) -> dv.DataViewItem:
        return (dv.NullDataViewItem if py_object is None
                else self.ObjectToItem(py_object))

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
    def GetChildren(
            self,
            parent: dv.DataViewItem,
            children: dv.DataViewItemArray
        ) -> int:
        i = 0
        for i, child in enumerate(self._model.get_children(
                                  self.unwrap(parent)), start=1):
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

    def GetAttr(
            self,
            item: dv.DataViewItem,
            column: int,
            attributes: dv.DataViewItemAttr
        ) -> bool:
        return self._model.get_attributes(self.unwrap(item), column,
            DataViewItemAttr.from_native(attributes))

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
        raise TypeError(
            f'DataViewModel: Unsupported column type {col_type!r}.')


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

    def get_attributes(
            self,
            item: Any,
            column: int,
            attributes: DataViewItemAttr
        ) -> bool:
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
        self._native_widget.ValueChanged(
            self._native_widget.wrap(item),
            column
        )

    def notify_item_added(self, parent: Any, item: Any) -> None:
        self._native_widget.ItemAdded(
            self._native_widget.wrap(parent),
            self._native_widget.wrap(item)
        )

    def notify_item_deleted(self, parent: Any, item: Any) -> None:
        self._native_widget.ItemDeleted(
            self._native_widget.wrap(parent),
            self._native_widget.wrap(item),
        )

    def notify_item_changed(self, item: Any) -> None:
        self._native_widget.ItemChanged(
            self._native_widget.wrap(item)
        )

    def notify_cleared(self) -> None:
        self._native_widget.Cleared()

    def notify_items_added(self, parent: Any, items: Iterable[Any]) -> None:
        self._native_widget.ItemsAdded(
            self._native_widget.wrap(parent),
            self._native_widget.wrap_list(items)
        )

    def notify_items_deleted(self, parent: Any, items: Iterable[Any]) -> None:
        self._native_widget.ItemsDeleted(
            self._native_widget.wrap(parent),
            self._native_widget.wrap_list(items)
        )

    def notify_items_changed(self, items: Iterable[Any]) -> None:
        self._native_widget.ItemsChanged(
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
    selected = forward.with_return(Optional[DataViewColumn.from_native])(
        property(dv.DataViewCtrl.GetCurrentColumn))
    expander = forward.with_wrappers(Optional[DataViewColumn.from_native],
        default_resolver)(dv.DataViewCtrl.ExpanderColumn)

    sorter = forward.with_return(Optional[DataViewColumn.from_native])(
        property(Optional[DataViewColumn.from_native]))

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
            return DataViewColumn.from_native(
                method(self._native_widget, *args, **kwargs))
        else:
            # Generic column append/prepend method with an already existing
            # DataViewColumn object
            # Quick way to extract the 'col' arg from *args, **kwargs
            def get_column_arg(col):
                return col
            col = get_column_arg(*args, **kwargs)
            # TODO: Check if dv.DataViewColumn derives from wx.Window
            # if it doesn't, we can't use _resolve
            if method(self._native_widget, _AComponent._resolve(col)):
                return col
            else:
                return None

    def append(self, *args, **kwargs) -> DataViewColumn | None:
        return self._insert_column(_ColumnInsert.Append, *args, **kwargs)

    def prepend(self, *args, **kwargs) -> DataViewColumn | None:
        return self._insert_column(_ColumnInsert.Prepend, *args, **kwargs)

    def insert(self, position: int, column: DataViewColumn) -> bool:
        return self._native_widget.InsertColumn(
            position, _AComponent._resolve(column))

    clear = forward(dv.DataViewCtrl.ClearColumns)
    __delitem__ = forward(dv.DataViewCtrl.DeleteColumn)
    __getitem__ = forward.with_return(DataViewColumn.from_native)(
        dv.DataViewCtrl.GetColumn)
    __len__ = forward(dv.DataViewCtrl.GetColumnCount)
    index = forward.with_input()(dv.DataViewCtrl.GetColumnPosition)


class _DataViewOptions:
    # Wrapper around a DataViewCtrl's UI configuration options.

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

    def _set_selection(self, new_selection: Iterable[Any] | Any) -> None:
        if new_selection:
            try:
                items = self._widget._wrap_list(new_selection)
            except TypeError: # Not iterable
                items = self._widget._wrap_list([new_selection])
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
    default_item_attributes = forward(
        property(dv.DataViewCtrl.GetClassDefaultAttributes))
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
