# FIXME: Move this module into .inkscape.runner

from contextlib import contextmanager
import locale
import logging
import os
from subprocess import check_call, STDOUT
from tempfile import NamedTemporaryFile, TemporaryFile

import pexpect
import shellescape

log = logging.getLogger()


class RunInkscape(object):
    """ Run inkscape with specific arguments.
    """
    def __init__(self, executable='inkscape'):
        self.executable = executable

    def __call__(self, args):
        cmd = [self.executable] + args
        with logging_output(cmd) as logfile:
            check_call(cmd, stdout=logfile, stderr=STDOUT)

    def close(self):
        pass


@contextmanager
def logging_output(cmd):
    """Yield a file handle to be used for logging subcommand output.

    If output is generated, generates a log message with the output.
    """
    with TemporaryFile() as logfile:
        try:
            yield logfile
        finally:
            logfile.flush()
            if logfile.tell() > 0:
                logfile.seek(0)
                log.warn("Unexpected output from %r:\n%s",
                         cmd, logfile.read())


class ShellModeInkscape(object):
    """Run inkscape with specific arguments.

    This uses inkscape's --shell mode so that (for efficiency)
    multiple commands may be run with a single invocation of inkscape.

    """
    def __init__(self, executable='inkscape', inkscape_args=['--shell']):
        self.executable = executable
        self.inkscape_args = inkscape_args
        self.child = None

    def __call__(self, args):
        cmdline = ' '.join(shellescape.quote(arg) for arg in args)
        if self.child is None:
            log.debug("Starting shell-mode inkscape subprocess")
            encoding = locale.getpreferredencoding()
            self.child = pexpect.spawn(self.executable, self.inkscape_args,
                                       encoding=encoding)
            self._wait_for_prompt()
        log.debug("Sending to shell-mode inkscape: %r", cmdline)
        self.child.sendline(cmdline)
        self._wait_for_prompt()

    def close(self):
        child = self.child
        if child is not None:
            log.debug("Shutting down shell-mode inkscape subprocess")
            child.sendline('quit')
            child.expect(u'quit\r?\n')
            child.expect(pexpect.EOF)
            self._log_output()
            self.child = None

    def _wait_for_prompt(self, prompt=u'\n>', expect_lines=1):
        """Wait for prompt."""
        self.child.expect_exact(prompt, searchwindowsize=len(prompt))
        self._log_output(expect_lines)

    def _log_output(self, expect_lines=0):
        before = self.child.before
        if before and before.count('\n') + 1 != expect_lines:
            log.warn("Unexpected output from shell-mode inkscape:\n%s",
                     before.replace('\r\n', '\n'))


class Inkscape(object):
    def __init__(self, executable='inkscape', shell_mode=True):
        runner_class = ShellModeInkscape if shell_mode else RunInkscape
        self.run_inkscape = runner_class(executable)

    def export_pdf(self, tree, filename):
        dirpath = os.path.dirname(filename)
        if dirpath and not os.path.isdir(dirpath):
            log.debug("creating directory %r", dirpath)
            os.makedirs(dirpath)

        with NamedTemporaryFile(suffix='.svg') as svg:
            tree.write(svg, xml_declaration=True)
            svg.flush()
            self.run_inkscape([svg.name, '--export-pdf=%s' % filename])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.run_inkscape.close()
