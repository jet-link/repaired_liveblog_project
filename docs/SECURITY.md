# Security and deployment hardening

This document complements production settings in `liveblog_project/settings.py` and middleware in `liveblog_project/security_middleware.py`.

## Secrets and configuration (S1–S4)

- Never commit `.env`. Use [.env.example](/.env.example) as a template only.
- **DJANGO_SECRET_KEY**: use a long random value (e.g. `openssl rand -hex 64`). If you rotate it, **all existing sessions are invalidated** and any signed tokens/objects using the old key become invalid until reissued.
- **DJANGO_ALLOWED_HOSTS**: exact hostnames only (comma-separated), e.g. `example.com,www.example.com`.
- **DJANGO_CSRF_TRUSTED_ORIGINS**: full URLs with scheme, e.g. `https://example.com,https://www.example.com`.
- Production must run with **DJANGO_DEBUG=false**.

### Rotating SECRET_KEY

1. Schedule a low-traffic window.
2. Set new `DJANGO_SECRET_KEY` in the environment; restart application workers.
3. All users will need to sign in again (sessions use the secret).
4. Invalidate old download links or signed URLs if your codebase uses signing beyond Django defaults.

## HTTP security headers (H2–H5)

- **Content-Security-Policy**: built-in default in `SecurityHeadersMiddleware` (allows inline scripts used by the theme toggle in `base.html`, CKEditor, jsDelivr, Google Fonts). Override with **DJANGO_SECURITY_CSP** (full header value).
- **DJANGO_SECURITY_CSP_REPORT_ONLY**: `true` / `false`. When unset: **Report-Only in DEBUG**, **enforced when DEBUG is False**.
- In **Report-Only** mode, `upgrade-insecure-requests` is stripped automatically (browsers ignore it there and would otherwise print a console warning).
- **Referrer-Policy** and **Permissions-Policy** are set by middleware (see code).

If you also set these headers in nginx/Caddy, avoid contradicting values.

## Sessions and rate limits

- **SESSION_COOKIE_HTTPONLY**, **SESSION_COOKIE_SAMESITE** (`Lax` by default), **SESSION_COOKIE_AGE** — see `settings.py`.
- Login: **RATELIMIT_LOGIN_RATE** (default `5/15m` per IP).
- Registration: **RATELIMIT_REGISTER_RATE** (default `5/h` per IP).
- Search and API limits: `RATELIMIT_*` variables in `settings.py` / `.env.example`.

Requires **django-ratelimit** and a shared cache in production (**Redis** recommended) so limits apply across gunicorn workers.

## Content and media (X1–X4)

- Post/comment HTML is sanitized with **bleach** in `smart_blog/forms.py` (allowlist tags/attributes).
- **MEDIA**: in production, serve files via the reverse proxy or object storage with appropriate access control; do not rely on Django `runserver` or accidental world-readable paths.
- **BACKUPS_ROOT**: restrict filesystem permissions to the deployment user only.

## Dependencies (D1–D3)

- Install app deps after clone: `pip install -r requirements.txt` (prod without ML: `requirements-prod.txt` includes **django-ratelimit**).
- Run periodically: `./scripts/audit_dependencies.sh` or `pip-audit -r requirements-prod.txt`.
- Prefer pinned versions for production images.
- **SRI**: third-party scripts in `base.html` may use `integrity=` where hashes are stable; CKEditor version bumps require hash updates — document exceptions if omitted.

## Logging and incidents (L*, B*)

- Loggers: `django.security`, `security.admin` (staff POST/DELETE under `/admin/` in production).
- **Backups**: define RPO/RTO; encrypt archives; store a copy off-site; run a **restore drill** on a staging clone at least once before go-live.
- Keep a short **incident runbook**: who can stop traffic, rotate keys, and communicate downtime.

## Infrastructure checklist

- PostgreSQL and Redis listen on private interfaces only.
- SSH: keys only; disable password authentication for root where policy allows.
- Optional: fail2ban/WAF, rate limits at edge for `/profile/login/`.
