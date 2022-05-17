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
"""Concrete DataViewModel classes for use in with DataViewCtrls."""
from __future__ import annotations

__author__ = u'Lojack'

from dataclasses import dataclass
from enum import auto, Enum, IntEnum
from functools import partial
from pathlib import Path
from typing import Dict, List, Iterable, Tuple

import wx

from .checkables import RadioButton
from .dataview import ADataViewModel, DataViewColumnType, DataViewItemAttr, \
    DataViewCtrl
from .layouts import HLayout, LayoutOptions, VLayout
from .top_level_windows import PanelWin

from ..bolt import round_size
from ..localize import format_date


__all__ = [
    'InstallerViewData',
    'InstallerTreeViewModel',
    'InstallerFlatViewModel',
    'InstallerViewCtrl',
]


@dataclass
class _ItemData:
    destination: Path
    source: Path
    size: int
    mtime: float
    crc: int
    status: 'InstallerViewData.ItemStatus'


class _DirectoryData(_ItemData):
    pass


class InstallerViewData:
    class ItemStatus(Enum):
        Matched = 'Installed'
        Missing = 'Missing'
        Overridden = 'Overridden'
        Mismatched = 'Mismatched'
        Skipped = 'Skipped'

    _install_directory = Path('Data')
    _conflicts_node = Path('conflicts')
    _skips_node = Path('skipped')

    def __init__(
            self,
            installers_data: 'InstallersData',
            installer: 'Installer' | None = None,
        ) -> None:
        self._idata = installers_data
        self._installer = installer
        self._data: Dict[Path, _ItemData] = dict()
        self._top_nodes: List[Path] = []
        self.scan()

    def __contains__(self, item: Path) -> bool:
        return item in self._data

    def __getitem__(self, item: Path) -> _ItemData:
        return self._data[item]

    def __iter__(self):
        return iter(self._data)

    @property
    def top_nodes(self) -> List[Path]:
        return self._top_nodes

    @property
    def installer(self) -> 'Installer':
        return self._installer
    
    @installer.setter
    def installer(self, installer: 'Installer') -> None:
        changed = self.installer != installer
        self._installer = installer
        if changed:
            self.scan()

    def scan(self) -> None:
        self._top_nodes = []
        self._data = {}
        installer = self.installer
        if not installer or installer.is_marker:
            return
        # Gather conflicts
        from .. import bosh
        ini_origin_match = self._idata._ini_origin.match
        active_bsas, bsa_cause = bosh.modInfos.get_active_bsas()
        lower_loose, higher_loose, lower_bsa, higher_bsa = \
            self._idata.find_conflicts(
            installer, active_bsas, bsa_cause, True, False, False, True
        )
        def _get_conflicts(loose_files, bsas):
            conflicts = {
                source_file: conflicting_installer
                for conflicting_installer, _package, installer_conflicts
                    in loose_files
                for source_file in installer_conflicts
            }
            for bsa_origin, conflicting_bsa, bsa_conflicts in bsas:
                if (match := ini_origin_match(bsa_origin)):
                    m1 = match.group(1)
                    m2 = match.group(2)
                else:
                    m1 = active_bsas[conflicting_bsa]
                    m2 = bsa_origin
                conflicts |= {source_file: (m1, m2, conflicting_bsa)
                              for source_file in bsa_conflicts}
            return conflicts
        # Overrides, underrides
        overrides = _get_conflicts(higher_loose, higher_bsa)
        underrides = _get_conflicts(lower_loose, lower_bsa)
        # Skips (TODO)
        skips = {Path(dest): 'ext' for dest in installer.skipExtFiles}
        skips |= {Path(dest): 'dir' for dest in installer.skipDirFiles}
        # Configured items
        matched = (set(installer.ci_dest_sizeCrc)
                   - installer.missingFiles
                   - installer.mismatchedFiles)
        # And build the view data
        data_root = self._install_directory
        skip_root = self._skips_node
        for dest, (size, crc) in installer.ci_dest_sizeCrc.items():
            if dest in overrides:
                status = self.ItemStatus.Overridden
                installed_source = f'{overrides[dest]}'
            elif dest in installer.missingFiles:
                status = self.ItemStatus.Missing
                installed_source = ''
            elif dest in installer.mismatchedFiles:
                status = self.ItemStatus.Mismatched
                if dest in underrides:
                    installed_source = f'{underrides[dest]}'
                else:
                    # TODO: Get installer source for mismatched files in
                    # uninstalled installers? like underrides, but this
                    # installer isn't configured to install
                    installed_source = ''
            else:
                status = self.ItemStatus.Matched
                installed_source = f'{installer.archive}'
            self._data[data_root / dest] = _ItemData(
                Path(dest), installed_source, size, 0, crc, status)
        if installer.ci_dest_sizeCrc:
            self._data[data_root] = _DirectoryData(
                data_root, Path(''), installer.unSize, installer.modified,
                installer.crc, self.ItemStatus.Matched)
            self._top_nodes.append(data_root)
        for skip, reason in skips:
            self._data[skip_root / skip] = _ItemData(
                skip, Path(reason), 0, 0, 0, self.ItemStatus.Skipped)
        if skips:
            self._top_nodes.append(skip_root)
        # Build tree branch nodes
        parents = {parent
                    for path in self._data
                    for parent in path.parents
        } - {data_root, Path('.')}
        for parent in parents:
            children = (path for path in self._data
                        if path.is_relative_to(parent))
            size = sum(self._data[child].size for child in children
                       if not isinstance(self._data[child], _DirectoryData))
            self._data[parent] = _DirectoryData(
                parent, Path(''), size, 0, 0, self.ItemStatus.Matched)


class InstallerTreeViewModel(ADataViewModel):
    class Columns(IntEnum):
        Destination = 0
        Source = auto()
        Size = auto()
        Crc = auto()
        Mtime = auto()
        Status = auto()

    _columns = {
        Columns.Destination: lambda item_data: item_data.destination.name,
        Columns.Source: lambda item_data: f'{item_data.source}',
        Columns.Size: lambda item_data: round_size(item_data.size),
        Columns.Mtime: lambda item_data: format_date(item_data.mtime),
        Columns.Crc: lambda item_data: f'{item_data.crc:08X}',
        Columns.Status: lambda item_data: item_data.status.value,
    }
    _folder_columns = {Columns.Destination, Columns.Size}
    _data_colunns = {
        Columns.Destination,
        Columns.Crc,
        Columns.Mtime,
        Columns.Size,
    }

    def __init__(self, installer_view_data: InstallerViewData) -> None:
        super().__init__()
        self._iview_data = installer_view_data
        img_size = (16, 16)
        self._image_list = wx.ImageList(*img_size)
        self._images: Dict[str, int] = {
            'folder': self._image_list.Add(wx.ArtProvider.GetIcon(
                wx.ART_FOLDER, wx.ART_OTHER, img_size)),
            'file': self._image_list.Add(wx.ArtProvider.GetIcon(
                wx.ART_NORMAL_FILE, wx.ART_OTHER, img_size)),
        }

    # DataViewModel methods
    def get_children(self, parent: Path | None) -> Iterable[Path]:
        if not parent:
            return self._iview_data.top_nodes
        return (item for item in self._iview_data if item.parent == parent)

    def is_container(self, parent: Path | None) -> bool:
        return parent is None or isinstance(self._iview_data[parent],
                                            _DirectoryData)

    def get_parent(self, item: Path) -> Path | None:
        if item in self._iview_data:
            return item.parent
        return None
    
    def has_value(self, item: Path | None, column: int) -> bool:
        if not item:
            return False
        if item is self._iview_data._install_directory:
            return column in self._data_colunns
        if isinstance(self._iview_data[item], _DirectoryData):
            return column in self._folder_columns
        return True

    def get_value(self, item: Path, column: int) -> str:
        item_data = self._iview_data[item]
        if column == self.Columns.Destination:
            text = self._columns[column](self._iview_data[item])
            if isinstance(item_data, _DirectoryData):
                icon_key = 'folder'
            else:
                icon_key = 'file'
            icon = self._image_list.GetIcon(self._images[icon_key])
            from wx import dataview as dv
            return dv.DataViewIconText(text, icon)
        return self._columns[column](item_data)

    # set_value -> don't override, this is a read-only view

    def get_column_count(self) -> int:
        return len(self._columns)

    def get_column_type(self, column: int) -> type:
        return str

    def get_attributes(
            self,
            item: Path,
            column: int,
            attributes: DataViewItemAttr
        ) -> bool:
        if not item:
            return False
        if column == self.Columns.Destination:
            item_data = self._iview_data[item]
            statuses = self._iview_data.ItemStatus
            if item_data.status is statuses.Mismatched:
                attributes.color = (255, 0, 0)
                return True
            if item_data.status is statuses.Skipped:
                attributes.italic = True
                return True
            if item_data.status is statuses.Overridden:
                attributes.color = (0, 255, 0)
                return True
        # No attributes changed
        return False


class InstallerFlatViewModel(InstallerTreeViewModel):
    # Override some InstallerTreeViewModel methods to
    # present the items as a semi-flat view.
    @staticmethod
    def _format_destination_flat(item_data: _ItemData) -> str:
        return f'{item_data.destination}'

    _columns = InstallerTreeViewModel._columns.copy()
    _columns[InstallerTreeViewModel.Columns.Destination] = \
        _format_destination_flat

    def get_children(self, parent: Path | None) -> Iterable[Path]:
        if not parent:
            return self._iview_data.top_nodes
        return (item for item in self._iview_data
                if not isinstance(self._iview_data[item], _DirectoryData)
                   and item.is_relative_to(parent))

    def get_parent(self, item: Path) -> Path | None:
        if item in self._iview_data:
            for parent in self._iview_data.top_nodes:
                if item.is_relative_to(parent):
                    return parent
        return None


class InstallerViewCtrl(PanelWin):
    class ViewMode(Enum):
        Tree = auto()
        Flat = auto()

    def __init__(
            self,
            parent,
            installer_view_data: InstallerViewData,
            view_mode: ViewMode = ViewMode.Tree,
            expand_top: bool = True,
        ) -> None:
        super().__init__(parent)
        self._view_mode = None
        self._expand_top = expand_top
        # Data models
        self._iview_data = installer_view_data
        self._models: Dict[InstallerViewCtrl.ViewMode, InstallerTreeViewModel] = {
            self.ViewMode.Tree: InstallerTreeViewModel(installer_view_data),
            self.ViewMode.Flat: InstallerFlatViewModel(installer_view_data),
        }
        # View toggles
        self._radio_tree = radio_tree = RadioButton(
            self, _('Tree View'), is_group=True)
        radio_tree.is_checked = view_mode is self.ViewMode.Tree
        radio_tree.on_checked.subscribe(self._on_radio_tree)
        self._radio_flat = radio_flat = RadioButton(self, _('Flat View'))
        radio_flat.is_checked = view_mode is not self.ViewMode.Tree
        radio_flat.on_checked.subscribe(self._on_radio_flat)
        # View control
        self._view_control = DataViewCtrl(self)
        text_column = partial(
            self._view_control.columns.append,
            column_type=DataViewColumnType.TEXT
        )
        col_names = self._models[self.ViewMode.Tree].Columns
        self._view_control.columns.append(
            _('Destination'), col_names.Destination,
            column_type=DataViewColumnType.ICON_TEXT)
        text_column(_('Status'), col_names.Status)
        text_column(_('Size'), col_names.Size, align=wx.ALIGN_RIGHT)
        text_column(_('CRC'), col_names.Crc, align=wx.ALIGN_RIGHT)
        text_column(_('Installed Source'), col_names.Source)
        text_column(_('Modified'), col_names.Mtime, align=wx.ALIGN_RIGHT)
        # Save view_mode and associate correct model to the control
        self.view_mode = view_mode
        # Setup layout
        VLayout(items=[
            HLayout(items=[radio_tree, radio_flat]),
            (self._view_control, LayoutOptions(expand=True, weight=1)),
        ]).apply_to(self)

    def set_installer(self, installer: 'Installer') -> None:
        with self.pause_drawing():
            self._iview_data.installer = installer
            self._refresh_and_expand()

    def _refresh_and_expand(self) -> None:
        self._models[self.view_mode].notify_cleared()
        data_key = self._iview_data._install_directory
        if data_key in self._iview_data:
            self.view.expand_item(data_key)

    @property
    def radios(self) -> Tuple[RadioButton, RadioButton]:
        return self._radio_tree, self._radio_flat

    @property
    def view(self) -> DataViewCtrl:
        return self._view_control

    @property
    def view_mode(self) -> ViewMode:
        return self._view_mode

    def _on_radio_tree(self, checked: bool) -> None:
        self.view_mode = self.ViewMode.Tree

    def _on_radio_flat(self, checked: bool) -> None:
        self.view_mode = self.ViewMode.Flat

    @view_mode.setter
    def view_mode(self, new_mode: ViewMode) -> None:
        if not isinstance(new_mode, self.ViewMode):
            raise TypeError(f'Expected {self.ViewMode.__name__}, '
                            f'not {type(new_mode)}.')
        changed = new_mode is not self.view_mode
        self._view_mode = new_mode
        if changed:
            self.view.associate_model(self._models[self.view_mode])
            self._refresh_and_expand()
