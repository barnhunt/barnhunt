import os

from PyPDF2 import PdfFileReader
import pytest

from barnhunt.pdfutil import (
    concat_pdfs,
    two_up,
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
    assert pdf_title(output_fn) == 'Test File #1'


def test_concat_pdfs_one_pdf(tmpdir, pdf1):
    output_fn = str(tmpdir.join('single.pdf'))
    concat_pdfs([pdf1], output_fn)
    assert page_count(output_fn) == 1
    assert pdf_title(output_fn) == 'Test File #1'


def test_concat_pdfs_no_pdfs(tmpdir):
    output_fn = str(tmpdir.join('empty.pdf'))
    with pytest.raises(ValueError):
        concat_pdfs([], output_fn)


def test_two_up_two_pages(tmpdir, pdf1, pdf2):
    out_path = tmpdir.join('output.pdf')
    in_files = [open(pdf1, 'rb'), open(pdf2, 'rb')]
    with out_path.open('wb') as out_file:
        two_up(in_files, out_file)
    assert page_count(str(out_path)) == 1


def test_two_up_three_pages(tmpdir, pdf1, pdf2):
    out_path = tmpdir.join('output.pdf')
    in_files = [open(pdf1, 'rb'), open(pdf1, 'rb'), open(pdf2, 'rb')]
    with out_path.open('wb') as out_file:
        two_up(in_files, out_file)
    assert page_count(str(out_path)) == 2


def page_count(pdf_fn):
    pdf = PdfFileReader(open(pdf_fn, 'rb'))
    return len(pdf.pages)


def pdf_title(pdf_fn):
    pdf = PdfFileReader(open(pdf_fn, 'rb'))
    return pdf.documentInfo.title
