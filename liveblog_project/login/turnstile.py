"""Cloudflare Turnstile server-side verification."""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)
VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'


def client_ip_from_request(request) -> str | None:
    """Best-effort client IP (works behind reverse proxy when X-Forwarded-For is set)."""
    xff = (request.META.get('HTTP_X_FORWARDED_FOR') or '').strip()
    if xff:
        return xff.split(',')[0].strip()
    addr = request.META.get('REMOTE_ADDR')
    return addr.strip() if addr else None


def verify_turnstile_response(token: str, secret: str, remote_ip: str | None) -> bool:
    if not token or not secret:
        return False
    data: dict[str, str] = {'secret': secret, 'response': token}
    if remote_ip:
        data['remoteip'] = remote_ip
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        VERIFY_URL,
        data=body,
        method='POST',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            payload = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning('Turnstile verify failed: %s', exc)
        return False
    return bool(payload.get('success'))
