import logging
import os
from pathlib import Path
import re
from shutil import copyfile

from click.testing import CliRunner
from lxml import etree
from PyPDF2 import PdfFileReader
import pytest

from barnhunt import main


@pytest.fixture
def tmp_drawing_svg(tmp_path):
    drawing_svg = Path(__file__).parent.joinpath('drawing.svg')
    tmp_drawing_svg = tmp_path.joinpath('drawing.svg')
    copyfile(drawing_svg, tmp_drawing_svg)
    return tmp_drawing_svg


def test_random_seed(tmp_drawing_svg, caplog):
    caplog.set_level(logging.INFO)
    svgfile = tmp_drawing_svg.__fspath__()

    def get_random_seed():
        tree = etree.parse(svgfile)
        root = tree.getroot()
        assert root.tag == '{http://www.w3.org/2000/svg}svg'
        value = root.attrib[
            '{http://dairiki.org/barnhunt/inkscape-extensions}random-seed'
        ]
        return int(value)

    def run_it(*args):
        cmd = ['random-seed']
        cmd.extend(args)
        cmd.append(svgfile)
        runner = CliRunner()
        result = runner.invoke(main, cmd)
        assert result.exit_code == 0

    # Set seed in SVG file without pre-existing seed
    run_it()
    random_seed = get_random_seed()
    assert isinstance(random_seed, int)

    # Check that existing seed is not overwritten
    caplog.clear()
    run_it()
    assert get_random_seed() == random_seed
    assert re.search(r'\balready\b.*\bset\b', caplog.text)

    # Force overwriting of existin seed
    caplog.clear()
    run_it("--force-reseed")
    assert get_random_seed() != random_seed
    assert not re.search(r'\balready\b.*\bset\b', caplog.text)


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
    outputs = {f.relto(tmpdir) for f in tmpdir.visit()}
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


def test_2up(tmpdir, test1_pdf):
    outfile = tmpdir.join('output.pdf')
    runner = CliRunner()
    result = runner.invoke(main, ['2up', '-o', str(outfile), str(test1_pdf)])
    assert result.exit_code == 0
    assert outfile.exists()
