import logging
import os
import re

from click.testing import CliRunner
from PyPDF2 import PdfFileReader
import pytest

from barnhunt import main


@pytest.mark.parametrize('processes', [None, '1'])
def test_pdfs(tmpdir, caplog, processes):
    caplog.set_level(logging.INFO)
    here = os.path.dirname(__file__)
    drawing_svg = os.path.join(here, 'drawing.svg')
    cmd = ['pdfs', '-o', str(tmpdir), drawing_svg]
    if processes is not None:
        cmd[1:1] = ['-p', processes]
    runner = CliRunner()
    result = runner.invoke(main, cmd)
    assert result.exit_code == 0
    outputs = set(f.relto(tmpdir) for f in tmpdir.visit())
    assert outputs == {
        'novice.pdf',
        'Master_1',
        'Master_1/Blind_1.pdf',
        }

    # Check that template was expanded
    pdf = PdfFileReader(open(str(tmpdir.join('novice.pdf')), 'rb'))
    assert 'Novice 1' in pdf.pages[0].extractText()


def test_rats():
    runner = CliRunner()
    result = runner.invoke(main, ['rats'])
    assert result.exit_code == 0
    assert re.sub(r'[1-5]', 'X', result.output) == (
        "X X X X X\n" * 5
        )


def test_coords():
    runner = CliRunner()
    result = runner.invoke(main, ['coords', '-n', '50'])
    assert result.exit_code == 0
    lines = result.output.rstrip().split('\n')
    pairs = [list(map(int, line.split(',')))
             for line in lines if line]
    assert len(pairs) == 50
    for x, y in pairs:
        assert 0 <= x <= 25
        assert 0 <= y <= 30


@pytest.fixture
def pdf1():
    here = os.path.dirname(__file__)
    return os.path.join(here, 'test1.pdf')


def test_2up(tmpdir, pdf1):
    runner = CliRunner()
    result = runner.invoke(main, [
        '2up', '-o', str(tmpdir.join('output.pdf')), pdf1,
        ])
    assert result.exit_code == 0
    outputs = set(f.relto(tmpdir) for f in tmpdir.visit())
    assert outputs == {
        'output.pdf',
        }
