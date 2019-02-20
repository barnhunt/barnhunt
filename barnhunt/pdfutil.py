# -*- coding: utf-8 -*-
""" Code for rendering Inkscape SVG to PDFS
"""
from __future__ import absolute_import

import os
import shutil

from pdfrw import PdfReader, PdfWriter

# FIXME: move ensure_directory_exists
from .inkscape.runner import ensure_directory_exists


def concat_pdfs(in_fns, out_fn):
    if len(in_fns) == 0:
        raise ValueError("No PDFs to concatenate")
    dirpath = os.path.dirname(out_fn)
    if dirpath:
        ensure_directory_exists(dirpath)
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
