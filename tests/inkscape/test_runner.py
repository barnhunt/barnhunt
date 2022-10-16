import logging
import os
import re
import sys
import threading
from dataclasses import dataclass
from subprocess import CalledProcessError
from typing import Any
from typing import Callable
from typing import Sequence
from typing import Type

import pytest

from barnhunt.inkscape.runner import CliRunner
from barnhunt.inkscape.runner import dwim_old_inkscape
from barnhunt.inkscape.runner import ExportPdfCommand
from barnhunt.inkscape.runner import ExportPdfCommand_0_9x
from barnhunt.inkscape.runner import ExportPdfCommand_1_0
from barnhunt.inkscape.runner import inkscape_runner
from barnhunt.inkscape.runner import InkscapeApi
from barnhunt.inkscape.runner import log_output
from barnhunt.inkscape.runner import Runner
from barnhunt.inkscape.runner import ShellModeRunner


class TestExportPdfCommand:
    @pytest.fixture(params=[ExportPdfCommand_0_9x, ExportPdfCommand_1_0])
    def command_class(self, request: pytest.FixtureRequest) -> ExportPdfCommand:
        return request.param  # type: ignore[no-any-return]

    def test_no_pdf_version(self, command_class: Type[ExportPdfCommand]) -> None:
        command = command_class("in.svg", "out.pdf")
        assert all("export-pdf-version" not in arg for arg in command.cli_args)
        assert "export-pdf-version" not in command.shell_mode_cmdline

    def test_pdf_version(self, command_class: Type[ExportPdfCommand]) -> None:
        command = command_class("in.svg", "out.pdf", "1.23")
        assert "--export-pdf-version=1.23" in command.cli_args
        if command_class is ExportPdfCommand_0_9x:
            assert " --export-pdf-version=1.23 " in command.shell_mode_cmdline
        else:
            assert "; export-pdf-version:1.23;" in command.shell_mode_cmdline


@dataclass
class DummyInkscapeCommand:
    cli_args: Sequence[str] = ()
    shell_mode_cmdline: str = ""


class TestCliRunner:
    @pytest.fixture
    def runner(self) -> CliRunner:
        api = InkscapeApi(
            export_pdf_command=lambda *_args: DummyInkscapeCommand(),
        )
        return CliRunner(api=api, executable=sys.executable)

    def test_success(self, runner: Runner) -> None:
        command = DummyInkscapeCommand(cli_args=("-c", ""))
        runner.run(command)

    def test_failure(self, runner: Runner) -> None:
        command = DummyInkscapeCommand(cli_args=("-c", "import sys; sys.exit(1)"))
        with pytest.raises(CalledProcessError):
            runner.run(command)

    def test_logs_output(
        self, runner: Runner, caplog: pytest.LogCaptureFixture
    ) -> None:
        command = DummyInkscapeCommand(cli_args=("-c", "print('foo')"))
        runner.run(command)
        assert "foo" in caplog.text

    def test_export_pdf(self, caplog: pytest.LogCaptureFixture) -> None:
        # mostly here for coverage
        command = DummyInkscapeCommand(cli_args=("-c", "print('foo')"))
        api = InkscapeApi(export_pdf_command=lambda *_args: command)
        runner = CliRunner(api=api, executable=sys.executable)
        runner.export_pdf("ignored", "ignored")
        assert "foo" in caplog.text

    def test_close(self, runner: Runner) -> None:
        # vanity test for coverage
        runner.close()


class TestShellModeRunner:
    @pytest.fixture
    def runner(self) -> ShellModeRunner:
        here = os.path.dirname(os.path.abspath(__file__))
        dummy_inkscape_py = os.path.join(here, "dummy_inkscape.py")
        api = InkscapeApi(
            export_pdf_command=lambda *_args: DummyInkscapeCommand(),
            shell_mode_cruft_patterns=(r"^DummyShellmodeInkscape$",),
        )
        return ShellModeRunner(
            api=api,
            executable=sys.executable,
            inkscape_args=(dummy_inkscape_py,),
            timeout=10,
        )

    def test_success(self, runner: Runner, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.INFO)
        command = DummyInkscapeCommand(shell_mode_cmdline="true")
        runner.run(command)
        assert len(caplog.messages) == 0

    def test_logs_output(
        self, runner: Runner, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO)
        command = DummyInkscapeCommand(shell_mode_cmdline="echo foo")
        runner.run(command)
        assert len(caplog.messages) == 1
        assert "foo" in caplog.messages[0]

    def test_close(self, runner: ShellModeRunner) -> None:
        command = DummyInkscapeCommand(shell_mode_cmdline="true")
        with runner:
            runner.run(command)
            proc = runner._proc
            assert proc is not None
            assert proc.poll() is None, "child process is alive"

        # check that child is killed within a reasonable time
        proc.wait(1.0)

    @pytest.mark.xfail(sys.platform == "darwin", reason="broken on macOS")
    def test_thread_safe(
        self, runner: ShellModeRunner, caplog: pytest.LogCaptureFixture
    ) -> None:
        nthreads = 16
        procs = set()
        command = DummyInkscapeCommand(shell_mode_cmdline="true")

        def target() -> None:
            runner.run(command)
            procs.add(runner._proc)

        caplog.set_level(logging.INFO)
        run_in_threads(target, nthreads=nthreads)
        assert len(caplog.messages) == 0
        assert len(procs) == nthreads
        for proc in procs:
            # Check that all subprocesses have exited
            assert proc is not None
            assert proc.wait(1.0) == 0

    def test_proc_is_none_if_not_started(self, runner: ShellModeRunner) -> None:
        assert runner._proc is None


def run_in_threads(target: Callable[[], Any], nthreads: int) -> None:
    threads = [threading.Thread(target=target) for _ in range(nthreads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def test_log_output(caplog: pytest.LogCaptureFixture) -> None:
    log_output("foo")
    assert len(caplog.messages) == 1
    assert re.search(r"(?m)^!! => foo", caplog.text)


def test_log_output_squelches_cruft(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    log_output("foo", cruft_patterns=(r"^foo$",))
    assert len(caplog.messages) == 0


@pytest.mark.parametrize(
    ("shell_mode", "old_inkscape", "runner_class", "export_pdf_command"),
    [
        (False, False, CliRunner, ExportPdfCommand_1_0),
        (False, True, CliRunner, ExportPdfCommand_0_9x),
        (True, False, ShellModeRunner, ExportPdfCommand_1_0),
        (True, True, ShellModeRunner, ExportPdfCommand_0_9x),
    ],
)
def test_inkscape_runner(
    shell_mode: bool,
    old_inkscape: bool,
    runner_class: Type[Runner],
    export_pdf_command: Any,
) -> None:
    runner = inkscape_runner(shell_mode, old_inkscape=old_inkscape)
    assert isinstance(runner, runner_class)
    assert runner.api.export_pdf_command is export_pdf_command


def test_dwim_old_inkscape(inkscape_executable: str) -> None:
    assert isinstance(dwim_old_inkscape(inkscape_executable), bool)


def test_dwim_old_inkscape_warns_on_garbage(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    python = sys.executable
    assert dwim_old_inkscape(python) is False
    assert "Can not determine Inkscape version" in caplog.text
