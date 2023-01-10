from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pytest

from barnhunt.inkscape.runner import dwim_old_inkscape
from barnhunt.inkscape.runner import inkscape_runner


@pytest.fixture
def inkscape1_executable(inkscape_executable: str) -> str:
    if dwim_old_inkscape(inkscape_executable):
        pytest.skip("test requires inkscape >= 1.0")
    return inkscape_executable


@dataclass
class DummyInkscapeCommand:
    cli_args: Sequence[str] = ()
    shell_mode_cmdline: str = ""


@pytest.fixture(autouse=True)
def rl_enable_horiz_scroll_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Configure GNU readline to scroll long input lines.

    When this scrolling is enabled, it screws up pexpect's command-line matching.
    """
    inputrc = tmp_path / ".inputrc"
    inputrc.write_text("set horizontal-scroll-mode on\n")
    monkeypatch.setitem(os.environ, "INPUTRC", os.fspath(inputrc))


@pytest.mark.parametrize("long_cmdline", [False, True])
def test_shell_mode_inkscape_version(
    long_cmdline: bool,
    inkscape1_executable: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    runner = inkscape_runner(shell_mode=True, executable=inkscape1_executable)
    cmdline = "inkscape-version"
    if long_cmdline:
        cmdline += f":{'x' * 256}"
    runner.run(DummyInkscapeCommand(shell_mode_cmdline=cmdline))

    warnings = [
        message
        for _, level, message in caplog.record_tuples
        if level >= logging.WARNING
    ]
    assert 1 <= len(warnings) <= 2

    unexpected_lines = [
        line[6:] for line in warnings[-1].splitlines() if line.startswith("!! => ")
    ]
    assert len(unexpected_lines) == 1
    assert re.match(r"\AInkscape \d+\.\d+\.\d+ ", unexpected_lines[0])
