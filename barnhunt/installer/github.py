import datetime
from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import quote

import marshmallow
import requests
from marshmallow_dataclass import class_schema


@dataclass
class ReleaseAsset:
    name: str
    label: str | None
    state: str  # enum: "uploaded", "open"
    download_count: int
    content_type: str
    size: int
    browser_download_url: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Meta:
        unknown = marshmallow.EXCLUDE


@dataclass
class Release:
    name: str | None
    body: str | None
    tag_name: str
    html_url: str
    draft: bool
    prerelease: bool
    created_at: datetime.datetime
    published_at: datetime.datetime | None
    assets: list[ReleaseAsset]

    class Meta:
        unknown = marshmallow.EXCLUDE


ReleaseSchema = class_schema(Release)


def iter_releases(
    owner: str,
    repo: str,
    per_page: int | None = None,
    *,
    github_token: str | None = None,
) -> Iterator[Release]:
    """Fetch releases for a GitHub repository.

    This uses GitHub’s `REST API`_ to download release data, including asset metadata,
    for the specified repository.

    .. _REST API: https://docs.github.com/en/rest/releases/releases
    """
    session = requests.Session()
    session.headers["Accept"] = "application/vnd.github+json"
    session.headers["User-Agent"] = "barnhunt (https://github.com/barnhunt/barnhunt)"
    if github_token is not None:
        session.headers["Authorization"] = f"Bearer {github_token}"
    releases_schema = ReleaseSchema(many=True)

    url = f"https://api.github.com/repos/{quote(owner)}/{quote(repo)}/releases"
    if per_page is not None:
        url += f"?per_page={per_page:d}"

    while url is not None:
        response = session.get(url)
        response.raise_for_status()
        assert response.status_code == 200
        yield from releases_schema.load(response.json())

        next = response.links.get("next")
        url = next["url"] if next else None
