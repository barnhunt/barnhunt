# -*- coding: utf-8 -*-
from collections import OrderedDict
from itertools import (
    chain,
    starmap,
    )
import logging
import os
import pathlib
import random
from tempfile import mkstemp

import click

from .coursemaps import iter_coursemaps
from .pager import get_pager
from .parallel import ParallelUnorderedStarmap
from .pdfutil import concat_pdfs, two_up
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
    coursemaps = iter_coursemaps(svgfiles)

    pages = OrderedDict()
    descriptions = dict()

    def render_info(coursemap):
        basename = coursemap['basename']
        pdf_fn = os.path.join(output_directory, basename + '.pdf')
        fd, temp_fn = mkstemp(prefix='barnhunt-', suffix='.pdf')
        pages.setdefault(pdf_fn, []).append(temp_fn)
        os.close(fd)
        descriptions[temp_fn] = coursemap.get('description')
        return coursemap['tree'], temp_fn

    inkscape = Inkscape(shell_mode=shell_mode_inkscape)

    if processes == 1:
        starmap_ = starmap
    else:
        starmap_ = ParallelUnorderedStarmap(processes)

    try:
        for fn in starmap_(inkscape.export_pdf, map(render_info, coursemaps)):
            log.info("Rendered %s", descriptions.get(fn, fn))

        for output_fn, temp_fns in pages.items():
            if log.isEnabledFor(logging.INFO):
                for fn in temp_fns:
                    log.info("Reading %s", descriptions.get(fn, fn))

            concat_pdfs(temp_fns, output_fn)

            n_pages = len(temp_fns)
            log.warning("Wrote %d page%s to %r",
                        n_pages, 's' if n_pages != 1 else '', output_fn)
    finally:
        for temp_fn in chain.from_iterable(pages.values()):
            os.unlink(temp_fn)


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
        for pt in random.sample(range(n_pts), number_of_rows)
        ])


def default_2up_output_file():
    """Compute default output filename.
    """
    ctx = click.get_current_context()
    input_paths = set(pathlib.Path(infp.name)
                      for infp in ctx.params.get('pdffiles', ()))
    if len(input_paths) != 1:
        raise click.UsageError(
            "Can not deduce default output filename when multiple input "
            "files are specified.",
            ctx=ctx)
    input_path = input_paths.pop()
    output_path = input_path.with_name(
        input_path.stem + "-2up" + input_path.suffix)
    click.echo("Writing output to {0!s}".format(output_path))
    return output_path


@main.command(name="2up")
@click.argument('pdffiles', type=click.File('rb'), nargs=-1, required=True)
@click.option('-o', '--output-file', type=click.File('wb', atomic=True),
              default=default_2up_output_file,
              help="Output file name. "
              "(Default input filename with '-2up' appended to stem.)")
def pdf_2up(pdffiles, output_file):
    """Format PDF(s) for 2-up printing.

    Pages printed "pre-shuffled".  The first half of the input pages
    will be printed on the top half of the output pages, and the
    second half on the lower part of the output pages.  This way, the
    resulting stack out output can be cut in half, and the pages will
    be in proper order without having to shuffle them.

    """
    two_up(pdffiles, output_file)
