import sys
from pathlib import Path
from subprocess import CompletedProcess

import click
import pytest
from pytest_mock import MockerFixture

from barnhunt.inkscape.utils import get_user_data_directory


def test_get_user_data_directory(mocker: MockerFixture) -> None:
    mocker.patch("shutil.which")
    mocker.patch(
        "barnhunt.inkscape.utils.run",
        return_value=CompletedProcess((), 0, "cruft\n/path/to/config\n"),
    )
    assert get_user_data_directory() == Path("/path/to/config")


def test_get_user_data_directory_no_output(mocker: MockerFixture) -> None:
    mocker.patch("shutil.which")
    mocker.patch(
        "barnhunt.inkscape.utils.run", return_value=CompletedProcess((), 0, "")
    )
    with pytest.raises(ValueError):
        get_user_data_directory()


def test_get_user_data_directory_no_inkscape(mocker: MockerFixture) -> None:
    mocker.patch("shutil.which", return_value=None)
    with pytest.raises(FileNotFoundError):
        get_user_data_directory()


@click.command()
@click.option("--user-data-directory", is_flag=True)
def dummy_inkscape(user_data_directory: bool) -> None:
    if user_data_directory:
        print("cruft")
        print("/path/to/config")
    else:
        sys.exit(1)


if __name__ == "__main__":
    dummy_inkscape()
