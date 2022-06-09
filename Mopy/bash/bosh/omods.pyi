from collections import OrderedDict

from ..bolt import Path, Progress, ReadableBuffer, StrPath


failedOmods: set[Path]

class OmodFile:
    omod_path: Path

    def __init__(self, omod_path: Path) -> None: ...
    def readConfig(self, conf_path: StrPath) -> None: ...
    def writeInfo(
        self,
        dest_path: Path,
        filename: str | bytes,
        readme: bool,
        scr_exists: bool,
    ) -> None: ...
    def getOmodContents(self) -> tuple[OrderedDict[str, int], int]: ...
    def extractToProject(
        self,
        outDir: Path,
        progress: Progress | None = ...,
    ) -> None: ...
    def extractFilesZip(
        self,
        crcPath: Path,
        dataPath: Path,
        outPath: Path,
        progress: Progress,
    ) -> None: ...
    def splitStream(
        self,
        in_stream: ReadableBuffer,
        outDir: Path,
        fileNames: list[bytes],
        sizes_: list[int],
        progress: Progress,
        base_progress_msg: str,
    ) -> None: ...
    def extractFiles7z(
        self,
        crcPath: Path,
        dataPath: Path,
        outPath: Path,
        progress: Progress,
    ) -> None: ...
    @staticmethod
    def getFile_CrcSizes(crc_file_path: Path) -> tuple[
        list[bytes], list[int], list[int]
    ]: ...

class OmodConfig:
    omod_proj: str
    vMajor: int
    vMinor: int
    vBuild: int
    omod_author: str
    email: str
    website: str
    abstract: str

    @staticmethod
    def getOmodConfig(omod_proj: Path) -> OmodConfig: ...
    def writeOmodConfig(self) -> None: ...
