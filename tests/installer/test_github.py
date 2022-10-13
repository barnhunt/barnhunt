import pytest

from barnhunt.installer.github import iter_releases


@pytest.mark.requiresinternet
def test_iter_releases() -> None:
    # Pass per_page=1 to test page traversal
    for n, release in enumerate(iter_releases("actions", "setup-python", per_page=1)):
        assert release.html_url.startswith("https://github.com/actions/setup-python/")
        if n:
            break
    assert n == 1
