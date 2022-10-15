from __future__ import annotations

import datetime
import io
import itertools
import json
import logging
import zipfile
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any
from typing import Callable
from typing import Iterable
from urllib.parse import urlunsplit

import pytest
from packaging.utils import canonicalize_name
from packaging.version import Version
from pytest_mock import MockerFixture

from barnhunt.installer import _copy_to_tmp
from barnhunt.installer import DownloadUrl
from barnhunt.installer import find_distributions
from barnhunt.installer import find_installed
from barnhunt.installer import github
from barnhunt.installer import InkexProject
from barnhunt.installer import InkexRequirement
from barnhunt.installer import Installer
from barnhunt.installer import NoSuchDistribution
from barnhunt.installer import open_zipfile


def test_InkexRequirement_project() -> None:
    req = InkexRequirement("inkex_bh")
    assert req.project.install_dir == "extensions"
    assert req.project.gh_owner == "barnhunt"
    assert req.project.gh_repo == "inkex-bh"


@pytest.mark.parametrize(
    "requirement, message",
    [
        ("unknown", "unknown requirement"),
        ("inkex-bh[extra]", "extras not"),
        ("inkex-bh; python_version>'3.6'", "markers not"),
        ("unparseable requirement", "(?i)parse error"),
    ],
)
def test_InkexRequirement_project_raises_value_error(
    requirement: str, message: str
) -> None:
    with pytest.raises(ValueError) as exc_info:
        InkexRequirement(requirement)
    assert exc_info.match(message)


@pytest.fixture
def zip_data() -> bytes:
    with io.BytesIO() as fp:
        with zipfile.ZipFile(fp, "w") as zf:
            zf.writestr("test.txt", "howdy")
        return fp.getvalue()


def test_copy_to_tmp() -> None:
    orig = io.BytesIO(b"content")
    with _copy_to_tmp(orig) as fp:
        assert fp.read() == b"content"
        assert fp.read() == b""
        assert fp.seekable()
        fp.seek(0)
        assert fp.read() == b"content"


def test_open_zipfile(mocker: MockerFixture, zip_data: bytes) -> None:
    requests = mocker.patch("barnhunt.installer.request")
    requests.urlopen.return_value = io.BytesIO(zip_data)
    with open_zipfile(DownloadUrl("https://example.com/dummy.zip")) as zf:
        assert zf.namelist() == ["test.txt"]


@pytest.mark.requiresinternet
def test_functional_download_zipfile() -> None:
    url = DownloadUrl(
        "https://github.com/barnhunt/inkex-bh/releases/download/v1.0.0rc3/"
        "inkex_bh-1.0.0rc3.zip"
    )
    with open_zipfile(url) as zf:
        assert "org.dairiki.inkex_bh/METADATA.json" in zf.namelist()


def make_distdir(dist_path: Path, metadata: dict[str, Any] | None = None) -> Path:
    dist_path.mkdir()
    Path(dist_path, "junk.txt").touch()
    if metadata is not None:
        Path(dist_path, "METADATA.json").write_text(json.dumps(metadata))
    return dist_path


def test_find_installed(tmp_path: Path) -> None:
    make_distdir(tmp_path / "not_a_dist")
    make_distdir(
        tmp_path / "wrong_dist", metadata=dict(name="wrong-proj", version="1.0")
    )
    dist_path = make_distdir(
        tmp_path / "distdir", metadata=dict(name="test_proj", version="1.2")
    )

    assert find_installed(tmp_path, canonicalize_name("test.proj")) == {
        Version("1.2"): dist_path,
    }


datetime_now = datetime.datetime.now(datetime.timezone.utc)


def make_asset(
    browser_download_url: str = "https://example.org/download",
    updated_at: datetime.datetime = datetime_now,
    content_type: str = "application/zip",
) -> github.ReleaseAsset:
    return github.ReleaseAsset(
        browser_download_url=browser_download_url,
        updated_at=updated_at,
        content_type=content_type,
        name="",
        label=None,
        state="uploaded",
        download_count=1,
        size=23,
        created_at=datetime_now,
    )


def make_release(
    tag_name: str, assets: Iterable[github.ReleaseAsset] = ()
) -> github.Release:
    return github.Release(
        tag_name=tag_name,
        assets=list(assets),
        name=None,
        body=None,
        html_url="",
        draft=False,
        prerelease=False,
        created_at=datetime_now,
        published_at=None,
    )


def test_find_distributions(mocker: MockerFixture) -> None:
    releases = [
        make_release("bad_tag_name"),
        make_release(
            "v1.2",
            [
                make_asset("old", datetime_now - datetime.timedelta(20)),
                make_asset("new"),
            ],
        ),
        make_release(
            "v1.5dev3+local",
            [
                make_asset("text", content_type="text/plain"),
                make_asset("zip"),
            ],
        ),
        make_release("v0.2", []),
    ]
    github = mocker.patch("barnhunt.installer.github")
    github.iter_releases.return_value = iter(releases)

    project = InkexProject("tests", "foo", "bar")

    assert find_distributions(project) == {
        Version("1.2"): "new",
        Version("1.5dev3+local"): "zip",
    }
    github.iter_releases.assert_called_once_with("foo", "bar")


@pytest.fixture
def target(tmp_path: Path) -> Path:
    extensions = tmp_path / "extensions"
    extensions.mkdir()
    make_distdir(extensions / "other", metadata=dict(name="other", version="1.0"))
    make_distdir(extensions / "nondist")

    symbols = tmp_path / "symbols"
    symbols.mkdir()
    make_distdir(symbols / "old", metadata=dict(name="bh-symbols", version="0.1rc1"))

    return tmp_path


ZipMaker = Callable[..., str]


@pytest.fixture
def make_distzip(tmp_path: Path) -> ZipMaker:
    zip_dir = tmp_path / "test-zips"
    zip_dir.mkdir()
    zip_files = (zip_dir / f"test{n}.zip" for n in itertools.count(1))

    def maker(name: str, version: str, install_dir: str = "new_install") -> str:
        zip_file = next(zip_files)
        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr(
                f"{install_dir}/METADATA.json",
                json.dumps({"name": name, "version": version}),
            )
        return urlunsplit(("file", "", str(PurePosixPath(zip_file.resolve())), "", ""))

    return maker


@pytest.mark.requiresinternet
def test_Installer_install_from_gh(
    target: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    installer = Installer(target)
    installer.install(InkexRequirement("inkex-bh==1.0.0rc3"))
    assert {p.name for p in Path(target, "extensions").iterdir()} == {
        "other",
        "nondist",
        "org.dairiki.inkex_bh",
    }
    assert "uninstalling" not in caplog.text
    assert "installing inkex-bh==1.0.0rc3" in caplog.text


def test_Installer_install_from_file(
    target: Path, make_distzip: ZipMaker, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    installer = Installer(target)
    download_url = make_distzip("bh_symbols", "0.1a1+test", "new")
    installer.install(InkexRequirement(f"bh-symbols @ {download_url}"))
    assert {p.name for p in Path(target, "symbols").iterdir()} == {
        "new",
    }
    assert "uninstalling bh-symbols==0.1rc1" in caplog.text
    assert "installing bh-symbols==0.1a1+test" in caplog.text


def test_Installer_install_dry_run(
    target: Path, make_distzip: ZipMaker, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    installer = Installer(target, dry_run=True)
    download_url = make_distzip("bh_symbols", "0.1a1+test", "new")
    installer.install(InkexRequirement(f"bh-symbols @ {download_url}"))
    assert {p.name for p in Path(target, "symbols").iterdir()} == {
        "old",
    }
    assert "uninstalling bh-symbols==0.1rc1" in caplog.text
    assert "installing bh-symbols==0.1a1+test" in caplog.text


def test_Installer_install_already_installed(
    target: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    installer = Installer(target)
    installer.install(InkexRequirement("bh.symbols"))
    assert {p.name for p in Path(target, "symbols").iterdir()} == {"old"}
    assert "bh.symbols==0.1rc1 is already installed" in caplog.text


def test_Installer_install_no_distribution_found(
    target: Path, caplog: pytest.LogCaptureFixture, mocker: MockerFixture
) -> None:
    github = mocker.patch("barnhunt.installer.github")
    github.iter_releases.return_value = iter([])
    caplog.set_level(logging.DEBUG)
    installer = Installer(target)
    with pytest.raises(NoSuchDistribution):
        installer.install(InkexRequirement("inkex-bh"))


def test_Installer_install_up_to_date(
    target: Path, caplog: pytest.LogCaptureFixture, mocker: MockerFixture
) -> None:
    github = mocker.patch("barnhunt.installer.github")
    github.iter_releases.return_value = iter([make_release("0.1rc1", [make_asset()])])
    caplog.set_level(logging.DEBUG)
    installer = Installer(target)
    installer.install(InkexRequirement("bh_symbols"), upgrade=True)
    assert "bh_symbols==0.1rc1 is up-to-date" in caplog.text


@pytest.mark.parametrize("pre_flag", [False, True])
def test_Installer_install_pre_flag(
    target: Path,
    pre_flag: bool,
    make_distzip: ZipMaker,
    caplog: pytest.LogCaptureFixture,
    mocker: MockerFixture,
) -> None:
    github = mocker.patch("barnhunt.installer.github")
    github.iter_releases.return_value = iter(
        [
            make_release("1.0.1", [make_asset(make_distzip("inkex-bh", "1.0.1"))]),
            make_release("1.1rc1", [make_asset(make_distzip("inkex-bh", "1.1rc1"))]),
        ]
    )
    caplog.set_level(logging.DEBUG)
    installer = Installer(target)
    installer.install(InkexRequirement("inkex-bh"), pre_flag=pre_flag)
    assert any(p.name == "new_install" for p in Path(target, "extensions").iterdir())
    if pre_flag:
        assert "installing inkex-bh==1.0.1" not in caplog.text
        assert "installing inkex-bh==1.1rc1" in caplog.text
    else:
        assert "installing inkex-bh==1.0.1" in caplog.text
        assert "installing inkex-bh==1.1rc1" not in caplog.text


def test_Installer_uninstall(
    target: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    installer = Installer(target)
    installer.uninstall(InkexRequirement("inkex-bh"))
    assert {p.name for p in Path(target, "extensions").iterdir()} == {
        "other",
        "nondist",
    }
    assert len(caplog.records) == 0

    installer.uninstall(InkexRequirement("bh.symbols"))
    assert {p.name for p in Path(target, "symbols").iterdir()} == set()
    assert "uninstalling bh.symbols==0.1rc1" in caplog.text
