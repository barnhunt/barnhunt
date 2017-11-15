import logging
import os
from random import randint
try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap

import click
from lxml import etree

from .coursemaps import CourseMaps, render_templates
from .templating import FileAdapter, render_template
from .inkscape.runner import Inkscape

log = logging.getLogger('')

POSITIVE_INT = click.IntRange(1, None)


@click.group()
@click.option('-v', '--verbose', count=True)
def main(verbose):
    """ Utilities for creating Barn Hunt course maps.

    """
    log_level = logging.WARNING
    if verbose:                 # pragma: NO COVER
        log_level = logging.DEBUG if verbose > 1 else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="(%(levelname)1.1s) %(message)s")


@main.command()
@click.argument('svgfile', type=click.File('r'))
@click.option('-o', '--output-directory', type=click.Path(file_okay=False))
@click.option(
    '--shell-mode-inkscape/--no-shell-mode-inkscape', default=True,
    help="Run inkscape in shell-mode for efficiency.  Default is true.")
def pdfs(svgfile, output_directory, shell_mode_inkscape):
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
    render_templates(tree, template_vars)

    with Inkscape(shell_mode=shell_mode_inkscape) as inkscape:
        coursemaps = CourseMaps()
        for context, tree in coursemaps(tree):
            basename = render_template(basename_tmpl,
                                       ChainMap(context, template_vars))
            filename = os.path.join(output_directory, basename) + '.pdf'
            log.info("writing %r", filename)
            inkscape.export_pdf(tree, filename)


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
        print("%d %d %d %d %d" % tuple(randint(1, 5) for n in range(5)))


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
    main()                      # pragma: NO COVER
