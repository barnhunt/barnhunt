# -*- coding: utf-8 -*-
"""Support for paging output
"""
from __future__ import absolute_import
import sys

import click
from six import unichr

from .compat import enum


def get_pager(group_size):
    if sys.stdout.isatty() and sys.stdin.isatty():
        pager_class = TTYPager
    else:
        pager_class = Grouper
    return pager_class(group_size)


class Grouper(object):
    """Simple "pager" which just spews all lines to stdout, with blank
    lines every ``group_size`` lines.

    """
    def __init__(self, group_size):
        self.group_size = group_size

    def __call__(self, lines):
        group_size = self.group_size
        for i in range(0, len(lines), group_size):
            for line in lines[i:i + group_size]:
                print(line)
            print('')


class TTYPager(object):
    """Fancy terminal pager.

    Displays ``group_size`` lines per page.
    Highlights the current line.
    Allows for scrolling forward as well as backward.

    """
    def __init__(self, group_size):
        self.group_size = group_size

    def __call__(self, lines):
        group_size = self.group_size
        increments = {
            Command.DOWN: 1,
            Command.UP: -1,
            Command.PAGE_DOWN: group_size,
            Command.PAGE_UP: -group_size,
            Command.REDRAW: 0,
            }
        n = 0
        while lines:
            click.clear()
            beg = n - (n % group_size)
            group = lines[beg:beg + group_size]
            for i, line in enumerate(group, beg):
                hilight = i == n
                click.secho(line,
                            bold=hilight,
                            bg='cyan' if hilight else None)
            click.echo()
            click.echo(
                u"Viewing {beg}–{end}. [jkq] ".format(
                    beg=beg + 1,
                    end=i + 1),
                nl=False)

            cmd = self._get_cmd()
            if cmd == Command.QUIT:
                break
            next_n = n + increments[cmd]
            if 0 < next_n < len(lines):
                n = next_n
            else:
                click.echo("\a", nl=False)
        click.echo()

    def _get_cmd(self):
        while True:
            key = click.getchar()
            if key == '\x1b':
                key += click.getchar()
            try:
                return Command.lookup(key)
            except KeyError:
                click.echo('\a', nl=False)


def CTL(c):
    return chr(ord(c) & 0x1f)


def ESC(c):
    return '\x1b' + c


def ALT(c):
    return unichr(0x100 | ord(c))


def ANSI_CSI(s):
    return '\x1b[' + s


K_Prior = ANSI_CSI('5~')        # Page_Up
K_Next = ANSI_CSI('6~')         # Page_Down
K_Up = ANSI_CSI('A')            # Up arrow
K_Down = ANSI_CSI('B')          # Up arrow
K_Return = '\r'
K_Escape = '\x1b'


class Command(enum.Enum):
    """Commands recognized by TTYPager.

    The value of each enum is a tuple specifying which keys or key combinations
    can be used to activate the given command.

    """
    PAGE_DOWN = (
        ' ',
        'v', CTL('v'),
        'f', CTL('f'),
        K_Next,
        # 'z', ESC(' '), ALT(' '),
        # 'd', CTL('d'),
        )
    PAGE_UP = (
        'b', CTL('b'),
        ESC('v'), ALT('v'),
        K_Prior,
        # 'w',
        # 'u', CTL('u'),
        )
    UP = (
        'k', CTL('k'),
        'y', CTL('y'),
        CTL('p'),
        K_Up,
        )
    DOWN = (
        'j', CTL('j'),
        'e', CTL('e'),
        K_Return,
        K_Down,
        )
    REDRAW = (
        'r', CTL('r'),
        CTL('l'),
        'R',
        )
    QUIT = (
        'q',
        )

    def __init__(self, *keys):
        _lookup = getattr(self.__class__, '_lookup', None)
        if _lookup is None:
            self.__class__._lookup = _lookup = {}

        for key in keys:
            assert key not in _lookup, "redefinition of key {!r}".format(key)
            _lookup[key] = self

    @classmethod
    def lookup(cls, key):
        """Look up comand for ``key``.

        """
        return cls._lookup[key]