from __future__ import annotations

import io
import locale
import logging
import re
import shlex
import threading
import weakref
from dataclasses import dataclass
from subprocess import PIPE
from subprocess import Popen
from subprocess import run
from subprocess import STDOUT
from typing import Any
from typing import Callable
from typing import Iterable
from typing import Sequence
from typing import TypeVar

from pexpect.popen_spawn import PopenSpawn

from .._compat import Protocol

log = logging.getLogger()


class InkscapeCommand(Protocol):
    @property
    def cli_args(self) -> Iterable[str]:
        """Commmand line args for Inkscape."""
        raise NotImplementedError()

    @property
    def shell_mode_cmdline(self) -> str:
        """Equivalent shell-mode command line"""
        raise NotImplementedError()


class ExportPdfCommand(InkscapeCommand):
    def __init__(self, svg_fn: str, output_fn: str, pdf_version: str | None = None):
        self.svg_fn = svg_fn
        self.output_fn = output_fn
        self.pdf_version = pdf_version

    @property
    def cli_args(self) -> list[str]:
        """Commmand line args for Inkscape."""
        return [self.svg_fn, *(f"--{param}" for param in map("=".join, self._params))]

    @property
    def _params(self) -> list[tuple[str, str] | tuple[str]]:
        raise NotImplementedError()


class ExportPdfCommand_1_0(ExportPdfCommand):
    @property
    def _params(self) -> list[tuple[str, str] | tuple[str]]:
        params: list[tuple[str, str] | tuple[str]] = [
            ("export-area-page",),
            ("export-type", "pdf"),
            ("export-dpi", "96"),  # for rasterization of filter effects
            ("export-filename", self.output_fn),
        ]
        if self.pdf_version is not None:
            params.insert(2, ("export-pdf-version", self.pdf_version))
        return params

    @property
    def shell_mode_cmdline(self) -> str:
        # Inkscape's current shell-mode parser appears to be quite rudimentary.
        # Split actions on \s*;\s*, then split max one parameter from each action
        # using \s*:\s*.  There appears to be no quoting mechanism.
        #
        # XXX: Not sure about encoding details.  Hope for the best for now.
        #
        # https://gitlab.com/inkscape/inkscape/-/blob/INKSCAPE_1_2_1/src/inkscape-application.cpp#L1119
        params: list[tuple[str, str] | tuple[str]] = [
            ("file-open", self.svg_fn),
            *self._params,
            ("export-do",),
        ]
        return "; ".join(map(":".join, params))


class ExportPdfCommand_0_9x(ExportPdfCommand):
    @property
    def _params(self) -> list[tuple[str, str] | tuple[str]]:
        params: list[tuple[str, str] | tuple[str]] = [
            ("export-area-page",),
            ("export-dpi", "96"),  # for rasterization of filter effects
            ("export-pdf", self.output_fn),
        ]
        if self.pdf_version is not None:
            params.insert(1, ("export-pdf-version", self.pdf_version))
        return params

    @property
    def shell_mode_cmdline(self) -> str:
        # Inkscape 0.9x's shell-mode parser uses Glib's g_shell_parse_argv
        # to parse command lines.  As such, I'm guessing it supports normal
        # shell quoting mechanisms.
        #
        # https://gitlab.com/inkscape/inkscape/-/blob/INKSCAPE_0_92_5/src/main.cpp#L1348
        return " ".join(map(shlex.quote, self.cli_args))


@dataclass
class InkscapeApi:
    export_pdf_command: Callable[[str, str, str | None], InkscapeCommand]
    cruft_patterns: tuple[str | re.Pattern[str], ...] = ()
    shell_mode_prompt: str = ">"
    shell_mode_cruft_patterns: tuple[str | re.Pattern[str], ...] = ()


# From RunApp in AppImage version
_appimage_cruft_patterns = (
    r"^Setting \$?(?:XDG_CONFIG_HOME|_INKSCAPE_GC)",
    r"^Run experimental bundle",  # (Inkscape 1.0.x only)
    r"^\s*$",
    r"^\(ld-linux.*?\):\s* Gtk-WARNING\b",
)
_gtk_cruft_patterns = (r"^Gtk-Message:",)

INKSCAPE_APIS = {
    "1.0": InkscapeApi(
        export_pdf_command=ExportPdfCommand_1_0,
        cruft_patterns=(
            *_gtk_cruft_patterns,
            *_appimage_cruft_patterns,
        ),
        shell_mode_prompt="> ",
        shell_mode_cruft_patterns=(
            r"^Inkscape interactive shell mode\.",
            r"^\s*Input of the form:",
            r"^\s*action1:arg1;",
            r"^Only (?:verbs|actions) that don't require a desktop may be used\.",
            *_gtk_cruft_patterns,
            *_appimage_cruft_patterns,
        ),
    ),
    "0.9x": InkscapeApi(
        export_pdf_command=ExportPdfCommand_0_9x,
        cruft_patterns=(),
        shell_mode_prompt=">",
        shell_mode_cruft_patterns=(r"^Inkscape \d.* interactive shell mode",),
    ),
}


_Runner = TypeVar("_Runner", bound="Runner")


class Runner:
    def __init__(self, api: InkscapeApi, executable: str):
        self.api = api
        self.executable = executable

    def export_pdf(
        self, svg_fn: str, output_fn: str, pdf_version: str | None = None
    ) -> None:
        self.run(self.api.export_pdf_command(svg_fn, output_fn, pdf_version))

    def run(self, cmd: InkscapeCommand) -> None:
        raise NotImplementedError()

    def close(self) -> None:
        pass

    def __enter__(self: _Runner) -> _Runner:
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()


class CliRunner(Runner):
    """Run Inkscape in normal command-line mode.

    This will run Inkscape once for each operation.

    """

    def run(self, cmd: InkscapeCommand) -> None:
        proc = run(
            [self.executable, *cmd.cli_args],
            stdout=PIPE,
            stderr=STDOUT,
            text=True,
            check=True,
        )
        log_output(proc.stdout, self.api.cruft_patterns)


class ShellModeRunner(Runner):
    """Run Inkscape using it's --shell mode.

    This allows for running multiple commands with a single invocation
    of Inkscape.

    This runner is thread-safe.  If called from multiple threads, a
    separate inkscape process will be run for each thread.

    """

    def __init__(
        self,
        api: InkscapeApi,
        executable: str,
        timeout: float = 30,
        inkscape_args: Iterable[str] = ("--shell",),
    ):
        super().__init__(api, executable)
        self.timeout = timeout
        self.inkscape_args = inkscape_args
        self.prompt_re = r"(\A|\n)" + re.escape(api.shell_mode_prompt)
        self._threadlocal = threading.local()

    @property
    def child(self) -> PopenSpawn[str, io.StringIO]:
        threadlocal = self._threadlocal
        child: PopenSpawn[str, io.StringIO] | None = getattr(threadlocal, "child", None)
        if child is not None:
            return child

        log.debug("Starting shell-mode inkscape subprocess")
        encoding = locale.getpreferredencoding(False)
        child = threadlocal.child = PopenSpawn(
            [self.executable, *self.inkscape_args],
            encoding=encoding,
            searchwindowsize=len(self.api.shell_mode_prompt) + 1,
            timeout=self.timeout,
        )
        # Arrange to shutdown child when current thread is done
        # There are circular references within the PopenSpawn, so
        # it does not clean itself up very quickly, if at all.
        obj = threadlocal.sentinel = _Object()
        threadlocal.finalizer = weakref.finalize(obj, self._shutdown_child, child)
        self._wait_for_prompt(self.api.shell_mode_cruft_patterns)
        return child

    def run(self, cmd: InkscapeCommand) -> None:
        cmdline = cmd.shell_mode_cmdline
        log.debug("Sending to shell-mode inkscape: %r", cmdline)
        self.child.sendline(cmdline)
        self._wait_for_prompt([re.escape(cmdline), r"\A\s*\Z"])

    def close(self) -> None:
        finalizer = getattr(self._threadlocal, "finalizer", None)
        if callable(finalizer):
            finalizer()

    def _wait_for_prompt(self, cruft_patterns: Sequence[str | re.Pattern[str]]) -> None:
        """Wait for prompt."""
        self.child.expect(self.prompt_re)
        log_output(
            output=self.child.before,
            cruft_patterns=cruft_patterns,
            command="shell-mode Inkscape",
        )

    @staticmethod
    def _shutdown_child(child: PopenSpawn[str, io.StringIO]) -> None:
        child.sendeof()
        # FIXME: send kill()s, too, after a bit of a wait?

    @property
    def _proc(self) -> Popen[bytes] | None:
        """Access to the underlyting Popen object.

        This is for use by tests.
        """
        child: PopenSpawn[str, io.StringIO] | None = getattr(
            self._threadlocal, "child", None
        )
        if child is not None:
            return child.proc
        return None


class _Object:
    """Minimal object we can create a weakref to.

    (Weakref.finalizer doesn't work with plain object().)
    """


def log_output(
    output: str,
    cruft_patterns: Sequence[str | re.Pattern[str]] = (),
    command: str = "Inkscape",
) -> None:
    """Log output from command.

    If the output contains any lines which are not matched by one of
    the ``cruft_patterns``, a warning is logged, with the suspicious lines
    flagged.  Otherwise, the output is logged at DEBUG level.

    The ``command`` parameter should be set to a textual description of the
    command which generated the output.
    """

    def is_unexpected(line: str) -> bool:
        return all(re.search(pat, line) is None for pat in cruft_patterns)

    output_lines = output.splitlines()
    if any(is_unexpected(line) for line in output_lines):
        flag = "!! =>"
        log.warning(
            f"Unexpected output from {command} "
            f"(Unexpected lines are marked with {flag!r}):\n%s",
            "\n".join(
                f"{flag if is_unexpected(line) else '':<{len(flag)}s} {line}"
                for line in output_lines
            ),
        )
    elif output_lines:
        log.debug(
            f"Output from {command}:\n%s",
            "\n".join(f"  {line}" for line in output_lines),
        )


def inkscape_runner(
    shell_mode: bool = True,
    executable: str = "inkscape",
    old_inkscape: bool | None = None,
) -> Runner:
    if old_inkscape or (old_inkscape is None and dwim_old_inkscape(executable)):
        api = INKSCAPE_APIS["0.9x"]
    else:
        api = INKSCAPE_APIS["1.0"]

    runner: type[Runner] = ShellModeRunner if shell_mode else CliRunner
    return runner(api, executable)


def dwim_old_inkscape(executable: str) -> bool:
    """Determine whether we're running an old Inkscape."""
    proc = run([executable, "--version"], capture_output=True, text=True, check=True)
    m = re.search(r"(?m)^Inkscape (\d+)\.(\d+)\.(\d+) ", proc.stdout)
    if m is None:
        log.warning("Can not determine Inkscape version.")
        return False
    version = tuple(map(int, m.groups()))
    return version < (1, 0)
