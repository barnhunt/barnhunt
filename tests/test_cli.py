import os
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Iterator

import click
import pytest
from click.testing import CliRunner
from pytest_mock import MockerFixture

from barnhunt.cli import _dump_loaded_modules
from barnhunt.cli import barnhunt_cli
from barnhunt.cli import default_2up_output_file
from barnhunt.cli import InkexRequirementType
from barnhunt.cli import main
from barnhunt.cli import pdf_2up
from barnhunt.installer import DEFAULT_REQUIREMENTS
from barnhunt.installer import InkexRequirement


class Test_default_2up_output_file:
    @pytest.fixture
    def resilient_parsing(self) -> bool:
        return False

    @pytest.fixture
    def ctx(self, resilient_parsing: bool) -> Iterator[click.Context]:
        with click.Context(pdf_2up, resilient_parsing=resilient_parsing) as ctx:
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

    @pytest.mark.parametrize("resilient_parsing", [True])
    def test_resilient(self, ctx: click.Context) -> None:
        assert default_2up_output_file() is None

    def test_shell_completion(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            barnhunt_cli,
            args="2up",
            env={
                "_BARNHUNT_COMPLETE": "bash_complete",
                "COMP_WORDS": "barnhunt 2up",
                "COMP_CWORD": "2",
            },
        )
        assert result.stdout.strip() == "file,"


def test_main(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    std = capsys.readouterr()
    assert "export pdfs from inkscape" in std.out.lower()


class Test_InkexRequirementType:
    CF = Callable[[Any], InkexRequirement]

    @pytest.fixture
    def allow_specifiers(self) -> bool:
        return True

    @pytest.fixture
    def convert(self, allow_specifiers: bool) -> CF:
        param_type = InkexRequirementType(allow_specifiers=allow_specifiers)

        def convert(value: Any) -> InkexRequirement:
            return param_type.convert(value, None, None)

        return convert

    def test_from_requirement(self, convert: CF) -> None:
        req = DEFAULT_REQUIREMENTS[0]
        assert convert(req) is req

    def test_from_string(self, convert: CF) -> None:
        req = convert("inkex_bh")
        assert req.name == "inkex_bh"

    def test_unknown_name(self, convert: CF) -> None:
        with pytest.raises(click.BadParameter):
            convert("unknown")

    def test_specifier(self, convert: CF) -> None:
        assert str(convert("inkex.bh<1.0.0").specifier) == "<1.0.0"

    def test_direct_reference(self, convert: CF) -> None:
        assert convert("inkex.bh @ file:///tmp/test.zip").url == "file:///tmp/test.zip"

    @pytest.mark.parametrize("allow_specifiers", [False])
    def test_allows_specifier(self, convert: CF) -> None:
        with pytest.raises(click.BadParameter):
            convert("inkex.bh==1.0.0")

    @pytest.mark.parametrize("allow_specifiers", [False])
    def test_allows_direct_reference(self, convert: CF) -> None:
        with pytest.raises(click.BadParameter):
            convert("inkex.bh @ file:///tmp/test.zip")


def test_install_target_from_inkscape(mocker: MockerFixture, tmp_path: Path) -> None:
    mocker.patch.dict("os.environ", GITHUB_TOKEN="token")
    target = tmp_path
    get_user_data_directory = mocker.patch(
        "barnhunt.cli.get_user_data_directory", return_value=target
    )
    Installer = mocker.patch("barnhunt.cli.Installer")
    runner = CliRunner()
    result = runner.invoke(barnhunt_cli, ("--inkscape", "myinkscape", "install"))
    assert result.exit_code == 0
    get_user_data_directory.assert_called_once_with("myinkscape")
    Installer.assert_called_once_with(target, dry_run=False, github_token="token")


def test_uninstall(mocker: MockerFixture, tmp_path: Path) -> None:
    Installer = mocker.patch("barnhunt.cli.Installer")
    runner = CliRunner()
    result = runner.invoke(barnhunt_cli, ("uninstall", "--target", os.fspath(tmp_path)))
    assert result.exit_code == 0
    assert Installer.mock_calls == [
        mocker.call(tmp_path, dry_run=False),
        *(mocker.call().uninstall(req) for req in DEFAULT_REQUIREMENTS),
    ]


def test_debug_info() -> None:
    runner = CliRunner()
    result = runner.invoke(barnhunt_cli, ("debug-info",))
    assert result.exit_code == 0


def test_main_dumps_loaded_modules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BARNHUNT_DUMP_LOADED_MODULES", "true")
    monkeypatch.setattr("sys.argv", ["-c", "--version"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    assert "Dumped loaded modules" in capsys.readouterr().err
    dumpfiles = [p for p in tmp_path.iterdir() if p.name.startswith("barnhunt-modules")]
    assert len(dumpfiles) == 1
    modules = set(dumpfiles[0].read_text("utf-8").splitlines())
    assert "pikepdf" in modules


def test_dump_loaded_modules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    _dump_loaded_modules()
    captured = capsys.readouterr()
    assert "Dumped loaded modules" in captured.err
    dumpfiles = [p for p in tmp_path.iterdir() if p.name.startswith("barnhunt-modules")]
    assert len(dumpfiles) == 1
