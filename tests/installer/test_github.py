from __future__ import annotations

import os

import pytest

from barnhunt.installer.github import iter_releases

from ratelimit import mayberatelimited  # noreorder (test library)


@pytest.mark.requiresinternet
@mayberatelimited
def test_iter_releases() -> None:
    github_token = os.environ.get("GITHUB_TOKEN")

    # Pass per_page=1 to test page traversal
    for n, release in enumerate(
        iter_releases("actions", "setup-python", per_page=1, github_token=github_token)
    ):
        assert release.html_url.startswith("https://github.com/actions/setup-python/")
        if n:
            break
    assert n == 1
