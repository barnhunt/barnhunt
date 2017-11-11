from contextlib import contextmanager
import logging
import os
import re
from subprocess import check_call, STDOUT
from tempfile import NamedTemporaryFile, TemporaryFile

import click
from lxml import etree
import pexpect
import shellescape

from .main import main

log = logging.getLogger('')

SVG = "{http://www.w3.org/2000/svg}"
INKSCAPE = "{http://www.inkscape.org/namespaces/inkscape}"


def _find_layers(elem):
    layers = []
    for g in elem.findall(SVG + 'g'):
        if g.get(INKSCAPE + 'groupmode') == 'layer':
            layers.insert(0, Layer(g))
    return layers


class Layer(object):
    def __init__(self, elem):
        self.elem = elem
        self.sublayers = _find_layers(elem)

    @property
    def id(self):
        return self.elem.get('id')

    @property
    def label(self):
        return self.elem.get(INKSCAPE + 'label')

    def _set_display(self, visibility):
        elem = self.elem
        style = elem.get('style') or ''
        bits = [bit for bit in style.split(';')
                if not bit.strip().startswith('display:')]
        bits.append('display:%s' % visibility)
        elem.set('style', ';'.join(bits))

    def walk(self):
        """ Depth first traversal of self and sublayers.
        """
        layers = [self]
        while layers:
            layer = layers.pop(0)
            layers[:0] = layer.sublayers
            yield layer

    def show(self, recursive=False):
        layers = self.walk() if recursive else [self]
        for layer in layers:
            layer._set_display('inline')

    def hide(self):
        self._set_display('none')

    def __repr__(self):
        return "<Layer %s %r [%d sublayers]>" % (
            self.id, self.label, len(self.sublayers))

    def __str__(self):
        return self.id

    def __unicode__(self):
        return self.id


class Drawing(object):
    def __init__(self, svgfile):
        RING = re.compile(r'\bring\b', re.I)
        COURSE = re.compile(
            r'\b(instinct|novice|open|senior|master|crazy ?8s?|c8)\b',
            re.I)

        tree = etree.parse(svgfile)
        root = tree.getroot()

        layers = _find_layers(root)

        rings = [layer for layer in layers if RING.search(layer.label)]
        if len(rings) != 1:
            if len(rings) > 1:
                raise RuntimeError("Multiple ring layers found")
            else:
                raise RuntimeError("No ring layers found")
        ring = rings[0]

        for layer in layers:
            layer.hide()
        ring.show(recursive=True)

        courses = [layer for layer in layers if COURSE.search(layer.label)]

        self.tree = tree
        self.root = root
        self.ring = ring
        self.courses = courses

    def iter_maps(self):

        for course in self.courses:
            log.debug("Processing course %r", course.label)
            # Hide other courses
            for layer in self.courses:
                layer.hide()
            # Show this course and all sublayers (for now)
            course.show(recursive=True)

            # Find "Overlays" layer
            for overlays in course.sublayers:
                if overlays.label == 'Overlays':
                    break
            else:
                overlays = None
                log.debug("No overlays found in course %r", course.label)

            if overlays:
                for overlay in overlays.sublayers:
                    # Hide other overlays
                    for layer in overlays.sublayers:
                        layer.hide()
                    overlay.show()
                    labels = (course.label, overlay.label)
                    yield labels, self.tree
            else:
                labels = (course.label,)
                yield labels, self.tree

    __iter__ = iter_maps


class Inkscape(object):
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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
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


class ShellModeInkscape(Inkscape):
    """Run inkscape with specific arguments.

    This uses inkscape's --shell mode so that (for efficiency)
    multiple commands may be run with a single invocation of inkscape.

    """
    def __init__(self, executable='inkscape'):
        child = pexpect.spawn(executable, ['--shell'])
        self.executable = executable
        self.child = child
        self._wait_for_prompt()

    def _wait_for_prompt(self, prompt='\n>', expect_lines=1):
        """Wait for prompt."""
        self.child.expect_exact(prompt, searchwindowsize=len(prompt))
        self._log_output(expect_lines)

    def _log_output(self, expect_lines=0):
        before = self.child.before
        if before and before.count('\n') + 1 != expect_lines:
            log.warn("Unexpected output from shell-mode inkscape:\n%s",
                     before.replace('\r\n', '\n'))

    def __call__(self, args):
        self.child.sendline(' '.join(shellescape.quote(arg) for arg in args))
        self._wait_for_prompt()

    def close(self):
        child = self.child
        if child is not None:
            child.sendline('quit')
            child.expect('quit\r?\n')
            child.expect(pexpect.EOF)
            self._log_output()
            self.child = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class InkscapeOperations(object):
    def __init__(self, inkscape):
        self.inkscape = inkscape

    def tree_to_pdf(self, tree, filename):
        with NamedTemporaryFile(suffix='.svg') as svg:
            tree.write(svg, xml_declaration=True)
            svg.flush()
            self.inkscape([svg.name, '--export-pdf=%s' % filename])


@main.command()
@click.argument('svgfile', type=click.File('r'))
@click.option('-o', '--output-directory', type=click.Path(file_okay=False))
@click.option(
    '--shell-mode-inkscape/--no-shell-mode-inkscape', default=True,
    help="Run inkscape in shell-mode for efficiency.  Default is true.")
def pdfs(svgfile, output_directory, shell_mode_inkscape):
    """ Export PDFs from inkscape SVG coursemaps.

    """
    inkscape_class = (ShellModeInkscape if shell_mode_inkscape
                      else Inkscape)

    def friendly(path_comp):
        """ Replace shell-unfriendly characters with underscore.
        """
        return re.sub(r"[\000-\040/\\\177\s]", '_', path_comp,
                      flags=re.UNICODE)

    with inkscape_class() as inkscape:
        ops = InkscapeOperations(inkscape)
        for labels, tree in Drawing(svgfile):
            path = [friendly(label) for label in labels]
            filename = os.path.join(output_directory, *path) + '.pdf'
            dirpath = os.path.dirname(filename)
            if dirpath and not os.path.isdir(dirpath):
                log.debug("creating directory %r", dirpath)
                os.makedirs(dirpath)
            log.info("writing %r", filename)
            ops.tree_to_pdf(tree, filename)
