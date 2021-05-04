# -*- coding: utf-8 -*-
""" Code for rendering Inkscape SVG to PDFS
"""
from collections import namedtuple
from itertools import chain, zip_longest
import pathlib
import shutil

from pdfrw import PageMerge, PdfReader, PdfWriter


def concat_pdfs(in_fns, out_fn):
    """ Concatenate named PDF files to a single output file.
    """
    if len(in_fns) == 0:
        raise ValueError("No PDFs to concatenate")
    pathlib.Path(out_fn).parent.mkdir(parents=True, exist_ok=True)
    if len(in_fns) == 1:
        shutil.copy(in_fns[0], out_fn)
    else:
        writer = PdfWriter()
        for n, in_fn in enumerate(in_fns):
            reader = PdfReader(in_fn)
            if n == 0:
                info = reader.Info
            writer.addpages(reader.pages)
        # Copy metadata from first PDF
        writer.trailer.Info = info
        writer.write(out_fn)


def two_up(infiles, outfile, width=612, height=792):
    """ Generate 2-up version of PDF file(s).

    """
    pages = list(chain.from_iterable(PdfReader(fp).pages for fp in infiles))
    n_out = (len(pages) + 1) // 2

    boxes = [
        _Rectangle(0, height / 2, width, height / 2),
        _Rectangle(0, 0, width, height / 2),
        ]
    pathlib.Path(outfile.name).parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter(outfile)

    for pair in zip_longest(pages[:n_out], pages[n_out:]):
        merged = PageMerge()
        for n, (box, page) in enumerate(zip(boxes, pair)):
            if page is None:
                continue
            rotate = (90 + 180 * n) % 360
            merged.add(page, rotate=rotate)
            xobj = merged[n]

            xobj.scale(min(box.w / xobj.w, box.h / xobj.h))
            xobj.x = box.x + (box.w - xobj.w) / 2
            xobj.y = box.y + (box.h - xobj.h) / 2
        writer.addpage(merged.render())
    writer.write()


_Rectangle = namedtuple('_Rectangle', ['x', 'y', 'w', 'h'])
