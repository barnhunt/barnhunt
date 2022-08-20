import io
import subprocess
from typing import Any
from typing import AnyStr
from typing import Callable
from typing import Iterable
from typing import Mapping
from typing import overload
from typing import TextIO

from _typeshed import StrOrBytesPath

from .spawnbase import _BufferType
from .spawnbase import SpawnBase

class PopenSpawn(SpawnBase[AnyStr, _BufferType]):
    proc: subprocess.Popen[bytes]
    pid: int
    terminated: bool

    @overload
    def __init__(
        self: "PopenSpawn[str, io.StringIO]",
        cmd: Iterable[str],
        timeout: float = ...,
        maxread: int = ...,
        searchwindowsize: int | None = ...,
        logfile: TextIO | None = ...,
        cwd: StrOrBytesPath | None = ...,
        env: Mapping[str, str] | None = ...,
        encoding: str = ...,
        codec_errors: str = ...,
        preexec_fn: Callable[[], Any] | None = ...,
    ) -> None: ...
    @overload
    def __init__(
        self: "PopenSpawn[bytes, io.BytesIO]",
        cmd: Iterable[str],
        timeout: float = ...,
        maxread: int = ...,
        searchwindowsize: int | None = ...,
        logfile: TextIO | None = ...,
        cwd: StrOrBytesPath | None = ...,
        env: Mapping[str, str] | None = ...,
        encoding: None = ...,
        codec_errors: str | None = ...,
        preexec_fn: Callable[[], Any] | None = ...,
    ) -> None: ...
    def read_nonblocking(self, size: int, timeout: float | None) -> AnyStr: ...
    def write(self, s: AnyStr) -> None: ...
    def writelines(self, sequence: Iterable[AnyStr]) -> None: ...
    def send(self, s: AnyStr) -> int: ...
    def sendline(self, s: AnyStr = ...) -> int: ...
    def wait(self) -> int: ...
    def kill(self, sig: int) -> None: ...
    def sendeof(self) -> None: ...
