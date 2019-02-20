# -*- coding: utf-8 -*-
from __future__ import absolute_import

from collections import defaultdict
import itertools
import logging
import os
import random
from tempfile import mkstemp

import click
from lxml import etree
from pdfrw import PdfReader, PdfWriter
from six.moves import range as xrange

from .compat import ChainMap
from .coursemaps import (
    CourseMaps,
    TemplateRenderer,
    )
from .layerinfo import dwim_layer_info
from .pager import get_pager
from .parallel import ParallelUnorderedStarmap
from .templating import FileAdapter, render_template
# FIXME: move ensure_directory_exists
from .inkscape.runner import Inkscape, ensure_directory_exists

log = logging.getLogger('')

POSITIVE_INT = click.IntRange(1, None)


@click.group()
@click.option('-v', '--verbose', count=True)
@click.version_option()
def main(verbose):
    """ Utilities for creating Barn Hunt course maps.

    """
    log_level = logging.WARNING
    if verbose:                 # pragma: NO COVER
        log_level = logging.DEBUG if verbose > 1 else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="(%(levelname)1.1s) [%(threadName)s] %(message)s")


@main.command()
@click.argument('svgfiles', type=click.File('r'), nargs=-1, required=True)
@click.option('-o', '--output-directory', type=click.Path(file_okay=False),
              default='.')
@click.option('--processes', '-p', type=POSITIVE_INT, default=None)
@click.option(
    '--shell-mode-inkscape/--no-shell-mode-inkscape', default=True,
    help="Run inkscape in shell-mode for efficiency.  Default is true.")
def pdfs(svgfiles, output_directory, shell_mode_inkscape, processes=None):
    """ Export PDFs from inkscape SVG coursemaps.

    """
    # FIXME: make configurable
    basename_tmpl = '{{ overlays|map("safepath")|join("/") }}'

    def pdfs():
        for svgfile in svgfiles:
            tree = etree.parse(svgfile)

            layer_info = dwim_layer_info(tree)

            # Expand jinja templates in text within SVG file
            template_vars = {
                # FIXME: support random_seed and add command-line arg
                'random_seed': 0,
                'svgfile': FileAdapter(svgfile),
                }
            render_templates = TemplateRenderer(layer_info)
            tree = render_templates(tree, template_vars)

            coursemaps = CourseMaps(layer_info)
            for context, tree_ in coursemaps(tree):
                basename = None
                for overlay in reversed(context['overlays']):
                    basename = getattr(overlay, 'output_basename', None)
                    if basename:
                        break

                basename_ctx = ChainMap(context, template_vars)
                if basename is None:
                    basename = render_template(basename_tmpl, basename_ctx)

                pdf_filename = os.path.join(output_directory,
                                            basename + '.pdf')
                description = render_template('{{ overlays|join("/") }}',
                                              basename_ctx)
                yield tree_, pdf_filename, description

    inkscape = Inkscape(shell_mode=shell_mode_inkscape)

    temporary_files = []

    def render(order, render_info):
        tree, pdf_filename, description = render_info
        fd, fn = mkstemp(suffix='.pdf', prefix='barnhunt-')
        os.close(fd)
        temporary_files.append(fn)
        inkscape.export_pdf(tree, fn)
        return pdf_filename, order, fn, description

    if processes == 1:
        starmap = itertools.starmap
    else:
        starmap = ParallelUnorderedStarmap(processes)

    by_output = defaultdict(list)
    try:
        for pdf_filename, order, fn, desc in starmap(render,
                                                     enumerate(pdfs())):
            log.debug("Rendered %s to %r", desc, fn)
            by_output[pdf_filename].append((order, fn, desc))

        def fn_order(pdf_filename):
            return max(order for order, fn, desc in by_output[pdf_filename])
        for pdf_filename in sorted(by_output.keys(), key=fn_order):
            dirpath = os.path.dirname(pdf_filename)
            if dirpath:
                ensure_directory_exists(dirpath)
            writer = PdfWriter()
            page_count = 0
            for order, fn, desc in sorted(by_output[pdf_filename]):
                reader = PdfReader(fn)
                log.debug("Read %s from %r", desc, fn)
                assert len(reader.pages) == 1
                page_count += len(reader.pages)
                writer.addpages(reader.pages)
            # FIXME: add some metadata?
            writer.write(pdf_filename)
            log.info("Wrote %d page(s) to %r", page_count, pdf_filename)

    finally:
        map(os.unlink, temporary_files)


@main.command('rats')
@click.option(
    '-n', '--number-of-rows', type=POSITIVE_INT,
    metavar="<n>",
    help="Number of rows of rat numbers to generate.  (Default: 5).",
    default=5
    )
def rats_(number_of_rows):
    """ Generate random rat counts.

    Prints rows of five random numbers in the range [1, 5].
    """
    for row in range(number_of_rows):
        rats = tuple(random.randint(1, 5) for n in range(5))
        print("%d %d %d %d %d" % rats)


@main.command()
@click.option(
    '-n', '--number-of-rows', type=POSITIVE_INT, default=1000,
    metavar="<n>",
    help="Number of coordinates to generate. "
    "(Default: 1000 or the number of points in the grid, "
    "whichever is fewer).",
    )
@click.option(
    '-g', '--group-size', type=POSITIVE_INT,
    metavar="<n>",
    help="Group output in chunks of this size. "
    "Blank lines will be printed between groups. "
    "(Default: 10).",
    default=10
    )
@click.argument(
    'dimensions', nargs=2, type=POSITIVE_INT,
    metavar="[<x-max> <y-max>]",
    envvar="BARNHUNT_DIMENSIONS",
    default=(25, 30)
    )
def coords(dimensions, number_of_rows, group_size):
    """Generate random coordinates.

    Generates random coordinates.  The coordinates will range between (0, 0)
    and the (<x-max>, <y-max>).  Duplicates will be eliminated.

    The course dimensions may also be specified via
    BARNHUNT_DIMENSIONS environment variable.  E.g.

        export BARNHUNT_DIMENSIONS="25 30"

    """
    x_max, y_max = dimensions

    dim_x = dimensions[0] + 1
    dim_y = dimensions[1] + 1
    n_pts = dim_x * dim_y
    number_of_rows = min(number_of_rows, n_pts)

    def coord(pt):
        y, x = divmod(pt, dim_x)
        return x, y

    pager = get_pager(group_size)
    pager([
        "{0[0]:3d},{0[1]:3d}".format(coord(pt))
        for pt in random.sample(xrange(n_pts), number_of_rows)
        ])
