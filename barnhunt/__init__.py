import logging
import os
from random import randint

import click
from lxml import etree

from .rats import random_rats
from .template import TemplateExpander
from .inkscape import Inkscape

log = logging.getLogger('')

POSITIVE_INT = click.IntRange(1, None)


@click.group()
@click.option('-v', '--verbose', count=True)
def main(verbose):
    """ Utilities for creating Barn Hunt course maps.

    """
    log_level = logging.WARNING
    if verbose:
        log_level = logging.DEBUG if verbose > 1 else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="(%(levelname)1.1s) %(message)s")


@main.command()
@click.argument('svgfile', type=click.File('r'))
@click.option('-o', '--output-directory', type=click.Path(file_okay=False))
@click.option(
    '--hash-seed', type=int,
    help="Seed used for hashing SVG layer ids in order to seed "
    "the RNG used to generate the random rat counts.  If not set, "
    "a seed will be computed from the input file name.")
@click.option(
    '--shell-mode-inkscape/--no-shell-mode-inkscape', default=True,
    help="Run inkscape in shell-mode for efficiency.  Default is true.")
def pdfs(svgfile, output_directory, hash_seed, shell_mode_inkscape):
    """ Export PDFs from inkscape SVG coursemaps.

    """
    if hash_seed is None:
        if svgfile.name:
            hash_seed = hash(os.path.realpath(svgfile.name))
    log.debug("hash_seed = %r", hash_seed)

    tree = etree.parse(svgfile)

    # Expand jinja templates in text within SVG file
    tree = TemplateExpander(hash_seed=hash_seed).expand(tree)

    with Inkscape(shell_mode=shell_mode_inkscape) as inkscape:
        inkscape.export_coursemaps(tree, output_directory)


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
        print(" ".join(map(str, random_rats())))


@main.command()
@click.option(
    '-n', '--number-of-rows', type=POSITIVE_INT,
    metavar="<n>",
    help="Number of coordinates to generate.  (Default: 10).",
    default=10
    )
@click.argument(
    'dimensions', nargs=2, type=POSITIVE_INT,
    metavar="[<x-max> <y-max>]",
    envvar="BARNHUNT_DIMENSIONS",
    default=(25, 30)
    )
def coords(dimensions, number_of_rows):
    """Generate random coordinates.

    Generates random coordinates.  The coordinates will range between (0, 0)
    and the (<x-max>, <y-max>).

    The course dimensions may also be specified via
    BARNHUNT_DIMENSIONS environment variable.  E.g.

        export BARNHUNT_DIMENSIONS="25 30"

    """
    x_max, y_max = dimensions

    for _ in range(number_of_rows):
        print("%3d,%3d" % (randint(0, x_max), randint(0, y_max)))


if __name__ == '__main__':
    main()
