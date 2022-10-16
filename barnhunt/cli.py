from __future__ import annotations

import logging
import os
import random
import sys
from collections import defaultdict
from contextlib import ExitStack
from functools import partial
from itertools import count
from multiprocessing.pool import ThreadPool
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from typing import BinaryIO
from typing import Callable
from typing import Iterable
from typing import Sequence
from typing import TypeVar

import click
from atomicwrites import atomic_write

from .coursemaps import Coursemap
from .coursemaps import iter_coursemaps
from .inkscape.runner import inkscape_runner
from .inkscape.utils import get_user_data_directory
from .installer import DEFAULT_REQUIREMENTS
from .installer import InkexRequirement
from .installer import Installer
from .pager import get_pager
from .pdfutil import concat_pdfs
from .pdfutil import two_up

_T = TypeVar("_T")
_U = TypeVar("_U")

log = logging.getLogger("")

POSITIVE_INT = click.IntRange(1, None)


@click.group()
@click.option("-v", "--verbose", count=True)
@click.version_option()
def main(verbose: int) -> None:
    """Utilities for creating Barn Hunt course maps."""
    log_level = logging.WARNING
    if verbose:  # pragma: NO COVER
        log_level = logging.DEBUG if verbose > 1 else logging.INFO
    logging.basicConfig(
        level=log_level, format="(%(levelname)1.1s) [%(threadName)s] %(message)s"
    )


@main.command()
@click.argument(
    "svgfiles",
    type=click.Path(exists=True, dir_okay=False, writable=True),
    nargs=-1,
    required=True,
)
@click.option(
    "--force-reseed/--no-force-reseed",
    "-f",
    help="Force reseeding, even if a seed has been previously set.",
)
def random_seed(svgfiles: Iterable[str], force_reseed: bool) -> None:
    """Set random-seem for SVG file.

    This command sets a random random seed in the named SVG files.
    The random seed is used, e.g., when generating random rat numbers.
    Having the seed specified in the source SVG file ensures that the
    random rat numbers are reproduceable.

    By default, this will only set a random seed if one has not
    already been set.  Use the --force-reseed to override this
    behavior.
    """
    from lxml import etree

    from barnhunt.inkscape import svg

    for svgpath in svgfiles:
        tree = etree.parse(svgpath)
        if not force_reseed:
            if svg.get_random_seed(tree) is not None:
                log.info("%s: already has random-seed set, skipping", svgpath)
                continue
        random_seed = random.randrange(2**128)
        log.debug("%s: setting random seed to %d", svgpath, random_seed)
        svg.set_random_seed(tree, random_seed)
        with atomic_write(svgpath, mode="wb", overwrite=True) as f:
            tree.write(f)


def default_inkscape_command() -> str:
    # This is what inkex.command does to find Inkscape (after first
    # checking $INKSCAPE_COMMAND).
    #
    # https://gitlab.com/inkscape/extensions/-/blob/cb74374e46894030775cf947e97ca341b6ed85d8/inkex/command.py#L45
    if sys.platform == "win32":
        # prefer inkscape.exe over inkscape.com which spawns a command window
        return "inkscape.exe"
    return "inkscape"


def inkscape_command_option(**kwargs: Any) -> Callable[..., Any]:
    return click.option(
        "--inkscape-command",
        "--inkscape",
        metavar="COMMAND",
        envvar="INKSCAPE_COMMAND",  # NB: this is what inkex uses
        default=default_inkscape_command,
        help=f"""
        Name of (or path to) inkscape executable to use for exporting PDFs.
        (Equivalently, you may set the $INKSCAPE_COMMAND environment variable.)
        The default is {default_inkscape_command()!r}.
        """,
        **kwargs,
    )


def default_shell_mode() -> bool:
    """Whether to use Inkscape's shell-mode by default."""
    if sys.platform == "darwin":
        return False  # ShellModeRunner current borked
    return True


@main.command()
@click.argument("svgfiles", type=click.File("rb"), nargs=-1, required=True)
@click.option(
    "--output-directory",
    "-o",
    type=click.Path(file_okay=False),
    default="pdfs",
    help="""
    Directory into which to write output PDF files.
    The default is './pdfs'.
    """,
)
@click.option(
    "--processes",
    "-p",
    metavar="N",
    type=POSITIVE_INT,
    default=os.cpu_count,
    help="""
    Number of inkscape processes to run in parallel.
    Set to one to disable parallel processing.
    The default is {os.cpu_count()} (the number of CPUs detected on this platform).
    """,
)
@inkscape_command_option()
@click.option(
    "--shell-mode-inkscape/--no-shell-mode-inkscape",
    "shell_mode",
    default=default_shell_mode,
    help="""
    Enable/disable running inkscape in shell-mode for efficiency.
    The default is enabled (except on macOS, where shell-mode currently
    seems to be broken).
    """,
)
def pdfs(
    svgfiles: Iterable[BinaryIO],
    output_directory: str,
    shell_mode: bool,
    inkscape_command: str,
    processes: int,
) -> None:
    """Export PDFs from inkscape SVG coursemaps."""
    counter = count(1)

    with ExitStack() as stack:
        tmpdir = stack.enter_context(TemporaryDirectory())
        inkscape = stack.enter_context(
            inkscape_runner(shell_mode=shell_mode, executable=inkscape_command)
        )

        def write_pdf(coursemap: Coursemap) -> tuple[Coursemap, str]:
            """Write coursemap to SVG, render to PDF in tmpdir"""
            n = next(counter)
            svg_fn = os.path.join(tmpdir, f"in{n}.svg")
            out_fn = os.path.join(tmpdir, f"out{n}.pdf")
            with open(svg_fn, "wb") as fp:
                coursemap.tree.write(fp)

            inkscape.export_pdf(svg_fn, out_fn)
            os.unlink(svg_fn)
            return coursemap, out_fn

        if processes == 1:
            map_: Callable[[Callable[[_T], _U], Iterable[_T]], Iterable[_U]] = map
        else:
            pool = stack.enter_context(ThreadPool(processes))
            map_ = pool.imap_unordered

        pages = defaultdict(list)
        for coursemap, temp_fn in map_(write_pdf, iter_coursemaps(svgfiles)):
            log.info("Rendered %s", coursemap.description)
            output_fn = os.path.join(output_directory, f"{coursemap.basename}.pdf")
            pages[output_fn].append((coursemap, temp_fn))

        for output_fn, render_info in pages.items():
            coursemaps, temp_fns = zip(*sorted(render_info))
            if log.isEnabledFor(logging.INFO):
                for coursemap in coursemaps:
                    log.info("Reading %s", coursemap.description)

            concat_pdfs(temp_fns, output_fn)
            log.warning("Wrote %d pages to %r", len(temp_fns), os.fspath(output_fn))


@main.command("rats")
@click.option(
    "-n",
    "--number-of-rows",
    type=POSITIVE_INT,
    metavar="<n>",
    help="Number of rows of rat numbers to generate.  (Default: 5).",
    default=5,
)
def rats_(number_of_rows: int) -> None:
    """Generate random rat counts.

    Prints rows of five random numbers in the range [1, 5].
    """
    for _ in range(number_of_rows):
        rats = tuple(random.randint(1, 5) for n in range(5))
        print("%d %d %d %d %d" % rats)


@main.command()
@click.option(
    "-n",
    "--number-of-rows",
    type=POSITIVE_INT,
    default=1000,
    metavar="<n>",
    help="Number of coordinates to generate. "
    "(Default: 1000 or the number of points in the grid, "
    "whichever is fewer).",
)
@click.option(
    "-g",
    "--group-size",
    type=POSITIVE_INT,
    metavar="<n>",
    help="Group output in chunks of this size. "
    "Blank lines will be printed between groups. "
    "(Default: 10).",
    default=10,
)
@click.argument(
    "dimensions",
    nargs=2,
    type=POSITIVE_INT,
    metavar="[<x-max> <y-max>]",
    envvar="BARNHUNT_DIMENSIONS",
    default=(25, 30),
)
def coords(dimensions: tuple[int, int], number_of_rows: int, group_size: int) -> None:
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

    def coord(pt: int) -> tuple[int, int]:
        y, x = divmod(pt, dim_x)
        return x, y

    pager = get_pager(group_size)
    pager(
        [
            "{0[0]:3d},{0[1]:3d}".format(coord(pt))
            for pt in random.sample(range(n_pts), number_of_rows)
        ]
    )


def default_2up_output_file() -> Path:
    """Compute default output filename."""
    ctx = click.get_current_context()
    input_paths = {Path(infp.name) for infp in ctx.params.get("pdffiles", ())}
    if len(input_paths) != 1:
        raise click.UsageError(
            "Can not deduce default output filename when multiple input "
            "files are specified.",
            ctx=ctx,
        )
    input_path = input_paths.pop()
    output_path = input_path.with_name(input_path.stem + "-2up" + input_path.suffix)
    click.echo(f"Writing output to {output_path!s}")
    return output_path


@main.command(name="2up")
@click.argument("pdffiles", type=click.File("rb"), nargs=-1, required=True)
@click.option(
    "-o",
    "--output-file",
    type=click.File("wb", atomic=True),
    default=default_2up_output_file,
    help="Output file name. " "(Default input filename with '-2up' appended to stem.)",
)
def pdf_2up(pdffiles: Iterable[BinaryIO], output_file: BinaryIO) -> None:
    """Format PDF(s) for 2-up printing.

    Pages printed "pre-shuffled".  The first half of the input pages
    will be printed on the top half of the output pages, and the
    second half on the lower part of the output pages.  This way, the
    resulting stack out output can be cut in half, and the pages will
    be in proper order without having to shuffle them.

    """
    two_up(pdffiles, output_file)


class InkexRequirementType(click.ParamType):
    name = "requirement"

    def __init__(self, allow_specifiers: bool = True):
        self.allow_specifiers = allow_specifiers

    def convert(
        self,
        value: str | InkexRequirement | None,
        param: click.Parameter | None,
        ctx: click.Context | None,
    ) -> InkexRequirement:
        if not isinstance(value, InkexRequirement):
            try:
                value = InkexRequirement(value or "")
            except ValueError as exc:
                self.fail(str(exc), param, ctx)
        if not self.allow_specifiers:
            if value.specifier:
                self.fail("specifiers not allowed in requirement")
            if value.url:
                self.fail("direct reference (URL) not allowed in requirement")
        return value


def set_default_target(
    ctx: click.Context, param: click.Parameter, inkscape_command: str
) -> str:
    if ctx.default_map is None:
        ctx.default_map = {}
    ctx.default_map["target"] = partial(get_user_data_directory, inkscape_command)
    return inkscape_command


@main.command()
@click.argument(
    "requirements",
    type=InkexRequirementType(),
    nargs=-1,
)
@click.option(
    "--upgrade/--no-upgrade", "-U", help="Upgrade to the newest available versions."
)
@click.option("--pre/--no-pre", help="Include pre-release and development versions.")
@click.option("-n", "--dry-run/--no-dry-run", help="Just show what would be done.")
@click.option(
    "--target",
    type=click.Path(exists=True, file_okay=False, writable=True, path_type=Path),
    help="""Where to install distributions.
    Defaults to inkscape’s user data directory (e.g. $XDG_CONFIG_HOME/inkscape).""",
)
@inkscape_command_option(
    is_eager=True,
    expose_value=False,
    callback=set_default_target,
)
@click.option(
    "--github-token",
    envvar="GITHUB_TOKEN",
    help=""" Token to use for authentication to GitHub’s REST API.
    This is not typically necessary, but if you are seeing rate-limit errors, using a
    GitHub “Personal Access Token” here (it does not need to be granted access to any
    scopes) greatly increases the rate-limit thresholds.  The token may also be passed
    in the $GITHUB_TOKEN environment variable. """,
)
def install(
    target: Path,
    upgrade: bool,
    pre: bool,
    dry_run: bool,
    github_token: str | None,
    requirements: Sequence[InkexRequirement],
) -> None:
    """Install extensions and/or symbol sets."""
    installer = Installer(target, dry_run=dry_run, github_token=github_token)
    for requirement in requirements or DEFAULT_REQUIREMENTS:
        installer.install(requirement, pre_flag=pre, upgrade=upgrade)


@main.command()
@click.argument(
    "requirements",
    type=InkexRequirementType(allow_specifiers=False),
    nargs=-1,
)
@click.option("-n", "--dry-run/--no-dry-run", help="Just show what would be done.")
@click.option(
    "--target",
    type=click.Path(exists=True, file_okay=False, writable=True, path_type=Path),
    help="""Where to install distributions.
    Defaults to inkscape’s user data directory (e.g. $XDG_CONFIG_HOME/inkscape).""",
)
@inkscape_command_option(
    is_eager=True,
    expose_value=False,
    callback=set_default_target,
)
def uninstall(
    target: Path,
    dry_run: bool,
    requirements: Sequence[InkexRequirement],
) -> None:
    """Uninstall extensions and/or symbol sets."""
    installer = Installer(target, dry_run=dry_run)
    for requirement in requirements or DEFAULT_REQUIREMENTS:
        installer.uninstall(requirement)
