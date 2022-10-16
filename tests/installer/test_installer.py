from __future__ import annotations

import datetime
import io
import itertools
import json
import os
import re
import zipfile
from pathlib import Path
from pathlib import PurePosixPath
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

from ratelimit import mayberatelimited  # noreorder (test library)


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
    urlopen = mocker.patch("barnhunt.installer.urlopen")
    urlopen.return_value = io.BytesIO(zip_data)
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


class DummyTarget:
    def __init__(self, path: Path):
        path.mkdir(exist_ok=True)
        self.path = path

    def add_dist(
        self,
        dir_name: str | None = None,
        **metadata: str,  # name and version, mostly
    ) -> Path:
        if dir_name:
            dist_path = self.path / dir_name
        else:
            base_name = re.sub(r"(?i)[^a-z0-9]", "_", metadata.get("name", "distdir"))
            dist_paths = (self.path / f"{base_name}_{n}" for n in itertools.count(1))
            for dist_path in dist_paths:
                if not dist_path.exists():
                    break
        dist_path.mkdir(parents=True)
        Path(dist_path, "junk.txt").touch()
        if metadata:
            Path(dist_path, "METADATA.json").write_text(json.dumps(metadata))
        return dist_path

    def __fspath__(self) -> str:
        return os.fspath(self.path)


@pytest.fixture
def target(tmp_path: Path) -> DummyTarget:
    return DummyTarget(tmp_path / "target")


def test_find_installed(target: DummyTarget) -> None:
    target.add_dist("not_a_dist")
    target.add_dist(name="wrong-proj", version="1.0")
    dist_path = target.add_dist(name="test_proj", version="1.2")

    assert find_installed(target, canonicalize_name("test.proj")) == {
        Version("1.2"): dist_path,
    }


@pytest.mark.parametrize("dir_exists", [False, True])
def test_find_installed_raises(dir_exists: bool, tmp_path: Path) -> None:
    distdir = tmp_path / "distdir"
    if dir_exists:
        distdir.mkdir()
    assert find_installed(distdir, canonicalize_name("inkex-bh")) == {}


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
    github.iter_releases.assert_called_once_with("foo", "bar", github_token=None)


@pytest.fixture
def target1(target: DummyTarget) -> Path:
    target.add_dist("extensions/other", name="other", version="1.0")
    target.add_dist("extensions/nondist")
    target.add_dist("symbols/old", name="bh-symbols", version="0.1rc1")
    return target.path


class ZipMaker:
    def __init__(self, zip_dir: Path):
        zip_dir.mkdir(exist_ok=True)
        self.zip_dir = zip_dir
        self._zip_files = (zip_dir / f"test{n}.zip" for n in itertools.count(1))

    def __call__(self, install_dir: str = "new", **metadata: str) -> str:
        zip_file = next(self._zip_files)
        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr(f"{install_dir}/METADATA.json", json.dumps(metadata))
        return urlunsplit(("file", "", str(PurePosixPath(zip_file.resolve())), "", ""))


@pytest.fixture
def zip_maker(tmp_path: Path) -> ZipMaker:
    return ZipMaker(tmp_path / "test-zips")


@pytest.mark.requiresinternet
@mayberatelimited
def test_Installer_install_from_gh(
    target: DummyTarget, caplog: pytest.LogCaptureFixture
) -> None:
    target.add_dist("extensions/other", name="other", version="1.0")
    target.add_dist("extensions/nondist")
    installer = Installer(target, github_token=os.environ.get("GITHUB_TOKEN"))
    installer.install(InkexRequirement("inkex-bh==1.0.0rc3"))
    assert {p.name for p in Path(target, "extensions").iterdir()} == {
        "other",
        "nondist",
        "org.dairiki.inkex_bh",
    }
    assert "uninstalling" not in caplog.text
    assert "installing inkex-bh==1.0.0rc3" in caplog.text


@pytest.mark.parametrize("dry_run", [False, True])
def test_Installer_install_from_file(
    dry_run: bool,
    target: DummyTarget,
    zip_maker: ZipMaker,
    caplog: pytest.LogCaptureFixture,
) -> None:
    target.add_dist("symbols/old", name="bh-symbols", version="0.1rc1")
    installer = Installer(target, dry_run=dry_run)
    download_url = zip_maker(name="bh_symbols", version="0.1a1+test")
    installer.install(InkexRequirement(f"bh-symbols @ {download_url}"))
    assert {p.name for p in Path(target, "symbols").iterdir()} == {
        "old" if dry_run else "new"
    }
    assert "uninstalling bh-symbols==0.1rc1" in caplog.text
    assert "installing bh-symbols==0.1a1+test" in caplog.text


def test_Installer_install_already_installed(
    target: DummyTarget, caplog: pytest.LogCaptureFixture
) -> None:
    target.add_dist("symbols/old", name="bh-symbols", version="0.1rc1")
    installer = Installer(target)
    installer.install(InkexRequirement("bh.symbols"))
    assert {p.name for p in Path(target, "symbols").iterdir()} == {"old"}
    assert "bh.symbols==0.1rc1 is already installed" in caplog.text


def test_Installer_install_no_distribution_found(
    target: DummyTarget, caplog: pytest.LogCaptureFixture, mocker: MockerFixture
) -> None:
    github = mocker.patch("barnhunt.installer.github")
    github.iter_releases.return_value = iter([])
    installer = Installer(target)
    with pytest.raises(NoSuchDistribution):
        installer.install(InkexRequirement("inkex-bh"))


def test_Installer_install_up_to_date(
    target: DummyTarget, caplog: pytest.LogCaptureFixture, mocker: MockerFixture
) -> None:
    target.add_dist("symbols/old", name="bh-symbols", version="0.1rc1")
    github = mocker.patch("barnhunt.installer.github")
    github.iter_releases.return_value = iter([make_release("0.1rc1", [make_asset()])])
    installer = Installer(target)
    installer.install(InkexRequirement("bh_symbols"), upgrade=True)
    assert "bh_symbols==0.1rc1 is up-to-date" in caplog.text


def test_Installer_install_multiple_installed(
    target: DummyTarget, caplog: pytest.LogCaptureFixture
) -> None:
    target.add_dist("symbols/dup1", name="bh-symbols", version="0.1rc1")
    target.add_dist("symbols/dup2", name="bh-symbols", version="0.2")
    installer = Installer(target)
    installer.install(InkexRequirement("bh.symbols"))
    assert {p.name for p in Path(target, "symbols").iterdir()} == {"dup1", "dup2"}
    assert "found multiple installed versions of bh.symbols" in caplog.text
    assert "bh.symbols==0.2 is already installed" in caplog.text


@pytest.mark.parametrize("pre_flag", [False, True])
def test_Installer_install_pre_flag(
    target: DummyTarget,
    pre_flag: bool,
    zip_maker: ZipMaker,
    caplog: pytest.LogCaptureFixture,
    mocker: MockerFixture,
) -> None:
    github = mocker.patch("barnhunt.installer.github")
    github.iter_releases.return_value = (
        make_release(version, [make_asset(zip_maker(name="inkex-bh", version=version))])
        for version in ("1.0.1", "1.1rc1")
    )

    installer = Installer(target)
    installer.install(InkexRequirement("inkex-bh"), pre_flag=pre_flag)

    assert {p.name for p in Path(target, "extensions").iterdir()} == {"new"}

    selected, unselected = ("1.1rc1", "1.0.1") if pre_flag else ("1.0.1", "1.1rc1")
    assert f"installing inkex-bh=={selected}" in caplog.text
    assert f"installing inkex-bh=={unselected}" not in caplog.text


@pytest.mark.parametrize("was_installed", [False, True])
def test_Installer_uninstall(
    was_installed: bool,
    target: DummyTarget,
    caplog: pytest.LogCaptureFixture,
) -> None:
    target.add_dist("extensions/other", name="other", version="1.0")
    target.add_dist("extensions/nondist")
    if was_installed:
        target.add_dist("extensions/old", name="inkex_bh", version="42.0")
    installer = Installer(target)
    installer.uninstall(InkexRequirement("inkex-bh"))
    assert {p.name for p in Path(target, "extensions").iterdir()} == {
        "other",
        "nondist",
    }
    if was_installed:
        assert "uninstalling inkex-bh==42.0" in caplog.text
    else:
        assert len(caplog.records) == 0
