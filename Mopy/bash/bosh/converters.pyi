

from collections import defaultdict
from typing import Any, Literal, TypeAlias, TypeVar
from ..bolt import DataDict, Path, PickleDict, Progress
from . import InstallerConverter as boshInstallerConverter
from . import InstallerArchive as boshInstallerArchive
from . import InstallerProject as boshInstallerProject

Installer: TypeAlias = boshInstallerArchive | boshInstallerProject


_CInstallerConverter = TypeVar('_CInstallerConverter', bound='InstallerConverter')

converters_dir: Path | None
installers_dir: Path | None


class ConvertersData(DataDict):
    dup_bcfs_dir: Path
    corrupt_bcfs_dir: Path
    converterFile: PickleDict   # [?]
    srcCRC_converters: defaultdict[int, list[InstallerConverter]]
    bcfCRC_converter: dict[int, InstallerConverter]
    bcfPath_sizeCrcDate: dict[Path, tuple[int, int, int]]

    def __init__(self, bain_data_dir: Path, converters_dir_: Path,
        dup_bcfs_dir: Path, corrupt_bcfs_dir: Path) -> None: ...

    def load(self) -> Literal[True]: ...
    def save(self) -> None: ...

    ##
    @staticmethod
    def validConverterName(fn_conf) -> bool: ...
    def refreshConverters(self, progress: Progress | None = ..., fullRefresh: bool = ...) -> bool: ...
    def addConverter(self, converter: InstallerConverter, update_cache: bool = ...) -> Literal[True]: ...
    def removeConverter(self, oldConverter: InstallerConverter | Path | None) -> None: ...

class InstallerConverter:
    srcCRCs: set    # [?]
    crc: int | None
    fullPath: Path
    volatile: list[str]
    addedSettings: list[str]
    dupeCount: dict #[?, ?]
    isSolid: bool

    @classmethod
    def from_path(cls: type[_CInstallerConverter], full_path: Path, cached_crc: int | None = ...) -> _CInstallerConverter: ...
    ##
    @classmethod
    def from_scratch(cls: type[_CInstallerConverter], srcArchives, idata, destArchive, BCFArchive, blockSize: int, progress: Progress) -> _CInstallerConverter: ...

    def __getstate__(self) -> tuple: ...    #[?]
    def __setstate__(self, values: tuple) -> None: ... #[?]
    def __reduce__(self) -> tuple[
        type[boshInstallerConverter],
        tuple[()],
        tuple[Any, ...], # Any = ?
    ]: ...

    def load(self, fullLoad: bool = ...) -> None: ...
    def save(self, destInstaller: Installer) -> None: ...
    ##
    def apply(self, destArchive, crc_installer: int, progress: Progress | None = ..., embedded: int = ...) -> None: ...
    def applySettings(self, destInstaller: Installer) -> None: ...
    def build(self, srcArchives, idata, destArchive, BCFArchive, blockSize: int, progress: Progress | None = ..., *, __read_ext: tuple[str] = ...) -> None: ...
