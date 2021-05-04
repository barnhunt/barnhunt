# -*- coding: utf-8 -*-
import sys

import pytest

from barnhunt.pager import (
    Command,
    Grouper,
    TTYPager,
    get_pager,
    )


@pytest.fixture
def tty_output(monkeypatch):
    monkeypatch.setattr(sys.stdout, 'isatty', lambda: True)
    monkeypatch.setattr(sys.stdin, 'isatty', lambda: True)


@pytest.mark.usefixtures('tty_output')
def test_get_pager_returns_ttypager():
    pager = get_pager(42)
    assert isinstance(pager, TTYPager)
    assert pager.group_size == 42


@pytest.mark.usefixtures('tty_output')
def test_get_pager_returns_grouper():
    sys.stdin.isatty = lambda: False
    pager = get_pager(43)
    assert isinstance(pager, Grouper)
    assert pager.group_size == 43


def test_Grouper(capsys):
    pager = Grouper(3)
    pager(["%d" % n for n in range(5)])
    output = capsys.readouterr().out
    assert output.split('\n') == [
        '0', '1', '2', '', '3', '4', '', ''
        ]


class TestTTYPager(object):
    @pytest.fixture
    def pager(self):
        return TTYPager(2)

    @pytest.fixture(autouse=True)
    def patch_getchar(self, keys, monkeypatch):
        keys = iter(keys)

        def getchar():
            return next(keys)
        monkeypatch.setattr('click.getchar', getchar)

    @pytest.mark.parametrize('keys', [
        ('v', 'q'),
        ])
    def test(self, pager, capsys):
        lines = ['one', 'two', 'three']
        pager(lines)
        output = capsys.readouterr().out
        for line in lines:
            assert line in output
        assert '\a' not in output

    @pytest.mark.parametrize('keys', [
        ('q',),
        ])
    def test_first_page(self, pager, capsys):
        lines = ['one', 'two', 'three']
        pager(lines)
        output = capsys.readouterr().out
        for line in lines[:2]:
            assert line in output
        assert lines[2] not in output

    @pytest.mark.parametrize('keys', [
        ('k', 'q'),
        ])
    def test_beep(self, pager, capsys):
        lines = ['one', 'two', 'three']
        pager(lines)
        output = capsys.readouterr().out
        assert '\a' in output

    @pytest.mark.parametrize('keys, command', [
        (('v',), Command.PAGE_DOWN),
        (('\x1b', 'v'), Command.PAGE_UP),
        ])
    def test_get_cmd(self, pager, command):
        assert pager._get_cmd() == command

    @pytest.mark.parametrize('keys, command', [
        (('x', 'q'), Command.QUIT),
        (('\x1b', 'x', 'r'), Command.REDRAW),
        ])
    def test_get_cmd_unrecognized_key(self, pager, command, capsys):
        assert pager._get_cmd() == command
        assert capsys.readouterr().out == '\a'


@pytest.mark.parametrize('key, command', [
    (' ', Command.PAGE_DOWN),
    ('q', Command.QUIT),
    ])
def test_Command_lookup(key, command):
    assert Command.lookup(key) == command


def test_Command_lookup_raises_KeyError():
    with pytest.raises(KeyError):
        Command.lookup('x')
