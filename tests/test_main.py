import subprocess
import sys

import barnhunt.__main__  # noqa: F401

# import for coverage


def test_execute_package() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "barnhunt", "--help"],
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )
    assert "export pdfs from inkscape" in proc.stdout.lower()
