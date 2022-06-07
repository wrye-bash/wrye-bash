from configparser import ConfigParser
from typing import Any, TypeAlias

import wx

from .bolt import Path, Settings

_BitmapId: TypeAlias = str | tuple[str, int]

active_locale: str
AppVersion: str
is_standalone: bool
wx_bitmap: dict[_BitmapId, wx.Bitmap]
dirs: dict[str, Path]
inisettings: dict[str, Any]
tooldirs: dict[str, Path]
settings: Settings
is_restarting: bool
sys_argv: list[str]

def update_sys_argv(arg: tuple[str, str] | str) -> None: ...
def getTempDir() -> Path: ...
def rmTempDir() -> None: ...
def newTempDir() -> Path: ...

def get_ini_option(
    ini_parser: ConfigParser,
    option_key: str,
    section_key: str = ...
) -> str: ...
