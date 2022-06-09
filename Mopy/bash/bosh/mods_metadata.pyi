from typing import Iterable, TypeAlias

from ..basher.frames import PluginChecker
from ..bolt import FName, _Packer, _Unpacker

from . import ModInfo, ModInfos


_FormID_long: TypeAlias = tuple[str, int]
_FormID_short: TypeAlias = int
_FormID: TypeAlias = _FormID_long | _FormID_short


def get_tags_from_dir(
    plugin_name: FName,
    ci_cached_bt_contents: set[str] | None = ...,
) -> tuple[set[str], set[str]]: ...

def save_tags_to_dir(
    plugin_name: FName,
    plugin_tag_diff: tuple[set[str], set[str]],
) -> None: ...

def diff_tags(
    plugin_new_tags: set[str],
    plugin_old_tags: set[str],
) -> tuple[set[str], set[str]]: ...

def checkMods(
    mc_parent: PluginChecker,
    modInfos: ModInfos,
    showModList: bool = ...,
    showCRC: bool = ...,
    showVersion: bool = ...,
    scan_pluigins: bool = ...,
) -> str: ...

##
class NVidiaFogFixer:
    modInfo: ModInfo
    fixedCells: set[_FormID]

    def __init__(self, modInfo: ModInfo) -> None: ...
    #
    def fog_fix(
        self,
        progress,
        __unpacker: _Unpacker = ...,
        __wrld_types: Iterable[bytes] = ...,
        __packer: _Packer = ...,
    ) -> None: ...
