

from collections import OrderedDict
from typing import ClassVar, Iterable, Literal, TypeAlias, overload

from ..bolt import AFile, Flags, Progress, ReadableBuffer


path_sep: str

class _Header:
    formats: ClassVar[list[tuple[str, int]]]
    bsa_magic: ClassVar[bytes]
    file_id: bytes
    version: int

    def load_header(self, ins: ReadableBuffer, bsa_name: str) -> None: ...

class BsaHeader(_Header):
    folder_records_offset: int
    archive_flags: Flags
    folder_count: int
    file_count: int
    total_folder_name_length: int
    total_file_name_length: int
    file_flags: int
    header_size: ClassVar[int]

    def is_compressed(self) -> bool: ...
    def embed_filenames(self) -> bool: ...

class Ba2Header(_Header):
    ba2_file_types: bytes
    ba2_num_files: int
    ba2_name_table_offset: int
    file_types: set[bytes]
    header_size: ClassVar[int]

class MorrowindBsaHeader(_Header):
    hash_offset: int
    file_count: int

class OblivionBsaHeader(BsaHeader):
    def embed_filenames(self) -> Literal[False]: ...

class _HashedRecord:
    record_hash: int
    formats: ClassVar[list[tuple[str, int]]]

    def load_record(self, ins: ReadableBuffer) -> None: ...
    def load_record_from_buffer(
        self,
        memview: memoryview,
        start: int,
    ) -> int: ...

    @classmethod
    def total_record_size(cls: type[_HashedRecord]) -> int: ...
    def __eq__(self, other: _HashedRecord) -> bool: ...
    def __ne__(self, other: _HashedRecord) -> bool: ...
    def __hash__(self) -> int: ...
    def __lt__(self, other: _HashedRecord) -> bool: ...
    def __ge__(self, other: _HashedRecord) -> bool: ...
    def __gt__(self, other: _HashedRecord) -> bool: ...
    def __le__(self, other: _HashedRecord) -> bool: ...
    def __repr__(self) -> str: ...

class _BsaHashedRecord(_HashedRecord): ...
class BSAFolderRecord(_BsaHashedRecord): ...
class BSASkyrimSEFolderRecord(_BsaHashedRecord): ...

class BSAFileRecord(_BsaHashedRecord):
    file_size_flags: int
    raw_file_data_offset: int

    def compression_toggle(self) -> int: ...
    def raw_data_size(self) -> int: ...

class BSAMorrowindFileRecord(_HashedRecord):
    file_size: int
    relative_offset: int
    file_name: str

    def load_name(self, ins: ReadableBuffer, bsa_name: str) -> None: ...
    def load_name_from_buffer(
        self,
        memview: memoryview,
        start: int,
        bsa_name: str,
    ) -> None: ...
    def load_hash(self, ins: ReadableBuffer) -> None: ...
    def load_hash_from_buffer(
        self,
        memview: memoryview,
        start: int,
    ) -> None: ...

class BSAOblivionFileRecord(BSAFileRecord):
    file_size_flags: int
    raw_file_data_offset: int
    file_pos: int

class Ba2FileRecordGeneral(_BsaHashedRecord):
    file_extension: bytes
    dir_hash: int
    unknown1: int
    offset: int
    packed_size: int
    unpacked_size: int
    unused1: int

class Ba2FileRecordTexture(_BsaHashedRecord):
    file_extension: bytes
    dir_hash: int
    unknown_tex: int
    num_chuncks: int
    chunk_header_size: int
    heigth: int
    width: int
    num_mips: int
    dxgi_format: int
    cube_maps: int
    tex_chunks: int

class Ba2TexChunk:
    offset: int
    packed_size: int
    unpacked_size: int
    start_mip: int
    end_mip: int
    unused1: int

    def load_chunk(self, ins: ReadableBuffer) -> None: ...
    def __repr__(self) -> str: ...

class BSAFolder:
    folder_record: _BsaHashedRecord
    folder_assets: OrderedDict  # [?, ?]

    def __init__(self, folder_record: _BsaHashedRecord) -> None: ...

class Ba2Folder:
    folder_assets: OrderedDict  # [?, ?]

    def __init__(self) -> None: ...

class ABsa(AFile):
    bsa_name: str
    bsa_header: BsaHeader
    bsa_folders: OrderedDict # [?, ?]
    total_names_length: int

    def inspect_version(self) -> int: ...
    def extract_assets(
        self,
        asset_paths: Iterable[str],
        dest_folder: str,
        progress: Progress | None = ...,
    ) -> None: ...
    def has_assets(self, asset_paths: Iterable[str]) -> list[str]: ...
    @property
    def assets(self) -> frozenset[str]: ...

class BSA(ABsa):
    file_record_type: ClassVar[type[BSAFileRecord]]
    folder_record_type: ClassVar[type[BSAFolderRecord]]

class BA2(ABsa):
    def ba2_hash(self) -> int: ...

class MorrowindBsa(ABsa): ...

class OblivionBsa(BSA):
    file_record_type: ClassVar[type[BSAOblivionFileRecord]]

    @staticmethod
    def calculate_hash(file_name: bytes) -> int: ...
    def undo_alterations(self, progress: Progress = ...) -> int: ...

class SkyrimSeBsa(BSA):
    folder_record_type: ClassVar[type[BSASkyrimSEFolderRecord]]

_MorrowindBsaGames: TypeAlias = Literal['Morrowind']
_OblivionBsaGames: TypeAlias = Literal['Oblivion']
_BSAGames: TypeAlias = Literal['Enderal', 'Fallout3', 'FalloutNV', 'Skyrim']
_SkyrimSeBsaGames: TypeAlias = Literal[
    'Skyrim Special Editions', 'Skyrim VR', 'Enderal Special Edition',
    'Skyrim Special Edition MS',
]
_BA2Games: TypeAlias = Literal['Fallout4', 'Fallout4VR', 'Fallout4 MS']

@overload
def get_bsa_type(game_fsName: _MorrowindBsaGames) -> type[MorrowindBsa]: ...
@overload
def get_bsa_type(game_fsName: _OblivionBsaGames) -> type[OblivionBsa]: ...
@overload
def get_bsa_type(game_fsName: _BSAGames) -> type[BSA]: ...
@overload
def get_bsa_type(game_fsName: _SkyrimSeBsaGames) -> type[SkyrimSeBsa]: ...
@overload
def get_bsa_type(game_fsName: _BA2Games) -> type[BA2]: ...
@overload
def get_bsa_type(game_fsName: str) -> type[ABsa]: ...
