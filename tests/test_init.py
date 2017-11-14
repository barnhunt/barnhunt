import re

from click.testing import CliRunner

from barnhunt import main


def test_rats():
    runner = CliRunner()
    result = runner.invoke(main, ['rats'])
    assert result.exit_code == 0
    assert re.sub(r'[1-5]', 'X', result.output) == (
        "X X X X X\n" * 5
        )


def test_coords():
    runner = CliRunner()
    result = runner.invoke(main, ['coords'])
    assert result.exit_code == 0
    lines = result.output.rstrip().split('\n')
    pairs = [list(map(int, line.split(','))) for line in lines]
    assert len(pairs) == 10
    for x, y in pairs:
        assert 0 <= x <= 25
        assert 0 <= y <= 30
