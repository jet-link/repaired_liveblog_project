"""Extract HTML-safe body fragments from PDF/DOCX uploads (create post)."""
from __future__ import annotations

import html
import io
import logging

logger = logging.getLogger(__name__)


def html_from_uploaded_document(uploaded_file) -> str:
    """Backward-compatible: HTML only."""
    h, _p = extract_html_and_plain_from_upload(uploaded_file)
    return h


def extract_html_and_plain_from_upload(uploaded_file) -> tuple[str, str]:
    """
    One read of the upload: (html_for_body_merge, plain_text_faithful_for_display).
    Plain text keeps line breaks / paragraph breaks closer to the source file.
    """
    data = uploaded_file.read()
    try:
        uploaded_file.seek(0)
    except Exception:
        pass
    if not data:
        return "", ""
    name = (getattr(uploaded_file, "name", "") or "").lower()
    try:
        if name.endswith(".docx"):
            return _docx_bytes_to_html_plain(data)
        if name.endswith(".pdf"):
            return _pdf_bytes_to_html_plain(data)
    except Exception:
        logger.exception("document_body_extract failed for %s", name)
    return "", ""


def _docx_bytes_to_html_plain(data: bytes) -> tuple[str, str]:
    from docx import Document

    doc = Document(io.BytesIO(data))
    plain_lines: list[str] = []
    for p in doc.paragraphs:
        plain_lines.append(p.text or "")
    plain = "\n".join(plain_lines).strip()
    if not plain:
        return "", ""
    # Single pre-wrap block matches on-page line breaks (avoids one-word <p> columns).
    html_out = f'<pre class="item-doc-faithful-block">{html.escape(plain)}</pre>'
    return html_out, plain


def _pdf_bytes_to_html_plain(data: bytes) -> tuple[str, str]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    page_texts: list[str] = []
    for page in reader.pages:
        t = page.extract_text() or ""
        page_texts.append(t.rstrip("\n"))
    plain = "\n\n".join(page_texts).replace("\r\n", "\n").strip()
    if not plain:
        return "", ""
    html_out = f'<pre class="item-doc-faithful-block">{html.escape(plain)}</pre>'
    return html_out, plain
