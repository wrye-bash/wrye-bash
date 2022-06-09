from typing import ClassVar
from ..bolt import Path, Flags, _SupportsRead

from . import AFile


# Unsure how much of the _ classes need typing, but these are the ones
# accessible through DDSFile, and are accessed in bsa_files
class _DDSPixelFormat:
    pf_size: int
    pf_flags: Flags
    pf_four_cc: bytes
    pf_rgb_bit_count: int
    pf_r_bit_mask: int
    pf_g_bit_mask: int
    pf_b_bit_mask: int
    pf_a_bit_mask: int

    def __init__(self) -> None: ...
    @property
    def nees_dxt10(self) -> bool: ...
    def load_format(self, ins: _SupportsRead) -> None: ...
    def dump_format(self) -> bytes: ...

class _DXGIFormat:
    index_to_fmt: ClassVar[dict[int, _DXGIFormat]]

    @property
    def fmt_index(self) -> int: ...
    def setup_file(self, dds_file: DDSFile, use_legacy_formats: bool = ...) -> None: ...

class _DDSHeader:
    dds_magic: bytes
    dw_size: int
    dw_flags: Flags | int
    dw_height: int
    dw_width: int
    dw_pitch_or_linear_size: int
    dw_depth: int
    dw_mip_map_count: ...
    dw_reserved1: list[int]
    ddspf: _DDSPixelFormat
    dw_caps: Flags | int
    dw_caps2: Flags | int
    dw_caps3: int       # Probably Flags | int, but not handled in _set_flags
    dw_caps4: int       # Probably Flags | int, but not handled in _set_flags
    dw_reserved2: int

    def load_header(self, ins: _SupportsRead): ...
    def dump_header(self) -> bytes: ...

class _DDSHeaderDXT10:
    dxgi_format: _DXGIFormat
    resource_dimension: int
    misc_flag: int
    array_size: int
    misc_flags2: int

    def dump_header(self) -> bytes: ...

class DDSFile(AFile):
    dds_header: _DDSHeader
    dds_dxt10: _DDSHeaderDXT10
    dds_contents: bytes

    def load_file(self) -> None: ...
    def load_from_stream(self, ins: _SupportsRead) -> None: ...
    def dump_file(self) -> bytes: ...
    def write_file(self, out_path: Path | None = ...) -> None: ...
    def write_file_safe(self, out_path: Path | None = ...) -> None: ...

def mk_dxgi_fmt(fmt_index: int): ...
