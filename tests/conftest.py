from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from barnhunt.cli import default_inkscape_command


@pytest.fixture
def tests_dir() -> Path:
    return Path(__file__).parent


@pytest.fixture
def test1_pdf(tests_dir: Path) -> Path:
    return tests_dir / "test1.pdf"


@pytest.fixture
def test2_pdf(tests_dir: Path) -> Path:
    return tests_dir / "test2.pdf"


@pytest.fixture
def drawing_svg(tests_dir: Path) -> Path:
    return tests_dir / "drawing.svg"


@pytest.fixture
def tmp_drawing_svg(tmp_path: Path, drawing_svg: Path) -> Path:
    tmp_drawing_svg = tmp_path / drawing_svg.name
    shutil.copyfile(drawing_svg, tmp_drawing_svg)
    return tmp_drawing_svg


_inkscape_executable = shutil.which(
    os.environ.get("INKSCAPE_COMMAND", default_inkscape_command())
)


@pytest.fixture
def inkscape_executable() -> str:
    """Path to inkscape executable."""
    if _inkscape_executable is None:
        pytest.skip("test requires inkscape")
    return _inkscape_executable
