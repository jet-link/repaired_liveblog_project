"""Mindset body sanitisation.

Reuses smart_blog.comment_html.sanitize_and_linkify_comment_html for URL/HTML
hardening and adds a hashtag pass that turns ``#word`` (outside <a> tags) into
``<a class="mindset-hashtag" href="/mindset/tag/<slug>/">#word</a>``.
"""
from __future__ import annotations

import html as html_module
import re
from typing import Iterable
from urllib.parse import parse_qs, urlparse

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


# Links to mindset tag pages that were saved from CKEditor (or got ``primary_`` from
# the comment linkify pass) must use ``mindset-hashtag`` so feed colours stay uniform.
_MINDSET_TAG_ANCHOR_RE = re.compile(
    r'<a\b[^>]*?\shref\s*=\s*(["\'])(?P<url>[^"\']*?/mindset/tag/[^"\']*)\1[^>]*>(?P<text>.*?)</a>',
    re.I | re.DOTALL,
)


def _normalize_mindset_hashtag_anchors(html: str) -> str:
    if not html or '/mindset/tag/' not in html:
        return html

    def fix(m: re.Match[str]) -> str:
        text = m.group('text')
        plain = re.sub(r'<[^>]+>', '', text).strip()
        if not plain.startswith('#'):
            return m.group(0)
        url = html_module.unescape(m.group('url'))
        return f'<a class="mindset-hashtag" href="{escape(url)}">{text}</a>'

    return _MINDSET_TAG_ANCHOR_RE.sub(fix, html)


_YT_ID_RE = re.compile(r'^[A-Za-z0-9_-]{11}$')

# Matches a single anchor <a ... href="URL" ...>...</a>. URL is a quoted attr value.
_ANCHOR_WITH_HREF_RE = re.compile(
    r'<a\b[^>]*?\shref\s*=\s*(["\'])(?P<url>[^"\']+)\1[^>]*>(?P<text>.*?)</a>',
    re.I | re.DOTALL,
)


def _extract_youtube_id(url: str) -> str | None:
    """Return the 11-char YouTube video id, or None for non-YouTube URLs.

    Handles youtu.be/<id>, youtube.com/watch?v=<id>, /embed/<id>, /shorts/<id>,
    and the m./www. subdomains.
    """
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    host = (parsed.hostname or '').lower()
    if host.startswith('www.'):
        host = host[4:]
    if host.startswith('m.'):
        host = host[2:]

    vid: str | None = None
    if host == 'youtu.be':
        vid = parsed.path.lstrip('/').split('/', 1)[0]
    elif host == 'youtube.com' or host.endswith('.youtube.com'):
        path = parsed.path
        if path == '/watch':
            vals = parse_qs(parsed.query).get('v') or []
            vid = vals[0] if vals else None
        elif path.startswith(('/embed/', '/shorts/', '/v/', '/live/')):
            parts = path.split('/', 3)
            vid = parts[2] if len(parts) >= 3 else None
    if vid and _YT_ID_RE.match(vid):
        return vid
    return None


def _embed_youtube_anchors(html: str) -> str:
    """Replace anchors that point to YouTube with a clickable poster preview.

    We deliberately avoid <iframe>: many videos have embedding disabled by the
    uploader and would render as "Video unavailable" inside the iframe. A
    poster + Play overlay always works (the thumbnail is publicly accessible)
    and the user can open the video on YouTube with a single click.

    Sanitisation has already removed any user-supplied <iframe>; the markup we
    inject is synthesised from a regex-validated video id, so there's no XSS
    surface.
    """
    if not html or 'youtu' not in html.lower():
        return html

    def replace(m: re.Match[str]) -> str:
        href = html_module.unescape(m.group('url'))
        vid = _extract_youtube_id(href)
        if not vid:
            return m.group(0)
        safe_vid = escape(vid)
        watch_url = f'https://www.youtube.com/watch?v={safe_vid}'
        thumb_url = f'https://i.ytimg.com/vi/{safe_vid}/hqdefault.jpg'
        return (
            f'<a class="mindset-embed mindset-embed--youtube" '
            f'href="{watch_url}" target="_blank" rel="noopener noreferrer" '
            f'aria-label="Watch on YouTube">'
            f'<img class="mindset-embed__poster" src="{thumb_url}" '
            f'alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer">'
            '<span class="mindset-embed__play" aria-hidden="true">'
            '<svg viewBox="0 0 68 48" width="68" height="48" focusable="false">'
            '<path class="mindset-embed__play-bg" d="M66.52 7.74c-.78-2.93-2.49-5.41-5.42-6.19C55.79.13 34 0 34 0S12.21.13 6.9 1.55C3.97 2.33 2.27 4.81 1.48 7.74 0 13.05 0 24 0 24s0 10.95 1.48 16.26c.78 2.93 2.49 5.41 5.42 6.19C12.21 47.87 34 48 34 48s21.79-.13 27.1-1.55c2.93-.78 4.64-3.26 5.42-6.19C68 34.95 68 24 68 24s0-10.95-1.48-16.26z"/>'
            '<path d="M45 24 27 14v20" fill="#fff"/>'
            '</svg>'
            '</span>'
            '</a>'
        )

    return _ANCHOR_WITH_HREF_RE.sub(replace, html)


def render_mindset_body(raw: str) -> str:
    """Sanitise + linkify URLs + linkify hashtags + embed YouTube. Safe HTML."""
    html = sanitize_and_linkify_comment_html(raw or '')
    html = _linkify_hashtags(html)
    html = _normalize_mindset_hashtag_anchors(html)
    html = _embed_youtube_anchors(html)
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
