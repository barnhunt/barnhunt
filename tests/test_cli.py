import os
from pathlib import Path
from typing import Callable
from typing import Iterator

import click
import pytest

from barnhunt.cli import default_2up_output_file
from barnhunt.cli import default_inkscape_command
from barnhunt.cli import default_shell_mode
from barnhunt.cli import main
from barnhunt.cli import pdf_2up


@pytest.mark.parametrize(
    "platform, expect",
    [
        ("linux", "inkscape"),
        ("win32", "inkscape.exe"),
    ],
)
def test_default_inkscape_command(
    platform: str, expect: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delitem(os.environ, "INKSCAPE_COMMAND", raising=False)
    monkeypatch.setattr("sys.platform", platform)
    assert default_inkscape_command() == expect


@pytest.mark.parametrize(
    "platform, expect",
    [
        ("linux", True),
        ("darwin", False),
    ],
)
def test_default_shell_mode(
    platform: str, expect: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.platform", platform)
    assert default_shell_mode() is expect


class Test_default_2up_output_file:
    @pytest.fixture
    def ctx(self) -> Iterator[click.Context]:
        with click.Context(pdf_2up) as ctx:
            yield ctx

    @pytest.fixture
    def add_input_file(
        self, ctx: click.Context, tmp_path: Path
    ) -> Callable[[str], Path]:
        def add_input_file(filename: str) -> Path:
            params = ctx.params
            param_name = "pdffiles"
            dummy_path = tmp_path / filename
            dummy_path.touch()
            fp = click.File("rb")(os.fspath(dummy_path))
            params[param_name] = params.get(param_name, ()) + (fp,)
            return dummy_path

        return add_input_file

    def test_default_output_filename(
        self,
        ctx: click.Context,
        add_input_file: Callable[[str], Path],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        input_pdf = add_input_file("input.pdf")
        output_filename = default_2up_output_file()
        assert output_filename == input_pdf.with_name("input-2up.pdf")
        assert "Writing output to " in capsys.readouterr().out

    def test_raises_error_when_multiple_inputs(
        self, ctx: click.Context, add_input_file: Callable[[str], Path]
    ) -> None:
        add_input_file("input1.pdf")
        add_input_file("input2.pdf")
        with pytest.raises(click.UsageError, match="multiple input files"):
            default_2up_output_file()


def test_main(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    std = capsys.readouterr()
    assert "export pdfs from inkscape" in std.out.lower()
