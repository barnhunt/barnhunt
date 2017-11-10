import logging

import click

log = logging.getLogger('')


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
