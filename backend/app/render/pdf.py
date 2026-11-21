"""PDF renderer module with fit-loop for CareerPR (T-023 / ADR-005).

Provides ATS-safe single-column PDF generation using PyMuPDF (pymupdf),
with page limit enforcement and deterministic low-priority item removal.
"""

from typing import Any

import pymupdf


def render_resume_pdf(resume_data: Any, max_pages: int = 1) -> bytes:
    """Render structured resume into an ATS-safe single-column PDF with fit-loop.

    Enforces max_pages limit by iteratively removing lowest priority items
    (and then by reverse item id order) if the generated PDF exceeds max_pages.
    """
    if hasattr(resume_data, "model_dump"):
        data = resume_data.model_dump()
    elif isinstance(resume_data, dict):
        data = resume_data
    else:
        raise TypeError("resume_data must be a Resume schema or dict")

    profile_id = data.get("profile_id", "")
    version = data.get("version", 1)
    items = list(data.get("items", []))

    def generate_pdf_bytes(current_items: list[dict[str, Any]]) -> bytes:
        doc = pymupdf.open()
        page = doc.new_page(width=595, height=842)  # A4 size in points

        y = 50
        margin_left = 50
        max_y = 842 - 50

        page.insert_text(
            (margin_left, y),
            f"Resume (Version {version})",
            fontsize=14,
            fontname="hebo",
        )
        y += 24
        page.insert_text(
            (margin_left, y),
            f"Profile ID: {profile_id}",
            fontsize=10,
            fontname="helv",
        )
        y += 30

        page.insert_text(
            (margin_left, y),
            "Professional Experience & Achievements",
            fontsize=12,
            fontname="hebo",
        )
        y += 20

        sorted_items = sorted(
            current_items,
            key=lambda x: (-int(x.get("priority", 0)), str(x.get("id", ""))),
        )

        for item in sorted_items:
            text = item.get("text", "")
            fact_ids = sorted(item.get("fact_ids", []))
            fact_str = f" (Facts: {', '.join(fact_ids)})" if fact_ids else ""
            line_text = f"- {text}{fact_str}"

            while True:
                rect = pymupdf.Rect(margin_left, y, 595 - 50, max_y)
                rc = page.insert_textbox(
                    rect,
                    line_text,
                    fontsize=9,
                    fontname="helv",
                )
                if rc >= 0:
                    used = rect.height - rc if rc >= 0 else rect.height
                    y += int(used) + 6
                    break
                else:
                    page = doc.new_page(width=595, height=842)
                    y = 50

        pdf_bytes_res = doc.tobytes()
        doc.close()
        return bytes(pdf_bytes_res)

    pdf_bytes = b""
    while True:
        pdf_bytes = generate_pdf_bytes(items)

        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(doc)
        doc.close()

        if page_count <= max_pages or not items:
            break

        sorted_for_removal = sorted(
            items,
            key=lambda x: (int(x.get("priority", 0)), str(x.get("id", ""))),
            reverse=False,
        )

        removed_item = sorted_for_removal[0]
        items.remove(removed_item)

    return pdf_bytes


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes for round-trip verification."""
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    text_runs = []
    page_count = len(doc)
    for i in range(page_count):
        page = doc[i]
        text_runs.append(page.get_text())
    doc.close()
    return "".join(text_runs)
