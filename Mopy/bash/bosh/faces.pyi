from typing import Any, ClassVar, Literal, TypeAlias

from ..bolt import Flags, FName, _Unpacker

# This is weird because of the dynamic imports involved,
# Probably only need the Oblivion one, I don't think we support
# face editing on other games.
from ..game.oblivion.records import MreNpc as _Npc_Oblivion
from ..game.fallout3.records import MreNpc as _Npc_Fallout3
from ..game.morrowind.records import MreNpc as _Npc_Morrowind
from ..game.skyrim.records import MreNpc as _Npc_Skyrim

from . import ModInfo, SaveInfo
from ._saves import SaveFile
from .mods_metadata import _FormID_short


# Aliases to make reading function signatures easier
_EditorID: TypeAlias = str
_FactionRank: TypeAlias = int
_ActorValueIndex: TypeAlias = int
_ActorValueModifier: TypeAlias = float

MreNpc: TypeAlias = (
    _Npc_Oblivion | _Npc_Fallout3 | _Npc_Morrowind | _Npc_Skyrim
)


class PCFaces:
    pcf_flags: ClassVar[Flags]

    class PCFace:
        # Attributes loaded ins bosh.SaveFile using SaveFileHeader
        # See:
        # - bosh.save_headers
        face_masters: list[FName]
        pcName: str

        # Attributes derived from other loaded attributes
        gender: Literal[0, 1]   # Should really be a bool

        # Attributes loaded in bosh.SaveFile using SreNpc
        # See
        # - bosh._saves SreNpc
        # - https://en.uesp.net/wiki/Oblivion_Mod:Save_File_Format/NPC
        factions: list[tuple[_FormID_short, _FactionRank]]
        modifiers: list[tuple[_ActorValueIndex, _ActorValueModifier]]
        spells: list[_FormID_short]

        # Attributes loaded in bosh.SaveFile using MreNpc
        # See:
        # - game.oblivion.records MreNpc
        # - https://en.uesp.net/wiki/Oblivion_Mod:Mod_File_Format/NPC
        eid: _EditorID
        race: _FormID_short
        eye: _FormID_short
        hair: _FormID_short
        hairLength: float
        hairRed: int
        hairBlue: int
        hairGreen: int
        unused3: Any
        fggs_p: bytes           # FaceGen Geometry-Symmetric: 50 packed floats
        fgga_p: bytes           # FaceGen Geometry-Asymmetric: 30 packed floats
        fgts_p: bytes           # FaceGen Texture-Symmetric: 50 packed floats
        level_offset: int
        skills: list[int]       # 21 bytes, one for each skill in Oblivion
        health: int
        unused2: Any
        baseSpell: int
        fatigue: int
        attributes: list[int]   # 8 bytes, one for each PC attribute (stat)
        iclass: _FormID_short

        def __init__(self) -> None: ...
        def getGenderName(self) -> Literal['Female', 'Male']: ...
        def getRaceName(self) -> str: ...
        # Currently only works with Oblivion
        def convertRace(self, fromRace: MreNpc, toRace: MreNpc) -> None: ...

    @staticmethod
    # data might be bytes or bytearray?
    def save_getNamePos(saveName: str, data: bytes, pcName: bytes) -> int: ...
    @staticmethod
    def save_getFaces(saveFile: SaveFile) -> dict[_FormID_short, PCFace]: ...
    @staticmethod
    def save_getChangedNpc(saveFile: SaveFile, npc_fid: _FormID_short, face: PCFace | None = ...) -> PCFace: ...
    @staticmethod
    def save_getPlayerFace(saveFile: SaveFile, *, __unpacker: _Unpacker = ..., __faceunpack: _Unpacker = ...) -> PCFace: ...
    @staticmethod
    def save_setFace(saveInfo: SaveInfo, face: PCFace, pcf_flags: Flags | int = ...) -> None: ...
    @staticmethod
    def save_setCreatedFace(saveFile: SaveFile, targetId: _FormID_short, face: PCFace) -> None: ...
    @staticmethod
    def save_setPlayerFace(saveFile: SaveFile, face: PCFace, pcf_flags: Flags | int = ...) -> None: ...
    @staticmethod
    def save_repairHair(saveInfo: SaveInfo) -> bool: ...
    @staticmethod
    def mod_getFaces(modInfo: ModInfo) -> dict[_EditorID, PCFace]: ...
    @staticmethod
    def mod_getRaceFaces(modInfo: ModInfo) -> dict[_EditorID, PCFace]: ...
    @staticmethod
    def mod_addFace(modInfo: ModInfo, face: PCFace) -> MreNpc: ...
