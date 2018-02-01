# -*- coding: utf-8 -*-
from __future__ import absolute_import

import itertools
import logging
import os
import random

import click
from lxml import etree
from six.moves import range as xrange

from .compat import ChainMap
from .coursemaps import (
    CourseMaps,
    dwim_layer_info,
    render_templates,
    )
from .pager import get_pager
from .parallel import ParallelUnorderedStarmap
from .templating import FileAdapter, render_template
from .inkscape.runner import Inkscape

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
@click.argument('svgfile', type=click.File('r'))
@click.option('-o', '--output-directory', type=click.Path(file_okay=False),
              default='.')
@click.option('--processes', '-p', type=POSITIVE_INT, default=None)
@click.option(
    '--shell-mode-inkscape/--no-shell-mode-inkscape', default=True,
    help="Run inkscape in shell-mode for efficiency.  Default is true.")
def pdfs(svgfile, output_directory, shell_mode_inkscape, processes=None):
    """ Export PDFs from inkscape SVG coursemaps.

    """
    # FIXME: make configurable
    basename_tmpl = (
        '{{ course.label|safepath }}'
        '{% if overlay %}/{{ overlay.label|safepath }}{% endif %}'
        )

    tree = etree.parse(svgfile)

    # Expand jinja templates in text within SVG file
    template_vars = {
        'random_seed': 0,       # FIXME: support this and add command-line arg
        'svgfile': FileAdapter(svgfile),
        }
    tree = render_templates(tree, template_vars)

    def pdf_filename(context):
        basename = render_template(basename_tmpl,
                                   ChainMap(context, template_vars))
        return os.path.join(output_directory, basename) + '.pdf'

    inkscape = Inkscape(shell_mode=shell_mode_inkscape)

    layer_info = dwim_layer_info(tree)
    coursemaps = CourseMaps(layer_info)
    pdfs = ((tree_, pdf_filename(context))
            for context, tree_ in coursemaps(tree))

    if processes == 1:
        starmap = itertools.starmap
    else:
        starmap = ParallelUnorderedStarmap(processes)

    for fn in starmap(inkscape.export_pdf, pdfs):
        log.info("Wrote %r" % fn)


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
