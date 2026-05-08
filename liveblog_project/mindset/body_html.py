"""Mindset body sanitisation.

Reuses smart_blog.comment_html.sanitize_and_linkify_comment_html for URL/HTML
hardening and adds a hashtag pass that turns ``#word`` (outside <a> tags) into
``<a class="mindset-hashtag" href="/mindset/tag/<slug>/">#word</a>``.
"""
from __future__ import annotations

import re
from typing import Iterable

from django.urls import reverse
from django.utils.html import escape
from django.utils.text import slugify

from smart_blog.comment_html import sanitize_and_linkify_comment_html

# Match #word that is NOT immediately preceded by a letter/digit (so we don't
# pick up "abc#tag"). The negative lookbehind also avoids touching CSS hex
# values like "#ff0" (those typically appear inside tags or attrs which are
# stripped anyway by bleach in sanitize_and_linkify_comment_html).
_HASHTAG_RE = re.compile(r'(?<![\w&])#([A-Za-zА-Яа-яЁё0-9_]{1,64})')

# Skip hashtag substitution inside an existing anchor.
_ANCHOR_BLOCK_RE = re.compile(r'<a\b[^>]*>.*?</a>', re.I | re.DOTALL)


def _linkify_hashtags(html: str) -> str:
    if not html or '#' not in html:
        return html

    def link_replace(m: re.Match[str]) -> str:
        word = m.group(1)
        slug = slugify(word) or word.lower()
        url = reverse('mindset:theme_list_by_tag', kwargs={'slug': slug})
        return f'<a class="mindset-hashtag" href="{escape(url)}">#{escape(word)}</a>'

    parts: list[str] = []
    last = 0
    for anchor in _ANCHOR_BLOCK_RE.finditer(html):
        if anchor.start() > last:
            parts.append(_HASHTAG_RE.sub(link_replace, html[last:anchor.start()]))
        parts.append(anchor.group(0))
        last = anchor.end()
    if last < len(html):
        parts.append(_HASHTAG_RE.sub(link_replace, html[last:]))
    return ''.join(parts)


def render_mindset_body(raw: str) -> str:
    """Sanitise + linkify URLs + linkify hashtags. Output is safe HTML."""
    html = sanitize_and_linkify_comment_html(raw or '')
    html = _linkify_hashtags(html)
    return html


def extract_hashtags(raw_text_or_html: str) -> list[str]:
    """Return unique lowercase hashtag names (no leading '#') in stable order.

    Accepts plain text or HTML; strips tags first to avoid false positives.
    """
    if not raw_text_or_html:
        return []
    plain = re.sub(r'<[^>]+>', ' ', raw_text_or_html)
    seen: set[str] = set()
    out: list[str] = []
    for m in _HASHTAG_RE.finditer(plain):
        word = m.group(1).lower()
        if word in seen:
            continue
        seen.add(word)
        out.append(word)
    return out


def html_to_plain_text(html: str) -> str:
    """Cheap HTML→text projection for previews/search."""
    if not html:
        return ''
    text = re.sub(r'<br\s*/?>', '\n', html, flags=re.I)
    text = re.sub(r'</p>\s*<p[^>]*>', '\n\n', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def normalise_hashtags(names: Iterable[str]) -> list[tuple[str, str]]:
    """For each tag name return (canonical_name, slug). Duplicates removed."""
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for raw in names:
        name = (raw or '').strip().lstrip('#').lower()
        if not name:
            continue
        slug = slugify(name) or name
        if slug in seen:
            continue
        seen.add(slug)
        out.append((name, slug))
    return out
