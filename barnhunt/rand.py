from random import randint

import click

from .main import main

POSITIVE_INT = click.IntRange(1, None)


@main.command()
@click.option(
    '-n', '--number-of-rows', type=POSITIVE_INT,
    metavar="<n>",
    help="Number of rows of rat numbers to generate.  (Default: 5).",
    default=5)
def rats(number_of_rows):
    """ Generate random rat counts.

    Prints rows of five random numbers in the range [1, 5].
    """
    for row in xrange(number_of_rows):
        print " ".join(str(randint(1, 5)) for col in range(5))


@main.command()
@click.option(
    '-n', '--number-of-rows', type=POSITIVE_INT,
    metavar="<n>",
    help="Number of coordinates to generate.  (Default: 10).",
    default=10)
@click.argument(
    'dimensions', nargs=2, type=POSITIVE_INT,
    metavar="[<x-max> <y-max>]",
    envvar="BARNHUNT_DIMENSIONS",
    default=(25, 30))
def coords(dimensions, number_of_rows):
    """Generate random coordinates.

    Generates random coordinates.  The coordinates will range between (0, 0)
    and the (<x-max>, <y-max>).

    The course dimensions may also be specified via
    BARNHUNT_DIMENSIONS environment variable.  E.g.

        export BARNHUNT_DIMENSIONS="25 30"

    """
    x_max, y_max = dimensions

    for _ in xrange(number_of_rows):
        print "%3d,%3d" % (randint(0, x_max), randint(0, y_max))
