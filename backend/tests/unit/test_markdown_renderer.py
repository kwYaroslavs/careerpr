"""Unit tests for the Markdown renderer (T-022)."""

import pytest

from app.domain.schemas import (
    BaseResume,
    ClarificationQuestion,
    ClarificationQuestionStatus,
    CoverLetterResult,
    ResumeItem,
)
from app.render.markdown import (
    escape_markdown,
    render_cover_letter_markdown,
    render_resume_markdown,
)


def test_escape_markdown() -> None:
    """Test HTML/Markdown special character escaping."""
    raw = "<script>alert('xss')</script>"
    expected = "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
    assert escape_markdown(raw) == expected
    assert escape_markdown("") == ""


def test_render_resume_markdown_normal() -> None:
    """Test deterministic resume markdown rendering with sorted items."""
    resume = BaseResume(
        id="br_1",
        profile_id="prof_1",
        version=1,
        items=[
            ResumeItem(id="item_2", text="Second item", priority=1, fact_ids=["f2"]),
            ResumeItem(id="item_1", text="First item", priority=5, fact_ids=["f1"]),
        ],
    )
    md = render_resume_markdown(resume)
    assert "# Resume (Version 1)" in md
    assert "Profile ID: prof_1" in md
    pos_1 = md.find("First item")
    pos_2 = md.find("Second item")
    assert pos_1 < pos_2
    assert "(Facts: f1)" in md


def test_render_resume_markdown_invalid_type() -> None:
    """Test passing invalid resume type raises TypeError."""
    with pytest.raises(TypeError, match="resume_data must be a Resume schema or dict"):
        render_resume_markdown("not_a_resume")


def test_render_cover_letter_markdown_normal() -> None:
    """Test cover letter markdown rendering."""
    clr = CoverLetterResult(
        cover_letter="Dear Team,\nI want to work with you.",
        fact_ids=["f1", "f2"],
        company_hook="innovative cloud platform",
        warnings=["Some warning"],
        clarification_questions=[
            ClarificationQuestion(
                id="cq_1",
                requirement_id="req_1",
                question="What is your experience?",
                status=ClarificationQuestionStatus.PENDING,
            )
        ],
    )
    md = render_cover_letter_markdown(clr)
    assert "# Cover Letter" in md
    assert "**Company Hook:** innovative cloud platform" in md
    assert "**Cited Facts:** f1, f2" in md
    assert "Dear Team," in md
    assert "Some warning" in md
    assert "cq_1" in md
    assert "What is your experience?" in md


def test_render_cover_letter_markdown_invalid_type() -> None:
    """Test passing invalid cover letter result raises TypeError."""
    err_msg = "cover_letter_result must be a CoverLetterResult schema or dict"
    with pytest.raises(TypeError, match=err_msg):
        render_cover_letter_markdown(123)
