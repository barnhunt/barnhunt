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

from barnhunt.inkscape.utils import _get_appdata
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
def mock_windll_SHGetFolderPathW(monkeypatch: pytest.MonkeyPatch) -> None:
    # OCD to get test coverage of the win32 bits under linux
    if sys.platform == "win32":
        return
    if not os.environ.get("BARNHUNT_MOCK_WIN32"):
        pytest.skip("BARNHUNT_MOCK_WIN32 not set")

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


@pytest.mark.skipif(sys.platform != "win32", reason="not Windows system")
def test_get_default_user_data_directory_from_appdata() -> None:
    default_user_data_directory = get_default_user_data_directory()
    assert default_user_data_directory.is_absolute()
    assert default_user_data_directory.name == "inkscape"


@pytest.mark.skipif(sys.platform == "win32", reason="not POSIX system")
@pytest.mark.usefixtures("mock_windll_SHGetFolderPathW")
def test_get_default_user_data_directory_from_appdata_coverage() -> None:
    default_user_data_directory = get_default_user_data_directory()
    assert default_user_data_directory.is_absolute()
    assert default_user_data_directory.name == "inkscape"


@pytest.mark.skipif(sys.platform != "win32", reason="not Windows system")
def test_get_appdata(monkeypatch: pytest.MonkeyPatch) -> None:
    appdata = _get_appdata()
    assert Path(appdata).is_absolute()
