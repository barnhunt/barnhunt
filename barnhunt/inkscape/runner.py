from contextlib import contextmanager
import errno
import locale
import logging
import os
from subprocess import check_call, STDOUT
from tempfile import NamedTemporaryFile, TemporaryFile
import threading

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

    This is thread-safe.  If called from multiple threads, a seperate
    inkscape process will be run for each thread.

    """
    def __init__(self, executable='inkscape',
                 inkscape_args=['--shell'],
                 timeout=30):
        self._threadlocal = threading.local()
        self.executable = executable
        self.inkscape_args = inkscape_args
        self.timeout = timeout

    @property
    def child(self):
        return getattr(self._threadlocal, 'child', None)

    @child.setter
    def child(self, value):
        self._threadlocal.child = value

    _lock = threading.Lock()

    def __call__(self, args):
        cmdline = ' '.join(shellescape.quote(arg) for arg in args)
        if self.child is None:
            self._start_child()
        log.debug("Sending to shell-mode inkscape: %r", cmdline)
        self.child.sendline(cmdline)
        self._wait_for_prompt()

    @property
    def pid(self):
        if self.child:
            return self.child.pid

    def close(self):
        self.child = None

    def _start_child(self):
        log.debug("Starting shell-mode inkscape subprocess")
        encoding = locale.getpreferredencoding()
        self.child = pexpect.spawn(self.executable, self.inkscape_args,
                                   encoding=encoding,
                                   timeout=self.timeout)
        self._wait_for_prompt()

    def _wait_for_prompt(self, prompt=u'\n>', expect_lines=1):
        """Wait for prompt."""
        # NB: pexpect (==4.4.0) appears to be broken when
        # searchwindowsize is set to something other than None.
        #
        # The problem seems to be in `pexpect.expect.py`__, and is
        # triggered when multiple chunks of output are read before a
        # match is found.
        #
        # __ https://github.com/pexpect/pexpect/blob/master/pexpect/expect.py#L22
        self.child.expect_exact(u'\n>') #, searchwindowsize=len(prompt))
        self._log_output(expect_lines)

    def _log_output(self, expect_lines=0):
        before = self.child.before
        if before and before.count('\n') + 1 != expect_lines:
            log.warn("Unexpected output from shell-mode inkscape:\n%s",
                     before.replace('\r\n', '\n'))


def ensure_directory_exists(path):
    try:
        os.makedirs(path)
    except OSError as ex:
        if ex.errno != errno.EEXIST:
            raise
    else:
        log.debug("created directory %r", path)


class Inkscape(object):
    def __init__(self, executable='inkscape', shell_mode=True):
        runner_class = ShellModeInkscape if shell_mode else RunInkscape
        self.run_inkscape = runner_class(executable)

    def export_pdf(self, tree, filename):
        log.debug("Writing %r", filename)
        dirpath = os.path.dirname(filename)
        if dirpath:
            ensure_directory_exists(dirpath)
        with NamedTemporaryFile(suffix='.svg') as svg:
            tree.write(svg, xml_declaration=True)
            svg.flush()
            self.run_inkscape([svg.name,
                               '--export-area-page',
                               '--export-pdf=%s' % filename])
        return filename

    def close(self):
        self.run_inkscape.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
