from collections import OrderedDict
from typing import ClassVar, Literal, NoReturn, TypeAlias, overload

from ..bolt import FName, ReadableBuffer, WriteableBuffer, _Packer, _Unpacker

from . import SaveInfo


_SkyrimGames: TypeAlias = Literal[
    'Enderal', 'Skyrim', 'Skyrim Special Edition', 'Skyrim VR',
    'Enderal Special Edition', 'Skyrim Special Edition MS',
]
_Fallout4Games: TypeAlias = Literal[
    'Fallout4', 'Fallout4VR', 'Fallout4 MS',
]


## save_headers public symbols
unpack_fstr16: _Unpacker

class SaveFileHeader:
    save_magic: ClassVar[str]
    unpackers: ClassVar[OrderedDict[str, tuple[_Packer, _Unpacker]]]
    
    # NOTE: some attributes are only valid in subclasses of SaveFileHeader
    header_size: int
    pcName: str
    pcLevel: int
    pcLocation: str
    ssWidth: int
    ssHeight: int
    masters: list[FName]
    ssData: bytearray
    gameDays: float
    gameTicks: int

    def __init__(self,
        save_inf: SaveInfo,
        load_image: bool = ...,
        ins: ReadableBuffer | None = ...,
    ) -> None: ...
    def read_save_header(
        self,
        load_image: bool = ...,
        ins: ReadableBuffer | None = ...
    ) -> None: ...
    def load_header(
        self,
        ins: ReadableBuffer,
        load_image: bool = ...,
    ) -> None: ...
    def dump_header(self, out: WriteableBuffer) -> None: ...
    def load_image_data(
        self,
        ins: ReadableBuffer,
        load_image: bool = ...,
    ) -> None: ...
    def calc_time(self) -> None: ...
    @property
    def has_alpha(self) -> bool: ...
    @property
    def image_loaded(self) -> bool: ...
    @property
    def image_parameters(self) -> tuple[int, int, bytearray, bool]: ...
    def writeMasters(
        self,
        ins: WriteableBuffer,
        out: ReadableBuffer
    ) -> list[bytes]: ...
    @property
    def can_edit_header(self) -> bool: ...

class OblivionSaveHeader(SaveFileHeader):
    major_version: int
    minor_version: int
    exe_time: bytes     # actually a SYSTEMTIME struct
    header_version: int
    saveNum: int
    gameTime: bytes     # actually a SYSTEMTIME struct
    ssSize: int

class SkyrimSaveHeader(SaveFileHeader):
    version: int
    saveNumber: int
    gameDate: bytes
    raceEid: bytes
    pcSex: int
    pcExp: float
    pcLvlExp: float
    filetime: bytes

class Fallout4SaveHeader(SkyrimSaveHeader): ...

class FalloutNVSaveHeader(SaveFileHeader):
    version: bytes
    language: bytes
    save_number: int
    pcNick: bytes
    gameDate: bytes

class Fallout3SaveHeader(FalloutNVSaveHeader):
    # NOTE: same as FalloutNVSaveHeader, but with `language` removed.
    # No good way to type this that preserves the class MRO and also indicate
    # the attribute doesn't exist, so marking it with NoReturn for now.
    # [NoReturn usually is for function return types to indicate they never
    # exit, either due to infinite loops or always raising.]
    language: NoReturn

class MorrowindSaveHeader(SaveFileHeader):
    # NOTE: only valid after load_header
    header_size: int
    pc_curr_health: float
    pc_max_health: float
    # Slightly different than SaveFileHeader.
    # See game\morrowind\records.MreTes3
    pcLevel: Literal[0]
    gameDays: Literal[0]
    gameTicks: Literal[0]
    ssData: bytes
    ssHeight: Literal[128]
    ssWidth: Literal[128]

@overload
def get_save_header_type(
    game_fsName: Literal['Oblivion'],
) -> type[OblivionSaveHeader]: ...
@overload
def get_save_header_type(
    game_fsName: _SkyrimGames,
) -> type[SkyrimSaveHeader]: ...
@overload
def get_save_header_type(
    game_fsName: _Fallout4Games,
) -> type[Fallout4SaveHeader]: ...
@overload
def get_save_header_type(
    game_fsName: Literal['FalloutNV'],
) -> type[FalloutNVSaveHeader]: ...
@overload
def get_save_header_type(
    game_fsName: Literal['Fallout3'],
) -> type[Fallout3SaveHeader]: ...
@overload
def get_save_header_type(
    game_fsName: Literal['Morrowind'],
) -> type[MorrowindSaveHeader]: ...
@overload
def get_save_header_type(
    game_fsName: str,
) -> type[SaveFileHeader]: ...
