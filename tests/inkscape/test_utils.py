from __future__ import annotations

import ctypes
import os
import re
import sys
from pathlib import Path
from subprocess import CompletedProcess
from types import ModuleType
from types import SimpleNamespace

import pytest
from pytest_mock import MockerFixture

from barnhunt.inkscape.utils import get_default_user_data_directory
from barnhunt.inkscape.utils import get_user_data_directory

if sys.version_info >= (3, 8):
    from ctypes import wintypes
else:
    wintypes = ModuleType("ctypes.wintypes")
    wintypes.HWND = ctypes.c_void_p
    wintypes.HANDLE = ctypes.c_void_p
    wintypes.DWORD = ctypes.c_ulong
    wintypes.LPWSTR = ctypes.c_wchar_p
    wintypes.MAX_PATH = 260


def test_get_user_data_directory(mocker: MockerFixture) -> None:
    mocker.patch("shutil.which", return_value="/bin/inkscape")
    mocker.patch(
        "barnhunt.inkscape.utils.run",
        return_value=CompletedProcess((), 0, "cruft\n/path/to/config\n"),
    )
    assert get_user_data_directory() == Path("/path/to/config")


def test_get_user_data_directory_no_output(
    mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    mocker.patch("shutil.which", return_value="/bin/inkscape")
    mocker.patch(
        "barnhunt.inkscape.utils.run", return_value=CompletedProcess((), 0, "")
    )
    assert get_user_data_directory() == get_default_user_data_directory()
    assert "did not produce any output" in caplog.text


def test_get_user_data_directory_no_inkscape(
    mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    mocker.patch("shutil.which", return_value=None)
    assert get_user_data_directory() == get_default_user_data_directory()
    assert re.search(r"command .* not found", caplog.text)


@pytest.mark.skipif(sys.platform == "win32", reason="not POSIX system")
def test_get_default_user_data_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(os.environ, "XDG_CONFIG_HOME", raising=False)
    assert get_default_user_data_directory() == Path.home() / ".config" / "inkscape"


@pytest.mark.skipif(sys.platform == "win32", reason="not POSIX system")
def test_get_default_user_data_directory_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(os.environ, "XDG_CONFIG_HOME", "/path/to/config")
    assert get_default_user_data_directory() == Path("/path/to/config/inkscape")


@pytest.fixture
def win32_appdata(monkeypatch: pytest.MonkeyPatch) -> Path:
    if sys.platform == "win32":
        return Path(os.environ["APPDATA"])

    # OCD to get test coverage of the win32 bits under linux
    monkeypatch.setattr("sys.platform", "win32")
    appdata = Path.home() / "AppData" / "Roaming"

    def SHGetFolderPathW(
        _hwnd: wintypes.HWND,
        csidl: ctypes.c_int,
        _hToken: wintypes.HANDLE,
        _dwFlags: wintypes.DWORD,
        pszPath: wintypes.LPWSTR,
    ) -> int:
        assert csidl.value == 26
        pszPath.value = os.fspath(appdata)
        return 0

    monkeypatch.setattr(
        "ctypes.windll",
        SimpleNamespace(shell32=SimpleNamespace(SHGetFolderPathW=SHGetFolderPathW)),
        raising=False,
    )
    monkeypatch.setitem(sys.modules, "ctypes.wintypes", wintypes)

    return appdata


def test_get_default_user_data_directory_win32(win32_appdata: Path) -> None:
    assert get_default_user_data_directory() == win32_appdata / "inkscape"
