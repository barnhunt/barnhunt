import sys
from typing import Iterable

import pytest

from barnhunt.pager import Command
from barnhunt.pager import get_pager
from barnhunt.pager import Grouper
from barnhunt.pager import Pager
from barnhunt.pager import TTYPager


@pytest.fixture
def tty_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)


@pytest.mark.usefixtures("tty_output")
def test_get_pager_returns_ttypager() -> None:
    pager = get_pager(42)
    assert isinstance(pager, TTYPager)
    assert pager.group_size == 42


@pytest.mark.usefixtures("tty_output")
def test_get_pager_returns_grouper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    pager = get_pager(43)
    assert isinstance(pager, Grouper)
    assert pager.group_size == 43


def test_Grouper(capsys: pytest.CaptureFixture[str]) -> None:
    pager = Grouper(3)
    pager([f"{n:d}" for n in range(5)])
    output = capsys.readouterr().out
    assert output.split("\n") == ["0", "1", "2", "", "3", "4", "", ""]


class TestTTYPager:
    @pytest.fixture
    def pager(self) -> Pager:
        return TTYPager(2)

    @pytest.fixture(autouse=True)
    def patch_getchar(
        self, keys: Iterable[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        keys_iter = iter(keys)

        def getchar() -> str:
            return next(keys_iter)

        monkeypatch.setattr("click.getchar", getchar)

    @pytest.mark.parametrize(
        "keys",
        [
            ("v", "q"),
        ],
    )
    def test(self, pager: Pager, capsys: pytest.CaptureFixture[str]) -> None:
        lines = ["one", "two", "three"]
        pager(lines)
        output = capsys.readouterr().out
        for line in lines:
            assert line in output
        assert "\a" not in output

    @pytest.mark.parametrize(
        "keys",
        [
            ("q",),
        ],
    )
    def test_first_page(self, pager: Pager, capsys: pytest.CaptureFixture[str]) -> None:
        lines = ["one", "two", "three"]
        pager(lines)
        output = capsys.readouterr().out
        for line in lines[:2]:
            assert line in output
        assert lines[2] not in output

    @pytest.mark.parametrize(
        "keys",
        [
            ("k", "q"),
        ],
    )
    def test_beep(self, pager: Pager, capsys: pytest.CaptureFixture[str]) -> None:
        lines = ["one", "two", "three"]
        pager(lines)
        output = capsys.readouterr().out
        assert "\a" in output

    @pytest.mark.parametrize(
        "keys, command",
        [
            (("v",), Command.PAGE_DOWN),
            (("\x1b", "v"), Command.PAGE_UP),
        ],
    )
    def test_get_cmd(self, pager: TTYPager, command: Command) -> None:
        assert pager._get_cmd() == command

    @pytest.mark.parametrize(
        "keys, command",
        [
            (("x", "q"), Command.QUIT),
            (("\x1b", "x", "r"), Command.REDRAW),
        ],
    )
    def test_get_cmd_unrecognized_key(
        self, pager: TTYPager, command: Command, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert pager._get_cmd() == command
        assert capsys.readouterr().out == "\a"


@pytest.mark.parametrize(
    "key, command",
    [
        (" ", Command.PAGE_DOWN),
        ("q", Command.QUIT),
    ],
)
def test_Command_lookup(key: str, command: Command) -> None:
    assert Command.lookup(key) == command


def test_Command_lookup_raises_KeyError() -> None:
    with pytest.raises(KeyError):
        Command.lookup("x")
