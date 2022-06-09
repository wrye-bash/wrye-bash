from typing import Callable, ClassVar, Literal, TypeAlias, overload

from ..bolt import AFile, Log, Path, StrPath, _SupportsRead, _SupportsWrite


_ParseSavePath: TypeAlias = Callable[[str], tuple[tuple, tuple]]



class _Remappable:
    def remap_plugins(self, plugin_renames: dict[str, str]) -> None: ...

class _Dumpable:
    def dump_to_log(self, log: Log, save_masters_: dict[int, str]) -> None: ...

class _AHeader:
    savefile_tag: str

    def __init__(self, ins: _SupportsRead, cosave_name: Path) -> None: ...

class _AChunk:
    def write_chunk(self, out: _SupportsWrite) -> None: ...

class ACosave(_Dumpable, _Remappable, AFile):
    cosave_ext: ClassVar[str]
    parse_save_path: ClassVar[_ParseSavePath]

    cosave_header: _AHeader
    cosave_chunks: list[_AChunk]
    remappable_chunks: list[_Remappable]
    loading_state: int

    def __init__(self, cosave_path: StrPath) -> None: ...
    def read_cosave(self, light: bool = ...) -> None: ...
    def write_cosave(self, out_path: Path) -> None: ...
    def write_cosave_safe(self, out_path: Path = ...) -> None: ...

    def get_master_list(self) -> list[str]: ...
    def has_accurate_master_list(self) -> bool: ...
    # save_masters_ probably works as dict[str, StrPath], the str
    # value is only ever used in string formatting.
    def dump_to_log(self, log: Log, save_masters_: dict[int, str]) -> None: ...

    @classmethod
    def get_cosave_path(cls, save_path: Path) -> Path: ...


class xSECosave(ACosave): ...
class PluggyCosave(ACosave):
    save_game_ticks: int

@overload
def get_cosave_types(
    game_fsName: Literal['Oblivion'],
    parse_save_path: _ParseSavePath,
    cosave_tag: str,
    cosave_ext: str,
) -> list[type[xSECosave] | type[PluggyCosave]]: ...
@overload
def get_cosave_types(
    game_fsName: str,
    parse_save_path: _ParseSavePath,
    cosave_tag: str,
    cosave_ext: str,
) -> list[type[xSECosave]]: ...
