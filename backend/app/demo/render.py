"""Demo renderers: tailored resume / cover letter -> Markdown, HTML-based PDF (unicode-safe)."""

import io
from html import escape
from typing import Any

import pymupdf

_CSS = (
    "body{font-family:sans-serif;font-size:10pt;line-height:1.35}"
    "h1{font-size:20pt;margin:0}h2{font-size:11pt;margin:12pt 0 3pt 0;"
    "border-bottom:1px solid #999;text-transform:uppercase}"
    "p.c{color:#555;margin:2pt 0}li{margin-bottom:2pt}"
)
_SECTIONS = [("experience", "Experience"), ("skill", "Skills"), ("education", "Education")]


def _group(items: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    known = {k for k, _ in _SECTIONS}
    out = []
    for key, title in _SECTIONS:
        sel = [i for i in items if i["category"] == key]
        if sel:
            out.append((title, sel))
    rest = [i for i in items if i["category"] not in known]
    if rest:
        out.append(("Additional", rest))
    return out


def resume_markdown(
    name: str, contacts: dict[str, str], summary: str, items: list[dict[str, Any]]
) -> str:
    lines = [f"# {name}", " · ".join(contacts.values()), ""]
    if summary:
        lines += [summary, ""]
    for title, sel in _group(items):
        lines += [f"## {title}", ""] + [f"- {i['text']}" for i in sel] + [""]
    return "\n".join(lines).strip() + "\n"


def resume_html(
    name: str, contacts: dict[str, str], summary: str, items: list[dict[str, Any]]
) -> str:
    h = [f"<h1>{escape(name)}</h1>"]
    if contacts:
        h.append(f"<p class='c'>{escape(' · '.join(contacts.values()))}</p>")
    if summary:
        h.append(f"<p>{escape(summary)}</p>")
    for title, sel in _group(items):
        h.append(f"<h2>{title}</h2><ul>")
        h += [f"<li>{escape(i['text'])}</li>" for i in sel]
        h.append("</ul>")
    return "".join(h)


def letter_html(name: str, letter: str) -> str:
    paras = "".join(f"<p>{escape(p)}</p>" for p in letter.split("\n\n") if p.strip())
    return f"<h1>{escape(name)}</h1><h2>Cover letter</h2>{paras}"


def html_to_pdf(html: str, max_pages: int = 2) -> tuple[bytes, int]:
    """Render HTML to A4 PDF; shrinks font a bit if over max_pages. Returns (bytes, pages)."""
    pdf, pages = b"", 0
    for scale in (1.0, 0.92, 0.85, 0.78):
        css = _CSS + f"body{{font-size:{10 * scale:.1f}pt}}"
        buf = io.BytesIO()
        writer = pymupdf.DocumentWriter(buf)
        story = pymupdf.Story(html=html, user_css=css)
        page_rect = pymupdf.paper_rect("a4")
        more, pages = 1, 0
        while more:
            dev = writer.begin_page(page_rect)
            more, _ = story.place(page_rect + (48, 48, -48, -48))
            story.draw(dev)
            writer.end_page()
            pages += 1
        writer.close()
        pdf = buf.getvalue()
        if pages <= max_pages:
            break
    return pdf, pages
