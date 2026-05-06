"""DOCX → HTML via pandoc (one-time at upload); PDF handled in template via iframe."""
from __future__ import annotations

import logging
import shutil

import bleach

logger = logging.getLogger(__name__)

# Allowed tags for pandoc output (no inline styles per product spec).
_DOCX_BLEACH_TAGS = [
    "p",
    "b",
    "i",
    "strong",
    "em",
    "h1",
    "h2",
    "h3",
    "ul",
    "ol",
    "li",
    "a",
    "br",
    "div",
    "span",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
]
_DOCX_BLEACH_ATTRS = {
    "a": ["href", "title", "rel"],
    "th": ["colspan", "rowspan"],
    "td": ["colspan", "rowspan"],
}


def is_pandoc_available() -> bool:
    try:
        import pypandoc  # noqa: F401

        if shutil.which("pandoc") is None:
            logger.warning(
                "pandoc binary not found on PATH; install pandoc (e.g. apt install pandoc) "
                "for DOCX HTML conversion."
            )
            return False
        return True
    except ImportError:
        logger.warning(
            "pypandoc not installed; DOCX HTML conversion disabled. pip install pypandoc"
        )
        return False


def clean_docx_html(html: str) -> str:
    if not html or not html.strip():
        return ""
    return bleach.clean(
        html,
        tags=_DOCX_BLEACH_TAGS,
        attributes=_DOCX_BLEACH_ATTRS,
        strip=True,
    )


def convert_docx_to_html(file_path: str) -> str | None:
    try:
        import pypandoc

        raw = pypandoc.convert_file(file_path, "html", format="docx")
        return raw if raw else None
    except Exception as e:
        logger.warning("DOCX conversion failed for %s: %s", file_path, e)
        return None


def process_item_document(item) -> None:
    """
    Set body_pin_content_type / body_pin_content_html from body_pin_original.
    Call once after the file is saved to storage (e.g. right after create_item save).
    Does not run pandoc on every request.
    """
    from smart_blog.models import BodyPinContentType

    if not item.body_pin_original:
        return

    name = (item.body_pin_original.name or "").lower()
    if name.endswith(".pdf"):
        item.body_pin_content_type = BodyPinContentType.PDF
        item.body_pin_content_html = ""
    elif name.endswith(".docx"):
        item.body_pin_content_type = BodyPinContentType.DOCX
        item.body_pin_content_html = ""
        if not is_pandoc_available():
            item.save(
                update_fields=[
                    "body_pin_content_type",
                    "body_pin_content_html",
                    "excerpt_plain",
                ]
            )
            return
        try:
            path = item.body_pin_original.path
        except Exception as e:
            logger.warning("Could not resolve path for item %s document: %s", item.pk, e)
            item.save(
                update_fields=[
                    "body_pin_content_type",
                    "body_pin_content_html",
                    "excerpt_plain",
                ]
            )
            return
        raw_html = convert_docx_to_html(path)
        if raw_html:
            item.body_pin_content_html = clean_docx_html(raw_html)
        else:
            item.body_pin_content_html = ""
    else:
        item.body_pin_content_type = BodyPinContentType.TEXT
        item.body_pin_content_html = ""

    item.save(
        update_fields=["body_pin_content_type", "body_pin_content_html", "excerpt_plain"]
    )
