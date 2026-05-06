"""Comment body: expand bare domains, sanitize, linkify (shared by CommentForm and templates)."""
from __future__ import annotations

import html as html_module
import re
import bleach
from django.utils.html import urlize

COMMENT_ALLOWED_TAGS = ['a', 'b', 'strong', 'i', 'em', 'u', 'br', 'p', 'div', 'span']
COMMENT_ALLOWED_ATTRS = {
    'a': ['href', 'title', 'target', 'rel', 'class'],
    'div': ['class'],
    'span': ['class'],
    'p': ['class'],
}

# host.pdf / setup.exe — не превращаем в ссылку без пути
_BLOCKED_LAST_LABEL = frozenset({
    'exe', 'dll', 'bat', 'cmd', 'msi', 'apk', 'deb', 'rpm',
    'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'ico', 'bmp', 'tif',
    'pdf', 'zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz',
    'txt', 'csv', 'log', 'md', 'rst',
    'json', 'xml', 'yml', 'yaml', 'toml', 'ini', 'env',
    'css', 'less', 'scss', 'js', 'mjs', 'cjs', 'map', 'ts', 'tsx', 'jsx', 'vue', 'coffee',
    'html', 'htm', 'shtml', 'wasm',
    'py', 'rb', 'go', 'java', 'c', 'h', 'cpp', 'cs', 'rs', 'swift', 'kt', 'php', 'pl', 'lua',
    'mp3', 'mp4', 'webm', 'mov', 'avi', 'mkv', 'opus', 'wav', 'flac',
    'woff', 'woff2', 'ttf', 'eot', 'otf',
    'sql', 'db', 'sqlite',
})

_BARE_URL_RE = re.compile(
    r'(?<!@)(?<![\w/])'
    r'(?P<tok>'
    r'(?:https?://[^\s<]+)'
    r'|(?:www\.[^\s<]+)'
    r'|(?:'
    r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+'
    r'[a-z]{2,}'
    r'(?::\d{1,5})?'
    r'(?:/[^\s<]*)?'
    r')'
    r')',
    re.I,
)


def expand_bare_domains(text: str) -> str:
    if not text:
        return ''

    def repl(m: re.Match[str]) -> str:
        tok = m.group('tok')
        if tok.startswith(('http://', 'https://')):
            return tok
        if '/' not in tok:
            host = tok.split(':')[0]
            labels = host.split('.')
            if len(labels) >= 2:
                last = labels[-1].rstrip('.,;:!?)').lower()
                if last in _BLOCKED_LAST_LABEL:
                    return tok
        if tok.startswith('www.'):
            return 'https://' + tok
        return 'https://' + tok

    return _BARE_URL_RE.sub(repl, text)


# urlize находит URL и внутри href="https://..." уже сохранённого <a> — ломает разметку (дубли, "> в тексте).
_ANCHOR_BLOCK_RE = re.compile(r'<a\b[^>]*>.*?</a>', re.I | re.DOTALL)


def _urlize_outside_anchors(html: str) -> str:
    if not html:
        return html
    parts: list[str] = []
    last = 0
    for m in _ANCHOR_BLOCK_RE.finditer(html):
        if m.start() > last:
            parts.append(
                urlize(
                    html[last:m.start()],
                    trim_url_limit=None,
                    nofollow=False,
                    autoescape=False,
                )
            )
        parts.append(m.group(0))
        last = m.end()
    if last < len(html):
        parts.append(
            urlize(
                html[last:],
                trim_url_limit=None,
                nofollow=False,
                autoescape=False,
            )
        )
    return ''.join(parts)


def _add_primary_class_if_missing(m: re.Match[str]) -> str:
    tag = m.group(0)
    if 'class=' in tag.lower():
        return tag
    return tag.replace('<a', '<a class="primary_"', 1)


def _inject_blank_target_external_opening_tags(html: str) -> str:
    """target=_blank только для внешних http(s); не трогаем #якоря, mention-link, mailto."""

    def patch(m: re.Match[str]) -> str:
        tag = m.group(0)
        low = tag.lower()
        if re.search(r'(?:^|[\s])target\s*=', low):
            return tag
        hm = re.search(r'href\s*=\s*(["\'])(.*?)\1', tag, re.I)
        if not hm:
            return tag
        href = html_module.unescape(hm.group(2).strip())
        if not re.match(r'https?://', href, re.I):
            return tag
        return tag.replace('<a', '<a target="_blank" rel="noopener noreferrer"', 1)

    return re.sub(r'<a\s[^>]*>', patch, html, flags=re.I)


def sanitize_and_linkify_comment_html(fragment: str) -> str:
    if not fragment:
        return ''
    fragment = fragment.replace('\r\n', '\n').replace('\r', '\n')

    # 1–2: санитизация; unescape чтобы &amp; в тексте не ломал разбор query в URL при linkify.
    # 3: urlize — распознаёт TLD вроде .news; bleach.linkify их режет.
    # 4: снова clean после вставки <a>.
    t = bleach.clean(fragment, tags=COMMENT_ALLOWED_TAGS, attributes=COMMENT_ALLOWED_ATTRS, strip=True)
    t = html_module.unescape(t)
    t = bleach.clean(t, tags=COMMENT_ALLOWED_TAGS, attributes=COMMENT_ALLOWED_ATTRS, strip=True)
    t = _urlize_outside_anchors(t)
    t = bleach.clean(t, tags=COMMENT_ALLOWED_TAGS, attributes=COMMENT_ALLOWED_ATTRS, strip=True)

    t = _inject_blank_target_external_opening_tags(t)
    t = re.sub(r'<a\s[^>]*>', _add_primary_class_if_missing, t, flags=re.I)
    t = re.sub(r'(<br\s*/?>\s*){3,}', '<br><br>', t, flags=re.I)
    t = re.sub(r'(<p>\s*<br\s*/?>\s*</p>\s*){3,}', '<br><br>', t, flags=re.I)
    t = re.sub(r'(<div>\s*<br\s*/?>\s*</div>\s*){3,}', '<br><br>', t, flags=re.I)
    return t


def comment_html_for_template(text: str) -> str:
    """Sanitize, linkify, newlines → br (caller wraps with mark_safe)."""
    return sanitize_and_linkify_comment_html(text or '').replace('\n', '<br>')
