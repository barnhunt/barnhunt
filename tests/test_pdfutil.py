from __future__ import annotations

import re
import time
from contextlib import ExitStack
from itertools import cycle
from itertools import islice
from pathlib import Path
from typing import Sequence

import pikepdf
import pytest

from barnhunt.pdfutil import concat_pdfs
from barnhunt.pdfutil import iso_date
from barnhunt.pdfutil import two_up
from barnhunt.pdfutil import update_metadata


@pytest.fixture
def input_pdfs(test1_pdf: Path, test2_pdf: Path, n_pdfs: int) -> list[Path]:
    return list(islice(cycle((test1_pdf, test2_pdf)), n_pdfs))


@pytest.mark.parametrize("n_pdfs", [1, 2, 3])
def test_concat_pdfs(input_pdfs: Sequence[Path], n_pdfs: int, tmp_path: Path) -> None:
    output_fn = tmp_path / "foo/output.pdf"
    concat_pdfs(input_pdfs, output_fn)
    assert page_count(output_fn) == n_pdfs
    if n_pdfs > 1:
        assert xmp_title(output_fn) == "Test File #1"
    assert docinfo_title(output_fn) == "Test File #1"


def test_concat_pdfs_no_pdfs(tmp_path: Path) -> None:
    output_fn = tmp_path / "empty.pdf"
    with pytest.raises(ValueError):
        concat_pdfs([], output_fn)


@pytest.mark.parametrize("n_pdfs", [1, 2, 3])
def test_two_up(input_pdfs: Sequence[Path], n_pdfs: int, tmp_path: Path) -> None:
    out_path = tmp_path / "output.pdf"
    with ExitStack() as stack:
        in_files = [stack.enter_context(pdf.open("rb")) for pdf in input_pdfs]
        with out_path.open("wb") as out_file:
            two_up(in_files, out_file)
    assert page_count(out_path) == (n_pdfs + 1) // 2
    assert xmp_title(out_path) == "Test File #1"


def test_two_up_no_pages(tmp_path: Path) -> None:
    out_path = tmp_path / "empty.pdf"
    with pytest.raises(ValueError):
        with out_path.open("wb") as out_file:
            two_up([], out_file)


def test_update_metadata() -> None:
    now = time.time()
    pdf = pikepdf.Pdf.new()
    update_metadata(pdf, now_=now)
    meta = pdf.open_metadata()
    assert meta["pdf:Producer"].startswith("barnhunt ")
    assert meta["xmp:MetadataDate"] == iso_date(now)
    assert meta["xmp:ModifyDate"] == iso_date(now)


@pytest.fixture
def docinfo_test_pdf(tmp_path: Path) -> Path:
    """A test_pdf file with docinfo but no XMP metadata."""
    test_pdf = tmp_path / "docinfo-test.pdf"
    pdf = pikepdf.Pdf.new()
    pdf.docinfo.Author = "Joe"
    pdf.save(test_pdf)
    return test_pdf


@pytest.fixture
def xmp_meta_test_pdf(tmp_path: Path) -> Path:
    """A test_pdf file XMP metadata (and docinfo metadata which does not match)."""
    test_pdf = tmp_path / "docinfo-test.pdf"
    pdf = pikepdf.Pdf.new()
    with pdf.open_metadata() as meta:
        meta["dc:creator"] = ["Jane"]
    pdf.docinfo.Author = "Not Jane"
    pdf.save(test_pdf)
    return test_pdf


def test_update_metadata_from_docinfo(docinfo_test_pdf: Path) -> None:
    pdf = pikepdf.Pdf.new()
    update_metadata(pdf, pikepdf.Pdf.open(docinfo_test_pdf))
    assert pdf.docinfo.Author == "Joe"
    meta = pdf.open_metadata()
    assert meta["dc:creator"] == ["Joe"]


def test_update_metadata_from_xmp_meta(xmp_meta_test_pdf: Path) -> None:
    pdf = pikepdf.Pdf.new()
    update_metadata(pdf, pikepdf.Pdf.open(xmp_meta_test_pdf))
    assert pdf.docinfo.Author == "Jane"
    meta = pdf.open_metadata()
    assert meta["dc:creator"] == ["Jane"]


def test_iso_date() -> None:
    assert re.match(r"\d{4}(-\d\d){2}T\d\d(:\d\d){2}(\.\d+)?[-+]\d\d:\d\d", iso_date())


def page_count(pdf_fn: str | Path) -> int:
    return len(pikepdf.Pdf.open(pdf_fn).pages)


def xmp_title(pdf_fn: str | Path) -> str | None:
    return pikepdf.Pdf.open(pdf_fn).open_metadata().get("dc:title")


def docinfo_title(pdf_fn: str | Path) -> str | None:
    title = pikepdf.Pdf.open(pdf_fn).docinfo.get("/Title")
    if title is not None:
        return str(title)
    return None
