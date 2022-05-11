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

from typing import Any, Callable, Iterable, Dict, Tuple, List
import os
from pathlib import Path
from enum import Enum, IntEnum, auto
from dataclasses import dataclass

from .dataview import ADataViewModel

from ..bolt import round_size
from ..localize import format_date


__all__ = [
    'InstallerViewModel',
]


class InstallerViewModel(ADataViewModel):
    class Columns(IntEnum):
        Destination = 0
        Source = auto()
        Size = auto()
        Crc = auto()
        Mtime = auto()
        Status = auto()

    class ViewMode(Enum):
        Tree = auto()
        Flat = auto()

    class ItemStatus(Enum):
        Matched = 'Installed'
        Missing = 'Missing'
        Overridden = 'Overridden'
        Mismatched = 'Mismatched'

    @dataclass
    class ItemData:
        destination: Path
        source: Path
        size: int
        mtime: float
        crc: int
        status: InstallerViewModel.ItemStatus

    class DirectoryData(ItemData):
        pass

    _columns = {
        Columns.Destination: lambda item_data: item_data.destination.name,
        Columns.Source: lambda item_data: f'{item_data.source}',
        Columns.Size: lambda item_data: round_size(item_data.size),
        Columns.Mtime: lambda item_data: format_date(item_data.mtime),
        Columns.Crc: lambda item_data: f'{item_data.crc:08X}',
        Columns.Status: lambda item_data: item_data.status.value,
    }
    _folder_columns = {Columns.Destination, Columns.Size}

    _install_directory = Path('Data')
    _conflicts_node = Path('conflicts')
    _skips_node = Path('skipped')

    def __init__(
            self,
            installers_data: 'InstallersData',
            installer: 'Installer' | None = None,
            view_mode: ViewMode = ViewMode.Tree
        ) -> None:
        super().__init__()
        self._idata = installers_data
        self._installer = installer
        self.scan()
        self._view_mode = view_mode
        self._data: Dict[Path, InstallerViewModel.ItemData] = {}
        self._top_nodes: List[Path] = []

    @property
    def view_mode(self) -> ViewMode:
        return self._view_mode

    @view_mode.setter
    def view_mode(self, new_mode: ViewMode) -> None:
        if not isinstance(new_mode, self.ViewMode):
            raise TypeError(f'Expected {self.ViewMode.__name__}, not {type(new_mode)}.')
        scan_needed = new_mode is not self.view_mode
        self._view_mode = new_mode
        if scan_needed:
            self.scan()
    
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
        # Clear the UI of old data
        self.notify_cleared()
        installer = self.installer
        if not installer or installer.is_marker:
            return
        # Gather conflicts
        from .. import bosh
        ini_origin_match = self._idata._ini_origin.match
        active_bsas, bsa_cause = bosh.modInfos.get_active_bsas()
        lower_loose, higher_loose, lower_bsa, higher_bsa = self._idata.find_conflicts(
            installer, active_bsas, bsa_cause, True, False, False, True
        )
        def _get_conflicts(loose_files, bsas):
            conflicts = {
                source_file: conflicting_installer
                for conflicting_installer, _package, installer_conflicts in loose_files
                for source_file in installer_conflicts
            }
            for bsa_origin, conflicting_bsa, bsa_conflicts in bsas:
                if (match := ini_origin_match(bsa_origin)):
                    m1 = match.group(1)
                    m2 = match.group(2)
                else:
                    m1 = active_bsas[conflicting_bsa]
                    m2 = bsa_origin
                conflicts |= {source_file: (m1, m2, conflicting_bsa) for source_file in bsa_conflicts}
            return conflicts
        # Overrides, underrides
        overrides = _get_conflicts(higher_loose, higher_bsa)
        underrides = _get_conflicts(lower_loose, lower_bsa)
        # Skips (TODO)
        skips = {Path(dest): 'ext' for dest in installer.skipExtFiles}
        skips |= {Path(dest): 'dir' for dest in installer.skipDirFiles}
        # Configured items
        matched = set(installer.ci_dest_sizeCrc) - installer.missingFiles - installer.mismatchedFiles
        # And build the view data
        if self.view_mode is self.ViewMode.Tree:
            # Tree view
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
                        # TODO: Get installer source for mismatched files in uninstalled installers?
                        # like underrides, but this installer isn't configured to install
                        installed_source = ''
                else:
                    status = self.ItemStatus.Matched
                    installed_source = f'{installer.archive}'
                self._data[data_root / dest] = self.ItemData(Path(dest), installed_source, size, 0, crc, status)
            if installer.ci_dest_sizeCrc:
                self._data[data_root] = self.DirectoryData(data_root, Path(''), installer.unSize, installer.modified, installer.crc, self.ItemStatus.Matched)
                self._top_nodes.append(data_root)
            for skip, reason in skips:
                self._data[skip_root / skip] = self.ItemData(skip, Path(reason), 0, 0, 0, self.ItemStatus.Missing)
            if skips:
                self._top_nodes.append(skip_root)
            # Build tree branch nodes
            parents = {parent
                       for path in self._data
                       for parent in path.parents
            } - {data_root, Path('.')}
            for parent in parents:
                children = (path for path in self._data if path.is_relative_to(parent))
                size = sum(self._data[child].size for child in children if not isinstance(self._data[child], self.DirectoryData))
                self._data[parent] = self.DirectoryData(parent, Path(''), size, 0, 0, self.ItemStatus.Matched)
        else:
            # TODO: Flat view
            pass
        # Notify UI of new data.
        self.notify_cleared()

    # DataViewModel methods
    def get_children(self, parent: Path | None) -> Iterable[Path]:
        if not parent:
            return self._top_nodes
        return (item for item in self._data if item.parent == parent)

    def is_container(self, parent: Path | None) -> bool:
        return parent is None or isinstance(self._data[parent], self.DirectoryData)

    def get_parent(self, item: Path) -> Path | None:
        if item in self._data:
            return item.parent
        return None
    
    def has_value(self, item: Path | None, column: int) -> bool:
        if not item:
            return False
        if item is self._install_directory:
            return column in {self.Columns.Destination, self.Columns.Crc, self.Columns.Mtime, self.Columns.Size}
        if isinstance(self._data[item], self.DirectoryData):
            return column in self._folder_columns
        return True

    def get_value(self, item: Path, column: int) -> str:
        return self._columns[column](self._data[item])

    # set_value -> don't override, this is a read-only view

    def get_column_count(self) -> int:
        return len(self._columns)

    def get_column_type(self, column: int) -> type:
        return str
