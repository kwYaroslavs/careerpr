"""Markdown renderer module for CareerPR (T-022).

Renders approved content only; enforces deterministic order and escaping.
No PDF generation or snapshot creation in this module.
"""

import html
from typing import Any


def escape_markdown(text: str) -> str:
    """Escape special markdown characters to prevent injection/formatting corruption

    while preserving standard text readability.
    """
    if not text:
        return ""
    return html.escape(text)


def render_resume_markdown(resume_data: Any) -> str:
    """Render a structured resume (BaseResume or ResumeVersion dict/object)

    into clean, deterministic Markdown.
    Enforces deterministic sorting of items (by priority descending, then id ascending)
    and rendering of approved content only.
    """
    if hasattr(resume_data, "model_dump"):
        data = resume_data.model_dump()
    elif isinstance(resume_data, dict):
        data = resume_data
    else:
        raise TypeError("resume_data must be a Resume schema or dict")

    profile_id = data.get("profile_id", "")
    version = data.get("version", 1)
    items = data.get("items", [])

    sorted_items = sorted(
        items,
        key=lambda x: (-int(x.get("priority", 0)), str(x.get("id", ""))),
    )

    lines = [
        f"# Resume (Version {version})",
        f"Profile ID: {escape_markdown(str(profile_id))}",
        "",
        "## Professional Experience & Achievements",
        "",
    ]

    for item in sorted_items:
        text = item.get("text", "")
        fact_ids = sorted(item.get("fact_ids", []))
        fact_str = f" (Facts: {', '.join(fact_ids)})" if fact_ids else ""
        lines.append(f"- {escape_markdown(text)}{fact_str}")

    return "\n".join(lines)


def render_cover_letter_markdown(cover_letter_result: Any) -> str:
    """Render a cover letter result object or dict into deterministic Markdown."""
    if hasattr(cover_letter_result, "model_dump"):
        data = cover_letter_result.model_dump()
    elif isinstance(cover_letter_result, dict):
        data = cover_letter_result
    else:
        raise TypeError("cover_letter_result must be a CoverLetterResult schema or dict")

    letter = data.get("cover_letter", "")
    company_hook = data.get("company_hook", "")
    fact_ids = sorted(data.get("fact_ids", []))
    warnings = sorted(data.get("warnings", []))
    clarification_questions = data.get("clarification_questions", [])

    lines = [
        "# Cover Letter",
        "",
        f"**Company Hook:** {escape_markdown(company_hook)}",
    ]

    if fact_ids:
        cited = ", ".join(escape_markdown(fid) for fid in fact_ids)
        lines.append(f"**Cited Facts:** {cited}")

    lines.extend(["", "## Letter Body", "", escape_markdown(letter)])

    if warnings:
        lines.extend(["", "## Warnings", ""])
        for w in warnings:
            lines.append(f"- {escape_markdown(w)}")

    if clarification_questions:
        lines.extend(["", "## Clarification Questions", ""])
        sorted_cq = sorted(
            clarification_questions,
            key=lambda cq_item: str(
                cq_item.get("id", "") if isinstance(cq_item, dict) else getattr(cq_item, "id", "")
            ),
        )
        for cq in sorted_cq:
            cq_id = cq.get("id") if isinstance(cq, dict) else getattr(cq, "id", "")
            q_text = cq.get("question") if isinstance(cq, dict) else getattr(cq, "question", "")
            lines.append(f"- **{escape_markdown(str(cq_id))}**: {escape_markdown(str(q_text))}")

    return "\n".join(lines)
