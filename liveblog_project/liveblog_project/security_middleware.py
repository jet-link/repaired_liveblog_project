"""Security headers (CSP, Referrer-Policy, Permissions-Policy) and admin audit logging."""
from __future__ import annotations

import logging
import os
from typing import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse

security_admin_logger = logging.getLogger('security.admin')


def _default_csp() -> str:
    """Policy aligned with templates/base.html (inline scripts, CDNs)."""
    return (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.ckeditor.com https://cdn.jsdelivr.net "
        "https://cdn.plyr.io https://challenges.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com "
        "https://cdn.plyr.io; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; "
        "img-src 'self' data: https: blob:; "
        "media-src 'self' blob: https://cdn.plyr.io https://*.cdn.example.com; "
        "connect-src 'self' https://cdn.ckeditor.com https://cdn.jsdelivr.net "
        "https://cdn.plyr.io https://challenges.cloudflare.com; "
        "worker-src 'self' blob: https://cdn.jsdelivr.net; "
        "frame-src 'self' https://cdn.ckeditor.com blob: https://challenges.cloudflare.com; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "upgrade-insecure-requests"
    )


def _csp_without_upgrade_for_report_only(csp: str) -> str:
    """
    Browsers ignore `upgrade-insecure-requests` in Content-Security-Policy-Report-Only
    and log a console warning. Strip it for report-only delivery.
    """
    if not csp or 'upgrade-insecure-requests' not in csp:
        return csp
    parts = [
        p.strip()
        for p in csp.split(';')
        if p.strip() and p.strip().lower() != 'upgrade-insecure-requests'
    ]
    return '; '.join(parts)


class SecurityHeadersMiddleware:
    """Add CSP (optional report-only), Referrer-Policy, Permissions-Policy."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response: HttpResponse = self.get_response(request)

        if not getattr(settings, 'SECURITY_HEADERS_ENABLED', True):
            return response

        csp = os.environ.get('DJANGO_SECURITY_CSP', '').strip() or getattr(
            settings, 'SECURITY_CSP_DEFAULT', _default_csp()
        )
        ro_env = os.environ.get('DJANGO_SECURITY_CSP_REPORT_ONLY', '').strip().lower()
        if ro_env in ('1', 'true', 'yes'):
            report_only = True
        elif ro_env in ('0', 'false', 'no'):
            report_only = False
        else:
            # Default: relaxed in DEBUG (report-only), enforced when DEBUG is False
            report_only = bool(getattr(settings, 'DEBUG', False))

        if csp:
            if report_only:
                response.headers['Content-Security-Policy-Report-Only'] = (
                    _csp_without_upgrade_for_report_only(csp)
                )
            else:
                response.headers['Content-Security-Policy'] = csp

        response.headers.setdefault(
            'Referrer-Policy',
            getattr(settings, 'SECURITY_REFERRER_POLICY', 'strict-origin-when-cross-origin'),
        )
        response.headers.setdefault(
            'Permissions-Policy',
            getattr(
                settings,
                'SECURITY_PERMISSIONS_POLICY',
                'accelerometer=(), camera=(), geolocation=(), gyroscope=(), microphone=(), '
                'payment=(), usb=()',
            ),
        )
        return response


class AdminAuditMiddleware:
    """Log staff POST/DELETE to /admin/ for accountability."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        try:
            if getattr(settings, 'DEBUG', False):
                return response
            if not request.path.startswith('/admin/'):
                return response
            if not request.user.is_authenticated or not request.user.is_staff:
                return response
            if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
                return response
            security_admin_logger.info(
                'staff_request user_id=%s username=%s method=%s path=%s status=%s',
                request.user.pk,
                request.user.username,
                request.method,
                request.path,
                response.status_code,
            )
        except Exception:
            pass
        return response
