import io
import re
from types import TracebackType
from typing import AnyStr
from typing import Awaitable
from typing import Callable
from typing import Generic
from typing import Iterable
from typing import Iterator
from typing import Literal
from typing import overload
from typing import TextIO
from typing import Type
from typing import TypeVar

from _typeshed import Incomplete

from .exceptions import EOF
from .exceptions import TIMEOUT

Pattern = AnyStr | re.Pattern[AnyStr] | Type[EOF] | Type[TIMEOUT]
CompiledPattern = re.Pattern[AnyStr] | Type[EOF] | Type[TIMEOUT]
ExactPattern = AnyStr | Type[EOF] | Type[TIMEOUT]

_BufferType = TypeVar("_BufferType", io.StringIO, io.BytesIO)

class SpawnBase(Generic[AnyStr, _BufferType]):
    encoding: str | None
    pid: int | None
    flag_eof: bool
    stdin: Incomplete
    stdout: Incomplete
    stderr: Incomplete
    searcher: Incomplete
    ignorecase: bool
    before: AnyStr
    after: AnyStr
    match: re.Match[AnyStr]
    match_index: int | None
    terminated: bool
    exitstatus: int | None
    signalstatus: int | None
    status: int | None
    child_fd: int
    timeout: float
    delimiter: Incomplete
    logfile: TextIO | None
    logfile_read: TextIO | None
    logfile_send: TextIO | None
    maxread: int
    searchwindowsize: int | None
    delaybeforesend: float
    delayafterclose: float
    delayafterterminate: float
    delayafterread: float
    softspace: bool
    name: str
    closed: bool
    codec_errors: str | None
    string_type: Type[AnyStr]
    buffer_type: Type[_BufferType]
    crlf: AnyStr
    allowed_string_types: tuple[Type[bytes] | Type[str], ...]
    linesep: AnyStr
    write_to_stdout: Callable[[AnyStr], int]
    async_pw_transport: Incomplete

    @overload
    def __init__(
        self: "SpawnBase[str, io.StringIO]",
        timeout: float = ...,
        maxread: int = ...,
        searchwindowsize: int | None = ...,
        logfile: TextIO | None = ...,
        encoding: str = ...,
        codec_errors: str = ...,
    ): ...
    @overload
    def __init__(
        self: "SpawnBase[bytes, io.BytesIO]",
        timeout: float = ...,
        maxread: int = ...,
        searchwindowsize: int | None = ...,
        logfile: TextIO | None = ...,
        encoding: None = ...,
        codec_errors: str | None = ...,
    ): ...

    buffer: AnyStr

    # The default values for `size` and `timeout` are incompatible
    # with PopenSpawn.read_nonblocking which does not provide
    # defaults. We'll just leave it as virtual
    # def read_nonblocking(
    #     self, size: int = ..., timeout: float | None = ...
    # ) -> AnyStr: ...

    def compile_pattern_list(
        self, patterns: Iterable[Pattern[AnyStr]] | Pattern[AnyStr]
    ) -> list[CompiledPattern[AnyStr]]: ...
    @overload
    def expect(
        self,
        pattern: Pattern[AnyStr] | Iterable[Pattern[AnyStr]],
        timeout: float = ...,
        searchwindowsize: int = ...,
    ) -> int: ...
    @overload
    def expect(
        self,
        pattern: Pattern[AnyStr] | Iterable[Pattern[AnyStr]],
        timeout: float = ...,
        searchwindowsize: int = ...,
        *,
        async_: Literal[False],
    ) -> int: ...
    @overload
    def expect(
        self,
        pattern: Pattern[AnyStr] | Iterable[Pattern[AnyStr]],
        timeout: float = ...,
        searchwindowsize: int = ...,
        *,
        async_: Literal[True],
    ) -> Awaitable[int]: ...
    @overload
    def expect_list(
        self,
        pattern_list: list[CompiledPattern[AnyStr]],
        timeout: float = ...,
        searchwindowsize: int = ...,
    ) -> int: ...
    @overload
    def expect_list(
        self,
        pattern_list: list[CompiledPattern[AnyStr]],
        timeout: float = ...,
        searchwindowsize: int = ...,
        *,
        async_: Literal[False],
    ) -> int: ...
    @overload
    def expect_list(
        self,
        pattern_list: list[CompiledPattern[AnyStr]],
        timeout: float = ...,
        searchwindowsize: int = ...,
        *,
        async_: Literal[True],
    ) -> Awaitable[int]: ...
    @overload
    def expect_exact(
        self,
        pattern_list: Iterable[ExactPattern[AnyStr]],
        timeout: float = ...,
        searchwindowsize: int = ...,
    ) -> int: ...
    @overload
    def expect_exact(
        self,
        pattern_list: Iterable[ExactPattern[AnyStr]],
        timeout: float = ...,
        searchwindowsize: int = ...,
        *,
        async_: Literal[False],
    ) -> int: ...
    @overload
    def expect_exact(
        self,
        pattern_list: Iterable[ExactPattern[AnyStr]],
        timeout: float = ...,
        searchwindowsize: int = ...,
        *,
        async_: Literal[True],
    ) -> Awaitable[int]: ...
    def expect_loop(
        self, searcher: Incomplete, timeout: float = ..., searchwindowsize: int = ...
    ) -> int: ...
    def read(self, size: int = ...) -> AnyStr: ...
    def readline(self, size: int = ...) -> AnyStr: ...
    def __iter__(self) -> Iterator[AnyStr]: ...
    def readlines(self, sizehint: int = ...) -> list[AnyStr]: ...
    def fileno(self) -> int: ...
    def flush(self) -> None: ...
    def isatty(self) -> bool: ...

    _Self = TypeVar("_Self", bound="SpawnBase[AnyStr, _BufferType]")
    def __enter__(self: _Self) -> _Self: ...
    def __exit__(
        self,
        etype: Type[BaseException] | None,
        evalue: Exception | None,
        tb: TracebackType | None,
    ) -> None: ...
