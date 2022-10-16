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
from typing import Mapping
from typing import NamedTuple
from typing import NewType
from typing import TYPE_CHECKING
from urllib.request import Request
from urllib.request import urlopen

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
    resp = urlopen(
        Request(
            url,
            headers={
                "User-Agent": "barnhunt (https://github.com/barnhunt/barnhunt)",
                "Accept": "application/zip, application/octet-stream;q=0.9, */*;q=0.1",
            },
        )
    )

    with ExitStack() as stack:
        resp = stack.enter_context(resp)
        if resp.seekable():
            fp = resp
        else:
            fp = stack.enter_context(_copy_to_tmp(resp))
        zf = zipfile.ZipFile(fp)
        yield stack.enter_context(zf)


class Installer:
    def __init__(
        self, target: StrPath, dry_run: bool = False, github_token: str | None = None
    ):
        self.target = Path(target)
        self.dry_run = dry_run
        self.github_token = github_token

    def install(
        self,
        requirement: InkexRequirement,
        pre_flag: bool = False,
        upgrade: bool = False,
    ) -> None:
        display_name = requirement.name
        canonical_name = canonicalize_name(requirement.name)
        specifiers = requirement.specifier
        project = requirement.project

        install_path = self.target / project.install_dir
        log.info("install_path is %s", install_path)
        installed = find_installed(install_path, canonical_name)
        versions = installed.keys()
        if len(versions) > 1:
            log.warning(
                "found multiple installed versions of %s: %s",
                display_name,
                ", ".join(map(str, versions)),
            )
        matching_version = max(
            specifiers.filter(versions, prereleases=True), default=None
        )
        if matching_version:
            if not upgrade and requirement.url is None:
                log.warning(
                    "%s==%s is already installed", display_name, matching_version
                )
                return
            log.debug("found installed %s==%s", display_name, matching_version)

        if requirement.url is None:
            dist_urls = find_distributions(project, self.github_token)
            log.debug(
                "found distributions for %s: %s",
                display_name,
                ", ".join(map(str, dist_urls.keys())),
            )
            prereleases = True if pre_flag else None
            try:
                version = max(specifiers.filter(dist_urls.keys(), prereleases))
            except ValueError as exc:
                raise NoSuchDistribution(
                    f"no distribution found for {requirement}"
                ) from exc

            if matching_version == version:
                log.warning("%s==%s is up-to-date", display_name, version)
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

            self._do_uninstall(display_name, installed)

            log.warning("installing %s==%s", display_name, metadata.version)
            if not self.dry_run:
                zf.extractall(install_path)

    def uninstall(self, requirement: InkexRequirement) -> None:
        canonical_name = canonicalize_name(requirement.name)
        install_path = self.target / requirement.project.install_dir
        installed = find_installed(install_path, canonical_name)
        self._do_uninstall(requirement.name, installed)

    def _do_uninstall(self, name: str, installed: Mapping[Version, Path]) -> None:
        for version, distdir in installed.items():
            log.warning("uninstalling %s==%s", name, version)
            log.info("removing %s", distdir)
            if not self.dry_run:
                shutil.rmtree(distdir)


def find_installed(
    install_path: StrPath, canonical_name: NormalizedName
) -> dict[Version, Path]:
    install_path = Path(install_path)
    installed: dict[Version, Path] = {}
    if install_path.is_dir():
        for distdir in install_path.iterdir():
            try:
                metadata = metadata_from_distdir(distdir)
            except InvalidDistribution:
                continue
            if metadata.canonical_name == canonical_name:
                # FIXME: warn/fix on duplicate version?
                installed[metadata.version] = distdir
    return installed


def find_distributions(
    project: InkexProject, github_token: str | None = None
) -> dict[Version, DownloadUrl]:
    """Find zip files assets attached to the releases for a GitHub repository.

    This returns a dict mapping versions to download URLs.

    Releases whose ``tag_name``s are not parseable as PEP440 version identifiers,
    and those that do not have a zip-file among their assets are ignored.
    """
    dists = {}
    for release in github.iter_releases(
        project.gh_owner, project.gh_repo, github_token=github_token
    ):
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
