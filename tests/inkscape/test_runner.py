import logging
import os
from subprocess import CalledProcessError
import sys

import pytest

from barnhunt.inkscape.runner import (
    Inkscape,
    RunInkscape,
    ShellModeInkscape,
    logging_output,
    )


class TestRunInkscape(object):
    def test_success(self):
        RunInkscape(executable='/bin/true')([])

    def test_failure(self, caplog):
        with pytest.raises(CalledProcessError):
            RunInkscape(executable='/bin/false')([])
        assert len(caplog.records) == 0

    def test_logs_output(self, caplog):
        RunInkscape(executable='/bin/echo')(['foo'])
        assert 'foo' in caplog.text

    def test_close(self):
        RunInkscape().close()


def test_logging_output(caplog):
    with logging_output('foo') as logfile:
        logfile.write(b'bar')
    assert len(caplog.records) == 1
    assert 'foo' in caplog.text
    assert 'bar' in caplog.text


class TestShellModeInkscape(object):
    @pytest.fixture
    def inkscape(self):
        here = os.path.dirname(os.path.abspath(__file__))
        dummy = os.path.join(here, 'dummy_inkscape.py')
        return ShellModeInkscape(executable=sys.executable,
                                 inkscape_args=[dummy])

    def test_success(self, inkscape, caplog):
        inkscape(['true'])
        assert not any(r.levelno >= logging.INFO for r in caplog.records)

    def test_logs_output(self, inkscape, caplog):
        inkscape(['echo', 'foo'])
        assert any(r.levelno >= logging.INFO for r in caplog.records)
        assert 'foo' in caplog.text

    def test_close(self, inkscape):
        inkscape(['true'])
        assert inkscape.child is not None
        inkscape.close()
        assert inkscape.child is None


class TestInkscape(object):
    @pytest.fixture
    def runner(self):
        return DummyInkscapeRunner()

    @pytest.fixture
    def tree(self):
        class DummyTree(object):
            def write(self, outfp, xml_declaration=False):
                pass
        return DummyTree()

    @pytest.fixture
    def inkscape(self, runner):
        rv = Inkscape()
        rv.run_inkscape = runner
        return rv

    def test_export_pdf(self, inkscape, runner, tree, tmpdir):
        output_path = str(tmpdir.join('foo/bar.pdf'))
        inkscape.export_pdf(tree, output_path)
        assert len(runner.commands) == 1
        args = runner.commands[0]
        assert args[1] == '--export-pdf=%s' % output_path
        assert tmpdir.join('foo').isdir()

    def test_contextmanager(self, inkscape, runner):
        with inkscape as rv:
            assert rv is inkscape
            assert not runner.closed
        assert runner.closed


class DummyInkscapeRunner(object):
    def __init__(self):
        self.commands = []
        self.closed = False

    def __call__(self, args):
        assert not self.closed
        self.commands.append(args)

    def close(self):
        self.closed = True
