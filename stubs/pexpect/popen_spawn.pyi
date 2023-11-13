from collections.abc import Callable
from collections.abc import Iterable
from subprocess import _CMD
from subprocess import _ENV
from subprocess import Popen
from typing import AnyStr
from typing import overload

from _typeshed import StrOrBytesPath

from .spawnbase import _SupportsWriteFlush
from .spawnbase import SpawnBase

class PopenSpawn(SpawnBase[AnyStr]):
    proc: Popen[AnyStr]
    @overload
    def __init__(
        self: PopenSpawn[bytes],
        cmd: _CMD,
        timeout: float | None = 30,
        maxread: int = 2000,
        searchwindowsize: int | None = None,
        logfile: _SupportsWriteFlush[bytes] | None = None,
        cwd: StrOrBytesPath | None = None,
        env: _ENV | None = None,
        encoding: None = None,
        codec_errors: str = "strict",
        preexec_fn: Callable[[], object] | None = None,
    ) -> None: ...
    @overload
    def __init__(
        self: PopenSpawn[str],
        cmd: _CMD,
        timeout: float | None,
        maxread: int,
        searchwindowsize: int | None,
        logfile: _SupportsWriteFlush[str] | None,
        cwd: StrOrBytesPath | None,
        env: _ENV | None,
        encoding: str,
        codec_errors: str = "strict",
        preexec_fn: Callable[[], object] | None = None,
    ) -> None: ...
    @overload
    def __init__(
        self: PopenSpawn[str],
        cmd: _CMD,
        timeout: float | None = 30,
        maxread: int = 2000,
        searchwindowsize: int | None = None,
        logfile: _SupportsWriteFlush[str] | None = None,
        cwd: StrOrBytesPath | None = None,
        env: _ENV | None = None,
        *,
        encoding: str,
        codec_errors: str = "strict",
        preexec_fn: Callable[[], object] | None = None,
    ) -> None: ...
    def read_nonblocking(self, size: int, timeout: float | None) -> AnyStr: ...  # type: ignore[override]
    def write(self, s: AnyStr | str) -> None: ...
    def writelines(self, sequence: Iterable[AnyStr | str]) -> None: ...
    def send(self, s: AnyStr | str) -> int: ...
    def sendline(self, s: AnyStr | str = "") -> int: ...
    def wait(self) -> int: ...
    def kill(self, sig: int) -> None: ...
    def sendeof(self) -> None: ...
