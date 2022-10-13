from __future__ import annotations

import io
import logging
import shutil
import zipfile
from contextlib import contextmanager
from contextlib import ExitStack
from operator import attrgetter
from pathlib import Path
from tempfile import TemporaryFile
from typing import IO
from typing import Iterator
from typing import NamedTuple
from typing import NewType
from typing import TYPE_CHECKING
from urllib import request

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.utils import NormalizedName
from packaging.version import InvalidVersion
from packaging.version import Version

from barnhunt.installer import github
from barnhunt.installer.metadata import InvalidDistribution
from barnhunt.installer.metadata import metadata_from_distdir
from barnhunt.installer.metadata import metadata_from_distzip

if TYPE_CHECKING:
    from _typeshed import StrPath
else:
    StrPath = object


DownloadUrl = NewType("DownloadUrl", str)


log = logging.getLogger()


class NoSuchDistribution(KeyError):
    """Raised if no matching distribution is found."""


class InkexProject(NamedTuple):
    install_dir: str  # FIXME: "type"?
    gh_owner: str
    gh_repo: str


INKEX_PROJECTS: dict[NormalizedName, InkexProject] = {
    canonicalize_name(name): project
    for name, project in [
        ("inkex-bh", InkexProject("extensions", "barnhunt", "inkex-bh")),
        ("bh-symbols", InkexProject("symbols", "barnhunt", "bh-symbols")),
    ]
}


class InkexRequirement(Requirement):
    url: DownloadUrl | None

    def __init__(self, requirement: str):
        super().__init__(requirement)
        self._validate()

    @property
    def project(self) -> InkexProject:
        return INKEX_PROJECTS[canonicalize_name(self.name)]

    def _validate(self) -> None:
        if canonicalize_name(self.name) not in INKEX_PROJECTS:
            raise ValueError(f"unknown requirement name {self.name!r}")
        if self.extras:
            raise ValueError("requirement extras not supported")
        if self.marker:
            raise ValueError("requirement markers not supported")


DEFAULT_REQUIREMENTS = tuple(InkexRequirement(name) for name in INKEX_PROJECTS)


@contextmanager
def _copy_to_tmp(fp: io.BufferedIOBase) -> Iterator[IO[bytes]]:
    with TemporaryFile() as tmp:
        for chunk in iter(fp.read1, b""):
            tmp.write(chunk)
        tmp.flush()
        tmp.seek(0)
        yield tmp


@contextmanager
def open_zipfile(url: DownloadUrl) -> Iterator[zipfile.ZipFile]:
    resp = request.urlopen(url)
    with ExitStack() as stack:
        resp = stack.enter_context(resp)
        if resp.seekable():
            fp = resp
        else:
            fp = stack.enter_context(_copy_to_tmp(resp))
        zf = zipfile.ZipFile(fp)
        yield stack.enter_context(zf)


class Installer:
    def __init__(self, target: StrPath):
        self.target = Path(target)

    def install(
        self,
        requirement: InkexRequirement,
        pre_flag: bool = False,
        upgrade: bool = False,
        dry_run: bool = False,
    ) -> None:
        display_name = requirement.name
        canonical_name = canonicalize_name(requirement.name)
        specifiers = requirement.specifier
        project = requirement.project
        prereleases = True if pre_flag else None

        install_path = self.target / project.install_dir
        installed = find_installed(install_path, canonical_name)
        # FIXME: warn if len(installed) > 1
        versions = installed.keys()
        # XXX: should pass prereleases=True?  If we have matching pre-release installed
        # it's okay?
        matching_version = max(specifiers.filter(versions, prereleases), default=None)
        if matching_version and not upgrade and requirement.url is None:
            log.info("%s==%s is already installed", display_name, matching_version)
            return

        if requirement.url is None:
            dist_urls = find_distributions(project)
            try:
                version = max(specifiers.filter(dist_urls.keys(), prereleases))
            except ValueError as exc:
                raise NoSuchDistribution(
                    f"no distribution found for {requirement}"
                ) from exc

            if matching_version == version:
                log.info("%s==%s is up-to-date", display_name, version)
                return
            download_url = dist_urls[version]
        else:
            version = None
            download_url = requirement.url

        # FIXME: check hashes?
        with open_zipfile(download_url) as zf:
            metadata = metadata_from_distzip(zf)
            # FIXME: better exceptions
            if version is not None:
                assert metadata.version == version
            assert metadata.canonical_name == canonical_name

            for version_, distdir in installed.items():
                log.info("uninstalling %s==%s at %s", display_name, version_, distdir)
                if not dry_run:
                    shutil.rmtree(distdir)

            log.info(
                "installing %s==%s to %s", display_name, metadata.version, install_path
            )
            if not dry_run:
                zf.extractall(install_path)


def find_installed(
    install_path: Path, canonical_name: NormalizedName
) -> dict[Version, Path]:
    installed: dict[Version, Path] = {}
    for distdir in Path(install_path).iterdir():
        try:
            metadata = metadata_from_distdir(distdir)
        except InvalidDistribution:
            continue
        if metadata.canonical_name == canonical_name:
            # FIXME: warn/fix on duplicate version?
            installed[metadata.version] = distdir
    return installed


def find_distributions(project: InkexProject) -> dict[Version, DownloadUrl]:
    """Find zip files assets attached to the releases for a GitHub repository.

    This returns a dict mapping versions to download URLs.

    Releases whose ``tag_name``s are not parseable as PEP440 version identifiers,
    and those that do not have a zip-file among their assets are ignored.
    """
    dists = {}
    for release in github.iter_releases(project.gh_owner, project.gh_repo):
        try:
            version = Version(release.tag_name)
        except InvalidVersion:
            continue  # FIXME: warn?
        try:
            dists[version] = _get_download_url(release)
        except ValueError:
            continue  # FIXME: warn?
    return dists


def _get_download_url(release: github.Release) -> DownloadUrl:
    for asset in sorted(release.assets, key=attrgetter("updated_at"), reverse=True):
        if asset.content_type == "application/zip":
            if asset.browser_download_url:
                return DownloadUrl(asset.browser_download_url)
    raise ValueError("No zip-file asset found")
