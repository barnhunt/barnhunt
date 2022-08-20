import subprocess
import sys

import pytest

from barnhunt.__main__ import main


def test_execute_package():
    proc = subprocess.run(
        [sys.executable, "-m", "barnhunt", "--help"],
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )
    assert "export pdfs from inkscape" in proc.stdout.lower()


def test_main(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    std = capsys.readouterr()
    assert "export pdfs from inkscape" in std.out.lower()
