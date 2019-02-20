import os

from PyPDF2 import PdfFileReader
import pytest

from barnhunt.pdfutil import (
    concat_pdfs,
    )


@pytest.fixture
def pdf1():
    here = os.path.dirname(__file__)
    return os.path.join(here, 'test1.pdf')


@pytest.fixture
def pdf2():
    here = os.path.dirname(__file__)
    return os.path.join(here, 'test2.pdf')


def test_concat_pdfs(tmpdir, pdf1, pdf2):
    output_fn = str(tmpdir.join('foo/output.pdf'))
    concat_pdfs([pdf1, pdf2], output_fn)
    assert page_count(output_fn) == 2


def test_concat_one_pdf(tmpdir, pdf1):
    output_fn = str(tmpdir.join('single.pdf'))
    concat_pdfs([pdf1], output_fn)
    assert page_count(output_fn) == 1


def page_count(pdf_fn):
    pdf = PdfFileReader(open(pdf_fn, 'rb'))
    return len(pdf.pages)
