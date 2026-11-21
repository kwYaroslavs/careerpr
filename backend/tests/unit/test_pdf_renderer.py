"""Unit tests for the PDF renderer and fit-loop (T-023 / ADR-005)."""

import pymupdf
import pytest

from app.domain.schemas import BaseResume, ResumeItem
from app.render.pdf import extract_pdf_text, render_resume_pdf


def test_render_resume_pdf_normal() -> None:
    """Test normal PDF rendering returns valid PDF bytes with extractable text."""
    resume = BaseResume(
        id="br_1",
        profile_id="prof_1",
        version=1,
        items=[
            ResumeItem(
                id="item_1",
                text="Software Engineer at Tech Corp",
                priority=5,
                fact_ids=["f1"],
            ),
        ],
    )
    pdf_bytes = render_resume_pdf(resume, max_pages=1)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0

    extracted = extract_pdf_text(pdf_bytes)
    assert "Resume (Version 1)" in extracted
    assert "Profile ID: prof_1" in extracted
    assert "Software Engineer at Tech Corp" in extracted
    assert "(Facts: f1)" in extracted


def test_render_resume_pdf_invalid_type() -> None:
    """Test passing invalid type raises TypeError."""
    with pytest.raises(TypeError, match="resume_data must be a Resume schema or dict"):
        render_resume_pdf("not_a_resume")


def test_render_resume_pdf_fit_loop() -> None:
    """Test fit-loop removes lowest priority items when exceeding max_pages."""
    long_items = [
        ResumeItem(
            id=f"item_{i:02d}",
            text=(
                f"Achievement description number {i} with a lot of verbose text repeating "
                "over and over to take up vertical space in the PDF document layout and ensure "
                "that multiple pages are filled if not pruned."
            ),
            priority=1,
            fact_ids=[f"f{i}"],
        )
        for i in range(1, 40)
    ]
    long_items.append(
        ResumeItem(
            id="item_vital",
            text="Critical Core Achievement",
            priority=10,
            fact_ids=["f_vital"],
        )
    )

    resume = BaseResume(
        id="br_overflow",
        profile_id="prof_overflow",
        version=1,
        items=long_items,
    )

    pdf_bytes = render_resume_pdf(resume, max_pages=1)
    extracted = extract_pdf_text(pdf_bytes)

    assert "Critical Core Achievement" in extracted
    # Verify low priority items were pruned to fit 1 page
    assert "Achievement description number 01" not in extracted


def test_render_resume_pdf_multiple_mid_priority_items_survive() -> None:
    """Assert that several mid-priority items survive when they genuinely fit on one page."""
    items = [
        ResumeItem(
            id=f"mid_{i}",
            text=f"Mid priority achievement item number {i} that fits comfortably.",
            priority=5,
            fact_ids=[f"f_mid_{i}"],
        )
        for i in range(1, 6)
    ]
    resume = BaseResume(
        id="br_mid",
        profile_id="prof_mid",
        version=1,
        items=items,
    )

    pdf_bytes = render_resume_pdf(resume, max_pages=1)
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    assert len(doc) == 1
    doc.close()

    extracted = extract_pdf_text(pdf_bytes)
    for i in range(1, 6):
        assert f"Mid priority achievement item number {i}" in extracted
