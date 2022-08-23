from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from PyPDF2 import PdfReader

from barnhunt.pdfutil import concat_pdfs
from barnhunt.pdfutil import two_up

if TYPE_CHECKING:
    from _typeshed import StrPath
else:
    StrPath = object


def test_concat_pdfs(tmp_path: Path, test1_pdf: Path, test2_pdf: Path) -> None:
    output_fn = tmp_path / "foo/output.pdf"
    concat_pdfs((test1_pdf, test2_pdf), output_fn)
    assert page_count(output_fn) == 2
    assert pdf_title(output_fn) == "Test File #1"


def test_concat_pdfs_one_pdf(tmp_path: Path, test1_pdf: Path) -> None:
    output_fn = tmp_path / "single.pdf"
    concat_pdfs([test1_pdf], output_fn)
    assert page_count(output_fn) == 1
    assert pdf_title(output_fn) == "Test File #1"


def test_concat_pdfs_no_pdfs(tmp_path: Path) -> None:
    output_fn = tmp_path / "empty.pdf"
    with pytest.raises(ValueError):
        concat_pdfs([], output_fn)


def test_two_up_two_pages(tmp_path: Path, test1_pdf: Path, test2_pdf: Path) -> None:
    out_path = tmp_path / "output.pdf"
    in_files = [test1_pdf.open("rb"), test2_pdf.open("rb")]
    with out_path.open("wb") as out_file:
        two_up(in_files, out_file)
    assert page_count(out_path) == 1


def test_two_up_three_pages(tmp_path: Path, test1_pdf: Path, test2_pdf: Path) -> None:
    out_path = tmp_path / "output.pdf"
    in_files = [
        test1_pdf.open("rb"),
        test1_pdf.open("rb"),
        test2_pdf.open("rb"),
    ]
    with out_path.open("wb") as out_file:
        two_up(in_files, out_file)
    assert page_count(out_path) == 2


def page_count(pdf_fn: StrPath) -> int:
    with open(pdf_fn, "rb") as fp:
        pdf = PdfReader(fp)
        return len(pdf.pages)


def pdf_title(pdf_fn: StrPath) -> str | None:
    with open(pdf_fn, "rb") as fp:
        pdf = PdfReader(fp)
        if pdf.metadata is not None:
            return pdf.metadata.title
    return None
