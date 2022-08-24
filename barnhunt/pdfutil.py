""" Code for rendering Inkscape SVG to PDFS
"""
from __future__ import annotations

import re
import shutil
import time
from itertools import chain
from itertools import zip_longest
from pathlib import Path
from typing import BinaryIO
from typing import Iterable
from typing import Sequence

from pikepdf import ObjectStreamMode
from pikepdf import Pdf
from pikepdf import Rectangle

from ._compat import metadata


def concat_pdfs(in_fns: Sequence[str | Path], out_fn: str | Path) -> None:
    """Concatenate named PDF files to a single output file."""
    if len(in_fns) == 0:
        raise ValueError("No PDFs to concatenate")
    Path(out_fn).parent.mkdir(parents=True, exist_ok=True)
    if len(in_fns) == 1:
        shutil.copy(in_fns[0], out_fn)
    else:
        pdf = Pdf.new()
        for n, in_fn in enumerate(in_fns):
            src = Pdf.open(in_fn)
            if n == 0:
                update_metadata(pdf, src)
            pdf.pages.extend(src.pages)
        save_pdf(pdf, out_fn)


def two_up(
    infiles: Iterable[BinaryIO], outfile: BinaryIO, width: int = 612, height: int = 792
) -> None:
    """Generate 2-up version of PDF file(s)."""
    in_pdfs = [Pdf.open(fp) for fp in infiles]
    if len(in_pdfs) == 0:
        raise ValueError("No PDFs to concatenate")
    in_pages = list(chain.from_iterable(pdf.pages for pdf in in_pdfs))

    locations = [
        (Rectangle(0, height / 2, width, height), 270),
        (Rectangle(0, 0, width, height / 2), 90),
    ]
    n_out = (len(in_pages) + 1) // 2

    pdf = Pdf.new()
    update_metadata(pdf, in_pdfs[0])

    for pair in zip_longest(in_pages[:n_out], in_pages[n_out:]):
        out_page = pdf.add_blank_page(page_size=(width, height))
        for in_page, (box, rotation) in zip(pair, locations):
            if in_page is not None:
                in_page.rotate(rotation, relative=True)
                # XXX: should we pass push_stack=False to add_overlay?
                out_page.add_overlay(in_page, box)
    save_pdf(pdf, outfile)


def update_metadata(
    dst: Pdf, src: Pdf | None = None, now_: float | None = None
) -> None:
    """Update PDF metadata of ``dst``

    This sets the ``pdf:Producer`` to a string of the form "barnhunt <ourversion>",
    and ``xmp:MetadataDate`` to the current date/time.

    If ``src`` is given, additional metadata will be copied from that PDF.

    """
    with dst.open_metadata(set_pikepdf_as_editor=False) as meta:
        if src is not None:
            src_meta = src.open_metadata()
            if src_meta:
                meta.update(src_meta)
            else:
                meta.load_from_docinfo(src.docinfo)

        date = iso_date(now_)
        meta["pdf:Producer"] = f"barnhunt {metadata.version('barnhunt')}"
        meta["xmp:MetadataDate"] = date
        meta.setdefault("xmp:ModifyDate", date)


def iso_date(secs: float | None = None) -> str:
    """Format date and time to ISO-8601 format.

    Format is as described in https://www.w3.org/TR/NOTE-datetime

    Parameters:

    secs — Number of seconds since the epoch (e.g. as returned by
        ``time.time()``), or ``None`` for the current time.
    """
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(secs))
    # Add colon to zone offset
    return re.sub(r"(?<=[-+]\d\d)(?=\d\d\Z)", ":", now)


def save_pdf(pdf: Pdf, outfile: str | Path | BinaryIO) -> None:
    """Save pdf to file.

    This handles setting a bunch of pikepdf's (qpdf's) optimization options.
    (I'm not sure how much most of these help us.)
    """
    pdf.remove_unreferenced_resources()  # XXX: necessary, in our case?
    pdf.save(
        outfile,
        # This does reduce file size. Does it hurt us at all?
        object_stream_mode=ObjectStreamMode.generate,
        recompress_flate=True,  # Does this help us?
        linearize=True,  # Does this help us?
    )
